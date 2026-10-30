"""Regenerates valheimapworld/boss_data.py: which bosses (or their drops) are needed before each research
can be crafted, each research's unlocks can be used, and each extra check can be done.

    python3 tools/gen_boss_gates.py <game database from tools/scan_game_data.py>

Each boss drops something later progress is made from: Eikthyr's Hard Antler (the first
pickaxe, so copper and tin), The Elder's Swamp Key (the Sunken Crypts: iron and the Withered
Bones that summon Bonemass), Bonemass's Wishbone (silver), Moder's Dragon Tears (Artisan
Table), Yagluth's Torn Spirit (Wisp Fountain), The Queen's Majestic Carapace (Artisan Press).
Starting from those, every item's needs follow the game's recipes, the stations they are
crafted at, and the materials those stations are built from.
"""
import csv
import json
import pathlib
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

BOSS_ORDER = ["Eikthyr", "The Elder", "Bonemass", "Moder", "Yagluth", "The Queen", "Fader", "Kall Fimbulbringer"]

# Raw materials that need a boss: its drop, or a tool made from its drop.
BASE = {
    "HardAntler": {"Eikthyr"},
    "CopperOre": {"Eikthyr"}, "TinOre": {"Eikthyr"}, "CopperScrap": {"Eikthyr"}, "Obsidian": {"Eikthyr"},
    "Chitin": {"Eikthyr"},
    "CryptKey": {"The Elder"}, "IronScrap": {"The Elder"}, "IronOre": {"The Elder"}, "WitheredBone": {"The Elder"},
    "Wishbone": {"Bonemass"}, "SilverOre": {"The Elder", "Bonemass"},
    "DragonTear": {"Moder"},
    "YagluthDrop": {"Yagluth"},
    "QueenDrop": {"The Queen"},
    "FaderDrop": {"Fader"},
    # Haldor sells these only after the boss is killed (the trader's required keys), so
    # receiving the boss's drop as an item doesn't help: "kill:" marks those.
    "YmirRemains": {"kill:The Elder"}, "Thunderstone": {"kill:The Elder"},
    # The Bog Witch's stock behind boss keys.
    "SpiceForests": {"kill:The Elder"}, "BlobVial": {"kill:The Elder"},
    # Hens come from Haldor's eggs, sold after Yagluth.
    "ChickenEgg": {"kill:Yagluth"}, "ChickenMeat": {"kill:Yagluth"}, "Hen": {"kill:Yagluth"},
}
# Smelted and refined materials: (input, station piece).
PROCESSED = {
    "Copper": ("CopperOre", "smelter"), "Tin": ("TinOre", "smelter"), "Iron": ("IronScrap", "smelter"),
    "Silver": ("SilverOre", "smelter"), "BlackMetal": ("BlackMetalScrap", "blastfurnace"),
    "FlametalNew": ("FlametalOreNew", "blastfurnace"), "Coal": ("Wood", "charcoal_kiln"),
    "Eitr": ("Softtissue", "eitrrefinery"), "Gold": ("GoldOre", "piece_FrostFoundry"),
}

recipes = {}
for r in data["recipes"]:
    if r["item"] and r["enabled"]:
        recipes.setdefault(r["item"], []).append(r)
pieces = {p["piece"]: p for p in data["pieces"] if p["piece"]}


def boss_of(token):
    return token[len("kill:"):] if token.startswith("kill:") else token


def rank(bosses):
    return (max((BOSS_ORDER.index(boss_of(b)) for b in bosses), default=-1), len(bosses))


memo = {}


def need(name, stack=()):
    """Bosses needed to get `name` (an item or piece). Unknown things need none."""
    if name in memo:
        return memo[name]
    if not name or name in stack:
        return set()
    stack = stack + (name,)
    options = []
    if name in PROCESSED:
        source, station = PROCESSED[name]
        options.append(need(source, stack) | need(station, stack))
    for r in recipes.get(name, []):
        options.append(set().union(*(need(i["item"], stack) for i in r["ingredients"]), need(r["station"], stack)))
    if name in pieces:
        p = pieces[name]
        options.append(set().union(*(need(i["item"], stack) for i in p["ingredients"]), need(p["station"], stack)))
    result = set(BASE.get(name, set()))
    if options:
        result |= min(options, key=rank)  # the easiest way to get it
    memo[name] = result
    return result


def ordered(bosses):
    return tuple(sorted(bosses, key=lambda b: (BOSS_ORDER.index(boss_of(b)), b)))


rows = [r for r in csv.reader(open(root / "mod" / "research.tsv", newline=""), delimiter="\t")
        if r and not r[0].startswith("#")]
cost, use = {}, {}
for r in rows:
    name = r[2]
    cost[name] = ordered(set().union(*(need(c.split(":")[0]) for c in r[5].split("|") if c)))
    unlocks = [g for g in r[6].split("|") if g]
    use[name] = ordered(min((need(g) for g in unlocks), key=rank)) if unlocks else ()

checks = {}
for r in csv.reader(open(root / "mod" / "checks.tsv", newline=""), delimiter="\t"):
    if r and not r[0].startswith("#") and r[0] in ("obtain", "eat", "catch", "buy", "tame"):
        checks[r[2]] = ordered(need(r[1]))

out = ["# Generated by tools/gen_boss_gates.py from the game's recipes. Do not edit by hand.",
       "",
       f"BOSS_ORDER = {tuple(BOSS_ORDER)!r}",
       "",
       "# Entries are boss names (its drop is needed: defeating it or receiving the drop as an",
       "# item both work) or \"kill:<boss>\" (only defeating it works).",
       "",
       "# Research -> bosses whose drops its research cost needs.",
       "RESEARCH_COST_BOSSES = {"]
out += [f"    {k!r}: {v!r}," for k, v in cost.items() if v]
out += ["}", "", "# Research item -> bosses needed to craft anything it unlocks.", "RESEARCH_USE_BOSSES = {"]
out += [f"    {k!r}: {v!r}," for k, v in use.items() if v]
out += ["}", "", "# Obtain, eat, catch, buy and tame checks -> bosses needed to get the item or creature.", "CHECK_BOSSES = {"]
out += [f"    {k!r}: {v!r}," for k, v in checks.items() if v]
out += ["}", ""]
(root / "valheimapworld" / "boss_data.py").write_text("\n".join(out))
print(f"{sum(1 for v in cost.values() if v)} research costs, {sum(1 for v in use.values() if v)} research unlocks, "
      f"{sum(1 for v in checks.values() if v)} checks need a boss")
