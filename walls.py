"""
Defensive walls along a perimeter drawn on the map.

- The wall follows the ground: the walkway on top rises and falls by at most one block at a
  time (with stairs), so it can be walked all the way round.
- Crenellated parapet on the outside, low railing on the inside, lanterns along the walkway.
- Towers at the corners and at regular intervals, each with a door towards the inside, a ladder
  up to the walkway and the roof, and a lamp that switches on by itself at night (inverted
  daylight detector).
- Gates: open arch, gate with wooden fence gates, or an automatic drawbridge: a moat in front
  of the gate and a bridge that rises out of the water (sticky pistons) when someone
  approaches, detected by sculk sensors hidden under the road. Lamps in the passage switch
  on whenever there is movement nearby.

Everything is returned as placements for world_editor.inject_structures.
"""
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "tools"))

from template_builder import Builder, AIR, DIRS  # noqa: E402

WALL_STYLES = {
    "medievale": {
        "title": "Pietra medievale",
        "body": [("stone_bricks", 8), ("cracked_stone_bricks", 2), ("mossy_stone_bricks", 2), ("andesite", 1)],
        "base": "cobblestone", "floor": "stone_bricks", "rail": "stone_brick_wall", "stairs": "stone_brick",
        "slab": "stone_brick", "accent": "chiseled_stone_bricks", "road": "stone_bricks", "wood": "spruce",
        "banner": "red",
    },
    "deserto": {
        "title": "Arenaria del deserto",
        "body": [("cut_sandstone", 6), ("sandstone", 3), ("smooth_sandstone", 2)],
        "base": "smooth_sandstone", "floor": "smooth_sandstone", "rail": "sandstone_wall", "stairs": "sandstone",
        "slab": "sandstone", "accent": "chiseled_sandstone", "road": "smooth_sandstone", "wood": "acacia",
        "banner": "orange",
    },
    "nordico": {
        "title": "Ardesia nordica",
        "body": [("deepslate_bricks", 6), ("cracked_deepslate_bricks", 2), ("deepslate_tiles", 2)],
        "base": "cobbled_deepslate", "floor": "polished_deepslate", "rail": "deepslate_brick_wall",
        "stairs": "deepslate_brick", "slab": "deepslate_brick", "accent": "chiseled_deepslate",
        "road": "polished_deepslate", "wood": "spruce", "banner": "blue",
    },
    "oscura": {
        "title": "Fortezza di pietra nera",
        "body": [("polished_blackstone_bricks", 7), ("cracked_polished_blackstone_bricks", 2), ("blackstone", 1)],
        "base": "blackstone", "floor": "polished_blackstone", "rail": "polished_blackstone_brick_wall",
        "stairs": "polished_blackstone_brick", "slab": "polished_blackstone_brick",
        "accent": "chiseled_polished_blackstone", "road": "polished_blackstone", "wood": "dark_oak",
        "banner": "purple",
    },
    "palizzata": {
        "title": "Palizzata di legno",
        "body": [("spruce_log", 1)], "palisade": True,
        "base": "cobblestone", "floor": "spruce_planks", "rail": "spruce_fence", "stairs": "spruce",
        "slab": "spruce", "accent": "stripped_spruce_log", "road": "coarse_dirt", "wood": "spruce",
        "banner": "green",
    },
}

GATE_TYPES = {
    "arco": "Arco aperto",
    "portone": "Portone con cancelli (leva dentro e leva nascosta fuori)",
    "levatoio": "Ponte levatoio (sensori + leva dentro e leva nascosta fuori)",
}

THICKNESS = 3          # wall thickness
TOWER_R = 3            # tower radius
GATE_HALF = 7          # half width of the gatehouse along the wall
GATE_RAISE = 10        # gatehouse roof above the road (the walkway reaches it at the gate)


def _cardinal(dx, dz):
    if abs(dx) >= abs(dz):
        return "east" if dx > 0 else "west"
    return "south" if dz > 0 else "north"


def _opp(d):
    return {"north": "south", "south": "north", "east": "west", "west": "east"}[d]


# ---------------------------------------------------------------------------
# Geometry
# ---------------------------------------------------------------------------

class Path:
    """Centre line of the wall: polyline in world block coordinates, optionally closed."""

    def __init__(self, points, closed):
        pts = []
        for p in points:
            p = (int(round(p[0])), int(round(p[1])))
            if not pts or p != pts[-1]:
                pts.append(p)
        if closed and len(pts) > 2 and pts[0] == pts[-1]:
            pts.pop()
        self.closed = closed and len(pts) >= 3
        self.points = pts
        self.segs = list(zip(pts, pts[1:])) + ([(pts[-1], pts[0])] if self.closed else [])
        self.cum = [0.0]
        for a, b in self.segs:
            self.cum.append(self.cum[-1] + math.hypot(b[0] - a[0], b[1] - a[1]))
        self.length = self.cum[-1]

    def area(self):
        if not self.closed:
            return 0.0
        a = 0.0
        for (x1, z1), (x2, z2) in self.segs:
            a += x1 * z2 - x2 * z1
        return a / 2

    def at(self, s):
        """(x, z, ux, uz) of the point at arc length s (and the segment direction)."""
        if self.closed:
            s %= self.length
        s = max(0.0, min(s, self.length))
        for i, (a, b) in enumerate(self.segs):
            if s <= self.cum[i + 1] or i == len(self.segs) - 1:
                ln = max(self.cum[i + 1] - self.cum[i], 1e-9)
                t = (s - self.cum[i]) / ln
                ux, uz = (b[0] - a[0]) / ln, (b[1] - a[1]) / ln
                return a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, ux, uz
        return self.points[0][0], self.points[0][1], 1.0, 0.0

    def ds(self, s1, s2):
        """Distance along the path (shortest way round on a closed path)."""
        d = abs(s1 - s2)
        return min(d, self.length - d) if self.closed else d

    def project(self, x, z):
        """(distance, s, signed cross) of the nearest centre-line point to (x, z)."""
        best = None
        for i, (a, b) in enumerate(self.segs):
            dx, dz = b[0] - a[0], b[1] - a[1]
            ln = math.hypot(dx, dz) or 1e-9
            px, pz = x - a[0], z - a[1]
            t = max(0.0, min(1.0, (px * dx + pz * dz) / (ln * ln)))
            qx, qz = px - t * dx, pz - t * dz
            dist = math.hypot(qx, qz)
            if best is None or dist < best[0] - 1e-9:
                cross = (dx * pz - dz * px) / ln
                best = (dist, self.cum[i] + t * ln, cross)
        return best

    def cells(self, half_width):
        """{(x, z): (dist, s, cross)} of the blocks within half_width of the centre line."""
        out = {}
        for i, (a, b) in enumerate(self.segs):
            x1, x2 = sorted((a[0], b[0]))
            z1, z2 = sorted((a[1], b[1]))
            r = int(math.ceil(half_width)) + 1
            for x in range(x1 - r, x2 + r + 1):
                for z in range(z1 - r, z2 + r + 1):
                    if (x, z) in out:
                        continue
                    dist, s, cross = self.project(x, z)
                    if dist <= half_width:
                        out[(x, z)] = (dist, s, cross)
        return out


def _median(values):
    v = sorted(values)
    return v[len(v) // 2] if v else None


def _slope_envelope(values, closed):
    """Raise values so that neighbours differ by at most 1 (walkable with stairs)."""
    n = len(values)
    out = list(values)
    rounds = 2 if closed else 1
    for _ in range(rounds):
        for i in range(1, n * rounds if closed else n):
            j, k = i % n, (i - 1) % n
            out[j] = max(out[j], out[k] - 1)
        for i in range((n * rounds if closed else n) - 2, -1, -1):
            j, k = i % n, (i + 1) % n
            out[j] = max(out[j], out[k] - 1)
    return out


# ---------------------------------------------------------------------------
# Redstone helpers
# ---------------------------------------------------------------------------

def repeater(b, x, y, z, signal_dir, delay=1):
    """Repeater whose output points towards signal_dir (Minecraft 'facing' is the input side)."""
    b.set(x, y, z, "repeater", delay=str(delay), facing=_opp(signal_dir), locked="false", powered="false")


def dust(b, x, y, z):
    b.set(x, y, z, "redstone_wire", north="none", south="none", east="none", west="none", power="0")


def sensor(b, x, y, z):
    b.set(x, y, z, "sculk_sensor", sculk_sensor_phase="inactive", power="0", waterlogged="false")


def night_lamp(b, x, y, z):
    """Lamp at (x, y, z) lit at night by an inverted daylight detector on top of it."""
    b.set(x, y, z, "redstone_lamp", lit="false")
    b.set(x, y + 1, z, "daylight_detector", inverted="true", power="0")


# ---------------------------------------------------------------------------
# Gate (built in a local frame: passage along Z, outside towards -Z)
# ---------------------------------------------------------------------------

GATE_OX, GATE_OZ, GATE_H = 12, 18, 5      # local origin inside the builder; road level


def build_gate(style_key, gate_type, lights=True):
    """Gatehouse structure; the road block at the gate centre is at builder (GATE_OX, GATE_H, GATE_OZ)."""
    st = WALL_STYLES[style_key]
    h = GATE_H
    b = Builder(2 * GATE_OX + 1, h + GATE_RAISE + 5, GATE_OZ + 22, seed=21)
    wood = st["wood"]
    moat = gate_type == "levatoio"
    portcullis = gate_type == "portone"
    pw = 2 if portcullis else 1          # half width of the passage
    zd = 3 if portcullis else 2          # half depth of the gatehouse
    ptop = h + 3 if portcullis else h + 4

    def P(x, y, z, block, **props):
        b.set(x + GATE_OX, y, z + GATE_OZ, block, **props)

    def D(x, y, z):
        """Redstone dust with a solid block under it."""
        P(x, y - 1, z, st["base"])
        dust(b, x + GATE_OX, y, z + GATE_OZ)

    def R(x, y, z, signal_dir, delay=1):
        P(x, y - 1, z, st["base"])
        repeater(b, x + GATE_OX, y, z + GATE_OZ, signal_dir, delay)

    def body(x, y, z):
        blocks = [c[0] for c in st["body"]]
        weights = [c[1] for c in st["body"]]
        name = b.rng.choices(blocks, weights)[0]
        if name.endswith("_log"):
            P(x, y, z, name, axis="y")
        else:
            P(x, y, z, name)

    def stair(x, y, z, facing, top=False):
        b.stair(x + GATE_OX, y, z + GATE_OZ, st["stairs"], facing, top)

    # --- roads in and out (levelled), clear of plants ---
    for z in range(-GATE_OZ + 1, 12):
        for x in range(-pw, pw + 1):
            P(x, h, z, st["road"])
            P(x, h - 1, z, st["base"])
        if not (-zd <= z <= zd):
            for x in range(-pw - 1, pw + 2):
                for y in range(h + 1, h + 4):
                    P(x, y, z, AIR)

    # --- drawbridge: moat and rising bridge with the sensors ---
    if moat:
        for x in range(-5, 6):
            for z in range(-15, 7):
                for y in range(h - 5, h - 1):
                    P(x, y, z, st["base"])
        for x in range(-7, 8):
            for z in (-6, -3):
                for y in range(h - 3, h):
                    P(x, y, z, st["base"])
        for x in range(-7, 8):
            for z in (-6, -3):
                if abs(x) > 1:
                    P(x, h, z, st["base"])
        for z in (-5, -4):
            for x in (-7, 7):
                for y in range(h - 3, h + 1):
                    body(x, y, z)
            for x in range(-6, 7):
                P(x, h, z, AIR)
                P(x, h - 1, z, "water", level="0")
                if abs(x) <= 1:
                    P(x, h - 2, z, f"{wood}_planks")            # bridge deck, rises with the pistons
                    P(x, h - 3, z, "sticky_piston", facing="up", extended="false")
                else:
                    P(x, h - 2, z, "water", level="0")
                    P(x, h - 3, z, st["base"])
        for x in range(-1, 2):
            stair(x, h, -6, "north")
            stair(x, h, -3, "south")
        _drawbridge_redstone(P, b, h)

    # --- gatehouse ---
    for x in range(-GATE_HALF, GATE_HALF + 1):
        for z in range(-zd, zd + 1):
            passage = abs(x) <= pw
            for y in range(h - 1 if not moat else h, h + GATE_RAISE):
                if passage and y <= h:
                    continue
                if passage and y <= ptop:
                    P(x, y, z, AIR)
                    continue
                body(x, y, z)
            P(x, h + GATE_RAISE, z, st["floor"])
            for y in range(h + GATE_RAISE + 1, h + GATE_RAISE + 4):
                P(x, y, z, AIR)
    if portcullis:
        # rounded corners of the big opening (the middle row is the portcullis)
        for z in range(-zd, zd + 1):
            if z:
                stair(-pw, ptop, z, "west", top=True)
                stair(pw, ptop, z, "east", top=True)
    else:
        for z in range(-zd, zd + 1):
            stair(-1, h + 4, z, "west", top=True)
            stair(1, h + 4, z, "east", top=True)
        for x in range(-1, 2):
            P(x, h + 4, -zd, "iron_bars")
    # carved frame around the opening on both faces, with a keystone
    for z in (-zd, zd):
        for y in range(h + 1, ptop + 2):
            for x in (-(pw + 1), pw + 1):
                P(x, y, z, st["accent"])
        for x in range(-(pw + 1), pw + 2):
            P(x, ptop + 1, z, st["accent"])
        P(0, ptop + 2, z, st["accent"])
        stair(-1, ptop + 2, z, "east")
        stair(1, ptop + 2, z, "west")
    # machicolations along the top of the outer face
    for x in range(-GATE_HALF, GATE_HALF + 1):
        stair(x, h + GATE_RAISE - 1, -zd - 1, "south", top=True)
    # banners on both sides of the entrance
    for x in (-(pw + 3), pw + 3):
        P(x, ptop + 2, -zd - 1, f"{st.get('banner', 'red')}_wall_banner", facing="north")
        P(x, ptop + 1, -zd - 1, AIR)
    # parapets on the gatehouse roof (open where the wall walkway arrives at x = +-GATE_HALF)
    top = h + GATE_RAISE
    for x in range(-GATE_HALF, GATE_HALF + 1):
        body(x, top + 1, -zd)
        if x % 2 == 0:
            body(x, top + 2, -zd)
        P(x, top + 1, zd, st["rail"])
    for x in (-GATE_HALF, GATE_HALF):
        for z in (-zd, zd):
            body(x, top + 1, z)
            body(x, top + 2, z)
            b.lantern(x + GATE_OX, top + 3, z + GATE_OZ)
    # two crenellated turrets on the front corners, taller than the gatehouse
    for sx in (-1, 1):
        xs = sorted((sx * (GATE_HALF - 2), sx * GATE_HALF))
        for x in range(xs[0], xs[1] + 1):
            for z in range(-zd, -zd + 2):
                for y in range(top + 1, top + 5):
                    body(x, y, z)
                if (x + z) % 2 == 0:
                    body(x, top + 5, z)
        b.lantern(sx * (GATE_HALF - 1) + GATE_OX, top + 5, -zd + GATE_OZ)
    # ladder from the courtyard up to the gatehouse roof, inside the west tower
    lx = -5 if portcullis else -4
    for y in range(h + 1, top):
        P(lx, y, 0, AIR)
    for z in range(1, zd):
        for y in range(h + 1, h + 4):
            P(lx, y, z, AIR)
        P(lx, h + 4, z, st["base"])
    b.ladder(lx + GATE_OX, h + 1, top, GATE_OZ, "south")
    b.door(lx + GATE_OX, h + 1, zd + GATE_OZ, "north", wood=wood)
    for x in range(lx, lx + 3):
        P(x, h, zd + 1, st["road"])
        P(x, h + 1, zd + 1, AIR)
        P(x, h + 2, zd + 1, AIR)
    b.lantern(lx + GATE_OX, h + 3, 1 + GATE_OZ, hanging=True)

    # --- lights ---
    if lights and not portcullis:
        # passage ceiling: a sculk sensor on the centre lamp lights the cross of five lamps
        for x, z in ((0, 0), (1, 0), (-1, 0), (0, 1), (0, -1)):
            P(x, h + 5, z, "redstone_lamp", lit="false")
        sensor(b, GATE_OX, h + 6, GATE_OZ)
        # lamps flanking the arch on both faces, each with its own sensor behind it
        for x in (-2, 2):
            for z, behind in ((-2, -1), (2, 1)):
                P(x, h + 3, z, "redstone_lamp", lit="false")
                sensor(b, x + GATE_OX, h + 3, behind + GATE_OZ)
    if lights:
        night_lamp(b, GATE_OX, top, GATE_OZ)
    if portcullis or not lights:
        for z in (-zd + 1, zd - 1):
            b.lantern(GATE_OX, ptop, z + GATE_OZ, hanging=True)
    # lantern posts along the approach road
    for x in (-pw - 1, pw + 1):
        for z in (-9 if moat else -6, 6):
            P(x, h, z, st["base"])
            P(x, h + 1, z, f"{wood}_fence")
            b.lantern(x + GATE_OX, h + 2, z + GATE_OZ)

    # --- mechanisms ---
    if portcullis:
        _portcullis(P, D, R, b, h, st)
    if gate_type in ("portone", "levatoio"):
        _xor_levers(P, D, R, b, h, st, gate_type)
    return b


def _wire(P, D, points):
    """
    Redstone dust along consecutive points (one block apart horizontally, at most one up or down),
    with a solid block under every dust and air above the lower dust of every step, as redstone needs.
    """
    for i, (x, y, z) in enumerate(points):
        D(x, y, z)
        if i:
            px, py, pz = points[i - 1]
            if y == py + 1:
                P(px, py + 1, pz, AIR)
            elif y == py - 1:
                P(x, y + 1, z, AIR)


def _portcullis(P, D, R, b, h, st):
    """
    The big gate: a portcullis 5 blocks wide. When the gate closes, five sticky pistons hidden in
    the ceiling lower the iron bars and five more under the road raise a row of road blocks, so the
    whole opening is shut. All the wiring is inside the gatehouse: two rows of dust (under the road
    and above the ceiling) joined by a staircase of dust hidden in the east tower.
    """
    m = h - 2
    for x in range(-4, 6):
        for z in range(-3, 4):
            for y in range(h - 4, h - 1):
                P(x, y, z, st["base"])
    for x in range(-2, 3):
        P(x, h - 1, 0, "sticky_piston", facing="up", extended="false")
        P(x, h, 0, st["road"])
        P(x, m, 0, st["base"])
        R(x, m, 1, "north")
        P(x, h + 3, 0, "iron_bars")
        P(x, h + 4, 0, "sticky_piston", facing="down", extended="false")
        P(x, h + 5, 0, st["base"])
        R(x, h + 5, 1, "north")
    _wire(P, D, [(x, m, 2) for x in range(-3, 5)])
    R(3, m, 2, "east")
    riser = [(4, m, 2), (5, h - 1, 2), (6, h, 2), (6, h + 1, 1), (6, h + 2, 0), (6, h + 3, -1), (6, h + 4, -2),
             (5, h + 5, -2), (4, h + 5, -2), (4, h + 5, -1), (4, h + 5, 0), (4, h + 5, 1), (4, h + 5, 2)]
    riser += [(x, h + 5, 2) for x in range(3, -3, -1)]
    _wire(P, D, riser)
    R(4, h + 5, -1, "south")


def _xor_levers(P, D, R, b, h, st, gate_type):
    """
    Two levers that both open and close the gate, like the two switches of a staircase light:
    one on the inner wall of the gatehouse, beside the passage, and one hidden in a bush beside the
    approach road outside. The gate is open when exactly one lever is down (exclusive OR, made with
    two comparators in subtract mode), so every flip of either lever changes its state: it can be
    opened from outside, crossed and closed from inside. All the wiring runs inside the gatehouse
    towers and under the courtyard.
      - portone:  the output drives the portcullis (open = pistons retracted, the initial state).
      - levatoio: the output joins the circuit of the sensors and keeps the bridge raised.
    """
    m, lo = h - 2, h - 4
    for x in range(-12, 10):
        for z in range(7, 21):
            for y in range(h - 5, h):
                P(x, y, z, st["base"])
    # inner lever, on the wall of the gatehouse beside the passage
    if gate_type == "portone":
        P(4, h + 2, 4, "lever", face="wall", facing="south", powered="false")
        a = [(4, h + 2, 2), (4, h + 1, 1), (4, h, 0), (4, h - 1, -1), (4, m, -2), (5, m, -2), (6, m, -2),
             (7, m, -2), (8, m, -2), (8, m, -1)]
    else:
        P(4, h + 2, 3, "lever", face="wall", facing="south", powered="false")
        a = [(4, h + 2, 1), (5, h + 1, 1), (6, h, 1), (6, h - 1, 0), (6, m, -1), (7, m, -1), (8, m, -1)]
    a += [(8, m, z) for z in range(0, 14)] + [(x, m, 13) for x in range(7, -5, -1)]
    a += [(-4, m, 12), (-4, m, 11), (-4, m, 10)]
    _wire(P, D, a)
    _wire(P, D, [(0, m, z) for z in range(13, 7, -1)])
    R(8, m, 3, "south")
    R(4, m, 13, "west")
    R(-4, m, 9, "north")
    # hidden outer lever, on a mossy stone inside a bush
    P(-6, h, -11, "mossy_cobblestone")
    P(-6, h + 1, -11, "lever", face="floor", facing="east", powered="false")
    for x, y, z in ((-7, h + 1, -11), (-6, h + 1, -12), (-6, h + 1, -10), (-7, h + 1, -12), (-7, h + 1, -10),
                    (-6, h + 2, -11), (-7, h + 2, -11), (-6, h + 2, -12), (-6, h + 2, -10)):
        if y == h + 1:
            P(x, h, z, "moss_block")
        P(x, y, z, "oak_leaves", persistent="true", distance="1", waterlogged="false")
    bpath = [(-6, h - 1, -11)] + [(x, m, -11) for x in range(-7, -12, -1)]
    bpath += [(-11, m, z) for z in range(-10, 20)] + [(x, m, 19) for x in range(-10, -1)]
    bpath += [(-2, m, 18), (-2, m, 17)] + [(x, m, 17) for x in range(-3, -7, -1)]
    bpath += [(-6, m, z) for z in range(16, 7, -1)]
    _wire(P, D, bpath)
    for x, y, z, d in ((-11, m, -4, "south"), (-11, m, 10, "south"), (-6, m, 19, "east"), (-6, m, 13, "north")):
        R(x, y, z, d)
    # B passes under A to reach the second comparator
    _wire(P, D, [(-2, m, 17), (-2, m - 1, 16), (-2, lo, 15), (-2, lo, 14), (-2, lo, 13), (-2, lo, 12),
                 (-2, m - 1, 11), (-2, m, 10)])
    R(-2, m, 9, "north")
    # exclusive OR: C1 = A minus B, C2 = B minus A
    for x in (-4, -2):
        P(x, m - 1, 8, st["base"])
        P(x, m, 8, "comparator", facing="south", mode="subtract", powered="false")
    R(-5, m, 8, "east")     # B into the side of C1
    R(-1, m, 8, "west")     # A into the side of C2
    _wire(P, D, [(-4, m, 7), (-3, m, 7), (-2, m, 7)])
    _wire(P, D, [(-3, m, 7), (-3, m, 6), (-3, m, 5), (-3, m, 4), (-3, m, 3)])
    R(-3, m, 4, "north")
    if gate_type == "portone":
        _wire(P, D, [(-3, m, 3), (-3, m, 2)])
    else:
        _wire(P, D, [(-3, m, 3), (-4, m, 3), (-5, m, 3), (-5, h - 3, 2), (-5, lo, 1), (-5, lo, 0), (-5, lo, -1),
                     (-5, lo, -2), (-5, lo, -3), (-4, lo, -3)])
        R(-5, lo, -1, "north")


def _drawbridge_redstone(P, b, h):
    """
    Rising bridge circuit (local coordinates, outside towards -Z). Under each bridge block a
    sticky piston facing up; under each piston a block strongly powered by a repeater. Two
    sculk sensors under the roads, 9 blocks from the pistons (out of their hearing range, so the
    pistons cannot re-trigger them), feed both rows of pistons through repeaters only (no
    loops). A delayed branch keeps the signal on during the sensors' 10-tick cooldown and for
    about 2 seconds after the last movement, enough to cross.
    """
    def D(x, y, z):
        dust(b, x + GATE_OX, y, z + GATE_OZ)

    def R(x, y, z, signal_dir, delay=1):
        repeater(b, x + GATE_OX, y, z + GATE_OZ, signal_dir, delay)

    lo = h - 4
    # repeaters into the blocks under the pistons, and the two rows feeding them
    for x in range(-1, 2):
        R(x, lo, -6, "south")
        R(x, lo, -3, "north")
        D(x, lo, -7)
        D(x, lo, -2)

    for side in (-1, 1):
        # side = -1: outer sensor (feeds the outer row directly, the inner row through the lane)
        def Z(z):
            return z if side == -1 else -9 - z

        def X(x):
            return x if side == -1 else -x

        toward_gate = "south" if side == -1 else "north"
        sensor(b, X(0) + GATE_OX, h - 2, Z(-14) + GATE_OZ)
        R(X(0), h - 2, Z(-13), toward_gate)
        D(X(0), h - 2, Z(-12))
        P(X(0), h - 2, Z(-11), AIR)
        D(X(0), h - 3, Z(-11))
        P(X(0), h - 3, Z(-10), AIR)
        D(X(0), lo, Z(-10))
        # direct path to the merge node and the repeater into the row
        D(X(0), lo, Z(-9))
        R(X(0), lo, Z(-8), toward_gate)
        # delayed branch: straight from the sensor (a pure source, so the two paths cannot form a
        # loop), two 4-tick repeaters, down to the merge node
        away = "west" if side == -1 else "east"
        R(X(-1), h - 2, Z(-14), away, delay=4)
        R(X(-2), h - 2, Z(-14), away, delay=4)
        D(X(-3), h - 2, Z(-14))
        P(X(-3), h - 2, Z(-13), AIR)
        D(X(-3), h - 3, Z(-13))
        P(X(-3), h - 3, Z(-12), AIR)
        for z in (-12, -11, -10, -9):
            D(X(-3), lo, Z(z))
        for x in (-2, -1):
            D(X(x), lo, Z(-9))
        # lane to the far row: along x = 3, into the far row through a repeater
        for x in (1, 2, 3):
            D(X(x), lo, Z(-9))
        for z in range(-8, -1):
            D(X(3), lo, Z(z))
        R(X(2), lo, Z(-2), away)
    return b


def straighten_at_gates(points, closed, gates):
    """
    A gatehouse is square, so a gate on a slanted stretch of wall would stick out of it. Around
    every gate on a slanted segment the centre line is replaced by a straight piece aligned with the
    nearest axis (as long as the gatehouse), joined to the rest of the slanted wall.
    Returns (new points, gates projected on the new line).
    """
    pts = [(int(round(x)), int(round(z))) for x, z in points]
    out_gates = []
    half = GATE_HALF + 3
    for gx, gz in gates:
        path = Path(pts, closed)
        if len(path.points) < 2:
            break
        dist, s, _ = path.project(gx, gz)
        if dist > 12:
            continue
        i = max(k for k in range(len(path.segs)) if path.cum[k] <= s + 1e-9)
        i = min(i, len(path.segs) - 1)
        a, c = path.segs[i]
        x, z, ux, uz = path.at(s)
        g = (int(round(x)), int(round(z)))
        if abs(ux) > 0.99 or abs(uz) > 0.99:
            out_gates.append(g)
            continue
        ax = (1 if ux > 0 else -1, 0) if abs(ux) >= abs(uz) else (0, 1 if uz > 0 else -1)
        p1 = (g[0] - ax[0] * half, g[1] - ax[1] * half)
        p2 = (g[0] + ax[0] * half, g[1] + ax[1] * half)
        seg_len = path.cum[i + 1] - path.cum[i]
        if s - path.cum[i] < half or path.cum[i + 1] - s < half or seg_len < 2 * half + 2:
            out_gates.append(g)      # too close to a corner: leave it as it is
            continue
        k = i + 1                     # insert between the two ends of segment i
        pts = pts[:k] + [p1, p2] + pts[k:]
        out_gates.append(g)
    return pts, out_gates


def _gates_off_corners(points, closed, gates, margin=GATE_HALF + 3):
    """
    A gatehouse astride a corner leaves holes in the wall: gates closer than 'margin' to a vertex
    are moved along the longer side; if no side is long enough the gate is dropped.
    Returns (gates, messages).
    """
    path = Path(points, closed)
    if len(path.points) < 2:
        return list(gates), []
    vertices = list(range(len(path.points))) if closed else list(range(1, len(path.points) - 1))
    out, msgs = [], []
    for gx, gz in gates:
        dist, s, _ = path.project(gx, gz)
        near = [i for i in vertices if path.ds(s, path.cum[i] if i < len(path.cum) else 0.0) < margin]
        if not near:
            out.append((gx, gz))
            continue
        i = near[0]
        sv = path.cum[i] if i < len(path.cum) else 0.0
        before = path.cum[i] - path.cum[i - 1] if i > 0 else (path.length - path.cum[-1] if closed else 0)
        after = (path.cum[i + 1] if i + 1 < len(path.cum) else path.length) - sv
        best = None
        for side_len, sign in ((after, 1), (before, -1)):
            if side_len >= 2 * margin + 1 and (best is None or side_len > best[0]):
                best = (side_len, sign)
        if best is None:
            msgs.append(f"Porta in X {gx}, Z {gz} tolta: e' su un angolo e i lati vicini sono troppo corti.")
            continue
        ns = (sv + best[1] * margin) % path.length if closed else sv + best[1] * margin
        x, z, _, _ = path.at(ns)
        out.append((int(round(x)), int(round(z))))
        msgs.append(f"Porta spostata in X {int(round(x))}, Z {int(round(z))}: un corpo di guardia su un angolo "
                    f"lascerebbe buchi nelle mura.")
    return out, msgs


def _gate_ramps(g, gate_type, st, terrain, reach=30):
    """
    The roads of a gatehouse are level: on sloping ground they would end in a cliff or a tunnel.
    Beyond their ends a ramp (at most one block per step, with a stair on every step) joins the terrain.
    Returns a placement or None when the ground is already level.
    """
    pw = 2 if gate_type == "portone" else 1
    ox, oz = DIRS[g["outward"]]
    ax, az = -oz, ox
    road = g["road"]
    cells = {}
    stairs = []
    for sign, start in ((1, GATE_OZ), (-1, 12)):
        prev, flat = road, 0
        prev_center = None
        for k in range(reach):
            d = start + k
            cx, cz = g["x"] + ox * d * sign, g["z"] + oz * d * sign
            hs = [terrain.height(cx + ax * w, cz + az * w) for w in range(-pw, pw + 1)]
            hs = sorted(h for h in hs if h is not None)
            if not hs:
                break
            gr = hs[len(hs) // 2]
            lvl = max(min(gr, prev + 1), prev - 1)
            for w in range(-pw - 1, pw + 2):
                cells[(cx + ax * w, cz + az * w)] = (lvl, abs(w) <= pw)
            if lvl < prev:          # going down away from the gate: stair on this cell, up towards the gate
                stairs += [((cx + ax * w, cz + az * w), lvl + 1, (-ox * sign, -oz * sign)) for w in range(-pw, pw + 1)]
            elif lvl > prev:        # going up: stair on the previous cell, up away from the gate
                px_, pz_ = prev_center if prev_center else (cx - ox * sign, cz - oz * sign)
                stairs += [((px_ + ax * w, pz_ + az * w), prev + 1, (ox * sign, oz * sign)) for w in range(-pw, pw + 1)]
            flat = flat + 1 if lvl == gr else 0
            prev, prev_center = lvl, (cx, cz)
            if flat >= 2:
                break
    if not cells or all(lvl == road for lvl, _ in cells.values()):
        return None
    xs = [x for x, _ in cells] + [p[0][0] for p in stairs]
    zs = [z for _, z in cells] + [p[0][1] for p in stairs]
    lows = [lvl for lvl, _ in cells.values()] + [terrain.height(x, z) or road for x, z in cells]
    y0, y1 = min(lows) - 1, max(lvl for lvl, _ in cells.values()) + 6
    x0, z0 = min(xs), min(zs)
    b = Builder(max(xs) - x0 + 1, y1 - y0 + 1, max(zs) - z0 + 1, seed=31)
    for (x, z), (lvl, is_road) in cells.items():
        gr = terrain.height(x, z)
        gr = lvl if gr is None else gr
        if is_road:
            for y in range(min(gr, lvl - 1) + 1, lvl):
                b.set(x - x0, y - y0, z - z0, st["base"])
            b.set(x - x0, lvl - y0, z - z0, st["road"])
        for y in range(lvl + 1, max(lvl + 3, gr) + 1):
            b.set(x - x0, y - y0, z - z0, AIR)
    for (x, z), y, (dx, dz) in stairs:
        b.stair(x - x0, y - y0, z - z0, st["stairs"], _cardinal(dx, dz))
    return {"structure": b.to_structure(), "world_x": x0, "world_z": z0, "y_coord": y0,
            "name": "Mura - rampa della porta", "group": "mura"}


# ---------------------------------------------------------------------------
# Towers
# ---------------------------------------------------------------------------

def _tower(b, put, cx, cz, walk_top, ground, inward, walk_cells, st, lights, palisade):
    """Round tower centred at (cx, cz) (builder coords); walk_top = Y of the walkway floor."""
    R = TOWER_R
    tt = walk_top + 5
    gc = ground(cx, cz)
    if gc is None:
        return
    gc = min(gc, walk_top - 1)
    in_dir = _cardinal(*inward)
    idx, idz = DIRS[in_dir]
    cells = [(dx, dz) for dx in range(-R, R + 1) for dz in range(-R, R + 1) if dx * dx + dz * dz <= (R + 0.4) ** 2]
    for dx, dz in cells:
        x, z = cx + dx, cz + dz
        g = ground(x, z)
        g = gc if g is None else g
        ring = dx * dx + dz * dz > 5.8
        if ring:
            for y in range(min(g, gc), tt + 1):
                put(x, y, z, "body")
            put(x, tt + 1, z, "body")
            if (math.atan2(dz, dx) * 4 / math.pi) % 2 < 1:
                put(x, tt + 2, z, "body")
        else:
            put(x, gc, z, "floor")
            for y in range(gc + 1, tt + 3):
                put(x, y, z, AIR)
            if walk_top - gc >= 3:
                put(x, walk_top, z, "floor")
            put(x, tt, z, "floor")
    Y0 = getattr(put, "y0", 0)          # b.door/ladder/lantern take builder Y, put() takes world Y
    # doorways where the walkway goes through the tower (3 high: the walkway may arrive on a stair)
    for dx, dz in cells:
        if dx * dx + dz * dz > 5.8 and (cx + dx, cz + dz) in walk_cells:
            for y in (walk_top + 1, walk_top + 2, walk_top + 3):
                if y < tt:
                    put(cx + dx, y, cz + dz, AIR)
    # ground door towards the inside, ladder on the opposite wall
    door = (cx + idx * R, cz + idz * R)
    walk_in = _opp(in_dir)
    if walk_top - gc >= 3:
        b.door(door[0], gc + 1 - Y0, door[1], walk_in, wood=st["wood"])
        put(door[0] + idx, gc + 1, door[1] + idz, AIR)
        put(door[0] + idx, gc + 2, door[1] + idz, AIR)
        put(door[0], gc + 3, door[1], "body")
    lx, lz = cx - idx * (R - 1), cz - idz * (R - 1)
    b.ladder(lx, gc + 1 - Y0, tt - Y0, lz, in_dir)
    # light
    side = (-idz, idx)
    b.lantern(cx + side[0], gc + 1 - Y0, cz + side[1])
    if walk_top - gc >= 3:
        b.lantern(cx + side[0], walk_top + 1 - Y0, cz + side[1])
    if lights:
        night_lamp(b, cx, tt - Y0, cz)
    else:
        b.lantern(cx, tt + 1 - Y0, cz)


# ---------------------------------------------------------------------------
# Planning
# ---------------------------------------------------------------------------

def plan_walls(points, closed, style, height, terrain, towers=True, tower_spacing=32, gates=(),
               gate_type="arco", lights=True, outside_ref=None):
    """
    points: centre line in world (x, z); gates: world points near the wall where to open gates.
    Returns {"placements": [...], "report": str, "gates": [(x, z, facing)], "length": float}.
    """
    st = WALL_STYLES[style]
    palisade = st.get("palisade", False)
    notes = []
    if gates:
        gates, moved = _gates_off_corners(points, closed, gates)
        notes += moved
        points, gates = straighten_at_gates(points, closed, gates)
    path = Path(points, closed)
    if len(path.points) < 2 or path.length < 4:
        return {"placements": [], "report": "Disegna almeno due punti distanti tra loro.", "gates": [], "length": 0}
    half = THICKNESS / 2.0
    cells = path.cells(half)

    # which side is outside: + cross on the right of the drawing direction for counter-clockwise...
    if path.closed:
        out_sign = -1 if path.area() > 0 else 1
    else:
        ref = outside_ref or path.points[0]
        _, _, c = path.project(*ref)
        out_sign = -1 if c > 0 else 1   # the reference point (e.g. the player) is inside

    heights = {}
    for (x, z) in cells:
        heights[(x, z)] = terrain.height(x, z)
    n = int(math.ceil(path.length)) + 1
    buckets = [[] for _ in range(n)]
    for (x, z), (dist, s, cross) in cells.items():
        h = heights[(x, z)]
        if h is not None:
            buckets[min(n - 1, int(s))].append(h)
    ground_s = [_median(bk) for bk in buckets]
    known = [i for i, g in enumerate(ground_s) if g is not None]
    if not known:
        return {"placements": [], "report": "Il perimetro e' in una zona non generata.", "gates": [], "length": 0}
    for i in range(n):
        if ground_s[i] is None:
            j = min(known, key=lambda k: abs(k - i))
            ground_s[i] = ground_s[j]

    # gates: snap to the centre line
    gate_info = []
    # the portcullis and drawbridge circuits reach 11 blocks from the gate centre on each side
    spacing = 2 * GATE_OX + 2 if gate_type in ("portone", "levatoio") else 2 * GATE_HALF + 4
    for gx, gz in gates:
        dist, s, _ = path.project(gx, gz)
        if dist > 12:
            continue
        if any(path.ds(s, g["s"]) < spacing for g in gate_info):
            notes.append(f"Porta in X {gx}, Z {gz} saltata: troppo vicina a un'altra (servono almeno "
                         f"{spacing} blocchi).")
            continue
        x, z, ux, uz = path.at(s)
        # (-uz, ux) has cross +1: it points outside when out_sign > 0
        nx, nz = (-uz, ux) if out_sign > 0 else (uz, -ux)
        outward = _cardinal(nx, nz)
        gx_, gz_ = int(round(x)), int(round(z))
        road = _median([terrain.height(gx_ + dx, gz_ + dz) for dx in range(-1, 2) for dz in range(-1, 2)
                        if terrain.height(gx_ + dx, gz_ + dz) is not None]) or ground_s[min(n - 1, int(s))]
        gate_info.append({"s": s, "x": gx_, "z": gz_, "outward": outward, "road": road})

    top = [g + height for g in ground_s]
    for g in gate_info:
        for i in range(n):
            if path.ds(i, g["s"]) <= GATE_HALF + 1:
                top[i] = max(top[i], g["road"] + GATE_RAISE)
    top = _slope_envelope(top, path.closed)

    def in_gate(s):
        return any(path.ds(s, g["s"]) <= GATE_HALF + 0.5 for g in gate_info)

    # towers: corners and every tower_spacing blocks
    tower_s = []
    if towers:
        cand = []
        for i, p in enumerate(path.points):
            if not path.closed and 0 < i < len(path.points) - 1 or path.closed:
                a = path.points[i - 1]
                c = path.points[(i + 1) % len(path.points)]
                v1 = (p[0] - a[0], p[1] - a[1])
                v2 = (c[0] - p[0], c[1] - p[1])
                ang = abs(math.atan2(v1[0] * v2[1] - v1[1] * v2[0], v1[0] * v2[0] + v1[1] * v2[1]))
                if ang > math.radians(35):
                    cand.append(path.cum[i] if i < len(path.cum) else 0.0)
            else:
                cand.append(path.cum[i] if i < len(path.cum) else path.length)
        for i in range(len(path.segs)):
            seg_len = path.cum[i + 1] - path.cum[i]
            k = int(seg_len // tower_spacing)
            for j in range(1, k + 1):
                cand.append(path.cum[i] + seg_len * j / (k + 1))
        for s in cand:
            if any(path.ds(s, g["s"]) < GATE_HALF + GATE_RAISE + TOWER_R + 2 for g in gate_info):
                continue                 # not on the ramp of the walkway that climbs to the gatehouse
            if any(path.ds(s, t) < 16 for t in tower_s):
                continue
            tower_s.append(s)

    # bounding box (world) and builder
    xs = [x for x, _ in cells]
    zs = [z for _, z in cells]
    x0, x1 = min(xs) - TOWER_R - 2, max(xs) + TOWER_R + 2
    z0, z1 = min(zs) - TOWER_R - 2, max(zs) + TOWER_R + 2
    known_h = [h for h in heights.values() if h is not None]
    y0 = min(known_h) - 1
    y1 = max(top) + 8
    b = Builder(x1 - x0 + 1, y1 - y0 + 1, z1 - z0 + 1, seed=5)

    body_blocks = [c[0] for c in st["body"]]
    body_weights = [c[1] for c in st["body"]]

    def put(x, y, z, what, **props):
        """x, z builder coordinates; y world. what: 'body', 'floor', 'base' or a block id."""
        yy = y - y0
        if what == "body":
            name = b.rng.choices(body_blocks, body_weights)[0]
            if name.endswith("_log"):
                b.set(x, yy, z, name, axis="y")
            else:
                b.set(x, yy, z, name)
        elif what in ("floor", "base", "accent", "road"):
            b.set(x, yy, z, st[what])
        else:
            b.set(x, yy, z, what, **props)
    put.y0 = y0

    def ground_b(bx, bz):
        h = heights.get((bx + x0, bz + z0))
        if h is None:
            h = terrain.height(bx + x0, bz + z0)
        return h

    walk_cells = set()
    for (x, z), (dist, s, cross) in cells.items():
        if in_gate(s):
            continue
        g = heights[(x, z)]
        if g is None:
            continue
        i = min(n - 1, int(s))
        t = top[i]
        d = cross * out_sign      # > 0 outside
        bx, bz = x - x0, z - z0
        tyy = lambda y: y - y0    # noqa: E731
        if palisade:
            if d > 0.5:
                for y in range(g, t + 2):
                    put(bx, y, bz, "body")
                put(bx, t + 2, bz, "spruce_fence" if (i // 1) % 2 else "body")
            else:
                put(bx, t, bz, "floor")
                if abs(d) <= 0.5:
                    walk_cells.add((bx, bz))
                    for y in range(t + 1, t + 3):
                        put(bx, y, bz, AIR)
                    if i % 4 == 0:
                        for y in range(g + 1, t):
                            put(bx, y, bz, "spruce_log", axis="y")
                else:
                    put(bx, t + 1, bz, st["rail"])
            continue
        put(bx, g, bz, "base")
        for y in range(g + 1, t):
            put(bx, y, bz, "body")
        if d > 0.5:
            put(bx, t, bz, "body")
            put(bx, t + 1, bz, "body")
            _, _, ux, uz = path.at(s)
            along = x if abs(ux) >= abs(uz) else z     # regular merlons on slanted walls too
            if (along // 2) % 2 == 0:
                put(bx, t + 2, bz, "body")
            else:
                put(bx, t + 2, bz, AIR)
        elif d < -0.5:
            put(bx, t, bz, "body")
            put(bx, t + 1, bz, st["rail"])
            if lights and i % 16 == 12:
                night_lamp(b, bx, tyy(t + 1), bz)
            elif i % 8 == 4:
                b.lantern(bx, tyy(t + 2), bz)
        else:
            walk_cells.add((bx, bz))
            put(bx, t, bz, "floor")
            for y in range(t + 1, t + 4):
                put(bx, y, bz, AIR)
    # stairs on the walkway where it rises
    for (bx, bz) in walk_cells:
        x, z = bx + x0, bz + z0
        _, s, _ = cells[(x, z)]
        i = min(n - 1, int(s))
        t = top[i]
        _, _, ux, uz = path.at(s)
        nxt = (i + 1) % n if path.closed else min(n - 1, i + 1)
        prv = (i - 1) % n if path.closed else max(0, i - 1)
        if top[nxt] == t + 1:
            b.stair(bx, t + 1 - y0, bz, st["stairs"], _cardinal(ux, uz))
        elif top[prv] == t + 1:
            b.stair(bx, t + 1 - y0, bz, st["stairs"], _cardinal(-ux, -uz))

    for s in tower_s:
        x, z, ux, uz = path.at(s)
        nx, nz = -uz, ux
        if (ux * nz - uz * nx) * out_sign > 0:   # make (nx, nz) point inside
            nx, nz = -nx, -nz
        cxb, czb = int(round(x)) - x0, int(round(z)) - z0
        _tower(b, put, cxb, czb, top[min(n - 1, int(s))], ground_b, (nx, nz), walk_cells, st, lights, palisade)

    structure = b.to_structure()
    placements = [{"structure": structure, "world_x": x0, "world_z": z0, "y_coord": y0,
                   "name": f"Mura - {st['title']}", "pillars": True, "group": "mura"}]
    rot = {"north": 0, "east": 90, "south": 180, "west": 270}
    for g in gate_info:
        gb = build_gate(style, gate_type, lights)
        gs = gb.to_structure()
        steps = rot[g["outward"]] // 90
        cx, cz, w, l = GATE_OX, GATE_OZ, gs.width, gs.length
        for _ in range(steps):
            cx, cz = l - 1 - cz, cx
            w, l = l, w
        gs = gs.rotate(rot[g["outward"]]) if steps else gs
        placements.append({"structure": gs, "world_x": g["x"] - cx, "world_z": g["z"] - cz,
                           "y_coord": g["road"] - GATE_H, "name": f"Porta ({GATE_TYPES[gate_type]})",
                           "pillars": True, "group": "mura"})
        ramp = _gate_ramps(g, gate_type, st, terrain)
        if ramp is not None:
            placements.append(ramp)
    report = (f"Mura '{st['title']}': perimetro {path.length:.0f} blocchi, altezza {height}, "
              f"{len(tower_s)} torri, {len(gate_info)} porte ({GATE_TYPES[gate_type]})."
              + ("".join(" " + n for n in notes)))
    return {"placements": placements, "report": report, "length": path.length, "points": path.points,
            "gates": [(g["x"], g["z"], g["outward"]) for g in gate_info], "towers": len(tower_s)}


# ---------------------------------------------------------------------------
# Suggestions
# ---------------------------------------------------------------------------

def _convex_hull(points):
    pts = sorted(set(points))
    if len(pts) <= 2:
        return pts

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    lower, upper = [], []
    for p in pts:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
    for p in reversed(pts):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)
    return lower[:-1] + upper[:-1]


def _simplify_closed(points, max_points=10):
    """Drops the vertices whose removal changes the shape least, down to max_points."""
    pts = list(points)

    def cost(i):
        a, p, c = pts[i - 1], pts[i], pts[(i + 1) % len(pts)]
        return abs((p[0] - a[0]) * (c[1] - a[1]) - (p[1] - a[1]) * (c[0] - a[0]))

    while len(pts) > max_points:
        i = min(range(len(pts)), key=cost)
        pts.pop(i)
    return pts


ROAD_HINTS = ("dirt_path", "gravel", "_bricks", "cobblestone", "polished_", "smooth_stone", "planks", "concrete")


def outward_normal(path, s, out_sign):
    _, _, ux, uz = path.at(s)
    return (-uz, ux) if out_sign > 0 else (uz, -ux)


def path_out_sign(path, outside_ref=None):
    if path.closed:
        return -1 if path.area() > 0 else 1
    _, _, c = path.project(*(outside_ref or path.points[0]))
    return -1 if c > 0 else 1


def best_gates(world, points, closed, roads=(), outside_ref=None, count=1, is_natural=None):
    """
    Best places for gates along a perimeter: where a road crosses it, otherwise where the gate,
    the moat and the approach roads would sit on free, dry and level ground (no buildings to
    demolish). Returns a list of world (x, z).
    """
    from world_extractor import is_natural_terrain
    is_natural = is_natural or is_natural_terrain
    path = Path(points, closed)
    if path.length < 2 * GATE_HALF + 4:
        return []
    out_sign = path_out_sign(path, outside_ref)
    road_s = []
    for (x, z) in roads:
        dist, s, _ = path.project(x, z)
        if dist < 4:
            road_s.append(s)
    cands = []
    step = 4
    s = GATE_HALF + 2.0
    while s < path.length - (0 if path.closed else GATE_HALF + 2):
        # keep away from the corners: the gatehouse needs a straight stretch of wall
        i = max(k for k in range(len(path.segs)) if path.cum[k] <= s)
        if s - path.cum[i] >= GATE_HALF + 1 and path.cum[i + 1] - s >= GATE_HALF + 1:
            cands.append(s)
        s += step
    scored = []
    for s in cands:
        x, z, ux, uz = path.at(s)
        nx, nz = outward_normal(path, s, out_sign)
        built = water = 0
        hs = []
        for a in range(-12, 19, 3):        # along the normal: inner road ... outer road
            for c in range(-6, 7, 3):      # across
                px = int(round(x + nx * a + ux * c))
                pz = int(round(z + nz * a + uz * c))
                top = world.surface_y(px, pz)
                if top is None:
                    built += 1
                    continue
                name = world.get_block_name(px, top, pz) or ""
                short = name.split(":", 1)[-1]
                if "water" in short:
                    water += 1
                elif not (is_natural(name) or short.endswith(("_leaves", "_log"))):
                    built += 1
                hs.append(top)
        slope = (max(hs) - min(hs)) if hs else 20
        score = built * 12 + water * 4 + slope
        if any(path.ds(s, r) < 3 for r in road_s):
            score -= 25
        scored.append((score, s))
    scored.sort()
    out = []
    for score, s in scored:
        if all(path.ds(s, o) > path.length / (count + 1) for o in out):
            out.append(s)
        if len(out) >= count:
            break
    res = []
    for s in out:
        x, z, _, _ = path.at(s)
        res.append((int(round(x)), int(round(z))))
    return res


def suggest_perimeter(world, center, radius=80, margin=10, placed=(), is_natural=None):
    """
    Perimeter around the buildings near 'center': convex hull of the built blocks (and of the
    structures placed with the program), widened by 'margin', with at most 10 corners.
    Returns (points, gates, message). Gates go where roads cross the perimeter, otherwise on
    the side facing the world spawn direction (the centre of the map).
    """
    from world_extractor import is_natural_terrain
    is_natural = is_natural or is_natural_terrain
    cx, cz = center
    built = []
    roads = set()
    for x in range(cx - radius, cx + radius + 1, 2):
        for z in range(cz - radius, cz + radius + 1, 2):
            top = world.surface_y(x, z)
            if top is None:
                continue
            name = world.get_block_name(x, top, z) or ""
            short = name.split(":", 1)[-1]
            if short.endswith(("_leaves", "_log", "_wood")) or "water" in short or is_natural(name):
                continue
            built.append((x, z))
            if any(hh in short for hh in ROAD_HINTS[:2]):
                roads.add((x, z))
    for s in placed:
        if abs(s["x"] - cx) <= radius * 2 and abs(s["z"] - cz) <= radius * 2:
            built.extend([(s["x"], s["z"]), (s["x"] + s["w"], s["z"]), (s["x"], s["z"] + s["l"]),
                          (s["x"] + s["w"], s["z"] + s["l"])])
    if len(built) < 6:
        r = 32
        pts = [(cx - r, cz - r), (cx + r, cz - r), (cx + r, cz + r), (cx - r, cz + r)]
        msg = "Nessuna costruzione trovata qui intorno: propongo un quadrato di 64 blocchi centrato sul giocatore."
    else:
        expanded = []
        for x, z in built:
            for dx, dz in ((-margin, 0), (margin, 0), (0, -margin), (0, margin),
                           (-margin * 0.7, -margin * 0.7), (margin * 0.7, -margin * 0.7),
                           (margin * 0.7, margin * 0.7), (-margin * 0.7, margin * 0.7)):
                expanded.append((int(round(x + dx)), int(round(z + dz))))
        pts = _simplify_closed(_convex_hull(expanded), 10)
        msg = (f"Perimetro proposto intorno a {len(built) * 4} blocchi costruiti, "
               f"con {margin} blocchi di margine.")
    gates = best_gates(world, pts, True, roads=roads)
    return pts, gates, msg
