"""
Strutture generate al volo dall'app: ponti di lunghezza qualsiasi (in vari stili),
calcolo di un ponte tra due sponde con aggancio ai ponti esistenti, lampioni.

Tutti i ponti sono generati lungo l'asse Z (larghezza su X) e ruotati quando servono lungo X.
"""
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "tools"))

from template_builder import Builder, AIR  # noqa: E402

SNAP_DISTANCE = 6   # blocchi entro cui un nuovo ponte si aggancia a un ponte esistente
BANK_OVERLAP = 2    # blocchi di ponte che appoggiano su ciascuna sponda


def _stone_variant(b):
    r = b.rng.random()
    return "mossy_stone_bricks" if r < 0.1 else "cracked_stone_bricks" if r < 0.18 else "stone_bricks"


def _pier_spans(length, pier=3, span=11, min_len=7):
    """(start, end) of the piers: one at each end plus evenly spaced ones in between."""
    length = max(length, min_len)
    inner = max(0, (length - 2 * pier) // (span + pier))
    free = length - pier * (inner + 2)
    piers = [(0, pier - 1)]
    for i in range(1, inner + 1):
        z = pier + round(i * free / (inner + 1)) + (i - 1) * pier
        piers.append((z, z + pier - 1))
    piers.append((length - pier, length - 1))
    return piers


def stone_bridge(length):
    """Ponte in pietra ad archi (stesso stile di stone_bridge.nbt)."""
    length = max(length, 7)
    b = Builder(5, 7, length, seed=7)
    for z1, z2 in _pier_spans(length):
        for z in range(z1, z2 + 1):
            for x in range(5):
                for y in range(4):
                    b.set(x, y, z, _stone_variant(b))
    piers = _pier_spans(length)
    for (a1, a2), (b1, b2) in zip(piers, piers[1:]):
        if b1 - a2 <= 1:
            continue
        for x in range(5):
            b.stair(x, 3, a2 + 1, "stone_brick", "north", top=True)
            b.stair(x, 3, b1 - 1, "stone_brick", "south", top=True)
            if b1 - a2 > 4:
                b.stair(x, 2, a2 + 1, "stone_brick", "north", top=True)
                b.stair(x, 2, b1 - 1, "stone_brick", "south", top=True)
            for z in range(a2 + 2, b1 - 1):
                b.slab(x, 3, z, "stone_brick", top=True)
    for z in range(length):
        for x in range(5):
            b.set(x, 4, z, _stone_variant(b))
        b.set(0, 5, z, "stone_brick_wall")
        b.set(4, 5, z, "stone_brick_wall")
    for z in range(0, length, 6):
        b.lantern(0, 6, z)
        b.lantern(4, 6, z)
    b.lantern(0, 6, length - 1)
    b.lantern(4, 6, length - 1)
    b.clear(1, 5, 0, 3, 6, length - 1)
    return b


def wooden_bridge(length):
    """Ponte in legno di abete su pali, con ringhiera e lanterne."""
    length = max(length, 3)
    b = Builder(5, 6, length)
    b.fill(0, 3, 0, 4, 3, length - 1, "spruce_planks")
    for z in range(length):
        b.set(0, 4, z, "spruce_fence")
        b.set(4, 4, z, "spruce_fence")
    posts = list(range(0, length, 4))
    if posts[-1] != length - 1:
        posts.append(length - 1)
    for z in posts:
        for x in (0, 4):
            b.fill(x, 0, z, x, 4, z, "spruce_log", axis="y")
        b.fill(1, 2, z, 3, 2, z, "stripped_spruce_log", axis="x")
    for z in posts[::2]:
        b.lantern(0, 5, z)
        b.lantern(4, 5, z)
    b.clear(1, 4, 0, 3, 5, length - 1)
    return b


def nether_bridge(length):
    """Ponte in mattoni del Nether in stile fortezza, con archi e lanterne dell'anima."""
    length = max(length, 7)
    b = Builder(5, 9, length)
    b.fill(0, 6, 0, 4, 6, length - 1, "nether_bricks")
    for z in range(length):
        b.set(0, 7, z, "nether_brick_fence")
        b.set(4, 7, z, "nether_brick_fence")
    piers = _pier_spans(length, pier=3, span=9)
    for z1, z2 in piers:
        b.fill(0, 0, z1, 4, 5, z2, "nether_bricks")
    for (a1, a2), (b1, b2) in zip(piers, piers[1:]):
        if b1 - a2 > 2:
            b.fill(0, 5, a2 + 1, 4, 5, b1 - 1, "nether_bricks")
            b.carve_arch("z", a2 + 1, b1 - 1, 0, 4, 0, 5)
    for (x, z) in [(0, z) for z in range(0, length, 6)] + [(4, z) for z in range(0, length, 6)]:
        b.lantern(x, 8, z, soul=True)
    b.clear(1, 7, 0, 3, 8, length - 1)
    return b


def suspension_bridge(length):
    """Ponte sospeso rosso con due torri, cavi parabolici e tiranti."""
    length = max(length, 12)
    deck = 4
    tower_h = deck + max(8, length // 5)
    b = Builder(7, tower_h + 2, length)
    b.fill(0, deck, 0, 6, deck, length - 1, "gray_concrete")
    b.fill(0, deck, 0, 0, deck, length - 1, "light_gray_concrete")
    b.fill(6, deck, 0, 6, deck, length - 1, "light_gray_concrete")
    for z in range(0, length, 2):
        b.set(3, deck, z, "yellow_concrete")
    b.fill(0, deck - 1, 0, 6, deck - 1, length - 1, "red_concrete")
    towers = (length // 4, (3 * length) // 4)
    for tz in towers:
        for x in (0, 6):
            b.fill(x, 0, tz, x, tower_h, tz, "red_concrete")
        b.fill(0, tower_h - 1, tz, 6, tower_h, tz, "red_concrete")
        b.fill(1, 0, tz, 5, deck - 1, tz, "red_concrete")
        b.lantern(0, tower_h + 1, tz)
        b.lantern(6, tower_h + 1, tz)

    def cable_y(z):
        a, c = towers
        top = tower_h - 1
        if z <= a:
            return deck + 1 + (top - deck - 1) * (z / max(a, 1)) ** 2
        if z >= c:
            return deck + 1 + (top - deck - 1) * ((length - 1 - z) / max(length - 1 - c, 1)) ** 2
        mid = (a + c) / 2
        return deck + 2 + (top - deck - 2) * ((z - mid) / max(mid - a, 1)) ** 2

    for x in (0, 6):
        for z in range(length - 1):
            b.line(x, round(cable_y(z)), z, x, round(cable_y(z + 1)), z + 1, "red_concrete")
        for z in range(length):
            if z not in towers:
                b.set(x, deck + 1, z, "mangrove_fence")
                if z % 3 == 0 and round(cable_y(z)) > deck + 2:
                    b.fill(x, deck + 2, z, x, round(cable_y(z)) - 1, z, "mangrove_fence")
    for z in range(2, length, 8):
        b.lantern(1, deck + 1, z)
        b.lantern(5, deck + 1, z)
    return b


BRIDGE_STYLES = {
    "stone": {"title": "Ponte in pietra ad archi", "fn": stone_bridge, "width": 5, "deck": 4},
    "wood": {"title": "Ponte in legno", "fn": wooden_bridge, "width": 5, "deck": 3},
    "nether": {"title": "Ponte in mattoni del Nether", "fn": nether_bridge, "width": 5, "deck": 6},
    "suspension": {"title": "Ponte sospeso", "fn": suspension_bridge, "width": 7, "deck": 4},
}


def make_bridge(style, length):
    """Structure of a bridge along Z with .bridge metadata (style, length, deck, width)."""
    spec = BRIDGE_STYLES[style]
    s = spec["fn"](length).to_structure()
    s.bridge = {"style": style, "length": s.length, "deck": spec["deck"], "width": spec["width"]}
    return s


def bridge_between(style, a, b, ground_a, ground_b, existing=(), water_level=None):
    """
    Plans a bridge from point a=(x, z) to b=(x, z); ground_* are the Y of the top block at the
    two banks. If a (or b) is near the end of an existing bridge on the same axis, the new one
    continues it: same axis line and deck height, starting right after the old end.
    water_level: highest water surface under the span; the deck stays at least one block above it.

    Returns a placement dict {structure, world_x, world_z, y_coord, name, bridge} where
    bridge = {style, axis, deck, center, a, b} describes the span in world coordinates.
    """
    spec = BRIDGE_STYLES[style]
    axis = "x" if abs(b[0] - a[0]) >= abs(b[1] - a[1]) else "z"
    along = 0 if axis == "x" else 1
    cross = 1 - along
    deck = max(ground_a, ground_b)
    if water_level is not None:
        deck = max(deck, water_level + 1)
    center = round((a[cross] + b[cross]) / 2)
    lo, hi = sorted((a[along], b[along]))
    lo -= BANK_OVERLAP
    hi += BANK_OVERLAP

    snapped = None
    for old in existing:
        if old.get("axis") != axis:
            continue
        for point in (a, b):
            if abs(point[cross] - old["center"]) > SNAP_DISTANCE:
                continue
            if abs(point[along] - old["b"]) <= SNAP_DISTANCE:
                lo, hi = old["b"] + 1, max(hi, old["b"] + 2)
                snapped = old
            elif abs(point[along] - old["a"]) <= SNAP_DISTANCE:
                lo, hi = min(lo, old["a"] - 2), old["a"] - 1
                snapped = old
            if snapped:
                break
        if snapped:
            center, deck, style = snapped["center"], snapped["deck"], snapped.get("style", style)
            spec = BRIDGE_STYLES[style]
            break

    length = hi - lo + 1
    s = make_bridge(style, length)
    if axis == "x":
        s = s.rotate(90)
        s.bridge = {"style": style, "length": length, "deck": spec["deck"], "width": spec["width"]}
    half = spec["width"] // 2
    world_x, world_z = (lo, center - half) if axis == "x" else (center - half, lo)
    info = {"style": style, "axis": axis, "deck": deck, "center": center, "a": lo, "b": lo + s.bridge["length"] - 1}
    return {
        "structure": s, "world_x": world_x, "world_z": world_z, "y_coord": deck - spec["deck"],
        "name": f"{spec['title']} ({s.bridge['length']} blocchi)", "bridge": info, "extend_columns": True,
        "snapped": snapped is not None,
    }


def end_ramp(axis, center, start, direction, deck, terrain, half=2, reach=40,
             top="polished_andesite", fill="stone_bricks", slab="polished_andesite"):
    """
    Ramp from the end of a flat deck (deck block at Y 'deck') down or up to the bank: one block
    per step with a slab on every step, from 'start' along the axis in 'direction' (+1/-1).
    Returns a placement, or None when the deck is already level with the bank.
    """
    cells, slabs = {}, []
    prev = deck
    for k in range(reach):
        p = start + direction * k
        cols = [(p, center + o) if axis == "x" else (center + o, p) for o in range(-half, half + 1)]
        hs = sorted(h for h in (terrain.height(x, z) for x, z in cols) if h is not None)
        if not hs:
            break
        g = hs[len(hs) // 2]
        if terrain.is_water(*cols[half]):
            g = prev                     # still over the water: keep the level
        lvl = max(min(g, prev + 1), prev - 1)
        if lvl == g and lvl == prev and k > 0:
            break                        # reached the bank
        for x, z in cols:
            cells[(x, z)] = lvl
        if lvl < prev:                   # half step on the lower cell
            slabs.extend((x, lvl + 1, z) for x, z in cols)
        elif lvl > prev:
            back = p - direction
            slabs.extend(((back, prev + 1, center + o) if axis == "x" else (center + o, prev + 1, back))
                         for o in range(-half, half + 1))
        prev = lvl
    if not cells or all(v == deck for v in cells.values()):
        return None
    xs = [x for x, _ in cells] + [s_[0] for s_ in slabs]
    zs = [z for _, z in cells] + [s_[2] for s_ in slabs]
    lows = [min(v, terrain.height(x, z) if terrain.height(x, z) is not None else v) for (x, z), v in cells.items()]
    y0 = min(lows) - 1
    y1 = max(cells.values()) + 5
    x0, z0 = min(xs), min(zs)
    b = Builder(max(xs) - x0 + 1, y1 - y0 + 1, max(zs) - z0 + 1)
    for (x, z), lvl in cells.items():
        g = terrain.height(x, z)
        g = lvl if g is None else g
        for y in range(min(g, lvl - 1) + 1, lvl):
            b.set(x - x0, y - y0, z - z0, fill)
        b.set(x - x0, lvl - y0, z - z0, top)
        for y in range(lvl + 1, max(lvl + 3, g) + 1):
            b.set(x - x0, y - y0, z - z0, AIR)
    for x, y, z in slabs:
        b.slab(x - x0, y - y0, z - z0, slab)
    return {"structure": b.to_structure(), "world_x": x0, "world_z": z0, "y_coord": y0,
            "name": "Rampa del ponte", "extend_columns": True}


def lamp_post(wood="spruce"):
    b = Builder(1, 3, 1)
    b.fill(0, 0, 0, 0, 1, 0, f"{wood}_fence")
    b.lantern(0, 2, 0)
    return b.to_structure()


# ---------------------------------------------------------------------------
# Bridges that follow the terrain profile
# ---------------------------------------------------------------------------

STONE_PALETTES = {
    "stone": {"main": [("stone_bricks", 8), ("cracked_stone_bricks", 1), ("mossy_stone_bricks", 1)],
              "stairs": "stone_brick", "rail": "stone_brick_wall", "accent": "chiseled_stone_bricks"},
    "mossy": {"main": [("mossy_stone_bricks", 5), ("mossy_cobblestone", 2), ("stone_bricks", 2)],
              "stairs": "mossy_stone_brick", "rail": "mossy_stone_brick_wall", "accent": "chiseled_stone_bricks"},
    "sandstone": {"main": [("cut_sandstone", 5), ("smooth_sandstone", 3), ("sandstone", 2)],
                  "stairs": "sandstone", "rail": "sandstone_wall", "accent": "chiseled_sandstone"},
    "red_sandstone": {"main": [("cut_red_sandstone", 5), ("smooth_red_sandstone", 3), ("red_sandstone", 2)],
                      "stairs": "red_sandstone", "rail": "red_sandstone_wall", "accent": "chiseled_red_sandstone"},
    "mud": {"main": [("mud_bricks", 1)], "stairs": "mud_brick", "rail": "mud_brick_wall", "accent": "packed_mud"},
    "deepslate": {"main": [("deepslate_bricks", 6), ("cracked_deepslate_bricks", 1), ("deepslate_tiles", 2)],
                  "stairs": "deepslate_brick", "rail": "deepslate_brick_wall", "accent": "chiseled_deepslate"},
    "nether": {"main": [("nether_bricks", 6), ("cracked_nether_bricks", 1)], "stairs": "nether_brick",
               "rail": "nether_brick_fence", "accent": "chiseled_nether_bricks", "soul": True},
}
PALETTE_TITLES = {"stone": "pietra", "mossy": "pietra muschiosa", "sandstone": "arenaria",
                  "red_sandstone": "arenaria rossa", "mud": "mattoni di fango", "deepslate": "ardesia",
                  "nether": "mattoni del Nether"}
WOOD_TYPES = ("oak", "spruce", "birch", "jungle", "acacia", "dark_oak", "mangrove", "cherry")
WOOD_TITLES = {"oak": "quercia", "spruce": "abete", "birch": "betulla", "jungle": "legno della giungla",
               "acacia": "acacia", "dark_oak": "quercia scura", "mangrove": "mangrovia", "cherry": "ciliegio"}


def environment_palette(world, points, radius=10):
    """(stone palette, wood type) that match the ground and the trees around the given points."""
    from collections import Counter
    stone, wood = Counter(), Counter()
    for px, pz in points:
        for dx in range(-radius, radius + 1, 2):
            for dz in range(-radius, radius + 1, 2):
                x, z = px + dx, pz + dz
                top = world.surface_y(x, z)
                if top is None:
                    continue
                for y in (top, top - 1):
                    n = (world.get_block_name(x, y, z) or "").split(":", 1)[-1]
                    if "red_sand" in n or "terracotta" in n:
                        stone["red_sandstone"] += 1
                    elif "sand" in n:
                        stone["sandstone"] += 1
                    elif n in ("mud", "muddy_mangrove_roots", "mangrove_roots"):
                        stone["mud"] += 1
                    elif "snow" in n or "ice" in n:
                        stone["deepslate"] += 1
                    elif "moss" in n or n.startswith("jungle") or n == "podzol":
                        stone["mossy"] += 1
                    elif "netherrack" in n or "nylium" in n or "soul_s" in n:
                        stone["nether"] += 2
                    elif n in ("stone", "grass_block", "dirt", "gravel", "andesite", "cobblestone"):
                        stone["stone"] += 0.4
                    for w in WOOD_TYPES:
                        if n in (f"{w}_log", f"{w}_leaves"):
                            wood[w] += 1
    key = stone.most_common(1)[0][0] if stone else "stone"
    return key, (wood.most_common(1)[0][0] if wood else "spruce")


def _profile(terrain, axis, center, lo, hi, half, clearance, integrate, start_deck=None, end_deck=None):
    """
    Deck height of each block of the span (and of the ramps added at the ends).
    Classic: flat at the higher bank (and above the water), with 45 degree ramps down to the
    banks. Integrated: a gentle hump from bank to bank (1 block every 2), high enough over the
    water for boats, riding over any hill instead of digging into it.
    """
    def col(i, c):
        return (i, c) if axis == "x" else (c, i)

    ground, water = {}, {}
    for i in range(lo - 32, hi + 33):
        land, wet = [], []
        for c in range(center - half, center + half + 1):
            x, z = col(i, c)
            h = terrain.height(x, z)
            if h is None:
                continue
            (wet if terrain.is_water(x, z) else land).append(h)
        water[i] = max(wet) if wet else None
        ground[i] = max(land) if land else (max(wet) if wet else None)

    def bank(i, step):
        for k in range(0, 12):
            j = i + k * step
            if ground.get(j) is not None and water.get(j) is None:
                return ground[j]
        return ground.get(i)

    ga = start_deck if start_deck is not None else bank(lo, -1)
    gb = end_deck if end_deck is not None else bank(hi, 1)
    if ga is None or gb is None:
        return None
    n = hi - lo + 1
    wet = [water[i] for i in range(lo, hi + 1) if water[i] is not None]
    target = []
    for k, i in enumerate(range(lo, hi + 1)):
        if integrate:
            t = ga + (gb - ga) * k / max(n - 1, 1)
            if water[i] is not None:
                t = max(t, water[i] + clearance)
            elif ground[i] is not None:
                t = max(t, ground[i])
        else:
            t = max(ga, gb, (max(wet) + clearance) if wet else -999)
        target.append(t)
    slope = 0.5 if integrate else 1.0
    deck = list(target)
    for k in range(1, n):
        deck[k] = max(deck[k], deck[k - 1] - slope)
    for k in range(n - 2, -1, -1):
        deck[k] = max(deck[k], deck[k + 1] - slope)
    if start_deck is not None:
        deck[0] = start_deck
    if end_deck is not None:
        deck[-1] = end_deck

    # ramps down to the banks beyond the clicked points
    pre, post = [], []
    if start_deck is None:
        v, i = deck[0], lo - 1
        while len(pre) < 30 and ground.get(i) is not None and v - slope >= ground[i] - 0.01:
            v -= slope
            pre.append(v)
            i -= 1
    if end_deck is None:
        v, i = deck[-1], hi + 1
        while len(post) < 30 and ground.get(i) is not None and v - slope >= ground[i] - 0.01:
            v -= slope
            post.append(v)
            i += 1
    deck = list(reversed(pre)) + deck + post
    lo2, hi2 = lo - len(pre), hi + len(post)
    deck = [int(math.ceil(v - 1e-6)) for v in deck]
    return {"lo": lo2, "hi": hi2, "deck": deck,
            "ground": [ground.get(i) for i in range(lo2, hi2 + 1)],
            "water": [water.get(i) for i in range(lo2, hi2 + 1)]}


def build_profile_bridge(kind, palette_key, wood, prof, axis, span=10):
    """Bridge 5 blocks wide along 'axis' whose deck follows prof['deck'] (world Y of the deck block)."""
    d, g, wat = prof["deck"], prof["ground"], prof["water"]
    n = len(d)
    W = 5
    y0 = min(d) - 4
    pal = STONE_PALETTES[palette_key]
    b = Builder(n if axis == "x" else W, max(d) - y0 + 5, W if axis == "x" else n, seed=11)
    fwd, back = ("east", "west") if axis == "x" else ("south", "north")
    pillars = set()

    def xz(u, v):
        return (u, v) if axis == "x" else (v, u)

    def P(u, y, v, block, **props):
        x, z = xz(u, v)
        b.set(x, y - y0, z, block, **props)

    def main(u, y, v):
        blocks = [c[0] for c in pal["main"]]
        P(u, y, v, b.rng.choices(blocks, [c[1] for c in pal["main"]])[0])

    def stair(u, y, v, facing, top=False):
        x, z = xz(u, v)
        b.stair(x, y - y0, z, wood if kind == "wood" else pal["stairs"], facing, top)

    def needs_support(u):
        if wat[u] is not None:
            return True
        return g[u] is None or d[u] - g[u] >= 3

    # piers (stone) / posts (wood) inside the stretches that need support
    supports = []
    u = 0
    every = span if kind == "stone" else 4
    while u < n:
        if needs_support(u):
            start = u
            while u < n and needs_support(u):
                u += 1
            m = u - start
            k = max(0, (m - 2) // every)
            for j in range(1, k + 1):
                supports.append(start + round(j * m / (k + 1)) - (1 if kind == "stone" else 0))
        else:
            u += 1
    support_cells = set()
    for s in supports:
        support_cells.update((s, s + 1) if kind == "stone" else (s,))

    for u in range(n):
        y = d[u]
        for v in range(W):
            if kind == "wood":
                P(u, y, v, f"{wood}_planks")
            else:
                main(u, y, v)
        for v in (0, W - 1):
            P(u, y + 1, v, pal["rail"] if kind == "stone" else f"{wood}_fence")
        for v in range(1, W - 1):
            for yy in range(y + 1, y + 4):
                P(u, yy, v, AIR)
        if not needs_support(u):
            if kind == "stone":
                for v in range(W):
                    pillars.add(xz(u, v))   # embankment: solid down to the ground
            else:
                for v in (0, W - 1):
                    P(u, y - 1, v, f"{wood}_log", axis="y")
                    pillars.add(xz(u, v))
        elif kind == "stone":
            for v in range(W):
                main(u, y - 1, v)
        # ramps
        if u + 1 < n and d[u + 1] == y + 1:
            for v in range(1, W - 1):
                stair(u, y + 1, v, fwd)
        if u > 0 and d[u - 1] == y + 1:
            for v in range(1, W - 1):
                stair(u, y + 1, v, back)

    if kind == "stone":
        for u in sorted(support_cells):
            if u >= n:
                continue
            for v in range(W):
                for yy in range(y0, d[u] - 1):
                    main(u, yy, v)
                pillars.add(xz(u, v))
        # arches between the supports (and the embankments)
        for u in range(n):
            if u in support_cells or not needs_support(u):
                continue
            left = u > 0 and (u - 1 in support_cells or not needs_support(u - 1))
            right = u < n - 1 and (u + 1 in support_cells or not needs_support(u + 1))
            for v in range(W):
                if left:
                    stair(u, d[u] - 2, v, back, top=True)
                elif right:
                    stair(u, d[u] - 2, v, fwd, top=True)
                else:
                    x, z = xz(u, v)
                    b.slab(x, d[u] - 2 - y0, z, pal["stairs"], top=True)
    else:
        for u in supports:
            for v in (0, W - 1):
                for yy in range(y0, d[u]):
                    P(u, yy, v, f"{wood}_log", axis="y")
                pillars.add(xz(u, v))
                P(u, d[u] + 1, v, f"{wood}_log", axis="y")
            for v in range(1, W - 1):
                P(u, d[u] - 1, v, f"stripped_{wood}_log", axis="z" if axis == "x" else "x")

    # lanterns on the railings and entrance pillars at the two ends
    soul = pal.get("soul", False) and kind == "stone"
    for u in range(0, n, 6):
        for v in (0, W - 1):
            if kind == "wood" and u not in supports:
                P(u, d[u] + 1, v, f"{wood}_log", axis="y")
            x, z = xz(u, v)
            b.lantern(x, d[u] + 2 - y0, z, soul=soul)
    for u in (0, n - 1):
        for v in (0, W - 1):
            if kind == "stone":
                P(u, d[u] + 1, v, pal["accent"])
            else:
                P(u, d[u] + 1, v, f"{wood}_log", axis="y")
            x, z = xz(u, v)
            b.lantern(x, d[u] + 2 - y0, z, soul=soul)
    return b.to_structure(), y0, pillars


def plan_bridge(style, a, b, terrain, existing=(), integrate=False, world=None):
    """
    Bridge from bank a=(x, z) to bank b. The bridge is straight along the main axis, starting
    from the first click. With integrate=True the deck rises gently from bank to bank, stays high
    enough over the water for boats and uses the materials of the place (sandstone in the
    desert, mud bricks in swamps, the local wood...).
    Returns a placement like bridge_between, with pillar_columns for the piers.
    """
    axis = "x" if abs(b[0] - a[0]) >= abs(b[1] - a[1]) else "z"
    along = 0 if axis == "x" else 1
    cross = 1 - along
    center = a[cross]
    lo, hi = sorted((a[along], b[along]))
    lo -= BANK_OVERLAP
    hi += BANK_OVERLAP
    start_deck = end_deck = None
    snapped = None
    for old in existing:
        if old.get("axis") != axis:
            continue
        for point in (a, b):
            if abs(point[cross] - old["center"]) > SNAP_DISTANCE:
                continue
            if abs(point[along] - old["b"]) <= SNAP_DISTANCE:
                lo, hi = old["b"] + 1, max(hi, old["b"] + 4)
                start_deck = old.get("deck_b", old["deck"])
                snapped = old
            elif abs(point[along] - old["a"]) <= SNAP_DISTANCE:
                lo, hi = min(lo, old["a"] - 4), old["a"] - 1
                end_deck = old.get("deck_a", old["deck"])
                snapped = old
            if snapped:
                break
        if snapped:
            center = snapped["center"]
            style = snapped.get("style", style)
            integrate = snapped.get("integrate", integrate)
            break
    if style == "suspension":
        ha, hb = terrain.height(*a), terrain.height(*b)
        if ha is None or hb is None:
            return None
        wet = []
        steps = max(abs(b[0] - a[0]), abs(b[1] - a[1]), 1)
        for i in range(steps + 1):
            x = round(a[0] + (b[0] - a[0]) * i / steps)
            z = round(a[1] + (b[1] - a[1]) * i / steps)
            if terrain.is_water(x, z):
                wet.append(terrain.height(x, z))
        plan = bridge_between(style, a, b, ha, hb, existing, water_level=(max(wet) + 3) if wet else None)
        plan["bridge"]["integrate"] = False
        info = plan["bridge"]
        plan["ramps"] = [r for r in (end_ramp(info["axis"], info["center"], info["a"] - 1, -1, info["deck"], terrain),
                                     end_ramp(info["axis"], info["center"], info["b"] + 1, 1, info["deck"], terrain))
                         if r is not None]
        return plan
    kind = "wood" if style == "wood" else "stone"
    palette, wood = ("nether" if style == "nether" else "stone"), "spruce"
    if integrate and world is not None:
        env_stone, env_wood = environment_palette(world, [a, b])
        if style != "nether":
            palette = env_stone
        wood = env_wood
    clearance = (4 if integrate else 3) if kind == "stone" else 2
    prof = _profile(terrain, axis, center, lo, hi, 2, clearance, integrate, start_deck, end_deck)
    if prof is None:
        return None
    structure, y0, pillars = build_profile_bridge(kind, palette, wood, prof, axis)
    lo, hi = prof["lo"], prof["hi"]
    world_x, world_z = (lo, center - 2) if axis == "x" else (center - 2, lo)
    title = BRIDGE_STYLES[style]["title"]
    material = WOOD_TITLES.get(wood, wood) if kind == "wood" else PALETTE_TITLES[palette]
    info = {"style": style, "axis": axis, "deck": max(prof["deck"]), "deck_a": prof["deck"][0],
            "deck_b": prof["deck"][-1], "center": center, "a": lo, "b": hi, "integrate": integrate}
    structure.bridge = {"style": style, "length": hi - lo + 1, "deck": 4, "width": 5}
    return {
        "structure": structure, "world_x": world_x, "world_z": world_z, "y_coord": y0,
        "name": f"{title}{' integrato' if integrate else ''} in {material} ({hi - lo + 1} blocchi)",
        "bridge": info, "pillar_columns": pillars, "snapped": snapped is not None,
    }
