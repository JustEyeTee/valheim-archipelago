# Changelog

Versions are the APWorld's `world_version`; the mod is released alongside it.

## 0.21.1

From the first playtest:
- The Research Bench and the Archipelago Chest cost scales with `research_cost_percent` too (at 1%: 1 Wood and
  1 Stone, and 1 Wood).
- The Starter Kit has no Raspberries any more: they were a check, and the kit sent "Obtain: Raspberries" on arrival.
- F8 is simpler and sits below the minimap: how many checks you can do now, the best thing to get next, and how
  many of each kind. F9 hides skill, exploration and comfort checks unless you ask (they come as you play), sorts
  its tabs by size and drops the repeated "Obtain:" inside a tab.
- A Map Fragment pins the spot it uncovers on your map.
- Traps: the Lightning Strike no longer kills a new character outright (the bolt lands beside you; you take a
  third of your health); Bat Swarm is 2 bats plus one per boss defeated (6 killed you at spawn over and over);
  the Launch Trap throws you higher; creatures a trap summons leave after 3 minutes or when you die (marked on the
  creature, so this holds across reloads); `/ap clear` removes bats around you.
- A research you receive shows up in the build and craft menus straight away (the game only refreshed them when
  your inventory changed, so a workbench stayed hidden until you picked something up). Crafting a research says
  that it was sent and that the research itself unlocks when you receive it.
- The Meteor Shower Trap drops meteors anywhere (12-35 m from you, one every 4 seconds for a minute); before, only
  the sky changed, since the game drops its meteors in the Ashlands only.
- The F8 panel hides while the inventory, the menu, a store or the map is open.

## 0.21.0

- **Testing with any item**: `/ap give [count] <item>` asks the server for any item through its item cheat (on in
  rooms you host), so it arrives the normal way; `/ap items [search]` lists item names. `tools/test_room.sh` hosts
  a test room from `tools/testing/solo-eikthyr.yaml` or `solo-elder.yaml`; `docs/TESTING.md` explains it.
- The hint shop keeps a fixed price (the scaling option is gone).

## 0.20.0

- **All 19 meads** are brewing checks: the Bog Witch's stock counts as a source for their ingredients, with new
  buy checks for her Toadstool and Fragrant Bundle (sold once Moder is dead).
- **Oats and poteitr** are farming checks too (their seeds come from Deep North granaries; the game data scan now
  records chest loot). Vineberry is still left out: no source for its seeds is in the game files.
- **What to get next**: the F8 panel, the F9 window and `/ap logic` show the items, bosses or gear that would each
  put the most checks in logic ("Next: Bronze (12 checks), defeat The Elder (9 checks)...").
- **Website home page** (https://justeyetee.github.io/valheim-archipelago/), a bug report form for issues, a social
  preview image (`docs/social-preview.png`, from `tools/make_social.py`) and Dependabot for CI's actions.

## 0.19.0

- **Raid checks** (`raid_checks`, off by default): surviving each raid that keeps coming once it starts (trolls
  after The Elder; blobs, ghosts, skeletons, Surtlings and wolves after Bonemass), sent when it ends with you in
  it, alive. Raids are random, so these never hold progression items; the boss armies aren't included (each
  stops once the next boss is dead, so it could be missed). The game data scan now records raids.
- **Playtest checklist** (`docs/PLAYTEST.md`): two sessions that cover everything since 0.11.0.
- Fixed (from an independent review): after a dropped connection the mod kept "sending" checks into the dead
  connection and marked them sent. It now notices the connection closing, only sends while connected, and on
  each connect resends any check it marked sent that the server still lists as missing. Connecting no longer
  freezes the game while the server answers. A raid counts only if you were in it for 45 seconds before it ended.
- Fixed: the Options Builder greyed out Raid Checks for every goal (it counted with the default options).

## 0.18.0

- **Brewing checks** (`brewing_checks`, on): tapping each mead from a Fermenter (13 meads, from Minor Healing to
  Lingering Eitr), with the Mead ketill and the Fermenter researched and the ingredients in logic.
- **Farming** now covers trees (beech, birch, fir, pine, oak), kale, ashvine and planting carrots, turnips and
  onions for seeds; new obtain checks for their seeds and for feathers, sap, scale hide, royal jelly, blood clot
  and smoke puff.
- **Connect from the pause menu**: the Archipelago window also shows in game while the menu is open, to connect,
  reconnect or disconnect mid-game. Disconnect now works (checks done meanwhile are sent on the next connect).
- New check rows always go at the end of `checks.tsv`, so existing location ids never move.
- **Player guide** (https://justeyetee.github.io/valheim-archipelago/guide/): setup, goals, every kind of check
  (with counts from the APWorld), items, the in-game keys and commands, co-op and trackers; built with the
  Options Builder by `tools/gen_options_page.py`.

## 0.17.0

- **Boss altar keys** (`boss_altar_keys`, off by default): every boss altar is sealed until you receive that
  boss's Altar Key from the multiworld (Eikthyr's Altar Key, The Elder's Altar Key...); the altar takes no
  offering until then. Logic needs the key for each boss fight, and Kall Fimbulbringer's for his prison's gate.
  The keys are in the PopTracker pack, the logic panel and the Options Builder's summary.
- The hint shop takes your Coins only once the server has made the hint (nothing is paid if the connection
  is lost). The logic window closes with its key or Close (Esc no longer also opens the menu).

## 0.16.0

- **Lore checks** (`lore_checks`, on): reading each biome's lore rune stones (11) and each boss's Vegvisir (8).
- **Farming checks** (`farming_checks`, on): planting carrot, turnip, onion, barley, flax, magecap and jotun puffs
  with the Cultivator. (Trees and the Deep North crops need obtain checks for their seeds first.)
- **Dungeon checks** (`dungeon_checks`, on): opening a treasure chest in a Burial Chamber, Troll Cave, Sunken
  Crypt, Frost Cave, Infested Mine and Charred Fortress (each kind of chest is only in that dungeon).
- **Map items** (`map_items`, on; `map_fragments`, 5): a Map to each boss of your era pins its altar, as its
  Vegvisir does; Map Fragments uncover a patch of the map near you (which counts for exploration).
- All era-limited like the other checks; the game data scan now records Vegvisirs, rune stones and plants
  (`tools/gen_world_checks.py` writes the rows).

## 0.15.0

- **Haldor's hint shop** (`hint_shop_price`, 100 Coins by default, 0 closes it): by a trader (Haldor, Hildir
  or the Bog Witch), `/ap shop hint [kind]` pays Coins to reveal one of your checks in logic as a hint for
  everyone. It costs no hint points.
- **Logic window** (F9, config `LogicWindowKey`): every check in logic now, by kind, with the mouse free to
  scroll, and a Hint button per check (`!hint_location`, which costs hint points). F8 still shows the panel.
- **CI**: every push runs Archipelago's test suites, test generations and the network test on GitHub; a
  `v*` tag drafts a release with the APWorld and the PopTracker pack (the mod zip is built locally).
- **Archipelago 0.6.8 or newer** is now required.

## 0.14.0

- **Co-op modes, chosen per world**: the first player to connect in a world picks **shared slot** (one player
  connects, everyone's checks count; the old behavior, and what existing worlds stay) or **a slot each**
  (every player connects to their own slot and has their own researches, checks, goal and Archipelago Chest
  in the same world). Set in the connection window or `CoopMode` in the config; `/ap status` shows it.

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
