"""
Block knowledge shared by the template builder, the validator and the renderer.

All names are vanilla Minecraft 1.21.1 block ids (without the "minecraft:" prefix
unless stated otherwise).
"""

WOODS = ("oak", "spruce", "birch", "jungle", "acacia", "dark_oak", "mangrove", "cherry", "bamboo",
         "crimson", "warped")
COLORS = ("white", "orange", "magenta", "light_blue", "yellow", "lime", "pink", "gray", "light_gray",
          "cyan", "purple", "blue", "brown", "green", "red", "black")

# Families that have _stairs/_slab (and sometimes _wall) variants
_STONE_FAMILIES_FULL = {
    # base block -> (stairs/slab prefix, has wall)
    "stone": ("stone", False), "cobblestone": ("cobblestone", True),
    "mossy_cobblestone": ("mossy_cobblestone", True), "stone_bricks": ("stone_brick", True),
    "mossy_stone_bricks": ("mossy_stone_brick", True), "smooth_stone": ("smooth_stone", False),
    "granite": ("granite", True), "polished_granite": ("polished_granite", False),
    "diorite": ("diorite", True), "polished_diorite": ("polished_diorite", False),
    "andesite": ("andesite", True), "polished_andesite": ("polished_andesite", False),
    "cobbled_deepslate": ("cobbled_deepslate", True), "polished_deepslate": ("polished_deepslate", True),
    "deepslate_bricks": ("deepslate_brick", True), "deepslate_tiles": ("deepslate_tile", True),
    "bricks": ("brick", True), "mud_bricks": ("mud_brick", True),
    "sandstone": ("sandstone", True), "smooth_sandstone": ("smooth_sandstone", False),
    "cut_sandstone": ("cut_sandstone", False),
    "red_sandstone": ("red_sandstone", True), "smooth_red_sandstone": ("smooth_red_sandstone", False),
    "cut_red_sandstone": ("cut_red_sandstone", False),
    "prismarine": ("prismarine", True), "prismarine_bricks": ("prismarine_brick", False),
    "dark_prismarine": ("dark_prismarine", False),
    "nether_bricks": ("nether_brick", True), "red_nether_bricks": ("red_nether_brick", True),
    "blackstone": ("blackstone", True), "polished_blackstone": ("polished_blackstone", True),
    "polished_blackstone_bricks": ("polished_blackstone_brick", True),
    "end_stone_bricks": ("end_stone_brick", True), "purpur_block": ("purpur", False),
    "quartz_block": ("quartz", False), "smooth_quartz": ("smooth_quartz", False),
    "tuff": ("tuff", True), "polished_tuff": ("polished_tuff", True), "tuff_bricks": ("tuff_brick", True),
    "waxed_cut_copper": ("waxed_cut_copper", False),
    "waxed_exposed_cut_copper": ("waxed_exposed_cut_copper", False),
    "waxed_weathered_cut_copper": ("waxed_weathered_cut_copper", False),
    "waxed_oxidized_cut_copper": ("waxed_oxidized_cut_copper", False),
}

# These families only have slabs
_NO_STAIRS = {"smooth_stone", "cut_sandstone", "cut_red_sandstone"}

_SIMPLE_BLOCKS = """
air cave_air void_air stone granite polished_granite diorite polished_diorite andesite polished_andesite
deepslate cobbled_deepslate polished_deepslate deepslate_bricks cracked_deepslate_bricks deepslate_tiles
cracked_deepslate_tiles chiseled_deepslate reinforced_deepslate calcite tuff polished_tuff tuff_bricks
chiseled_tuff chiseled_tuff_bricks dripstone_block pointed_dripstone beehive bee_nest grass_block dirt coarse_dirt podzol rooted_dirt mud
mycelium dirt_path farmland cobblestone mossy_cobblestone stone_bricks mossy_stone_bricks
cracked_stone_bricks chiseled_stone_bricks smooth_stone bedrock sand red_sand gravel clay
sandstone chiseled_sandstone cut_sandstone smooth_sandstone red_sandstone chiseled_red_sandstone
cut_red_sandstone smooth_red_sandstone bricks mud_bricks packed_mud bookshelf chiseled_bookshelf
obsidian crying_obsidian glowstone sea_lantern shroomlight ochre_froglight verdant_froglight
pearlescent_froglight prismarine prismarine_bricks dark_prismarine netherrack nether_bricks
cracked_nether_bricks chiseled_nether_bricks red_nether_bricks nether_wart_block warped_wart_block
soul_sand soul_soil basalt polished_basalt smooth_basalt blackstone polished_blackstone
polished_blackstone_bricks cracked_polished_blackstone_bricks chiseled_polished_blackstone
gilded_blackstone magma_block end_stone end_stone_bricks purpur_block purpur_pillar quartz_block
chiseled_quartz_block quartz_pillar quartz_bricks smooth_quartz ice packed_ice blue_ice snow_block snow
powder_snow glass tinted_glass glass_pane iron_bars iron_block gold_block diamond_block emerald_block
lapis_block redstone_block netherite_block copper_block coal_block amethyst_block budding_amethyst
amethyst_cluster raw_iron_block raw_gold_block raw_copper_block hay_block bone_block melon pumpkin
carved_pumpkin jack_o_lantern sponge wet_sponge slime_block honey_block honeycomb_block moss_block
moss_carpet sculk sculk_vein sculk_catalyst sculk_sensor sculk_shrieker
waxed_cut_copper waxed_exposed_cut_copper waxed_weathered_cut_copper waxed_oxidized_cut_copper
waxed_copper_block waxed_exposed_copper waxed_weathered_copper waxed_oxidized_copper
crafting_table furnace blast_furnace smoker chest trapped_chest ender_chest barrel anvil chipped_anvil
damaged_anvil grindstone smithing_table fletching_table cartography_table loom stonecutter lectern
enchanting_table brewing_stand cauldron water_cauldron lava_cauldron powder_snow_cauldron composter
jukebox note_block beacon conduit bell campfire soul_campfire respawn_anchor lodestone target
torch wall_torch soul_torch soul_wall_torch redstone_torch redstone_wall_torch lantern soul_lantern
end_rod lightning_rod ladder scaffolding cobweb water lava bubble_column
rail powered_rail detector_rail activator_rail redstone_wire redstone_lamp lever hopper dropper
dispenser observer piston sticky_piston piston_head tripwire tripwire_hook daylight_detector repeater comparator
calibrated_sculk_sensor note_block copper_bulb waxed_copper_bulb
nether_portal end_portal end_portal_frame end_gateway spawner dragon_egg
flower_pot potted_poppy potted_dandelion potted_blue_orchid potted_allium potted_azure_bluet
potted_red_tulip potted_orange_tulip potted_white_tulip potted_pink_tulip potted_oxeye_daisy
potted_cornflower potted_lily_of_the_valley potted_fern potted_cactus potted_bamboo
potted_red_mushroom potted_brown_mushroom potted_oak_sapling potted_spruce_sapling
potted_cherry_sapling potted_azalea_bush potted_flowering_azalea_bush potted_dead_bush
poppy dandelion blue_orchid allium azure_bluet red_tulip orange_tulip white_tulip pink_tulip
oxeye_daisy cornflower lily_of_the_valley sunflower lilac rose_bush peony torchflower pink_petals
short_grass tall_grass fern large_fern dead_bush seagrass tall_seagrass kelp kelp_plant sea_pickle
lily_pad vine glow_lichen hanging_roots sugar_cane cactus bamboo sweet_berry_bush
wheat carrots potatoes beetroots melon_stem pumpkin_stem attached_melon_stem attached_pumpkin_stem
nether_wart cocoa azalea flowering_azalea red_mushroom brown_mushroom red_mushroom_block
brown_mushroom_block mushroom_stem crimson_fungus warped_fungus crimson_roots warped_roots
oak_sapling spruce_sapling birch_sapling jungle_sapling acacia_sapling dark_oak_sapling cherry_sapling
mangrove_propagule decorated_pot candle chain skeleton_skull wither_skeleton_skull player_head
creeper_head zombie_head dragon_head piglin_head heavy_core vault trial_spawner crafter
"""

_FAMILY_SUFFIXES_WOOD = ("planks", "log", "wood", "stripped_{w}_log", "stripped_{w}_wood", "stairs", "slab",
                         "fence", "fence_gate", "door", "trapdoor", "pressure_plate", "button", "leaves",
                         "sign", "wall_sign", "hanging_sign")


def _build_vanilla_blocks():
    names = set(_SIMPLE_BLOCKS.split())
    for w in WOODS:
        nether = w in ("crimson", "warped")
        log, wood = ("stem", "hyphae") if nether else ("log", "wood")
        if w == "bamboo":
            names.update({"bamboo_block", "stripped_bamboo_block", "bamboo_planks", "bamboo_mosaic",
                          "bamboo_mosaic_stairs", "bamboo_mosaic_slab"})
        else:
            names.update({f"{w}_{log}", f"{w}_{wood}", f"stripped_{w}_{log}", f"stripped_{w}_{wood}"})
        names.update({f"{w}_planks", f"{w}_stairs", f"{w}_slab", f"{w}_fence", f"{w}_fence_gate",
                      f"{w}_door", f"{w}_trapdoor", f"{w}_pressure_plate", f"{w}_button",
                      f"{w}_sign", f"{w}_wall_sign", f"{w}_hanging_sign", f"{w}_wall_hanging_sign"})
        if not nether and w != "bamboo":
            names.add(f"{w}_leaves")
    names.update({"azalea_leaves", "flowering_azalea_leaves", "mangrove_roots", "muddy_mangrove_roots"})
    for c in COLORS:
        for suffix in ("wool", "carpet", "concrete", "concrete_powder", "terracotta", "glazed_terracotta",
                       "stained_glass", "stained_glass_pane", "bed", "candle", "banner", "wall_banner",
                       "shulker_box"):
            names.add(f"{c}_{suffix}")
    names.update({"terracotta", "shulker_box"})
    for base, (prefix, wall) in _STONE_FAMILIES_FULL.items():
        names.update({base, f"{prefix}_slab"})
        if base not in _NO_STAIRS:
            names.add(f"{prefix}_stairs")
        if wall:
            names.add(f"{prefix}_wall")
    names.add("nether_brick_fence")
    names.update({"iron_door", "iron_trapdoor", "stone_pressure_plate", "stone_button",
                  "light_weighted_pressure_plate", "heavy_weighted_pressure_plate",
                  "polished_blackstone_pressure_plate", "polished_blackstone_button"})
    return frozenset(names)


VANILLA_BLOCKS = _build_vanilla_blocks()


def short(name):
    return name.split(":", 1)[1] if name.startswith("minecraft:") else name


# ---------------------------------------------------------------------------
# Shape / physics classification
# ---------------------------------------------------------------------------

AIR_LIKE = frozenset(("air", "cave_air", "void_air"))
FLUIDS = frozenset(("water", "lava", "bubble_column"))

_PARTIAL_HINTS = (
    "stairs", "slab", "door", "pressure_plate", "button", "carpet", "sign", "banner", "ladder",
    "torch", "lantern", "rod", "chain", "_bed", "chest", "rail", "candle", "flower_pot", "potted_",
    "campfire", "bell", "anvil", "lectern", "brewing_stand", "_fence", "fence_gate", "pane", "iron_bars",
    "cauldron", "enchanting_table", "end_portal_frame", "stonecutter", "grindstone", "hopper",
    "scaffolding", "cobweb", "lily_pad", "vine", "lichen", "skull", "head", "sea_pickle", "cluster",
    "decorated_pot", "daylight_detector", "lever", "tripwire", "redstone_wire", "conduit", "dragon_egg",
    "composter", "bamboo_sapling",
)
_PLANT_HINTS = (
    "flower", "poppy", "dandelion", "orchid", "allium", "bluet", "tulip", "daisy", "cornflower",
    "lily_of_the_valley", "sunflower", "lilac", "rose_bush", "peony", "torchflower", "petals", "short_grass",
    "tall_grass", "fern", "dead_bush", "seagrass", "kelp", "sugar_cane", "cactus", "sweet_berry", "wheat",
    "carrots", "potatoes", "beetroots", "stem", "nether_wart", "cocoa", "sapling", "propagule", "mushroom",
    "fungus", "roots", "hanging_roots",
)


def is_air(n):
    return short(n) in AIR_LIKE


def is_wall_block(n):
    n = short(n)
    return n.endswith("_wall") and "sign" not in n and "torch" not in n and "banner" not in n


def is_plant(n):
    n = short(n)
    if n.endswith("_leaves") or n.startswith("potted_") or n == "flower_pot":
        return False
    if n.endswith("mushroom_block") or n == "mushroom_stem" or n.endswith(("_stem", "_hyphae")) and "stripped" in n:
        return False
    if n in ("crimson_stem", "warped_stem", "mangrove_roots", "muddy_mangrove_roots"):
        return False
    return any(h in n for h in _PLANT_HINTS)


def is_partial(n):
    """Not a full 1x1x1 cube (collision-wise)."""
    n = short(n)
    if n in ("sea_lantern", "jack_o_lantern"):
        return False
    if n in AIR_LIKE or n in FLUIDS:
        return True
    if is_wall_block(n) or is_plant(n):
        return True
    if n in ("snow", "farmland", "dirt_path", "moss_carpet", "pointed_dripstone", "bamboo"):
        return True
    return any(h in n for h in _PARTIAL_HINTS)


def is_full_solid(n):
    """Full cube with sturdy faces: supports torches, ladders, connects fences."""
    n = short(n)
    return not is_partial(n) and n not in ("powder_snow",)


def is_transparent_full(n):
    n = short(n)
    return ("glass" in n and "pane" not in n) or n.endswith("leaves") or n in (
        "ice", "beacon", "slime_block", "honey_block", "spawner")


def blocks_light(n):
    """Opaque for light propagation (approximation)."""
    n = short(n)
    return is_full_solid(n) and not is_transparent_full(n) and n not in ("barrier",)


def is_passable(n):
    """A player can stand inside this cell (no collision)."""
    n = short(n)
    if n in AIR_LIKE:
        return True
    if is_plant(n) and n not in ("cactus", "sweet_berry_bush"):
        return True
    return any(h in n for h in ("torch", "pressure_plate", "button", "carpet", "rail", "ladder", "vine",
                                 "lichen", "redstone_wire", "lever", "tripwire", "sign")) \
        or (n.endswith("_door")) or n == "water"


def is_standable(n):
    """A player can stand on top of this block."""
    n = short(n)
    if n in AIR_LIKE or is_plant(n) or n == "lava":
        return False
    if any(h in n for h in ("torch", "pressure_plate", "button", "carpet", "rail", "redstone_wire",
                             "lever", "tripwire", "sign", "_door", "_fence", "pane", "iron_bars",
                             "lantern", "rod", "chain", "candle", "potted_", "flower_pot", "ladder", "vine",
                             "cobweb")) and n not in ("sea_lantern", "jack_o_lantern"):
        return False
    if is_wall_block(n):
        return False
    return True


def is_climbable(n):
    n = short(n)
    return n in ("ladder", "vine", "scaffolding", "water", "twisting_vines", "weeping_vines")


def is_gravity(n):
    n = short(n)
    return n in ("sand", "red_sand", "gravel", "dragon_egg", "scaffolding", "pointed_dripstone") \
        or n.endswith("concrete_powder") or "anvil" in n


INTERACTIVE = frozenset((
    "crafting_table", "furnace", "blast_furnace", "smoker", "chest", "trapped_chest", "ender_chest",
    "barrel", "anvil", "chipped_anvil", "damaged_anvil", "grindstone", "smithing_table", "fletching_table",
    "cartography_table", "loom", "stonecutter", "lectern", "enchanting_table", "brewing_stand", "cauldron",
    "water_cauldron", "lava_cauldron", "composter", "jukebox", "beacon", "bell", "respawn_anchor",
))


def is_interactive(n):
    n = short(n)
    return n in INTERACTIVE or n.endswith("_bed") or n.endswith("shulker_box")


# ---------------------------------------------------------------------------
# Light
# ---------------------------------------------------------------------------

_LIGHT = {
    "torch": 14, "wall_torch": 14, "soul_torch": 10, "soul_wall_torch": 10, "lantern": 15,
    "soul_lantern": 10, "glowstone": 15, "sea_lantern": 15, "shroomlight": 15, "jack_o_lantern": 15,
    "end_rod": 14, "beacon": 15, "lava": 15, "ochre_froglight": 15, "verdant_froglight": 15,
    "pearlescent_froglight": 15, "magma_block": 3, "crying_obsidian": 10, "nether_portal": 11,
    "enchanting_table": 7, "ender_chest": 7, "conduit": 15, "lava_cauldron": 15, "amethyst_cluster": 5,
    "redstone_torch": 7, "redstone_wall_torch": 7, "glow_lichen": 7, "end_portal": 15, "end_gateway": 15,
    "respawn_anchor": 0, "brewing_stand": 1, "sculk_catalyst": 6, "trial_spawner": 4, "vault": 6,
}


def light_level(n, props=None):
    n = short(n)
    props = props or {}
    if n in ("campfire", "soul_campfire"):
        return (15 if n == "campfire" else 10) if props.get("lit", "true") == "true" else 0
    if n in ("furnace", "blast_furnace", "smoker"):
        return 13 if props.get("lit") == "true" else 0
    if n == "redstone_lamp":
        return 15 if props.get("lit") == "true" else 0
    if n.endswith("candle") and props.get("lit") == "true":
        return 3 * int(props.get("candles", "1"))
    if n == "sea_pickle":
        return 3 * (int(props.get("pickles", "1")) + 1) if props.get("waterlogged") == "true" else 0
    return _LIGHT.get(n, 0)


# ---------------------------------------------------------------------------
# Allowed properties (validator)
# ---------------------------------------------------------------------------

HORIZONTAL = {"north", "south", "east", "west"}
ALL_DIRS = HORIZONTAL | {"up", "down"}
BOOL = {"true", "false"}


def allowed_properties(n):
    """dict prop -> set of values (None = any) for the block, or {} if it has no properties."""
    n = short(n)
    wl = {"waterlogged": BOOL}
    if n.endswith("_stairs"):
        return {"facing": HORIZONTAL, "half": {"top", "bottom"},
                "shape": {"straight", "inner_left", "inner_right", "outer_left", "outer_right"}, **wl}
    if n.endswith("_slab"):
        return {"type": {"top", "bottom", "double"}, **wl}
    if n.endswith("_trapdoor"):
        return {"facing": HORIZONTAL, "half": {"top", "bottom"}, "open": BOOL, "powered": BOOL, **wl}
    if n.endswith("_door"):
        return {"facing": HORIZONTAL, "half": {"upper", "lower"}, "hinge": {"left", "right"},
                "open": BOOL, "powered": BOOL}
    if n.endswith("_fence_gate"):
        return {"facing": HORIZONTAL, "in_wall": BOOL, "open": BOOL, "powered": BOOL}
    if n.endswith("_fence") or n.endswith("pane") or n == "iron_bars":
        return {d: BOOL for d in HORIZONTAL} | wl
    if is_wall_block(n):
        return {**{d: {"none", "low", "tall"} for d in HORIZONTAL}, "up": BOOL, **wl}
    if n.endswith(("_log", "_wood", "_stem", "_hyphae")) and not is_plant(n) or n in (
            "hay_block", "basalt", "polished_basalt", "bone_block", "quartz_pillar", "purpur_pillar",
            "chain", "nether_portal", "bamboo_block", "stripped_bamboo_block", "muddy_mangrove_roots",
            "ochre_froglight", "verdant_froglight", "pearlescent_froglight", "deepslate"):
        return {"axis": {"x", "y", "z"} if n != "nether_portal" else {"x", "z"}}
    if n.endswith("_bed"):
        return {"facing": HORIZONTAL, "part": {"head", "foot"}, "occupied": BOOL}
    if n.endswith("_leaves"):
        return {"distance": {str(i) for i in range(1, 8)}, "persistent": BOOL, **wl}
    if n.endswith("glazed_terracotta"):
        return {"facing": HORIZONTAL}
    if n.endswith("_candle") or n == "candle":
        return {"candles": {"1", "2", "3", "4"}, "lit": BOOL, **wl}
    if n.endswith("_button"):
        return {"face": {"floor", "wall", "ceiling"}, "facing": HORIZONTAL, "powered": BOOL}
    if n.endswith("_pressure_plate"):
        return {"powered": BOOL} if "weighted" not in n else {"power": None}
    if n.endswith(("_wall_sign", "_wall_hanging_sign")):
        return {"facing": HORIZONTAL, **wl}
    if n.endswith("_hanging_sign"):
        return {"rotation": {str(i) for i in range(16)}, "attached": BOOL, **wl}
    if n.endswith("_sign"):
        return {"rotation": {str(i) for i in range(16)}, **wl}
    if n.endswith("_wall_banner"):
        return {"facing": HORIZONTAL}
    if n.endswith("_banner"):
        return {"rotation": {str(i) for i in range(16)}}
    table = {
        "beehive": {"facing": HORIZONTAL, "honey_level": {str(i) for i in range(6)}},
        "bee_nest": {"facing": HORIZONTAL, "honey_level": {str(i) for i in range(6)}},
        "melon_stem": {"age": {str(i) for i in range(8)}}, "pumpkin_stem": {"age": {str(i) for i in range(8)}},
        "attached_melon_stem": {"facing": HORIZONTAL}, "attached_pumpkin_stem": {"facing": HORIZONTAL},
        "pointed_dripstone": {"thickness": {"tip_merge", "tip", "frustum", "middle", "base"},
                              "vertical_direction": {"up", "down"}, **wl},
        "ladder": {"facing": HORIZONTAL, **wl},
        "wall_torch": {"facing": HORIZONTAL}, "soul_wall_torch": {"facing": HORIZONTAL},
        "redstone_wall_torch": {"facing": HORIZONTAL, "lit": BOOL}, "redstone_torch": {"lit": BOOL},
        "lantern": {"hanging": BOOL, **wl}, "soul_lantern": {"hanging": BOOL, **wl},
        "chest": {"facing": HORIZONTAL, "type": {"single", "left", "right"}, **wl},
        "trapped_chest": {"facing": HORIZONTAL, "type": {"single", "left", "right"}, **wl},
        "ender_chest": {"facing": HORIZONTAL, **wl},
        "barrel": {"facing": ALL_DIRS, "open": BOOL},
        "furnace": {"facing": HORIZONTAL, "lit": BOOL}, "blast_furnace": {"facing": HORIZONTAL, "lit": BOOL},
        "smoker": {"facing": HORIZONTAL, "lit": BOOL},
        "campfire": {"lit": BOOL, "signal_fire": BOOL, "facing": HORIZONTAL, **wl},
        "soul_campfire": {"lit": BOOL, "signal_fire": BOOL, "facing": HORIZONTAL, **wl},
        "anvil": {"facing": HORIZONTAL}, "chipped_anvil": {"facing": HORIZONTAL},
        "damaged_anvil": {"facing": HORIZONTAL},
        "grindstone": {"face": {"floor", "wall", "ceiling"}, "facing": HORIZONTAL},
        "lectern": {"facing": HORIZONTAL, "has_book": BOOL, "powered": BOOL},
        "loom": {"facing": HORIZONTAL}, "stonecutter": {"facing": HORIZONTAL},
        "bell": {"attachment": {"floor", "ceiling", "single_wall", "double_wall"}, "facing": HORIZONTAL,
                 "powered": BOOL},
        "composter": {"level": {str(i) for i in range(9)}},
        "water_cauldron": {"level": {"1", "2", "3"}}, "powder_snow_cauldron": {"level": {"1", "2", "3"}},
        "farmland": {"moisture": {str(i) for i in range(8)}},
        "wheat": {"age": {str(i) for i in range(8)}}, "carrots": {"age": {str(i) for i in range(8)}},
        "potatoes": {"age": {str(i) for i in range(8)}}, "beetroots": {"age": {"0", "1", "2", "3"}},
        "sugar_cane": {"age": {str(i) for i in range(16)}}, "cactus": {"age": {str(i) for i in range(16)}},
        "sweet_berry_bush": {"age": {"0", "1", "2", "3"}}, "nether_wart": {"age": {"0", "1", "2", "3"}},
        "water": {"level": {str(i) for i in range(16)}}, "lava": {"level": {str(i) for i in range(16)}},
        "end_rod": {"facing": ALL_DIRS},
        "lightning_rod": {"facing": ALL_DIRS, "powered": BOOL, **wl},
        "end_portal_frame": {"eye": BOOL, "facing": HORIZONTAL},
        "rail": {"shape": None, **wl},
        "snow": {"layers": {str(i) for i in range(1, 9)}},
        "vine": {**{d: BOOL for d in HORIZONTAL}, "up": BOOL},
        "carved_pumpkin": {"facing": HORIZONTAL}, "jack_o_lantern": {"facing": HORIZONTAL},
        "redstone_lamp": {"lit": BOOL},
        "repeater": {"delay": {"1", "2", "3", "4"}, "facing": HORIZONTAL, "locked": BOOL, "powered": BOOL},
        "comparator": {"facing": HORIZONTAL, "mode": {"compare", "subtract"}, "powered": BOOL},
        "redstone_wire": {**{d: {"up", "side", "none"} for d in HORIZONTAL},
                          "power": {str(i) for i in range(16)}},
        "sculk_sensor": {"sculk_sensor_phase": {"inactive", "active", "cooldown"},
                         "power": {str(i) for i in range(16)}, **wl},
        "calibrated_sculk_sensor": {"sculk_sensor_phase": {"inactive", "active", "cooldown"}, "facing": HORIZONTAL,
                                    "power": {str(i) for i in range(16)}, **wl},
        "daylight_detector": {"inverted": BOOL, "power": {str(i) for i in range(16)}},
        "piston": {"facing": ALL_DIRS, "extended": BOOL}, "sticky_piston": {"facing": ALL_DIRS, "extended": BOOL},
        "observer": {"facing": ALL_DIRS, "powered": BOOL},
        "copper_bulb": {"lit": BOOL, "powered": BOOL}, "waxed_copper_bulb": {"lit": BOOL, "powered": BOOL},
        "lever": {"face": {"floor", "wall", "ceiling"}, "facing": HORIZONTAL, "powered": BOOL},
        "tripwire_hook": {"attached": BOOL, "facing": HORIZONTAL, "powered": BOOL},
        "note_block": {"instrument": None, "note": {str(i) for i in range(25)}, "powered": BOOL},
        "sea_pickle": {"pickles": {"1", "2", "3", "4"}, **wl},
        "amethyst_cluster": {"facing": ALL_DIRS, **wl},
        "hopper": {"facing": {"down", "north", "south", "east", "west"}, "enabled": BOOL},
        "dispenser": {"facing": ALL_DIRS, "triggered": BOOL}, "dropper": {"facing": ALL_DIRS, "triggered": BOOL},
        "crafter": {"orientation": None, "crafting": BOOL, "triggered": BOOL},
        "bubble_column": {"drag": BOOL},
        "pink_petals": {"facing": HORIZONTAL, "flower_amount": {"1", "2", "3", "4"}},
        "tall_grass": {"half": {"upper", "lower"}}, "large_fern": {"half": {"upper", "lower"}},
        "sunflower": {"half": {"upper", "lower"}}, "lilac": {"half": {"upper", "lower"}},
        "rose_bush": {"half": {"upper", "lower"}}, "peony": {"half": {"upper", "lower"}},
        "scaffolding": {"bottom": BOOL, "distance": None, **wl},
        "brewing_stand": {"has_bottle_0": BOOL, "has_bottle_1": BOOL, "has_bottle_2": BOOL},
        "conduit": wl, "decorated_pot": {"facing": HORIZONTAL, "cracked": BOOL, **wl},
        "cocoa": {"age": {"0", "1", "2"}, "facing": HORIZONTAL},
        "bamboo": {"age": {"0", "1"}, "leaves": {"none", "small", "large"}, "stage": {"0", "1"}},
    }
    if n in table:
        return table[n]
    if n.endswith("_sapling"):
        return {"stage": {"0", "1"}}
    if n.endswith("mushroom_block") or n == "mushroom_stem":
        return {d: BOOL for d in ALL_DIRS}
    if n.endswith("shulker_box"):
        return {"facing": ALL_DIRS}
    return {}


# ---------------------------------------------------------------------------
# Colors (renderer)
# ---------------------------------------------------------------------------

_COLOR_RGB = {
    "white": (233, 236, 236), "orange": (240, 118, 19), "magenta": (189, 68, 179),
    "light_blue": (58, 175, 217), "yellow": (248, 197, 39), "lime": (112, 185, 25), "pink": (237, 141, 172),
    "gray": (62, 68, 71), "light_gray": (142, 142, 134), "cyan": (21, 137, 145), "purple": (121, 42, 172),
    "blue": (53, 57, 157), "brown": (114, 71, 40), "green": (84, 109, 27), "red": (161, 39, 34),
    "black": (20, 21, 25),
}
_WOOD_RGB = {
    "oak": (162, 130, 78), "spruce": (114, 84, 48), "birch": (196, 179, 123), "jungle": (160, 115, 80),
    "acacia": (168, 90, 50), "dark_oak": (66, 43, 20), "mangrove": (117, 54, 48), "cherry": (226, 178, 172),
    "bamboo": (194, 173, 80), "crimson": (101, 48, 70), "warped": (43, 104, 99),
}
_LOG_RGB = {
    "oak": (109, 85, 50), "spruce": (58, 37, 16), "birch": (216, 215, 210), "jungle": (85, 67, 25),
    "acacia": (103, 96, 86), "dark_oak": (60, 46, 26), "mangrove": (84, 66, 36), "cherry": (54, 33, 44),
    "crimson": (92, 25, 29), "warped": (58, 58, 77),
}
_KEYWORD_RGB = [
    ("water", (63, 118, 228)), ("lava", (207, 92, 20)), ("grass_block", (95, 159, 53)),
    ("leaves", (60, 120, 40)), ("dirt_path", (148, 122, 65)), ("farmland", (110, 75, 45)),
    ("podzol", (91, 63, 24)), ("mycelium", (111, 98, 101)), ("mud_brick", (137, 103, 79)), ("mud", (60, 57, 60)),
    ("dirt", (134, 96, 67)), ("red_sand", (190, 102, 33)), ("sand", (219, 207, 163)),
    ("gravel", (131, 127, 126)), ("clay", (160, 166, 179)),
    ("red_nether_brick", (69, 7, 9)), ("nether_brick", (44, 21, 26)), ("netherrack", (97, 38, 38)),
    ("red_sandstone", (186, 99, 29)), ("sandstone", (216, 203, 155)),
    ("quartz", (236, 230, 223)), ("calcite", (223, 224, 220)), ("purpur", (169, 125, 169)),
    ("end_stone", (219, 222, 158)), ("prismarine_brick", (99, 171, 158)), ("dark_prismarine", (51, 91, 75)),
    ("prismarine", (99, 156, 151)), ("crying_obsidian", (52, 15, 92)), ("obsidian", (15, 10, 24)),
    ("gilded_blackstone", (56, 43, 38)), ("blackstone", (42, 36, 41)), ("basalt", (73, 72, 77)),
    ("reinforced_deepslate", (80, 82, 78)), ("deepslate", (80, 80, 82)), ("tuff", (108, 109, 102)),
    ("mossy", (100, 118, 80)), ("cracked_stone", (118, 117, 118)), ("stone_brick", (122, 121, 122)),
    ("smooth_stone", (158, 158, 158)), ("cobblestone", (127, 127, 127)), ("andesite", (136, 136, 136)),
    ("diorite", (188, 188, 188)), ("granite", (149, 103, 85)), ("brick", (150, 97, 83)),
    ("stone", (125, 125, 125)), ("bedrock", (85, 85, 85)),
    ("iron_bars", (110, 110, 112)), ("iron", (220, 220, 220)), ("gold", (246, 208, 61)),
    ("diamond", (98, 237, 228)), ("emerald", (42, 203, 87)), ("lapis", (30, 67, 140)),
    ("redstone_block", (175, 24, 5)), ("copper", (192, 107, 79)), ("coal_block", (16, 15, 15)),
    ("amethyst", (133, 97, 191)), ("hay", (166, 136, 38)), ("bone_block", (229, 225, 207)),
    ("melon", (111, 145, 30)), ("pumpkin", (198, 118, 24)), ("jack_o_lantern", (214, 152, 52)),
    ("glowstone", (171, 131, 84)), ("sea_lantern", (172, 199, 190)), ("shroomlight", (240, 146, 70)),
    ("froglight", (245, 233, 182)), ("magma", (142, 63, 31)), ("snow", (249, 254, 254)),
    ("packed_ice", (141, 180, 250)), ("blue_ice", (116, 167, 253)), ("ice", (145, 183, 253)),
    ("bookshelf", (117, 94, 59)), ("crafting_table", (120, 73, 42)), ("furnace", (110, 110, 110)),
    ("smoker", (107, 106, 104)), ("chest", (164, 116, 42)), ("barrel", (134, 100, 58)),
    ("anvil", (68, 68, 68)), ("cauldron", (74, 73, 74)), ("composter", (117, 72, 32)),
    ("lectern", (173, 137, 83)), ("enchanting_table", (128, 40, 40)), ("beacon", (117, 220, 215)),
    ("bell", (253, 229, 92)), ("ladder", (125, 97, 55)), ("torch", (255, 214, 90)),
    ("lantern", (106, 91, 83)), ("campfire", (110, 80, 50)), ("end_rod", (240, 236, 230)),
    ("lightning_rod", (192, 107, 79)), ("rail", (125, 112, 95)), ("cobweb", (228, 233, 234)),
    ("sculk", (12, 30, 36)), ("moss", (89, 109, 45)), ("vine", (50, 100, 30)), ("lily_pad", (35, 120, 35)),
    ("sugar_cane", (148, 192, 101)), ("cactus", (85, 127, 43)), ("bamboo", (93, 144, 19)),
    ("wheat", (204, 180, 80)), ("carrots", (100, 160, 40)), ("potatoes", (90, 150, 40)),
    ("beetroots", (110, 140, 50)), ("poppy", (200, 30, 30)), ("dandelion", (240, 220, 40)),
    ("tulip", (220, 90, 60)), ("orchid", (40, 160, 220)), ("allium", (180, 110, 220)),
    ("cornflower", (70, 100, 220)), ("flower_pot", (124, 68, 52)), ("potted", (124, 68, 52)),
    ("mushroom_stem", (203, 196, 185)), ("red_mushroom_block", (200, 46, 45)),
    ("brown_mushroom_block", (149, 111, 81)), ("short_grass", (100, 160, 60)), ("fern", (90, 140, 60)),
    ("nether_portal", (110, 30, 200)), ("end_portal_frame", (90, 120, 100)), ("spawner", (30, 40, 50)),
    ("terracotta", (152, 94, 68)), ("glass", (200, 225, 235)), ("slime", (110, 190, 90)),
    ("honey", (240, 170, 30)), ("sponge", (196, 192, 75)), ("target", (230, 175, 160)),
    ("note_block", (88, 58, 40)), ("jukebox", (93, 64, 47)), ("loom", (142, 119, 91)),
    ("stonecutter", (120, 118, 116)), ("grindstone", (140, 140, 140)), ("smithing", (60, 60, 70)),
    ("fletching", (196, 180, 130)), ("cartography", (100, 75, 50)), ("brewing", (120, 100, 80)),
    ("chain", (60, 65, 75)), ("skull", (200, 200, 200)), ("head", (200, 200, 200)),
]


def block_color(n):
    """(r, g, b, a) used by the isometric renderer."""
    n = short(n)
    alpha = 255
    if "glass" in n:
        alpha = 110
    if n == "water":
        alpha = 150
    for c in sorted(_COLOR_RGB, key=len, reverse=True):
        if n.startswith(c + "_") and any(s in n for s in ("wool", "carpet", "concrete", "terracotta", "glass",
                                                           "bed", "candle", "banner", "shulker")):
            r, g, b = _COLOR_RGB[c]
            if "terracotta" in n and "glazed" not in n:
                r, g, b = (int(r * 0.6 + 90), int(g * 0.5 + 50), int(b * 0.5 + 40))
            return (r, g, b, alpha)
    for w in sorted(_WOOD_RGB, key=len, reverse=True):
        if w + "_" in n or n.startswith(w):
            if n.endswith("_leaves"):
                break
            if any(n.endswith(s) for s in ("_log", "_wood", "_stem", "_hyphae")) and "stripped" not in n:
                return (*_LOG_RGB.get(w, _WOOD_RGB[w]), alpha)
            if n.startswith(w + "_") or n.startswith("stripped_" + w):
                return (*_WOOD_RGB[w], alpha)
    if n == "cherry_leaves":
        return (230, 160, 190, 255)
    for key, rgb in _KEYWORD_RGB:
        if key in n:
            return (*rgb, alpha)
    return (170, 170, 170, alpha)
