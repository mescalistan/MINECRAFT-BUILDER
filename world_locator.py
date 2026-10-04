"""
Finds a Minecraft world from any path the user points at.

Accepted inputs: the world folder itself, any folder or file inside it
(region/, DIM-1/, playerdata/, level.dat, r.0.0.mca...), the saves folder,
or the .minecraft folder.
"""
import os
import sys

# (label, legacy path, 1.21+ "dimensions" path) relative to the world folder
DIMENSIONS = [
    ("Overworld", ("region",), ("dimensions", "minecraft", "overworld", "region")),
    ("Nether", ("DIM-1", "region"), ("dimensions", "minecraft", "the_nether", "region")),
    ("End", ("DIM1", "region"), ("dimensions", "minecraft", "the_end", "region")),
]
DIMENSION_IDS = {"Overworld": "minecraft:overworld", "Nether": "minecraft:the_nether", "End": "minecraft:the_end"}


def default_saves_dir():
    """The standard saves folder of the Java Edition launcher on this OS."""
    if sys.platform == "win32":
        base = os.path.expandvars(r"%APPDATA%\.minecraft")
    elif sys.platform == "darwin":
        base = os.path.expanduser("~/Library/Application Support/minecraft")
    else:
        base = os.path.expanduser("~/.minecraft")
    return os.path.join(base, "saves")


def is_world(path):
    """A world folder has level.dat; a world copied without it is still usable if it has region files."""
    if not path or not os.path.isdir(path):
        return False
    return os.path.isfile(os.path.join(path, "level.dat")) or bool(region_dirs(path))


def list_worlds(saves_dir):
    """World folder names in saves_dir, most recently played first. Folders without level.dat are ignored."""
    if not saves_dir or not os.path.isdir(saves_dir):
        return []
    worlds = []
    for name in os.listdir(saves_dir):
        path = os.path.join(saves_dir, name)
        if is_world(path):
            level = os.path.join(path, "level.dat")
            worlds.append((os.path.getmtime(level if os.path.exists(level) else path), name))
    return [name for _, name in sorted(worlds, reverse=True)]


def region_dirs(world_path):
    """[(label, region_dir)] of the dimensions that have at least one .mca file."""
    found = []
    for label, legacy, modern in DIMENSIONS:
        for rel in (legacy, modern):
            d = os.path.join(world_path, *rel)
            if os.path.isdir(d) and any(f.endswith(".mca") for f in os.listdir(d)):
                found.append((label, d))
                break
    return found


def _dimension_from_path(world_path, path):
    rel = os.path.relpath(os.path.abspath(path), os.path.abspath(world_path)).replace("\\", "/").lower()
    if rel.startswith("dim-1") or "the_nether" in rel:
        return "Nether"
    if rel.startswith("dim1/") or rel == "dim1" or "the_end" in rel:
        return "End"
    return None


def resolve(path):
    """
    Returns {"saves_dir", "world", "dimension"} for any path related to a world
    (world/dimension may be None), or None if nothing usable is found.
    """
    if not path:
        return None
    path = os.path.abspath(os.path.expanduser(path.strip().strip('"')))
    if not os.path.exists(path):
        return None
    start = path if os.path.isdir(path) else os.path.dirname(path)

    # Inside a world (or the world folder itself): walk up to the world folder.
    # level.dat wins; region files alone count only outside dimension folders (DIM-1 has its own region/).
    chain = [start]
    while len(chain) < 7 and os.path.dirname(chain[-1]) != chain[-1]:
        chain.append(os.path.dirname(chain[-1]))
    world = next((d for d in chain if os.path.isfile(os.path.join(d, "level.dat"))), None)
    if world is None:
        world = next((d for d in chain if is_world(d) and os.path.basename(d) not in ("DIM-1", "DIM1", "region")
                      and "dimensions" not in os.path.normpath(d).split(os.sep)), None)
    if world:
        return {
            "saves_dir": os.path.dirname(world),
            "world": os.path.basename(world),
            "dimension": _dimension_from_path(world, path),
        }

    # A saves folder, or a .minecraft folder containing one
    for candidate in (start, os.path.join(start, "saves")):
        if list_worlds(candidate):
            return {"saves_dir": candidate, "world": None, "dimension": None}
    return None
