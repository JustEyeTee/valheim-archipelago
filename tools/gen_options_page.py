"""Builds the options builder web page from the APWorld's own option definitions, so it can't drift out of
date: docs/options/index.html (for GitHub Pages) and, with --fragment, the page body alone.

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
        entry.update(kind="set", keys=sorted(cls.valid_keys), default=sorted(cls.default))
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


CHECK_OPTIONS = {"Biome: ": "biome_checks", "Obtain: ": "obtain_checks", "Explore: ": "exploration_checks",
                 "Kill: ": "kill_checks", "Discover: ": "discovery_checks", "Build: ": "build_checks",
                 "Eat: ": "eat_checks", "Catch: ": "fishing_checks", "Tame: ": "taming_checks", "Buy: ": "trader_checks"}


def locations(options):
    """Location names of a world built with these options (others default)."""
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
    return [loc.name for loc in mw.get_locations(1) if loc.address is not None]


def count_checks(goal):
    """Locations in a world built with default options and this goal."""
    return len(locations({"goal": goal}))


def breakdown(goal, deep_north=False):
    """How many checks each option adds for this goal: with every kind of check on, each location is
    counted under the option that adds it (skill checks by level); the rest are always there."""
    out = {"base": 0, "skills": {}}
    for name in locations({"goal": goal, "include_deep_north": deep_north, "kill_checks": 1, "skill_checks": 50}):
        option = next((o for prefix, o in CHECK_OPTIONS.items() if name.startswith(prefix)), None)
        if option:
            out[option] = out.get(option, 0) + 1
        elif name.startswith("Skill: "):
            level = name.rsplit(" ", 1)[1]
            out["skills"][level] = out["skills"].get(level, 0) + 1
        else:
            out["base"] += 1
    return out


goal_cls = hints["goal"]
eras = {"eikthyr": "Meadows", "the_elder": "Black Forest", "bonemass": "Swamp", "moder": "Mountains",
        "yagluth": "Plains", "the_queen": "Mistlands", "fader": "Ashlands", "kall_fimbulbringer": "Deep North"}
goals = [{"key": key, "boss": world.GOAL_BOSSES[value][0], "era": eras.get(key, ""), "checks": count_checks(key),
          "breakdown": breakdown(key), **({"deep_north": breakdown(key, True)} if key == "fader" else {})}
         for value, key in sorted(goal_cls.name_lookup.items())]

data = {
    "game": "Valheim",
    "world_version": manifest["world_version"],
    "minimum_ap_version": manifest["minimum_ap_version"],
    "groups": groups,
    "presets": options_presets,
    "goals": goals,
}

page = (root / "tools" / "options_page.html").read_text()
body = page.replace("/*DATA*/", json.dumps(data, separators=(",", ":")).replace("</", "<\\/"))
head, _, rest = body.partition("<!--BODY-->")
full = ("<!doctype html>\n<html lang=\"en\">\n<head>\n<meta charset=\"utf-8\">\n"
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1, viewport-fit=cover\">\n"
        + head + "</head>\n<body>\n" + rest + "</body>\n</html>\n")
out = root / "docs" / "options" / "index.html"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(full)
print(f"wrote {out}: {sum(len(g['options']) for g in groups)} options, goals {[(g['key'], g['checks']) for g in goals]}")
if "--fragment" in sys.argv:
    pathlib.Path(sys.argv[sys.argv.index("--fragment") + 1]).write_text(head + rest)
