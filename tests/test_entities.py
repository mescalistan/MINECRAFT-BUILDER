"""Container contents, entities and underground (groundOffset) structures, end to end."""
import os
import shutil
import sys
import tempfile
import unittest

from fake_world import make_region, GROUND_Y

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(HERE, "..", "tools"))

from mca_codec import MCARegion                       # noqa: E402
from structure_manager import Structure                # noqa: E402
from template_builder import Builder                   # noqa: E402
from world_editor import World, inject_structures      # noqa: E402
from validate_templates import validate                # noqa: E402


def small_build():
    b = Builder(6, 6, 6)
    b.fill(0, 0, 0, 5, 0, 5, "stone_bricks")
    b.set(1, 1, 1, "hopper", facing="west", enabled="false")
    b.contents(1, 1, 1, [("iron_ingot", 41)] + [("barrier", 1)] * 4)
    b.chest(3, 1, 1, "south")
    b.contents(3, 1, 1, [(13, "bread", 5)], name="Dispensa")
    b.villager(2, 1, 4, profession="farmer")
    b.mob(4, 1, 4, "zombie", yaw=180)
    return b


class StructureFileTests(unittest.TestCase):
    def test_round_trip_keeps_items_entities_and_ground_offset(self):
        tmp = tempfile.mkdtemp()
        try:
            b = small_build()
            b.ground_offset = 3
            path = b.save(os.path.join(tmp, "t.nbt"))
            s = Structure.load(path)
            self.assertEqual(s.ground_offset, 3)
            items = s.block_nbt[(1, 1, 1)]["Items"]
            self.assertEqual([int(i["count"]) for i in items], [41, 1, 1, 1, 1])
            self.assertEqual(str(s.block_nbt[(3, 1, 1)]["CustomName"]), "Dispensa")
            self.assertEqual(sorted(str(e["nbt"]["id"]) for e in s.entities),
                             ["minecraft:villager", "minecraft:zombie"])
        finally:
            shutil.rmtree(tmp)

    def test_rotation_moves_data_with_blocks(self):
        s = small_build().to_structure()
        for angle in (90, 180, 270):
            r = s.rotate(angle)
            for pos in r.block_nbt:
                self.assertIn(r.get_block(*pos)["Name"], ("minecraft:hopper", "minecraft:chest"))
            for e in r.entities:
                x, y, z = e["pos"]
                self.assertTrue(0 < x < r.width and 0 < z < r.length)
                self.assertEqual(r.get_block(int(x), int(y) - 1, int(z))["Name"], "minecraft:stone_bricks")


class InjectionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.region_dir = os.path.join(self.tmp, "region")
        make_region(self.region_dir, 0, 0, chunks=[(cx, cz) for cx in range(4) for cz in range(4)])

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_items_and_entities_reach_the_world(self):
        world = World(self.region_dir)
        stats = inject_structures(world, [{"structure": small_build().to_structure(), "world_x": 20,
                                           "world_z": 20, "y_coord": GROUND_Y + 1, "name": "t"}])
        self.assertEqual(stats["block_data"], 2)
        self.assertEqual(stats["entities"], 2)
        world.save(backup=True)
        ent_file = os.path.join(self.tmp, "entities", "r.0.0.mca")
        self.assertIn((ent_file, None), world.last_backups)   # undo deletes the new file

        chunk = MCARegion(os.path.join(self.region_dir, "r.0.0.mca")).chunks[(1, 1)][0]
        bes = {(int(b["x"]), int(b["y"]), int(b["z"])): b for b in chunk["block_entities"]}
        hopper = bes[(21, GROUND_Y + 2, 21)]
        self.assertEqual(str(hopper["id"]), "minecraft:hopper")
        self.assertEqual(int(hopper["Items"][0]["count"]), 41)
        self.assertEqual(str(bes[(23, GROUND_Y + 2, 21)]["Items"][0]["id"]), "minecraft:bread")

        ents = MCARegion(ent_file).chunks[(1, 1)][0]
        self.assertEqual(list(ents["Position"]), [1, 1])
        by_id = {str(e["id"]): e for e in ents["Entities"]}
        v = by_id["minecraft:villager"]
        self.assertEqual([float(p) for p in v["Pos"]], [22.5, GROUND_Y + 2.0, 24.5])
        self.assertEqual(len(v["UUID"]), 4)
        self.assertEqual(str(v["VillagerData"]["profession"]), "minecraft:farmer")
        self.assertEqual(int(by_id["minecraft:zombie"]["PersistenceRequired"]), 1)
        self.assertEqual(float(by_id["minecraft:zombie"]["Rotation"][0]), 180.0)

        # a second injection appends to the existing entity chunk and backs the file up
        world = World(self.region_dir)
        inject_structures(world, [{"structure": small_build().to_structure(), "world_x": 20,
                                   "world_z": 20, "y_coord": GROUND_Y + 1, "name": "t"}])
        world.save(backup=True)
        self.assertTrue(any(r == ent_file and b for r, b in world.last_backups))
        self.assertEqual(len(MCARegion(ent_file).chunks[(1, 1)][0]["Entities"]), 4)


class UndergroundValidationTests(unittest.TestCase):
    def test_dug_rooms_are_reachable_through_the_stairs(self):
        b = Builder(7, 8, 7)
        b.ground_offset = 4
        b.fill(1, 0, 1, 5, 3, 5, "air")                 # room 4 layers below the terrain level
        b.fill(1, 4, 1, 5, 4, 5, "stone_bricks")        # its roof is the terrain surface
        for y in range(0, 5):                           # ladder shaft up to the surface
            b.set(3, y, 0, "air")
        b.ladder(3, 0, 4, 0, "south")
        b.fill(3, 0, -1, 3, 4, -1, "stone")
        b.set(1, 0, 1, "chest", facing="south")
        b.lantern(5, 0, 5)
        b.lantern(1, 0, 5)
        errors, _, _ = validate(b.to_structure())
        self.assertEqual([e for e in errors if "senza supporto" in e or "non raggiungibili" in e], [])


if __name__ == "__main__":
    unittest.main()
