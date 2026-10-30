"""Flags checks placed in an earlier tier than the materials they need.

    python3 tools/audit_tiers.py <game database from tools/scan_game_data.py>

A material's tier is the tier of its obtain check in mod/checks.tsv. For build, eat, obtain and buy
checks and every research's cost, the recipe tree (recipes, pieces, smelting) is followed down to
materials with an obtain check; if one of those comes from a later tier than the check, the check is
reachable in logic before the player can get what it needs. Boss drops are handled by
gen_boss_gates.py; this catches tool and biome needs (Finewood needs the Bronze Axe, and so on).
"""
import csv
import json
import pathlib
import re
import sys


def load_game_data(path):
    """Reads tools/scan_game_data.py's database (or the older extract_game_data.py json) as lists of
    recipes and pieces."""
    data = json.load(open(path))
    if isinstance(data["recipes"], dict):
        data["recipes"] = [dict(recipe=name, **r) for name, r in data["recipes"].items()]
        data["pieces"] = [dict(piece=name, token=p["name"], **p) for name, p in data["pieces"].items()]
    return data

root = pathlib.Path(__file__).resolve().parent.parent
data = load_game_data(sys.argv[1])
recipes = {}
for r in data["recipes"]:
    if r["item"] and r["enabled"]:
        recipes.setdefault(r["item"], []).append(r)
pieces = {p["piece"]: p for p in data["pieces"] if p["piece"]}
PROCESSED = {"Copper": "CopperOre", "Tin": "TinOre", "Iron": "IronScrap", "Silver": "SilverOre",
             "BlackMetal": "BlackMetalScrap", "FlametalNew": "FlametalOreNew", "Eitr": "Softtissue", "Gold": "GoldOre"}

rows = [r for r in csv.reader(open(root / "mod" / "checks.tsv", newline=""), delimiter="\t")
        if r and not r[0].startswith("#")]
material_tier = {r[1]: int(r[3]) for r in rows if r[0] == "obtain"}


def materials(name, stack=()):
    """Materials (with obtain checks) needed for `name`, by its easiest recipe."""
    if not name or name in stack:
        return set()
    if name in material_tier:
        return {name}
    stack += (name,)
    options = []
    if name in PROCESSED:
        options.append(materials(PROCESSED[name], stack))
    for r in recipes.get(name, []):
        options.append(set().union(*(materials(i["item"], stack) for i in r["ingredients"])))
    if name in pieces:
        options.append(set().union(*(materials(i["item"], stack) for i in pieces[name]["ingredients"])))
    return min(options, key=lambda s: max((material_tier[m] for m in s), default=0)) if options else set()


problems = []


def check(label, tier, mats):
    need = max((material_tier[m] for m in mats), default=0)
    if need > tier:
        problems.append(f"{label}: tier {tier}, but {', '.join(sorted(m for m in mats if material_tier[m] == need))} "
                        f"is tier {need}")


for r in rows:
    if r[0] in ("build", "eat", "obtain", "buy"):
        check(r[2], int(r[3]), materials(r[1]))
research_tier = {}
for line in open(root / "valheimapworld" / "Locations.py"):
    m = re.match(r"Research,([^,]+),loc:[^,]+,[^,]+,Tier(\d+)", line)
    if m:
        research_tier[m.group(1)] = int(m.group(2))
for r in csv.reader(open(root / "mod" / "research.tsv", newline=""), delimiter="\t"):
    if r and not r[0].startswith("#") and r[2] in research_tier and r[5]:
        check(f"Research {r[2]}", research_tier[r[2]],
              set().union(*(materials(c.split(":")[0]) for c in r[5].split("|") if c)))
print("\n".join(problems) or "no checks placed before their materials")
sys.exit(1 if problems else 0)
