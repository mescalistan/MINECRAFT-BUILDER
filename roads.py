"""
Roads drawn on the map, built with the same technique as the walls.

- The centre line is a polyline (0/45/90 degree segments when drawn with snapping).
- The road surface follows the ground but rises or falls by at most one block at a time; the steps
  get a slab, dips are filled (embankment) and small bumps are cut, trees in the way are removed.
- Over water the road becomes a wooden boardwalk on piles that reach the bottom.
- Optional kerbs and lamp posts.
- The ends snap onto existing roads: the ones built with the program (remembered in the world
  folder), the walls' walkways are excluded, and paths/paved roads found in the world itself.
"""
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "tools"))

from template_builder import Builder, AIR  # noqa: E402
from walls import Path, _cardinal          # noqa: E402

ROAD_STYLES = {
    "sentiero": {"title": "Sentiero di terra battuta", "surface": [("dirt_path", 8), ("coarse_dirt", 1), ("gravel", 1)],
                 "edge": None, "slab": "spruce", "base": "dirt", "wood": "spruce"},
    "ciottoli": {"title": "Strada di ciottoli", "surface": [("cobblestone", 4), ("andesite", 2), ("stone", 2),
                                                             ("gravel", 1)],
                 "edge": "mossy_cobblestone", "slab": "cobblestone", "base": "cobblestone", "wood": "spruce"},
    "lastricata": {"title": "Strada lastricata", "surface": [("stone_bricks", 6), ("cracked_stone_bricks", 1),
                                                              ("polished_andesite", 2)],
                   "edge": "chiseled_stone_bricks", "slab": "stone_brick", "base": "cobblestone", "wood": "dark_oak"},
    "deserto": {"title": "Strada del deserto", "surface": [("smooth_sandstone", 4), ("cut_sandstone", 3),
                                                           ("sandstone", 1)],
                "edge": "chiseled_sandstone", "slab": "sandstone", "base": "sandstone", "wood": "acacia"},
    "nordica": {"title": "Strada di ardesia", "surface": [("polished_deepslate", 4), ("deepslate_tiles", 2),
                                                          ("cobbled_deepslate", 1)],
                "edge": "deepslate_bricks", "slab": "polished_deepslate", "base": "cobbled_deepslate",
                "wood": "spruce"},
}

ROAD_HINTS = ("dirt_path", "gravel", "cobblestone", "stone_bricks", "polished_andesite", "smooth_sandstone",
              "cut_sandstone", "polished_deepslate", "deepslate_tiles", "bricks", "mud_bricks", "planks")
SNAP_DISTANCE = 8


def _median(values):
    v = sorted(values)
    return v[len(v) // 2] if v else None


def road_profile(ground, water):
    """
    Surface height along the road: close to the ground, never more than one block of difference
    between neighbours (so it can be walked, with a slab on every step), above the water.
    """
    n = len(ground)
    y = list(ground)
    for i in range(n):
        if water[i] is not None:
            y[i] = max(y[i], water[i] + 1)
    for _ in range(3):
        for i in range(1, n):
            y[i] = max(min(y[i], y[i - 1] + 1), y[i - 1] - 1)
        for i in range(n - 2, -1, -1):
            y[i] = max(min(y[i], y[i + 1] + 1), y[i + 1] - 1)
        for i in range(n):           # never below the water surface
            if water[i] is not None:
                y[i] = max(y[i], water[i] + 1)
    return y


def detect_road(world, x, z, radius=6):
    """
    Road-like surface blocks (paths, paved roads) near (x, z) in the world: returns
    (cx, cz, direction (dx, dz) or None) of the nearest group, or None if there is no road.
    """
    cells = []
    for dx in range(-radius, radius + 1):
        for dz in range(-radius, radius + 1):
            px, pz = x + dx, z + dz
            top = world.surface_y(px, pz)
            if top is None:
                continue
            for y in (top, top - 1):
                name = (world.get_block_name(px, y, pz) or "").split(":", 1)[-1]
                if any(h in name for h in ROAD_HINTS) and "wall" not in name and "stairs" not in name:
                    cells.append((px, pz))
                    break
    if len(cells) < 3:
        return None
    nearest = min(cells, key=lambda c: (c[0] - x) ** 2 + (c[1] - z) ** 2)
    near = [c for c in cells if abs(c[0] - nearest[0]) <= 3 and abs(c[1] - nearest[1]) <= 3]
    cx = round(sum(c[0] for c in near) / len(near))
    cz = round(sum(c[1] for c in near) / len(near))
    # main direction of the road cells (principal axis)
    mx = sum(c[0] for c in cells) / len(cells)
    mz = sum(c[1] for c in cells) / len(cells)
    sxx = sum((c[0] - mx) ** 2 for c in cells)
    szz = sum((c[1] - mz) ** 2 for c in cells)
    sxz = sum((c[0] - mx) * (c[1] - mz) for c in cells)
    if abs(sxx - szz) < 1e-6 and abs(sxz) < 1e-6:
        return cx, cz, None
    ang = 0.5 * math.atan2(2 * sxz, sxx - szz)
    return cx, cz, (math.cos(ang), math.sin(ang))


def snap_endpoints(points, existing=(), world=None):
    """
    Moves the first and the last point onto a nearby existing road: the polylines of the roads
    built with the program ('existing', world coordinates) or road blocks found in the world.
    Returns (points, messages).
    """
    pts = [(int(round(x)), int(round(z))) for x, z in points]
    msgs = []
    for idx in (0, len(pts) - 1):
        if idx == len(pts) - 1 and len(pts) == 1:
            break
        px, pz = pts[idx]
        best = None
        for line in existing:
            if len(line) < 2:
                continue
            path = Path(line, False)
            dist, s, _ = path.project(px, pz)
            if dist <= SNAP_DISTANCE and (best is None or dist < best[0]):
                x, z, _, _ = path.at(s)
                best = (dist, (int(round(x)), int(round(z))))
        if best is None and world is not None:
            found = detect_road(world, px, pz)
            if found:
                cx, cz, _ = found
                if abs(cx - px) + abs(cz - pz) <= SNAP_DISTANCE:
                    best = (abs(cx - px) + abs(cz - pz), (cx, cz))
        if best and best[1] != (px, pz):
            pts[idx] = best[1]
            msgs.append(f"{'Inizio' if idx == 0 else 'Fine'} della strada agganciato alla strada esistente "
                        f"in X {best[1][0]}, Z {best[1][1]}.")
    return pts, msgs


def plan_road(points, style, width, terrain, lamps=True, lamp_spacing=12, kerbs=True):
    """Road along the polyline 'points' (world x, z). Returns {"placements", "report", "length"}."""
    st = ROAD_STYLES[style]
    path = Path(points, False)
    if len(path.points) < 2 or path.length < 2:
        return {"placements": [], "report": "Disegna almeno due punti per la strada.", "length": 0}
    half = width / 2.0
    cells = path.cells(half + (1.2 if lamps else 0.0))
    n = int(math.ceil(path.length)) + 1
    ground_b = [[] for _ in range(n)]
    water_b = [[] for _ in range(n)]
    heights = {}
    for (x, z), (dist, s, cross) in cells.items():
        h = terrain.height(x, z)
        heights[(x, z)] = h
        if h is None or dist > half:
            continue
        i = min(n - 1, int(s))
        (water_b if terrain.is_water(x, z) else ground_b)[i].append(h)
    ground = [_median(g) for g in ground_b]
    water = [max(w) if w else None for w in water_b]
    for i in range(n):
        if ground[i] is None:
            ground[i] = water[i] if water[i] is not None else None
    known = [i for i in range(n) if ground[i] is not None]
    if not known:
        return {"placements": [], "report": "La strada e' in una zona non generata.", "length": 0}
    for i in range(n):
        if ground[i] is None:
            ground[i] = ground[min(known, key=lambda k: abs(k - i))]
    top = road_profile(ground, water)

    xs = [x for x, _ in cells]
    zs = [z for _, z in cells]
    x0, z0 = min(xs) - 1, min(zs) - 1
    known_h = [h for h in heights.values() if h is not None]
    y0 = min(min(known_h), min(top)) - 2
    y1 = max(max(known_h), max(top)) + 6
    b = Builder(max(xs) - x0 + 2, y1 - y0 + 1, max(zs) - z0 + 2, seed=13)
    surface = [c[0] for c in st["surface"]]
    weights = [c[1] for c in st["surface"]]
    wood = st["wood"]
    bridge_len = 0
    lamp_done = set()
    piles = set()

    def put(x, y, z, block, **props):
        b.set(x - x0, y - y0, z - z0, block, **props)

    for (x, z), (dist, s, cross) in cells.items():
        i = min(n - 1, int(s))
        t = top[i]
        g = heights[(x, z)]
        wet = terrain.is_water(x, z)
        if dist > half:
            continue
        edge = kerbs and st["edge"] and dist > half - 0.75 and width >= 3
        if water[i] is not None:
            put(x, t, z, f"{wood}_planks")
            if dist > half - 0.75:
                put(x, t + 1, z, f"{wood}_fence")
                if i % 4 == 0:                        # a pile down to the bottom every 4 blocks
                    put(x, t - 1, z, f"{wood}_log", axis="y")
                    piles.add((x - x0, z - z0))
            bridge_len += 1
        else:
            put(x, t, z, st["edge"] if edge else b.rng.choices(surface, weights)[0])
            if g is not None and not wet:
                for y in range(g + 1, t):             # embankment
                    put(x, y, z, st["base"])
        # clear the space above: trees, bushes, the top of small bumps
        hi = max(t + 3, (g or t) + 1)
        for y in range(t + 1 + (1 if water[i] is not None and dist > half - 0.75 else 0), hi + 1):
            put(x, y, z, AIR)
        # slab on the lower side of every step, to walk up without jumping
        nxt = min(n - 1, i + 1)
        prv = max(0, i - 1)
        if water[i] is None and (top[nxt] == t + 1 or top[prv] == t + 1):
            b.slab(x - x0, t + 1 - y0, z - z0, st["slab"])
    # lamp posts beside the road
    if lamps:
        s = lamp_spacing / 2.0
        side = 1
        while s < path.length:
            x, z, ux, uz = path.at(s)
            i = min(n - 1, int(s))
            nx, nz = -uz * side, ux * side
            lx, lz = int(round(x + nx * (half + 1))), int(round(z + nz * (half + 1)))
            g = heights.get((lx, lz))
            if g is None:
                g = terrain.height(lx, lz)
            if g is not None and (lx, lz) not in lamp_done:
                base = top[i] if water[i] is not None else g
                put(lx, base, lz, st["base"] if water[i] is None else f"{wood}_planks")
                put(lx, base + 1, lz, f"{wood}_fence")
                put(lx, base + 2, lz, f"{wood}_fence")
                b.lantern(lx - x0, base + 3 - y0, lz - z0)
                lamp_done.add((lx, lz))
            s += lamp_spacing
            side = -side
    structure = b.to_structure()
    placement = {"structure": structure, "world_x": x0, "world_z": z0, "y_coord": y0,
                 "name": f"Strada - {st['title']}", "pillar_columns": piles, "group": "strada"}
    report = (f"Strada '{st['title']}': {path.length:.0f} blocchi, larghezza {width}"
              + (f", di cui {bridge_len // max(width, 1)} sull'acqua" if bridge_len else "") + ".")
    return {"placements": [placement], "report": report, "length": path.length, "points": path.points}
