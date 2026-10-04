"""Strutture "vetrina": edifici dettagliati con piu' materiali, profondita' e arredi curati."""
import math

from template_builder import Builder, AIR, template

STONE_MIX = [("stone_bricks", 6), ("mossy_stone_bricks", 1), ("cracked_stone_bricks", 1), ("andesite", 1)]


def _windows(b, x1, x2, z1, z2, y, block="glass_pane", step=3, skip=()):
    for x in range(x1 + 2, x2 - 1, step):
        for z in (z1, z2):
            if (x, z) not in skip:
                b.set(x, y, z, block)
    for z in range(z1 + 2, z2 - 1, step):
        for x in (x1, x2):
            if (x, z) not in skip:
                b.set(x, y, z, block)


@template("himeji_castle", "Japanese Castle (Himeji)", "Castelli e fortezze",
          "Castello giapponese ispirato a Himeji: basamento di pietra a scarpa, quattro piani bianchi con tetti "
          "a gronda ricurva, timpani decorativi e pesci d'oro sul colmo.")
def himeji_castle():
    W, L = 31, 28
    b = Builder(W, 38, L, seed=61)
    c = 15
    # Basamento a scarpa
    for level, (x1, z1, x2, z2) in enumerate(((2, 2, 28, 24), (2, 2, 28, 24), (3, 3, 27, 23), (3, 3, 27, 23),
                                              (4, 4, 26, 22), (4, 4, 26, 22))):
        b.fill_random(x1, level, z1, x2, level, z2, STONE_MIX)
        if level % 2 == 0 and level > 0:
            for x in range(x1, x2 + 1):
                b.stair(x, level - 1, z1 - 1, "andesite", "south")
                b.stair(x, level - 1, z2 + 1, "andesite", "north")
            for z in range(z1, z2 + 1):
                b.stair(x1 - 1, level - 1, z, "andesite", "east")
                b.stair(x2 + 1, level - 1, z, "andesite", "west")
    # Scalinata d'ingresso
    for i, z in enumerate(range(27, 22, -1)):
        for x in range(c - 1, c + 2):
            b.stair(x, i, z, "stone_brick", "north")
            if i:
                b.fill(x, 0, z, x, i - 1, z, "stone_bricks")
    # Piani del mastio
    tiers = [(5, 5, 25, 21, 5), (7, 7, 23, 19, 11), (9, 9, 21, 17, 17), (11, 11, 19, 15, 23)]
    for i, (x1, z1, x2, z2, yb) in enumerate(tiers):
        b.room(x1, yb, z1, x2, yb + 5, z2, "white_concrete", floor="dark_oak_planks", ceiling="dark_oak_planks")
        for x, z in ((x1, z1), (x2, z1), (x1, z2), (x2, z2)):
            b.fill(x, yb + 1, z, x, yb + 4, z, "light_gray_concrete")
        b.walls(x1, yb + 1, z1, x2, yb + 1, z2, "light_gray_concrete")
        _windows(b, x1, x2, z1, z2, yb + 3, "black_stained_glass_pane", step=3)
        for lx, lz in ((x1 + 2, z1 + 2), (x2 - 2, z2 - 2), (x1 + 2, z2 - 2), (x2 - 2, z1 + 2)):
            b.lantern(lx, yb + 1, lz)
        if i < len(tiers) - 1:
            b.eave(x1, x2, z1, z2, yb + 5, "deepslate_tile", overhang=2)
            # timpano decorativo (chidori-hafu) bianco sul lato sud
            if i in (0, 2):
                b.gable_roof(c - 2, c + 2, z2, z2 + 1, yb + 6, "deepslate_tile", "white_concrete", axis="z",
                             overhang=0, fill_attic=False)
    top = b.hip_roof(11, 19, 11, 15, 28, "deepslate_tile", "deepslate_tiles", overhang=2)
    for x in (12, 18):
        b.set(x, top + 1, 13, "gold_block")
    # Scala interna e ingresso
    b.fill(c, 6, c - 2, c, 28, c - 2, "stripped_dark_oak_log", axis="y")
    b.ladder(c, 6, 27, c - 1, "south")
    b.entrance(c, 6, 21, "north", wood="dark_oak", step=None)
    b.chest(c + 2, 24, 12, "south")
    b.set(c - 2, 24, 12, "bell", attachment="floor", facing="south", powered="false")
    for x, z in ((1, 1), (29, 1), (1, 25), (29, 25)):
        b.set(x, 0, z, "stone_brick_wall")
        b.lantern(x, 1, z)
    for x, z in ((3, 26), (27, 26)):
        b.tree(x, 0, z, "cherry", height=4, radius=2)
    return b


@template("santorini_villa", "Santorini Villa", "Case",
          "Villa cicladica di Santorini: terrazze imbiancate, cappella con cupola blu e campaniletto, piscina, "
          "porte e persiane turchesi e buganvillee rosa.")
def santorini_villa():
    W, L = 25, 23
    b = Builder(W, 17, L, seed=62)
    WH = "white_concrete"
    b.fill(1, 0, 1, W - 2, 2, L - 2, WH)
    for x in range(1, W - 1):
        b.slab(x, 3, L - 2, "smooth_quartz")
    for z in range(1, L - 1):
        b.slab(1, 3, z, "smooth_quartz")
        b.slab(W - 2, 3, z, "smooth_quartz")
    # Scala d'accesso alla terrazza, ricavata nel bordo
    for x in (11, 12, 13):
        for i, z in enumerate((L - 2, L - 3, L - 4)):
            b.clear(x, i + 1, z, x, 3, z)
            b.stair(x, i, z, "smooth_quartz", "north")
    # Casa principale (due volumi sfalsati)
    b.room(2, 3, 2, 11, 8, 10, WH, floor="smooth_quartz", ceiling=WH)
    b.room(4, 8, 3, 10, 12, 8, WH, floor=WH, ceiling=WH)
    for x in range(2, 12):
        b.slab(x, 9, 10, "smooth_quartz")
    for x, y, z in ((4, 5, 10), (8, 5, 10), (2, 5, 6), (6, 10, 8), (9, 10, 8), (4, 10, 3)):
        b.set(x, y, z, "glass_pane")
    for x in (3, 5, 7, 9):
        b.set(x, 5, 11, "warped_trapdoor", facing="south", half="top", open="true", powered="false",
              waterlogged="false")
    b.entrance(6, 4, 10, "north", wood="warped", step=None)
    b.fill(10, 4, 4, 10, 7, 4, WH)
    b.ladder(9, 4, 8, 4, "west")
    b.bed(6, 9, 5, "north", color="light_blue")
    b.chest(8, 9, 7, "north")
    b.set(3, 4, 3, "smoker", facing="south", lit="false")
    b.set(4, 4, 3, "barrel", facing="up", open="false")
    b.table(7, 4, 6, "birch")
    for x, y, z in ((5, 7, 6), (8, 7, 6), (7, 11, 5)):
        b.set(x, y + 1, z, "sea_lantern")
    # Cappella con cupola blu
    b.room(14, 3, 2, 21, 8, 9, WH, floor="smooth_quartz", ceiling=WH)
    b.dome(17, 9, 5, 2.5, "blue_concrete", hollow=False)
    b.set(17, 12, 5, "gold_block")
    b.fill(21, 9, 7, 21, 11, 7, WH)
    b.fill(21, 9, 9, 21, 11, 9, WH)
    b.fill(21, 12, 7, 21, 12, 9, WH)
    b.set(21, 11, 8, "bell", attachment="ceiling", facing="east", powered="false")
    b.entrance(17, 4, 9, "north", wood="warped", step=None)
    b.set(17, 4, 3, "gold_block")
    b.set(16, 4, 3, "white_candle", candles="3", lit="true", waterlogged="false")
    b.set(18, 4, 3, "white_candle", candles="3", lit="true", waterlogged="false")
    b.set(17, 7, 6, "sea_lantern")
    b.ladder(13, 3, 8, 2, "west")
    b.set(14, 5, 5, "light_blue_stained_glass_pane")
    # Piscina
    b.fill(14, 2, 12, 22, 2, 19, "light_blue_concrete")
    b.fill(15, 2, 13, 21, 2, 18, "water", level="0")
    for z in (13, 18):
        b.set(13, 3, z, "white_stained_glass_pane")
    # Buganvillee e lanterne
    for x, y, z in ((2, 7, 11), (3, 8, 11), (12, 6, 3), (12, 7, 4), (13, 3, 11), (2, 3, 12), (3, 3, 12)):
        b.leaves(x, y, z, "cherry")
    for x, z in ((3, 18), (10, 18), (23, 2)):
        b.lantern(x, 3, z)
    b.set(6, 3, 15, "potted_azalea_bush")
    b.set(8, 3, 15, "potted_flowering_azalea_bush")
    return b


@template("cottage_garden", "Cottage with Garden", "Case",
          "Cottage inglese con tetto di paglia, muri in pietra e graticcio, camino, giardino fiorito con "
          "staccionata, pozzetto, arnia e melo.")
def cottage_garden():
    W, L = 21, 21
    b = Builder(W, 13, L, seed=63)
    # Casetta
    b.fill_random(5, 0, 3, 15, 0, 11, [("cobblestone", 3), ("mossy_cobblestone", 2)])
    b.fill(6, 0, 4, 14, 0, 10, "spruce_planks")
    b.walls(5, 1, 3, 15, 2, 11, "cobblestone")
    b.replace(5, 1, 3, 15, 2, 11, "cobblestone", "mossy_cobblestone", chance=0.35)
    b.walls(5, 3, 3, 15, 4, 11, "mushroom_stem")
    for x in (5, 8, 12, 15):
        b.fill(x, 3, 3, x, 4, 3, "spruce_log", axis="y")
        b.fill(x, 3, 11, x, 4, 11, "spruce_log", axis="y")
    for z in (3, 7, 11):
        b.fill(5, 3, z, 5, 4, z, "spruce_log", axis="y")
        b.fill(15, 3, z, 15, 4, z, "spruce_log", axis="y")
    b.fill(5, 5, 3, 15, 5, 11, "spruce_planks")
    b.clear(6, 1, 4, 14, 4, 10)
    # Tetto di paglia (balle di fieno) con gronde in abete
    for lvl in range(6):
        z1, z2 = 2 + lvl, 12 - lvl
        if z1 > z2:
            break
        for x in range(4, 17):
            if z1 == z2:
                b.set(x, 6 + lvl, z1, "hay_block", axis="x")
            else:
                b.set(x, 6 + lvl, z1, "hay_block", axis="x")
                b.set(x, 6 + lvl, z2, "hay_block", axis="x")
        for z in range(z1 + 1, z2):
            for x in (5, 15):
                b.set(x, 6 + lvl, z, "mushroom_stem")
    for x in range(4, 17):
        b.stair(x, 5, 2, "spruce", "south")
        b.stair(x, 5, 12, "spruce", "north")
    for x, z in ((9, 3), (11, 3), (7, 11), (13, 11), (5, 6), (15, 6)):
        b.set(x, 2 if z in (3, 11) else 3, z, "glass_pane")
        if z in (3, 11):
            b.set(x, 1, z - 1 if z == 3 else z + 1, "spruce_trapdoor", facing="north" if z == 3 else "south",
                  half="top", open="false", powered="false", waterlogged="false")
    b.entrance(10, 1, 11, "north", wood="spruce", step="cobblestone")
    # Camino
    b.fill(14, 1, 7, 14, 11, 7, "bricks")
    b.set(14, 12, 7, "campfire", lit="true", signal_fire="false", facing="north", waterlogged="false")
    b.set(13, 1, 7, "campfire", lit="false", signal_fire="false", facing="west", waterlogged="false")
    # Arredi
    b.bed(7, 1, 5, "north", color="pink")
    b.set(7, 1, 9, "crafting_table")
    b.set(8, 1, 9, "smoker", facing="north", lit="false")
    b.chest(13, 1, 4, "west")
    b.table(10, 1, 6, "spruce")
    b.set(6, 1, 9, "potted_lily_of_the_valley")
    b.lantern(10, 4, 7, hanging=True)
    b.lantern(12, 1, 9)
    b.lantern(8, 6, 7)
    b.lantern(12, 6, 7)
    # Giardino
    b.walls(1, 0, 1, 19, 0, 19, "birch_fence")
    b.set(10, 0, 19, "birch_fence_gate", facing="south", in_wall="false", open="false", powered="false")
    for z in range(12, 19):
        b.set(10, 0, z, AIR)
        b.set(9, 0, z, AIR)
    path = [(10, z) for z in range(12, 19)] + [(9, z) for z in range(13, 19, 2)]
    flowers = ["poppy", "cornflower", "allium", "oxeye_daisy", "azure_bluet", "red_tulip", "pink_tulip",
               "white_tulip", "lily_of_the_valley"]
    for x in range(2, 19):
        for z in range(13, 19):
            if x in (8, 9, 10, 11):
                continue
            if (x + z) % 3 and b.rng.random() < 0.7:
                b.set(x, 0, z, b.rng.choice(flowers))
    for x in (3, 5, 15, 17):
        b.set(x, 0, 14, "rose_bush", half="lower")
        b.set(x, 1, 14, "rose_bush", half="upper")
        b.set(x, 0, 17, "peony", half="lower")
        b.set(x, 1, 17, "peony", half="upper")
    for x, z in path:
        b.set(x, 0, z, "dirt_path")
    b.tree(3, 0, 8, "oak", height=4, radius=2)
    b.set(17, 0, 8, "composter", level="0")
    b.fill(16, 0, 3, 18, 0, 5, "cobblestone")
    b.set(17, 0, 4, "water", level="0")
    b.set(17, 1, 4, AIR)
    for x, z in ((16, 3), (18, 3), (16, 5), (18, 5)):
        b.set(x, 1, z, "cobblestone_wall")
    for x, z in ((1, 1), (19, 1), (1, 19), (19, 19)):
        b.lantern(x, 1, z)
    return b


@template("red_barn", "Red Barn and Silo", "Fattorie e animali",
          "Grande fienile rosso con tetto a mansarda, finiture bianche, fienile soppalcato, box per animali "
          "e silo in mattoni con cupola.")
def red_barn():
    W, L = 29, 25
    b = Builder(W, 20, L, seed=64)
    RED, TRIM = "mangrove_planks", "birch_planks"
    x1, x2, z1, z2 = 2, 18, 2, 22
    b.fill(x1, 0, z1, x2, 0, z2, "stone_bricks")
    b.fill(x1 + 1, 0, z1 + 1, x2 - 1, 0, z2 - 1, "coarse_dirt")
    b.walls(x1, 1, z1, x2, 8, z2, RED)
    b.clear(x1 + 1, 1, z1 + 1, x2 - 1, 8, z2 - 1)
    for x, z in ((x1, z1), (x2, z1), (x1, z2), (x2, z2)):
        b.fill(x, 1, z, x, 8, z, TRIM)
    b.walls(x1, 8, z1, x2, 8, z2, TRIM)
    # Tetto a mansarda (gambrel): falde basse ripide, falde alte dolci
    profile = [(0, 9), (0, 10), (1, 11), (2, 12), (2, 13), (3, 13), (4, 14), (5, 14), (6, 15), (7, 15), (8, 15)]
    half = (x2 - x1) // 2
    roof_top = {}
    for dx, y in profile:
        roof_top[dx] = max(roof_top.get(dx, 0), y)
    for z in range(z1 - 1, z2 + 2):
        for dx, y in profile:
            if dx > half:
                continue
            for x, facing in ((x1 - 1 + dx, "east"), (x2 + 1 - dx, "west")):
                b.stair(x, y, z, "dark_oak", facing)
        b.set(x1 + half, 16, z, "dark_oak_slab", type="bottom", waterlogged="false")
    # timpani pieni e sottotetto vuoto, seguendo il profilo del tetto
    for x in range(x1, x2 + 1):
        dx = min(x - (x1 - 1), (x2 + 1) - x)
        h = roof_top.get(dx, 16)
        for y in range(9, h):
            for z in range(z1, z2 + 1):
                if z in (z1, z2):
                    b.set_if_empty(x, y, z, RED)
                elif b.get(x, y, z) is None:
                    b.set(x, y, z, AIR)
    # Porte del fienile con croce bianca
    for z, face in ((z2, "north"), (z1, "south")):
        b.clear(8, 1, z, 12, 5, z)
        for y in range(1, 7):
            b.set(7, y, z, TRIM)
            b.set(13, y, z, TRIM)
        b.fill(7, 6, z, 13, 6, z, TRIM)
    b.fill(8, 10, z2, 12, 12, z2, AIR)
    b.fill(9, 10, z2, 11, 11, z2, "hay_block", axis="y")
    # Soppalco del fieno e scala
    b.fill(x1 + 1, 6, z1 + 1, x2 - 1, 6, z1 + 8, "spruce_planks")
    b.fill(x1 + 1, 7, z1 + 1, x2 - 1, 7, z1 + 3, "hay_block", axis="y")
    b.ladder(x1 + 1, 1, 6, z1 + 9, "east")
    b.fill(x1 + 1, 7, z1 + 9, x1 + 1, 7, z1 + 9, AIR)
    # Box per animali
    for z in range(z1 + 10, z2 - 1, 4):
        b.fill(x1 + 1, 1, z, x1 + 5, 1, z, "spruce_fence")
        b.fill(x2 - 5, 1, z, x2 - 1, 1, z, "spruce_fence")
        b.set(x1 + 5, 1, z + 2, "spruce_fence_gate", facing="east", in_wall="false", open="false", powered="false")
        b.set(x2 - 5, 1, z + 2, "spruce_fence_gate", facing="west", in_wall="false", open="false", powered="false")
        for zz in (z + 1, z + 3):
            b.set(x1 + 5, 1, zz, "spruce_fence")
            b.set(x2 - 5, 1, zz, "spruce_fence")
        b.set(x1 + 1, 1, z + 1, "hay_block", axis="y")
        b.set(x2 - 1, 1, z + 1, "water_cauldron", level="3")
    for x, z in ((10, 6), (10, 12), (10, 18), (6, 4), (14, 4)):
        b.lantern(x, 1, z)
    for x, z in ((6, 5), (14, 5)):
        b.lantern(x, 7, z + 2)
    # Silo
    sx, sz = 23, 8
    b.cylinder(sx, sz, 0, 14, 3, "bricks", hollow=True)
    for y in range(1, 15):
        b.disk(sx, sz, y, 2, AIR)
    b.disk(sx, sz, 0, 2.5, "stone_bricks")
    b.dome(sx, 15, sz, 3, "waxed_weathered_cut_copper", hollow=False)
    for y in (4, 9):
        b.ring(sx, sz, y, 3, "white_concrete")
    b.door(sx - 3, 1, sz, "east", wood="spruce")
    b.set(sx - 4, 0, sz, "stone_brick_stairs", facing="east", half="bottom", shape="straight", waterlogged="false")
    b.lantern(sx + 1, 1, sz + 1)
    b.fill(sx, 1, sz, sx, 3, sz, "hay_block", axis="y")
    for x, z in ((20, 18), (25, 18), (25, 22)):
        b.set(x, 0, z, "oak_fence")
        b.lantern(x, 1, z)
    return b


@template("watermill", "Watermill", "Fattorie e animali",
          "Mulino ad acqua con grande ruota a pale sul canale, basamento in pietra, piano a graticcio, "
          "macina, sacchi di farina e soppalco.")
def watermill():
    W, L = 19, 17
    b = Builder(W, 16, L, seed=65)
    # Canale (acqua contenuta tra muri di pietra)
    b.fill(0, 0, 0, 3, 2, L - 1, "stone_bricks")
    b.fill(1, 1, 1, 2, 2, L - 2, "water", level="0")
    b.clear(1, 3, 0, 2, 12, L - 1)
    # Casa del mulino
    x1, x2, z1, z2 = 4, 15, 3, 13
    b.fill_random(x1, 0, z1, x2, 3, z2, [("cobblestone", 4), ("mossy_cobblestone", 1), ("stone_bricks", 2)])
    b.clear(x1 + 1, 1, z1 + 1, x2 - 1, 3, z2 - 1)
    b.fill(x1 + 1, 0, z1 + 1, x2 - 1, 0, z2 - 1, "spruce_planks")
    b.walls(x1, 4, z1, x2, 8, z2, "mushroom_stem")
    for x in range(x1, x2 + 1, 3):
        b.fill(x, 4, z1, x, 8, z1, "dark_oak_log", axis="y")
        b.fill(x, 4, z2, x, 8, z2, "dark_oak_log", axis="y")
    for z in range(z1, z2 + 1, 3):
        b.fill(x1, 4, z, x1, 8, z, "dark_oak_log", axis="y")
        b.fill(x2, 4, z, x2, 8, z, "dark_oak_log", axis="y")
    b.walls(x1, 4, z1, x2, 4, z2, "dark_oak_log", axis="x")
    b.fill(x1 + 1, 4, z1 + 1, x2 - 1, 4, z2 - 1, "spruce_planks")
    b.clear(x1 + 1, 5, z1 + 1, x2 - 1, 8, z2 - 1)
    b.gable_roof(x1, x2, z1, z2, 9, "dark_oak", "dark_oak_planks", axis="x", overhang=1)
    _windows(b, x1, x2, z1, z2, 6, "glass_pane", step=3)
    _windows(b, x1, x2, z1, z2, 2, "glass_pane", step=4)
    # Ruota ad acqua sul piano y-z, accanto al muro ovest
    wx, wy, wz, r = 3, 5, 8, 4.5
    for y in range(0, 11):
        for z in range(wz - 5, wz + 6):
            d = math.hypot(y - wy, z - wz)
            if r - 1 < d <= r + 0.3:
                b.set(wx, y, z, "spruce_planks")
            elif d <= r - 1 and (y == wy or z == wz or abs((y - wy) - (z - wz)) < 0.5 or abs((y - wy) + (z - wz)) < 0.5):
                b.set(wx, y, z, "spruce_fence")
            elif d <= r - 1 and y > 2:
                b.set(wx, y, z, AIR)
    b.set(wx, wy, wz, "dark_oak_log", axis="x")
    b.set(wx + 1, wy, wz, "dark_oak_log", axis="x")
    # Interni
    b.entrance(10, 1, z2, "north", wood="spruce", step="cobblestone")
    b.set(6, 1, 8, "grindstone", face="floor", facing="east")
    b.set(6, 1, 6, "stonecutter", facing="east")
    for x, z in ((13, 5), (13, 6), (12, 5)):
        b.set(x, 1, z, "barrel", facing="up", open="false")
    b.set(13, 2, 5, "white_wool")
    b.chest(12, 1, 11, "north")
    b.ladder(14, 1, 4, 11, "west")
    b.set(14, 4, 11, "ladder", facing="west", waterlogged="false")
    b.fill(15, 1, 11, 15, 4, 11, "cobblestone")
    b.bed(6, 5, 6, "south", color="brown")
    b.chest(13, 5, 5, "west")
    for x, y, z in ((9, 1, 6), (9, 1, 10), (9, 5, 8), (12, 5, 10)):
        b.lantern(x, y, z)
    b.lantern(8, 3, 8, hanging=True)
    return b


@template("stave_church", "Norwegian Stave Church", "Templi e luoghi sacri",
          "Chiesa norvegese in legno (stavkirke) ispirata a Borgund: tetti a scandole sovrapposti, galleria "
          "porticata, torretta a pagoda e teste di drago sui colmi.")
def stave_church():
    W, L = 17, 21
    b = Builder(W, 27, L, seed=66)
    c = 8
    # Galleria esterna (svalgang) con tettoia
    b.fill(2, 0, 3, 14, 0, 17, "cobblestone")
    b.fill(3, 0, 4, 13, 0, 16, "spruce_planks")
    for x in range(2, 15, 2):
        for z in (3, 17):
            b.fill(x, 1, z, x, 2, z, "dark_oak_fence")
    for z in range(3, 18, 2):
        for x in (2, 14):
            b.fill(x, 1, z, x, 2, z, "dark_oak_fence")
    for x in range(1, 16):
        b.stair(x, 3, 2, "dark_oak", "south")
        b.stair(x, 3, 18, "dark_oak", "north")
    for z in range(3, 18):
        b.stair(1, 3, z, "dark_oak", "east")
        b.stair(15, 3, z, "dark_oak", "west")
    # Navata
    b.room(4, 0, 5, 12, 8, 15, "dark_oak_planks", floor="spruce_planks", ceiling=False, corner="dark_oak_log", axis="y")
    b.fill(3, 4, 4, 13, 4, 16, "dark_oak_planks")
    b.clear(5, 1, 6, 11, 4, 14)
    b.clear(5, 4, 6, 11, 4, 14)
    b.gable_roof(4, 12, 5, 15, 9, "spruce", "dark_oak_planks", axis="z", overhang=1)
    # Livello intermedio e torretta a pagoda
    tiers = [(6, 10, 8, 12, 14), (7, 9, 9, 11, 18)]
    for x1, x2, z1, z2, y in tiers:
        b.fill(x1, y - 1, z1, x2, y + 1, z2, "dark_oak_planks")
        b.hip_roof(x1, x2, z1, z2, y + 2, "spruce", "dark_oak_planks", overhang=1)
    b.cone(c, 10, 21, 1.6, "dark_oak_planks", step=0.5)
    b.fill(c, 24, 10, c, 25, 10, "dark_oak_fence")
    b.set(c, 26, 10, "lightning_rod", facing="up", powered="false", waterlogged="false")
    # Teste di drago sui colmi
    for z, dz in ((4, -1), (16, 1)):
        top = 9 + 5
        b.set(c, top, z, "dark_oak_planks")
        b.set(c, top + 1, z + dz, "dark_oak_fence")
        b.set(c, top + 2, z + dz, "dark_oak_fence")
        b.set(c, top + 2, z + 2 * dz, "dark_oak_trapdoor", facing="north" if dz < 0 else "south", half="top",
              open="true", powered="false", waterlogged="false")
    # Portale e interni
    b.entrance(c, 1, 15, "north", wood="dark_oak", step=None)
    b.set(c, 0, 18, "stone_brick_stairs", facing="north", half="bottom", shape="straight", waterlogged="false")
    for x in (c - 1, c + 1):
        b.fill(x, 1, 15, x, 3, 15, "stripped_dark_oak_log", axis="y")
    for z in range(8, 13, 2):
        for x in (5, 6, 10, 11):
            b.stair(x, 1, z, "spruce", "south")
    b.set(c, 1, 6, "chiseled_stone_bricks")
    b.set(c, 2, 6, "gold_block")
    b.set(c - 1, 1, 6, "white_candle", candles="3", lit="true", waterlogged="false")
    b.set(c + 1, 1, 6, "white_candle", candles="3", lit="true", waterlogged="false")
    for z in (8, 13):
        b.lantern(5, 1, z)
        b.lantern(11, 1, z)
    b.set(4, 2, 10, "yellow_stained_glass_pane")
    b.set(12, 2, 10, "yellow_stained_glass_pane")
    for x, z in ((3, 4), (13, 4), (3, 16), (13, 16)):
        b.lantern(x, 1, z)
    return b


@template("victorian_mansion", "Victorian Mansion", "Case",
          "Villa vittoriana in stile 'painted lady': tre piani pastello con finiture bianche, torretta d'angolo "
          "con tetto conico, bovindo, veranda a colonne, comignoli e abbaini.")
def victorian_mansion():
    W, L = 23, 22
    b = Builder(W, 26, L, seed=67)
    WALL, TRIM = "light_blue_terracotta", "white_concrete"
    x1, x2, z1, z2 = 3, 18, 3, 16
    b.fill(x1 - 1, 0, z1 - 1, x2 + 1, 0, z2 + 1, "stone_bricks")
    for f, yb in enumerate((0, 5, 10)):
        b.room(x1, yb, z1, x2, yb + 5, z2, WALL, floor="dark_oak_planks" if yb else "polished_andesite",
               ceiling="dark_oak_planks")
        b.walls(x1, yb + 5, z1, x2, yb + 5, z2, TRIM)
        for x, z in ((x1, z1), (x2, z1), (x1, z2), (x2, z2)):
            b.fill(x, yb + 1, z, x, yb + 4, z, "quartz_pillar", axis="y")
        for x in range(x1 + 2, x2 - 1, 3):
            for z in (z1, z2):
                b.fill(x, yb + 2, z, x, yb + 3, z, "glass_pane")
        for z in range(z1 + 2, z2 - 1, 3):
            for x in (x1, x2):
                b.fill(x, yb + 2, z, x, yb + 3, z, "glass_pane")
        b.lantern(x1 + 3, yb + 4, z1 + 3, hanging=True)
        b.lantern(x2 - 3, yb + 4, z2 - 3, hanging=True)
        b.lantern(x1 + 3, yb + 4, z2 - 3, hanging=True)
        b.lantern(x2 - 3, yb + 4, z1 + 3, hanging=True)
    b.hip_roof(x1, x2, z1, z2, 16, "deepslate_tile", "deepslate_tiles", overhang=1)
    # Abbaini
    for x in (7, 14):
        b.fill(x - 1, 16, z2, x + 1, 18, z2, TRIM)
        b.set(x, 17, z2, "glass_pane")
        b.gable_roof(x - 1, x + 1, z2, z2, 19, "deepslate_tile", "deepslate_tiles", axis="z", overhang=0,
                     fill_attic=False)
    # Comignoli
    for x, z in ((5, 5), (16, 5)):
        b.fill(x, 16, z, x, 21, z, "bricks")
        b.set(x, 22, z, "brick_wall")
    # Torretta d'angolo
    tx, tz = x2, z2
    b.cylinder(tx, tz, 0, 18, 2.6, WALL, hollow=True)
    for y in range(1, 18):
        b.disk(tx, tz, y, 1.6, AIR)
    for y in (5, 10, 15):
        b.disk(tx, tz, y, 1.6, "dark_oak_planks")
        b.ring(tx, tz, y, 2.6, TRIM)
    for y in (2, 7, 12, 16):
        for x, z in ((tx + 2, tz), (tx, tz + 2)):
            b.set(x, y, z, "glass_pane")
            b.set(x, y + 1, z, "glass_pane")
    b.cone(tx, tz, 19, 3.2, "deepslate_tiles", step=0.55)
    b.set(tx, 25, tz, "lightning_rod", facing="up", powered="false", waterlogged="false")
    for y in (1, 6, 11, 16):
        b.lantern(tx - 1, y, tz - 1)
    # Bovindo sul fronte
    b.fill(7, 1, z2 + 1, 10, 3, z2 + 1, TRIM)
    b.fill(8, 2, z2 + 1, 9, 3, z2 + 1, "glass_pane")
    b.fill(7, 4, z2 + 1, 10, 4, z2 + 1, "smooth_quartz_slab", type="bottom", waterlogged="false")
    # Veranda
    for x in range(11, 18):
        b.set(x, 0, z2 + 1, "dark_oak_planks")
        b.set(x, 0, z2 + 2, "dark_oak_planks")
    for x in (11, 14, 17):
        b.fill(x, 1, z2 + 2, x, 3, z2 + 2, "birch_fence")
    b.fill(11, 4, z2 + 1, 17, 4, z2 + 2, "smooth_quartz_slab", type="bottom", waterlogged="false")
    b.entrance(14, 1, z2, "north", wood="dark_oak", step=None)
    b.stair(13, 0, z2 + 3, "dark_oak", "north")
    b.stair(14, 0, z2 + 3, "dark_oak", "north")
    b.stair(15, 0, z2 + 3, "dark_oak", "north")
    # Scala a pioli interna e arredi
    b.fill(x1 + 1, 1, z1 + 1, x1 + 1, 14, z1 + 1, "dark_oak_log", axis="y")
    b.ladder(x1 + 2, 1, 14, z1 + 1, "east")
    b.set(x1 + 2, 0, z1 + 1, "polished_andesite")
    b.lantern(10, 16, 10)
    b.lantern(10, 16, 7)
    b.bed(6, 11, 6, "north", color="purple")
    b.bed(12, 11, 6, "north", color="light_blue")
    b.chest(16, 11, 5, "west")
    b.fill(5, 6, 4, 9, 6, 4, "bookshelf")
    b.set(7, 6, 7, "lectern", facing="north", has_book="false", powered="false")
    b.set(16, 1, 5, "smoker", facing="west", lit="false")
    b.set(16, 1, 6, "crafting_table")
    b.table(10, 1, 9, "dark_oak")
    b.stair(9, 1, 9, "dark_oak", "west")
    b.stair(11, 1, 9, "dark_oak", "east")
    for x, z in ((1, 1), (21, 1), (1, 20), (21, 20)):
        b.set(x, 0, z, "dark_oak_fence")
        b.lantern(x, 1, z)
    return b


@template("chinese_pavilion", "Chinese Pavilion and Pond", "Piazze e decorazioni",
          "Padiglione cinese a colonne rosse con tetto a gronde ricurve su un isolotto, laghetto con ninfee, "
          "ponticello a zig-zag e lanterne di pietra.")
def chinese_pavilion():
    S = 23
    b = Builder(S, 13, S, seed=68)
    c = 11
    for x in range(S):
        for z in range(S):
            d = math.hypot(x - c, z - c)
            if d <= 10.4:
                b.set(x, 0, z, "smooth_stone" if d > 9.4 else "water", **({} if d > 9.4 else {"level": "0"}))
    b.octagon(c, c, 0, 4, "stone_bricks")
    b.octagon(c, c, 1, 4, "polished_andesite")
    for x, z in ((c - 3, c - 3), (c + 3, c - 3), (c - 3, c + 3), (c + 3, c + 3),
                 (c, c - 4), (c, c + 4), (c - 4, c), (c + 4, c)):
        b.fill(x, 2, z, x, 5, z, "stripped_mangrove_log", axis="y")
    b.fill(c - 4, 6, c - 4, c + 4, 6, c + 4, "dark_oak_planks")
    for x in range(c - 4, c + 5):
        b.set(x, 6, c - 4, "red_concrete")
        b.set(x, 6, c + 4, "red_concrete")
    for z in range(c - 4, c + 5):
        b.set(c - 4, 6, z, "red_concrete")
        b.set(c + 4, 6, z, "red_concrete")
    top = b.flared_roof(c - 4, c + 4, c - 4, c + 4, 7, "deepslate_tile", "deepslate_tiles", overhang=2)
    b.set(c, top + 1, c, "gold_block")
    b.set(c, 2, c, "chiseled_stone_bricks")
    b.lantern(c, 3, c)
    b.lantern(c, 5, c - 2, hanging=True)
    b.lantern(c, 5, c + 2, hanging=True)
    # Ponticello a zig-zag verso sud
    zig = [(c, z) for z in range(c + 5, c + 7)] + [(c + 1, c + 7), (c + 2, c + 7), (c + 2, c + 8), (c + 2, c + 9),
                                                    (c + 1, c + 9), (c, c + 9), (c, c + 10)]
    for x, z in zig:
        b.set(x, 1, z, "spruce_planks")
        b.set(x, 0, z, "stone_bricks")
    # Ninfee e lanterne di pietra sul bordo
    for x, z in ((6, 6), (16, 7), (7, 15), (15, 15), (5, 11), (17, 12)):
        if b.get(x, 0, z) == "minecraft:water":
            b.set(x, 1, z, "lily_pad")
    for a in range(0, 360, 60):
        x = c + int(round(10 * math.cos(math.radians(a + 30))))
        z = c + int(round(10 * math.sin(math.radians(a + 30))))
        b.set(x, 1, z, "stone_brick_wall")
        b.lantern(x, 2, z)
        b.slab(x, 3, z, "stone_brick")
    for x, z in ((1, 1), (21, 21)):
        b.tree(x, 0, z, "cherry", height=4, radius=2)
    return b


@template("city_gate", "Medieval City Gate", "Castelli e fortezze",
          "Porta di citta' medievale: grande arco con saracinesca, due torri merlate con tetti a punta, "
          "stendardi, mura con camminamento e scale interne.")
def city_gate():
    W, L = 37, 13
    b = Builder(W, 22, L, seed=69)
    c = W // 2
    # Mura laterali
    for x1, x2 in ((0, 11), (25, 36)):
        b.fill_random(x1, 0, 4, x2, 8, 8, [("stone_bricks", 6), ("mossy_stone_bricks", 1), ("cracked_stone_bricks", 1)])
        b.fill(x1, 9, 4, x2, 9, 8, "polished_andesite")
        for x in range(x1, x2 + 1):
            for z in (4, 8):
                if x % 2 == 0:
                    b.set(x, 10, z, "stone_bricks")
                else:
                    b.slab(x, 10, z, "stone_brick")
        for x in range(x1 + 2, x2, 6):
            b.lantern(x, 10, 6)
    # Torri
    for tx in (11, 25):
        b.fill_random(tx - 3, 0, 2, tx + 3, 15, 10, [("stone_bricks", 6), ("mossy_stone_bricks", 1), ("cracked_stone_bricks", 1)])
        b.clear(tx - 2, 1, 3, tx + 2, 14, 9)
        for y in (5, 10):
            b.fill(tx - 2, y, 3, tx + 2, y, 9, "spruce_planks")
        b.fill(tx - 3, 15, 2, tx + 3, 15, 10, "stone_bricks")
        for x in range(tx - 3, tx + 4):
            for z in (2, 10):
                if (x + z) % 2 == 0:
                    b.set(x, 16, z, "stone_bricks")
        for z in range(2, 11):
            for x in (tx - 3, tx + 3):
                if (x + z) % 2 == 0:
                    b.set(x, 16, z, "stone_bricks")
        b.pyramid(tx - 2, 3, tx + 2, 9, 16, "deepslate_tiles")
        for y in (3, 8, 12):
            b.set(tx, y, 2, AIR)
        b.fill(tx + 2, 1, 9, tx + 2, 10, 9, "stone_bricks")
        b.ladder(tx + 2, 1, 10, 8, "north")
        for y in (1, 6, 11):
            b.lantern(tx - 2, y, 4)
        # porta verso le mura al livello del camminamento
        side = -1 if tx < c else 1
        b.clear(tx + 3 * side, 10, 6, tx + 3 * side, 11, 6)
        # stendardi (lana) sulla facciata
        for x in (tx - 1, tx + 1):
            b.fill(x, 9, 1, x, 12, 1, "red_wool")
            b.set(x, 12, 1, "yellow_wool")
            b.set(x, 13, 1, "dark_oak_fence")
    # Corpo della porta con arco e saracinesca
    b.fill_random(14, 0, 3, 22, 12, 9, [("stone_bricks", 6), ("mossy_stone_bricks", 1), ("cracked_stone_bricks", 1)])
    b.carve_arch("x", 16, 20, 3, 9, 0, 8)
    b.fill(16, 0, 3, 20, 0, 9, "cobblestone")
    for x in range(16, 21):
        b.fill(x, 6, 3, x, 7, 3, "iron_bars")
    b.fill(14, 12, 3, 22, 12, 9, "stone_bricks")
    for x in range(14, 23, 2):
        b.set(x, 13, 3, "stone_bricks")
        b.set(x, 13, 9, "stone_bricks")
    b.lantern(18, 7, 6, hanging=True)
    b.set(18, 9, 6, "chiseled_stone_bricks")
    b.lantern(15, 13, 6)
    b.lantern(21, 13, 6)
    for tx in (11, 25):
        b.entrance(tx, 1, 10, "north", wood="spruce", step="stone_brick")
    return b


@template("alpine_chalet", "Alpine Chalet", "Case",
          "Chalet alpino: basamento in pietra, piano in legno con balcone avvolgente, tetto largo e spiovente "
          "con grandi gronde, camino e caminetto.")
def alpine_chalet():
    W, L = 19, 17
    b = Builder(W, 17, L, seed=70)
    x1, x2, z1, z2 = 3, 15, 3, 13
    b.fill_random(x1, 0, z1, x2, 4, z2, [("stone_bricks", 3), ("cobblestone", 2), ("andesite", 1)])
    b.clear(x1 + 1, 1, z1 + 1, x2 - 1, 3, z2 - 1)
    b.fill(x1 + 1, 0, z1 + 1, x2 - 1, 0, z2 - 1, "spruce_planks")
    b.fill(x1 + 1, 4, z1 + 1, x2 - 1, 4, z2 - 1, "spruce_planks")
    b.walls(x1, 5, z1, x2, 8, z2, "spruce_log", axis="y")
    for y in (5, 8):
        b.walls(x1, y, z1, x2, y, z2, "stripped_spruce_log", axis="x")
    b.clear(x1 + 1, 5, z1 + 1, x2 - 1, 9, z2 - 1)
    # Balcone avvolgente (largo 2, ringhiera sul bordo esterno)
    for d in (1, 2):
        for x in range(x1 - d, x2 + d + 1):
            for z in (z1 - d, z2 + d):
                b.slab(x, 4, z, "spruce", top=True)
        for z in range(z1 - d, z2 + d + 1):
            for x in (x1 - d, x2 + d):
                b.slab(x, 4, z, "spruce", top=True)
    b.walls(x1 - 2, 5, z1 - 2, x2 + 2, 5, z2 + 2, "spruce_fence")
    for x, z in ((x1 - 2, z1 - 2), (x2 + 2, z1 - 2), (x1 - 2, z2 + 2), (x2 + 2, z2 + 2)):
        b.lantern(x, 6, z)
    # Finestre con persiane
    for x in (6, 12):
        for z in (z1, z2):
            b.fill(x, 6, z, x, 7, z, "glass_pane")
        b.fill(x, 2, z1, x, 2, z1, "glass_pane")
    for z in (6, 10):
        for x in (x1, x2):
            b.fill(x, 6, z, x, 7, z, "glass_pane")
            b.set(x, 2, z, "glass_pane")
    b.entrance(9, 1, z2, "north", wood="spruce", step="stone_brick")
    b.door(9, 5, z2, "south", wood="spruce")
    # Tetto largo (colmo lungo Z)
    b.gable_roof(x1, x2, z1, z2, 9, "spruce", "spruce_planks", axis="z", overhang=2)
    b.fill(9, 14, z1 - 2, 9, 14, z2 + 2, "spruce_planks")
    # Camino e caminetto
    b.fill(x2 - 2, 1, z1 + 1, x2 - 2, 15, z1 + 1, "cobblestone")
    b.set(x2 - 2, 16, z1 + 1, "campfire", lit="true", signal_fire="false", facing="north", waterlogged="false")
    b.set(x2 - 3, 1, z1 + 1, "campfire", lit="false", signal_fire="false", facing="west", waterlogged="false")
    # Interni
    b.ladder(x1 + 1, 1, 4, z1 + 2, "east")
    b.set(x1 + 1, 4, z1 + 2, "ladder", facing="east", waterlogged="false")
    b.table(8, 1, 7, "spruce")
    b.stair(7, 1, 7, "spruce", "west")
    b.stair(9, 1, 7, "spruce", "east")
    b.set(x2 - 1, 1, z2 - 1, "smoker", facing="west", lit="false")
    b.set(x2 - 1, 1, z2 - 2, "barrel", facing="up", open="false")
    b.bed(5, 5, 6, "north", color="red")
    b.bed(7, 5, 6, "north", color="red")
    b.chest(13, 5, 5, "west")
    b.set(12, 5, 11, "bookshelf")
    for x, y, z in ((6, 1, 11), (12, 1, 6), (6, 5, 10), (12, 5, 9)):
        b.lantern(x, y, z)
    b.lantern(9, 3, 7, hanging=True)
    for x, z in ((1, 1), (17, 15)):
        b.tree(x, 0, z, "spruce", height=6, radius=2)
    return b
