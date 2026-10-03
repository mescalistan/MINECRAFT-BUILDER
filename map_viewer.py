from PyQt6.QtWidgets import QWidget
from PyQt6.QtGui import QPainter, QColor, QImage, QPixmap, QPen, QTransform, QFont
from PyQt6.QtCore import Qt, pyqtSignal, QPointF, QRectF, QTimer
from mca_codec import read_world_surface, surface_heights

class MapViewer(QWidget):
    # Signals
    hover_changed = pyqtSignal(int, int, int)  # x, z, y height
    structure_placed = pyqtSignal(int, int)    # grid_x, grid_z
    rotate_requested = pyqtSignal()            # R key pressed
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        
        # Pan and Zoom state
        self.zoom_level = 1.0
        self.pan_offset = QPointF(0, 0)
        self.last_mouse_pos = None
        self.is_panning = False
        
        # Map image data
        self.map_pixmap = None
        self.region = None
        self.heights_cache = {}  # (cx, cz) -> Y of the top block of each of the 256 columns
        self.region_heights = [[62] * 512 for _ in range(512)]  # 512x512 heightmap for hillshading
        
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
        
        # UI Styling (Harmonious Premium Theme)
        self.grid_color = QColor(255, 255, 255, 20)
        self.bg_color = QColor(25, 25, 25)
        self.border_color = QColor(40, 40, 40)
        
        # Precompute base RGB values for all heights (-64 to 320) to speed up rendering
        self.height_color_cache = {}
        for y in range(-64, 325):
            c = self.get_color_for_height(y)
            self.height_color_cache[y] = (c.red(), c.green(), c.blue())
            
        # Animation & HUD state for pulsing player marker & floating tooltip
        self.pulse_radius = 5.0
        self.pulse_alpha = 150
        self.mouse_screen_pos = None
        
        self.pulse_timer = QTimer(self)
        self.pulse_timer.timeout.connect(self.update_pulse_animation)
        self.pulse_timer.start(50)
        
    def update_pulse_animation(self):
        self.pulse_radius += 0.5
        if self.pulse_radius > 20.0:
            self.pulse_radius = 5.0
        progress = (self.pulse_radius - 5.0) / 15.0
        self.pulse_alpha = int(150 * (1.0 - progress))
        if self.player_x is not None and self.player_z is not None:
            self.update()
        
    def set_region(self, region):
        self.region = region
        self.heights_cache.clear()
        self.region_heights = [[62] * 512 for _ in range(512)]
        self.zoom_level = 1.0
        self.pan_offset = QPointF(0, 0)
        self.render_map()
        self.update()
        
    def get_block_color(self, name):
        name = name.lower()
        if "air" in name:
            return QColor(0, 0, 0, 0)
        elif "water" in name:
            return QColor(41, 128, 185, 200) # Semi-transparent blue
        elif "lava" in name:
            return QColor(230, 126, 34)
        elif "grass_block" in name or "grass" in name:
            return QColor(46, 204, 113)
        elif "farmland" in name:
            return QColor(109, 76, 65)
        elif "dirt" in name:
            return QColor(141, 110, 99)
        elif "wheat" in name:
            return QColor(241, 196, 15)
        elif "planks" in name or "wood" in name or "log" in name or "fence" in name or "gate" in name or "door" in name or "slab" in name or "stairs" in name or "chest" in name or "composter" in name or "ladder" in name:
            return QColor(211, 166, 119)
        elif "quartz" in name or ("concrete" in name and "white" in name):
            return QColor(245, 246, 250)
        elif "gray_concrete" in name or "grey_concrete" in name:
            return QColor(127, 140, 141)
        elif "stone" in name or "brick" in name or "wall" in name or "cobblestone" in name or "hopper" in name or "iron" in name or "redstone" in name:
            return QColor(149, 165, 166)
        elif "bed" in name:
            return QColor(231, 76, 60)
        elif "glass" in name:
            return QColor(224, 247, 250, 150)
        elif "pot" in name or "poppy" in name or "flower" in name:
            return QColor(231, 76, 60)
        elif "glowstone" in name or "lantern" in name or "torch" in name:
            return QColor(241, 196, 15)
        else:
            if "oak" in name or "spruce" in name or "birch" in name or "jungle" in name or "acacia" in name or "dark_oak" in name:
                return QColor(211, 166, 119)
            elif "redstone" in name or "comparator" in name or "repeater" in name:
                return QColor(192, 57, 43)
            return QColor(189, 195, 199)

    def precompute_structure_preview(self):
        if not self.selected_structure:
            self.structure_preview_pixmap = None
            return
            
        w = self.selected_structure.width
        l = self.selected_structure.length
        h = self.selected_structure.height
        
        img = QImage(w, l, QImage.Format.Format_ARGB32)
        img.fill(Qt.GlobalColor.transparent)
        
        for z in range(l):
            for x in range(w):
                found_color = None
                for y in range(h - 1, -1, -1):
                    block = self.selected_structure.get_block(x, y, z)
                    name = block.get("Name", "minecraft:air")
                    if name != "minecraft:air":
                        found_color = self.get_block_color(name)
                        break
                if found_color:
                    img.setPixelColor(x, z, found_color)
                else:
                    img.setPixelColor(x, z, QColor(0, 0, 0, 0))
                    
        self.structure_preview_pixmap = QPixmap.fromImage(img)

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
        
    def get_chunk_heightmap(self, cx, cz):
        """Y of the topmost block of each column (index z*16+x) of a region-local chunk."""
        if (cx, cz) in self.heights_cache:
            return self.heights_cache[(cx, cz)]

        if not self.region:
            return None
        # Fast path: read only the heightmap bytes instead of parsing the whole chunk
        heights = self.region.quick_surface((cx, cz))
        if heights is not None:
            self.heights_cache[(cx, cz)] = heights
            return heights
        entry = self.region.chunks.get((cx, cz))
        if entry is None:
            return None
        chunk_nbt, _ = entry

        heights = read_world_surface(chunk_nbt)
        if heights is None:
            if chunk_nbt.get("sections") and "Level" not in chunk_nbt:
                heights, _ = surface_heights(chunk_nbt)
            else:
                heights = [62] * 256
        self.heights_cache[(cx, cz)] = heights
        return heights

    def render_map(self):
        if not self.region:
            self.map_pixmap = None
            return
            
        # First phase: Populate 2D heightmap array
        for cz in range(32):
            for cx in range(32):
                if (cx, cz) in self.region.chunks:
                    heights = self.get_chunk_heightmap(cx, cz)
                    if heights:
                        for z in range(16):
                            for x in range(16):
                                self.region_heights[cz * 16 + z][cx * 16 + x] = heights[z * 16 + x]
                                
        # Second phase: Draw with Hillshading
        img = QImage(512, 512, QImage.Format.Format_RGB32)
        
        # Pre-cache references for fast local access in loop
        region_heights = self.region_heights
        height_colors = self.height_color_cache
        chunks = self.region.chunks
        
        for cz in range(32):
            for cx in range(32):
                if (cx, cz) not in chunks:
                    # Draw un-generated chunks as dark hatching using fast setPixel integer
                    for z in range(16):
                        for x in range(16):
                            px = cx * 16 + x
                            pz = cz * 16 + z
                            color_val = 0xFF232328 if (px + pz) % 8 == 0 else 0xFF19191C
                            img.setPixel(px, pz, color_val)
                    continue
                    
                for z in range(16):
                    for x in range(16):
                        px = cx * 16 + x
                        pz = cz * 16 + z
                        y = region_heights[pz][px]
                        
                        # Calculate slopes for Northwest hillshading
                        dx = region_heights[pz][px + 1] - y if px < 511 else 0
                        dz = region_heights[pz + 1][px] - y if pz < 511 else 0
                        
                        # Hillshading factor (bright for slopes facing Northwest, dark for Southeast)
                        shading = max(-35, min(35, -dx * 7 - dz * 7))
                        
                        base_r, base_g, base_b = height_colors.get(y, (35, 120, 45))
                        r = max(0, min(255, base_r + shading))
                        g = max(0, min(255, base_g + shading))
                        b = max(0, min(255, base_b + shading))
                        
                        # Pack ARGB integer (alpha is 0xFF)
                        img.setPixel(px, pz, 0xFF000000 | (r << 16) | (g << 8) | b)
                        
        self.map_pixmap = QPixmap.fromImage(img)

    def get_color_for_height(self, y):
        # Deep Water
        if y < 60:
            return QColor(15, 37, 75)
        # Shallow Water
        elif y <= 62:
            return QColor(25, 59, 107)
        # Sandy Shore
        elif y <= 64:
            return QColor(228, 208, 155)
        # Lush Valley/Plains
        elif y <= 80:
            # Shift from dark green to lime green as height increases
            factor = (y - 65) / 15
            r = int(35 + (50 - 35) * factor)
            g = int(120 + (145 - 120) * factor)
            b = int(45 + (35 - 45) * factor)
            return QColor(r, g, b)
        # Forest Hills
        elif y <= 110:
            factor = (y - 81) / 29
            r = int(50 + (95 - 50) * factor)
            g = int(110 + (90 - 110) * factor)
            b = int(35 + (45 - 35) * factor)
            return QColor(r, g, b)
        # High Mountain Stone
        elif y <= 160:
            factor = (y - 111) / 49
            val = int(90 + (150 - 90) * factor)
            return QColor(val, val, val + 5)
        # Snow Peaks
        else:
            return QColor(240, 240, 245)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw background
        painter.fillRect(self.rect(), self.bg_color)
        
        # Apply transformation: Zoom and Pan
        transform = QTransform()
        transform.translate(self.width() / 2, self.height() / 2)
        transform.scale(self.zoom_level, self.zoom_level)
        transform.translate(-256 + self.pan_offset.x(), -256 + self.pan_offset.y())
        
        painter.setTransform(transform)
        
        # Draw region terrain map
        if self.map_pixmap:
            painter.drawPixmap(0, 0, self.map_pixmap)
            
            # Draw Region Grid outline (512x512)
            grid_pen = QPen(self.grid_color, 1)
            painter.setPen(grid_pen)
            painter.drawRect(0, 0, 512, 512)
            
            # Draw chunk borders (every 16 blocks)
            for i in range(16, 512, 16):
                painter.drawLine(i, 0, i, 512)
                painter.drawLine(0, i, 512, i)
        else:
            # Draw placeholder empty region
            font = QFont("Outfit", 12)
            painter.setFont(font)
            painter.setPen(QColor(100, 100, 100))
            painter.drawText(QRectF(0, 0, 512, 512), Qt.AlignmentFlag.AlignCenter, "Nessuna mappa caricata\nSeleziona una cartella salvataggi")
            
        # Draw Staged Placements
        if self.staged_placements and self.map_pixmap and self.region:
            for item in self.staged_placements:
                s = item["structure"]
                # Staged placements are stored in world coordinates (they may span regions)
                gx = item["world_x"] - self.region.rx * 512
                gz = item["world_z"] - self.region.rz * 512
                y_val = item["y_coord"]
                name = item["name"]
                pixmap = item["preview_pixmap"]
                sw = s.width
                sl = s.length
                
                rect = QRectF(gx, gz, sw, sl)
                
                # Draw the precomputed top-down blocks
                if pixmap:
                    old_opacity = painter.opacity()
                    painter.setOpacity(0.65)  # 65% opacity for staged structures
                    painter.drawPixmap(rect.toRect(), pixmap)
                    painter.setOpacity(old_opacity)
                    
                # Outer subtle border (semi-transparent blue/gray for staged)
                staged_border = QColor(149, 165, 166, 180)
                staged_fill = QColor(149, 165, 166, 15)
                
                painter.fillRect(rect, staged_fill)
                painter.setPen(QPen(staged_border, 1.0, Qt.PenStyle.DashLine))
                painter.drawRect(rect)
                
                # Draw a tiny text overlay with the structure name and coordinates
                font = QFont("Inter", 6)
                painter.setFont(font)
                painter.setPen(QColor(180, 180, 180))
                text_rect = QRectF(gx, gz + sl, max(80, sw), 12)
                painter.drawText(text_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop, f"{name} (Y:{y_val})")

        # Draw Structure Preview
        if self.selected_structure and self.map_pixmap:
            sw = self.selected_structure.width
            sl = self.selected_structure.length
            
            # Target rect on map
            rect = QRectF(self.preview_grid_x, self.preview_grid_z, sw, sl)
            
            # Draw precalculated top-down blocks
            if hasattr(self, 'structure_preview_pixmap') and self.structure_preview_pixmap:
                old_opacity = painter.opacity()
                painter.setOpacity(0.8)  # 80% opacity to see terrain underneath
                painter.drawPixmap(rect.toRect(), self.structure_preview_pixmap)
                painter.setOpacity(old_opacity)
                
            # Outer neon-green bounding box
            preview_border = QColor(46, 204, 113, 200)
            preview_fill = QColor(46, 204, 113, 30)  # Shrunk opacity of fill so structure blocks are clear
            
            painter.fillRect(rect, preview_fill)
            painter.setPen(QPen(preview_border, 1.5, Qt.PenStyle.SolidLine))
            painter.drawRect(rect)
            
            # Compass heading orientation indicator (draw an arrow or line for "facing north")
            painter.setPen(QPen(QColor(231, 76, 60, 200), 2))
            # North is top of the screen (Z axis decreases)
            painter.drawLine(QPointF(self.preview_grid_x + sw/2, self.preview_grid_z),
                             QPointF(self.preview_grid_x + sw/2, self.preview_grid_z - 3))
            
            # Draw size text over preview
            font = QFont("Inter", 7)
            painter.setFont(font)
            painter.setPen(QColor(255, 255, 255))
            text_rect = QRectF(self.preview_grid_x, self.preview_grid_z + sl, max(60, sw), 15)
            painter.drawText(text_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop, f"{sw}x{self.selected_structure.height}x{sl}")
            
        # Draw Player Marker (Red radar pulse pin)
        if self.player_x is not None and self.player_z is not None and self.region:
            local_x = self.player_x - self.region.rx * 512
            local_z = self.player_z - self.region.rz * 512
            if 0 <= local_x < 512 and 0 <= local_z < 512:
                # Pulsing outer ring (animated radar halo)
                painter.setBrush(QColor(231, 76, 60, self.pulse_alpha))
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawEllipse(QRectF(local_x - self.pulse_radius, local_z - self.pulse_radius, self.pulse_radius * 2, self.pulse_radius * 2))
                
                # Solid red center core with white outline
                painter.setBrush(QColor(231, 76, 60))
                painter.setPen(QPen(QColor(255, 255, 255), 1.5))
                painter.drawEllipse(QRectF(local_x - 3.5, local_z - 3.5, 7, 7))

        # Reset transform to widget coordinate space to draw fixed-size HUD elements (un-zoomed, un-panned)
        painter.setTransform(QTransform())
        
        # Draw floating glassmorphic tooltip HUD near mouse cursor
        if hasattr(self, 'mouse_screen_pos') and self.mouse_screen_pos and self.underMouse() and self.region:
            grid_x, grid_z = self.screen_to_grid(self.mouse_screen_pos)
            if 0 <= grid_x < 512 and 0 <= grid_z < 512:
                # Find height at cursor
                cx = grid_x // 16
                cz = grid_z // 16
                bx = grid_x % 16
                bz = grid_z % 16
                heights = self.get_chunk_heightmap(cx, cz)
                y_val = heights[bz * 16 + bx] if heights else 64
                
                # Biome classification by elevation
                biome = "Pianura"
                if y_val < 60:
                    biome = "Oceano Profondo"
                elif y_val <= 62:
                    biome = "Mare Calmo"
                elif y_val <= 64:
                    biome = "Spiaggia"
                elif y_val <= 80:
                    biome = "Pianura Erbosa"
                elif y_val <= 110:
                    biome = "Foresta Collinare"
                elif y_val <= 160:
                    biome = "Montagna Rocciosa"
                else:
                    biome = "Picco Innevato"
                    
                world_x = self.region.rx * 512 + grid_x
                world_z = self.region.rz * 512 + grid_z
                
                # Tooltip card dimensions
                tt_w = 175
                tt_h = 85
                mx = self.mouse_screen_pos.x() + 15
                my = self.mouse_screen_pos.y() + 15
                
                # Prevent clipping beyond the canvas bounds
                if mx + tt_w > self.width():
                    mx = self.mouse_screen_pos.x() - tt_w - 10
                if my + tt_h > self.height():
                    my = self.mouse_screen_pos.y() - tt_h - 10
                    
                rect = QRectF(mx, my, tt_w, tt_h)
                
                # Translucent dark HUD background
                painter.setBrush(QColor(16, 16, 20, 215))
                painter.setPen(QPen(QColor(46, 204, 113, 170), 1.5))
                painter.drawRoundedRect(rect, 8.0, 8.0)
                
                # Draw tooltip text contents
                font = QFont("Outfit", 9)
                font.setWeight(QFont.Weight.Medium)
                painter.setFont(font)
                painter.setPen(QColor(240, 240, 248))
                
                text_margin = 8
                painter.drawText(rect.adjusted(text_margin, text_margin, -text_margin, -text_margin),
                                 Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop,
                                 f"Coordinate: {world_x}, {world_z}\n"
                                 f"Altezza Y: {y_val}\n"
                                 f"Bioma: {biome}\n"
                                 f"Sezione: Chk ({cx}, {cz})")

    def screen_to_grid(self, screen_pos):
        # Invert the painter's transform to convert window coordinates to map grid coordinates
        transform = QTransform()
        transform.translate(self.width() / 2, self.height() / 2)
        transform.scale(self.zoom_level, self.zoom_level)
        transform.translate(-256 + self.pan_offset.x(), -256 + self.pan_offset.y())
        
        inv_transform, ok = transform.inverted()
        if not ok:
            return 0, 0
            
        map_pos = inv_transform.map(QPointF(screen_pos))
        grid_x = int(map_pos.x())
        grid_z = int(map_pos.y())
        return grid_x, grid_z

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.MiddleButton or (event.button() == Qt.MouseButton.LeftButton and event.modifiers() == Qt.KeyboardModifier.ControlModifier):
            self.is_panning = True
            self.last_mouse_pos = event.position()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
        elif event.button() == Qt.MouseButton.LeftButton:
            if self.selected_structure and self.map_pixmap:
                grid_x, grid_z = self.screen_to_grid(event.position())
                sw = self.selected_structure.width
                sl = self.selected_structure.length
                
                # Check if click is inside current preview box bounds to start dragging
                if (self.preview_grid_x <= grid_x < self.preview_grid_x + sw) and (self.preview_grid_z <= grid_z < self.preview_grid_z + sl):
                    self.is_dragging_structure = True
                    self.drag_offset_x = grid_x - self.preview_grid_x
                    self.drag_offset_z = grid_z - self.preview_grid_z
                    self.setCursor(Qt.CursorShape.SizeAllCursor)
                    self.is_locked = True
                else:
                    # Relocate preview box center to click, lock coordinates, and start dragging immediately
                    self.preview_grid_x = grid_x - sw // 2
                    self.preview_grid_z = grid_z - sl // 2
                    self.is_dragging_structure = True
                    self.drag_offset_x = sw // 2
                    self.drag_offset_z = sl // 2
                    self.setCursor(Qt.CursorShape.SizeAllCursor)
                    self.is_locked = True
                    self.structure_placed.emit(self.preview_grid_x, self.preview_grid_z)
                    self.update()
            else:
                self.is_panning = True
                self.last_mouse_pos = event.position()
                self.setCursor(Qt.CursorShape.ClosedHandCursor)
        elif event.button() == Qt.MouseButton.RightButton:
            # Right-click unlocks placement to follow mouse
            self.is_locked = False
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.MiddleButton or event.button() == Qt.MouseButton.LeftButton:
            if self.is_dragging_structure:
                self.is_dragging_structure = False
                self.structure_placed.emit(self.preview_grid_x, self.preview_grid_z)
            self.is_panning = False
            self.setCursor(Qt.CursorShape.ArrowCursor)
            self.update()

    def mouseMoveEvent(self, event):
        self.mouse_screen_pos = event.position()
        grid_x, grid_z = self.screen_to_grid(event.position())
        
        # Panning operation
        if self.is_panning and self.last_mouse_pos:
            delta = event.position() - self.last_mouse_pos
            self.pan_offset += delta / self.zoom_level
            self.last_mouse_pos = event.position()
            self.update()
            return
            
        # Dragging structure preview box
        if self.is_dragging_structure and self.selected_structure:
            self.preview_grid_x = grid_x - self.drag_offset_x
            self.preview_grid_z = grid_z - self.drag_offset_z
            self.structure_placed.emit(self.preview_grid_x, self.preview_grid_z)
            self.update()
            self.trigger_hover_event(grid_x, grid_z)
            return
            
        # Update hover preview location (snapped to block grid) if NOT dragging and NOT locked
        if self.selected_structure and not self.is_dragging_structure and not self.is_locked:
            # Place center of structure at mouse pointer
            sw = self.selected_structure.width
            sl = self.selected_structure.length
            self.preview_grid_x = grid_x - sw // 2
            self.preview_grid_z = grid_z - sl // 2
            
        self.trigger_hover_event(grid_x, grid_z)
        self.update()

    def trigger_hover_event(self, grid_x, grid_z):
        if self.region:
            if 0 <= grid_x < 512 and 0 <= grid_z < 512:
                cx = grid_x // 16
                cz = grid_z // 16
                bx = grid_x % 16
                bz = grid_z % 16
                
                heights = self.get_chunk_heightmap(cx, cz)
                y_val = heights[bz * 16 + bx] if heights else 64
                self.preview_y = y_val
                world_x = self.region.rx * 512 + grid_x
                world_z = self.region.rz * 512 + grid_z
                self.hover_changed.emit(world_x, world_z, y_val)

    def wheelEvent(self, event):
        old_zoom = self.zoom_level
        zoom_step = 1.15
        
        # Calculate new zoom level
        if event.angleDelta().y() > 0:
            self.zoom_level *= zoom_step
        else:
            self.zoom_level /= zoom_step
            
        # Cap zoom levels
        self.zoom_level = max(0.4, min(self.zoom_level, 25.0))
        
        # Adjust pan offset to zoom on mouse position
        new_zoom = self.zoom_level
        if old_zoom != new_zoom:
            mouse_pos = event.position()
            center = QPointF(self.width() / 2, self.height() / 2)
            self.pan_offset += (mouse_pos - center) * (1.0 / new_zoom - 1.0 / old_zoom)
            
        self.update()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_R and self.selected_structure:
            # The main window owns the selected structure: rotating only the preview
            # here would inject a structure different from the one displayed.
            self.rotate_requested.emit()
            
    def center_on_map(self):
        self.zoom_level = 1.0
        self.pan_offset = QPointF(0, 0)
        self.update()
