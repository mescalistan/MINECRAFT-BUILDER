import os
from nbt_codec import load_nbt

# DataVersion of 1.13 ("The Flattening"): older files use block names that no longer exist
DATA_VERSION_FLATTENING = 1451


class Structure:
    def __init__(self, width=0, height=0, length=0, blocks=None, data_version=None):
        self.width = width      # X
        self.height = height    # Y
        self.length = length    # Z
        self.blocks = blocks or {}  # Maps (x, y, z) -> {"Name": name, "Properties": props}
        self.data_version = data_version
        # Layers of the structure below the original ground (cut areas with basements)
        self.ground_offset = 0

    def modded_blocks(self):
        """Counts blocks that do not belong to the minecraft: namespace, per namespace."""
        counts = {}
        for block in self.blocks.values():
            name = block.get("Name", "minecraft:air")
            ns = name.split(":", 1)[0] if ":" in name else "minecraft"
            if ns != "minecraft":
                counts[ns] = counts.get(ns, 0) + 1
        return counts

    def is_pre_flattening(self):
        return self.data_version is not None and self.data_version < DATA_VERSION_FLATTENING

    def get_block(self, x, y, z):
        return self.blocks.get((x, y, z), {"Name": "minecraft:air", "Properties": {}})

    def rotate(self, angle):
        """
        Rotate the structure clockwise by 90, 180, or 270 degrees.
        Returns a new Structure object.
        """
        if angle not in (90, 180, 270):
            return self  # Return self for 0 or invalid angle
            
        new_blocks = {}
        steps = angle // 90
        
        # Determine new dimensions
        if steps % 2 == 1:
            new_w = self.length
            new_l = self.width
        else:
            new_w = self.width
            new_l = self.length
            
        new_h = self.height

        for (x, y, z), block in self.blocks.items():
            # Apply coordinate rotation step-by-step
            rx, rz = x, z
            w, l = self.width, self.length
            for _ in range(steps):
                # 90 degrees clockwise rotation:
                # new_x = length - 1 - old_z
                # new_z = old_x
                rx, rz = l - 1 - rz, rx
                w, l = l, w  # Dimensions swap
                
            # Rotate properties
            props = block.get("Properties", {})
            if props:
                rotated_props = rotate_properties(props, angle)
            else:
                rotated_props = {}
                
            new_blocks[(rx, y, rz)] = {
                "Name": block["Name"],
                "Properties": rotated_props
            }
            
        rotated = Structure(new_w, new_h, new_l, new_blocks, self.data_version)
        rotated.ground_offset = self.ground_offset
        for attr in ("bridge",):
            if hasattr(self, attr):
                setattr(rotated, attr, dict(getattr(self, attr)))
        return rotated

    @classmethod
    def load(cls, file_path):
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Structure file not found: {file_path}")
            
        ext = os.path.splitext(file_path)[1].lower()
        if ext == '.nbt':
            return cls._load_nbt(file_path)
        elif ext in ('.schem', '.schematic'):
            return cls._load_schem(file_path)
        else:
            raise ValueError(f"Unsupported structure format: {ext}")

    @classmethod
    def _load_nbt(cls, file_path):
        """Loads native Minecraft Structure NBT format (fast path, fine for millions of blocks)."""
        from nbt_codec import parse_structure_bytes, _maybe_decompress
        with open(file_path, "rb") as f:
            tag, block_list = parse_structure_bytes(_maybe_decompress(f.read()))
        if not tag:
            raise ValueError("Empty or invalid NBT file")
        size_list = tag.get("size", [])
        if len(size_list) < 3:
            raise ValueError("Structure NBT is missing 'size' tag")
        w, h, l = int(size_list[0]), int(size_list[1]), int(size_list[2])

        # One shared dict per palette entry: identical blocks share the same object
        states = []
        for state in tag.get("palette", []):
            props = state.get("Properties", {})
            states.append({"Name": str(state.get("Name", "minecraft:air")),
                           "Properties": {k: str(v) for k, v in props.items()}})
        blocks = {}
        n = len(states)
        for x, y, z, idx in block_list or ():
            if 0 <= idx < n:
                blocks[(x, y, z)] = states[idx]

        dv = tag.get("DataVersion")
        struct = cls(w, h, l, blocks, int(dv) if dv is not None else None)
        meta = tag.get("MinecraftBuilder") or {}
        struct.ground_offset = int(meta.get("groundOffset", 0))
        return struct

    @classmethod
    def _load_schem(cls, file_path):
        """Loads Sponge Schematic format (.schem)."""
        tag, _ = load_nbt(file_path)
        if not tag:
            raise ValueError("Empty or invalid Schematic NBT file")
            
        # Sponge schematic has Width, Height, Length as Short tags
        w = int(tag.get("Width", 0))
        h = int(tag.get("Height", 0))
        l = int(tag.get("Length", 0))
        
        # Palette: dictionary of string -> int ID
        raw_palette = tag.get("Palette", {})
        palette = {}
        for bs_str, val in raw_palette.items():
            palette[int(val)] = parse_block_state_str(bs_str)
            
        # BlockData: byte array (contains VarInts)
        block_data = tag.get("BlockData", b"")
        if not block_data:
            # Check for MCEdit schematic format (.schematic)
            # MCEdit schematic has "Blocks" and "Data" byte arrays
            if "Blocks" in tag:
                return cls._load_mcedit_schematic(tag)
            raise ValueError("No block data found in schematic")
            
        # Unpack VarInts from BlockData
        indices = []
        offset = 0
        while offset < len(block_data):
            val, offset = read_varint(block_data, offset)
            indices.append(val)
            
        blocks = {}
        for y in range(h):
            for z in range(l):
                for x in range(w):
                    idx = (y * l + z) * w + x
                    if idx < len(indices):
                        state_idx = indices[idx]
                        if state_idx in palette:
                            block = palette[state_idx]
                            if block["Name"] != "minecraft:air":
                                blocks[(x, y, z)] = block

        dv = tag.get("DataVersion")
        return cls(w, h, l, blocks, int(dv) if dv is not None else None)

    @classmethod
    def _load_mcedit_schematic(cls, tag):
        """Loads older MCEdit Schematic format (.schematic)."""
        w = int(tag.get("Width", 0))
        h = int(tag.get("Height", 0))
        l = int(tag.get("Length", 0))
        
        blocks_array = tag.get("Blocks", b"")
        data_array = tag.get("Data", b"")
        
        # Add support for AddBlocks if present (for ID > 255)
        add_blocks = tag.get("AddBlocks", b"")
        
        blocks = {}
        # MCEdit schematic index = (y * Length + z) * Width + x
        for y in range(h):
            for z in range(l):
                for x in range(w):
                    idx = (y * l + z) * w + x
                    if idx < len(blocks_array):
                        block_id = blocks_array[idx]
                        # Merge AddBlocks if available
                        if add_blocks:
                            add_idx = idx // 2
                            add_val = add_blocks[add_idx]
                            if idx % 2 == 0:
                                block_id |= (add_val & 0x0F) << 8
                            else:
                                block_id |= (add_val & 0xF0) << 4
                                
                        block_data = data_array[idx] if idx < len(data_array) else 0
                        
                        # Map older block IDs to Minecraft 1.13+ block names (basic mapping)
                        block_name = legacy_block_id_to_name(block_id, block_data)
                        if block_name != "minecraft:air":
                            blocks[(x, y, z)] = {
                                "Name": block_name,
                                "Properties": {}
                            }
                            
        # Legacy numeric IDs are already converted to modern names above
        return cls(w, h, l, blocks, data_version=None)


def read_varint(data, offset):
    value = 0
    sec = 0
    while True:
        byte = data[offset]
        offset += 1
        value |= (byte & 0x7F) << sec
        if (byte & 0x80) == 0:
            break
        sec += 7
    return value, offset


def parse_block_state_str(bs_str):
    if '[' in bs_str and bs_str.endswith(']'):
        idx = bs_str.index('[')
        name = bs_str[:idx]
        prop_str = bs_str[idx+1:-1]
        properties = {}
        for part in prop_str.split(','):
            if '=' in part:
                k, v = part.split('=', 1)
                properties[k] = v
        # Ensure name starts with minecraft:
        if not name.startswith("minecraft:"):
            name = "minecraft:" + name
        return {"Name": name, "Properties": properties}
    else:
        name = bs_str
        if not name.startswith("minecraft:"):
            name = "minecraft:" + name
        return {"Name": name, "Properties": {}}


_CW = {"north": "east", "east": "south", "south": "west", "west": "north"}

# Rail shapes after one clockwise step
_RAIL_CW = {
    "north_south": "east_west", "east_west": "north_south",
    "ascending_north": "ascending_east", "ascending_east": "ascending_south",
    "ascending_south": "ascending_west", "ascending_west": "ascending_north",
    "north_east": "south_east", "south_east": "south_west",
    "south_west": "north_west", "north_west": "north_east",
}


def _rotate_dir(val, steps):
    for _ in range(steps):
        val = _CW.get(val, val)
    return val


def rotate_properties(properties, angle):
    """Rotates block state properties clockwise by 90/180/270 degrees."""
    steps = (angle // 90) % 4
    new_props = dict(properties)
    if steps == 0 or not properties:
        return new_props

    # facing (up/down are unchanged)
    if "facing" in new_props:
        new_props["facing"] = _rotate_dir(new_props["facing"], steps)

    # Connection properties of fences, panes, walls, vines, redstone wire,
    # mushroom blocks, glow lichen...: move each value to the rotated side
    sides = [d for d in ("north", "east", "south", "west") if d in properties]
    for d in sides:
        new_props.pop(d)
    for d in sides:
        new_props[_rotate_dir(d, steps)] = properties[d]

    if "axis" in new_props and steps % 2 == 1:
        new_props["axis"] = {"x": "z", "z": "x"}.get(new_props["axis"], new_props["axis"])

    # Signs, banners, heads: 16 rotation steps, 4 per quarter turn
    if "rotation" in new_props:
        try:
            new_props["rotation"] = str((int(new_props["rotation"]) + 4 * steps) % 16)
        except ValueError:
            pass

    # Rails (stairs shapes like inner_left are relative to facing and stay unchanged)
    if new_props.get("shape") in _RAIL_CW:
        val = new_props["shape"]
        for _ in range(steps):
            val = _RAIL_CW[val]
        new_props["shape"] = val

    # Jigsaw / crafter orientation, e.g. "north_up" or "up_east"
    if "orientation" in new_props:
        parts = new_props["orientation"].split("_")
        new_props["orientation"] = "_".join(_rotate_dir(p, steps) for p in parts)

    return new_props


def legacy_block_id_to_name(block_id, data):
    # A basic fallback mapping for common block IDs
    mapping = {
        0: "minecraft:air",
        1: "minecraft:stone",
        2: "minecraft:grass_block",
        3: "minecraft:dirt",
        4: "minecraft:cobblestone",
        5: "minecraft:oak_planks",
        6: "minecraft:oak_sapling",
        7: "minecraft:bedrock",
        8: "minecraft:water",
        9: "minecraft:water",
        10: "minecraft:lava",
        11: "minecraft:lava",
        12: "minecraft:sand",
        13: "minecraft:gravel",
        14: "minecraft:gold_ore",
        15: "minecraft:iron_ore",
        16: "minecraft:coal_ore",
        17: "minecraft:oak_log",
        18: "minecraft:oak_leaves",
        19: "minecraft:sponge",
        20: "minecraft:glass",
        35: "minecraft:white_wool",
        41: "minecraft:gold_block",
        42: "minecraft:iron_block",
        43: "minecraft:stone_slab",
        45: "minecraft:bricks",
        46: "minecraft:tnt",
        47: "minecraft:bookshelf",
        48: "minecraft:mossy_cobblestone",
        49: "minecraft:obsidian",
        50: "minecraft:torch",
        54: "minecraft:chest",
        56: "minecraft:diamond_ore",
        57: "minecraft:diamond_block",
        58: "minecraft:crafting_table",
        59: "minecraft:wheat",
        60: "minecraft:farmland",
        61: "minecraft:furnace",
        64: "minecraft:oak_door",
        81: "minecraft:cactus",
        82: "minecraft:clay",
        83: "minecraft:sugar_cane",
        85: "minecraft:oak_fence",
        89: "minecraft:glowstone",
        98: "minecraft:stone_bricks",
        138: "minecraft:beacon",
    }
    
    # Custom block mapping for specific sub-types
    if block_id == 5: # Planks
        plank_types = {0: "minecraft:oak_planks", 1: "minecraft:spruce_planks", 2: "minecraft:birch_planks", 3: "minecraft:jungle_planks", 4: "minecraft:acacia_planks", 5: "minecraft:dark_oak_planks"}
        return plank_types.get(data, "minecraft:oak_planks")
    elif block_id == 17: # Wood Logs
        log_types = {0: "minecraft:oak_log", 1: "minecraft:spruce_log", 2: "minecraft:birch_log", 3: "minecraft:jungle_log"}
        return log_types.get(data & 3, "minecraft:oak_log")
        
    return mapping.get(block_id, "minecraft:stone")
