# Valheim Archipelago Randomizer

[![CI](https://github.com/JustEyeTee/valheim-archipelago/actions/workflows/ci.yml/badge.svg)](https://github.com/JustEyeTee/valheim-archipelago/actions/workflows/ci.yml)

A [Valheim](https://www.valheimgame.com/) mod and APWorld for [Archipelago](https://archipelago.gg/), the
multi-game randomizer. Recipes and building pieces are locked behind researches you craft at a Research
Bench; each research, trophy and many other things you do in the game are checks that send items to you
or to other players in the multiworld.

Based on [Samupo's Valheim Archipelago Randomizer](https://github.com/Samupo/ValheimArchipelagoRandomizer),
updated for Valheim 1.0.21 ("Deep North") and current Archipelago, with many additions (see
[CHANGELOG.md](CHANGELOG.md)). Most of this project's code, tools and documentation were written by Claude,
an AI model made by Anthropic, at JustEyeTee's direction.

> **Status: beta.** Generation is tested for every goal; in-game testing is ongoing ([checklist](docs/PLAYTEST.md)).
> Back up your characters and worlds, and please report problems with your `BepInEx/LogOutput.log`.

## Requirements

- Valheim 1.0.21 (Deep North)
- [BepInExPack Valheim](https://thunderstore.io/c/valheim/p/denikson/BepInExPack_Valheim/) and
  [Jotunn](https://thunderstore.io/c/valheim/p/ValheimModding/Jotunn/) (2.30 or newer)
- Archipelago 0.6.8 or newer

## Installing

**APWorld.** Put `valheimapworld.apworld` in your Archipelago `custom_worlds` folder (or double-click it
to install with the Archipelago Launcher). Get it from the
[GitHub releases](https://github.com/JustEyeTee/valheim-archipelago/releases).

**Mod, with a mod manager (easiest).** In r2modman (or Thunderstore Mod Manager), find **ValheimArchipelago**
and install it; BepInExPack Valheim and Jotunn are installed with it.

**Mod, by hand.** With BepInExPack Valheim and Jotunn installed, copy the files from the release zip's
`BepInEx/plugins` folder into your `BepInEx/plugins` folder (directly, or in a subfolder of their own):
`ValheimRandomizer.dll`, `Archipelago.MultiClient.Net.dll`, `Newtonsoft.Json.dll`, `research.tsv` and
`trophies.tsv`.

The APWorld (`valheimapworld.apworld`) is in the GitHub release and in the Thunderstore package (in the mod's
folder, found with r2modman's Settings > Browse profile folder).

## Setting up a game

New to it? The **[player guide](https://justeyetee.github.io/valheim-archipelago/guide/)** covers setup, goals, every
kind of check, the in-game keys and commands, and co-op.

1. Make your options file with the **[Options Builder](https://justeyetee.github.io/valheim-archipelago/options/)**
   (pick your options, then copy or download the YAML), or copy [docs/Valheim.yaml](docs/Valheim.yaml) and edit it.
   Put it in your Archipelago `Players` folder.
2. Generate and host the multiworld as usual.
3. Start Valheim. In the **Archipelago** window on the main menu, enter the host, port, slot name and
   password, click **Connect**, then start a **new world** (and preferably a new character).

## Playing

- Build the **Research Bench** (Hammer > Randomizer) and craft researches there. Recipes and pieces stay
  locked until you receive the research item for them.
- Build an **Archipelago Chest** (Hammer > Randomizer, 10 Wood). Resource bundles, tools and boss drops
  sent to you are delivered into it.
- You win by picking up the trophy of your goal boss (for Kall Fimbulbringer, who has no trophy, his
  Sacrificial Blood), or by doing the goal conditions you chose (`/ap goal` shows your progress).

**Chat commands** (type them in the in-game chat):

| Command | |
|---|---|
| `/ap status` | Connection, Death Link and Trap Link settings |
| `/ap goal` | Your goal and how far along each condition is |
| `/ap logic`, `/ap logic <kind>` | The checks you can do now (in logic); **F8** shows them in a panel, **F9** opens the full list (mouse free, with a Hint button per check) and a Hints tab (your hints, found or not) |
| `/ap clear` | Removes bats around you (from a Bat Swarm Trap) |
| `/ap give [n] <item>`, `/ap items [search]` | Testing: get any item through the server's item cheat (rooms you host; see [docs/TESTING.md](docs/TESTING.md)) |
| `/ap shop`, `/ap shop hint [kind]` | Haldor's hint shop: by a trader, pay Coins to reveal one of your checks in logic as a hint |
| `/ap checks` | Checks done, and what's left by category |
| `/ap missing <category>` | Lists what's left, e.g. `/ap missing obtain` |
| `/ap hint <item>` | Asks the server for a hint |
| `/ap say <text>` | Archipelago chat |
| `/ap energy`, `/ap deposit <coins>`, `/ap withdraw <coins>` | Energy Link (1 Coin = 1 MJ) |
| `/ap deathlink on\|off` | Turns Death Link on or off for this session |

Items you send and receive, hints and other players' chat are shown on screen and in chat (turn off with
`ShowItemFeed` and `ShowChat` in the mod's config).

### Co-op

Each world has a co-op mode: the first player connected in a new world is asked to pick one when the world loads:

- **Shared slot** (the default): **one** player connects; everyone else just joins that world, with the mod
  installed and without connecting. Their researches, pickups, kills and other checks are sent by the
  connected player. Traps, boss items and Death Link reach only the connected player.
- **A slot each**: every player connects to their own slot. Each has their own researches, checks, goal and
  Archipelago Chest in the same world. Pass boss trophies around so everyone picks them up.

`/ap status` shows the world's mode.

## Options

Every option is described in [docs/Valheim.yaml](docs/Valheim.yaml). In short:

| Option | Default | |
|---|---|---|
| `goal` | `kall_fimbulbringer` | Eikthyr, The Elder, Bonemass, Moder, Yagluth, The Queen, Fader or Kall Fimbulbringer (the full game, through the Deep North). Checks and items past the goal are left out. |
| `goal_conditions` | Goal Boss | What you have to do to win, any combination (all of them): Goal Boss, All Bosses, Relic Hunt, Trophy Hunt, Researcher, Explorer, Skill Master, Great Hall, Hildir's Quests. Counted within the goal's era; a condition with nothing to do in it is dropped. |
| `relic_hunt_total`, `relic_hunt_percent` | 20, 75 | Relic Hunt: Forsaken Relics placed, and the share you need. |
| `trophy_hunt_percent`, `researcher_percent` | 50, 75 | Share of the era's trophies or researches you need. |
| `explorer_percent` | 5 | Share of the world map to uncover (lowered to the most the era allows). |
| `skill_master_count`, `skill_master_level` | 5, 50 | How many skills, to what level. |
| `great_hall_comfort` | 10 | Great Hall: the comfort level to reach (lowered to the most the era allows). |
| `research_cost_percent` | 100 | Research costs, 1-200%; the Research Bench and the Archipelago Chest scale with it. |
| `combat_logic` | normal | Logic expects armor and a weapon from the era before each new biome and boss fight (`strict` adds a bow or crossbow; `off` turns it off). |
| `biome_checks`, `obtain_checks`, `discovery_checks`, `build_checks`, `eat_checks`, `fishing_checks`, `taming_checks`, `trader_checks`, `lore_checks`, `farming_checks`, `brewing_checks`, `dungeon_checks` | on | Extra kinds of checks (lore: rune stones and Vegvisirs; farming: planting crops and trees; brewing: tapping each mead; dungeons: opening each kind of dungeon's treasure chest). |
| `exploration_checks`, `exploration_check_spacing` | 6, one_percent | Checks for exploring up to this % of the map (0-20), every half, one or two percent. |
| `raid_checks` | off | Checks for surviving each repeating raid (random, so they never hold progression items). |
| `comfort_checks` | 14 | Checks for each comfort level you reach, up to this level (0 turns them off); capped at what your era allows. |
| `kill_checks` | off | First kill of each creature. |
| `skill_checks`, `skill_check_spacing` | 20, every_10 | Checks for raising skills up to this level (0-100), every 10, 20 or 25 levels; each skill starts once you can train it. |
| `progressive_items` | off | Tiered researches come as progressive items (Progressive Axes, Progressive Bows...): each copy unlocks the next tier. |
| `boss_altar_keys` | off | Boss altars stay sealed until you receive each boss's Altar Key from the multiworld. |
| `map_items`, `map_fragments` | on, 5 | Maps to each boss of your era (they pin its altar) and Map Fragments (they uncover part of the map). |
| `hint_shop_price` | 100 | Coins per hint in the hint shop (0 closes it). |
| `boss_items` | on | The drops of the bosses before your goal are items (Hard Antler, Swamp Key, Wishbone...). |
| `gear_items` | on | Tools from your goal's era. |
| `starter_kit` | on | Start with a Club, Stone Axe and Torch. |
| `trap_percentage`, `boost_percentage`, `excluded_traps` | 20, 20, none | Traps and boosts among the extra items; 21 traps. |
| `death_link`, `death_link_mode`, `death_link_amnesty` | off, kill, 0 | Death Link; your deaths can be forgiven, and others' can wound you or set off a trap instead. |
| `trap_link` | off | Share traps with other Trap Link games. |

Each boss's drops gate the next part of the game in logic (copper needs Eikthyr's antler, iron The Elder's
Swamp Key, silver Bonemass's Wishbone, and so on). With `boss_items`, receiving the drop works too.
Default check counts: Eikthyr 114, The Elder 227, Bonemass 284, Moder 327, Yagluth 400, The Queen 490,
Fader 566, Kall Fimbulbringer 611.

## Trackers

- **Universal Tracker** works without extra setup.
- **PopTracker**: put the `ValheimArchipelagoPopTracker` zip in PopTracker's `packs` folder and connect
  it to the room; checks your seed doesn't have are hidden.

## Help and documentation

- [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md): common problems and how to read the log.
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md): how the mod and the APWorld work, for maintainers.
- Bugs and requests: [GitHub issues](https://github.com/JustEyeTee/valheim-archipelago/issues).

## Building from source

Needs the .NET 8 SDK and Python 3. Copy the game's `valheim_Data/Managed` assemblies to
`../valheim-archipelago-refs/game`, BepInEx core to `../valheim-archipelago-refs/bepinex/BepInExPack_Valheim/BepInEx/core`
and `Jotunn.dll` to `../valheim-archipelago-refs/jotunn` (or set `ValheimRefs`), then run `./build.sh`
(`FAST_TEST=1 ./build.sh` makes every research cost 1). The zips land in `dist/`.

Data files and their generators:

- `mod/research.tsv`, `mod/trophies.tsv`, `mod/checks.tsv`: the researches, trophies and extra checks.
- `tools/gen_apworld_data.py` writes the APWorld's `research_data.py` and `check_data.py` from them.
- `tools/gen_boss_gates.py <game data json>` writes `boss_data.py` from the game's recipes
  (`tools/extract_game_data.py` makes the json from a Valheim install, with UnityPy).
- `tools/gen_poptracker.py <Archipelago folder>` writes the PopTracker pack.
- `tools/test_generate.sh <goal> <seeds>` generates seeds and checks they can be beaten;
  `tools/net_test.sh` tests the mod's network code against a live Archipelago server;
  `tools/options_page_test.sh` checks the Options Builder's check and item counts against real generation.

## License

[CC0 1.0](LICENSE): public domain. The original mod is CC0 too, by its author's permission. The release
zip includes Archipelago.MultiClient.Net and Newtonsoft.Json under the MIT license (see
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)). Valheim is a trademark of Iron Gate AB; this project
is not affiliated with Iron Gate or Coffee Stain.
