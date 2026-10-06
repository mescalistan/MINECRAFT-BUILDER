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
    r"sunflower|lilac|rose_bush|peony|petals|bush|sapling|propagule|mushroom|fungus|roots$|vine|lichen|kelp|"
    r"seagrass|sea_pickle|coral|sugar_cane|cactus|^bamboo$|bamboo_sapling|sweet_berry|cocoa|dripleaf|"
    r"spore_blossom|azalea|amethyst_cluster|_bud$|hanging_moss|frogspawn|eyeblossom)")
# names matched above that are building blocks all the same
_BUILT_EXCEPTIONS = re.compile(r"(_pot$|_planks$|_mosaic|^dried_kelp_block$|_block$(?<!^bamboo_block$)|coral_fan)")
# natural in the desert under the sand, a building block when it stands on the ground (desert houses)
_STANDS_ON_GROUND = {"sandstone", "red_sandstone", "cut_sandstone", "smooth_sandstone"}


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
    return n.endswith(("_log", "_wood", "_stem", "_hyphae")) and not n.startswith("stripped_")


def _plain(block):
    props = block.get("Properties") or {}
    return {"Name": str(block.get("Name", "minecraft:air")), "Properties": {k: str(v) for k, v in props.items()}}


def _slug(text):
    s = re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")
    return s or "ritaglio"


def extract_area(world, x1, z1, x2, z2, mode="costruzioni", include_trees=False, depth=16,
                 progress=None, cancelled=None):
    """
    Cuts the area (inclusive world coordinates), of any size. Returns (Structure, info) or raises
    ValueError. The area is read one chunk at a time straight from the decoded sections (each
    chunk is released right after), what is known about each kind of block is computed once per
    palette entry, and identical blocks share the same dict, so that large areas are fast and fit
    in memory. progress(done, total) is called after every chunk; cancelled() can stop the job.
    """
    from structure_manager import Structure
    x1, x2 = sorted((x1, x2))
    z1, z2 = sorted((z1, z2))
    w, l = x2 - x1 + 1, z2 - z1 + 1

    shared = {}
    air_block = {"Name": "minecraft:air", "Properties": {}}
    AIR, GROUND, TREE, LEAVES, WATER, OTHER_NATURAL, BUILT, AMBIGUOUS = range(8)

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
        if n in ("air", "cave_air", "void_air"):
            kind = AIR
        elif n.endswith("_leaves"):
            kind = LEAVES
        elif _is_tree_part(n):
            kind = TREE
        elif n == "water":
            kind = WATER
        elif n in _STANDS_ON_GROUND:
            kind = AMBIGUOUS
        elif is_natural_terrain(n):
            kind = GROUND if not _NATURAL_PATTERNS.search(n) and n not in ("snow", "lava") else OTHER_NATURAL
        else:
            kind = BUILT
        persistent = str(props.get("persistent", "false")) == "true"
        return kind, plain, persistent

    def built(i, col):
        """Is col[i] = (y, kind, plain, persistent) part of a construction?"""
        _, kind, _, persistent = col[i]
        if kind == BUILT:
            return True
        if kind == AMBIGUOUS:
            # sandstone standing on natural ground is a wall; under the sand it is the desert itself
            for j in range(i + 1, len(col)):
                k2 = col[j][1]
                if k2 == AMBIGUOUS:
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

    out = []            # (x, absolute y, z, block)
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
                    rx, rz = x - x1, z - z1
                    if mode == "tutto":
                        top_max = col[0][0] if top_max is None else max(top_max, col[0][0])
                        lowest = col[-1][0] if lowest is None else min(lowest, col[-1][0])
                        for y, kind, plain, _ in col:
                            out.append((rx, y, rz, plain))
                        continue
                    flags = [built(i, col) for i in range(len(col))]
                    ys = [col[i][0] for i in range(len(col)) if flags[i]]
                    if not ys:
                        continue
                    lo, hi = min(ys), max(ys)
                    for i, (y, kind, plain, _) in enumerate(col):
                        if not lo <= y <= hi:
                            continue
                        if flags[i] or kind == WATER:
                            out.append((rx, y, rz, plain))     # water: pools and fountains inside
                        elif kind == AIR:
                            out.append((rx, y, rz, air_block))
                        # natural terrain -> structure void
        world.forget_chunk(cx, cz)
        if progress:
            progress(n + 1, len(chunks))

    if mode == "tutto":
        if top_max is None:
            raise ValueError("L'area scelta non e' generata in questo mondo.")
        y_lo = min(grounds) - 2 if grounds else lowest
        y_hi = top_max
    else:
        if not out:
            if missing == w * l:
                raise ValueError("L'area scelta non e' generata in questo mondo.")
            raise ValueError("Nell'area non ci sono costruzioni: prova la modalita' 'Tutto, terreno compreso'.")
        y_lo = min(t[1] for t in out)
        y_hi = max(t[1] for t in out)
    blocks = {}
    count = 0
    out.reverse()
    while out:
        rx, y, rz, b = out.pop()
        if y >= y_lo:
            blocks[(rx, y - y_lo, rz)] = b
            if b["Name"] != "minecraft:air":
                count += 1
    ground_list = sorted(grounds)
    median_ground = ground_list[len(ground_list) // 2] if ground_list else y_lo - 1
    ground_offset = max(0, median_ground + 1 - y_lo)
    struct = Structure(w, y_hi - y_lo + 1, l, blocks, data_version)
    struct.ground_offset = ground_offset
    struct.block_nbt = {(rx, y - y_lo, rz): d for (rx, y, rz), d in block_data.items()
                        if (rx, y - y_lo, rz) in blocks}
    for ex, ey, ez, nbt in entities:
        if y_lo <= ey <= y_hi + 1:
            rot = nbt.get("Rotation")
            struct.entities.append({"pos": (ex, ey - y_lo, ez), "nbt": nbt,
                                    "yaw": float(rot[0]) if rot else 0.0})
    info = {"blocks": count, "missing_columns": missing, "y_range": (y_lo, y_hi),
            "ground_offset": ground_offset, "mode": mode}
    return struct, info


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
    blocks = struct.blocks
    block_nbt = getattr(struct, "block_nbt", None) or {}
    for p in positions:
        out += pos_head
        out += pack3(*p)
        out += state_head
        out += pack1(by_obj[id(blocks[p])])
        if p in block_nbt:
            out += nbt_to_bytes(block_nbt[p], "nbt")    # chest contents, sign texts...
        out += b"\x00"
    out += b"\x00"
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "wb") as f:
        f.write(gzip.compress(bytes(out), compresslevel=6))
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
