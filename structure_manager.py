import os
from nbt_codec import load_nbt, TAG_Compound, TAG_List, TAG_Int

class Structure:
    def __init__(self, width=0, height=0, length=0, blocks=None):
        self.width = width      # X
        self.height = height    # Y
        self.length = length    # Z
        self.blocks = blocks or {}  # Maps (x, y, z) -> {"Name": name, "Properties": props}

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
            
        return Structure(new_w, new_h, new_l, new_blocks)

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
        """Loads native Minecraft Structure NBT format."""
        tag, _ = load_nbt(file_path)
        if not tag:
            raise ValueError("Empty or invalid NBT file")
            
        # Parse size [X, Y, Z]
        size_list = tag.get("size", [])
        if len(size_list) < 3:
            raise ValueError("Structure NBT is missing 'size' tag")
            
        w, h, l = int(size_list[0]), int(size_list[1]), int(size_list[2])
        
        # Parse palette
        palette = tag.get("palette", [])
        
        # Parse blocks
        blocks_list = tag.get("blocks", [])
        blocks = {}
        
        for b in blocks_list:
            pos = b.get("pos", [])
            state_idx = int(b.get("state", 0))
            if len(pos) < 3:
                continue
                
            bx, by, bz = int(pos[0]), int(pos[1]), int(pos[2])
            
            if state_idx < len(palette):
                state = palette[state_idx]
                name = state.get("Name", "minecraft:air")
                props = state.get("Properties", {})
                
                # Copy properties safely
                properties = {}
                for k, v in props.items():
                    properties[k] = str(v)
                    
                blocks[(bx, by, bz)] = {
                    "Name": name,
                    "Properties": properties
                }
                
        return cls(w, h, l, blocks)

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
                                
        return cls(w, h, l, blocks)

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
                            
        return cls(w, h, l, blocks)


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


def rotate_properties(properties, angle):
    new_props = dict(properties)
    steps = angle // 90
    
    facing_rotations_cw = {
        "north": "east",
        "east": "south",
        "south": "west",
        "west": "north"
    }
    
    if "facing" in new_props:
        val = new_props["facing"]
        # Rotate 'facing' for block states
        for _ in range(steps):
            val = facing_rotations_cw.get(val, val)
        new_props["facing"] = val
        
    if "axis" in new_props and steps % 2 == 1:
        val = new_props["axis"]
        if val == "x":
            new_props["axis"] = "z"
        elif val == "z":
            new_props["axis"] = "x"
            
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
