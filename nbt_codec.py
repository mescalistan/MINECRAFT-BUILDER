import struct
import sys
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


def decode_mutf8(raw):
    """Java 'modified UTF-8': NUL is C0 80, characters beyond U+FFFF are two 3-byte surrogates."""
    try:
        return raw.decode('utf-8')
    except UnicodeDecodeError:
        pass
    raw = bytes(raw).replace(b'\xc0\x80', b'\x00')
    s = raw.decode('utf-8', errors='surrogatepass')
    # recombine the surrogate pairs into real characters
    return s.encode('utf-16-le', errors='surrogatepass').decode('utf-16-le', errors='replace')


def encode_mutf8(s):
    if s.isascii() and '\x00' not in s:
        return s.encode('ascii')
    out = []
    for ch in s:
        c = ord(ch)
        if c > 0xFFFF:
            c -= 0x10000
            out.append(chr(0xD800 + (c >> 10)))
            out.append(chr(0xDC00 + (c & 0x3FF)))
        else:
            out.append(ch)
    return ''.join(out).encode('utf-8', errors='surrogatepass').replace(b'\x00', b'\xc0\x80')


def _read_string(buf, pos):
    end = pos + 2 + ((buf[pos] << 8) | buf[pos + 1])
    raw = buf[pos + 2:end]
    s = _STR_CACHE.get(raw)
    if s is None:
        s = TAG_String(decode_mutf8(raw))
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


# A block record {pos: [x, y, z], state: n} with nothing else: always 36 bytes
_REC_HEAD = b"\x09\x00\x03pos\x03\x00\x00\x00\x03"
_STATE_HEAD = b"\x03\x00\x05state"
_REC = struct.Struct(">iii8xi")
_FIXED_SIZE = {1: 1, 2: 2, 3: 4, 4: 8, 5: 4, 6: 8}


def skip_payload(buf, pos, t):
    """Position after a tag payload, without building any object."""
    if t in _FIXED_SIZE:
        return pos + _FIXED_SIZE[t]
    if t == 8:
        return pos + 2 + ((buf[pos] << 8) | buf[pos + 1])
    if t == 7:
        return pos + 4 + _I.unpack_from(buf, pos)[0]
    if t == 11:
        return pos + 4 + 4 * _I.unpack_from(buf, pos)[0]
    if t == 12:
        return pos + 4 + 8 * _I.unpack_from(buf, pos)[0]
    if t == 9:
        it, n = buf[pos], _I.unpack_from(buf, pos + 1)[0]
        pos += 5
        if it in _FIXED_SIZE:
            return pos + _FIXED_SIZE[it] * max(0, n)
        for _ in range(max(0, n)):
            pos = skip_payload(buf, pos, it)
        return pos
    if t == 10:
        while True:
            tt = buf[pos]
            if tt == 0:
                return pos + 1
            pos = skip_payload(buf, pos + 3 + ((buf[pos + 1] << 8) | buf[pos + 2]), tt)
    if t == 0:
        return pos
    raise ValueError(f"Tag NBT sconosciuto {t}")


def parse_root_skipping(data, skip):
    """Root compound with the top-level tags named in 'skip' left out (read-only uses, e.g. the map)."""
    data = bytes(data)
    if not data or data[0] != 10:
        return parse_nbt_bytes(data)[0]
    _, pos = _read_string(data, 1)
    root = TAG_Compound()
    while True:
        t = data[pos]
        if t == 0:
            break
        name, pos = _read_string(data, pos + 1)
        if name in skip:
            pos = skip_payload(data, pos, t)
        else:
            root[name], pos = _read_payload(data, pos, t)
    return root


def _fixed_fields(data, pos, n):
    """
    The n block records at pos are all the fixed 36-byte kind: their x, y, z, state as four
    array('i'), sliced out of the bytes at C speed; None if any record differs.
    """
    from array import array
    end = pos + 36 * n
    if n <= 0 or end > len(data):
        return None
    for off, pattern in ((0, _REC_HEAD), (23, _STATE_HEAD), (35, b"\x00")):
        for k, byte in enumerate(pattern):
            if data[pos + off + k:end:36] != bytes((byte,)) * n:
                return None
    fields = []
    for off in (11, 15, 19, 31):
        buf = bytearray(4 * n)
        for k in range(4):
            buf[k::4] = data[pos + off + k:end:36]
        a = array("i")
        a.frombytes(buf)
        if sys.byteorder == "little":
            a.byteswap()
        fields.append(a)
    return fields


def fixed_records_bytes(xs, ys, zs, si):
    """The 36-byte records of n blocks built at C speed (the inverse of _fixed_fields)."""
    from array import array
    n = len(xs)
    buf = bytearray(36 * n)
    for off, pattern in ((0, _REC_HEAD), (23, _STATE_HEAD)):
        for k, byte in enumerate(pattern):
            buf[off + k::36] = bytes((byte,)) * n
    for off, values in ((11, xs), (15, ys), (19, zs), (31, si)):
        a = array("i", values)
        if sys.byteorder == "little":
            a.byteswap()
        raw = a.tobytes()
        for k in range(4):
            buf[off + k::36] = raw[k::4]
    return buf


def parse_structure_packed(data, block_nbt=None, only_extra=False):
    """
    Like parse_structure_bytes, but the blocks come back as four array('i') (x, y, z, state): a few
    bytes per block instead of a tuple, read at C speed when the records have the fixed layout.
    Records after 'fixedRecords' (MinecraftBuilder metadata) only carry block entity data.
    """
    from array import array
    data = bytes(data)
    _, pos = _read_string(data, 1)
    root = TAG_Compound()
    fields = None
    while True:
        t_type = data[pos]
        if t_type == 0:
            break
        name, pos = _read_string(data, pos + 1)
        if name == "blocks" and t_type == 9 and data[pos] == 10:
            length = _I.unpack_from(data, pos + 1)[0]
            pos += 5
            meta = root.get("MinecraftBuilder") or {}
            n_fixed = 0 if only_extra else int(meta.get("fixedRecords", length))
            fields = _fixed_fields(data, pos, n_fixed) if 0 < n_fixed <= length else None
            done = 0
            if fields is not None:
                pos += 36 * n_fixed
                done = n_fixed
                extra_only = "fixedRecords" in meta       # the rest: block entity data of placed blocks
            else:
                fields = [array("i"), array("i"), array("i"), array("i")]
                extra_only = only_extra
            xs, ys, zs, si = fields
            for _ in range(max(0, length - done)):
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
                    if tt == 9 and key == b"pos" and data[pos] == 3 and _I.unpack_from(data, pos + 1)[0] == 3:
                        x, y, z = struct.unpack_from(">iii", data, pos + 5)
                        pos += 17
                    elif tt == 3 and key == b"state":
                        state = _I.unpack_from(data, pos)[0]
                        pos += 4
                    elif tt == 10 and key == b"nbt" and block_nbt is not None:
                        extra, pos = _read_payload(data, pos, tt)
                    else:
                        _, pos = _read_payload(data, pos, tt)
                if not extra_only:
                    xs.append(x)
                    ys.append(y)
                    zs.append(z)
                    si.append(state)
                if extra:
                    block_nbt[(x, y, z)] = extra
        else:
            root[name], pos = _read_payload(data, pos, t_type)
    return root, fields


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
            rec_head, state_head = _REC_HEAD, _STATE_HEAD
            unpack_rec = _REC.unpack_from
            for _ in range(max(0, length)):
                if data.startswith(rec_head, pos) and data.startswith(state_head, pos + 23) and data[pos + 35] == 0:
                    append(unpack_rec(data, pos + 11))      # x, y, z, state in one call
                    pos += 36
                    continue
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
    b = encode_mutf8(val)
    if len(b) > 0xFFFF:
        raise ValueError(f"Testo NBT troppo lungo ({len(b)} byte, massimo 65535)")
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

def read_structure_file(path, block_nbt=None):
    """
    parse_structure_packed() for a file, streaming: the fixed block records of the files written by
    this program (MinecraftBuilder.fixedRecords before the block list) are decompressed and converted
    about 10 MB at a time, so a cut with tens of millions of blocks never sits in memory decompressed.
    Other files are read whole.
    """
    from array import array
    with open(path, "rb") as fh:
        magic = fh.read(2)
    if magic != b"\x1f\x8b":
        with open(path, "rb") as fh:
            return parse_structure_packed(_maybe_decompress(fh.read()), block_nbt)
    f = gzip.open(path, "rb")
    try:
        buf = bytearray()

        def need(n):
            while len(buf) < n:
                chunk = f.read(max(1 << 20, n - len(buf)))
                if not chunk:
                    raise ValueError("File NBT troncato")
                buf.extend(chunk)

        need(3)
        if buf[0] != 10:
            buf.extend(f.read())
            return parse_structure_packed(bytes(buf), block_nbt)
        pos = 3 + ((buf[1] << 8) | buf[2])
        root = TAG_Compound()
        while True:
            need(pos + 3)
            t_type = buf[pos]
            if t_type == 0:
                break
            nlen = (buf[pos + 1] << 8) | buf[pos + 2]
            need(pos + 3 + nlen)
            name = decode_mutf8(bytes(buf[pos + 3:pos + 3 + nlen]))
            body = pos + 3 + nlen
            meta = root.get("MinecraftBuilder") or {}
            if name == "blocks" and t_type == 9 and "fixedRecords" in meta:
                need(body + 5)
                length = _I.unpack_from(buf, body + 1)[0]
                n_fixed = int(meta["fixedRecords"])
                del buf[:body + 5]
                xs, ys, zs, si = array("i"), array("i"), array("i"), array("i")
                step = 262144                       # records per piece (about 9 MB)
                left = n_fixed
                while left > 0:
                    take = min(step, left)
                    need(36 * take)
                    piece = bytes(buf[:36 * take])
                    del buf[:36 * take]
                    fields = _fixed_fields(piece, 0, take)
                    if fields is None:
                        raise ValueError("Record dei blocchi non validi")
                    for dst, src in zip((xs, ys, zs, si), fields):
                        dst.extend(src)
                    left -= take
                # what follows (block entity records, other tags) is small: parse it whole
                buf.extend(f.read())
                rest = b"\x0a\x00\x00" + b"\x09\x00\x06blocks\x0a" + struct.pack(">i", length - n_fixed) + bytes(buf)
                tail_root, extra = parse_structure_packed(rest, block_nbt, only_extra=True)
                root.update({k: v for k, v in tail_root.items()})
                return root, [xs, ys, zs, si]
            if name == "blocks":
                break                               # not written by this program: read it whole
            # any other tag: parse it (reading more of the file until it is complete)
            while True:
                try:
                    data = bytes(buf)
                    root[name], end = _read_payload(data, body, t_type)
                    break
                except (IndexError, struct.error):
                    more = f.read(1 << 22)
                    if not more:
                        raise ValueError("File NBT troncato")
                    buf.extend(more)
            del buf[:end]
            pos = 0
    finally:
        f.close()
    with open(path, "rb") as fh:
        return parse_structure_packed(_maybe_decompress(fh.read()), block_nbt)


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
