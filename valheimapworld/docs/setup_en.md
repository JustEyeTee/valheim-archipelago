# Valheim Setup Guide

## Required software

- [Valheim](https://store.steampowered.com/app/892970/Valheim/) 1.0.21 or newer
- [r2modman](https://thunderstore.io/package/ebkr/r2modman/) (or another Thunderstore mod manager)
- [BepInExPack Valheim](https://thunderstore.io/c/valheim/p/denikson/BepInExPack_Valheim/) and
  [Jotunn](https://thunderstore.io/c/valheim/p/ValheimModding/Jotunn/), installed through the mod manager
- The Valheim Archipelago mod release zip, which also contains `valheimapworld.apworld`

## Installing the mod

1. In r2modman, select Valheim, create a profile, and install **ValheimArchipelago** (BepInExPack Valheim and
   Jotunn are installed with it).
2. Install `valheimapworld.apworld` into Archipelago (double-click it, or put it in `custom_worlds`). It is in
   the [GitHub releases](https://github.com/JustEyeTee/valheim-archipelago/releases), and in the mod's folder in
   your r2modman profile.

To install by hand instead, copy the release zip's `BepInEx/plugins` files into your `BepInEx/plugins` folder.

## Creating a config file

Use the [player options page](../player-options), or the template `Valheim.yaml` that comes with the release, and
put the file in your Archipelago `Players` folder.

## Connecting

1. Start Valheim through r2modman (Start modded).
2. In the Archipelago window on the main menu, enter the server address, port, your slot name and the password if
   there is one, then click Connect.
3. Start a new world (a new character is recommended too).

Type `/ap status` in the in-game chat to check the connection, and `/ap` for the list of commands. The
Archipelago window also shows in the pause menu (Esc), to connect, reconnect or disconnect mid-game.

## Playing together

Each world has a co-op mode, chosen in the connection window ("Co-op (new worlds)") by the first player who
connects in it. A world keeps that mode.

- **Shared slot**: one player connects, and the others just join that world with the mod installed, without
  connecting. Everyone's checks count for that one slot, and its researches unlock for everyone.
- **A slot each**: every player has their own slot in the room (their own YAML) and connects to it before loading
  the world. Each player has their own researches, checks, goal and Archipelago Chest (bundles go to a chest you
  built). A boss drops one trophy: pass it around so everyone picks it up.
