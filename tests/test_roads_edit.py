"""Roads, and walls/roads that are edited or demolished after being built (footprint + restore)."""
import os
import shutil
import sys
import tempfile
import unittest

from fake_world import make_region, GROUND_Y

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))

import roads                                                     # noqa: E402
import walls                                                     # noqa: E402
from world_editor import (World, WorldTerrain, RecordedTerrain, inject_structures, footprint,   # noqa: E402
                          footprint_to_text, footprint_from_text)


def snapshot(world, x1, z1, x2, z2, y1, y2):
    return {(x, y, z): world.get_block_name(x, y, z)
            for x in range(x1, x2 + 1) for z in range(z1, z2 + 1) for y in range(y1, y2 + 1)}


class BuildAndDemolishTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.region_dir = os.path.join(self.tmp, "region")
        make_region(self.region_dir, 0, 0, chunks=[(cx, cz) for cx in range(10) for cz in range(10)])

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def build(self, plan_fn):
        world = World(self.region_dir)
        terrain = WorldTerrain(world)
        plan = plan_fn(terrain)
        self.assertTrue(plan["placements"], plan["report"])
        fp = footprint(plan["placements"], terrain)
        inject_structures(world, plan["placements"])
        world.save(backup=False)
        return fp

    def demolish(self, fp):
        world = World(self.region_dir)
        stats = inject_structures(world, [{"kind": "demolish", "footprint": fp, "name": "x"}])
        world.save(backup=False)
        return stats

    def check_restored(self, before, area):
        world = World(self.region_dir)
        after = snapshot(world, *area)
        diff = [p for p in before if before[p] != after[p]]
        self.assertEqual(diff, [], f"{len(diff)} blocchi diversi dal terreno originale, es. "
                                   f"{[(p, before[p], after[p]) for p in diff[:3]]}")

    def test_road_demolition_restores_the_ground(self):
        area = (20, 20, 120, 60, GROUND_Y - 4, GROUND_Y + 8)
        before = snapshot(World(self.region_dir), *area)
        fp = self.build(lambda t: roads.plan_road([(30, 40), (70, 40), (100, 50)], "lastricata", 3, t))
        self.assertGreater(len(fp["columns"]), 100)
        changed = snapshot(World(self.region_dir), *area)
        self.assertNotEqual(before, changed)
        self.assertGreater(self.demolish(footprint_from_text(footprint_to_text(fp)))["demolished"], 100)
        self.check_restored(before, area)

    def test_wall_demolition_restores_the_ground(self):
        area = (30, 30, 110, 110, GROUND_Y - 6, GROUND_Y + 16)
        before = snapshot(World(self.region_dir), *area)
        pts = [(50, 50), (90, 50), (90, 90), (50, 90)]
        fp = self.build(lambda t: walls.plan_walls(pts, True, "medievale", 8, t, gates=[(70, 90)],
                                                   gate_type="arco", lights=False, outside_ref=(70, 130)))
        self.demolish(fp)
        self.check_restored(before, area)

    def test_recorded_terrain_ignores_the_build_itself(self):
        fp = self.build(lambda t: roads.plan_road([(30, 40), (70, 40)], "ciottoli", 5, t))
        live = WorldTerrain(World(self.region_dir))
        recorded = RecordedTerrain(live, [fp])
        x, z = 50, 40
        self.assertEqual(recorded.height(x, z), GROUND_Y)          # the original grass level
        self.assertEqual(recorded.original_name(x, GROUND_Y, z), "minecraft:grass_block")
        self.assertEqual(recorded.original_name(x, GROUND_Y + 1, z), "minecraft:air")
        self.assertEqual(recorded.height(200, 200), live.height(200, 200))   # outside: the live world

    def test_editing_a_built_road_moves_it(self):
        area = (20, 20, 110, 80, GROUND_Y - 4, GROUND_Y + 8)
        before = snapshot(World(self.region_dir), *area)
        old_fp = self.build(lambda t: roads.plan_road([(30, 40), (90, 40)], "ciottoli", 3, t, lamps=False))
        # the user drags the end point 20 blocks south
        world = World(self.region_dir)
        terrain = RecordedTerrain(WorldTerrain(world), [old_fp])
        plan = roads.plan_road([(30, 40), (60, 40), (90, 60)], "ciottoli", 3, terrain, lamps=False)
        new_fp = footprint(plan["placements"], terrain)
        inject_structures(world, [{"kind": "demolish", "footprint": old_fp, "name": "old"}] + plan["placements"])
        world.save(backup=False)
        after = snapshot(World(self.region_dir), *area)
        new_cols = {(c[0], c[1]) for c in new_fp["columns"]}
        old_only = [(c[0], c[1]) for c in old_fp["columns"] if (c[0], c[1]) not in new_cols]
        self.assertGreater(len(old_only), 20)
        for x, z in old_only:                         # the abandoned stretch is grass again
            for y in range(area[4], area[5] + 1):
                self.assertEqual(after[(x, y, z)], before[(x, y, z)], (x, y, z))
        self.assertEqual(after[(85, GROUND_Y + 1, 40)], "minecraft:air")
        shared = [c for c in new_fp["columns"] if (c[0], c[1]) == (40, 40)][0]
        self.assertEqual(shared[2], GROUND_Y)          # planned on the original ground, not on the old road
        self.assertNotEqual(after[(75, GROUND_Y, 50)], "minecraft:grass_block")   # the new stretch is built

    def test_footprint_text_round_trip(self):
        fp = {"columns": [[1, 2, 63, 60, 70, 0, 60, 0, 0, 0, 0], [-5, 7, 62, 62, 66, -1, 63, 0, 0]],
              "surfaces": ["minecraft:sand"], "v": 2}
        self.assertEqual(footprint_from_text(footprint_to_text(fp)), fp)
        self.assertEqual(footprint_from_text(None), {"columns": [], "surfaces": []})
        old = {"cols": "1,2,63,60,70,0,0,0,0,0", "surfaces": ["minecraft:sand"]}      # records before v2
        self.assertEqual(footprint_from_text(old)["v"], 1)


class RoadSnapTests(unittest.TestCase):
    def test_ends_snap_to_a_road_built_with_the_program(self):
        pts, msgs = roads.snap_endpoints([(10, 3), (40, 3), (40, 30)], existing=[[(0, 0), (100, 0)]])
        self.assertEqual(pts[0], (10, 0))
        self.assertEqual(pts[-1], (40, 30))
        self.assertEqual(len(msgs), 1)


if __name__ == "__main__":
    unittest.main()
