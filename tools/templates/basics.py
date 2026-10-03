"""Template di base: case, pozzo, torri, fattorie e utilita'."""
import math

from template_builder import Builder, AIR, template


def stone_variant(rng, base="stone_bricks"):
    r = rng.random()
    if r < 0.12:
        return "mossy_stone_bricks"
    if r < 0.22:
        return "cracked_stone_bricks"
    return base


@template("starter_cottage", "Starter Cottage", "House",
          "Casetta 9x9 in quercia con tetto a capanna, letto, forno, cassa e illuminazione.")
def starter_cottage():
    b = Builder(11, 10, 11)
    b.fill(1, 0, 1, 9, 0, 9, "cobblestone")
    b.fill(2, 0, 2, 8, 0, 8, "oak_planks")
    b.walls(1, 1, 1, 9, 3, 9, "oak_planks")
    for x, z in ((1, 1), (9, 1), (1, 9), (9, 9)):
        b.fill(x, 1, z, x, 3, z, "oak_log", axis="y")
    b.clear(2, 1, 2, 8, 3, 8)
    for x in (3, 7):
        b.set(x, 2, 1, "glass_pane")
        b.set(x, 2, 9, "glass_pane")
    for z in (3, 7):
        b.set(1, 2, z, "glass_pane")
        b.set(9, 2, z, "glass_pane")
    b.door(5, 1, 9, facing="north")
    b.stair(5, 0, 10, "oak", "north")
    b.fill(1, 4, 1, 9, 4, 9, "oak_planks")
    b.gable_roof(1, 9, 1, 9, 4, "spruce", "spruce_planks", axis="x")
    b.bed(3, 1, 3, facing="north", color="red")
    b.set(7, 1, 2, "crafting_table")
    b.set(8, 1, 2, "furnace", facing="south", lit="false")
    b.chest(8, 1, 5, "west")
    b.set(8, 1, 6, "barrel", facing="up", open="false")
    b.set(2, 1, 8, "potted_poppy")
    b.lantern(5, 3, 5, hanging=True)
    b.wall_torch(4, 2, 8, "north")
    b.wall_torch(6, 2, 8, "north")
    for x in (3, 7):
        b.leaves(x, 0, 10)
    return b


@template("village_well", "Village Well", "Decoration",
          "Pozzo da villaggio con acqua, tettoia in pietra e lanterne.")
def village_well():
    b = Builder(6, 9, 6)
    b.fill(0, 0, 0, 5, 0, 5, "cobblestone")
    b.walls(0, 1, 0, 5, 4, 5, "cobblestone")
    b.fill(1, 1, 1, 4, 3, 4, "water", level="0")
    b.clear(1, 4, 1, 4, 4, 4)
    b.walls(0, 4, 0, 5, 4, 5, "mossy_cobblestone")
    for x, z in ((0, 0), (5, 0), (0, 5), (5, 5)):
        b.fill(x, 5, z, x, 6, z, "oak_fence")
    b.clear(1, 5, 1, 4, 6, 4)
    b.fill(0, 7, 0, 5, 7, 5, "cobblestone_slab", type="bottom", waterlogged="false")
    b.fill(1, 8, 1, 4, 8, 4, "cobblestone_slab", type="bottom", waterlogged="false")
    b.fill(2, 7, 2, 3, 7, 3, "cobblestone")
    b.lantern(2, 6, 2, hanging=True)
    b.lantern(3, 6, 3, hanging=True)
    return b


@template("watchtower", "Medieval Watchtower", "Medieval",
          "Torre di guardia 7x7 alta 16 blocchi con scala a pioli, piano intermedio e merli.")
def watchtower():
    b = Builder(9, 16, 9, seed=42)
    b.fill(1, 0, 1, 7, 0, 7, "stone_bricks")
    for y in range(1, 13):
        for x in range(1, 8):
            for z in range(1, 8):
                if x in (1, 7) or z in (1, 7):
                    b.set(x, y, z, stone_variant(b.rng))
    b.clear(2, 1, 2, 6, 12, 6)
    b.door(4, 1, 7, facing="north", wood="spruce")
    b.stair(4, 0, 8, "stone_brick", "north")
    for y in (4, 9):
        b.set(1, y, 4, AIR)
        b.set(7, y, 4, AIR)
        b.set(2, y, 1, AIR)
        b.set(6, y, 1, AIR)
    b.set(4, 9, 7, AIR)
    b.fill(2, 7, 2, 6, 7, 6, "spruce_planks")
    b.fill(0, 13, 0, 8, 13, 8, "stone_bricks")
    for i in range(1, 8):
        b.stair(i, 12, 0, "stone_brick", "south", top=True)
        b.stair(i, 12, 8, "stone_brick", "north", top=True)
        b.stair(0, 12, i, "stone_brick", "east", top=True)
        b.stair(8, 12, i, "stone_brick", "west", top=True)
    b.ladder(4, 1, 13, 2, "south")
    for i in range(9):
        for x, z in ((i, 0), (i, 8), (0, i), (8, i)):
            b.set(x, 14, z, "stone_brick_wall")
    for x, z in ((0, 0), (8, 0), (0, 8), (8, 8)):
        b.set(x, 14, z, "chiseled_stone_bricks")
        b.lantern(x, 15, z)
    b.clear(1, 14, 1, 7, 15, 7)
    b.wall_torch(2, 3, 4, "east")
    b.wall_torch(6, 3, 4, "west")
    b.wall_torch(2, 10, 4, "east")
    b.wall_torch(6, 10, 4, "west")
    b.chest(6, 8, 6, "west")
    b.set(2, 8, 6, "barrel", facing="up", open="false")
    b.lantern(4, 14, 4)
    return b


@template("lighthouse", "Lighthouse", "Utility",
          "Faro a strisce bianche e rosse con galleria panoramica e lanterna in vetro.")
def lighthouse():
    b = Builder(11, 28, 11)
    c = 5

    def dist(x, z):
        return math.hypot(x - c, z - c)

    for x in range(11):
        for z in range(11):
            d = dist(x, z)
            if d <= 5.5:
                b.set(x, 0, z, "stone_bricks")
            for y in range(1, 21):
                if 2.5 < d <= 3.6:
                    b.set(x, y, z, "red_concrete" if (y - 1) // 4 % 2 else "white_concrete")
                elif d <= 2.5:
                    b.set(x, y, z, AIR)
            if d <= 5.5:
                b.set(x, 21, z, "smooth_stone")
            if 4.5 < d <= 5.5:
                b.set(x, 22, z, "iron_bars")
            elif 3.6 < d <= 4.5:
                b.set(x, 22, z, AIR)
            for y in range(22, 25):
                if 2.5 < d <= 3.6:
                    b.set(x, y, z, "glass")
                elif d <= 2.5:
                    b.set(x, y, z, AIR)
            if d <= 3.6:
                b.set(x, 25, z, "red_concrete")
            if d <= 2.3:
                b.set(x, 26, z, "red_concrete")
    b.set(c, 27, c, "lightning_rod", facing="up", powered="false", waterlogged="false")
    b.set(c, 22, c, "polished_andesite")
    b.set(c, 23, c, "sea_lantern")
    b.set(c, 24, c, "glowstone")
    b.door(c, 1, 8, facing="north", wood="spruce")
    b.ladder(c, 1, 22, 3, "south")
    b.door(c, 22, 8, facing="north", wood="spruce")
    for y in (6, 12, 18):
        b.wall_torch(c + 2, y, c, "west")
        b.wall_torch(c - 2, y, c, "east")
    b.lantern(c + 1, 1, c + 1)
    return b


@template("crop_farm", "Crop Farm (Mixed)", "Farm",
          "Campo idratato con grano, carote, patate e barbabietole, recintato.")
def crop_farm():
    b = Builder(11, 3, 15)
    b.walls(0, 0, 0, 10, 0, 14, "oak_log", axis="y")
    b.fill(1, 0, 1, 9, 0, 13, "farmland", moisture="7")
    b.fill(5, 0, 1, 5, 0, 13, "water", level="0")
    crops = [("wheat", "7", 1, 3), ("carrots", "7", 4, 6), ("potatoes", "7", 7, 9), ("beetroots", "3", 10, 13)]
    for name, age, z1, z2 in crops:
        for x in range(1, 10):
            if x == 5:
                continue
            for z in range(z1, z2 + 1):
                b.set(x, 1, z, name, age=age)
    b.fill(5, 1, 1, 5, 1, 13, "oak_slab", type="bottom", waterlogged="false")
    b.walls(0, 1, 0, 10, 1, 14, "oak_fence")
    b.set(5, 1, 14, "oak_fence_gate", facing="south", in_wall="false", open="false", powered="false")
    for x, z in ((0, 0), (10, 0), (0, 14), (10, 14)):
        b.set(x, 2, z, "torch")
    b.lantern(4, 2, 14)
    b.lantern(6, 2, 14)
    return b


@template("animal_pen", "Animal Pen", "Farm",
          "Recinto per animali con riparo, fieno, compostiera e abbeveratoi.")
def animal_pen():
    b = Builder(11, 4, 11)
    b.walls(0, 0, 0, 10, 0, 10, "spruce_fence")
    b.set(5, 0, 10, "spruce_fence_gate", facing="south", in_wall="false", open="false", powered="false")
    for x, z in ((0, 0), (10, 0), (0, 10), (10, 10)):
        b.lantern(x, 1, z)
    for x, z in ((6, 1), (9, 1), (6, 4), (9, 4)):
        b.fill(x, 0, z, x, 1, z, "spruce_log", axis="y")
    b.fill(6, 2, 0, 9, 2, 5, "spruce_slab", type="bottom", waterlogged="false")
    b.fill(7, 0, 1, 8, 0, 1, "hay_block", axis="x")
    b.set(7, 1, 1, "hay_block", axis="z")
    b.set(1, 0, 8, "water_cauldron", level="3")
    b.set(2, 0, 8, "water_cauldron", level="3")
    b.set(1, 0, 1, "composter", level="0")
    b.set(2, 0, 1, "barrel", facing="up", open="false")
    b.lantern(7, 1, 3, hanging=True)
    return b


@template("stone_bridge", "Stone Bridge", "Utility",
          "Ponte in pietra 5x25 a tre pile con archi, parapetti e lanterne.")
def stone_bridge():
    b = Builder(5, 7, 25, seed=7)
    for z1, z2 in [(0, 2), (11, 13), (22, 24)]:
        for z in range(z1, z2 + 1):
            for x in range(5):
                for y in range(0, 4):
                    b.set(x, y, z, stone_variant(b.rng))
    for z in range(25):
        for x in range(5):
            b.set(x, 4, z, stone_variant(b.rng))
            if b.get(x, 3, z) is None:
                b.slab(x, 3, z, "stone_brick", top=True)
        b.set(0, 5, z, "stone_brick_wall")
        b.set(4, 5, z, "stone_brick_wall")
    for z, facing in ((3, "north"), (10, "south"), (14, "north"), (21, "south")):
        for x in range(5):
            b.stair(x, 3, z, "stone_brick", facing, top=True)
            b.stair(x, 2, z, "stone_brick", facing, top=True)
    for z in (0, 6, 12, 18, 24):
        b.lantern(0, 6, z)
        b.lantern(4, 6, z)
    b.clear(1, 5, 0, 3, 6, 24)
    return b


@template("market_stall", "Market Stall", "Decoration",
          "Bancarella con tendone a righe, bancone, barili e lanterna.")
def market_stall():
    b = Builder(5, 5, 5)
    for x, z in ((0, 1), (4, 1), (0, 4), (4, 4)):
        b.fill(x, 0, z, x, 2, z, "spruce_log", axis="y")
    for x in range(1, 4):
        b.stair(x, 0, 1, "spruce", "south", top=True)
    b.set(1, 1, 1, "potted_dandelion")
    b.set(3, 1, 1, "potted_blue_orchid")
    b.set(2, 1, 1, "melon")
    b.set(1, 0, 4, "barrel", facing="up", open="false")
    b.chest(2, 0, 4, "north")
    b.set(3, 0, 4, "barrel", facing="up", open="false")
    b.clear(1, 0, 2, 3, 2, 3)
    b.clear(1, 1, 4, 3, 2, 4)
    for x in range(5):
        wool = "red_wool" if x % 2 == 0 else "white_wool"
        b.fill(x, 3, 0, x, 3, 4, wool)
        b.set(x, 4, 2, wool)
        b.set(x, 4, 3, wool)
    b.lantern(2, 2, 2, hanging=True)
    # side openings so the shopkeeper can get behind the counter
    b.clear(0, 0, 2, 0, 1, 3)
    return b


@template("nether_portal_shrine", "Nether Portal Shrine", "Utility",
          "Portale del Nether gia' acceso su piattaforma in pietranera con lanterne dell'anima.")
def nether_portal_shrine():
    b = Builder(8, 7, 5, seed=3)
    for x in range(8):
        for z in range(5):
            b.set(x, 0, z, "gilded_blackstone" if b.rng.random() < 0.08 else "polished_blackstone_bricks")
    b.clear(0, 1, 0, 7, 5, 4)
    for y in range(1, 6):
        b.set(2, y, 2, "obsidian")
        b.set(5, y, 2, "obsidian")
    for x in range(2, 6):
        b.set(x, 1, 2, "obsidian")
        b.set(x, 5, 2, "obsidian")
    for x, y in ((2, 1), (5, 1), (2, 5), (5, 5)):
        b.set(x, y, 2, "crying_obsidian")
    for x in (3, 4):
        for y in (2, 3, 4):
            b.set(x, y, 2, "nether_portal", axis="x")
    for x, z in ((0, 0), (7, 0), (0, 4), (7, 4)):
        b.set(x, 1, z, "polished_blackstone_wall")
        b.lantern(x, 2, z, soul=True)
    for x in range(2, 6):
        b.stair(x, 0, 0, "polished_blackstone_brick", "south")
        b.stair(x, 0, 4, "polished_blackstone_brick", "north")
    return b


@template("blacksmith_forge", "Blacksmith Forge", "House",
          "Fucina aperta con altoforno, incudine, banco da forgiatura e camino fumante.")
def blacksmith_forge():
    b = Builder(9, 11, 9)
    b.fill(1, 0, 1, 7, 0, 7, "cobblestone")
    b.fill(2, 0, 2, 6, 0, 6, "stone_bricks")
    b.fill(1, 1, 1, 7, 3, 1, "stone_bricks")
    b.fill(1, 1, 1, 1, 3, 7, "stone_bricks")
    for x, z in ((7, 1), (1, 7), (7, 7)):
        b.fill(x, 1, z, x, 3, z, "spruce_log", axis="y")
    b.clear(2, 1, 2, 6, 3, 6)
    b.clear(7, 1, 2, 7, 3, 6)
    b.clear(2, 1, 7, 6, 3, 7)
    b.set(1, 2, 4, "iron_bars")
    b.set(4, 2, 1, "iron_bars")
    b.fill(1, 4, 1, 7, 4, 1, "spruce_log", axis="x")
    b.fill(1, 4, 7, 7, 4, 7, "spruce_log", axis="x")
    b.fill(1, 4, 2, 1, 4, 6, "spruce_log", axis="z")
    b.fill(7, 4, 2, 7, 4, 6, "spruce_log", axis="z")
    b.clear(2, 4, 2, 6, 4, 6)
    b.gable_roof(1, 7, 1, 7, 4, "spruce", "spruce_planks", axis="x")
    b.set(2, 1, 2, "blast_furnace", facing="south", lit="false")
    b.fill(2, 2, 2, 2, 9, 2, "bricks")
    b.set(2, 10, 2, "campfire", lit="true", signal_fire="false", facing="north", waterlogged="false")
    b.set(3, 1, 2, "lava_cauldron")
    b.set(4, 1, 2, "smithing_table")
    b.set(5, 1, 2, "grindstone", face="floor", facing="north")
    b.set(4, 1, 4, "anvil", facing="east")
    b.chest(2, 1, 5, "east")
    b.set(2, 1, 6, "barrel", facing="up", open="false")
    b.set(6, 1, 6, "water_cauldron", level="3")
    b.fill(4, 5, 4, 4, 7, 4, "spruce_fence")
    b.lantern(4, 4, 4, hanging=True)
    return b
