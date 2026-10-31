using System;
using System.Collections;
using System.Collections.Concurrent;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using HarmonyLib;
using Jotunn.Configs;
using Jotunn.Entities;
using Jotunn.Managers;
using UnityEngine;

// Checks and items beyond researches and trophies: biome, obtain, kill, skill, discover and
// explore checks, resource bundles (delivered to an Archipelago Chest the player builds),
// boosts and traps.
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
        { "3 Minor Healing Meads", ("MeadHealthMinor", 3) },
        { "3 Minor Stamina Meads", ("MeadStaminaMinor", 3) },
        { "20 Fire Arrows", ("ArrowFire", 20) },
        { "10 Flint", ("Flint", 10) },
        // Era bundles (the APWorld only places those up to the goal's tier)
        { "10 Copper", ("Copper", 10) }, { "10 Tin", ("Tin", 10) }, { "10 Coal", ("Coal", 10) },
        { "3 Surtling Cores", ("SurtlingCore", 3) }, { "10 Bronze", ("Bronze", 10) },
        { "10 Finewood", ("FineWood", 10) }, { "10 Ancient Bark", ("ElderBark", 10) }, { "10 Iron", ("Iron", 10) },
        { "10 Silver", ("Silver", 10) }, { "5 Obsidian", ("Obsidian", 5) }, { "10 Black Metal", ("BlackMetal", 10) },
        { "10 Linen Thread", ("LinenThread", 10) }, { "10 Yggdrasil Wood", ("YggdrasilWood", 10) },
        { "10 Black Marble", ("BlackMarble", 10) }, { "5 Refined Eitr", ("Eitr", 5) },
        { "10 Flametal", ("FlametalNew", 10) }, { "10 Ashwood", ("Blackwood", 10) }, { "5 Bloodgold", ("Gold", 5) },
        // Boss drops
        { "Hard Antler", ("HardAntler", 1) }, { "Swamp Key", ("CryptKey", 1) }, { "Wishbone", ("Wishbone", 1) },
        { "3 Dragon Tears", ("DragonTear", 3) }, { "Torn Spirit", ("YagluthDrop", 1) },
        { "Majestic Carapace", ("QueenDrop", 1) },
        // Tools
        { "Flint Axe", ("AxeFlint", 1) }, { "Antler Pickaxe", ("PickaxeAntler", 1) },
        { "Bronze Axe", ("AxeBronze", 1) }, { "Bronze Pickaxe", ("PickaxeBronze", 1) },
        { "Iron Axe", ("AxeIron", 1) }, { "Iron Pickaxe", ("PickaxeIron", 1) },
        { "Black Metal Axe", ("AxeBlackMetal", 1) }, { "Black Metal Pickaxe", ("PickaxeBlackMetal", 1) },
    };

    // The item prefab a bundle, tool or boss drop delivers (for its icon), or null.
    public static string ItemPrefab(string apItem) => Bundles.TryGetValue(apItem, out var b) ? b.prefab : null;

    // Maps: AP item name -> the boss location it pins (as that boss's Vegvisir does), and Map Fragments.
    private static readonly Dictionary<string, (string location, string pin)> BossMaps = new Dictionary<string, (string, string)>
    {
        { "Map to Eikthyr", ("Eikthyrnir", "Eikthyr") }, { "Map to The Elder", ("GDKing", "The Elder") },
        { "Map to Bonemass", ("Bonemass", "Bonemass") }, { "Map to Moder", ("Dragonqueen", "Moder") },
        { "Map to Yagluth", ("GoblinKing", "Yagluth") }, { "Map to The Queen", ("Mistlands_DvergrBossEntrance1", "The Queen") },
        { "Map to Fader", ("FaderLocation", "Fader") }, { "Map to Kall Fimbulbringer", ("DN_Bossroom", "Kall Fimbulbringer") },
    };
    private const string MapFragment = "Map Fragment";
    private const float FragmentRadius = 250f;
    private static readonly System.Reflection.MethodInfo MinimapExplore =
        AccessTools.Method(typeof(Minimap), "Explore", new[] { typeof(Vector3), typeof(float) });

    // Starter Kit: straight into the inventory, since there's no chest yet. Nothing in it is a check (Raspberries
    // were, and the kit sent "Obtain: Raspberries" on arrival).
    private static readonly (string prefab, int amount)[] StarterKit =
        { ("Club", 1), ("AxeStone", 1), ("Torch", 1) };

    // From checks.tsv (embedded in the DLL; the APWorld is generated from the same file).
    private static readonly Dictionary<string, string> ObtainLocations = new Dictionary<string, string>();
    private static readonly Dictionary<string, string> KillLocations = new Dictionary<string, string>();
    private static readonly List<(float percent, string location)> ExploreLocations = new List<(float, string)>();
    private static readonly List<(int level, string location)> ComfortLocations = new List<(int, string)>();
    private static readonly List<(string prefix, string location)> ReadLocations = new List<(string, string)>();
    private static readonly Dictionary<string, string> VegvisirLocations = new Dictionary<string, string>();
    private static readonly Dictionary<string, string> LootLocations = new Dictionary<string, string>();
    private static readonly Dictionary<string, string> BrewLocations = new Dictionary<string, string>();
    private static readonly Dictionary<string, string> RaidLocations = new Dictionary<string, string>();

    private static readonly List<(Skills.SkillType skill, int level, string location)> SkillLocations =
        new List<(Skills.SkillType, int, string)>();
    private static readonly List<(string prefix, string location)> DiscoverLocations = new List<(string, string)>();
    private static readonly Dictionary<string, string> EatLocations = new Dictionary<string, string>();
    private static readonly Dictionary<string, string> BuildLocations = new Dictionary<string, string>();
    private static readonly Dictionary<string, string> BuyLocations = new Dictionary<string, string>();
    private static readonly Dictionary<string, string> TameLocations = new Dictionary<string, string>();

    public static readonly string[] TrapNames =
    {
        "Greydwarf Ambush Trap", "Thunderstorm Trap", "Burning Trap", "Soaked Trap", "Famine Trap",
        "Skeleton Ambush Trap", "Poison Trap", "Frost Trap", "Raid Trap", "Butterfingers Trap", "Heavy Load Trap",
        "Monster Pack Trap", "Bat Swarm Trap", "Lightning Strike Trap", "Floor Is Lava Trap", "Blizzard Trap",
        "Tar Trap", "Launch Trap", "Rust Trap", "Meteor Shower Trap", "Fake Item Trap",
    };

    // Monster Pack Trap: what lives in each biome (Ocean gets bats, which fly).
    private static readonly Dictionary<Heightmap.Biome, (string creature, int count)> BiomePacks =
        new Dictionary<Heightmap.Biome, (string, int)>
    {
        { Heightmap.Biome.Meadows, ("Greydwarf", 4) },
        { Heightmap.Biome.BlackForest, ("Greydwarf_Elite", 2) },
        { Heightmap.Biome.Swamp, ("Draugr", 3) },
        { Heightmap.Biome.Mountain, ("Wolf", 3) },
        { Heightmap.Biome.Plains, ("Goblin", 3) },
        { Heightmap.Biome.Mistlands, ("Seeker", 3) },
        { Heightmap.Biome.AshLands, ("Charred_Melee", 3) },
        { Heightmap.Biome.DeepNorth, ("BlobFrost", 3) },
        { Heightmap.Biome.Ocean, ("Bat", 6) },
    };
    private static readonly HashSet<string> Traps = new HashSet<string>(TrapNames);

    private static readonly HashSet<string> Boosts = new HashSet<string>
    {
        "Combat Training", "Woodcutting Training", "Mining Training",
        "Rested Blessing", "Eikthyr's Blessing", "Moder's Blessing",
    };

    // Traps from other games (Trap Link, Death Link in trap mode), fired on the main thread.
    private static readonly ConcurrentQueue<string> externalTraps = new ConcurrentQueue<string>();
    public static void QueueTrap(string trap) => externalTraps.Enqueue(trap);

    // /ap clear traps: the traps waiting now are counted as done without firing.
    private static bool clearTraps;
    public static void ClearTraps()
    {
        clearTraps = true;
        while (externalTraps.TryDequeue(out _)) { }
    }

    private const float TrapSpacingSeconds = 10f;
    // With traps waiting (a release, or Trap Link), they come faster, down to one a second, so they pile up.
    private static float TrapSpacing(int waiting) => waiting <= 1 ? TrapSpacingSeconds : Mathf.Max(1f, TrapSpacingSeconds / waiting);
    private const int MaxMeteorShowers = 10;       // at once (each drops its own meteors)
    private const float MaxLavaSeconds = 90f;      // stacked Floor Is Lava
    private const float MaxStormSeconds = 300f;    // stacked weather
    private const float StormSeconds = 120f;
    private const float BlizzardSeconds = 90f;
    private const float MeteorSeconds = 60f;
    private const float LavaSeconds = 30f;
    private const float ReminderSeconds = 60f;
    private const float ExploreCheckSeconds = 15f;
    private const float WorldRadius = 10000f;

    private static readonly AccessTools.FieldRef<Character, Collider> LastGroundRef =
        AccessTools.FieldRefAccess<Character, Collider>("m_lastGroundCollider");
    private static readonly AccessTools.FieldRef<Minimap, BitArray> ExploredRef =
        AccessTools.FieldRefAccess<Minimap, BitArray>("m_explored");

    private static float nextTrapTime;
    private static float stormEndTime;
    private static string forcedEnvironment;
    private static float lavaEndTime;
    private static float nextReminderTime;
    private static float nextExploreTime;
    private static int[] exploredWords;

    public static IEnumerable<string> LocationNames => BiomeLocations.Values
        .Concat(ObtainLocations.Values).Concat(KillLocations.Values).Concat(ExploreLocations.Select(e => e.location))
        .Concat(SkillLocations.Select(e => e.location)).Concat(DiscoverLocations.Select(e => e.location))
        .Concat(ComfortLocations.Select(e => e.location)).Concat(ReadLocations.Select(e => e.location))
        .Concat(VegvisirLocations.Values).Concat(LootLocations.Values).Concat(BrewLocations.Values)
        .Concat(RaidLocations.Values)
        .Concat(EatLocations.Values).Concat(BuildLocations.Values).Concat(BuyLocations.Values).Concat(TameLocations.Values);

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
                    case "obtain":
                    case "catch": ObtainLocations[cols[1]] = cols[2]; break;
                    case "eat": EatLocations[cols[1]] = cols[2]; break;
                    case "build":
                    case "plant": BuildLocations[cols[1]] = cols[2]; break;
                    case "read": ReadLocations.Add((cols[1], cols[2])); break;
                    case "vegvisir": VegvisirLocations[cols[1]] = cols[2]; break;
                    case "loot": LootLocations[cols[1]] = cols[2]; break;
                    case "brew": BrewLocations[cols[1]] = cols[2]; break;
                    case "raid": RaidLocations[cols[1]] = cols[2]; break;
                    case "buy": BuyLocations[cols[1]] = cols[2]; break;
                    case "tame": TameLocations[cols[1]] = cols[2]; break;
                    case "kill": KillLocations[cols[1]] = cols[2]; break;
                    case "explore":
                        ExploreLocations.Add((float.Parse(cols[1], CultureInfo.InvariantCulture), cols[2]));
                        break;
                    case "skill":
                        var parts = cols[1].Split(':');
                        SkillLocations.Add(((Skills.SkillType)Enum.Parse(typeof(Skills.SkillType), parts[0]),
                            int.Parse(parts[1], CultureInfo.InvariantCulture), cols[2]));
                        break;
                    case "discover": DiscoverLocations.Add((cols[1], cols[2])); break;
                    case "comfort": ComfortLocations.Add((int.Parse(cols[1], CultureInfo.InvariantCulture), cols[2])); break;
                }
            }
        }
    }

    // Every item name the mod handles beyond researches (for /ap give and /ap items).
    public static IEnumerable<string> ItemNames => Bundles.Keys.Concat(TrapNames).Concat(Boosts)
        .Concat(new[] { "Starter Kit", ArchipelagoGoal.RelicName, MapFragment }).Concat(BossMaps.Keys);

    public static bool IsExtraItem(string name) =>
        Bundles.ContainsKey(name) || Traps.Contains(name) || Boosts.Contains(name) || name == "Starter Kit" ||
        name == ArchipelagoGoal.RelicName || BossMaps.ContainsKey(name) || name == MapFragment;

    // The skill a skill check is for ("Skill: Woodcutting 10" -> WoodCutting).
    public static Skills.SkillType? SkillOf(string location)
    {
        foreach (var (skill, _, skillLocation) in SkillLocations)
        {
            if (skillLocation == location) return skill;
        }
        return null;
    }

    public static void RegisterChest()
    {
        var clone = PrefabManager.Instance.CreateClonedPrefab(ChestPrefabName, "piece_chest_wood");
        if (!clone)
        {
            ValheimRandomizer.Log.LogError("Failed to clone 'piece_chest_wood' for the Archipelago Chest");
            return;
        }
        var container = clone.GetComponent<Container>();
        if (container)
        {
            container.m_name = "Archipelago Chest";
            // 32 stacks (a Black Metal Chest's size) instead of the wooden chest's 10: deliveries pile up fast.
            container.m_width = 8;
            container.m_height = 4;
        }

        var pieceCfg = new PieceConfig
        {
            Name = "Archipelago Chest",
            Description = "Resource bundles sent to you through Archipelago are delivered here.",
            PieceTable = "Hammer",
            Category = "Randomizer",
#if FASTTEST
            Requirements = new[] { new RequirementConfig("Wood", 1, recover: true) }
#else
            Requirements = new[] { new RequirementConfig("Wood", 10, recover: true) }
#endif
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

        foreach (var (skill, level, skillLocation) in SkillLocations)
        {
            if (player.GetSkills().GetSkillLevel(skill) >= level && ArchipelagoConnection.IsSkillLevelChecked(level))
                ArchipelagoConnection.SendLocationOnce(skillLocation);
        }
        ArchipelagoGoal.MarkSkills(player);

        // Comfort checks: the level the game would give the Rested effect where you stand.
        if (ComfortLocations.Count > 0)
        {
            int comfort = SE_Rested.CalculateComfortLevel(player);
            foreach (var (level, comfortLocation) in ComfortLocations)
            {
                if (comfort >= level) ArchipelagoConnection.SendLocationOnce(comfortLocation);
            }
        }

        var here = Location.GetLocation(player.transform.position);
        if (here != null)
        {
            var prefab = here.gameObject.name;
            foreach (var (prefix, discoverLocation) in DiscoverLocations)
            {
                if (prefab.StartsWith(prefix, StringComparison.Ordinal)) ArchipelagoConnection.SendLocationOnce(discoverLocation);
            }
        }

        if (ArchipelagoConnection.GoalDone) ClearTraps();
        if (Time.time >= nextTrapTime && !player.IsDead() && externalTraps.TryDequeue(out var trap))
        {
            FireTrap(player, trap);
            nextTrapTime = Time.time + TrapSpacing(externalTraps.Count);
        }

        ArchipelagoLinks.Tick(player);
        ArchipelagoRewards.Apply();
        if (player.IsDead() || Time.time >= nextTrapCreatureCheck)
        {
            nextTrapCreatureCheck = Time.time + 5f;
            DespawnTrapCreatures(player.IsDead());
        }

        if (Time.time >= nextExploreTime)
        {
            nextExploreTime = Time.time + ExploreCheckSeconds;
            CheckExploration(player);
        }

        if (lavaEndTime > 0f)
        {
            if (Time.time >= lavaEndTime || player.IsDead())
            {
                lavaEndTime = 0f;
                player.Message(MessageHud.MessageType.Center, "The floor is no longer lava");
            }
            else if (player.IsOnGround() && !OnSafeGround(player) &&
                     AddEffect(player, "Burning") is SE_Burning lava)
            {
                lava.AddFireDamage(player.GetMaxHealth() * 0.05f);
            }
        }

        if (meteorShowers.Count > 0)
        {
            if (player.IsDead()) meteorShowers.Clear();
            else meteorShowers.RemoveAll(end => Time.time >= end);
            if (meteorShowers.Count > 0 && Time.time >= nextMeteorTime)
            {
                nextMeteorTime = Time.time + MeteorSpacingSeconds;
                for (int i = 0; i < meteorShowers.Count; i++) DropMeteor(player);  // stacked showers: one meteor each
            }
        }

        if (stormEndTime > 0f && Time.time >= stormEndTime)
        {
            stormEndTime = 0f;
            EnvMan.instance?.SetForceEnvironment("");
        }
    }

    // Obtain checks: anything entering the inventory, picked up or crafted. A shuffled boss drop's check is
    // picking up the boss's own drop (AllowPickup), not the received one coming out of the Archipelago Chest.
    public static void OnInventoryChanged(Inventory inventory)
    {
        foreach (var item in inventory.GetAllItems())
        {
            var prefab = item?.m_dropPrefab?.name;
            if (prefab != null && !ArchipelagoConnection.ShuffledBossDrops.ContainsKey(prefab)
                && ObtainLocations.TryGetValue(prefab, out var location))
            {
                ArchipelagoConnection.SendLocationOnce(location);
            }
        }
    }

    private static float nextDropMessage;

    // boss_items shuffled: picking up a boss's drop (Hard Antler, Swamp Key...) before receiving its item sends
    // the drop's check and takes one of it away (drops on the ground stack); the item comes from the multiworld.
    // Once the check is sent, the rest stay on the ground for other players (a slot each) and you can't pick
    // them up. Once the item is received, drops are picked up as usual. Returns whether the game's own pickup
    // goes ahead.
    public static bool AllowPickup(Humanoid who, ItemDrop drop, bool autoPickupDelay)
    {
        if (who != Player.m_localPlayer || drop == null || !ArchipelagoConnection.IsConnected) return true;
        var prefab = drop.m_itemData?.m_dropPrefab ? drop.m_itemData.m_dropPrefab.name : PrefabName(drop.gameObject);
        if (!ArchipelagoConnection.ShuffledBossDrops.TryGetValue(prefab, out var item)) return true;
        ObtainLocations.TryGetValue(prefab, out var location);
        if (!drop.CanPickup(autoPickupDelay)) return true;  // the game asks for ownership and tries again
        if (ArchipelagoConnection.ReceivedCount(item) > 0)
        {
            if (location != null) ArchipelagoConnection.SendLocationOnce(location);
            return true;
        }
        if (location != null && !ArchipelagoConnection.IsLocationDone(location))
        {
            ArchipelagoConnection.SendLocation(location);
            drop.RemoveOne();  // ours: CanPickup said so
            Player.m_localPlayer.Message(MessageHud.MessageType.Center,
                $"{Localization.instance.Localize(drop.m_itemData.m_shared.m_name)} sent off as a check: your {item} comes from Archipelago");
            return false;
        }
        drop.m_autoPickup = false;  // left for other players; walking past it shouldn't keep trying
        if (Time.time >= nextDropMessage)
        {
            nextDropMessage = Time.time + 3f;
            Player.m_localPlayer.Message(MessageHud.MessageType.Center, $"Your {item} comes from Archipelago");
        }
        return false;
    }

    private static string PrefabName(GameObject go)
    {
        var name = go.name;
        int clone = name.IndexOf("(Clone)", StringComparison.Ordinal);
        return clone >= 0 ? name.Substring(0, clone) : name;
    }

    private static void SendFrom(Dictionary<string, string> locations, string prefab)
    {
        if (prefab != null && locations.TryGetValue(prefab, out var location)) ArchipelagoConnection.SendLocationOnce(location);
    }

    public static void OnFoodEaten(ItemDrop.ItemData food) => SendFrom(EatLocations, food?.m_dropPrefab?.name);
    public static void OnPiecePlaced(Piece piece) => SendFrom(BuildLocations, piece ? PrefabName(piece.gameObject) : null);
    // A trader's list: items whose first purchase is a check still to do say so, and what it sends.
    public static void MarkBuyCheck(Trader.TradeItem item, GameObject element)
    {
        var prefab = item?.m_prefab ? item.m_prefab.name : null;
        if (prefab == null || element == null || !BuyLocations.TryGetValue(prefab, out var location)) return;
        if (ArchipelagoConnection.IsLocationDone(location) || !ArchipelagoRewards.TryGet(location, out var reward)) return;
        var name = element.transform.Find("name")?.GetComponent<TMPro.TMP_Text>();
        if (name != null) name.text += " <color=#e8a33d>(check)</color>";
        var tooltip = element.GetComponent<UITooltip>();
        if (tooltip != null)
            tooltip.m_text += $"\n\n<color=#e8a33d>Archipelago:</color> buying this the first time sends {ArchipelagoRewards.Describe(reward)}.";
    }

    public static void OnItemBought(Trader.TradeItem item) => SendFrom(BuyLocations, item?.m_prefab ? item.m_prefab.name : null);
    // Lore checks: a rune stone, by the rune stone location it stands in; a Vegvisir, by the boss it reveals.
    public static void OnRuneStoneRead(RuneStone stone)
    {
        var here = stone ? Location.GetLocation(stone.transform.position) : null;
        if (here == null) return;
        var prefab = PrefabName(here.gameObject);
        foreach (var (prefix, location) in ReadLocations)
        {
            if (prefab.StartsWith(prefix, StringComparison.Ordinal)) ArchipelagoConnection.SendLocationOnce(location);
        }
    }

    public static void OnVegvisirRead(Vegvisir vegvisir)
    {
        foreach (var target in vegvisir.m_locations) SendFrom(VegvisirLocations, target.m_locationName);
    }

    // Brewing checks: tapping a ready Fermenter, by the mead it makes (read from its private state).
    private static readonly System.Reflection.MethodInfo FermenterStatus = AccessTools.Method(typeof(Fermenter), "GetStatus");
    private static readonly System.Reflection.MethodInfo FermenterContent = AccessTools.Method(typeof(Fermenter), "GetContent");
    private static readonly System.Reflection.MethodInfo FermenterConversion = AccessTools.Method(typeof(Fermenter), "GetItemConversion");

    public static void OnFermenterTapped(Fermenter fermenter)
    {
        if (fermenter == null || FermenterStatus == null || FermenterContent == null || FermenterConversion == null) return;
        if (FermenterStatus.Invoke(fermenter, null)?.ToString() != "Ready") return;
        var content = FermenterContent.Invoke(fermenter, null);
        var conversion = FermenterConversion.Invoke(fermenter, new[] { content }) as Fermenter.ItemConversion;
        if (conversion?.m_to != null) SendFrom(BrewLocations, conversion.m_to.gameObject.name);
    }

    // Raid checks: a raid ending while you're in it, alive, having been in it (without leaving) for a while, so
    // walking in at the last moment doesn't count.
    private const float RaidSecondsInside = 45f;
    private static readonly Dictionary<string, float> raidJoined = new Dictionary<string, float>();

    public static void OnRaidActivated(RandomEvent raid)
    {
        if (raid != null) raidJoined[raid.m_name] = Time.time;
    }

    public static void OnRaidDeactivated(RandomEvent raid, bool end)
    {
        if (raid == null || !raidJoined.TryGetValue(raid.m_name, out var joined)) return;
        raidJoined.Remove(raid.m_name);
        var player = Player.m_localPlayer;
        if (end && player != null && !player.IsDead() && Time.time - joined >= RaidSecondsInside)
            SendFrom(RaidLocations, raid.m_name);
    }

    // Dungeon checks: opening a treasure chest only that kind of dungeon has.
    public static void OnContainerOpened(Container container) => SendFrom(LootLocations, container ? PrefabName(container.gameObject) : null);

    public static void OnTamed(Tameable tameable) => SendFrom(TameLocations, tameable ? PrefabName(tameable.gameObject) : null);

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

    private static void ApplyMap(Player player, string name)
    {
        if (BossMaps.TryGetValue(name, out var map))
        {
            Game.instance.DiscoverClosestLocation(map.location, player.transform.position, map.pin, (int)Minimap.PinType.Boss, false);
            player.Message(MessageHud.MessageType.Center, $"Archipelago: {name}! Its altar is on your map.");
            return;
        }
        // A Map Fragment: a patch of the map somewhere around you, 0.5 to 2.5 km away.
        float angle = UnityEngine.Random.Range(0f, Mathf.PI * 2f), distance = UnityEngine.Random.Range(500f, 2500f);
        var spot = player.transform.position + new Vector3(Mathf.Cos(angle), 0f, Mathf.Sin(angle)) * distance;
        MinimapExplore?.Invoke(Minimap.instance, new object[] { spot, FragmentRadius });
        AddPin(spot, Minimap.PinType.Icon3, "Map Fragment");
        ValheimRandomizer.Log.LogInfo($"[AP] Map Fragment: uncovered {spot} ({distance:0} m away)");
        string direction = new[] { "east", "northeast", "north", "northwest", "west", "southwest", "south", "southeast" }
            [Mathf.RoundToInt(angle / (Mathf.PI / 4f)) % 8];
        player.Message(MessageHud.MessageType.Center, $"Archipelago: a Map Fragment! It shows land {distance / 1000f:0.0} km {direction} of here (pinned on your map).");
    }

    // Minimap.AddPin by reflection: its last parameter's type (PlatformUserID) lives in an assembly this mod
    // doesn't build against. Optional parameters get their defaults.
    private static readonly System.Reflection.MethodInfo MinimapAddPin = AccessTools.Method(typeof(Minimap), "AddPin");

    private static void AddPin(Vector3 pos, Minimap.PinType type, string name)
    {
        if (MinimapAddPin == null || Minimap.instance == null) return;
        var given = new object[] { pos, type, name, true, false };
        var args = MinimapAddPin.GetParameters().Select((p, i) => i < given.Length ? given[i]
            : p.HasDefaultValue && p.DefaultValue != null ? p.DefaultValue
            : p.ParameterType.IsValueType ? Activator.CreateInstance(p.ParameterType) : null).ToArray();
        MinimapAddPin.Invoke(Minimap.instance, args);
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
        int boostsDone = GetCount(player, progressKey + ":boosts");
        int kitsDone = GetCount(player, progressKey + ":kits");
        int mapsDone = GetCount(player, progressKey + ":maps");
        int bundleIndex = 0, trapIndex = 0, boostIndex = 0, kitIndex = 0, mapIndex = 0, waiting = 0;
        int trapsWaiting = receivedNames.Count(n => Traps.Contains(n)) - trapsDone + externalTraps.Count;
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
                // Once the goal is done (a release then sends everything at once), or when cleared, traps
                // are counted without firing, and not passed on to Trap Link.
                if (clearTraps || ArchipelagoConnection.GoalDone)
                {
                    SetCount(player, progressKey + ":traps", ++trapsDone);
                    continue;
                }
                if (Time.time < nextTrapTime || player.IsDead()) continue;
                FireTrap(player, name);
                SetCount(player, progressKey + ":traps", ++trapsDone);
                nextTrapTime = Time.time + TrapSpacing(--trapsWaiting);
                ArchipelagoLinks.SendTrapLink(name);
            }
            else if (name == "Starter Kit")
            {
                if (kitIndex++ < kitsDone || player.IsDead()) continue;
                foreach (var (prefab, amount) in StarterKit)
                {
                    var item = ObjectDB.instance ? ObjectDB.instance.GetItemPrefab(prefab) : null;
                    if (item) player.GetInventory().AddItem(item, amount);
                }
                SetCount(player, progressKey + ":kits", ++kitsDone);
                player.Message(MessageHud.MessageType.Center, "Archipelago: Starter Kit!");
            }
            else if (Boosts.Contains(name))
            {
                if (boostIndex++ < boostsDone || player.IsDead()) continue;
                ApplyBoost(player, name);
                SetCount(player, progressKey + ":boosts", ++boostsDone);
            }
            else if (BossMaps.ContainsKey(name) || name == MapFragment)
            {
                if (mapIndex++ < mapsDone || Minimap.instance == null || Game.instance == null) continue;
                ApplyMap(player, name);
                SetCount(player, progressKey + ":maps", ++mapsDone);
            }
        }
        clearTraps = false;  // only the traps that were waiting when it was asked

        if (waiting > 0 && Time.time >= nextReminderTime)
        {
            nextReminderTime = Time.time + ReminderSeconds;
            string others = chestFull ? null : OthersChestNearby();
            player.Message(MessageHud.MessageType.Center, chestFull
                ? $"{waiting} Archipelago deliveries waiting: your Archipelago Chest is full"
                : others != null
                    ? $"{waiting} Archipelago deliveries waiting: that chest is {others}; build your own Archipelago Chest (each slot has its own)"
                    : $"{waiting} Archipelago deliveries waiting: build an Archipelago Chest (Hammer > Randomizer)");
        }
    }

    // The slot an Archipelago Chest belongs to, kept on the chest when it's built (see OnChestBuilt).
    public const string ChestSlotKey = "ap_slot";

    // An Archipelago Chest that's loaded; with separate co-op slots, one of this player's slot. Only that
    // player's game writes to it: two games adding to one chest could overwrite each other's items.
    private static Container FindChest() => LoadedChests().FirstOrDefault(IsMyChest);

    private static IEnumerable<Container> LoadedChests() =>
        UnityEngine.Object.FindObjectsByType<Container>(FindObjectsSortMode.None)
            .Where(c => c && c.name.StartsWith(ChestPrefabName, StringComparison.Ordinal)
                        && c.GetComponent<ZNetView>() is ZNetView nview && nview.IsValid());

    private static bool IsMyChest(Container chest)
    {
        if (!ArchipelagoCoop.IsSeparate) return true;
        string owner = ChestSlot(chest);
        // Chests built before they were marked with a slot belong to whoever built them.
        if (string.IsNullOrEmpty(owner))
            return chest.GetComponent<Piece>() is Piece piece && Player.m_localPlayer && piece.GetCreator() == Player.m_localPlayer.GetPlayerID();
        return string.Equals(owner, ArchipelagoCoop.Slot, StringComparison.OrdinalIgnoreCase);
    }

    public static string ChestSlot(Container chest) =>
        chest.GetComponent<ZNetView>() is ZNetView nview && nview.IsValid() ? nview.GetZDO().GetString(ChestSlotKey) : "";

    // A new Archipelago Chest belongs to the slot of the player who built it (with separate co-op slots).
    public static void OnChestBuilt(Piece piece)
    {
        if (!piece.name.StartsWith(ChestPrefabName, StringComparison.Ordinal) || !ArchipelagoCoop.IsSeparate) return;
        if (piece.GetComponent<ZNetView>() is ZNetView nview && nview.IsValid() && nview.IsOwner() && !string.IsNullOrEmpty(ArchipelagoCoop.Slot))
            nview.GetZDO().Set(ChestSlotKey, ArchipelagoCoop.Slot);
    }

    // Shown when deliveries wait and the only chest nearby is someone else's.
    private static string OthersChestNearby()
    {
        if (!ArchipelagoCoop.IsSeparate) return null;
        var other = LoadedChests().FirstOrDefault(c => !IsMyChest(c));
        if (other == null) return null;
        string owner = ChestSlot(other);
        return string.IsNullOrEmpty(owner) ? "another player's" : owner + "'s";
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

    // A trap that throws must not stop item processing (bundles and later traps).
    public static void FireTrap(Player player, string trap)
    {
        try { FireTrapUnsafe(player, trap); }
        catch (Exception ex) { ValheimRandomizer.Log.LogError($"[AP] Trap '{trap}' failed: {ex}"); }
    }

    // Floor Is Lava: standing on something built (or a boat) is safe.
    private static bool OnSafeGround(Player player)
    {
        if (player.GetStandingOnShip() != null) return true;
        var ground = LastGroundRef(player);
        return ground != null && ground.GetComponentInParent<Piece>() != null;
    }

    private const float MeteorSpacingSeconds = 4f;
    private static readonly List<float> meteorShowers = new List<float>();  // end times of the showers falling now
    private static float nextMeteorTime;
    private static readonly string[] MeteorPrefabs = { "projectile_ashlandmeteor", "projectile_meteor" };

    // A meteor 12-35 m from you: a prefab that falls by itself (MeteorSmash) goes where it lands; a plain projectile
    // is launched from high above at that spot.
    private static void DropMeteor(Player player)
    {
        float angle = UnityEngine.Random.Range(0f, 360f), distance = UnityEngine.Random.Range(12f, 35f);
        var target = player.transform.position + Quaternion.Euler(0f, angle, 0f) * Vector3.forward * distance;
        target.y = ZoneSystem.instance.GetGroundHeight(target);
        foreach (var name in MeteorPrefabs)
        {
            var prefab = ZNetScene.instance ? ZNetScene.instance.GetPrefab(name) : null;
            if (!prefab) continue;
            if (prefab.GetComponent<MeteorSmash>())
            {
                UnityEngine.Object.Instantiate(prefab, target, Quaternion.identity);
                return;
            }
            if (prefab.GetComponent<Projectile>())
            {
                var start = target + Vector3.up * 80f + Quaternion.Euler(0f, angle, 0f) * Vector3.forward * 20f;
                var meteor = UnityEngine.Object.Instantiate(prefab, start, Quaternion.LookRotation(target - start));
                meteor.GetComponent<Projectile>().Setup(null, (target - start).normalized * 45f, -1f, null, null, null);  // null: keeps the meteor's own damage
                return;
            }
        }
        ValheimRandomizer.Log.LogWarning("[AP] Meteor Shower Trap: no meteor prefab found");
        meteorShowers.Clear();
    }

    private static void ForceEnvironment(string environment, float seconds)
    {
        if (EnvMan.instance != null && EnvMan.instance.m_environments.Any(env => env.m_name == environment))
        {
            // The same weather again lasts longer (up to MaxStormSeconds); other weather replaces it.
            bool same = stormEndTime > Time.time && forcedEnvironment == environment;
            EnvMan.instance.SetForceEnvironment(environment);
            forcedEnvironment = environment;
            stormEndTime = same ? Mathf.Min(stormEndTime + seconds, Time.time + MaxStormSeconds) : Time.time + seconds;
        }
        else ValheimRandomizer.Log.LogWarning($"[AP] Environment '{environment}' not found");
    }

    private static void FireTrapUnsafe(Player player, string trap)
    {
        ValheimRandomizer.Log.LogInfo("[AP] Trap: " + trap);
        switch (trap)
        {
            case "Monster Pack Trap":
                (string creature, int count) pack = BiomePacks.TryGetValue(player.GetCurrentBiome(), out var p) ? p : ("Greydwarf", 4);
                SpawnAround(player, pack.creature, pack.count, 12f);
                break;
            case "Bat Swarm Trap":
                // 2 bats early on, one more per boss defeated (6 at most): 6 at the start was a death loop.
                SpawnAround(player, "Bat", Math.Min(6, 2 + BossesDefeated()), 6f);
                break;
            case "Lightning Strike Trap":
                // The game's lightning blast is tuned for late-game armor and killed a new character outright: the
                // bolt lands a few metres away, and you take a third of your health as a lightning hit.
                var bolt = ZNetScene.instance ? ZNetScene.instance.GetPrefab("lightningAOE") : null;
                if (bolt) UnityEngine.Object.Instantiate(bolt, player.transform.position + Quaternion.Euler(0f, UnityEngine.Random.Range(0f, 360f), 0f) * Vector3.forward * 6f, Quaternion.identity);
                else ValheimRandomizer.Log.LogWarning("[AP] 'lightningAOE' not found");
                var shock = new HitData { m_point = player.transform.position, m_hitType = HitData.HitType.Undefined };
                shock.m_damage.m_lightning = player.GetMaxHealth() * 0.35f;
                player.Damage(shock);
                break;
            case "Floor Is Lava Trap":
                lavaEndTime = Mathf.Min(Mathf.Max(lavaEndTime, Time.time) + LavaSeconds, Time.time + MaxLavaSeconds);
                break;
            case "Blizzard Trap":
                ForceEnvironment("SnowStorm", BlizzardSeconds);
                break;
            case "Meteor Shower Trap":
                // The weather alone only darkens the sky: the game drops its meteors in the Ashlands only, so the
                // trap drops them itself around you while it lasts.
                ForceEnvironment("Ashlands_meteorshower", MeteorSeconds);
                // Showers stack: each one adds its own meteors for its minute.
                if (meteorShowers.Count >= MaxMeteorShowers) meteorShowers.RemoveAt(0);
                meteorShowers.Add(Time.time + MeteorSeconds);
                if (meteorShowers.Count == 1) nextMeteorTime = Time.time + 2f;
                break;
            case "Fake Item Trap":
                // Looks like a real delivery message; nothing arrives.
                player.Message(MessageHud.MessageType.TopLeft, ArchipelagoLinks.FakeItemMessage());
                return;
            case "Tar Trap":
                AddEffect(player, "Tared");
                break;
            case "Launch Trap":
                player.ForceJump(Vector3.up * 18f, true);
                break;
            case "Rust Trap":
                foreach (var item in player.GetInventory().GetEquippedItems())
                {
                    if (item.m_shared.m_useDurability) item.m_durability *= 0.5f;
                }
                break;
            case "Greydwarf Ambush Trap":
                SpawnAround(player, "Greydwarf", 3, 10f);
                break;
            case "Skeleton Ambush Trap":
                SpawnAround(player, "Skeleton", 3, 10f);
                break;
            case "Raid Trap":
                StartRaid(player);
                break;
            case "Poison Trap":
                if (AddEffect(player, "Poison") is SE_Poison poison) poison.AddDamage(player.GetMaxHealth() * 0.3f);
                break;
            case "Frost Trap":
                if (AddEffect(player, "Frost") is SE_Frost frost) frost.AddDamage(player.GetMaxHealth() * 0.1f);
                break;
            case "Butterfingers Trap":
                player.UnequipAllItems();
                break;
            case "Heavy Load Trap":
                var stone = ObjectDB.instance ? ObjectDB.instance.GetItemPrefab("Stone") : null;
                if (stone) player.GetInventory().AddItem(stone, 50);
                break;
            case "Thunderstorm Trap":
                ForceEnvironment("ThunderStorm", StormSeconds);
                break;
            case "Burning Trap":
                if (AddEffect(player, "Burning") is SE_Burning burning) burning.AddFireDamage(player.GetMaxHealth() * 0.25f);
                break;
            case "Soaked Trap":
                AddEffect(player, "Wet");
                break;
            case "Famine Trap":
                player.ClearFood();
                break;
        }
        player.Message(MessageHud.MessageType.Center, trap == "Floor Is Lava Trap"
            ? "Archipelago: The floor is lava! Get onto something you built"
            : $"Archipelago: {trap}!");
    }

    // A raid the player is ready for (by the game's own rules) in the biome they're in. Only
    // the host runs raids, so other players, or anyone no raid fits, get a bigger ambush.
    private static void StartRaid(Player player)
    {
        var events = RandEventSystem.instance;
        var zones = ZoneSystem.instance;
        if (events != null && zones != null && ZNet.instance != null && ZNet.instance.IsServer())
        {
            var biome = player.GetCurrentBiome();
            bool playerEvents = zones.GetGlobalKey(GlobalKeys.PlayerEvents);
            var candidates = events.m_events.Where(e => e.m_enabled && e.m_random && (e.m_biome & biome) != 0 &&
                (playerEvents && (e.m_altRequiredKnownItems.Count > 0 || e.m_altRequiredNotKnownItems.Count > 0 ||
                                  e.m_altNotRequiredPlayerKeys.Count > 0 || e.m_altRequiredPlayerKeysAny.Count > 0 ||
                                  e.m_altRequiredPlayerKeysAll.Count > 0)
                    ? events.PlayerIsReadyForEvent(player, e)
                    : e.m_requiredGlobalKeys.All(zones.GetGlobalKey) && !e.m_notRequiredGlobalKeys.Any(zones.GetGlobalKey)))
                .ToList();
            if (candidates.Count > 0)
            {
                var raid = candidates[UnityEngine.Random.Range(0, candidates.Count)];
                ValheimRandomizer.Log.LogInfo("[AP] Raid: " + raid.m_name);
                events.SetRandomEventByName(raid.m_name, player.transform.position);
                return;
            }
        }
        SpawnAround(player, "Greydwarf", 5, 12f);
    }

    private static void ApplyBoost(Player player, string boost)
    {
        ValheimRandomizer.Log.LogInfo("[AP] Boost: " + boost);
        switch (boost)
        {
            case "Combat Training":
                var skill = player.GetCurrentWeapon()?.m_shared?.m_skillType ?? Skills.SkillType.Unarmed;
                if (skill == Skills.SkillType.None) skill = Skills.SkillType.Unarmed;
                RaiseSkill(player, skill, 5f);
                break;
            case "Woodcutting Training":
                RaiseSkill(player, Skills.SkillType.WoodCutting, 5f);
                break;
            case "Mining Training":
                RaiseSkill(player, Skills.SkillType.Pickaxes, 5f);
                break;
            case "Rested Blessing":
                AddEffect(player, "Rested");
                break;
            case "Eikthyr's Blessing":
                AddEffect(player, "GP_Eikthyr");
                break;
            case "Moder's Blessing":
                AddEffect(player, "GP_Moder");
                break;
        }
        player.Message(MessageHud.MessageType.Center, $"Archipelago: {boost}!");
    }

    private static void RaiseSkill(Player player, Skills.SkillType skill, float levels)
    {
        // CheatRaiseSkill doesn't mark the character as cheated; it prints to the console,
        // which may not exist, after raising the level.
        try { player.GetSkills().CheatRaiseSkill(skill.ToString(), levels, true); }
        catch (NullReferenceException) { }
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
            var creature = UnityEngine.Object.Instantiate(prefab, pos, Quaternion.identity);
            // Marked on the creature itself (saved with the world), so it still leaves after a reload or an update.
            var zdo = creature.GetComponent<ZNetView>()?.GetZDO();
            zdo?.Set(TrapUntilKey, (long)(ZNet.instance.GetTimeSeconds() + TrapCreatureSeconds));
        }
    }

    // Creatures a trap summons leave after a few minutes, or when you die, so you don't respawn into them.
    private const float TrapCreatureSeconds = 180f;
    private const string TrapUntilKey = "ap_trap_until";
    private static float nextTrapCreatureCheck;

    private static void DespawnTrapCreatures(bool all)
    {
        double now = ZNet.instance.GetTimeSeconds();
        foreach (var character in Character.GetAllCharacters().ToList())
        {
            var nview = character ? character.GetComponent<ZNetView>() : null;
            if (nview == null || !nview.IsValid() || character.IsPlayer()) continue;
            long until = nview.GetZDO().GetLong(TrapUntilKey, 0L);
            if (until == 0L || (!all && now < until)) continue;
            if (!nview.IsOwner()) nview.ClaimOwnership();
            ZNetScene.instance.Destroy(character.gameObject);
        }
    }

    // /ap clear: removes the bats around you (bats never live in the open, so these came from a trap), for
    // creatures summoned before trap creatures were marked to leave.
    public static int ClearNearbyBats(Player player, float radius = 60f)
    {
        int removed = 0;
        foreach (var character in Character.GetAllCharacters().ToList())
        {
            if (!character || character.IsPlayer() || PrefabName(character.gameObject) != "Bat") continue;
            if (Vector3.Distance(character.transform.position, player.transform.position) > radius) continue;
            var nview = character.GetComponent<ZNetView>();
            if (nview == null || !nview.IsValid()) continue;
            if (!nview.IsOwner()) nview.ClaimOwnership();
            ZNetScene.instance.Destroy(character.gameObject);
            removed++;
        }
        return removed;
    }

    // How many bosses this world has seen defeated (the keys the game sets).
    private static readonly string[] BossKeys =
        { "defeated_eikthyr", "defeated_gdking", "defeated_bonemass", "defeated_dragon", "defeated_goblinking",
          "defeated_queen", "defeated_fader", "defeated_frozenking_p3" };

    private static int BossesDefeated() =>
        ZoneSystem.instance == null ? 0 : BossKeys.Count(key => ZoneSystem.instance.GetGlobalKey(key));

    private static StatusEffect AddEffect(Player player, string effectName)
    {
        int hash = effectName.GetStableHashCode();
        if (ObjectDB.instance == null || ObjectDB.instance.GetStatusEffect(hash) == null)
        {
            ValheimRandomizer.Log.LogWarning($"[AP] Status effect '{effectName}' not found");
            return null;
        }
        return player.GetSEMan().AddStatusEffect(hash, true);
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
