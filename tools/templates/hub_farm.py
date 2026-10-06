"""
Hub sotterraneo con magazzino automatico e iron farm (vedi docs/PROMPT_ARCHITETTO.md).

Convenzioni redstone (verificate nel resto del progetto):
- comparatore: 'facing' = lato d'ingresso, l'uscita e' dal lato opposto;
- torcia a muro: 'facing' = direzione verso cui punta, e' attaccata al blocco dal lato opposto;
- tramoggia: 'facing' = beccuccio; 'enabled=false' quando e' bloccata (alimentata).
I circuiti sono verificati da tests/test_hub_farm.py con il simulatore analogico (AnalogSim).
"""
import math

import blockinfo as bi
from template_builder import Builder, AIR, template

SQ3 = math.sqrt(3)
ALL6 = ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1))


def fill_roof_cavity(b, x1, x2, z1, z2, y, block):
    """
    The hollow inside a hip roof is a sealed dark attic where mobs can spawn: fill it.
    Only cells enclosed by the roof (some roof block above them in the same column) are filled.
    """
    for x in range(x1, x2 + 1):
        for z in range(z1, z2 + 1):
            above = [yy for yy in range(y, b.h) if b.get(x, yy, z) not in (None, AIR)]
            if not above:
                continue
            for yy in range(y, max(above)):
                if b.get(x, yy, z) in (None, AIR):
                    b.set(x, yy, z, block)


def seal_underground(b, top, filler=(("deepslate", 6), ("tuff", 2), ("cobbled_deepslate", 1))):
    """
    Underground builds: every open cell (air, stairs, water...) below 'top' gets solid neighbours where
    the template would leave the terrain as it is. A cave or an aquifer next to the build can then
    neither flood it nor let mobs in.
    """
    names = [f[0] for f in filler]
    weights = [f[1] for f in filler]
    open_cells = [p for p, (n, _) in b.cells.items() if p[1] < top and not bi.is_full_solid(bi.short(n))]
    for x, y, z in open_cells:
        for dx, dy, dz in ALL6:
            q = (x + dx, y + dy, z + dz)
            if q[1] >= top or not b.inside(*q) or q in b.cells:
                continue
            b.set(*q, b.rng.choices(names, weights)[0])


# ===========================================================================
# Multi-Item Sorter (schema anti-overflow tipo ImpulseSV)
# ===========================================================================
#
# Fetta vista dall'alto (x verso est, z verso sud), livelli dal basso:
#   y0     L = tramoggia bloccata -> barile (sud); S = blocco sotto la terza polvere; T = torcia sul lato di S
#   y0+1   F = tramoggia filtro (beccuccio verso un blocco pieno, ovest: non spinge in L);
#          C = comparatore (confronto) che legge F; tre polveri; vetro sopra T
#   y0+2   H = catena di tramogge verso est
#
#   z: zf-2   polvere1  polvere2
#      zf-1   C         polvere3 (su S)
#      zf     F/L       vetro/T
#      zf+1   barile
#
# F contiene 41 oggetti bersaglio + 4 riempitivi rinominati: segnale 2, che si spegne prima di arrivare a S
# (2 -> 1 -> 0). Al 42esimo oggetto il segnale e' 3: la terza polvere ha forza 1, alimenta S, la torcia si
# spegne, L si sblocca e preleva un oggetto da F, che torna a 41. Se il barile e' pieno F si riempie, smette
# di prelevare da H e gli oggetti proseguono lungo la catena fino al barile di troppo pieno (anti-overflow).

FILTER_COUNT = 41
FILLER = ("stick", "Filtro")          # bastoni rinominati: non si impilano mai con quelli normali
SLICE_STEP = 3


def sorter_slice(b, x, zf, y0, item, label, filler_block="deepslate_tiles"):
    """One sorter slice at column x; returns the positions of its parts (for the tests)."""
    L, F = (x, y0, zf), (x, y0 + 1, zf)
    C = (x, y0 + 1, zf - 1)
    S, T = (x + 1, y0, zf - 1), (x + 1, y0, zf)
    dust = [(x, y0 + 1, zf - 2), (x + 1, y0 + 1, zf - 2), (x + 1, y0 + 1, zf - 1)]
    barrel = (x, y0, zf + 1)
    for p in ((x, y0, zf - 2), (x + 1, y0, zf - 2), (x, y0, zf - 1), S):   # supports of dust and comparator
        b.set(*p, filler_block)
    b.set(*L, "hopper", facing="south", enabled="false")
    b.set(*F, "hopper", facing="west", enabled="true")
    b.contents(*F, [(item, FILTER_COUNT)] + [(FILLER[0], 1, FILLER[1])] * 4)
    b.set(*C, "comparator", facing="south", mode="compare", powered="false")
    for p in dust:
        b.set(*p, "redstone_wire", power="0")
    b.set(*T, "redstone_wall_torch", facing="south", lit="true")
    b.set(x + 1, y0 + 1, zf, "glass")
    b.set(*barrel, "barrel", facing="south", open="false")
    b.contents(*barrel, [], name=label)
    return {"L": L, "F": F, "C": C, "S": S, "T": T, "dust": dust, "barrel": barrel, "item": item}


SORTED_ITEMS = [
    ("iron_ingot", "Ferro"), ("gold_ingot", "Oro"), ("copper_ingot", "Rame"), ("redstone", "Redstone"),
    ("coal", "Carbone"), ("lapis_lazuli", "Lapislazzuli"), ("cobblestone", "Pietrisco"),
    ("cobbled_deepslate", "Ardesia"), ("poppy", "Papaveri (iron farm)"),
]


# ===========================================================================
# Hub sotterraneo
# ===========================================================================

HUB_G = 22                    # strati sotto il terreno: il pavimento della sala e' 22 blocchi sotto
HUB_W, HUB_L = 39, 57
HUB_C = (19, 31)              # centro della sala esagonale
HUB_R = 15                    # raggio (centro -> vertice); apotema ~13
HUB_ZF = 9                    # riga delle tramogge filtro dello smistatore
HUB_SLICE_X = [8 + SLICE_STEP * k for k in range(len(SORTED_ITEMS))]
HUB_ELEVATOR = (19, 50)


def hex_norm(dx, dz, r=HUB_R):
    """0 at the centre, 1 on the walls of a flat-topped hexagon (vertices east and west)."""
    a = r * SQ3 / 2.0
    return max(abs(dz) / a, (SQ3 * abs(dx) + abs(dz)) / (SQ3 * r))


def _hub_hall(b):
    cx, cz = HUB_C
    r = HUB_R
    vertex_dirs = [(math.cos(math.radians(a)), math.sin(math.radians(a))) for a in range(0, 360, 60)]
    for x in range(cx - r - 3, cx + r + 4):
        for z in range(cz - r, cz + r + 1):
            dx, dz = x - cx, z - cz
            hn = hex_norm(dx, dz)
            if hn > 1 + 2.1 / r:
                continue
            dist = math.hypot(dx, dz)
            rib = dist > 1.5 and any(abs(dx * vz - dz * vx) < 0.75 and dx * vx + dz * vz > 0
                                     for vx, vz in vertex_dirs)
            if hn <= 1.0:
                # floor: concentric bands, worn near the walls
                if hn < 0.13:
                    floor = "chiseled_polished_blackstone" if (dx + dz) % 2 == 0 else "polished_blackstone"
                elif rib:
                    floor = "polished_blackstone_bricks"
                elif int(hn * 7) % 2 == 0:
                    floor = "polished_deepslate"
                else:
                    floor = "deepslate_tiles" if b.rng.random() > 0.12 else "cracked_deepslate_tiles"
                if hn > 0.9 and b.rng.random() < 0.3:
                    floor = "cobbled_deepslate"
                b.set(x, 0, z, floor)
                ceiling = 10 + int(round(8 * math.sqrt(max(0.0, 1 - hn * hn))))
                for y in range(1, ceiling + 1):
                    b.set(x, y, z, AIR)
                b.set(x, ceiling + 1, z, "polished_blackstone_bricks" if rib else
                      b.rng.choice(["deepslate_tiles", "deepslate_tiles", "deepslate_bricks", "tuff_bricks"]))
                b.set(x, ceiling + 2, z, "deepslate_bricks")
                if rib:                                       # ribs hang one block below the vault
                    b.set(x, ceiling, z, "polished_blackstone_bricks")
            else:
                b.set(x, 0, z, "cobbled_deepslate")
                for y in range(1, 13):
                    if y <= 1:
                        block = "polished_deepslate"
                    elif y <= 7:
                        block = "deepslate_bricks" if b.rng.random() > 0.15 else "cracked_deepslate_bricks"
                    else:
                        block = "tuff_bricks" if b.rng.random() > 0.2 else "polished_tuff"
                    b.set(x, y, z, block)
                b.set(x, 13, z, "deepslate_tiles")
    # plinth, pilasters at the six vertices and cornice: three layers of relief
    for x in range(cx - r, cx + r + 1):
        for z in range(cz - r, cz + r + 1):
            dx, dz = x - cx, z - cz
            hn = hex_norm(dx, dz)
            if not (0.9 < hn <= 1.0):
                continue
            ang = math.degrees(math.atan2(dz, dx)) % 60
            near_vertex = min(ang, 60 - ang) < 9
            if near_vertex:
                for y in range(1, 11):
                    b.set(x, y, z, "polished_blackstone_bricks" if y % 4 else "chiseled_polished_blackstone")
            else:
                b.set(x, 10, z, "polished_deepslate")
    # crown of lanterns on the cornice ledge (otherwise a dark shelf where mobs could spawn)
    for i in range(12):
        a = math.radians(15 + 30 * i)
        for rr in [k / 4.0 for k in range(40, 64)]:
            lx, lz = cx + int(round(rr * math.cos(a))), cz + int(round(rr * math.sin(a)))
            if 0.9 < hex_norm(lx - cx, lz - cz) <= 1.0:
                b.lantern(lx, 11, lz)
                break
    # lamp posts in front of the four diagonal vertex pilasters (east and west are the ports)
    for vx, vz in vertex_dirs:
        if abs(vz) < 0.1:
            continue
        lx, lz = cx + int(round(vx * (r - 4))), cz + int(round(vz * (r - 4)))
        b.set(lx, 1, lz, "polished_blackstone_wall")
        b.set(lx, 2, lz, "polished_blackstone_wall")
        b.lantern(lx, 3, lz)


def _hub_center(b):
    cx, cz = HUB_C
    # chandelier hanging from the apex of the dome
    for y in range(12, 18):
        b.set(cx, y, cz, "chain", axis="y")
    b.set(cx, 11, cz, "polished_blackstone")
    for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        b.set(cx + dx, 11, cz + dz, "polished_blackstone_wall")
        b.set(cx + 2 * dx, 11, cz + 2 * dz, "polished_blackstone_brick_slab", type="top", waterlogged="false")
        b.lantern(cx + 2 * dx, 10, cz + 2 * dz, hanging=True)
    b.lantern(cx, 10, cz, hanging=True)
    # six lamp posts around the medallion
    for i in range(6):
        a = math.radians(30 + 60 * i)
        x, z = cx + int(round(4 * math.cos(a))), cz + int(round(4 * math.sin(a)))
        b.set(x, 1, z, "polished_blackstone_wall")
        b.set(x, 2, z, "polished_blackstone_wall")
        b.lantern(x, 3, z, soul=i % 2 == 1)


def _station(b, x, z, kind):
    """Work stations in the hall (on a low dais of polished deepslate)."""
    for dx in range(-2, 3):
        for dz in range(-2, 3):
            b.set(x + dx, 0, z + dz, "polished_deepslate")
    b.set(x, 0, z, "waxed_oxidized_cut_copper")
    if kind == "incanti":
        b.set(x, 1, z, "enchanting_table")
        for dx in range(-2, 3):
            for dz in range(-2, 3):
                if max(abs(dx), abs(dz)) == 2 and not (dz == 2 and dx in (-1, 0, 1)):
                    b.set(x + dx, 1, z + dz, "bookshelf")
                    b.set(x + dx, 2, z + dz, "bookshelf" if abs(dx) != 2 or abs(dz) != 2 else "polished_deepslate")
        for dx, dz in ((-2, -2), (2, -2)):
            b.lantern(x + dx, 3, z + dz)
        b.lantern(x - 2, 1, z + 2)
        b.lantern(x + 2, 1, z + 2)
    elif kind == "alchimia":
        b.set(x, 1, z, "brewing_stand", has_bottle_0="false", has_bottle_1="false", has_bottle_2="false")
        b.set(x - 1, 1, z - 1, "water_cauldron", level=3)
        b.set(x + 1, 1, z - 1, "barrel", facing="up", open="false")
        b.set(x - 1, 1, z + 1, "polished_blackstone_wall")
        b.lantern(x - 1, 2, z + 1, soul=True)
        b.set(x + 1, 1, z + 1, "polished_blackstone_wall")
        b.lantern(x + 1, 2, z + 1)
    elif kind == "officina":
        b.set(x - 1, 1, z - 1, "crafting_table")
        b.set(x, 1, z - 1, "smithing_table")
        b.set(x + 1, 1, z - 1, "anvil", facing="east")
        b.set(x - 1, 1, z + 1, "stonecutter", facing="south")
        b.set(x + 1, 1, z + 1, "grindstone", face="floor", facing="south")
        b.set(x, 1, z + 1, "polished_blackstone_wall")
        b.lantern(x, 2, z + 1)
    elif kind == "fonderia":
        b.set(x - 1, 1, z - 1, "blast_furnace", facing="south", lit="false")
        b.set(x, 1, z - 1, "blast_furnace", facing="south", lit="false")
        b.set(x + 1, 1, z - 1, "smoker", facing="south", lit="false")
        b.set(x - 1, 1, z + 1, "furnace", facing="north", lit="false")
        b.set(x + 1, 1, z + 1, "polished_blackstone_wall")
        b.lantern(x + 1, 2, z + 1)
        for y in range(2, 9):                                  # copper flue towards the vault
            b.set(x, y, z - 1, "waxed_weathered_cut_copper" if y % 3 else "waxed_oxidized_copper")


def _hub_gallery(b):
    """Storage gallery north of the hall: barrels in the wall, the sorter hidden behind it."""
    x1, x2 = 2, 36
    # gallery body
    b.fill(1, 0, 5, 37, 9, 17, "deepslate_bricks")
    for x in range(x1, x2 + 1):
        for z in range(11, 17):
            b.set(x, 0, z, "polished_deepslate" if z in (11, 16) else
                  ("deepslate_tiles" if (x + z) % 3 else "polished_blackstone_bricks"))
            for y in range(1, 8):
                b.set(x, y, z, AIR)
            b.set(x, 8, z, "deepslate_tiles")
    # mechanism block behind the barrels: solid, the components replace single cells
    b.fill(1, 0, 6, 37, 5, 10, "deepslate_tiles")
    slices = []
    for (item, label), x in zip(SORTED_ITEMS, HUB_SLICE_X):
        slices.append(sorter_slice(b, x, HUB_ZF, 1, item, label))
    # hopper chain (flows east), overflow at the end
    for x in range(4, 35):
        b.set(x, 3, HUB_ZF, "hopper", facing="east", enabled="true")
    b.set(35, 3, HUB_ZF, "hopper", facing="down", enabled="true")
    b.set(35, 2, HUB_ZF, "hopper", facing="down", enabled="true")
    b.set(35, 1, HUB_ZF, "hopper", facing="south", enabled="true")
    # a barrel opens even with a solid block on top (a chest would stay shut under the wall)
    b.set(35, 1, 10, "barrel", facing="south", open="false")
    b.contents(35, 1, 10, [], name="Troppo pieno")
    # wall face above the barrels
    for x in range(x1, x2 + 1):
        if x >= 8:
            b.set(x, 2, 10, "chiseled_deepslate" if x in HUB_SLICE_X else "polished_deepslate")
        for y in range(3, 8):
            b.set(x, y, 10, "tuff_bricks" if y == 5 else "deepslate_bricks")
    # pilasters and transverse ribs between the barrels
    for x in [sx + 2 for sx in HUB_SLICE_X]:
        for y in range(1, 7):
            b.set(x, y, 11, "polished_deepslate" if y < 6 else "chiseled_deepslate")
        b.stair(x, 6, 12, "polished_deepslate", "north", top=True)
        for z in range(11, 17):
            b.set(x, 7, z, "polished_blackstone_bricks")
    for sx in HUB_SLICE_X:
        b.lantern(sx + 1, 7, 13, hanging=True)
    b.lantern(4, 7, 12, hanging=True)
    # input dais at the west end: floor chest feeding the chain + water drop-off trench
    for x in range(2, 8):
        for z in range(9, 15):
            for y in range(1, 4):
                if z > HUB_ZF:                                # the z = 9 row holds the hopper chain
                    b.set(x, y, z, "deepslate_bricks")
            b.set(x, 4, z, "polished_deepslate" if (x + z) % 2 else "deepslate_tiles")
            for y in range(5, 8):
                b.set(x, y, z, AIR)
    for x in range(2, 8):
        b.set(x, 4, 8, "polished_blackstone_bricks")         # back wall of the dais
    b.chest(4, 4, HUB_ZF, "south")
    b.contents(4, 4, HUB_ZF, [], name="Deposito")
    b.set(6, 4, 13, "water", level=0)
    for i, z in enumerate((12, 11, 10, 9), start=1):
        b.set(6, 4, z, "water", level=i)
    b.set(6, 4, 14, "polished_blackstone_bricks")
    for x in range(2, 8):                                     # dais railing (4-block drop)
        b.set(x, 5, 14, "polished_blackstone_wall")
    b.set(7, 5, 11, "polished_blackstone_wall")
    b.lantern(2, 6, 14)
    b.lantern(7, 6, 14)
    for i, x in enumerate((8, 9, 10)):                        # steps down to the gallery floor
        for z in (12, 13, 14):
            b.stair(x, 3 - i, z, "polished_deepslate", "west")
            for y in range(1, 3 - i):
                b.set(x, y, z, "deepslate_bricks")
    b.technical_area(1, 0, 6, 37, 3, HUB_ZF)
    return slices


def _hub_openings(b):
    cx, cz = HUB_C
    # big pointed arch between the gallery and the hall
    b.carve_arch("x", cx - 6, cx + 6, cz - 15, cz - 13, 1, 8, pointed=True)
    for x in range(cx - 6, cx + 7):
        for z in range(cz - 15, cz - 12):
            b.set(x, 0, z, "polished_deepslate")
    # south doorway and corridor to the stair tower
    b.carve_arch("x", cx - 1, cx + 1, cz + 13, cz + 15, 1, 5, pointed=True)
    for z in range(cz + 13, cz + 16):
        for x in range(cx - 1, cx + 2):
            b.set(x, 0, z, "polished_deepslate")
    # east and west ports: corridor stubs for future modules (dig through the cracked wall)
    for side in (-1, 1):
        x_from = cx + side * (HUB_R - 1)
        x_to = 1 if side < 0 else HUB_W - 2
        for x in range(min(x_from, x_to), max(x_from, x_to) + 1):
            for z in range(cz - 1, cz + 2):
                b.set(x, 0, z, "polished_deepslate")
                for y in range(1, 5):
                    b.set(x, y, z, AIR)
                b.set(x, 5, z, "deepslate_tiles")
            for z in (cz - 2, cz + 2):
                for y in range(0, 6):
                    b.set(x, y, z, "deepslate_bricks")
        end = 0 if side < 0 else HUB_W - 1
        for z in range(cz - 2, cz + 3):
            for y in range(0, 6):
                b.set(end, y, z, "cracked_deepslate_bricks")
        b.set(end, 2, cz, "chiseled_deepslate")
        b.lantern(x_to, 1, cz - 1)


def _hub_tower(b):
    """Spiral stair around a soul-sand bubble column, from the hall up to the kiosk."""
    ex, ez = HUB_ELEVATOR
    top = HUB_G                                   # standing level of the kiosk floor
    for x in range(ex - 3, ex + 4):
        for z in range(ez - 3, ez + 4):
            d = max(abs(x - ex), abs(z - ez))
            b.set(x, 0, z, "polished_deepslate")
            for y in range(1, top):
                if d == 3:
                    b.set(x, y, z, "deepslate_bricks" if (y // 4) % 2 else "polished_deepslate")
                elif d == 2:
                    b.set(x, y, z, AIR)
    # corridor from the hall
    for z in range(HUB_C[1] + 15, ez - 2):
        b.set(ex, 0, z, "polished_deepslate")
        for y in (1, 2):
            b.set(ex, y, z, AIR)
    for y in (1, 2):
        b.set(ex, y, ez - 3, AIR)
    # ring of 16 cells, clockwise from just east of the entrance
    ring = [(ex + 1, ez - 2), (ex + 2, ez - 2)] + [(ex + 2, ez + k) for k in (-1, 0, 1, 2)] + \
           [(ex + k, ez + 2) for k in (1, 0, -1, -2)] + [(ex - 2, ez + k) for k in (1, 0, -1, -2)] + \
           [(ex - 1, ez - 2), (ex, ez - 2)]
    steps = top - 1                                # stair blocks at y = 1 .. top-1
    for i in range(steps):
        x, z = ring[i % 16]
        nx, nz = ring[(i + 1) % 16]
        facing = {(1, 0): "east", (-1, 0): "west", (0, 1): "south", (0, -1): "north"}[(nx - x, nz - z)]
        y = 1 + i
        b.stair(x, y, z, "polished_deepslate", facing)
        if y - 1 >= 1:
            b.stair(x, y - 1, z, "polished_deepslate", facing, top=True)
    # lights in the outer wall every few steps
    for i in range(2, steps, 4):
        x, z = ring[i % 16]
        ox = x + (1 if x - ex == 2 else -1 if x - ex == -2 else 0)
        oz = z + (1 if z - ez == 2 else -1 if z - ez == -2 else 0)
        b.set(ox, 2 + i, oz, "ochre_froglight")
    b.set(ex + 3, 3, ez - 3, "ochre_froglight")
    # elevator core: glass tube, soul sand, bubble column, doors at the bottom (north) and top (south)
    for x in range(ex - 1, ex + 2):
        for z in range(ez - 1, ez + 2):
            if (x, z) != (ex, ez):
                for y in range(1, top + 2):
                    b.set(x, y, z, "glass")
                b.set(x, top + 2, z, "polished_blackstone_bricks")
    b.set(ex, 0, ez, "soul_sand")
    for y in range(1, top + 1):
        b.set(ex, y, ez, "bubble_column", drag="false")
    b.set(ex, top + 1, ez, AIR)
    b.set(ex, top + 2, ez, "polished_blackstone_bricks")
    b.door(ex, 1, ez - 1, "south", wood="dark_oak")
    b.door(ex, top, ez + 1, "north", wood="dark_oak")
    # door at the foot of the stair: mobs wandering down from the kiosk do not reach the hall
    b.door(ex, 1, ez - 3, "north", wood="dark_oak")
    return ring


def _hub_kiosk(b):
    ex, ez = HUB_ELEVATOR
    g = HUB_G
    x1, x2, z1, z2 = ex - 5, ex + 5, ez - 5, ez + 5
    # floor (replaces the terrain surface), with the stair well left open where the steps arrive
    for x in range(x1, x2 + 1):
        for z in range(z1, z2 + 1):
            if abs(x - ex) <= 1 and abs(z - ez) <= 1:
                continue                                    # elevator core (glass tube and water)
            edge = x in (x1, x2) or z in (z1, z2)
            b.set(x, g - 1, z, "deepslate_bricks" if edge else
                  ("polished_deepslate" if (x + z) % 2 else "deepslate_tiles"))
    # the last steps (y = g-4 .. g-2) come up through the floor: head room for whoever walks down
    for x, z in ((ex + 2, ez - 2), (ex + 2, ez - 1), (ex + 2, ez)):
        b.set(x, g - 1, z, AIR)
    b.stair(ex + 2, g - 1, ez + 1, "polished_deepslate", "south")
    for x, z in ((ex + 3, ez - 2), (ex + 3, ez - 1), (ex + 3, ez), (ex + 2, ez - 3), (ex + 1, ez - 2),
                 (ex + 3, ez - 3)):
        b.set(x, g, z, "polished_blackstone_wall")
    # four pillars and pointed arches
    for px in (x1 + 1, x2 - 1):
        for pz in (z1 + 1, z2 - 1):
            for y in range(g, g + 7):
                b.set(px, y, pz, "polished_blackstone_bricks" if y % 3 else "chiseled_polished_blackstone")
            b.set(px, g + 7, pz, "chiseled_polished_blackstone")
    for y in range(g + 5, g + 8):
        for x in range(x1 + 1, x2):
            for z in (z1 + 1, z2 - 1):
                b.set(x, y, z, "deepslate_bricks")
        for z in range(z1 + 1, z2):
            for x in (x1 + 1, x2 - 1):
                b.set(x, y, z, "deepslate_bricks")
    b.carve_arch("x", x1 + 2, x2 - 2, z1 + 1, z1 + 1, g, 6, pointed=True)
    b.carve_arch("x", x1 + 2, x2 - 2, z2 - 1, z2 - 1, g, 6, pointed=True)
    b.carve_arch("z", z1 + 2, z2 - 2, x1 + 1, x1 + 1, g, 6, pointed=True)
    b.carve_arch("z", z1 + 2, z2 - 2, x2 - 1, x2 - 1, g, 6, pointed=True)
    for x in range(x1 + 1, x2):
        for z in range(z1 + 1, z2):
            b.set(x, g + 8, z, "deepslate_tiles")
    b.hip_roof(x1 + 1, x2 - 1, z1 + 1, z2 - 1, g + 9, "deepslate_tile", "deepslate_tiles", overhang=1)
    fill_roof_cavity(b, x1, x2, z1, z2, g + 9, "deepslate_tiles")
    for y in range(g + 13, g + 15):
        b.set(ex, y, ez, "polished_blackstone_wall")
    b.set(ex, g + 15, ez, "lightning_rod", facing="up", powered="false")
    # lanterns under the roof
    for x, z in ((x1 + 2, z1 + 2), (x2 - 2, z1 + 2), (x1 + 2, z2 - 2), (x2 - 2, z2 - 2)):
        b.lantern(x, g + 7, z, hanging=True)
    b.lantern(ex, g + 3, ez)                      # on top of the elevator cap


@template("underground_hub", "Hub sotterraneo esagonale con magazzino",
          "Hub e magazzini",
          "Sala esagonale gotico-industriale 22 blocchi sotto terra con cupola a costoloni e lampadario, "
          "quattro stazioni (incanti, alchimia, officina, fonderia), galleria-magazzino con smistatore "
          "automatico a 9 oggetti (barili con nome, barile di troppo pieno, deposito con canale d'acqua), "
          "ascensore a bolle di sabbia delle anime con scala a chiocciola e chiosco in superficie, porte di "
          "servizio a est e ovest per agganciare altri moduli. Redstone tutta nascosta dietro le pareti; "
          "i filtri e i nomi dei barili sono gia' scritti dall'app.")
def underground_hub():
    b = Builder(HUB_W, HUB_G + 16, HUB_L, seed=2201)
    b.ground_offset = HUB_G
    slices = _hub_gallery(b)
    _hub_hall(b)
    _hub_openings(b)
    _hub_center(b)
    cx, cz = HUB_C
    _station(b, cx - 8, cz - 5, "incanti")
    _station(b, cx + 8, cz - 5, "alchimia")
    _station(b, cx - 8, cz + 5, "officina")
    _station(b, cx + 8, cz + 5, "fonderia")
    _hub_tower(b)
    _hub_kiosk(b)
    seal_underground(b, HUB_G - 1)
    b.sorter_slices = slices
    return b


# ===========================================================================
# Iron farm (Java 1.21+)
# ===========================================================================
#
# Meccanica (codice di Minecraft Java): ogni 100 tick un villager in preda al panico (vede uno zombie entro
# 8 blocchi) prova a evocare un golem se almeno 3 villager vicini "vogliono" un golem: devono aver dormito
# nelle ultime 24000 tick e non aver visto un golem negli ultimi 600. Il golem nasce in 10 tentativi
# casuali entro +-8 blocchi in orizzontale e +-6 in verticale dal villager, sul primo blocco solido
# (non vetro) con aria o acqua sopra, scendendo dall'alto. Qui l'unica superficie valida e' la
# piattaforma d'acqua: tutto il resto nel raggio e' vetro, coperto, o fuori quota.
# Lo zombie e' visibile solo di giorno: di notte un pistone chiude la feritoia cosi' i villager dormono.

FARM_W = 18
FARM_V = 14                   # quota dei letti (villager); piattaforma a V-5, tetto a V+6
FARM_O = 1                    # margine: l'edificio occupa x, z 1..16


def _farm_coords():
    o = FARM_O
    return {
        "platform": (o + 3, o + 12),            # x/z range of the spawning platform
        "hole": (o + 7, o + 8),
        "villagers": [(o + 7, o + 5), (o + 8, o + 5), (o + 9, o + 5)],
        "zombie": (o + 8, o + 9),
        "opening": (o + 8, FARM_V + 2, o + 8),
        "piston": (o + 8, FARM_V + 4, o + 8),
        "torch_dd": (o + 8, FARM_V + 4, o + 9),
        "s3": (o + 8, FARM_V + 4, o + 10),
        "daylight": (o + 9, FARM_V + 5, o + 10),
        "lever": (o + 2, 4, o + 8),
        "tower": (o + 1, o + 8),
    }


@template("iron_farm", "Fonderia del ferro (iron farm 1.21)",
          "Farm automatiche",
          "Iron farm compatta per Java 1.21+ dentro una fonderia di mattoni e ardesia: 3 villager sui letti e "
          "1 zombie (scritti dall'app), piattaforma d'acqua che porta i golem in un pozzo con lama di lava "
          "sostenuta da cartelli, tramogge e 4 bauli al piano terra. Di notte un sensore di luce chiude la "
          "feritoia dello zombie per far dormire i villager; la leva nel muro ovest del piano terra spegne la farm. "
          "Circa 260-320 lingotti all'ora di giorno: vedi la checklist nel README prima di usarla.")
def iron_farm():
    o = FARM_O
    V = FARM_V
    c = _farm_coords()
    b = Builder(FARM_W, V + 17, FARM_W, seed=1214)
    x0, x1 = o, o + 15                          # building footprint
    p0, p1 = c["platform"]
    h0, h1 = c["hole"]
    roof = V + 6

    # ---- shell: plinth (y 0..6, may protrude), upper walls flush (no ledges in the golem range) ----
    for x in range(x0, x1 + 1):
        for z in range(x0, x1 + 1):
            b.set(x, 0, z, "polished_blackstone_bricks")
            edge = x in (x0, x1) or z in (x0, x1)
            inner = x in (x0 + 1, x1 - 1) or z in (x0 + 1, x1 - 1)
            wall = x in (x0 + 2, x1 - 2) or z in (x0 + 2, x1 - 2)
            if edge or inner or wall:
                for y in range(1, roof + 1):
                    if edge:
                        if y <= 2:
                            block = "polished_blackstone_bricks"
                        elif y <= 6:
                            block = "bricks" if b.rng.random() > 0.1 else "mud_bricks"
                        else:
                            block = "bricks" if b.rng.random() > 0.15 else "granite"
                    else:
                        block = "deepslate_bricks" if inner else "polished_deepslate"
                    b.set(x, y, z, block)
    # protruding pilasters (skeleton layer): they rise to the roof, so their top is out of the golem range
    lo, hi = x0 - 1, x1 + 1
    for k in range(x0, x1 + 1, 5):
        for x, z in ((k, lo), (k, hi), (lo, k), (hi, k)):
            for y in range(0, roof + 1):
                b.set(x, y, z, "polished_deepslate" if y % 6 else "chiseled_deepslate")
    for x, z in ((lo, lo), (lo, hi), (hi, lo), (hi, hi)):
        for y in range(0, roof + 1):
            b.set(x, y, z, "polished_blackstone_bricks")
    # plinth course: its top (y=2) is far below the golem range (y 8..20)
    for k in range(x0, x1 + 1):
        for x, z, f in ((k, lo, "north"), (k, hi, "south"), (lo, k, "west"), (hi, k, "east")):
            if b.get(x, 1, z) is None:
                b.set(x, 0, z, "polished_blackstone_bricks")
                b.set(x, 1, z, "polished_blackstone_bricks")
                b.stair(x, 2, z, "polished_blackstone_brick", {"north": "south", "south": "north",
                                                               "west": "east", "east": "west"}[f])
    # flush bands and tall windows in every bay (glass panes are never a golem spawn surface)
    for k in range(x0 + 1, x1):
        for x, z in ((k, x0), (k, x1), (x0, k), (x1, k)):
            if (k - x0) % 5:
                b.set(x, 7, z, "polished_blackstone_bricks")
                b.set(x, roof - 1, z, "polished_blackstone_bricks")
                b.set(x, roof - 2, z, "chiseled_polished_blackstone" if (k - x0) % 5 in (2, 3) else
                      "polished_blackstone_bricks")
    for bay in range(x0 + 1, x1, 5):
        for k in (bay + 1, bay + 2):
            for x, z in ((k, x0), (k, x1), (x0, k), (x1, k)):
                for y in range(9, roof - 3):
                    b.set(x, y, z, "black_stained_glass_pane")
                b.set(x, 8, z, "polished_blackstone_bricks")
    for k in (3, 12):
        for x, z in ((x0 + k, x1), (x0, x0 + k), (x1, x0 + k)):
            b.set(x, 3, z, "glass_pane")
            b.set(x, 4, z, "glass_pane")

    # ---- ground floor: collection room ----
    for x in range(p0, p1 + 1):
        for z in range(p0, p1 + 1):
            for y in range(1, 8):
                b.set(x, y, z, AIR)
            b.set(x, 0, z, "polished_deepslate" if (x + z) % 2 else "deepslate_tiles")
    # door (south), double
    for x in (o + 7, o + 8):
        for z in (x1 - 2, x1 - 1):
            b.set(x, 1, z, AIR)
            b.set(x, 2, z, AIR)
    b.door(o + 7, 1, x1, "north", wood="spruce", hinge="left")
    b.door(o + 8, 1, x1, "north", wood="spruce", hinge="right")
    for x in (o + 7, o + 8):
        b.set(x, 0, x1 + 1, "polished_blackstone_bricks")
        b.set(x, 1, x1 + 1, AIR)
        b.set(x, 2, x1 + 1, AIR)
        b.set(x, 3, x1 + 1, AIR)
    # kill pit and collection: chests (y1) <- hoppers (y2) <- golem (y3), signs y4, lava y5, signs y6
    for x in range(h0 - 1, h1 + 2):
        for z in range(h0 - 1, h1 + 2):
            ring = x in (h0 - 1, h1 + 1) or z in (h0 - 1, h1 + 1)
            if ring:
                for y in range(3, 9):
                    win = y in (3, 4, 5) and (x in (h0, h1) or z in (h0, h1))
                    b.set(x, y, z, "glass" if win else "polished_blackstone_bricks")
    for x in (h0, h1):
        for z in (h0, h1):
            b.set(x, 2, z, "hopper", facing="down", enabled="true")
            b.chest(x, 1, z, "west" if x == h0 else "east")
            b.set(x, 3, z, AIR)
            wall_face = "east" if x == h0 else "west"       # sign leans on the outer ring block
            b.set(x, 4, z, "oak_wall_sign", facing=wall_face, waterlogged="false")
            b.set(x, 5, z, "lava", level=0)
            b.set(x, 6, z, "oak_wall_sign", facing=wall_face, waterlogged="false")
            b.set(x, 7, z, AIR)
            b.set(x, 8, z, AIR)
            b.set(x, 9, z, AIR)
    # flush & lock lever in a niche of the west wall, and the torch tower inside the wall
    lx, ly, lz = c["lever"]
    b.set(lx, ly, lz, "lever", face="wall", facing="east", powered="false")
    # torch tower inside the wall: blocks B0..B7 at y = 4, 6, ..., 18, torches T1..T8 at y = 5, 7, ..., 19.
    # Every torch inverts: with the lever off T1, T3, T5, T7 are lit and T8 is off.
    tx, tz = c["tower"]
    for k in range(0, 8):
        b.set(tx, 4 + 2 * k, tz, "smooth_stone")
    for k in range(1, 9):
        b.set(tx, 3 + 2 * k, tz, "redstone_torch", lit="true" if k % 2 == 1 else "false")
    b.set(tx, roof, tz, "glass")
    # decoration of the ground floor: foundry
    b.set(p0, 1, p0, "blast_furnace", facing="south", lit="false")
    b.set(p0 + 1, 1, p0, "smithing_table")
    b.set(p0 + 2, 1, p0, "anvil", facing="east")
    b.set(p1, 1, p0, "water_cauldron", level=3)
    b.set(p1 - 1, 1, p0, "grindstone", face="floor", facing="south")
    b.set(p0, 1, p1, "crafting_table")
    b.set(p1, 1, p1, "barrel", facing="up", open="false")
    for x, z in ((p0 + 1, p0 + 1), (p1 - 1, p0 + 1), (p0 + 1, p1 - 1), (p1 - 1, p1 - 1), (p0 + 3, p0 + 6),
                 (p1 - 3, p0 + 6)):
        b.lantern(x, 7, z, hanging=True)
    for x, z in ((p0, p0 + 4), (p1, p0 + 4), (p0 + 4, p0), (p1 - 4, p0), (p0 + 2, p1), (p1 - 2, p1)):
        b.lantern(x, 1, z)

    # ---- platform: water flowing to the 2x2 hole ----
    for x in range(p0, p1 + 1):
        for z in range(p0, p1 + 1):
            b.set(x, 8, z, "smooth_stone" if (x, z) not in {(hx, hz) for hx in (h0, h1) for hz in (h0, h1)}
                  else AIR)
            i, j = x - p0, z - p0
            d = min(i, j, p1 - x, p1 - z)
            if x in (h0, h1) and z in (h0, h1):
                continue
            b.set(x, 9, z, "water", level=d)
            for y in range(10, V - 1):
                b.set(x, y, z, AIR)
    for x in range(p0, p1 + 1):                       # open space above the platform, up to the attic
        for z in range(p0, p1 + 1):
            for y in range(V - 1, roof - 2):
                if b.get(x, y, z) is None:
                    b.set(x, y, z, AIR)

    # ---- pod: villagers, sight slot and zombie (glass everywhere a golem could otherwise spawn) ----
    zx, zz = c["zombie"]
    for x in range(o + 6, o + 11):
        for z in range(o + 4, o + 11):
            b.set(x, V - 1, z, "glass")
            for y in range(V, V + 3):
                b.set(x, y, z, "glass")
            b.set(x, V + 3, z, "glass")
    for vx, vz in c["villagers"]:
        b.bed(vx, V, vz + 1, "north", color="white")
        for y in (V + 1, V + 2):
            b.set(vx, y, vz, AIR)
        b.set(vx, V + 2, vz + 1, AIR)                      # slot over the bed foot (glass at V+1)
        b.set(vx, V, vz + 2, "polished_deepslate")         # slot wall: solid, glass, open
        b.set(vx, V + 2, vz + 2, AIR)
        b.villager(vx, V + 0.5625, vz, profession="none", yaw=0.0)
    ox, oy, oz = c["opening"]
    for x in (ox - 1, ox + 1):
        for y in range(V, V + 3):
            b.set(x, y, oz, "polished_deepslate")
    b.set(ox, V, oz, "polished_deepslate")
    b.set(ox, V + 2, oz, AIR)
    b.set(ox, V + 3, oz, "smooth_stone")               # pushed down into the slot at night
    b.set(zx, V, zz, "smooth_stone_slab", type="bottom", waterlogged="false")
    b.set(zx, V + 1, zz, AIR)
    b.set(zx, V + 2, zz, AIR)
    for x, z in ((zx - 1, zz), (zx + 1, zz), (zx, zz + 1)):
        for y in range(V, V + 3):
            b.set(x, y, z, "polished_deepslate")
    b.mob(zx, V + 0.5, zz, "zombie", yaw=180.0)

    # ---- attic: piston + daylight inverter + lever line (1-block crawl space under the roof) ----
    for x in range(x0 + 3, x1 - 2):
        for z in range(x0 + 3, x1 - 2):
            b.set(x, roof - 2, z, "glass")
            b.set(x, roof - 1, z, AIR)
    px, py, pz = c["piston"]
    b.set(px, py, pz, "sticky_piston", facing="down", extended="false")
    sx, sy, sz = c["s3"]
    b.set(sx, sy, sz, "smooth_stone")
    tqx, tqy, tqz = c["torch_dd"]
    b.set(tqx, tqy, tqz, "redstone_wall_torch", facing="north", lit="true")
    b.set(sx, sy + 1, sz, "redstone_wire", power="0")
    dx_, dy_, dz_ = c["daylight"]
    b.set(dx_, dy_, dz_, "daylight_detector", inverted="false", power="0")
    for x in range(tx + 1, px + 1):
        b.set(x, roof - 1, tz, "redstone_wire", power="0")
    b.set(tx + 1, roof - 2, tz, "polished_deepslate")      # support of the first dust in the wall
    b.technical_area(o + 5, V - 1, o + 3, o + 11, roof, o + 11)
    b.technical_area(tx, 3, tz, tx, roof, tz)

    # ---- roof: full slab of blocks at V+6, skylight over the detector, hip roof and chimney above ----
    for x in range(x0, x1 + 1):
        for z in range(x0, x1 + 1):
            b.set(x, roof, z, "deepslate_tiles")
    b.set(dx_, roof, dz_, "glass")
    for x, z in ((o + 5, o + 5), (o + 10, o + 5), (o + 5, o + 12), (o + 12, o + 12)):
        b.set(x, roof, z, "glass")
    b.hip_roof(x0, x1, x0, x1, roof + 1, "deepslate_tile", "deepslate_tiles", overhang=1)
    fill_roof_cavity(b, x0 - 1, x1 + 1, x0 - 1, x1 + 1, roof + 1, "deepslate_tiles")
    # glass shaft through the roof: the daylight detector must see the open sky
    dxs, _, dzs = c["daylight"]
    for y in range(roof + 1, b.h):
        if b.get(dxs, y, dzs) not in (None, AIR):
            b.set(dxs, y, dzs, "glass")
    for y in range(roof + 1, roof + 9):
        for x in (x0 + 2, x0 + 4):
            for z in (x1 - 4, x1 - 2):
                b.set(x, y, z, "bricks")
        b.set(x0 + 3, y, x1 - 4, "bricks")
        b.set(x0 + 3, y, x1 - 2, "bricks")
        b.set(x0 + 2, y, x1 - 3, "bricks")
        b.set(x0 + 4, y, x1 - 3, "bricks")
        b.set(x0 + 3, y, x1 - 3, AIR)
    b.set(x0 + 3, roof + 1, x1 - 3, "campfire", lit="true", signal_fire="false", facing="north",
          waterlogged="false")
    return b
