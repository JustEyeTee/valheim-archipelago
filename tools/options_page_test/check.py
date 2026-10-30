"""Generates each case saved by page.py (with this repo's APWorld, through create_items) and compares its
checks and items by kind with what the Options Builder said. Run from an Archipelago checkout."""
import json, os, pathlib, sys, yaml
from argparse import Namespace
repo = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(repo))
sys.path.insert(0, os.getcwd())  # the Archipelago checkout
from BaseClasses import MultiWorld, CollectionState
from worlds.AutoWorld import AutoWorldRegister, call_all
AutoWorldRegister.world_types.pop("Valheim", None)
import valheimapworld as vw
PREFIXES = {"Biome: ": "Biomes", "Obtain: ": "Obtain", "Kill: ": "Kills", "Discover: ": "Discoveries", "Build: ": "Build",
            "Eat: ": "Eat", "Catch: ": "Fishing", "Tame: ": "Taming", "Buy: ": "Trader", "Skill: ": "Skills",
            "Explore: ": "Exploration", "Trophy: ": "Trophies"}
def item_kind(n):
    if n in vw.RESEARCH_PREREQS: return "Researches"
    if n.startswith("Trophy: "): return "Trophy boosts"
    if n in vw.BOSS_DROP_ITEMS.values(): return "Boss drops"
    if n in vw.GEAR_ITEMS: return "Tools"
    if n == vw.RELIC: return "Forsaken Relics"
    if n in vw.TRAP_ITEMS: return "Traps"
    if n in vw.BOOST_ITEMS: return "Boosts"
    if n in vw.FILLER_ITEMS: return "Resource bundles"
    return "?" + n
bad = 0
for case in json.load(open(sys.argv[1])):
    opts = yaml.safe_load(case["yaml"])["Valheim"]
    w = AutoWorldRegister.world_types["Valheim"]
    mw = MultiWorld(1); mw.game[1] = "Valheim"; mw.player_name = {1: "P"}; mw.set_seed(1)
    args = Namespace()
    for name, option in w.options_dataclass.type_hints.items():
        setattr(args, name, {1: option.from_any(opts.get(name, option.default))})
    mw.set_options(args); mw.state = CollectionState(mw)
    for step in ("generate_early", "create_regions", "create_items"):
        call_all(mw, step)
    checks, items = {}, {}
    for loc in mw.get_locations(1):
        if loc.address is None: continue
        k = next((v for p, v in PREFIXES.items() if loc.name.startswith(p)), "Researches")
        checks[k] = checks.get(k, 0) + 1
    for it in mw.itempool:
        k = item_kind(it.name); items[k] = items.get(k, 0) + 1
    ok = checks == case["summary"]["Checks"] and items == case["summary"]["Items"]
    bad += not ok
    print(f"{case['goal']:<20} {'MATCH' if ok else 'DIFFERENT'}  checks {sum(checks.values())}, items {sum(items.values())}: {items}")
    if not ok:
        print("   page checks", case["summary"]["Checks"], "\n   real checks", checks)
        print("   page items ", case["summary"]["Items"], "\n   real items ", items)
print("all match" if not bad else f"{bad} differ")
sys.exit(1 if bad else 0)
