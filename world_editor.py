"""
World-level block editing across multiple region files, plus the structure
injection routine used by the GUI worker thread.
"""
import gzip
import json
import math
import os
import zlib
from array import array
import time
import uuid

from nbt_codec import (TAG_Compound, TAG_String, TAG_List, TAG_Double, TAG_Float, TAG_Int, TAG_Int_Array,
                       TAG_Byte)
from mca_codec import (
    MCARegion, ChunkEditor, AIR_NAMES, block_key, chunk_is_full, read_world_surface,
    chunk_format_supported,
)
from nbt_codec import parse_nbt_bytes, nbt_to_bytes

AIR_STATE = TAG_Compound({"Name": TAG_String("minecraft:air")})
_AIR_KEY = block_key(AIR_STATE)

# Blocks skipped while looking for the ground under a structure
_NON_GROUND_HINTS = (
    "water", "lava", "leaves", "short_grass", "tall_grass", "fern", "flower", "poppy",
    "dandelion", "tulip", "orchid", "allium", "bluet", "daisy", "cornflower", "lily",
    "sapling", "bush", "vine", "torch", "snow", "seagrass", "kelp", "sugar_cane",
    "mushroom", "sweet_berry", "dripleaf", "azalea", "moss_carpet", "carpet",
)


MAX_FOUNDATION_GAP = 10   # blocks of empty space filled under a structure
MAX_PILLAR_DEPTH = 96     # bridge piers / towers reach the ground up to this depth


_NOT_PILLAR = ("stairs", "slab", "banner", "lever", "fence", "_wall", "torch", "lantern", "door", "button",
               "sign", "carpet", "pane", "bars", "chain", "rail", "pressure_plate", "ladder", "vine", "flower",
               "sapling", "head", "skull", "candle", "redstone", "repeater", "comparator", "hopper", "_bed",
               "chest", "barrel", "water", "lava", "glass", "leaves", "air", "piston", "observer", "sensor",
               "detector", "bulb", "lamp")


def _is_pillar_block(name):
    """Full building blocks that can continue down to the ground as a pillar."""
    return not any(k in name for k in _NOT_PILLAR)


def is_ground(name):
    if name in AIR_NAMES:
        return False
    if name in ("minecraft:snow_block", "minecraft:powder_snow"):
        return True
    return not any(h in name for h in _NON_GROUND_HINTS)


def surface_fill_blocks(surface_block_name):
    """(top block, filler block) matching the ground the structure stands on."""
    s_name = surface_block_name.lower()
    if "grass_block" in s_name or "dirt_path" in s_name or "farmland" in s_name:
        return "minecraft:grass_block", "minecraft:dirt"
    if "red_sand" in s_name:
        return "minecraft:red_sand", "minecraft:red_sandstone"
    if "sand" in s_name:
        return "minecraft:sand", "minecraft:sandstone"
    if "snow" in s_name:
        return "minecraft:snow_block", "minecraft:dirt"
    if "podzol" in s_name:
        return "minecraft:podzol", "minecraft:dirt"
    if "mycelium" in s_name:
        return "minecraft:mycelium", "minecraft:dirt"
    if "mud" in s_name:
        return "minecraft:mud", "minecraft:mud"
    if "terracotta" in s_name:
        return "minecraft:terracotta", "minecraft:terracotta"
    if "dirt" in s_name or "gravel" in s_name:
        return s_name if s_name.startswith("minecraft:") else "minecraft:dirt", "minecraft:dirt"
    if any(k in s_name for k in ("stone", "deepslate", "andesite", "diorite", "granite", "tuff", "calcite")):
        return "minecraft:stone", "minecraft:stone"
    return "minecraft:grass_block", "minecraft:dirt"


# Block renames between versions: (first DataVersion with the new name, old name, new name).
# Chunks are written without DataFixer, so a structure saved with an older name must use the
# name the target world knows, otherwise the game drops the whole 16x16x16 section.
BLOCK_RENAMES = [
    (2724, "minecraft:grass_path", "minecraft:dirt_path"),     # 1.17
    (3679, "minecraft:grass", "minecraft:short_grass"),        # 1.20.3
    (4536, "minecraft:chain", "minecraft:iron_chain"),         # 1.21.9
]


def upgrade_block(block, target_version):
    """Block dict with its name updated for the target world's DataVersion."""
    name = block.get("Name", "")
    for version, old, new in BLOCK_RENAMES:
        if name == old and target_version >= version:
            return dict(block, Name=new)
    return block


def to_state(block):
    state = TAG_Compound({"Name": TAG_String(block["Name"])})
    props = block.get("Properties")
    if props:
        state["Properties"] = TAG_Compound({k: TAG_String(v) for k, v in props.items()})
    return state


TEXT_COMPONENT_NBT_VERSION = 4325   # 1.21.5: names are stored as text components, no longer as JSON
ITEM_COMPONENTS_VERSION = 3837      # 1.20.5: items have "count" and "components" instead of "Count" and "tag"


def adapt_block_data(data, version):
    """
    Block entity data written by the templates uses plain strings for names (CustomName, item
    custom_name), valid from 1.21.5. Older worlds want a JSON string: converted here.
    """
    if version >= TEXT_COMPONENT_NBT_VERSION:
        return data

    def to_json(v):
        try:
            json.loads(v)               # already a JSON text component
            return v
        except ValueError:
            return TAG_String(json.dumps(str(v)))

    out = TAG_Compound(data)
    if isinstance(out.get("CustomName"), str):
        out["CustomName"] = to_json(out["CustomName"])
    items = out.get("Items")
    if items:
        new_items = []
        for item in items:
            comps = item.get("components")
            if version < ITEM_COMPONENTS_VERSION:
                # 1.20.4 and older: byte "Count" and the name in tag.display.Name
                old = TAG_Compound({"id": item.get("id", TAG_String("minecraft:air")),
                                    "Count": TAG_Byte(int(item.get("count", item.get("Count", 1))))})
                if "Slot" in item:
                    old["Slot"] = item["Slot"]
                if comps and isinstance(comps.get("minecraft:custom_name"), str):
                    old["tag"] = TAG_Compound({"display": TAG_Compound(
                        {"Name": to_json(comps["minecraft:custom_name"])})})
                item = old
            elif comps and isinstance(comps.get("minecraft:custom_name"), str):
                item = TAG_Compound(item)
                item["components"] = TAG_Compound(comps)
                item["components"]["minecraft:custom_name"] = to_json(comps["minecraft:custom_name"])
            new_items.append(item)
        out["Items"] = TAG_List(10, new_items)
    return out


class World:
    """Global-coordinate access to the regions of one dimension."""

    def __init__(self, region_dir, preloaded=None):
        self.region_dir = region_dir
        self._regions = {}   # (rx, rz) -> MCARegion | None
        self._editors = {}   # (chunk_x, chunk_z) -> ChunkEditor | None
        self.skipped_chunks = {}  # (chunk_x, chunk_z) -> reason
        self._entities = {}       # (chunk_x, chunk_z) -> [entity compound] to add on save
        self._versions = {}       # (chunk_x, chunk_z) -> DataVersion of chunks already released
        self._stored_regions = set()   # regions with chunks re-encoded in memory (release_chunk)
        for region in (preloaded or []):
            self._regions[(region.rx, region.rz)] = region

    def region(self, rx, rz):
        key = (rx, rz)
        if key not in self._regions:
            path = os.path.join(self.region_dir, f"r.{rx}.{rz}.mca")
            self._regions[key] = MCARegion(path) if os.path.exists(path) else None
        return self._regions[key]

    def editor(self, chunk_x, chunk_z):
        key = (chunk_x, chunk_z)
        if key in self._editors:
            return self._editors[key]
        editor = None
        region = self.region(chunk_x >> 5, chunk_z >> 5)
        local = (chunk_x & 31, chunk_z & 31)
        if region is None:
            self.skipped_chunks[key] = "regione inesistente"
        else:
            entry = region.chunks.get(local)
            if entry is None:
                self.skipped_chunks[key] = "chunk non generato"
            elif not chunk_format_supported(entry[0]):
                # Worlds upgraded from older versions keep old-format chunks until the
                # game loads them again: skip them instead of aborting the whole injection.
                self.skipped_chunks[key] = "chunk in formato pre-1.18 (visita l'area in gioco per aggiornarlo)"
            elif not chunk_is_full(entry[0]):
                self.skipped_chunks[key] = "chunk generato solo in parte"
            else:
                editor = ChunkEditor(entry[0], chunk_x, chunk_z)
        self._editors[key] = editor
        return editor

    def release_chunk(self, chunk_x, chunk_z):
        """
        Big injections: the edits of a chunk are encoded and compressed now and its decoded data is
        dropped, so the memory used does not grow with the area. Reading it again decodes the new data.
        """
        key = (chunk_x, chunk_z)
        editor = self._editors.get(key)
        if editor is None:
            return
        self._versions[key] = editor.data_version
        region = self.region(chunk_x >> 5, chunk_z >> 5)
        if editor.flush():
            region.store_chunk((chunk_x & 31, chunk_z & 31), editor.nbt)
            self._stored_regions.add(region)
        else:
            region.chunks._decoded.pop((chunk_x & 31, chunk_z & 31), None)
        del self._editors[key]

    def data_version(self, chunk_x, chunk_z):
        v = self._versions.get((chunk_x, chunk_z))
        if v is not None:
            return v
        editor = self.editor(chunk_x, chunk_z)
        return editor.data_version if editor is not None else 0

    def forget_chunk(self, chunk_x, chunk_z):
        """Frees the memory of a chunk that was only read (used when scanning large areas)."""
        key = (chunk_x, chunk_z)
        editor = self._editors.get(key)
        if editor is not None and editor.dirty:
            return
        self._editors.pop(key, None)
        region = self._regions.get((chunk_x >> 5, chunk_z >> 5))
        if region is not None and (chunk_x & 31, chunk_z & 31) not in region.dirty:
            region.chunks._decoded.pop((chunk_x & 31, chunk_z & 31), None)

    def get_block(self, x, y, z):
        """Block state compound at (x, y, z), or None if the chunk is not editable/loaded."""
        editor = self.editor(x >> 4, z >> 4)
        if editor is None:
            return None
        return editor.get_block(x & 15, y, z & 15)

    def get_block_name(self, x, y, z):
        editor = self.editor(x >> 4, z >> 4)
        if editor is None:
            return None
        block = editor.get_block(x & 15, y, z & 15)
        return None if block is None else str(block.get("Name", "minecraft:air"))

    def set_block(self, x, y, z, state, key=None):
        editor = self.editor(x >> 4, z >> 4)
        if editor is None:
            return False
        return editor.set_block(x & 15, y, z & 15, state, key)

    def set_block_data(self, x, y, z, data):
        """Block entity data (container items...) merged into the block at (x, y, z) on save."""
        editor = self.editor(x >> 4, z >> 4)
        if editor is None:
            return False
        editor.set_block_data(x, y, z, adapt_block_data(data, editor.data_version))
        return True

    def add_entity(self, nbt, x, y, z, yaw=0.0):
        """
        Adds an entity (compound with "id", as in structure files) at world position (x, y, z).
        It gets a new UUID and is written to the entities/ region folder on save.
        Returns False if the chunk is not generated.
        """
        cx, cz = math.floor(x) >> 4, math.floor(z) >> 4
        if self.editor(cx, cz) is None:
            return False
        ent = TAG_Compound(nbt)
        for k in ("UUID", "UUIDMost", "UUIDLeast", "Pos", "Motion", "Rotation", "Leash", "sleeping_pos"):
            ent.pop(k, None)
        ent["Pos"] = TAG_List(6, [TAG_Double(x), TAG_Double(y), TAG_Double(z)])
        ent["Motion"] = TAG_List(6, [TAG_Double(0.0)] * 3)
        ent["Rotation"] = TAG_List(5, [TAG_Float(yaw), TAG_Float(0.0)])
        ent["OnGround"] = TAG_Byte(1)
        u = uuid.uuid4().int
        ent["UUID"] = TAG_Int_Array([((u >> s) & 0xFFFFFFFF) - ((u >> s) & 0x80000000) * 2 for s in (96, 64, 32, 0)])
        self._entities.setdefault((cx, cz), []).append(ent)
        return True

    def entities_dir(self):
        return os.path.join(os.path.dirname(os.path.abspath(self.region_dir)), "entities")

    def surface_y(self, x, z):
        """Y of the topmost block of a column from the chunk heightmap, or None."""
        editor = self.editor(x >> 4, z >> 4)
        if editor is None:
            return None
        if not hasattr(editor, "_surface"):
            editor._surface = read_world_surface(editor.nbt)
        if not editor._surface:
            return None
        return editor._surface[((z & 15) << 4) | (x & 15)]

    def ground_y(self, x, z, start_y, max_depth=96):
        """Y of the first ground block at or below start_y, or None."""
        for y in range(start_y, start_y - max_depth, -1):
            name = self.get_block_name(x, y, z)
            if name is None:
                return None
            if is_ground(name):
                return y
        return None

    def modified_regions(self):
        result = [r for r in self._stored_regions]
        for (cx, cz), editor in self._editors.items():
            if editor is not None and editor.dirty:
                region = self.region(cx >> 5, cz >> 5)
                if region not in result:
                    result.append(region)
        return result

    def save(self, backup=True, log=None):
        """Flushes edited chunks and writes every modified region. Returns backup paths."""
        backups = []
        self.last_backups = []    # (region file, backup file): used to undo the injection
        regions = self.modified_regions()
        for region in regions:
            if backup:
                path = region.create_backup()
                if path:
                    backups.append(path)
                    self.last_backups.append((region.file_path, path))
                    if log:
                        log(f"Backup creato: {os.path.basename(path)}")
        for (cx, cz), editor in self._editors.items():
            if editor is not None and editor.flush():
                self.region(cx >> 5, cz >> 5).mark_dirty((cx & 31, cz & 31))
        for region in regions:
            if log:
                log(f"Scrittura {os.path.basename(region.file_path)} ({len(region.dirty)} chunk modificati)...")
            region.save()
        # the regions were reloaded from disk: editors holding the old chunk objects must not be reused
        self._editors = {}
        self._stored_regions = set()
        if self._entities:
            backups += self._save_entities(backup, log)
        return backups

    def _save_entities(self, backup, log):
        """Appends the new entities to the chunks of the entities/ region files (1.17+ worlds)."""
        backups = []
        by_region = {}
        for (cx, cz), ents in self._entities.items():
            by_region.setdefault((cx >> 5, cz >> 5), []).append((cx, cz, ents))
        folder = self.entities_dir()
        for (rx, rz), chunks in by_region.items():
            path = os.path.join(folder, f"r.{rx}.{rz}.mca")
            existed = os.path.exists(path)
            region = MCARegion(path)
            if backup:
                if existed:
                    bpath = region.create_backup()
                    if bpath:
                        backups.append(bpath)
                        self.last_backups.append((path, bpath))
                else:
                    self.last_backups.append((path, None))   # undo = delete the new file
            now = int(time.time())
            count = 0
            for cx, cz, ents in chunks:
                key = (cx & 31, cz & 31)
                entry = region.chunks.get(key)
                if entry is None and key in region._raw:
                    # the chunk exists but cannot be read: writing a new one would delete its entities
                    if log:
                        log(f"Avviso: entita' del chunk {cx}, {cz} illeggibili: {len(ents)} entita' non aggiunte.")
                    continue
                version = self.data_version(cx, cz)
                if entry is None:
                    nbt = TAG_Compound({"DataVersion": TAG_Int(version),
                                        "Position": TAG_Int_Array([cx, cz]),
                                        "Entities": TAG_List(10, [])})
                else:
                    nbt = entry[0]
                old = list(nbt.get("Entities") or [])
                nbt["Entities"] = TAG_List(10, old + ents)
                region.chunks[key] = (nbt, now)
                count += len(ents)
            if log:
                log(f"Scrittura entita' in {os.path.basename(path)} ({count} entita')...")
            region.save()
        self._entities = {}
        return backups


class WorldTerrain:
    """Terrain queries for the village generator: ground height and water, cached per column."""

    def __init__(self, world):
        self.world = world
        self._cache = {}

    def _column(self, x, z):
        key = (x, z)
        if key not in self._cache:
            top = self.world.surface_y(x, z)
            if top is None:
                self._cache[key] = (None, False, False)
            else:
                name = self.world.get_block_name(x, top, z) or ""
                tree = name.endswith(("_leaves", "_log", "_wood"))
                if "water" in name or "lava" in name:
                    self._cache[key] = (top, True, False)
                else:
                    ground = self.world.ground_y(x, z, top)
                    # under a tree the ground is below the trunk
                    while ground is not None and (self.world.get_block_name(x, ground, z) or "").endswith(
                            ("_log", "_wood")):
                        ground = self.world.ground_y(x, z, ground - 1)
                    self._cache[key] = (ground if ground is not None else top, False, tree)
        return self._cache[key]

    def is_tree(self, x, z):
        return self._column(x, z)[2]

    def height(self, x, z):
        return self._column(x, z)[0]

    def is_water(self, x, z):
        return self._column(x, z)[1]


def _packed_view(struct):
    """(iterable of (x, y, z, palette index), palette states, block count): no dict per block needed."""
    blocks = struct.blocks
    if getattr(blocks, "packed", False):
        return blocks.iter_xyzs(), blocks.states, len(blocks)
    states, index, out = [], {}, []
    for (x, y, z), b in blocks.items():
        i = index.get(id(b))
        if i is None:
            i = index[id(b)] = len(states)
            states.append(b)
        out.append((x, y, z, i))
    return out, states, len(out)


# kinds of structure palette entries
_K_BLOCK, _K_AIR, _K_MODDED = 0, 1, 2
_FLUID_ENDS = ("water", "lava")


def _palette_kinds(states, skip_modded):
    kinds = []
    for b in states:
        name = b.get("Name", "minecraft:air")
        if name in AIR_NAMES:
            kinds.append(_K_AIR)
        elif skip_modded and not name.startswith("minecraft:"):
            kinds.append(_K_MODDED)
        else:
            kinds.append(_K_BLOCK)
    return kinds


def _place_chunk(ed, pos_arr, s_arr, kinds, states, targets, clear_terrain, stats):
    """
    Writes the blocks of one chunk straight into its decoded sections. pos = (y << 8) | (z << 4) | x
    (chunk-local x, z). Every section is looked up once; states are converted once per palette entry.
    """
    version = ed.data_version
    tg = targets.get(version)
    if tg is None:
        tg = targets[version] = [None] * len(states)
    secs = {}
    load = ed._load
    dirty = ed._dirty_secs
    changed = ed._changed
    placed = cleared = destroyed = skipped_h = skipped_mod = 0
    air_names = AIR_NAMES
    fluid = _FLUID_ENDS
    for p, s in zip(pos_arr, s_arr):
        kind = kinds[s]
        if kind == _K_MODDED:
            skipped_mod += 1
            continue
        y = p >> 8
        sy = y >> 4
        e = secs.get(sy, 0)
        if e == 0:
            e = secs[sy] = load(sy)
        if e is None:
            if kind == _K_BLOCK:
                skipped_h += 1
            continue
        palette, indices, lookup = e
        local = ((y & 15) << 8) | (p & 255)
        cur_i = indices[local]
        cur_name = palette[cur_i].get("Name", "minecraft:air")
        if kind == _K_AIR:
            if not clear_terrain or cur_name in air_names:
                continue
            state, key = AIR_STATE, _AIR_KEY
            cleared += 1
            if not cur_name.endswith(fluid):
                destroyed += 1
        else:
            t = tg[s]
            if t is None:
                state = to_state(upgrade_block(states[s], version))
                t = tg[s] = (state, block_key(state))
            state, key = t
            placed += 1
            if cur_name not in air_names and not cur_name.endswith(fluid) and cur_name != state["Name"]:
                destroyed += 1
        ti = lookup.get(key)
        if ti is None:
            ti = lookup[key] = len(palette)
            palette.append(state)
        if cur_i != ti:
            indices[local] = ti
            if sy not in dirty:
                dirty.add(sy)
            cs = changed.get(sy)
            if cs is None:
                cs = changed[sy] = set()
            cs.add(local)
    stats["placed"] += placed
    stats["cleared"] += cleared
    stats["destroyed"] += destroyed
    stats["skipped_height"] += skipped_h
    stats["skipped_modded"] += skipped_mod


def _foundation_plan(world, item, ox, oy, oz, cols, base_layer, states):
    """Foundations under the columns of one chunk (read before its blocks are placed)."""
    out = []
    pillar_cols = item.get("pillar_columns")
    pillars = item.get("extend_columns") or item.get("pillars") or pillar_cols is not None
    for bx, bz, by, s in cols:
        # Only columns resting on the structure's lowest layer: arches, bridges and overhangs keep the
        # empty space below them.
        if pillar_cols is not None:
            if (bx, bz) not in pillar_cols:
                continue
        elif by != base_layer and not item.get("pillars"):
            continue
        gx, gz = ox + bx, oz + bz
        base_y = oy + by
        ground = world.ground_y(gx, gz, base_y - 1)
        if ground is None or ground >= base_y - 1:
            continue
        # A big gap means the structure floats on purpose: only small gaps are filled. Structures resting
        # on water are not propped up either; bridge piers always go down to the bottom.
        if base_y - 1 - ground > (MAX_PILLAR_DEPTH if pillars else MAX_FOUNDATION_GAP):
            continue
        below = world.get_block_name(gx, base_y - 1, gz) or ""
        if not pillars and ("water" in below or "lava" in below):
            continue
        if pillars:
            bottom = states[s]
            if not _is_pillar_block(bottom.get("Name", "")):
                continue        # stairs, banners, levers... hanging under an overhang
            fill = (bottom, bottom)
        else:
            surface = world.get_block_name(gx, ground, gz) or "minecraft:grass_block"
            fill = tuple({"Name": n} for n in surface_fill_blocks(surface))
        out.append((gx, gz, ground, base_y, fill))
    return out


def _fill_foundations(world, foundation_cols, stats):
    for gx, gz, ground, base_y, (surf_block, sub_block) in foundation_cols:
        surf, sub = to_state(surf_block), to_state(sub_block)
        for y in range(ground + 1, base_y):
            if world.set_block(gx, y, gz, surf if y == base_y - 1 else sub):
                stats["foundation"] += 1


def _new_stats():
    return {"placed": 0, "cleared": 0, "foundation": 0, "landscape": 0, "skipped_missing": 0, "skipped_modded": 0,
            "skipped_height": 0, "destroyed": 0, "blend": 0, "block_data": 0, "entities": 0,
            "path": 0, "demolished": 0}


class _OneChunkWorld(World):
    """World view of a single decoded chunk (worker processes)."""

    def __init__(self, editor):
        self.region_dir = None
        self._regions = {}
        self._editors = {(editor.chunk_x, editor.chunk_z): editor}
        self.skipped_chunks = {}
        self._entities = {}
        self._versions = {}
        self._stored_regions = set()

    def editor(self, chunk_x, chunk_z):
        return self._editors.get((chunk_x, chunk_z))


def _chunk_job(payload, cx, cz, pos_arr, s_arr, kinds, states, clear_terrain, item, ox, oy, oz, cols,
               base_layer, block_data, stats, targets):
    """Decodes one chunk, places its blocks, foundations and block data; returns the new payload."""
    compression, raw = payload
    data = zlib.decompress(raw) if compression == 2 else gzip.decompress(raw) if compression == 1 else raw
    nbt, _ = parse_nbt_bytes(data)
    if not chunk_format_supported(nbt) or not chunk_is_full(nbt):
        stats["skipped_missing"] += sum(1 for s in s_arr if kinds[s] == _K_BLOCK)
        reason = ("chunk generato solo in parte" if chunk_format_supported(nbt) else
                  "chunk in formato pre-1.18 (visita l'area in gioco per aggiornarlo)")
        stats.setdefault("skipped", []).append(((cx, cz), reason))
        return None, nbt
    ed = ChunkEditor(nbt, cx, cz)
    w = _OneChunkWorld(ed)
    if cols is None and item.get("foundations"):
        cols = _chunk_columns(cx, cz, pos_arr, s_arr, kinds, ox, oy, oz)
    found = _foundation_plan(w, item, ox, oy, oz, cols, base_layer, states) if cols else []
    _place_chunk(ed, pos_arr, s_arr, kinds, states, targets, clear_terrain, stats)
    _fill_foundations(w, found, stats)
    for (x, y, z), d in block_data:
        name = w.get_block_name(x, y, z)
        if name is not None and name not in AIR_NAMES:
            ed.set_block_data(x, y, z, adapt_block_data(d, ed.data_version))
            stats["block_data"] += 1
    if not ed.flush():
        return None, nbt
    return (2, zlib.compress(nbt_to_bytes(nbt, ""))), nbt


def _chunk_columns(cx, cz, pos_arr, s_arr, kinds, ox, oy, oz):
    """Lowest non-air block of every column of a chunk, in structure coordinates (for the foundations)."""
    low = {}
    for p, s in zip(pos_arr, s_arr):
        if kinds[s] == _K_AIR:
            continue
        col, y = p & 255, p >> 8
        cur = low.get(col)
        if cur is None or y < cur[0]:
            low[col] = (y, s)
    return [(cx * 16 + (col & 15) - ox, cz * 16 + (col >> 4) - oz, y - oy, s) for col, (y, s) in low.items()]


def _group_job(args):
    """Worker process: a slice of a big structure split by world chunk. Returns ({chunk: arrays}, min y)."""
    xs, ys, zs, si, rot, bw, bl, ox, oy, oz, air = args
    w1, l1 = bw - 1, bl - 1
    it = zip(xs, ys, zs, si)
    if rot == 1:
        it = ((l1 - z, y, x, s) for x, y, z, s in it)
    elif rot == 2:
        it = ((w1 - x, y, l1 - z, s) for x, y, z, s in it)
    elif rot == 3:
        it = ((z, y, w1 - x, s) for x, y, z, s in it)
    groups = {}
    low = 1 << 30
    for x, y, z, s in it:
        if y < low and not air[s]:
            low = y
        gx, gz = x + ox, z + oz
        k = (gx >> 4, gz >> 4)
        g = groups.get(k)
        if g is None:
            g = groups[k] = (array("i"), array("i"))
        g[0].append(((y + oy) << 8) | ((gz & 15) << 4) | (gx & 15))
        g[1].append(s)
    return groups, low


def _inject_big(world, item, struct, kinds, states, clear_terrain, fill_foundations, stats, log):
    """Very large structures: grouping by chunk and placing are both done by worker processes."""
    from concurrent.futures import ProcessPoolExecutor
    ox, oy, oz = item["world_x"], item["y_coord"], item["world_z"]
    blocks = struct.blocks
    if getattr(blocks, "packed", False):
        xs, ys, zs, si = blocks.xs, blocks.ys, blocks.zs, blocks.si
        rot, bw, bl = blocks.rot, blocks.base_w, blocks.base_l
    else:
        index = {id(b): i for i, b in enumerate(states)}
        xs, ys, zs, si = array("i"), array("i"), array("i"), array("i")
        for (x, y, z), b in blocks.items():
            xs.append(x)
            ys.append(y)
            zs.append(z)
            si.append(index[id(b)])
        rot, bw, bl = 0, struct.width, struct.length
    air = bytes(1 if k == _K_AIR else 0 for k in kinds)
    n = len(xs)
    parts = _workers() * 2
    step = -(-n // parts)
    slices = [(xs[a:a + step], ys[a:a + step], zs[a:a + step], si[a:a + step], rot, bw, bl, ox, oy, oz, air)
              for a in range(0, n, step)]
    log(f"  {n} blocchi divisi in {len(slices)} parti, {_workers()} processi...")
    groups, base_layer = {}, 1 << 30
    with ProcessPoolExecutor(max_workers=_workers()) as pool:
        for part, low in pool.map(_group_job, slices):
            base_layer = min(base_layer, low)
            for k, (pa, sa) in part.items():
                g = groups.get(k)
                if g is None:
                    groups[k] = (pa, sa)
                else:
                    g[0].extend(pa)
                    g[1].extend(sa)
    del slices
    has_blocks = base_layer != 1 << 30
    base_layer = base_layer if has_blocks else 0
    data_by_chunk = {}
    for (bx, by, bz), d in getattr(struct, "block_nbt", {}).items():
        gx, gy, gz = ox + bx, oy + by, oz + bz
        data_by_chunk.setdefault((gx >> 4, gz >> 4), []).append(((gx, gy, gz), d))
    order = sorted(groups, key=lambda k: (k[0] >> 5, k[1] >> 5, k[1], k[0]))
    _inject_parallel(world, dict(item, foundations=fill_foundations), order, groups, kinds, states,
                     clear_terrain, ox, oy, oz, None, base_layer, data_by_chunk, stats, log)
    return base_layer, has_blocks


def _region_job(job):
    """Worker process: a batch of chunks. Returns ({(cx, cz): payload}, versions, stats)."""
    out, versions = {}, {}
    stats = _new_stats()
    targets = {}
    for (cx, cz), payload, pos_arr, s_arr, cols, block_data in job["chunks"]:
        cols = None if cols == "worker" else cols
        try:
            new, nbt = _chunk_job(payload, cx, cz, pos_arr, s_arr, job["kinds"], job["states"],
                                  job["clear_terrain"], job["item"], job["ox"], job["oy"], job["oz"], cols,
                                  job["base_layer"], block_data, stats, targets)
        except Exception as e:      # a damaged chunk must not stop the others
            stats.setdefault("errors", []).append(f"chunk {cx},{cz}: {e}")
            continue
        versions[(cx, cz)] = int(nbt.get("DataVersion", 0) or 0)
        if new is not None:
            out[(cx, cz)] = new
    return out, versions, stats


PARALLEL_MIN_BLOCKS = 300_000      # structures smaller than this are placed in this process


def _workers():
    return max(1, min(8, (os.cpu_count() or 2) - 1))


def _inject_structure(world, item, clear_terrain, skip_modded, fill_foundations, stats, log, parallel):
    struct = item["structure"]
    ox, oy, oz = item["world_x"], item["y_coord"], item["world_z"]
    if parallel and len(struct.blocks) >= PARALLEL_MIN_BLOCKS:
        blocks = struct.blocks
        states = blocks.states if getattr(blocks, "packed", False) else _dict_palette(blocks)
        kinds = _palette_kinds(states, skip_modded)
        result = _inject_big(world, item, struct, kinds, states, clear_terrain, fill_foundations, stats, log)
        _add_entities(world, struct, ox, oy, oz, stats)
        return result
    blocks_iter, states, n_blocks = _packed_view(struct)
    kinds = _palette_kinds(states, skip_modded)
    W, L = max(struct.width, 1), max(struct.length, 1)
    NO = 1 << 30
    bottom = array("i", [NO]) * (W * L)
    bottom_s = array("i", [0]) * (W * L)
    groups = {}
    for x, y, z, s in blocks_iter:
        if kinds[s] != _K_AIR and 0 <= x < W and 0 <= z < L:
            c = x * L + z
            if y < bottom[c]:
                bottom[c] = y
                bottom_s[c] = s
        gx, gz = x + ox, z + oz
        k = (gx >> 4, gz >> 4)
        g = groups.get(k)
        if g is None:
            g = groups[k] = (array("i"), array("i"))
        g[0].append(((y + oy) << 8) | ((gz & 15) << 4) | (gx & 15))
        g[1].append(s)
    used = [b for b in bottom if b != NO]
    base_layer = min(used) if used else 0

    # columns (with their lowest block) and block entity data, chunk by chunk
    cols_by_chunk = {}
    if fill_foundations and used:
        for c in range(W * L):
            by = bottom[c]
            if by == NO:
                continue
            bx, bz = divmod(c, L)
            cols_by_chunk.setdefault(((ox + bx) >> 4, (oz + bz) >> 4), []).append((bx, bz, by, bottom_s[c]))
    data_by_chunk = {}
    for (bx, by, bz), d in getattr(struct, "block_nbt", {}).items():
        gx, gy, gz = ox + bx, oy + by, oz + bz
        data_by_chunk.setdefault((gx >> 4, gz >> 4), []).append(((gx, gy, gz), d))

    order = sorted(groups, key=lambda k: (k[0] >> 5, k[1] >> 5, k[1], k[0]))
    targets = {}
    release = n_blocks >= PARALLEL_MIN_BLOCKS      # big but not parallel: keep the memory flat
    for n, k in enumerate(order):
        ed = world.editor(*k)
        pos_arr, s_arr = groups[k]
        if ed is None:
            stats["skipped_missing"] += sum(1 for s in s_arr if kinds[s] == _K_BLOCK)
            continue
        found = _foundation_plan(world, item, ox, oy, oz, cols_by_chunk.get(k, ()), base_layer, states)
        _place_chunk(ed, pos_arr, s_arr, kinds, states, targets, clear_terrain, stats)
        _fill_foundations(world, found, stats)
        for (gx, gy, gz), d in data_by_chunk.get(k, ()):
            name = world.get_block_name(gx, gy, gz)
            if name is not None and name not in AIR_NAMES and world.set_block_data(gx, gy, gz, d):
                stats["block_data"] += 1
        if release:
            world.release_chunk(*k)
        if n % 500 == 499:
            log(f"  {n + 1} chunk su {len(order)}...")
    _add_entities(world, struct, ox, oy, oz, stats)
    return base_layer, bool(used)


def _add_entities(world, struct, ox, oy, oz, stats):
    for ent in getattr(struct, "entities", ()):
        ex, ey, ez = ent["pos"]
        if world.add_entity(ent["nbt"], ox + ex, oy + ey, oz + ez, ent.get("yaw", 0.0)):
            stats["entities"] += 1


def _dict_palette(blocks):
    """The distinct state dicts of a dict structure (blocks loaded from a file share them)."""
    seen, out = set(), []
    for b in blocks.values():
        if id(b) not in seen:
            seen.add(id(b))
            out.append(b)
    return out


def _inject_parallel(world, item, order, groups, kinds, states, clear_terrain, ox, oy, oz, cols_by_chunk,
                     base_layer, data_by_chunk, stats, log):
    """Big structures: every region file is processed by a worker process (chunks travel compressed)."""
    from concurrent.futures import ProcessPoolExecutor
    plain_states = [{"Name": str(b.get("Name", "minecraft:air")),
                     "Properties": {k: str(v) for k, v in (b.get("Properties") or {}).items()}} for b in states]
    item_spec = {k: item.get(k) for k in ("pillar_columns", "extend_columns", "pillars", "foundations")}
    jobs = {}
    batch = max(8, len(order) // (_workers() * 4))   # several batches per process: balanced load
    for k in order:
        cx, cz = k
        region = world.region(cx >> 5, cz >> 5)
        local = (cx & 31, cz & 31)
        world.release_chunk(cx, cz)                 # in-memory edits of earlier placements go first
        raw = region._raw.get(local) if region is not None else None
        pos_arr, s_arr = groups[k]
        if raw is None or raw[2] or local in region._bad:
            if raw is not None and raw[2]:         # external .mcc chunk: done in this process
                ed = world.editor(cx, cz)
                if ed is not None:
                    cols = (cols_by_chunk.get(k, []) if cols_by_chunk is not None else
                            _chunk_columns(cx, cz, pos_arr, s_arr, kinds, ox, oy, oz) if item.get("foundations")
                            else [])
                    found = _foundation_plan(world, item, ox, oy, oz, cols, base_layer, states)
                    _place_chunk(ed, pos_arr, s_arr, kinds, states, {}, clear_terrain, stats)
                    _fill_foundations(world, found, stats)
                    continue
            world.skipped_chunks[k] = "chunk non generato"
            stats["skipped_missing"] += sum(1 for s in s_arr if kinds[s] == _K_BLOCK)
            continue
        job = jobs.setdefault(len(jobs) if not jobs or len(jobs[len(jobs) - 1]["chunks"]) >= batch
                              else len(jobs) - 1, {
            "kinds": kinds, "states": plain_states, "clear_terrain": clear_terrain, "item": item_spec,
            "ox": ox, "oy": oy, "oz": oz, "base_layer": base_layer, "chunks": []})
        cols = "worker" if cols_by_chunk is None else cols_by_chunk.get(k, [])
        job["chunks"].append((k, (raw[0], raw[1]), pos_arr, s_arr, cols, data_by_chunk.get(k, [])))
    total = sum(len(j["chunks"]) for j in jobs.values())
    log(f"  {total} chunk in {len(jobs)} gruppi, {_workers()} processi in parallelo...")
    done = 0
    with ProcessPoolExecutor(max_workers=_workers()) as pool:
        for job, (out, versions, st) in zip(jobs.values(), pool.map(_region_job, jobs.values())):
            for (cx, cz), (compression, payload) in out.items():
                region = world.region(cx >> 5, cz >> 5)
                region.store_raw((cx & 31, cz & 31), compression, payload)
                world._stored_regions.add(region)
            world._versions.update(versions)
            for key, v in st.items():
                if key == "errors":
                    for msg in v:
                        log(f"Avviso: {msg}")
                elif key == "skipped":
                    for k, reason in v:
                        world.skipped_chunks[k] = reason
                else:
                    stats[key] = stats.get(key, 0) + v
            done += len(job["chunks"])
            log(f"  {done} chunk su {total}...")


def inject_structures(world, placements, fill_foundations=True, clear_terrain=True,
                      skip_modded=True, log=None, blend=False, parallel=True):
    """
    Places the structures in the world (in memory). Call world.save() afterwards.
    Each placement: {"structure", "world_x", "world_z", "y_coord", "name"}, optionally "terrain"
    ("natural", "blend", "none") and "water_mode" ("island", "float").
    blend: the default terrain around the structures: "natural" reshapes the land (hill, stairs,
    island: see landscape.py), True only adds a short earth slope, False leaves it as it is.
    Big structures are placed chunk by chunk (and region by region in parallel processes).
    Returns a stats dict.
    """
    import landscape
    log = log or (lambda msg: None)
    stats = _new_stats()
    boxes = [(it["world_x"], it["world_z"], it["world_x"] + it["structure"].width,
              it["world_z"] + it["structure"].length) for it in placements if it.get("structure") is not None]
    for item in placements:
        if item.get("kind") == "path":
            stats["path"] += paint_path(world, item.get("cells", ()), item.get("block", "minecraft:dirt_path"))
            continue
        if item.get("kind") == "demolish":
            log(f"Demolizione {item.get('name', '')}...")
            stats["demolished"] += demolish(world, item["footprint"])
            continue
        struct = item["structure"]
        ox, oy, oz = item["world_x"], item["y_coord"], item["world_z"]
        log(f"Iniezione {item['name']} a X: {ox}, Y: {oy}, Z: {oz}...")
        terrain = item.get("terrain") or (blend if blend in ("natural", "blend", "none")
                                          else "blend" if blend else "none")
        special = item.get("extend_columns") or item.get("pillars") or item.get("pillar_columns") is not None \
            or not item.get("blend", True)
        site = low = None
        if terrain == "natural" and not special:
            low = landscape.footprint_of(struct)
            if low:
                site = landscape.survey(world, ox, oz, struct, oy, low)
            else:
                terrain = "blend"            # very large structures: the plain earth slope
        base_layer, has_blocks = _inject_structure(world, item, clear_terrain, skip_modded,
                                                   fill_foundations and site is None, stats, log, parallel)
        if site is not None and has_blocks:
            landscape.shape(world, item, site, low, stats, log)
            continue
        if terrain == "blend" and not special \
                and struct.width >= 3 and struct.length >= 3 and has_blocks:
            stats["blend"] += blend_terrain(world, ox, oz, struct.width, struct.length, oy + base_layer - 1,
                                            skip_boxes=boxes)
    return stats


BLEND_MARGIN = 3


def blend_terrain(world, ox, oz, width, length, floor_ground, margin=BLEND_MARGIN, skip_boxes=()):
    """
    Gentle earth slope around a building: natural ground lower than the building's
    ground level is raised gradually over 'margin' blocks. Only adds blocks on natural
    terrain (never digs, never covers water, trees or other constructions).
    Returns the number of blocks added.
    """
    from world_extractor import is_natural_terrain
    added = 0
    for x in range(ox - margin, ox + width + margin):
        for z in range(oz - margin, oz + length + margin):
            if ox <= x < ox + width and oz <= z < oz + length:
                continue
            if any(x1 <= x < x2 and z1 <= z < z2 for x1, z1, x2, z2 in skip_boxes):
                continue            # another structure of the same injection: never refill its digging
            d = max(ox - x, x - (ox + width - 1), oz - z, z - (oz + length - 1))
            top = world.surface_y(x, z)
            if top is None:
                continue
            ground = world.ground_y(x, z, top)
            if ground is None:
                continue
            name = world.get_block_name(x, ground, z) or ""
            if not is_natural_terrain(name) or name.endswith(("water", "lava")):
                continue
            # something non-natural (a building, a path, a fence) stands right above: leave it alone
            above = world.get_block_name(x, ground + 1, z) or "minecraft:air"
            if above not in AIR_NAMES and not is_natural_terrain(above):
                continue
            gap = floor_ground - ground
            if gap <= 0 or gap > MAX_FOUNDATION_GAP:
                continue
            target = ground + int(round(gap * (1 - d / (margin + 1))))
            surf_name, sub_name = surface_fill_blocks(name)
            surf, sub = to_state({"Name": surf_name}), to_state({"Name": sub_name})
            for y in range(ground + 1, target + 1):
                if world.set_block(x, y, z, surf if y == target else sub):
                    added += 1
            if target > ground and name.endswith("grass_block"):
                world.set_block(x, ground, z, sub)  # buried grass becomes dirt
    return added


_PATH_ON = {
    "minecraft:sand": "minecraft:smooth_sandstone", "minecraft:red_sand": "minecraft:smooth_red_sandstone",
    "minecraft:stone": "minecraft:gravel", "minecraft:snow_block": "minecraft:packed_ice",
}


# ---------------------------------------------------------------------------
# Footprint of walls and roads: lets the program demolish or rebuild them later
# ---------------------------------------------------------------------------

def footprint(placements, terrain):
    """
    Columns touched by a group of placements (a wall, a road), with the ground as it was before:
    {"columns": [[x, z, ground, low, high, surface, b_low, ..., b_ground]], "surfaces": [block names]}.
    'surface' is -1 for water, else an index in 'surfaces'; b_low..b_ground are the original blocks
    (indexes in 'surfaces') from the lowest block of the build up to the old ground level. Saved in
    the world registry, so the build can be demolished or edited later restoring the ground exactly.
    """
    cols = {}
    for p in placements:
        s = p.get("structure")
        if s is None:
            continue
        ox, oy, oz = p["world_x"], p["y_coord"], p["world_z"]
        for (bx, by, bz) in s.blocks:
            key = (ox + bx, oz + bz)
            y = oy + by
            lo, hi = cols.get(key, (y, y))
            cols[key] = (min(lo, y), max(hi, y))
    names, index, out = [], {}, []

    def idx(name):
        if name not in index:
            index[name] = len(names)
            names.append(name)
        return index[name]

    original = getattr(terrain, "original_name", None)
    world = getattr(terrain, "world", None)
    for (x, z), (lo, hi) in sorted(cols.items()):
        g = terrain.height(x, z)
        if g is None:
            g = lo - 1
        start = min(lo, g + 1)          # foundations and piers fill from the old ground up
        blocks = []
        for y in range(start, hi + 1):
            name = original(x, y, z) if original else None
            if name is None and world is not None:
                name = world.get_block_name(x, y, z)
            blocks.append(idx(name or "minecraft:stone"))
        if terrain.is_water(x, z):
            surf = -1
        else:
            name = original(x, g, z) if original else None
            if name is None and world is not None:
                name = world.get_block_name(x, g, z)
            surf = idx(name or "minecraft:grass_block")
        out.append([x, z, int(g), int(lo), int(hi), surf, int(start)] + blocks)
    return {"columns": out, "surfaces": names, "v": 2}


def footprint_to_text(fp):
    """Compact form for the world registry (a long wall has thousands of columns)."""
    if not fp:
        return None
    return {"surfaces": fp["surfaces"], "v": fp.get("v", 1),
            "cols": ";".join(",".join(str(v) for v in c) for c in fp["columns"])}


def footprint_from_text(data):
    if not data:
        return {"columns": [], "surfaces": []}
    cols = [[int(v) for v in c.split(",")] for c in data.get("cols", "").split(";") if c]
    return {"columns": cols, "surfaces": list(data.get("surfaces", [])), "v": data.get("v", 1)}


def _column_original(col, version):
    """(first y, [palette index per y]) of the original blocks recorded for a footprint column."""
    x, z, g, lo, hi, surf = col[:6]
    if version >= 2:
        return col[6], col[7:]
    return lo, col[6:]


class RecordedTerrain:
    """
    Terrain for re-planning a wall/road that is already built: inside its footprint the ground and
    the blocks are the ones recorded before it was built (the build itself must not count as ground).
    """

    def __init__(self, base, record):
        self.base = base
        self.world = getattr(base, "world", None)
        self.cols = {}
        self.blocks = {}
        for rec in (record or ()):
            names = rec.get("surfaces", [])
            for col in rec.get("columns", ()):
                x, z, g, lo, hi, surf = col[:6]
                self.cols[(x, z)] = (g, surf)
                start, original = _column_original(col, rec.get("v", 1))
                for i, b in enumerate(original):
                    if 0 <= b < len(names):
                        self.blocks[(x, start + i, z)] = names[b]

    def original_name(self, x, y, z):
        """Block that was there before the old build (None: not recorded, read the world)."""
        if (x, y, z) in self.blocks:
            return self.blocks[(x, y, z)]
        c = self.cols.get((x, z))
        if c is not None and y > c[0]:
            return "minecraft:air"
        return None

    def height(self, x, z):
        c = self.cols.get((x, z))
        return c[0] if c else self.base.height(x, z)

    def is_water(self, x, z):
        c = self.cols.get((x, z))
        return c[1] == -1 if c else self.base.is_water(x, z)

    def is_tree(self, x, z):
        return False if (x, z) in self.cols else self.base.is_tree(x, z)


def demolish(world, footprint_data):
    """
    Removes a wall/road built by the program and puts the ground back as it was: air above the
    old ground, the recorded original blocks below it. Returns the number of blocks changed.
    """
    from world_extractor import is_natural_terrain
    names = footprint_data.get("surfaces", [])
    changed = 0
    states = {}

    def state(name):
        if name not in states:
            props = {"level": "0"} if name.endswith(":water") or name.endswith(":lava") else {}
            states[name] = to_state({"Name": name, "Properties": props})
        return states[name]

    version = footprint_data.get("v", 1)
    for col in footprint_data.get("columns", ()):
        x, z, g, lo, hi, surf = col[:6]
        start, original = _column_original(col, version)
        top_recorded = start + len(original) - 1
        for y in range(max(g + 1, top_recorded + 1), hi + 1):     # (old records: above ground = air)
            name = world.get_block_name(x, y, z)
            if name is not None and name not in AIR_NAMES and world.set_block(x, y, z, AIR_STATE):
                changed += 1
        for i, b in enumerate(original):
            y = start + i
            target = names[b] if 0 <= b < len(names) else None
            name = world.get_block_name(x, y, z)
            if target is None or name is None or name == target:
                continue
            if target in AIR_NAMES:
                if world.set_block(x, y, z, AIR_STATE):
                    changed += 1
                continue
            if world.set_block(x, y, z, state(target)):
                changed += 1
        if surf == -1:
            # piles and piers that went down to the bottom of the water
            water = state("minecraft:water")
            for y in range(min(start - 1, g), min(lo, g) - MAX_PILLAR_DEPTH, -1):
                name = world.get_block_name(x, y, z)
                if name is None or name in AIR_NAMES or name.endswith("water") or is_natural_terrain(name):
                    break
                if world.set_block(x, y, z, water):
                    changed += 1
    return changed


def paint_path(world, cells, block="minecraft:dirt_path"):
    """Turns the ground of each (x, z) cell into a path that follows the terrain. Returns blocks set."""
    count = 0
    for x, z in cells:
        top = world.surface_y(x, z)
        if top is None:
            continue
        ground = world.ground_y(x, z, top)
        if ground is None:
            continue
        current = world.get_block_name(x, ground, z) or ""
        if "water" in current or "lava" in current:
            continue
        material = _PATH_ON.get(current, block) if block == "minecraft:dirt_path" else block
        if world.set_block(x, ground, z, to_state({"Name": material})):
            count += 1
        for y in (ground + 1, ground + 2):
            above = world.get_block_name(x, y, z)
            if above and above not in AIR_NAMES and not is_ground(above):
                world.set_block(x, y, z, AIR_STATE)
    return count
