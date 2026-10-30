using System;
using System.Collections.Generic;
using System.Linq;
using Jotunn.Configs;
using Jotunn.Entities;
using Jotunn.Managers;
using UnityEngine;

// Checks and items beyond researches and trophies: biome discovery checks, resource bundles
// (delivered to an Archipelago Chest the player builds) and traps.
public static class ArchipelagoExtras
{
    public const string ChestPrefabName = "piece_randomizer_apchest";

    private static readonly Dictionary<Heightmap.Biome, string> BiomeLocations = new Dictionary<Heightmap.Biome, string>
    {
        { Heightmap.Biome.BlackForest, "Biome: Black Forest" },
        { Heightmap.Biome.Swamp, "Biome: Swamp" },
        { Heightmap.Biome.Mountain, "Biome: Mountains" },
        { Heightmap.Biome.Ocean, "Biome: Ocean" },
        { Heightmap.Biome.Plains, "Biome: Plains" },
        { Heightmap.Biome.Mistlands, "Biome: Mistlands" },
        { Heightmap.Biome.AshLands, "Biome: Ashlands" },
        { Heightmap.Biome.DeepNorth, "Biome: Deep North" },
    };

    // AP item name -> item prefab and stack size
    private static readonly Dictionary<string, (string prefab, int amount)> Bundles = new Dictionary<string, (string, int)>
    {
        { "20 Wood", ("Wood", 20) },
        { "20 Stone", ("Stone", 20) },
        { "10 Resin", ("Resin", 10) },
        { "50 Coins", ("Coins", 50) },
        { "5 Cooked Meat", ("CookedMeat", 5) },
    };

    private static readonly HashSet<string> Traps = new HashSet<string>
    {
        "Greydwarf Ambush Trap", "Thunderstorm Trap", "Burning Trap", "Soaked Trap", "Famine Trap",
    };

    private const float TrapSpacingSeconds = 10f;
    private const float StormSeconds = 120f;
    private const float ReminderSeconds = 60f;

    private static float nextTrapTime;
    private static float stormEndTime;
    private static float nextReminderTime;

    public static IEnumerable<string> LocationNames => BiomeLocations.Values;

    public static bool IsExtraItem(string name) => Bundles.ContainsKey(name) || Traps.Contains(name);

    public static void RegisterChest()
    {
        var clone = PrefabManager.Instance.CreateClonedPrefab(ChestPrefabName, "piece_chest_wood");
        if (!clone)
        {
            ValheimRandomizer.Log.LogError("Failed to clone 'piece_chest_wood' for the Archipelago Chest");
            return;
        }
        var container = clone.GetComponent<Container>();
        if (container) container.m_name = "Archipelago Chest";

        var pieceCfg = new PieceConfig
        {
            Name = "Archipelago Chest",
            Description = "Resource bundles sent to you through Archipelago are delivered here.",
            PieceTable = "Hammer",
            Category = "Randomizer",
            Requirements = new[] { new RequirementConfig("Wood", 10, recover: true) }
        };
        PieceManager.Instance.AddPiece(new CustomPiece(clone, true, pieceCfg));
        ValheimRandomizer.Log.LogInfo("Archipelago Chest registered");
    }

    // Called every couple of seconds while a randomized world is loaded.
    public static void Tick()
    {
        var player = Player.m_localPlayer;
        if (player == null) return;

        if (BiomeLocations.TryGetValue(player.GetCurrentBiome(), out var location))
        {
            ArchipelagoConnection.SendLocationOnce(location);
        }

        if (stormEndTime > 0f && Time.time >= stormEndTime)
        {
            stormEndTime = 0f;
            EnvMan.instance?.SetForceEnvironment("");
        }
    }

    // Bundles and traps can be received more than once, so they are handled by their order
    // in the received list. How many of each were handled is kept in the character's custom
    // data under `progressKey` (room seed, slot and world), so nothing repeats or is lost.
    public static void ProcessItems(IEnumerable<string> receivedNames, string progressKey)
    {
        var player = Player.m_localPlayer;
        if (player == null) return;

        int bundlesDone = GetCount(player, progressKey + ":bundles");
        int trapsDone = GetCount(player, progressKey + ":traps");
        int bundleIndex = 0, trapIndex = 0, waiting = 0;
        bool bundlesBlocked = false;
        Container chest = null;
        bool chestFull = false;

        foreach (var name in receivedNames)
        {
            if (Bundles.TryGetValue(name, out var bundle))
            {
                if (bundleIndex++ < bundlesDone) continue;
                if (!bundlesBlocked)
                {
                    if (chest == null) chest = FindChest();
                    if (chest != null && Deliver(chest, bundle.prefab, bundle.amount, out chestFull))
                    {
                        SetCount(player, progressKey + ":bundles", ++bundlesDone);
                        player.Message(MessageHud.MessageType.TopLeft, $"Archipelago: {name} delivered to your Archipelago Chest");
                        continue;
                    }
                    bundlesBlocked = true; // keep later bundles waiting so the order is kept
                }
                waiting++;
            }
            else if (Traps.Contains(name))
            {
                if (trapIndex++ < trapsDone) continue;
                if (Time.time < nextTrapTime) continue;
                FireTrap(player, name);
                SetCount(player, progressKey + ":traps", ++trapsDone);
                nextTrapTime = Time.time + TrapSpacingSeconds;
            }
        }

        if (waiting > 0 && Time.time >= nextReminderTime)
        {
            nextReminderTime = Time.time + ReminderSeconds;
            player.Message(MessageHud.MessageType.Center, chestFull
                ? $"{waiting} Archipelago deliveries waiting: your Archipelago Chest is full"
                : $"{waiting} Archipelago deliveries waiting: build an Archipelago Chest (Hammer > Randomizer)");
        }
    }

    private static Container FindChest()
    {
        return UnityEngine.Object.FindObjectsByType<Container>(FindObjectsSortMode.None)
            .FirstOrDefault(c => c && c.name.StartsWith(ChestPrefabName, StringComparison.Ordinal)
                                 && c.GetComponent<ZNetView>() is ZNetView nview && nview.IsValid());
    }

    private static bool Deliver(Container chest, string prefabName, int amount, out bool full)
    {
        full = false;
        var prefab = ObjectDB.instance ? ObjectDB.instance.GetItemPrefab(prefabName) : null;
        if (!prefab)
        {
            // Bad data must not block every later delivery.
            ValheimRandomizer.Log.LogError($"[AP] Bundle item '{prefabName}' not found; skipping it.");
            return true;
        }
        var nview = chest.GetComponent<ZNetView>();
        if (!nview.IsOwner()) nview.ClaimOwnership();

        var inventory = chest.GetInventory();
        if (!inventory.CanAddItem(prefab, amount))
        {
            full = true;
            return false;
        }
        return inventory.AddItem(prefab, amount);
    }

    private static void FireTrap(Player player, string trap)
    {
        ValheimRandomizer.Log.LogInfo("[AP] Trap: " + trap);
        switch (trap)
        {
            case "Greydwarf Ambush Trap":
                SpawnAround(player, "Greydwarf", 3, 10f);
                break;
            case "Thunderstorm Trap":
                if (EnvMan.instance != null && EnvMan.instance.m_environments.Any(env => env.m_name == "ThunderStorm"))
                {
                    EnvMan.instance.SetForceEnvironment("ThunderStorm");
                    stormEndTime = Time.time + StormSeconds;
                }
                else ValheimRandomizer.Log.LogWarning("[AP] Environment 'ThunderStorm' not found");
                break;
            case "Burning Trap":
                AddEffect(player, "Burning");
                break;
            case "Soaked Trap":
                AddEffect(player, "Wet");
                break;
            case "Famine Trap":
                player.ClearFood();
                break;
        }
        player.Message(MessageHud.MessageType.Center, $"Archipelago: {trap}!");
    }

    private static void SpawnAround(Player player, string prefabName, int count, float distance)
    {
        var prefab = ZNetScene.instance ? ZNetScene.instance.GetPrefab(prefabName) : null;
        if (!prefab)
        {
            ValheimRandomizer.Log.LogWarning($"[AP] Creature '{prefabName}' not found");
            return;
        }
        for (int i = 0; i < count; i++)
        {
            var offset = Quaternion.Euler(0f, 360f * i / count, 0f) * Vector3.forward * distance;
            var pos = player.transform.position + offset;
            pos.y = ZoneSystem.instance.GetGroundHeight(pos) + 0.5f;
            UnityEngine.Object.Instantiate(prefab, pos, Quaternion.identity);
        }
    }

    private static void AddEffect(Player player, string effectName)
    {
        int hash = effectName.GetStableHashCode();
        if (ObjectDB.instance == null || ObjectDB.instance.GetStatusEffect(hash) == null)
        {
            ValheimRandomizer.Log.LogWarning($"[AP] Status effect '{effectName}' not found");
            return;
        }
        player.GetSEMan().AddStatusEffect(hash, true);
    }

    private static int GetCount(Player player, string key)
    {
        return player.m_customData.TryGetValue(key, out var value) && int.TryParse(value, out var count) ? count : 0;
    }

    private static void SetCount(Player player, string key, int count)
    {
        player.m_customData[key] = count.ToString();
    }
}
