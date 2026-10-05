import math
import os
import threading
import time

from PyQt6.QtWidgets import QWidget
from PyQt6.QtGui import QPainter, QColor, QImage, QPixmap, QPen, QTransform, QFont, QBrush, QFontMetrics
from PyQt6.QtCore import Qt, pyqtSignal, QPointF, QRectF, QTimer, QThread

import map_tiles
from mca_codec import MCARegion, read_world_surface, surface_heights

TILE = map_tiles.TILE

# Colours of the placed structures by category (border; the fill uses the same colour, translucent)
CATEGORY_COLORS = {
    "Case": (241, 196, 15), "Castelli e fortezze": (231, 76, 60), "Torri": (155, 89, 182),
    "Ponti": (230, 126, 34), "Monumenti": (26, 188, 156), "Templi e luoghi sacri": (52, 152, 219),
    "Fattorie e animali": (46, 204, 113), "Piazze e decorazioni": (236, 112, 160), "Utilità e magia": (142, 68, 173),
    "Navi": (41, 128, 185), "Rovine e portali": (192, 57, 43), "Fantascienza": (0, 206, 209),
    "Ritagli": (149, 165, 166), "Villaggio": (243, 156, 18), "Altro": (189, 195, 199),
}
GAME_STRUCTURE_COLOR = QColor(0, 229, 255)


class TileLoader(QThread):
    """
    Renders region tiles in the background, nearest to the view first.
    Each tile comes first as a quick height map, then in detail (cached on disk).
    """
    tile_ready = pyqtSignal(int, int, object)

    def __init__(self, region_dir, parent=None):
        super().__init__(parent)
        self.region_dir = region_dir
        self.cache = map_tiles.TileCache(region_dir)
        self._cond = threading.Condition()
        self._queue = {}          # (rx, rz) -> (priority, path)
        self._stop = False
        self._paused = False
        self.busy = 0

    def request(self, rx, rz, path, priority):
        with self._cond:
            old = self._queue.get((rx, rz))
            if old is None or priority < old[0]:
                self._queue[(rx, rz)] = (priority, path)
                self._cond.notify()

    def reprioritize(self, fn):
        with self._cond:
            for key, (_, path) in list(self._queue.items()):
                self._queue[key] = (fn(*key), path)

    def pending(self):
        with self._cond:
            return len(self._queue) + (self.busy or 0)

    def pause(self, paused=True):
        with self._cond:
            self._paused = paused
            self._cond.notify()

    def stop(self):
        with self._cond:
            self._stop = True
            self._queue.clear()
            self._cond.notify()

    def _take(self):
        """Next job without waiting (None if the queue is empty or loading is paused)."""
        with self._cond:
            if self._stop or self._paused or not self._queue:
                return None
            key = min(self._queue, key=lambda k: self._queue[k][0])
            _, path = self._queue.pop(key)
            return key, path

    def run(self):
        """
        Regions are rendered in parallel in separate processes (the work is pure Python, so
        threads would not help); the first pass is the quick height map, then the detailed one.
        """
        from concurrent.futures import ProcessPoolExecutor, wait, FIRST_COMPLETED
        workers = max(1, min(4, (os.cpu_count() or 2) - 1))
        cache_root = self.cache.dir and os.path.dirname(self.cache.dir)
        try:
            pool = ProcessPoolExecutor(max_workers=workers)
        except Exception:
            pool = None
        running = {}
        try:
            while not self._stop:
                while len(running) < workers:
                    job = self._take()
                    if job is None:
                        break
                    (rx, rz), path = job
                    cached = self.cache.load(rx, rz, path)
                    if cached is not None:
                        self._emit_tile(rx, rz, cached)
                        continue
                    if pool is None:
                        self._render_here(rx, rz, path)
                        continue
                    for detailed in (False, True):
                        fut = pool.submit(map_tiles.render_job, path, rx, rz, self.region_dir, detailed, cache_root)
                        running[fut] = (rx, rz)
                self.busy = len({v for v in running.values()})
                if not running:
                    with self._cond:
                        if not self._stop and (self._paused or not self._queue):
                            self._cond.wait(0.5)
                    continue
                done, _ = wait(list(running), timeout=0.3, return_when=FIRST_COMPLETED)
                for fut in done:
                    rx, rz = running.pop(fut)
                    try:
                        payload = fut.result()
                    except Exception as e:  # file being rewritten, corrupted chunk...: retry later
                        print(f"Mappa: impossibile leggere r.{rx}.{rz}: {e}")
                        payload = None
                    if not self._stop:
                        self.tile_ready.emit(rx, rz, payload)
        finally:
            self.busy = 0
            if pool is not None:
                pool.shutdown(wait=False, cancel_futures=True)

    def _emit_tile(self, rx, rz, tile):
        payload = {"image": map_tiles.shade(tile), "heights": tile["heights"],
                   "structures": tile["structures"], "detailed": tile["detailed"]}
        self.tile_ready.emit(rx, rz, payload)

    def _render_here(self, rx, rz, path):
        try:
            for detailed in (False, True):
                payload = map_tiles.render_job(path, rx, rz, self.region_dir, detailed,
                                               os.path.dirname(self.cache.dir))
                if self._stop:
                    return
                self.tile_ready.emit(rx, rz, payload)
        except Exception as e:
            print(f"Mappa: impossibile leggere r.{rx}.{rz}: {e}")
            self.tile_ready.emit(rx, rz, None)


class MapViewer(QWidget):
    # Signals
    hover_changed = pyqtSignal(int, int, int)  # x, z, y height
    structure_placed = pyqtSignal(int, int)    # grid_x, grid_z
    rotate_requested = pyqtSignal()            # R key pressed
    bridge_requested = pyqtSignal(int, int, int, int)  # grid x/z of the two banks
    area_selected = pyqtSignal(int, int, int, int)     # grid x1, z1, x2, z2 of the selected area
    mode_cancelled = pyqtSignal()
    point_selected = pyqtSignal(int, int)              # grid x/z of a single click ("point" mode)
    game_structures_changed = pyqtSignal()             # a rendered tile brought new game structures
    polygon_finished = pyqtSignal(object, bool)        # grid points of a drawn perimeter, closed?
    preview_edited = pyqtSignal(object)                # grid points of the perimeter/road after an edit

    MIN_ZOOM = 0.04
    MAX_ZOOM = 32.0

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        # Pan and Zoom state. "Grid" coordinates are relative to the current region (the anchor):
        # world = anchor * 512 + grid, and they extend beyond 0..511 into the neighbouring regions.
        self.zoom_level = 1.0
        self.pan_offset = QPointF(0, 0)
        self.last_mouse_pos = None
        self.is_panning = False

        # Tiles of every region of the world, kept while the world stays open
        self.region = None
        self.region_dir = None
        self.regions = {}          # (rx, rz) -> region file path
        self.tiles = {}            # (rx, rz) -> {"pixmap", "heights", "detailed", "structures", "stale"}
        self.requested = set()
        self.failed = {}           # (rx, rz) -> time of the failure (retried after a while)
        self.loader = None
        self._sync_regions = {}    # fallback height reads for tiles not rendered yet
        self._sync_heights = {}

        # Overlays
        self.show_game_structures = True
        self.show_placed_structures = True
        self.show_chunk_grid = True
        self.placed_structures = []   # [{title, category, x, y, z, w, h, l, ...}] in world coordinates

        # Player marker state
        self.player_x = None
        self.player_z = None

        # Structure preview & drag state
        self.selected_structure = None
        self.preview_grid_x = 0
        self.preview_grid_z = 0
        self.preview_y = 64
        self.is_dragging_structure = False
        self.drag_offset_x = 0
        self.drag_offset_z = 0
        self.is_locked = False
        self.structure_preview_pixmap = None
        self.staged_placements = []
        # Interaction mode: "place" (structures), "bridge" (click the two banks), "select" (drag an area)
        self.mode = "place"
        self.bridge_start = None
        self.select_start = None
        self.select_end = None
        self.poly_points = []        # perimeter being drawn ("polygon" mode), grid coordinates
        self.wall_preview = None     # {"points", "closed", "gates"} in grid coordinates
        self.poly_closable = True    # False while drawing a road (open line)
        self.snap_targets = []       # polylines (grid) the drawn points stick to (existing roads)
        self.edit_drag = None        # index of the vertex being dragged ("edit_poly" mode)
        self.magnet_point = None

        # UI Styling (Harmonious Premium Theme)
        self.grid_color = QColor(255, 255, 255, 20)
        self.bg_color = QColor(18, 18, 21)
        self.border_color = QColor(40, 40, 40)

        # Animation & HUD state for pulsing player marker & floating tooltip
        self.pulse_radius = 5.0
        self.pulse_alpha = 150
        self.mouse_screen_pos = None

        self.pulse_timer = QTimer(self)
        self.pulse_timer.timeout.connect(self.update_pulse_animation)
        self.pulse_timer.start(50)
        # Re-checks which tiles are needed while the view stays still (failed reads, queue order)
        self.tile_timer = QTimer(self)
        self.tile_timer.timeout.connect(self.request_visible_tiles)
        self.tile_timer.start(700)

    # ------------------------------------------------------------------
    # Region / tiles
    # ------------------------------------------------------------------
    @property
    def anchor(self):
        return (self.region.rx, self.region.rz) if self.region else (0, 0)

    def update_pulse_animation(self):
        self.pulse_radius += 0.5
        if self.pulse_radius > 20.0:
            self.pulse_radius = 5.0
        progress = (self.pulse_radius - 5.0) / 15.0
        self.pulse_alpha = int(150 * (1.0 - progress))
        if self.player_x is not None and self.player_z is not None:
            self.update()

    def set_region(self, region):
        """Shows the world of 'region' centred on it; tiles already rendered are kept."""
        self.region = region
        if region is None:
            self._set_region_dir(None)
            self.update()
            return
        self._set_region_dir(os.path.dirname(os.path.abspath(region.file_path)))
        self.regions = map_tiles.list_regions(self.region_dir)
        self.pan_offset = QPointF(0, 0)
        if self.zoom_level < 0.5:
            self.zoom_level = 1.0
        self.request_visible_tiles()
        self.update()

    def _set_region_dir(self, region_dir):
        if region_dir == self.region_dir:
            return
        self.shutdown()
        self.region_dir = region_dir
        self.tiles.clear()
        self.requested.clear()
        self.failed.clear()
        self.regions = {}
        self._sync_regions.clear()
        self._sync_heights.clear()
        if region_dir:
            self.loader = TileLoader(region_dir, self)
            self.loader.tile_ready.connect(self.on_tile_ready)
            self.loader.start()

    def shutdown(self):
        if self.loader:
            self.loader.stop()
            self.loader.wait(3000)
            self.loader = None

    def pause_loading(self, paused=True):
        """Stops reading region files (e.g. while they are being written)."""
        if self.loader:
            self.loader.pause(paused)

    def invalidate(self):
        """The world has been modified: re-render the tiles (unchanged ones come back from the cache)."""
        if self.region_dir:
            self.regions = map_tiles.list_regions(self.region_dir)
        for tile in self.tiles.values():
            tile["stale"] = True
        self.requested.clear()
        self._sync_regions.clear()
        self._sync_heights.clear()
        self.request_visible_tiles()
        self.update()

    def render_map(self):
        """Compatibility with the old single-region map: refresh everything."""
        self.invalidate()

    def on_tile_ready(self, rx, rz, payload):
        key = (rx, rz)
        if payload is None:
            self.requested.discard(key)
            self.failed[key] = time.time()
            return
        img = QImage(payload["image"], TILE, TILE, TILE * 4, QImage.Format.Format_ARGB32).copy()
        old = self.tiles.get(key)
        self.tiles[key] = {
            "pixmap": QPixmap.fromImage(img),
            "heights": payload["heights"],
            "detailed": payload["detailed"],
            "structures": payload["structures"],
            "stale": False,
        }
        if payload["detailed"]:
            self.requested.discard(key)
        elif old and old.get("detailed") and not old.get("stale"):
            self.tiles[key] = old  # never replace a detailed tile with a quick one
        self._sync_heights = {k: v for k, v in self._sync_heights.items() if (k[0], k[1]) != key}
        if payload["detailed"] and payload["structures"] != ((old or {}).get("structures") or []):
            self.game_structures_changed.emit()
        self._evict()
        self.update()

    def _evict(self, keep=160):
        if len(self.tiles) <= keep:
            return
        cx, cz = self.view_center_region()
        far = sorted(self.tiles, key=lambda k: -((k[0] - cx) ** 2 + (k[1] - cz) ** 2))
        for k in far[:len(self.tiles) - keep]:
            del self.tiles[k]  # will come back from the disk cache when needed

    def _view_transform(self):
        t = QTransform()
        t.translate(self.width() / 2, self.height() / 2)
        t.scale(self.zoom_level, self.zoom_level)
        t.translate(-256 + self.pan_offset.x(), -256 + self.pan_offset.y())
        return t

    def visible_grid_rect(self):
        inv, ok = self._view_transform().inverted()
        if not ok:
            return QRectF(0, 0, TILE, TILE)
        return inv.mapRect(QRectF(0, 0, self.width(), self.height()))

    def view_center_region(self):
        c = self.visible_grid_rect().center()
        ax, az = self.anchor
        return ax + int(c.x() // TILE), az + int(c.y() // TILE)

    def request_visible_tiles(self):
        if not self.loader or not self.region:
            return
        rect = self.visible_grid_rect()
        ax, az = self.anchor
        x1, x2 = int(rect.left() // TILE) - 1, int(rect.right() // TILE) + 1
        z1, z2 = int(rect.top() // TILE) - 1, int(rect.bottom() // TILE) + 1
        if (x2 - x1 + 1) * (z2 - z1 + 1) > 400:  # extremely zoomed out: only the regions near the centre
            c = rect.center()
            mx, mz = int(c.x() // TILE), int(c.y() // TILE)
            x1, x2, z1, z2 = mx - 10, mx + 10, mz - 10, mz + 10
        c = rect.center()
        ccx, ccz = c.x() / TILE - 0.5, c.y() / TILE - 0.5

        def priority(rx, rz):
            return (rx - ax - ccx) ** 2 + (rz - az - ccz) ** 2

        now = time.time()
        for gx in range(x1, x2 + 1):
            for gz in range(z1, z2 + 1):
                key = (ax + gx, az + gz)
                path = self.regions.get(key)
                if not path or key in self.requested:
                    continue
                tile = self.tiles.get(key)
                if tile and tile["detailed"] and not tile["stale"]:
                    continue
                if now - self.failed.get(key, 0) < 5:
                    continue
                self.requested.add(key)
                self.loader.request(key[0], key[1], path, priority(*key))
        self.loader.reprioritize(priority)

    # ------------------------------------------------------------------
    # Heights (used by the main window for placement)
    # ------------------------------------------------------------------
    def height_at(self, grid_x, grid_z):
        """Top block Y at a grid position (any region), or None where nothing is generated."""
        ax, az = self.anchor
        wx, wz = ax * TILE + grid_x, az * TILE + grid_z
        key = (wx // TILE, wz // TILE)
        lx, lz = wx - key[0] * TILE, wz - key[1] * TILE
        tile = self.tiles.get(key)
        if tile is not None:
            y = tile["heights"][lz * TILE + lx]
            return None if y == map_tiles.NO_DATA else y
        heights = self._chunk_heights_sync(key, lx // 16, lz // 16)
        return heights[(lz % 16) * 16 + lx % 16] if heights else None

    def _chunk_heights_sync(self, rkey, cx, cz):
        ck = (rkey[0], rkey[1], cx, cz)
        if ck in self._sync_heights:
            return self._sync_heights[ck]
        path = self.regions.get(rkey)
        heights = None
        if path:
            region = self._sync_regions.get(rkey)
            if region is None:
                try:
                    region = MCARegion(path)
                except OSError:
                    region = None
                if region is not None:
                    if len(self._sync_regions) > 6:
                        self._sync_regions.clear()
                    self._sync_regions[rkey] = region
            if region is not None:
                heights = region.quick_surface((cx, cz))
                if heights is None and (cx, cz) in region.chunks:
                    try:
                        chunk, _ = region.chunks[(cx, cz)]
                        heights = read_world_surface(chunk)
                        if heights is None and chunk.get("sections") and "Level" not in chunk:
                            heights, _ = surface_heights(chunk)
                    except KeyError:
                        heights = None
                    region.chunks.clear_cache()
        self._sync_heights[ck] = heights
        return heights

    def get_chunk_heightmap(self, cx, cz):
        """Y of the topmost block of each column (index z*16+x) of a chunk, in grid chunk coordinates."""
        out = []
        for z in range(16):
            for x in range(16):
                y = self.height_at(cx * 16 + x, cz * 16 + z)
                if y is None:
                    if not out and x == 0 and z == 0:
                        return None
                    y = 62
                out.append(y)
        return out

    # ------------------------------------------------------------------
    # Structures
    # ------------------------------------------------------------------
    def get_block_color(self, name):
        if "air" in name.split(":", 1)[-1] and name.endswith("air"):
            return QColor(0, 0, 0, 0)
        r, g, b = map_tiles.surface_rgb(name)
        alpha = 150 if "glass" in name or "water" in name else 255
        return QColor(r, g, b, alpha)

    def structure_pixmap(self, structure):
        """Top-down picture of a structure (one pixel per column, colour of the top block)."""
        top = {}
        for (x, y, z), block in structure.blocks.items():
            name = block.get("Name", "minecraft:air")
            if not name.endswith(":air") and y >= top.get((x, z), (-1, None))[0]:
                top[(x, z)] = (y, name)
        img = QImage(max(structure.width, 1), max(structure.length, 1), QImage.Format.Format_ARGB32)
        img.fill(Qt.GlobalColor.transparent)
        for (x, z), (_, name) in top.items():
            img.setPixelColor(x, z, self.get_block_color(name))
        return QPixmap.fromImage(img)

    def precompute_structure_preview(self):
        self.structure_preview_pixmap = self.structure_pixmap(self.selected_structure) if self.selected_structure else None

    def set_placed_structures(self, items):
        self.placed_structures = list(items or [])
        self.update()

    def game_structures(self):
        """Structure starts of the rendered tiles: [(label, x1, z1, x2, z2)] in world coordinates."""
        seen = set()
        out = []
        for tile in self.tiles.values():
            for sid, x1, z1, x2, z2 in tile.get("structures") or ():
                key = (sid, x1, z1)
                if key not in seen:
                    seen.add(key)
                    out.append((map_tiles.structure_label(sid), x1, z1, x2, z2))
        return out

    def structures_at(self, wx, wz):
        """Placed and game structures under a world position, for the tooltip."""
        found = []
        if self.show_placed_structures:
            for s in self.placed_structures:
                if s["x"] <= wx < s["x"] + s["w"] and s["z"] <= wz < s["z"] + s["l"]:
                    found.append(f"{s.get('title', s.get('name', '?'))} - {s.get('category', '')}\n"
                                 f"  X {s['x']} Y {s.get('y', '?')} Z {s['z']}  ({s['w']}x{s.get('h', '?')}x{s['l']})")
        if self.show_game_structures:
            for label, x1, z1, x2, z2 in self.game_structures():
                if x1 <= wx <= x2 and z1 <= wz <= z2:
                    found.append(f"{label} (generata dal gioco)")
        return found

    # ------------------------------------------------------------------
    # Modes / selection
    # ------------------------------------------------------------------
    def set_mode(self, mode):
        self.mode = mode
        self.poly_points = []
        self.bridge_start = None
        self.select_start = self.select_end = None
        self.setCursor(Qt.CursorShape.CrossCursor if mode != "place" else Qt.CursorShape.ArrowCursor)
        self.update()

    def set_selected_structure(self, structure, keep_lock=False):
        self.selected_structure = structure
        if not keep_lock:
            self.is_locked = False
        self.precompute_structure_preview()
        self.update()

    def set_player_position(self, px, pz):
        self.player_x = px
        self.player_z = pz
        self.update()

    def get_color_for_height(self, y):
        return QColor(*map_tiles.HEIGHT_RGB.get(y, (35, 120, 45)))

    # ------------------------------------------------------------------
    # Painting
    # ------------------------------------------------------------------
    def _grid_of_world(self, wx, wz):
        ax, az = self.anchor
        return wx - ax * TILE, wz - az * TILE

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), self.bg_color)

        if not self.region:
            painter.setPen(QColor(110, 110, 110))
            painter.setFont(QFont("Outfit", 12))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter,
                             "Nessuna mappa caricata\nSeleziona una cartella salvataggi")
            return

        transform = self._view_transform()
        painter.setTransform(transform)
        visible = self.visible_grid_rect()
        ax, az = self.anchor
        z = self.zoom_level
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, z < 1.0)

        # --- terrain tiles ---
        x1, x2 = int(visible.left() // TILE), int(visible.right() // TILE)
        z1, z2 = int(visible.top() // TILE), int(visible.bottom() // TILE)
        missing = False
        for gx in range(x1, x2 + 1):
            for gz in range(z1, z2 + 1):
                key = (ax + gx, az + gz)
                ox, oz = gx * TILE, gz * TILE
                tile = self.tiles.get(key)
                if tile:
                    painter.drawPixmap(ox, oz, tile["pixmap"])
                elif key in self.regions:
                    missing = True
                    painter.fillRect(QRectF(ox, oz, TILE, TILE), QColor(32, 32, 38))
                    painter.setPen(QPen(QColor(80, 80, 90), 0))
                    painter.drawRect(QRectF(ox, oz, TILE, TILE))
        if missing:
            QTimer.singleShot(0, self.request_visible_tiles)

        # --- grids ---
        cosmetic = QPen(QColor(255, 255, 255, 34), 0)
        if self.show_chunk_grid and z >= 2.0:
            painter.setPen(cosmetic)
            cx1, cx2 = int(visible.left() // 16), int(visible.right() // 16) + 1
            cz1, cz2 = int(visible.top() // 16), int(visible.bottom() // 16) + 1
            for c in range(cx1, cx2 + 1):
                painter.drawLine(QPointF(c * 16, visible.top()), QPointF(c * 16, visible.bottom()))
            for c in range(cz1, cz2 + 1):
                painter.drawLine(QPointF(visible.left(), c * 16), QPointF(visible.right(), c * 16))
        painter.setPen(QPen(QColor(255, 255, 255, 55), 0))
        for gx in range(x1, x2 + 2):
            painter.drawLine(QPointF(gx * TILE, visible.top()), QPointF(gx * TILE, visible.bottom()))
        for gz in range(z1, z2 + 2):
            painter.drawLine(QPointF(visible.left(), gz * TILE), QPointF(visible.right(), gz * TILE))
        # current region highlighted
        painter.setPen(QPen(QColor(46, 204, 113, 110), 0))
        painter.drawRect(QRectF(0, 0, TILE, TILE))

        labels = []  # (screen point, text, colour, bold) drawn later without zoom
        # --- game structures (villages, temples...) ---
        if self.show_game_structures:
            pen = QPen(GAME_STRUCTURE_COLOR, 0, Qt.PenStyle.DashLine)
            for label, sx1, sz1, sx2, sz2 in self.game_structures():
                gx1, gz1 = self._grid_of_world(sx1, sz1)
                rect = QRectF(gx1, gz1, sx2 - sx1 + 1, sz2 - sz1 + 1)
                if not rect.intersects(visible):
                    continue
                painter.fillRect(rect, QColor(0, 229, 255, 28))
                painter.setPen(pen)
                painter.drawRect(rect)
                labels.append((transform.map(QPointF(rect.left(), rect.top())), label, GAME_STRUCTURE_COLOR, False,
                               rect.width() * z))

        # --- structures placed with the program ---
        if self.show_placed_structures:
            for s in self.placed_structures:
                gx1, gz1 = self._grid_of_world(s["x"], s["z"])
                rect = QRectF(gx1, gz1, s["w"], s["l"])
                if not rect.intersects(visible):
                    continue
                rgb = CATEGORY_COLORS.get(s.get("category"), CATEGORY_COLORS["Altro"])
                painter.fillRect(rect, QColor(*rgb, 45 if z >= 2 else 90))
                painter.setPen(QPen(QColor(*rgb, 235), 0 if z < 3 else 1.5 / z * 2))
                painter.drawRect(rect)
                if z < 0.6:  # far away: a dot so that even small buildings stay visible
                    c = rect.center()
                    r = 3.5 / z
                    painter.setBrush(QColor(*rgb, 230))
                    painter.drawEllipse(c, r, r)
                    painter.setBrush(Qt.BrushStyle.NoBrush)
                labels.append((transform.map(QPointF(rect.left(), rect.top())), s.get("title") or s.get("name", ""),
                               QColor(*rgb), True, rect.width() * z))

        # --- staged placements (not injected yet) ---
        if self.staged_placements:
            path_color = QColor(214, 180, 120, 170)
            flat = []
            for entry in self.staged_placements:
                flat.extend(entry["items"] if entry.get("kind") == "group" else [entry])
            for item in flat:
                if item.get("kind") == "path":
                    for (x, zz) in item.get("cells", ()):
                        gx, gz = self._grid_of_world(x, zz)
                        painter.fillRect(QRectF(gx, gz, 1, 1), path_color)
                    continue
                if item.get("preview_pixmap") is None:
                    item["preview_pixmap"] = self.structure_pixmap(item["structure"])
                s = item["structure"]
                gx, gz = self._grid_of_world(item["world_x"], item["world_z"])
                rect = QRectF(gx, gz, s.width, s.length)
                if not rect.intersects(visible):
                    continue
                painter.setOpacity(0.8)
                painter.drawPixmap(rect.toRect(), item["preview_pixmap"])
                painter.setOpacity(1.0)
                painter.setPen(QPen(QColor(255, 255, 255, 200), 0, Qt.PenStyle.DashLine))
                painter.drawRect(rect)
                labels.append((transform.map(QPointF(rect.left(), rect.bottom())),
                               f"{item['name']} (Y:{item['y_coord']}) - da iniettare", QColor(220, 220, 220), False,
                               max(rect.width() * z, 120)))

        self.hint_text = None
        self._draw_wall_overlay(painter)

        # --- bridge / area selection overlays ---
        if self.mode == "bridge" and self.bridge_start and self.mouse_screen_pos is not None:
            sx, sz = self.bridge_start
            gx, gz = self.bridge_end(sx, sz, *self.screen_to_grid(self.mouse_screen_pos))
            band = QRectF(min(sx, gx) - (2 if sz == gz else 0), min(sz, gz) - (2 if sx == gx else 0),
                          abs(gx - sx) + (1 if sz == gz else 5), abs(gz - sz) + (1 if sx == gx else 5))
            painter.fillRect(band, QColor(241, 196, 15, 60))
            painter.setPen(QPen(QColor(241, 196, 15, 230), 0, Qt.PenStyle.DashLine))
            painter.drawRect(band)
            painter.fillRect(QRectF(sx - 1, sz - 1, 3, 3), QColor(241, 196, 15, 230))
        if self.mode == "select" and self.select_start and self.select_end:
            (sx1, sz1), (sx2, sz2) = self.select_start, self.select_end
            rect = QRectF(min(sx1, sx2), min(sz1, sz2), abs(sx2 - sx1) + 1, abs(sz2 - sz1) + 1)
            painter.fillRect(rect, QColor(52, 152, 219, 50))
            painter.setPen(QPen(QColor(52, 152, 219, 230), 0, Qt.PenStyle.DashLine))
            painter.drawRect(rect)

        # --- structure being placed ---
        if self.selected_structure:
            sw, sl = self.selected_structure.width, self.selected_structure.length
            rect = QRectF(self.preview_grid_x, self.preview_grid_z, sw, sl)
            if self.structure_preview_pixmap:
                painter.setOpacity(0.85)
                painter.drawPixmap(rect.toRect(), self.structure_preview_pixmap)
                painter.setOpacity(1.0)
            painter.fillRect(rect, QColor(46, 204, 113, 30))
            painter.setPen(QPen(QColor(46, 204, 113, 220), 0))
            painter.drawRect(rect)
            painter.setPen(QPen(QColor(231, 76, 60, 220), 0))
            painter.drawLine(QPointF(self.preview_grid_x + sw / 2, self.preview_grid_z),
                             QPointF(self.preview_grid_x + sw / 2, self.preview_grid_z - max(3, 6 / z)))
            labels.append((transform.map(QPointF(rect.left(), rect.bottom())),
                           f"{sw}x{self.selected_structure.height}x{sl}", QColor(255, 255, 255), True, 200))

        # --- player ---
        painter.setTransform(QTransform())
        if self.player_x is not None and self.player_z is not None:
            gx, gz = self.player_x - ax * TILE, self.player_z - az * TILE
            p = transform.map(QPointF(gx, gz))
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.setBrush(QColor(231, 76, 60, self.pulse_alpha))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(p, self.pulse_radius, self.pulse_radius)
            painter.setBrush(QColor(231, 76, 60))
            painter.setPen(QPen(QColor(255, 255, 255), 1.5))
            painter.drawEllipse(p, 4.5, 4.5)

        # --- labels (screen space, readable at any zoom) ---
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        self._draw_labels(painter, labels)
        self._draw_region_names(painter, transform, x1, x2, z1, z2)
        self._draw_hud(painter)
        self._draw_hint(painter)
        self._draw_tooltip(painter)

    def _draw_hint(self, painter):
        """One line of help at the top of the map while drawing or editing a line."""
        text = getattr(self, "hint_text", None)
        if not text:
            if self.mode == "polygon":
                n = len(self.poly_points)
                text = ("Clic per aggiungere punti (Shift = linea libera)  |  Backspace annulla l'ultimo  |  "
                        + ("Invio o clic sul primo punto chiude, C chiude allineato, doppio clic = tratto aperto"
                           if self.poly_closable else "Invio o doppio clic per finire")
                        + ("" if n else "  |  Esc esce"))
            elif self.mode == "edit_poly":
                text = ("Modifica: trascina i punti azzurri  |  doppio clic su un tratto aggiunge un punto  |  "
                        "clic destro su un punto lo toglie  |  Esc per finire")
        if not text:
            return
        painter.setFont(QFont("Segoe UI", 9))
        fm = QFontMetrics(painter.font())
        w = fm.horizontalAdvance(text) + 20
        rect = QRectF((self.width() - w) / 2, 8, w, 24)
        painter.setBrush(QColor(12, 12, 16, 215))
        painter.setPen(QPen(QColor(241, 196, 15, 180), 1))
        painter.drawRoundedRect(rect, 6, 6)
        painter.setPen(QColor(240, 240, 248))
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, text)

    def _vertex_at(self, gx, gz):
        if not self.wall_preview:
            return None
        thr = max(1.5, 8.0 / self.zoom_level)
        best = None
        for i, (x, z) in enumerate(self.wall_preview["points"]):
            d = math.hypot(x - gx, z - gz)
            if d <= thr and (best is None or d < best[0]):
                best = (d, i)
        return best[1] if best else None

    def _segment_at(self, gx, gz):
        pts = self.wall_preview["points"] if self.wall_preview else []
        segs = list(zip(range(len(pts)), pts, pts[1:] + (pts[:1] if self.wall_preview.get("closed") else [])))
        thr = max(1.5, 8.0 / self.zoom_level)
        for i, (ax, az), (bx, bz) in segs:
            dx, dz = bx - ax, bz - az
            ln2 = dx * dx + dz * dz
            if not ln2:
                continue
            t = max(0.0, min(1.0, ((gx - ax) * dx + (gz - az) * dz) / ln2))
            if math.hypot(ax + t * dx - gx, az + t * dz - gz) <= thr:
                return i + 1, (int(round(ax + t * dx)), int(round(az + t * dz)))
        return None

    def _draw_labels(self, painter, labels):
        font = QFont("Segoe UI", 8)
        bold = QFont("Segoe UI", 8)
        bold.setBold(True)
        taken = []
        for point, text, color, is_bold, width_px in labels:
            if not text or (width_px < 14 and self.zoom_level < 0.6 and not is_bold):
                continue
            painter.setFont(bold if is_bold else font)
            fm = QFontMetrics(painter.font())
            w = fm.horizontalAdvance(text) + 8
            rect = QRectF(point.x(), point.y() - 16, w, 15)
            if not rect.intersects(QRectF(self.rect())) or any(rect.intersects(t) for t in taken):
                continue
            taken.append(rect)
            painter.setBrush(QColor(12, 12, 16, 200))
            painter.setPen(QPen(QColor(color.red(), color.green(), color.blue(), 200), 1))
            painter.drawRoundedRect(rect, 3, 3)
            painter.setPen(color)
            painter.drawText(rect.adjusted(4, 0, -2, 0), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, text)

    def _draw_region_names(self, painter, transform, x1, x2, z1, z2):
        if self.zoom_level < 0.12:
            return
        ax, az = self.anchor
        painter.setFont(QFont("Segoe UI", 8))
        for gx in range(x1, x2 + 1):
            for gz in range(z1, z2 + 1):
                key = (ax + gx, az + gz)
                if key not in self.regions:
                    continue
                p = transform.map(QPointF(gx * TILE, gz * TILE))
                tile = self.tiles.get(key)
                state = "" if tile and tile["detailed"] else "  (caricamento...)" if key in self.requested else ""
                painter.setPen(QColor(255, 255, 255, 120))
                painter.drawText(QPointF(p.x() + 5, p.y() + 13), f"r.{key[0]}.{key[1]}{state}")

    def _draw_hud(self, painter):
        n_placed = len(self.placed_structures)
        n_game = len(self.game_structures())
        pending = self.loader.pending() if self.loader else 0
        lines = [f"Zoom {self.zoom_level * 100:.0f}%   |   regioni caricate {sum(1 for t in self.tiles.values() if t['detailed'])}"
                 f"/{len(self.regions)}" + (f"   |   in caricamento: {pending}" if pending else "")]
        lines.append(f"Strutture: {n_placed} piazzate col programma, {n_game} generate dal gioco")
        painter.setFont(QFont("Segoe UI", 8))
        fm = QFontMetrics(painter.font())
        w = max(fm.horizontalAdvance(t) for t in lines) + 16
        rect = QRectF(10, self.height() - 14 - 16 * len(lines), w, 16 * len(lines) + 6)
        painter.setBrush(QColor(12, 12, 16, 190))
        painter.setPen(QPen(QColor(60, 60, 70), 1))
        painter.drawRoundedRect(rect, 6, 6)
        painter.setPen(QColor(210, 210, 220))
        for i, t in enumerate(lines):
            painter.drawText(QPointF(rect.left() + 8, rect.top() + 15 + 16 * i), t)
        # scale bar
        blocks = 16
        for b in (16, 32, 64, 128, 256, 512, 1024, 2048, 4096):
            if b * self.zoom_level >= 70:
                blocks = b
                break
        px = blocks * self.zoom_level
        y = 30
        x = self.width() - px - 20
        painter.setPen(QPen(QColor(230, 230, 235), 2))
        painter.drawLine(QPointF(x, y), QPointF(x + px, y))
        painter.drawLine(QPointF(x, y - 4), QPointF(x, y + 2))
        painter.drawLine(QPointF(x + px, y - 4), QPointF(x + px, y + 2))
        painter.drawText(QRectF(x, y - 20, px, 14), Qt.AlignmentFlag.AlignCenter, f"{blocks} blocchi")

    def _draw_tooltip(self, painter):
        if not (self.mouse_screen_pos and self.underMouse() and self.region) or self.is_panning:
            return
        grid_x, grid_z = self.screen_to_grid(self.mouse_screen_pos)
        ax, az = self.anchor
        world_x, world_z = ax * TILE + grid_x, az * TILE + grid_z
        y_val = self.height_at(grid_x, grid_z)
        lines = [f"Coordinate: {world_x}, {world_z}",
                 f"Altezza Y: {y_val if y_val is not None else 'zona non generata'}",
                 f"Regione r.{world_x // TILE}.{world_z // TILE}  -  chunk {world_x // 16}, {world_z // 16}"]
        found = self.structures_at(world_x, world_z)
        if found:
            lines.append("")
            lines.extend(found)
        painter.setFont(QFont("Segoe UI", 9))
        fm = QFontMetrics(painter.font())
        text_lines = "\n".join(lines).split("\n")
        tt_w = max(fm.horizontalAdvance(t) for t in text_lines) + 18
        tt_h = fm.height() * len(text_lines) + 14
        mx = self.mouse_screen_pos.x() + 16
        my = self.mouse_screen_pos.y() + 16
        if mx + tt_w > self.width():
            mx = self.mouse_screen_pos.x() - tt_w - 10
        if my + tt_h > self.height():
            my = self.mouse_screen_pos.y() - tt_h - 10
        rect = QRectF(mx, my, tt_w, tt_h)
        painter.setBrush(QColor(16, 16, 20, 225))
        painter.setPen(QPen(QColor(46, 204, 113, 170), 1.5))
        painter.drawRoundedRect(rect, 8.0, 8.0)
        painter.setPen(QColor(240, 240, 248))
        painter.drawText(rect.adjusted(9, 7, -9, -7), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop,
                         "\n".join(text_lines))

    @staticmethod
    def bridge_end(sx, sz, gx, gz):
        """Bridges are straight: the second bank is aligned with the first on the main axis."""
        return (gx, sz) if abs(gx - sx) >= abs(gz - sz) else (sx, gz)

    def magnet(self, gx, gz):
        """Point of an existing road/line near (gx, gz): a vertex first, otherwise the nearest point."""
        thr = max(2.0, 9.0 / self.zoom_level)
        best = None
        for line in self.snap_targets:
            for (x, z) in line:
                d = math.hypot(x - gx, z - gz)
                if d <= thr and (best is None or d < best[0]):
                    best = (d - 0.5, (x, z))
            for (ax, az), (bx, bz) in zip(line, line[1:]):
                dx, dz = bx - ax, bz - az
                ln2 = dx * dx + dz * dz
                if not ln2:
                    continue
                t = max(0.0, min(1.0, ((gx - ax) * dx + (gz - az) * dz) / ln2))
                px, pz = ax + t * dx, az + t * dz
                d = math.hypot(px - gx, pz - gz)
                if d <= thr and (best is None or d < best[0]):
                    best = (d, (int(round(px)), int(round(pz))))
        return best[1] if best else None

    @staticmethod
    def aligned(a, b):
        dx, dz = b[0] - a[0], b[1] - a[1]
        return dx == 0 or dz == 0 or abs(dx) == abs(dz)

    @staticmethod
    def closing_corner(last, first):
        """Corner to add so that last -> corner -> first are both at 0/45/90 degrees (None if not needed)."""
        if MapViewer.aligned(last, first):
            return None
        (lx, lz), (fx, fz) = last, first
        dx, dz = fx - lx, fz - lz
        sx, sz = (1 if dx > 0 else -1), (1 if dz > 0 else -1)
        d = min(abs(dx), abs(dz))
        options = [(fx, lz), (lx, fz), (lx + sx * d, lz + sz * d), (fx - sx * d, fz - sz * d)]

        def length(c):
            return math.hypot(c[0] - lx, c[1] - lz) + math.hypot(fx - c[0], fz - c[1])
        return min(options, key=length)

    def snapped_point(self, gx, gz, free=False):
        """Next perimeter point: on an existing road nearby, else 0/45/90 degrees from the previous one."""
        self.magnet_point = self.magnet(gx, gz) if not free else None
        if self.magnet_point:
            return self.magnet_point
        if not self.poly_points or free:
            return gx, gz
        px, pz = self.poly_points[-1]
        dx, dz = gx - px, gz - pz
        if abs(dx) > 2 * abs(dz):
            return gx, pz
        if abs(dz) > 2 * abs(dx):
            return px, gz
        d = round((abs(dx) + abs(dz)) / 2)
        return px + (d if dx >= 0 else -d), pz + (d if dz >= 0 else -d)

    def _draw_wall_overlay(self, painter):
        z = self.zoom_level
        pts = None
        closed = False
        gates = []
        if self.mode == "polygon" and self.poly_points:
            pts = list(self.poly_points)
            if self.mouse_screen_pos is not None:
                gx, gz = self.screen_to_grid(self.mouse_screen_pos)
                from PyQt6.QtWidgets import QApplication
                free = bool(QApplication.keyboardModifiers() & Qt.KeyboardModifier.ShiftModifier)
                pts.append(self.snapped_point(gx, gz, free))
        elif self.wall_preview:
            pts = self.wall_preview["points"]
            closed = self.wall_preview["closed"]
            gates = self.wall_preview.get("gates", [])
        if not pts:
            return
        editing = self.mode == "edit_poly" and self.wall_preview
        poly = [QPointF(x + 0.5, zz + 0.5) for x, zz in pts]
        if closed:
            poly.append(poly[0])
        # closing hint while drawing a perimeter: aligned or not, and the corner that would align it
        if self.mode == "polygon" and self.poly_closable and len(self.poly_points) >= 2:
            first, cur = self.poly_points[0], pts[-1]
            dist = math.hypot(cur[0] - first[0], cur[1] - first[1])
            if dist <= max(16, 60 / z):
                fp = QPointF(first[0] + 0.5, first[1] + 0.5)
                ok = self.aligned(cur, first)
                colour = QColor(46, 204, 113, 230) if ok else QColor(230, 126, 34, 230)
                painter.setPen(QPen(colour, 0, Qt.PenStyle.DashLine))
                painter.drawLine(poly[-1], fp)
                painter.drawEllipse(fp, max(2.0, 7 / z), max(2.0, 7 / z))
                corner = self.closing_corner(cur, first)
                if corner:
                    cp = QPointF(corner[0] + 0.5, corner[1] + 0.5)
                    painter.setPen(QPen(QColor(46, 204, 113, 200), 0, Qt.PenStyle.DotLine))
                    painter.drawLine(poly[-1], cp)
                    painter.drawLine(cp, fp)
                    painter.setBrush(QColor(46, 204, 113, 200))
                    painter.drawEllipse(cp, max(1.0, 3 / z), max(1.0, 3 / z))
                    painter.setBrush(Qt.BrushStyle.NoBrush)
                    self.hint_text = (f"Chiusura NON allineata: premi C per chiudere con un angolo in "
                                      f"X {self.anchor[0] * TILE + corner[0]}, Z {self.anchor[1] * TILE + corner[1]}")
                else:
                    self.hint_text = "Chiusura allineata: clicca sul primo punto (o premi Invio) per chiudere"
        if self.magnet_point and self.mode == "polygon":
            mp = QPointF(self.magnet_point[0] + 0.5, self.magnet_point[1] + 0.5)
            painter.setPen(QPen(QColor(0, 229, 255, 240), 0))
            painter.drawEllipse(mp, max(1.5, 6 / z), max(1.5, 6 / z))
        band = QPen(QColor(149, 165, 166, 150), 3.0)
        band.setCapStyle(Qt.PenCapStyle.RoundCap)
        band.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(band)
        for a, b2 in zip(poly, poly[1:]):
            painter.drawLine(a, b2)
        painter.setPen(QPen(QColor(241, 196, 15, 240), 0, Qt.PenStyle.DashLine))
        for a, b2 in zip(poly, poly[1:]):
            painter.drawLine(a, b2)
        r = max(1.0, (6 if editing else 4) / z)
        painter.setBrush(QColor(241, 196, 15, 230) if not editing else QColor(0, 229, 255, 230))
        for p in poly[:len(pts)]:
            painter.drawEllipse(p, r, r)
        painter.setBrush(QColor(231, 76, 60, 230))
        for gx, gz in gates:
            painter.drawRect(QRectF(gx - 3, gz - 3, 7, 7))
        painter.setBrush(Qt.BrushStyle.NoBrush)

    # ------------------------------------------------------------------
    # Input
    # ------------------------------------------------------------------
    def screen_to_grid(self, screen_pos):
        inv, ok = self._view_transform().inverted()
        if not ok:
            return 0, 0
        p = inv.map(QPointF(screen_pos))
        return int(p.x() // 1), int(p.y() // 1)

    def mousePressEvent(self, event):
        has_map = self.region is not None
        if event.button() == Qt.MouseButton.MiddleButton or (event.button() == Qt.MouseButton.LeftButton and event.modifiers() == Qt.KeyboardModifier.ControlModifier):
            self.is_panning = True
            self.last_mouse_pos = event.position()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
        elif event.button() == Qt.MouseButton.LeftButton and self.mode == "bridge" and has_map:
            grid_x, grid_z = self.screen_to_grid(event.position())
            if self.bridge_start is None:
                self.bridge_start = (grid_x, grid_z)
            else:
                (ax, az), self.bridge_start = self.bridge_start, None
                bx, bz = self.bridge_end(ax, az, grid_x, grid_z)
                self.bridge_requested.emit(ax, az, bx, bz)
            self.update()
        elif event.button() == Qt.MouseButton.LeftButton and self.mode == "polygon" and has_map:
            gx, gz = self.screen_to_grid(event.position())
            free = bool(event.modifiers() & Qt.KeyboardModifier.ShiftModifier)
            p = self.snapped_point(gx, gz, free)
            if len(self.poly_points) >= 3:
                fx, fz = self.poly_points[0]
                if abs(p[0] - fx) + abs(p[1] - fz) <= max(3, 10 / self.zoom_level):
                    self._finish_polygon(True)
                    return
            if not self.poly_points or p != self.poly_points[-1]:
                self.poly_points.append(p)
            self.update()
        elif event.button() == Qt.MouseButton.RightButton and self.mode == "polygon":
            self._finish_polygon(len(self.poly_points) >= 3 and self.poly_closable)
        elif self.mode == "edit_poly" and self.wall_preview and event.button() == Qt.MouseButton.LeftButton:
            idx = self._vertex_at(*self.screen_to_grid(event.position()))
            if idx is not None:
                self.edit_drag = idx
                self.setCursor(Qt.CursorShape.SizeAllCursor)
            else:
                self.is_panning = True
                self.last_mouse_pos = event.position()
        elif self.mode == "edit_poly" and self.wall_preview and event.button() == Qt.MouseButton.RightButton:
            idx = self._vertex_at(*self.screen_to_grid(event.position()))
            pts = self.wall_preview["points"]
            if idx is not None and len(pts) > (3 if self.wall_preview.get("closed") else 2):
                pts.pop(idx)
                self.preview_edited.emit(list(pts))
                self.update()
        elif event.button() == Qt.MouseButton.LeftButton and self.mode == "point" and has_map:
            self.point_selected.emit(*self.screen_to_grid(event.position()))
        elif event.button() == Qt.MouseButton.LeftButton and self.mode == "select" and has_map:
            self.select_start = self.select_end = self.screen_to_grid(event.position())
            self.update()
        elif event.button() == Qt.MouseButton.LeftButton:
            if self.selected_structure and has_map:
                grid_x, grid_z = self.screen_to_grid(event.position())
                sw = self.selected_structure.width
                sl = self.selected_structure.length
                if (self.preview_grid_x <= grid_x < self.preview_grid_x + sw) and (self.preview_grid_z <= grid_z < self.preview_grid_z + sl):
                    self.drag_offset_x = grid_x - self.preview_grid_x
                    self.drag_offset_z = grid_z - self.preview_grid_z
                else:
                    # Relocate preview box center to click, lock coordinates, and start dragging immediately
                    self.preview_grid_x = grid_x - sw // 2
                    self.preview_grid_z = grid_z - sl // 2
                    self.drag_offset_x = sw // 2
                    self.drag_offset_z = sl // 2
                    self.structure_placed.emit(self.preview_grid_x, self.preview_grid_z)
                self.is_dragging_structure = True
                self.is_locked = True
                self.setCursor(Qt.CursorShape.SizeAllCursor)
                self.update()
            else:
                self.is_panning = True
                self.last_mouse_pos = event.position()
                self.setCursor(Qt.CursorShape.ClosedHandCursor)
        elif event.button() == Qt.MouseButton.RightButton:
            # Right-click unlocks placement to follow mouse
            self.is_locked = False
            self.update()

    def _finish_polygon(self, closed):
        pts = list(self.poly_points)
        self.poly_points = []
        if len(pts) >= 2:
            self.mode = "place"
            self.setCursor(Qt.CursorShape.ArrowCursor)
            self.polygon_finished.emit(pts, closed and len(pts) >= 3)
        self.update()

    def mouseDoubleClickEvent(self, event):
        if self.mode == "polygon" and event.button() == Qt.MouseButton.LeftButton:
            self._finish_polygon(False)
            return
        if self.mode == "edit_poly" and self.wall_preview and event.button() == Qt.MouseButton.LeftButton:
            hit = self._segment_at(*self.screen_to_grid(event.position()))
            if hit:
                self.wall_preview["points"].insert(hit[0], hit[1])
                self.preview_edited.emit(list(self.wall_preview["points"]))
                self.update()
            return
        super().mouseDoubleClickEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.mode == "select" and self.select_start:
            (x1, z1), (x2, z2) = self.select_start, self.screen_to_grid(event.position())
            self.select_start = self.select_end = None
            self.update()
            if abs(x2 - x1) >= 1 and abs(z2 - z1) >= 1:
                self.area_selected.emit(min(x1, x2), min(z1, z2), max(x1, x2), max(z1, z2))
            return
        if self.edit_drag is not None and event.button() == Qt.MouseButton.LeftButton:
            self.edit_drag = None
            self.setCursor(Qt.CursorShape.ArrowCursor)
            self.preview_edited.emit(list(self.wall_preview["points"]))
            self.update()
            return
        if event.button() in (Qt.MouseButton.MiddleButton, Qt.MouseButton.LeftButton):
            if self.is_dragging_structure:
                self.is_dragging_structure = False
                self.structure_placed.emit(self.preview_grid_x, self.preview_grid_z)
            if self.is_panning:
                self.request_visible_tiles()
            self.is_panning = False
            self.setCursor(Qt.CursorShape.ArrowCursor if self.mode == "place" else Qt.CursorShape.CrossCursor)
            self.update()

    def mouseMoveEvent(self, event):
        self.mouse_screen_pos = event.position()
        grid_x, grid_z = self.screen_to_grid(event.position())

        if self.is_panning and self.last_mouse_pos:
            delta = event.position() - self.last_mouse_pos
            self.pan_offset += delta / self.zoom_level
            self.last_mouse_pos = event.position()
            self.update()
            return

        if self.mode == "select" and self.select_start:
            self.select_end = (grid_x, grid_z)
            self.trigger_hover_event(grid_x, grid_z)
            self.update()
            return
        if self.mode in ("bridge", "point", "polygon"):
            self.trigger_hover_event(grid_x, grid_z)
            self.update()
            return
        if self.mode == "edit_poly":
            if self.edit_drag is not None and self.wall_preview:
                p = self.magnet(grid_x, grid_z) or (grid_x, grid_z)
                self.wall_preview["points"][self.edit_drag] = p
            self.trigger_hover_event(grid_x, grid_z)
            self.update()
            return

        if self.is_dragging_structure and self.selected_structure:
            self.preview_grid_x = grid_x - self.drag_offset_x
            self.preview_grid_z = grid_z - self.drag_offset_z
            self.structure_placed.emit(self.preview_grid_x, self.preview_grid_z)
            self.update()
            self.trigger_hover_event(grid_x, grid_z)
            return

        if self.selected_structure and not self.is_dragging_structure and not self.is_locked:
            sw = self.selected_structure.width
            sl = self.selected_structure.length
            self.preview_grid_x = grid_x - sw // 2
            self.preview_grid_z = grid_z - sl // 2

        self.trigger_hover_event(grid_x, grid_z)
        self.update()

    def leaveEvent(self, event):
        self.update()

    def trigger_hover_event(self, grid_x, grid_z):
        if not self.region:
            return
        y_val = self.height_at(grid_x, grid_z)
        if y_val is None:
            return
        self.preview_y = y_val
        ax, az = self.anchor
        self.hover_changed.emit(ax * TILE + grid_x, az * TILE + grid_z, y_val)

    def zoom_by(self, factor, screen_pos=None):
        old_zoom = self.zoom_level
        self.zoom_level = max(self.MIN_ZOOM, min(self.zoom_level * factor, self.MAX_ZOOM))
        if old_zoom != self.zoom_level:
            pos = screen_pos if screen_pos is not None else QPointF(self.width() / 2, self.height() / 2)
            center = QPointF(self.width() / 2, self.height() / 2)
            self.pan_offset += (pos - center) * (1.0 / self.zoom_level - 1.0 / old_zoom)
        self.request_visible_tiles()
        self.update()

    def wheelEvent(self, event):
        self.zoom_by(1.2 if event.angleDelta().y() > 0 else 1 / 1.2, event.position())

    def keyPressEvent(self, event):
        key = event.key()
        if self.mode == "polygon":
            if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                self._finish_polygon(bool(event.modifiers() & Qt.KeyboardModifier.ShiftModifier) is False
                                     and len(self.poly_points) >= 3 and self.poly_closable)
                return
            if key == Qt.Key.Key_C and self.poly_closable and len(self.poly_points) >= 2:
                corner = self.closing_corner(self.poly_points[-1], self.poly_points[0])
                if corner and corner not in self.poly_points:
                    self.poly_points.append(corner)
                self._finish_polygon(len(self.poly_points) >= 3)
                return
            if key == Qt.Key.Key_Backspace and self.poly_points:
                self.poly_points.pop()
                self.update()
                return
        if key == Qt.Key.Key_Escape and self.mode != "place":
            self.set_mode("place")
            self.mode_cancelled.emit()
            return
        if key == Qt.Key.Key_R and self.selected_structure:
            # The main window owns the selected structure: rotating only the preview
            # here would inject a structure different from the one displayed.
            self.rotate_requested.emit()
            return
        if key in (Qt.Key.Key_Plus, Qt.Key.Key_Equal):
            self.zoom_by(1.25)
        elif key == Qt.Key.Key_Minus:
            self.zoom_by(1 / 1.25)
        elif key in (Qt.Key.Key_Left, Qt.Key.Key_Right, Qt.Key.Key_Up, Qt.Key.Key_Down,
                     Qt.Key.Key_A, Qt.Key.Key_D, Qt.Key.Key_W, Qt.Key.Key_S):
            step = 120 / self.zoom_level
            dx = step if key in (Qt.Key.Key_Left, Qt.Key.Key_A) else -step if key in (Qt.Key.Key_Right, Qt.Key.Key_D) else 0
            dz = step if key in (Qt.Key.Key_Up, Qt.Key.Key_W) else -step if key in (Qt.Key.Key_Down, Qt.Key.Key_S) else 0
            self.pan_offset += QPointF(dx, dz)
            self.request_visible_tiles()
            self.update()
        else:
            super().keyPressEvent(event)

    def center_on_grid(self, gx, gz, zoom=None):
        if zoom is not None:
            self.zoom_level = max(self.MIN_ZOOM, min(zoom, self.MAX_ZOOM))
        self.pan_offset = QPointF(256 - gx, 256 - gz)
        self.request_visible_tiles()
        self.update()

    def center_on_map(self):
        self.center_on_grid(256, 256, 1.0)

    def show_whole_world(self):
        """Zooms out to fit every region of the world."""
        if not self.regions or not self.region:
            return
        ax, az = self.anchor
        xs = [k[0] for k in self.regions]
        zs = [k[1] for k in self.regions]
        w = (max(xs) - min(xs) + 1) * TILE
        h = (max(zs) - min(zs) + 1) * TILE
        zoom = min(self.width() / w, self.height() / h) * 0.95
        cx = (min(xs) - ax) * TILE + w / 2
        cz = (min(zs) - az) * TILE + h / 2
        self.center_on_grid(cx, cz, zoom)
