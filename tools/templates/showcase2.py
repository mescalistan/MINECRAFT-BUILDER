"""New showcase builds inspired by the most popular Minecraft builds (Japanese temples, fairytale castles)."""
import math

from template_builder import Builder, AIR, template

STONE_MIX = [("stone_bricks", 6), ("mossy_stone_bricks", 1), ("cracked_stone_bricks", 1), ("andesite", 1)]
ROCK_MIX = [("stone", 6), ("andesite", 3), ("cobblestone", 2), ("tuff", 1), ("mossy_cobblestone", 1)]


def _posts(b, x1, x2, z1, z2, y1, y2, log, step=3):
    """Vertical log posts at the corners and every 'step' blocks along the walls of a room."""
    for x in range(x1, x2 + 1):
        for z in (z1, z2):
            if (x - x1) % step == 0 or x == x2:
                b.fill(x, y1, z, x, y2, z, log, axis="y")
    for z in range(z1, z2 + 1):
        for x in (x1, x2):
            if (z - z1) % step == 0 or z == z2:
                b.fill(x, y1, z, x, y2, z, log, axis="y")


def _windows(b, x1, x2, z1, z2, ys, pane, step=3, offset=1):
    for y in ys:
        for x in range(x1 + offset + 1, x2, step):
            for z in (z1, z2):
                if b.get(x, y, z) not in (None, AIR) and not b.get(x, y, z).endswith("_log"):
                    b.set(x, y, z, pane)
        for z in range(z1 + offset + 1, z2, step):
            for x in (x1, x2):
                if b.get(x, y, z) not in (None, AIR) and not b.get(x, y, z).endswith("_log"):
                    b.set(x, y, z, pane)


def _stone_lantern(b, x, y, z):
    b.set(x, y, z, "stone_brick_wall")
    b.lantern(x, y + 1, z)


@template("cherry_temple", "Japanese Cherry Temple", "Templi e luoghi sacri",
          "Tempio-castello giapponese a tre piani: pareti bianche con pilastri di ciliegio, tetti a gronda in "
          "mattoni del Nether, pavimenti in mangrovia, basamento di pietra, ciliegi in fiore e lanterne di pietra.")
def cherry_temple():
    W = L = 23
    b = Builder(W, 27, L, seed=33)
    c = 11
    b.fill_random(1, 0, 1, W - 2, 1, L - 2, STONE_MIX)
    for i in range(W):
        b.stair(i, 0, 0, "stone_brick", "south")
        b.stair(i, 0, L - 1, "stone_brick", "north")
        b.stair(0, 0, i, "stone_brick", "east")
        b.stair(W - 1, 0, i, "stone_brick", "west")
    for x in range(c - 1, c + 2):
        b.stair(x, 1, L - 2, "stone_brick", "north")
    floors = [(4, 18, 1, 7), (6, 16, 7, 12), (8, 14, 12, 17)]
    for i, (a, e, yb, yt) in enumerate(floors):
        b.room(a, yb, a, e, yt, e, "white_wool", floor="mangrove_planks", ceiling="cherry_planks")
        _posts(b, a, e, a, e, yb + 1, yt - 1, "cherry_log", step=3)
        b.walls(a, yb + 1, a, e, yb + 1, e, "cherry_planks")
        _windows(b, a, e, a, e, (yb + 3,), "pink_stained_glass_pane", step=3)
        if i < 2:
            b.eave(a, e, a, e, yt, "nether_brick", overhang=2)
    top = b.hip_roof(8, 14, 8, 14, 17, "nether_brick", "nether_bricks", overhang=2)
    b.set(c, top + 1, c, "gold_block")
    b.set(c, top + 2, c, "lightning_rod", facing="up", powered="false", waterlogged="false")
    # ladder on a central column
    b.fill(c, 2, c - 1, c, 12, c - 1, "stripped_cherry_log", axis="y")
    b.ladder(c, 2, 12, c, "south")
    b.entrance(c, 2, 18, "north", wood="cherry", step=None)
    # furniture and lights
    for x, z in ((6, 6), (16, 6), (6, 16), (16, 16), (c + 3, c + 4)):
        b.lantern(x, 2, z)
    b.table(8, 2, 8, "cherry")
    b.table(14, 2, 8, "cherry")
    b.bed(8, 8, 9, "north", color="pink")
    for x, z in ((14, 14), (8, 14), (14, 8)):
        b.lantern(x, 8, z)
    b.chest(9, 13, 9, "south")
    b.set(13, 13, 13, "bell", attachment="floor", facing="north", powered="false")
    b.lantern(9, 13, 13)
    b.lantern(13, 13, 9)
    for x, z in ((2, 2), (20, 2), (2, 20), (20, 20)):
        b.tree(x, 2, z, "cherry", height=4, radius=2)
    for x in (7, 15):
        _stone_lantern(b, x, 2, 20)
    return b


@template("kinkaku_ji", "Golden Pavilion (Kinkaku-ji)", "Templi e luoghi sacri",
          "Padiglione d'Oro di Kyoto affacciato sullo stagno: primo piano in legno e intonaco, due piani dorati "
          "con balconata, tetti scuri a gronda, fenice d'oro, isola con pino, sentiero e lanterne di pietra.")
def kinkaku_ji():
    W, L = 29, 28
    b = Builder(W, 24, L, seed=44)
    b.fill(0, 0, 0, W - 1, 0, L - 1, "dirt")
    b.fill(0, 1, 0, W - 1, 1, L - 1, "grass_block")
    pcx, pcz = 14, 8
    for x in range(W):
        for z in range(L):
            if ((x - pcx) / 12.5) ** 2 + ((z - pcz) / 6.8) ** 2 <= 1:
                b.set(x, 1, z, "water", level="0")
                b.set(x, 0, z, "clay" if b.rng.random() < 0.3 else "dirt")
    # island with a pine and rocks along the shore
    for x in range(4, 11):
        for z in range(4, 10):
            if (x - 7) ** 2 + (z - 7) ** 2 <= 4:
                b.set(x, 1, z, "grass_block")
    b.tree(7, 2, 7, "spruce", height=5, radius=2)
    for x, z in ((3, 10), (22, 4), (24, 9), (12, 2), (19, 13)):
        b.set(x, 1, z, "mossy_cobblestone")
        b.set(x, 2, z, "mossy_cobblestone" if (x + z) % 2 else "cobblestone")
    # first floor: wood and plaster
    b.room(9, 1, 13, 19, 6, 21, "mushroom_stem", floor="spruce_planks", ceiling="dark_oak_planks")
    _posts(b, 9, 19, 13, 21, 2, 5, "dark_oak_log", step=2)
    _windows(b, 9, 19, 13, 21, (3, 4), "white_stained_glass_pane", step=2, offset=0)
    for x in range(8, 21):
        for z in (12, 22):
            b.slab(x, 6, z, "dark_oak")
    for z in range(12, 23):
        for x in (8, 20):
            b.slab(x, 6, z, "dark_oak")
    for x, z in ((8, 12), (20, 12), (8, 22), (20, 22)):
        b.slab(x, 7, z, "dark_oak")
    for x in range(9, 20):
        for z in (13, 21):
            b.set(x, 7, z, "dark_oak_fence")
    for z in range(13, 22):
        for x in (9, 19):
            b.set(x, 7, z, "dark_oak_fence")
    # second and third floors: gold
    b.room(10, 6, 14, 18, 11, 20, "gold_block", floor="dark_oak_planks", ceiling="dark_oak_planks")
    _windows(b, 10, 18, 14, 20, (8, 9), "yellow_stained_glass_pane", step=2, offset=0)
    b.eave(10, 18, 14, 20, 11, "dark_oak", overhang=2)
    b.room(11, 11, 15, 17, 15, 19, "gold_block", floor="dark_oak_planks", ceiling="dark_oak_planks")
    _windows(b, 11, 17, 15, 19, (13,), "yellow_stained_glass_pane", step=2, offset=0)
    top = b.hip_roof(11, 17, 15, 19, 15, "dark_oak", "dark_oak_planks", overhang=2)
    b.set(14, top + 1, 17, "gold_block")
    b.set(14, top + 2, 17, "lightning_rod", facing="up", powered="false", waterlogged="false")
    # ladder, door, path
    b.fill(14, 2, 16, 14, 11, 16, "stripped_dark_oak_log", axis="y")
    b.ladder(14, 2, 11, 17, "south")
    b.entrance(14, 2, 21, "north", wood="dark_oak", step=None)
    for z in range(22, L):
        for x in range(13, 16):
            b.set(x, 1, z, "dirt_path" if (x + z) % 3 else "gravel")
    for x in (11, 17):
        _stone_lantern(b, x, 2, 24)
    for x, z in ((10, 14), (18, 14), (10, 20), (18, 20)):
        b.lantern(x, 2, z)
    for x, z in ((11, 15), (17, 19), (11, 19)):
        b.lantern(x, 7, z)
    b.lantern(12, 12, 16)
    b.lantern(16, 12, 18)
    b.chest(16, 12, 16, "west")
    for x, z, kind, h in ((2, 24, "spruce", 5), (26, 24, "spruce", 5), (26, 19, "spruce", 4), (3, 18, "cherry", 4),
                          (24, 16, "cherry", 4)):
        b.tree(x, 2, z, kind, height=h, radius=2)
    # the garden layer goes onto the existing ground (one block lower), so that the garden is level
    # with the land around it and the pond water rests on the terrain
    b.cells = {(x, y - 1, z): v for (x, y, z), v in b.cells.items() if y >= 1}
    return b


@template("neuschwanstein", "Neuschwanstein Castle", "Castelli e fortezze",
          "Castello fiabesco ispirato a Neuschwanstein su uno sperone di roccia: palazzo bianco a tre piani con "
          "tetto d'ardesia, torre altissima con belvedere, torrette a cono, corpo di guardia in mattoni rossi, "
          "cortile e scalinata d'accesso.")
def neuschwanstein():
    W, L = 35, 31
    b = Builder(W, 46, L, seed=55)
    cx, cz = 17, 15
    # rocky crag, five layers, grass on top
    for y in range(5):
        rx, rz = 16 - y * 0.6, 14 - y * 0.6
        for x in range(W):
            for z in range(L):
                if ((x - cx) / rx) ** 2 + ((z - cz) / rz) ** 2 <= 1:
                    if y == 4:
                        b.set(x, y, z, "grass_block")
                    else:
                        blocks = [m[0] for m in ROCK_MIX]
                        b.set(x, y, z, b.rng.choices(blocks, [m[1] for m in ROCK_MIX])[0])
    # stairs up the crag from the south
    for y in range(5):
        z = 29 - y
        for x in range(15, 20):
            b.stair(x, y, z, "stone_brick", "north")
            if y:
                b.fill(x, 0, z, x, y - 1, z, "stone_bricks")
            b.clear(x, y + 1, z, x, y + 3, z)
    # parapet along the edge of the plateau
    plateau = {(x, z) for x in range(W) for z in range(L) if b.get(x, 4, z) == "minecraft:grass_block"}
    for (x, z) in plateau:
        if any((x + dx, z + dz) not in plateau for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1))):
            if not (14 <= x <= 20 and z >= 20):
                b.set(x, 5, z, "stone_brick_wall")
    # courtyard paving
    b.fill(8, 4, 15, 26, 4, 19, "stone_bricks")
    # palace: three floors of white stone, slate roof
    for yb, yt in ((4, 10), (10, 16), (16, 23)):
        b.room(8, yb, 8, 26, yt, 14, "calcite", floor="polished_andesite" if yb == 4 else "spruce_planks",
               ceiling="spruce_planks")
    _windows(b, 8, 26, 8, 14, (6, 7, 12, 13, 18, 19, 20), "glass_pane", step=3, offset=0)
    b.walls(8, 9, 8, 26, 9, 14, "smooth_quartz")
    b.walls(8, 15, 8, 26, 15, 14, "smooth_quartz")
    b.gable_roof(8, 26, 8, 14, 24, "deepslate_tile", "deepslate_tiles", axis="x", overhang=1, gable="calcite")
    b.fill(10, 5, 10, 10, 22, 10, "calcite")
    b.ladder(10, 5, 22, 11, "south")
    b.entrance(17, 5, 14, "north", wood="dark_oak", step=None)
    for yb in (5, 11, 17):
        for x, z in ((12, 9), (24, 9), (24, 13), (14, 13)):
            b.lantern(x, yb, z)
    b.chest(20, 17, 9, "south")
    b.set(16, 11, 9, "red_carpet")
    # tall tower with a lookout, east of the palace
    tx, tz = 28, 11
    b.cylinder(tx, tz, 5, 36, 2.5, "calcite", hollow=True)
    b.disk(tx, tz, 34, 2.2, "spruce_planks")
    b.disk(tx, tz, 4, 2.2, "polished_andesite")
    for y in (35, 36):
        for ang in range(0, 360, 90):
            b.set(tx + int(round(2.5 * math.cos(math.radians(ang)))), y,
                  tz + int(round(2.5 * math.sin(math.radians(ang)))), "glass_pane")
    b.cone(tx, tz, 37, 3.4, "deepslate_tiles", step=0.6)
    b.set(tx, 43, tz, "gold_block")
    b.ladder(tx, 5, 34, tz - 1, "south")
    b.entrance(tx, 5, tz + 2, "north", wood="dark_oak", step=None)
    for y in (5, 20, 35):
        b.lantern(tx + 1, y, tz + 1)
    b.set(tx + 1, 19, tz + 1, "calcite")
    # corner turrets on the west side of the palace
    for x, z in ((8, 8), (8, 14)):
        b.cylinder(x, z, 5, 27, 1.6, "calcite")
        b.cone(x, z, 28, 2.4, "deepslate_tiles", step=0.5)
    # red-brick gatehouse with flanking towers
    b.fill(13, 5, 20, 21, 14, 24, "bricks")
    b.clear(16, 5, 20, 18, 8, 24)
    for z in range(20, 25):
        b.stair(16, 8, z, "brick", "west", top=True)
        b.stair(18, 8, z, "brick", "east", top=True)
    b.fill(16, 4, 20, 18, 4, 24, "stone_bricks")
    for x in range(13, 22):
        for z in (20, 24):
            b.set(x, 15, z, "bricks" if x % 2 else AIR)
    for z in range(21, 24):
        for x in (13, 21):
            b.set(x, 15, z, "bricks" if z % 2 else AIR)
    b.lantern(17, 8, 22, hanging=True)
    for x in (12, 22):
        b.cylinder(x, 22, 5, 17, 1.6, "bricks")
        b.cone(x, 22, 18, 2.4, "deepslate_tiles", step=0.5)
    for x in (14, 20):
        b.lantern(x, 5, 25)
    for x, z in ((9, 17), (25, 17), (12, 19), (22, 19)):
        b.lantern(x, 5, z)
    return b
