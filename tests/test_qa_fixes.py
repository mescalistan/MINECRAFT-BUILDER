"""Regression tests for the issues found by the multi-agent QA (core I/O, cuts, generators, villages)."""
import os
import shutil
import sys
import tempfile
import unittest

from fake_world import make_region, GROUND_Y

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(HERE, "..", "tools"))

import nbt_codec                                                         # noqa: E402
from nbt_codec import TAG_Compound, TAG_String, TAG_List, TAG_Int        # noqa: E402
from mca_codec import MCARegion                                          # noqa: E402
import structure_generators as sg                                        # noqa: E402
import village_generator as vg                                           # noqa: E402
import world_extractor as we                                             # noqa: E402
from world_editor import World, adapt_block_data, inject_structures      # noqa: E402
from template_builder import item_stack                                  # noqa: E402


class NbtTextTests(unittest.TestCase):
    def test_modified_utf8_round_trip(self):
        for text in ("ascii", "città", "emoji \U0001F600", "nul\x00inside"):
            raw = nbt_codec.encode_mutf8(text)
            self.assertNotIn(b"\x00", raw)
            self.assertNotIn(b"\xf0", raw)                 # Java never writes 4-byte sequences
            self.assertEqual(nbt_codec.decode_mutf8(raw), text)

    def test_fixed_records_and_generic_records_parse_the_same(self):
        tag = TAG_Compound({"size": TAG_List(3, [TAG_Int(2), TAG_Int(1), TAG_Int(1)]),
                            "palette": TAG_List(10, [TAG_Compound({"Name": TAG_String("minecraft:stone")})]),
                            "blocks": TAG_List(10, [
                                TAG_Compound({"pos": TAG_List(3, [TAG_Int(0), TAG_Int(0), TAG_Int(0)]),
                                              "state": TAG_Int(0)}),
                                TAG_Compound({"state": TAG_Int(0),                       # other key order
                                              "pos": TAG_List(3, [TAG_Int(1), TAG_Int(0), TAG_Int(0)])})])})
        _, blocks = nbt_codec.parse_structure_bytes(nbt_codec.nbt_to_bytes(tag))
        self.assertEqual(blocks, [(0, 0, 0, 0), (1, 0, 0, 0)])


class ItemFormatTests(unittest.TestCase):
    def test_items_are_converted_for_old_worlds(self):
        data = TAG_Compound({"Items": TAG_List(10, [item_stack("stick", 1, 2, name="Filtro")])})
        old = adapt_block_data(data, 3700)                   # 1.20.4
        item = old["Items"][0]
        self.assertEqual(int(item["Count"]), 1)
        self.assertEqual(int(item["Slot"]), 2)
        self.assertEqual(str(item["tag"]["display"]["Name"]), '"Filtro"')
        self.assertNotIn("components", item)
        mid = adapt_block_data(data, 4000)                   # 1.21.1: JSON name inside components
        self.assertEqual(str(mid["Items"][0]["components"]["minecraft:custom_name"]), '"Filtro"')
        self.assertIs(adapt_block_data(data, 4325), data)    # 1.21.5+: as written


class ReadOnlyRegionTests(unittest.TestCase):
    def test_a_region_read_with_skipped_tags_cannot_be_saved(self):
        tmp = tempfile.mkdtemp()
        try:
            region = make_region(os.path.join(tmp, "region"), 0, 0, chunks=[(0, 0)])
            r = MCARegion(region.file_path)
            r.skip_tags = frozenset(("block_entities",))
            chunk, _ = r.chunks[(0, 0)]
            self.assertNotIn("block_entities", chunk)
            with self.assertRaises(RuntimeError):
                r.save()
        finally:
            shutil.rmtree(tmp)


class CutTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.rd = os.path.join(self.tmp, "region")
        make_region(self.rd, 0, 0, chunks=[(cx, cz) for cx in range(3) for cz in range(3)])

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def build(self, blocks):
        world = World(self.rd)
        for (x, y, z), name in blocks.items():
            world.set_block(x, y, z, TAG_Compound({"Name": TAG_String("minecraft:" + name)}))
        world.save(backup=False)

    def test_building_blocks_are_kept_and_ambiguous_ones_on_request(self):
        g = GROUND_Y
        self.build({(5, g + 1, 5): "oak_planks", (6, g + 1, 5): "bamboo_planks", (7, g + 1, 5): "flower_pot",
                    (8, g + 1, 5): "obsidian", (9, g + 1, 5): "sandstone", (10, g + 1, 5): "snow_block",
                    (11, g + 1, 5): "oak_log"})                         # a lone log: landscape
        names = lambda st: {b["Name"].split(":")[1] for b in st.blocks.values()}     # noqa: E731
        st, _ = we.extract_area(World(self.rd), 4, 4, 12, 6)
        kept = names(st)
        for n in ("oak_planks", "bamboo_planks", "flower_pot", "obsidian", "sandstone"):
            self.assertIn(n, kept)
        self.assertNotIn("snow_block", kept)
        self.assertNotIn("oak_log", kept)
        st, _ = we.extract_area(World(self.rd), 4, 4, 12, 6, keep_ambiguous=True)
        self.assertIn("snow_block", names(st))

    def test_chest_contents_survive_a_cut(self):
        world = World(self.rd)
        world.set_block(5, GROUND_Y + 1, 5, TAG_Compound({"Name": TAG_String("minecraft:chest")}))
        world.set_block(5, GROUND_Y + 1, 6, TAG_Compound({"Name": TAG_String("minecraft:stone_bricks")}))
        world.set_block_data(5, GROUND_Y + 1, 5, TAG_Compound({"Items": TAG_List(10, [item_stack("bread", 3, 0)])}))
        world.save(backup=False)
        st, _ = we.extract_area(World(self.rd), 4, 4, 7, 7)
        path = we.save_structure(st, os.path.join(self.tmp, "cut.nbt"))
        from structure_manager import Structure
        back = Structure.load(path)
        items = [d["Items"] for d in back.block_nbt.values()]
        self.assertEqual([int(i[0]["count"]) for i in items], [3])


class Flat:
    def __init__(self, h=64, water=None):
        self.h, self.water = h, water or (lambda x, z: False)

    def height(self, x, z):
        return 62 if self.water(x, z) else self.h

    def is_water(self, x, z):
        return self.water(x, z)

    def is_tree(self, x, z):
        return False


class GeneratorTests(unittest.TestCase):
    def test_suspension_bridge_has_ramps_down_to_the_banks(self):
        river = lambda x, z: 20 <= x <= 40          # noqa: E731
        plan = sg.plan_bridge("suspension", (15, 30), (45, 30), Flat(64, river))
        self.assertEqual(len(plan["ramps"]), 2)
        deck = plan["bridge"]["deck"]
        for ramp in plan["ramps"]:
            tops = [ramp["y_coord"] + y for (x, y, z), b in ramp["structure"].blocks.items()
                    if b["Name"].endswith("polished_andesite")]
            self.assertEqual(max(tops), deck - 1)    # first step right below the deck
            self.assertEqual(min(tops), 64)          # last step on the bank

    def test_village_stops_at_the_river(self):
        river = lambda x, z: 20 <= x <= 23          # noqa: E731

        def load(name):
            from structure_manager import Structure
            return Structure.load(os.path.join(HERE, "..", "templates", name + ".nbt"))
        r = vg.generate_village((0, 0), "pianura", "medio", Flat(64, river), load, seed=1)
        self.assertFalse([c for c in r["path_cells"] if c[0] > 23 and abs(c[1]) <= 1])
        self.assertFalse([p for p in r["placements"] if p["world_x"] > 23])


if __name__ == "__main__":
    unittest.main()
