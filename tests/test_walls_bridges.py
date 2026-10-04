"""Tests of the walls generator, the drawbridge circuit and the terrain-following bridges."""
import os
import shutil
import sys
import tempfile
import unittest

from fake_world import make_region, make_chunk, GROUND_Y
from redstone_sim import Sim, ToggleSim

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tools"))

import walls
import structure_generators as sg
from mca_codec import ChunkEditor
from nbt_codec import TAG_Compound, TAG_String
from world_editor import World, WorldTerrain, inject_structures
from validate_templates import check_names, Grid


class FlatTerrain:
    """Ground at 64, a river (water surface 62) for 20 <= x <= 40, a hill for z > 200."""

    def height(self, x, z):
        if 20 <= x <= 40:
            return 62
        return 64 + (max(0, z - 200) // 3)

    def is_water(self, x, z):
        return 20 <= x <= 40


def names_ok(structure):
    errors = []
    check_names(Grid(structure), errors)
    return errors


class DrawbridgeCircuitTests(unittest.TestCase):
    def test_each_sensor_raises_all_pistons_and_nothing_latches(self):
        for style in walls.WALL_STYLES:
            b = walls.build_gate(style, "levatoio", lights=True)
            b.finalize()
            sim = Sim(b.cells)
            pistons = [p for p, (n, _) in sim.cells.items() if n == "sticky_piston"]
            road = [p for p, (n, _) in sim.cells.items() if n == "sculk_sensor" and p[1] == walls.GATE_H - 2]
            self.assertEqual(len(pistons), 6)
            self.assertEqual(len(road), 2)
            for sensor in road:
                sim.on_sources = {sensor}
                self.assertTrue(sim.settle())
                self.assertEqual(sum(sim.piston_on(p) for p in pistons), 6, style)
                sim.on_sources = set()
                self.assertTrue(sim.settle())
                self.assertEqual(sum(sim.piston_on(p) for p in pistons), 0, "a loop keeps the bridge up")
                self.assertFalse(any(sim.rep.values()))
            # pistons are out of the sensors' hearing range (8 blocks): no self-triggering
            for s in road:
                for p in pistons:
                    d2 = sum((a - c) ** 2 for a, c in zip(s, p))
                    self.assertGreater(d2, 64)
            self.assertEqual(names_ok(b.to_structure()), [])

    def test_lights_and_gate_types(self):
        for gate in walls.GATE_TYPES:
            s = walls.build_gate("medievale", gate, lights=True).to_structure()
            names = [b["Name"] for b in s.blocks.values()]
            self.assertIn("minecraft:daylight_detector", names)
            self.assertGreaterEqual(names.count("minecraft:redstone_lamp"), 9)
            self.assertEqual("minecraft:sticky_piston" in names, gate == "levatoio")
            self.assertEqual("minecraft:spruce_fence_gate" in names, gate == "portone")
            self.assertEqual(names_ok(s), [])


class LeverToggleTests(unittest.TestCase):
    def test_each_lever_toggles_the_gate(self):
        for gate, count in (("portone", "fence_gate"), ("levatoio", "sticky_piston")):
            b = walls.build_gate("medievale", gate, lights=True)
            b.finalize()
            sim = ToggleSim(b.cells)
            sim.settle()
            observers = sorted(p for p, (n, _) in sim.cells.items() if n == "observer")
            levers = [p for p, (n, _) in sim.cells.items() if n == "lever"]
            self.assertEqual(len(observers), 2)
            self.assertEqual(sorted((x, y - 1, z) for x, y, z in levers), observers)  # each lever on its observer
            parts = [p for p, (n, _) in sim.cells.items() if n.endswith(count)]

            def opened():
                if gate == "portone":
                    return sum(sim.gate_open(g) for g in parts)
                return sum(sim.piston_on(p) for p in parts)

            start = opened()
            self.assertEqual(start, 3 if gate == "portone" else 0)
            expected = start
            for o in (observers[0], observers[1], observers[1], observers[0], observers[1]):
                sim.flip(o)
                expected = (3 - expected) if gate == "portone" else (6 - expected)
                self.assertEqual(opened(), expected, f"{gate}: flipping {o}")
            self.assertEqual(names_ok(b.to_structure()), [])


class WallPlanTests(unittest.TestCase):
    def test_gate_on_slanted_wall_gets_a_straight_stretch(self):
        pts = [(0, 0), (60, 60), (60, 100), (0, 100)]
        plan = walls.plan_walls(pts, True, "medievale", 9, FlatTerrain(), gates=[(30, 30)], gate_type="arco")
        self.assertIn((21, 30), plan["points"])
        self.assertIn((39, 30), plan["points"])
        self.assertEqual(plan["gates"], [(30, 30, "north")])

    def test_closed_perimeter_with_gate(self):
        pts = [(100, 100), (160, 100), (160, 150), (100, 150)]
        plan = walls.plan_walls(pts, True, "medievale", 9, FlatTerrain(), gates=[(130, 99)], gate_type="levatoio")
        self.assertEqual(len(plan["placements"]), 2)
        self.assertEqual(plan["gates"], [(130, 100, "north")])  # outside of the square is north there
        self.assertGreaterEqual(plan["towers"], 4)
        wall = plan["placements"][0]
        self.assertTrue(wall["pillars"])
        s = wall["structure"]
        self.assertEqual(names_ok(s), [])
        # walkway at ground + 9 on the east side, crenellations outside
        tops = [y for (x, y, z), b in s.blocks.items()
                if x + wall["world_x"] == 160 and z + wall["world_z"] == 112 and b["Name"] != "minecraft:air"]
        self.assertEqual(max(tops) + wall["y_coord"], 64 + 9)
        gate = plan["placements"][1]
        g = gate["structure"]
        road = [(x, y, z) for (x, y, z), b in g.blocks.items() if b["Name"] == "minecraft:sticky_piston"]
        self.assertEqual(len(road), 6)

    def test_walkway_rises_at_most_one_block_at_a_time(self):
        pts = [(0, 180), (0, 260)]   # open wall climbing the hill
        plan = walls.plan_walls(pts, False, "nordico", 8, FlatTerrain(), outside_ref=(10, 220))
        wall = plan["placements"][0]
        s = wall["structure"]
        rail = {}
        for (x, y, z), b in s.blocks.items():
            if x + wall["world_x"] == 1 and b["Name"] == "minecraft:deepslate_brick_wall":
                rail[z] = max(rail.get(z, -999), y)
        zs = sorted(rail)
        self.assertGreater(len(zs), 40)
        for z1, z2 in zip(zs, zs[1:]):
            if z2 == z1 + 1:
                self.assertLessEqual(abs(rail[z2] - rail[z1]), 1)
        self.assertGreater(max(rail.values()) - min(rail.values()), 10)   # it does climb the hill

    def test_suggestion_surrounds_buildings(self):
        tmp = tempfile.mkdtemp()
        try:
            make_region(tmp, 0, 0, chunks=[(cx, cz) for cx in range(0, 12) for cz in range(0, 12)])
            world = World(tmp)
            for x in range(60, 80):
                for z in range(70, 90):
                    world.set_block(x, GROUND_Y + 1, z, {"Name": "minecraft:oak_planks"})
            world.save(backup=False)
            world = World(tmp)
            pts, gates, msg = walls.suggest_perimeter(world, (70, 80), radius=60)
            xs = [p[0] for p in pts]
            zs = [p[1] for p in pts]
            self.assertLess(min(xs), 60)
            self.assertGreater(max(xs), 79)
            self.assertLess(min(zs), 70)
            self.assertGreater(max(zs), 89)
            self.assertEqual(len(gates), 1)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class ProfileBridgeTests(unittest.TestCase):
    def test_integrated_bridge_clears_the_water_and_reaches_both_banks(self):
        plan = sg.plan_bridge("stone", (15, 50), (45, 55), FlatTerrain(), integrate=True)
        info = plan["bridge"]
        self.assertEqual(info["axis"], "x")
        self.assertEqual(info["center"], 50)              # straight from the first click
        self.assertEqual(info["deck_a"], 64)               # ends at the level of the banks
        self.assertEqual(info["deck_b"], 64)
        self.assertGreaterEqual(info["deck"], 62 + 4)       # boats pass under the arches
        self.assertTrue(plan["pillar_columns"])
        self.assertEqual(names_ok(plan["structure"]), [])

    def test_classic_bridge_has_ramps_to_lower_bank(self):
        class Banks(FlatTerrain):
            def height(self, x, z):
                return 70 if x < 20 else 62 if x <= 40 else 64

        plan = sg.plan_bridge("wood", (15, 0), (45, 0), Banks(), integrate=False)
        info = plan["bridge"]
        self.assertEqual(info["deck_a"], 70)
        self.assertEqual(info["deck_b"], 65)               # ramp down to the lower bank
        s = plan["structure"]
        stairs = [b for b in s.blocks.values() if b["Name"] == "minecraft:spruce_stairs"]
        self.assertGreaterEqual(len(stairs), 3 * 5)

    def test_continuation_keeps_the_deck_height(self):
        first = sg.plan_bridge("stone", (15, 50), (45, 50), FlatTerrain(), integrate=True)
        second = sg.plan_bridge("wood", (first["bridge"]["b"] + 2, 50), (first["bridge"]["b"] + 20, 50),
                                FlatTerrain(), existing=[first["bridge"]])
        self.assertTrue(second["snapped"])
        self.assertEqual(second["bridge"]["a"], first["bridge"]["b"] + 1)
        self.assertEqual(second["bridge"]["deck_a"], first["bridge"]["deck_b"])
        self.assertEqual(second["bridge"]["style"], "stone")

    def test_bridge_injects_with_piers_down_to_the_bottom(self):
        tmp = tempfile.mkdtemp()
        try:
            make_region(tmp, 0, 0, chunks=[(cx, cz) for cx in range(0, 6) for cz in range(0, 6)])
            world = World(tmp)
            for x in range(30, 50):
                for z in range(0, 96):
                    for y in range(GROUND_Y - 4, GROUND_Y + 1):
                        world.set_block(x, y, z, {"Name": "minecraft:water", "Properties": {"level": "0"}})
            world.save(backup=False)
            world = World(tmp)
            plan = sg.plan_bridge("stone", (25, 40), (55, 40), WorldTerrain(world), integrate=True, world=world)
            stats = inject_structures(world, [plan])
            self.assertGreater(stats["foundation"], 0)
            world.save(backup=False)
            world = World(tmp)
            piers = [x for x in range(30, 50) if (world.get_block_name(x, GROUND_Y - 4, 40) or "").endswith("bricks")]
            self.assertTrue(piers, "piers reach the river bed")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class LargeCutTests(unittest.TestCase):
    def test_cut_larger_than_256_and_reload(self):
        import world_extractor
        from structure_manager import Structure
        tmp = tempfile.mkdtemp()
        try:
            make_region(tmp, 0, 0, chunks=[(cx, cz) for cx in range(19) for cz in range(19)])
            world = World(tmp)
            for x in range(0, 300, 7):
                world.set_block(x, GROUND_Y + 1, x, {"Name": "minecraft:oak_planks"})
            world.save(backup=False)
            done = []
            s, info = world_extractor.extract_area(World(tmp), 0, 0, 299, 299, progress=lambda d, t: done.append(d))
            self.assertEqual((s.width, s.length), (300, 300))
            self.assertEqual(info["blocks"], len(range(0, 300, 7)))
            self.assertEqual(done[-1], len(done))
            path = os.path.join(tmp, "cut.nbt")
            world_extractor.save_structure(s, path)
            back = Structure.load(path)
            self.assertEqual(len(back.blocks), len(s.blocks))
            self.assertEqual(back.blocks[(294, 0, 294)]["Name"], "minecraft:oak_planks")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class BlockEntityTests(unittest.TestCase):
    def test_new_sensors_and_containers_get_block_entities(self):
        chunk = make_chunk(0, 0)
        ed = ChunkEditor(chunk, 0, 0)
        ed.set_block(1, 70, 1, TAG_Compound({"Name": TAG_String("minecraft:daylight_detector")}))
        ed.set_block(2, 70, 2, TAG_Compound({"Name": TAG_String("minecraft:sculk_sensor")}))
        ed.set_block(3, 70, 3, TAG_Compound({"Name": TAG_String("minecraft:stone")}))
        ed.flush()
        ids = sorted(str(be["id"]) for be in chunk["block_entities"])
        self.assertEqual(ids, ["minecraft:daylight_detector", "minecraft:sculk_sensor"])


if __name__ == "__main__":
    unittest.main()
