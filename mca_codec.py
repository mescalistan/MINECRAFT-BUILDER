import functools
import os
import struct
import zlib
import gzip
import time
import shutil
from collections.abc import MutableMapping

from nbt_codec import (
    parse_nbt_bytes, nbt_to_bytes, TAG_Compound, TAG_List, TAG_Byte, TAG_Int,
    TAG_Long_Array, TAG_String,
)

SECTOR = 4096
MAX_INLINE_SECTORS = 255  # the sector count in the region header is a single byte

AIR_NAMES = frozenset(("minecraft:air", "minecraft:cave_air", "minecraft:void_air"))

# DataVersion of 1.18: sections at the chunk root, "block_states"/"biomes" palettes, Y from -64
DATA_VERSION_1_18 = 2860

# Raw NBT headers (tag type + name) used by MCARegion.quick_surface()
_WORLD_SURFACE_TAG = b'\x0c\x00\x0dWORLD_SURFACE'
_YPOS_TAG = b'\x03\x00\x04yPos'
_STATUS_TAG = b'\x08\x00\x06Status'


class UnsupportedChunkFormat(Exception):
    pass


# ---------------------------------------------------------------------------
# Region file (.mca)
# ---------------------------------------------------------------------------

class _ChunkMap(MutableMapping):
    """
    Dict-like view of the chunks of a region: (cx, cz) -> (chunk_nbt, timestamp).
    Chunks are decompressed and parsed only when accessed; assigning a chunk
    marks it as modified so that only modified chunks are re-encoded on save.
    """

    def __init__(self, region):
        self._region = region
        self._decoded = {}

    def __getitem__(self, key):
        if key in self._decoded:
            return self._decoded[key]
        if key not in self._region._raw or key in self._region._bad:
            raise KeyError(key)
        try:
            nbt = self._region._decode(key)
        except Exception as e:
            self._region._bad.add(key)
            print(f"Error reading chunk {key} in {self._region.file_path}: {e}")
            raise KeyError(key) from e
        entry = (nbt, self._region.timestamps[key[0] + key[1] * 32])
        self._decoded[key] = entry
        return entry

    def __setitem__(self, key, value):
        self._decoded[key] = value
        self._region.dirty.add(key)

    def __delitem__(self, key):
        found = False
        if key in self._decoded:
            del self._decoded[key]
            found = True
        if key in self._region._raw:
            del self._region._raw[key]
            found = True
        if not found:
            raise KeyError(key)
        self._region.dirty.add(key)

    def __contains__(self, key):
        return key in self._decoded or (key in self._region._raw and key not in self._region._bad)

    def __iter__(self):
        keys = set(self._decoded) | (set(self._region._raw) - self._region._bad)
        return iter(sorted(keys, key=lambda k: (k[1], k[0])))

    def __len__(self):
        return sum(1 for _ in self)

    def clear_cache(self):
        self._decoded = {}


class MCARegion:
    def __init__(self, file_path):
        self.file_path = file_path
        filename = os.path.basename(file_path)
        parts = filename.split('.')
        if len(parts) >= 4 and parts[0] == 'r':
            try:
                self.rx = int(parts[1])
                self.rz = int(parts[2])
            except ValueError:
                self.rx = 0
                self.rz = 0
        else:
            self.rx = 0
            self.rz = 0

        self._raw = {}       # (cx, cz) -> (compression, payload_bytes, external)
        self._bad = set()    # chunks that failed to decode
        self.dirty = set()   # chunks to re-encode on save
        self.timestamps = [0] * 1024
        self.chunks = _ChunkMap(self)
        self.load()

    # ---- reading ----
    def load(self):
        # The new state is built aside and swapped in at the end, so the map
        # (GUI thread) never sees a half-loaded region while a save reloads it.
        raw = {}
        timestamps = [0] * 1024
        if os.path.exists(self.file_path):
            with open(self.file_path, 'rb') as f:
                data = f.read()
            if len(data) >= 2 * SECTOR:
                offsets = struct.unpack_from('>1024I', data, 0)
                timestamps = list(struct.unpack_from('>1024I', data, SECTOR))
                for idx in range(1024):
                    offset_val = offsets[idx]
                    if offset_val == 0:
                        continue
                    start = (offset_val >> 8) * SECTOR
                    if start + 5 > len(data):
                        continue
                    length, compression = struct.unpack_from('>IB', data, start)
                    if length == 0:
                        continue
                    external = bool(compression & 0x80)
                    # External chunks are stored in c.<x>.<z>.mcc next to the region file
                    payload = None if external else data[start + 5:start + 4 + length]
                    raw[(idx % 32, idx // 32)] = (compression & 0x7F, payload, external)

        self._raw = raw
        self.timestamps = timestamps
        self._bad = set()
        self.dirty = set()
        self.chunks.clear_cache()

    def _external_path(self, cx, cz):
        gx = self.rx * 32 + cx
        gz = self.rz * 32 + cz
        return os.path.join(os.path.dirname(self.file_path), f"c.{gx}.{gz}.mcc")

    def _decode(self, key):
        compression, payload, external = self._raw[key]
        if external:
            with open(self._external_path(*key), 'rb') as f:
                payload = f.read()
        if compression == 1:
            data = gzip.decompress(payload)
        elif compression == 2:
            data = zlib.decompress(payload)
        elif compression == 3:
            data = payload
        else:
            raise ValueError(f"Unsupported chunk compression {compression}")
        nbt, _ = parse_nbt_bytes(data)
        return nbt

    def quick_surface(self, key):
        """
        Top-block Y of the 256 columns of a chunk read straight from the
        WORLD_SURFACE heightmap bytes, without parsing the whole chunk NBT.
        Returns None when the fast path is not possible (caller falls back).
        """
        if key in self.chunks._decoded or key not in self._raw or key in self._bad:
            return None
        compression, payload, external = self._raw[key]
        if external or compression != 2:
            return None
        try:
            data = zlib.decompress(payload)
        except zlib.error:
            return None
        st = data.find(_STATUS_TAG)
        if st >= 0:
            start = st + len(_STATUS_TAG)
            ln = struct.unpack_from('>H', data, start)[0]
            if data[start + 2:start + 2 + ln] not in (b'minecraft:full', b'full'):
                return []            # still being generated: nothing to show (not None: no fallback)
        hm = data.find(_WORLD_SURFACE_TAG)
        ypos = data.find(_YPOS_TAG)
        if hm < 0 or ypos < 0:
            return None
        start = hm + len(_WORLD_SURFACE_TAG)
        if struct.unpack_from('>i', data, start)[0] != 37:
            return None
        longs = struct.unpack_from('>37q', data, start + 4)
        min_y = struct.unpack_from('>i', data, ypos + len(_YPOS_TAG))[0] * 16
        return [v + min_y - 1 for v in decode_indices(longs, 9, 256)]

    def mark_dirty(self, key):
        if key in self.chunks:
            self.dirty.add(key)

    # ---- writing ----
    def create_backup(self):
        if os.path.exists(self.file_path):
            backup_dir = os.path.join(os.path.dirname(self.file_path), 'backups')
            os.makedirs(backup_dir, exist_ok=True)
            filename = os.path.basename(self.file_path)
            ts = int(time.time())
            backup_path = os.path.join(backup_dir, f"{filename}.{ts}.bak")
            n = 1
            while os.path.exists(backup_path):        # two injections in the same second
                backup_path = os.path.join(backup_dir, f"{filename}.{ts}_{n}.bak")
                n += 1
            shutil.copy2(self.file_path, backup_path)
            return backup_path
        return None

    def save(self, dest_path=None):
        if dest_path is None:
            dest_path = self.file_path
        os.makedirs(os.path.dirname(os.path.abspath(dest_path)), exist_ok=True)

        new_offsets = [0] * 1024
        new_timestamps = list(self.timestamps)
        blocks = []
        external_writes = []
        current_sector = 2
        now = int(time.time())

        for cz in range(32):
            for cx in range(32):
                key = (cx, cz)
                idx = cx + cz * 32
                if key in self.dirty and key in self.chunks._decoded:
                    nbt_data, ts = self.chunks._decoded[key]
                    payload = zlib.compress(nbt_to_bytes(nbt_data, ""))
                    compression, external = 2, False
                    new_timestamps[idx] = ts or now
                elif key in self._raw:
                    # Untouched chunk: copy the original compressed bytes as they are
                    compression, payload, external = self._raw[key]
                else:
                    new_timestamps[idx] = 0
                    continue

                if not external and len(payload) + 5 > MAX_INLINE_SECTORS * SECTOR:
                    # Too large for the region file: store it in an external .mcc file
                    external_writes.append((self._external_path(cx, cz), payload))
                    external = True

                if external:
                    chunk_bytes = struct.pack('>IB', 1, compression | 0x80)
                else:
                    chunk_bytes = struct.pack('>IB', len(payload) + 1, compression) + payload
                padding = (-len(chunk_bytes)) % SECTOR
                sectors = (len(chunk_bytes) + padding) // SECTOR
                new_offsets[idx] = (current_sector << 8) | sectors
                blocks.append(chunk_bytes)
                if padding:
                    blocks.append(b'\x00' * padding)
                current_sector += sectors

        for path, payload in external_writes:
            with open(path + ".tmp", 'wb') as f:
                f.write(payload)
            os.replace(path + ".tmp", path)

        # Atomic write: a crash while saving never leaves a half-written region
        tmp_path = dest_path + ".tmp"
        with open(tmp_path, 'wb') as f:
            f.write(struct.pack('>1024I', *new_offsets))
            f.write(struct.pack('>1024I', *new_timestamps))
            for block in blocks:
                f.write(block)
        os.replace(tmp_path, dest_path)

        if os.path.abspath(dest_path) == os.path.abspath(self.file_path):
            self.load()


# ---------------------------------------------------------------------------
# Paletted containers (block_states)
# ---------------------------------------------------------------------------

def decode_indices(data, bits, count=4096):
    """Unpacks palette indices from a long array (1.16+ layout, no spanning)."""
    mask = (1 << bits) - 1
    per_long = 64 // bits
    out = []
    append = out.append
    for v in data:
        v &= 0xFFFFFFFFFFFFFFFF
        for _ in range(per_long):
            append(v & mask)
            v >>= bits
    if len(out) < count:
        out.extend([0] * (count - len(out)))
    elif len(out) > count:
        del out[count:]
    return out


def encode_indices(indices, bits):
    per_long = 64 // bits
    longs = []
    for start in range(0, len(indices), per_long):
        v = 0
        shift = 0
        for idx in indices[start:start + per_long]:
            v |= idx << shift
            shift += bits
        if v >= 1 << 63:
            v -= 1 << 64
        longs.append(v)
    return longs


def _palette_bits(palette_len):
    return max(4, (palette_len - 1).bit_length())


def block_key(b):
    name = b.get("Name", "minecraft:air")
    properties = b.get("Properties", {})
    prop_tuple = tuple(sorted((k, str(v)) for k, v in properties.items()))
    return (name, prop_tuple)


def normalize_state(entry):
    """
    Block state of any palette encoding as {Name, Properties?} (the 1.18-1.21 form).

    Minecraft 26.x writes "minecraft:stone" for blocks without properties and
    {id, properties} for the others; in lists mixing both, strings are wrapped as {"": ...}.
    """
    if isinstance(entry, str):
        return TAG_Compound({"Name": TAG_String(str(entry))})
    if "Name" in entry:
        return entry
    if len(entry) == 1 and "" in entry:
        return normalize_state(entry[""])
    if "id" in entry:
        state = TAG_Compound({"Name": TAG_String(str(entry["id"]))})
        props = entry.get("properties")
        if props:
            state["Properties"] = TAG_Compound({k: TAG_String(str(v)) for k, v in props.items()})
        return state
    return entry


def is_new_state_encoding(palette):
    """True if a palette uses the Minecraft 26.x encoding (strings / {id, properties})."""
    return any(isinstance(e, str) or (hasattr(e, "keys") and "Name" not in e) for e in palette or ())


def encode_palette(states, new_encoding):
    """Palette list of normalized states in the encoding used by the chunk."""
    if not new_encoding:
        return TAG_List(10, states)
    out = []
    for s in states:
        props = s.get("Properties")
        if props:
            out.append(TAG_Compound({"id": TAG_String(str(s["Name"])),
                                     "properties": TAG_Compound({k: TAG_String(str(v)) for k, v in props.items()})}))
        else:
            out.append(TAG_String(str(s["Name"])))
    if all(isinstance(o, str) for o in out):
        return TAG_List(8, out)
    return TAG_List(10, [o if hasattr(o, "keys") else TAG_Compound({"": o}) for o in out])


def section_indices(section_nbt):
    """Returns (palette_list, indices_list) for a section's block_states (palette normalized)."""
    bs = section_nbt.get("block_states")
    if not bs or not bs.get("palette"):
        return [TAG_Compound({"Name": TAG_String("minecraft:air")})], [0] * 4096
    palette = [normalize_state(e) for e in bs["palette"]]
    data = bs.get("data")
    if not data or len(palette) == 1:
        return palette, [0] * 4096
    return palette, decode_indices(data, _palette_bits(len(palette)))


def write_section_indices(section_nbt, palette, indices, new_encoding=None):
    """Stores palette + indices into the section, dropping unused palette entries."""
    if new_encoding is None:
        new_encoding = is_new_state_encoding((section_nbt.get("block_states") or {}).get("palette"))
    remap = {}
    new_palette = []
    for idx in indices:
        if idx not in remap:
            remap[idx] = len(new_palette)
            new_palette.append(palette[idx])
    if "block_states" not in section_nbt:
        section_nbt["block_states"] = TAG_Compound()
    bs = section_nbt["block_states"]
    bs["palette"] = encode_palette(new_palette, new_encoding)
    if len(new_palette) <= 1:
        bs.pop("data", None)
        return
    bits = _palette_bits(len(new_palette))
    bs["data"] = TAG_Long_Array(encode_indices([remap[i] for i in indices], bits))


def unpack_section(section_nbt):
    palette, indices = section_indices(section_nbt)
    return [palette[i] if i < len(palette) else palette[0] for i in indices]


def pack_section(section_nbt, blocks):
    assert len(blocks) == 4096
    palette, index, indices = [], {}, []
    for b in blocks:
        key = block_key(b)
        i = index.get(key)
        if i is None:
            i = index[key] = len(palette)
            palette.append(b)
        indices.append(i)
    write_section_indices(section_nbt, palette, indices)


# ---------------------------------------------------------------------------
# Chunk helpers
# ---------------------------------------------------------------------------

def chunk_format_supported(chunk_nbt):
    """Only the 1.18+ chunk format (sections at root, block_states palettes) is editable."""
    if "Level" in chunk_nbt:
        return False
    dv = chunk_nbt.get("DataVersion")
    return dv is None or int(dv) >= DATA_VERSION_1_18


def chunk_is_full(chunk_nbt):
    status = str(chunk_nbt.get("Status", ""))
    return status in ("full", "minecraft:full")


def chunk_min_y(chunk_nbt):
    ys = [int(s.get("Y", 0)) for s in chunk_nbt.get("sections", []) if "block_states" in s]
    return min(ys) * 16 if ys else -64


def surface_heights(chunk_nbt):
    """Y of the topmost non-air block of each column (index z*16+x), or min_y-1."""
    min_y = chunk_min_y(chunk_nbt)
    heights = [None] * 256
    remaining = 256
    secs = sorted(
        (s for s in chunk_nbt.get("sections", []) if "block_states" in s),
        key=lambda s: int(s.get("Y", 0)), reverse=True,
    )
    for sec in secs:
        if remaining == 0:
            break
        palette = [normalize_state(e) for e in sec["block_states"].get("palette", [])]
        solid = {i for i, b in enumerate(palette) if b.get("Name", "minecraft:air") not in AIR_NAMES}
        if not solid:
            continue
        sy = int(sec.get("Y", 0))
        if len(palette) == 1 or "data" not in sec["block_states"]:
            for i in range(256):
                if heights[i] is None:
                    heights[i] = sy * 16 + 15
                    remaining -= 1
            continue
        _, indices = section_indices(sec)
        for col in range(256):
            if heights[col] is not None:
                continue
            for by in range(15, -1, -1):
                if indices[by * 256 + col] in solid:
                    heights[col] = sy * 16 + by
                    remaining -= 1
                    break
    return [h if h is not None else min_y - 1 for h in heights], min_y


def read_world_surface(chunk_nbt):
    """Reads the WORLD_SURFACE heightmap as top-block Y values, or None if absent."""
    legacy = "Level" in chunk_nbt  # 1.16-1.17 chunk not yet upgraded by the game
    root = chunk_nbt["Level"] if legacy else chunk_nbt
    hm = root.get("Heightmaps") or {}
    ws = hm.get("WORLD_SURFACE")
    if not ws or len(ws) != 37:  # 9 bits per value, 7 values per long (1.16+ layout)
        return None
    min_y = 0 if legacy else chunk_min_y(chunk_nbt)
    values = decode_indices(ws, 9, 256)
    return [v + min_y - 1 for v in values]


def recalculate_heightmaps(chunk_nbt):
    """
    Rewrites WORLD_SURFACE (used by the map viewer) and removes the other
    heightmaps, which Minecraft recomputes exactly when the chunk is loaded.
    """
    heights, min_y = surface_heights(chunk_nbt)
    values = [h - min_y + 1 for h in heights]
    if "Heightmaps" not in chunk_nbt:
        chunk_nbt["Heightmaps"] = TAG_Compound()
    hm = chunk_nbt["Heightmaps"]
    hm["WORLD_SURFACE"] = TAG_Long_Array(encode_indices(values, 9))
    for key in ("MOTION_BLOCKING", "MOTION_BLOCKING_NO_LEAVES", "OCEAN_FLOOR"):
        hm.pop(key, None)


# Blocks that need a block entity to work (ticking detectors, sensors, containers...). Chunks written
# by the program get a minimal one; the game fills in the defaults.
_BLOCK_ENTITY_IDS = {
    "chest": "chest", "trapped_chest": "trapped_chest", "barrel": "barrel", "furnace": "furnace",
    "smoker": "smoker", "blast_furnace": "blast_furnace", "hopper": "hopper", "dispenser": "dispenser",
    "dropper": "dropper", "brewing_stand": "brewing_stand", "lectern": "lectern", "beacon": "beacon",
    "bell": "bell", "campfire": "campfire", "soul_campfire": "campfire", "enchanting_table": "enchanting_table",
    "ender_chest": "ender_chest", "jukebox": "jukebox", "daylight_detector": "daylight_detector",
    "sculk_sensor": "sculk_sensor", "calibrated_sculk_sensor": "calibrated_sculk_sensor",
    "sculk_catalyst": "sculk_catalyst", "sculk_shrieker": "sculk_shrieker", "comparator": "comparator",
    "spawner": "mob_spawner", "decorated_pot": "decorated_pot", "chiseled_bookshelf": "chiseled_bookshelf",
    "crafter": "crafter", "beehive": "beehive", "bee_nest": "beehive", "conduit": "conduit",
}


@functools.lru_cache(maxsize=4096)
def block_entity_id(name):
    short = name.split(":", 1)[-1]
    be = _BLOCK_ENTITY_IDS.get(short)
    if be:
        return "minecraft:" + be
    if short.endswith("_bed"):
        return "minecraft:bed"
    if short.endswith("_hanging_sign") or short.endswith("_wall_hanging_sign"):
        return "minecraft:hanging_sign"
    if short.endswith("_sign"):
        return "minecraft:sign"
    if short.endswith("_banner"):
        return "minecraft:banner"
    if short.endswith("shulker_box"):
        return "minecraft:shulker_box"
    if short.endswith(("_skull", "_head")) and "piston" not in short:
        return "minecraft:skull"
    return None


class ChunkEditor:
    """
    Batched block editing of one chunk: every section is unpacked once,
    edited in memory and packed again only once in flush().
    """

    def __init__(self, chunk_nbt, chunk_x, chunk_z):
        if not chunk_format_supported(chunk_nbt):
            raise UnsupportedChunkFormat(
                "Formato chunk precedente alla 1.18 non supportato: apri il mondo con una versione recente di Minecraft"
            )
        self.nbt = chunk_nbt
        self.chunk_x = chunk_x
        self.chunk_z = chunk_z
        self._sections = {}
        for sec in chunk_nbt.get("sections", []):
            if "block_states" in sec:
                self._sections[int(sec.get("Y", 0))] = sec
        # Minecraft 26.x encodes block states differently: keep the chunk's own encoding
        self.new_encoding = any(is_new_state_encoding(s["block_states"].get("palette"))
                                for s in self._sections.values())
        self.data_version = int(chunk_nbt.get("DataVersion", 0) or 0)
        self._cache = {}       # sy -> [palette, indices, key->index]
        self._dirty_secs = set()
        self.changed = set()   # absolute (x, y, z) of changed blocks
        self.block_data = {}   # absolute (x, y, z) -> block entity tags to merge in on flush

    def _load(self, sy):
        entry = self._cache.get(sy)
        if entry is None:
            sec = self._sections.get(sy)
            if sec is None:
                return None
            palette, indices = section_indices(sec)
            lookup = {block_key(b): i for i, b in enumerate(palette)}
            entry = self._cache[sy] = [palette, indices, lookup]
        return entry

    def get_block(self, x, y, z):
        entry = self._load(y >> 4)
        if entry is None:
            return None
        palette, indices, _ = entry
        return palette[indices[((y & 15) << 8) | (z << 4) | x]]

    def set_block(self, x, y, z, state, key=None):
        """x, z are chunk-local (0..15). Returns False if y is outside the world."""
        sy = y >> 4
        entry = self._load(sy)
        if entry is None:
            return False
        palette, indices, lookup = entry
        if key is None:
            key = block_key(state)
        p = lookup.get(key)
        if p is None:
            p = lookup[key] = len(palette)
            palette.append(state)
        pos = ((y & 15) << 8) | (z << 4) | x
        if indices[pos] != p:
            indices[pos] = p
            self._dirty_secs.add(sy)
            self.changed.add((self.chunk_x * 16 + x, y, self.chunk_z * 16 + z))
        return True

    @property
    def dirty(self):
        return bool(self._dirty_secs or self.block_data)

    def set_block_data(self, x, y, z, data):
        """Block entity data (container items...) for the block at absolute (x, y, z), written on flush."""
        self.block_data[(x, y, z)] = data

    def flush(self):
        if not self.dirty:
            return False
        for sy in self._dirty_secs:
            palette, indices, _ = self._cache[sy]
            sec = self._sections[sy]
            write_section_indices(sec, palette, indices, self.new_encoding)
            # Stale light data: Minecraft recomputes it because isLightOn is reset below
            sec.pop("BlockLight", None)
            sec.pop("SkyLight", None)
        self.nbt["isLightOn"] = TAG_Byte(0)

        # Remove block entities (chest contents, signs...) of overwritten blocks, and add an empty
        # one for the new blocks that need it (detectors and sensors would not tick without it)
        be_list = self.nbt.get("block_entities") or []
        kept = [be for be in be_list
                if (int(be.get("x", 0)), int(be.get("y", 0)), int(be.get("z", 0))) not in self.changed]
        for (x, y, z) in self.changed:
            state = self.get_block(x - self.chunk_x * 16, y, z - self.chunk_z * 16)
            be_id = block_entity_id(str(state.get("Name", ""))) if state is not None else None
            if be_id:
                kept.append(TAG_Compound({"id": TAG_String(be_id), "x": TAG_Int(x), "y": TAG_Int(y),
                                          "z": TAG_Int(z), "keepPacked": TAG_Byte(0)}))
        if self.block_data:
            by_pos = {(int(be.get("x", 0)), int(be.get("y", 0)), int(be.get("z", 0))): i
                      for i, be in enumerate(kept)}
            for (x, y, z), data in self.block_data.items():
                i = by_pos.get((x, y, z))
                if i is None:
                    state = self.get_block(x - self.chunk_x * 16, y, z - self.chunk_z * 16)
                    be_id = block_entity_id(str(state.get("Name", ""))) if state is not None else None
                    if not be_id:
                        continue
                    kept.append(TAG_Compound({"id": TAG_String(be_id), "x": TAG_Int(x), "y": TAG_Int(y),
                                              "z": TAG_Int(z), "keepPacked": TAG_Byte(0)}))
                    i = len(kept) - 1
                be = TAG_Compound(kept[i])
                for k, v in data.items():
                    if k not in ("id", "x", "y", "z"):
                        be[k] = v
                kept[i] = be
            self.block_data = {}
        if len(kept) != len(be_list) or any(k is not o for k, o in zip(kept, be_list)):
            self.nbt["block_entities"] = TAG_List(10, kept)

        recalculate_heightmaps(self.nbt)
        self._dirty_secs.clear()
        self._cache.clear()
        self.changed = set()        # a later flush must not reset the block entities written now
        return True


def set_block(chunk_nbt, x, y, z, block_state):
    """Single block edit (kept for compatibility). Prefer ChunkEditor for many blocks."""
    editor = ChunkEditor(chunk_nbt, int(chunk_nbt.get("xPos", 0)), int(chunk_nbt.get("zPos", 0)))
    editor.set_block(x, y, z, block_state)
    for sy in editor._dirty_secs:
        palette, indices, _ = editor._cache[sy]
        write_section_indices(editor._sections[sy], palette, indices)
