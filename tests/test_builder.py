"""
Run with:  python -m unittest discover -s tests -v
"""
import os
import random
import sys
import shutil
import tempfile
import time
import unittest

from fake_world import make_region, make_chunk, GROUND_Y

from nbt_codec import (
    load_nbt, nbt_to_bytes, parse_nbt_bytes, TAG_Compound, TAG_String, TAG_Int,
)
from mca_codec import (
    MCARegion, ChunkEditor, decode_indices, encode_indices, unpack_section,
    read_world_surface, surface_heights,
)
from structure_manager import Structure
from world_editor import World, inject_structures, upgrade_block

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
TEMPLATES = os.path.join(ROOT, "templates")


def state(name, **props):
    s = TAG_Compound({"Name": TAG_String("minecraft:" + name)})
    if props:
        s["Properties"] = TAG_Compound({k: TAG_String(v) for k, v in props.items()})
    return s


def block_at(region, x, y, z):
    """Block name at absolute coordinates inside a region, read back from the file."""
    chunk, _ = region.chunks[((x >> 4) & 31, (z >> 4) & 31)]
    for sec in chunk["sections"]:
        if int(sec["Y"]) == y >> 4:
            return unpack_section(sec)[((y & 15) << 8) | ((z & 15) << 4) | (x & 15)]["Name"]
    return None


class NbtTests(unittest.TestCase):
    def test_templates_roundtrip(self):
        for f in sorted(f for f in os.listdir(TEMPLATES) if f.endswith(".nbt")):
            tag, name = load_nbt(os.path.join(TEMPLATES, f))
            data = nbt_to_bytes(tag, name)
            self.assertEqual(parse_nbt_bytes(data), (tag, name), f)


class PalettedContainerTests(unittest.TestCase):
    def test_indices_roundtrip(self):
        rng = random.Random(1)
        for bits in range(4, 16):
            values = [rng.randrange(1 << bits) for _ in range(4096)]
            self.assertEqual(decode_indices(encode_indices(values, bits), bits), values)


class RegionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_lazy_load_and_untouched_chunks_are_copied(self):
        make_region(self.tmp, 0, 0, chunks=[(0, 0), (1, 0), (5, 7)])
        region = MCARegion(os.path.join(self.tmp, "r.0.0.mca"))
        self.assertEqual(len(region.chunks._decoded), 0, "chunks must not be decoded on open")
        self.assertIn((5, 7), region.chunks)
        self.assertNotIn((2, 2), region.chunks)
        raw_before = region._raw[(1, 0)]

        chunk, ts = region.chunks[(0, 0)]
        editor = ChunkEditor(chunk, 0, 0)
        editor.set_block(3, 70, 4, state("gold_block"))
        editor.flush()
        region.mark_dirty((0, 0))
        region.save()

        self.assertEqual(region._raw[(1, 0)][1], raw_before[1], "untouched chunk must be byte-identical")
        self.assertEqual(block_at(region, 3, 70, 4), "minecraft:gold_block")
        self.assertEqual(sorted(region.chunks), [(0, 0), (1, 0), (5, 7)])

    def test_quick_surface_matches_full_parse(self):
        make_region(self.tmp, 0, 0, chunks=[(0, 0), (3, 4)])
        region = MCARegion(os.path.join(self.tmp, "r.0.0.mca"))
        fast = region.quick_surface((3, 4))
        self.assertIsNotNone(fast)
        self.assertEqual(fast, read_world_surface(region.chunks[(3, 4)][0]))

    def test_chunk_editor_light_heightmaps_block_entities(self):
        chunk = make_chunk(0, 0)
        chunk["block_entities"].append(TAG_Compound({
            "id": TAG_String("minecraft:chest"), "x": TAG_Int(2), "y": TAG_Int(64), "z": TAG_Int(2),
        }))
        editor = ChunkEditor(chunk, 0, 0)
        for y in range(64, 80):
            editor.set_block(2, y, 2, state("stone_bricks"))
        editor.set_block(5, 64, 5, state("air"))  # unchanged: already air
        self.assertTrue(editor.flush())

        self.assertEqual(int(chunk["isLightOn"]), 0)
        self.assertEqual(len(chunk["block_entities"]), 0, "chest entity of the overwritten block removed")
        self.assertNotIn("MOTION_BLOCKING", chunk["Heightmaps"])
        heights = read_world_surface(chunk)
        self.assertEqual(heights[2 * 16 + 2], 79)
        self.assertEqual(heights[0], GROUND_Y)
        self.assertEqual(heights, surface_heights(chunk)[0])
        for sec in chunk["sections"]:
            if int(sec["Y"]) in (4,):
                self.assertNotIn("SkyLight", sec)


class WorldLocatorTests(unittest.TestCase):
    def setUp(self):
        import world_locator
        self.loc = world_locator
        self.tmp = tempfile.mkdtemp()
        self.saves = os.path.join(self.tmp, ".minecraft", "saves")
        self.world = os.path.join(self.saves, "Mio Mondo")
        for sub in ("region", "playerdata", os.path.join("DIM-1", "region"), "datapacks"):
            os.makedirs(os.path.join(self.world, sub))
        with open(os.path.join(self.world, "level.dat"), "wb") as f:
            f.write(b"x")
        for rel in ("region/r.0.0.mca", "DIM-1/region/r.0.0.mca"):
            open(os.path.join(self.world, rel), "wb").close()
        os.makedirs(os.path.join(self.saves, "##Mio Mondo.UNDO##"))  # not a world: no level.dat

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_any_path_inside_a_world_finds_it(self):
        for rel, dim in (("", None), ("region", None), ("playerdata", None), ("datapacks", None),
                         ("level.dat", None), ("region/r.0.0.mca", None), ("DIM-1", "Nether"),
                         ("DIM-1/region", "Nether")):
            found = self.loc.resolve(os.path.join(self.world, rel))
            self.assertEqual((found["saves_dir"], found["world"], found["dimension"]),
                             (self.saves, "Mio Mondo", dim), rel)

    def test_saves_and_minecraft_folders(self):
        self.assertEqual(self.loc.resolve(self.saves), {"saves_dir": self.saves, "world": None, "dimension": None})
        self.assertEqual(self.loc.resolve(os.path.dirname(self.saves))["saves_dir"], self.saves)
        self.assertIsNone(self.loc.resolve(self.tmp))
        self.assertIsNone(self.loc.resolve(os.path.join(self.tmp, "non esiste")))

    def test_world_without_level_dat_is_found_by_its_regions(self):
        os.remove(os.path.join(self.world, "level.dat"))
        self.assertEqual(self.loc.resolve(os.path.join(self.world, "region"))["world"], "Mio Mondo")
        self.assertEqual(self.loc.list_worlds(self.saves), ["Mio Mondo"])

    def test_lists_only_real_worlds_and_their_dimensions(self):
        self.assertEqual(self.loc.list_worlds(self.saves), ["Mio Mondo"])
        self.assertEqual([d for d, _ in self.loc.region_dirs(self.world)], ["Overworld", "Nether"])


class RotationTests(unittest.TestCase):
    def test_four_rotations_are_identity(self):
        for f in sorted(f for f in os.listdir(TEMPLATES) if f.endswith(".nbt")):
            s = Structure.load(os.path.join(TEMPLATES, f))
            r = s.rotate(90).rotate(90).rotate(90).rotate(90)
            self.assertEqual(r.blocks, s.blocks, f)
            self.assertEqual((r.width, r.length), (s.width, s.length))

    def test_fence_connections_follow_rotation(self):
        s = Structure(3, 1, 1, {(1, 0, 0): {"Name": "minecraft:oak_fence",
                                            "Properties": {"east": "true", "west": "false",
                                                           "north": "false", "south": "false"}}})
        r = s.rotate(90)
        props = r.blocks[(0, 0, 1)]["Properties"]
        self.assertEqual(props["south"], "true")
        self.assertEqual(props["east"], "false")


class InjectionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        make_region(self.tmp, 0, 0)
        # Neighbour region east: only the first chunk column exists
        make_region(self.tmp, 1, 0, chunks=[(0, cz) for cz in range(32)])

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def place(self, name, x, y, z, **kw):
        world = World(self.tmp)
        s = Structure.load(os.path.join(TEMPLATES, name))
        stats = inject_structures(world, [{"structure": s, "world_x": x, "world_z": z,
                                           "y_coord": y, "name": name}], **kw)
        backups = world.save()
        return s, stats, backups

    def test_structure_crossing_region_border(self):
        s, stats, backups = self.place("starter_cottage.nbt", 506, GROUND_Y + 1, 100)
        self.assertEqual(len(backups), 2, "both regions backed up")
        r0 = MCARegion(os.path.join(self.tmp, "r.0.0.mca"))
        r1 = MCARegion(os.path.join(self.tmp, "r.1.0.mca"))
        self.assertEqual(block_at(r0, 507, GROUND_Y + 1, 101), "minecraft:cobblestone")
        self.assertEqual(block_at(r1, 512 + 3, GROUND_Y + 1, 101), "minecraft:cobblestone")
        self.assertEqual(stats["skipped_missing"], 0)

    def test_missing_chunks_are_skipped_not_created(self):
        # x = 512+16.. lies in chunks that do not exist in r.1.0
        s, stats, _ = self.place("market_stall.nbt", 512 + 20, GROUND_Y + 1, 10)
        self.assertGreater(stats["skipped_missing"], 0)
        r1 = MCARegion(os.path.join(self.tmp, "r.1.0.mca"))
        self.assertNotIn((1, 0), r1.chunks)

    def test_foundations_fill_only_base_layer_columns(self):
        # Bridge 4 blocks above the ground: piers get foundations, spans under the arches do not
        y = GROUND_Y + 5
        s, stats, _ = self.place("stone_bridge.nbt", 100, y, 100)
        r0 = MCARegion(os.path.join(self.tmp, "r.0.0.mca"))
        self.assertEqual(block_at(r0, 100, y - 1, 100), "minecraft:grass_block")  # under pier
        self.assertEqual(block_at(r0, 100, y - 2, 100), "minecraft:dirt")
        self.assertEqual(block_at(r0, 100, y - 1, 106), "minecraft:air")  # under arch
        self.assertGreater(stats["foundation"], 0)

    def test_air_cells_dig_terrain(self):
        # Cottage sunk 2 blocks into the ground: its interior air must be dug out
        y = GROUND_Y - 1
        s, stats, _ = self.place("starter_cottage.nbt", 50, y, 50)
        r0 = MCARegion(os.path.join(self.tmp, "r.0.0.mca"))
        self.assertEqual(block_at(r0, 50 + 5, y + 1, 50 + 5), "minecraft:air")
        self.assertGreater(stats["cleared"], 0)

    def test_legacy_chunks_are_skipped_not_fatal(self):
        # Worlds upgraded from 1.16 keep "Level"-wrapped chunks until the game reloads them
        region = MCARegion(os.path.join(self.tmp, "r.0.0.mca"))
        chunk, ts = region.chunks[(3, 3)]
        legacy = TAG_Compound({"DataVersion": TAG_Int(2586), "Level": TAG_Compound({"xPos": TAG_Int(3)})})
        region.chunks[(3, 3)] = (legacy, ts)
        region.save()
        s, stats, _ = self.place("market_stall.nbt", 46, GROUND_Y + 1, 46)
        self.assertGreater(stats["skipped_missing"], 0)
        self.assertGreater(stats["placed"], 0)

    def test_modded_blocks_are_skipped(self):
        s, stats, _ = self.place("space_station.nbt", 200, GROUND_Y + 1, 200)
        self.assertGreater(stats["skipped_modded"], 0)
        r0 = MCARegion(os.path.join(self.tmp, "r.0.0.mca"))
        names = set()
        for (cx, cz) in [(12, 12), (13, 13)]:
            chunk, _ = r0.chunks[(cx, cz)]
            for sec in chunk["sections"]:
                names.update(str(b["Name"]) for b in sec["block_states"]["palette"])
        self.assertTrue(all(n.startswith("minecraft:") for n in names), names)

    def test_large_structure_is_fast(self):
        t0 = time.perf_counter()
        s, stats, _ = self.place("auto_warehouse.nbt", 300, GROUND_Y + 1, 300)
        elapsed = time.perf_counter() - t0
        print(f"\n    auto_warehouse: {stats['placed']} blocchi + {stats['cleared']} scavati in {elapsed:.2f} s")
        self.assertGreater(stats["placed"], 15000)
        self.assertLess(elapsed, 60)


class TemplateLibraryTests(unittest.TestCase):
    """Every generated template must be valid, playable and inject exactly."""

    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, os.path.join(ROOT, "tools"))
        import build_templates
        import validate_templates
        cls.registry = build_templates.all_templates()
        cls.validate = staticmethod(validate_templates.validate)

    def test_catalog_lists_every_template(self):
        import json
        with open(os.path.join(TEMPLATES, "catalog.json"), encoding="utf-8") as f:
            files = {e["file"] for e in json.load(f)}
        self.assertEqual(files, {f"{n}.nbt" for n in self.registry})
        self.assertGreaterEqual(len(files), 60)

    def test_generated_templates_are_playable(self):
        for name in sorted(self.registry):
            s = Structure.load(os.path.join(TEMPLATES, f"{name}.nbt"))
            errors, warnings, stats = self.validate(s)
            self.assertEqual(errors, [], name)
            self.assertEqual(stats["dark_spots"], 0, name)
            self.assertEqual(s.modded_blocks(), {}, name)

    def test_every_template_injects_and_reads_back(self):
        tmp = tempfile.mkdtemp()
        try:
            make_region(tmp, 0, 0)
            world = World(tmp)
            import json
            try:
                with open(os.path.join(TEMPLATES, "user_catalog.json"), encoding="utf-8") as f:
                    user_files = {e["file"] for e in json.load(f)}
            except (OSError, ValueError):
                user_files = set()
            # the user's own cuts and saved structures are not part of the library under test
            names = sorted(f[:-4] for f in os.listdir(TEMPLATES) if f.endswith(".nbt") and f not in user_files)
            placements = []
            ox = oz = row_depth = 0
            for name in names:
                s = Structure.load(os.path.join(TEMPLATES, f"{name}.nbt"))
                if ox + s.width > 512:
                    ox, oz, row_depth = 0, oz + row_depth + 1, 0
                placements.append({"structure": s, "world_x": ox, "world_z": oz, "y_coord": GROUND_Y + 1,
                                   "name": name})
                ox += s.width + 1
                row_depth = max(row_depth, s.length)
            self.assertLessEqual(oz + row_depth, 512)
            inject_structures(world, placements, fill_foundations=False, clear_terrain=True, skip_modded=True)
            world.save(backup=False)
            region = MCARegion(os.path.join(tmp, "r.0.0.mca"))
            cache = {}
            for p in placements:
                for (x, y, z), block in p["structure"].blocks.items():
                    if not block["Name"].startswith("minecraft:"):
                        continue
                    gx, gy, gz = p["world_x"] + x, p["y_coord"] + y, p["world_z"] + z
                    key = (gx >> 4, gz >> 4, gy >> 4)
                    if key not in cache:
                        chunk, _ = region.chunks[(key[0], key[1])]
                        sec = next(sc for sc in chunk["sections"] if int(sc["Y"]) == key[2])
                        cache[key] = unpack_section(sec)
                    got = cache[key][((gy & 15) << 8) | ((gz & 15) << 4) | (gx & 15)]
                    expected_props = {k: str(v) for k, v in block.get("Properties", {}).items()}
                    got_props = {k: str(v) for k, v in got.get("Properties", {}).items()}
                    expected_name = upgrade_block(block, 3955)["Name"]
                    if expected_name in ("minecraft:cave_air", "minecraft:void_air"):
                        expected_name = "minecraft:air"
                    self.assertEqual((got["Name"], got_props), (expected_name, expected_props),
                                     f"{p['name']} {(x, y, z)}")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class BuilderTests(unittest.TestCase):
    def test_hip_roof_corners_get_outer_shapes(self):
        sys.path.insert(0, os.path.join(ROOT, "tools"))
        from template_builder import Builder
        b = Builder(9, 6, 9)
        b.hip_roof(1, 7, 1, 7, 0, "oak", "oak_planks", overhang=1)
        b.finalize()
        shapes = {b.cells[p][1]["shape"] for p in ((0, 0, 0), (8, 0, 0), (0, 0, 8), (8, 0, 8))}
        self.assertTrue(all(s.startswith("outer") for s in shapes), shapes)
        self.assertEqual(b.cells[(4, 0, 0)][1]["shape"], "straight")


class NewChunkFormatTests(unittest.TestCase):
    """Minecraft 26.x: block states as strings / {id, properties}, mixed lists wrapped as {"": ...}."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        make_region(self.tmp, 0, 0, chunks=[(cx, cz) for cx in range(3) for cz in range(3)], new_encoding=True)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_normalize_all_encodings(self):
        from mca_codec import normalize_state
        self.assertEqual(normalize_state(TAG_String("minecraft:stone")), {"Name": "minecraft:stone"})
        self.assertEqual(normalize_state(TAG_Compound({"": TAG_String("minecraft:dirt")})), {"Name": "minecraft:dirt"})
        s = normalize_state(TAG_Compound({"id": TAG_String("minecraft:oak_log"),
                                          "properties": TAG_Compound({"axis": TAG_String("y")})}))
        self.assertEqual((s["Name"], dict(s["Properties"])), ("minecraft:oak_log", {"axis": "y"}))

    def test_injection_keeps_the_new_encoding(self):
        world = World(self.tmp)
        cottage = Structure.load(os.path.join(TEMPLATES, "starter_cottage.nbt"))
        old = Structure(1, 2, 1, {(0, 0, 0): {"Name": "minecraft:chain", "Properties": {"axis": "y"}},
                                   (0, 1, 0): {"Name": "minecraft:grass", "Properties": {}}}, 2580)
        stats = inject_structures(world, [
            {"structure": cottage, "world_x": 5, "world_z": 5, "y_coord": GROUND_Y + 1, "name": "c"},
            {"structure": old, "world_x": 30, "world_z": 30, "y_coord": GROUND_Y + 1, "name": "old"}])
        world.save(backup=False)
        region = MCARegion(os.path.join(self.tmp, "r.0.0.mca"))
        for key in list(region.chunks):
            chunk, _ = region.chunks[key]
            for sec in chunk["sections"]:
                for e in sec["block_states"]["palette"]:
                    self.assertFalse(hasattr(e, "keys") and "Name" in e, f"palette in formato vecchio in {key}")
        world = World(self.tmp)
        self.assertEqual(str(world.get_block(5 + 5, GROUND_Y + 2, 5 + 9)["Name"]), "minecraft:oak_door")
        self.assertEqual(str(world.get_block(30, GROUND_Y + 1, 30)["Name"]), "minecraft:iron_chain")
        self.assertEqual(str(world.get_block(30, GROUND_Y + 2, 30)["Name"]), "minecraft:short_grass")
        self.assertEqual(stats["placed"], 424 + 2)


class FoundationLimitTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        make_region(self.tmp, 0, 0, chunks=[(0, 0), (1, 0)])

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_floating_and_water_structures_are_not_propped_up(self):
        world = World(self.tmp)
        slab = Structure(3, 1, 3, {(x, 0, z): {"Name": "minecraft:stone", "Properties": {}}
                                   for x in range(3) for z in range(3)})
        for x in range(20, 23):
            for z in range(0, 3):
                world.set_block(x, GROUND_Y + 1, z, state("water", level="0"))
        stats = inject_structures(world, [
            {"structure": slab, "world_x": 0, "world_z": 0, "y_coord": GROUND_Y + 30, "name": "in cielo"},
            {"structure": slab, "world_x": 20, "world_z": 0, "y_coord": GROUND_Y + 2, "name": "sull'acqua"},
            {"structure": slab, "world_x": 10, "world_z": 0, "y_coord": GROUND_Y + 4, "name": "poco sollevata"}])
        self.assertEqual(stats["foundation"], 9 * 3)  # only the slightly raised one


class CatalogTests(unittest.TestCase):
    def test_every_structure_has_an_italian_category(self):
        import catalog
        entries = catalog.load_catalog(TEMPLATES)
        self.assertEqual(len(entries), len([f for f in os.listdir(TEMPLATES) if f.endswith(".nbt")]))
        # the built-in library only (downloads and cuts of the user may legitimately be "Altro")
        import json
        with open(os.path.join(TEMPLATES, "catalog.json"), encoding="utf-8") as f:
            builtin = {e["file"] for e in json.load(f)} | {f"{n}.nbt" for n in catalog.ORIGINALS}
        entries = [e for e in entries if e["file"] in builtin]
        self.assertEqual(catalog.category_for("crop_farm_(mixed)"), "Fattorie e animali")
        self.assertTrue(all(e["category"] in catalog.CATEGORIES and e["category"] != "Altro" for e in entries),
                        [e["file"] for e in entries if e["category"] == "Altro"])
        self.assertEqual({e["file"] for e in entries if e["category"] == "Ponti"},
                         {"stone_bridge.nbt", "suspension_bridge.nbt", "tower_bridge.nbt", "nether_fortress_bridge.nbt"})


class BridgeGeneratorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, os.path.join(ROOT, "tools"))
        import structure_generators
        import validate_templates
        cls.g = structure_generators
        cls.validate = staticmethod(validate_templates.validate)

    def test_bridges_of_any_length_are_valid(self):
        for style in self.g.BRIDGE_STYLES:
            for length in (9, 23, 57, 120):
                s = self.g.make_bridge(style, length)
                self.assertEqual(s.length, max(length, 12 if style == "suspension" else 7), style)
                errors, _, _ = self.validate(s)
                self.assertEqual(errors, [], f"{style} {length}")

    def test_bridge_between_banks_and_continuation(self):
        first = self.g.bridge_between("stone", (100, 50), (130, 52), 64, 66, water_level=62)
        info = first["bridge"]
        self.assertEqual((info["axis"], info["deck"], info["center"]), ("x", 66, 51))
        self.assertEqual((info["a"], info["b"]), (98, 132))
        self.assertEqual(first["y_coord"], 66 - 4)
        self.assertEqual(first["structure"].width, 35)
        # a second bridge starting near the end continues the first one
        second = self.g.bridge_between("wood", (134, 54), (150, 50), 70, 63, existing=[info])
        self.assertTrue(second["snapped"])
        self.assertEqual((second["bridge"]["a"], second["bridge"]["deck"], second["bridge"]["center"]), (133, 66, 51))
        self.assertEqual(second["bridge"]["style"], "stone")
        # deck stays above water
        wet = self.g.bridge_between("wood", (0, 0), (0, 20), 60, 60, water_level=62)
        self.assertEqual(wet["bridge"]["deck"], 63)


class VillageGeneratorTests(unittest.TestCase):
    class Terrain:
        def height(self, x, z):
            return None if x > 70 else 64 + max(0, x - 40) // 5

        def is_water(self, x, z):
            return (x + 20) ** 2 + (z - 15) ** 2 < 50

    def test_village_layout(self):
        import village_generator as vg
        load = lambda n: Structure.load(os.path.join(TEMPLATES, f"{n}.nbt"))
        result = vg.generate_village((0, 0), "medievale", "grande", self.Terrain(), load, seed=3)
        self.assertGreaterEqual(len(result["placements"]), 10, result["report"])
        terrain = self.Terrain()
        occupied = {}
        for p in result["placements"]:
            s = p["structure"]
            cells = [(x, z) for x in range(p["world_x"], p["world_x"] + s.width)
                     for z in range(p["world_z"], p["world_z"] + s.length)]
            for c in cells:
                self.assertNotIn(c, occupied, f"{p['name']} sovrapposto a {occupied.get(c)}")
                occupied[c] = p["name"]
                self.assertIsNotNone(terrain.height(*c), "edificio fuori dal terreno generato")
            heights = sorted(terrain.height(*c) for c in cells)
            self.assertEqual(p["y_coord"], heights[len(heights) // 2] + 1)
        self.assertFalse(any(c in occupied for c in result["path_cells"]), "strada sotto un edificio")
        # every door opens towards a path
        paths = set(result["path_cells"])
        for p in result["placements"][1:]:
            side, door = vg.front_side(p["structure"])
            if door is None:
                continue
            dx, dz = vg.DIR[side]
            x, z = p["world_x"] + door[0], p["world_z"] + door[1]
            steps = 0
            while (x, z) not in paths and steps < 20:
                x, z, steps = x + dx, z + dz, steps + 1
            self.assertLess(steps, 20, f"la porta di {p['name']} non porta a una strada")


class ExtractorTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        make_region(self.tmp, 0, 0, chunks=[(cx, cz) for cx in range(4) for cz in range(4)])

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_cut_keeps_buildings_drops_terrain_and_trees(self):
        from world_extractor import extract_area, save_structure
        world = World(self.tmp)
        cottage = Structure.load(os.path.join(TEMPLATES, "starter_cottage.nbt"))
        inject_structures(world, [{"structure": cottage, "world_x": 10, "world_z": 10, "y_coord": GROUND_Y + 1,
                                   "name": "c"}])
        # a natural tree next to the house and a basement room under it
        for y in range(GROUND_Y + 1, GROUND_Y + 5):
            world.set_block(26, y, 12, state("oak_log", axis="y"))
        for y in range(GROUND_Y + 5, GROUND_Y + 7):
            world.set_block(26, y, 12, state("oak_leaves", distance="1", persistent="false", waterlogged="false"))
        for y in range(GROUND_Y - 3, GROUND_Y + 1):
            world.set_block(15, y, 15, state("stone_bricks") if y == GROUND_Y - 3 else state("air"))
        world.save(backup=False)
        world = World(self.tmp)
        cut, info = extract_area(world, 8, 8, 28, 24)
        names = {b["Name"] for b in cut.blocks.values()}
        tree_column = [p for p in cut.blocks if (p[0], p[2]) == (26 - 8, 12 - 8)]
        self.assertEqual(tree_column, [], "l'albero naturale non deve essere copiato")
        self.assertIn("minecraft:oak_leaves", names)  # the cottage's hand-placed (persistent) bushes stay
        self.assertNotIn("minecraft:grass_block", names)
        self.assertNotIn("minecraft:dirt", names)
        # cottage + the basement floor; the basement makes the cut go 4 layers below the ground
        self.assertEqual(info["ground_offset"], 4)
        self.assertEqual(info["blocks"], 424 + 1)
        path = os.path.join(self.tmp, "cut.nbt")
        save_structure(cut, path)
        loaded = Structure.load(path)
        self.assertEqual(loaded.ground_offset, 4)
        self.assertEqual(len(loaded.blocks), len(cut.blocks))

    def test_paths_follow_the_terrain(self):
        from world_editor import paint_path
        world = World(self.tmp)
        world.set_block(5, GROUND_Y + 1, 5, state("poppy"))
        n = paint_path(world, [(5, 5), (6, 5), (7, 5)])
        self.assertEqual(n, 3)
        self.assertEqual(str(world.get_block(5, GROUND_Y, 5)["Name"]), "minecraft:dirt_path")
        self.assertEqual(str(world.get_block(5, GROUND_Y + 1, 5)["Name"]), "minecraft:air")


if __name__ == "__main__":
    unittest.main()
