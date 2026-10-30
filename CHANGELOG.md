# Changelog

Versions are the APWorld's `world_version`; the mod is released alongside it.

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
