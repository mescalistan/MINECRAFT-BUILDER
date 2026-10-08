"""
Ritaglio di una zona di mondo come struttura riutilizzabile.

Modalita' "costruzioni" (predefinita): vengono salvati solo i blocchi costruiti
(e l'aria al loro interno); terreno, minerali, piante e alberi naturali diventano
"structure void", cosi' all'incolla la costruzione si appoggia al terreno della
nuova mappa. Modalita' "tutto": copia letterale, terreno compreso.

Nel file viene salvato anche groundOffset: quanti strati della struttura stanno
sotto il livello del terreno originale (cantine, fondamenta), usato per calcolare
la quota giusta all'incolla.
"""
import os
import re
from array import array

from nbt_codec import save_nbt, TAG_Compound, TAG_List, TAG_Int, TAG_String, TAG_Double, TAG_Int_Array
from mca_codec import AIR_NAMES


_NATURAL_EXACT = {
    "stone", "granite", "diorite", "andesite", "deepslate", "tuff", "calcite", "dripstone_block", "grass_block",
    "dirt", "coarse_dirt", "podzol", "rooted_dirt", "mud", "mycelium", "sand", "red_sand", "gravel", "clay",
    "sandstone", "red_sandstone", "terracotta", "snow_block", "snow", "ice", "packed_ice", "blue_ice",
    "powder_snow", "bedrock", "water", "lava", "bubble_column", "netherrack", "soul_sand", "soul_soil", "basalt",
    "blackstone", "magma_block", "end_stone", "moss_block", "moss_carpet", "smooth_basalt", "budding_amethyst",
    "amethyst_block", "sculk", "sculk_vein", "sculk_sensor", "sculk_catalyst", "sculk_shrieker",
    "crimson_nylium", "warped_nylium", "glowstone", "nether_wart_block", "warped_wart_block", "shroomlight",
    "mangrove_roots", "muddy_mangrove_roots", "bee_nest", "suspicious_sand", "suspicious_gravel", "infested_stone",
    "pointed_dripstone", "cobweb", "pale_moss_block", "pale_moss_carpet",
}
_NATURAL_PATTERNS = re.compile(
    r"(_ore$|^raw_|grass$|fern$|flower|tulip|poppy|dandelion|orchid|allium|bluet|daisy|cornflower|lily|"
    r"sunflower|lilac|rose_bush|peony|petals|bush|sapling|propagule|mushroom|fungus|(?<!beet)roots$|vine|lichen|"
    r"kelp|seagrass|sea_pickle|coral|sugar_cane|cactus|^bamboo$|bamboo_sapling|sweet_berry|cocoa|dripleaf|"
    r"spore_blossom|azalea|amethyst_cluster|_bud$|hanging_moss|frogspawn|eyeblossom)")
# names matched above that are building blocks all the same
_BUILT_EXCEPTIONS = re.compile(r"(_pot$|_planks$|_mosaic|^dried_kelp_block$|_block$(?<!^bamboo_block$)|coral_fan)")
# natural in the desert under the sand, a building block when it stands on the ground (desert houses)
_STANDS_ON_GROUND = {"sandstone", "red_sandstone", "cut_sandstone", "smooth_sandstone"}
# natural in some biomes (snowy peaks, badlands): kept only when the user asks for it
_AMBIGUOUS_NATURAL = {"snow_block", "packed_ice", "blue_ice", "ice", "terracotta"} | \
    {f"{c}_terracotta" for c in ("white", "orange", "yellow", "brown", "red", "light_gray")}
# natural only in their own dimension: glowstone in the Overworld is a lamp, end stone a wall
_DIMENSION_BLOCKS = {
    "nether": {"glowstone", "netherrack", "nether_wart_block", "warped_wart_block", "shroomlight", "crimson_nylium",
               "warped_nylium", "soul_sand", "soul_soil", "basalt", "blackstone"},
    "end": {"end_stone"},
}
# natural decorations that grow down from a block (kept under a built one)
_HANGING = re.compile(r"(vines?$|vines_plant$|hanging_roots|spore_blossom|pointed_dripstone|cobweb|hanging_moss|"
                      r"glow_lichen)")
# natural blocks that cling to a side or grow next to farms (kept next to a built block)
_CLINGING = re.compile(r"(^vine$|lichen$|^cocoa$|sculk_vein|moss_carpet|sugar_cane|^bamboo$|^cactus$|^kelp|"
                       r"sea_pickle|coral_fan$|_coral$|sweet_berry_bush|lily_pad)")
# plants that need the block under them: when the plant is kept, that block is kept too
_ROOTED = re.compile(r"(sugar_cane|^bamboo$|^cactus$|sweet_berry_bush)")
ENCLOSURE_MAX_COLUMNS = 4_000_000     # courtyards are looked for in areas up to 2000x2000


def dimension_of(region_dir):
    """'overworld', 'nether' or 'end' from the path of a region folder."""
    p = os.path.abspath(region_dir or "").replace("\\", "/").lower() + "/"
    if "/dim-1/" in p or "/the_nether/" in p:
        return "nether"
    if "/dim1/" in p or "/the_end/" in p:
        return "end"
    return "overworld"


def short(name):
    return name.split(":", 1)[1] if ":" in name else name


def is_natural_terrain(name):
    n = short(name)
    if n in _NATURAL_EXACT:
        return True
    return bool(_NATURAL_PATTERNS.search(n)) and not n.startswith("potted_") \
        and not (_BUILT_EXCEPTIONS.search(n) and n not in ("bamboo_block",) and "coral" not in n
                 and not n.endswith("mushroom_block"))


def _is_tree_part(n):
    # wood and hyphae (bark on all six sides) never grow on their own: they are building blocks;
    # pumpkin and melon stems are crops
    return n.endswith(("_log", "_stem")) and not n.startswith("stripped_") and not n.endswith(("pumpkin_stem",
                                                                                                "melon_stem"))


def _plain(block):
    props = block.get("Properties") or {}
    return {"Name": str(block.get("Name", "minecraft:air")), "Properties": {k: str(v) for k, v in props.items()}}


def _slug(text):
    s = re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")
    return s or "ritaglio"


def extract_area(world, x1, z1, x2, z2, mode="costruzioni", include_trees=False, depth=16,
                 progress=None, cancelled=None, keep_ambiguous=False, enclosures=True):
    """
    Cuts the area (inclusive world coordinates), of any size. Returns (Structure, info) or raises
    ValueError. The area is read one chunk at a time straight from the decoded sections (each
    chunk is released right after), what is known about each kind of block is computed once per
    palette entry, and identical blocks share the same dict, so that large areas are fast and fit
    in memory. progress(done, total) is called after every chunk; cancelled() can stop the job.

    In "costruzioni" mode a natural block is kept when the construction makes it a detail: it rests
    on built blocks (roof gardens, planters, crops), it is the ceiling of a room, it hangs from or
    clings to a built block (vines, lichen, cocoa, sugar cane farms), or - with enclosures - it is
    the ground closed in by the construction (courtyards, sports pitches, gardens inside walls).
    """
    from structure_manager import Structure
    x1, x2 = sorted((x1, x2))
    z1, z2 = sorted((z1, z2))
    w, l = x2 - x1 + 1, z2 - z1 + 1
    dim = dimension_of(getattr(world, "region_dir", ""))
    foreign = set().union(*(names for d, names in _DIMENSION_BLOCKS.items() if d != dim))

    shared = {}
    air_block = {"Name": "minecraft:air", "Properties": {}}
    AIR, GROUND, TREE, LEAVES, WATER, OTHER_NATURAL, BUILT, AMBIGUOUS = range(8)
    HANG, CLING, ROOTED = 1, 2, 4
    roles = {}

    def describe(block):
        """(kind, plain dict, persistent leaves?) of a palette entry."""
        name = str(block.get("Name", "minecraft:air"))
        n = short(name)
        props = block.get("Properties") or {}
        key = (name, tuple(sorted((k, str(v)) for k, v in props.items())))
        plain = shared.get(key)
        if plain is None:
            p = {k: str(v) for k, v in props.items()}
            if name.endswith("_leaves"):
                p["persistent"] = "true"    # cut leaves must not decay where they are pasted
            plain = shared[key] = {"Name": name, "Properties": p}
            roles[id(plain)] = ((HANG if _HANGING.search(n) else 0) | (CLING if _CLINGING.search(n) else 0)
                                | (ROOTED if _ROOTED.search(n) else 0))
        if n in ("air", "cave_air", "void_air"):
            kind = AIR
        elif n.endswith("_leaves"):
            kind = LEAVES
        elif _is_tree_part(n):
            kind = TREE
        elif n == "water":
            kind = WATER
        elif n in foreign or (n.startswith("dead_") and n.endswith("coral_block")):
            kind = BUILT
        elif n in _STANDS_ON_GROUND or (keep_ambiguous and n in _AMBIGUOUS_NATURAL):
            kind = AMBIGUOUS
        elif is_natural_terrain(n):
            kind = GROUND if not _NATURAL_PATTERNS.search(n) and n not in ("snow", "lava") else OTHER_NATURAL
        else:
            kind = BUILT
        persistent = str(props.get("persistent", "false")) == "true"
        return kind, plain, persistent

    def built(i, col):
        """Is col[i] = (y, kind, plain, persistent) part of a construction, by its own kind?"""
        _, kind, _, persistent = col[i]
        if kind == BUILT:
            return True
        if kind == AMBIGUOUS:
            # sandstone under the sand is the desert itself; standing on the ground or on a
            # construction (also across an opening: arches, cornices) it is a wall
            for j in range(i - 1, -1, -1):
                k2 = col[j][1]
                if k2 == AMBIGUOUS:
                    continue
                if k2 == GROUND:
                    return False
                break
            for j in range(i + 1, len(col)):
                k2 = col[j][1]
                if k2 in (AMBIGUOUS, AIR):
                    continue
                return k2 == GROUND or k2 == BUILT
            return False
        if kind == LEAVES:
            return persistent or include_trees
        if kind == TREE:
            if include_trees:
                return True
            # a trunk goes up into natural leaves; a post of a house goes into a roof;
            # a log with nothing built above it (fallen logs, bare branches) is part of the landscape
            for j in range(i - 1, -1, -1):
                k2 = col[j][1]
                if k2 in (TREE, AIR):
                    continue
                return k2 == BUILT or (k2 == LEAVES and col[j][3])
            return False
        return False

    def column_flags(col):
        """Which blocks of a column (top to bottom) belong to the construction."""
        n = len(col)
        flags = [built(i, col) for i in range(n)]
        if not any(flags):
            return flags
        # bottom up: natural blocks resting on the construction (roof gardens, planters, crops, sand
        # on a roof) and ceilings of rooms (stone, glowstone, ice over air with a floor under it)
        run = 0
        for i in range(n - 2, -1, -1):
            kind = col[i][1]
            if flags[i] or kind in (AIR, WATER):
                run = 0
                continue
            if flags[i + 1] and run < 4:
                flags[i] = True
                run += 1
                continue
            if col[i + 1][1] == AIR:
                j = i + 1
                while j < n and col[j][1] == AIR:
                    j += 1
                if j < n and flags[j] and j - i <= 16:
                    flags[i] = True
                    run = 1
                    continue
            run = 0
        hang_down(col, flags)
        return flags

    def hang_down(col, flags):
        """
        Top down: vines, lichen, dripstone, cobwebs hanging under a kept block, and a ceiling
        layer of natural blocks right under a built one with a room (air) below.
        """
        n = len(col)
        for i in range(1, n):
            if flags[i] or not flags[i - 1]:
                continue
            if roles.get(id(col[i][2]), 0) & HANG:
                flags[i] = True
            elif col[i][1] in (GROUND, AMBIGUOUS) and i + 1 < n and col[i + 1][1] == AIR \
                    and col[i - 1][1] != GROUND:
                flags[i] = True

    # output blocks: four arrays (x, absolute y, z, palette index) instead of a tuple per block
    oxs, oys, ozs, osi = array("i"), array("i"), array("i"), array("i")
    out_states, out_index = [], {}
    kept_data = set()

    def add(rx, y, rz, b):
        i = out_index.get(id(b))
        if i is None:
            i = out_index[id(b)] = len(out_states)
            out_states.append(b)
        oxs.append(rx)
        oys.append(y)
        ozs.append(rz)
        osi.append(i)
        if block_data and (rx, y, rz) in block_data:
            kept_data.add((rx, y, rz))

    # courtyards: per column, does the construction rise there (a "wall")? and the natural blocks
    # from the top down to the ground, kept later if the column turns out to be closed in
    look_for_enclosures = mode != "tutto" and enclosures and w * l <= ENCLOSURE_MAX_COLUMNS
    walls = bytearray(w * l) if look_for_enclosures else None
    cand_c, cand_y = array("i"), array("i")
    cand_b = []

    grounds = []
    missing = 0
    data_version = None
    top_max = None
    lowest = None
    block_data, entities, entity_regions = {}, [], {}
    chunks = [(cx, cz) for cx in range(x1 >> 4, (x2 >> 4) + 1) for cz in range(z1 >> 4, (z2 >> 4) + 1)]
    for n, (cx, cz) in enumerate(chunks):
        if cancelled and cancelled():
            raise ValueError("Ritaglio annullato.")
        xs = range(max(x1, cx * 16), min(x2, cx * 16 + 15) + 1)
        zs = range(max(z1, cz * 16), min(z2, cz * 16 + 15) + 1)
        ed = world.editor(cx, cz)
        if ed is None:
            missing += len(xs) * len(zs)
        else:
            # chest contents, sign texts, banner patterns...: kept with the blocks
            for be in ed.nbt.get("block_entities") or []:
                bx, by, bz = int(be.get("x", 0)), int(be.get("y", 0)), int(be.get("z", 0))
                if x1 <= bx <= x2 and z1 <= bz <= z2:
                    data = TAG_Compound({k: v for k, v in be.items() if k not in ("id", "x", "y", "z", "keepPacked")})
                    if data:
                        block_data[(bx - x1, by, bz - z1)] = data
            entities.extend(_area_entities(world, cx, cz, x1, z1, x2, z2, entity_regions))
            if data_version is None:
                data_version = int(ed.nbt.get("DataVersion", 0)) or None
            sections = {}                       # sy -> (indices, metas) or None

            def section(sy):
                if sy not in sections:
                    entry = ed._load(sy)
                    sections[sy] = None if entry is None else (entry[1], [describe(b) for b in entry[0]])
                return sections[sy]

            columns = {}                        # (x, z) -> [col, flags, ground]
            for x in xs:
                for z in zs:
                    top = world.surface_y(x, z)
                    if top is None:
                        missing += 1
                        continue
                    lx, lz = x & 15, z & 15
                    col = []
                    ground = None
                    y = top
                    while y >= -64:
                        sec = section(y >> 4)
                        if sec is None:
                            break
                        kind, plain, persistent = sec[1][sec[0][((y & 15) << 8) | (lz << 4) | lx]]
                        col.append((y, kind, plain, persistent))
                        if ground is None and kind == GROUND:
                            ground = y
                        if ground is not None and y <= ground - depth:
                            break
                        y -= 1
                    if not col:
                        missing += 1
                        continue
                    if ground is not None:
                        grounds.append(ground)
                    if mode == "tutto":
                        rx, rz = x - x1, z - z1
                        top_max = col[0][0] if top_max is None else max(top_max, col[0][0])
                        lowest = col[-1][0] if lowest is None else min(lowest, col[-1][0])
                        for y, kind, plain, _ in col:
                            add(rx, y, rz, plain)
                        continue
                    columns[(x, z)] = [col, column_flags(col), ground]

            # clinging decorations and farm plants next to a built block of a neighbouring column
            changed = set()
            for (x, z), (col, flags, _) in columns.items():
                top_y = col[0][0]
                for i, (y, kind, plain, _) in enumerate(col):
                    if flags[i] or not roles.get(id(plain), 0) & CLING:
                        continue
                    for nx, nz in ((x + 1, z), (x - 1, z), (x, z + 1), (x, z - 1)):
                        other = columns.get((nx, nz))
                        if other is None:
                            continue
                        j = other[0][0][0] - y
                        if 0 <= j < len(other[1]) and other[1][j]:
                            flags[i] = True
                            changed.add((x, z))
                            break
            for key in changed:
                col, flags, _ = columns[key]
                for i in range(len(col) - 1):
                    # sugar cane, bamboo, cactus, berry bushes: the block they grow on goes with them
                    if flags[i] and roles.get(id(col[i][2]), 0) & ROOTED and not flags[i + 1] \
                            and col[i + 1][1] == GROUND:
                        flags[i + 1] = True
                hang_down(col, flags)

            for (x, z), (col, flags, ground) in columns.items():
                rx, rz = x - x1, z - z1
                ys = [col[i][0] for i in range(len(col)) if flags[i]]
                if walls is not None:
                    c = rz * w + rx
                    if ys and (ground is None or ys[0] >= ground + 2):
                        walls[c] = 1
                    elif ground is not None:
                        # the natural top of the column, from its highest block down to the ground
                        for i, (y, kind, plain, _) in enumerate(col):
                            if y < ground:
                                break
                            if not flags[i] and kind != AIR:
                                cand_c.append(c)
                                cand_y.append(y)
                                cand_b.append(plain)
                if not ys:
                    continue
                lo, hi = min(ys), max(ys)
                for i, (y, kind, plain, _) in enumerate(col):
                    if not lo <= y <= hi:
                        continue
                    if flags[i] or kind == WATER:
                        add(rx, y, rz, plain)     # water: pools and fountains inside
                    elif kind == AIR:
                        add(rx, y, rz, air_block)
                    # natural terrain -> structure void
        world.forget_chunk(cx, cz)
        if progress:
            progress(n + 1, len(chunks))

    enclosed_columns = 0
    if walls is not None and any(walls):
        inside = _enclosed(walls, w, l)
        enclosed_columns = sum(inside)
        for c, y, b in zip(cand_c, cand_y, cand_b):
            if inside[c]:
                add(c % w, y, c // w, b)
    del cand_c, cand_y, cand_b

    if mode == "tutto":
        if top_max is None:
            raise ValueError("L'area scelta non e' generata in questo mondo.")
        y_lo = min(grounds) - 2 if grounds else lowest
        y_hi = top_max
    else:
        if not oxs:
            if missing == w * l:
                raise ValueError("L'area scelta non e' generata in questo mondo.")
            raise ValueError("Nell'area non ci sono costruzioni: prova la modalita' 'Tutto, terreno compreso'.")
        y_lo = min(oys)
        y_hi = max(oys)
    from structure_manager import PackedBlocks, PACKED_MIN_BLOCKS
    from collections import Counter
    if oys and min(oys) < y_lo:              # "tutto": the layers deep under the ground are left out
        keep = [i for i, y in enumerate(oys) if y >= y_lo]
        oxs, oys, ozs, osi = (array("i", (a[i] for i in keep)) for a in (oxs, oys, ozs, osi))
    oys = array("i", (y - y_lo for y in oys))
    counts = Counter(osi)
    count = sum(c for i, c in counts.items() if out_states[i]["Name"] != "minecraft:air")
    if len(oxs) >= PACKED_MIN_BLOCKS:
        blocks = PackedBlocks(oxs, oys, ozs, osi, out_states, 0, w, l)
    else:
        blocks = {(x, y, z): out_states[s] for x, y, z, s in zip(oxs, oys, ozs, osi)}
    del oxs, ozs, osi
    ground_list = sorted(grounds)
    median_ground = ground_list[len(ground_list) // 2] if ground_list else y_lo - 1
    ground_offset = max(0, median_ground + 1 - y_lo)
    struct = Structure(w, y_hi - y_lo + 1, l, blocks, data_version)
    struct.ground_offset = ground_offset
    struct.block_nbt = {(rx, y - y_lo, rz): d for (rx, y, rz), d in block_data.items()
                        if (rx, y, rz) in kept_data and y >= y_lo}
    for ex, ey, ez, nbt in entities:
        if y_lo <= ey <= y_hi + 1:
            rot = nbt.get("Rotation")
            struct.entities.append({"pos": (ex, ey - y_lo, ez), "nbt": nbt,
                                    "yaw": float(rot[0]) if rot else 0.0})
    info = {"blocks": count, "missing_columns": missing, "y_range": (y_lo, y_hi),
            "ground_offset": ground_offset, "mode": mode, "enclosed_columns": enclosed_columns}
    return struct, info


def _enclosed(walls, w, l, gap=2):
    """
    Columns closed in by the construction (bytearray, 1 = inside): the walls are first joined
    across openings up to 2*gap+1 wide (doors, gates, stadium entrances), then everything that
    can be reached from the edge of the area without crossing them is outside.
    """
    from collections import deque
    full = (1 << w) - 1
    table = bytes.maketrans(b"\x00\x01", b"01")
    rows = [int(bytes(walls[z * w:(z + 1) * w]).translate(table)[::-1], 2) for z in range(l)]
    # closing = dilation then erosion; outside the area there is nothing (the strip between a
    # construction and the edge of the area stays open), and the walls themselves always block
    dil = []
    for m in rows:
        d = m
        for k in range(1, gap + 1):
            d |= (m << k) | (m >> k)
        dil.append(d & full)
    dil = [_or_rows(dil, z, gap, l) for z in range(l)]
    ero = []
    for m in dil:
        e = m
        for k in range(1, gap + 1):
            e &= (m << k) & (m >> k)
        ero.append(e & full)
    closed = []
    for z in range(l):
        e = ero[z]
        for k in range(1, gap + 1):
            e &= (ero[z - k] if z - k >= 0 else 0) & (ero[z + k] if z + k < l else 0)
        closed.append(e | rows[z])
    blocked = bytearray(w * l)
    for z, m in enumerate(closed):
        if m:
            bits = bin(m)[2:].zfill(w)[::-1]
            blocked[z * w:(z + 1) * w] = bits.encode().translate(bytes.maketrans(b"01", b"\x00\x01"))
    reached = bytearray(w * l)
    todo = deque()
    for x in range(w):
        for c in (x, (l - 1) * w + x):
            if not blocked[c] and not reached[c]:
                reached[c] = 1
                todo.append(c)
    for z in range(l):
        for c in (z * w, z * w + w - 1):
            if not blocked[c] and not reached[c]:
                reached[c] = 1
                todo.append(c)
    while todo:
        c = todo.popleft()
        x = c % w
        for nc in ((c - 1) if x > 0 else -1, (c + 1) if x < w - 1 else -1, c - w, c + w):
            if 0 <= nc < w * l and not reached[nc] and not blocked[nc]:
                reached[nc] = 1
                todo.append(nc)
    return bytearray(1 if not reached[c] and not walls[c] else 0 for c in range(w * l))


def _or_rows(rows, z, r, l):
    m = 0
    for k in range(max(0, z - r), min(l, z + r + 1)):
        m |= rows[k]
    return m


def _area_entities(world, cx, cz, x1, z1, x2, z2, cache):
    """Entities (item frames, armor stands, animals...) of one chunk inside the area, relative positions."""
    import math
    from mca_codec import MCARegion
    folder = world.entities_dir() if hasattr(world, "entities_dir") else None
    if not folder:
        return []
    key = (cx >> 5, cz >> 5)
    if key not in cache:
        path = os.path.join(folder, f"r.{key[0]}.{key[1]}.mca")
        try:
            cache[key] = MCARegion(path) if os.path.exists(path) else None
        except Exception:
            cache[key] = None
    region = cache[key]
    if region is None:
        return []
    entry = region.chunks.get((cx & 31, cz & 31))
    if entry is None:
        return []
    out = []
    for ent in entry[0].get("Entities") or []:
        pos = ent.get("Pos")
        if not pos or len(pos) < 3 or str(ent.get("id", "")) == "minecraft:player":
            continue
        ex, ey, ez = (float(v) for v in pos[:3])
        if not (x1 <= math.floor(ex) <= x2 and z1 <= math.floor(ez) <= z2):
            continue
        nbt = TAG_Compound({k: v for k, v in ent.items() if k not in ("UUID", "Pos", "Motion", "Leash")})
        out.append((ex - x1, ey, ez - z1, nbt))
    return out


def save_structure(struct, path, extra=None):
    """
    Writes a Structure as a vanilla structure-block .nbt file (+ MinecraftBuilder metadata).
    The block list is written directly as bytes, without a tag object per block, so even
    structures with millions of blocks are saved quickly and with little memory.
    """
    import gzip
    import struct as st
    from nbt_codec import nbt_to_bytes
    if getattr(struct.blocks, "packed", False):
        return _save_packed(struct, path, extra)
    palette, index, by_obj = [], {}, {}
    for b in struct.blocks.values():
        if id(b) in by_obj:
            continue
        props = b.get("Properties") or {}
        key = (b["Name"], tuple(sorted((p, str(v)) for p, v in props.items())))
        idx = index.get(key)
        if idx is None:
            idx = index[key] = len(palette)
            entry = TAG_Compound({"Name": TAG_String(b["Name"])})
            if props:
                entry["Properties"] = TAG_Compound({p: TAG_String(str(v)) for p, v in sorted(props.items())})
            palette.append(entry)
        by_obj[id(b)] = idx
    head = TAG_Compound()
    head["DataVersion"] = TAG_Int(struct.data_version or 3955)
    head["size"] = TAG_List(3, [TAG_Int(struct.width), TAG_Int(struct.height), TAG_Int(struct.length)])
    head["palette"] = TAG_List(10, palette)
    ents = []
    for ent in getattr(struct, "entities", []) or []:
        ex, ey, ez = ent["pos"]
        ents.append(TAG_Compound({
            "pos": TAG_List(6, [TAG_Double(ex), TAG_Double(ey), TAG_Double(ez)]),
            "blockPos": TAG_List(3, [TAG_Int(int(ex // 1)), TAG_Int(int(ey // 1)), TAG_Int(int(ez // 1))]),
            "nbt": ent["nbt"]}))
    head["entities"] = TAG_List(10, ents)
    meta = TAG_Compound({"groundOffset": TAG_Int(getattr(struct, "ground_offset", 0))})
    technical = getattr(struct, "technical", None)
    if technical:
        meta["technical"] = TAG_List(11, [TAG_Int_Array(list(b)) for b in technical])
    for k, v in (extra or {}).items():
        meta[k] = TAG_String(str(v))
    head["MinecraftBuilder"] = meta
    body = nbt_to_bytes(head, "")          # 0x0a, name, tags..., 0x00
    out = bytearray(body[:-1])             # reopen the root compound to append "blocks"
    positions = sorted(struct.blocks, key=lambda p: (p[1], p[2], p[0]))
    out += b"\x09" + st.pack(">H", 6) + b"blocks" + b"\x0a" + st.pack(">i", len(positions))
    pos_head = b"\x09" + st.pack(">H", 3) + b"pos" + b"\x03" + st.pack(">i", 3)
    state_head = b"\x03" + st.pack(">H", 5) + b"state"
    pack3 = st.Struct(">iii").pack
    pack1 = st.Struct(">i").pack
    pack_rec = st.Struct(">11siii8sib").pack          # a whole 36-byte record in one call
    blocks = struct.blocks
    block_nbt = getattr(struct, "block_nbt", None) or {}
    for p in positions:
        if p in block_nbt:
            out += pos_head
            out += pack3(*p)
            out += state_head
            out += pack1(by_obj[id(blocks[p])])
            out += nbt_to_bytes(block_nbt[p], "nbt")    # chest contents, sign texts...
            out += b"\x00"
        else:
            out += pack_rec(pos_head, p[0], p[1], p[2], state_head, by_obj[id(blocks[p])], 0)
    out += b"\x00"
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "wb") as f:
        f.write(gzip.compress(bytes(out), compresslevel=6))
    os.replace(tmp, path)
    return path


def _structure_head(struct, palette, extra):
    head = TAG_Compound()
    head["DataVersion"] = TAG_Int(struct.data_version or 3955)
    head["size"] = TAG_List(3, [TAG_Int(struct.width), TAG_Int(struct.height), TAG_Int(struct.length)])
    head["palette"] = TAG_List(10, palette)
    ents = []
    for ent in getattr(struct, "entities", []) or []:
        ex, ey, ez = ent["pos"]
        ents.append(TAG_Compound({
            "pos": TAG_List(6, [TAG_Double(ex), TAG_Double(ey), TAG_Double(ez)]),
            "blockPos": TAG_List(3, [TAG_Int(int(ex // 1)), TAG_Int(int(ey // 1)), TAG_Int(int(ez // 1))]),
            "nbt": ent["nbt"]}))
    head["entities"] = TAG_List(10, ents)
    meta = TAG_Compound({"groundOffset": TAG_Int(getattr(struct, "ground_offset", 0))})
    technical = getattr(struct, "technical", None)
    if technical:
        meta["technical"] = TAG_List(11, [TAG_Int_Array(list(b)) for b in technical])
    for k, v in (extra or {}).items():
        meta[k] = TAG_String(str(v))
    head["MinecraftBuilder"] = meta
    return head


def _save_packed(struct, path, extra=None):
    """
    Very large structures: every block as a fixed 36-byte record built at C speed; blocks with block
    entity data are repeated after them with their 'nbt' (metadata 'fixedRecords' tells the loader).
    """
    import gzip
    import struct as st
    from nbt_codec import nbt_to_bytes, fixed_records_bytes
    pb = struct.blocks
    palette = []
    for b in pb.states:
        entry = TAG_Compound({"Name": TAG_String(b["Name"])})
        props = b.get("Properties") or {}
        if props:
            entry["Properties"] = TAG_Compound({p: TAG_String(str(v)) for p, v in sorted(props.items())})
        palette.append(entry)
    xs, ys, zs, si = pb.arrays()
    head = _structure_head(struct, palette, extra)
    head["MinecraftBuilder"]["fixedRecords"] = TAG_Int(len(xs))
    block_nbt = getattr(struct, "block_nbt", None) or {}
    states_of = {}
    if block_nbt:
        wanted = set(block_nbt)
        for x, y, z, s in zip(xs, ys, zs, si):
            if (x, y, z) in wanted:
                states_of[(x, y, z)] = s
    body = nbt_to_bytes(head, "")
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    tmp = path + ".tmp"
    # written piece by piece: neither the records nor the compressed file are ever whole in memory
    with gzip.open(tmp, "wb", compresslevel=3) as f:
        f.write(body[:-1])
        f.write(b"\x09" + st.pack(">H", 6) + b"blocks" + b"\x0a" + st.pack(">i", len(xs) + len(states_of)))
        step = 262144
        for a in range(0, len(xs), step):
            f.write(fixed_records_bytes(xs[a:a + step], ys[a:a + step], zs[a:a + step], si[a:a + step]))
        for p, s in states_of.items():
            f.write(b"\x09" + st.pack(">H", 3) + b"pos" + b"\x03" + st.pack(">i", 3) + st.pack(">iii", *p)
                    + b"\x03" + st.pack(">H", 5) + b"state" + st.pack(">i", s)
                    + nbt_to_bytes(block_nbt[p], "nbt") + b"\x00")
        f.write(b"\x00")
    os.replace(tmp, path)
    return path


def unique_path(templates_dir, title):
    base = _slug(title)
    path = os.path.join(templates_dir, f"{base}.nbt")
    i = 2
    while os.path.exists(path):
        path = os.path.join(templates_dir, f"{base}_{i}.nbt")
        i += 1
    return path
