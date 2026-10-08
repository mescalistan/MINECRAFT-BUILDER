"""The land around pasted structures: hills with stairs, islands with beaches, floating boats."""
import os
import shutil
import sys
import tempfile
import unittest

from fake_world import make_region, GROUND_Y

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))

import landscape                                     # noqa: E402
from nbt_codec import TAG_Compound, TAG_String       # noqa: E402
from structure_manager import Structure              # noqa: E402
from world_editor import World, inject_structures   # noqa: E402

TEMPLATES = os.path.join(HERE, "..", "templates")
G = GROUND_Y


def st(name, **p):
    s = TAG_Compound({"Name": TAG_String("minecraft:" + name)})
    if p:
        s["Properties"] = TAG_Compound({k: TAG_String(str(v)) for k, v in p.items()})
    return s


class LandscapeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.rd = os.path.join(self.tmp, "region")
        make_region(self.rd, 0, 0, chunks=[(cx, cz) for cx in range(6) for cz in range(6)])

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def lake(self, depth=5):
        world = World(self.rd)
        for x in range(4, 92):
            for z in range(4, 92):
                for y in range(G - depth + 1, G + 1):
                    world.set_block(x, y, z, st("water", level=0))
                world.set_block(x, G - depth, z, st("sand"))
        world.save(backup=False)

    def place(self, template, dy, **extra):
        world = World(self.rd)
        s = Structure.load(os.path.join(TEMPLATES, template + ".nbt"))
        ox, oz = (96 - s.width) // 2, (96 - s.length) // 2
        item = {"structure": s, "world_x": ox, "world_z": oz, "y_coord": G + 1 + dy, "name": template}
        item.update(extra)
        stats = inject_structures(world, [item], blend="natural")
        world.save(backup=False)
        return World(self.rd), s, ox, oz, stats

    def column_top(self, world, x, z):
        top = world.surface_y(x, z)
        return top, world.get_block_name(x, top, z)

    def test_raised_house_gets_a_hill_and_stairs(self):
        world, s, ox, oz, stats = self.place("starter_cottage", 8)
        self.assertGreater(stats["landscape"], 1000)
        g0 = G + 8
        # right next to the house the ground is up at its floor, farther out it slopes down to the plain
        mid_z = oz + s.length // 2
        near = world.ground_y(ox - 2, mid_z, g0 + 5)
        far = world.ground_y(ox - 40, mid_z, g0 + 5)
        self.assertGreaterEqual(near, g0 - 2)
        self.assertEqual(far, G)
        # a flight of stairs somewhere around the house
        stairs = [(x, y, z) for x in range(ox - 25, ox + s.width + 25) for z in range(oz - 25, oz + s.length + 25)
                  for y in range(G + 1, g0 + 2)
                  if (world.get_block_name(x, y, z) or "").endswith("_stairs")
                  and not (ox <= x < ox + s.width and oz <= z < oz + s.length)]
        self.assertGreaterEqual(len(stairs), 5)
        ys = sorted({y for _, y, _ in stairs})
        self.assertGreaterEqual(ys[-1] - ys[0], 4, "la scalinata deve scendere lungo la collina")
        # the hill is grass on top
        top, name = self.column_top(world, ox - 3, oz - 3)
        self.assertTrue(name.endswith(("grass_block", "short_grass", "tall_grass", "dandelion", "poppy",
                                       "oxeye_daisy", "cornflower", "azure_bluet", "oak_leaves", "oak_log",
                                       "stone", "andesite", "cobblestone", "_stairs", "lantern")), name)

    def test_house_on_water_gets_an_island_with_a_beach(self):
        self.lake()
        world, s, ox, oz, stats = self.place("starter_cottage", 1, water_mode="island")
        self.assertGreater(stats["landscape"], 500)
        # under the house: ground up to the water level + 1
        cx, cz = ox + s.width // 2, oz + s.length // 2
        self.assertFalse((world.get_block_name(cx, G, cz) or "").endswith("water"))
        # around it a dry sandy beach, then the water again far away
        sand = sum(1 for x in range(ox - 8, ox + s.width + 8) for z in range(oz - 8, oz + s.length + 8)
                   if world.get_block_name(x, G + 1, z) == "minecraft:sand")
        self.assertGreater(sand, 30)
        self.assertEqual(world.get_block_name(10, G, 10), "minecraft:water")

    def test_boat_floats_and_its_hull_is_dried(self):
        self.lake()
        world, s, ox, oz, stats = self.place("sea_boat", -3, water_mode="float")
        # nothing built around it
        self.assertEqual(world.get_block_name(ox - 3, G, oz + s.length // 2), "minecraft:water")
        # the inside of the hull, below the water level, is air
        inside = [(x, z) for x in range(s.width) for z in range(s.length) if (x, 2, z) not in s.blocks
                  and 2 <= z <= s.length - 3 and 2 <= x <= s.width - 3]
        self.assertTrue(inside)
        for x, z in inside:
            self.assertEqual(world.get_block_name(ox + x, G - 2 + 2, oz + z), "minecraft:air")

    def test_biome_theme_and_stair_material(self):
        self.assertEqual(landscape.theme_of("minecraft:desert"), "desert")
        self.assertEqual(landscape.theme_of("minecraft:snowy_taiga"), "snowy")
        self.assertEqual(landscape.theme_of("minecraft:old_growth_spruce_taiga"), "taiga")
        self.assertEqual(landscape.theme_of("minecraft:sunflower_plains"), "flower")
        self.assertEqual(landscape.theme_of(None), "plains")
        keep = Structure.load(os.path.join(TEMPLATES, "castle_keep.nbt"))
        self.assertIn(landscape.stair_material(keep, "plains"), landscape._MATERIALS)
        world = World(self.rd)
        self.assertIsNotNone(landscape.biome_at(world, 5, G, 5))


if __name__ == "__main__":
    unittest.main()
