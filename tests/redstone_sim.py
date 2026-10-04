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
