"""
Catalogo delle strutture: categorie in italiano, titoli e descrizioni.

Unisce:
- templates/catalog.json      template generati da tools/build_templates.py
- le strutture originali del repository
- templates/user_catalog.json ritagli e strutture salvate dall'utente
"""
import json
import os
import re

TEMPLATES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates")
USER_CATALOG = os.path.join(TEMPLATES_DIR, "user_catalog.json")

CATEGORIES = [
    "Case", "Castelli e fortezze", "Torri", "Ponti", "Monumenti", "Templi e luoghi sacri",
    "Fattorie e animali", "Farm automatiche", "Hub e magazzini", "Piazze e decorazioni", "Utilità e magia", "Navi", "Rovine e portali",
    "Fantascienza", "Ritagli", "Altro",
]

CATEGORY_OF = {
    # Case
    "starter_cottage": "Case", "plains_village_house": "Case", "tudor_house": "Case", "modern_villa": "Case",
    "hobbit_hole": "Case", "treehouse": "Case", "igloo": "Case", "witch_hut": "Case",
    "viking_longhouse": "Case", "medieval_tavern": "Case", "blacksmith_forge": "Case", "modern_house": "Case",
    "beach_shack": "Case",
    # Castelli e fortezze
    "castle_keep": "Castelli e fortezze", "castle_gatehouse": "Castelli e fortezze",
    "fairytale_castle": "Castelli e fortezze", "pillager_outpost": "Castelli e fortezze",
    "great_wall": "Castelli e fortezze",
    # Torri
    "watchtower": "Torri", "lighthouse": "Torri", "leaning_tower_pisa": "Torri", "big_ben": "Torri",
    "eiffel_tower": "Torri", "wizard_tower": "Torri", "end_city_tower": "Torri", "skyscraper": "Torri",
    "space_needle": "Torri", "obelisk": "Torri", "castle_tower": "Torri",
    # Ponti
    "stone_bridge": "Ponti", "suspension_bridge": "Ponti", "tower_bridge": "Ponti",
    "nether_fortress_bridge": "Ponti",
    # Monumenti
    "colosseum": "Monumenti", "great_pyramid": "Monumenti", "stonehenge": "Monumenti", "taj_mahal": "Monumenti",
    "moai_heads": "Monumenti", "arc_de_triomphe": "Monumenti", "dutch_windmill": "Monumenti",
    # Templi e luoghi sacri
    "parthenon": "Templi e luoghi sacri", "pantheon": "Templi e luoghi sacri",
    "gothic_cathedral": "Templi e luoghi sacri", "onion_dome_cathedral": "Templi e luoghi sacri",
    "five_storey_pagoda": "Templi e luoghi sacri", "temple_of_heaven": "Templi e luoghi sacri",
    "torii_gate": "Templi e luoghi sacri", "village_chapel": "Templi e luoghi sacri",
    "el_castillo": "Templi e luoghi sacri", "desert_temple": "Templi e luoghi sacri",
    "jungle_temple": "Templi e luoghi sacri", "dread_mausoleum": "Templi e luoghi sacri",
    "graveyard": "Templi e luoghi sacri",
    # Fattorie e animali
    "crop_farm": "Fattorie e animali", "animal_pen": "Fattorie e animali", "sugar_cane_farm": "Fattorie e animali",
    "greenhouse": "Fattorie e animali", "horse_stable": "Fattorie e animali", "wheat_farm": "Fattorie e animali",
    # Piazze e decorazioni
    "village_well": "Piazze e decorazioni", "desert_well": "Piazze e decorazioni",
    "market_stall": "Piazze e decorazioni", "fountain_plaza": "Piazze e decorazioni",
    "zen_garden": "Piazze e decorazioni",
    # Utilità e magia
    "villager_trading_hall": "Utilità e magia", "enchanting_room": "Utilità e magia",
    "beacon_pyramid": "Utilità e magia", "nether_portal_shrine": "Utilità e magia",
    "auto_warehouse": "Utilità e magia", "portal_room": "Utilità e magia", "treasure_room": "Utilità e magia",
    # Navi
    "pirate_ship": "Navi", "sea_boat": "Navi",
    # Rovine e portali
    "ruined_portal": "Rovine e portali", "ancient_city_portal": "Rovine e portali",
    # Fantascienza
    "space_station": "Fantascienza", "sky_fan": "Fantascienza",
    # Strutture vetrina
    "himeji_castle": "Castelli e fortezze", "city_gate": "Castelli e fortezze",
    "santorini_villa": "Case", "cottage_garden": "Case", "victorian_mansion": "Case", "alpine_chalet": "Case",
    "red_barn": "Fattorie e animali", "watermill": "Fattorie e animali",
    "stave_church": "Templi e luoghi sacri", "chinese_pavilion": "Piazze e decorazioni",
    "cherry_temple": "Templi e luoghi sacri", "kinkaku_ji": "Templi e luoghi sacri",
    "neuschwanstein": "Castelli e fortezze",
    # Moduli tecnici (docs/PROMPT_ARCHITETTO.md)
    "underground_hub": "Hub e magazzini", "iron_farm": "Farm automatiche",
}

# Strutture originali del repository (non generate dagli script)
ORIGINALS = {
    "wheat_farm": ("Automatic Wheat Farm (9x9)", "Fattoria di grano compatta con acqua centrale."),
    "modern_house": ("Medieval Scriber House", "Casa dello scrivano con tavoli, sedie e librerie (Ice and Fire)."),
    "castle_tower": ("Gorgon Temple Tower", "Torre del tempio della gorgone con pilastri di pietra (Ice and Fire)."),
    "auto_warehouse": ("Grand Library Warehouse", "Grande biblioteca su piu' livelli (Better Strongholds)."),
    "portal_room": ("Ender Portal Room", "Stanza del portale dell'End con lava e sbarre (Better Strongholds)."),
    "dread_mausoleum": ("Dread Mausoleum", "Mausoleo in pietra del terrore (richiede la mod Ice and Fire)."),
    "space_station": ("Futuristic Space Station", "Stazione spaziale (richiede mod: Ad Astra, AE2)."),
    "beach_shack": ("Beach Shack", "Capanno sulla spiaggia con portico (richiede la mod Chipped)."),
    "treasure_room": ("Stronghold Treasure Room", "Stanza del tesoro con colonne e casse (Better Strongholds)."),
    "graveyard": ("Gothic Graveyard", "Cimitero gotico con tombe e muri di mattoni."),
    "sea_boat": ("Sea Boat", "Barca rustica in legno per fiumi e coste."),
    "sky_fan": ("Sky Fan", "Elica industriale sospesa."),
}

# Template ridimensionabili: nome file -> stile del generatore di ponti (structure_generators)
BRIDGE_STYLE_OF = {
    "stone_bridge": "stone",
    "suspension_bridge": "suspension",
    "nether_fortress_bridge": "nether",
}


_GUESS = [
    (("iron_farm", "golem", "mob_farm", "xp_farm", "gold_farm", "raid_farm", "auto_farm"), "Farm automatiche"),
    (("hub", "storage", "magazzin", "sorter", "smistat"), "Hub e magazzini"),
    (("bridge", "ponte"), "Ponti"),
    (("castle", "castello", "fort", "keep", "citadel", "gate"), "Castelli e fortezze"),
    (("tower", "torre", "lighthouse", "faro", "spire"), "Torri"),
    (("farm", "fattoria", "barn", "stable", "pen", "coop", "silo", "crop", "field"), "Fattorie e animali"),
    (("temple", "tempio", "church", "chiesa", "chapel", "cathedral", "shrine", "pagoda", "mosque"),
     "Templi e luoghi sacri"),
    (("house", "casa", "home", "cottage", "hut", "cabin", "villa", "mansion", "shack", "inn", "tavern"), "Case"),
    (("ship", "boat", "nave", "barca"), "Navi"),
    (("portal", "portale", "ruin", "rovina"), "Rovine e portali"),
    (("fountain", "well", "statue", "garden", "plaza", "market", "fontana", "piazza"), "Piazze e decorazioni"),
    (("monument", "pyramid", "arch", "colosseum", "monumento"), "Monumenti"),
    (("space", "rocket", "station", "sci"), "Fantascienza"),
]


def category_for(name):
    """Italian category of a structure: known templates, otherwise guessed from the file name."""
    if name in CATEGORY_OF:
        return CATEGORY_OF[name]
    low = name.lower()
    tokens = set(re.split(r"[^a-z0-9]+", low))
    for words, category in _GUESS:
        # whole words ("dwelling" is not a "well"), or the start of a word for the Italian stems
        if any(w in tokens or (len(w) >= 5 and any(t.startswith(w) for t in tokens)) or ("_" in w and w in low)
               for w in words):
            return category
    return "Altro"


def _load_json(path):
    """List of catalog entries; anything malformed (wrong shape, missing file name) is skipped."""
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return []
    if not isinstance(data, list):
        return []
    out = []
    for e in data:
        if isinstance(e, dict) and isinstance(e.get("file"), str) and e["file"]:
            e = dict(e)
            if not isinstance(e.get("title"), str) or not e["title"]:
                e["title"] = os.path.splitext(e["file"])[0].replace("_", " ").title()
            out.append(e)
    return out


def load_user_catalog():
    return _load_json(USER_CATALOG)


def add_user_entry(file, title, category="Ritagli", description="", extra=None):
    entries = [e for e in load_user_catalog() if e.get("file") != file]
    entry = {"file": file, "title": title, "category": category, "description": description}
    entry.update(extra or {})
    entries.append(entry)
    tmp = USER_CATALOG + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(entries, f, ensure_ascii=False, indent=1)
    os.replace(tmp, USER_CATALOG)


def load_catalog(templates_dir=TEMPLATES_DIR):
    """All structure files in templates_dir as [{file, title, category, description}], sorted."""
    known = {}
    for e in _load_json(os.path.join(templates_dir, "catalog.json")):
        known[e["file"]] = dict(e)
    for name, (title, desc) in ORIGINALS.items():
        known.setdefault(f"{name}.nbt", {"file": f"{name}.nbt", "title": title, "description": desc})
    for e in _load_json(os.path.join(templates_dir, "user_catalog.json")):
        known[e["file"]] = dict(e)
    entries = []
    for f in sorted(os.listdir(templates_dir)) if os.path.isdir(templates_dir) else []:
        if not f.lower().endswith((".nbt", ".schem", ".schematic")):
            continue
        name = os.path.splitext(f)[0]
        e = known.get(f, {"file": f, "title": name.replace("_", " ").title(), "description": "Struttura importata."})
        if e.get("category") not in CATEGORIES:
            e["category"] = category_for(name)
        if name in BRIDGE_STYLE_OF:
            e["bridge_style"] = BRIDGE_STYLE_OF[name]
        entries.append(e)
    order = {c: i for i, c in enumerate(CATEGORIES)}
    return sorted(entries, key=lambda e: (order.get(e["category"], len(order)), e["title"].lower()))
