"""Castelli, case medievali e costruzioni fantasy."""
import math

from template_builder import Builder, AIR, template

STONE_MIX = [("stone_bricks", 6), ("mossy_stone_bricks", 1), ("cracked_stone_bricks", 1)]


def _round_tower(b, cx, cz, y1, y2, r, roof="deepslate_tile", wall="stone_bricks", cone_block=None):
    b.cylinder(cx, cz, y1, y2, r, wall, hollow=True)
    for y in range(y1 + 1, y2 + 1):
        b.disk(cx, cz, y, r - 1.2, AIR)
    top = b.cone(cx, cz, y2 + 1, r + 0.8, cone_block or f"{roof}s" if roof.endswith("tile") else roof, step=0.6)
    return top


@template("castle_keep", "Castle Keep", "Medieval",
          "Mastio normanno a quattro piani con torrette angolari, sala del trono, camere, armeria e camminamento.")
def castle_keep():
    S = 23
    b = Builder(S, 33, S, seed=31)
    b.fill(1, 0, 1, S - 2, 0, S - 2, "cobblestone")
    b.fill_random(2, 0, 2, S - 3, 22, S - 3, STONE_MIX)
    b.clear(3, 1, 3, S - 4, 21, S - 4)
    floors = (7, 14, 21)
    for y in floors:
        b.fill(3, y, 3, S - 4, y, S - 4, "spruce_planks" if y < 21 else "stone_bricks")
    # Torrette angolari
    for cx, cz in ((2, 2), (S - 3, 2), (2, S - 3), (S - 3, S - 3)):
        b.cylinder(cx, cz, 0, 25, 2.6, "stone_bricks")
        b.cone(cx, cz, 26, 3.2, "deepslate_tiles", step=0.55)
    # Merli
    for i in range(2, S - 2):
        if i % 2 == 0:
            for x, z in ((i, 2), (i, S - 3), (2, i), (S - 3, i)):
                b.set(x, 23, z, "stone_bricks")
    # Finestre
    for y in (3, 10, 17):
        for i in range(6, S - 6, 4):
            for x, z in ((i, 2), (i, S - 3), (2, i), (S - 3, i)):
                b.set(x, y, z, "glass_pane")
                b.set(x, y + 1, z, "glass_pane")
    # Ingresso
    c = S // 2
    b.carve_arch("x", c - 1, c + 1, S - 3, S - 3, 1, 4)
    b.door(c, 1, S - 3, "north", wood="dark_oak")
    b.door(c - 1, 1, S - 3, "north", wood="dark_oak", hinge="right")
    b.door(c + 1, 1, S - 3, "north", wood="dark_oak")
    for x in (c - 1, c, c + 1):
        b.stair(x, 0, S - 2, "stone_brick", "north")
    b.clear(c - 1, 1, S - 2, c + 1, 2, S - 2)
    # Scala a pioli di servizio
    b.ladder(4, 1, 21, 3, "south")
    b.set(4, 22, 3, AIR)
    # Piano terra: sala del trono
    b.fill(c - 1, 1, 4, c + 1, 1, 6, "red_carpet")
    for z in range(8, S - 4):
        b.set(c, 1, z, "red_carpet")
    b.set(c, 1, 4, "quartz_stairs", facing="north", half="bottom", shape="straight", waterlogged="false")
    b.set(c, 2, 3, "gold_block")
    for z in range(9, S - 6, 3):
        b.table(c - 4, 1, z, "dark_oak")
        b.table(c + 4, 1, z, "dark_oak")
    # Primo piano: armeria e magazzino
    for x in range(5, S - 5, 2):
        b.chest(x, 8, 3, "south")
    b.set(5, 8, S - 4, "anvil", facing="north")
    b.set(7, 8, S - 4, "smithing_table")
    b.set(9, 8, S - 4, "grindstone", face="floor", facing="north")
    # Secondo piano: camere
    for i, x in enumerate(range(6, S - 5, 4)):
        b.bed(x, 15, S - 5, "north", color=("red", "blue", "green", "yellow")[i % 4])
    b.set(S - 5, 15, 4, "bookshelf")
    b.set(S - 6, 15, 4, "lectern", facing="south", has_book="false", powered="false")
    # Luci
    for y in (1, 8, 15):
        for x in range(5, S - 4, 4):
            for z in range(5, S - 4, 5):
                if b.get(x, y, z) in (None, AIR):
                    b.lantern(x, y, z)
    for x in range(5, S - 4, 5):
        b.lantern(x, 22, 5)
    return b


@template("castle_gatehouse", "Castle Gatehouse", "Medieval",
          "Corpo di guardia con saracinesca, due torri cilindriche, ponte levatoio e camminamento merlato.")
def castle_gatehouse():
    W, L = 21, 15
    b = Builder(W, 22, L, seed=32)
    c = W // 2
    b.fill_random(4, 0, 3, W - 5, 13, 10, STONE_MIX)
    b.carve_arch("x", c - 2, c + 2, 3, 10, 0, 7)
    b.fill(c - 2, 0, 3, c + 2, 0, 10, "cobblestone")
    for x in range(c - 2, c + 3):
        b.fill(x, 5, 3, x, 6, 3, "iron_bars")
    for cx in (3, W - 4):
        b.cylinder(cx, 6, 0, 16, 3.4, "stone_bricks")
        b.cylinder(cx, 6, 1, 16, 2.3, AIR)
        b.disk(cx, 6, 8, 2.3, "spruce_planks")
        b.disk(cx, 6, 14, 2.3, "spruce_planks")
        b.ring(cx, 6, 17, 3.4, "stone_bricks")
        for a in range(0, 360, 45):
            x = cx + int(round(3.4 * math.cos(math.radians(a))))
            z = 6 + int(round(3.4 * math.sin(math.radians(a))))
            b.set(x, 18, z, "stone_bricks")
        b.fill(cx, 1, 6 + 1, cx, 14, 6 + 1, "stone_bricks")
        b.ladder(cx, 1, 14, 6, "north")
        b.lantern(cx + 1, 1, 5)
        b.lantern(cx + 1, 9, 5)
        b.lantern(cx - 1, 15, 5)
        for y in (4, 11):
            b.set(cx, y, 6 - 3, AIR)
            b.set(cx + (3 if cx < c else -3), y, 6, AIR)
    # Porte delle torri dal passaggio della porta
    b.clear(6, 1, 6, c - 3, 2, 6)
    b.clear(c + 3, 1, 6, W - 7, 2, 6)
    b.entrance(5, 1, 6, "west", wood="spruce", step=None)
    b.entrance(W - 6, 1, 6, "east", wood="spruce", step=None)
    # Camminamento
    b.fill(4, 14, 3, W - 5, 14, 10, "stone_bricks")
    for i in range(4, W - 4, 2):
        b.set(i, 15, 3, "stone_bricks")
        b.set(i, 15, 10, "stone_bricks")
    b.clear(6, 15, 4, W - 7, 16, 9)
    for x, z in ((6, 4), (W - 7, 9)):
        b.lantern(x, 15, z)
    for x in (3, W - 4):
        b.clear(x + (2 if x < c else -2), 15, 6, x + (2 if x < c else -2), 16, 6)
    # Ponte levatoio
    b.fill(c - 2, 0, 11, c + 2, 0, L - 1, "spruce_planks")
    for z in (11, L - 1):
        b.set(c - 2, 1, z, "spruce_fence")
        b.set(c + 2, 1, z, "spruce_fence")
        b.lantern(c - 2, 2, z)
        b.lantern(c + 2, 2, z)
    b.lantern(c, 6, 6, hanging=True)
    return b


@template("fairytale_castle", "Fairytale Castle", "Fantasy",
          "Castello da fiaba ispirato a Neuschwanstein: mura bianche, torri con tetti conici blu, cortile e sale illuminate.")
def fairytale_castle():
    W, L = 35, 29
    b = Builder(W, 44, L, seed=33)
    WHITE = "smooth_quartz"
    ROOF = "blue_concrete"
    # Mura del cortile
    b.fill(1, 0, 1, W - 2, 0, L - 2, "stone_bricks")
    b.walls(1, 1, 1, W - 2, 7, L - 2, WHITE)
    for i in range(1, W - 1, 2):
        b.set(i, 8, 1, WHITE)
        b.set(i, 8, L - 2, WHITE)
    for i in range(1, L - 1, 2):
        b.set(1, 8, i, WHITE)
        b.set(W - 2, 8, i, WHITE)
    c = W // 2
    b.carve_arch("x", c - 1, c + 1, L - 2, L - 2, 1, 4)
    # Palazzo principale
    b.room(5, 0, 3, W - 6, 18, 12, WHITE, floor="polished_andesite", ceiling=WHITE)
    b.fill(6, 9, 4, W - 7, 9, 11, "spruce_planks")
    b.gable_roof(5, W - 6, 3, 12, 18, "deepslate_tile", "deepslate_tiles", axis="x", overhang=1)
    for y in (3, 4, 12, 13):
        for x in range(8, W - 7, 3):
            b.set(x, y, 12, "light_blue_stained_glass_pane")
            b.set(x, y, 3, "light_blue_stained_glass_pane")
    b.entrance(c, 1, 12, "north", wood="dark_oak", step=None)
    b.ladder(6, 1, 9, 4, "south")
    for x in range(8, W - 7, 4):
        b.lantern(x, 1, 6)
        b.lantern(x, 10, 6)
    b.set(c, 10, 5, "red_carpet")
    b.bed(c - 3, 10, 6, "north", color="blue")
    b.set(c + 3, 10, 5, "bookshelf")
    b.chest(c + 4, 10, 5, "south")
    b.set(c, 1, 5, "quartz_stairs", facing="north", half="bottom", shape="straight", waterlogged="false")
    # Grande torre
    tx, tz = W - 9, 8
    b.cylinder(tx, tz, 0, 30, 4, WHITE, hollow=True, thickness=1.2)
    for y in (10, 20):
        b.disk(tx, tz, y, 3, "spruce_planks")
    for y in range(1, 31):
        if y not in (10, 20):
            b.disk(tx, tz, y, 2.6, AIR)
    b.cone(tx, tz, 31, 5, ROOF, step=0.45)
    b.fill(tx, 1, tz - 2, tx, 30, tz - 2, WHITE)
    b.ladder(tx, 1, 30, tz - 1, "south")
    for y in (5, 15, 25):
        b.set(tx + 4, y, tz, "light_blue_stained_glass_pane")
        b.set(tx, y, tz + 4, "light_blue_stained_glass_pane")
        b.lantern(tx + 1, y - 4, tz + 1)
    b.ring(tx, tz, 30, 4.6, "smooth_quartz_slab", thickness=1.2, type="bottom", waterlogged="false")
    for y in (1, 10):
        b.lantern(tx + 1, y, 4)
        b.lantern(tx - 2, y, 4)
        b.lantern(tx, y + 1 if y == 10 else y, 5)
    # Torrette secondarie
    for cx, cz, h in ((2, 2, 14), (W - 3, 2, 14), (2, L - 3, 12), (W - 3, L - 3, 12), (6, 13, 22)):
        b.cylinder(cx, cz, 0, h, 2.2, WHITE)
        b.cone(cx, cz, h + 1, 2.9, ROOF, step=0.4)
        b.set(cx, h + 1 + int(2.9 / 0.4) + 1, cz, "gold_block")
    # Cortile con fontana e alberi
    b.disk(c, 20, 0, 2, "stone_bricks")
    b.set(c, 0, 20, "water", level="0")
    b.ring(c, 20, 1, 2, "stone_brick_wall")
    b.tree(6, 0, 22, "birch", height=4, radius=2)
    b.tree(W - 7, 0, 22, "birch", height=4, radius=2)
    for x, z in ((c - 4, 16), (c + 4, 16), (c - 4, 24), (c + 4, 24)):
        b.lantern(x, 1, z)
    return b


@template("gothic_cathedral", "Gothic Cathedral", "Landmark",
          "Cattedrale gotica ispirata a Notre-Dame: navata alta, archi rampanti, rosone, vetrate colorate e due torri.")
def gothic_cathedral():
    W, L = 23, 47
    b = Builder(W, 42, L, seed=34)
    c = W // 2
    glass = ["red_stained_glass", "blue_stained_glass", "yellow_stained_glass", "purple_stained_glass"]
    # Navata centrale
    b.room(6, 0, 8, W - 7, 18, L - 2, "stone_bricks", floor="polished_andesite", ceiling="stone_bricks")
    b.gable_roof(6, W - 7, 8, L - 2, 19, "deepslate_tile", "deepslate_tiles", axis="z", overhang=1)
    # Navate laterali
    for x1, x2 in ((1, 6), (W - 7, W - 2)):
        b.room(x1, 0, 10, x2, 8, L - 4, "stone_bricks", floor="polished_andesite", ceiling="stone_bricks")
    b.clear(7, 1, 11, W - 8, 7, L - 5)
    b.clear(2, 1, 11, W - 3, 7, L - 5)
    for z in range(11, L - 4, 4):
        for x in (6, W - 7):
            b.fill(x, 1, z, x, 7, z, "stone_bricks")
    # Vetrate colorate (archi a sesto acuto)
    for i, z in enumerate(range(12, L - 4, 4)):
        g = glass[i % len(glass)]
        b.carve_arch("z", z, z + 1, 6, 6, 10, 7, block=g, pointed=True)
        b.carve_arch("z", z, z + 1, W - 7, W - 7, 10, 7, block=g, pointed=True)
        b.carve_arch("z", z, z + 1, 1, 1, 2, 5, block=g, pointed=True)
        b.carve_arch("z", z, z + 1, W - 2, W - 2, 2, 5, block=g, pointed=True)
        # Archi rampanti
        b.line(0, 8, z, 5, 15, z, "stone_bricks")
        b.line(W - 1, 8, z, W - 6, 15, z, "stone_bricks")
        b.fill(0, 0, z, 0, 9, z, "stone_bricks")
        b.fill(W - 1, 0, z, W - 1, 9, z, "stone_bricks")
    # Facciata con due torri
    for x1 in (1, W - 8):
        b.fill_random(x1, 0, 1, x1 + 6, 30, 8, STONE_MIX)
        b.clear(x1 + 1, 1, 2, x1 + 5, 29, 7)
        for y in (10, 20):
            b.fill(x1 + 1, y, 2, x1 + 5, y, 7, "spruce_planks")
        b.fill(x1 + 1, 30, 2, x1 + 5, 30, 7, "stone_bricks")
        for y in range(22, 29):
            b.set(x1 + 3, y, 1, AIR if y < 28 else "stone_bricks")
        b.pyramid(x1, 1, x1 + 6, 8, 31, "deepslate_tiles")
        b.ladder(x1 + 3, 1, 30, 7, "north")
        b.lantern(x1 + 1, 1, 2)
        b.lantern(x1 + 1, 11, 2)
        b.lantern(x1 + 1, 21, 2)
        b.carve_arch("z", 4, 5, x1 + (6 if x1 < c else 0), x1 + (6 if x1 < c else 0), 1, 3)
    b.fill_random(8, 0, 1, W - 9, 24, 8, STONE_MIX)
    b.clear(9, 1, 2, W - 10, 23, 8)
    # Rosone
    for x in range(c - 3, c + 4):
        for y in range(13, 20):
            d = math.hypot(x - c, y - 16)
            if d <= 3.3:
                b.set(x, y, 1, "light_blue_stained_glass" if d < 1 else glass[int(d * 2) % 4])
    # Portale
    b.carve_arch("x", c - 1, c + 1, 1, 1, 1, 6, pointed=True)
    b.door(c - 1, 1, 1, "south", wood="dark_oak", hinge="right")
    b.door(c, 1, 1, "south", wood="dark_oak")
    b.door(c + 1, 1, 1, "south", wood="dark_oak")
    for x in range(c - 1, c + 2):
        b.stair(x, 0, 0, "stone_brick", "south")
    b.clear(c - 1, 1, 8, c + 1, 3, 8)
    # Interno
    for z in range(13, L - 8, 2):
        for x in range(8, c - 1):
            b.stair(x, 1, z, "spruce", "south")
        for x in range(c + 2, W - 8):
            b.stair(x, 1, z, "spruce", "south")
    b.fill(c - 2, 1, L - 6, c + 2, 1, L - 4, "smooth_stone")
    b.set(c, 2, L - 5, "gold_block")
    for x in (c - 2, c + 2):
        b.set(x, 2, L - 5, "white_candle", candles="3", lit="true", waterlogged="false")
    for z in range(10, L - 3, 5):
        b.lantern(c, 1 if z < 13 else 17, z, hanging=z >= 13)
        b.fill(c, 18, z, c, 18, z, "stone_bricks")
        b.lantern(3, 1, z)
        b.lantern(W - 4, 1, z)
    for z in range(12, L - 4, 6):
        b.lantern(c - 3, 1, z)
        b.lantern(c + 3, 1, z)
    for x, z in ((10, 3), (W - 11, 3), (c, 5)):
        b.lantern(x, 1, z)
    return b


@template("tudor_house", "Tudor House", "House",
          "Casa Tudor a graticcio con piano superiore sporgente, tetto ripido, camino e due piani arredati.")
def tudor_house():
    b = Builder(13, 17, 13)
    b.room(2, 0, 2, 10, 5, 10, "cobblestone", floor="stone_bricks", ceiling="dark_oak_planks")
    b.walls(2, 2, 2, 10, 4, 10, "mushroom_stem")
    for x in (2, 5, 7, 10):
        for z in (2, 10):
            b.fill(x, 1, z, x, 4, z, "dark_oak_log", axis="y")
            b.fill(z, 1, x, z, 4, x, "dark_oak_log", axis="y")
    # Piano superiore sporgente
    b.room(1, 5, 1, 11, 10, 11, "mushroom_stem", floor="dark_oak_planks", ceiling="dark_oak_planks")
    for i in range(1, 12, 2):
        for x, z in ((i, 1), (i, 11), (1, i), (11, i)):
            b.fill(x, 6, z, x, 9, z, "dark_oak_log", axis="y")
    for x, z in ((1, 1), (11, 1), (1, 11), (11, 11)):
        b.fill(x, 6, z, x, 9, z, "dark_oak_log", axis="y")
    for i in range(2, 11):
        for x, z in ((i, 1), (i, 11), (1, i), (11, i)):
            if b.get(x, 7, z) == "minecraft:white_terracotta":
                b.line(x, 6, z, x, 6, z, "dark_oak_planks")
    b.gable_roof(1, 11, 1, 11, 10, "dark_oak", "dark_oak_planks", axis="x", overhang=1)
    for x in (4, 8):
        b.set(x, 3, 2, "glass_pane")
        b.set(x, 7, 1, "glass_pane")
        b.set(x, 8, 1, "glass_pane")
        b.set(x, 7, 11, "glass_pane")
        b.set(x, 8, 11, "glass_pane")
    b.set(10, 3, 6, "glass_pane")
    # Camino
    b.fill(2, 1, 6, 2, 15, 6, "bricks")
    b.set(3, 1, 6, "campfire", lit="false", signal_fire="false", facing="east", waterlogged="false")
    b.entrance(6, 1, 10, "north", wood="dark_oak", step="stone_brick")
    # Piano terra: cucina
    b.set(9, 1, 3, "smoker", facing="south", lit="false")
    b.set(8, 1, 3, "crafting_table")
    b.set(7, 1, 3, "barrel", facing="up", open="false")
    b.table(6, 1, 6, "spruce")
    b.stair(5, 1, 6, "spruce", "west")
    b.stair(7, 1, 6, "spruce", "east")
    b.lantern(8, 1, 8)
    b.lantern(4, 1, 4)
    # Scala a pioli e piano superiore
    b.ladder(9, 1, 5, 9, "west")
    b.fill(10, 1, 9, 10, 4, 9, "dark_oak_log", axis="y")
    b.bed(3, 6, 4, "north", color="red")
    b.bed(4, 6, 9, "north", color="green")
    b.chest(10, 6, 3, "west")
    b.set(10, 6, 5, "bookshelf")
    b.lantern(7, 6, 6)
    b.lantern(4, 6, 7)
    return b


@template("medieval_tavern", "Medieval Tavern", "Medieval",
          "Taverna su due piani: bancone, botti, tavoli, focolare con camino e stanze per gli ospiti al piano di sopra.")
def medieval_tavern():
    W, L = 17, 15
    b = Builder(W, 15, L)
    b.room(1, 0, 1, W - 2, 5, L - 2, "spruce_planks", floor="stone_bricks", ceiling="spruce_planks",
           corner="stripped_spruce_log", axis="y")
    b.walls(1, 1, 1, W - 2, 1, L - 2, "cobblestone")
    b.room(1, 5, 1, W - 2, 9, L - 2, "spruce_planks", floor="spruce_planks", ceiling="spruce_planks",
           corner="stripped_spruce_log", axis="y")
    b.gable_roof(1, W - 2, 1, L - 2, 9, "dark_oak", "dark_oak_planks", axis="x", overhang=1)
    for x in range(3, W - 3, 3):
        for y in (2, 3, 7):
            b.set(x, y, 1, "glass_pane")
            b.set(x, y, L - 2, "glass_pane")
    # Bancone e botti
    for x in range(3, 9):
        b.stair(x, 1, 4, "spruce", "south", top=True)
    for x in range(3, 9, 2):
        b.set(x, 1, 2, "barrel", facing="south", open="false")
        b.set(x + 1, 1, 2, "barrel", facing="south", open="false")
    b.set(3, 2, 2, "barrel", facing="up", open="false")
    b.set(9, 1, 2, "smoker", facing="south", lit="false")
    # Tavoli
    for x, z in ((4, 9), (8, 9), (12, 6), (12, 10)):
        b.table(x, 1, z, "spruce")
        b.stair(x - 1, 1, z, "spruce", "west")
        b.stair(x + 1, 1, z, "spruce", "east")
    # Focolare
    b.fill(W - 2, 1, 2, W - 2, 13, 3, "bricks")
    b.set(W - 3, 1, 3, "campfire", lit="true", signal_fire="false", facing="west", waterlogged="false")
    b.fill(W - 3, 0, 2, W - 3, 0, 4, "cobblestone")
    b.entrance(W // 2, 1, L - 2, "north", wood="spruce", step="cobblestone")
    # Scala a pioli e camere
    b.fill(2, 1, L - 3, 2, 4, L - 3, "stripped_spruce_log", axis="y")
    b.ladder(3, 1, 5, L - 3, "east")
    for i, x in enumerate((4, 8, 12)):
        b.bed(x, 6, 3, "north", color=("red", "blue", "lime")[i])
        b.chest(x + 1, 6, 2, "south")
        b.fill(x + 2, 6, 2, x + 2, 8, 5, "spruce_planks")
    for x in (3, 7, 11, 14):
        b.lantern(x, 6, 8)
    for x, z in ((2, 7), (6, 6), (10, 12), (14, 8)):
        b.lantern(x, 1, z)
    b.lantern(W // 2, 4, 7, hanging=True)
    return b


@template("village_chapel", "Village Chapel", "Medieval",
          "Cappella di villaggio con campanile, campana, panche, altare con candele e vetrate.")
def village_chapel():
    W, L = 11, 21
    b = Builder(W, 22, L)
    b.room(1, 0, 6, W - 2, 7, L - 2, "stone_bricks", floor="polished_andesite", ceiling=False)
    b.gable_roof(1, W - 2, 6, L - 2, 7, "deepslate_tile", "deepslate_tiles", axis="z", overhang=1)
    for z in range(9, L - 3, 3):
        b.carve_arch("z", z, z, 1, 1, 2, 4, block="yellow_stained_glass", pointed=True)
        b.carve_arch("z", z, z, W - 2, W - 2, 2, 4, block="yellow_stained_glass", pointed=True)
    # Campanile
    b.room(2, 0, 1, 8, 15, 6, "stone_bricks", floor="polished_andesite", ceiling="stone_bricks")
    b.fill(3, 10, 2, 7, 10, 5, "spruce_planks")
    for y in (11, 12, 13):
        b.set(5, y, 1, AIR)
        b.set(2, y, 3, AIR)
        b.set(8, y, 3, AIR)
    b.set(5, 14, 3, "bell", attachment="ceiling", facing="north", powered="false")
    b.pyramid(2, 1, 8, 6, 16, "deepslate_tiles")
    b.set(5, 19, 3, "gold_block")
    b.ladder(7, 1, 10, 3, "west")
    b.fill(8, 1, 3, 8, 10, 3, "stone_bricks")
    b.entrance(5, 1, 1, "south", wood="dark_oak", step="stone_brick")
    b.clear(4, 1, 6, 6, 4, 6)
    b.carve_arch("x", 4, 6, 6, 6, 1, 4)
    b.lantern(4, 1, 2)
    b.lantern(4, 11, 4)
    # Panche e altare
    for z in range(9, L - 5, 2):
        for x in (2, 3, W - 4, W - 3):
            b.stair(x, 1, z, "spruce", "south")
    b.fill(3, 1, L - 3, W - 4, 1, L - 3, "smooth_stone")
    b.set(5, 2, L - 3, "gold_block")
    b.set(4, 2, L - 3, "white_candle", candles="3", lit="true", waterlogged="false")
    b.set(6, 2, L - 3, "white_candle", candles="3", lit="true", waterlogged="false")
    for z in (8, 13, 17):
        b.lantern(2, 1, z) if z != 8 else b.lantern(W - 3, 1, z)
        b.lantern(W - 3, 1, z)
    b.lantern(5, 1, 11)
    return b


@template("wizard_tower", "Wizard Tower", "Fantasy",
          "Torre del mago in ardesia con tetto conico di ametista, biblioteca con tavolo da incantamento, alchimia e alloggio.")
def wizard_tower():
    W = 15
    b = Builder(W, 38, W)
    c = 7
    b.disk(c, c, 0, 5.5, "polished_deepslate")
    b.cylinder(c, c, 1, 26, 5, "deepslate_bricks", hollow=True, thickness=1.2)
    for y in range(1, 27):
        b.disk(c, c, y, 3.6, AIR)
    for y in (9, 18):
        b.disk(c, c, y, 4, "dark_oak_planks")
    b.ring(c, c, 26, 6, "polished_deepslate_slab", thickness=1.4, type="bottom", waterlogged="false")
    b.disk(c, c, 26, 4.4, "dark_oak_planks")
    top = b.cone(c, c, 27, 5.5, "amethyst_block", step=0.6)
    b.set(c, top + 1, c, "lightning_rod", facing="up", powered="false", waterlogged="false")
    for y in (4, 13, 22):
        for x, z in ((c, c - 5), (c, c + 5), (c - 5, c), (c + 5, c)):
            b.set(x, y, z, "purple_stained_glass")
            b.set(x, y + 1, z, "purple_stained_glass")
    # Piano terra: biblioteca con tavolo da incantamento
    b.set(c, 1, c, "enchanting_table")
    for x in range(c - 2, c + 3):
        for z in range(c - 2, c + 3):
            if max(abs(x - c), abs(z - c)) == 2 and (x, z) not in ((c, c + 2), (c + 2, c + 2)):
                b.set(x, 1, z, "bookshelf")
                b.set(x, 2, z, "bookshelf")
    b.lantern(c - 3, 1, c - 1, soul=False)
    b.lantern(c - 2, 1, c + 3)
    b.set(c - 3, 1, c + 1, "lectern", facing="east", has_book="false", powered="false")
    # Primo piano: alchimia
    b.set(c, 10, c, "brewing_stand")
    b.set(c + 1, 10, c, "cauldron")
    b.chest(c - 2, 10, c, "east")
    b.set(c, 10, c + 2, "purple_carpet")
    b.lantern(c + 2, 10, c - 2)
    b.lantern(c - 2, 10, c + 2)
    # Secondo piano: alloggio
    b.bed(c - 1, 19, c + 1, "north", color="purple")
    b.set(c + 2, 19, c, "bookshelf")
    b.lantern(c + 2, 19, c - 2)
    b.lantern(c + 1, 19, c + 2)
    # Scala a pioli e ingresso
    b.ladder(c + 3, 1, 26, c, "west")
    b.fill(c + 4, 1, c, c + 4, 26, c, "deepslate_bricks")
    b.entrance(c, 1, c + 5, "north", wood="dark_oak", step="polished_deepslate")
    b.clear(c, 1, c + 4, c, 2, c + 4)
    b.lantern(c + 2, 27, c)
    return b


@template("hobbit_hole", "Hobbit Hole", "Fantasy",
          "Casa hobbit scavata in una collina erbosa: porta rotonda, finestre tonde, camere, cucina e giardino fiorito.")
def hobbit_hole():
    W, L = 19, 19
    b = Builder(W, 10, L, seed=35)
    c, cz = 9, 8
    b.ellipsoid(c, 0, cz, 8.5, 8, 7.5, "grass_block")
    b.ellipsoid(c, 0, cz, 7.6, 7.1, 6.6, "dirt")
    for (x, y, z), (n, _) in list(b.cells.items()):
        if n == "minecraft:dirt" and b.get(x, y + 1, z) is None:
            b.set(x, y, z, "grass_block")
    # Stanze interne
    b.room(5, 0, 4, 13, 4, 12, "spruce_planks", floor="spruce_planks", ceiling="spruce_planks")
    b.fill(9, 1, 5, 9, 3, 9, "spruce_planks")
    b.clear(9, 1, 7, 9, 2, 8)
    # Tunnel d'ingresso con porta tonda sulla facciata
    b.fill(c, 0, 13, c, 0, 15, "spruce_planks")
    b.clear(c, 1, 13, c, 2, 15)
    for x in range(c - 2, c + 3):
        for y in range(0, 5):
            d = (x - c) ** 2 + (y - 2) ** 2
            if 2.5 <= d <= 5.3:
                b.set(x, y, 15, "stripped_oak_log", axis="z")
    b.set(c, 3, 15, "stripped_oak_log", axis="z")
    b.entrance(c, 1, 12, "north", wood="oak", step=None)
    for x in (6, 12):
        b.fill(x, 2, 12, x, 2, 15, "glass")
    # Arredi
    b.bed(6, 1, 6, "north", color="green")
    b.chest(6, 1, 8, "east")
    b.set(6, 1, 10, "bookshelf")
    b.set(12, 1, 5, "furnace", facing="south", lit="false")
    b.set(11, 1, 5, "crafting_table")
    b.set(10, 1, 5, "smoker", facing="south", lit="false")
    b.table(11, 1, 9, "oak")
    b.stair(10, 1, 9, "oak", "west")
    b.stair(12, 1, 9, "oak", "east")
    for x, z in ((7, 6), (7, 11), (11, 11), (12, 7)):
        b.lantern(x, 1, z)
    # Camino e giardino
    b.fill(12, 5, 7, 12, 9, 7, "cobblestone")
    b.set(12, 9, 7, "campfire", lit="true", signal_fire="false", facing="north", waterlogged="false")
    b.set(12, 4, 7, "cobblestone")
    flowers = ["poppy", "dandelion", "cornflower", "allium", "oxeye_daisy", "azure_bluet"]
    for x in range(1, W - 1):
        for z in (16, 17):
            if abs(x - c) > 1 and b.get(x, 0, z) is None and b.rng.random() < 0.7:
                b.set(x, 0, z, b.rng.choice(flowers))
    for x in range(0, W):
        b.set(x, 0, 18, "oak_fence")
    b.set(c, 0, 18, "oak_fence_gate", facing="south", in_wall="false", open="false", powered="false")
    b.lantern(c - 2, 1, 18)
    b.lantern(c + 2, 1, 18)
    return b


@template("treehouse", "Treehouse", "Fantasy",
          "Casa sull'albero: grande quercia scura, piattaforma con capanna, ringhiera, scala a pioli e chioma folta.")
def treehouse():
    W = 19
    b = Builder(W, 27, W, seed=36)
    c = 9
    b.fill(c, 0, c, c + 1, 19, c + 1, "dark_oak_log", axis="y")
    for dx, dz in ((-1, 0), (2, 1), (0, -1), (1, 2)):
        b.set(c + dx, 0, c + dz, "dark_oak_log", axis="y")
    for dx, dz, h in ((-4, -3, 16), (5, 4, 17), (4, -4, 18), (-3, 5, 15)):
        b.line(c, h - 3, c, c + dx, h, c + dz, "dark_oak_log", axis="y")
    b.ellipsoid(c, 17, c, 8, 6, 8, "dark_oak_leaves", persistent="true", distance="1", waterlogged="false")
    b.ellipsoid(c, 17, c, 8, 6, 8, "dark_oak_leaves", upper_only=False, persistent="true", distance="1",
                waterlogged="false")
    for y in range(11, 24):
        for x in range(W):
            for z in range(W):
                if b.get(x, y, z) == "minecraft:dark_oak_leaves" and b.rng.random() < 0.12:
                    b.remove(x, y, z)
    # Piattaforma e capanna
    p = 9
    b.fill(c - 5, p, c - 5, c + 6, p, c + 6, "spruce_planks")
    b.walls(c - 5, p + 1, c - 5, c + 6, p + 1, c + 6, "spruce_fence")
    b.room(c - 3, p, c - 3, c + 4, p + 5, c + 4, "spruce_planks", floor="spruce_planks", ceiling="spruce_planks",
           corner="spruce_log", axis="y")
    b.clear(c - 4, p + 1, c - 4, c + 5, p + 6, c - 4)
    b.clear(c - 4, p + 6, c - 4, c + 5, p + 7, c + 5)
    b.clear(c - 2, p + 1, c - 2, c + 3, p + 4, c + 3)
    b.fill(c, p + 1, c, c + 1, p + 4, c + 1, "dark_oak_log", axis="y")
    b.hip_roof(c - 3, c + 4, c - 3, c + 4, p + 5, "spruce", "spruce_planks", overhang=1)
    for x in (c - 1, c + 2):
        b.set(x, p + 2, c - 3, "glass_pane")
        b.set(x, p + 2, c + 4, "glass_pane")
    b.entrance(c + 4, p + 1, c + 1, "west", wood="spruce", step=None)
    b.bed(c - 2, p + 1, c + 3, "north", color="lime")
    b.chest(c + 3, p + 1, c - 2, "south")
    b.set(c - 2, p + 1, c - 2, "crafting_table")
    b.lantern(c + 3, p + 1, c + 3)
    b.lantern(c - 1, p + 1, c - 1)
    for x, z in ((c - 5, c - 5), (c + 6, c - 5), (c - 5, c + 6), (c + 6, c + 6)):
        b.lantern(x, p + 2, z)
    b.lantern(c + 5, p + 1, c + 4)
    # Scala a pioli lungo il tronco
    b.ladder(c + 2, 0, p + 1, c, "east")
    b.set(c + 2, p, c, "ladder", facing="east", waterlogged="false")
    b.clear(c + 2, p + 1, c, c + 2, p + 2, c)
    b.ladder(c + 2, 0, p, c, "east")
    b.lantern(c - 2, 0, c + 3)
    b.lantern(c + 3, 0, c - 2)
    return b


@template("pirate_ship", "Pirate Ship", "Fantasy",
          "Galeone pirata con scafo in quercia scura, due alberi con vele, coffa, cabina del capitano, cannoni e stiva.")
def pirate_ship():
    W, L = 13, 39
    b = Builder(W, 30, L)
    c = W // 2
    deck = 6

    def half_width(z):
        t = z / (L - 1)
        if t < 0.25:
            return 1 + (t / 0.25) * 4
        if t > 0.85:
            return 5 - (t - 0.85) / 0.15 * 1.5
        return 5

    for z in range(2, L - 1):
        hw = half_width(z)
        for y in range(0, deck + 1):
            w = hw * (0.55 + 0.45 * y / deck)
            r = int(round(w))
            for x in range(c - r, c + r + 1):
                edge = abs(x - c) == r or y == 0
                b.set(x, y, z, ("dark_oak_planks" if y > 2 else "spruce_planks") if edge else AIR)
        r = int(round(hw))
        b.fill(c - r + 1, deck, z, c + r - 1, deck, z, "spruce_planks")
        b.set(c - r, deck + 1, z, "dark_oak_fence")
        b.set(c + r, deck + 1, z, "dark_oak_fence")
    b.fill(c - 1, 1, 6, c + 1, 1, L - 5, "spruce_planks")
    # Castello di poppa con cabina del capitano
    b.room(c - 4, deck, L - 9, c + 4, deck + 4, L - 3, "dark_oak_planks", floor="spruce_planks", ceiling="spruce_planks")
    b.walls(c - 4, deck + 5, L - 9, c + 4, deck + 5, L - 3, "dark_oak_fence")
    for x in (c - 2, c + 2):
        b.set(x, deck + 2, L - 3, "glass_pane")
    b.entrance(c, deck + 1, L - 9, "south", wood="dark_oak", step=None)
    b.bed(c - 2, deck + 1, L - 6, "south", color="black")
    b.chest(c + 3, deck + 1, L - 5, "west")
    b.set(c + 3, deck + 1, L - 7, "cartography_table")
    b.lantern(c, deck + 3, L - 6, hanging=True)
    b.lantern(c - 3, deck + 1, L - 4)
    b.fill(c + 3, deck + 1, L - 8, c + 3, deck + 4, L - 8, "dark_oak_planks")
    b.ladder(c + 2, deck + 1, deck + 4, L - 8, "west")
    # Bompresso
    b.line(c, deck + 1, 2, c, deck + 4, 0, "dark_oak_log", axis="z")
    # Alberi e vele
    for mz, mh in ((12, 23), (23, 21)):
        b.fill(c, 1, mz, c, deck + mh, mz, "dark_oak_log", axis="y")
        for y, w in ((deck + 5, 5), (deck + 12, 4)):
            for dy in range(5):
                ww = w - (1 if dy in (0, 4) else 0)
                for x in range(c - ww, c + ww + 1):
                    if x != c:
                        b.set(x, y + dy, mz + 1, "white_wool")
            b.fill(c - w, y + 5, mz, c - 1, y + 5, mz, "dark_oak_fence")
            b.fill(c + 1, y + 5, mz, c + w, y + 5, mz, "dark_oak_fence")
        b.disk(c, mz, deck + 18, 1.5, "spruce_planks")
        b.ring(c, mz, deck + 19, 1.5, "spruce_fence")
        b.set(c, deck + 18, mz, "dark_oak_log", axis="y")
        b.ladder(c, deck + 1, deck + 17, mz - 1, "north")
        b.set(c, deck + 18, mz - 1, "ladder", facing="north", waterlogged="false")
    b.fill(c + 1, deck + 21, 12, c + 3, deck + 22, 12, "black_wool")
    b.set(c + 2, deck + 22, 12, "white_wool")
    # Cannoni
    for z in (9, 15, 21, 27):
        for x in (c - 5, c + 5):
            b.set(x, deck - 1, z, AIR)
    # Stiva
    b.fill(c - 2, 2, 7, c - 2, 5, 7, "dark_oak_planks")
    b.ladder(c - 1, 2, deck, 7, "east")
    b.chest(c, 2, 16, "north")
    b.chest(c + 1, 2, 16, "north")
    b.set(c - 1, 2, 18, "barrel", facing="up", open="false")
    b.set(c + 1, 2, 20, "barrel", facing="up", open="false")
    for z in (9, 14, 20, 26):
        b.lantern(c, 2, z)
    for z in (5, 17, 28):
        b.lantern(c - 3, deck + 1, z)
        b.lantern(c + 3, deck + 1, z)
    return b
