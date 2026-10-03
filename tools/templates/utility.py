"""Costruzioni funzionali: fattorie, stanze da lavoro, decorazioni."""
import math

from template_builder import Builder, template


@template("villager_trading_hall", "Villager Trading Hall", "Utility",
          "Sala degli scambi con 20 celle per villici, ognuna con il proprio blocco professione (porta i tuoi villici).")
def villager_trading_hall():
    W, L = 23, 11
    b = Builder(W, 13, L)
    b.room(0, 0, 0, W - 1, 5, L - 1, "stone_bricks", floor="polished_andesite", ceiling="stone_bricks")
    b.gable_roof(0, W - 1, 0, L - 1, 5, "spruce", "spruce_planks", axis="x", overhang=1)
    for x in range(0, W, 4):
        b.fill(x, 1, 0, x, 4, 0, "spruce_log", axis="y")
        b.fill(x, 1, L - 1, x, 4, L - 1, "spruce_log", axis="y")
    stations = ["lectern", "composter", "barrel", "smoker", "blast_furnace", "cartography_table",
                "fletching_table", "smithing_table", "stonecutter", "loom", "grindstone", "brewing_stand",
                "cauldron", "lectern", "composter", "barrel", "smoker", "cartography_table", "stonecutter", "loom"]
    props = {
        "lectern": {"has_book": "false", "powered": "false"}, "barrel": {"open": "false"},
        "smoker": {"lit": "false"}, "blast_furnace": {"lit": "false"}, "composter": {"level": "0"},
        "grindstone": {"face": "floor"},
    }
    facing_prop = {"lectern", "barrel", "smoker", "blast_furnace", "stonecutter", "loom", "grindstone"}
    i = 0
    for side, (z_cell, z_station, z_sep_from, facing) in enumerate(((1, 2, 1, "south"), (L - 2, L - 3, L - 3, "north"))):
        for x in range(2, W - 2, 2):
            st = stations[i % len(stations)]
            i += 1
            p = dict(props.get(st, {}))
            if st in facing_prop:
                p["facing"] = facing
            b.set(x, 1, z_station, st, **p)
            b.clear(x, 1, z_cell, x, 2, z_cell)
            b.fill(x, 3, min(z_cell, z_station), x, 3, max(z_cell, z_station), "stone_bricks")
            for sep in (x - 1, x + 1):
                b.fill(sep, 1, min(z_cell, z_station), sep, 3, max(z_cell, z_station), "glass")
    b.clear(1, 1, 3, W - 2, 4, L - 4)
    b.entrance(0, 1, L // 2, "east", wood="spruce", step=None)
    b.entrance(W - 1, 1, L // 2, "west", wood="spruce", step=None)
    for x in range(3, W - 2, 4):
        b.set(x, 5, L // 2, "sea_lantern")
    for x in range(2, W - 2, 2):
        b.set(x, 4, 1, "sea_lantern")
        b.set(x, 4, L - 2, "sea_lantern")
    return b


@template("sugar_cane_farm", "Sugar Cane Farm", "Farm",
          "Piantagione di canna da zucchero: file di sabbia irrigate, recinto con cancello e lampioni.")
def sugar_cane_farm():
    W, L = 13, 13
    b = Builder(W, 4, L)
    b.walls(0, 0, 0, W - 1, 0, L - 1, "oak_log", axis="y")
    for z in range(1, L - 3):
        row = (z - 1) % 3
        for x in range(1, W - 1):
            if row == 1:
                b.set(x, 0, z, "water", level="0")
            else:
                b.set(x, 0, z, "sand")
                b.set(x, 1, z, "sugar_cane", age="0")
                b.set(x, 2, z, "sugar_cane", age="0")
    b.walls(0, 1, 0, W - 1, 1, L - 1, "oak_fence")
    b.set(W // 2, 1, L - 1, "oak_fence_gate", facing="south", in_wall="false", open="false", powered="false")
    b.clear(1, 1, L - 3, W - 2, 2, L - 2)
    b.fill(1, 0, L - 3, W - 2, 0, L - 2, "dirt_path")
    for x, z in ((0, 0), (W - 1, 0), (0, L - 1), (W - 1, L - 1)):
        b.set(x, 2, z, "torch")
    b.chest(1, 1, L - 2, "east")
    return b


@template("enchanting_room", "Enchanting Room", "Utility",
          "Stanza dell'incantamento al livello massimo (15 librerie), con leggio, incudine, cassa e tappeto.")
def enchanting_room():
    S = 9
    b = Builder(S, 11, S)
    b.room(0, 0, 0, S - 1, 5, S - 1, "dark_oak_planks", floor="dark_oak_planks", ceiling="dark_oak_planks",
           corner="dark_oak_log", axis="y")
    b.walls(0, 1, 0, S - 1, 1, S - 1, "cobblestone")
    b.hip_roof(0, S - 1, 0, S - 1, 5, "deepslate_tile", "deepslate_tiles", overhang=1)
    for i in (2, S - 3):
        for x, z in ((i, 0), (0, i), (S - 1, i)):
            b.fill(x, 3, z, x, 3, z, "purple_stained_glass_pane")
    c = S // 2
    b.set(c, 1, c, "enchanting_table")
    for x in range(c - 2, c + 3):
        for z in range(c - 2, c + 3):
            if max(abs(x - c), abs(z - c)) == 2 and not (x == c and z == c + 2):
                b.set(x, 1, z, "bookshelf")
                b.set(x, 2, z, "bookshelf")
    for x in range(c - 1, c + 2):
        for z in range(c - 1, c + 2):
            if (x, z) != (c, c):
                b.set(x, 1, z, "red_carpet")
    b.entrance(c, 1, S - 1, "north", wood="dark_oak", step="cobblestone")
    b.set(1, 1, 1, "lectern", facing="south", has_book="false", powered="false")
    b.set(S - 2, 1, 1, "anvil", facing="east")
    b.chest(1, 1, S - 2, "east")
    b.set(S - 2, 1, S - 2, "bookshelf")
    for x, z in ((1, c), (S - 2, c), (c, 1)):
        b.lantern(x, 1, z)
    b.lantern(c, 4, c, hanging=True)
    return b


@template("beacon_pyramid", "Beacon Pyramid", "Utility",
          "Piramide completa a quattro livelli in ferro e oro con faro attivo sulla cima.")
def beacon_pyramid():
    b = Builder(9, 6, 9)
    for level in range(4):
        a, z = level, 8 - level
        mat = "iron_block" if level % 2 == 0 else "gold_block"
        b.fill(a, level, a, z, level, z, mat)
    b.set(4, 4, 4, "beacon")
    for x, z in ((0, 0), (8, 0), (0, 8), (8, 8)):
        b.lantern(x, 1, z)
    return b


@template("fountain_plaza", "Fountain Plaza", "Decoration",
          "Piazza con fontana a tre vasche, panchine, aiuole fiorite e lampioni.")
def fountain_plaza():
    S = 17
    b = Builder(S, 8, S, seed=51)
    c = S // 2
    for x in range(S):
        for z in range(S):
            d = math.hypot(x - c, z - c)
            if d <= 8.3:
                b.set(x, 0, z, "polished_andesite" if (x + z) % 2 else "smooth_stone")
    b.ring(c, c, 1, 5, "stone_bricks", thickness=1)
    b.disk(c, c, 0, 4, "stone_bricks")
    b.disk(c, c, 1, 4, "water", level="0")
    b.cylinder(c, c, 1, 3, 1, "stone_bricks")
    b.disk(c, c, 4, 2.5, "stone_bricks")
    b.ring(c, c, 5, 2.5, "stone_brick_wall")
    b.disk(c, c, 5, 1.6, "water", level="0")
    b.set(c, 5, c, "stone_bricks")
    b.set(c, 6, c, "stone_brick_wall")
    b.lantern(c, 7, c)
    # Panchine e aiuole
    flowers = ["poppy", "dandelion", "cornflower", "allium", "red_tulip", "oxeye_daisy"]
    for a in (45, 135, 225, 315):
        x = c + int(round(7 * math.cos(math.radians(a))))
        z = c + int(round(7 * math.sin(math.radians(a))))
        b.set(x, 0, z, "grass_block")
        b.set(x, 1, z, b.rng.choice(flowers))
        for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            if math.hypot(x + dx - c, z + dz - c) <= 8.3:
                b.set(x + dx, 0, z + dz, "grass_block")
                b.set(x + dx, 1, z + dz, b.rng.choice(flowers))
    for a in (0, 90, 180, 270):
        x = c + int(round(7 * math.cos(math.radians(a))))
        z = c + int(round(7 * math.sin(math.radians(a))))
        b.set(x, 1, z, "stone_brick_wall")
        b.set(x, 2, z, "stone_brick_wall")
        b.lantern(x, 3, z)
    for a, f in ((22, "east"), (158, "west"), (202, "west"), (338, "east")):
        x = c + int(round(6.5 * math.cos(math.radians(a))))
        z = c + int(round(6.5 * math.sin(math.radians(a))))
        b.stair(x, 1, z, "spruce", "north" if z > c else "south")
    return b


@template("zen_garden", "Zen Garden", "Decoration",
          "Giardino zen giapponese con ghiaia, laghetto con ninfee, ponticello, ciliegi in fiore, bambu' e lanterne di pietra.")
def zen_garden():
    S = 19
    b = Builder(S, 9, S, seed=52)
    b.fill(0, 0, 0, S - 1, 0, S - 1, "gravel")
    for x in range(S):
        for z in range(S):
            if x in (0, S - 1) or z in (0, S - 1):
                b.set(x, 0, z, "moss_block")
    # Laghetto
    for x in range(3, 11):
        for z in range(9, 16):
            if ((x - 7) / 4.2) ** 2 + ((z - 12) / 3.4) ** 2 <= 1:
                b.set(x, 0, z, "water", level="0")
    for x, z in ((5, 11), (8, 13), (6, 14)):
        b.set(x, 1, z, "lily_pad")
    # Ponticello
    for x in range(5, 10):
        b.slab(x, 1, 12, "dark_oak")
    # Sentiero di pietre
    for x, z in ((9, 1), (9, 3), (10, 5), (11, 7), (12, 9), (12, 11), (13, 13), (14, 15)):
        b.set(x, 0, z, "polished_andesite")
    # Ciliegi
    for x, z in ((3, 4), (15, 6), (15, 14)):
        b.set(x, 0, z, "grass_block")
        for y in range(1, 5):
            b.set(x, y, z, "cherry_log", axis="y")
        b.ellipsoid(x, 5, z, 2.6, 1.6, 2.6, "cherry_leaves", upper_only=False, persistent="true", distance="1",
                    waterlogged="false")
    # Bambu'
    for x, z in ((1, 13), (1, 14), (2, 15), (1, 16), (2, 17)):
        b.set(x, 0, z, "grass_block")
        for y in range(1, 5):
            b.set(x, y, z, "bamboo", age="0", leaves="small" if y == 4 else "none", stage="0")
    # Lanterne di pietra
    for x, z in ((6, 3), (13, 3), (11, 16), (16, 10)):
        b.set(x, 1, z, "stone_brick_wall")
        b.lantern(x, 2, z)
        b.slab(x, 3, z, "stone_brick")
    return b


@template("greenhouse", "Greenhouse", "Farm",
          "Serra in vetro con struttura in quercia: aiuole coltivate e irrigate, fiori, compostiera e banco.")
def greenhouse():
    W, L = 11, 15
    b = Builder(W, 12, L)
    b.fill(0, 0, 0, W - 1, 0, L - 1, "stone_bricks")
    b.walls(0, 1, 0, W - 1, 4, L - 1, "glass")
    for z in range(0, L, 3):
        b.fill(0, 1, z, 0, 4, z, "oak_log", axis="y")
        b.fill(W - 1, 1, z, W - 1, 4, z, "oak_log", axis="y")
    b.gable_roof(0, W - 1, 0, L - 1, 5, "oak", "oak_planks", axis="z", overhang=0)
    for (x, y, z), (n, p) in list(b.cells.items()):
        if y >= 5 and n.endswith("oak_stairs") and z % 3:
            b.set(x, y, z, "glass")
        if y >= 6 and n == "minecraft:oak_planks" and z % 3:
            b.set(x, y, z, "glass")
    b.clear(1, 1, 1, W - 2, 4, L - 2)
    crops = ["wheat", "carrots", "potatoes", "beetroots"]
    for i, x0 in enumerate((1, W - 4)):
        b.fill(x0, 0, 2, x0 + 2, 0, L - 3, "farmland", moisture="7")
        b.fill(x0 + 1, 0, 2, x0 + 1, 0, L - 3, "water", level="0")
        for z in range(2, L - 2):
            for x in (x0, x0 + 2):
                cr = crops[(z + i) % 4]
                b.set(x, 1, z, cr, age="3" if cr == "beetroots" else "7")
            b.slab(x0 + 1, 1, z, "oak")
    b.entrance(W // 2, 1, L - 1, "north", wood="oak", step="stone_brick")
    b.set(4, 1, 1, "composter", level="0")
    b.chest(6, 1, 1, "south")
    b.set(5, 1, 1, "potted_poppy")
    for z in (3, 8, 12):
        b.lantern(W // 2, 1, z)
    return b


@template("horse_stable", "Horse Stable", "Farm",
          "Scuderia in abete con sei box, cancelli, fieno, abbeveratoi, cassa per selle e tetto a capanna.")
def horse_stable():
    W, L = 15, 13
    b = Builder(W, 14, L)
    b.room(0, 0, 0, W - 1, 5, L - 1, "spruce_planks", floor="spruce_planks", ceiling=False,
           corner="spruce_log", axis="y")
    b.gable_roof(0, W - 1, 0, L - 1, 5, "dark_oak", "dark_oak_planks", axis="x", overhang=1)
    c = L // 2
    for x0 in (1, 5, 9):
        for side, z_back, z_gate in ((0, 1, 4), (1, L - 2, L - 5)):
            zs = range(1, 5) if side == 0 else range(L - 5, L - 1)
            for z in zs:
                b.set(x0 + 3 if x0 + 3 < W - 1 else x0 - 1, 1, z, "spruce_fence")
            gx = x0 + 1
            b.set(gx, 1, z_gate, "spruce_fence_gate", facing="south" if side == 0 else "north", in_wall="false",
                  open="false", powered="false")
            for x in range(x0, x0 + 3):
                if x != gx:
                    b.set(x, 1, z_gate, "spruce_fence")
            b.set(x0, 1, z_back, "hay_block", axis="y")
            b.set(x0 + 2, 1, z_back, "water_cauldron", level="3")
    b.clear(1, 1, c - 1, W - 2, 4, c + 1)
    b.entrance(0, 1, c, "east", wood="spruce", step=None)
    b.entrance(W - 1, 1, c, "west", wood="spruce", step=None)
    b.chest(1, 1, c + 1, "east")
    for x in (2, 6, 10):
        b.lantern(x, 1, c - 1)
    for x in range(2, W - 2, 4):
        b.lantern(x, 1, 2)
        b.lantern(x, 1, L - 3)
    return b
