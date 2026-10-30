# Valheim

## Where is the options page?

The [player options page for this game](../player-options) contains all the options you need to configure and
export a config file.

## What does randomization do to this game?

Recipes and building pieces are locked behind researches, which you craft at a Research Bench (Hammer > Randomizer).
Crafting a research is a check; the research itself is an item that can be anywhere in the multiworld. Each
research needs some materials and, often, other researches first.

Many other things you do are checks too, depending on your options: picking up each trophy, entering each biome,
getting each material for the first time, reaching dungeons and boss altars, raising skills, exploring the map,
building stations, eating foods, catching fish, taming animals, buying from traders and killing each kind of
creature.

## What is the goal of Valheim when randomized?

Your goal boss sets how far the game goes: Eikthyr, The Elder, Bonemass, Moder, Yagluth, The Queen, Fader, or
Kall Fimbulbringer in the Deep North (the full game). Checks and items from after it are left out of the game.

By default you win by defeating that boss and picking up its trophy (Kall Fimbulbringer has none, so his
Sacrificial Blood). With `goal_conditions` you can instead (or also) have to do any combination of these,
counted within your goal's era:

- **All Bosses**: defeat every boss up to your goal, in any order.
- **Relic Hunt**: receive a share of the Forsaken Relics spread through the multiworld.
- **Trophy Hunt**: collect a share of the era's trophies.
- **Researcher**: craft a share of the era's researches.
- **Explorer**: uncover a share of the world map.
- **Skill Master**: raise a number of skills to a level.
- **Hildir's Quests**: return the chests Hildir asks for (from The Elder's era on).

Type `/ap goal` in the in-game chat to see your progress.

## What items can be sent to me?

- Researches, which unlock recipes and building pieces.
- Trophy researches, which give a permanent boost.
- The drops of earlier bosses (Hard Antler, Swamp Key, Wishbone, Dragon Tears, Torn Spirit, Majestic Carapace),
  which open the next part of the game without the fight.
- Tools, resource bundles and boosts (skill training, blessings).
- Forsaken Relics, in a Relic Hunt.
- Traps, such as ambushes, raids, storms, Floor Is Lava and Butterfingers.

Physical items arrive in an Archipelago Chest you build (Hammer > Randomizer).

## What does another world's item look like in Valheim?

Nothing changes in the world itself: when you craft a research or do another check, a message says what was sent
and to whom.

## When the player receives an item, what happens?

A message shows what you received and who sent it. Researches unlock at once; physical items appear in your
Archipelago Chest; traps and boosts take effect right away.
