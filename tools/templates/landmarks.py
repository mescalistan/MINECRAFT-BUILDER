"""Monumenti famosi del mondo, in scala ridotta e giocabili (interni illuminati, accessi)."""
import math

from template_builder import Builder, AIR, template


@template("eiffel_tower", "Eiffel Tower", "Landmark",
          "Torre Eiffel in scala: quattro gambe ad arco, due piattaforme panoramiche e scala a pioli centrale.")
def eiffel_tower():
    W, H, c = 25, 60, 12
    b = Builder(W, H, W)
    M = "waxed_exposed_cut_copper"

    def half(y):
        return 1.5 + 10.5 * max(0.0, 1 - y / 50.0) ** 1.8

    for y in range(0, 50):
        r = int(round(half(y)))
        leg = max(1, int(round(half(y) * 0.25)))
        if y < 27:
            for sx in (-1, 1):
                for sz in (-1, 1):
                    for i in range(leg):
                        for j in range(leg):
                            b.set(c + sx * (r - i), y, c + sz * (r - j), M)
        else:
            b.walls(c - r, y, c - r, c + r, y, c + r, "iron_bars")
            for sx in (-1, 1):
                for sz in (-1, 1):
                    b.set(c + sx * r, y, c + sz * r, M)
    # Archi tra le gambe sotto la prima piattaforma
    r0 = int(round(half(6)))
    for i in range(-r0 + 2, r0 - 1):
        y = 11 - int(round(4 * (i / r0) ** 2))
        for side in (-1, 1):
            rr = int(round(half(y)))
            b.set(c + i, y, c + side * rr, M)
            b.set(c + side * rr, y, c + i, M)
    # Piattaforme
    for py in (12, 26):
        r = int(round(half(py))) + 1
        b.fill(c - r, py, c - r, c + r, py, c + r, M)
        b.walls(c - r, py + 1, c - r, c + r, py + 1, c + r, "iron_bars")
        b.clear(c - r + 1, py + 1, c - r + 1, c + r - 1, py + 3, c + r - 1)
        for x in range(c - r + 2, c + r - 1, 4):
            for z in range(c - r + 2, c + r - 1, 4):
                b.lantern(x, py - 1, z, hanging=True)
        for x, z in ((c - r + 1, c - r + 1), (c + r - 1, c - r + 1), (c - r + 1, c + r - 1), (c + r - 1, c + r - 1)):
            b.lantern(x, py + 1, z)
    # Terrazza sommitale e antenna
    b.fill(c - 2, 47, c - 2, c + 2, 47, c + 2, M)
    b.walls(c - 2, 48, c - 2, c + 2, 48, c + 2, "iron_bars")
    b.clear(c - 1, 48, c - 1, c + 1, 49, c + 1)
    b.fill(c, 48, c, c, 56, c, M)
    b.set(c, 57, c, "lightning_rod", facing="up", powered="false", waterlogged="false")
    b.lantern(c - 1, 48, c - 1)
    # Pozzo dell'ascensore con scala a pioli
    b.fill(c, 0, c, c, 47, c, M)
    b.ladder(c, 0, 47, c + 1, "south")
    b.set(c, 48, c + 1, AIR)
    b.lantern(c + 2, 0, c + 2)
    b.lantern(c - 2, 0, c - 2)
    return b


@template("leaning_tower_pisa", "Leaning Tower of Pisa", "Landmark",
          "Torre di Pisa pendente in marmo con logge a colonne, cella campanaria e scala interna.")
def leaning_tower_pisa():
    b = Builder(15, 40, 15)
    c0, cz = 5, 7

    def cx(y):
        return c0 + int(y * 0.1)

    b.disk(cx(0), cz, 0, 5.5, "smooth_quartz")
    for y in range(1, 8):
        b.ring(cx(y), cz, y, 4.5, "smooth_quartz", thickness=1.2)
        b.disk(cx(y), cz, y, 3.2, AIR)
    for i, a in enumerate(range(0, 360, 30)):
        if a == 90:
            continue  # lato della porta
        x = cx(4) + int(round(4.6 * math.cos(math.radians(a))))
        z = cz + int(round(4.6 * math.sin(math.radians(a))))
        b.fill(x, 2, z, x, 6, z, "quartz_pillar", axis="y")
    for s in range(6):
        y0 = 8 + s * 4
        x0 = cx(y0)
        b.disk(x0, cz, y0, 5, "smooth_quartz")
        b.disk(x0, cz, y0, 3.2, "smooth_quartz")
        for y in range(y0 + 1, y0 + 4):
            xc = cx(y)
            b.ring(xc, cz, y, 3.6, "smooth_quartz", thickness=1)
            b.disk(xc, cz, y, 2.6, AIR)
            if y < y0 + 3:
                for a in range(30, 360, 30):
                    x = xc + int(round(4.6 * math.cos(math.radians(a))))
                    z = cz + int(round(4.6 * math.sin(math.radians(a))))
                    b.set(x, y, z, "quartz_pillar", axis="y")
        b.ring(cx(y0 + 3), cz, y0 + 3, 5, "smooth_quartz_slab", thickness=1.4, type="bottom", waterlogged="false")
        b.lantern(cx(y0 + 1) + 1, y0 + 1, cz - 1)
    # Cella campanaria
    yb = 32
    xb = cx(yb)
    b.disk(xb, cz, yb, 3.6, "smooth_quartz")
    for y in range(yb + 1, yb + 4):
        b.ring(xb, cz, y, 3.2, "quartz_pillar", axis="y")
        b.disk(xb, cz, y, 2.2, AIR)
    for a in range(0, 360, 45):
        x = xb + int(round(3 * math.cos(math.radians(a + 22))))
        z = cz + int(round(3 * math.sin(math.radians(a + 22))))
        b.set(x, yb + 1, z, AIR)
        b.set(x, yb + 2, z, AIR)
    b.disk(xb, cz, yb + 4, 3.4, "smooth_quartz_slab", type="bottom", waterlogged="false")
    b.set(xb + 1, yb + 1, cz + 1, "bell", attachment="floor", facing="north", powered="false")
    b.lantern(xb - 1, yb + 1, cz + 1)
    # Colonna interna verticale con scala a pioli fino alla cella campanaria
    col = c0 + 1
    b.fill(col, 1, cz - 1, col, yb, cz - 1, "smooth_quartz")
    b.ladder(col, 1, yb, cz, "south")
    b.set(col, yb + 1, cz, AIR)
    # Ingresso
    door_x = cx(1)
    b.entrance(door_x, 1, cz + 4, "north", wood="dark_oak", step="smooth_quartz")
    b.lantern(c0 - 1, 1, cz - 1)
    return b


@template("big_ben", "Big Ben (Elizabeth Tower)", "Landmark",
          "Torre dell'orologio di Londra con quadranti, cella campanaria, guglia e scala interna.")
def big_ben():
    b = Builder(11, 52, 11)
    c = 5
    b.fill(0, 0, 0, 10, 0, 10, "smooth_sandstone")
    b.room(1, 0, 1, 9, 31, 9, "smooth_sandstone", floor="sandstone", ceiling="cut_sandstone")
    for x in (1, 3, 5, 7, 9):
        for z in (1, 9):
            b.fill(x, 1, z, x, 30, z, "cut_sandstone")
            b.fill(z, 1, x, z, 30, x, "cut_sandstone")
    for y in range(4, 30, 5):
        for i in (2, 4, 6, 8):
            for x, z in ((i, 1), (i, 9), (1, i), (9, i)):
                b.set(x, y, z, "yellow_stained_glass_pane")
                b.set(x, y + 1, z, "yellow_stained_glass_pane")
    for y in (10, 20):
        b.fill(2, y, 2, 8, y, 8, "spruce_planks")
        b.lantern(5, y + 1, 7)
    b.lantern(7, 1, 7)
    b.lantern(3, 21, 7)
    # Sezione orologio (sporgente)
    b.room(0, 31, 0, 10, 38, 10, "chiseled_sandstone", floor="cut_sandstone", ceiling="cut_sandstone")
    for side in ("n", "s", "e", "w"):
        for dx in range(-2, 3):
            for dy in range(-2, 3):
                if dx * dx + dy * dy <= 5:
                    y = 34 + dy
                    if side == "n":
                        b.set(c + dx, y, 0, "white_concrete")
                    elif side == "s":
                        b.set(c + dx, y, 10, "white_concrete")
                    elif side == "e":
                        b.set(10, y, c + dx, "white_concrete")
                    else:
                        b.set(0, y, c + dx, "white_concrete")
        for (x, y, z) in ((c, 34, 0), (c, 35, 0), (c + 1, 34, 0)) if side == "n" else \
                ((c, 34, 10), (c, 35, 10), (c - 1, 34, 10)) if side == "s" else \
                ((10, 34, c), (10, 35, c), (10, 34, c + 1)) if side == "e" else ((0, 34, c), (0, 35, c), (0, 34, c - 1)):
            b.set(x, y, z, "black_concrete")
    b.lantern(5, 32, 5)
    b.fill(5, 32, 1, 5, 37, 1, "chiseled_sandstone")
    # Cella campanaria
    b.room(1, 38, 1, 9, 43, 9, "smooth_sandstone", floor="cut_sandstone", ceiling="cut_sandstone")
    for a in (3, 5, 7):
        for y in (39, 40, 41):
            if a != 5:
                b.set(a, y, 1, "iron_bars")
            b.set(a, y, 9, "iron_bars")
            b.set(1, y, a, "iron_bars")
            b.set(9, y, a, "iron_bars")
    b.set(5, 39, 5, "bell", attachment="floor", facing="south", powered="false")
    b.lantern(3, 39, 7)
    # Guglia
    y = 44
    for r in (4, 3, 2, 1):
        for _ in range(2):
            b.fill(c - r, y, c - r, c + r, y, c + r, "deepslate_tiles")
            y += 1
    b.fill(c, y, c, c, y + 1, c, "gold_block")
    b.set(c, y + 2, c, "lightning_rod", facing="up", powered="false", waterlogged="false")
    for x, z in ((1, 1), (9, 1), (1, 9), (9, 9)):
        b.fill(x, 44, z, x, 46, z, "cut_sandstone")
        b.set(x, 47, z, "gold_block")
    # Scala interna e ingresso
    b.ladder(5, 1, 42, 2, "south")
    b.entrance(5, 1, 9, "north", wood="dark_oak", step="sandstone")
    return b


@template("colosseum", "Colosseum", "Landmark",
          "Colosseo di Roma: anello ellittico a quattro ordini di arcate, gradinate, arena e un lato in rovina.")
def colosseum():
    rx, rz = 20, 16
    b = Builder(41, 17, 33, seed=11)
    cx, cz = 20, 16
    for x in range(41):
        for z in range(33):
            e = math.sqrt(((x - cx) / rx) ** 2 + ((z - cz) / rz) ** 2)
            ang = math.atan2(z - cz, x - cx)
            ruined = -0.3 < ang < 1.1
            if e > 1.0:
                continue
            if e < 0.6:
                b.set(x, 0, z, "sand")
                continue
            b.set(x, 0, z, "smooth_sandstone")
            if e >= 0.92:
                top = 16
                if ruined:
                    top = 6 + int(abs(math.sin(ang * 7)) * 6)
                for y in range(1, top + 1):
                    tier = (y - 1) // 4
                    k = int((ang + math.pi) / (2 * math.pi) * 64)
                    opening = tier < 3 and k % 2 == 0
                    if (y - 1) % 4 == 3:
                        b.set(x, y, z, "cut_sandstone")
                    elif opening and (y - 1) % 4 in (1, 2):
                        b.set(x, y, z, AIR)
                    else:
                        b.set(x, y, z, "smooth_sandstone" if k % 2 else "sandstone")
            elif e >= 0.86:
                for y in range(1, 4):
                    b.set(x, y, z, AIR)
            else:
                h = 2 + int((e - 0.6) / 0.26 * 10)
                if ruined:
                    h = min(h, 4 + int(abs(math.sin(ang * 5)) * 4))
                for y in range(1, h):
                    b.set(x, y, z, "sandstone")
                b.slab(x, h, z, "smooth_sandstone")
                if e < 0.64:
                    b.fill(x, 1, z, x, 2, z, "smooth_sandstone")
    # Ingressi assiali verso l'arena
    for x0, z0, x1, z1 in ((cx - 1, 0, cx + 1, 6), (cx - 1, 26, cx + 1, 32), (0, cz - 1, 8, cz + 1), (32, cz - 1, 40, cz + 1)):
        for x in range(x0, x1 + 1):
            for z in range(z0, z1 + 1):
                e = math.sqrt(((x - cx) / rx) ** 2 + ((z - cz) / rz) ** 2)
                if 0.58 < e <= 1.0:
                    b.set(x, 0, z, "smooth_sandstone")
                    b.clear(x, 1, z, x, 3, z)
                    if b.get(x, 4, z) not in (None, AIR):
                        b.lantern(x, 3, z, hanging=True)
    for x, z in ((cx, cz), (cx - 6, cz), (cx + 6, cz)):
        b.lantern(x, 1, z)
    # Lanterne nel corridoio coperto dietro le arcate
    for a in range(0, 360, 20):
        x = cx + int(round(rx * 0.89 * math.cos(math.radians(a))))
        z = cz + int(round(rz * 0.89 * math.sin(math.radians(a))))
        if b.get(x, 1, z) == AIR:
            b.lantern(x, 1, z)
    return b


@template("great_pyramid", "Great Pyramid of Giza", "Landmark",
          "Grande Piramide con facce lisce, corridoio d'ingresso illuminato e camera del re con il tesoro.")
def great_pyramid():
    n = 39
    b = Builder(n, 21, n)
    top = b.pyramid(0, 0, n - 1, n - 1, 0, "sandstone")
    for level in range(top + 1):
        a, z = level, n - 1 - level
        if a >= z:
            break
        for i in range(a, z + 1):
            b.stair(i, level, a, "sandstone", "south")
            b.stair(i, level, z, "sandstone", "north")
            b.stair(a, level, i, "sandstone", "east")
            b.stair(z, level, i, "sandstone", "west")
    b.set(n // 2, top, n // 2, "gold_block")
    c = n // 2
    # Corridoio dal lato nord fino alla camera
    b.clear(c, 1, 0, c, 2, c - 3)
    b.set(c, 0, 0, "smooth_sandstone")
    for z in range(2, c - 3, 4):
        if z >= 4:
            b.wall_torch(c, 2, z, "east")
    b.room(c - 3, 0, c - 3, c + 3, 5, c + 3, "smooth_sandstone", floor="chiseled_sandstone")
    b.clear(c, 1, c - 3, c, 2, c - 3)
    b.set(c, 1, c + 1, "gold_block")
    b.chest(c, 1, c + 2, "north")
    b.chest(c - 2, 1, c + 2, "north")
    for x, z in ((c - 2, c - 2), (c + 2, c - 2), (c + 2, c + 2)):
        b.lantern(x, 1, z)
    b.lantern(c, 4, c, hanging=True)
    return b


@template("parthenon", "Parthenon", "Landmark",
          "Partenone di Atene: stilobate a gradini, peristilio di colonne doriche, frontoni e cella con statua.")
def parthenon():
    W, L = 19, 33
    b = Builder(W, 18, L)
    b.fill(0, 0, 0, W - 1, 0, L - 1, "smooth_quartz")
    b.fill(1, 1, 1, W - 2, 1, L - 2, "smooth_quartz")
    for x in range(1, W - 1):
        b.stair(x, 1, 1, "smooth_quartz", "south")
        b.stair(x, 1, L - 2, "smooth_quartz", "north")
    for z in range(2, L - 2):
        b.stair(1, 1, z, "smooth_quartz", "east")
        b.stair(W - 2, 1, z, "smooth_quartz", "west")
    b.fill(2, 2, 2, W - 3, 2, L - 3, "quartz_block")
    cols = [(x, 2) for x in range(2, W - 2, 2)] + [(x, L - 3) for x in range(2, W - 2, 2)] + \
           [(2, z) for z in range(4, L - 3, 2)] + [(W - 3, z) for z in range(4, L - 3, 2)]
    for x, z in cols:
        b.fill(x, 3, z, x, 8, z, "quartz_pillar", axis="y")
        b.set(x, 9, z, "chiseled_quartz_block")
    b.walls(2, 10, 2, W - 3, 10, L - 3, "smooth_quartz")
    b.walls(2, 11, 2, W - 3, 11, L - 3, "chiseled_quartz_block")
    b.fill(3, 11, 3, W - 4, 11, L - 4, "smooth_quartz")
    # Tetto basso con frontoni (pendenza di mezzo blocco)
    half = (W - 3) // 2
    for k in range(half):
        y = 12 + k // 2
        for x in (2 + k, W - 3 - k):
            for z in range(1, L - 1):
                if k % 2 == 0:
                    b.slab(x, y, z, "smooth_quartz")
                else:
                    b.slab(x, y, z, "smooth_quartz", top=True)
            for z in (2, L - 3):
                for yy in range(12, y):
                    b.set(x, yy, z, "smooth_quartz")
    # Cella interna
    b.room(5, 2, 7, W - 6, 10, L - 8, "quartz_bricks", floor="polished_diorite", ceiling=False)
    b.entrance(W // 2, 3, 7, "south", wood="birch", step=None)
    b.fill(W // 2, 3, L - 11, W // 2, 5, L - 11, "gold_block")
    b.set(W // 2, 6, L - 11, "chiseled_quartz_block")
    for x, z in ((6, 9), (W - 7, 9), (6, L - 10), (W - 7, L - 10), (W // 2, 15)):
        b.lantern(x, 3, z)
    for x, z in ((4, 4), (W - 5, 4), (4, L - 5), (W - 5, L - 5), (W // 2, 4), (W // 2, L - 5)):
        b.lantern(x, 3, z)
    for z in range(8, L - 8, 6):
        b.lantern(4, 3, z)
        b.lantern(W - 5, 3, z)
    return b


@template("stonehenge", "Stonehenge", "Landmark",
          "Cerchio megalitico di Stonehenge con architravi, triliti interni, pietre cadute e altare.")
def stonehenge():
    b = Builder(27, 8, 27, seed=5)
    c = 13
    mats = [("stone", 5), ("andesite", 3), ("tuff", 2), ("mossy_cobblestone", 1)]
    pos = []
    for i in range(20):
        a = 2 * math.pi * i / 20
        pos.append((c + int(round(11 * math.cos(a))), c + int(round(11 * math.sin(a)))))
    for i, (x, z) in enumerate(pos):
        if i in (6, 13):
            continue
        b.fill_random(x, 0, z, x, 4, z, mats)
        nx, nz = pos[(i + 1) % len(pos)]
        if i not in (5, 12, 15):
            b.line(x, 5, z, nx, 5, nz, "stone")
    for k, a in enumerate(range(0, 300, 60)):
        ang = math.radians(a + 120)
        x = c + int(round(6 * math.cos(ang)))
        z = c + int(round(6 * math.sin(ang)))
        dx = int(round(math.sin(ang)))
        dz = -int(round(math.cos(ang)))
        b.fill_random(x, 0, z, x, 5, z, mats)
        b.fill_random(x + dx * 2, 0, z + dz * 2, x + dx * 2, 5, z + dz * 2, mats)
        b.line(x, 6, z, x + dx * 2, 6, z + dz * 2, "stone")
    # Pietre cadute
    b.line(4, 0, 20, 8, 0, 23, "andesite")
    b.line(22, 0, 6, 24, 0, 10, "stone")
    b.fill(c - 1, 0, c, c + 1, 0, c, "smooth_stone")
    b.lantern(c, 1, c)
    return b


@template("taj_mahal", "Taj Mahal", "Landmark",
          "Taj Mahal in marmo bianco: piattaforma, iwan ad arco, cupola a cipolla, quattro minareti e vasca riflettente.")
def taj_mahal():
    W, L = 41, 57
    b = Builder(W, 36, L)
    c = 20
    M = "smooth_quartz"
    b.fill(0, 0, 0, 40, 2, 40, "quartz_bricks")
    # Scalinata frontale
    for k in range(3):
        for x in range(c - 2, c + 3):
            b.set(x, k, 41 + (2 - k), "smooth_quartz_stairs", facing="north", half="bottom", shape="straight",
                  waterlogged="false")
            for kk in range(k):
                b.set(x, kk, 41 + (2 - k), M)
    # Corpo principale con angoli smussati
    x1, x2 = 10, 30
    for x in range(x1, x2 + 1):
        for z in range(x1, x2 + 1):
            if min(x - x1, x2 - x) + min(z - x1, x2 - z) < 3:
                continue
            for y in range(3, 19):
                edge = x in (x1, x2) or z in (x1, x2) or min(x - x1, x2 - x) + min(z - x1, x2 - z) == 3
                b.set(x, y, z, M if edge else AIR)
    b.fill(x1 + 1, 2, x1 + 1, x2 - 1, 2, x2 - 1, "polished_diorite")
    b.fill(x1, 19, x1, x2, 19, x2, M)
    for x in range(x1, x2 + 1):
        for z in range(x1, x2 + 1):
            if min(x - x1, x2 - x) + min(z - x1, x2 - z) < 3:
                b.remove(x, 19, z)
    # Iwan (grandi archi) su ogni lato, con passaggio all'interno
    b.carve_arch("x", c - 3, c + 3, x2 - 1, x2, 3, 12, pointed=True)
    b.carve_arch("x", c - 3, c + 3, x1, x1 + 1, 3, 12, pointed=True)
    b.carve_arch("z", c - 3, c + 3, x1, x1 + 1, 3, 12, pointed=True)
    b.carve_arch("z", c - 3, c + 3, x2 - 1, x2, 3, 12, pointed=True)
    for x in range(c - 4, c + 5):
        for y in range(3, 17):
            for z in (x2 + 1, x1 - 1):
                if b.get(x, y, z) is None and (y >= 15 or x in (c - 4, c + 4)):
                    b.set(x, y, z, "chiseled_quartz_block")
    # Cupola principale
    b.cylinder(c, c, 20, 22, 6, M, hollow=True)
    b.disk(c, c, 19, 5.2, AIR)
    b.fill(c, 29, c, c, 33, c, "white_concrete")
    b.lantern(c, 28, c, hanging=True)
    profile = [6.5, 7.5, 8, 8, 7.8, 7.2, 6.4, 5.4, 4.2, 3, 1.8, 0.8]
    for i, r in enumerate(profile):
        b.ring(c, c, 23 + i, r, "white_concrete", thickness=1.4)
    b.fill(c, 35 - 1, c, c, 35, c, "gold_block")
    # Chhatri (piccole cupole) agli angoli del tetto
    for x, z in ((x1 + 3, x1 + 3), (x2 - 3, x1 + 3), (x1 + 3, x2 - 3), (x2 - 3, x2 - 3)):
        b.cylinder(x, z, 20, 22, 1.6, M)
        b.dome(x, 23, z, 2, "white_concrete", hollow=False)
        b.set(x, 26, z, "gold_block")
    # Minareti
    for x, z in ((3, 3), (37, 3), (3, 37), (37, 37)):
        b.cylinder(x, z, 3, 28, 1.5, "white_concrete")
        for y in (11, 19, 27):
            b.ring(x, z, y, 2.6, "smooth_quartz_slab", thickness=1.2, type="bottom", waterlogged="false")
        b.dome(x, 29, z, 1.6, M, hollow=False)
        b.set(x, 32, z, "gold_block")
        b.lantern(x + 2, 3, z)
    # Interno: cenotafio e luci
    b.fill(c - 1, 3, c, c + 1, 3, c, "chiseled_quartz_block")
    for x, z in ((c - 5, c - 5), (c + 5, c - 5), (c - 5, c + 5), (c + 5, c + 5), (c, c - 3), (c, c + 3)):
        b.lantern(x, 3, z)
    for x, z in ((c, 12), (c, 28), (12, c), (28, c)):
        b.lantern(x, 3, z)
    for x in range(4, 37, 6):
        for z in range(4, 37, 6):
            if b.get(x, 3, z) == AIR:
                b.lantern(x, 3, z)
    # Vasca riflettente con giardino
    b.fill(c - 3, 0, 44, c + 3, 0, 56, "quartz_bricks")
    b.fill(c - 1, 0, 45, c + 1, 0, 55, "water", level="0")
    for z in range(45, 56, 3):
        b.tree(c - 6, 0, z, "oak", height=3, radius=1)
        b.tree(c + 6, 0, z, "oak", height=3, radius=1)
    return b


@template("tower_bridge", "Tower Bridge", "Landmark",
          "Tower Bridge di Londra: due torri gotiche, passerelle alte vetrate, catene blu e carreggiata.")
def tower_bridge():
    L, W = 49, 9
    b = Builder(L, 36, W, seed=2)
    deck = 8
    b.fill(0, deck, 1, L - 1, deck, W - 2, "polished_andesite")
    b.fill(0, deck, 4, L - 1, deck, 4, "gray_concrete")
    for x in range(L):
        b.set(x, deck + 1, 1, "light_blue_stained_glass_pane")
        b.set(x, deck + 1, W - 2, "light_blue_stained_glass_pane")
    towers = (10, 32)
    for tx in towers:
        b.fill(tx, 0, 0, tx + 6, deck - 1, W - 1, "stone_bricks")
        for y in range(deck, 29):
            for x in range(tx, tx + 7):
                for z in range(W):
                    edge = x in (tx, tx + 6) or z in (0, W - 1)
                    if edge:
                        b.set(x, y, z, "stone_bricks" if (x + y) % 5 else "chiseled_stone_bricks")
        b.clear(tx + 1, deck + 1, 1, tx + 5, 27, W - 2)
        b.carve_arch("z", 1, W - 2, tx, tx + 6, deck + 1, 6, pointed=True)
        for y in range(16, 28, 4):
            for x in (tx + 2, tx + 4):
                b.set(x, y, 0, "glass_pane")
                b.set(x, y, W - 1, "glass_pane")
        for y in (15, 23):
            b.fill(tx + 1, y, 1, tx + 5, y, W - 2, "spruce_planks")
            b.lantern(tx + 4, y + 1, 4)
        b.fill(tx + 1, 28, 1, tx + 5, 28, W - 2, "stone_bricks")
        b.ladder(tx + 3, deck + 1, 27, 1, "south")
        b.lantern(tx + 5, deck + 1, 7)
        # Torrette d'angolo con tetti a punta
        for x, z in ((tx, 0), (tx + 6, 0), (tx, W - 1), (tx + 6, W - 1)):
            b.fill(x, 29, z, x, 31, z, "stone_bricks")
            b.fill(x, 32, z, x, 33, z, "deepslate_tiles")
            b.set(x, 34, z, "gold_block")
        b.hip_roof(tx + 1, tx + 5, 1, W - 2, 29, "deepslate_tile", "deepslate_tiles", overhang=0)
    # Passerelle alte
    for y in (24, 25, 26):
        for x in range(towers[0] + 7, towers[1]):
            b.set(x, y, 2, "light_blue_concrete" if y != 25 else "glass")
            b.set(x, y, W - 3, "light_blue_concrete" if y != 25 else "glass")
    b.fill(towers[0] + 7, 23, 2, towers[1] - 1, 23, W - 3, "light_blue_concrete")
    b.fill(towers[0] + 7, 27, 2, towers[1] - 1, 27, W - 3, "light_blue_concrete")
    b.clear(towers[0] + 7, 24, 3, towers[1] - 1, 26, W - 4)
    b.clear(towers[0] + 6, 24, 3, towers[0] + 6, 25, W - 4)
    b.clear(towers[1], 24, 3, towers[1], 25, W - 4)
    for x in range(towers[0] + 9, towers[1] - 1, 4):
        b.lantern(x, 24, 4)
    # Catene di sospensione
    for z in (1, W - 2):
        b.line(0, deck + 2, z, towers[0], 27, z, "light_blue_concrete")
        b.line(L - 1, deck + 2, z, towers[1] + 6, 27, z, "light_blue_concrete")
    for x in range(2, L, 8):
        b.lantern(x, deck + 1, 2)
        b.lantern(x, deck + 1, W - 3)
    return b


@template("moai_heads", "Moai of Easter Island", "Landmark",
          "Tre statue Moai dell'Isola di Pasqua su un ahu di pietra, una con il pukao rosso.")
def moai_heads():
    b = Builder(19, 13, 8, seed=9)
    b.fill_random(0, 0, 1, 18, 1, 6, [("stone_bricks", 4), ("mossy_stone_bricks", 1), ("cobblestone", 2)])
    for i, a in enumerate((2, 8, 14)):
        b.fill(a, 2, 2, a + 2, 10, 4, "tuff")
        b.fill(a, 9, 2, a + 2, 10, 4, "polished_tuff")
        for x in range(a, a + 3):
            b.stair(x, 8, 5, "polished_tuff", "north", top=True)
        b.set(a + 1, 6, 5, "polished_tuff")
        b.set(a + 1, 5, 5, "tuff_stairs", facing="north", half="top", shape="straight", waterlogged="false")
        b.slab(a + 1, 3, 5, "tuff", top=True)
        b.set(a - 1 if a > 0 else a, 6, 3, "tuff_wall")
        b.set(a + 3, 6, 3, "tuff_wall")
        if i == 1:
            b.cylinder(a + 1, 3, 11, 12, 1.4, "red_terracotta")
    for x in (0, 18):
        b.lantern(x, 2, 6)
    return b


@template("el_castillo", "El Castillo (Chichen Itza)", "Landmark",
          "Piramide maya di Kukulkan: nove terrazze, scalinate sui quattro lati e tempio sulla cima.")
def el_castillo():
    n = 45
    b = Builder(n, 25, n, seed=13)
    c = n // 2
    for t in range(9):
        a = 9 + t
        bb = n - 1 - 9 - t
        mat = [("stone_bricks", 5), ("mossy_stone_bricks", 2), ("cracked_stone_bricks", 1)]
        b.fill_random(a, t * 2, a, bb, t * 2 + 1, bb, mat)
    for s in range(18):
        y = 17 - s
        for side in ("n", "s", "e", "w"):
            for w in range(-2, 3):
                if side == "s":
                    x, z, f = c + w, c + 5 + s, "north"
                elif side == "n":
                    x, z, f = c + w, c - 5 - s, "south"
                elif side == "e":
                    x, z, f = c + 5 + s, c + w, "west"
                else:
                    x, z, f = c - 5 - s, c + w, "east"
                if abs(w) == 2:
                    b.fill(x, 0, z, x, y + 1, z, "stone_bricks")
                else:
                    b.fill(x, 0, z, x, y - 1, z, "stone_bricks")
                    b.stair(x, y, z, "stone_brick", f)
    for x, z in ((c - 2, c + 23), (c + 2, c + 23)):
        b.set(x, 1, z, "carved_pumpkin", facing="south")
    # Tempio sulla cima
    b.room(c - 4, 18, c - 4, c + 4, 23, c + 4, "chiseled_stone_bricks", floor="stone_bricks", ceiling="stone_bricks")
    for x, z, f in ((c, c + 4, "north"), (c, c - 4, "south"), (c + 4, c, "west"), (c - 4, c, "east")):
        b.clear(x, 19, z, x, 21, z)
    for i in range(c - 4, c + 5, 2):
        for x, z in ((i, c - 4), (i, c + 4), (c - 4, i), (c + 4, i)):
            b.set(x, 24, z, "stone_bricks")
    b.lantern(c - 2, 19, c - 2)
    b.lantern(c + 2, 19, c + 2)
    b.lantern(c, 22, c, hanging=True)
    return b


@template("arc_de_triomphe", "Arc de Triomphe", "Landmark",
          "Arco di Trionfo di Parigi con fornice principale, archi laterali, rilievi e terrazza panoramica.")
def arc_de_triomphe():
    W, L = 17, 11
    b = Builder(W, 19, L)
    b.fill(0, 0, 0, W - 1, 15, L - 1, "smooth_sandstone")
    b.carve_arch("x", 5, 11, 0, L - 1, 0, 12)
    b.carve_arch("z", 3, 7, 0, W - 1, 0, 7)
    b.fill(5, 0, 0, 11, 0, L - 1, "smooth_stone")
    b.fill(0, 0, 3, W - 1, 0, 7, "smooth_stone")
    for x, z in ((1, 0), (13, 0), (1, L - 1), (13, L - 1)):
        b.fill(x, 4, z, x + 2, 8, z, "chiseled_sandstone")
    for x in range(W):
        b.stair(x, 13, 0, "smooth_sandstone", "south", top=True)
        b.stair(x, 13, L - 1, "smooth_sandstone", "north", top=True)
    b.fill(0, 14, 0, W - 1, 15, L - 1, "cut_sandstone")
    b.walls(0, 16, 0, W - 1, 16, L - 1, "sandstone_wall")
    b.clear(1, 16, 1, W - 2, 17, L - 2)
    # Scala interna al pilone ovest fino alla terrazza
    b.clear(1, 1, 8, 3, 14, 9)
    b.entrance(2, 1, 8, "south", wood="dark_oak", step=None)
    b.ladder(1, 1, 15, 9, "east")
    b.set(1, 16, 9, AIR)
    b.lantern(3, 1, 9)
    # Fiamma del milite ignoto e luci sotto l'arco
    b.set(8, 1, 5, "chiseled_quartz_block")
    b.lantern(8, 2, 5)
    b.lantern(6, 10, 5, hanging=True)
    b.lantern(10, 10, 5, hanging=True)
    for x, z in ((3, 2), (13, 2), (3, 8), (13, 8)):
        b.lantern(x, 16, z)
    return b


@template("five_storey_pagoda", "Five-Storey Pagoda", "Landmark",
          "Pagoda giapponese a cinque piani con gronde ricurve, pilastro centrale e guglia sorin.")
def five_storey_pagoda():
    W = 17
    b = Builder(W, 38, W)
    c = 8
    b.fill(1, 0, 1, W - 2, 0, W - 2, "stone_bricks")
    y = 1
    for level in range(5):
        r = 4 - (level + 1) // 2
        x1, x2 = c - r, c + r
        b.room(x1, y - 1 if level else 0, x1, x2, y + 3, x2, "white_terracotta", floor="spruce_planks", ceiling="spruce_planks")
        for x, z in ((x1, x1), (x2, x1), (x1, x2), (x2, x2)):
            b.fill(x, y, z, x, y + 2, z, "stripped_mangrove_log", axis="y")
        for i in range(x1 + 1, x2):
            if (i - x1) % 2 == 0:
                for x, z in ((i, x1), (i, x2), (x1, i), (x2, i)):
                    b.fill(x, y, z, x, y + 2, z, "stripped_mangrove_log", axis="y")
        b.set(c, y + 1, x1, "spruce_trapdoor", facing="north", half="bottom", open="true", powered="false",
              waterlogged="false")
        b.lantern(c + 1, y, c + 1)
        y = b.eave(x1, x2, x1, x2, y + 3, "deepslate_tile", overhang=2) + 1
    top = b.hip_roof(c - 1, c + 1, c - 1, c + 1, y - 1, "deepslate_tile", "deepslate_tiles", overhang=1)
    b.fill(c, top + 1, c, c, top + 8, c, "iron_bars")
    for yy in range(top + 2, top + 8, 2):
        b.set(c, yy, c, "waxed_exposed_cut_copper")
    b.set(c, top + 9, c, "lightning_rod", facing="up", powered="false", waterlogged="false")
    # Pilastro centrale con scala a pioli
    b.fill(c, 1, c, c, y - 2, c, "stripped_spruce_log", axis="y")
    b.ladder(c, 1, y - 2, c - 1, "north")
    b.entrance(c, 1, c + 4, "north", wood="spruce", step="stone_brick")
    for x, z in ((1, 1), (W - 2, 1), (1, W - 2), (W - 2, W - 2)):
        b.set(x, 1, z, "stone_brick_wall")
        b.lantern(x, 2, z)
    return b


@template("torii_gate", "Torii Gate", "Landmark",
          "Portale torii rosso in stile Itsukushima con architrave nera ricurva e lanterne di pietra.")
def torii_gate():
    b = Builder(15, 11, 7)
    for x in (3, 11):
        b.set(x, 0, 3, "black_concrete")
        b.fill(x, 1, 3, x, 8, 3, "red_concrete")
    b.fill(2, 6, 3, 12, 6, 3, "red_concrete")
    b.fill(1, 8, 3, 13, 8, 3, "red_concrete")
    b.fill(0, 9, 3, 14, 9, 3, "black_concrete")
    b.stair(0, 10, 3, "blackstone", "east")
    b.stair(14, 10, 3, "blackstone", "west")
    b.set(7, 7, 3, "black_concrete")
    for x, z in ((0, 0), (14, 0), (0, 6), (14, 6)):
        b.set(x, 0, z, "stone_brick_wall")
        b.lantern(x, 1, z)
        b.slab(x, 2, z, "stone_brick")
    return b


@template("great_wall", "Great Wall Segment", "Landmark",
          "Tratto della Grande Muraglia cinese con camminamento merlato e torre di guardia abitabile.")
def great_wall():
    b = Builder(11, 17, 45, seed=21)
    mats = [("stone_bricks", 5), ("cracked_stone_bricks", 1), ("mossy_stone_bricks", 1), ("cobblestone", 1)]
    b.fill_random(3, 0, 0, 7, 7, 44, mats)
    b.fill(3, 8, 0, 7, 8, 44, "polished_andesite")
    for z in range(45):
        for x in (3, 7):
            if z % 2 == 0:
                b.set(x, 9, z, "stone_bricks")
            else:
                b.slab(x, 9, z, "stone_brick")
    # Torre di guardia
    t1, t2 = 18, 26
    b.room(1, 0, t1, 9, 14, t2, "stone_bricks", floor="stone_bricks", ceiling="stone_bricks")
    b.fill(2, 8, t1 + 1, 8, 8, t2 - 1, "spruce_planks")
    b.clear(2, 1, t1 + 1, 8, 7, t2 - 1)
    for z in (t1, t2):
        b.carve_arch("x", 4, 6, z, z, 9, 4)
    for z in range(t1 + 3, t2 - 1, 3):
        for x in (1, 9):
            b.carve_arch("z", z, z, x, x, 10, 2)
    for i in range(1, 10, 2):
        b.set(i, 15, t1, "stone_bricks")
        b.set(i, 15, t2, "stone_bricks")
    for i in range(t1, t2 + 1, 2):
        b.set(1, 15, i, "stone_bricks")
        b.set(9, 15, i, "stone_bricks")
    b.entrance(1, 1, t1 + 6, "east", wood="dark_oak", step="stone_brick")
    b.ladder(2, 1, 14, t1 + 2, "east")
    b.set(2, 15, t1 + 2, AIR)
    b.lantern(5, 1, t1 + 4)
    b.lantern(5, 9, t1 + 4)
    b.lantern(7, 9, t2 - 2)
    b.lantern(5, 13, t1 + 4, hanging=True)
    b.chest(8, 9, t1 + 1, "south")
    b.lantern(5, 15, t1 + 4)
    for z in range(2, 45, 8):
        if not t1 <= z <= t2:
            b.lantern(5, 9, z)
    return b


@template("dutch_windmill", "Dutch Windmill", "Landmark",
          "Mulino a vento olandese di Kinderdijk: base ottagonale in mattoni, ballatoio, cappello e pale in tela.")
def dutch_windmill():
    W = 17
    b = Builder(W, 26, W)
    c = 8
    for y in range(0, 16):
        r = 5 if y < 6 else 4 if y < 14 else 3
        mat = "bricks" if y < 6 else "dark_oak_planks"
        b.octagon(c, c, y, r, mat if y > 0 else "stone_bricks", hollow=y > 0)
    for y in (6, 11):
        b.octagon(c, c, y, 4, "spruce_planks")
    b.octagon(c, c, 6, 6, "spruce_slab", type="top", waterlogged="false")
    b.octagon(c, c, 6, 4, "spruce_planks")
    for x in range(W):
        for z in range(W):
            if b.get(x, 6, z) == "minecraft:spruce_slab":
                dx, dz = abs(x - c), abs(z - c)
                if dx == 6 or dz == 6 or dx + dz == 9:
                    b.set(x, 7, z, "spruce_fence")
    b.cone(c, c, 16, 3.5, "dark_oak_planks", step=0.8)
    b.set(c, 21, c, "dark_oak_fence")
    # Pale
    hub_z = c - 4
    b.set(c, 15, hub_z, "dark_oak_log", axis="z")
    for sx, sy in ((1, 1), (-1, 1), (1, -1), (-1, -1)):
        for k in range(1, 9):
            x, y = c + sx * k, 15 + sy * k
            if 0 <= y < 26:
                b.set(x, y, hub_z, "dark_oak_fence")
                if k > 2:
                    b.set(x, y - sy, hub_z, "white_wool")
                    b.set(x - sx, y, hub_z, "white_wool")
    # Interni
    b.entrance(c, 1, c + 5, "north", wood="spruce", step="stone_brick")
    b.fill(c, 1, c - 4, c, 5, c - 4, "bricks")
    b.ladder(c, 1, 11, c - 3, "south")
    b.set(c, 6, c - 3, "ladder", facing="south", waterlogged="false")
    b.set(c, 11, c - 3, "ladder", facing="south", waterlogged="false")
    b.set(c + 2, 1, c, "grindstone", face="floor", facing="north")
    b.set(c - 2, 1, c, "stonecutter", facing="north")
    b.set(c + 2, 7, c, "barrel", facing="up", open="false")
    b.chest(c - 2, 7, c, "east")
    b.lantern(c, 1, c)
    b.lantern(c, 7, c)
    b.lantern(c, 12, c)
    # Porta sul ballatoio
    b.door(c + 4, 7, c, "east", wood="spruce")
    return b


@template("pantheon", "Pantheon", "Landmark",
          "Pantheon di Roma: rotonda con cupola e oculo, pavimento a scacchi e pronao a colonne con frontone.")
def pantheon():
    W, L = 25, 33
    b = Builder(W, 24, L)
    c, cz = 12, 12
    b.disk(c, cz, 0, 11, "polished_andesite")
    for x in range(c - 10, c + 11):
        for z in range(cz - 10, cz + 11):
            if (x - c) ** 2 + (z - cz) ** 2 <= 100:
                b.set(x, 0, z, "polished_diorite" if (x + z) % 2 else "polished_andesite")
    b.cylinder(c, cz, 1, 10, 11, "stone_bricks", hollow=True, thickness=1.5)
    b.dome(c, 11, cz, 11, "smooth_stone", hollow=True, thickness=1.5)
    b.disk(c, cz, 21, 1.6, AIR)
    b.disk(c, cz, 22, 1.6, AIR)
    for a in range(0, 360, 45):
        x = c + int(round(8 * math.cos(math.radians(a))))
        z = cz + int(round(8 * math.sin(math.radians(a))))
        b.lantern(x, 1, z)
    b.lantern(c, 1, cz + 3)
    b.lantern(c, 1, cz - 3)
    b.set(c, 1, cz - 9, "chiseled_stone_bricks")
    b.set(c, 2, cz - 9, "gold_block")
    # Avancorpo e pronao
    b.fill(c - 5, 0, 21, c + 5, 12, 24, "stone_bricks")
    b.clear(c - 4, 1, 20, c + 4, 9, 24)
    b.fill(c - 8, 0, 24, c + 8, 0, 32, "polished_andesite")
    for x in range(c - 7, c + 8, 2):
        for z in (26, 29, 32):
            if z == 32 or x in (c - 7, c + 7) or z == 26 and abs(x - c) > 2:
                b.fill(x, 1, z, x, 9, z, "polished_granite")
                b.set(x, 10, z, "chiseled_stone_bricks")
    b.fill(c - 8, 11, 24, c + 8, 11, 32, "smooth_stone")
    b.gable_roof(c - 8, c + 8, 24, 32, 12, "stone_brick", "stone_bricks", axis="z", overhang=0)
    for x, z in ((c - 4, 27), (c + 4, 27), (c, 30)):
        b.lantern(x, 1, z)
    return b
