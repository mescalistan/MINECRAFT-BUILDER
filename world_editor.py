"""
World-level block editing across multiple region files, plus the structure
injection routine used by the GUI worker thread.
"""
import os

from nbt_codec import TAG_Compound, TAG_String
from mca_codec import (
    MCARegion, ChunkEditor, AIR_NAMES, block_key, chunk_is_full,
    chunk_format_supported, UnsupportedChunkFormat,
)

AIR_STATE = TAG_Compound({"Name": TAG_String("minecraft:air")})

# Blocks skipped while looking for the ground under a structure
_NON_GROUND_HINTS = (
    "water", "lava", "leaves", "short_grass", "tall_grass", "fern", "flower", "poppy",
    "dandelion", "tulip", "orchid", "allium", "bluet", "daisy", "cornflower", "lily",
    "sapling", "bush", "vine", "torch", "snow", "seagrass", "kelp", "sugar_cane",
    "mushroom", "sweet_berry", "dripleaf", "azalea", "moss_carpet", "carpet",
)


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
                raise UnsupportedChunkFormat(
                    "Il mondo usa un formato precedente alla 1.18: aprilo e salvalo con una versione recente di Minecraft."
                )
            elif not chunk_is_full(entry[0]):
                self.skipped_chunks[key] = "chunk generato solo in parte"
            else:
                editor = ChunkEditor(entry[0], chunk_x, chunk_z)
        self._editors[key] = editor
        return editor

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


def inject_structures(world, placements, fill_foundations=True, clear_terrain=True,
                      skip_modded=True, log=None):
    """
    Places the structures in the world (in memory). Call world.save() afterwards.
    Each placement: {"structure", "world_x", "world_z", "y_coord", "name"}.
    Returns a stats dict.
    """
    log = log or (lambda msg: None)
    stats = {"placed": 0, "cleared": 0, "foundation": 0, "skipped_missing": 0,
             "skipped_modded": 0, "skipped_height": 0}

    for item in placements:
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
                if by != base_layer:
                    continue
                gx, gz = ox + bx, oz + bz
                base_y = oy + by
                ground = world.ground_y(gx, gz, base_y - 1)
                if ground is None or ground >= base_y - 1:
                    continue
                surface = world.get_block_name(gx, ground, gz) or "minecraft:grass_block"
                foundation_cols.append((gx, gz, ground, base_y, surface_fill_blocks(surface)))

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
                continue
            if skip_modded and not name.startswith("minecraft:"):
                stats["skipped_modded"] += 1
                continue
            bk = block_key(block)
            state = state_cache.get(bk)
            if state is None:
                state = state_cache[bk] = to_state(block)
            if world.editor(gx >> 4, gz >> 4) is None:
                stats["skipped_missing"] += 1
            elif world.set_block(gx, gy, gz, state, bk):
                stats["placed"] += 1
            else:
                stats["skipped_height"] += 1

        for gx, gz, ground, base_y, (surf_name, sub_name) in foundation_cols:
            surf = TAG_Compound({"Name": TAG_String(surf_name)})
            sub = TAG_Compound({"Name": TAG_String(sub_name)})
            for y in range(ground + 1, base_y):
                if world.set_block(gx, y, gz, surf if y == base_y - 1 else sub):
                    stats["foundation"] += 1

    return stats
