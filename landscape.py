"""
Natural ground around a structure pasted in a world.

A structure is placed at a height that rarely matches the terrain. This module reshapes the
land around it so that it looks made for that place:
- placed higher than the ground: a hill with an irregular edge rises to the structure, in the
  materials of the biome (grass, sand, snow, podzol, red sand...), rocky where it is steep, with
  grass, flowers, boulders and small trees; themed stairs lead from the doors down to the ground,
  following the slope, in the material of the structure, with lanterns along the way;
- placed lower than the ground (on a slope): the ground in front of it is cut back in terraces so
  the doors are free;
- placed on water: an island with a sandy beach that slopes gently under the water (sea grass,
  sugar cane, palms in warm biomes). Boats and underwater structures are not touched: they float
  at the chosen depth.

survey() reads the terrain before the structure is placed; shape() changes it afterwards.
Every block written goes through world.set_block, so the usual save/backup/undo apply.
"""
import math

from mca_codec import AIR_NAMES

MAX_GAP = 48            # higher than this the structure is meant to float (sky islands): no hill
MAX_AREA = 400_000      # structures with a larger footprint keep the plain foundations
MAX_CUT = 14            # deepest terrace cut into a slope

# ---------------------------------------------------------------------------
# Biomes
# ---------------------------------------------------------------------------


def biome_at(world, x, y, z):
    """Biome id ("minecraft:plains") at a block, read from the chunk's biome palette, or None."""
    ed = world.editor(x >> 4, z >> 4)
    if ed is None:
        return None
    sy = y >> 4
    for s in ed.nbt.get("sections") or []:
        if int(s.get("Y", 0)) != sy:
            continue
        b = s.get("biomes") or {}
        palette = b.get("palette") or []
        if not palette:
            return None
        names = [str(p if isinstance(p, str) else p.get("Name", p.get("", ""))) for p in palette]
        data = b.get("data")
        if len(names) == 1 or not data:
            return names[0]
        bits = max(1, (len(names) - 1).bit_length())
        per = 64 // bits
        i = (((y & 15) >> 2) << 4) | (((z & 15) >> 2) << 2) | ((x & 15) >> 2)
        q, r = divmod(i, per)
        if q >= len(data):
            return names[0]
        idx = ((data[q] & 0xFFFFFFFFFFFFFFFF) >> (r * bits)) & ((1 << bits) - 1)
        return names[idx] if idx < len(names) else names[0]
    return None


# Look of the land per family of biomes
_THEMES = {
    "plains": dict(top="grass_block", sub="dirt", deep="stone", rock=("stone", "andesite", "cobblestone"),
                   flowers=("dandelion", "poppy", "oxeye_daisy", "cornflower", "azure_bluet"),
                   grass=0.30, tall=0.05, flower=0.06, fern=0.0, bush=0.01, tree="oak", trees=0.010, boulder=0.004),
    "forest": dict(top="grass_block", sub="dirt", deep="stone", rock=("stone", "mossy_cobblestone", "andesite"),
                   flowers=("lily_of_the_valley", "poppy", "dandelion"),
                   grass=0.30, tall=0.06, flower=0.03, fern=0.03, bush=0.02, tree="oak", trees=0.025, boulder=0.005),
    "birch": dict(top="grass_block", sub="dirt", deep="stone", rock=("stone", "andesite"),
                  flowers=("lily_of_the_valley", "allium", "dandelion"),
                  grass=0.30, tall=0.05, flower=0.04, fern=0.02, bush=0.01, tree="birch", trees=0.025, boulder=0.004),
    "flower": dict(top="grass_block", sub="dirt", deep="stone", rock=("stone", "andesite"),
                   flowers=("allium", "azure_bluet", "red_tulip", "orange_tulip", "pink_tulip", "oxeye_daisy",
                            "cornflower", "lily_of_the_valley", "poppy", "dandelion"),
                   grass=0.15, tall=0.03, flower=0.30, fern=0.0, bush=0.01, tree="birch", trees=0.012, boulder=0.0),
    "taiga": dict(top="podzol", top2="grass_block", sub="dirt", deep="stone", rock=("mossy_cobblestone", "cobblestone",
                                                                                     "stone"),
                  flowers=("sweet_berry_bush",), grass=0.15, tall=0.0, flower=0.02, fern=0.20, bush=0.0,
                  tree="spruce", trees=0.025, boulder=0.010),
    "snowy": dict(top="grass_block", top_props={"snowy": "true"}, sub="dirt", deep="stone",
                  rock=("stone", "cobblestone", "packed_ice"), flowers=(), grass=0.0, tall=0.0, flower=0.0,
                  fern=0.03, bush=0.0, tree="spruce", trees=0.012, boulder=0.004, snow=True),
    "desert": dict(top="sand", sub="sand", deep="sandstone", rock=("sandstone", "smooth_sandstone", "cut_sandstone"),
                   flowers=("dead_bush",), grass=0.0, tall=0.0, flower=0.02, fern=0.0, bush=0.0, tree="cactus",
                   trees=0.006, boulder=0.003, warm=True),
    "badlands": dict(top="red_sand", sub="terracotta", deep="terracotta",
                     rock=("terracotta", "orange_terracotta", "brown_terracotta", "yellow_terracotta"),
                     flowers=("dead_bush",), grass=0.0, tall=0.0, flower=0.02, fern=0.0, bush=0.0, tree="cactus",
                     trees=0.003, boulder=0.004, warm=True),
    "savanna": dict(top="grass_block", top2="coarse_dirt", sub="dirt", deep="stone", rock=("stone", "andesite"),
                    flowers=("dandelion", "poppy"), grass=0.35, tall=0.10, flower=0.01, fern=0.0, bush=0.0,
                    tree="acacia", trees=0.008, boulder=0.003, warm=True),
    "jungle": dict(top="grass_block", sub="dirt", deep="stone", rock=("mossy_cobblestone", "stone"),
                   flowers=("poppy", "dandelion"), grass=0.30, tall=0.08, flower=0.01, fern=0.12, bush=0.06,
                   tree="jungle", trees=0.020, boulder=0.004, warm=True),
    "swamp": dict(top="grass_block", top2="mud", sub="dirt", deep="clay", rock=("mud_bricks", "mossy_cobblestone"),
                  flowers=("blue_orchid",), grass=0.25, tall=0.05, flower=0.03, fern=0.03, bush=0.0, tree="oak",
                  trees=0.010, boulder=0.0),
    "cherry": dict(top="grass_block", sub="dirt", deep="stone", rock=("stone", "andesite"),
                   flowers=("pink_petals",), grass=0.20, tall=0.02, flower=0.25, fern=0.0, bush=0.0, tree="cherry",
                   trees=0.015, boulder=0.003),
    "mushroom": dict(top="mycelium", sub="dirt", deep="stone", rock=("stone",), flowers=("red_mushroom",
                                                                                       "brown_mushroom"),
                     grass=0.0, tall=0.0, flower=0.04, fern=0.0, bush=0.0, tree=None, trees=0.0, boulder=0.0),
    "peaks": dict(top="stone", top2="gravel", sub="stone", deep="stone", rock=("stone", "andesite", "gravel", "tuff"),
                  flowers=(), grass=0.0, tall=0.0, flower=0.0, fern=0.0, bush=0.0, tree=None, trees=0.0,
                  boulder=0.006),
    "beach": dict(top="sand", sub="sand", deep="sandstone", rock=("sandstone", "smooth_sandstone"),
                  flowers=(), grass=0.0, tall=0.0, flower=0.0, fern=0.0, bush=0.0, tree="palm", trees=0.004,
                  boulder=0.0, warm=True),
    "nether": dict(top="netherrack", sub="netherrack", deep="netherrack", rock=("blackstone", "basalt"),
                   flowers=("crimson_fungus", "crimson_roots"), grass=0.0, tall=0.0, flower=0.05, fern=0.0, bush=0.0,
                   tree=None, trees=0.0, boulder=0.003),
    "end": dict(top="end_stone", sub="end_stone", deep="end_stone", rock=("end_stone_bricks",), flowers=(),
                grass=0.0, tall=0.0, flower=0.0, fern=0.0, bush=0.0, tree=None, trees=0.0, boulder=0.0),
}


def theme_of(biome):
    b = (biome or "minecraft:plains").split(":", 1)[-1]
    if b.startswith(("nether", "crimson", "warped", "soul_sand", "basalt")):
        return "nether"
    if b.startswith(("the_end", "end_", "small_end", "end")) or b == "the_void":
        return "end"
    if "badlands" in b:
        return "badlands"
    if "desert" in b:
        return "desert"
    if any(k in b for k in ("snowy", "frozen", "ice_spikes", "grove", "jagged", "frozen_peaks")):
        return "snowy"
    if any(k in b for k in ("stony", "peaks", "windswept_gravelly")):
        return "peaks"
    if "taiga" in b or "old_growth" in b:
        return "taiga"
    if "savanna" in b:
        return "savanna"
    if "jungle" in b or "bamboo" in b:
        return "jungle"
    if "swamp" in b or "mangrove" in b:
        return "swamp"
    if "cherry" in b:
        return "cherry"
    if "mushroom" in b:
        return "mushroom"
    if "flower" in b or "meadow" in b or "sunflower" in b:
        return "flower"
    if "birch" in b:
        return "birch"
    if "forest" in b:
        return "forest"
    if "beach" in b or b in ("warm_ocean", "lukewarm_ocean", "deep_lukewarm_ocean"):
        return "beach"
    return "plains"


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------

def _st(name, **props):
    from nbt_codec import TAG_Compound, TAG_String
    state = TAG_Compound({"Name": TAG_String(name if ":" in name else "minecraft:" + name)})
    if props:
        state["Properties"] = TAG_Compound({k: TAG_String(str(v)) for k, v in props.items()})
    return state


def _hash(x, z, salt=0):
    """Deterministic pseudo random number in [0, 1) for a column (same world, same result)."""
    h = (x * 374761393 + z * 668265263 + salt * 2147483647) & 0xFFFFFFFF
    h = ((h ^ (h >> 13)) * 1274126177) & 0xFFFFFFFF
    return ((h ^ (h >> 16)) & 0xFFFFFF) / float(0x1000000)


def _noise(x, z, scale, salt=0):
    """Smooth value noise in [-1, 1]."""
    fx, fz = x / scale, z / scale
    x0, z0 = math.floor(fx), math.floor(fz)
    tx, tz = fx - x0, fz - z0
    tx, tz = tx * tx * (3 - 2 * tx), tz * tz * (3 - 2 * tz)
    a = _hash(x0, z0, salt)
    b = _hash(x0 + 1, z0, salt)
    c = _hash(x0, z0 + 1, salt)
    d = _hash(x0 + 1, z0 + 1, salt)
    return (a + (b - a) * tx + (c - a) * tz + (a - b - c + d) * tx * tz) * 2 - 1


_PLANTS = ("short_grass", "tall_grass", "fern", "large_fern", "flower", "tulip", "poppy", "dandelion", "orchid",
           "allium", "bluet", "daisy", "cornflower", "lily_of", "sapling", "dead_bush", "sweet_berry", "petals",
           "mushroom", "seagrass", "kelp", "snow", "vine", "bush", "leaf_litter", "wildflowers", "roots")


def _is_soft(name):
    """Blocks the new ground may replace: air, water, plants, snow layers."""
    if name is None:
        return False
    if name in AIR_NAMES:
        return True
    short = name.split(":", 1)[-1]
    if short in ("water", "bubble_column", "snow"):
        return True
    return any(p in short for p in _PLANTS) and not short.endswith("_block")


def _is_terrain(name):
    from world_extractor import is_natural_terrain
    return name is not None and name not in AIR_NAMES and is_natural_terrain(name)


# ---------------------------------------------------------------------------
# Survey (before placing) and shaping (after)
# ---------------------------------------------------------------------------

class Site:
    """The terrain around a placement as it was before the structure went in."""

    def __init__(self, x0, z0, w, l):
        self.x0, self.z0, self.w, self.l = x0, z0, w, l
        n = w * l
        self.ground = [None] * n      # top solid block Y (None: not generated)
        self.water = [None] * n       # Y of the water surface where the column is water, else None
        self.natural = bytearray(n)   # 1 if the top of the column is natural terrain (may be reshaped)
        self.surface = [None] * n     # name of the top solid block
        self.biome = None
        self.water_level = None

    def idx(self, x, z):
        x -= self.x0
        z -= self.z0
        if 0 <= x < self.w and 0 <= z < self.l:
            return z * self.w + x
        return None


def footprint_of(struct):
    """{(x, z): lowest non-air y} of a structure (structure coordinates), or None if too big."""
    blocks = struct.blocks
    if getattr(blocks, "packed", False) or struct.width * struct.length > MAX_AREA:
        return None
    low = {}
    for (x, y, z), b in blocks.items():
        if b.get("Name", "minecraft:air").split(":", 1)[-1] in ("air", "cave_air", "structure_void"):
            continue
        if y < low.get((x, z), 1 << 30):
            low[(x, z)] = y
    return low


def plan_for(struct, oy, low):
    """Height of the ground the structure stands on (world Y of the top ground block)."""
    base = min(low.values()) if low else 0
    level = max(int(getattr(struct, "ground_offset", 0) or 0), base) - 1
    return oy + level


def survey(world, ox, oz, struct, oy, low, radius=None):
    """Reads the land around a placement before the structure is placed."""
    g0 = plan_for(struct, oy, low)
    if radius is None:
        # wide enough for the slope down from the structure (and a beach and sea bed on water)
        lowest = g0
        for x in (ox - 4, ox + struct.width // 2, ox + struct.width + 3):
            for z in (oz - 4, oz + struct.length // 2, oz + struct.length + 3):
                top = world.surface_y(x, z)
                if top is not None:
                    lowest = min(lowest, top)
        radius = max(8, min(64, int((g0 - lowest) / 0.65) + 14))
    w, l = struct.width + 2 * radius, struct.length + 2 * radius
    site = Site(ox - radius, oz - radius, w, l)
    site.g0, site.radius = g0, radius
    site.box = (ox, oz, ox + struct.width - 1, oz + struct.length - 1)
    levels = {}
    for z in range(site.z0, site.z0 + l):
        for x in range(site.x0, site.x0 + w):
            top = world.surface_y(x, z)
            if top is None:
                continue
            i = (z - site.z0) * w + x - site.x0
            y = top
            water_top = None
            while y > top - 64:
                name = world.get_block_name(x, y, z)
                if name is None:
                    break
                short = name.split(":", 1)[-1]
                if short in ("water", "bubble_column") or "seagrass" in short or "kelp" in short:
                    if water_top is None:
                        water_top = y
                    y -= 1
                    continue
                if _is_soft(name) or short.endswith("_leaves") or short.endswith(("_log", "_wood")):
                    y -= 1
                    continue
                site.ground[i] = y
                site.surface[i] = name
                site.natural[i] = 1 if _is_terrain(name) else 0
                break
            if water_top is not None:
                site.water[i] = water_top
                levels[water_top] = levels.get(water_top, 0) + 1
    if levels:
        site.water_level = max(levels, key=levels.get)
    cx, cz = (site.box[0] + site.box[2]) // 2, (site.box[1] + site.box[3]) // 2
    site.biome = biome_at(world, cx, max(g0, -60), cz)
    return site


def on_water(site, low, ox, oz):
    """Share of the structure's columns that stand over water."""
    if not low:
        return 0.0
    wet = 0
    for (x, z) in low:
        i = site.idx(ox + x, oz + z)
        if i is not None and site.water[i] is not None:
            wet += 1
    return wet / len(low)


class _Writer:
    def __init__(self, world, stats):
        self.world, self.stats = world, stats
        self.cache = {}

    def put(self, x, y, z, name, **props):
        key = (name, tuple(sorted(props.items())))
        st = self.cache.get(key)
        if st is None:
            st = self.cache[key] = _st(name, **props)
        if self.world.set_block(x, y, z, st):
            self.stats["landscape"] = self.stats.get("landscape", 0) + 1
            return True
        return False

    def put_mat(self, x, y, z, mat):
        return self.put(x, y, z, mat[0], **(mat[1] if len(mat) > 1 else {}))


def shape(world, item, site, low, stats, log=None):
    """
    Reshapes the land around a placed structure (see the module doc). item: the placement dict
    (structure, world_x, y_coord, world_z, water_mode "island"/"float").
    """
    log = log or (lambda m: None)
    struct = item["structure"]
    ox, oy, oz = item["world_x"], item["y_coord"], item["world_z"]
    g0 = site.g0
    theme_name = theme_of(site.biome)
    th = _THEMES[theme_name]
    out = _Writer(world, stats)
    W = site.water_level
    wet_share = on_water(site, low, ox, oz)
    if wet_share >= 0.3 and item.get("water_mode") == "float":
        dry = drain_hull(world, item, W, stats) if W is not None else 0
        log("Struttura galleggiante: il terreno intorno resta com'e'"
            + (f", {dry} blocchi d'acqua tolti dallo scafo." if dry else "."))
        return
    gaps = [g0 - site.ground[i] for i in range(len(site.ground)) if site.ground[i] is not None]
    if not gaps:
        return
    under = [g0 - site.ground[site.idx(ox + x, oz + z)] for (x, z) in low
             if site.idx(ox + x, oz + z) is not None and site.ground[site.idx(ox + x, oz + z)] is not None]
    max_gap = max(under) if under else 0
    if max_gap > MAX_GAP:
        log(f"La struttura sta {max_gap} blocchi sopra il terreno: la lascio sospesa (niente collina).")
        return
    island = W is not None and wet_share >= 0.3
    beach_level = min(g0, W + 1) if W is not None else None
    # gentle hills for small heights, steeper ones when the structure is high up (or they get huge)
    slope = 0.45 if max_gap <= 12 else 0.6 if max_gap <= 24 else 0.8
    x1, z1, x2, z2 = site.box

    def dist(x, z):
        dx = max(x1 - x, 0, x - x2)
        dz = max(z1 - z, 0, z - z2)
        return math.hypot(dx, dz)

    def profile(x, z):
        """(height of the reshaped ground outside the structure, sandy?) for a column."""
        # the distance is stretched by a broad noise: the hill gets lobes and bays, not a rectangle
        d = dist(x, z)
        d *= 1 + 0.28 * _noise(x, z, 16, 21) + 0.1 * _noise(x, z, 6, 22)
        h = g0 - slope * max(0.0, d - 1)
        sandy = False
        if W is not None and beach_level is not None and g0 >= W:
            # the land goes down to the beach, the beach stays dry for a few blocks, then the sea bed
            d_shore = (g0 - beach_level) / slope + 1
            beach = 3 + 3 * (_noise(x, z, 9, 7) + 1) / 2 if island else 2
            if d > d_shore:
                h = beach_level if d <= d_shore + beach else beach_level - 0.3 * (d - d_shore - beach)
            # an island keeps a grassy heart; the last blocks before the water are sand
            sandy = d > d_shore + (beach - 2.5 if island else -1.5) + _noise(x, z, 4, 8)
        jag = min(2.0, 0.15 * d) * _noise(x, z, 9, 1) + min(0.8, 0.08 * d) * _noise(x, z, 4, 2)
        return h + jag, sandy

    # 1. the target height of every column
    target = [None] * len(site.ground)
    sand = bytearray(len(site.ground))
    for z in range(site.z0, site.z0 + site.l):
        for x in range(site.x0, site.x0 + site.w):
            i = (z - site.z0) * site.w + x - site.x0
            g = site.ground[i]
            if g is None:
                continue
            if x1 <= x <= x2 and z1 <= z <= z2:
                lo = low.get((x - ox, z - oz))
                t = g0 if lo is None else min(g0, oy + lo - 1)
                sand[i] = 1 if island and W is not None and g0 <= W + 1 else 0
            else:
                h, sandy = profile(x, z)
                t = int(round(h))
                sand[i] = 1 if sandy or (W is not None and t <= W) else 0
            target[i] = t

    def tgt(x, z):
        i = site.idx(x, z)
        return None if i is None else target[i]

    # 2. raise the ground (hill / island) and cut terraces where the slope buries the doors
    raised = bytearray(len(target))
    for z in range(site.z0, site.z0 + site.l):
        for x in range(site.x0, site.x0 + site.w):
            i = (z - site.z0) * site.w + x - site.x0
            g, t = site.ground[i], target[i]
            if g is None or t is None:
                continue
            inside = x1 <= x <= x2 and z1 <= z <= z2
            if t > g:
                if not inside and not site.natural[i] and site.water[i] is None:
                    continue                   # another construction: left alone
                steep = max(abs((tgt(x + 1, z) or t) - (tgt(x - 1, z) or t)),
                            abs((tgt(x, z + 1) or t) - (tgt(x, z - 1) or t)))
                for y in range(g + 1, t + 1):
                    name = world.get_block_name(x, y, z)
                    if not inside and not _is_soft(name):
                        break
                    if inside and name is not None and not _is_soft(name):
                        continue               # the structure itself
                    out.put_mat(x, y, z, _material(th, t - y, y, W, steep, x, z, inside, sand[i]))
                raised[i] = 1
            elif t < g and not inside and site.natural[i] and site.water[i] is None:
                d = dist(x, z)
                if d > 4 or g - t > MAX_CUT:
                    continue
                cut_to = max(t, g0 + int(max(0.0, d - 1.5)))
                if cut_to >= g:
                    continue
                # only bare ground and plants above it: never undermine trees or buildings
                if any(not (_is_soft(world.get_block_name(x, y, z)) or _is_terrain(world.get_block_name(x, y, z)))
                       for y in range(cut_to + 1, g + 4)):
                    continue
                for y in range(cut_to + 1, g + 4):
                    world.set_block(x, y, z, _st("air"))
                out.put_mat(x, cut_to, z, _material(th, 0, cut_to, W, 0, x, z, False, False))
                target[i] = cut_to
                raised[i] = 1

    # 3. stairs from the doors (or one side) down to the ground
    reserved = set()
    flights = _stairs(world, item, site, low, target, out, reserved, th, W)
    # 4. plants, boulders, trees on the new land
    _decorate(world, site, target, raised, reserved, out, th, theme_name, island, W, dist)
    what = "isola con spiaggia" if island else "collina naturale" if max_gap >= 2 else "raccordo col terreno"
    log(f"Terreno adattato ({what}, bioma {(site.biome or '?').split(':')[-1]}): "
        f"{stats.get('landscape', 0)} blocchi" + (f", {flights} scalinate" if flights else "") + ".")


def drain_hull(world, item, W, stats):
    """
    A boat put in the water deeper than its bottom: the water left inside the hull (closed in by
    the structure's blocks, layer by layer, below the water level) becomes air. Returns the count.
    """
    from collections import deque
    struct = item["structure"]
    ox, oy, oz = item["world_x"], item["y_coord"], item["world_z"]
    w, l = struct.width, struct.length
    layers = {}
    for (x, y, z), b in struct.blocks.items():
        if oy + y <= W and not b.get("Name", "").endswith(("air", "water")):
            layers.setdefault(y, set()).add((x, z))
    air = _st("air")
    dried = 0
    for y, solid in layers.items():
        outside = set()
        todo = deque()
        for x in range(-1, w + 1):
            for z in (-1, l):
                todo.append((x, z))
        for z in range(l):
            todo.extend(((-1, z), (w, z)))
        while todo:
            c = todo.popleft()
            if c in outside or c in solid:
                continue
            x, z = c
            if not (-1 <= x <= w and -1 <= z <= l):
                continue
            outside.add(c)
            todo.extend(((x + 1, z), (x - 1, z), (x, z + 1), (x, z - 1)))
        for x in range(w):
            for z in range(l):
                if (x, z) in solid or (x, z) in outside:
                    continue
                name = world.get_block_name(ox + x, oy + y, oz + z) or ""
                if name.endswith(("water", "seagrass", "kelp", "kelp_plant", "bubble_column")):
                    if world.set_block(ox + x, oy + y, oz + z, air):
                        dried += 1
    stats["landscape"] = stats.get("landscape", 0) + dried
    return dried


def _material(th, k, y, W, steep, x, z, inside, sandy=False):
    """(block, props) for the block k layers under the top of a raised column."""
    under_water = W is not None and y <= W
    if under_water and k == 0 or (under_water and k < 3):
        r = _hash(x, z, 31)
        return ("gravel",) if r < 0.15 else ("clay",) if r < 0.2 else ("sand",)
    if k == 0:
        if steep >= 3 and not inside:
            rock = th["rock"]
            return (rock[int(_hash(x, z, 11) * len(rock)) % len(rock)],)
        if sandy and th["top"] not in ("netherrack", "end_stone"):
            return ("sand",)                   # the beach
        if th.get("top2") and _noise(x, z, 5, 4) > 0.35:
            return (th["top2"],)
        return (th["top"],) + ((th["top_props"],) if th.get("top_props") else ())
    if k <= 3:
        return ("sand",) if sandy else (th["sub"],)
    return (th["deep"],)


# ---------------------------------------------------------------------------
# Stairs
# ---------------------------------------------------------------------------

_DIRS = {"north": (0, -1), "south": (0, 1), "west": (-1, 0), "east": (1, 0)}
_OPPOSITE = {"north": "south", "south": "north", "west": "east", "east": "west"}
# full block -> (stairs, slab, wall or fence) of the same material
_MATERIALS = {
    "stone_bricks": ("stone_brick_stairs", "stone_brick_slab", "stone_brick_wall"),
    "mossy_stone_bricks": ("mossy_stone_brick_stairs", "mossy_stone_brick_slab", "mossy_stone_brick_wall"),
    "cobblestone": ("cobblestone_stairs", "cobblestone_slab", "cobblestone_wall"),
    "mossy_cobblestone": ("mossy_cobblestone_stairs", "mossy_cobblestone_slab", "mossy_cobblestone_wall"),
    "stone": ("stone_stairs", "stone_slab", "cobblestone_wall"),
    "bricks": ("brick_stairs", "brick_slab", "brick_wall"),
    "sandstone": ("sandstone_stairs", "sandstone_slab", "sandstone_wall"),
    "cut_sandstone": ("sandstone_stairs", "cut_sandstone_slab", "sandstone_wall"),
    "smooth_sandstone": ("smooth_sandstone_stairs", "smooth_sandstone_slab", "sandstone_wall"),
    "red_sandstone": ("red_sandstone_stairs", "red_sandstone_slab", "red_sandstone_wall"),
    "quartz_block": ("quartz_stairs", "quartz_slab", "diorite_wall"),
    "smooth_quartz": ("smooth_quartz_stairs", "smooth_quartz_slab", "diorite_wall"),
    "polished_andesite": ("polished_andesite_stairs", "polished_andesite_slab", "andesite_wall"),
    "andesite": ("andesite_stairs", "andesite_slab", "andesite_wall"),
    "polished_diorite": ("polished_diorite_stairs", "polished_diorite_slab", "diorite_wall"),
    "polished_granite": ("polished_granite_stairs", "polished_granite_slab", "granite_wall"),
    "deepslate_bricks": ("deepslate_brick_stairs", "deepslate_brick_slab", "deepslate_brick_wall"),
    "deepslate_tiles": ("deepslate_tile_stairs", "deepslate_tile_slab", "deepslate_tile_wall"),
    "polished_deepslate": ("polished_deepslate_stairs", "polished_deepslate_slab", "polished_deepslate_wall"),
    "cobbled_deepslate": ("cobbled_deepslate_stairs", "cobbled_deepslate_slab", "cobbled_deepslate_wall"),
    "blackstone": ("blackstone_stairs", "blackstone_slab", "blackstone_wall"),
    "polished_blackstone_bricks": ("polished_blackstone_brick_stairs", "polished_blackstone_brick_slab",
                                   "polished_blackstone_brick_wall"),
    "mud_bricks": ("mud_brick_stairs", "mud_brick_slab", "mud_brick_wall"),
    "prismarine_bricks": ("prismarine_brick_stairs", "prismarine_brick_slab", "prismarine_wall"),
    "end_stone_bricks": ("end_stone_brick_stairs", "end_stone_brick_slab", "end_stone_brick_wall"),
    "nether_bricks": ("nether_brick_stairs", "nether_brick_slab", "nether_brick_fence"),
    "tuff_bricks": ("tuff_brick_stairs", "tuff_brick_slab", "tuff_brick_wall"),
    "purpur_block": ("purpur_stairs", "purpur_slab", "end_stone_brick_wall"),
}
for _wood in ("oak", "spruce", "birch", "jungle", "acacia", "dark_oak", "mangrove", "cherry", "bamboo",
              "crimson", "warped", "pale_oak"):
    _MATERIALS[f"{_wood}_planks"] = (f"{_wood}_stairs", f"{_wood}_slab", f"{_wood}_fence")
_STAIRS_TO_BLOCK = {v[0]: k for k, v in _MATERIALS.items()}
_THEME_STAIRS = {"desert": "sandstone", "badlands": "red_sandstone", "snowy": "spruce_planks",
                 "taiga": "spruce_planks", "jungle": "jungle_planks", "savanna": "acacia_planks",
                 "swamp": "mud_bricks", "cherry": "cherry_planks", "beach": "smooth_sandstone",
                 "nether": "nether_bricks", "end": "end_stone_bricks", "peaks": "cobblestone",
                 "mushroom": "cobblestone"}


def stair_material(struct, theme_name):
    """Full block of the stairs: the stairs the structure uses most, else its main material, else the biome's."""
    stairs, blocks = {}, {}
    for b in struct.blocks.values():
        n = b.get("Name", "").split(":", 1)[-1]
        if n in _STAIRS_TO_BLOCK:
            stairs[n] = stairs.get(n, 0) + 1
        elif n in _MATERIALS:
            blocks[n] = blocks.get(n, 0) + 1
    if stairs:
        return _STAIRS_TO_BLOCK[max(stairs, key=stairs.get)]
    if blocks:
        return max(blocks, key=blocks.get)
    return _THEME_STAIRS.get(theme_name, "stone_bricks")


def _entrances(struct, low, g0, oy):
    """(x, z, direction) of the doors on the outside of the structure, structure coordinates."""
    out = []
    w, l = struct.width, struct.length
    floor = g0 - oy + 1                 # structure y of the floor a door stands on
    for (x, y, z), b in struct.blocks.items():
        n = b.get("Name", "")
        if not n.endswith("_door") or (b.get("Properties") or {}).get("half") == "upper":
            continue
        if not floor - 1 <= y <= floor + 1:
            continue
        for d, (dx, dz) in _DIRS.items():
            # outward: the edge of the footprint in that direction is close and the way there is free
            steps = (w - 1 - x) if dx > 0 else x if dx < 0 else (l - 1 - z) if dz > 0 else z
            if steps > 3:
                continue
            free = True
            for k in range(1, steps + 1):
                lo = low.get((x + dx * k, z + dz * k))
                if lo is not None and lo <= y + 1:
                    free = False
                    break
            if free:
                out.append((x, z, d))
    # doors next to each other (double doors) count once
    result = []
    for x, z, d in sorted(out, key=lambda t: (t[2], t[0] if t[2] in ("north", "south") else t[1])):
        along = x if d in ("north", "south") else z
        if any(d2 == d and abs((x2 if d2 in ("north", "south") else z2) - along) <= 2 for x2, z2, d2 in result):
            continue
        result.append((x, z, d))
    return result[:4]


def _stairs(world, item, site, low, target, out, reserved, th, W):
    struct = item["structure"]
    ox, oy, oz = item["world_x"], item["y_coord"], item["world_z"]
    g0 = site.g0
    x1, z1, x2, z2 = site.box
    theme_name = theme_of(site.biome)
    block = stair_material(struct, theme_name)
    stairs_name, _slab, post = _MATERIALS.get(block, _MATERIALS["stone_bricks"])
    doors = _entrances(struct, low, g0, oy)
    if not doors:
        # no door on the outside: one flight on the side where the ground is closest
        best = None
        for d, (dx, dz) in _DIRS.items():
            mx = (x1 + x2) // 2 if dx == 0 else (x2 if dx > 0 else x1)
            mz = (z1 + z2) // 2 if dz == 0 else (z2 if dz > 0 else z1)
            i = site.idx(mx + dx * 3, mz + dz * 3)
            if i is None or site.ground[i] is None:
                continue
            drop = g0 - site.ground[i]
            if site.water[i] is not None:
                drop += 50                     # never towards the sea when there is land
            if best is None or drop < best[0]:
                best = (drop, mx - ox, mz - oz, d)
        if best is None:
            return 0
        doors = [(best[1], best[2], best[3])]
    width = 3 if min(struct.width, struct.length) >= 9 else 1
    flights = 0
    for sx, sz, d in doors:
        dx, dz = _DIRS[d]
        px, pz = -dz, dx                     # across the flight
        # start at the first column outside the footprint
        cx, cz = ox + sx, oz + sz
        while x1 <= cx <= x2 and z1 <= cz <= z2:
            cx, cz = cx + dx, cz + dz
        h_prev = g0
        cells = []
        for k in range(80):
            x, z = cx + dx * k, cz + dz * k
            i = site.idx(x, z)
            if i is None or site.ground[i] is None:
                break
            t = target[i] if target[i] is not None else site.ground[i]
            if site.water[i] is not None:
                if W is None or t <= W:
                    break                      # the stairs end on the beach, never in the sea
                ground = t                     # the new beach is the ground here
            else:
                ground = site.ground[i]
            h = max(min(t, h_prev), h_prev - 1)
            cells.append((x, z, h, h < h_prev))
            h_prev = h
            if h <= ground and k >= 1:
                for e in (1, 2):              # a short path on the ground at the bottom
                    xe, ze = x + dx * e, z + dz * e
                    ie = site.idx(xe, ze)
                    if ie is None or site.ground[ie] is None or site.water[ie] is not None:
                        break
                    cells.append((xe, ze, site.ground[ie], False))
                break
        if len(cells) < 2 or not any(step for *_, step in cells):
            continue
        flights += 1
        facing = _OPPOSITE[d]                # stairs face up the flight, towards the structure
        half = width // 2
        for n, (x, z, h, step) in enumerate(cells):
            for o in range(-half, half + 1):
                bx, bz = x + px * o, z + pz * o
                if x1 <= bx <= x2 and z1 <= bz <= z2:
                    continue
                reserved.add((bx, bz))
                # support under the step, then the step or a paved block
                ib = site.idx(bx, bz)
                g = site.ground[ib] if ib is not None and site.ground[ib] is not None else h - 4
                for y in range(min(g, h) + 1, h):
                    name = world.get_block_name(bx, y, bz)
                    if _is_soft(name):
                        out.put(bx, y, bz, th["sub"] if W is None or y > W else "sand")
                out.put(bx, h, bz, block)
                top = h
                if step:
                    out.put(bx, h + 1, bz, stairs_name, facing=facing, half="bottom", shape="straight",
                            waterlogged="false")
                    top = h + 1
                for y in range(top + 1, top + 4):
                    name = world.get_block_name(bx, y, bz)
                    if name is not None and name not in AIR_NAMES and (_is_soft(name) or _is_terrain(name)
                                                                       or name.endswith("_leaves")):
                        world.set_block(bx, y, bz, _st("air"))
            # lanterns on posts every 6 steps, alternating sides
            if n % 6 == 3 and n < len(cells) - 1:
                side = 1 if (n // 6) % 2 == 0 else -1
                lx, lz = x + px * (half + 1) * side, z + pz * (half + 1) * side
                il = site.idx(lx, lz)
                if il is not None and target[il] is not None and site.water[il] is None \
                        and not (x1 <= lx <= x2 and z1 <= lz <= z2):
                    ly = max(target[il], h)
                    if _is_soft(world.get_block_name(lx, ly + 1, lz)):
                        out.put(lx, ly + 1, lz, post)
                        out.put(lx, ly + 2, lz, "lantern", hanging="false", waterlogged="false")
                        reserved.add((lx, lz))
    return flights


# ---------------------------------------------------------------------------
# Plants, boulders, trees
# ---------------------------------------------------------------------------

def _decorate(world, site, target, raised, reserved, out, th, theme_name, island, W, dist):
    x1, z1, x2, z2 = site.box
    trees = []
    for z in range(site.z0, site.z0 + site.l):
        for x in range(site.x0, site.x0 + site.w):
            i = (z - site.z0) * site.w + x - site.x0
            if not raised[i] or (x, z) in reserved or (x1 <= x <= x2 and z1 <= z <= z2):
                continue
            t = target[i]
            name_top = world.get_block_name(x, t, z) or ""
            above = world.get_block_name(x, t + 1, z)
            if above is None or above not in AIR_NAMES and not above.endswith("water"):
                continue
            d = dist(x, z)
            r = _hash(x, z, 5)
            short = name_top.split(":", 1)[-1]
            if above.endswith("water"):
                # under water: sea grass and pickles in the shallows
                if W is not None and W - t <= 6:
                    if r < 0.25:
                        out.put(x, t + 1, z, "seagrass")
                    elif r < 0.27 and th.get("warm"):
                        out.put(x, t + 1, z, "sea_pickle", pickles=str(1 + int(r * 400) % 4), waterlogged="true")
                continue
            if short == "sand" and W is not None and t == W + 1 or (short == "sand" and t == W):
                # shoreline: sugar cane next to the water
                if r < 0.04 and any(site.idx(x + a, z + b) is not None and site.water[site.idx(x + a, z + b)]
                                    is not None and target[site.idx(x + a, z + b)] is not None
                                    and target[site.idx(x + a, z + b)] < t
                                    for a, b in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                    for k in range(1, 2 + int(r * 30) % 3):
                        out.put(x, t + k, z, "sugar_cane", age="0")
                    continue
            if th.get("snow"):
                out.put(x, t + 1, z, "snow", layers="1")
                continue
            if short in ("sand", "red_sand"):
                if d >= 3 and r < th["trees"] * 1.5 and (island and th.get("warm") or th["tree"] == "cactus"):
                    trees.append((x, t + 1, z))
                elif r < 0.03 and theme_name in ("desert", "badlands", "beach"):
                    out.put(x, t + 1, z, "dead_bush")
                continue
            if short in ("stone", "andesite", "cobblestone", "gravel", "tuff", "mossy_cobblestone", "sandstone",
                         "terracotta") and not short.endswith("sand"):
                continue                      # bare rock
            if d >= 3 and r < th["trees"] * 0.45 and th.get("tree"):
                trees.append((x, t + 1, z))
                continue
            if d >= 2 and th["trees"] * 0.45 <= r < th["trees"] * 0.45 + th["boulder"]:
                rock = th["rock"]
                out.put(x, t + 1, z, rock[int(_hash(x, z, 9) * len(rock)) % len(rock)])
                if _hash(x, z, 10) < 0.5 and _is_soft(world.get_block_name(x + 1, t + 1, z)):
                    out.put(x + 1, t + 1, z, rock[0])
                continue
            if short not in ("grass_block", "dirt", "podzol", "coarse_dirt", "mycelium", "moss_block", "mud",
                             "rooted_dirt", "netherrack"):
                continue
            r2 = _hash(x, z, 6)
            acc = 0.0
            for key in ("flower", "tall", "fern", "bush", "grass"):
                acc += th[key] * 0.6
                if r2 < acc:
                    _plant(out, x, t + 1, z, key, th, r2, world)
                    break
    for x, y, z in trees:
        if island and th.get("warm"):
            _palm(world, out, x, y, z)
        else:
            _tree(world, out, x, y, z, th["tree"])


def _plant(out, x, y, z, key, th, r, world):
    if key == "flower" and th["flowers"]:
        f = th["flowers"][int(r * 997) % len(th["flowers"])]
        if f == "pink_petals":
            out.put(x, y, z, f, flower_amount=str(1 + int(r * 31) % 4), facing="north")
        elif f == "sweet_berry_bush":
            out.put(x, y, z, f, age="3")
        else:
            out.put(x, y, z, f)
    elif key == "tall" and _is_soft(world.get_block_name(x, y + 1, z)):
        out.put(x, y, z, "tall_grass", half="lower")
        out.put(x, y + 1, z, "tall_grass", half="upper")
    elif key == "fern":
        out.put(x, y, z, "fern")
    elif key == "bush":
        out.put(x, y, z, "oak_leaves" if "jungle" not in str(th.get("tree")) else "jungle_leaves",
                persistent="true", distance="1", waterlogged="false")
    else:
        out.put(x, y, z, "short_grass")


def _free(world, x, y, z):
    return _is_soft(world.get_block_name(x, y, z))


def _tree(world, out, x, y, z, kind):
    """Small tree of the biome (leaves are persistent: they never decay)."""
    if kind == "cactus":
        for k in range(1 + int(_hash(x, z, 12) * 3)):
            if _free(world, x, y + k, z):
                out.put(x, y + k, z, "cactus", age="0")
        return
    log = {"oak": "oak_log", "birch": "birch_log", "spruce": "spruce_log", "jungle": "jungle_log",
           "acacia": "acacia_log", "cherry": "cherry_log", "dark_oak": "dark_oak_log"}.get(kind, "oak_log")
    leaves = log.replace("_log", "_leaves")
    height = 4 + int(_hash(x, z, 13) * 3)
    if any(not _free(world, x, y + k, z) for k in range(height + 2)):
        return
    out.put(x, y - 1, z, "dirt")
    for k in range(height):
        out.put(x, y + k, z, log, axis="y")
    top = y + height
    leaf = dict(persistent="true", distance="1", waterlogged="false")
    if kind == "spruce":
        for k, r in ((0, 0), (-1, 1), (-2, 2), (-3, 1), (-4, 2)):
            for a in range(-r, r + 1):
                for b in range(-r, r + 1):
                    if abs(a) + abs(b) <= r + (r > 1) and (a or b) and _free(world, x + a, top + k, z + b):
                        out.put(x + a, top + k, z + b, leaves, **leaf)
        out.put(x, top, z, leaves, **leaf)
        return
    if kind == "acacia":
        for a in range(-2, 3):
            for b in range(-2, 3):
                if abs(a) + abs(b) <= 3 and _free(world, x + a, top, z + b):
                    out.put(x + a, top, z + b, leaves, **leaf)
        return
    for k in (-2, -1, 0, 1):
        r = 2 if k < 0 else 1
        for a in range(-r, r + 1):
            for b in range(-r, r + 1):
                if (abs(a) == r and abs(b) == r and (k >= 0 or _hash(x + a, z + b, k) < 0.5)) or (a == 0 and b == 0
                                                                                                and k < 0):
                    continue
                if _free(world, x + a, top + k, z + b):
                    out.put(x + a, top + k, z + b, leaves, **leaf)


def _palm(world, out, x, y, z):
    """Palm for warm islands: a leaning jungle trunk and a crown of fronds."""
    height = 5 + int(_hash(x, z, 14) * 2)
    dx = 1 if _hash(x, z, 15) < 0.5 else 0
    dz = 0 if dx else 1
    px, pz = x, z
    for k in range(height):
        if k == height // 2:
            px, pz = px + dx, pz + dz
        if not _free(world, px, y + k, pz):
            return
        out.put(px, y + k, pz, "jungle_log", axis="y")
    top = y + height
    leaf = dict(persistent="true", distance="1", waterlogged="false")
    out.put(px, top, pz, "jungle_leaves", **leaf)
    for a, b in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        for r in (1, 2, 3):
            yy = top if r < 3 else top - 1
            if _free(world, px + a * r, yy, pz + b * r):
                out.put(px + a * r, yy, pz + b * r, "jungle_leaves", **leaf)
    for a, b in ((1, 1), (-1, 1), (1, -1), (-1, -1)):
        if _free(world, px + a, top, pz + b):
            out.put(px + a, top, pz + b, "jungle_leaves", **leaf)
