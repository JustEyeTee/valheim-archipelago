# Changelog

Versions are the APWorld's `world_version`; the mod is released alongside it.

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
