import struct
import gzip
import zlib

class TAG_Byte(int):
    tag_type = 1
    def __new__(cls, val):
        return super().__new__(cls, int(val))

class TAG_Short(int):
    tag_type = 2
    def __new__(cls, val):
        return super().__new__(cls, int(val))

class TAG_Int(int):
    tag_type = 3
    def __new__(cls, val):
        return super().__new__(cls, int(val))

class TAG_Long(int):
    tag_type = 4
    def __new__(cls, val):
        return super().__new__(cls, int(val))

class TAG_Float(float):
    tag_type = 5
    def __new__(cls, val):
        return super().__new__(cls, float(val))

class TAG_Double(float):
    tag_type = 6
    def __new__(cls, val):
        return super().__new__(cls, float(val))

class TAG_Byte_Array(bytes):
    tag_type = 7
    def __new__(cls, val):
        return super().__new__(cls, bytes(val))

class TAG_String(str):
    tag_type = 8
    def __new__(cls, val):
        return super().__new__(cls, str(val))

class TAG_List(list):
    tag_type = 9
    def __init__(self, item_type=0, iterable=None):
        super().__init__(iterable or [])
        self.item_type = item_type

class TAG_Compound(dict):
    tag_type = 10

class TAG_Int_Array(list):
    tag_type = 11

class TAG_Long_Array(list):
    tag_type = 12


# Pre-compiled struct formats (big endian)
_B = struct.Struct('>b')
_UB = struct.Struct('>B')
_H = struct.Struct('>h')
_UH = struct.Struct('>H')
_I = struct.Struct('>i')
_Q = struct.Struct('>q')
_F = struct.Struct('>f')
_D = struct.Struct('>d')


# ---------------------------------------------------------------------------
# Reading: the parser works on an in-memory buffer with an explicit offset,
# which is much faster than many small file.read() calls.
# ---------------------------------------------------------------------------

# Tag names and short string values repeat a lot (block names, "Name", "Properties"...):
# decoded strings are cached by their raw bytes.
_STR_CACHE = {}
_STR_CACHE_MAX = 8192


def _read_string(buf, pos):
    end = pos + 2 + ((buf[pos] << 8) | buf[pos + 1])
    raw = buf[pos + 2:end]
    s = _STR_CACHE.get(raw)
    if s is None:
        s = TAG_String(raw.decode('utf-8', errors='replace'))
        if len(raw) <= 64 and len(_STR_CACHE) < _STR_CACHE_MAX:
            _STR_CACHE[raw] = s
    return s, end


def _read_payload(buf, pos, tag_type):
    if tag_type == 10:
        comp = TAG_Compound()
        while True:
            t_type = buf[pos]
            if t_type == 0:
                return comp, pos + 1
            t_name, pos = _read_string(buf, pos + 1)
            comp[t_name], pos = _read_payload(buf, pos, t_type)
    if tag_type == 8:
        return _read_string(buf, pos)
    if tag_type == 1:
        return TAG_Byte(_B.unpack_from(buf, pos)[0]), pos + 1
    if tag_type == 3:
        return TAG_Int(_I.unpack_from(buf, pos)[0]), pos + 4
    if tag_type == 9:
        item_type = buf[pos]
        length = _I.unpack_from(buf, pos + 1)[0]
        pos += 5
        lst = TAG_List(item_type)
        append = lst.append
        for _ in range(max(0, length)):
            val, pos = _read_payload(buf, pos, item_type)
            append(val)
        return lst, pos
    if tag_type == 12:
        length = _I.unpack_from(buf, pos)[0]
        pos += 4
        return TAG_Long_Array(struct.unpack_from(f'>{length}q', buf, pos)), pos + length * 8
    if tag_type == 2:
        return TAG_Short(_H.unpack_from(buf, pos)[0]), pos + 2
    if tag_type == 4:
        return TAG_Long(_Q.unpack_from(buf, pos)[0]), pos + 8
    if tag_type == 5:
        return TAG_Float(_F.unpack_from(buf, pos)[0]), pos + 4
    if tag_type == 6:
        return TAG_Double(_D.unpack_from(buf, pos)[0]), pos + 8
    if tag_type == 7:
        length = _I.unpack_from(buf, pos)[0]
        pos += 4
        return TAG_Byte_Array(buf[pos:pos + length]), pos + length
    if tag_type == 11:
        length = _I.unpack_from(buf, pos)[0]
        pos += 4
        return TAG_Int_Array(struct.unpack_from(f'>{length}i', buf, pos)), pos + length * 4
    if tag_type == 0:
        return None, pos
    raise ValueError(f"Unknown tag type {tag_type}")


def parse_nbt_bytes(data):
    """Parses an uncompressed NBT document. Returns (root_tag, root_name)."""
    data = bytes(data)
    if not data or data[0] == 0:
        return None, ""
    t_type = data[0]
    name, pos = _read_string(data, 1)
    val, _ = _read_payload(data, pos, t_type)
    return val, str(name)


def parse_structure_bytes(data, block_nbt=None):
    """
    Parses a structure-block .nbt document without building a tag object for every block:
    returns (root_tag_without_blocks, [(x, y, z, state_index), ...]). Much lighter on memory
    for very large structures (millions of blocks). Block entity data ('nbt': chest contents,
    sign texts...) is skipped, or stored in the dict 'block_nbt' as (x, y, z) -> compound.
    """
    data = bytes(data)
    if not data or data[0] != 10:
        root, _ = parse_nbt_bytes(data)
        return root, None
    _, pos = _read_string(data, 1)
    root = TAG_Compound()
    blocks = None
    unpack_i = _I.unpack_from
    while True:
        t_type = data[pos]
        if t_type == 0:
            break
        name, pos = _read_string(data, pos + 1)
        if name == "blocks" and t_type == 9 and data[pos] == 10:
            length = unpack_i(data, pos + 1)[0]
            pos += 5
            blocks = []
            append = blocks.append
            for _ in range(max(0, length)):
                x = y = z = state = 0
                extra = None
                while True:
                    tt = data[pos]
                    if tt == 0:
                        pos += 1
                        break
                    nlen = (data[pos + 1] << 8) | data[pos + 2]
                    key = data[pos + 3:pos + 3 + nlen]
                    pos += 3 + nlen
                    if tt == 9 and key == b"pos" and data[pos] == 3 and unpack_i(data, pos + 1)[0] == 3:
                        x, y, z = struct.unpack_from(">iii", data, pos + 5)
                        pos += 17
                    elif tt == 3 and key == b"state":
                        state = unpack_i(data, pos)[0]
                        pos += 4
                    elif tt == 10 and key == b"nbt" and block_nbt is not None:
                        extra, pos = _read_payload(data, pos, tt)
                    else:
                        _, pos = _read_payload(data, pos, tt)
                append((x, y, z, state))
                if extra:
                    block_nbt[(x, y, z)] = extra
        else:
            root[name], pos = _read_payload(data, pos, t_type)
    return root, blocks


def read_tag(f, tag_type):
    """Compatibility helper: reads a tag payload from a file-like object."""
    data = f.read()
    val, pos = _read_payload(data, 0, tag_type)
    if hasattr(f, 'seek'):
        f.seek(pos - len(data), 1)
    return val


# ---------------------------------------------------------------------------
# Writing: tags are serialized into a bytearray, then written in one go.
# ---------------------------------------------------------------------------

def to_nbt(val):
    if hasattr(val, 'tag_type'):
        return val
    if isinstance(val, bool):
        return TAG_Byte(1 if val else 0)
    if isinstance(val, int):
        if -128 <= val <= 127:
            return TAG_Byte(val)
        if -32768 <= val <= 32767:
            return TAG_Short(val)
        if -2147483648 <= val <= 2147483647:
            return TAG_Int(val)
        return TAG_Long(val)
    if isinstance(val, float):
        return TAG_Double(val)
    if isinstance(val, str):
        return TAG_String(val)
    if isinstance(val, (bytes, bytearray)):
        return TAG_Byte_Array(bytes(val))
    if isinstance(val, dict):
        comp = TAG_Compound()
        for k, v in val.items():
            comp[k] = to_nbt(v)
        return comp
    if isinstance(val, (list, tuple)):
        if not val:
            return TAG_List(0, [])
        nbt_items = [to_nbt(x) for x in val]
        types = {x.tag_type for x in nbt_items}
        if len(types) == 1:
            it = next(iter(types))
        else:
            # Fallback to List of strings if mixed types
            it = 8
            nbt_items = [TAG_String(str(x)) for x in val]
        return TAG_List(it, nbt_items)
    raise TypeError(f"Cannot convert type {type(val)} to NBT tag")


def _write_string(out, val):
    b = val.encode('utf-8')
    out += _UH.pack(len(b))
    out += b


def _write_payload(out, tag):
    tag_type = tag.tag_type
    if tag_type == 1:
        out += _B.pack(tag)
    elif tag_type == 2:
        out += _H.pack(tag)
    elif tag_type == 3:
        out += _I.pack(tag)
    elif tag_type == 4:
        out += _Q.pack(tag)
    elif tag_type == 5:
        out += _F.pack(tag)
    elif tag_type == 6:
        out += _D.pack(tag)
    elif tag_type == 7:
        out += _I.pack(len(tag))
        out += tag
    elif tag_type == 8:
        _write_string(out, tag)
    elif tag_type == 9:
        items = [to_nbt(x) for x in tag]
        item_type = tag.item_type if getattr(tag, 'item_type', 0) else (items[0].tag_type if items else 0)
        out += _UB.pack(item_type)
        out += _I.pack(len(items))
        for item in items:
            _write_payload(out, item)
    elif tag_type == 10:
        for name, item in tag.items():
            c_tag = to_nbt(item)
            out += _UB.pack(c_tag.tag_type)
            _write_string(out, name)
            _write_payload(out, c_tag)
        out += b'\x00'  # TAG_End
    elif tag_type == 11:
        out += _I.pack(len(tag))
        out += struct.pack(f'>{len(tag)}i', *tag)
    elif tag_type == 12:
        out += _I.pack(len(tag))
        out += struct.pack(f'>{len(tag)}q', *tag)


def nbt_to_bytes(tag, name=""):
    """Serializes a root tag into uncompressed NBT bytes."""
    tag = to_nbt(tag)
    out = bytearray()
    out += _UB.pack(tag.tag_type)
    _write_string(out, name)
    _write_payload(out, tag)
    return bytes(out)


def write_tag(f, tag):
    """Compatibility helper: writes a tag payload to a file-like object."""
    out = bytearray()
    _write_payload(out, to_nbt(tag))
    f.write(out)


# ---------------------------------------------------------------------------
# File helpers
# ---------------------------------------------------------------------------

def _maybe_decompress(data):
    if data[:2] == b'\x1f\x8b':
        return gzip.decompress(data)
    if data[:1] == b'\x78':  # zlib header
        try:
            return zlib.decompress(data)
        except zlib.error:
            pass
    return data


def load_nbt(f_or_path):
    if isinstance(f_or_path, (bytes, bytearray)):
        data = bytes(f_or_path)
    elif isinstance(f_or_path, str):
        with open(f_or_path, 'rb') as raw:
            data = raw.read()
    elif hasattr(f_or_path, 'read'):
        data = f_or_path.read()
    else:
        raise ValueError("Invalid file or path")
    return parse_nbt_bytes(_maybe_decompress(data))


def save_nbt(tag, name, f_or_path, compressed=True):
    data = nbt_to_bytes(tag, name)
    if compressed:
        data = gzip.compress(data, compresslevel=6, mtime=0)   # deterministic: same content, same file
    if isinstance(f_or_path, str):
        with open(f_or_path, 'wb') as f:
            f.write(data)
    elif hasattr(f_or_path, 'write'):
        f_or_path.write(data)
    else:
        raise ValueError("Invalid file or path")
