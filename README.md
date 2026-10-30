# Valheim Archipelago Randomizer

A [Valheim](https://www.valheimgame.com/) mod and APWorld for [Archipelago](https://archipelago.gg/), the
multi-game randomizer. Recipes and building pieces are locked behind researches you craft at a Research
Bench; each research, trophy and many other things you do in the game are checks that send items to you
or to other players in the multiworld.

Based on [Samupo's Valheim Archipelago Randomizer](https://github.com/Samupo/ValheimArchipelagoRandomizer),
updated for Valheim 1.0.21 ("Deep North") and current Archipelago, with many additions (see
[CHANGELOG.md](CHANGELOG.md)). Made with the help of an AI assistant (Claude).

> **Status: beta.** Generation is tested for every goal; in-game testing is ongoing. Back up your
> characters and worlds, and please report problems with your `BepInEx/LogOutput.log`.

## Requirements

- Valheim 1.0.21 (Deep North)
- [BepInExPack Valheim](https://thunderstore.io/c/valheim/p/denikson/BepInExPack_Valheim/) and
  [Jotunn](https://thunderstore.io/c/valheim/p/ValheimModding/Jotunn/) (2.30 or newer)
- Archipelago 0.6.4 or newer (tested on 0.6.4 and 0.6.8)

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

1. Copy [docs/Valheim.yaml](docs/Valheim.yaml) into your Archipelago `Players` folder, rename it, and set
   your `name` and options (see below).
2. Generate and host the multiworld as usual.
3. Start Valheim. In the **Archipelago** window on the main menu, enter the host, port, slot name and
   password, click **Connect**, then start a **new world** (and preferably a new character).

## Playing

- Build the **Research Bench** (Hammer > Randomizer) and craft researches there. Recipes and pieces stay
  locked until you receive the research item for them.
- Build an **Archipelago Chest** (Hammer > Randomizer, 10 Wood). Resource bundles, tools and boss drops
  sent to you are delivered into it.
- You win by picking up the trophy of your goal boss.

**Chat commands** (type them in the in-game chat):

| Command | |
|---|---|
| `/ap status` | Connection, Death Link and Trap Link settings |
| `/ap checks` | Checks done, and what's left by category |
| `/ap missing <category>` | Lists what's left, e.g. `/ap missing obtain` |
| `/ap hint <item>` | Asks the server for a hint |
| `/ap say <text>` | Archipelago chat |
| `/ap energy`, `/ap deposit <coins>`, `/ap withdraw <coins>` | Energy Link (1 Coin = 1 MJ) |
| `/ap deathlink on\|off` | Turns Death Link on or off for this session |

Items you send and receive, hints and other players' chat are shown on screen and in chat (turn off with
`ShowItemFeed` and `ShowChat` in the mod's config).

### Co-op

Several Vikings can share one slot: one player connects; everyone else ticks **Randomized** in the
Archipelago window and does **not** connect. Their researches, pickups, kills and other checks are sent
through the world by the connected player. Traps, boss items and Death Link reach only the connected player.

## Options

Every option is described in [docs/Valheim.yaml](docs/Valheim.yaml). In short:

| Option | Default | |
|---|---|---|
| `goal` | `fader` | Eikthyr, The Elder, Bonemass, Moder, Yagluth, The Queen or Fader. Checks and items past the goal are left out. |
| `include_deep_north` | off | Adds the Deep North tier (goal Fader only). |
| `research_cost_percent` | 100 | Research costs, 1-200%. |
| `biome_checks`, `obtain_checks`, `exploration_checks`, `discovery_checks`, `build_checks`, `eat_checks`, `fishing_checks`, `taming_checks`, `trader_checks` | on | Extra kinds of checks. |
| `kill_checks` | off | First kill of each creature. |
| `skill_checks` | 20 | Skills to level 10, 20, 30, 40 or 50 (0 = off). |
| `boss_items` | on | The drops of the bosses before your goal are items (Hard Antler, Swamp Key, Wishbone...). |
| `gear_items` | on | Tools from your goal's era. |
| `starter_kit` | on | Start with a Club, Stone Axe, Torch and Raspberries. |
| `trap_percentage`, `boost_percentage`, `excluded_traps` | 20, 20, none | Traps and boosts among the extra items; 21 traps. |
| `death_link`, `death_link_mode`, `death_link_amnesty` | off, kill, 0 | Death Link; your deaths can be forgiven, and others' can wound you or set off a trap instead. |
| `trap_link` | off | Share traps with other Trap Link games. |

Each boss's drops gate the next part of the game in logic (copper needs Eikthyr's antler, iron The Elder's
Swamp Key, silver Bonemass's Wishbone, and so on). With `boss_items`, receiving the drop works too.
Default check counts: Eikthyr 111, The Elder 223, Bonemass 274, Moder 318, Yagluth 391, The Queen 481,
Fader 557.

## Trackers

- **Universal Tracker** works without extra setup.
- **PopTracker**: put the `ValheimArchipelagoPopTracker` zip in PopTracker's `packs` folder and connect
  it to the room; checks your seed doesn't have are hidden.

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
  `tools/net_test.sh` tests the mod's network code against a live Archipelago server.

## License

[CC0 1.0](LICENSE): public domain. The original mod is CC0 too, by its author's permission. The release
zip includes Archipelago.MultiClient.Net and Newtonsoft.Json under the MIT license (see
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)). Valheim is a trademark of Iron Gate AB; this project
is not affiliated with Iron Gate or Coffee Stain.
