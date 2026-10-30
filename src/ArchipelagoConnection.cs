using System;
using System.Linq;
using UnityEngine.Events;
using Archipelago.MultiClient.Net;
using Archipelago.MultiClient.Net.Enums;
using Archipelago.MultiClient.Net.Models;
using Archipelago.MultiClient.Net.Helpers;

internal static class ArchipelagoConnection
{
    private static ArchipelagoSession session;
    private static bool connected;

    // Trophy that wins the game, from the room's slot data. Rooms generated before the
    // goal option existed send none, and their goal was always Fader.
    public static string GoalTrophy { get; private set; } = "TrophyFader";

    private static string slotName;

    // progressive_items: each progressive item -> its family's researches in order; the k-th copy received
    // unlocks the k-th. Empty when the option is off (or for rooms from before it).
    private static readonly System.Collections.Generic.Dictionary<string, System.Collections.Generic.List<string>> Progressive =
        new System.Collections.Generic.Dictionary<string, System.Collections.Generic.List<string>>();

    // Set in a world once an Archipelago player has played in it while connected.
    private const string WorldKey = "ap_world";

    public static bool IsConnected => connected && session != null;
    public static string SlotName => IsConnected ? slotName : null;
    public static bool IsArchipelagoWorld => HasGlobal(WorldKey);

    public static void Connect(string host, int port, string slot, string password)
    {
        // Dispose previous session if any
        session?.Socket?.DisconnectAsync();
        session = null;
        connected = false;

        // Create & login
        session = ArchipelagoSessionFactory.CreateSession(host, port);
        var result = session.TryConnectAndLogin("Valheim", slot,
            ItemsHandlingFlags.AllItems, password: password);

        if (!result.Successful)
        {
            // Throw the first error up; UI handles it and shows the message
            var failure = (LoginFailure)result;
            throw new Exception(string.Join("; ", failure.Errors ?? Array.Empty<string>()));
        }

        var slotData = ((LoginSuccessful)result).SlotData;
        if (slotData != null && slotData.TryGetValue("goal_trophy", out var goal) && goal is string trophy && trophy.Length > 0)
        {
            GoalTrophy = trophy;
        }
        ArchipelagoGoal.Load(slotData);
        LoadProgressive(slotData);
        ArchipelagoLogic.Load(slotData);
        if (!ArchipelagoGoal.HasConditions) ValheimRandomizer.Log.LogInfo("[AP] Goal: pick up " + GoalTrophy);

        // Slot data numbers arrive as Int64; rooms from before this option use full costs.
        int costPercent = 100;
        if (slotData != null && slotData.TryGetValue("research_cost_percent", out var cost) && cost != null)
        {
            try { costPercent = Convert.ToInt32(cost); } catch (Exception) { }
        }
        RandomizerUtils.ApplyResearchCostPercent(costPercent);

        slotName = slot;
        ArchipelagoLinks.OnConnected(session, slot, slotData);

        // Hook item reception
        session.Items.ItemReceived += OnApItemReceived;

        connected = true;
    }

    // Global keys are "key value" pairs split at the first space, so a location name with
    // spaces can't be a key as it is: "ap_sent:clubs tier 1" would be stored as key
    // "ap_sent:clubs" (lookups of the whole name never match, and "Clubs Tier 2" would replace
    // it). Keys use the name lowercased with spaces as underscores instead.
    private static string Key(string prefix, string locationName)
        => ArchipelagoCoop.Scoped(prefix + locationName.ToLowerInvariant().Replace(' ', '_'));

    public static bool IsLocationDone(string locationName)
        => HasGlobal(Key("ap_sent:", locationName)) || HasGlobal(Key("ap_pending:", locationName));

    // For checks that are re-detected over and over (biomes, inventory, exploration): only
    // queue them the first time.
    public static void SendLocationOnce(string locationName)
    {
        if (!WorldLoaded() || IsLocationDone(locationName)) return;
        SendLocation(locationName);
    }

    public static void SendLocation(string locationName)
    {
        if (!ValheimRandomizer.Randomized) return;
        if (!WorldLoaded()) return;
        if (string.IsNullOrWhiteSpace(locationName)) return;

        ArchipelagoCoop.WhenReady(() =>
        {
            if (HasGlobal(Key("ap_sent:", locationName))) return;
            ValheimRandomizer.Log.LogInfo("Queue location " + locationName);
            SetGlobal(Key("ap_pending:", locationName));
            TryFlushPendingLocations();
        });
    }

    // Runs on the websocket thread, where Unity and game calls aren't safe. Received items are
    // applied on the main thread by TryGetAllItems (every couple of seconds), so just drain.
    private static void OnApItemReceived(ReceivedItemsHelper helper)
    {
        while (helper.DequeueItem() != null) { }
    }

    private static void LoadProgressive(System.Collections.Generic.Dictionary<string, object> slotData)
    {
        Progressive.Clear();
        if (slotData == null || !slotData.TryGetValue("progressive", out var raw) || raw == null) return;
        try
        {
            var families = raw as Newtonsoft.Json.Linq.JObject ?? Newtonsoft.Json.Linq.JObject.FromObject(raw);
            foreach (var family in families.Properties())
            {
                Progressive[family.Name] = family.Value.Values<string>().ToList();
            }
        }
        catch (Exception ex)
        {
            ValheimRandomizer.Log.LogWarning("[AP] Couldn't read progressive items from the slot data: " + ex.Message);
        }
        if (Progressive.Count > 0) ValheimRandomizer.Log.LogInfo($"[AP] Progressive items: {Progressive.Count} families");
    }

    // Items already applied to the loaded world (unlocking a research sets a world key); reset when another
    // world is loaded, or another slot connects, which need them applied too.
    static System.Collections.Generic.List<string> gottenItems = new System.Collections.Generic.List<string>();
    static string gottenFor;
    static void TryGetAllItems()
    {
        if (!WorldLoaded()) return;
        var target = $"{ZNet.instance.GetWorldUID()}:{slotName}";  // with separate co-op slots, also per slot
        if (target != gottenFor)
        {
            gottenFor = target;
            gottenItems.Clear();
        }

        foreach (var item in session.Items.AllItemsReceived)
        {
            var name = item.ItemName;
            if (string.IsNullOrEmpty(name)) continue;

            if (Progressive.ContainsKey(name)) continue; // counted below
            if (gottenItems.Contains(name)) continue;
            gottenItems.Add(name);

            if (ValheimRandomizer.archipelagoToResearch.TryGetValue(name, out var researchId))
            {
                ValheimRandomizer.DoUnlockResearch(researchId);
            }
            else if (!ArchipelagoExtras.IsExtraItem(name))
            {
                ValheimRandomizer.Log.LogWarning(
                    $"Received AP item '{name}' but no research mapping was found.");
            }
        }

        // Progressive items: unlock as many of each family's researches as copies received (unlocking is a
        // world key, so doing it again is harmless).
        foreach (var family in Progressive)
        {
            int copies = session.Items.AllItemsReceived.Count(item => item.ItemName == family.Key);
            foreach (var research in family.Value.Take(copies))
            {
                if (gottenItems.Contains(research)) continue;
                gottenItems.Add(research);
                if (ValheimRandomizer.archipelagoToResearch.TryGetValue(research, out var researchId))
                {
                    ValheimRandomizer.DoUnlockResearch(researchId);
                }
                else
                {
                    ValheimRandomizer.Log.LogWarning($"Progressive item '{family.Key}': no research '{research}'.");
                }
            }
        }

        var progressKey = $"ap:{session.RoomState.Seed}:{slotName}:{ZNet.instance.GetWorldUID()}";
        ArchipelagoExtras.ProcessItems(session.Items.AllItemsReceived.Select(i => i.ItemName), progressKey);
    }

    public static void TryFlushPendingLocations()
    {
        if (!connected || session == null) return;
        if (!WorldLoaded()) return;
        // The world's co-op mode has to be known before any per-slot key is written (see ArchipelagoCoop.Ready).
        if (!ArchipelagoCoop.Ready) return;
        ArchipelagoCoop.Replay();
        if (!HasGlobal(WorldKey)) SetGlobal(WorldKey);
        TryGetAllItems();
        if (HasGlobal(ArchipelagoCoop.Scoped("ap_goal_pending"))) CompleteGame();
        ArchipelagoGoal.Check(ReceivedCount);

        foreach (var key in ZoneSystem.instance.GetGlobalKeys())
        {
            if (!key.StartsWith("ap_pending:", StringComparison.Ordinal)) continue;
            // Separate co-op slots: only this player's checks.
            if (!ArchipelagoCoop.IsMine(key, out var unscoped)) continue;

            // Pending keys from older builds hold the lowercased name with its spaces.
            var pendingName = unscoped.Substring("ap_pending:".Length);
            if (string.IsNullOrWhiteSpace(pendingName)) continue;
            var locationName = ValheimRandomizer.archipelagoToResearch.Keys.Concat(ArchipelagoExtras.LocationNames)
                .FirstOrDefault(name => name.ToLowerInvariant().Replace(' ', '_') == pendingName || name.ToLower() == pendingName) ?? pendingName;

            try
            {
                var id = session.Locations.GetLocationIdFromName("Valheim", locationName);
                if (id >= 0 && session.Locations.AllLocations.Contains(id))
                {
                    ValheimRandomizer.Log.LogInfo("Unlock location " + locationName);
                    session.Locations.CompleteLocationChecks(id);
                }
                else
                {
                    // An option left this check out of the seed (or it's past the goal).
                    ValheimRandomizer.Log.LogInfo($"Location '{locationName}' is not in this seed; skipping it.");
                }

                // NEW: mark success so we don't resend forever
                SetGlobal(Key("ap_sent:", locationName));
                RemoveGlobal(key);
            }
            catch (Exception ex)
            {
                // NEW: make the problem visible
                ValheimRandomizer.Log.LogWarning(
                    $"AP location lookup failed for '{locationName}'. " +
                    $"Check the exact name in your AP world. Error: {ex.Message}");
                // keep pending; will retry next tick/reconnect
            }
        }
    }

    // How many of an item the slot has received (Relic Hunt counts its relics).
    public static int ReceivedCount(string itemName)
        => session == null ? 0 : session.Items.AllItemsReceived.Count(item => item.ItemName == itemName);

    private static bool WorldLoaded()
        => ZoneSystem.instance != null && Player.m_localPlayer != null; // simple & reliable

    private static bool HasGlobal(string k)
        => ZoneSystem.instance != null && ZoneSystem.instance.GetGlobalKey(k);

    private static void SetGlobal(string k)
    {
        if (ZoneSystem.instance == null) return;
        ZoneSystem.instance.SetGlobalKey(k);
    }

    private static void RemoveGlobal(string k)
    {
        if (ZoneSystem.instance == null) return;
        ZoneSystem.instance.RemoveGlobalKey(k);
    }

    // Called once the goal is done (every goal condition, or for older rooms, the goal trophy in the
    // inventory). Sends the goal once per world; if not connected yet, it is remembered in the world and
    // sent by TryFlushPendingLocations.
    public static void CompleteGame()
    {
        if (!WorldLoaded() || !ArchipelagoCoop.Ready || HasGlobal(ArchipelagoCoop.Scoped("ap_goal_sent"))) return;
        SetGlobal(ArchipelagoCoop.Scoped("ap_goal_pending"));
        if (!connected || session == null) return;

        session.SetGoalAchieved();
        SetGlobal(ArchipelagoCoop.Scoped("ap_goal_sent"));
        ValheimRandomizer.Log.LogInfo("[AP] Goal complete");
        Player.m_localPlayer?.Message(MessageHud.MessageType.Center, "Archipelago: goal complete!");
    }
}
