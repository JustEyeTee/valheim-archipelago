# Valheim Setup Guide

## Required software

- [Valheim](https://store.steampowered.com/app/892970/Valheim/) 1.0.21 or newer
- [r2modman](https://thunderstore.io/package/ebkr/r2modman/) (or another Thunderstore mod manager)
- [BepInExPack Valheim](https://thunderstore.io/c/valheim/p/denikson/BepInExPack_Valheim/) and
  [Jotunn](https://thunderstore.io/c/valheim/p/ValheimModding/Jotunn/), installed through the mod manager
- The Valheim Archipelago mod release zip, which also contains `valheimapworld.apworld`

## Installing the mod

1. In r2modman, select Valheim, create a profile and install BepInExPack Valheim and Jotunn.
2. Open the profile folder (Settings > Browse profile folder).
3. Copy the files from the release zip's `BepInEx/plugins` folder into the profile's `BepInEx/plugins` folder.
   They must be directly in that folder, not in a subfolder.
4. Install `valheimapworld.apworld` into Archipelago (double-click it, or put it in `custom_worlds`).

## Creating a config file

Use the [player options page](../player-options), or the template `Valheim.yaml` that comes with the release, and
put the file in your Archipelago `Players` folder.

## Connecting

1. Start Valheim through r2modman (Start modded).
2. In the Archipelago window on the main menu, enter the server address, port, your slot name and the password if
   there is one, then click Connect.
3. Start a new world (a new character is recommended too).

Type `/ap status` in the in-game chat to check the connection, and `/ap` for the list of commands.

## Playing together

Several players can share one slot: one player connects, and the others tick Randomized in the Archipelago window
without connecting. Their checks are sent through the world.
