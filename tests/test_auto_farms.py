"""The automatic farms: circuits (simulated), plant/water/hopper geometry, validation."""
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "tools"))
sys.path.insert(0, os.path.join(HERE, ".."))

import build_templates                      # noqa: E402
from validate_templates import validate    # noqa: E402
from redstone_sim import AnalogSim          # noqa: E402

REG = build_templates.all_templates()
STEP = {"north": (0, 0, -1), "south": (0, 0, 1), "east": (1, 0, 0), "west": (-1, 0, 0), "down": (0, -1, 0),
        "up": (0, 1, 0)}


def short(n):
    return n.split(":", 1)[-1] if n else None


def build(name):
    b = REG[name]["fn"]()
    b.finalize() if hasattr(b, "finalize") else None
    return b


def cells_named(b, *names):
    return sorted(p for p, (n, _) in b.cells.items() if short(n) in names)


def hopper_end(b, p, limit=400):
    """Where the items of the hopper at p end up: the first block that is not a hopper."""
    seen = set()
    while short(b.cells.get(p, (None, {}))[0]) == "hopper":
        if p in seen or len(seen) > limit:
            raise AssertionError(f"giro chiuso di tramogge da {p}")
        seen.add(p)
        d = STEP[b.cells[p][1]["facing"]]
        p = (p[0] + d[0], p[1] + d[1], p[2] + d[2])
    return p, short(b.cells.get(p, (None, {}))[0])


def in_front(p, facing):
    d = STEP[facing]
    return (p[0] + d[0], p[1] + d[1], p[2] + d[2])


class FarmValidationTests(unittest.TestCase):
    def test_every_farm_validates_without_errors(self):
        for name in REG:
            if not name.startswith("auto_") or name == "auto_warehouse":
                continue
            errors, _, _ = validate(build(name).to_structure())
            self.assertEqual(errors, [], f"{name}: {errors[:5]}")

    def test_every_hopper_leads_to_a_container(self):
        for name in REG:
            if not name.startswith("auto_") or name == "auto_warehouse":
                continue
            b = build(name)
            for h in cells_named(b, "hopper"):
                _, end = hopper_end(b, h)
                self.assertIn(end, ("chest", "furnace", "blast_furnace", "smoker", "stone_bricks",
                                    "white_concrete", "spruce_planks"),
                              f"{name}: la tramoggia {h} porta in {end}")


class PlantFarmTests(unittest.TestCase):
    NAMES = [n for n in REG if n.startswith(("auto_sugar_cane_farm", "auto_bamboo_farm"))]

    def test_observers_see_the_third_block_and_pistons_break_the_second(self):
        for name in self.NAMES:
            b = build(name)
            for o in cells_named(b, "observer"):
                face = b.cells[o][1]["facing"]
                h3 = in_front(o, face)
                piston = (o[0], o[1] - 1, o[2])
                self.assertEqual(short(b.cells[piston][0]), "piston", name)
                self.assertEqual(b.cells[piston][1]["facing"], face)
                h2 = in_front(piston, face)
                self.assertEqual(h2, (h3[0], h3[1] - 1, h3[2]))
                plant = (h2[0], h2[1] - 1, h2[2])
                self.assertIn(short(b.cells[plant][0]), ("sugar_cane", "bamboo"), f"{name}: {plant}")
                self.assertNotIn(h2, b.cells)
                self.assertNotIn(h3, b.cells)
                dirt = (plant[0], plant[1] - 1, plant[2])
                self.assertEqual(short(b.cells[dirt][0]), "dirt")
                water = [q for q in (in_front(dirt, f) for f in ("north", "south", "east", "west"))
                         if short(b.cells.get(q, (None, {}))[0]) == "water"]
                self.assertTrue(water, f"{name}: la terra {dirt} non ha acqua accanto")

    def test_one_observer_fires_its_row_only_and_nothing_runs_idle(self):
        for name in self.NAMES:
            b = build(name)
            pistons = cells_named(b, "piston")
            idle = AnalogSim(b.cells).settle()
            self.assertFalse(any(idle.piston_on(p) for p in pistons), name)
            for o in cells_named(b, "observer")[::5]:
                sim = AnalogSim(b.cells, firing={o}).settle()
                on = {p for p in pistons if sim.piston_on(p)}
                self.assertIn((o[0], o[1] - 1, o[2]), on, name)
                self.assertTrue(all(p[2] == o[2] for p in on), f"{name}: scattano pistoni di altre file")

    def test_the_stream_never_goes_beyond_seven_blocks(self):
        for name in self.NAMES:
            b = build(name)
            for p in cells_named(b, "water"):
                self.assertLessEqual(int(b.cells[p][1]["level"]), 7)
                if b.cells[p][1]["level"] == "7":
                    self.assertEqual(short(b.cells[(p[0], p[1] - 1, p[2])][0]), "hopper",
                                     f"{name}: la corrente finisce in {p} senza tramoggia")


class FruitFarmTests(unittest.TestCase):
    NAMES = [n for n in REG if n.startswith(("auto_melon_farm", "auto_pumpkin_farm"))]

    def test_observers_watch_stems_and_fire_the_pistons_of_their_fruit_spots(self):
        for name in self.NAMES:
            b = build(name)
            pistons = cells_named(b, "piston")
            self.assertFalse(any(AnalogSim(b.cells).settle().piston_on(p) for p in pistons))
            for o in cells_named(b, "observer"):
                self.assertEqual(b.cells[o][1]["facing"], "down")
                stem = (o[0], o[1] - 1, o[2])
                self.assertTrue(short(b.cells[stem][0]).endswith("_stem"), name)
                sim = AnalogSim(b.cells, firing={o}).settle()
                for dz in (-2, 2):
                    piston = (stem[0], stem[1], stem[2] + dz)
                    self.assertEqual(short(b.cells[piston][0]), "piston")
                    self.assertTrue(sim.piston_on(piston), f"{name}: {piston} non scatta")
                    spot = in_front(piston, b.cells[piston][1]["facing"])
                    self.assertEqual(spot, (stem[0], stem[1], stem[2] + dz // 2))
                    self.assertNotIn(spot, b.cells)                  # free for the fruit
                    self.assertEqual(short(b.cells[(spot[0], spot[1] - 1, spot[2])][0]), "dirt")

    def test_farmland_is_wet(self):
        for name in self.NAMES:
            b = build(name)
            waters = cells_named(b, "water")
            for f in cells_named(b, "farmland"):
                near = any(w[1] == f[1] and abs(w[0] - f[0]) <= 4 and abs(w[2] - f[2]) <= 4 for w in waters)
                self.assertTrue(near, f"{name}: terra arata {f} lontana dall'acqua")


class WoolFarmTests(unittest.TestCase):
    def test_eaten_grass_fires_the_shears_of_that_pen_only(self):
        for name in ("auto_wool_farm", "auto_wool_farm_colori", "auto_wool_farm_grande"):
            b = build(name)
            dispensers = cells_named(b, "dispenser")
            self.assertFalse(any(AnalogSim(b.cells).settle().dispenser_on(d) for d in dispensers))
            sheep = {(int(e["pos"][0]), int(e["pos"][1]), int(e["pos"][2])) for e in b.entities
                     if str(e["nbt"]["id"]).endswith("sheep")}
            self.assertEqual(len(sheep), len(dispensers))
            for o in cells_named(b, "observer"):
                grass = in_front(o, b.cells[o][1]["facing"])
                self.assertEqual(short(b.cells[grass][0]), "grass_block")
                sim = AnalogSim(b.cells, firing={o}).settle()
                on = [d for d in dispensers if sim.dispenser_on(d)]
                self.assertEqual(on, [(o[0], o[1] + 1, o[2])], name)
                target = in_front(on[0], b.cells[on[0]][1]["facing"])
                self.assertIn(target, sheep)
                items = b.block_nbt[on[0]]["Items"]
                self.assertTrue(items and all(str(i["id"]).endswith("shears") for i in items))


class SmelterTests(unittest.TestCase):
    def test_every_furnace_gets_ores_from_above_fuel_from_behind_and_empties_below(self):
        for name in ("auto_super_smelter", "auto_super_smelter_grande", "auto_blast_smelter", "auto_smoker_kitchen"):
            b = build(name)
            furnaces = cells_named(b, "furnace", "blast_furnace", "smoker")
            self.assertGreaterEqual(len(furnaces), 6)
            for f in furnaces:
                top = (f[0], f[1] + 1, f[2])
                self.assertEqual(hopper_end(b, top)[0], f)
                line = (f[0], f[1] + 2, f[2])                 # the ore line above feeds the top hopper
                self.assertEqual(short(b.cells[line][0]), "hopper")
                back = (f[0], f[1], f[2] - 1)
                self.assertEqual(hopper_end(b, back)[0], f)
                self.assertEqual(short(b.cells[(back[0], back[1] + 1, back[2])][0]), "hopper")
                below = (f[0], f[1] - 1, f[2])
                self.assertEqual(hopper_end(b, below)[1], "chest")
            # the two input lines start under a chest
            feeders = [h for h in cells_named(b, "hopper") if h[0] == 0]
            for h in feeders:
                self.assertEqual(short(b.cells[(h[0], h[1] + 1, h[2])][0]), "chest")


class LavaAndCactusTests(unittest.TestCase):
    def test_each_cauldron_has_a_dripstone_under_lava_above_it(self):
        for name in ("auto_lava_farm", "auto_lava_farm_grande"):
            b = build(name)
            cauldrons = cells_named(b, "cauldron")
            self.assertTrue(cauldrons)
            for c in cauldrons:
                y = c[1] + 1
                while (c[0], y, c[2]) not in b.cells:
                    y += 1
                tip = (c[0], y, c[2])
                self.assertEqual(short(b.cells[tip][0]), "pointed_dripstone")
                self.assertLessEqual(tip[1] - c[1], 11)
                self.assertTrue(b.cells[(c[0], y + 1, c[2])][0].endswith("stone"))
                self.assertEqual(short(b.cells[(c[0], y + 2, c[2])][0]), "lava")

    def test_cacti_stand_free_on_sand_and_grow_into_a_fence(self):
        for name in ("auto_cactus_farm", "auto_cactus_farm_grande"):
            b = build(name)
            cacti = cells_named(b, "cactus")
            self.assertGreaterEqual(len(cacti), 9)
            for c in cacti:
                self.assertEqual(short(b.cells[(c[0], c[1] - 1, c[2])][0]), "sand")
                for f in ("north", "south", "east", "west"):
                    self.assertNotIn(in_front(c, f), b.cells, f"{name}: il cactus {c} tocca un blocco")
                h2 = (c[0], c[1] + 1, c[2])
                self.assertTrue(any(short(b.cells.get(in_front(h2, f), (None, {}))[0]) == "oak_fence"
                                    for f in ("north", "south", "east", "west")))
                self.assertEqual(short(b.cells[(c[0], 0, c[2])][0]), "hopper")


if __name__ == "__main__":
    unittest.main()
