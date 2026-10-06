"""
Hub with the item sorter and iron farm (tools/templates/hub_farm.py): circuits checked with the analog
simulator, golem spawning and the villager -> zombie sight line checked against the game's rules.
"""
import math
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(HERE, "..", "tools"))

from redstone_sim import AnalogSim, container_signal                 # noqa: E402
import blockinfo as bi                                               # noqa: E402
from templates import hub_farm as hf                                 # noqa: E402
from validate_templates import validate                              # noqa: E402


def _items(data):
    return [(str(i["id"]), int(i["count"])) for i in data.get("Items", [])]


def _short(n):
    return n.split(":", 1)[-1] if n else None


class SorterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.b = hf.underground_hub()
        cls.b.finalize()
        cls.contents = {p: _items(d) for p, d in cls.b.block_nbt.items()}

    def sim(self, extra=None):
        contents = dict(self.contents)
        contents.update(extra or {})
        return AnalogSim(self.b.cells, contents).settle()

    def test_filter_contents_give_signal_two(self):
        for sl in self.b.sorter_slices:
            items = self.contents[sl["F"]]
            self.assertEqual(items[0], ("minecraft:" + sl["item"], hf.FILTER_COUNT))
            self.assertEqual(len(items), 5)
            self.assertEqual(container_signal("hopper", items), 2)
            self.assertEqual(container_signal("hopper", [(items[0][0], 42)] + items[1:]), 3)

    def test_idle_sorter_keeps_every_bottom_hopper_locked(self):
        sim = self.sim()
        for sl in self.b.sorter_slices:
            self.assertEqual(sim.comp[sl["C"]], 2)
            self.assertEqual([sim.dust[d] for d in sl["dust"]], [2, 1, 0])
            self.assertTrue(sim.torch[sl["T"]], sl)
            self.assertTrue(sim.hopper_locked(sl["L"]), sl)
            self.assertFalse(sim.hopper_locked(sl["F"]), sl)
        chain = [p for p, (n, pr) in self.b.cells.items() if n.endswith("hopper") and p[2] == hf.HUB_ZF
                 and p[1] == 3]
        self.assertGreater(len(chain), 30)
        self.assertFalse(any(sim.hopper_locked(p) for p in chain))

    def test_one_more_item_unlocks_only_its_slice(self):
        for k, sl in enumerate(self.b.sorter_slices):
            items = self.contents[sl["F"]]
            sim = self.sim({sl["F"]: [(items[0][0], hf.FILTER_COUNT + 1)] + items[1:]})
            self.assertEqual(sim.comp[sl["C"]], 3)
            self.assertFalse(sim.torch[sl["T"]])
            self.assertFalse(sim.hopper_locked(sl["L"]), f"fetta {k} resta bloccata")
            for other in self.b.sorter_slices:
                if other is not sl:
                    self.assertTrue(sim.hopper_locked(other["L"]), f"la fetta {k} sblocca anche {other['item']}")

    def test_barrels_are_named(self):
        for sl in self.b.sorter_slices:
            self.assertTrue(str(self.b.block_nbt[sl["barrel"]]["CustomName"]))


class IronFarmCircuitTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.b = hf.iron_farm()
        cls.b.finalize()
        cls.c = hf._farm_coords()

    def piston(self, day, lever):
        sim = AnalogSim(self.b.cells, daylight={self.c["daylight"]: 15 if day else 0},
                        levers={self.c["lever"]: lever}).settle()
        return sim.piston_on(self.c["piston"])

    def test_zombie_visible_by_day_hidden_at_night(self):
        self.assertFalse(self.piston(day=True, lever=False))
        self.assertTrue(self.piston(day=False, lever=False))

    def test_lever_locks_the_farm_day_and_night(self):
        self.assertTrue(self.piston(day=True, lever=True))
        self.assertTrue(self.piston(day=False, lever=True))

    def test_weak_dawn_light_already_opens_the_slot(self):
        sim = AnalogSim(self.b.cells, daylight={self.c["daylight"]: 1}, levers={self.c["lever"]: False}).settle()
        self.assertFalse(sim.piston_on(self.c["piston"]))

    def test_entities(self):
        ids = sorted(str(e["nbt"]["id"]) for e in self.b.entities)
        self.assertEqual(ids, ["minecraft:villager"] * 3 + ["minecraft:zombie"])
        for e in self.b.entities:
            self.assertEqual(int(e["nbt"]["PersistenceRequired"]), 1)


# ---- golem spawning (SpawnUtil.Strategy.LEGACY_IRON_GOLEM, 1.21) ----
NOT_ON = ("glass", "tinted_glass", "glass_pane", "ice", "frosted_ice", "glowstone", "sea_lantern", "beacon",
          "conduit", "tnt", "cobweb", "cactus")


def _excluded(n):
    return n in NOT_ON or n.endswith(("_stained_glass", "_stained_glass_pane", "_leaves"))


def _is_solid(n):
    """BlockState.isSolid(): collision box big enough (slabs, stairs, beds, pistons, walls... count)."""
    if n is None or n in bi.AIR_LIKE or n in ("water", "lava", "bubble_column"):
        return False
    if n.endswith(("_sign", "torch", "redstone_wire", "_carpet", "lever", "_button", "lantern", "chain",
                   "rail", "_pressure_plate", "flower_pot")) or n in ("ladder", "vine", "tripwire"):
        return False
    return True


def _collider(n):
    return n is not None and _is_solid(n)


class IronFarmSpawnTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.b = hf.iron_farm()
        cls.b.finalize()
        cls.c = hf._farm_coords()

    def name(self, x, y, z):
        if not self.b.inside(x, y, z):
            return None if y >= 0 else "grass_block"    # around the farm: open air above flat ground
        cell = self.b.cells.get((x, y, z))
        if cell is None:
            return None if y >= 0 else "grass_block"
        return _short(cell[0])

    def spawn_spot(self, vx, vy, vz, dx, dz):
        """First position from the top where the game would try to place the golem, or None."""
        x, z = vx + dx, vz + dz
        for y in range(vy + 6, vy - 7, -1):
            here, below = self.name(x, y, z), self.name(x, y - 1, z)
            if below is not None and _excluded(below):
                continue
            if (here is None or here in ("air", "cave_air", "water", "lava", "bubble_column")) and _is_solid(below):
                return (x, y, z)
        return None

    def fits(self, p):
        x, y, z = p
        return not any(_collider(self.name(x + i, y + j, z + k))
                       for i in (-1, 0, 1) for j in (0, 1, 2) for k in (-1, 0, 1))

    def test_golems_can_only_spawn_on_the_platform(self):
        p0, p1 = self.c["platform"]
        V = hf.FARM_V
        for vx, vz in self.c["villagers"]:
            good = 0
            for dx in range(-8, 9):
                for dz in range(-8, 9):
                    spot = self.spawn_spot(vx, V, vz, dx, dz)
                    if spot is None or not self.fits(spot):
                        continue
                    x, y, z = spot
                    on_platform = p0 <= x <= p1 and p0 <= z <= p1 and y == 9 and self.name(x, y, z) == "water"
                    self.assertTrue(on_platform, f"un golem puo' nascere in {spot} ({self.name(x, y - 1, z)})")
                    good += 1
            self.assertGreaterEqual(good, 30)

    def test_daylight_detector_sees_the_sky(self):
        x, y, z = self.c["daylight"]
        column = [self.name(x, yy, z) for yy in range(y + 1, self.b.h)]
        self.assertTrue(all(n in (None, "air", "glass") for n in column), column)
        self.assertTrue(column and column[-1] in (None, "air", "glass"))

    def sight_clear(self, a, bpos):
        steps = 200
        for i in range(1, steps):
            t = i / steps
            p = [a[k] + (bpos[k] - a[k]) * t for k in range(3)]
            cell = (math.floor(p[0]), math.floor(p[1]), math.floor(p[2]))
            if _collider(self.name(*cell)) and cell[1] != math.floor(a[1]) - 2:
                return False
        return True

    def test_villagers_see_the_zombie_only_through_the_open_slot(self):
        V = hf.FARM_V
        zx, zz = self.c["zombie"]
        zombie_eye = (zx + 0.5, V + 0.5 + 1.74, zz + 0.5)
        for vx, vz in self.c["villagers"]:
            eye = (vx + 0.5, V + 0.5625 + 1.62, vz + 0.5)
            self.assertTrue(self.sight_clear(eye, zombie_eye), (vx, vz))
            self.assertLessEqual(math.dist(eye, zombie_eye), 8.0)
        ox, oy, oz = self.c["opening"]
        saved = self.b.cells.get((ox, oy, oz))
        self.b.cells[(ox, oy, oz)] = ("minecraft:smooth_stone", {})          # piston extended
        try:
            for vx, vz in self.c["villagers"]:
                eye = (vx + 0.5, V + 0.5625 + 1.62, vz + 0.5)
                self.assertFalse(self.sight_clear(eye, zombie_eye))
        finally:
            self.b.cells[(ox, oy, oz)] = saved

    def test_villagers_and_zombie_are_trapped(self):
        V = hf.FARM_V
        for vx, vz in self.c["villagers"]:
            self.assertTrue(self.name(vx, V, vz).endswith("_bed"))
            self.assertEqual(self.name(vx, V + 1, vz + 1), "glass")             # cannot step on the bed foot
            for dx in (-1, 1):
                n = self.name(vx + dx, V + 1, vz)
                self.assertTrue(n.endswith("_bed") is False and (n in ("air", "glass") or _collider(n)))
        zx, zz = self.c["zombie"]
        self.assertEqual(self.name(zx, V, zz), "smooth_stone_slab")
        self.assertEqual(self.name(zx, V + 3, zz), "glass")


class InjectionTests(unittest.TestCase):
    def test_hub_and_farm_write_contents_and_entities(self):
        import shutil
        import tempfile
        from fake_world import make_region, GROUND_Y
        from mca_codec import MCARegion
        from world_editor import World, inject_structures
        tmp = tempfile.mkdtemp()
        try:
            region_dir = os.path.join(tmp, "region")
            make_region(region_dir, 0, 0, chunks=[(cx, cz) for cx in range(8) for cz in range(8)])
            world = World(region_dir)
            hub = hf.underground_hub().to_structure()
            farm = hf.iron_farm().to_structure()
            stats = inject_structures(world, [
                {"structure": hub, "world_x": 4, "world_z": 4, "y_coord": GROUND_Y + 1 - hub.ground_offset,
                 "name": "hub"},
                {"structure": farm, "world_x": 60, "world_z": 60, "y_coord": GROUND_Y + 1, "name": "farm"}])
            self.assertEqual(stats["block_data"], 2 * len(hf.SORTED_ITEMS) + 2)
            self.assertEqual(stats["entities"], 4)
            world.save(backup=False)
            ents = MCARegion(os.path.join(tmp, "entities", "r.0.0.mca"))
            found = [str(e["id"]) for key in ents.chunks for e in ents.chunks[key][0]["Entities"]]
            self.assertEqual(sorted(found), ["minecraft:villager"] * 3 + ["minecraft:zombie"])
            # the filter of the first slice, in the world
            fx, fy, fz = hf.HUB_SLICE_X[0], 2, hf.HUB_ZF
            gx, gy, gz = 4 + fx, GROUND_Y + 1 - hub.ground_offset + fy, 4 + fz
            chunk = MCARegion(os.path.join(region_dir, "r.0.0.mca")).chunks[(gx >> 4, gz >> 4)][0]
            be = [b for b in chunk["block_entities"] if (int(b["x"]), int(b["y"]), int(b["z"])) == (gx, gy, gz)]
            self.assertEqual(len(be), 1)
            self.assertEqual(int(be[0]["Items"][0]["count"]), hf.FILTER_COUNT)
        finally:
            shutil.rmtree(tmp)


class TemplateValidationTests(unittest.TestCase):
    def test_hub_and_farm_validate_without_errors(self):
        for fn in (hf.underground_hub, hf.iron_farm):
            errors, _, _ = validate(fn().to_structure())
            self.assertEqual(errors, [], fn.__name__)

    def test_hub_is_underground_and_sealed(self):
        s = hf.underground_hub().to_structure()
        self.assertEqual(s.ground_offset, hf.HUB_G)
        ex, ez = hf.HUB_ELEVATOR
        self.assertEqual(_short(s.blocks[(ex, 0, ez)]["Name"]), "soul_sand")
        for y in range(1, hf.HUB_G + 1):
            self.assertEqual(_short(s.blocks[(ex, y, ez)]["Name"]), "bubble_column")
        # no open cell below the surface touches the untouched terrain
        for (x, y, z), blk in s.blocks.items():
            if y >= hf.HUB_G - 1 or bi.is_full_solid(_short(blk["Name"])):
                continue
            for dx, dy, dz in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)):
                q = (x + dx, y + dy, z + dz)
                if 0 <= q[1] < hf.HUB_G - 1 and 0 <= q[0] < s.width and 0 <= q[2] < s.length:
                    self.assertIn(q, s.blocks, f"{(x, y, z)} confina con il terreno in {q}")


if __name__ == "__main__":
    unittest.main()
