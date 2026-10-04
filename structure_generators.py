"""
Strutture generate al volo dall'app: ponti di lunghezza qualsiasi (in vari stili),
calcolo di un ponte tra due sponde con aggancio ai ponti esistenti, lampioni.

Tutti i ponti sono generati lungo l'asse Z (larghezza su X) e ruotati quando servono lungo X.
"""
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


def lamp_post(wood="spruce"):
    b = Builder(1, 3, 1)
    b.fill(0, 0, 0, 0, 1, 0, f"{wood}_fence")
    b.lantern(0, 2, 0)
    return b.to_structure()
