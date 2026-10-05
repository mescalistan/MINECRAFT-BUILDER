"""
Validatore di "giocabilita'" dei template.

Controlli (E = errore, W = avviso):
  E  nomi di blocco non vanilla / proprieta' o valori non validi
  E  blocchi senza supporto (torce, scale a pioli, lanterne, colture, porte, blocchi con gravita'...)
  E  letti e porte incompleti
  E  blocchi interattivi (letti, casse, banchi da lavoro...) non raggiungibili a piedi
  E  porte bloccate su entrambi i lati
  W  zone interne coperte e buie dove possono nascere mob (luce di blocco 0)
  W  acqua/lava che puo' fuoriuscire
  W  foglie non persistenti (si seccano)

Uso:
    python tools/validate_templates.py                # tutti i template generati
    python tools/validate_templates.py --all          # anche quelli originali del repo
    python tools/validate_templates.py lighthouse ... # solo alcuni
"""
import math
import os
import sys
from collections import deque

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
sys.path.insert(0, HERE)

import blockinfo as bi
from structure_manager import Structure

TEMPLATES_DIR = os.path.join(HERE, "..", "templates")
DIRS = {"north": (0, -1), "south": (0, 1), "east": (1, 0), "west": (-1, 0)}
REACH = 4.5


class Grid:
    """Structure cells with padding; void cells count as air, y<0 is terrain."""

    def __init__(self, struct):
        self.s = struct
        # Underground builds (ground_offset > 0): y is shifted so that y = 0 is still the terrain
        # level; the layers below have negative y and their void cells are solid ground.
        self.g = getattr(struct, "ground_offset", 0) or 0
        self.ymin = -self.g
        self.w, self.h, self.l = struct.width, struct.height - self.g, struct.length
        self.names = {}
        self.props = {}
        self.dug = set()          # cells explicitly set to air below the terrain level
        for (x, y, z), b in struct.blocks.items():
            y -= self.g
            n = bi.short(b["Name"])
            if n in bi.AIR_LIKE:
                if y < 0:
                    self.dug.add((x, y, z))
                continue
            self.names[(x, y, z)] = n
            if b.get("Properties"):
                self.props[(x, y, z)] = b["Properties"]

    def name(self, x, y, z):
        if y < 0:
            n = self.names.get((x, y, z))
            if n is not None:
                return n
            if (x, y, z) in self.dug:
                return "air"
            return "grass_block" if y == -1 else "stone"  # terrain
        return self.names.get((x, y, z), "air")

    def in_bounds(self, x, y, z):
        return 0 <= x < self.w and self.ymin <= y < self.h and 0 <= z < self.l

    def passable(self, x, y, z):
        n = self.name(x, y, z)
        return bi.is_passable(n) or n.endswith("fence_gate")

    def standable(self, x, y, z):
        return bi.is_standable(self.name(x, y, z))     # below y = 0 name() is the terrain unless dug

    def climbable(self, x, y, z):
        return bi.is_climbable(self.name(x, y, z))


# ---------------------------------------------------------------------------

def check_names(grid, errors):
    for pos, n in grid.names.items():
        full = grid.s.blocks[(pos[0], pos[1] + grid.g, pos[2])]["Name"]
        if not full.startswith("minecraft:") or n not in bi.VANILLA_BLOCKS:
            errors.append(f"blocco non vanilla '{full}' in {pos}")
            continue
        allowed = bi.allowed_properties(n)
        for k, v in grid.props.get(pos, {}).items():
            if k not in allowed:
                errors.append(f"proprieta' '{k}' non valida per {n} in {pos}")
            elif allowed[k] is not None and v not in allowed[k]:
                errors.append(f"valore {k}={v} non valido per {n} in {pos}")


def _support_ok(grid, x, y, z, n, props):
    below = grid.name(x, y - 1, z)
    above = grid.name(x, y + 1, z)
    if n in ("torch", "soul_torch", "redstone_torch"):
        return bi.is_full_solid(below) or bi.is_wall_block(below) or below.endswith("_fence") or y == 0
    if n in ("wall_torch", "soul_wall_torch", "redstone_wall_torch", "ladder"):
        dx, dz = DIRS[props.get("facing", "north")]
        bx, bz = x - dx, z - dz
        if not grid.in_bounds(bx, y, bz):
            return True  # attached to whatever is outside: cannot verify
        return bi.is_full_solid(grid.name(bx, y, bz))
    if n in ("lantern", "soul_lantern"):
        if props.get("hanging") == "true":
            return not bi.is_air(above) and above not in ("water", "lava") and y + 1 < grid.h
        return y == 0 or not bi.is_air(below)
    if n.endswith("_carpet") or n.endswith("pressure_plate") or n in ("rail", "redstone_wire", "flower_pot") \
            or n.startswith("potted_") or n.endswith("candle"):
        return y == 0 or not bi.is_air(below) and below not in ("water", "lava")
    if n in ("wheat", "carrots", "potatoes", "beetroots"):
        return below == "farmland"
    if n == "sugar_cane":
        if below == "sugar_cane":
            return True
        if below not in ("sand", "red_sand", "dirt", "grass_block", "coarse_dirt", "podzol", "mud", "moss_block") and y > 0:
            return False
        if y == 0:
            return True
        return any(grid.name(x + dx, y - 1, z + dz) == "water" for dx, dz in DIRS.values())
    if n == "cactus":
        return below in ("sand", "red_sand", "cactus") or y == 0
    if bi.is_plant(n) and n not in ("vine", "glow_lichen", "kelp", "kelp_plant", "seagrass", "tall_seagrass",
                                    "cocoa", "hanging_roots", "lily_pad", "nether_wart") and not n.endswith("_stem"):
        if props.get("half") == "upper":
            return below == n
        return y == 0 or below in ("grass_block", "dirt", "coarse_dirt", "podzol", "rooted_dirt", "moss_block",
                                   "mud", "farmland", "mycelium", "sand", "red_sand")
    if n == "lily_pad":
        return below == "water"
    if n.endswith("_door"):
        if props.get("half") == "upper":
            return below == n
        return y == 0 or (not bi.is_air(below) and not below.endswith("_door"))
    if bi.is_gravity(n):
        return y == 0 or not bi.is_air(below)
    return True


def check_support(grid, errors, warnings):
    for (x, y, z), n in grid.names.items():
        props = grid.props.get((x, y, z), {})
        if not _support_ok(grid, x, y, z, n, props):
            errors.append(f"{n} senza supporto in {(x, y, z)}")
        if n.endswith("_door") and props.get("half") == "lower" and grid.name(x, y + 1, z) != n:
            errors.append(f"porta senza meta' superiore in {(x, y, z)}")
        if n.endswith("_bed"):
            dx, dz = DIRS[props.get("facing", "north")]
            if props.get("part") == "foot":
                other = (x + dx, y, z + dz)
            else:
                other = (x - dx, y, z - dz)
            if grid.name(*other) != n:
                errors.append(f"letto incompleto in {(x, y, z)}")
        if n.endswith("_leaves") and props.get("persistent") != "true":
            warnings.append(f"foglie non persistenti in {(x, y, z)} (si seccheranno)")


def check_fluids(grid, warnings):
    leaks = 0
    for (x, y, z), n in grid.names.items():
        if n not in ("water", "lava"):
            continue
        if grid.props.get((x, y, z), {}).get("level", "0") != "0":
            warnings.append(f"{n} non sorgente in {(x, y, z)}")
        for dx, dy, dz in ((1, 0, 0), (-1, 0, 0), (0, 0, 1), (0, 0, -1), (0, -1, 0)):
            nx, ny, nz = x + dx, y + dy, z + dz
            if ny < grid.ymin:
                continue
            nb = grid.name(nx, ny, nz)
            if bi.is_air(nb) or (bi.is_plant(nb) and nb not in ("seagrass", "kelp", "kelp_plant", "lily_pad")):
                leaks += 1
                break
    if leaks:
        warnings.append(f"{leaks} blocchi di fluido possono fuoriuscire")


def walkable(grid, x, y, z):
    if not grid.passable(x, y, z):
        return False
    if grid.climbable(x, y, z):
        return True
    if not (grid.passable(x, y + 1, z) or grid.climbable(x, y + 1, z)):
        return False
    return grid.standable(x, y - 1, z) and not grid.passable(x, y - 1, z) or grid.climbable(x, y - 1, z)


def reachable_cells(grid):
    start = []
    for x in range(-1, grid.w + 1):
        for z in range(-1, grid.l + 1):
            if x in (-1, grid.w) or z in (-1, grid.l):
                start.append((x, 0, z))
    seen = set(start)
    q = deque(start)
    ymax = grid.h + 1

    def ok(x, y, z):
        return -1 <= x <= grid.w and -1 <= z <= grid.l and grid.ymin <= y <= ymax and walkable(grid, x, y, z)

    while q:
        x, y, z = q.popleft()
        nexts = []
        for dx, dz in DIRS.values():
            nx, nz = x + dx, z + dz
            if ok(nx, y, nz):
                nexts.append((nx, y, nz))
                continue
            # jump up one block (needs head room above the current position)
            if ok(nx, y + 1, nz) and grid.passable(x, y + 2, z):
                nexts.append((nx, y + 1, nz))
                continue
            # step / fall down up to 3 blocks
            if grid.passable(nx, y, nz) and grid.passable(nx, y + 1, nz):
                for d in range(1, 4):
                    if not grid.passable(nx, y - d, nz) and not grid.climbable(nx, y - d, nz):
                        break
                    if ok(nx, y - d, nz):
                        nexts.append((nx, y - d, nz))
                        break
        if grid.climbable(x, y, z) or grid.climbable(x, y + 1, z):
            if ok(x, y + 1, z) or (grid.passable(x, y + 1, z) and grid.climbable(x, y + 1, z)):
                nexts.append((x, y + 1, z))
        if grid.climbable(x, y - 1, z) or (grid.passable(x, y - 1, z) and y > grid.ymin):
            if ok(x, y - 1, z):
                nexts.append((x, y - 1, z))
        for c in nexts:
            if c not in seen:
                seen.add(c)
                q.append(c)
    return seen


def line_of_sight(grid, eye, target):
    tx, ty, tz = target
    ex, ey, ez = eye
    steps = int(max(abs(tx + 0.5 - ex), abs(ty + 0.5 - ey), abs(tz + 0.5 - ez)) * 4) + 1
    for i in range(1, steps):
        t = i / steps
        cx = math.floor(ex + (tx + 0.5 - ex) * t)
        cy = math.floor(ey + (ty + 0.5 - ey) * t)
        cz = math.floor(ez + (tz + 0.5 - ez) * t)
        if (cx, cy, cz) == (tx, ty, tz):
            return True
        if bi.is_full_solid(grid.name(cx, cy, cz)) and (cy >= 0 or grid.g):
            return False
    return True


def check_access(grid, reach, errors):
    by_column = {}
    for (x, y, z) in reach:
        by_column.setdefault((x, z), []).append(y)

    def can_use(p):
        px, py, pz = p
        r = int(REACH) + 1
        for x in range(px - r, px + r + 1):
            for z in range(pz - r, pz + r + 1):
                for y in by_column.get((x, z), ()):
                    eye = (x + 0.5, y + 1.6, z + 0.5)
                    if math.dist(eye, (px + 0.5, py + 0.5, pz + 0.5)) <= REACH and line_of_sight(grid, eye, p):
                        return True
        return False

    sealed = [(x1, y1 - grid.g, z1, x2, y2 - grid.g, z2) for x1, y1, z1, x2, y2, z2 in getattr(grid.s, "technical", [])]

    def in_technical_area(p):
        return any(b[0] <= p[0] <= b[3] and b[1] <= p[1] <= b[4] and b[2] <= p[2] <= b[5] for b in sealed)

    unreachable = []
    for pos, n in grid.names.items():
        if in_technical_area(pos):
            continue
        if bi.is_interactive(n) and not (n.endswith("_bed") and grid.props.get(pos, {}).get("part") == "head"):
            if not can_use(pos):
                unreachable.append(f"{n}{pos}")
        if n.endswith("_door") and grid.props.get(pos, {}).get("half") == "lower":
            x, y, z = pos
            dx, dz = DIRS[grid.props[pos].get("facing", "north")]
            sides = [(x + dx, y, z + dz), (x - dx, y, z - dz)]
            if not any(s in reach for s in sides):
                errors.append(f"porta {pos} non raggiungibile da nessun lato")
            elif not all(walkable(grid, *s) or walkable(grid, s[0], s[1] - 1, s[2])
                         or grid.name(*s) in ("water", "bubble_column") for s in sides):  # e.g. water lifts
                # a side one block lower is fine: the player jumps onto the threshold
                errors.append(f"porta {pos} bloccata su un lato")
    if unreachable:
        errors.append(f"{len(unreachable)} blocchi interattivi non raggiungibili: {', '.join(unreachable[:6])}")


def light_map(grid):
    level = {}
    q = deque()
    for pos, n in grid.names.items():
        lv = bi.light_level(n, grid.props.get(pos, {}))
        if lv > 0:
            level[pos] = lv
            q.append(pos)
    while q:
        x, y, z = q.popleft()
        lv = level[(x, y, z)] - 1
        if lv <= 0:
            continue
        for dx, dy, dz in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)):
            p = (x + dx, y + dy, z + dz)
            if not (-1 <= p[0] <= grid.w and grid.ymin <= p[1] <= grid.h and -1 <= p[2] <= grid.l):
                continue
            if bi.blocks_light(grid.name(*p)):
                continue
            if level.get(p, 0) < lv:
                level[p] = lv
                q.append(p)
    return level


def sky_light_map(grid):
    """Sky light: 15 straight under the open sky, -1 per step sideways/under roofs."""
    level = {}
    q = deque()
    for x in range(-1, grid.w + 1):
        for z in range(-1, grid.l + 1):
            for y in range(grid.h, grid.ymin - 1, -1):
                if bi.blocks_light(grid.name(x, y, z)):
                    break
                level[(x, y, z)] = 15
                q.append((x, y, z))
    while q:
        x, y, z = q.popleft()
        lv = level[(x, y, z)] - 1
        if lv <= 0:
            continue
        for dx, dy, dz in ((1, 0, 0), (-1, 0, 0), (0, -1, 0), (0, 1, 0), (0, 0, 1), (0, 0, -1)):
            p = (x + dx, y + dy, z + dz)
            if not (-1 <= p[0] <= grid.w and grid.ymin <= p[1] <= grid.h and -1 <= p[2] <= grid.l):
                continue
            if bi.blocks_light(grid.name(*p)):
                continue
            if level.get(p, 0) < lv:
                level[p] = lv
                q.append(p)
    return level


INDOOR_SKY = 11  # cells with less sky light than this are considered "indoors"


def check_dark_spots(grid, warnings, stats):
    """Indoor floor cells with block light 0: mobs can spawn there day and night."""
    level = light_map(grid)
    sky = sky_light_map(grid)
    dark = []
    for x in range(grid.w):
        for z in range(grid.l):
            for y in range(grid.ymin, grid.h):
                if not (bi.is_air(grid.name(x, y, z)) and bi.is_air(grid.name(x, y + 1, z))):
                    continue
                if sky.get((x, y, z), 0) >= INDOOR_SKY:
                    continue
                below = grid.name(x, y - 1, z)
                spawnable = y == 0 or bi.blocks_light(below) or                     (below.endswith("_slab") and grid.props.get((x, y - 1, z), {}).get("type") in ("top", "double"))
                if not spawnable or below in ("glass", "ice", "bedrock"):
                    continue
                if level.get((x, y, z), 0) == 0:
                    dark.append((x, y, z))
    stats["dark_spots"] = len(dark)
    if dark:
        warnings.append(f"{len(dark)} punti interni bui dove possono nascere mob, es. {dark[:4]}")


def validate(struct):
    """Returns (errors, warnings, stats)."""
    errors, warnings, stats = [], [], {}
    grid = Grid(struct)
    stats["blocks"] = len(grid.names)
    stats["lights"] = sum(1 for p, n in grid.names.items() if bi.light_level(n, grid.props.get(p, {})) > 0)
    check_names(grid, errors)
    check_support(grid, errors, warnings)
    check_fluids(grid, warnings)
    reach = reachable_cells(grid)
    check_access(grid, reach, errors)
    check_dark_spots(grid, warnings, stats)
    return errors, warnings, stats


def main(argv):
    show_all = "--all" in argv
    names = [a for a in argv if not a.startswith("--")]
    sys.path.insert(0, HERE)
    import build_templates
    generated = set(build_templates.all_templates())
    files = sorted(f for f in os.listdir(TEMPLATES_DIR) if f.endswith(".nbt"))
    if names:
        files = [f for f in files if f[:-4] in names]
    elif not show_all:
        files = [f for f in files if f[:-4] in generated]

    total_err = 0
    for f in files:
        s = Structure.load(os.path.join(TEMPLATES_DIR, f))
        errors, warnings, stats = validate(s)
        total_err += len(errors)
        status = "OK " if not errors else "ERR"
        print(f"[{status}] {f[:-4]:28s} {s.width:3d}x{s.height:3d}x{s.length:3d}  blocchi={stats['blocks']:6d} "
              f"luci={stats['lights']:4d} buio={stats['dark_spots']:4d}")
        for e in errors:
            print(f"      E {e}")
        for w in warnings:
            print(f"      W {w}")
    print(f"\n{len(files)} template controllati, {total_err} errori")
    return 1 if total_err else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
