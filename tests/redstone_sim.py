"""
Minimal steady-state redstone simulator for the tests: dust, repeaters, sculk sensors and
daylight detectors as sources, solid blocks powered by repeaters, pistons and lamps.
It ignores timing; it is meant to check wiring (what gets powered) and the absence of loops
(signals that keep themselves on after the source turns off).
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tools"))
import blockinfo as bi  # noqa: E402

DIRS = {"north": (0, -1), "south": (0, 1), "east": (1, 0), "west": (-1, 0)}
OPP = {"north": "south", "south": "north", "east": "west", "west": "east"}


def _short(n):
    return n.split(":", 1)[-1] if n else None


class Sim:
    def __init__(self, cells):
        """cells: {(x, y, z): (name, props)} as in template_builder.Builder.cells."""
        self.cells = {p: (_short(n), dict(pr)) for p, (n, pr) in cells.items()}
        self.on_sources = set()
        self.dust = {p: 0 for p, (n, _) in self.cells.items() if n == "redstone_wire"}
        self.rep = {p: False for p, (n, _) in self.cells.items() if n == "repeater"}

    def name(self, p):
        return self.cells.get(p, (None, {}))[0]

    def solid(self, p):
        n = self.name(p)
        return n is not None and bi.is_full_solid(n) and n not in ("redstone_lamp",) or n == "redstone_lamp"

    def source_power(self, p):
        return 15 if p in self.on_sources else 0

    def rep_output_target(self, p):
        facing = self.cells[p][1]["facing"]       # input side
        dx, dz = DIRS[OPP[facing]]
        return (p[0] + dx, p[1], p[2] + dz)

    def rep_input_pos(self, p):
        dx, dz = DIRS[self.cells[p][1]["facing"]]
        return (p[0] + dx, p[1], p[2] + dz)

    def strongly_powered(self, p):
        """Solid block powered by a repeater pointing into it, or a sensor on top of it."""
        if not self.solid(p):
            return False
        for r, on in self.rep.items():
            if on and self.rep_output_target(r) == p:
                return True
        above = (p[0], p[1] + 1, p[2])
        return self.name(above) == "sculk_sensor" and above in self.on_sources

    def dust_links(self, p):
        x, y, z = p
        props = self.cells[p][1]
        out = []
        for d, (dx, dz) in DIRS.items():
            if props.get(d, "none") == "none":
                continue
            for q in ((x + dx, y, z + dz), (x + dx, y + 1, z + dz), (x + dx, y - 1, z + dz)):
                if q in self.dust:
                    out.append(q)
        return out

    def step(self):
        changed = False
        # dust
        new = {}
        for p in self.dust:
            x, y, z = p
            power = 0
            for d, (dx, dz) in DIRS.items():
                q = (x + dx, y, z + dz)
                n = self.name(q)
                if n in ("sculk_sensor", "daylight_detector"):
                    power = max(power, self.source_power(q))
                if n == "repeater" and self.rep[q] and self.rep_output_target(q) == p:
                    power = 15
                if self.solid(q) and self.strongly_powered(q):
                    power = 15
            for q in ((x, y - 1, z), (x, y + 1, z)):
                if self.solid(q) and self.strongly_powered(q):
                    power = 15
            for q in self.dust_links(p):
                power = max(power, self.dust[q] - 1)
            new[p] = power
        if new != self.dust:
            changed = True
            self.dust = new
        # repeaters
        for p in self.rep:
            q = self.rep_input_pos(p)
            n = self.name(q)
            on = (q in self.dust and self.dust[q] > 0) or (n == "sculk_sensor" and q in self.on_sources) or \
                 (n == "repeater" and self.rep[q] and self.rep_output_target(q) == p) or \
                 (self.solid(q) and self.strongly_powered(q))
            if on != self.rep[p]:
                self.rep[p] = on
                changed = True
        return changed

    def settle(self, max_steps=200):
        for _ in range(max_steps):
            if not self.step():
                return True
        return False

    def piston_on(self, p):
        """Piston activated by an adjacent (not front) strongly powered block or dust on/into it."""
        facing = self.cells[p][1].get("facing", "up")
        x, y, z = p
        neighbours = [(x + dx, y, z + dz) for dx, dz in DIRS.values()] + [(x, y - 1, z), (x, y + 1, z)]
        front = (x, y + 1, z) if facing == "up" else (x, y - 1, z) if facing == "down" else \
            (x + DIRS[facing][0], y, z + DIRS[facing][1])
        for q in neighbours:
            if q == front:
                continue
            if self.strongly_powered(q):
                return True
            if self.name(q) in ("sculk_sensor", "daylight_detector") and q in self.on_sources:
                return True
        return False

    def lamp_on(self, p):
        x, y, z = p
        for q in [(x + dx, y, z + dz) for dx, dz in DIRS.values()] + [(x, y - 1, z), (x, y + 1, z)]:
            if self.name(q) in ("sculk_sensor", "daylight_detector") and q in self.on_sources:
                return True
            if q in self.dust and self.dust[q] > 0 and q == (x, y + 1, z):
                return True
            if self.strongly_powered(q):
                return True
        return self.strongly_powered(p)


class ToggleSim(Sim):
    """
    Sim with the extra components of the lever toggle: observers (pulsed by the test), a copper
    bulb that toggles on every rising edge, a comparator reading it, redstone torches standing on
    blocks, fence gates.
    """

    def __init__(self, cells):
        super().__init__(cells)
        self.pulsing = set()
        self.bulbs = {p: False for p, (n, _) in self.cells.items() if n.endswith("copper_bulb")}
        self.bulb_powered = {p: False for p in self.bulbs}
        self.torches = {p: pr.get("lit", "true") == "true"
                        for p, (n, pr) in self.cells.items() if n == "redstone_torch"}

    @staticmethod
    def _dir(facing):
        return {"up": (0, 1, 0), "down": (0, -1, 0), "north": (0, 0, -1), "south": (0, 0, 1),
                "east": (1, 0, 0), "west": (-1, 0, 0)}[facing]

    def observer_back(self, p):
        dx, dy, dz = self._dir(self.cells[p][1]["facing"])
        return (p[0] - dx, p[1] - dy, p[2] - dz)

    def comparator_on(self, p):
        rear = self.rep_input_pos(p)
        return self.bulbs.get(rear, False)

    def solid(self, p):
        n = self.name(p)
        if n in ("observer", "comparator", "repeater", "redstone_wire", "redstone_torch", "lever"):
            return False
        return super().solid(p) or (n is not None and n.endswith("copper_bulb"))

    def strongly_powered(self, p):
        if not self.solid(p):
            return False
        if super().strongly_powered(p):
            return True
        for o in self.pulsing:
            if self.observer_back(o) == p:
                return True
        for c, (n, _) in self.cells.items():
            if n == "comparator" and self.comparator_on(c) and self.rep_output_target(c) == p:
                return True
        below = (p[0], p[1] - 1, p[2])
        return self.torches.get(below, False)

    def weakly_powered(self, p):
        """Solid block powered by dust on top of it or pointing into it."""
        x, y, z = p
        above = (x, y + 1, z)
        if above in self.dust and self.dust[above] > 0:
            return True
        for d, (dx, dz) in DIRS.items():
            q = (x - dx, y, z - dz)          # dust west of p points east into p, etc.
            if q in self.dust and self.dust[q] > 0 and self.cells[q][1].get(d, "none") != "none":
                return True
        return False

    def step(self):
        changed = False
        new = {}
        for p in self.dust:
            x, y, z = p
            power = 0
            for d, (dx, dz) in DIRS.items():
                q = (x + dx, y, z + dz)
                n = self.name(q)
                if n in ("sculk_sensor", "daylight_detector") and q in self.on_sources:
                    power = 15
                if n == "repeater" and self.rep[q] and self.rep_output_target(q) == p:
                    power = 15
                if n == "comparator" and self.comparator_on(q) and self.rep_output_target(q) == p:
                    power = 15
                if n == "redstone_torch" and self.torches.get(q):
                    power = 15
                if self.solid(q) and self.strongly_powered(q):
                    power = 15
            for o in self.pulsing:
                if self.observer_back(o) == p:
                    power = 15
            for q in ((x, y - 1, z), (x, y + 1, z)):
                if self.solid(q) and self.strongly_powered(q):
                    power = 15
            for q in self.dust_links(p):
                power = max(power, self.dust[q] - 1)
            new[p] = power
        if new != self.dust:
            changed = True
            self.dust = new
        for p in self.rep:
            q = self.rep_input_pos(p)
            n = self.name(q)
            on = (q in self.dust and self.dust[q] > 0) or (n == "sculk_sensor" and q in self.on_sources) or \
                 (n == "repeater" and self.rep[q] and self.rep_output_target(q) == p) or \
                 (self.solid(q) and self.strongly_powered(q)) or (q in self.pulsing and self.observer_back(q) == p)
            if on != self.rep[p]:
                self.rep[p] = on
                changed = True
        for t in self.torches:
            support = (t[0], t[1] - 1, t[2])
            lit = not (self.strongly_powered(support) or self.weakly_powered(support))
            if lit != self.torches[t]:
                self.torches[t] = lit
                changed = True
        return changed

    def bulb_input(self, p):
        for r, on in self.rep.items():
            if on and self.rep_output_target(r) == p:
                return True
        return any(self.observer_back(o) == p for o in self.pulsing)

    def flip(self, observer):
        """A lever on 'observer' is flipped: the observer sends a pulse."""
        self.pulsing = {observer}
        self.settle()
        for b in self.bulbs:
            powered = self.bulb_input(b)
            if powered and not self.bulb_powered[b]:
                self.bulbs[b] = not self.bulbs[b]
            self.bulb_powered[b] = powered
        self.settle()
        self.pulsing = set()
        self.settle()
        for b in self.bulbs:
            self.bulb_powered[b] = self.bulb_input(b)
        self.settle()

    def gate_open(self, p):
        x, y, z = p
        for q in [(x + dx, y, z + dz) for dx, dz in DIRS.values()] + [(x, y - 1, z), (x, y + 1, z)]:
            if self.strongly_powered(q) or (self.name(q) == "redstone_torch" and self.torches.get(q)):
                return True
        return False


class LeverSim(Sim):
    """
    Sim with levers (switched by the test) and comparators (compare / subtract), for the gates
    opened by two levers. Levers strongly power the block they are attached to and power the
    dust next to them.
    """

    def __init__(self, cells):
        super().__init__(cells)
        self.levers = {p: False for p, (n, _) in self.cells.items() if n == "lever"}
        self.comp = {p: 0 for p, (n, _) in self.cells.items() if n == "comparator"}

    def solid(self, p):
        n = self.name(p)
        if n in ("comparator", "repeater", "redstone_wire", "lever", "sticky_piston", "iron_bars"):
            return False
        return super().solid(p)

    def lever_support(self, p):
        props = self.cells[p][1]
        face = props.get("face", "wall")
        if face == "floor":
            return (p[0], p[1] - 1, p[2])
        if face == "ceiling":
            return (p[0], p[1] + 1, p[2])
        dx, dz = DIRS[props.get("facing", "north")]
        return (p[0] - dx, p[1], p[2] - dz)

    def strongly_powered(self, p):
        if not self.solid(p):
            return False
        if super().strongly_powered(p):
            return True
        for lv, on in self.levers.items():
            if on and self.lever_support(lv) == p:
                return True
        for c, v in self.comp.items():
            if v > 0 and self.rep_output_target(c) == p:
                return True
        return False

    def _side_cells(self, p):
        facing = self.cells[p][1]["facing"]
        if facing in ("north", "south"):
            return [(p[0] + 1, p[1], p[2]), (p[0] - 1, p[1], p[2])]
        return [(p[0], p[1], p[2] + 1), (p[0], p[1], p[2] - 1)]

    def _signal_into(self, q, target):
        """Power that cell q sends into the diode at target (dust level, repeater/comparator output)."""
        n = self.name(q)
        if q in self.dust:
            return self.dust[q]
        if n == "repeater" and self.rep[q] and self.rep_output_target(q) == target:
            return 15
        if n == "comparator" and self.rep_output_target(q) == target:
            return self.comp[q]
        if n == "lever" and self.levers[q]:
            return 15
        if self.solid(q) and self.strongly_powered(q):
            return 15
        return 0

    def step(self):
        changed = False
        new = {}
        for p in self.dust:
            x, y, z = p
            power = 0
            for d, (dx, dz) in DIRS.items():
                q = (x + dx, y, z + dz)
                n = self.name(q)
                if n == "repeater" and self.rep[q] and self.rep_output_target(q) == p:
                    power = 15
                if n == "comparator" and self.rep_output_target(q) == p:
                    power = max(power, self.comp[q])
                if n == "lever" and self.levers[q]:
                    power = 15
                if n in ("sculk_sensor", "daylight_detector") and q in self.on_sources:
                    power = 15
                if self.solid(q) and self.strongly_powered(q):
                    power = 15
            for q in ((x, y - 1, z), (x, y + 1, z)):
                if self.solid(q) and self.strongly_powered(q):
                    power = 15
            for q in self.dust_links(p):
                power = max(power, self.dust[q] - 1)
            new[p] = power
        if new != self.dust:
            changed = True
            self.dust = new
        for p in self.rep:
            on = self._signal_into(self.rep_input_pos(p), p) > 0
            if on != self.rep[p]:
                self.rep[p] = on
                changed = True
        for p in self.comp:
            rear = self._signal_into(self.rep_input_pos(p), p)
            side = max(self._signal_into(q, p) for q in self._side_cells(p))
            if self.cells[p][1].get("mode") == "subtract":
                out = max(0, rear - side)
            else:
                out = rear if rear >= side else 0
            if out != self.comp[p]:
                self.comp[p] = out
                changed = True
        return changed


# ---------------------------------------------------------------------------
# Analog simulator: comparators reading containers, torches (standing and wall), levers,
# daylight detectors, pistons (with quasi-connectivity) and hopper locking.
# ---------------------------------------------------------------------------

CONTAINER_SLOTS = {"hopper": 5, "dropper": 9, "dispenser": 9, "chest": 27, "trapped_chest": 27, "barrel": 27}
NOT_CONDUCTORS = ("piston", "sticky_piston", "observer", "daylight_detector", "comparator", "repeater",
                  "redstone_wire", "lever", "redstone_torch", "redstone_wall_torch", "hopper", "redstone_lamp")
ALL6 = ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1))


def stack_size(item):
    item = _short(item)
    if item in ("ender_pearl", "snowball", "egg", "honey_bottle", "armor_stand", "bucket") or \
            item.endswith(("_sign", "_banner")):
        return 16
    if item.endswith(("_sword", "_pickaxe", "_axe", "_shovel", "_hoe", "_helmet", "_chestplate",
                      "_leggings", "_boots", "potion", "_bed", "shulker_box", "bow", "trident")):
        return 1
    return 64


def container_signal(name, items):
    """Comparator output reading a container: floor(1 + 14 * fullness), 0 if empty (Java formula)."""
    if not items:
        return 0
    slots = CONTAINER_SLOTS.get(_short(name), 27)
    fullness = sum(count / stack_size(item) for item, count in items) / slots
    return int(1 + 14 * fullness)


class AnalogSim:
    """
    Steady state of a circuit with analog signals. cells: Builder.cells; contents: {pos: [(item, count)]};
    daylight: {pos: power} of the daylight detectors; levers: {pos: bool} overrides the lever states.
    Iterates (dust relaxation, comparators, torches) until nothing changes; raises on oscillation.
    """

    def __init__(self, cells, contents=None, daylight=None, levers=None, firing=None, hives=None):
        """
        firing: observers sending their pulse right now (the steady state during the pulse);
        hives: {pos: honey level 0-5} of the beehives read by comparators. Buttons are levers held down.
        """
        self.cells = {p: (_short(n), dict(pr)) for p, (n, pr) in cells.items()}
        self.hives = dict(hives or {})
        self.firing = set(firing or ())
        self.rep = {p: False for p, (n, _) in self.cells.items() if n == "repeater"}
        self.contents = {p: list(v) for p, v in (contents or {}).items()}
        self.daylight = dict(daylight or {})
        self.levers = {p: pr.get("powered") == "true" for p, (n, pr) in self.cells.items()
                       if n == "lever" or n.endswith("_button")}
        self.levers.update(levers or {})
        self.dust = {p: 0 for p, (n, _) in self.cells.items() if n == "redstone_wire"}
        self.comp = {p: 0 for p, (n, _) in self.cells.items() if n == "comparator"}
        self.torch = {p: pr.get("lit", "true") == "true" for p, (n, pr) in self.cells.items()
                      if n in ("redstone_torch", "redstone_wall_torch")}

    # ---- geometry ----
    def name(self, p):
        return self.cells.get(p, (None, {}))[0]

    def props(self, p):
        return self.cells.get(p, (None, {}))[1]

    def conductor(self, p):
        n = self.name(p)
        return (n is not None and bi.is_full_solid(n) and not bi.is_transparent_full(n)
                and n not in NOT_CONDUCTORS and n not in CONTAINER_SLOTS)

    def torch_attached(self, t):
        if self.name(t) == "redstone_wall_torch":
            dx, dz = DIRS[OPP[self.props(t)["facing"]]]
            return (t[0] + dx, t[1], t[2] + dz)
        return (t[0], t[1] - 1, t[2])

    def lever_attached(self, lv):
        pr = self.props(lv)
        face = pr.get("face", "wall")
        if face == "floor":
            return (lv[0], lv[1] - 1, lv[2])
        if face == "ceiling":
            return (lv[0], lv[1] + 1, lv[2])
        dx, dz = DIRS[OPP[pr["facing"]]]
        return (lv[0] + dx, lv[1], lv[2] + dz)

    def observer_out(self, o):
        """Cell an observer pulses into: the side opposite to its face."""
        f = self.props(o).get("facing", "north")
        d = {"up": (0, 1, 0), "down": (0, -1, 0), "north": (0, 0, -1), "south": (0, 0, 1),
             "east": (1, 0, 0), "west": (-1, 0, 0)}[f]
        return (o[0] - d[0], o[1] - d[1], o[2] - d[2])

    def observer_watches(self, o):
        f = self.props(o).get("facing", "north")
        d = {"up": (0, 1, 0), "down": (0, -1, 0), "north": (0, 0, -1), "south": (0, 0, 1),
             "east": (1, 0, 0), "west": (-1, 0, 0)}[f]
        return (o[0] + d[0], o[1] + d[1], o[2] + d[2])

    def diode_out(self, p):
        """Cell a comparator outputs into (its 'facing' is the input side)."""
        dx, dz = DIRS[OPP[self.props(p)["facing"]]]
        return (p[0] + dx, p[1], p[2] + dz)

    def dust_points_into(self, d, q):
        """Dust d powers the block below it and the horizontal neighbour its shape points to."""
        if q == (d[0], d[1] - 1, d[2]):
            return True
        for side, (dx, dz) in DIRS.items():
            if (d[0] + dx, d[1], d[2] + dz) == q:
                return self.props(d).get(side, "none") != "none"
        return False

    # ---- power ----
    def strong(self, b):
        """Strong power of a conductor block (it can power dust next to it)."""
        if not self.conductor(b):
            return 0
        best = 0
        for dx, dy, dz in ALL6:
            q = (b[0] + dx, b[1] + dy, b[2] + dz)
            n = self.name(q)
            if (n == "lever" or (n or "").endswith("_button")) and self.levers.get(q) and self.lever_attached(q) == b:
                best = 15
            elif n in ("redstone_torch", "redstone_wall_torch") and self.torch.get(q) \
                    and q == (b[0], b[1] - 1, b[2]):
                best = 15                         # a torch strongly powers the block above it
            elif n == "comparator" and self.diode_out(q) == b:
                best = max(best, self.comp[q])
            elif n == "repeater" and self.rep.get(q) and self.diode_out(q) == b:
                best = 15
            elif n == "observer" and q in self.firing and self.observer_out(q) == b:
                best = 15
        return best

    def weak(self, b):
        """Power from dust on top of or pointing into the conductor block b."""
        if not self.conductor(b):
            return 0
        best = 0
        for dx, dy, dz in ALL6:
            q = (b[0] + dx, b[1] + dy, b[2] + dz)
            if q in self.dust and self.dust[q] > 0 and dy >= 0 and self.dust_points_into(q, b):
                best = max(best, self.dust[q])
        return best

    def block_power(self, b):
        return max(self.strong(b), self.weak(b))

    def source_into(self, q, target):
        """Power a non-dust neighbour q sends to the component or dust at 'target'."""
        n = self.name(q)
        if n == "lever" or (n or "").endswith("_button"):
            return 15 if self.levers.get(q) else 0
        if n in ("redstone_torch", "redstone_wall_torch"):
            return 15 if self.torch.get(q) and self.torch_attached(q) != target else 0
        if n == "daylight_detector":
            return self.daylight.get(q, 0)
        if n == "comparator":
            return self.comp[q] if self.diode_out(q) == target else 0
        if n == "repeater":
            return 15 if self.rep.get(q) and self.diode_out(q) == target else 0
        if n == "observer":
            return 15 if q in self.firing and self.observer_out(q) == target else 0
        return 0

    def component_power(self, c, exclude=None):
        """Power reaching a mechanism at c (piston, hopper, lamp). exclude: a cell to ignore (QC)."""
        best = 0
        for dx, dy, dz in ALL6:
            q = (c[0] + dx, c[1] + dy, c[2] + dz)
            if q == exclude:
                continue
            if q in self.dust:
                if self.dust[q] > 0 and (dy == 1 or (dy == 0 and self.dust_points_into(q, c))):
                    best = max(best, self.dust[q])
                continue
            best = max(best, self.source_into(q, c))
            if self.conductor(q):
                best = max(best, self.block_power(q))
        return best

    def piston_on(self, p):
        if self.component_power(p) > 0:
            return True
        above = (p[0], p[1] + 1, p[2])
        return self.component_power(above, exclude=p) > 0      # quasi-connectivity

    def hopper_locked(self, p):
        return self.component_power(p) > 0

    def dispenser_on(self, p):
        """Dispensers and droppers fire like pistons (quasi-connectivity included)."""
        return self.piston_on(p)

    def repeater_input(self, r):
        dx, dz = DIRS[self.props(r)["facing"]]
        q = (r[0] + dx, r[1], r[2] + dz)
        if q in self.dust:
            return self.dust[q]
        return max(self.source_into(q, r), self.block_power(q) if self.conductor(q) else 0)

    # ---- relaxation ----
    def _dust_sources(self, d):
        best = 0
        for dx, dy, dz in ALL6:
            q = (d[0] + dx, d[1] + dy, d[2] + dz)
            if q in self.dust:
                continue
            best = max(best, self.source_into(q, d))
            if self.conductor(q):
                best = max(best, self.strong(q))
        return best

    def _dust_links(self, d):
        x, y, z = d
        out = []
        for side, (dx, dz) in DIRS.items():
            if self.props(d).get(side, "none") == "none":
                continue
            for q, between in (((x + dx, y, z + dz), None),
                               ((x + dx, y + 1, z + dz), (x, y + 1, z)),
                               ((x + dx, y - 1, z + dz), (x + dx, y, z + dz))):
                if q in self.dust and (between is None or not self.conductor(between)):
                    out.append(q)
        return out

    def _relax_dust(self):
        src = {d: self._dust_sources(d) for d in self.dust}
        links = {d: self._dust_links(d) for d in self.dust}
        power = {d: 0 for d in self.dust}
        changed = True
        while changed:
            changed = False
            for d in self.dust:
                v = max([src[d]] + [power[q] - 1 for q in links[d]])
                if v > power[d]:
                    power[d] = v
                    changed = True
        return power

    def comparator_rear(self, c):
        dx, dz = DIRS[self.props(c)["facing"]]
        q = (c[0] + dx, c[1], c[2] + dz)
        n = self.name(q)
        if n in ("beehive", "bee_nest"):
            return self.hives.get(q, 0)
        if n in CONTAINER_SLOTS:
            return container_signal(n, self.contents.get(q))
        if q in self.dust:
            return self.dust[q]
        return max(self.source_into(q, c), self.block_power(q) if self.conductor(q) else 0)

    def comparator_side(self, c):
        fx, fz = DIRS[self.props(c)["facing"]]
        best = 0
        for dx, dz in ((fz, fx), (-fz, -fx)):
            q = (c[0] + dx, c[1], c[2] + dz)
            if q in self.dust and self.dust_points_into(q, c):
                best = max(best, self.dust[q])
            elif self.name(q) == "comparator" and self.diode_out(q) == c:
                best = max(best, self.comp[q])
        return best

    def settle(self, max_steps=100):
        seen = []
        for _ in range(max_steps):
            self.dust = self._relax_dust()
            changed = False
            for c in self.comp:
                rear, side = self.comparator_rear(c), self.comparator_side(c)
                if self.props(c).get("mode") == "subtract":
                    out = max(0, rear - side)
                else:
                    out = rear if rear >= side else 0
                if out != self.comp[c]:
                    self.comp[c] = out
                    changed = True
            for r in self.rep:
                on = self.repeater_input(r) > 0
                if on != self.rep[r]:
                    self.rep[r] = on
                    changed = True
            for t in self.torch:
                lit = self.block_power(self.torch_attached(t)) == 0
                if lit != self.torch[t]:
                    self.torch[t] = lit
                    changed = True
            if not changed:
                return self
            state = (tuple(sorted(self.torch.items())), tuple(sorted(self.comp.items())),
                     tuple(sorted(self.rep.items())))
            if state in seen:
                raise RuntimeError("il circuito oscilla (clock non previsto)")
            seen.append(state)
        raise RuntimeError("il circuito non si stabilizza")
