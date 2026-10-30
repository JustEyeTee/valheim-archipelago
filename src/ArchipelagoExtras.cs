using System;
using System.Collections;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using HarmonyLib;
using Jotunn.Configs;
using Jotunn.Entities;
using Jotunn.Managers;
using UnityEngine;

// Checks and items beyond researches and trophies: biome discovery, obtain, kill and explore
// checks, resource bundles (delivered to an Archipelago Chest the player builds) and traps.
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

    // From checks.tsv (embedded in the DLL; the APWorld is generated from the same file).
    private static readonly Dictionary<string, string> ObtainLocations = new Dictionary<string, string>();
    private static readonly Dictionary<string, string> KillLocations = new Dictionary<string, string>();
    private static readonly List<(float percent, string location)> ExploreLocations = new List<(float, string)>();

    private static readonly HashSet<string> Traps = new HashSet<string>
    {
        "Greydwarf Ambush Trap", "Thunderstorm Trap", "Burning Trap", "Soaked Trap", "Famine Trap",
    };

    private const float TrapSpacingSeconds = 10f;
    private const float StormSeconds = 120f;
    private const float ReminderSeconds = 60f;
    private const float ExploreCheckSeconds = 15f;
    private const float WorldRadius = 10000f;

    private static readonly AccessTools.FieldRef<Minimap, BitArray> ExploredRef =
        AccessTools.FieldRefAccess<Minimap, BitArray>("m_explored");

    private static float nextTrapTime;
    private static float stormEndTime;
    private static float nextReminderTime;
    private static float nextExploreTime;
    private static int[] exploredWords;

    public static IEnumerable<string> LocationNames => BiomeLocations.Values
        .Concat(ObtainLocations.Values).Concat(KillLocations.Values).Concat(ExploreLocations.Select(e => e.location));

    static ArchipelagoExtras()
    {
        using (var stream = typeof(ArchipelagoExtras).Assembly.GetManifestResourceStream("checks.tsv"))
        using (var reader = new StreamReader(stream))
        {
            string line;
            while ((line = reader.ReadLine()) != null)
            {
                if (line.Length == 0 || line.StartsWith("#", StringComparison.Ordinal)) continue;
                var cols = line.Split('\t');
                switch (cols[0])
                {
                    case "obtain": ObtainLocations[cols[1]] = cols[2]; break;
                    case "kill": KillLocations[cols[1]] = cols[2]; break;
                    case "explore":
                        ExploreLocations.Add((float.Parse(cols[1], CultureInfo.InvariantCulture), cols[2]));
                        break;
                }
            }
        }
    }

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

        if (Time.time >= nextExploreTime)
        {
            nextExploreTime = Time.time + ExploreCheckSeconds;
            CheckExploration(player);
        }

        if (stormEndTime > 0f && Time.time >= stormEndTime)
        {
            stormEndTime = 0f;
            EnvMan.instance?.SetForceEnvironment("");
        }
    }

    // Obtain checks: anything entering the inventory, picked up or crafted.
    public static void OnInventoryChanged(Inventory inventory)
    {
        foreach (var item in inventory.GetAllItems())
        {
            var prefab = item?.m_dropPrefab?.name;
            if (prefab != null && ObtainLocations.TryGetValue(prefab, out var location))
            {
                ArchipelagoConnection.SendLocationOnce(location);
            }
        }
    }

    // Kill checks: creatures are known by the trophy in their drop table, which every
    // variant of a creature shares (a sleeping Draugr or a frozen Greydwarf counts).
    public static void OnCreatureKilled(Character character)
    {
        var drops = character.GetComponent<CharacterDrop>();
        if (drops == null || drops.m_drops == null) return;
        foreach (var drop in drops.m_drops)
        {
            if (drop?.m_prefab != null && KillLocations.TryGetValue(drop.m_prefab.name, out var location))
            {
                ArchipelagoConnection.SendLocationOnce(location);
            }
        }
    }

    // Explore checks: the share of the world (a 10 km radius disc) uncovered on your own map.
    private static void CheckExploration(Player player)
    {
        var minimap = Minimap.instance;
        if (minimap == null || ExploreLocations.All(e => ArchipelagoConnection.IsLocationDone(e.location))) return;
        var explored = ExploredRef(minimap);
        if (explored == null) return;

        int words = (explored.Length + 31) / 32;
        if (exploredWords == null || exploredWords.Length != words) exploredWords = new int[words];
        explored.CopyTo(exploredWords, 0);
        long count = 0;
        foreach (var word in exploredWords) count += PopCount((uint)word);

        float radiusPixels = WorldRadius / minimap.m_pixelSize;
        double total = Math.Min(Math.PI * radiusPixels * radiusPixels, (double)minimap.m_textureSize * minimap.m_textureSize);
        float percent = (float)(100.0 * count / total);

        foreach (var (threshold, location) in ExploreLocations)
        {
            if (percent < threshold || ArchipelagoConnection.IsLocationDone(location)) continue;
            ArchipelagoConnection.SendLocationOnce(location);
            player.Message(MessageHud.MessageType.TopLeft, $"Archipelago: explored {percent:0.##}% of the world");
        }
    }

    private static int PopCount(uint v)
    {
        v -= (v >> 1) & 0x55555555u;
        v = (v & 0x33333333u) + ((v >> 2) & 0x33333333u);
        return (int)((((v + (v >> 4)) & 0x0F0F0F0Fu) * 0x01010101u) >> 24);
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
