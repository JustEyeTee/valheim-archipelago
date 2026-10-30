# Changelog

Versions are the APWorld's `world_version`; the mod is released alongside it.

## 0.13.0

- **Progressive items** (`progressive_items`, off by default): tiered researches come as progressive items
  (Progressive Axes, Progressive Bows, Progressive Forge Upgrade... 32 families); each copy unlocks the next
  tier in the seed. Logic counts copies; the PopTracker pack lights up each tier as copies arrive.
- **Logic panel**: press F8 in game (config `LogicPanelKey`) for the checks you can do now, by kind;
  `/ap logic` and `/ap logic <kind>` in chat. It follows the APWorld's rules (`mod/logic.tsv`, written by
  `tools/gen_mod_logic.py`): checked against generation on random item sets, it only differs on a few
  comfort levels, where it waits a little longer.
- Fixed: after loading a second world in the same game session, received researches weren't unlocked in it.

## 0.12.0

- **Comfort checks** (`comfort_checks`, on by default): a check for each comfort level you reach, up to 14.
  Logic adds up the best comfort piece of each kind (fire, bed, chair, table, banner, rug, bathtub) among
  the pieces you can build with the researches you've received, under a roof, the way the game does; levels
  past what your goal's era allows are left out (5 in an Eikthyr or The Elder game, 10 by Bonemass).
- **Great Hall** goal condition: reach comfort `great_hall_comfort` (lowered to your era's most).
- Comfort data comes from the game files (`tools/scan_game_data.py` records each piece's comfort;
  `tools/gen_comfort_data.py` builds the table, leaving out pieces you can't build: copies placed in world
  locations, camp decoration and seasonal pieces). Pieces needing nails, chains, jute or Frostwood aren't
  counted yet, so logic expects a little less comfort than you can reach.

## 0.11.0

- **Goal conditions** (`goal_conditions`): pick any combination of Goal Boss (the default), All Bosses, Relic
  Hunt, Trophy Hunt, Researcher, Explorer, Skill Master and Hildir's Quests; you win once all are done. The
  `goal` boss still sets the era, and Trophy Hunt, Researcher, Skill Master, Explorer and Hildir's Quests
  count only what's possible in it (a condition with nothing to do is dropped, Explorer is lowered to the
  era's most). Settings: `relic_hunt_total`, `relic_hunt_percent`, `trophy_hunt_percent`,
  `researcher_percent`, `explorer_percent`, `skill_master_count`, `skill_master_level`.
- Relic Hunt places Forsaken Relics in the multiworld in place of filler.
- `/ap goal` in chat shows your progress; the game shows each step and each condition done.
- Presets "Relic hunt to Moder" and "Trophy and Hildir hunt to Yagluth".
- Options Builder: each goal condition says what it means for the chosen goal (e.g. "21 of 42 trophies"),
  and is greyed out when there's nothing to do in that era. A live summary shows your game's checks and items
  by kind (researches, trophies, boss drops, tools, relics, traps, boosts, bundles), checked against real
  generation by `tools/options_page_test.sh`.

## 0.10.0

- Skill checks go to level 100 (`skill_checks`), every 10, 20 or 25 levels (`skill_check_spacing`). A goal no
  longer caps them: each skill's checks start once you can train it (Pickaxes after Eikthyr's antler,
  Farming with the Cultivator, Riding in the Plains, magic in the Mistlands), at any level.
- Exploration checks up to 20% of the map (`exploration_checks`), every half, one or two percent
  (`exploration_check_spacing`); larger percentages come later in logic.
- Skill levels above 30 and exploration past 6% never hold progression items, so no seed makes you grind
  for a key item.
- Removed `include_deep_north` (the goal decides: Kall includes the Deep North, Fader doesn't) and the
  "Classic" preset; "Full game with every check" goes to skills 100 and exploration 20%.
- Options Builder: counts for the new options (checked against generation), singular "check".

## 0.9.1

- **Kall Fimbulbringer is now the default goal**: the full game, through the Deep North. Fader ends the game
  after the Ashlands; presets "Full game", "Full game with every check" and "Classic (ends at Fader)".
- The Options Builder shows live check counts per option for your goal, and says which version is the game's
  and which the randomizer's.

## 0.9.0

- `combat_logic` (normal by default): entering the Swamp, Mountains, Plains, Mistlands, Ashlands and Deep
  North, and fighting each boss, need armor and a weapon from the era before; `strict` also needs a bow or
  crossbow. The idea comes from xyzzy44's version of the randomizer. The PopTracker pack follows the
  seed's setting.

## 0.8.1

- No more "Randomized?" box. A game is randomized while you're connected, or in a world an Archipelago
  player has connected in, so co-op partners just join the world, and offline play keeps working. A world
  never connected runs the research system on its own (the original vanilla mode).
- Research tooltips list what they unlock (and say that in an Archipelago game it unlocks when you receive
  the research), without the stray trailing comma.
- Architecture guide diagrams are now proper flowcharts and sequence diagrams.

## 0.8.0

- New goal: **Kall Fimbulbringer**, the Deep North boss (win by picking up his Sacrificial Blood); it
  includes the Deep North and every boss before him.
- New checks: Obtain Malicious Blood and Sacrificial Blood, Discover The First Prison (Kall's arena) and
  the Bog Witch's Camp, and buying 8 items from the Bog Witch.
- A later boss's goal location is never in an earlier goal's game (Fader with the Deep North doesn't ask
  you to beat Kall).
- `tools/scan_game_data.py` reads every game file into one database; `tools/verify_game_data.py` checks
  every name the randomizer uses against it.
- Docs: architecture and troubleshooting guides.

## 0.7.2

- Installs through a mod manager: the mod finds its data files in its own folder. Thunderstore package.
- Fish use the bait the game actually requires (Pike: plain bait; Giant Herring: Swamp bait).
- Ocean checks that need sailing (Serpent, Tuna, Coral Cod, Serpent Scale) need the Karve.
- No check is placed before its materials (new `tools/audit_tiers.py`): Karve, Portal, Forge, Charcoal
  Kiln, Eitr Refinery and Black Forge builds, and several obtain checks moved to their right tiers.

## 0.7.1

- Passes Archipelago's own test suites (run with `tools/ap_tests.sh`).
- Fixed: item links crashed generation.
- The APWorld's manifest follows the current spec (no container fields in the source).
- Game info and setup pages for the Archipelago website, option groups, presets, and item and location
  name groups (hint or item-link "Boss Drops", "Traps", "Tier 4"...).

## 0.7.0

- Boss drops as items (`boss_items`): Hard Antler, Swamp Key, Wishbone, 3 Dragon Tears, Torn Spirit and
  Majestic Carapace for the bosses before your goal; logic accepts the kill or the drop (Haldor's
  boss-unlocked stock still needs the kill).
- Tools from your goal's era (`gear_items`), era material bundles, and a `starter_kit`.
- In-game item feed (sent, received, hints, chat) and `/ap checks`, `/ap missing`, `/ap hint`, `/ap say`.
- Co-op on one slot: other players tick Randomized without connecting.
- Traps: Meteor Shower, Fake Item (21 in all).
- PopTracker pack, generated from the APWorld; autotracking hides checks your seed doesn't have.
- Fixed: Energy Link failed on a new multiworld and withdrawals never paid out.
- Tested on Archipelago 0.6.8 (0.6.4 still supported).

## 0.6.0

- Traps: Monster Pack (the current biome's creatures), Bat Swarm, Lightning Strike, Floor Is Lava,
  Blizzard, Tar, Launch, Rust; `excluded_traps` option.
- The Swamp and Mountains biome checks moved to their eras (The Elder and Bonemass).

## 0.5.0

- Boss gates: each boss's drops gate the next part of the game in logic, worked out from the game's
  recipes; a goal leaves out everything that needs the goal boss defeated.
- Bonemass's trophy moved to the iron age, so the Bonemass goal differs from The Elder's.
- Build, eat, fishing, taming and trader checks.
- Universal Tracker support.

## 0.4.0

- Skill checks (24 skills, levels 10-50) and discovery checks (dungeons, traders, boss altars).
- Traps: Skeleton Ambush, Poison, Frost, Raid, Butterfingers, Heavy Load; boosts (training and
  blessings); more bundles.
- Death Link (kill, wounded or trap mode, amnesty), Trap Link, Energy Link, `/ap` chat command.

## 0.3.0

- Obtain checks (93 materials), exploration checks (0.25%-6% of the map), kill checks.
- Fixed: the Tier 1 Troll trophy check could never be done (the Troll drops `TrophyFrostTroll`).
- Fixed: sent checks were never recognized (world keys split at spaces), so biome checks were re-sent
  every 2 seconds and offline checks could replace each other.

## 0.2.0

- Goal option (every boss), with checks and items past the goal left out.
- Research prerequisites in logic (the original logic left most of a seed unreachable).
- `research_cost_percent`; the Deep North tier (`include_deep_north`).
- Biome checks, resource bundles delivered to an Archipelago Chest, traps.
- Ported to Valheim 1.0.21 and Archipelago 0.6.4; fixed four prefab name typos, a missing research
  prerequisite and the Artisan Press gate; connecting now always turns on randomized mode; received items
  are applied on the game's main thread.

## 0.1.0

- Samupo's original release.
