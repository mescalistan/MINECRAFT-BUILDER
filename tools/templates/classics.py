"""Strutture classiche di Minecraft, ricreate in versione giocabile e sicura (niente trappole)."""

from template_builder import Builder, AIR, template


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
