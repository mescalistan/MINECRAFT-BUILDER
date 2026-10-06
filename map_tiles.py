"""
Map tiles: one 512x512 image per region file.

Two detail levels:
- fast: terrain height only (heightmap bytes read straight from the chunk);
- detailed: colour of the surface block (grass, sand, wood, stone, roofs...) with hillshading,
  water depth, and the game's structures (villages, temples...) read from the chunks.

Detailed tiles are saved to a disk cache keyed by the region file's size and modification
time, so areas already seen show up immediately, even after reopening the program.
Pure Python (no Qt): the tile is returned as BGRA bytes that QImage can wrap directly.
"""
import array
import hashlib
import json
import os
import re
import sys
import zlib

from mca_codec import (MCARegion, normalize_state, read_world_surface, surface_heights, chunk_min_y,
                       chunk_is_full, _palette_bits)

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "tools"))
import blockinfo  # noqa: E402

TILE = 512
NO_DATA = -32768          # height of columns in chunks that have not been generated
CACHE_VERSION = 3
_REGION_RE = re.compile(r"^r\.(-?\d+)\.(-?\d+)\.mca$")

# Blocks seen "through" when colouring the map (the ground below them is coloured instead)
_SEE_THROUGH = ("short_grass", "tall_grass", "fern", "large_fern", "dead_bush", "torch", "lantern",
                "flower", "tulip", "poppy", "dandelion", "orchid", "allium", "bluet", "daisy", "cornflower",
                "lily_of_the_valley", "rose_bush", "lilac", "peony", "sunflower", "sapling", "mushroom",
                "rail", "button", "pressure_plate", "carpet", "sign", "banner", "seagrass", "kelp",
                "pink_petals", "wildflowers", "leaf_litter", "bush", "firefly_bush", "short_dry_grass",
                "tall_dry_grass", "redstone_wire", "string", "tripwire", "candle",
                "lever", "ladder", "end_rod", "lightning_rod", "chain", "cobweb")
_WATERY = ("water", "bubble_column", "seagrass", "kelp")


def region_coords(filename):
    m = _REGION_RE.match(os.path.basename(filename))
    return (int(m.group(1)), int(m.group(2))) if m else None


def list_regions(region_dir):
    """{(rx, rz): path} of the region files in a folder."""
    out = {}
    try:
        names = os.listdir(region_dir)
    except OSError:
        return out
    for n in names:
        rc = region_coords(n)
        if rc:
            path = os.path.join(region_dir, n)
            if os.path.getsize(path) >= 8192:
                out[rc] = path
    return out


# ---------------------------------------------------------------------------
# Colours
# ---------------------------------------------------------------------------

def _height_rgb(y):
    if y < 60:
        return (15, 37, 75)
    if y <= 62:
        return (25, 59, 107)
    if y <= 64:
        return (228, 208, 155)
    if y <= 80:
        f = (y - 65) / 15
        return (int(35 + 15 * f), int(120 + 25 * f), int(45 - 10 * f))
    if y <= 110:
        f = (y - 81) / 29
        return (int(50 + 45 * f), int(110 - 20 * f), int(35 + 10 * f))
    if y <= 160:
        v = int(90 + 60 * (y - 111) / 49)
        return (v, v, v + 5)
    return (240, 240, 245)


HEIGHT_RGB = {y: _height_rgb(y) for y in range(-64, 330)}

_color_cache = {}


def surface_rgb(name):
    """Map colour of a block id (with or without the minecraft: prefix)."""
    c = _color_cache.get(name)
    if c is None:
        short = name.split(":", 1)[-1]
        if short in ("grass_block", "moss_block", "moss_carpet"):
            c = (98, 152, 58)
        elif short.endswith("_leaves"):
            c = (230, 160, 190) if short.startswith("cherry") else (52, 104, 36) if "spruce" in short \
                else (76, 128, 44) if "birch" in short else (58, 112, 34)
        elif short in ("snow", "snow_block", "powder_snow"):
            c = (246, 250, 252)
        else:
            c = blockinfo.block_color(short)[:3]
        _color_cache[name] = c
    return c


AIR_SHORT = ("air", "cave_air", "void_air")
SOLID, SEE_THROUGH, WATER = 0, 1, 2
_kind_cache = {}


def block_kind(name):
    """SOLID, SEE_THROUGH (coloured from the block below) or WATER, cached per block id."""
    k = _kind_cache.get(name)
    if k is None:
        short = name.split(":", 1)[-1]
        if any(w in short for w in _WATERY):
            k = WATER
        elif short in AIR_SHORT or any(t in short for t in _SEE_THROUGH):
            k = SEE_THROUGH
        else:
            k = SOLID
        _kind_cache[name] = k
    return k


def is_see_through(name):
    return block_kind(name) == SEE_THROUGH


# ---------------------------------------------------------------------------
# Surface reading
# ---------------------------------------------------------------------------

class _ChunkBlocks:
    """Random access to single blocks of a chunk without unpacking whole sections."""

    def __init__(self, chunk):
        self.sections = {}
        for s in chunk.get("sections", []):
            bs = s.get("block_states")
            if not bs or not bs.get("palette"):
                continue
            palette = [str(normalize_state(e).get("Name", "minecraft:air")) for e in bs["palette"]]
            data = bs.get("data")
            if not data or len(palette) == 1:
                self.sections[int(s.get("Y", 0))] = (palette, None, 0, 0, 0)
            else:
                bits = _palette_bits(len(palette))
                self.sections[int(s.get("Y", 0))] = (palette, data, bits, 64 // bits, (1 << bits) - 1)

    def name(self, x, y, z):
        sec = self.sections.get(y >> 4)
        if sec is None:
            return "minecraft:air"
        palette, data, bits, per_long, mask = sec
        if data is None:
            return palette[0]
        i = ((y & 15) << 8) | (z << 4) | x
        q, r = divmod(i, per_long)
        if q >= len(data):
            return palette[0]
        idx = ((data[q] & 0xFFFFFFFFFFFFFFFF) >> (r * bits)) & mask
        return palette[idx] if idx < len(palette) else palette[0]


def chunk_surface(chunk, heights):
    """
    (rgb list, depth list) for the 256 columns: colour of the visible surface block and,
    for water, how deep it is (0 on land). heights = top block Y of each column.
    """
    blocks = _ChunkBlocks(chunk)
    min_y = chunk_min_y(chunk)
    colors = [None] * 256
    depth = [0] * 256
    kind = block_kind
    name_at = blocks.name
    for col in range(256):
        x, z = col & 15, col >> 4
        y = heights[col]
        name = name_at(x, y, z)
        k = kind(name)
        steps = 0
        while k == SEE_THROUGH and y > min_y and steps < 48:
            y -= 1
            steps += 1
            name = name_at(x, y, z)
            k = kind(name)
        if k == WATER:
            d = 1
            while d < 24 and y - d > min_y:
                name = name_at(x, y - d, z)
                if kind(name) != WATER:
                    break
                d += 1
            depth[col] = d
        colors[col] = surface_rgb(name)
    return colors, depth


def chunk_structures(chunk, rx, rz):
    """Structure starts stored in a chunk: [(id, x1, z1, x2, z2)] in world coordinates."""
    root = chunk["Level"] if "Level" in chunk else chunk
    st = root.get("structures") or root.get("Structures") or {}
    starts = st.get("starts") or st.get("Starts") or {}
    out = []
    for key, start in starts.items():
        sid = str(start.get("id", key))
        if sid == "INVALID":
            continue
        boxes = [c.get("BB") for c in start.get("Children", []) if c.get("BB") is not None]
        boxes = [list(b) for b in boxes if len(b) == 6]
        if not boxes:
            continue
        x1 = min(b[0] for b in boxes)
        z1 = min(b[2] for b in boxes)
        x2 = max(b[3] for b in boxes)
        z2 = max(b[5] for b in boxes)
        out.append((sid, int(x1), int(z1), int(x2), int(z2)))
    return out


def _column_heights(region, key, chunk=None):
    h = None if chunk is not None else region.quick_surface(key)
    if h == []:
        return None, None            # chunk not fully generated
    if h is not None:
        return h, None
    if chunk is None:
        try:
            chunk, _ = region.chunks[key]
        except KeyError:
            return None, None
    h = read_world_surface(chunk)
    if h is None and chunk.get("sections") and "Level" not in chunk:
        h, _ = surface_heights(chunk)
    return h, chunk


def build_tile(path, detailed=True, cancelled=lambda: False):
    """
    Renders a region file. Returns a dict:
        heights    array('h') of TILE*TILE top-block Y values (NO_DATA = not generated)
        rgb        bytearray TILE*TILE*3 with the base colour (before shading)
        depth      bytearray TILE*TILE with the water depth (0 = land)
        structures [(id, x1, z1, x2, z2)] structure starts found in the region
        detailed   whether block colours were read (False = height colours only)
    or None if cancelled.
    """
    region = MCARegion(path)
    n = TILE * TILE
    heights = array.array("h", [NO_DATA]) * n
    rgb = bytearray(n * 3)
    depth = bytearray(n)
    structures = []
    done = 0
    for key in list(region.chunks):
        if cancelled():
            return None
        cx, cz = key
        chunk = None
        if detailed:
            try:
                chunk, _ = region.chunks[key]
            except KeyError:
                continue
        if chunk is not None and "Level" not in chunk and not chunk_is_full(chunk):
            continue  # still being generated by the game: shown as not generated
        h, chunk = _column_heights(region, key, chunk)
        if h is None:
            continue
        colors = dep = None
        if detailed and chunk is not None and "Level" not in chunk:
            try:
                colors, dep = chunk_surface(chunk, h)
            except Exception:
                colors = None
            structures.extend(chunk_structures(chunk, region.rx, region.rz))
        for z in range(16):
            row = (cz * 16 + z) * TILE + cx * 16
            for x in range(16):
                col = z * 16 + x
                y = h[col]
                i = row + x
                heights[i] = max(-2048, min(4095, y))
                c = colors[col] if colors else HEIGHT_RGB.get(y, (35, 120, 45))
                rgb[i * 3:i * 3 + 3] = bytes(c)
                if dep:
                    depth[i] = min(255, dep[col])
        done += 1
        if done % 64 == 0:
            region.chunks.clear_cache()
    region.chunks.clear_cache()
    return {"heights": heights, "rgb": rgb, "depth": depth, "structures": structures, "detailed": detailed,
            "complete": not region._bad}


def shade(tile):
    """BGRA bytes of the final image: base colours + hillshading + water depth."""
    heights, rgb, depth = tile["heights"], tile["rgb"], tile["depth"]
    out = bytearray(TILE * TILE * 4)
    for pz in range(TILE):
        base = pz * TILE
        for px in range(TILE):
            i = base + px
            y = heights[i]
            o = i * 4
            if y == NO_DATA:
                v = 0x23 if (px + pz) % 8 == 0 else 0x19
                out[o:o + 4] = bytes((v + 3, v, v, 255))
                continue
            r, g, b = rgb[i * 3], rgb[i * 3 + 1], rgb[i * 3 + 2]
            d = depth[i]
            if d:
                # water: the bottom shows through in the shallows, darker blue the deeper it is
                k = 0.62 + d * 0.06 if d < 6 else 0.95
                dark = 1.0 - (d * 0.025 if d < 18 else 0.45)
                r = int((r * (1 - k) + 40 * k) * dark)
                g = int((g * (1 - k) + 96 * k) * dark)
                b = int((b * (1 - k) + 206 * k) * dark)
            else:
                yw = heights[i - 1] if px > 0 else y
                yn = heights[i - TILE] if pz > 0 else y
                if yw == NO_DATA:
                    yw = y
                if yn == NO_DATA:
                    yn = y
                s = (y - yw) * 9 + (y - yn) * 9
                s = 40 if s > 40 else -40 if s < -40 else s
                r = r + s
                g = g + s
                b = b + s
                r = 0 if r < 0 else 255 if r > 255 else r
                g = 0 if g < 0 else 255 if g > 255 else g
                b = 0 if b < 0 else 255 if b > 255 else b
            out[o] = b
            out[o + 1] = g
            out[o + 2] = r
            out[o + 3] = 255
    return bytes(out)


# ---------------------------------------------------------------------------
# Disk cache
# ---------------------------------------------------------------------------

def default_cache_root():
    if os.environ.get("MINECRAFT_BUILDER_MAP_CACHE"):
        return os.environ["MINECRAFT_BUILDER_MAP_CACHE"]
    base = os.environ.get("LOCALAPPDATA") or os.path.join(os.path.expanduser("~"), ".cache")
    return os.path.join(base, "MinecraftBuilder", "map_cache")


class TileCache:
    """Detailed tiles on disk: <root>/<hash of the region folder>/r.X.Z.tile (zlib)."""

    def __init__(self, region_dir, root=None):
        key = hashlib.sha1(os.path.abspath(region_dir).lower().encode("utf-8")).hexdigest()[:16]
        self.dir = os.path.join(root or default_cache_root(), key)

    @staticmethod
    def _stamp(path):
        st = os.stat(path)
        return [st.st_size, st.st_mtime_ns]

    def _file(self, rx, rz):
        return os.path.join(self.dir, f"r.{rx}.{rz}.tile")

    def load(self, rx, rz, path):
        """Cached tile if still valid for the region file, else None."""
        try:
            with open(self._file(rx, rz), "rb") as f:
                raw = zlib.decompress(f.read())
            head_len = int.from_bytes(raw[:4], "big")
            head = json.loads(raw[4:4 + head_len].decode("utf-8"))
            if head.get("v") != CACHE_VERSION or head.get("stamp") != self._stamp(path):
                return None
            body = raw[4 + head_len:]
            n = TILE * TILE
            heights = array.array("h")
            heights.frombytes(body[:n * 2])
            if sys.byteorder != "little":
                heights.byteswap()
            rgb = bytearray(body[n * 2:n * 5])
            depth = bytearray(body[n * 5:n * 6])
            if len(heights) != n or len(rgb) != n * 3 or len(depth) != n:
                return None
            structures = [tuple(s) for s in head.get("structures", [])]
            return {"heights": heights, "rgb": rgb, "depth": depth, "structures": structures,
                    "detailed": head.get("detailed", True)}
        except (OSError, ValueError, zlib.error, KeyError):
            return None

    def save(self, rx, rz, path, tile, stamp=None):
        try:
            os.makedirs(self.dir, exist_ok=True)
            head = json.dumps({"v": CACHE_VERSION, "stamp": stamp or self._stamp(path), "detailed": tile["detailed"],
                               "structures": tile["structures"]}).encode("utf-8")
            heights = array.array("h", tile["heights"])
            if sys.byteorder != "little":
                heights.byteswap()
            raw = len(head).to_bytes(4, "big") + head + heights.tobytes() + bytes(tile["rgb"]) + bytes(tile["depth"])
            tmp = self._file(rx, rz) + ".tmp"
            with open(tmp, "wb") as f:
                f.write(zlib.compress(raw, 6))
            os.replace(tmp, self._file(rx, rz))
        except OSError:
            pass


def structure_label(sid):
    """Readable Italian name of a vanilla structure id."""
    short = sid.split(":", 1)[-1]
    names = {
        "village_plains": "Villaggio (pianura)", "village_desert": "Villaggio (deserto)",
        "village_savanna": "Villaggio (savana)", "village_snowy": "Villaggio (neve)",
        "village_taiga": "Villaggio (taiga)", "desert_pyramid": "Tempio del deserto",
        "jungle_pyramid": "Tempio della giungla", "swamp_hut": "Capanna della strega", "igloo": "Igloo",
        "pillager_outpost": "Avamposto dei predoni", "mansion": "Villa nel bosco", "monument": "Monumento oceanico",
        "stronghold": "Fortezza (End)", "mineshaft": "Miniera abbandonata", "mineshaft_mesa": "Miniera (mesa)",
        "shipwreck": "Relitto", "shipwreck_beached": "Relitto (spiaggia)", "buried_treasure": "Tesoro sepolto",
        "ocean_ruin_cold": "Rovine oceaniche", "ocean_ruin_warm": "Rovine oceaniche",
        "ruined_portal": "Portale in rovina", "ruined_portal_desert": "Portale in rovina",
        "ruined_portal_jungle": "Portale in rovina", "ruined_portal_swamp": "Portale in rovina",
        "ruined_portal_mountain": "Portale in rovina", "ruined_portal_ocean": "Portale in rovina",
        "ancient_city": "Citta' antica", "trail_ruins": "Rovine dei sentieri", "trial_chambers": "Camere della prova",
        "fortress": "Fortezza del Nether", "bastion_remnant": "Bastione", "end_city": "Citta' dell'End",
        "nether_fossil": "Fossile",
    }
    return names.get(short, short.replace("_", " ").capitalize())


def render_job(path, rx, rz, region_dir, detailed, cache_root=None):
    """
    Worker entry point (runs in a separate process): renders a region and, for detailed tiles,
    stores it in the disk cache. Returns the payload for the map, or None if the region is empty.
    """
    cache = TileCache(region_dir, root=cache_root)
    tile = cache.load(rx, rz, path) if detailed else None
    if tile is None:
        try:
            stamp = TileCache._stamp(path)       # taken before reading: a write meanwhile invalidates it
        except OSError:
            stamp = None
        tile = build_tile(path, detailed=detailed)
        if tile is None:
            return None
        if detailed and stamp and tile.get("complete", True):
            cache.save(rx, rz, path, tile, stamp)
    return {"image": shade(tile), "heights": tile["heights"], "structures": tile["structures"],
            "detailed": tile["detailed"]}
