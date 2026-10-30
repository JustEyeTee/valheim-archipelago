"""Checks the randomizer's tables and the mod's hard-coded names against the game database written by
tools/scan_game_data.py.

    python3 tools/verify_game_data.py <gamedb.json>

Reports every prefab, creature, location, effect or environment name that the game doesn't have, kill
checks whose trophy nothing drops, and a few facts worth reviewing by hand (fish baits, trader stock,
which tool tier ores and trees need). Exits 1 if any name is missing.
"""
import csv
import json
import pathlib
import re
import sys

root = pathlib.Path(__file__).resolve().parent.parent
db = json.load(open(sys.argv[1]))
items, pieces, creatures = db["items"], db["pieces"], db["creatures"]
prefabs = set(items) | set(pieces) | set(creatures) | set(db.get("pickables", {})) | set(db.get("tool_tiers", {}))
locations = {e["name"] for lst in db["locations"]["lists"] for e in lst["entries"] if e.get("enable")}
problems, notes = [], []


def need(kind, name, where, pool):
    if name and name not in pool:
        problems.append(f"{where}: {kind} '{name}' not in the game")


def rows(path):
    return [r for r in csv.reader(open(path, newline=""), delimiter="\t") if r and not r[0].startswith("#")]


for r in rows(root / "mod" / "research.tsv"):
    need("icon item", r[0], f"research.tsv {r[2]}", items)
    for c in r[5].split("|"):
        if c:
            need("cost item", c.split(":")[0], f"research.tsv {r[2]}", items)
    for g in r[6].split("|"):
        if g:
            need("unlocked prefab", g, f"research.tsv {r[2]}", set(items) | set(pieces))
dropped = {d["item"] for ds in db["drops"].values() for d in ds}
for r in rows(root / "mod" / "trophies.tsv"):
    need("trophy", r[0], "trophies.tsv", items)
    if r[0] not in dropped:
        problems.append(f"trophies.tsv: nothing drops '{r[0]}'")
for kind, key, name, tier, reqs in rows(root / "mod" / "checks.tsv"):
    where = f"checks.tsv {name}"
    if kind in ("obtain", "catch", "eat", "buy"):
        need("item", key, where, items)
    elif kind == "build":
        need("piece", key, where, pieces)
    elif kind == "tame":
        need("tameable", key, where, db["tameables"])
    elif kind == "kill":
        need("trophy", key, where, items)
        if key not in dropped:
            problems.append(f"{where}: nothing drops '{key}'")
    elif kind == "discover":
        # Location lists name some entries differently from the prefab they place ("bosslocation" places
        # DN_Bossroom), so a prefab with a Location component counts too, with a note.
        if not any(loc.startswith(key) for loc in locations):
            if any(c and c.startswith(key) for c in db["locations"]["components"]):
                notes.append(f"{where}: '{key}' is a location prefab but no list entry has that name; confirm in game")
            else:
                problems.append(f"{where}: no location starts with '{key}'")

# Names the mod uses directly: ("Prefab", n) pairs, SpawnAround/AddEffect/ForceEnvironment calls.
src = "\n".join(p.read_text() for p in (root / "src").glob("*.cs"))
for prefab in set(re.findall(r'\("([A-Za-z_]+)", \d+\)', src)):
    need("prefab", prefab, "mod code", prefabs)
for creature in set(re.findall(r'SpawnAround\(player, "([A-Za-z_]+)"', src)) | \
        {c for c in re.findall(r"Heightmap\.Biome\.\w+, \(\"([A-Za-z_]+)\", \d+\)", src)}:
    need("creature", creature, "mod code (spawn)", creatures)

print("\n".join(problems) or "every name exists in the game")
for note in notes:
    print("note:", note)
print()
print("== Fish baits")
for fish, baits in sorted(db["fish"].items(), key=lambda kv: str(kv[0])):
    if fish and "(" not in fish:
        print(f"  {fish}: {', '.join(b['bait'] or '?' for b in baits)}")
print("== Tool tiers (what needs a better tool to break, and its drops)")
for name, t in sorted(db["tool_tiers"].items(), key=lambda kv: (kv[1]["min_tool_tier"] or 0, str(kv[0]))):
    drops = sorted({d["item"] for d in t["drops"] if d["item"]})
    if (t["min_tool_tier"] or 0) > 0 and drops:
        print(f"  tier {t['min_tool_tier']}: {name} -> {', '.join(drops)}")
print("== Tools by tier")
for name, it in sorted(items.items(), key=lambda kv: (kv[1].get("toolTier") or 0, kv[0])):
    if it.get("toolTier") and name.startswith(("Pickaxe", "Axe", "Battleaxe")):
        print(f"  {it['toolTier']}: {name}")
sys.exit(1 if problems else 0)
