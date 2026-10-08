"""
Automatic farms (Minecraft 1.21+), built on mechanisms that work in survival:

- sugar cane / bamboo: an observer at the third block of each plant fires a piston at the second
  block (the observer never sees the piston head, so there is no clock); the drops fall into a
  water stream or on the dirt, where a hopper minecart below collects them through the block;
- melons / pumpkins: the observer watches the stem (it changes when a fruit grows and when the
  fruit goes), the piston destroys the fruit; hopper minecarts under the fruit spots collect it;
- wool: a sheep eats the grass under it (its wool grows back), the observer next to the grass
  fires a dispenser with shears;
- super smelter: hopper lines spread ores and fuel over a row of furnaces, the smelted items go
  down into a chest;
- lava: pointed dripstone under a lava pool fills the cauldrons below by itself;
- cactus: cacti on sand break when they grow next to a fence, the pieces fall on hoppers.

Each farm comes in a few sizes and styles. The redstone of every farm is checked by the tests
(tests/test_auto_farms.py) with the circuit simulator: the right pistons and dispensers fire, only
when they should, and nothing oscillates.
"""
from template_builder import Builder, template

THEMES = {
    "pietra": dict(wall="stone_bricks", trim="polished_andesite", post="spruce_log", slab="stone_brick_slab",
                   stairs="stone_brick_stairs", sign="spruce"),
    "legno": dict(wall="spruce_planks", trim="stripped_spruce_log", post="spruce_log", slab="spruce_slab",
                  stairs="spruce_stairs", sign="spruce"),
    "moderno": dict(wall="white_concrete", trim="light_gray_concrete", post="quartz_pillar", slab="smooth_quartz_slab",
                    stairs="smooth_quartz_stairs", sign="birch"),
}


def _posts(b, x1, z1, x2, z2, y1, y2, t):
    for x, z in ((x1, z1), (x2, z1), (x1, z2), (x2, z2)):
        b.fill(x, y1, z, x, y2, z, t["post"], axis="y")


def _output_chest(b, x, z, facing, items_label):
    """Collection chest at ground level with a lantern next to it."""
    b.chest(x, 0, z, facing)
    b.set(x, 1, z, "air")
    b.set(x, 2, z, "air")
    b.contents(x, 0, z, [], name=items_label)


# ---------------------------------------------------------------------------
# Sugar cane / bamboo
# ---------------------------------------------------------------------------

def plant_farm(plant, length=8, modules=1, theme="pietra"):
    """
    Rows of 'length' plants along x, two rows per module (one each side of a water channel).
    Module section (z): wall+dust | piston/observer | plant | channel | plant | piston/observer | wall+dust.
    Heights: hoppers y0, rails y1, dirt y2, plant y3 (h1), y4 (h2, broken by the piston), y5 (h3, seen
    by the observer), glass roof y6.
    """
    t = THEMES[theme]
    N = length
    assert N <= 8, "the water stream reaches 7 blocks from its source"
    # modules 8 apart: a full column between two dust lines keeps every row on its own circuit
    W, L, H = N + 4, 8 * modules - 1, 7
    b = Builder(W, H, L)
    for z in range(L):
        b.fill(0, 0, z, 0, 5, z, t["wall"])
        b.fill(N + 1, 0, z, N + 1, 5, z, t["wall"])
    for m in range(modules):
        z0 = 8 * m
        if m:
            b.fill(1, 0, z0 - 1, N, 5, z0 - 1, t["wall"])
        for x in range(1, N + 1):
            for zw in (z0, z0 + 6):
                b.fill(x, 0, zw, x, 4, zw, t["wall"])
                b.set(x, 5, zw, "redstone_wire")
            for zp, face, zd in ((z0 + 1, "south", z0 + 2), (z0 + 5, "north", z0 + 4)):
                b.fill(x, 0, zp, x, 3, zp, t["wall"])
                b.set(x, 4, zp, "piston", facing=face, extended="false")
                b.set(x, 5, zp, "observer", facing=face, powered="false")
                b.set(x, 0, zd, "hopper", facing="east", enabled="true")
                b.set(x, 1, zd, "rail", shape="east_west", waterlogged="false")
                b.entity(x, 1, zd, "hopper_minecart")
                b.set(x, 2, zd, "dirt")
                if plant == "bamboo":
                    b.set(x, 3, zd, "bamboo", age="0", leaves="none", stage="0")
                else:
                    b.set(x, 3, zd, "sugar_cane", age="0")
            b.set(x, 0, z0 + 3, t["wall"])
            b.set(x, 1, z0 + 3, t["wall"])
            # the channel: source at x=1, flowing towards the hopper at x=N
            b.set(x, 2, z0 + 3, "water", level=str(min(7, x - 1)))
        b.set(N, 1, z0 + 3, "hopper", facing="down", enabled="true")
        b.set(N, 0, z0 + 3, "hopper", facing="east", enabled="true")
        b.set(N + 1, 0, z0 + 2, "hopper", facing="south", enabled="true")
        b.set(N + 1, 0, z0 + 4, "hopper", facing="north", enabled="true")
        b.set(N + 1, 0, z0 + 3, "hopper", facing="east", enabled="true")
        _output_chest(b, N + 2, z0 + 3, "east", "Canna da zucchero" if plant != "bamboo" else "Bambu'")
        b.lantern(N + 2, 0, z0 + 1)
    b.fill(0, 6, 0, N + 1, 6, L - 1, "glass")
    _posts(b, 0, 0, N + 1, L - 1, 0, 6, t)
    b.technical_area(1, 0, 0, N + 1, 6, L - 1)
    return b


# a water stream carries items 7 blocks from its source: rows are at most 8 long, bigger farms add modules
_PLANT_SIZES = (("", 8, 1, "pietra"), ("_grande", 8, 3, "legno"), ("_moderna", 8, 2, "moderno"))
for _suffix, _n, _m, _th in _PLANT_SIZES:
    for _plant, _title, _cat in (("sugar_cane", "Farm automatica di canna da zucchero", "Farm automatiche"),
                                 ("bamboo", "Farm automatica di bambu'", "Farm automatiche")):
        def _make(plant=_plant, n=_n, m=_m, th=_th):
            return plant_farm(plant, n, m, th)
        _rows = 2 * _m
        template(f"auto_{_plant}_farm{_suffix}", f"{_title} ({_rows * _n} piante)", _cat,
                 f"{_rows} file da {_n}: osservatori e pistoni rompono la pianta quando arriva al terzo blocco, "
                 "canale d'acqua e carrelli tramoggia sotto la terra raccolgono tutto nella cassa.")(_make)


# ---------------------------------------------------------------------------
# Melons / pumpkins
# ---------------------------------------------------------------------------

def fruit_farm(fruit, length=9, modules=1, theme="pietra"):
    """
    One row of stems per module with a fruit spot on each side.
    Section (z): wall | piston | fruit spot | stems | fruit spot | piston | wall.
    Heights: hoppers y0, rails y1, dirt/farmland y2, fruit/stem y3, observer over the stems and glass
    over the fruit spots y4, a carpet of redstone dust y5 (power from the observers down to the
    pistons), glass roof y6. A water source every 8 blocks of the stem row keeps the farmland wet.
    """
    t = THEMES[theme]
    N = length
    W, L, H = N + 4, 6 * modules + 1, 7
    b = Builder(W, H, L)
    waters = set(range(5, N + 1, 8))
    for z in range(L):
        b.fill(0, 0, z, 0, 5, z, t["wall"])
        b.fill(N + 1, 0, z, N + 1, 5, z, t["wall"])
    for m in range(modules):
        z0 = 6 * m
        for x in range(1, N + 1):
            for zw in (z0, z0 + 6):
                b.fill(x, 0, zw, x, 5, zw, t["wall"])
            for zp, face in ((z0 + 1, "south"), (z0 + 5, "north")):
                b.fill(x, 0, zp, x, 2, zp, t["wall"])
                b.set(x, 3, zp, "piston", facing=face, extended="false")
                b.set(x, 4, zp, t["wall"])
                b.set(x, 5, zp, "redstone_wire")
            for zf in (z0 + 2, z0 + 4):
                b.set(x, 0, zf, "hopper", facing="east", enabled="true")
                b.set(x, 1, zf, "rail", shape="east_west", waterlogged="false")
                b.entity(x, 1, zf, "hopper_minecart")
                b.set(x, 2, zf, "dirt")
                b.set(x, 4, zf, "glass")
                b.set(x, 5, zf, "redstone_wire")
            zs = z0 + 3
            b.set(x, 0, zs, t["wall"])
            b.set(x, 1, zs, t["wall"])
            if x in waters:
                b.set(x, 2, zs, "water", level="0")
                b.set(x, 4, zs, "glass")
            else:
                b.set(x, 2, zs, "farmland", moisture="7")
                b.set(x, 3, zs, f"{fruit}_stem", age="7")
                b.set(x, 4, zs, "observer", facing="down", powered="false")
            b.set(x, 5, zs, "redstone_wire")
        for zf, face in ((z0 + 2, "south"), (z0 + 4, "north")):
            b.set(N + 1, 0, zf, "hopper", facing=face, enabled="true")
        b.set(N + 1, 0, z0 + 3, "hopper", facing="east", enabled="true")
        _output_chest(b, N + 2, z0 + 3, "east", "Meloni" if fruit == "melon" else "Zucche")
        b.lantern(N + 2, 0, z0 + 1)
    b.fill(0, 6, 0, N + 1, 6, L - 1, "glass")
    _posts(b, 0, 0, N + 1, L - 1, 0, 6, t)
    b.technical_area(1, 0, 0, N + 1, 6, L - 1)
    return b


_FRUIT_SIZES = (("", 9, 1, "pietra"), ("_grande", 13, 2, "legno"), ("_moderna", 9, 2, "moderno"))
for _suffix, _n, _m, _th in _FRUIT_SIZES:
    for _fruit, _title in (("melon", "Farm automatica di meloni"), ("pumpkin", "Farm automatica di zucche")):
        def _make(fruit=_fruit, n=_n, m=_m, th=_th):
            return fruit_farm(fruit, n, m, th)
        _stems = _m * (_n - len(range(5, _n + 1, 8)))
        template(f"auto_{_fruit}_farm{_suffix}", f"{_title} ({_stems} gambi)", "Farm automatiche",
                 f"{_stems} gambi con un posto per il frutto da ogni lato: l'osservatore sopra il gambo "
                 "fa scattare i pistoni appena cresce un frutto, i carrelli tramoggia sotto la terra lo "
                 "raccolgono e lo portano nella cassa.")(_make)


# ---------------------------------------------------------------------------
# Wool
# ---------------------------------------------------------------------------

_WOOL_COLORS = (0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15)


def wool_farm(sheep=8, theme="legno", colors=None):
    """
    A row of 1x1 pens, one sheep each (x even), on a grass block. Section (z):
    z0 glass back wall; z1 the pen (hopper y0, rail+hopper minecart y1, grass y2, sheep y3-y4);
    z2 observer on the grass (y2) and dispenser with shears facing the sheep (y3);
    z3 the block the observer powers (y2) with a dust under the open sky that powers the dispenser.
    Between the pens grass under glass makes the eaten grass grow back.
    """
    from nbt_codec import TAG_Byte
    t = THEMES[theme]
    W, L, H = 2 * sheep + 3, 5, 6
    b = Builder(W, H, L)
    colors = colors or (0,)
    for x in range(0, 2 * sheep + 1):
        pen = x % 2 == 1
        b.set(x, 0, 1, "hopper", facing="east", enabled="true")
        b.set(x, 1, 1, "rail", shape="east_west", waterlogged="false")
        b.set(x, 2, 1, "grass_block")
        b.set(x, 2, 0, "grass_block")
        b.fill(x, 0, 0, x, 1, 0, t["wall"])
        b.fill(x, 3, 0, x, 4, 0, "glass")
        b.fill(x, 0, 2, x, 1, 2, t["wall"])
        b.fill(x, 0, 3, x, 1, 3, t["wall"])
        if pen:
            k = x // 2
            b.entity(x, 1, 1, "hopper_minecart")
            b.mob(x, 3, 1, "sheep", 180.0, Color=TAG_Byte(colors[k % len(colors)]), Sheared=TAG_Byte(0))
            b.set(x, 2, 2, "observer", facing="north", powered="false")
            b.set(x, 3, 2, "dispenser", facing="north", triggered="false")
            b.contents(x, 3, 2, [("shears", 1)] * 9, name="Cesoie")
            b.set(x, 4, 2, "glass")
            b.set(x, 2, 3, t["wall"])
            b.set(x, 3, 3, "redstone_wire")
        else:
            b.fill(x, 3, 1, x, 4, 1, "glass")
            b.fill(x, 2, 2, x, 4, 2, "glass")
            b.set(x, 2, 3, t["wall"])
    b.fill(0, 5, 0, 2 * sheep, 5, 2, "glass")
    # collection: the hopper line ends in a chest at the east end
    b.set(2 * sheep + 1, 0, 1, "hopper", facing="east", enabled="true")
    b.fill(2 * sheep + 1, 1, 0, 2 * sheep + 1, 5, 3, t["wall"])
    b.fill(2 * sheep + 1, 0, 0, 2 * sheep + 1, 0, 0, t["wall"])
    b.fill(2 * sheep + 1, 0, 2, 2 * sheep + 1, 0, 3, t["wall"])
    _output_chest(b, 2 * sheep + 2, 1, "east", "Lana")
    b.lantern(2 * sheep + 2, 0, 3)
    b.technical_area(0, 0, 0, 2 * sheep + 1, 5, 3)
    return b


for _name, _n, _th, _cols, _title in (
        ("auto_wool_farm", 8, "legno", (0,), "Farm automatica di lana bianca (8 pecore)"),
        ("auto_wool_farm_colori", 16, "moderno", _WOOL_COLORS, "Farm automatica di lana colorata (16 pecore)"),
        ("auto_wool_farm_grande", 24, "pietra", (0, 15, 8, 7, 12), "Farm automatica di lana (24 pecore)")):
    def _make(n=_n, th=_th, cols=_cols):
        return wool_farm(n, th, cols)
    template(_name, _title, "Farm automatiche",
             f"{_n} pecore, ognuna nel suo recinto su un blocco d'erba: quando la mangia (e la lana "
             "ricresce) l'osservatore fa scattare un dispenser con le cesoie; i carrelli tramoggia sotto "
             "l'erba portano la lana nella cassa.")(_make)


# ---------------------------------------------------------------------------
# Super smelter
# ---------------------------------------------------------------------------

def super_smelter(furnaces=8, kind="furnace", theme="pietra"):
    """
    Furnaces in a row (x 1..N, z1). Ores: chest (x0, y4) -> hopper (x0, y3) -> hopper line y3 above the
    furnaces; under each line hopper a hopper facing down into the furnace. Fuel: chest (x0, y3, z0)
    -> hopper line y2 at z0, under each a hopper (y1) facing into the back of the furnace. Output:
    hoppers under the furnaces (y0) towards the chest at the east end.
    """
    t = THEMES[theme]
    N = furnaces
    W, L, H = N + 3, 4, 6
    b = Builder(W, H, L)
    _posts(b, 0, 0, N + 1, 1, 0, 4, t)          # first: the machinery below replaces them where needed
    for x in range(1, N + 1):
        b.set(x, 0, 1, "hopper", facing="east", enabled="true")
        b.set(x, 1, 1, kind, facing="south", lit="false")
        b.set(x, 2, 1, "hopper", facing="down", enabled="true")
        b.set(x, 3, 1, "hopper", facing="east", enabled="true")
        b.set(x, 1, 0, "hopper", facing="south", enabled="true")
        b.set(x, 2, 0, "hopper", facing="east", enabled="true")
        b.set(x, 0, 0, t["wall"])
        b.set(x, 3, 0, t["wall"])
        b.set(x, 4, 1, t["slab"], type="bottom", waterlogged="false")
        b.set(x, 4, 0, t["slab"], type="bottom", waterlogged="false")
    # feeders at the west end
    b.set(0, 3, 1, "hopper", facing="east", enabled="true")
    b.chest(0, 4, 1, "west")
    b.contents(0, 4, 1, [], name="Minerali da fondere")
    b.set(0, 2, 0, "hopper", facing="east", enabled="true")
    b.chest(0, 3, 0, "west")
    b.contents(0, 3, 0, [("coal", 64), ("coal", 64)], name="Combustibile")
    b.fill(0, 0, 0, 0, 1, 1, t["wall"])
    b.set(0, 2, 1, t["wall"])
    # the last hoppers of the two lines end against a wall block; the output goes to the chest in front
    b.fill(N + 1, 1, 0, N + 1, 3, 1, t["wall"])
    b.set(N + 1, 0, 0, t["wall"])
    b.set(N + 1, 0, 1, "hopper", facing="south", enabled="true")
    _output_chest(b, N + 1, 2, "south", "Prodotti")
    b.lantern(0, 0, 2)
    b.lantern(N + 2, 0, 2)
    b.technical_area(0, 0, 0, N + 1, 4, 1)
    return b


for _name, _n, _kind, _th, _title in (
        ("auto_super_smelter", 8, "furnace", "pietra", "Super fornace automatica (8 fornaci)"),
        ("auto_super_smelter_grande", 16, "furnace", "moderno", "Super fornace automatica (16 fornaci)"),
        ("auto_blast_smelter", 8, "blast_furnace", "pietra", "Altoforno automatico (8 altoforni, minerali)"),
        ("auto_smoker_kitchen", 6, "smoker", "legno", "Cucina automatica (6 affumicatori, cibo)")):
    def _make(n=_n, kind=_kind, th=_th):
        return super_smelter(n, kind, th)
    template(_name, _title, "Farm automatiche",
             f"Metti i materiali nella cassa in alto a sinistra e il combustibile in quella sotto: le "
             f"tramogge li distribuiscono su {_n} {'fornaci' if _kind == 'furnace' else 'blocchi'} e "
             "raccolgono tutto il prodotto nella cassa in fondo.")(_make)


# ---------------------------------------------------------------------------
# Lava (pointed dripstone under a lava pool)
# ---------------------------------------------------------------------------

def lava_farm(size=3, theme="pietra"):
    """
    size x size cauldrons (every other block, with walkways between). Over each one, at y2, a pointed
    dripstone hanging from the stone layer (y3) under a lava pool (y4) closed by a roof (y5).
    """
    t = THEMES[theme]
    S = 2 * size + 1
    W = L = S + 2
    b = Builder(W, 6, L)
    b.walls(0, 0, 0, W - 1, 2, L - 1, t["wall"])
    b.fill(0, 3, 0, W - 1, 3, L - 1, "stone")
    b.walls(0, 4, 0, W - 1, 4, L - 1, t["wall"])
    b.fill(1, 4, 1, W - 2, 4, L - 2, "lava", level="0")
    b.fill(0, 5, 0, W - 1, 5, L - 1, t["wall"])
    for i in range(size):
        for j in range(size):
            x, z = 2 + 2 * i, 2 + 2 * j
            b.set(x, 0, z, "cauldron")
            b.set(x, 2, z, "pointed_dripstone", thickness="tip", vertical_direction="down", waterlogged="false")
    # door and lights
    b.door(W // 2, 0, 0, "north", wood="spruce")
    for x in range(1, W - 1, 4):
        for z in range(1, L - 1, 4):
            b.lantern(x, 2, z, hanging=True)            # at the crossings of the walkways
    b.lantern(1, 0, 1)
    b.lantern(W - 2, 0, L - 2)
    return b


for _name, _n, _th in (("auto_lava_farm", 3, "pietra"), ("auto_lava_farm_grande", 5, "pietra")):
    def _make(n=_n, th=_th):
        return lava_farm(n, th)
    template(_name, f"Farm di lava ({_n * _n} calderoni)", "Farm automatiche",
             f"{_n * _n} calderoni sotto spuntoni di dripstone appesi a uno strato di pietra con la lava "
             "sopra: i calderoni si riempiono di lava da soli, basta raccoglierla col secchio.")(_make)


# ---------------------------------------------------------------------------
# Cactus (no redstone)
# ---------------------------------------------------------------------------

def cactus_farm(size=7, theme="pietra"):
    """
    Cacti on sand in a checkerboard over a floor of hoppers; the second block of each cactus grows
    next to a fence and breaks, the piece falls on the hoppers, which carry it to the chest.
    """
    t = THEMES[theme]
    S = size
    W, L, H = S + 3, S + 2, 5
    b = Builder(W, H, L)
    # serpentine hopper floor: even rows go east, odd rows west, each row ends going south
    for z in range(1, S + 1):
        for x in range(1, S + 1):
            east = (z % 2 == 1)
            last = x == (S if east else 1)
            facing = "south" if last else ("east" if east else "west")
            b.set(x, 0, z, "hopper", facing=facing, enabled="true")
            inner = 2 <= x <= S - 1 and 2 <= z <= S - 1     # a cactus next to the glass walls would break
            if (x + z) % 2 == 0 and inner:
                b.set(x, 1, z, "sand")
                b.set(x, 2, z, "cactus", age="0")
            elif (x + z) % 2 == 1:
                b.set(x, 3, z, "oak_fence")
    b.walls(0, 0, 0, S + 1, 3, S + 1, "glass")
    b.walls(0, 0, 0, S + 1, 0, S + 1, t["wall"])
    b.fill(0, 4, 0, S + 1, 4, S + 1, "glass")
    _posts(b, 0, 0, S + 1, S + 1, 0, 4, t)
    # the last row ends south into a hopper through the wall and the chest outside
    end_x = S if S % 2 == 1 else 1
    b.set(end_x, 0, S + 1, "hopper", facing="south", enabled="true")
    b.set(end_x, 1, S + 1, t["wall"])
    return b, end_x


def _cactus(size, th):
    b, end_x = cactus_farm(size, th)
    # grow the structure by one row to hold the chest
    nb = Builder(b.w, b.h, b.l + 1)
    nb.cells.update(b.cells)
    nb.block_nbt.update(b.block_nbt)
    _output_chest(nb, end_x, b.l, "south", "Cactus")
    nb.lantern(end_x + 1 if end_x + 1 < nb.w else end_x - 1, 0, b.l)
    nb.technical_area(1, 0, 1, b.w - 3, 4, b.l - 2)
    return nb


for _name, _n, _th in (("auto_cactus_farm", 7, "pietra"), ("auto_cactus_farm_grande", 11, "legno")):
    def _make(n=_n, th=_th):
        return _cactus(n, th)
    template(_name, f"Farm di cactus ({(_n * _n + 1) // 2} cactus)", "Farm automatiche",
             "Cactus sulla sabbia a scacchiera sopra un pavimento di tramogge: crescendo toccano una "
             "staccionata e si spezzano, i pezzi cadono nelle tramogge e finiscono nella cassa. "
             "Nessuna redstone.")(_make)
