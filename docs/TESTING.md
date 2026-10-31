# Testing with any item on demand

To test a feature you need the item that drives it: a trap, a research, an altar key, a map. In a room you host
yourself, Archipelago's server can hand you any item through its **item cheat**: the item comes from the server
and arrives the same way an item another player found would. So what you see is a valid test of the item, the
mod and the logic; the only difference is the item feed saying "Cheat console".

## 1. Host a test room

**On the VPS** (from the repository, with Archipelago 0.6.8 in `../archipelago-0.6.8`):

```
tools/test_room.sh                                   # tools/testing/solo-eikthyr.yaml, port 38281
tools/test_room.sh tools/testing/solo-elder.yaml     # The Elder's era (Hildir, farming, brewing, raids)
PORT=38282 PASSWORD=secret tools/test_room.sh        # another port, a password to join
```

It builds the APWorld, generates a seed from the YAML and hosts it, printing the address to connect to. The server
runs in that terminal: type its commands there (below), and `/exit` to stop it. Rooms are kept in
`~/valheim-test-rooms/`. `GENERATE_ONLY=1 tools/test_room.sh` only generates, to host the `.zip` somewhere else
(for example as a separate service user).

**On your own PC**: generate as usual (your YAML in Archipelago's `Players` folder, then Generate), then host the
`.zip` from the Archipelago Launcher (Host). Item cheats are on unless your `host.yaml` has
`disable_item_cheat: true`. Connect to `localhost` and port `38281`.

A room on archipelago.gg allows item cheats only if that was chosen when the room was made.

The test YAMLs in `tools/testing/` turn most features on and set researches to cost 1 of each ingredient
(`research_cost_percent: 1`), so you can get through Eikthyr's era quickly.

## 2. Get items in the game

| Command | Does |
|---|---|
| `/ap give <item>` | Asks the server for the item (any part of its name works when only one item matches) |
| `/ap give <count> <item>` | Several (up to 20), e.g. `/ap give 3 Progressive Axes` |
| `/ap items [search]` | Lists item names, e.g. `/ap items trap`, `/ap items altar` |

What to give to test each feature:

| Feature | Give | Look for |
|---|---|---|
| Traps | `Burning Trap`, `Floor Is Lava Trap`, `Raid Trap`... (`/ap items trap`) | the trap's effect, one every 10 s |
| Researches | a research's name, e.g. `Bows Tier 2`, `Leather Armor` (standard also `Smelter`, `Forge`; with `item_sanity`, also `Wooden Roofs`) | its recipes and pieces unlocked |
| Progressive items | `Progressive Axes` (several times) | each copy unlocks the next tier |
| Altar keys | `Eikthyr's Altar Key` | the altar takes offerings only after |
| Maps | `Map to Eikthyr`, `Map Fragment` | the altar pinned; fog cleared on the map |
| Relic Hunt | `Forsaken Relic` | `/ap goal` counts it |
| Bundles, tools, boss drops | `20 Wood`, `Bronze Pickaxe`, `Hard Antler` | delivered to your Archipelago Chest |
| Boosts | `Combat Training`, `Rested Blessing` | the boost |

## 3. Server commands (in the test room's terminal)

| Command | Does |
|---|---|
| `/send TestViking <item>` | Gives an item (the same as `/ap give`, from the host's side) |
| `/send_location TestViking <location>` | Marks a check done, as if you'd done it (for testing goals and the logic panel) |
| `/collect TestViking` | Marks every check done |
| `/exit` | Stops the server (the room is saved; run it again with the Launcher to continue) |

Checks themselves (reading a rune stone, planting, brewing, opening a dungeon chest...) are tested by doing them in
the game: the server's terminal shows each check as it arrives. [PLAYTEST.md](PLAYTEST.md) lists what to try.

## 4. A dedicated test server

To test on a dedicated server (and multiplayer), run Valheim's dedicated server with BepInEx, Jotunn and this
mod (the plugin folder's DLLs **and** its `research.tsv` and `trophies.tsv`). With `-public 1` it answers the
Steam query that joining by IP needs (`-public 0` doesn't); a `-password` keeps it private.

If the server's environment has `AP_ADMIN_QUEUE=<file>`, lines appended to that file run on the server:

| Line | Does |
|---|---|
| `spawn <player\|*> <prefab> [count]` | Drops items (or creatures) beside a player, e.g. `spawn * TrophyDeer 2` |
| `say <text>` | Shows a message to everyone |
| `players` | Logs who's online and where |

Players' games never set it, so it does nothing there.
