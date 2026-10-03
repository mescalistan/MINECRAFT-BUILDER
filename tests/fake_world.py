"""Builds small synthetic 1.18+ worlds for the tests (no Minecraft install needed)."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from nbt_codec import (
    TAG_Compound, TAG_List, TAG_String, TAG_Int, TAG_Byte, TAG_Byte_Array, TAG_Long_Array,
    nbt_to_bytes, parse_nbt_bytes,
)
from mca_codec import MCARegion, write_section_indices, recalculate_heightmaps

GROUND_Y = 63  # grass_block at y=63, dirt below down to 60, stone below


def _state(name):
    return TAG_Compound({"Name": TAG_String("minecraft:" + name)})


def make_chunk(chunk_x, chunk_z, ground_y=GROUND_Y, status="minecraft:full"):
    palette = [_state("air"), _state("stone"), _state("dirt"), _state("grass_block")]
    sections = TAG_List(10)
    for sy in range(-4, 20):
        indices = []
        for i in range(4096):
            y = sy * 16 + (i >> 8)
            if y < ground_y - 3:
                indices.append(1)
            elif y < ground_y:
                indices.append(2)
            elif y == ground_y:
                indices.append(3)
            else:
                indices.append(0)
        sec = TAG_Compound({
            "Y": TAG_Byte(sy),
            "biomes": TAG_Compound({"palette": TAG_List(8, [TAG_String("minecraft:plains")])}),
            "SkyLight": TAG_Byte_Array(b"\xff" * 2048),
        })
        write_section_indices(sec, palette, indices)
        sections.append(sec)
    chunk = TAG_Compound({
        "DataVersion": TAG_Int(3955),
        "xPos": TAG_Int(chunk_x),
        "zPos": TAG_Int(chunk_z),
        "yPos": TAG_Int(-4),
        "Status": TAG_String(status),
        "isLightOn": TAG_Byte(1),
        "sections": sections,
        "block_entities": TAG_List(10, []),
    })
    recalculate_heightmaps(chunk)
    chunk["Heightmaps"]["MOTION_BLOCKING"] = TAG_Long_Array(list(chunk["Heightmaps"]["WORLD_SURFACE"]))
    return chunk


def make_region(region_dir, rx, rz, chunks=None, ground_y=GROUND_Y):
    """chunks: iterable of local (cx, cz); default all 1024."""
    os.makedirs(region_dir, exist_ok=True)
    region = MCARegion(os.path.join(region_dir, f"r.{rx}.{rz}.mca"))
    keys = chunks if chunks is not None else [(cx, cz) for cz in range(32) for cx in range(32)]
    template = nbt_to_bytes(make_chunk(0, 0, ground_y))
    for cx, cz in keys:
        # Cheap copy: re-parse the template bytes and patch the coordinates
        chunk, _ = parse_nbt_bytes(template)
        chunk["xPos"] = TAG_Int(rx * 32 + cx)
        chunk["zPos"] = TAG_Int(rz * 32 + cz)
        region.chunks[(cx, cz)] = (chunk, 1700000000)
    region.save()
    return region
