"""Very large structures: packed blocks, streaming files, chunk-by-chunk and parallel injection."""
import os
import random
import shutil
import sys
import tempfile
import unittest

from fake_world import make_region, GROUND_Y

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))

import structure_manager as sm                                       # noqa: E402
import world_editor as we_mod                                        # noqa: E402
import world_extractor as wx                                         # noqa: E402
from mca_codec import MCARegion, ChunkEditor                         # noqa: E402
from nbt_codec import TAG_Compound, TAG_String                       # noqa: E402
from structure_manager import Structure, PackedBlocks                # noqa: E402
from world_editor import World, inject_structures                    # noqa: E402

STATES = [{"Name": "minecraft:stone_bricks", "Properties": {}},
          {"Name": "minecraft:oak_stairs", "Properties": {"facing": "north", "half": "bottom",
                                                          "shape": "straight", "waterlogged": "false"}},
          {"Name": "minecraft:air", "Properties": {}},
          {"Name": "minecraft:chest", "Properties": {"facing": "east", "type": "single", "waterlogged": "false"}},
          {"Name": "minecraft:glass", "Properties": {}}]


def random_structure(w=70, h=12, l=50, seed=3):
    rng = random.Random(seed)
    blocks = {}
    for x in range(w):
        for z in range(l):
            top = rng.randrange(2, h)
            for y in range(top):
                blocks[(x, y, z)] = STATES[rng.choice((0, 0, 0, 1, 2, 4))]
    blocks[(5, 1, 5)] = STATES[3]
    s = Structure(w, h, l, blocks, 3955)
    s.block_nbt = {(5, 1, 5): TAG_Compound({"CustomName": TAG_String("Cassa")})}
    return s


def as_packed(s):
    states = STATES
    idx = {id(b): i for i, b in enumerate(states)}
    from array import array
    xs, ys, zs, si = array("i"), array("i"), array("i"), array("i")
    for (x, y, z), b in s.blocks.items():
        xs.append(x)
        ys.append(y)
        zs.append(z)
        si.append(idx[id(b)])
    p = Structure(s.width, s.height, s.length, PackedBlocks(xs, ys, zs, si, list(states), 0, s.width, s.length), 3955)
    p.block_nbt = dict(s.block_nbt)
    return p


class PackedTests(unittest.TestCase):
    def test_packed_rotation_equals_dict_rotation(self):
        s = random_structure()
        p = as_packed(s)
        for angle in (90, 180, 270):
            a, b = p.rotate(angle), s.rotate(angle)
            self.assertEqual(dict(a.blocks.items()), b.blocks)
            self.assertEqual((a.width, a.length), (b.width, b.length))
        self.assertEqual(dict(p.rotate(90).rotate(90).rotate(90).rotate(90).blocks.items()), s.blocks)

    def test_streaming_file_round_trip(self):
        tmp = tempfile.mkdtemp()
        try:
            p = as_packed(random_structure())
            for rot in (0, 90):
                src = p.rotate(rot) if rot else p
                path = wx.save_structure(src, os.path.join(tmp, f"big{rot}.nbt"))
                old_min = sm.PACKED_MIN_BLOCKS
                sm.PACKED_MIN_BLOCKS = 10                     # read back packed too
                try:
                    back = Structure.load(path)
                finally:
                    sm.PACKED_MIN_BLOCKS = old_min
                self.assertTrue(getattr(back.blocks, "packed", False))
                self.assertEqual(dict(back.blocks.items()), dict(src.blocks.items()))
                self.assertEqual(len(back.block_nbt), 1)
        finally:
            shutil.rmtree(tmp)


class InjectionPathTests(unittest.TestCase):
    def world_blocks(self, rd):
        region = MCARegion(os.path.join(rd, "r.0.0.mca"))
        out = {}
        for key in region.chunks:
            nbt, _ = region.chunks[key]
            ed = ChunkEditor(nbt, *key)
            for sy in range(-4, 20):
                e = ed._load(sy)
                if e:
                    names = [str(b.get("Name")) + str(sorted((b.get("Properties") or {}).items())) for b in e[0]]
                    out[(key, sy)] = [names[i] for i in e[1]]
            out[(key, "be")] = sorted((int(b["x"]), int(b["y"]), int(b["z"]), str(b["id"]))
                                      for b in nbt.get("block_entities", []))
        return out

    def inject(self, structure, parallel):
        tmp = tempfile.mkdtemp()
        rd = os.path.join(tmp, "region")
        make_region(rd, 0, 0, chunks=[(cx, cz) for cx in range(10) for cz in range(10)])
        world = World(rd)
        stats = inject_structures(world, [{"structure": structure, "world_x": 13, "world_z": 9,
                                           "y_coord": GROUND_Y + 3, "name": "t"}], blend=True, parallel=parallel)
        world.save(backup=False)
        return tmp, rd, stats

    def test_parallel_and_sequential_injection_are_identical(self):
        s = random_structure()
        old = we_mod.PARALLEL_MIN_BLOCKS
        we_mod.PARALLEL_MIN_BLOCKS = 1000          # force the parallel path on a small structure
        tmps = []
        try:
            results = []
            for structure, parallel in ((s, False), (s, True), (as_packed(s).rotate(90), True),
                                        (s.rotate(90), False)):
                tmp, rd, stats = self.inject(structure, parallel)
                tmps.append(tmp)
                results.append((self.world_blocks(rd), stats))
        finally:
            we_mod.PARALLEL_MIN_BLOCKS = old
            for t in tmps:
                shutil.rmtree(t, ignore_errors=True)
        (seq, st_seq), (par, st_par), (rot_par, _), (rot_seq, _) = results
        self.assertEqual(seq, par)
        self.assertEqual(st_seq, st_par)
        self.assertEqual(rot_par, rot_seq)
        self.assertGreater(st_seq["foundation"], 0)          # floating columns got their foundations
        chest = [be for key, v in seq.items() if key[1] == "be" for be in v if be[3] == "minecraft:chest"]
        self.assertEqual(len(chest), 1)


if __name__ == "__main__":
    unittest.main()
