"""Cuts in 'costruzioni' mode keep the details made of natural blocks and leave out the landscape."""
import os
import shutil
import sys
import tempfile
import unittest

from fake_world import make_region, GROUND_Y

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import world_extractor as wx                     # noqa: E402
from world_editor import World                   # noqa: E402

G = GROUND_Y


def state(name, **props):
    return {"Name": "minecraft:" + name, "Properties": {k: str(v) for k, v in props.items()}}


class CutDetailTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.rd = os.path.join(self.tmp, "region")
        make_region(self.rd, 0, 0, chunks=[(cx, cz) for cx in range(4) for cz in range(4)])
        self.world = World(self.rd)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def put(self, x, y, z, name, **props):
        self.world.set_block(x, y, z, state(name, **props))

    def box(self, x1, z1, x2, z2, y1, y2, name):
        for x in range(x1, x2 + 1):
            for z in range(z1, z2 + 1):
                for y in range(y1, y2 + 1):
                    self.put(x, y, z, name)

    def cut(self, *area, **kw):
        self.world.save(backup=False)
        st, info = wx.extract_area(World(self.rd), *area, **kw)
        x1, z1 = min(area[0], area[2]), min(area[1], area[3])
        y0 = info["y_range"][0]
        return {(x + x1, y + y0, z + z1): b["Name"].split(":")[1] for (x, y, z), b in st.blocks.items()}, info

    def test_roof_garden_ceiling_lamps_and_vines(self):
        # a hut: stone brick walls, a planks roof with a garden on top, glowstone in a raw stone ceiling
        self.box(10, 10, 16, 16, G + 1, G + 4, "stone_bricks")
        self.box(11, 11, 15, 15, G + 1, G + 3, "air")
        self.box(10, 10, 16, 16, G + 5, G + 5, "oak_planks")
        self.box(11, 11, 15, 15, G + 4, G + 4, "stone")           # ceiling of the room
        self.put(13, G + 4, 13, "glowstone")                     # lamp in the ceiling
        self.box(11, 11, 15, 15, G + 6, G + 6, "dirt")            # roof garden
        self.box(11, 11, 15, 15, G + 7, G + 7, "grass_block")
        self.put(12, G + 8, 12, "poppy")
        self.put(9, G + 4, 13, "vine", east="true")               # vine on the west wall...
        self.put(9, G + 3, 13, "vine", east="true")               # ...hanging down
        b, _ = self.cut(5, 5, 21, 21)
        self.assertEqual(b.get((13, G + 4, 13)), "glowstone")
        self.assertEqual(b.get((12, G + 4, 12)), "stone")
        self.assertEqual(b.get((12, G + 7, 12)), "grass_block")
        self.assertEqual(b.get((12, G + 6, 12)), "dirt")
        self.assertEqual(b.get((12, G + 8, 12)), "poppy")
        self.assertEqual(b.get((9, G + 4, 13)), "vine")
        self.assertEqual(b.get((9, G + 3, 13)), "vine")
        # the landscape around stays out
        self.assertNotIn((5, G, 5), b)
        self.assertNotIn((10, G, 10), b)

    def test_crops_stems_and_glowstone_in_the_overworld(self):
        self.box(20, 20, 26, 20, G, G, "farmland")
        for x, crop in zip(range(20, 27), ("beetroots", "wheat", "carrots", "pumpkin_stem", "melon_stem",
                                           "potatoes", "beetroots")):
            self.put(x, G + 1, 20, crop)
        self.put(28, G + 1, 20, "glowstone")                     # a lamp post head on the lawn
        b, _ = self.cut(18, 18, 30, 22)
        for x in range(20, 27):
            self.assertIn((x, G + 1, 20), b, f"coltura in x={x} persa")
        self.assertEqual(b.get((23, G + 1, 20)), "pumpkin_stem")
        self.assertEqual(b.get((28, G + 1, 20)), "glowstone")

    def test_courtyard_closed_by_walls_is_kept(self):
        # castle walls 4 high around a 9x9 courtyard with a 3 wide gate and a tree-less lawn
        for x in range(30, 43):
            for z in range(30, 43):
                if x in (30, 42) or z in (30, 42):
                    self.box(x, z, x, z, G + 1, G + 4, "cobblestone")
        self.box(35, 30, 37, 30, G + 1, G + 2, "air")              # the gate
        self.put(36, G + 1, 36, "poppy")
        b, info = self.cut(26, 26, 46, 46)
        self.assertGreater(info["enclosed_columns"], 0)
        self.assertEqual(b.get((36, G, 36)), "grass_block")       # lawn of the courtyard
        self.assertEqual(b.get((36, G + 1, 36)), "poppy")
        self.assertNotIn((27, G, 27), b)                           # outside the walls: landscape
        self.assertNotIn((36, G - 1, 36), b)                       # only the top of the courtyard ground
        # without the option the courtyard ground is left to the new map
        b2, _ = self.cut(26, 26, 46, 46, enclosures=False)
        self.assertNotIn((36, G, 36), b2)

    def test_sugar_cane_farm_next_to_observers(self):
        for z in range(50, 54):
            self.put(50, G, z, "water")
            self.put(51, G + 1, z, "sugar_cane")
            self.put(51, G + 2, z, "sugar_cane")
            self.put(52, G + 2, z, "observer", facing="west")
            self.put(52, G + 1, z, "stone_bricks")
        b, _ = self.cut(48, 48, 56, 56)
        self.assertEqual(b.get((51, G + 2, 51)), "sugar_cane")
        self.assertEqual(b.get((51, G + 1, 51)), "sugar_cane")
        self.assertEqual(b.get((51, G, 51)), "grass_block")       # the cane needs its block

    def test_desert_sandstone_under_the_sand_is_landscape(self):
        self.box(60, 60, 62, 62, G - 2, G - 1, "sandstone")
        self.box(60, 60, 62, 62, G, G, "sand")
        self.box(61, 61, 61, 61, G + 1, G + 3, "cut_sandstone")    # a sandstone pillar on the sand
        b, _ = self.cut(58, 58, 64, 64)
        self.assertEqual(b.get((61, G + 2, 61)), "cut_sandstone")
        self.assertNotIn((60, G - 1, 60), b)

    def test_dimension_of_region_folders(self):
        self.assertEqual(wx.dimension_of(r"C:\saves\W\region"), "overworld")
        self.assertEqual(wx.dimension_of(r"C:\saves\W\DIM-1\region"), "nether")
        self.assertEqual(wx.dimension_of("/saves/W/dimensions/minecraft/the_end/region"), "end")


if __name__ == "__main__":
    unittest.main()
