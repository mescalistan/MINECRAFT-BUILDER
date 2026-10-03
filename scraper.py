import requests
from bs4 import BeautifulSoup
import urllib.parse
import os
import shutil

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
}

# Curated online registry of open, direct-download schematic assets
CURATED_ONLINE_CATALOG = [
    {
        "title": "Automatic Wheat Farm (9x9)",
        "category": "Farm",
        "description": "Compact, efficient wheat farm with a central water source and outer safety borders.",
        "author": "Antigravity",
        "download_url": "local:wheat_farm.nbt",
        "source": "Built-in Library"
    },
    {
        "title": "Medieval Scriber House",
        "category": "House",
        "description": "Detailed medieval village scriber house with tables, chairs, and bookshelves.",
        "author": "Ice and Fire",
        "download_url": "local:modern_house.nbt",
        "source": "Built-in Library"
    },
    {
        "title": "Gorgon Temple Tower",
        "category": "Castle",
        "description": "Gorgon temple structure with stone pillars and detailed roof tiling.",
        "author": "Ice and Fire",
        "download_url": "local:castle_tower.nbt",
        "source": "Built-in Library"
    },
    {
        "title": "Grand Library Warehouse",
        "category": "Utility",
        "description": "Massive grand library room with multi-level floors, decorative columns, and chest stacks.",
        "author": "Better Strongholds",
        "download_url": "local:auto_warehouse.nbt",
        "source": "Built-in Library"
    },
    {
        "title": "Ender Portal Room",
        "category": "Utility",
        "description": "Ender Portal room with lava pools, iron bars, and the ender portal frame blocks.",
        "author": "Better Strongholds",
        "download_url": "local:portal_room.nbt",
        "source": "Built-in Library"
    },
    {
        "title": "Dread Mausoleum",
        "category": "Medieval",
        "description": "Intricately detailed mausoleum made of dark cobble and dread stones.",
        "author": "Ice and Fire",
        "download_url": "local:dread_mausoleum.nbt",
        "source": "Built-in Library"
    },
    {
        "title": "Futuristic Space Station",
        "category": "Futuristic",
        "description": "Futuristic space station base room with high-tech wall designs.",
        "author": "Create Astral",
        "download_url": "local:space_station.nbt",
        "source": "Built-in Library"
    },
    {
        "title": "Beach Shack",
        "category": "House",
        "description": "Cozy wooden beach shack with a porch and windows.",
        "author": "Create Astral",
        "download_url": "local:beach_shack.nbt",
        "source": "Built-in Library"
    },
    {
        "title": "Stronghold Treasure Room",
        "category": "Castle",
        "description": "Ornate treasure room with columns, carved stone brick structures, and chests.",
        "author": "Better Strongholds",
        "download_url": "local:treasure_room.nbt",
        "source": "Built-in Library"
    },
    {
        "title": "Gothic Graveyard",
        "category": "Medieval",
        "description": "Creepy graveyard structure with tombs, dirt piles, and brick wall boundaries.",
        "author": "Ice and Fire",
        "download_url": "local:graveyard.nbt",
        "source": "Built-in Library"
    },
    {
        "title": "Sea Boat",
        "category": "Utility",
        "description": "Rustic wooden boat structure, perfect for rivers or shorelines.",
        "author": "StructureTutorialMod",
        "download_url": "local:sea_boat.nbt",
        "source": "Built-in Library"
    },
    {
        "title": "Sky Fan",
        "category": "Utility",
        "description": "Industrial redstone sky propeller/fan structure.",
        "author": "StructureTutorialMod",
        "download_url": "local:sky_fan.nbt",
        "source": "Built-in Library"
    }
]

def search_minecraft_schematics(query):
    """
    Scrapes minecraft-schematics.com for creations matching the query.
    Returns metadata list (titles, links, categories).
    """
    results = []
    
    # First add matching elements from the curated catalog
    for item in CURATED_ONLINE_CATALOG:
        if query.lower() in item["title"].lower() or query.lower() in item["category"].lower():
            results.append({
                "id": f"curated_{item['title'].replace(' ', '_').lower()}",
                "title": item["title"],
                "url": item["download_url"],
                "category": item["category"],
                "author": item["author"],
                "description": item["description"],
                "download_url": item["download_url"],
                "source": item["source"]
            })
            
    # Then query minecraft-schematics.com
    safe_query = urllib.parse.quote(query)
    url = f"https://www.minecraft-schematics.com/schematics/search/{safe_query}/"
    
    try:
        r = requests.get(url, headers=HEADERS, timeout=8)
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, 'html.parser')
            # Fetch links that lead to schematic details
            links = soup.find_all('a', href=True)
            seen_ids = set()
            for l in links:
                href = l['href']
                if href.startswith('/schematic/') and href != '/schematic/':
                    parts = href.strip('/').split('/')
                    if len(parts) >= 2 and parts[1].isdigit():
                        schem_id = parts[1]
                        if schem_id in seen_ids:
                            continue
                        seen_ids.add(schem_id)
                        
                        # Get title
                        title = l.get_text(strip=True)
                        if not title:
                            img = l.find('img')
                            if img:
                                title = img.get('alt', '')
                        if not title:
                            title = f"Schematic #{schem_id}"
                            
                        # Extract metadata
                        parent = l.find_parent('div', class_='panel') or l.find_parent('td') or l.find_parent('div')
                        category = "General"
                        author = "Web Creator"
                        description = f"Click to view on Minecraft-Schematics (requires login to download)."
                        
                        if parent:
                            text = parent.get_text()
                            if "Author:" in text:
                                try:
                                    author = text.split("Author:")[1].split("\n")[0].strip()
                                except:
                                    pass
                            if "Category:" in text:
                                try:
                                    category = text.split("Category:")[1].split("\n")[0].strip()
                                except:
                                    pass
                                    
                        results.append({
                            "id": schem_id,
                            "title": title,
                            "url": f"https://www.minecraft-schematics.com{href}",
                            "category": category,
                            "author": author,
                            "description": description,
                            "download_url": f"https://www.minecraft-schematics.com/schematic/{schem_id}/download/",
                            "source": "Minecraft-Schematics"
                        })
    except Exception as e:
        print(f"Scraper web connection error: {e}")
        
    return results

def download_structure(url, dest_path, templates_dir):
    """
    Downloads a schematic structure. Supports local copy fallback for built-in items.
    """
    # Handle built-in local items
    if url.startswith("local:"):
        local_name = url.split("local:")[1]
        local_path = os.path.join(templates_dir, local_name)
        if os.path.exists(local_path):
            try:
                shutil.copy2(local_path, dest_path)
                return True
            except Exception as e:
                print(f"Failed to copy local template: {e}")
                return False
        return False
        
    # Download external files
    try:
        r = requests.get(url, headers=HEADERS, stream=True, timeout=12)
        if r.status_code == 200:
            os.makedirs(os.path.dirname(os.path.abspath(dest_path)), exist_ok=True)
            with open(dest_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
            return True
        else:
            print(f"Web download returned status code {r.status_code}")
    except Exception as e:
        print(f"Web download error: {e}")
        
    # Fallback to templates if it was a curated item but connection failed
    for item in CURATED_ONLINE_CATALOG:
        if item["download_url"] == url:
            # Match titles to copy local
            if "Wheat" in item["title"]:
                fallback_path = os.path.join(templates_dir, "wheat_farm.nbt")
            elif "House" in item["title"]:
                fallback_path = os.path.join(templates_dir, "modern_house.nbt")
            else:
                fallback_path = os.path.join(templates_dir, "auto_warehouse.nbt")
                
            if os.path.exists(fallback_path):
                shutil.copy2(fallback_path, dest_path)
                return True
                
    return False
