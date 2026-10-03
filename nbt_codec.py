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


def read_byte(f):
    return struct.unpack('>b', f.read(1))[0]

def read_ubyte(f):
    return struct.unpack('>B', f.read(1))[0]

def read_short(f):
    return struct.unpack('>h', f.read(2))[0]

def read_ushort(f):
    return struct.unpack('>H', f.read(2))[0]

def read_int(f):
    return struct.unpack('>i', f.read(4))[0]

def read_long(f):
    return struct.unpack('>q', f.read(8))[0]

def read_float(f):
    return struct.unpack('>f', f.read(4))[0]

def read_double(f):
    return struct.unpack('>d', f.read(8))[0]

def read_string(f):
    length = read_ushort(f)
    if length == 0:
        return ""
    return f.read(length).decode('utf-8', errors='replace')


def read_tag(f, tag_type):
    if tag_type == 0: # END
        return None
    elif tag_type == 1:
        return TAG_Byte(struct.unpack('>b', f.read(1))[0])
    elif tag_type == 2:
        return TAG_Short(struct.unpack('>h', f.read(2))[0])
    elif tag_type == 3:
        return TAG_Int(struct.unpack('>i', f.read(4))[0])
    elif tag_type == 4:
        return TAG_Long(struct.unpack('>q', f.read(8))[0])
    elif tag_type == 5:
        return TAG_Float(struct.unpack('>f', f.read(4))[0])
    elif tag_type == 6:
        return TAG_Double(struct.unpack('>d', f.read(8))[0])
    elif tag_type == 7:
        length = read_int(f)
        return TAG_Byte_Array(f.read(length))
    elif tag_type == 8:
        return TAG_String(read_string(f))
    elif tag_type == 9:
        item_type = read_ubyte(f)
        length = read_int(f)
        lst = TAG_List(item_type)
        for _ in range(length):
            lst.append(read_tag(f, item_type))
        return lst
    elif tag_type == 10:
        comp = TAG_Compound()
        while True:
            t_type = read_ubyte(f)
            if t_type == 0:
                break
            t_name = read_string(f)
            t_val = read_tag(f, t_type)
            comp[t_name] = t_val
        return comp
    elif tag_type == 11:
        length = read_int(f)
        ints = struct.unpack(f'>{length}i', f.read(length * 4))
        return TAG_Int_Array(ints)
    elif tag_type == 12:
        length = read_int(f)
        longs = struct.unpack(f'>{length}q', f.read(length * 8))
        return TAG_Long_Array(longs)
    else:
        raise ValueError(f"Unknown tag type {tag_type}")


def write_byte(f, val):
    f.write(struct.pack('>b', int(val)))

def write_ubyte(f, val):
    f.write(struct.pack('>B', int(val)))

def write_short(f, val):
    f.write(struct.pack('>h', int(val)))

def write_ushort(f, val):
    f.write(struct.pack('>H', int(val)))

def write_int(f, val):
    f.write(struct.pack('>i', int(val)))

def write_long(f, val):
    f.write(struct.pack('>q', int(val)))

def write_float(f, val):
    f.write(struct.pack('>f', float(val)))

def write_double(f, val):
    f.write(struct.pack('>d', float(val)))

def write_string(f, val):
    b = val.encode('utf-8')
    write_ushort(f, len(b))
    f.write(b)


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


def write_tag(f, tag):
    tag_type = getattr(tag, 'tag_type', None)
    if tag_type is None:
        tag = to_nbt(tag)
        tag_type = tag.tag_type

    if tag_type == 1:
        f.write(struct.pack('>b', tag))
    elif tag_type == 2:
        f.write(struct.pack('>h', tag))
    elif tag_type == 3:
        f.write(struct.pack('>i', tag))
    elif tag_type == 4:
        f.write(struct.pack('>q', tag))
    elif tag_type == 5:
        f.write(struct.pack('>f', tag))
    elif tag_type == 6:
        f.write(struct.pack('>d', tag))
    elif tag_type == 7:
        write_int(f, len(tag))
        f.write(tag)
    elif tag_type == 8:
        write_string(f, tag)
    elif tag_type == 9:
        write_ubyte(f, tag.item_type)
        write_int(f, len(tag))
        for item in tag:
            write_tag(f, item)
    elif tag_type == 10:
        for name, item in tag.items():
            c_tag = to_nbt(item)
            write_ubyte(f, c_tag.tag_type)
            write_string(f, name)
            write_tag(f, c_tag)
        write_ubyte(f, 0) # TAG_End
    elif tag_type == 11:
        write_int(f, len(tag))
        f.write(struct.pack(f'>{len(tag)}i', *tag))
    elif tag_type == 12:
        write_int(f, len(tag))
        f.write(struct.pack(f'>{len(tag)}q', *tag))


def load_nbt(f_or_path):
    if isinstance(f_or_path, str):
        with open(f_or_path, 'rb') as raw:
            magic = raw.read(2)
        if magic == b'\x1f\x8b':
            f = gzip.open(f_or_path, 'rb')
        else:
            f = open(f_or_path, 'rb')
    elif hasattr(f_or_path, 'read'):
        # Peek magic bytes if possible, else wrap or trust gzip
        # We can try to read 2 bytes, then seek back if it's seekable
        f = f_or_path
        if hasattr(f, 'seek'):
            pos = f.tell()
            magic = f.read(2)
            f.seek(pos)
            if magic == b'\x1f\x8b':
                # Re-wrap
                # GzipFile needs a seekable object if we pass fileobj
                f = gzip.GzipFile(fileobj=f)
    else:
        raise ValueError("Invalid file or path")

    try:
        t_type = read_ubyte(f)
        if t_type == 0:
            return None, ""
        name = read_string(f)
        val = read_tag(f, t_type)
        return val, name
    finally:
        if isinstance(f_or_path, str):
            f.close()


def save_nbt(tag, name, f_or_path, compressed=True):
    if isinstance(f_or_path, str):
        if compressed:
            f = gzip.open(f_or_path, 'wb')
        else:
            f = open(f_or_path, 'wb')
    elif hasattr(f_or_path, 'write'):
        f = f_or_path
        if compressed:
            f = gzip.GzipFile(fileobj=f, mode='wb')
    else:
        raise ValueError("Invalid file or path")

    try:
        tag = to_nbt(tag)
        write_ubyte(f, tag.tag_type)
        write_string(f, name)
        write_tag(f, tag)
        if hasattr(f, 'flush'):
            f.flush()
    finally:
        if isinstance(f_or_path, str):
            f.close()
        elif compressed and hasattr(f, 'close'):
            f.close() # Close gzip wrapper
