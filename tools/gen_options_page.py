"""Builds the options builder web page from the APWorld's own option definitions, so it can't drift out of
date: docs/options/index.html (for GitHub Pages) and, with --fragment, the page body alone. Also builds the
player guide, docs/guide/index.html, whose check counts come from the same worlds, and the site's home page,
docs/index.html.

Needs Archipelago's Python (for the World and its options):
    ~/projects/archipelago-0.6.8/.venv/bin/python tools/gen_options_page.py ~/projects/archipelago-0.6.8 [--fragment out.html]

For each goal it also builds a world with default options and counts its checks.
"""
import inspect
import json
import pathlib
import sys
from argparse import Namespace

root = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(pathlib.Path(sys.argv[1]).resolve()))
sys.path.insert(0, str(root))

import Options  # noqa: E402
from BaseClasses import MultiWorld  # noqa: E402
from worlds.AutoWorld import AutoWorldRegister, call_all  # noqa: E402

# Archipelago loads an installed valheimapworld.apworld too; use this repo's copy instead.
AutoWorldRegister.world_types.pop("Valheim", None)
import valheimapworld as world  # noqa: E402
from valheimapworld.Options import ValheimOptions, option_groups, options_presets  # noqa: E402

manifest = json.load(open(root / "valheimapworld" / "archipelago.json"))
GAME_VERSION = "1.0.21"  # the Valheim version the mod is built and tested against
hints = ValheimOptions.type_hints
name_of = {cls: name for name, cls in hints.items()}


def describe(name, cls):
    doc = inspect.cleandoc(cls.__doc__ or "")
    entry = {"name": name, "display": getattr(cls, "display_name", name), "doc": doc}
    if issubclass(cls, Options.Toggle):
        entry.update(kind="toggle", default=bool(cls.default))
    elif issubclass(cls, Options.Choice):
        entry.update(kind="choice", choices=[cls.name_lookup[v] for v in sorted(cls.name_lookup)],
                     default=cls.name_lookup[cls.default])
    elif issubclass(cls, Options.Range):
        entry.update(kind="range", min=cls.range_start, max=cls.range_end, default=cls.default,
                     names=dict(getattr(cls, "special_range_names", {}) or {}))
    elif issubclass(cls, Options.OptionSet):
        # Goal conditions keep their own order (Goal Boss first); others are alphabetical.
        keys = list(cls.valid_keys) if name == "goal_conditions" else sorted(cls.valid_keys)
        entry.update(kind="set", keys=keys, default=sorted(cls.default))
    else:
        return None
    return entry


# Archipelago appends its own "Item & Location Options" group (local items, start inventory, plando...):
# item lists too long for a form, so the page leaves them for editing the YAML by hand.
groups = []
for group in option_groups:
    if group.name == "Item & Location Options":
        continue
    described = [describe(name_of[c], c) for c in group.options if c in name_of]
    groups.append({"name": group.name, "options": [d for d in described if d]})
groups.append({"name": "Archipelago", "options": [describe(n, hints[n]) for n in ("progression_balancing", "accessibility")]})


CHECK_OPTIONS = {"Biome: ": "biome_checks", "Obtain: ": "obtain_checks",
                 "Kill: ": "kill_checks", "Discover: ": "discovery_checks", "Build: ": "build_checks",
                 "Eat: ": "eat_checks", "Catch: ": "fishing_checks", "Tame: ": "taming_checks", "Buy: ": "trader_checks",
                 "Read: ": "lore_checks", "Vegvisir: ": "lore_checks", "Plant: ": "farming_checks", "Brew: ": "brewing_checks",
                 "Loot: ": "dungeon_checks", "Survive: ": "raid_checks"}


def build(options):
    """A world built with these options (others default), through create_regions."""
    w = AutoWorldRegister.world_types["Valheim"]
    mw = MultiWorld(1)
    mw.game[1] = "Valheim"
    mw.player_name = {1: "Count"}
    mw.set_seed(1)
    args = Namespace()
    for name, option in w.options_dataclass.type_hints.items():
        setattr(args, name, {1: option.from_any(options.get(name, option.default))})
    mw.set_options(args)
    for step in ("generate_early", "create_regions"):
        call_all(mw, step)
    return mw.worlds[1]


def locations(options):
    """Location names of a world built with these options (others default)."""
    built = build(options)
    return [loc.name for loc in built.multiworld.get_locations(1) if loc.address is not None]


def goal_info(goal):
    """What each goal condition has to work with in this goal's era: how many trophies, researches,
    skills, Hildir's quests and bosses, and the most of the map Explorer can ask for (0: none)."""
    built = build({"goal": goal, "explorer_percent": 20})
    targets = built.goal_targets
    explore = targets["Explorer"]
    sanity = build({"goal": goal, "item_sanity": 1}).goal_targets["Researcher"]
    return {"All Bosses": len(built.era_bosses), "Trophy Hunt": len(targets["Trophy Hunt"]),
            "Researcher": len(targets["Researcher"]), "Researcher (item-sanity)": len(sanity), "Skill Master": len(targets["Skill Master"]),
            "Hildir's Quests": len(targets["Hildir's Quests"]), "Great Hall": built.max_comfort if targets["Great Hall"] else 0,
            "Explorer": int(float(explore[0][len("Explore: "):].split("%")[0])) if explore else 0}


def count_checks(goal):
    """Locations in a world built with default options and this goal."""
    return len(locations({"goal": goal}))


def breakdown(goal):
    """How many checks each option adds for this goal: with every kind of check on, each location is
    counted under the option that adds it. Skills: how many can be trained in this goal (every level of a
    skill comes with it); exploration: the percentages available. The rest are always there."""
    out = {"base": 0, "research": 0, "trophy": 0, "skills_available": 0, "explore": [], "comfort": []}
    every_kind = {option: 1 for option in CHECK_OPTIONS.values()}  # some are off by default (kills, raids)
    for name in locations({**every_kind, "goal": goal, "skill_checks": 10, "skill_check_spacing": "every_10",
                           "exploration_checks": 20, "exploration_check_spacing": "half_percent",
                           "comfort_checks": hints["comfort_checks"].range_end}):
        option = next((o for prefix, o in CHECK_OPTIONS.items() if name.startswith(prefix)), None)
        if option:
            out[option] = out.get(option, 0) + 1
        elif name.startswith("Skill: "):
            out["skills_available"] += 1
        elif name.startswith("Explore: "):
            out["explore"].append(float(name[len("Explore: "):].split("%")[0]))
        elif name.startswith(world.COMFORT):
            out["comfort"].append(world.comfort_level(name))
        else:
            out["base"] += 1
            out["trophy" if name.startswith("Trophy: ") else "research"] += 1
    # item_sanity adds the building and material researches (the other kinds of check don't change).
    out["research_sanity"] = sum(1 for name in locations({"goal": goal, "item_sanity": 1})
                                 if name in world.RESEARCH_PREREQS)
    out["explore"].sort()
    out["comfort"].sort()
    out.update(pool_info(goal))
    return out


def pool_info(goal):
    """The items a goal's pool starts from, before filler (the same rules as ValheimWorld.create_items):
    the earlier bosses' drops (boss_items) and the era's tools (gear_items)."""
    built = build({"goal": goal})
    earlier = world.BOSS_ORDER[:world.BOSS_ORDER.index(built.goal_boss)]
    return {"boss_drops": sum(1 for boss in earlier if boss in world.BOSS_DROP_ITEMS),
            "gear": sum(1 for gear in world.GEAR_ITEMS if world.ITEM_TIERS[gear] <= built.scope_tier)}


goal_cls = hints["goal"]
eras = {"eikthyr": "Meadows", "the_elder": "Black Forest", "bonemass": "Swamp", "moder": "Mountains",
        "yagluth": "Plains", "the_queen": "Mistlands", "fader": "Ashlands", "kall_fimbulbringer": "Deep North"}
goals = [{"key": key, "boss": world.GOAL_BOSSES[value][0], "era": eras.get(key, ""), "checks": count_checks(key),
          "breakdown": breakdown(key), "conditions": goal_info(key)}
         for value, key in sorted(goal_cls.name_lookup.items())]

data = {
    "game": "Valheim",
    "world_version": manifest["world_version"],
    "game_version": GAME_VERSION,
    "minimum_ap_version": manifest["minimum_ap_version"],
    "groups": groups,
    "presets": options_presets,
    "goals": goals,
    "trap_count": len(world.TRAP_ITEMS),
}

def write_page(template, page_data, out):
    """A page from its template (head, then <!--BODY-->, then the body) with page_data as its /*DATA*/."""
    page = (root / "tools" / template).read_text()
    body = page.replace("/*DATA*/", json.dumps(page_data, separators=(",", ":")).replace("</", "<\\/"))
    head, _, rest = body.partition("<!--BODY-->")
    full = ("<!doctype html>\n<html lang=\"en\">\n<head>\n<meta charset=\"utf-8\">\n"
            "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1, viewport-fit=cover\">\n"
            + head + "</head>\n<body>\n" + rest + "</body>\n</html>\n")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(full)
    return head, rest


out = root / "docs" / "options" / "index.html"
head, rest = write_page("options_page.html", data, out)

# The guide's table of check kinds: what each is, its option, and how many the full game has with all of them on.
full_game = next(g["breakdown"] for g in goals if g["key"] == "kall_fimbulbringer")
KINDS = [("Research", "crafting each research at the Research Bench", "always", full_game["research"]),
         ("Trophy", "picking up each creature's and boss's trophy", "always", full_game["trophy"])]
KINDS += [(kind, what, option, full_game.get(option, 0)) for kind, what, option in [
    ("Biome", "entering each biome", "biome_checks"),
    ("Obtain", "getting each material for the first time", "obtain_checks"),
    ("Kill", "the first kill of each creature", "kill_checks"),
    ("Discover", "reaching each kind of place: dungeons, camps, altars", "discovery_checks"),
    ("Build", "placing each kind of station and piece", "build_checks"),
    ("Eat", "eating each food", "eat_checks"),
    ("Catch", "catching each fish", "fishing_checks"),
    ("Tame", "taming each creature", "taming_checks"),
    ("Buy", "buying from the traders", "trader_checks"),
    ("Read, Vegvisir", "reading each biome's rune stones and each boss's Vegvisir", "lore_checks"),
    ("Plant", "planting each crop and tree", "farming_checks"),
    ("Brew", "tapping each mead from a Fermenter", "brewing_checks"),
    ("Loot", "opening each kind of dungeon's treasure chest", "dungeon_checks"),
    ("Survive", "surviving each kind of repeating raid (random; no progression items)", "raid_checks")]]
KINDS += [("Skill", "each skill reaching 10, 20... 100", "skill_checks", full_game["skills_available"] * 10),
          ("Explore", "uncovering the map, up to 20%", "exploration_checks", len(full_game["explore"])),
          ("Comfort", "reaching each comfort level", "comfort_checks", len(full_game["comfort"]))]
guide = {k: data[k] for k in ("world_version", "game_version", "minimum_ap_version")}
guide["goals"] = [{"boss": g["boss"], "era": g["era"], "checks": g["checks"]} for g in goals]
guide["kinds"] = [{"kind": k, "what": w, "option": o if o == "always" else o, "count": n} for k, w, o, n in KINDS]
write_page("guide_page.html", guide, root / "docs" / "guide" / "index.html")
# The site's home page (https://justeyetee.github.io/valheim-archipelago/): links to the guide, the builder, downloads.
write_page("home_page.html", {k: data[k] for k in ("world_version", "game_version", "minimum_ap_version")},
           root / "docs" / "index.html")
print(f"wrote {out}: {sum(len(g['options']) for g in groups)} options, goals {[(g['key'], g['checks']) for g in goals]}")
if "--fragment" in sys.argv:
    pathlib.Path(sys.argv[sys.argv.index("--fragment") + 1]).write_text(head + rest)
