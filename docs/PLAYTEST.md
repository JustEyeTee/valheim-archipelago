# Playtest checklist

Everything since 0.11.0 passes the automated tests (generation, Archipelago's test suites, a live server), but
none of it has been played yet. This list covers it in two sessions, in the order you'd meet things. Tick what
works; for anything that doesn't, note what you did and send `BepInEx/LogOutput.log` (the `[AP]` lines matter).

## Setup

[TESTING.md](TESTING.md) explains how to host a test room and get any item with `/ap give` (traps, researches,
altar keys...), so you don't have to wait for the multiworld to send them. The test YAMLs in `tools/testing/` are
the two sessions below.

Or make your own with the [Options Builder](https://justeyetee.github.io/valheim-archipelago/options/):

- **Session 1 (Eikthyr):** goal `eikthyr`; goal conditions **Goal Boss + Trophy Hunt + Skill Master**
  (skill_master_count 2, skill_master_level 20); `boss_altar_keys` on; `progressive_items` on;
  `map_fragments` 5; `hint_shop_price` 10; `research_cost_percent` 25.
- **Session 2 (The Elder):** goal `the_elder`; goal conditions **Goal Boss + Hildir's Quests**; `raid_checks` on;
  `research_cost_percent` 25. If you can, play it in co-op with **A slot each** (two YAMLs, two players).

Generate both in one room (or one room each) and keep the server console open.

## Session 1: Eikthyr

- [ ] **Connect** from the main menu, load a **new** world. `/ap status` says connected and shows the co-op mode.
- [ ] **F8** shows the panel; **F9** opens the window: the mouse is free, you can't walk or turn while it's open,
      tabs switch kinds, it closes with F9 or Close, and the mouse is captured again afterwards.
- [ ] **F9 Hints tab**: after a hint (a check's Hint button, `!hint <item>` or the hint shop) it's listed as
      "to find" or "to send"; once its check is done it moves to "found" (shown with the toggle).
- [ ] Press **Esc** (pause menu): the Archipelago window shows there too. **Disconnect**, then **Connect** again.
      Do something while disconnected (pick up Flint): it's sent after reconnecting.
- [ ] **Research Bench** and **Archipelago Chest** (Hammer > Randomizer). Bundles and Map Fragments arrive
      (a fragment shows "it shows land ... km ... of here" and clears fog on the map).
- [ ] **Progressive items**: receiving a "Progressive ..." unlocks the next tier (check the recipe list).
- [ ] **Lore**: read the Meadows rune stone and Eikthyr's Vegvisir: "Read: Runestone (Meadows)" and "Vegvisir:
      Eikthyr" are sent (server console or `/ap checks`).
- [ ] **Comfort**: build a roof, a campfire and a bed: "Comfort: Level 2" to "4" are sent while you stand there.
- [ ] **Hint shop**: stand by Haldor (or any trader) with 10 Coins: `/ap shop hint` takes the Coins only after
      the hint appears. `/ap shop hint obtain` picks an obtain check.
- [ ] **Altar keys**: before you have Eikthyr's Altar Key, the altar refuses the Deer Trophies ("The altar is
      sealed..."). After receiving the key, it accepts them.
- [ ] **Goal**: `/ap goal` shows each condition's progress; each step shows on screen; when all are done the
      goal is sent ("Archipelago: goal complete!").

## Session 2: The Elder

- [ ] **Co-op, a slot each** (if two players): the first to connect is asked for the world's co-op mode when it loads: pick "A slot each".
      Each player has their own unlocks (one's research doesn't unlock the other's recipes); bundles go to the
      Archipelago Chest each one built. Pass The Elder's trophy around.
- [ ] **Farming**: plant carrot seeds with the Cultivator: "Plant: Carrot" is sent.
- [ ] **Brewing**: brew a Minor Healing Mead and tap it from the Fermenter: "Brew: Minor Healing Mead".
- [ ] **Dungeons**: open the chest in a Burial Chamber: "Loot: Burial Chamber".
- [ ] **Hildir**: return the Smouldering Tomb chest to Hildir: the goal condition counts it.
- [ ] **Raids**: once The Elder is dead and you've killed a troll, survive a troll raid near your base
      (be in it when "The shaking begins to fade"): "Survive: Troll Raid".
- [ ] **Map to Bonemass** (if you receive it): its altar is pinned on your map.

## Anything else

- Note anything that's locked when it shouldn't be (or the other way round), and the F8 panel's view of it.
- Note the frame rate with the F8 panel open in a big base (it recalculates every 2 seconds).
