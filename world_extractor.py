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

from nbt_codec import save_nbt, TAG_Compound, TAG_List, TAG_Int, TAG_String
from mca_codec import AIR_NAMES

MAX_AREA = 256 * 256

_NATURAL_EXACT = {
    "stone", "granite", "diorite", "andesite", "deepslate", "tuff", "calcite", "dripstone_block", "grass_block",
    "dirt", "coarse_dirt", "podzol", "rooted_dirt", "mud", "mycelium", "sand", "red_sand", "gravel", "clay",
    "sandstone", "red_sandstone", "terracotta", "snow_block", "snow", "ice", "packed_ice", "blue_ice",
    "powder_snow", "bedrock", "water", "lava", "bubble_column", "netherrack", "soul_sand", "soul_soil", "basalt",
    "blackstone", "magma_block", "end_stone", "moss_block", "moss_carpet", "smooth_basalt", "budding_amethyst",
    "amethyst_block", "sculk", "sculk_vein", "sculk_sensor", "sculk_catalyst", "sculk_shrieker", "obsidian",
    "crimson_nylium", "warped_nylium", "glowstone", "nether_wart_block", "warped_wart_block", "shroomlight",
    "mangrove_roots", "muddy_mangrove_roots", "bee_nest", "suspicious_sand", "suspicious_gravel", "infested_stone",
    "pointed_dripstone", "cobweb", "pale_moss_block", "pale_moss_carpet",
}
_NATURAL_PATTERNS = re.compile(
    r"(_ore$|^raw_|grass$|fern$|flower|tulip|poppy|dandelion|orchid|allium|bluet|daisy|cornflower|lily|"
    r"sunflower|lilac|rose_bush|peony|petals|bush|sapling|propagule|mushroom|fungus|roots$|vine|lichen|kelp|"
    r"seagrass|sea_pickle|coral|sugar_cane|cactus|bamboo|sweet_berry|cocoa|dripleaf|spore_blossom|azalea|"
    r"amethyst_cluster|_bud$|hanging_moss|frogspawn|eyeblossom)")


def short(name):
    return name.split(":", 1)[1] if ":" in name else name


def is_natural_terrain(name):
    n = short(name)
    return n in _NATURAL_EXACT or bool(_NATURAL_PATTERNS.search(n)) and not n.startswith("potted_")


def _is_tree_part(n):
    return n.endswith(("_log", "_wood", "_stem", "_hyphae")) and not n.startswith("stripped_")


def _plain(block):
    props = block.get("Properties") or {}
    return {"Name": str(block.get("Name", "minecraft:air")), "Properties": {k: str(v) for k, v in props.items()}}


def _slug(text):
    s = re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")
    return s or "ritaglio"


def extract_area(world, x1, z1, x2, z2, mode="costruzioni", include_trees=False, depth=16):
    """
    Cuts the area (inclusive world coordinates). Returns (Structure, info) or raises ValueError.
    """
    from structure_manager import Structure
    x1, x2 = sorted((x1, x2))
    z1, z2 = sorted((z1, z2))
    w, l = x2 - x1 + 1, z2 - z1 + 1
    if w * l > MAX_AREA:
        raise ValueError(f"Area troppo grande ({w}x{l}): il massimo e' 256x256 blocchi.")

    columns = {}       # (x, z) -> list of (y, block) from top to bottom
    grounds = {}       # (x, z) -> Y of the natural ground
    missing = 0
    data_version = None
    for x in range(x1, x2 + 1):
        for z in range(z1, z2 + 1):
            top = world.surface_y(x, z)
            if top is None:
                missing += 1
                continue
            if data_version is None:
                ed = world.editor(x >> 4, z >> 4)
                data_version = int(ed.nbt.get("DataVersion", 0)) or None
            col = []
            ground = None
            y = top
            while y >= -64:
                block = world.get_block(x, y, z)
                if block is None:
                    break
                name = short(str(block.get("Name", "minecraft:air")))
                col.append((y, block))
                if ground is None and name not in ("air", "cave_air", "void_air") and is_natural_terrain(name) \
                        and not _NATURAL_PATTERNS.search(name) and name not in ("snow", "water", "lava"):
                    ground = y
                if ground is not None and y <= ground - depth:
                    break
                y -= 1
            columns[(x, z)] = col
            if ground is not None:
                grounds[(x, z)] = ground
    if not columns:
        raise ValueError("L'area scelta non e' generata in questo mondo.")

    def built(col_index, col):
        """Is the block at col[col_index] part of a construction?"""
        y, block = col[col_index]
        name = short(str(block.get("Name", "minecraft:air")))
        if name in ("air", "cave_air", "void_air"):
            return False
        props = block.get("Properties") or {}
        if name.endswith("_leaves"):
            return str(props.get("persistent", "false")) == "true" or include_trees
        if _is_tree_part(name):
            if include_trees:
                return True
            # a trunk goes up into natural leaves; a post of a house goes into a roof
            for j in range(col_index - 1, -1, -1):
                above = short(str(col[j][1].get("Name", "")))
                if _is_tree_part(above):
                    continue
                return not (above.endswith("_leaves") and
                            str((col[j][1].get("Properties") or {}).get("persistent", "false")) != "true")
            return True
        return not is_natural_terrain(name)

    blocks = {}
    if mode == "tutto":
        y_lo = min(grounds.values()) - 2 if grounds else min(c[-1][0] for c in columns.values())
        y_hi = max(c[0][0] for c in columns.values())
        for (x, z), col in columns.items():
            for y, block in col:
                if y_lo <= y <= y_hi:
                    b = _plain(block)
                    if b["Name"].endswith("_leaves"):
                        b["Properties"]["persistent"] = "true"
                    blocks[(x - x1, y - y_lo, z - z1)] = b
    else:
        per_col = {}
        for key, col in columns.items():
            ys = [col[i][0] for i in range(len(col)) if built(i, col)]
            if ys:
                per_col[key] = (min(ys), max(ys))
        if not per_col:
            raise ValueError("Nell'area non ci sono costruzioni: prova la modalita' 'Tutto, terreno compreso'.")
        y_lo = min(lo for lo, _ in per_col.values())
        y_hi = max(hi for _, hi in per_col.values())
        for key, (lo, hi) in per_col.items():
            col = columns[key]
            for i, (y, block) in enumerate(col):
                if not lo <= y <= hi:
                    continue
                name = short(str(block.get("Name", "minecraft:air")))
                if built(i, col):
                    b = _plain(block)
                    if b["Name"].endswith("_leaves"):
                        b["Properties"]["persistent"] = "true"
                elif name in ("air", "cave_air", "void_air"):
                    b = {"Name": "minecraft:air", "Properties": {}}
                elif name == "water":
                    b = _plain(block)   # pools and fountains inside the build
                else:
                    continue            # natural terrain -> structure void
                blocks[(key[0] - x1, y - y_lo, key[1] - z1)] = b

    ground_list = sorted(grounds.values())
    median_ground = ground_list[len(ground_list) // 2] if ground_list else y_lo - 1
    ground_offset = max(0, median_ground + 1 - y_lo)
    struct = Structure(w, y_hi - y_lo + 1, l, blocks, data_version)
    struct.ground_offset = ground_offset
    info = {"blocks": sum(1 for b in blocks.values() if b["Name"] != "minecraft:air"), "missing_columns": missing,
            "y_range": (y_lo, y_hi), "ground_offset": ground_offset, "mode": mode}
    return struct, info


def save_structure(struct, path, extra=None):
    """Writes a Structure as a vanilla structure-block .nbt file (+ MinecraftBuilder metadata)."""
    palette, index, blocks = [], {}, []
    for (x, y, z) in sorted(struct.blocks, key=lambda p: (p[1], p[2], p[0])):
        b = struct.blocks[(x, y, z)]
        props = b.get("Properties") or {}
        key = (b["Name"], tuple(sorted((k, str(v)) for k, v in props.items())))
        if key not in index:
            index[key] = len(palette)
            entry = TAG_Compound({"Name": TAG_String(b["Name"])})
            if props:
                entry["Properties"] = TAG_Compound({k: TAG_String(str(v)) for k, v in sorted(props.items())})
            palette.append(entry)
        blocks.append(TAG_Compound({"pos": TAG_List(3, [TAG_Int(x), TAG_Int(y), TAG_Int(z)]),
                                    "state": TAG_Int(index[key])}))
    root = TAG_Compound()
    root["DataVersion"] = TAG_Int(struct.data_version or 3955)
    root["size"] = TAG_List(3, [TAG_Int(struct.width), TAG_Int(struct.height), TAG_Int(struct.length)])
    root["palette"] = TAG_List(10, palette)
    root["blocks"] = TAG_List(10, blocks)
    root["entities"] = TAG_List(10, [])
    meta = TAG_Compound({"groundOffset": TAG_Int(getattr(struct, "ground_offset", 0))})
    for k, v in (extra or {}).items():
        meta[k] = TAG_String(str(v))
    root["MinecraftBuilder"] = meta
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    save_nbt(root, "", path, compressed=True)
    return path


def unique_path(templates_dir, title):
    base = _slug(title)
    path = os.path.join(templates_dir, f"{base}.nbt")
    i = 2
    while os.path.exists(path):
        path = os.path.join(templates_dir, f"{base}_{i}.nbt")
        i += 1
    return path
