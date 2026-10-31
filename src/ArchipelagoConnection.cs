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
    private static bool altarKeys;  // boss_altar_keys
    private static bool resentLost;  // checks marked sent that the server lacks were resent this connection

    // progressive_items: each progressive item -> its family's researches in order; the k-th copy received
    // unlocks the k-th. Empty when the option is off (or for rooms from before it).
    private static readonly System.Collections.Generic.Dictionary<string, System.Collections.Generic.List<string>> Progressive =
        new System.Collections.Generic.Dictionary<string, System.Collections.Generic.List<string>>();

    // Set in a world once an Archipelago player has played in it while connected.
    private const string WorldKey = "ap_world";

    public static bool IsConnected => connected && session != null;
    public static string SlotName => IsConnected ? slotName : null;
    public static bool IsArchipelagoWorld => HasGlobal(WorldKey);

    // Connecting is two steps: Login waits on the server, so it runs off the main thread (the connection window
    // starts it on a task); Finish uses the result and touches the game, so it runs on the main thread.
    public static (ArchipelagoSession session, LoginResult result) Login(string host, int port, string slot, string password)
    {
        var newSession = ArchipelagoSessionFactory.CreateSession(host, port);
        return (newSession, newSession.TryConnectAndLogin("Valheim", slot, ItemsHandlingFlags.AllItems, password: password));
    }

    public static void Finish(ArchipelagoSession newSession, LoginResult result, string slot)
    {
        if (!result.Successful)
        {
            // Throw the first error up; UI handles it and shows the message
            var failure = (LoginFailure)result;
            throw new Exception(string.Join("; ", failure.Errors ?? Array.Empty<string>()));
        }
        if (session != null) Disconnect();
        session = newSession;
        resentLost = false;
        // A dropped connection isn't connected any more (checks wait in the world until the next connect).
        newSession.Socket.SocketClosed += reason => { if (session == newSession) connected = false; };

        var slotData = ((LoginSuccessful)result).SlotData;
        if (slotData != null && slotData.TryGetValue("goal_trophy", out var goal) && goal is string trophy && trophy.Length > 0)
        {
            GoalTrophy = trophy;
        }
        ArchipelagoGoal.Load(slotData);
        LoadProgressive(slotData);
        LoadFreeResearches(slotData);
        LoadSkillChecks(slotData);
        ArchipelagoLogic.Load(slotData);
        altarKeys = slotData != null && slotData.TryGetValue("boss_altar_keys", out var keys) && keys is bool on && on;
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

    // Once per connection: checks marked sent (ap_sent) that the server still lists as missing were sent into a
    // connection that had dropped; send them again.
    private static void ResendLost()
    {
        if (resentLost) return;
        resentLost = true;
        var lost = session.Locations.AllMissingLocations
            .Where(id => HasGlobal(Key("ap_sent:", session.Locations.GetLocationNameFromId(id, "Valheim") ?? ""))).ToArray();
        if (lost.Length == 0) return;
        ValheimRandomizer.Log.LogInfo($"[AP] Resending {lost.Length} checks the server didn't get");
        session.Locations.CompleteLocationChecks(lost);
    }

    // Disconnects from the room (the connection window's Disconnect button). Checks done meanwhile wait in the
    // world as pending keys and are sent on the next connect.
    public static void Disconnect()
    {
        if (session != null)
        {
            session.Items.ItemReceived -= OnApItemReceived;
            try { session.Socket?.DisconnectAsync(); } catch (Exception) { }
        }
        ArchipelagoLinks.OnDisconnected();
        session = null;
        connected = false;
        ValheimRandomizer.Log.LogInfo("[AP] Disconnected");
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

    public static System.Collections.Generic.IEnumerable<string> ProgressiveNames => Progressive.Keys;

    // Researches known from the start in this seed (everything but equipment, unless item_sanity is on): unlocked
    // once the world is loaded, and their Research Bench recipes hidden. Rooms from before the option send none.
    private static readonly System.Collections.Generic.List<string> FreeResearchIds = new System.Collections.Generic.List<string>();

    private static void LoadFreeResearches(System.Collections.Generic.Dictionary<string, object> slotData)
    {
        FreeResearchIds.Clear();
        if (slotData != null && slotData.TryGetValue("free_researches", out var raw) && raw != null)
        {
            try
            {
                var names = raw as Newtonsoft.Json.Linq.JArray ?? Newtonsoft.Json.Linq.JArray.FromObject(raw);
                foreach (var name in names.Values<string>())
                {
                    if (ValheimRandomizer.archipelagoToResearch.TryGetValue(name, out var id)) FreeResearchIds.Add(id);
                    else ValheimRandomizer.Log.LogWarning($"[AP] Unknown free research '{name}'");
                }
            }
            catch (Exception ex)
            {
                ValheimRandomizer.Log.LogWarning("[AP] Couldn't read free researches from the slot data: " + ex.Message);
            }
        }
        // Researches whose item is in the seed but whose check isn't: their recipes are hidden too, not unlocked.
        var hidden = new System.Collections.Generic.HashSet<string>(FreeResearchIds);
        if (slotData != null && slotData.TryGetValue("item_only_researches", out var itemOnly) && itemOnly != null)
        {
            try
            {
                var names = itemOnly as Newtonsoft.Json.Linq.JArray ?? Newtonsoft.Json.Linq.JArray.FromObject(itemOnly);
                foreach (var name in names.Values<string>())
                    if (ValheimRandomizer.archipelagoToResearch.TryGetValue(name, out var id)) hidden.Add(id);
            }
            catch (Exception ex)
            {
                ValheimRandomizer.Log.LogWarning("[AP] Couldn't read item-only researches from the slot data: " + ex.Message);
            }
        }
        RandomizerUtils.SetFreeResearches(hidden);
        ValheimRandomizer.Log.LogInfo(FreeResearchIds.Count > 0
            ? $"[AP] {FreeResearchIds.Count} researches known from the start (only equipment is locked)"
            : "[AP] Every research is locked (item-sanity)");
    }

    // Which skill levels are checks in this seed (skill_checks, skill_check_spacing). checks.tsv has every level
    // of every skill; sending the ones the seed doesn't have would only fill the world with keys. Kept in the
    // world ("ap_skill_checks <max>x<step>") for co-op players who aren't connected.
    private const string SkillChecksKey = "ap_skill_checks";
    private static readonly int[] SkillSteps = { 10, 20, 25, 1, 2, 5 };  // skill_check_spacing's values, in order
    private static int skillMax = -1, skillStep = 10;

    private static void LoadSkillChecks(System.Collections.Generic.Dictionary<string, object> slotData)
    {
        skillMax = -1;
        try
        {
            if (slotData != null && slotData.TryGetValue("options", out var raw) && raw != null)
            {
                var options = raw as Newtonsoft.Json.Linq.JObject ?? Newtonsoft.Json.Linq.JObject.FromObject(raw);
                int spacing = options["skill_check_spacing"]?.ToObject<int>() ?? 0;
                skillStep = spacing >= 0 && spacing < SkillSteps.Length ? SkillSteps[spacing] : 10;
                skillMax = options["skill_checks"]?.ToObject<int>() ?? -1;
            }
        }
        catch (Exception ex)
        {
            ValheimRandomizer.Log.LogWarning("[AP] Couldn't read the skill check options from the slot data: " + ex.Message);
        }
    }

    public static bool IsSkillLevelChecked(int level)
    {
        int max = skillMax, step = skillStep;
        if ((!connected || max < 0) && WorldLoaded() &&
            ZoneSystem.instance.GetGlobalKey(ArchipelagoCoop.Scoped(SkillChecksKey), out var saved))
        {
            var parts = saved.Split('x');
            if (parts.Length == 2 && int.TryParse(parts[0], out var m) && int.TryParse(parts[1], out var s) && s > 0)
            {
                max = m;
                step = s;
            }
        }
        // Rooms that don't say: the levels skill checks had before every level could be one.
        if (max < 0) return level % 10 == 0 || level % 25 == 0;
        return level <= max && level % step == 0;
    }

    private static void UnlockFreeResearches()
    {
        foreach (var id in FreeResearchIds)
            if (!ValheimRandomizer.IsResearchUnlocked(id)) ValheimRandomizer.DoUnlockResearch(id);
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
            else if (ArchipelagoAltars.IsAltarKey(name))
            {
                ArchipelagoAltars.OnReceived(name);
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
        if (!connected || session == null || !session.Socket.Connected) return;
        if (!WorldLoaded()) return;
        // The world's co-op mode has to be known before any per-slot key is written (see ArchipelagoCoop.Ready).
        if (!ArchipelagoCoop.Ready) return;
        ArchipelagoCoop.Replay();
        if (!HasGlobal(WorldKey)) SetGlobal(WorldKey);
        ArchipelagoAltars.OnConnected(altarKeys, session.RoomState.Seed);
        ResendLost();
        UnlockFreeResearches();
        if (skillMax >= 0) SetGlobal(ArchipelagoCoop.Scoped($"{SkillChecksKey} {skillMax}x{skillStep}"));
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

    // Whether this slot's goal has been sent from this world: after that, traps no longer fire (ArchipelagoExtras).
    public static bool GoalDone => WorldLoaded() && HasGlobal(ArchipelagoCoop.Scoped("ap_goal_sent"));

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
