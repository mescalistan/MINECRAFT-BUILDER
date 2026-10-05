"""
Mini-DSL per costruire strutture Minecraft (formato Structure Block .nbt).

Convenzioni:
- x = est, y = alto, z = sud. y=0 e' il primo strato sopra il terreno.
- Le celle non impostate restano "structure void" (il terreno esistente viene
  preservato); le celle impostate ad aria vengono scavate dall'iniettore.
- Scale: "facing" e' la direzione in cui si sale (dove sta lo schienale alto).
- In fase di export vengono calcolate automaticamente le connessioni di
  recinti/pannelli/muretti e la forma (shape) delle scale, come fa il gioco.
"""
import math
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from nbt_codec import (save_nbt, TAG_Compound, TAG_List, TAG_Int, TAG_String, TAG_Byte, TAG_Double, TAG_Float,
                       TAG_Int_Array)
import blockinfo

DATA_VERSION = 3955  # Minecraft 1.21.1

AIR = "minecraft:air"

DIRS = {"north": (0, -1), "south": (0, 1), "east": (1, 0), "west": (-1, 0)}
OPPOSITE = {"north": "south", "south": "north", "east": "west", "west": "east"}
CCW = {"north": "west", "west": "south", "south": "east", "east": "north"}

STAIR = dict(half="bottom", shape="straight", waterlogged="false")
STAIR_TOP = dict(half="top", shape="straight", waterlogged="false")


def _short(name):
    return name if ":" in name else "minecraft:" + name


def _is_fence(n):
    return n.endswith("_fence")


def _is_pane(n):
    return n.endswith("glass_pane") or n == "minecraft:iron_bars"


def _is_wall(n):
    return blockinfo.is_wall_block(n)


def _is_solid(n):
    return n is not None and blockinfo.is_full_solid(n)


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

REGISTRY = {}


def template(name, title, category, description):
    """Decorator that registers a template-building function."""
    def wrap(fn):
        REGISTRY[name] = {"fn": fn, "title": title, "category": category, "description": description}
        return fn
    return wrap


def item_stack(item, count=1, slot=None, name=None):
    """
    Item compound as stored in containers (1.20.5+ format: id + int count). 'name' renames the item
    (custom_name component; converted to the JSON form for pre-1.21.5 worlds at injection).
    """
    tag = TAG_Compound({"id": TAG_String(item if ":" in item else "minecraft:" + item),
                        "count": TAG_Int(count)})
    if slot is not None:
        tag["Slot"] = TAG_Byte(slot)
    if name:
        tag["components"] = TAG_Compound({"minecraft:custom_name": TAG_String(name)})
    return tag


# ---------------------------------------------------------------------------
# Builder
# ---------------------------------------------------------------------------

class Builder:
    def __init__(self, width, height, length, seed=0):
        self.w, self.h, self.l = width, height, length
        self.cells = {}  # (x, y, z) -> (name, props_dict)
        self.rng = random.Random(seed)
        self.block_nbt = {}    # (x, y, z) -> block entity data written with the block (container items)
        self.entities = []     # [{"pos": (x, y, z), "nbt": compound, "yaw": degrees}]
        self.ground_offset = 0  # layers below the terrain level (underground builds)
        self.technical = []     # sealed technical areas (x1, y1, z1, x2, y2, z2): hidden on purpose

    # ---- primitives ----
    def inside(self, x, y, z):
        return 0 <= x < self.w and 0 <= y < self.h and 0 <= z < self.l

    def set(self, x, y, z, block, **props):
        if self.inside(x, y, z):
            self.cells[(x, y, z)] = (_short(block), {k: str(v).lower() for k, v in props.items()})
            if self.block_nbt:
                self.block_nbt.pop((x, y, z), None)

    # ---- block entity data and entities ----
    def contents(self, x, y, z, items, name=None):
        """
        Items of the container at (x, y, z): a list of (item, count) put in slots 0, 1, 2...
        or of (slot, item, count), optionally followed by the item's custom name.
        'name' is the custom name shown in the container window.
        """
        stacks = []
        for i, entry in enumerate(items):
            entry = tuple(entry)
            if isinstance(entry[0], int):
                slot, item, count, label = (entry + (None,))[:4]
            else:
                item, count, label = (entry + (None,))[:3]
                slot = i
            stacks.append(item_stack(item, count, slot, label))
        data = TAG_Compound({"Items": TAG_List(10, stacks)})
        if name:
            data["CustomName"] = TAG_String(name)
        self.block_nbt[(x, y, z)] = data

    def technical_area(self, x1, y1, z1, x2, y2, z2):
        """
        Declares a sealed technical area (redstone, villager pods): the validator does not require
        its interactive blocks to be reachable. Use it only for parts hidden on purpose.
        """
        self.technical.append((min(x1, x2), min(y1, y2), min(z1, z2), max(x1, x2), max(y1, y2), max(z1, z2)))

    def entity(self, x, y, z, entity_id, yaw=0.0, **tags):
        """
        Entity standing in the middle of block cell (x, y, z). 'tags' are extra NBT tags
        (nbt_codec TAG objects). Yaw: 0 = looking south, 90 = west, 180 = north, 270 = east.
        """
        nbt = TAG_Compound({"id": TAG_String(entity_id if ":" in entity_id else "minecraft:" + entity_id)})
        nbt.update(tags)
        self.entities.append({"pos": (x + 0.5, float(y), z + 0.5), "nbt": nbt, "yaw": float(yaw)})

    def villager(self, x, y, z, profession="none", biome="plains", yaw=0.0):
        self.entity(x, y, z, "villager", yaw, PersistenceRequired=TAG_Byte(1), VillagerData=TAG_Compound({
            "profession": TAG_String("minecraft:" + profession), "type": TAG_String("minecraft:" + biome),
            "level": TAG_Int(1)}))

    def mob(self, x, y, z, entity_id, yaw=0.0, **tags):
        """Hostile/passive mob that never despawns."""
        self.entity(x, y, z, entity_id, yaw, PersistenceRequired=TAG_Byte(1), **tags)

    def get(self, x, y, z):
        return self.cells.get((x, y, z), (None, {}))[0]

    def remove(self, x, y, z):
        """Back to structure void (terrain preserved)."""
        self.cells.pop((x, y, z), None)

    def set_if_empty(self, x, y, z, block, **props):
        if self.get(x, y, z) in (None, AIR):
            self.set(x, y, z, block, **props)

    def fill(self, x1, y1, z1, x2, y2, z2, block, **props):
        for x in range(min(x1, x2), max(x1, x2) + 1):
            for y in range(min(y1, y2), max(y1, y2) + 1):
                for z in range(min(z1, z2), max(z1, z2) + 1):
                    self.set(x, y, z, block, **props)

    def fill_random(self, x1, y1, z1, x2, y2, z2, choices, **props):
        """choices: list of (block, weight)."""
        blocks = [c[0] for c in choices]
        weights = [c[1] for c in choices]
        for x in range(min(x1, x2), max(x1, x2) + 1):
            for y in range(min(y1, y2), max(y1, y2) + 1):
                for z in range(min(z1, z2), max(z1, z2) + 1):
                    self.set(x, y, z, self.rng.choices(blocks, weights)[0], **props)

    def replace(self, x1, y1, z1, x2, y2, z2, old, new, chance=1.0, **props):
        old = _short(old)
        for x in range(min(x1, x2), max(x1, x2) + 1):
            for y in range(min(y1, y2), max(y1, y2) + 1):
                for z in range(min(z1, z2), max(z1, z2) + 1):
                    if self.get(x, y, z) == old and self.rng.random() < chance:
                        self.set(x, y, z, new, **props)

    def walls(self, x1, y1, z1, x2, y2, z2, block, **props):
        """Perimetro verticale di un parallelepipedo (senza pavimento/soffitto)."""
        for y in range(y1, y2 + 1):
            for x in range(x1, x2 + 1):
                self.set(x, y, z1, block, **props)
                self.set(x, y, z2, block, **props)
            for z in range(z1, z2 + 1):
                self.set(x1, y, z, block, **props)
                self.set(x2, y, z, block, **props)

    def clear(self, x1, y1, z1, x2, y2, z2):
        self.fill(x1, y1, z1, x2, y2, z2, AIR)

    def room(self, x1, y1, z1, x2, y2, z2, wall, floor=None, ceiling=None, corner=None, **corner_props):
        """Stanza chiusa: pavimento (y1), muri, soffitto (y2), interno d'aria."""
        self.fill(x1, y1, z1, x2, y1, z2, floor or wall)
        self.walls(x1, y1 + 1, z1, x2, y2 - 1, z2, wall)
        if ceiling is not False:
            self.fill(x1, y2, z1, x2, y2, z2, ceiling or wall)
        self.clear(x1 + 1, y1 + 1, z1 + 1, x2 - 1, y2 - 1, z2 - 1)
        if corner:
            for x, z in ((x1, z1), (x2, z1), (x1, z2), (x2, z2)):
                self.fill(x, y1 + 1, z, x, y2 - 1, z, corner, **corner_props)

    def line(self, x1, y1, z1, x2, y2, z2, block, **props):
        n = max(abs(x2 - x1), abs(y2 - y1), abs(z2 - z1), 1)
        for i in range(n + 1):
            t = i / n
            self.set(round(x1 + (x2 - x1) * t), round(y1 + (y2 - y1) * t), round(z1 + (z2 - z1) * t), block, **props)

    # ---- round shapes ----
    @staticmethod
    def _in_circle(dx, dz, r):
        return dx * dx + dz * dz <= (r + 0.35) ** 2

    def disk(self, cx, cz, y, r, block, **props):
        ri = int(math.ceil(r)) + 1
        for x in range(cx - ri, cx + ri + 1):
            for z in range(cz - ri, cz + ri + 1):
                if self._in_circle(x - cx, z - cz, r):
                    self.set(x, y, z, block, **props)

    def ring(self, cx, cz, y, r, block, thickness=1, **props):
        ri = int(math.ceil(r)) + 1
        for x in range(cx - ri, cx + ri + 1):
            for z in range(cz - ri, cz + ri + 1):
                dx, dz = x - cx, z - cz
                if self._in_circle(dx, dz, r) and not self._in_circle(dx, dz, r - thickness):
                    self.set(x, y, z, block, **props)

    def cylinder(self, cx, cz, y1, y2, r, block, hollow=False, thickness=1, **props):
        for y in range(y1, y2 + 1):
            if hollow:
                self.ring(cx, cz, y, r, block, thickness, **props)
            else:
                self.disk(cx, cz, y, r, block, **props)

    def dome(self, cx, cy, cz, r, block, hollow=True, thickness=1, clear_inside=True, **props):
        """Semisfera con base a quota cy."""
        ri = int(math.ceil(r)) + 1
        for x in range(cx - ri, cx + ri + 1):
            for z in range(cz - ri, cz + ri + 1):
                for y in range(cy, cy + ri + 1):
                    d = math.sqrt((x - cx) ** 2 + (y - cy) ** 2 + (z - cz) ** 2)
                    if d <= r + 0.4:
                        if not hollow or d > r + 0.4 - thickness - 0.6:
                            self.set(x, y, z, block, **props)
                        elif clear_inside:
                            self.set(x, y, z, AIR)

    def sphere(self, cx, cy, cz, r, block, **props):
        ri = int(math.ceil(r)) + 1
        for x in range(cx - ri, cx + ri + 1):
            for y in range(cy - ri, cy + ri + 1):
                for z in range(cz - ri, cz + ri + 1):
                    if (x - cx) ** 2 + (y - cy) ** 2 + (z - cz) ** 2 <= (r + 0.4) ** 2:
                        self.set(x, y, z, block, **props)

    def cone(self, cx, cz, y, r, block, step=1.0, hollow=False, **props):
        """Cono che parte da raggio r a quota y e si restringe di 'step' per livello."""
        level = 0
        while r - level * step >= 0:
            rr = r - level * step
            if hollow and rr > 1:
                self.ring(cx, cz, y + level, rr, block, **props)
            else:
                self.disk(cx, cz, y + level, rr, block, **props)
            level += 1
        return y + level - 1

    def onion_dome(self, cx, cy, cz, r, block, tip="gold_block"):
        """Cupola a cipolla (stile russo)."""
        profile = [r * 0.8, r, r, r * 0.9, r * 0.7, r * 0.45, r * 0.25, 0.4]
        for i, rr in enumerate(profile):
            self.disk(cx, cz, cy + i, rr, block)
        self.set(cx, cy + len(profile), cz, tip)
        return cy + len(profile)

    def pyramid(self, x1, z1, x2, z2, y, block, step=1, hollow=False, **props):
        """Piramide a gradoni: ogni livello rientra di 'step' blocchi."""
        level = 0
        while x1 + level * step <= x2 - level * step and z1 + level * step <= z2 - level * step:
            a, b = x1 + level * step, x2 - level * step
            c, d = z1 + level * step, z2 - level * step
            if hollow and b - a > 1 and d - c > 1:
                self.walls(a, y + level, c, b, y + level, d, block, **props)
            else:
                self.fill(a, y + level, c, b, y + level, d, block, **props)
            level += 1
        return y + level - 1

    # ---- furniture & details ----
    def door(self, x, y, z, facing, wood="oak", hinge="left"):
        self.set(x, y, z, f"{wood}_door", facing=facing, half="lower", hinge=hinge, open="false", powered="false")
        self.set(x, y + 1, z, f"{wood}_door", facing=facing, half="upper", hinge=hinge, open="false", powered="false")

    def bed(self, x, y, z, facing, color="red"):
        """(x,y,z) = piede del letto; la testa e' verso 'facing'."""
        dx, dz = DIRS[facing]
        self.set(x, y, z, f"{color}_bed", facing=facing, part="foot", occupied="false")
        self.set(x + dx, y, z + dz, f"{color}_bed", facing=facing, part="head", occupied="false")

    def stair(self, x, y, z, material, facing, top=False):
        self.set(x, y, z, f"{material}_stairs", facing=facing, **(STAIR_TOP if top else STAIR))

    def slab(self, x, y, z, material, top=False):
        self.set(x, y, z, f"{material}_slab", type="top" if top else "bottom", waterlogged="false")

    def lantern(self, x, y, z, hanging=False, soul=False):
        self.set(x, y, z, "soul_lantern" if soul else "lantern", hanging=hanging, waterlogged="false")

    def wall_torch(self, x, y, z, facing):
        """facing = direzione verso cui punta la torcia (il muro e' dal lato opposto)."""
        self.set(x, y, z, "wall_torch", facing=facing)

    def ladder(self, x, y1, y2, z, facing):
        """facing = direzione verso cui guarda la scala (il muro e' dal lato opposto)."""
        for y in range(y1, y2 + 1):
            self.set(x, y, z, "ladder", facing=facing, waterlogged="false")

    def chest(self, x, y, z, facing):
        self.set(x, y, z, "chest", facing=facing, type="single", waterlogged="false")

    def table(self, x, y, z, wood="oak"):
        self.set(x, y, z, f"{wood}_fence")
        self.set(x, y + 1, z, f"{wood}_pressure_plate", powered="false")

    def leaves(self, x, y, z, kind="oak"):
        self.set(x, y, z, f"{kind}_leaves", persistent="true", distance="1", waterlogged="false")

    def tree(self, x, y, z, kind="oak", height=5, radius=2):
        """Albero semplice con foglie persistenti (non si seccano)."""
        for i in range(height):
            self.set(x, y + i, z, f"{kind}_log", axis="y")
        top = y + height
        for dy in range(-2, 2):
            rr = radius if dy < 0 else radius - 1
            for dx in range(-rr, rr + 1):
                for dz in range(-rr, rr + 1):
                    if abs(dx) == rr and abs(dz) == rr and self.rng.random() < 0.5:
                        continue
                    if self.get(x + dx, top + dy, z + dz) in (None, AIR):
                        self.leaves(x + dx, top + dy, z + dz, kind)
        self.leaves(x, top + 2, z, kind)

    def carve_arch(self, axis, a1, a2, b1, b2, y, height, block=AIR, pointed=False):
        """
        Apre un arco. axis='x': luce dell'arco lungo X (a1..a2), spessore lungo Z (b1..b2);
        axis='z' viceversa. 'height' e' l'altezza in chiave; pointed=True = sesto acuto (gotico).
        """
        width = a2 - a1 + 1
        r = width / 2.0
        center = (a1 + a2) / 2.0
        spring = y + height - (int(math.ceil(r * 1.5)) if pointed else int(math.ceil(r)))
        for a in range(a1, a2 + 1):
            d = abs(a - center)
            if pointed:
                top = spring + int(math.floor((r - d) * 1.5 + 0.2))
            else:
                top = spring + int(math.floor(math.sqrt(max(0.0, r * r - d * d)) - 0.15))
            for yy in range(y, max(top, y) + 1):
                for b in range(min(b1, b2), max(b1, b2) + 1):
                    if axis == "x":
                        self.set(a, yy, b, block)
                    else:
                        self.set(b, yy, a, block)

    def octagon(self, cx, cz, y, r, block, hollow=False, **props):
        for x in range(cx - r, cx + r + 1):
            for z in range(cz - r, cz + r + 1):
                dx, dz = abs(x - cx), abs(z - cz)
                inside = dx + dz <= r + r // 2
                if not inside:
                    continue
                edge = dx == r or dz == r or dx + dz == r + r // 2
                if not hollow or edge:
                    self.set(x, y, z, block, **props)
                elif hollow:
                    self.set(x, y, z, AIR)

    def ellipsoid(self, cx, cy, cz, rx, ry, rz, block, hollow=False, thickness=1.2, upper_only=True,
                  clear_inside=True, **props):
        for x in range(int(cx - rx) - 1, int(cx + rx) + 2):
            for z in range(int(cz - rz) - 1, int(cz + rz) + 2):
                for y in range(cy if upper_only else int(cy - ry) - 1, int(cy + ry) + 2):
                    e = ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2 + ((z - cz) / rz) ** 2
                    if e > 1.0:
                        continue
                    inner = ((x - cx) / max(rx - thickness, 0.5)) ** 2 + ((y - cy) / max(ry - thickness, 0.5)) ** 2                         + ((z - cz) / max(rz - thickness, 0.5)) ** 2
                    if hollow and inner < 1.0:
                        if clear_inside:
                            self.set(x, y, z, AIR)
                    else:
                        self.set(x, y, z, block, **props)

    def entrance(self, x, y, z, facing, wood="oak", step="cobblestone", hinge="left"):
        """
        Porta in (x,y,z) che si attraversa camminando verso 'facing' (verso l'interno),
        con gradino esterno a y-1 e lo spazio davanti libero.
        """
        self.door(x, y, z, facing, wood, hinge)
        dx, dz = DIRS[facing]
        ox, oz = x - dx, z - dz
        if y > 0 and step:
            self.stair(ox, y - 1, oz, step, facing)
        self.set_if_empty(ox, y, oz, AIR)
        self.set_if_empty(ox, y + 1, oz, AIR)
        self.set_if_empty(x + dx, y, z + dz, AIR)
        self.set_if_empty(x + dx, y + 1, z + dz, AIR)

    def eave(self, x1, x2, z1, z2, y, material, overhang=2):
        """Gronda da pagoda: anello di lastre con angoli rialzati e due giri di scale."""
        a, b, c, d = x1 - overhang, x2 + overhang, z1 - overhang, z2 + overhang
        for x in range(a, b + 1):
            self.slab(x, y, c, material)
            self.slab(x, y, d, material)
        for z in range(c, d + 1):
            self.slab(a, y, z, material)
            self.slab(b, y, z, material)
        for x, z in ((a, c), (b, c), (a, d), (b, d)):
            self.slab(x, y + 1, z, material)
        for k in range(1, overhang + 1):
            yy = y + k
            xa, xb, za, zb = a + k, b - k, c + k, d - k
            for x in range(xa, xb + 1):
                self.stair(x, yy, za, material, "south")
                self.stair(x, yy, zb, material, "north")
            for z in range(za + 1, zb):
                self.stair(xa, yy, z, material, "east")
                self.stair(xb, yy, z, material, "west")
        return y + overhang

    # ---- roofs ----
    def gable_roof(self, x1, x2, z1, z2, y, stair, full, axis="x", overhang=1, gable=None, fill_attic=True):
        """
        Tetto a capanna. axis='x': colmo lungo X (falde verso nord e sud).
        stair = materiale delle scale (es. 'spruce'), full = blocco del colmo.
        """
        gable = gable or full
        if axis == "x":
            a1, a2, b1, b2 = z1 - overhang, z2 + overhang, x1 - overhang, x2 + overhang
        else:
            a1, a2, b1, b2 = x1 - overhang, x2 + overhang, z1 - overhang, z2 + overhang
        level = 0
        while a1 + level <= a2 - level:
            lo, hi = a1 + level, a2 - level
            for b in range(b1, b2 + 1):
                for a, facing in ((lo, "south" if axis == "x" else "east"), (hi, "north" if axis == "x" else "west")):
                    x, z = (b, a) if axis == "x" else (a, b)
                    if lo == hi:
                        self.set(x, y + level, z, full)
                    else:
                        self.stair(x, y + level, z, stair, facing)
            if level > 0:
                ends = (x1, x2) if axis == "x" else (z1, z2)
                for a in range(lo + 1, hi):
                    for e in ends:
                        x, z = (e, a) if axis == "x" else (a, e)
                        self.set(x, y + level, z, gable)
                    if fill_attic:
                        inner = range(min(ends) + 1, max(ends))
                        for e in inner:
                            x, z = (e, a) if axis == "x" else (a, e)
                            if self.get(x, y + level, z) is None:
                                self.set(x, y + level, z, AIR)
            level += 1
        return y + level - 1

    def hip_roof(self, x1, x2, z1, z2, y, stair, full, overhang=1, flat_top=True):
        """Tetto a padiglione (quattro falde)."""
        a, b, c, d = x1 - overhang, x2 + overhang, z1 - overhang, z2 + overhang
        level = 0
        while a + level <= b - level and c + level <= d - level:
            xa, xb, za, zb = a + level, b - level, c + level, d - level
            if xa == xb or za == zb:
                self.fill(xa, y + level, za, xb, y + level, zb, full)
                break
            for x in range(xa, xb + 1):
                self.stair(x, y + level, za, stair, "south")
                self.stair(x, y + level, zb, stair, "north")
            for z in range(za + 1, zb):
                self.stair(xa, y + level, z, stair, "east")
                self.stair(xb, y + level, z, stair, "west")
            if level > 0 or overhang == 0:
                for x in range(xa + 1, xb):
                    for z in range(za + 1, zb):
                        if self.get(x, y + level, z) is None:
                            self.set(x, y + level, z, AIR)
            level += 1
            if flat_top and xb - xa <= 2 and zb - za <= 2:
                self.fill(xa + 1, y + level - 1, za + 1, xb - 1, y + level - 1, zb - 1, full)
                break
        return y + level - 1

    def flared_roof(self, x1, x2, z1, z2, y, stair, full, overhang=2):
        """Tetto orientale: gronda rialzata agli angoli, poi padiglione."""
        a, b, c, d = x1 - overhang, x2 + overhang, z1 - overhang, z2 + overhang
        for x in range(a, b + 1):
            self.slab(x, y, c, stair)
            self.slab(x, y, d, stair)
        for z in range(c, d + 1):
            self.slab(a, y, z, stair)
            self.slab(b, y, z, stair)
        for x, z in ((a, c), (b, c), (a, d), (b, d)):
            self.set(x, y + 1, z, f"{stair}_slab", type="bottom", waterlogged="false")
        return self.hip_roof(x1, x2, z1, z2, y + 1, stair, full, overhang=overhang - 1)

    # ---- post-processing ----
    def connect_states(self):
        """Calcola north/east/south/west per recinti, pannelli e muretti."""
        updates = {}
        for (x, y, z), (n, props) in self.cells.items():
            fence, pane, wall = _is_fence(n), _is_pane(n), _is_wall(n)
            if not (fence or pane or wall):
                continue
            new = dict(props)
            links = {}
            for d, (dx, dz) in DIRS.items():
                nb = self.get(x + dx, y, z + dz) or AIR
                if fence:
                    ok = (_is_fence(nb) and ("nether" in nb) == ("nether" in n)) or nb.endswith("fence_gate") or _is_solid(nb)
                elif pane:
                    ok = _is_pane(nb) or _is_wall(nb) or _is_solid(nb)
                else:
                    ok = _is_wall(nb) or _is_pane(nb) or nb.endswith("fence_gate") or _is_solid(nb)
                links[d] = ok
            if wall:
                above = self.get(x, y + 1, z) or AIR
                height = "tall" if _is_solid(above) or _is_wall(above) else "low"
                for d, ok in links.items():
                    new[d] = height if ok else "none"
                straight = (links["north"] and links["south"] and not links["east"] and not links["west"]) or \
                           (links["east"] and links["west"] and not links["north"] and not links["south"])
                new["up"] = "false" if straight and above == AIR else "true"
            else:
                for d, ok in links.items():
                    new[d] = "true" if ok else "false"
            new.setdefault("waterlogged", "false")
            updates[(x, y, z)] = (n, new)
        self.cells.update(updates)

    def stair_shapes(self):
        """Forma delle scale (inner/outer) calcolata con la stessa logica di Minecraft."""
        def stair_at(x, y, z):
            n, p = self.cells.get((x, y, z), (None, {}))
            return p if n and n.endswith("_stairs") else None

        def can_take(props, x, y, z, direction):
            dx, dz = DIRS[direction]
            other = stair_at(x + dx, y, z + dz)
            return other is None or other.get("facing") != props.get("facing") or other.get("half") != props.get("half")

        updates = {}
        for (x, y, z), (n, props) in self.cells.items():
            if not n.endswith("_stairs"):
                continue
            facing = props.get("facing", "north")
            half = props.get("half", "bottom")
            shape = "straight"
            dx, dz = DIRS[facing]
            behind = stair_at(x + dx, y, z + dz)
            if behind and behind.get("half", "bottom") == half:
                f1 = behind.get("facing", "north")
                if (f1 in ("north", "south")) != (facing in ("north", "south")) and can_take(props, x, y, z, OPPOSITE[f1]):
                    shape = "outer_left" if f1 == CCW[facing] else "outer_right"
            if shape == "straight":
                front = stair_at(x - dx, y, z - dz)
                if front and front.get("half", "bottom") == half:
                    f2 = front.get("facing", "north")
                    if (f2 in ("north", "south")) != (facing in ("north", "south")) and can_take(props, x, y, z, f2):
                        shape = "inner_left" if f2 == CCW[facing] else "inner_right"
            new = dict(props)
            new["shape"] = shape
            updates[(x, y, z)] = (n, new)
        self.cells.update(updates)

    def connect_redstone(self):
        """Side connections of redstone dust (the game does not recompute them for injected blocks)."""
        sources = ("sculk_sensor", "calibrated_sculk_sensor", "daylight_detector", "lever", "redstone_torch",
                   "redstone_wall_torch", "redstone_block", "target", "observer", "tripwire_hook")
        updates = {}
        for (x, y, z), (n, props) in self.cells.items():
            if n != "minecraft:redstone_wire":
                continue
            links = {}
            for d, (dx, dz) in DIRS.items():
                nb, nprops = self.cells.get((x + dx, y, z + dz), (None, {}))
                ok = False
                if nb == "minecraft:redstone_wire":
                    ok = True
                elif nb in ("minecraft:repeater", "minecraft:observer"):
                    ok = nprops.get("facing") in (d, OPPOSITE[d])
                elif nb == "minecraft:comparator":
                    ok = True  # comparators take side inputs: dust connects on every side
                elif nb and nb.split(":", 1)[1] in sources:
                    ok = True
                elif not _is_solid(self.get(x, y + 1, z)):
                    # dust one block higher on the next block (step up)
                    ok = self.get(x + dx, y + 1, z + dz) == "minecraft:redstone_wire"
                if not ok and not _is_solid(nb) and self.get(x + dx, y - 1, z + dz) == "minecraft:redstone_wire":
                    ok = True  # step down
                links[d] = ok
            linked = [d for d, ok in links.items() if ok]
            if len(linked) == 1:
                links[OPPOSITE[linked[0]]] = True
            if not linked:
                links = {d: True for d in links}
            new = dict(props)
            for d, ok in links.items():
                up = ok and self.get(x + DIRS[d][0], y + 1, z + DIRS[d][1]) == "minecraft:redstone_wire"
                new[d] = "up" if up else "side" if ok else "none"
            new.setdefault("power", "0")
            updates[(x, y, z)] = (n, new)
        self.cells.update(updates)

    def finalize(self):
        self.connect_states()
        self.stair_shapes()
        self.connect_redstone()

    # ---- export ----
    def to_nbt(self):
        self.finalize()
        palette, index = [], {}
        blocks = []
        for (x, y, z) in sorted(self.cells, key=lambda p: (p[1], p[2], p[0])):
            name, props = self.cells[(x, y, z)]
            key = (name, tuple(sorted(props.items())))
            if key not in index:
                index[key] = len(palette)
                entry = TAG_Compound({"Name": TAG_String(name)})
                if props:
                    entry["Properties"] = TAG_Compound({k: TAG_String(v) for k, v in sorted(props.items())})
                palette.append(entry)
            entry = TAG_Compound({
                "pos": TAG_List(3, [TAG_Int(x), TAG_Int(y), TAG_Int(z)]),
                "state": TAG_Int(index[key]),
            })
            if (x, y, z) in self.block_nbt:
                entry["nbt"] = self.block_nbt[(x, y, z)]
            blocks.append(entry)
        root = TAG_Compound()
        root["DataVersion"] = TAG_Int(DATA_VERSION)
        root["size"] = TAG_List(3, [TAG_Int(self.w), TAG_Int(self.h), TAG_Int(self.l)])
        root["palette"] = TAG_List(10, palette)
        root["blocks"] = TAG_List(10, blocks)
        entities = []
        for ent in self.entities:
            ex, ey, ez = ent["pos"]
            nbt = TAG_Compound(ent["nbt"])
            nbt["Rotation"] = TAG_List(5, [TAG_Float(ent.get("yaw", 0.0)), TAG_Float(0.0)])
            entities.append(TAG_Compound({
                "pos": TAG_List(6, [TAG_Double(ex), TAG_Double(ey), TAG_Double(ez)]),
                "blockPos": TAG_List(3, [TAG_Int(math.floor(ex)), TAG_Int(math.floor(ey)), TAG_Int(math.floor(ez))]),
                "nbt": nbt,
            }))
        root["entities"] = TAG_List(10, entities)
        if self.ground_offset or self.technical:
            meta = TAG_Compound({"groundOffset": TAG_Int(self.ground_offset)})
            if self.technical:
                meta["technical"] = TAG_List(11, [TAG_Int_Array(list(box)) for box in self.technical])
            root["MinecraftBuilder"] = meta
        return root

    def to_structure(self):
        """Finalized blocks as a structure_manager.Structure (no file round-trip)."""
        from structure_manager import Structure
        self.finalize()
        blocks = {pos: {"Name": name, "Properties": dict(props)} for pos, (name, props) in self.cells.items()}
        struct = Structure(self.w, self.h, self.l, blocks, DATA_VERSION)
        struct.ground_offset = self.ground_offset
        struct.block_nbt = {p: d for p, d in self.block_nbt.items() if p in self.cells}
        struct.entities = [dict(e) for e in self.entities]
        struct.technical = list(self.technical)
        return struct

    def save(self, path):
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        save_nbt(self.to_nbt(), "", path, compressed=True)
        return path
