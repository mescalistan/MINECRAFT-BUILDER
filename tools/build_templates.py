"""
Genera i template vanilla (Minecraft 1.21) nella cartella templates/ e il
catalogo templates/catalog.json usato dall'app.

Uso:
    python tools/build_templates.py            # genera tutti i template
    python tools/build_templates.py lighthouse # genera solo quello indicato
    python tools/build_templates.py --list     # elenca i template disponibili

I template sono definiti nei moduli di tools/templates/ con il decoratore
@template(...) di template_builder. Il livello y=0 di ogni template e' il primo
strato d'aria sopra il terreno (la quota calcolata da "Adatta altezza al terreno").
"""
import importlib
import json
import os
import pkgutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from template_builder import REGISTRY

sys.path.insert(0, os.path.join(HERE, ".."))
import catalog

TEMPLATES_DIR = os.path.join(HERE, "..", "templates")
CATALOG_PATH = os.path.join(TEMPLATES_DIR, "catalog.json")


def all_templates():
    """Imports every module of tools/templates/ and returns the registry."""
    import templates as pkg
    for mod in pkgutil.iter_modules(pkg.__path__):
        importlib.import_module(f"templates.{mod.name}")
    return REGISTRY


def build(name):
    entry = all_templates()[name]
    builder = entry["fn"]()
    # no dark corners where mobs spawn (sealed attics, big halls): a lantern on each dark floor
    from validate_templates import auto_light
    for x, y, z in auto_light(builder.to_structure()):
        builder.lantern(x, y, z)
    builder.save(os.path.join(TEMPLATES_DIR, f"{name}.nbt"))
    return builder


def write_catalog(reg):
    entries = []
    for name, entry in sorted(reg.items(), key=lambda kv: (catalog.category_for(kv[0]), kv[1]["title"])):
        entries.append({
            "file": f"{name}.nbt",
            "title": entry["title"],
            "category": catalog.CATEGORY_OF.get(name) or (
                entry["category"] if entry["category"] in catalog.CATEGORIES else "Altro"),
            "description": entry["description"],
        })
    with open(CATALOG_PATH, "w", encoding="utf-8") as f:
        json.dump(entries, f, ensure_ascii=False, indent=1)


def main(argv):
    reg = all_templates()
    if "--list" in argv:
        for name, e in sorted(reg.items(), key=lambda kv: (kv[1]["category"], kv[0])):
            print(f"{e['category']:12s} {name:28s} {e['title']}")
        return
    names = [a for a in argv if not a.startswith("--")] or sorted(reg)
    for name in names:
        if name not in reg:
            print(f"Template sconosciuto: {name}. Usa --list per l'elenco.")
            continue
        b = build(name)
        print(f"{name:28s} {b.w:3d}x{b.h:3d}x{b.l:3d}  {len(b.cells):6d} celle")
    write_catalog(reg)
    print(f"\n{len(names)} template generati, catalogo: {os.path.relpath(CATALOG_PATH)}")


if __name__ == "__main__":
    main(sys.argv[1:])
