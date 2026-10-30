"""Extracts Valheim's crafting recipes and building pieces from the game's asset files.

    python tools/extract_game_data.py <valheim_server_Data dir> <out.json>

Needs UnityPy (pip install UnityPy). Output, per recipe and piece: the result prefab, the
crafting station prefab and minimum level, and the ingredients as (prefab, amount). Item
display tokens ($item_...) are included so names can be localized later.
Asset references are (file, path id) pairs; refs into other files go through the
file's externals list, which names the target by its CAB.
"""
import json
import os
import sys

import UnityPy

data_dir, out_path = sys.argv[1], sys.argv[2]

game_objects = {}   # (cab, path_id) -> GameObject name
behaviours = {}     # (cab, path_id) -> (kind, typetree, cab of the file, externals)


def cab_of(assets_file):
    return os.path.basename(assets_file.name).lower()


def kind_of(tree):
    if "m_item" in tree and "m_resources" in tree and "m_craftingStation" in tree:
        return "recipe"
    if "m_resources" in tree and "m_craftingStation" in tree and "m_category" in tree:
        return "piece"
    if "m_itemData" in tree:
        return "itemdrop"
    if "m_craftRequireRoof" in tree:
        return "station"
    return None


for dirpath, _, files in os.walk(data_dir):
    for name in files:
        try:
            env = UnityPy.load(os.path.join(dirpath, name))
        except Exception:
            continue
        for obj in env.objects:
            cab = cab_of(obj.assets_file)
            if obj.type.name == "GameObject":
                try:
                    game_objects[(cab, obj.path_id)] = obj.peek_name() or obj.read().m_Name
                except Exception:
                    pass
            elif obj.type.name == "MonoBehaviour":
                try:
                    tree = obj.read_typetree()
                except Exception:
                    continue
                kind = kind_of(tree)
                if kind:
                    externals = [os.path.basename(e.path).lower() for e in obj.assets_file.externals]
                    behaviours[(cab, obj.path_id)] = (kind, tree, cab, externals)


def resolve(pptr, cab, externals):
    file_id, path_id = pptr.get("m_FileID", 0), pptr.get("m_PathID", 0)
    if not path_id:
        return None
    target_cab = cab if file_id == 0 else (externals[file_id - 1] if file_id - 1 < len(externals) else None)
    return (target_cab, path_id) if target_cab else None


def component_owner(key):
    """GameObject name owning the component at `key` (an ItemDrop, CraftingStation, Piece...)."""
    entry = behaviours.get(key)
    if not entry:
        return None
    _, tree, cab, externals = entry
    go = resolve(tree.get("m_GameObject", {}), cab, externals)
    return game_objects.get(go) if go else None


def ingredients(tree, cab, externals):
    out = []
    for res in tree.get("m_resources", []):
        ref = resolve(res.get("m_resItem", {}), cab, externals)
        out.append({"item": component_owner(ref) if ref else None, "amount": res.get("m_amount", 0)})
    return out


recipes, pieces, items = [], [], {}
for key, (kind, tree, cab, externals) in behaviours.items():
    if kind == "itemdrop":
        owner = component_owner(key)
        shared = tree.get("m_itemData", {}).get("m_shared", {})
        if owner:
            items[owner] = {"token": shared.get("m_name"), "type": shared.get("m_itemType")}
    elif kind == "recipe":
        item_ref = resolve(tree.get("m_item", {}), cab, externals)
        station_ref = resolve(tree.get("m_craftingStation", {}), cab, externals)
        recipes.append({
            "recipe": tree.get("m_Name"),
            "item": component_owner(item_ref) if item_ref else None,
            "amount": tree.get("m_amount"),
            "enabled": tree.get("m_enabled", 1),
            "station": component_owner(station_ref) if station_ref else None,
            "station_level": tree.get("m_minStationLevel"),
            "ingredients": ingredients(tree, cab, externals),
        })
    elif kind == "piece":
        station_ref = resolve(tree.get("m_craftingStation", {}), cab, externals)
        pieces.append({
            "piece": component_owner(key),
            "token": tree.get("m_name"),
            "category": tree.get("m_category"),
            "enabled": tree.get("m_enabled", 1),
            "station": component_owner(station_ref) if station_ref else None,
            "ingredients": ingredients(tree, cab, externals),
        })

json.dump({"recipes": recipes, "pieces": pieces, "items": items}, open(out_path, "w"), indent=1)
unresolved = sum(1 for r in recipes + pieces for i in r["ingredients"] if not i["item"])
print(f"{len(recipes)} recipes, {len(pieces)} pieces, {len(items)} items; {unresolved} unresolved ingredients")
