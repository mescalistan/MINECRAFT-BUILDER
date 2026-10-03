import os
import struct
import zlib
import time
import io
from nbt_codec import load_nbt, save_nbt, TAG_Compound, TAG_List, TAG_Byte, TAG_Long, TAG_Long_Array, TAG_Byte_Array, to_nbt

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

        self.chunks = {}  # Maps (cx, cz) -> (decompressed_nbt, timestamp)
        self.offsets = [0] * 1024
        self.timestamps = [0] * 1024
        self.load()

    def load(self):
        if not os.path.exists(self.file_path):
            return
        
        with open(self.file_path, 'rb') as f:
            offset_data = f.read(4096)
            timestamp_data = f.read(4096)
            
            if len(offset_data) < 4096 or len(timestamp_data) < 4096:
                return

            for i in range(1024):
                self.offsets[i] = struct.unpack('>I', offset_data[i*4 : i*4+4])[0]
                self.timestamps[i] = struct.unpack('>I', timestamp_data[i*4 : i*4+4])[0]

            for cz in range(32):
                for cx in range(32):
                    idx = cx + cz * 32
                    offset_val = self.offsets[idx]
                    if offset_val == 0:
                        continue
                    
                    sector_offset = offset_val >> 8
                    sector_count = offset_val & 0xFF
                    
                    f.seek(sector_offset * 4096)
                    chunk_header = f.read(5)
                    if len(chunk_header) < 5:
                        continue
                    
                    length, compression = struct.unpack('>IB', chunk_header)
                    if length == 0:
                        continue
                    
                    chunk_bytes = f.read(length - 1)
                    
                    try:
                        if compression == 1:
                            decompressed = gzip_decompress(chunk_bytes)
                        elif compression == 2:
                            decompressed = zlib.decompress(chunk_bytes)
                        elif compression == 3:
                            decompressed = chunk_bytes
                        else:
                            continue
                        
                        stream = io.BytesIO(decompressed)
                        nbt_data, _ = load_nbt(stream)
                        self.chunks[(cx, cz)] = (nbt_data, self.timestamps[idx])
                    except Exception as e:
                        print(f"Error reading chunk ({cx}, {cz}) in {self.file_path}: {e}")

    def create_backup(self):
        if os.path.exists(self.file_path):
            backup_dir = os.path.join(os.path.dirname(self.file_path), 'backups')
            os.makedirs(backup_dir, exist_ok=True)
            import shutil
            filename = os.path.basename(self.file_path)
            ts = int(time.time())
            backup_path = os.path.join(backup_dir, f"{filename}.{ts}.bak")
            shutil.copy2(self.file_path, backup_path)
            return backup_path
        return None

    def save(self, dest_path=None):
        if dest_path is None:
            dest_path = self.file_path
            
        os.makedirs(os.path.dirname(os.path.abspath(dest_path)), exist_ok=True)
        
        compressed_chunks = {}
        for (cx, cz), (nbt_data, ts) in self.chunks.items():
            stream = io.BytesIO()
            save_nbt(nbt_data, "", stream, compressed=False)
            uncompressed_bytes = stream.getvalue()
            compressed_bytes = zlib.compress(uncompressed_bytes)
            compressed_chunks[(cx, cz)] = (compressed_bytes, ts)

        current_sector = 2
        chunk_data_blocks = []
        
        new_offsets = [0] * 1024
        new_timestamps = [0] * 1024
        
        for cz in range(32):
            for cx in range(32):
                idx = cx + cz * 32
                if (cx, cz) not in compressed_chunks:
                    new_offsets[idx] = 0
                    new_timestamps[idx] = self.timestamps[idx]
                    continue
                
                compressed_bytes, ts = compressed_chunks[(cx, cz)]
                chunk_len = len(compressed_bytes) + 1
                header = struct.pack('>IB', chunk_len, 2)
                full_chunk_data = header + compressed_bytes
                
                padding_len = (4096 - (len(full_chunk_data) % 4096)) % 4096
                padded_data = full_chunk_data + b'\x00' * padding_len
                sectors_used = len(padded_data) // 4096
                
                new_offsets[idx] = (current_sector << 8) | (sectors_used & 0xFF)
                new_timestamps[idx] = ts or int(time.time())
                
                chunk_data_blocks.append(padded_data)
                current_sector += sectors_used

        with open(dest_path, 'wb') as f:
            for offset in new_offsets:
                f.write(struct.pack('>I', offset))
            for ts in new_timestamps:
                f.write(struct.pack('>I', ts))
            for block in chunk_data_blocks:
                f.write(block)


def gzip_decompress(data):
    import gzip
    with gzip.GzipFile(fileobj=io.BytesIO(data)) as f:
        return f.read()


def unpack_section(section_nbt):
    blocks = [TAG_Compound({"Name": "minecraft:air"}) for _ in range(4096)]
    if "block_states" not in section_nbt:
        return blocks
    
    bs = section_nbt["block_states"]
    if "palette" not in bs:
        return blocks
        
    palette = bs["palette"]
    if "data" not in bs:
        # If there is no data array, the entire section is filled with the single block in the palette
        if len(palette) > 0:
            single_block = palette[0]
            blocks = [single_block for _ in range(4096)]
        return blocks

    data = bs["data"]
    # Calculate bits needed per block index
    B = max(4, (len(palette) - 1).bit_length())
    V = 64 // B  # blocks per long
    
    for index in range(4096):
        long_idx = index // V
        if long_idx >= len(data):
            continue
        
        bit_offset = (index % V) * B
        long_val = data[long_idx]
        
        # Convert signed long to unsigned
        u_val = long_val & 0xFFFFFFFFFFFFFFFF
        palette_idx = (u_val >> bit_offset) & ((1 << B) - 1)
        
        if palette_idx < len(palette):
            blocks[index] = palette[palette_idx]
            
    return blocks


def pack_section(section_nbt, blocks):
    # Ensure blocks contains 4096 items
    assert len(blocks) == 4096
    
    # Build unique palette
    palette = []
    seen = {}
    
    # We want to make sure minecraft:air is at index 0 if it is present
    has_air = False
    air_block = None
    for b in blocks:
        name = b.get("Name", "minecraft:air")
        if name == "minecraft:air":
            has_air = True
            air_block = b
            break
            
    if has_air and air_block:
        palette.append(air_block)
        # Serialize block key
        seen[block_key(air_block)] = 0

    for b in blocks:
        key = block_key(b)
        if key not in seen:
            seen[key] = len(palette)
            palette.append(b)
            
    # Modify block_states in section
    if "block_states" not in section_nbt:
        section_nbt["block_states"] = TAG_Compound()
        
    bs = section_nbt["block_states"]
    bs["palette"] = TAG_List(10, palette)
    
    if len(palette) <= 1:
        # No data array needed, entire section is this block
        if "data" in bs:
            del bs["data"]
        return

    B = max(4, (len(palette) - 1).bit_length())
    V = 64 // B
    L = (4096 + V - 1) // V
    
    longs = [0] * L
    for index in range(4096):
        b = blocks[index]
        p_idx = seen[block_key(b)]
        long_idx = index // V
        bit_offset = (index % V) * B
        longs[long_idx] |= (p_idx << bit_offset)
        
    # Convert unsigned to signed 64-bit long
    signed_longs = []
    for val in longs:
        if val >= 2**63:
            val -= 2**64
        signed_longs.append(val)
        
    bs["data"] = TAG_Long_Array(signed_longs)


def block_key(b):
    name = b.get("Name", "minecraft:air")
    properties = b.get("Properties", {})
    prop_tuple = tuple(sorted((k, str(v)) for k, v in properties.items()))
    return (name, prop_tuple)


def set_block(chunk_nbt, x, y, z, block_state):
    # Local coordinates: 0<=x<=15, 0<=z<=15, -64<=y<=319
    if "sections" not in chunk_nbt:
        chunk_nbt["sections"] = TAG_List(10)
        
    sections = chunk_nbt["sections"]
    sy = y // 16
    bx = x
    by = y % 16
    bz = z
    
    target_section = None
    for sec in sections:
        if sec.get("Y") == sy:
            target_section = sec
            break
            
    if target_section is None:
        target_section = TAG_Compound()
        target_section["Y"] = TAG_Byte(sy)
        target_section["block_states"] = TAG_Compound()
        sections.append(target_section)
        
    blocks = unpack_section(target_section)
    idx = by * 256 + bz * 16 + bx
    blocks[idx] = block_state
    pack_section(target_section, blocks)


def recalculate_heightmaps(chunk_nbt):
    sections = chunk_nbt.get("sections", [])
    unpacked_sections = {}
    min_y = -64
    max_y = 319
    
    for sec in sections:
        sy = int(sec.get("Y", 0))
        unpacked_sections[sy] = unpack_section(sec)
        
    heights = [0] * 256
    for z in range(16):
        for x in range(16):
            col_height = min_y
            found = False
            for y in range(max_y, min_y - 1, -1):
                sy = y // 16
                by = y % 16
                if sy in unpacked_sections:
                    idx = by * 256 + z * 16 + x
                    block = unpacked_sections[sy][idx]
                    name = block.get("Name", "minecraft:air")
                    if name != "minecraft:air":
                        col_height = y
                        found = True
                        break
            if found:
                heights[z * 16 + x] = col_height - min_y + 1
            else:
                heights[z * 16 + x] = 0

    B = 9
    V = 7
    longs = [0] * 37
    for index in range(256):
        val = heights[index]
        long_idx = index // V
        bit_offset = (index % V) * B
        longs[long_idx] |= (val << bit_offset)
        
    signed_longs = []
    for l in longs:
        if l >= 2**63:
            l -= 2**64
        signed_longs.append(l)
        
    if "Heightmaps" not in chunk_nbt:
        chunk_nbt["Heightmaps"] = TAG_Compound()
        
    hm = chunk_nbt["Heightmaps"]
    hm["WORLD_SURFACE"] = TAG_Long_Array(signed_longs)
    hm["MOTION_BLOCKING"] = TAG_Long_Array(signed_longs)
