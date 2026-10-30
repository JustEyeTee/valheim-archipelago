# Troubleshooting

Most problems show up in **`BepInEx/LogOutput.log`** in your mod profile (r2modman: Settings > Browse
profile folder). The randomizer's lines contain `[AP]`, `Queue location`, `Unlock location` or
`Research`. When asking for help or [reporting a bug](https://github.com/JustEyeTee/valheim-archipelago/issues),
include that file, your YAML, and your Archipelago version.

In game, type **`/ap status`** in chat to see whether you're connected and your Death Link and Trap Link
settings.

## Installing

**There's no Archipelago window on the main menu.**
The mod isn't loading. Check that BepInExPack Valheim and Jotunn are installed in the same profile, that
you started the game through the mod manager ("Start modded"), and that `ValheimRandomizer.dll`,
`Archipelago.MultiClient.Net.dll` and `Newtonsoft.Json.dll` are in `BepInEx/plugins` (or a subfolder of
it). A common mistake is a `plugins` folder at the profile's top level: BepInEx only reads
`BepInEx/plugins`.

**The log says `Created starter research file` or `Trophy research file not found`.**
`research.tsv` and `trophies.tsv` must be next to `ValheimRandomizer.dll`. Without them only a placeholder
research exists. Copy them from the release zip and delete the placeholder `research.tsv` the mod wrote.

**Archipelago says Valheim isn't a known game, or my YAML fails to generate.**
Install `valheimapworld.apworld` (double-click it, or put it in `custom_worlds`) and restart the Launcher.
If the YAML's `requires` section names a newer APWorld than you have, update the APWorld.

## Connecting

**`Error: ...` in the Archipelago window.**
The text after "Error:" comes from the server:
- *InvalidSlot*: the slot name doesn't match a name in the multiworld.
- *InvalidGame*: that slot isn't a Valheim slot.
- *InvalidPassword*: the room has a password; enter it.
- A timeout or "connection refused": check the host and port (archipelago.gg rooms give a port like
  `38281` that changes when the room restarts) and that the room is running.

**I connected but nothing seems randomized.**
Connect **before** loading the world (the window is on the main menu), and use a **new world**: one played
before without Archipelago may already have researches unlocked.

## Researches and checks

**Where is the Research Bench?**
Hammer > **Randomizer** tab. Researches are crafted there; locked recipes and pieces appear once you
receive their research.

**A research says "(Completed)" but I still can't build it.**
"(Completed)" means you **did the check**: the research item you found went to whoever's world it
belongs to. You can build it once **you receive** that research, from any player's check.

**My checks aren't being sent.**
The log shows `Queue location <name>` when a check is done and `Unlock location <name>` when it's sent.
- Only `Queue location`: you're not connected; it's sent when you reconnect.
- `Location '<name>' is not in this seed`: that kind of check is turned off in your YAML, or it's past
  your goal. Nothing is wrong.
- `AP location lookup failed`: the mod and the APWorld are different versions; install both from the
  same release.

**I did my goal but didn't win.** Type `/ap goal` in chat: it lists each goal condition and how far along it
is. You have to be connected; progress made offline counts once you reconnect. Trophy Hunt and Researcher
count trophies and researches from your goal's era only; Skill Master counts a skill once it reaches the
level while the mod is running.

**I received an item but nothing happened.**
- Researches unlock their recipes at once (the log says `Research unlocked: ...`).
- Resource bundles, boss drops and tools go to your **Archipelago Chest** (Hammer > Randomizer, 10 Wood).
  Build one; deliveries wait, in order, until a chest is loaded near you and has room. You'll see a
  reminder every minute while deliveries are waiting.
- Traps and boosts happen at once (traps at least 10 seconds apart).

**A skill or obtain check went off immediately.**
They count what your character already has: an old character's skill levels or inventory. Use a new
character for a fresh game.

## Traps

**I don't want a certain trap.** Add it to `excluded_traps` in your YAML, or lower `trap_percentage`.

**The Raid Trap only spawned Greydwarfs.** Raids run on the world's host; other players, or anyone who isn't
ready for any raid in their biome, get an ambush instead.

**The log says `Status effect ... not found` or `Environment ... not found`.** A game update renamed
something; the trap is skipped. Please report it.

## Links

**Death Link isn't doing anything.** It's off unless `death_link: true` in your YAML; `/ap status` shows it.
`/ap deathlink on|off` changes it for the session. With `death_link_amnesty`, some of your deaths are
forgiven before one is sent.

**Energy Link.** `/ap energy` shows the team pool; `/ap deposit <coins>` and `/ap withdraw <coins>`
move Coins in and out (1 Coin = 1 MJ). Withdrawals need room in your inventory.

## Co-op

Only **one** player connects to the slot. Everyone else just joins that world with the mod installed and
does **not** connect: once the connected player has played in it, the world is marked as an Archipelago
world, and their checks are passed to the server by the connected player. Traps, boss items
and Death Link reach only the connected player. If two players connect to the same slot, items are applied
twice.

## Trackers

**Universal Tracker** works without setup. **PopTracker**: put the PopTracker zip in its `packs` folder,
choose the Valheim pack and connect it to the room. Checks your seed doesn't have are cleared when it
connects.
