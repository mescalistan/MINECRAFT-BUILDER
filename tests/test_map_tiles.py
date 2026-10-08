"""Tests of the map tiles (surface colours, game structures, disk cache)."""
import os
import shutil
import sys
import tempfile
import time
import unittest

from fake_world import make_region, GROUND_Y

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import map_tiles as mt
from mca_codec import MCARegion, ChunkEditor
from nbt_codec import TAG_Compound, TAG_List, TAG_String, TAG_Int, TAG_Int_Array


class MapTilesTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.region_dir = os.path.join(self.tmp, "region")
        make_region(self.region_dir, 0, 0, chunks=[(0, 0), (1, 0)], new_encoding=True)
        region = MCARegion(os.path.join(self.region_dir, "r.0.0.mca"))
        chunk, ts = region.chunks[(0, 0)]
        ed = ChunkEditor(chunk, 0, 0)
        ed.set_block(5, GROUND_Y, 5, {"Name": "minecraft:water"})       # one block of water on dirt
        ed.set_block(8, GROUND_Y + 1, 8, {"Name": "minecraft:short_grass"})  # seen through
        ed.set_block(10, GROUND_Y + 1, 10, {"Name": "minecraft:oak_planks"})
        ed.flush()
        chunk["structures"] = TAG_Compound({"starts": TAG_Compound({
            "minecraft:village_plains": TAG_Compound({
                "id": TAG_String("minecraft:village_plains"),
                "Children": TAG_List(10, [TAG_Compound({"BB": TAG_Int_Array([0, 60, 0, 40, 80, 30])}),
                                          TAG_Compound({"BB": TAG_Int_Array([-10, 60, 5, 12, 70, 50])})]),
            })}), "References": TAG_Compound()})
        region.chunks[(0, 0)] = (chunk, ts)
        region.save()
        self.path = os.path.join(self.region_dir, "r.0.0.mca")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def px(self, tile, x, z):
        i = z * mt.TILE + x
        return tile["heights"][i], tuple(tile["rgb"][i * 3:i * 3 + 3]), tile["depth"][i]

    def test_detailed_tile(self):
        tile = mt.build_tile(self.path, detailed=True)
        self.assertTrue(tile["detailed"])
        h, rgb, depth = self.px(tile, 1, 1)
        self.assertEqual(h, GROUND_Y)
        self.assertEqual(rgb, mt.surface_rgb("minecraft:grass_block"))
        self.assertEqual(depth, 0)
        self.assertEqual(self.px(tile, 8, 8)[1], mt.surface_rgb("minecraft:grass_block"))  # grass tuft ignored
        self.assertEqual(self.px(tile, 10, 10)[1], mt.surface_rgb("minecraft:oak_planks"))
        self.assertEqual(self.px(tile, 10, 10)[0], GROUND_Y + 1)
        h, rgb, depth = self.px(tile, 5, 5)
        self.assertEqual(depth, 1)
        self.assertEqual(rgb, mt.surface_rgb("minecraft:dirt"))  # water bottom
        self.assertEqual(self.px(tile, 40, 3)[0], mt.NO_DATA)    # chunk (2, 0) not generated
        self.assertEqual(tile["structures"], [("minecraft:village_plains", -10, 0, 40, 50)])
        self.assertEqual(len(mt.shade(tile)), mt.TILE * mt.TILE * 4)

    def test_fast_tile_has_heights_only(self):
        tile = mt.build_tile(self.path, detailed=False)
        self.assertFalse(tile["detailed"])
        self.assertEqual(self.px(tile, 20, 2)[0], GROUND_Y)
        self.assertEqual(tile["structures"], [])

    def test_cache_roundtrip_and_invalidation(self):
        cache = mt.TileCache(self.region_dir, root=os.path.join(self.tmp, "cache"))
        self.assertIsNone(cache.load(0, 0, self.path))
        tile = mt.build_tile(self.path)
        cache.save(0, 0, self.path, tile)
        back = cache.load(0, 0, self.path)
        self.assertEqual(back["heights"], tile["heights"])
        self.assertEqual(back["rgb"], tile["rgb"])
        self.assertEqual(back["structures"], tile["structures"])
        # the region file changes (e.g. after an injection): the cached tile is no longer valid
        later = time.time() + 10
        os.utime(self.path, (later, later))
        self.assertIsNone(cache.load(0, 0, self.path))

    def test_stale_cache_is_still_available(self):
        cache = mt.TileCache(self.region_dir, root=os.path.join(self.tmp, "cache"))
        cache.save(0, 0, self.path, mt.build_tile(self.path))
        later = time.time() + 10
        os.utime(self.path, (later, later))
        self.assertIsNone(cache.load(0, 0, self.path))
        tile, stamp = cache.load_any(0, 0)            # shown at once while the region is redrawn
        self.assertIsNotNone(tile)
        self.assertEqual(len(tile["image"]), mt.TILE * mt.TILE * 4)
        self.assertNotEqual(stamp, mt.TileCache._stamp(self.path))

    def test_incremental_redraw_reads_only_changed_chunks(self):
        root = os.path.join(self.tmp, "cache")
        mt.render_job(self.path, 0, 0, self.region_dir, True, root)
        # the game saves chunk (1, 0) again, with a new block on top
        region = MCARegion(self.path)
        chunk, ts = region.chunks[(1, 0)]
        ed = ChunkEditor(chunk, 1, 0)
        ed.set_block(3, GROUND_Y + 1, 3, {"Name": "minecraft:gold_block"})
        ed.flush()
        region.chunks[(1, 0)] = (chunk, ts + 5)
        region.save()
        reads = []
        orig = mt._render_chunk
        mt._render_chunk = lambda r, k, d: (reads.append(k), orig(r, k, d))[1]
        try:
            again = mt.render_job(self.path, 0, 0, self.region_dir, True, root)
        finally:
            mt._render_chunk = orig
        self.assertEqual(reads, [(1, 0)])
        full = mt.build_tile(self.path)
        self.assertEqual(again["heights"], full["heights"])
        self.assertEqual(again["image"], mt.shade(full))
        self.assertEqual(full["heights"][3 * mt.TILE + 16 + 3], GROUND_Y + 1)
        self.assertEqual(again["structures"], full["structures"])

    def test_old_palette_encoding_draws_the_same(self):
        other = os.path.join(self.tmp, "old")
        make_region(other, 0, 0, chunks=[(0, 0), (1, 0)], new_encoding=False)
        new_dir = os.path.join(self.tmp, "new")
        make_region(new_dir, 0, 0, chunks=[(0, 0), (1, 0)], new_encoding=True)
        a = mt.build_tile(os.path.join(other, "r.0.0.mca"))
        b = mt.build_tile(os.path.join(new_dir, "r.0.0.mca"))
        self.assertEqual(a["rgb"], b["rgb"])
        self.assertEqual(a["heights"], b["heights"])
        self.assertEqual(self.px(a, 1, 1)[1], mt.surface_rgb("minecraft:grass_block"))

    def test_list_regions_and_labels(self):
        self.assertEqual(list(mt.list_regions(self.region_dir)), [(0, 0)])
        self.assertEqual(mt.region_coords("r.-3.12.mca"), (-3, 12))
        self.assertIsNone(mt.region_coords("c.1.2.mcc"))
        self.assertEqual(mt.structure_label("minecraft:village_plains"), "Villaggio (pianura)")
        self.assertEqual(mt.structure_label("mymod:sky_tower"), "Sky tower")


if __name__ == "__main__":
    unittest.main()
