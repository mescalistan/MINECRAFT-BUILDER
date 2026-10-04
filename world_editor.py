"""
World-level block editing across multiple region files, plus the structure
injection routine used by the GUI worker thread.
"""
import os

from nbt_codec import TAG_Compound, TAG_String
from mca_codec import (
    MCARegion, ChunkEditor, AIR_NAMES, block_key, chunk_is_full, read_world_surface,
    chunk_format_supported,
)

AIR_STATE = TAG_Compound({"Name": TAG_String("minecraft:air")})

# Blocks skipped while looking for the ground under a structure
_NON_GROUND_HINTS = (
    "water", "lava", "leaves", "short_grass", "tall_grass", "fern", "flower", "poppy",
    "dandelion", "tulip", "orchid", "allium", "bluet", "daisy", "cornflower", "lily",
    "sapling", "bush", "vine", "torch", "snow", "seagrass", "kelp", "sugar_cane",
    "mushroom", "sweet_berry", "dripleaf", "azalea", "moss_carpet", "carpet",
)


MAX_FOUNDATION_GAP = 10   # blocks of empty space filled under a structure
MAX_PILLAR_DEPTH = 96     # bridge piers / towers reach the ground up to this depth


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


class World:
    """Global-coordinate access to the regions of one dimension."""

    def __init__(self, region_dir, preloaded=None):
        self.region_dir = region_dir
        self._regions = {}   # (rx, rz) -> MCARegion | None
        self._editors = {}   # (chunk_x, chunk_z) -> ChunkEditor | None
        self.skipped_chunks = {}  # (chunk_x, chunk_z) -> reason
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
        result = []
        for (cx, cz), editor in self._editors.items():
            if editor is not None and editor.dirty:
                region = self.region(cx >> 5, cz >> 5)
                if region not in result:
                    result.append(region)
        return result

    def save(self, backup=True, log=None):
        """Flushes edited chunks and writes every modified region. Returns backup paths."""
        backups = []
        regions = self.modified_regions()
        for region in regions:
            if backup:
                path = region.create_backup()
                if path:
                    backups.append(path)
                    if log:
                        log(f"Backup creato: {os.path.basename(path)}")
        for (cx, cz), editor in self._editors.items():
            if editor is not None and editor.flush():
                self.region(cx >> 5, cz >> 5).mark_dirty((cx & 31, cz & 31))
        for region in regions:
            if log:
                log(f"Scrittura {os.path.basename(region.file_path)} ({len(region.dirty)} chunk modificati)...")
            region.save()
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


def inject_structures(world, placements, fill_foundations=True, clear_terrain=True,
                      skip_modded=True, log=None, blend=False):
    """
    Places the structures in the world (in memory). Call world.save() afterwards.
    Each placement: {"structure", "world_x", "world_z", "y_coord", "name"}.
    Returns a stats dict.
    """
    log = log or (lambda msg: None)
    stats = {"placed": 0, "cleared": 0, "foundation": 0, "skipped_missing": 0,
             "skipped_modded": 0, "skipped_height": 0, "destroyed": 0, "blend": 0}

    stats["path"] = 0
    for item in placements:
        if item.get("kind") == "path":
            stats["path"] += paint_path(world, item.get("cells", ()), item.get("block", "minecraft:dirt_path"))
            continue
        struct = item["structure"]
        ox, oy, oz = item["world_x"], item["y_coord"], item["world_z"]
        log(f"Iniezione {item['name']} a X: {ox}, Y: {oy}, Z: {oz}...")

        # Lowest solid block of each column and of the whole structure
        columns_bottom = {}
        for (bx, by, bz), block in struct.blocks.items():
            if block.get("Name", "minecraft:air") not in AIR_NAMES:
                if by < columns_bottom.get((bx, bz), 1 << 30):
                    columns_bottom[(bx, bz)] = by
        base_layer = min(columns_bottom.values()) if columns_bottom else 0

        # Foundations first: the ground scan must see the terrain before the structure is placed
        foundation_cols = []
        if fill_foundations:
            for (bx, bz), by in columns_bottom.items():
                # Only columns resting on the structure's lowest layer: arches, bridges
                # and overhangs keep the empty space below them.
                pillar_cols = item.get("pillar_columns")
                if pillar_cols is not None:
                    if (bx, bz) not in pillar_cols:
                        continue  # e.g. under the arches of a bridge
                elif by != base_layer and not item.get("pillars"):
                    continue
                gx, gz = ox + bx, oz + bz
                base_y = oy + by
                ground = world.ground_y(gx, gz, base_y - 1)
                if ground is None or ground >= base_y - 1:
                    continue
                pillars = item.get("extend_columns") or item.get("pillars") or pillar_cols is not None
                # A big gap means the structure floats on purpose (sky builds, high placements):
                # only small gaps are filled. Structures resting on water (boats, docks) are not
                # propped up either; bridge piers always go down to the bottom.
                if base_y - 1 - ground > (MAX_PILLAR_DEPTH if pillars else MAX_FOUNDATION_GAP):
                    continue
                below = world.get_block_name(gx, base_y - 1, gz) or ""
                if not pillars and ("water" in below or "lava" in below):
                    continue
                if pillars:
                    # Bridges and towers: the pillar itself continues down to the ground
                    bottom = struct.blocks[(bx, by, bz)]
                    fill = (bottom, bottom)
                else:
                    surface = world.get_block_name(gx, ground, gz) or "minecraft:grass_block"
                    fill = tuple({"Name": n} for n in surface_fill_blocks(surface))
                foundation_cols.append((gx, gz, ground, base_y, fill))

        state_cache = {}
        for (bx, by, bz), block in struct.blocks.items():
            name = block.get("Name", "minecraft:air")
            gx, gy, gz = ox + bx, oy + by, oz + bz
            if name in AIR_NAMES:
                if not clear_terrain:
                    continue
                current = world.get_block_name(gx, gy, gz)
                if current is None or current in AIR_NAMES:
                    continue
                if world.set_block(gx, gy, gz, AIR_STATE):
                    stats["cleared"] += 1
                    if not current.endswith(("water", "lava")):
                        stats["destroyed"] += 1
                continue
            if skip_modded and not name.startswith("minecraft:"):
                stats["skipped_modded"] += 1
                continue
            editor = world.editor(gx >> 4, gz >> 4)
            version = editor.data_version if editor is not None else 0
            bk = (block_key(block), version)
            cached = state_cache.get(bk)
            if cached is None:
                state = to_state(upgrade_block(block, version))
                cached = state_cache[bk] = (state, block_key(state))
            state, state_key = cached
            if editor is None:
                stats["skipped_missing"] += 1
                continue
            current = editor.get_block(gx & 15, gy, gz & 15)
            current_name = str(current.get("Name", "minecraft:air")) if current is not None else "minecraft:air"
            if world.set_block(gx, gy, gz, state, state_key):
                stats["placed"] += 1
                if current_name not in AIR_NAMES and not current_name.endswith(("water", "lava"))                         and current_name != state["Name"]:
                    stats["destroyed"] += 1
            else:
                stats["skipped_height"] += 1

        for gx, gz, ground, base_y, (surf_block, sub_block) in foundation_cols:
            surf, sub = to_state(surf_block), to_state(sub_block)
            for y in range(ground + 1, base_y):
                if world.set_block(gx, y, gz, surf if y == base_y - 1 else sub):
                    stats["foundation"] += 1

        if blend and item.get("blend", True) and not item.get("extend_columns")                 and struct.width >= 3 and struct.length >= 3 and columns_bottom:
            stats["blend"] += blend_terrain(world, ox, oz, struct.width, struct.length, oy + base_layer - 1)

    return stats


BLEND_MARGIN = 3


def blend_terrain(world, ox, oz, width, length, floor_ground, margin=BLEND_MARGIN):
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
