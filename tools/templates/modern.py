"""Architettura moderna."""
from template_builder import Builder, AIR, template


@template("modern_villa", "Modern Villa", "House",
          "Villa moderna in cemento bianco e vetro: volume superiore a sbalzo, terrazza, piscina, scala interna e giardino.")
def modern_villa():
    W, L = 23, 20
    b = Builder(W, 10, L, seed=41)
    WH = "white_concrete"
    # Volume inferiore
    b.room(1, 0, 1, 14, 4, 12, WH, floor="smooth_quartz", ceiling=WH)
    for x in range(2, 14):
        for y in (1, 2, 3):
            b.set(x, y, 12, "glass")
    for z in range(3, 11, 2):
        b.set(1, 2, z, "glass")
    # Volume superiore a sbalzo
    b.room(6, 4, 2, 21, 8, 11, WH, floor=WH, ceiling=WH)
    for x in range(7, 21):
        b.set(x, 6, 2, "glass")
        b.set(x, 6, 11, "glass")
    for z in (2, 11):
        b.fill(21, 0, z, 21, 3, z, WH)
    b.walls(6, 9, 2, 21, 9, 11, "smooth_quartz_slab", type="bottom", waterlogged="false")
    b.clear(7, 9, 3, 20, 9, 10)
    # Terrazza sul volume inferiore
    for x in range(1, 6):
        b.set(x, 5, 1, "glass_pane")
        b.set(x, 5, 12, "glass_pane")
    for z in range(1, 13):
        b.set(1, 5, z, "glass_pane")
    b.clear(2, 5, 2, 5, 7, 11)
    b.entrance(6, 5, 6, "west", wood="birch", step=None)
    b.lantern(3, 5, 3)
    b.lantern(3, 5, 10)
    # Ingresso
    b.entrance(7, 1, 1, "south", wood="birch", step="smooth_quartz")
    # Scala interna (rampa lungo z)
    for i, (y, z) in enumerate(((1, 9), (2, 8), (3, 7), (4, 6))):
        b.stair(13, y, z, "quartz", "north")
        if y > 1:
            b.fill(13, 1, z, 13, y - 1, z, "smooth_quartz")
    b.clear(13, 4, 7, 13, 4, 9)
    b.clear(12, 4, 7, 12, 4, 9)
    b.set(12, 4, 6, WH)
    # Luci a soffitto
    for x, z in ((4, 4), (4, 9), (9, 4), (9, 9)):
        b.set(x, 4, z, "sea_lantern")
    for x, z in ((9, 5), (9, 8), (15, 5), (15, 8), (19, 6)):
        b.set(x, 8, z, "sea_lantern")
    # Arredi piano terra: soggiorno e cucina
    for x in range(3, 7):
        b.set(x, 1, 10, "white_wool")
    b.stair(3, 1, 9, "quartz", "south")
    b.set(4, 1, 8, "black_carpet")
    b.set(10, 1, 2, "smoker", facing="south", lit="false")
    b.set(11, 1, 2, "barrel", facing="south", open="false")
    b.set(12, 1, 2, "crafting_table")
    b.table(10, 1, 5, "birch")
    b.set(2, 1, 2, "potted_fern")
    # Arredi piano superiore
    b.bed(16, 5, 4, "north", color="white")
    b.bed(19, 5, 4, "north", color="black")
    b.chest(20, 5, 9, "west")
    b.set(16, 5, 9, "bookshelf")
    b.set(9, 5, 9, "potted_bamboo")
    # Piscina e giardino
    b.fill(2, 0, 13, 14, 0, 18, "smooth_quartz")
    b.fill(3, 0, 14, 13, 0, 17, "water", level="0")
    b.tree(17, 0, 15, "birch", height=4, radius=2)
    b.tree(20, 0, 18, "birch", height=3, radius=1)
    for x in (1, 15):
        b.lantern(x, 0, 18)
    b.lantern(17, 0, 6)
    return b


@template("skyscraper", "Skyscraper", "House",
          "Grattacielo di 15 piani con facciata in vetro, atrio, uffici illuminati, scala a pioli nel nucleo ed eliporto.")
def skyscraper():
    W = 15
    b = Builder(W, 64, W)
    top = 60
    for y in range(0, top + 1):
        for x in range(1, 14):
            for z in range(1, 14):
                edge = x in (1, 13) or z in (1, 13)
                if y % 4 == 0:
                    b.set(x, y, z, "gray_concrete" if edge else "smooth_stone")
                elif edge:
                    mullion = (x in (1, 13) and z % 3 == 1) or (z in (1, 13) and x % 3 == 1)
                    b.set(x, y, z, "gray_concrete" if mullion else "light_blue_stained_glass")
                else:
                    b.set(x, y, z, AIR)
    # Nucleo con scala a pioli
    for y in range(1, top):
        if y % 4:
            b.walls(6, y, 6, 8, y, 8, "white_concrete")
    b.fill(7, 0, 7, 7, top, 7, AIR)
    b.ladder(7, 1, top, 7, "south")
    for f in range(0, top, 4):
        b.set(7, f + 1, 8, AIR)
        b.set(7, f + 2, 8, AIR)
        for x, z in ((4, 4), (10, 4), (4, 10), (10, 10)):
            if f > 0:
                b.set(x, f, z, "sea_lantern")
        if f > 0:
            b.set(3, f + 1, 3, "barrel", facing="up", open="false")
            b.set(11, f + 1, 11, "potted_fern")
            b.table(11, f + 1, 3, "birch")
    for x, z in ((4, 4), (10, 4), (4, 10), (10, 10)):
        b.set(x, top, z, "sea_lantern")
    # Atrio
    b.door(6, 1, 13, "north", wood="birch", hinge="right")
    b.door(7, 1, 13, "north", wood="birch")
    for x in (6, 7):
        b.slab(x, 0, 14, "smooth_stone")
    b.lantern(3, 1, 10)
    b.lantern(11, 1, 6)
    b.lantern(3, 1, 4)
    for x in range(4, 10):
        b.stair(x, 1, 10, "quartz", "south", top=True)
    # Tetto con eliporto
    b.fill(4, top, 4, 10, top, 10, "gray_concrete")
    for z in range(5, 10):
        b.set(5, top, z, "yellow_concrete")
        b.set(9, top, z, "yellow_concrete")
    for x in range(6, 9):
        b.set(x, top, 7, "yellow_concrete")
    b.set(7, top, 7, "ladder", facing="south", waterlogged="false")
    b.walls(1, top + 1, 1, 13, top + 1, 13, "white_stained_glass_pane")
    b.fill(12, top + 1, 12, 12, top + 2, 12, "iron_bars")
    b.set(12, top + 3, 12, "lightning_rod", facing="up", powered="false", waterlogged="false")
    for x, z in ((2, 2), (12, 2), (2, 12)):
        b.lantern(x, top + 1, z)
    return b
