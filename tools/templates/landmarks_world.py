"""Altri monumenti famosi: Asia, Russia, America."""
import math

from template_builder import Builder, AIR, template


@template("temple_of_heaven", "Temple of Heaven", "Landmark",
          "Tempio del Cielo di Pechino: tre terrazze di marmo con balaustre, sala rotonda rossa e tre tetti blu con pinnacolo d'oro.")
def temple_of_heaven():
    W = 25
    b = Builder(W, 28, W)
    c = 12
    for y, r in ((0, 12), (1, 10), (2, 8)):
        b.disk(c, c, y, r, "smooth_quartz")
        b.ring(c, c, y + 1, r, "diorite_wall")
    for y, r in ((0, 12), (1, 10), (2, 8)):
        for x in range(c - 1, c + 2):
            b.set(x, y + 1, c + r, AIR)
            if y > 0:
                b.stair(x, y, c + r, "smooth_quartz", "north")
    b.ring(c, c, 3, 8, "diorite_wall")
    for x in range(c - 1, c + 2):
        b.set(x, 3, c + 8, AIR)
    # Sala rotonda
    b.cylinder(c, c, 3, 7, 5, "red_concrete", hollow=True, thickness=1.2)
    for y in range(3, 8):
        b.disk(c, c, y, 3.8, AIR)
    for a in range(0, 360, 30):
        x = c + int(round(5 * math.cos(math.radians(a))))
        z = c + int(round(5 * math.sin(math.radians(a))))
        b.fill(x, 5, z, x, 6, z, "yellow_stained_glass")
    b.entrance(c, 3, c + 5, "north", wood="dark_oak", step=None)
    b.clear(c, 3, c + 4, c, 4, c + 4)
    b.set(c, 3, c, "gold_block")
    for x, z in ((c - 2, c - 2), (c + 2, c - 2), (c - 2, c + 2), (c + 2, c + 1)):
        b.lantern(x, 3, z)
    # Tetti
    for y, r in ((8, 7), (9, 6), (10, 5)):
        b.disk(c, c, y, r, "blue_concrete")
    b.ring(c, c, 8, 7, "gold_block", thickness=0.6)
    b.cylinder(c, c, 11, 12, 4, "red_concrete")
    for y, r in ((13, 6), (14, 5), (15, 4)):
        b.disk(c, c, y, r, "blue_concrete")
    b.cylinder(c, c, 16, 17, 3, "red_concrete")
    top = b.cone(c, c, 18, 5, "blue_concrete", step=0.8)
    b.fill(c, top + 1, c, c, top + 2, c, "gold_block")
    b.set(c, top + 3, c, "lightning_rod", facing="up", powered="false", waterlogged="false")
    for a in range(0, 360, 45):
        x = c + int(round(11 * math.cos(math.radians(a))))
        z = c + int(round(11 * math.sin(math.radians(a))))
        b.lantern(x, 1, z)
    return b


def _striped_onion(b, cx, cy, cz, profile, colors):
    for i, r in enumerate(profile):
        b.disk(cx, cz, cy + i, r, colors[i % len(colors)])
    b.set(cx, cy + len(profile), cz, "gold_block")
    return cy + len(profile)


@template("onion_dome_cathedral", "Onion Dome Cathedral", "Landmark",
          "Cattedrale a cupole a cipolla ispirata a San Basilio: torre centrale a tenda e cappelle con cupole colorate a strisce.")
def onion_dome_cathedral():
    W = 21
    b = Builder(W, 34, W)
    c = 10
    b.fill(1, 0, 1, W - 2, 0, W - 2, "bricks")
    b.room(6, 0, 6, 14, 9, 14, "bricks", floor="polished_andesite", ceiling="bricks")
    b.walls(6, 9, 6, 14, 9, 14, "white_concrete")
    for x in (8, 12):
        for z in (6, 14):
            b.fill(x, 3, z, x, 5, z, "yellow_stained_glass")
        for xx in (6, 14):
            b.fill(xx, 3, x, xx, 5, x, "yellow_stained_glass")
    b.entrance(c, 1, 14, "north", wood="dark_oak", step="brick")
    for y in range(10, 18):
        b.octagon(c, c, y, 3, "bricks" if y % 3 else "white_concrete")
    top = b.cone(c, c, 18, 3.5, "green_concrete", step=0.45)
    _striped_onion(b, c, top + 1, c, [1.2, 1.6, 1.5, 1.1, 0.6], ["gold_block"])
    chapels = (((4, 4), ["red_concrete", "green_concrete"]), ((16, 4), ["blue_concrete", "white_concrete"]),
               ((4, 16), ["yellow_concrete", "green_concrete"]), ((16, 16), ["red_concrete", "white_concrete"]))
    for (x, z), cols in chapels:
        b.cylinder(x, z, 1, 9, 2.4, "bricks")
        b.cylinder(x, z, 10, 11, 1.6, "white_concrete")
        _striped_onion(b, x, 12, z, [1.9, 2.5, 2.6, 2.4, 2.0, 1.4, 0.8, 0.3], cols)
    for (x, z), cols in (((c, 2), ["orange_concrete", "lime_concrete"]), ((2, c), ["cyan_concrete", "yellow_concrete"]),
                         ((W - 3, c), ["purple_concrete", "white_concrete"])):
        b.cylinder(x, z, 1, 7, 1.6, "bricks")
        _striped_onion(b, x, 8, z, [1.4, 1.8, 1.8, 1.5, 1.0, 0.5], cols)
    b.set(c, 1, 7, "gold_block")
    b.set(c - 1, 1, 7, "white_candle", candles="3", lit="true", waterlogged="false")
    b.set(c + 1, 1, 7, "white_candle", candles="3", lit="true", waterlogged="false")
    for x, z in ((8, 9), (12, 9), (8, 12), (12, 12)):
        b.lantern(x, 1, z)
    b.lantern(c, 8, c, hanging=True)
    for x, z in ((2, 2), (W - 3, 2), (2, W - 3), (W - 3, W - 3), (c - 3, W - 2), (c + 3, W - 2)):
        b.lantern(x, 1, z)
    return b


@template("suspension_bridge", "Suspension Bridge", "Landmark",
          "Ponte sospeso rosso ispirato al Golden Gate: due torri con traversi, cavi parabolici, tiranti e carreggiata.")
def suspension_bridge():
    L, W = 71, 9
    b = Builder(L, 36, W)
    deck = 8
    b.fill(0, deck, 1, L - 1, deck, W - 2, "gray_concrete")
    b.fill(0, deck, 1, L - 1, deck, 1, "light_gray_concrete")
    b.fill(0, deck, W - 2, L - 1, deck, W - 2, "light_gray_concrete")
    for x in range(0, L, 2):
        b.set(x, deck, 4, "yellow_concrete")
    b.fill(0, deck - 1, 1, L - 1, deck - 1, W - 2, "red_concrete")
    towers = (18, 52)
    for tx in towers:
        for z0 in (0, W - 2):
            b.fill(tx, 0, z0, tx + 1, 33, z0 + 1, "red_concrete")
        for y in (12, 22, 32):
            b.fill(tx, y, 0, tx + 1, y + 1, W - 1, "red_concrete")
        b.fill(tx, 0, 2, tx + 1, deck - 1, W - 3, "red_concrete")

    def cable_y(x):
        a, bb = towers[0] + 0.5, towers[1] + 0.5
        if x <= a:
            return deck + 1 + 24 * (x / a) ** 2
        if x >= bb:
            return deck + 1 + 24 * ((L - 1 - x) / (L - 1 - bb)) ** 2
        mid = (a + bb) / 2
        return deck + 3 + 22 * ((x - mid) / (mid - a)) ** 2

    for z in (1, W - 2):
        for x in range(L - 1):
            y1, y2 = int(round(cable_y(x))), int(round(cable_y(x + 1)))
            b.line(x, y1, z, x + 1, y2, z, "red_concrete")
        for x in range(1, L - 1):
            if towers[0] + 2 <= x < towers[1] or x < towers[0] or x > towers[1] + 1:
                b.set(x, deck + 1, z, "mangrove_fence")
                if x % 3 == 0:
                    yc = int(round(cable_y(x)))
                    b.fill(x, deck + 2, z, x, yc - 1, z, "mangrove_fence")
    for x in range(4, L, 8):
        b.lantern(x, deck + 1, 2)
        b.lantern(x, deck + 1, W - 3)
    for tx in towers:
        b.lantern(tx, 34, 0)
        b.lantern(tx + 1, 34, W - 1)
    return b


@template("obelisk", "Obelisk", "Landmark",
          "Obelisco in marmo bianco in stile Washington Monument, su piazza a gradini con lanterne.")
def obelisk():
    W = 13
    b = Builder(W, 38, W)
    c = 6
    b.fill(0, 0, 0, W - 1, 0, W - 1, "polished_andesite")
    b.fill(2, 1, 2, W - 3, 1, W - 3, "smooth_stone")
    for i in range(2, W - 2):
        for x, z, f in ((i, 2, "south"), (i, W - 3, "north"), (2, i, "east"), (W - 3, i, "west")):
            b.stair(x, 1, z, "stone", f)
    b.fill(3, 2, 3, W - 4, 3, W - 4, "chiseled_quartz_block")
    b.fill(4, 4, 4, 8, 22, 8, "smooth_quartz")
    for i in range(4, 9):
        for x, z, f in ((i, 4, "south"), (i, 8, "north"), (4, i, "east"), (8, i, "west")):
            b.stair(x, 23, z, "smooth_quartz", f)
    b.fill(5, 23, 5, 7, 33, 7, "smooth_quartz")
    for i in range(5, 8):
        for x, z, f in ((i, 5, "south"), (i, 7, "north"), (5, i, "east"), (7, i, "west")):
            b.stair(x, 34, z, "smooth_quartz", f)
    b.set(c, 34, c, "smooth_quartz")
    b.set(c, 35, c, "smooth_quartz_slab", type="bottom", waterlogged="false")
    for x, z in ((0, 0), (W - 1, 0), (0, W - 1), (W - 1, W - 1)):
        b.set(x, 1, z, "stone_brick_wall")
        b.lantern(x, 2, z)
    return b


@template("space_needle", "Space Needle", "Landmark",
          "Torre panoramica ispirata allo Space Needle di Seattle: gambe a clessidra, disco ristorante vetrato e guglia.")
def space_needle():
    W = 23
    b = Builder(W, 56, W)
    c = 11
    b.disk(c, c, 0, 10.5, "smooth_stone")
    b.fill(c - 1, 1, c - 1, c + 1, 44, c + 1, "light_gray_concrete")
    b.fill(c, 1, c, c, 44, c, AIR)
    b.ladder(c, 1, 41, c, "south")
    b.clear(c, 1, c + 1, c, 2, c + 1)

    def r(y):
        return 2 + 7 * abs(y - 20) / 20 if y < 20 else 2 + 4.5 * (y - 20) / 20

    for base in (90, 210, 330):
        for off in (-9, 9):
            a = math.radians(base + off)
            prev = None
            for y in range(0, 41):
                rr = r(y)
                x = c + int(round(rr * math.cos(a)))
                z = c + int(round(rr * math.sin(a)))
                b.set(x, y, z, "white_concrete")
                if prev and (abs(prev[0] - x) > 1 or abs(prev[1] - z) > 1):
                    b.line(prev[0], y - 1, prev[1], x, y, z, "white_concrete")
                prev = (x, z)
    b.ring(c, c, 20, 3.4, "smooth_stone_slab", thickness=1.2, type="bottom", waterlogged="false")
    for a in range(0, 360, 60):
        x = c + int(round(3 * math.cos(math.radians(a + 30))))
        z = c + int(round(3 * math.sin(math.radians(a + 30))))
        if b.get(x, 20, z) == "minecraft:smooth_stone_slab":
            b.lantern(x, 21, z)
    for a in range(0, 360, 45):
        x = c + int(round(4 * math.cos(math.radians(a))))
        z = c + int(round(4 * math.sin(math.radians(a))))
        if b.get(x, 38, z) is None:
            b.lantern(x, 38, z, hanging=True)
    for y in (8, 30):
        for a in range(0, 360, 120):
            x = c + int(round(1.8 * math.cos(math.radians(a + 45))))
            z = c + int(round(1.8 * math.sin(math.radians(a + 45))))
            if b.get(x, y, z) is None and b.get(x, y + 1, z) is None:
                b.set(x, y, z, "sea_lantern")
    # Disco panoramico
    b.disk(c, c, 39, 5, "white_concrete")
    b.disk(c, c, 40, 7, "white_concrete")
    b.disk(c, c, 41, 9, "light_gray_concrete")
    for y in (42, 43):
        b.ring(c, c, y, 9, "light_blue_stained_glass", thickness=1)
        b.disk(c, c, y, 7.9, AIR)
    b.fill(c - 1, 42, c - 1, c + 1, 43, c + 1, "light_gray_concrete")
    b.set(c, 41, c, "ladder", facing="south", waterlogged="false")
    b.set(c, 42, c, AIR)
    b.set(c, 43, c, AIR)
    b.clear(c, 42, c + 1, c, 43, c + 1)
    b.disk(c, c, 44, 9.6, "white_concrete")
    b.disk(c, c, 45, 7, "orange_concrete")
    b.disk(c, c, 46, 4.5, "white_concrete")
    b.fill(c, 47, c, c, 53, c, "iron_bars")
    b.set(c, 54, c, "lightning_rod", facing="up", powered="false", waterlogged="false")
    for a in range(0, 360, 45):
        x = c + int(round(6 * math.cos(math.radians(a))))
        z = c + int(round(6 * math.sin(math.radians(a))))
        b.lantern(x, 42, z)
    for x, z in ((c + 3, c + 3), (c - 4, c + 2)):
        b.table(x, 42, z, "birch")
    b.lantern(c + 2, 1, c + 3)
    b.lantern(c - 3, 1, c - 2)
    return b
