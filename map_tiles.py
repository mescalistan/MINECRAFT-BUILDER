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
import struct
import sys
import zlib

from mca_codec import (MCARegion, normalize_state, read_world_surface, surface_heights, chunk_min_y,
                       chunk_is_full, _palette_bits)
from nbt_codec import _read_string, _read_payload, skip_payload

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "tools"))
import blockinfo  # noqa: E402

TILE = 512
NO_DATA = -32768          # height of columns in chunks that have not been generated
CACHE_VERSION = 4
_REGION_RE = re.compile(r"^r\.(-?\d+)\.(-?\d+)\.mca$")

# Blocks seen "through" when colouring the map (the ground below them is coloured instead)
_SEE_THROUGH = ("short_grass", "tall_grass", "fern", "large_fern", "dead_bush", "torch", "lantern",
                "flower", "tulip", "poppy", "dandelion", "orchid", "allium", "bluet", "daisy", "cornflower",
                "lily_of_the_valley", "rose_bush", "lilac", "peony", "sunflower", "sapling", "mushroom",
                "rail", "button", "pressure_plate", "carpet", "sign", "banner", "seagrass", "kelp",
                "pink_petals", "wildflowers", "leaf_litter", "bush", "firefly_bush", "short_dry_grass",
                "tall_dry_grass", "redstone_wire", "string", "tripwire", "candle",
                "lever", "ladder", "end_rod", "lightning_rod", "chain", "cobweb")
_WATERY = ("water", "bubble_column", "seagrass", "kelp", "sea_pickle")


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
        if any(w in short for w in _WATERY) or ("coral" in short and not short.startswith("dead_")
                                                 and not short.endswith("_block")):
            k = WATER           # live corals only grow under water: the map shows the sea bed below
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


TILE_SKIP_TAGS = frozenset(("block_ticks", "fluid_ticks", "PostProcessing", "block_entities", "blending_data",
                            "Lights", "CarvingMasks", "entities", "UpgradeData", "Entities", "TileEntities",
                            "TileTicks", "LiquidTicks"))


# ---------------------------------------------------------------------------
# Light chunk reading: only the tags the map draws are decoded, everything else is skipped
# ---------------------------------------------------------------------------

_SEC_Y = struct.Struct(">b")
_INT = struct.Struct(">i")


def _skip_compound(buf, pos):
    """Position after a compound payload; primitive tags are skipped inline (no call per tag)."""
    while True:
        t = buf[pos]
        if t == 0:
            return pos + 1
        pos += 3 + ((buf[pos + 1] << 8) | buf[pos + 2])
        if t == 3 or t == 5:
            pos += 4
        elif t == 8:
            pos += 2 + ((buf[pos] << 8) | buf[pos + 1])
        elif t == 1:
            pos += 1
        elif t == 4 or t == 6:
            pos += 8
        elif t == 2:
            pos += 2
        else:
            pos = _skip(buf, pos, t)


def _skip(buf, pos, t):
    """Like nbt_codec.skip_payload, faster on the big lists of compounds (block_ticks...)."""
    if t == 10:
        return _skip_compound(buf, pos)
    if t == 9 and buf[pos] == 10:
        n = _INT.unpack_from(buf, pos + 1)[0]
        pos += 5
        for _ in range(max(0, n)):
            pos = _skip_compound(buf, pos)
        return pos
    return skip_payload(buf, pos, t)


def _long_array(buf, pos):
    n = _INT.unpack_from(buf, pos)[0]
    a = array.array("Q")
    a.frombytes(buf[pos + 4:pos + 4 + 8 * n])
    if sys.byteorder == "little":
        a.byteswap()
    return a, pos + 4 + 8 * n


def _palette_names(buf, pos):
    """Block ids of a block_states palette (any encoding: {Name}, {id}, {"": id}, plain strings)."""
    it, n = buf[pos], _INT.unpack_from(buf, pos + 1)[0]
    if it not in (8, 10):
        return [], _skip(buf, pos, 9)
    pos += 5
    names = []
    for _ in range(max(0, n)):
        if it == 8:
            s, pos = _read_string(buf, pos)
            names.append(str(s))
            continue
        name = "minecraft:air"
        while True:
            t = buf[pos]
            if t == 0:
                pos += 1
                break
            key, pos = _read_string(buf, pos + 1)
            if t == 8 and key in ("Name", "id", ""):
                s, pos = _read_string(buf, pos)
                name = str(s)
            else:
                pos = _skip(buf, pos, t)
        names.append(name)
    return names, pos


def _light_section(buf, pos):
    y = names = data = None
    while True:
        t = buf[pos]
        if t == 0:
            return (y, names, data), pos + 1
        key, pos = _read_string(buf, pos + 1)
        if key == "Y" and t == 1:
            y = _SEC_Y.unpack_from(buf, pos)[0]
            pos += 1
        elif key == "block_states" and t == 10:
            while True:
                tt = buf[pos]
                if tt == 0:
                    pos += 1
                    break
                k2, pos = _read_string(buf, pos + 1)
                if k2 == "palette" and tt == 9:
                    names, pos = _palette_names(buf, pos)
                elif k2 == "data" and tt == 12:
                    data, pos = _long_array(buf, pos)
                else:
                    pos = _skip(buf, pos, tt)
        else:
            pos = _skip(buf, pos, t)


def read_light_chunk(data):
    """
    What the map needs of a chunk (1.18+ layout): status, yPos, heightmaps, block palettes and
    indices of the sections, structure starts. None for chunks in the old "Level" layout.
    """
    if not data or data[0] != 10:
        return None
    _, pos = _read_string(data, 1)
    out = {"sections": [], "heightmaps": {}, "status": None, "ypos": None, "structures": None}
    wanted = {"sections", "Heightmaps", "structures", "Status", "yPos"}
    while True:
        t = data[pos]
        if t == 0 or not wanted:
            return out          # the game writes block_ticks & co. after these: no need to walk them
        key, pos = _read_string(data, pos + 1)
        wanted.discard(key)
        if key == "sections" and t == 9:
            it, n = data[pos], _INT.unpack_from(data, pos + 1)[0]
            if it != 10:
                pos = _skip(data, pos, 9)
                continue
            pos += 5
            for _ in range(max(0, n)):
                sec, pos = _light_section(data, pos)
                out["sections"].append(sec)
        elif key == "Heightmaps" and t == 10:
            while True:
                tt = data[pos]
                if tt == 0:
                    pos += 1
                    break
                k2, pos = _read_string(data, pos + 1)
                if tt == 12:
                    out["heightmaps"][str(k2)], pos = _long_array(data, pos)
                else:
                    pos = _skip(data, pos, tt)
        elif key == "structures" and t == 10:
            out["structures"], pos = _read_payload(data, pos, t)
        elif key == "Status" and t == 8:
            s, pos = _read_string(data, pos)
            out["status"] = str(s)
            if out["status"] not in ("full", "minecraft:full"):
                return out      # still being generated: not drawn anyway
        elif key == "yPos" and t == 3:
            out["ypos"] = _INT.unpack_from(data, pos)[0]
            pos += 4
        elif key == "Level":
            return None
        else:
            pos = _skip(data, pos, t)


def _heightmap(longs, min_y):
    """Top-block Y of the 256 columns from a packed heightmap (9 bits, 7 per long), or None."""
    if longs is None or len(longs) != 37:
        return None
    out = []
    append = out.append
    base = min_y - 1
    for v in longs:
        for _ in range(7):
            append((v & 511) + base)
            v >>= 9
    del out[256:]
    return out


_RGB_BYTES = {}


def _rgb_bytes(name):
    b = _RGB_BYTES.get(name)
    if b is None:
        b = _RGB_BYTES[name] = bytes(surface_rgb(name))
    return b


def _section_record(names, data):
    """[kinds, colours (filled on demand), names, data, bits, per long, mask] of a section."""
    kinds = [block_kind(nm) for nm in names]
    if data is None or len(names) == 1 or not len(data):
        return [kinds, [None] * len(names), names, None, 0, 1, 0]
    bits = _palette_bits(len(names))
    return [kinds, [None] * len(names), names, data, bits, 64 // bits, (1 << bits) - 1]


def light_surface(light, heights, min_y):
    """
    (colour bytes list, depth list) of the 256 columns of a light chunk: like chunk_surface, but
    the block palettes are decoded only for the sections actually looked at, and the depth of the
    water comes from the OCEAN_FLOOR heightmap when the game has written it (checked, not trusted).
    """
    raw = {y: (names, data) for y, names, data in light["sections"] if y is not None and names}
    secs = {}

    def look(y, col):
        """(kind, palette index, section record) of the block at height y of a column."""
        sy = y >> 4
        rec = secs.get(sy)
        if rec is None:
            r = raw.get(sy)
            rec = secs[sy] = _section_record(*r) if r else _section_record(["minecraft:air"], None)
        data = rec[3]
        if data is None:
            return rec[0][0], 0, rec
        q, r = divmod(((y & 15) << 8) | col, rec[5])
        i = (data[q] >> (r * rec[4])) & rec[6] if q < len(data) else 0
        kinds = rec[0]
        if i >= len(kinds):
            i = 0
        return kinds[i], i, rec

    floor = _heightmap(light["heightmaps"].get("OCEAN_FLOOR"), min_y)
    colors = [None] * 256
    depth = [0] * 256
    for col in range(256):
        y = heights[col]
        k, i, rec = look(y, col)
        steps = 0
        while k == SEE_THROUGH and y > min_y and steps < 48:
            y -= 1
            steps += 1
            k, i, rec = look(y, col)
        if k == WATER:
            d = None
            if floor is not None:
                # bottom of the water from the heightmap, verified on the two blocks around it
                dd = min(24, y - floor[col])
                if 1 <= dd < 24 and y - dd > min_y:
                    kb, ib, rb = look(y - dd, col)
                    if kb != WATER and (dd == 1 or look(y - dd + 1, col)[0] == WATER):
                        d, i, rec = dd, ib, rb
                elif dd >= 24 and y - 23 > min_y:
                    kb, ib, rb = look(y - 23, col)
                    if kb == WATER:
                        d, i, rec = 24, ib, rb
            if d is None:
                d = 1
                while d < 24 and y - d > min_y:
                    kb, i, rec = look(y - d, col)
                    if kb != WATER:
                        break
                    d += 1
            depth[col] = d
        c = rec[1][i]
        if c is None:
            c = rec[1][i] = _rgb_bytes(rec[2][i])
        colors[col] = c
    return colors, depth


def _old_chunk_surface(region, key, h):
    """Chunks the light reader does not handle (old layout, no heightmap): full parse."""
    chunk, _ = region.chunks[key]
    region.chunks.clear_cache()
    if "Level" not in chunk and not chunk_is_full(chunk):
        return None, None, None, []
    if h is None:
        h, chunk = _column_heights(region, key, chunk)
        if h is None:
            return None, None, None, []
    if "Level" in chunk:
        return h, None, None, []
    try:
        colors, dep = chunk_surface(chunk, h)
        colors = [bytes(c) for c in colors]
    except Exception:
        colors = dep = None
    return h, colors, dep, chunk_structures(chunk, region.rx, region.rz)


def _render_chunk(region, key, detailed):
    """(heights, colour bytes or None, depth or None, structures) of a chunk, heights None = not drawn."""
    if not detailed:
        h, _ = _column_heights(region, key)
        return h, None, None, []
    try:
        data = region.chunk_bytes(key)
        light = read_light_chunk(data)
    except Exception as e:
        region._bad.add(key)
        print(f"Error reading chunk {key} in {region.file_path}: {e}")
        return None, None, None, []
    if light is None:
        return _old_chunk_surface(region, key, None)
    if light["status"] is not None and light["status"] not in ("full", "minecraft:full"):
        return None, None, None, []       # still being generated by the game: shown as not generated
    ys = [y for y, names, _ in light["sections"] if y is not None and names]
    min_y = min(ys) * 16 if ys else -64
    h = _heightmap(light["heightmaps"].get("WORLD_SURFACE"), min_y)
    if h is None:
        return _old_chunk_surface(region, key, None)
    try:
        colors, dep = light_surface(light, h, min_y)
    except Exception:
        colors = dep = None
    st = light["structures"]
    structures = chunk_structures({"structures": st}, region.rx, region.rz) if st else []
    return h, colors, dep, structures


def build_tile(path, detailed=True, cancelled=lambda: False, base=None):
    """
    Renders a region file. Returns a dict:
        heights    array('h') of TILE*TILE top-block Y values (NO_DATA = not generated)
        rgb        bytearray TILE*TILE*3 with the base colour (before shading)
        depth      bytearray TILE*TILE with the water depth (0 = land)
        structures [(id, x1, z1, x2, z2)] structure starts found in the region
        detailed   whether block colours were read (False = height colours only)
        chunk_sig  per chunk, its place and timestamp in the region header (0 = absent)
        chunk_structures {chunk index: [structures]}
    or None if cancelled.
    base: an older detailed tile of the same region; only the chunks whose header entry changed
    since then are read again (the game rewrites just the chunks it saved).
    """
    region = MCARegion(path)
    region.skip_tags = TILE_SKIP_TAGS            # read only: ticks, block entities... are never drawn
    n = TILE * TILE
    if base is not None and detailed and base.get("detailed") and base.get("chunk_sig"):
        heights = array.array("h", base["heights"])
        rgb = bytearray(base["rgb"])
        depth = bytearray(base["depth"])
        old_sig = base["chunk_sig"]
        chunk_structs = {int(k): list(v) for k, v in (base.get("chunk_structures") or {}).items()}
    else:
        heights = array.array("h", [NO_DATA]) * n
        rgb = bytearray(n * 3)
        depth = bytearray(n)
        old_sig = None
        chunk_structs = {}
    sig = _chunk_signatures(region)
    no_row = array.array("h", [NO_DATA]) * 16
    zero48, zero16 = bytes(48), bytes(16)
    for idx in range(1024):
        if cancelled():
            return None
        key = (idx % 32, idx // 32)
        present = key in region._raw
        if old_sig is not None and old_sig[idx] == sig[idx]:
            continue                             # unchanged since the base tile
        cx, cz = key
        if old_sig is not None:                  # changed or removed: clear it first
            chunk_structs.pop(idx, None)
            for z in range(16):
                row = (cz * 16 + z) * TILE + cx * 16
                heights[row:row + 16] = no_row
                rgb[row * 3:row * 3 + 48] = zero48
                depth[row:row + 16] = zero16
        if not present:
            continue
        try:
            h, colors, dep, structs = _render_chunk(region, key, detailed)
        except KeyError:
            continue
        if h is None:
            continue
        if structs:
            chunk_structs[idx] = structs
        for z in range(16):
            row = (cz * 16 + z) * TILE + cx * 16
            hs = h[z * 16:z * 16 + 16]
            heights[row:row + 16] = array.array("h", [-2048 if y < -2048 else 4095 if y > 4095 else y for y in hs])
            if colors:
                rgb[row * 3:row * 3 + 48] = b"".join(colors[z * 16:z * 16 + 16])
            else:
                rgb[row * 3:row * 3 + 48] = b"".join(_height_bytes(y) for y in hs)
            if dep:
                depth[row:row + 16] = bytes(255 if d > 255 else d for d in dep[z * 16:z * 16 + 16])
    structures = [tuple(s) for idx in sorted(chunk_structs) for s in chunk_structs[idx]]
    return {"heights": heights, "rgb": rgb, "depth": depth, "structures": structures, "detailed": detailed,
            "complete": not region._bad, "chunk_sig": sig, "chunk_structures": chunk_structs}


def _chunk_signatures(region):
    """Per chunk index: its header entry (sectors and timestamp), 0 if the chunk is absent."""
    offs, ts = region.header_offsets, region.timestamps
    return [(offs[i] << 32 | ts[i]) if (i % 32, i // 32) in region._raw else 0 for i in range(1024)]


_HEIGHT_BYTES = {}


def _height_bytes(y):
    b = _HEIGHT_BYTES.get(y)
    if b is None:
        b = _HEIGHT_BYTES[y] = bytes(HEIGHT_RGB.get(y, (35, 120, 45)))
    return b


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
    """
    Detailed tiles on disk: <root>/<hash of the region folder>/r.X.Z.tile (zlib). Each file keeps
    the final image too (opening a world already seen costs no rendering at all) and the header
    entries of the chunks, so a region the game has saved again is redrawn only where it changed.
    """

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
        tile, stamp = self.load_any(rx, rz)
        try:
            return tile if tile is not None and stamp == self._stamp(path) else None
        except OSError:
            return None

    def load_any(self, rx, rz):
        """(tile, stamp of the region file it was drawn from), even if the region changed since; (None, None)."""
        try:
            with open(self._file(rx, rz), "rb") as f:
                raw = zlib.decompress(f.read())
            head_len = int.from_bytes(raw[:4], "big")
            head = json.loads(raw[4:4 + head_len].decode("utf-8"))
            if head.get("v") != CACHE_VERSION:
                return None, None
            body = memoryview(raw)[4 + head_len:]
            n = TILE * TILE
            if len(body) != 1024 * 8 + n * 10:
                return None, None
            sig = array.array("Q")
            sig.frombytes(body[:8192])
            heights = array.array("h")
            heights.frombytes(body[8192:8192 + n * 2])
            if sys.byteorder != "little":
                sig.byteswap()
                heights.byteswap()
            o = 8192 + n * 2
            chunk_structs = {int(k): [tuple(x) for x in v] for k, v in head.get("structures", {}).items()}
            tile = {"heights": heights, "rgb": bytearray(body[o:o + n * 3]), "depth": bytearray(body[o + n * 3:o + n * 4]),
                    "image": bytes(body[o + n * 4:]), "detailed": head.get("detailed", True),
                    "structures": [s for k in sorted(chunk_structs) for s in chunk_structs[k]],
                    "chunk_structures": chunk_structs, "chunk_sig": list(sig), "complete": True}
            return tile, head.get("stamp")
        except (OSError, ValueError, zlib.error, KeyError, TypeError):
            return None, None

    def save(self, rx, rz, path, tile, stamp=None):
        try:
            os.makedirs(self.dir, exist_ok=True)
            image = tile.get("image") or shade(tile)
            chunk_structs = tile.get("chunk_structures")
            if chunk_structs is None:
                chunk_structs = {0: tile["structures"]} if tile["structures"] else {}
            head = json.dumps({"v": CACHE_VERSION, "stamp": stamp or self._stamp(path), "detailed": tile["detailed"],
                               "structures": {str(k): v for k, v in chunk_structs.items()}}).encode("utf-8")
            sig = array.array("Q", tile.get("chunk_sig") or [0] * 1024)
            heights = array.array("h", tile["heights"])
            if sys.byteorder != "little":
                sig.byteswap()
                heights.byteswap()
            raw = b"".join((len(head).to_bytes(4, "big"), head, sig.tobytes(), heights.tobytes(),
                            bytes(tile["rgb"]), bytes(tile["depth"]), image))
            tmp = self._file(rx, rz) + f".{os.getpid()}.tmp"
            with open(tmp, "wb") as f:
                f.write(zlib.compress(raw, 1))
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


def _payload(tile):
    return {"image": tile.get("image") or shade(tile), "heights": tile["heights"], "structures": tile["structures"],
            "detailed": tile["detailed"], "complete": tile.get("complete", True), "stamp": tile.get("stamp")}


def render_job(path, rx, rz, region_dir, detailed, cache_root=None):
    """
    Worker entry point (runs in a separate process): renders a region and, for detailed tiles,
    stores it in the disk cache. A cached tile of an older version of the file is the starting
    point: only its changed chunks are read again. Returns the payload for the map, or None.
    """
    try:
        stamp = TileCache._stamp(path)           # taken before reading: a write meanwhile invalidates it
    except OSError:
        stamp = None
    if not detailed:
        tile = build_tile(path, detailed=False)
        if tile is None:
            return None
        tile["stamp"] = stamp
        return _payload(tile)
    cache = TileCache(region_dir, root=cache_root)
    base, base_stamp = cache.load_any(rx, rz)
    if base is not None and stamp is not None and base_stamp == stamp:
        base["stamp"] = stamp
        return _payload(base)
    tile = build_tile(path, detailed=True, base=base)
    if tile is None:
        return None
    tile["image"] = shade(tile)
    tile["stamp"] = stamp
    if stamp and tile.get("complete", True):
        cache.save(rx, rz, path, tile, stamp)
    return _payload(tile)
