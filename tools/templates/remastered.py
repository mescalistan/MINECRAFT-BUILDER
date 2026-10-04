"""Remakes of the weakest templates: more detail, cleaner proportions, more faithful to the originals."""
import math

from template_builder import Builder, AIR, template


@template("arc_de_triomphe", "Arc de Triomphe", "Landmark",
          "Arco di Trionfo di Parigi: grande fornice con archivolto scolpito, archi laterali, gruppi in rilievo "
          "sui piloni, cornice, attico e terrazza panoramica raggiungibile con una scala interna.")
def arc_de_triomphe():
    W, L = 19, 13
    b = Builder(W, 22, L)
    SS, CUT, CH = "smooth_sandstone", "cut_sandstone", "chiseled_sandstone"
    b.fill(0, 0, 0, W - 1, 0, L - 1, CUT)
    b.fill(1, 1, 1, W - 2, 18, L - 2, SS)
    b.carve_arch("x", 6, 12, 0, L - 1, 1, 12)
    b.carve_arch("z", 5, 7, 0, W - 1, 1, 7)
    # archivolts: carved frame around the openings
    for (x, y, z) in list(b.cells):
        if b.get(x, y, z) != "minecraft:" + SS or y == 0:
            continue
        on_face = z in (1, L - 2) or x in (1, W - 2)
        if on_face and any(b.get(x + dx, y + dy, z + dz) == AIR
                           for dx, dy, dz in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, 0, 1), (0, 0, -1))):
            b.set(x, y, z, CH)
    # sculpture groups in relief on the piers
    for xa in (2, 14):
        for z, facing in ((0, "south"), (L - 1, "north")):
            b.fill(xa, 2, z, xa + 2, 10, z, CUT)
            b.fill(xa + 1, 4, z, xa + 1, 8, z, CH)
            for x in range(xa, xa + 3):
                b.stair(x, 11, z, "smooth_sandstone", facing, top=True)
                b.stair(x, 1, z, "sandstone", facing)
    # cornice, attic, crown
    for y in (15, 18):
        for x in range(W):
            b.stair(x, y, 0, "smooth_sandstone", "south", top=True)
            b.stair(x, y, L - 1, "smooth_sandstone", "north", top=True)
        for z in range(1, L - 1):
            b.stair(0, y, z, "smooth_sandstone", "east", top=True)
            b.stair(W - 1, y, z, "smooth_sandstone", "west", top=True)
    b.walls(1, 16, 1, W - 2, 16, L - 2, CH)
    b.walls(1, 17, 1, W - 2, 17, L - 2, CUT)
    for x in range(3, W - 3, 3):
        b.set(x, 17, 1, CH)
        b.set(x, 17, L - 2, CH)
    b.walls(1, 19, 1, W - 2, 19, L - 2, "sandstone_wall")
    b.clear(2, 19, 2, W - 3, 20, L - 3)
    # staircase inside the west pier up to the terrace
    b.clear(2, 1, 9, 4, 17, 10)
    b.entrance(3, 1, 8, "south", wood="dark_oak", step=None)
    b.ladder(3, 1, 18, 10, "north")
    b.lantern(2, 1, 9)
    for y in (9, 14):
        b.set(4, y, 9, CH)
        b.lantern(4, y + 1, 9)
    # eternal flame and lights under the arches
    b.set(9, 1, 6, "chiseled_quartz_block")
    b.lantern(9, 2, 6)
    for z in (3, 9):
        b.lantern(9, 12, z, hanging=True)
    for x in (2, 16):
        b.lantern(x, 7, 6, hanging=True)
    for x, z in ((2, 2), (16, 2), (2, 10), (16, 10)):
        b.lantern(x, 19, z)
    return b


@template("moai_heads", "Moai of Easter Island", "Landmark",
          "Cinque Moai dell'Isola di Pasqua su un ahu cerimoniale: volti allungati con arcata sopraccigliare, "
          "naso, labbra imbronciate, orbite profonde, orecchie lunghe, braccia scolpite e pukao rossi.")
def moai_heads():
    W, L = 36, 11
    b = Builder(W, 20, L, seed=9)
    b.fill_random(0, 0, 2, W - 1, 1, 8, [("stone_bricks", 4), ("tuff", 3), ("mossy_stone_bricks", 1),
                                         ("cobblestone", 1)])
    for x in range(W):
        b.stair(x, 0, 9, "stone_brick", "north")
        b.stair(x, 0, 1, "stone_brick", "south")
    for i, extra in enumerate((0, 1, 2, 1, 0)):
        a = 1 + 7 * i
        y0 = 2
        top = y0 + 11 + extra
        b.fill(a, y0, 4, a + 4, top, 6, "tuff")
        b.fill(a, top, 4, a + 4, top, 6, "polished_tuff")
        for x in range(a, a + 5):                                   # heavy brow
            b.stair(x, top - 2, 7, "tuff_brick", "north", top=True)
        for x in (a + 1, a + 3):                                    # deep eye sockets
            b.set(x, top - 3, 6, AIR)
            b.set(x, top - 3, 5, "polished_deepslate")
        for y in range(top - 5, top - 2):                           # long nose
            b.set(a + 2, y, 7, "polished_tuff")
        b.stair(a + 1, top - 5, 7, "tuff", "north")
        b.stair(a + 3, top - 5, 7, "tuff", "north")
        for x in range(a + 1, a + 4):
            b.slab(x, top - 6, 7, "polished_tuff", top=True)         # pouting lips
            b.stair(x, top - 7, 7, "tuff", "north", top=True)        # chin
        for x in (a - 1, a + 5):                                    # long ears
            b.fill(x, top - 5, 5, x, top - 2, 5, "tuff_wall")
        for x in (a, a + 4):                                        # arms and hands
            b.fill(x, y0 + 1, 7, x, y0 + 5, 7, "tuff_bricks")
        for x in (a + 1, a + 3):
            b.slab(x, y0 + 1, 7, "tuff_brick", top=True)
        if i in (1, 3):
            b.cylinder(a + 2, 5, top + 1, top + 2, 1.5, "red_terracotta")
        b.lantern(a + 2, 2, 8)
    for x in (0, W - 1):
        b.lantern(x, 2, 3)
    return b


@template("colosseum", "Colosseum", "Landmark",
          "Colosseo di Roma: anello ellittico con tre ordini di arcate regolari e attico, corridoi interni "
          "illuminati, gradinate, podio e arena, quattro ingressi e il lato in rovina.")
def colosseum():
    rx, rz = 21.0, 17.0
    W, L = 43, 35
    cx, cz = 21, 17
    b = Builder(W, 18, L, seed=11)

    def e_of(x, z):
        return math.sqrt(((x - cx) / rx) ** 2 + ((z - cz) / rz) ** 2)

    # arc length along the outer ellipse, so that the arcades are evenly spaced
    steps = 720
    table = [0.0]
    px, pz = rx, 0.0
    for i in range(1, steps + 1):
        t = 2 * math.pi * i / steps
        qx, qz = rx * math.cos(t), rz * math.sin(t)
        table.append(table[-1] + math.hypot(qx - px, qz - pz))
        px, pz = qx, qz
    bays = int(table[-1] // 3)
    scale = bays * 3 / table[-1]

    def pos(x, z):
        t = math.atan2((z - cz) / rz, (x - cx) / rx) % (2 * math.pi)
        return int(table[min(steps, int(t / (2 * math.pi) * steps))] * scale)

    def ruin_top(x, z):
        a = math.atan2(z - cz, x - cx)
        return 5 + int(abs(math.sin(a * 9)) * 5) if (a > 2.35 or a < -2.75) else 16

    inside = {(x, z) for x in range(W) for z in range(L) if e_of(x, z) <= 1.0}
    nbrs = ((1, 0), (-1, 0), (0, 1), (0, -1))
    outer = {p for p in inside if any((p[0] + dx, p[1] + dz) not in inside for dx, dz in nbrs)}
    inner_wall = {p for p in inside if e_of(*p) <= 0.84 and any(e_of(p[0] + dx, p[1] + dz) > 0.84 for dx, dz in nbrs)}
    for (x, z) in inside:
        e = e_of(x, z)
        top = ruin_top(x, z)
        if e < 0.6:
            b.set(x, 0, z, "sand" if (x + z) % 7 else "smooth_sandstone")
            continue
        b.set(x, 0, z, "smooth_sandstone")
        p = pos(x, z)
        col, bay = p % 3, p // 3
        if (x, z) in outer:
            for y in range(1, top + 1):
                tier, row = divmod(y - 1, 4)
                if row == 3:
                    b.set(x, y, z, "cut_sandstone")
                elif tier < 3:
                    if col == 0:
                        b.set(x, y, z, "smooth_sandstone" if row else "chiseled_sandstone")
                    elif row == 2:
                        b.slab(x, y, z, "smooth_sandstone", top=True)
                    else:
                        b.set(x, y, z, AIR)
                else:
                    b.set(x, y, z, AIR if row == 1 and col == 1 and bay % 2 == 0 else "sandstone")
        elif e > 0.84:                       # vaulted corridor on three floors
            for y in range(1, min(top, 13)):
                b.set(x, y, z, "smooth_sandstone" if y in (4, 8, 12) else AIR)
            if p % 9 == 4:
                for y in (3, 7, 11):
                    if y + 1 < top:
                        b.lantern(x, y, z, hanging=True)
        elif (x, z) in inner_wall:
            for y in range(1, min(12, top) + 1):
                door = col in (1, 2) and y in (1, 2) and bay % 4 == 0
                b.set(x, y, z, AIR if door else "cut_sandstone" if y in (4, 8, 12) else "sandstone")
        elif e < 0.64:                       # podium around the arena
            b.fill(x, 1, z, x, 2, z, "smooth_sandstone")
            if p % 12 == 0:
                b.lantern(x, 3, z)
        else:                                # cavea: stepped seats
            h = 1 + int((e - 0.6) / 0.24 * 10.99)
            if top < 16:
                h = min(h, max(1, top - 2))
            for y in range(1, h):
                b.set(x, y, z, "sandstone")
            b.slab(x, h, z, "smooth_sandstone")
    # four entrances on the axes
    for x0, z0, x1, z1 in ((cx - 1, 0, cx + 1, L - 1), (0, cz - 1, W - 1, cz + 1)):
        for x in range(x0, x1 + 1):
            for z in range(z0, z1 + 1):
                if (x, z) in inside and e_of(x, z) > 0.58:
                    b.set(x, 0, z, "smooth_sandstone")
                    b.clear(x, 1, z, x, 3, z)
                    if b.get(x, 4, z) not in (None, AIR) and (x + z) % 3 == 0:
                        b.lantern(x, 3, z, hanging=True)
    for x, z in ((cx, cz), (cx - 7, cz), (cx + 7, cz), (cx, cz - 5), (cx, cz + 5)):
        b.lantern(x, 1, z)
    return b


@template("igloo", "Igloo", "Minecraft Classic",
          "Igloo a cupola liscia con tunnel arrotondato, finestre di vetro azzurro, pavimento in legno, letto, "
          "fornace, banco da lavoro, cassa, tappeti, lanterne e abeti innevati.")
def igloo():
    b = Builder(13, 7, 17, seed=6)
    cx, cz = 6, 6
    b.ellipsoid(cx, 0, cz, 5.4, 5.3, 5.4, "snow_block", hollow=True, thickness=1.15)
    b.disk(cx, cz, 0, 3.8, "spruce_planks")
    b.disk(cx, cz, 1, 2.3, "white_carpet")
    b.set(cx, 1, cz, "light_blue_carpet")
    for ang in (0, 45, 135, 180, 225, 315):
        x = cx + int(round(4.9 * math.cos(math.radians(ang))))
        z = cz + int(round(4.9 * math.sin(math.radians(ang))))
        if b.get(x, 2, z) == "minecraft:snow_block":
            b.set(x, 2, z, "light_blue_stained_glass")
    # rounded tunnel to the south
    for z in range(10, 15):
        b.fill(5, 0, z, 5, 2, z, "snow_block")
        b.fill(7, 0, z, 7, 2, z, "snow_block")
        b.set(6, 0, z, "snow_block")
        b.set(6, 3, z, "snow_block")
        b.clear(6, 1, z, 6, 2, z)
        for x in (5, 7):
            b.set(x, 3, z, "snow", layers="4")
        b.set(6, 4, z, "snow", layers="2")
    b.clear(6, 1, 9, 6, 2, 11)
    for x in (4, 8):
        b.set(x, 0, 15, "spruce_fence")
        b.lantern(x, 1, 15)
    # furniture
    b.bed(3, 1, 5, "north", color="white")
    b.set(9, 1, 5, "furnace", facing="west", lit="false")
    b.set(9, 1, 6, "crafting_table")
    b.chest(9, 1, 7, "west")
    b.lantern(cx, 4, cz, hanging=True)
    b.lantern(4, 1, 8)
    b.tree(1, 0, 14, "spruce", height=4, radius=1)
    b.tree(11, 0, 15, "spruce", height=3, radius=1)
    return b


@template("ruined_portal", "Ruined Portal", "Minecraft Classic",
          "Grande portale in rovina come quelli del gioco: cornice di ossidiana spezzata con ossidiana piangente, "
          "basamento di mattoni crepati, chiazza di netherrack e magma, frammenti caduti, oro e cassa.")
def ruined_portal():
    W, L = 15, 11
    b = Builder(W, 12, L, seed=17)
    cx, cz = 7, 5
    for x in range(W):
        for z in range(L):
            d = ((x - cx) / 7.3) ** 2 + ((z - cz) / 5.3) ** 2
            if d > 1:
                continue
            r = b.rng.random()
            if r > 1.15 - d * 0.6:
                continue
            blk = "netherrack" if r < 0.55 else "magma_block" if r < 0.63 else "blackstone" if r < 0.72 else "netherrack"
            if d > 0.7 and b.rng.random() < 0.4:
                blk = b.rng.choice(["stone_bricks", "cracked_stone_bricks", "mossy_stone_bricks"])
            b.set(x, 0, z, blk)
    b.fill_random(3, 1, 4, 11, 1, 6, [("stone_bricks", 4), ("cracked_stone_bricks", 3), ("mossy_stone_bricks", 2)])
    for x in range(3, 12):
        b.stair(x, 1, 3, "stone_brick", "south")
        b.stair(x, 1, 7, "stone_brick", "north")
    for z in (4, 5, 6):
        b.stair(2, 1, z, "stone_brick", "east")
        b.stair(12, 1, z, "stone_brick", "west")
    missing = {(9, 9), (8, 9), (9, 8), (4, 6), (7, 2)}
    for x in range(4, 10):
        for y in range(2, 10):
            if (x in (4, 9) or y in (2, 9)) and (x, y) not in missing:
                b.set(x, y, 5, "crying_obsidian" if b.rng.random() < 0.22 else "obsidian")
    b.set(4, 7, 5, "gold_block")
    for x, y, z, blk in ((10, 2, 4, "obsidian"), (11, 1, 8, "crying_obsidian"), (12, 1, 7, "obsidian"),
                         (8, 1, 9, "obsidian"), (2, 1, 8, "gold_block")):
        b.set(x, y - 1, z, "netherrack") if y == 1 else None
        b.set(x, y, z, blk)
    b.chest(6, 2, 6, "south")
    b.lantern(3, 2, 4)
    b.lantern(11, 2, 6)
    return b


@template("ancient_city_portal", "Ancient City Portal", "Minecraft Classic",
          "Il grande portale della citta' antica: sagoma a gradoni in ardesia rinforzata spessa tre blocchi, "
          "basamento con scalini, sculk, ali laterali, lanterne dell'anima, candele e casse.")
def ancient_city_portal():
    W, L = 27, 13
    b = Builder(W, 21, L, seed=8)
    c = 13
    b.fill_random(0, 0, 0, W - 1, 0, L - 1, [("deepslate_tiles", 5), ("deepslate_bricks", 3), ("sculk", 2),
                                              ("cracked_deepslate_tiles", 1)])
    b.fill(3, 1, 3, 23, 1, 9, "polished_deepslate")
    for x in range(3, 24):
        b.stair(x, 1, 2, "polished_deepslate", "south")
        b.stair(x, 1, 10, "polished_deepslate", "north")
    for z in range(3, 10):
        b.stair(2, 1, z, "polished_deepslate", "east")
        b.stair(24, 1, z, "polished_deepslate", "west")

    def outer_top(dx):
        return 18 if dx <= 5 else {6: 17, 7: 16, 8: 15, 9: 13}.get(dx, -1)

    def inner_top(dx):
        return 13 if dx <= 3 else {4: 12, 5: 11}.get(dx, 0)

    frame = set()
    for x in range(c - 9, c + 10):
        dx = abs(x - c)
        for y in range(2, outer_top(dx) + 1):
            if not (dx <= 5 and y <= inner_top(dx)):
                frame.add((x, y))
    for (x, y) in frame:
        edge = any((x + ex, y + ey) not in frame and y + ey >= 2 for ex, ey in ((1, 0), (-1, 0), (0, 1), (0, -1)))
        for z in (5, 7):
            if edge:
                b.set(x, y, z, "reinforced_deepslate")
            else:
                b.set(x, y, z, "cracked_deepslate_tiles" if b.rng.random() < 0.15 else "deepslate_tiles")
        b.set(x, y, 6, "deepslate_bricks")
    for dx in (-3, 0, 3):
        b.lantern(c + dx, 13, 6, hanging=True, soul=True)
    for x in (1, W - 2):
        b.fill(x, 1, 4, x, 3, 8, "deepslate_bricks")
        b.fill(x, 4, 4, x, 4, 8, "polished_deepslate_wall")
        for z in (4, 8):
            b.lantern(x, 5, z, soul=True)
    for x in range(5, 22, 4):
        for z in (3, 9):
            b.set(x, 2, z, "sculk")
    b.set(c - 6, 2, 3, "sculk_catalyst")
    b.set(5, 2, 3, "gray_candle", candles="3", lit="true", waterlogged="false")
    b.set(21, 2, 9, "gray_candle", candles="2", lit="true", waterlogged="false")
    b.chest(4, 2, 8, "south")
    b.chest(22, 2, 4, "north")
    for x in (c - 7, c + 7):
        b.lantern(x, 2, 9, soul=True)
    return b


@template("viking_longhouse", "Viking Longhouse", "Medieval",
          "Casa lunga vichinga a forma di scafo: zoccolo di pietra, pareti di tronchi, tetto spiovente con colmo "
          "e corna di drago, timpani a travi, lungo focolare, panche, letti e catasta di legna.")
def viking_longhouse():
    W, L = 15, 27
    b = Builder(W, 13, L, seed=3)
    c = 7
    half_of = {}
    for z in range(1, L - 1):
        t = (z - 1) / (L - 3)
        half_of[z] = 4 + int(round(1.5 * math.sin(math.pi * t)))
    for z in range(L):
        half = half_of.get(z, 4)
        x1, x2 = c - half, c + half
        if 1 <= z <= L - 2:
            b.fill(x1, 0, z, x2, 0, z, "spruce_planks")
            b.set(x1, 0, z, "cobblestone")
            b.set(x2, 0, z, "cobblestone")
            post = z % 4 == 1 or z in (1, L - 2)
            for y in range(1, 4):
                for x in (x1, x2):
                    if post:
                        b.set(x, y, z, "spruce_log", axis="y")
                    elif y == 2 and z % 4 == 3 and 3 < z < L - 4:
                        b.set(x, y, z, "spruce_fence")
                    else:
                        b.set(x, y, z, "stripped_spruce_log", axis="z")
            b.clear(x1 + 1, 1, z, x2 - 1, 3, z)
        for k in range(half + 2):
            y = 4 + k
            xl, xr = x1 - 1 + k, x2 + 1 - k
            if xl >= xr:
                b.set(c, y, z, "stripped_dark_oak_log", axis="z")
                b.slab(c, y + 1, z, "dark_oak")
                break
            b.stair(xl, y, z, "spruce", "east")
            b.stair(xr, y, z, "spruce", "west")
            if 1 <= z <= L - 2:
                for x in range(xl + 1, xr):
                    if z in (1, L - 2):
                        b.set(x, y, z, "spruce_log" if y == 4 else "dark_oak_planks", **({"axis": "x"} if y == 4 else {}))
                    else:
                        b.set_if_empty(x, y, z, AIR)
    for z in (1, L - 2):
        b.fill(c, 5, z, c, 4 + half_of[z], z, "stripped_dark_oak_log", axis="y")
    for z in (0, L - 1):
        b.set(c, 10, z, "dark_oak_fence")
        for dx, y in ((1, 11), (2, 12)):
            b.set(c - dx, y, z, "dark_oak_fence")
            b.set(c + dx, y, z, "dark_oak_fence")
    b.entrance(c, 1, L - 2, "north", wood="spruce", step="cobblestone")
    b.entrance(c, 1, 1, "south", wood="spruce", step="cobblestone")
    # long hearth
    m = L // 2
    b.fill(c - 1, 0, m - 2, c + 1, 0, m + 2, "cobblestone")
    for z in (m - 1, m + 1):
        b.set(c, 1, z, "campfire", lit="true", signal_fire="false", facing="north", waterlogged="false")
    for z in range(4, L - 4):
        if abs(z - m) > 3 and z % 4 != 1:
            half = half_of[z]
            b.stair(c - half + 1, 1, z, "spruce", "west")
            b.stair(c + half - 1, 1, z, "spruce", "east")
    for z in range(5, L - 5, 4):
        if abs(z - m) > 3:
            for x in (c - 2, c + 2):
                b.fill(x, 1, z, x, half_of[z] + 2, z, "spruce_log", axis="y")
    b.bed(c - 3, 1, 3, "north", color="brown")
    b.bed(c + 3, 1, 3, "north", color="brown")
    b.chest(c - 3, 1, L - 4, "east")
    b.set(c + 3, 1, L - 4, "barrel", facing="up", open="false")
    b.set(c + 3, 1, L - 5, "crafting_table")
    for z in (5, 9, 17, 21):
        b.lantern(c, 4 + half_of[z], z, hanging=True)
    b.lantern(c - 2, 1, 2)
    b.lantern(c + 2, 1, L - 3)
    for z in (2, 3):
        b.set(1, 0, z, "spruce_log", axis="z")
    b.set(1, 1, 2, "spruce_log", axis="z")
    b.set(13, 0, 3, "hay_block", axis="y")
    return b


@template("desert_temple", "Desert Temple", "Minecraft Classic",
          "Tempio del deserto: torri angolari a fasce di terracotta con il volto decorato, facciata a colonne, "
          "lesene, piramide a gradoni sul tetto, sala a mosaico con colonne e quattro casse del tesoro.")
def desert_temple():
    S = 21
    b = Builder(S, 18, S, seed=2)
    c = S // 2
    SS, CUT, CH, SM = "sandstone", "cut_sandstone", "chiseled_sandstone", "smooth_sandstone"
    b.room(0, 0, 2, S - 1, 9, S - 1, SS, floor=SS, ceiling=CUT)
    # pilasters and bands on the outer walls
    for z in range(4, S - 1, 4):
        for x in (0, S - 1):
            b.fill(x, 1, z, x, 8, z, CUT)
            b.set(x, 8, z, CH)
    for x in range(4, S - 1, 4):
        b.fill(x, 1, S - 1, x, 8, S - 1, CUT)
        b.set(x, 8, S - 1, CH)
    for x in range(S):
        for z in range(2, S):
            if (x in (0, S - 1) or z in (2, S - 1)) and b.get(x, 6, z) == "minecraft:" + SS:
                mid = (z % 4 == 2 and x in (0, S - 1)) or (x % 4 == 2 and z == S - 1)
                b.set(x, 6, z, "blue_terracotta" if mid else "orange_terracotta")
    for x in range(S):
        for z in range(2, S):
            if x in (0, S - 1) or z in (2, S - 1):
                b.set(x, 10, z, CUT if (x + z) % 2 == 0 else "sandstone_wall")
    # stepped pyramid on the roof
    for k in range(6):
        a, e, z1, z2 = 5 + k, 15 - k, 7 + k, 17 - k
        if a > e or z1 > z2:
            break
        b.fill(a, 10 + k, z1, e, 10 + k, z2, SS)
        b.walls(a, 10 + k, z1, e, 10 + k, z2, "orange_terracotta" if k == 3 else CUT if k % 2 == 0 else SM)
    b.set(c, 16, 12, CH)
    # corner towers with the decorated face
    for tx in (0, S - 5):
        b.room(tx, 0, 0, tx + 4, 14, 4, SS, floor=SS, ceiling=CUT)
        for y in (4, 8, 12):
            b.walls(tx, y, 0, tx + 4, y, 4, "orange_terracotta")
        b.set(tx + 2, 10, 0, "blue_terracotta")
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            b.set(tx + 2 + dx, 10 + dy, 0, "orange_terracotta")
        b.set(tx + 2, 6, 0, CH)
        ox = tx if tx == 0 else tx + 4
        for y in (6, 7, 10, 11):
            b.set(ox, y, 2, AIR)
        b.walls(tx, 15, 0, tx + 4, 15, 4, "sandstone_wall")
        for x, z in ((tx, 0), (tx + 4, 0), (tx, 4), (tx + 4, 4)):
            b.set(x, 15, z, CH)
            b.slab(x, 16, z, SS)
        b.fill(tx + 1, 9, 1, tx + 3, 9, 3, SS)
        b.ladder(tx + 2, 1, 14, 1, "south")
        b.clear(tx + 2, 1, 4, tx + 2, 2, 4)
        b.lantern(tx + 1, 1, 3)
        b.lantern(tx + 3, 10, 3)
    # facade and entrance between the towers
    b.carve_arch("x", c - 1, c + 1, 2, 2, 1, 4)
    for x in (c - 2, c + 2):
        b.fill(x, 1, 2, x, 5, 2, CH)
    for x in (6, 14):
        b.fill(x, 1, 2, x, 8, 2, CUT)
    b.fill(5, 0, 1, 15, 0, 1, CUT)
    for x in range(c - 2, c + 3):
        b.stair(x, 0, 0, SS, "south")
    # hall: columns, mosaic floor, treasure
    hz = 11
    for x, z in ((c - 4, hz - 4), (c + 4, hz - 4), (c - 4, hz + 4), (c + 4, hz + 4)):
        b.fill(x, 1, z, x, 8, z, CUT)
        b.set(x, 8, z, CH)
    for x in range(c - 4, c + 5):
        for z in range(hz - 4, hz + 5):
            d = abs(x - c) + abs(z - hz)
            if d <= 4:
                b.set(x, 0, z, "blue_terracotta" if d == 0 else "orange_terracotta" if d % 2 else CUT)
    for x, z, f in ((1, hz, "east"), (S - 2, hz, "west"), (c, S - 2, "north"), (c - 5, S - 2, "north")):
        b.chest(x, 1, z, f)
    for x, z in ((3, 7), (S - 4, 7), (3, S - 4), (S - 4, S - 4), (c, 5)):
        b.lantern(x, 1, z)
    b.lantern(c, 8, hz, hanging=True)
    return b


@template("jungle_temple", "Jungle Temple", "Minecraft Classic",
          "Tempio della giungla a tre gradoni in pietrisco muschioso con cornici, merlature, padiglione sul tetto, "
          "scalinata interna, colonne scolpite, viticci e due casse del tesoro.")
def jungle_temple():
    W, L = 15, 17
    b = Builder(W, 13, L, seed=4)
    mats = [("mossy_cobblestone", 4), ("cobblestone", 3), ("mossy_stone_bricks", 2), ("stone_bricks", 1)]
    b.fill_random(1, 0, 1, 13, 4, 15, mats)
    b.clear(2, 1, 2, 12, 3, 14)
    b.fill_random(3, 5, 3, 11, 8, 13, mats)
    b.clear(4, 5, 4, 10, 7, 12)
    # cornices
    for y, (x1, z1, x2, z2) in ((4, (0, 0, 14, 16)), (8, (2, 2, 12, 14))):
        for x in range(x1 + 1, x2):
            b.stair(x, y, z1, "mossy_cobblestone", "south", top=True)
            b.stair(x, y, z2, "mossy_cobblestone", "north", top=True)
        for z in range(z1 + 1, z2):
            b.stair(x1, y, z, "mossy_cobblestone", "east", top=True)
            b.stair(x2, y, z, "mossy_cobblestone", "west", top=True)
    for x in range(1, 14, 2):
        b.set(x, 5, 1, "mossy_cobblestone_wall")
        b.set(x, 5, 15, "mossy_cobblestone_wall")
    for z in range(3, 14, 2):
        b.set(1, 5, z, "mossy_cobblestone_wall")
        b.set(13, 5, z, "mossy_cobblestone_wall")
    # roof pavilion
    for x, z in ((5, 5), (9, 5), (5, 11), (9, 11)):
        b.fill(x, 9, z, x, 10, z, "chiseled_stone_bricks")
    b.fill_random(4, 11, 4, 10, 11, 12, mats)
    for x in range(4, 11):
        b.stair(x, 11, 3, "mossy_cobblestone", "south")
        b.stair(x, 11, 13, "mossy_cobblestone", "north")
    for z in range(4, 13):
        b.stair(3, 11, z, "mossy_cobblestone", "east")
        b.stair(11, 11, z, "mossy_cobblestone", "west")
    b.set(7, 12, 8, "chiseled_stone_bricks")
    b.lantern(7, 9, 8)
    # entrance and outer steps
    b.clear(6, 1, 15, 8, 3, 15)
    for y in range(1, 5):
        b.set(5, y, 15, "chiseled_stone_bricks")
        b.set(9, y, 15, "chiseled_stone_bricks")
    for x in range(6, 9):
        b.stair(x, 0, 16, "cobblestone", "north")
    # hall columns and staircase to the upper floor
    for x, z in ((4, 6), (10, 6), (4, 10), (10, 10)):
        b.fill(x, 1, z, x, 3, z, "chiseled_stone_bricks")
    for x in (6, 7):
        for i, (y, z) in enumerate(((1, 12), (2, 11), (3, 10), (4, 9))):
            b.stair(x, y, z, "cobblestone", "north")
            if y > 1:
                b.fill(x, 1, z, x, y - 1, z, "cobblestone")
        for z in (10, 11, 12):
            b.set(x, 4, z, AIR)
    b.set(7, 5, 13, AIR)
    b.set(7, 6, 13, AIR)
    b.ladder(8, 5, 8, 4, "south")
    b.chest(2, 1, 8, "east")
    b.chest(5, 5, 5, "south")
    b.set(9, 5, 4, "chiseled_stone_bricks")
    for x, z in ((3, 3), (11, 3), (3, 13), (11, 13)):
        b.lantern(x, 1, z)
    b.lantern(9, 5, 11)
    b.lantern(5, 5, 11)
    # vines
    for x in range(1, 14):
        for y in range(1, 4):
            if b.rng.random() < 0.45:
                b.set(x, y, 0, "vine", south="true", north="false", east="false", west="false", up="false")
            if not 5 <= x <= 9 and b.rng.random() < 0.45:
                b.set(x, y, 16, "vine", north="true", south="false", east="false", west="false", up="false")
    for z in range(1, 16):
        for y in range(1, 4):
            if b.rng.random() < 0.45:
                b.set(0, y, z, "vine", east="true", north="false", south="false", west="false", up="false")
            if b.rng.random() < 0.45:
                b.set(14, y, z, "vine", west="true", north="false", south="false", east="false", up="false")
    return b


@template("leaning_tower_pisa", "Leaning Tower of Pisa", "Landmark",
          "Torre di Pisa pendente: basamento ad arcate cieche, sei logge a colonne regolari attorno al nucleo a "
          "fasce, cornici aggettanti, cella campanaria e scala interna fino in cima.")
def leaning_tower_pisa():
    W, L, H = 17, 15, 40
    b = Builder(W, H, L, seed=1)
    c0, cz = 6, 7

    def cx(y):
        return c0 + int(y * 0.1)

    def ring_cells(x0, r, th=1.0):
        out = []
        ri = int(math.ceil(r)) + 1
        for x in range(x0 - ri, x0 + ri + 1):
            for z in range(cz - ri, cz + ri + 1):
                d2 = (x - x0) ** 2 + (z - cz) ** 2
                if (r - th + 0.35) ** 2 < d2 <= (r + 0.35) ** 2:
                    out.append((x, z))
        out.sort(key=lambda p: math.atan2(p[1] - cz, p[0] - x0))
        return out

    WHITE, BAND = "smooth_quartz", "polished_diorite"
    b.disk(cx(0), cz, 0, 5.5, WHITE)
    for y in range(1, 8):
        x0 = cx(y)
        for i, (x, z) in enumerate(ring_cells(x0, 4.5)):
            if i % 2 == 0:
                b.set(x, y, z, "quartz_pillar", axis="y")
            else:
                b.set(x, y, z, "chiseled_quartz_block" if y == 6 else WHITE if y % 2 else BAND)
        b.disk(x0, cz, y, 3.4, AIR)
    for s in range(6):
        y0 = 8 + 4 * s
        x0 = cx(y0)
        b.disk(x0, cz, y0, 5.0, WHITE)
        for (x, z) in ring_cells(x0, 6.0, 0.65):
            b.slab(x, y0, z, "smooth_quartz")
        for y in range(y0 + 1, y0 + 4):
            xc = cx(y)
            for (x, z) in ring_cells(xc, 3.0):
                b.set(x, y, z, WHITE if (y - y0) % 2 else BAND)
            b.disk(xc, cz, y, 2.0, AIR)
            for (x, z) in ring_cells(xc, 4.0):
                b.set(x, y, z, AIR)
            for i, (x, z) in enumerate(ring_cells(xc, 5.0)):
                if y == y0 + 3:
                    b.slab(x, y, z, "smooth_quartz", top=True)
                elif i % 2 == 0:
                    b.set(x, y, z, "quartz_pillar", axis="y")
                else:
                    b.set(x, y, z, AIR)
        xc = cx(y0 + 1)
        b.set(xc, y0 + 1, cz + 3, AIR)
        b.set(xc, y0 + 2, cz + 3, AIR)
        b.lantern(xc - 1, y0 + 1, cz + 1)
        if s < 5:
            b.lantern(xc, y0 + 3, cz - 4, hanging=True)
        else:
            b.lantern(xc, y0 + 1, cz - 4)
    # belfry
    yb = 32
    xb = cx(yb)
    b.disk(xb, cz, yb, 3.6, WHITE)
    for i, (x, z) in enumerate(ring_cells(xb, 3.2)):
        for y in range(yb + 1, yb + 4):
            open_arch = i % 2 == 1 and y < yb + 3
            b.set(x, y, z, AIR if open_arch else "quartz_pillar", **({} if open_arch else {"axis": "y"}))
    b.disk(xb, cz, yb + 4, 3.6, "smooth_quartz_slab", type="bottom", waterlogged="false")
    b.set(xb, yb + 1, cz + 1, "bell", attachment="floor", facing="north", powered="false")
    b.lantern(xb + 1, yb + 1, cz - 1)
    # ladder on a central column up to the belfry
    col = c0 + 2
    b.fill(col, 1, cz - 1, col, yb, cz - 1, WHITE)
    b.ladder(col, 1, yb, cz, "south")
    b.entrance(cx(1), 1, cz + 4, "north", wood="dark_oak", step=None)
    b.lantern(c0 - 1, 1, cz - 1)
    return b
