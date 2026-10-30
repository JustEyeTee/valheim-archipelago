"""Scans every Valheim asset file (including the SoftRef bundles) in one pass and writes a single
JSON database of what the randomizer needs to know about the game.

    python tools/scan_game_data.py <valheim_server_Data dir> <out.json>

Needs UnityPy (pip install UnityPy). Takes 20-30 minutes on the 1.9 GB of game data.

Sections, all keyed by prefab (GameObject) name where there is one:
  items        ItemDrop: display token, item type, food values, tool tier, skill
  recipes      crafted item, amount, station and level, ingredients
  pieces       building pieces: token, category, station, ingredients
  stations     crafting stations: token
  creatures    Character: token, boss, health, faction, defeat key, boss event
  drops        CharacterDrop: what each creature drops (with chances)
  locations    world locations from every location list (m_name is the real name; m_prefabName can
               be stale), with biome, quantity, group, prioritized; plus prefabs with a Location component
  spawns       creature spawners from spawn lists: biome, required keys, night only
  vegetation   trees, rocks and other world objects from vegetation lists: biome
  tool_tiers   things that need a tool tier to break (trees, ore deposits, rocks) and what they drop
  pickables    things picked by hand and the item they give
  offerings    boss altars: the boss, the offering item and how many
  traders      trader stock with prices and required keys
  tameables    creatures that can be tamed
  fish         each fish's baits
Asset references are (file, path id); refs to components resolve to the GameObject owning them.
"""
import json
import os
import sys
from collections import defaultdict

import UnityPy

data_dir, out_path = sys.argv[1], sys.argv[2]

game_objects = {}  # (cab, path_id) -> name
owners = {}        # MonoBehaviour (cab, path_id) -> (cab, path_id) of its GameObject
kept = []          # (kind, cab, path_id, externals, typetree) of interesting MonoBehaviours


def cab_of(assets_file):
    return os.path.basename(assets_file.name).lower()


def kinds_of(t):
    """Every kind of data in this component (ZoneSystem holds both locations and vegetation)."""
    found = []
    if isinstance(t.get("m_spawners"), list):
        found.append("spawnlist")
    if isinstance(t.get("m_vegetation"), list):
        found.append("vegetationlist")
    kind = kind_of(t)
    if kind and kind not in found:
        found.append(kind)
    return found


def kind_of(t):
    if "m_itemData" in t:
        return "itemdrop"
    if "m_item" in t and "m_resources" in t and "m_craftingStation" in t:
        return "recipe"
    if "m_resources" in t and "m_craftingStation" in t and "m_category" in t:
        return "piece"
    if "m_craftRequireRoof" in t:
        return "station"
    if "m_faction" in t and "m_health" in t:
        return "character"
    if "m_drops" in t and "m_spawnOffset" in t:
        return "chardrop"
    if isinstance(t.get("m_locations"), list) and t["m_locations"] and isinstance(t["m_locations"][0], dict) \
            and "m_biome" in t["m_locations"][0]:
        return "locationlist"
    if "m_exteriorRadius" in t and "m_noBuild" in t:
        return "location"
    if isinstance(t.get("m_spawners"), list):
        return "spawnlist"
    if isinstance(t.get("m_vegetation"), list):
        return "vegetationlist"
    if "m_bossItem" in t and "m_bossPrefab" in t:
        return "offering"
    if isinstance(t.get("m_items"), list) and t["m_items"] and isinstance(t["m_items"][0], dict) \
            and "m_price" in t["m_items"][0]:
        return "trader"
    if "m_fedDuration" in t and "m_tamingTime" in t:
        return "tameable"
    if "m_baits" in t:
        return "fish"
    if "m_minToolTier" in t:
        return "tooltier"
    if "m_itemPrefab" in t and "m_amount" in t:
        return "pickable"
    if "m_dropWhenDestroyed" in t:
        return "dropondestroyed"
    return None


files = [os.path.join(dp, n) for dp, _, names in os.walk(data_dir) for n in names]
for i, path in enumerate(files):
    try:
        env = UnityPy.load(path)
    except Exception:
        continue
    for o in env.objects:
        cab = cab_of(o.assets_file)
        if o.type.name == "GameObject":
            try:
                game_objects[(cab, o.path_id)] = o.peek_name()
            except Exception:
                pass
        elif o.type.name == "MonoBehaviour":
            try:
                t = o.read_typetree()
            except Exception:
                continue
            externals = [os.path.basename(e.path).lower() for e in o.assets_file.externals]
            go = t.get("m_GameObject", {})
            if go.get("m_PathID"):
                f = go.get("m_FileID", 0)
                target = cab if f == 0 else (externals[f - 1] if f - 1 < len(externals) else None)
                if target:
                    owners[(cab, o.path_id)] = (target, go["m_PathID"])
            for kind in kinds_of(t):
                kept.append((kind, cab, o.path_id, externals, t))
    print(f"{i + 1}/{len(files)} {os.path.basename(path)}: {len(kept)} kept", file=sys.stderr, flush=True)


def resolve(ptr, cab, externals):
    """A PPtr to a GameObject or a component, as the GameObject's name."""
    if not isinstance(ptr, dict) or not ptr.get("m_PathID"):
        return None
    f = ptr.get("m_FileID", 0)
    target = cab if f == 0 else (externals[f - 1] if f - 1 < len(externals) else None)
    key = (target, ptr["m_PathID"])
    if key in game_objects:
        return game_objects[key]
    return game_objects.get(owners.get(key))


def ingredients(t, cab, ex):
    return [{"item": resolve(r.get("m_resItem"), cab, ex), "amount": r.get("m_amount")} for r in t.get("m_resources", [])]


def drop_table(table, cab, ex):
    return [{"item": resolve(d.get("m_item"), cab, ex), "min": d.get("m_stackMin"), "max": d.get("m_stackMax"),
             "weight": d.get("m_weight")} for d in (table or {}).get("m_drops", [])]


db = defaultdict(dict)
db["locations"] = {"lists": [], "components": []}
for kind, cab, pid, ex, t in kept:
    owner = game_objects.get(owners.get((cab, pid)))
    if kind == "itemdrop":
        sh = t["m_itemData"].get("m_shared", {})
        db["items"][owner] = {k[2:]: sh.get(k) for k in ("m_name", "m_itemType", "m_food", "m_foodStamina", "m_foodEitr",
                                                         "m_maxStackSize", "m_toolTier", "m_skillType", "m_weight")}
    elif kind == "recipe":
        db["recipes"][t.get("m_Name")] = {
            "item": resolve(t.get("m_item"), cab, ex), "amount": t.get("m_amount"), "enabled": t.get("m_enabled", 1),
            "station": resolve(t.get("m_craftingStation"), cab, ex), "station_level": t.get("m_minStationLevel"),
            "ingredients": ingredients(t, cab, ex)}
    elif kind == "piece":
        db["pieces"][owner] = {"name": t.get("m_name"), "category": t.get("m_category"), "enabled": t.get("m_enabled", 1),
                               "station": resolve(t.get("m_craftingStation"), cab, ex), "ingredients": ingredients(t, cab, ex)}
    elif kind == "station":
        db["stations"][owner] = {"name": t.get("m_name")}
    elif kind == "character":
        db["creatures"][owner] = {k[2:]: t.get(k) for k in ("m_name", "m_boss", "m_health", "m_faction",
                                                            "m_defeatSetGlobalKey", "m_bossEvent", "m_tolerateWater")}
    elif kind == "chardrop":
        db["drops"][owner] = [{"item": resolve(d.get("m_prefab"), cab, ex), "min": d.get("m_amountMin"),
                               "max": d.get("m_amountMax"), "chance": d.get("m_chance"),
                               "one_per_player": d.get("m_onePerPlayer")} for d in t["m_drops"]]
    elif kind == "locationlist":
        db["locations"]["lists"].append({"list": owner, "entries": [
            {k[2:]: e.get(k) for k in ("m_name", "m_prefabName", "m_enable", "m_biome", "m_quantity", "m_group",
                                       "m_prioritized", "m_unique", "m_minDistance", "m_maxDistance")}
            for e in t["m_locations"]]})
    elif kind == "location":
        db["locations"]["components"].append(owner)
    elif kind == "spawnlist":
        db["spawns"].setdefault(owner, []).extend(
            {"prefab": resolve(s.get("m_prefab"), cab, ex), "name": s.get("m_name"), "enabled": s.get("m_enabled"),
             "biome": s.get("m_biome"), "required_global_key": s.get("m_requiredGlobalKey"),
             "required_environments": s.get("m_requiredEnvironments"), "night_only": s.get("m_spawnAtNight") and not
             s.get("m_spawnAtDay")} for s in t["m_spawners"])
    elif kind == "vegetationlist":
        db["vegetation"].setdefault(owner, []).extend(
            {"prefab": resolve(v.get("m_prefab"), cab, ex), "name": v.get("m_name"), "enabled": v.get("m_enable"),
             "biome": v.get("m_biome")} for v in t["m_vegetation"])
    elif kind == "offering":
        db["offerings"][owner] = {"name": t.get("m_name"), "boss": resolve(t.get("m_bossPrefab"), cab, ex),
                                  "item": resolve(t.get("m_bossItem"), cab, ex), "count": t.get("m_bossItems")}
    elif kind == "trader":
        db["traders"][owner] = [{"item": resolve(i.get("m_prefab"), cab, ex), "stack": i.get("m_stack"),
                                 "price": i.get("m_price"), "key": i.get("m_requiredGlobalKey")} for i in t["m_items"]]
    elif kind == "tameable":
        db["tameables"][owner] = {"fed_duration": t.get("m_fedDuration"), "taming_time": t.get("m_tamingTime")}
    elif kind == "fish":
        db["fish"][owner] = [{"bait": resolve(b.get("m_bait"), cab, ex), "chance": b.get("m_chance")} for b in t["m_baits"]]
    elif kind == "tooltier":
        drops = drop_table(t.get("m_dropItems"), cab, ex) or drop_table(t.get("m_dropWhenDestroyed"), cab, ex)
        db["tool_tiers"][owner] = {"min_tool_tier": t.get("m_minToolTier"), "drops": drops,
                                   "spawn_when_destroyed": resolve(t.get("m_spawnWhenDestroyed"), cab, ex)}
    elif kind == "pickable":
        db["pickables"][owner] = {"item": resolve(t.get("m_itemPrefab"), cab, ex), "amount": t.get("m_amount")}
    elif kind == "dropondestroyed":
        db["destroy_drops"][owner] = drop_table(t.get("m_dropWhenDestroyed"), cab, ex)

json.dump(db, open(out_path, "w"), indent=1, default=str)
print({k: len(v) for k, v in db.items()})
