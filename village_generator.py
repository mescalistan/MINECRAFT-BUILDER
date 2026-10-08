"""
Generatore di villaggi: piazza centrale, quattro strade, edifici girati con la porta verso
la strada e appoggiati al terreno, sentieri dalle porte alle strade e lampioni.

La logica e' indipendente dall'interfaccia: riceve un oggetto "terrain" con
height(x, z) -> Y del terreno (o None se non generato) e is_water(x, z) -> bool,
e una funzione load(name) -> Structure.
"""
import random

STYLES = {
    "pianura": {
        "title": "Villaggio di pianura",
        "center": "village_well",
        "special": ["medieval_tavern", "blacksmith_forge", "village_chapel", "market_stall"],
        "houses": ["starter_cottage", "plains_village_house", "tudor_house"],
        "farms": ["crop_farm", "animal_pen", "horse_stable"],
        "path": "minecraft:dirt_path", "lamp": "oak",
    },
    "medievale": {
        "title": "Borgo medievale",
        "center": "fountain_plaza",
        "special": ["medieval_tavern", "blacksmith_forge", "village_chapel", "watchtower", "market_stall"],
        "houses": ["tudor_house", "starter_cottage", "viking_longhouse", "plains_village_house"],
        "farms": ["crop_farm", "horse_stable", "animal_pen", "greenhouse"],
        "path": "minecraft:gravel", "lamp": "spruce",
    },
    "nordico": {
        "title": "Villaggio nordico",
        "center": "village_well",
        "special": ["viking_longhouse", "blacksmith_forge", "watchtower"],
        "houses": ["viking_longhouse", "starter_cottage", "witch_hut"],
        "farms": ["animal_pen", "crop_farm"],
        "path": "minecraft:dirt_path", "lamp": "spruce",
    },
}

SIZES = {"piccolo": (6, 24), "medio": (10, 36), "grande": (16, 52)}  # (edifici, lunghezza strade)

ORDER = ["north", "east", "south", "west"]
DIR = {"north": (0, -1), "south": (0, 1), "east": (1, 0), "west": (-1, 0)}

MAX_SLOPE = 6          # dislivello massimo nell'impronta di un edificio
MAX_WATER = 0.08       # frazione massima di acqua sotto un edificio
MAX_FILL = 8           # massimo riempimento sotto un edificio (fondamenta)
ROAD_HALF = 1          # strade larghe 3
SLOT_SEARCH = 14       # posizioni provate lungo la strada per ogni edificio


def front_side(struct):
    """Side of the bounding box the main door is on (or 'south' if there is no door)."""
    doors = [(x, z) for (x, y, z), b in struct.blocks.items()
             if b["Name"].endswith("_door") and b.get("Properties", {}).get("half") == "lower"]
    if not doors:
        return "south", None
    # the door closest to an edge, lowest first
    best = None
    for x, z in doors:
        dist = {"north": z, "south": struct.length - 1 - z, "west": x, "east": struct.width - 1 - x}
        side = min(dist, key=dist.get)
        if best is None or dist[side] < best[0]:
            best = (dist[side], side, (x, z))
    return best[1], best[2]


def rotate_to_face(struct, target):
    """Rotates the structure clockwise until its door faces 'target'."""
    side, _ = front_side(struct)
    steps = (ORDER.index(target) - ORDER.index(side)) % 4
    return struct.rotate(90 * steps) if steps else struct


class _Plan:
    def __init__(self):
        self.reserved = set()
        self.placements = []
        self.paths = set()
        self.lamps = []
        self.destroyed = 0

    def free(self, x1, z1, x2, z2, margin=1):
        return all((x, z) not in self.reserved
                   for x in range(x1 - margin, x2 + margin + 1) for z in range(z1 - margin, z2 + margin + 1))

    def reserve(self, x1, z1, x2, z2):
        for x in range(x1, x2 + 1):
            for z in range(z1, z2 + 1):
                self.reserved.add((x, z))


def site_cost(terrain, x1, z1, x2, z2):
    """
    Evaluates a footprint. Returns (cost, y_coord, destroyed_estimate) or None if unsuitable.

    The floor goes at the 75th percentile of the ground: most of the footprint is filled
    (foundations) instead of dug, so few natural blocks are destroyed. Trees under the
    footprint are expensive (they would be cut); water and ungenerated chunks exclude the site.
    """
    heights, water, trees, total = [], 0, 0, 0
    step = 2 if max(x2 - x1, z2 - z1) > 12 else 1
    has_trees = hasattr(terrain, "is_tree")
    for x in range(x1, x2 + 1, step):
        for z in range(z1, z2 + 1, step):
            total += 1
            h = terrain.height(x, z)
            if h is None:
                return None
            if terrain.is_water(x, z):
                water += 1
            if has_trees and terrain.is_tree(x, z):
                trees += 1
            heights.append(h)
    if water > MAX_WATER * total or max(heights) - min(heights) > MAX_SLOPE:
        return None
    heights.sort()
    ground = heights[min(len(heights) - 1, (len(heights) * 3) // 4)]
    if ground - heights[0] > MAX_FILL:
        return None
    area = step * step
    cut = sum(h - ground for h in heights if h > ground) * area
    fill = sum(ground - h for h in heights if h < ground) * area
    tree_cols = trees * area
    cost = cut * 3 + tree_cols * 10 + fill * 0.4
    return cost, ground + 1, cut + tree_cols * 6


def _rect_for(arm, side, t, w, l, cx, cz):
    """Footprint (x1, z1, x2, z2) and door-facing direction of a building along a road arm."""
    g = ROAD_HALF + 2  # road half width + 1 gap
    if arm in ("east", "west"):
        x1 = cx + t if arm == "east" else cx - t - w + 1
        if side == 0:
            return (x1, cz - g - l + 1, x1 + w - 1, cz - g), "south"
        return (x1, cz + g, x1 + w - 1, cz + g + l - 1), "north"
    z1 = cz + t if arm == "south" else cz - t - l + 1
    if side == 0:
        return (cx - g - w + 1, z1, cx - g, z1 + l - 1), "east"
    return (cx + g, z1, cx + g + w - 1, z1 + l - 1), "west"


def generate_village(center, style, size, terrain, load, seed=None):
    """Returns {"placements": [...], "path_cells": [...], "report": str}."""
    spec = STYLES[style]
    n_buildings, road_len = SIZES[size]
    rng = random.Random(seed if seed is not None else hash(center))
    cx, cz = center
    plan = _Plan()

    # Piazza centrale
    hub = load(spec["center"])
    hub_eval = site_cost(terrain, cx - hub.width // 2, cz - hub.length // 2,
                         cx - hub.width // 2 + hub.width - 1, cz - hub.length // 2 + hub.length - 1)
    hy = None if hub_eval is None else hub_eval[1] - 1
    if hy is None:
        return {"placements": [], "path_cells": [], "report": "Il centro scelto non e' adatto (acqua, pendenza o "
                                                            "terreno non generato): prova un punto piu' pianeggiante."}
    hx1, hz1 = cx - hub.width // 2, cz - hub.length // 2
    plan.placements.append({"structure": hub, "world_x": hx1, "world_z": hz1, "y_coord": hy + 1,
                            "name": spec["center"] + ".nbt", "group": "villaggio"})
    plan.reserve(hx1, hz1, hx1 + hub.width - 1, hz1 + hub.length - 1)
    r0 = max(hub.width, hub.length) // 2 + 2
    for x in range(cx - r0, cx + r0 + 1):
        for z in range(cz - r0, cz + r0 + 1):
            if (x, z) not in plan.reserved:
                plan.paths.add((x, z))

    # Strade
    road = set()
    arm_len = {}
    for arm in ORDER:
        dx, dz = DIR[arm]
        arm_len[arm] = r0
        for t in range(r0, road_len + 1):
            cells = [(cx + dx * t + (o if dz else 0), cz + dz * t + (o if dx else 0))
                     for o in range(-ROAD_HALF, ROAD_HALF + 1)]
            if any(terrain.height(x, z) is None or terrain.is_water(x, z) for x, z in cells):
                break                        # the arm stops at the river: no road (and houses) beyond it
            road.update(cells)
            arm_len[arm] = t
    plan.paths |= road
    plan.reserved |= road

    # Edifici: speciali vicino al centro, case nel mezzo, fattorie in fondo
    queue = list(spec["special"]) + [rng.choice(spec["houses"]) for _ in range(n_buildings)]
    farms = list(spec["farms"])
    rng.shuffle(farms)
    queue = queue[:max(n_buildings - len(farms) // 2, 1)] + farms
    queue = queue[:n_buildings]
    cursors = {(arm, side): r0 + 1 for arm in ORDER for side in (0, 1)}
    slots = [(arm, side) for arm in ORDER for side in (0, 1)]
    placed, skipped = 0, 0
    cache = {}
    for name in queue:
        done = False
        rng.shuffle(slots)
        for arm, side in sorted(slots, key=lambda s: cursors[s]):
            base = cache.get(name) or cache.setdefault(name, load(name))
            t0 = cursors[(arm, side)]
            _, target = _rect_for(arm, side, t0, 1, 1, cx, cz)
            struct = rotate_to_face(base, target)
            best = None
            # try several positions along the road and keep the one that fits the land best
            for t in range(t0, min(t0 + SLOT_SEARCH, arm_len[arm] - 2)):
                rect, _ = _rect_for(arm, side, t, struct.width, struct.length, cx, cz)
                if not plan.free(*rect):
                    continue
                evaluation = site_cost(terrain, *rect)
                if evaluation and (best is None or evaluation[0] + (t - t0) * 2 < best[0]):
                    best = (evaluation[0] + (t - t0) * 2, t, rect, evaluation)
            if best:
                _, t, (x1, z1, x2, z2), (_cost, y, destroyed) = best
                plan.placements.append({"structure": struct, "world_x": x1, "world_z": z1, "y_coord": y,
                                        "name": name + ".nbt", "group": "villaggio"})
                plan.reserve(x1, z1, x2, z2)
                plan.destroyed += destroyed
                _door_path(plan, struct, x1, z1, target, road)
                cursors[(arm, side)] = t + (struct.width if arm in ("east", "west") else struct.length) + 2
                placed += 1
                done = True
                break
            cursors[(arm, side)] = min(t0 + SLOT_SEARCH, road_len)
        if not done:
            skipped += 1

    # Lampioni ai lati delle strade
    for arm in ORDER:
        dx, dz = DIR[arm]
        for t in range(r0 + 2, arm_len[arm], 8):
            x = cx + dx * t + (ROAD_HALF + 1 if dz else 0)
            z = cz + dz * t + (ROAD_HALF + 1 if dx else 0)
            if (x, z) not in plan.reserved and terrain.height(x, z) is not None and not terrain.is_water(x, z):
                plan.lamps.append((x, z, terrain.height(x, z) + 1))
                plan.reserved.add((x, z))

    report = (f"{spec['title']}: {placed} edifici, {len(plan.paths)} blocchi di strada, {len(plan.lamps)} lampioni, "
              f"circa {plan.destroyed} blocchi naturali da rimuovere")
    if skipped:
        report += f" ({skipped} edifici non piazzati per mancanza di spazio adatto)"
    return {"placements": plan.placements, "path_cells": sorted(plan.paths), "lamps": plan.lamps,
            "placed": placed, "destroyed": plan.destroyed,
            "path_block": spec["path"], "lamp_wood": spec["lamp"], "report": report}


def _door_path(plan, struct, x1, z1, facing, road):
    """Path from just outside the building front to the road."""
    _, door = front_side(struct)
    if door is None:
        door = (struct.width // 2, struct.length // 2)
    dx, dz = DIR[facing]
    x, z = x1 + door[0], z1 + door[1]
    # walk out of the footprint, then on to the road
    for _ in range(max(struct.width, struct.length) + 6):
        x, z = x + dx, z + dz
        if (x, z) in road:
            return
        if not (x1 <= x < x1 + struct.width and z1 <= z < z1 + struct.length):
            plan.paths.add((x, z))
            plan.reserved.add((x, z))


def find_best_site(terrain, around, style, size, load, radius=160, step=16, log=None):
    """
    Looks for the best village centre within 'radius' blocks of 'around': flat, dry, few
    trees, fully generated, not too far. Returns (center, result) or (None, reason).
    """
    log = log or (lambda m: None)
    half = SIZES[size][1]
    ax, az = around
    has_trees = hasattr(terrain, "is_tree")
    quick = []
    for gx in range(ax - radius, ax + radius + 1, step):
        for gz in range(az - radius, az + radius + 1, step):
            hs, water, trees, missing, n = [], 0, 0, 0, 0
            for x in range((gx - half) // 4 * 4, gx + half + 1, 4):
                for z in range((gz - half) // 4 * 4, gz + half + 1, 4):
                    n += 1
                    h = terrain.height(x, z)
                    if h is None:
                        missing += 1
                        continue
                    hs.append(h)
                    water += terrain.is_water(x, z)
                    trees += bool(has_trees and terrain.is_tree(x, z))
            if missing > 0.03 * n or len(hs) < 10:
                continue
            mean = sum(hs) / len(hs)
            rough = (sum((h - mean) ** 2 for h in hs) / len(hs)) ** 0.5
            distance = ((gx - ax) ** 2 + (gz - az) ** 2) ** 0.5
            score = rough * 10 + water / n * 300 + trees / n * 120 + distance * 0.05
            quick.append((score, (gx, gz)))
    if not quick:
        return None, "Nessuna zona adatta e completamente generata nei dintorni: esplora di piu' in gioco."
    quick.sort()
    best = None
    for _, center in quick[:5]:
        result = generate_village(center, style, size, terrain, load, seed=1)
        if not result["placements"]:
            continue
        value = result["placed"] * 100 - result["destroyed"] * 0.5
        log(f"  candidato {center}: {result['placed']} edifici, circa {result['destroyed']} blocchi da rimuovere")
        if best is None or value > best[0]:
            best = (value, center, result)
    if best is None:
        return None, "Le zone pianeggianti trovate non bastano per un villaggio di questa dimensione."
    return best[1], best[2]
