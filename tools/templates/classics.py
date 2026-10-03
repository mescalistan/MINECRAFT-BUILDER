"""Strutture classiche di Minecraft, ricreate in versione giocabile e sicura (niente trappole)."""

from template_builder import Builder, AIR, template


@template("igloo", "Igloo", "Minecraft Classic",
          "Igloo di neve con tunnel d'ingresso, letto, fornace, banco da lavoro e tappeti.")
def igloo():
    b = Builder(11, 6, 14)
    c = 5
    b.dome(c, 0, c, 4.6, "snow_block", hollow=True, thickness=1.2)
    b.disk(c, c, 0, 3.6, "white_carpet")
    # tunnel d'ingresso verso sud
    b.fill(c - 1, 0, 9, c + 1, 2, 12, "snow_block")
    b.clear(c, 0, 8, c, 1, 13)
    b.fill(c - 1, 3, 10, c + 1, 3, 11, "snow_block")
    b.bed(c - 2, 1 - 1, c - 1, "north", color="white")
    b.set(c + 2, 0, c - 1, "furnace", facing="west", lit="false")
    b.set(c + 2, 0, c, "crafting_table")
    b.chest(c + 2, 0, c + 1, "west")
    b.lantern(c, 0, c - 2)
    b.lantern(c - 2, 0, c + 2)
    return b


@template("desert_temple", "Desert Temple", "Minecraft Classic",
          "Tempio del deserto con torri decorate in terracotta, sala centrale a mosaico e quattro casse del tesoro.")
def desert_temple():
    S = 21
    b = Builder(S, 16, S)
    b.room(0, 0, 0, S - 1, 10, S - 1, "sandstone", floor="sandstone", ceiling="cut_sandstone")
    for tx in (0, S - 5):
        b.room(tx, 0, 0, tx + 4, 14, 4, "sandstone", floor="sandstone", ceiling="cut_sandstone")
        for y in (4, 8, 12):
            b.walls(tx, y, 0, tx + 4, y, 4, "orange_terracotta")
        for x in (tx, tx + 4):
            for z in (0, 4):
                b.set(x, 15, z, "sandstone_slab", type="bottom", waterlogged="false")
        b.set(tx + 2, 13, 0, "chiseled_sandstone")
        b.lantern(tx + 2, 1, 2)
        b.lantern(tx + 2, 11, 2, hanging=True)
        b.clear(tx + 2, 1, 4, tx + 2, 2, 4)
        b.fill(tx + 1, 9, 1, tx + 3, 9, 3, "sandstone")
        b.clear(tx + 1, 10, 1, tx + 3, 13, 3)
        b.ladder(tx + 2, 1, 9, 1, "south")
    b.fill(1, 0, 5, S - 2, 0, S - 2, "sandstone")
    c = S // 2
    for x in range(c - 4, c + 5):
        for z in range(c - 4, c + 5):
            d = abs(x - c) + abs(z - c)
            if d <= 4:
                b.set(x, 0, z, "blue_terracotta" if d == 0 else "orange_terracotta" if d % 2 else "cut_sandstone")
    b.pyramid(4, 4, S - 5, S - 5, 11, "sandstone")
    b.set(c, 11 + 6, c, "chiseled_sandstone")
    # Ingresso ad arco
    b.carve_arch("x", c - 1, c + 1, S - 1, S - 1, 1, 4)
    b.stair(c, 0, S - 1, "sandstone", "north")
    for x in (c - 2, c + 2):
        b.fill(x, 1, S - 1, x, 6, S - 1, "chiseled_sandstone")
    # Nicchie con tesoro
    for x, z, f in ((1, c, "east"), (S - 2, c, "west"), (c, 6, "south"), (c - 6, 6, "south")):
        b.chest(x, 1, z, f)
    for x, z in ((3, 7), (S - 4, 7), (3, S - 4), (S - 4, S - 4), (c, c - 6), (c - 4, c + 4), (c + 4, c + 4)):
        b.lantern(x, 1, z)
    b.lantern(c, 9, c, hanging=True)
    return b


@template("jungle_temple", "Jungle Temple", "Minecraft Classic",
          "Tempio della giungla in pietrisco muschioso su due livelli, con viticci, scalinata e cassa.")
def jungle_temple():
    b = Builder(14, 12, 17, seed=4)
    mats = [("mossy_cobblestone", 3), ("cobblestone", 2), ("mossy_stone_bricks", 1)]
    b.fill_random(1, 0, 1, 12, 5, 15, mats)
    b.clear(2, 1, 2, 11, 4, 14)
    b.fill_random(3, 6, 4, 10, 8, 12, mats)
    b.clear(4, 6, 5, 9, 7, 11)
    b.fill_random(1, 5, 1, 12, 5, 15, mats)
    b.fill(4, 5, 5, 9, 5, 11, "cobblestone")
    b.fill_random(2, 9, 3, 11, 9, 13, mats)
    b.fill_random(4, 10, 5, 9, 10, 11, mats)
    for x in range(2, 12, 3):
        b.set(x, 6, 2, "cobblestone_wall")
        b.set(x, 6, 14, "cobblestone_wall")
    # Ingresso e scalinata
    b.clear(6, 1, 15, 7, 3, 15)
    for x in (6, 7):
        b.stair(x, 0, 16, "cobblestone", "north")
    for i, y in enumerate(range(1, 5)):
        for x in (6, 7):
            b.stair(x, y, 11 - i, "cobblestone", "north")
            if y > 1:
                b.fill(x, 1, 11 - i, x, y - 1, 11 - i, "cobblestone")
    b.clear(6, 5, 8, 7, 5, 10)
    b.set(3, 1, 3, "chiseled_stone_bricks")
    b.chest(4, 1, 3, "south")
    b.chest(6, 6, 6, "south")
    for x, z in ((3, 7), (10, 7), (3, 12), (10, 12), (8, 4)):
        b.lantern(x, 1, z)
    b.lantern(5, 6, 10)
    b.lantern(8, 6, 6)
    # Viticci sulle facciate
    for x in range(1, 13, 2):
        for y in range(2, 5):
            if b.rng.random() < 0.6:
                b.set(x, y, 0, "vine", south="true", north="false", east="false", west="false", up="false")
    for z in range(2, 15, 3):
        for y in range(1, 5):
            if b.rng.random() < 0.6:
                b.set(0, y, z, "vine", east="true", north="false", south="false", west="false", up="false")
                b.set(13, y, z, "vine", west="true", north="false", south="false", east="false", up="false")
    return b


@template("witch_hut", "Witch Hut", "Minecraft Classic",
          "Capanna della strega su palafitte in abete con calderone, vaso con fungo e scala d'accesso.")
def witch_hut():
    b = Builder(9, 14, 10)
    for x, z in ((1, 2), (7, 2), (1, 8), (7, 8)):
        b.fill(x, 0, z, x, 3, z, "oak_log", axis="y")
    b.fill(1, 4, 1, 7, 4, 8, "spruce_planks")
    b.room(1, 4, 3, 7, 8, 8, "spruce_planks", floor="spruce_planks", ceiling=False, corner="oak_log", axis="y")
    b.gable_roof(1, 7, 3, 8, 8, "spruce", "spruce_planks", axis="z")
    for x in (2, 6):
        b.set(x, 6, 3, "spruce_fence")
    for z in (5, 6):
        b.set(1, 6, z, "spruce_fence")
        b.set(7, 6, z, "spruce_fence")
    b.door(4, 5, 3, "south", wood="spruce")
    for x in (1, 7):
        b.set(x, 5, 1, "oak_fence")
    b.set(2, 5, 7, "cauldron")
    b.set(6, 5, 7, "crafting_table")
    b.set(6, 5, 5, "potted_red_mushroom")
    b.set(2, 5, 5, "barrel", facing="up", open="false")
    b.lantern(4, 5, 7)
    # Scala a pioli dal terreno al portico
    b.fill(4, 0, 1, 4, 3, 1, "oak_log", axis="y")
    b.ladder(4, 0, 4, 0, "north")
    b.set(4, 4, 1, "spruce_planks")
    b.lantern(1, 6, 1)
    return b


@template("pillager_outpost", "Pillager Outpost", "Minecraft Classic",
          "Avamposto dei predoni in quercia scura e betulla, con piani collegati da scale e terrazza di vedetta.")
def pillager_outpost():
    b = Builder(15, 24, 15)
    c = 7
    b.fill(2, 0, 2, 12, 0, 12, "cobblestone")
    b.room(3, 0, 3, 11, 6, 11, "birch_planks", floor="cobblestone", ceiling="dark_oak_planks",
           corner="dark_oak_log", axis="y")
    b.room(3, 6, 3, 11, 12, 11, "birch_planks", floor="dark_oak_planks", ceiling="dark_oak_planks",
           corner="dark_oak_log", axis="y")
    b.fill(1, 12, 1, 13, 12, 13, "dark_oak_planks")
    for y in (2, 3, 8, 9):
        for i in (5, 9):
            for x, z in ((i, 3), (i, 11), (3, i), (11, i)):
                if b.get(x, y, z) == "minecraft:birch_planks":
                    b.set(x, y, z, "dark_oak_fence")
    b.hip_roof(2, 12, 2, 12, 18, "dark_oak", "dark_oak_planks", overhang=1)
    b.walls(1, 13, 1, 13, 13, 13, "dark_oak_fence")
    b.clear(2, 13, 2, 12, 17, 12)
    for x, z in ((2, 2), (12, 2), (2, 12), (12, 12)):
        b.fill(x, 13, z, x, 17, z, "dark_oak_log", axis="y")
    b.entrance(c, 1, 11, "north", wood="dark_oak", step="cobblestone")
    b.fill(10, 1, 4, 10, 12, 4, "dark_oak_log", axis="y")
    b.ladder(9, 1, 12, 4, "west")
    b.chest(4, 13, 4, "south")
    b.set(5, 13, 4, "crafting_table")
    for y in (1, 7, 13):
        b.lantern(5, y, 9)
    for y in (5, 11):
        b.lantern(c, y, c, hanging=True)
    b.lantern(10, 13, 10)
    return b


@template("ruined_portal", "Ruined Portal", "Minecraft Classic",
          "Portale in rovina con cornice di ossidiana spezzata, netherrack, magma, oro e cassa del bottino.")
def ruined_portal():
    b = Builder(13, 10, 9, seed=17)
    for x in range(13):
        for z in range(9):
            if (x - 6) ** 2 / 36 + (z - 4) ** 2 / 16 <= 1 and b.rng.random() < 0.85:
                b.set(x, 0, z, b.rng.choice(["netherrack", "netherrack", "netherrack", "magma_block", "stone_bricks",
                                              "cracked_stone_bricks"]))
    frame = [(x, y) for x in range(4, 9) for y in range(1, 8) if x in (4, 8) or y in (1, 7)]
    for x, y in frame:
        r = b.rng.random()
        if (x, y) in ((8, 6), (8, 7), (7, 7)):
            continue
        b.set(x, y, 4, "crying_obsidian" if r < 0.2 else "obsidian")
    b.set(8, 1, 3, "obsidian")
    b.set(9, 1, 5, "crying_obsidian")
    b.fill(2, 1, 2, 2, 3, 2, "stone_bricks")
    b.stair(2, 4, 2, "stone_brick", "east")
    b.fill(10, 1, 6, 10, 2, 6, "cracked_stone_bricks")
    b.set(5, 1, 6, "gold_block")
    b.chest(7, 1, 6, "south")
    b.set(3, 1, 6, "netherrack")
    b.lantern(10, 3, 6)
    b.lantern(2, 1, 6)
    return b


@template("nether_fortress_bridge", "Nether Fortress Bridge", "Minecraft Classic",
          "Ponte della fortezza del Nether in mattoni infernali con archi, ringhiere e giardino di verruche.")
def nether_fortress_bridge():
    b = Builder(7, 11, 31)
    b.fill(1, 6, 0, 5, 6, 30, "nether_bricks")
    for z in range(31):
        b.set(1, 7, z, "nether_brick_fence")
        b.set(5, 7, z, "nether_brick_fence")
    for z1 in (3, 15, 27):
        b.fill(1, 0, z1 - 2, 5, 5, z1 + 2, "nether_bricks")
        b.carve_arch("z", z1 - 1, z1 + 1, 1, 5, 0, 3)
    for z1, z2 in ((6, 12), (18, 24)):
        b.carve_arch("z", z1, z2, 1, 5, 0, 5)
        b.fill(1, 5, z1, 5, 5, z2, "nether_bricks")
        b.carve_arch("z", z1 + 1, z2 - 1, 1, 5, 0, 4)
    for z in range(2, 31, 6):
        b.lantern(1, 8, z, soul=True)
        b.lantern(5, 8, z, soul=True)
    # Giardino di verruche del Nether
    b.fill(2, 6, 26, 4, 6, 29, "soul_sand")
    b.fill(2, 7, 27, 4, 7, 28, "nether_wart", age="3")
    b.stair(2, 7, 26, "nether_brick", "south")
    b.stair(4, 7, 26, "nether_brick", "south")
    b.set(3, 7, 29, "nether_bricks")
    b.chest(3, 7, 3, "south")
    # Accesso dal terreno: scala a pioli sul pilone e cancello nella ringhiera
    b.ladder(0, 0, 6, 1, "west")
    b.set(1, 7, 1, "crimson_fence_gate", facing="west", in_wall="false", open="false", powered="false")
    for z in (8, 20):
        b.lantern(3, 4, z, hanging=True)
    return b


@template("end_city_tower", "End City Tower", "Minecraft Classic",
          "Torre della citta' dell'End in purpur, con stanze sporgenti, verghe dell'End e vetrate magenta.")
def end_city_tower():
    W = 15
    b = Builder(W, 38, W)
    c = 7
    b.fill(3, 0, 3, 11, 0, 11, "end_stone_bricks")
    b.room(4, 0, 4, 10, 28, 10, "purpur_block", floor="end_stone_bricks", ceiling="purpur_block")
    for y in range(1, 28):
        for x, z in ((4, 4), (10, 4), (4, 10), (10, 10)):
            b.set(x, y, z, "purpur_pillar", axis="y")
    for py in (8, 18):
        b.room(2, py, 2, 12, py + 5, 12, "purpur_block", floor="purpur_block", ceiling="purpur_block")
        for i in (4, 7, 10):
            for x, z in ((i, 2), (i, 12), (2, i), (12, i)):
                b.set(x, py + 2, z, "magenta_stained_glass")
                b.set(x, py + 3, z, "magenta_stained_glass")
        for x in range(2, 13):
            b.stair(x, py + 6, 2, "purpur", "south")
            b.stair(x, py + 6, 12, "purpur", "north")
        for z in range(3, 12):
            b.stair(2, py + 6, z, "purpur", "east")
            b.stair(12, py + 6, z, "purpur", "west")
        b.set(c, py + 4, c, "end_rod", facing="down")
        b.set(4, py + 1, 4, "end_rod", facing="up")
        b.set(10, py + 1, 10, "end_rod", facing="up")
    for y in range(3, 28, 4):
        for x, z in ((c, 4), (c, 10), (4, c), (10, c)):
            if b.get(x, y, z) == "minecraft:purpur_block":
                b.set(x, y, z, "magenta_stained_glass")
    # Cima
    b.room(3, 28, 3, 11, 32, 11, "purpur_block", floor="purpur_block", ceiling=False)
    b.hip_roof(3, 11, 3, 11, 32, "purpur", "purpur_block", overhang=1)
    b.set(c, 31, 3, AIR)
    b.set(c, 30, 3, AIR)
    for x, z in ((4, 4), (10, 4), (4, 10), (10, 10)):
        b.set(x, 29, z, "end_rod", facing="up")
    b.chest(c, 29, 10, "north")
    b.set(c + 1, 29, 10, "brewing_stand")
    # Scala interna
    b.fill(c, 1, 5, c, 28, 5, "purpur_pillar", axis="y")
    b.ladder(c, 1, 28, 6, "south")
    b.entrance(c, 1, 10, "north", wood="birch", step="end_stone_brick")
    for y in (1, 5, 13, 25):
        b.set(5, y, 9, "end_rod", facing="up")
    b.set(9, 13, 9, "end_rod", facing="up")
    b.set(9, 23, 9, "end_rod", facing="up")
    b.set(9, 1, 6, "end_rod", facing="up")
    return b


@template("ancient_city_portal", "Ancient City Portal", "Minecraft Classic",
          "Il grande portale della citta' antica in ardesia rinforzata, con sculk, lanterne dell'anima e casse.")
def ancient_city_portal():
    W = 27
    b = Builder(W, 19, 11, seed=8)
    b.fill_random(0, 0, 0, W - 1, 0, 10, [("deepslate_tiles", 5), ("deepslate_bricks", 3), ("sculk", 2),
                                          ("cracked_deepslate_tiles", 1)])
    c = W // 2
    outline = []
    for x in range(3, W - 3):
        dx = abs(x - c)
        top = 16 - max(0, dx - 6)
        outline.append((x, top))
    for x, top in outline:
        dx = abs(x - c)
        for y in range(1, top + 1):
            inner = dx < 8 and y < top - 2 and y > 0
            if not inner:
                b.set(x, y, 5, "reinforced_deepslate" if dx >= 8 or y >= top - 2 else "deepslate_tiles")
        if dx < 8:
            b.set(x, top - 2, 5, "reinforced_deepslate")
    for x in (c - 9, c + 9):
        b.fill(x, 1, 4, x, 3, 6, "deepslate_bricks")
        b.set(x, 4, 5, "polished_deepslate_wall")
        b.lantern(x, 5, 5, soul=True)
    for x in range(c - 6, c + 7, 3):
        b.fill(x, 1, 1, x, 1, 1, "deepslate_tile_wall")
        b.lantern(x, 2, 1, soul=True)
        b.fill(x, 1, 9, x, 1, 9, "deepslate_tile_wall")
        b.lantern(x, 2, 9, soul=True)
    b.chest(2, 1, 2, "south")
    b.chest(W - 3, 1, 8, "north")
    b.set(4, 1, 8, "gray_candle", candles="3", lit="true", waterlogged="false")
    b.set(W - 5, 1, 2, "gray_candle", candles="2", lit="true", waterlogged="false")
    return b


@template("desert_well", "Desert Well", "Minecraft Classic",
          "Il classico pozzo del deserto in arenaria con acqua al centro e tettoia su quattro pilastri.")
def desert_well():
    b = Builder(5, 5, 5)
    b.fill(0, 0, 0, 4, 0, 4, "sandstone")
    b.set(2, 0, 2, "water", level="0")
    b.walls(1, 1, 1, 3, 1, 3, "sandstone_slab", type="bottom", waterlogged="false")
    b.set(2, 1, 2, AIR)
    for x, z in ((1, 1), (3, 1), (1, 3), (3, 3)):
        b.fill(x, 1, z, x, 2, z, "sandstone")
    b.fill(1, 3, 1, 3, 3, 3, "sandstone_slab", type="bottom", waterlogged="false")
    b.set(2, 3, 2, "sandstone")
    b.lantern(2, 2, 2, hanging=True)
    return b


@template("plains_village_house", "Plains Village House", "Minecraft Classic",
          "Casa del villaggio delle pianure: fondamenta in pietrisco, travi di quercia, fioriere e arredamento.")
def plains_village_house():
    b = Builder(11, 10, 9)
    b.room(1, 0, 1, 9, 4, 7, "oak_planks", floor="cobblestone", ceiling="oak_planks", corner="oak_log", axis="y")
    b.walls(1, 1, 1, 9, 1, 7, "cobblestone")
    for x, z in ((1, 1), (9, 1), (1, 7), (9, 7)):
        b.set(x, 1, z, "oak_log", axis="y")
    for x in (3, 7):
        b.set(x, 2, 1, "glass_pane")
        b.set(x, 2, 7, "glass_pane")
    b.set(1, 2, 4, "glass_pane")
    b.set(9, 2, 4, "glass_pane")
    b.gable_roof(1, 9, 1, 7, 4, "oak", "oak_planks", axis="x")
    b.entrance(5, 1, 7, "north", wood="oak", step="cobblestone")
    b.bed(2, 1, 3, "north", color="yellow")
    b.set(8, 1, 2, "crafting_table")
    b.set(8, 1, 3, "furnace", facing="west", lit="false")
    b.chest(8, 1, 6, "west")
    b.set(2, 1, 6, "composter", level="0")
    b.set(5, 1, 2, "potted_cornflower")
    b.lantern(5, 3, 4, hanging=True)
    b.wall_torch(4, 3, 6, "north")
    b.wall_torch(6, 3, 6, "north")
    return b
