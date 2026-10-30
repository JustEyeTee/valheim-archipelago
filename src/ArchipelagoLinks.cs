using System;
using System.Collections.Concurrent;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using Archipelago.MultiClient.Net;
using Archipelago.MultiClient.Net.BounceFeatures.DeathLink;
using Archipelago.MultiClient.Net.Enums;
using Archipelago.MultiClient.Net.Models;
using Archipelago.MultiClient.Net.Packets;
using HarmonyLib;
using Jotunn.Entities;
using Newtonsoft.Json.Linq;
using UnityEngine;

// Features shared with the other games in the multiworld: Death Link, Trap Link and Energy
// Link. Packets and data storage replies arrive on the websocket thread, so everything that
// touches the game is queued and handled in Tick on the main thread.
public static class ArchipelagoLinks
{
    // Energy Link pool (shared by the whole team, in joules) <-> Coins.
    public const long JoulesPerCoin = 1_000_000;

    private static ArchipelagoSession session;
    private static string slot;
    private static DeathLinkService deathLinkService;
    private static bool deathLink;
    private static string deathLinkMode = "kill";
    private static int deathLinkAmnesty;
    private static int deathsSinceSent;
    private static float ignoreOwnDeathUntil;
    private static bool trapLink;

    private static readonly ConcurrentQueue<DeathLink> incomingDeaths = new ConcurrentQueue<DeathLink>();
    private static readonly ConcurrentQueue<int> incomingCoins = new ConcurrentQueue<int>();
    private static readonly ConcurrentQueue<string> messages = new ConcurrentQueue<string>();

    private static readonly AccessTools.FieldRef<Character, HitData> LastHitRef =
        AccessTools.FieldRefAccess<Character, HitData>("m_lastHit");

    // Trap names other games send over Trap Link -> the closest Valheim trap. Our own trap
    // names map to themselves; anything not listed is ignored.
    private static readonly Dictionary<string, string> TrapLinkAliases = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase)
    {
        { "Ice Trap", "Frost Trap" }, { "Freeze Trap", "Frost Trap" }, { "Frozen Trap", "Frost Trap" },
        { "Chill Trap", "Frost Trap" }, { "Slow Trap", "Tar Trap" }, { "Slowness Trap", "Tar Trap" },
        { "Stun Trap", "Frost Trap" }, { "Paralyze Trap", "Frost Trap" },
        { "Poison Trap", "Poison Trap" }, { "Poison Mushroom", "Poison Trap" },
        { "Fire Trap", "Burning Trap" }, { "Burn Trap", "Burning Trap" }, { "Bomb", "Burning Trap" },
        { "Bomb Trap", "Burning Trap" }, { "Explosion Trap", "Burning Trap" }, { "Damage Trap", "Burning Trap" },
        { "Bee Trap", "Greydwarf Ambush Trap" }, { "Spring Trap", "Greydwarf Ambush Trap" },
        { "Monster Trap", "Greydwarf Ambush Trap" }, { "Enemy Trap", "Greydwarf Ambush Trap" },
        { "Spawn Trap", "Greydwarf Ambush Trap" }, { "Ambush Trap", "Greydwarf Ambush Trap" },
        { "Disarm Trap", "Butterfingers Trap" }, { "Drop Trap", "Butterfingers Trap" }, { "Fumble Trap", "Butterfingers Trap" },
        { "Thunder Trap", "Thunderstorm Trap" }, { "Lightning Trap", "Lightning Strike Trap" },
        { "Storm Trap", "Thunderstorm Trap" }, { "Rain Trap", "Thunderstorm Trap" }, { "Weather Trap", "Thunderstorm Trap" },
        { "Hunger Trap", "Famine Trap" }, { "Starvation Trap", "Famine Trap" }, { "Food Trap", "Famine Trap" },
        { "Heavy Trap", "Heavy Load Trap" }, { "Weight Trap", "Heavy Load Trap" }, { "Gravity Trap", "Heavy Load Trap" },
        { "Water Trap", "Soaked Trap" }, { "Wet Trap", "Soaked Trap" }, { "Soak Trap", "Soaked Trap" },
        { "Lava Trap", "Floor Is Lava Trap" }, { "Floor Is Lava", "Floor Is Lava Trap" },
        { "Bat Trap", "Bat Swarm Trap" }, { "Swarm Trap", "Bat Swarm Trap" },
        { "Snow Trap", "Blizzard Trap" }, { "Blizzard", "Blizzard Trap" }, { "Cold Trap", "Blizzard Trap" },
        { "Sticky Trap", "Tar Trap" }, { "Slime Trap", "Tar Trap" },
        { "Launch Trap", "Launch Trap" }, { "Jump Trap", "Launch Trap" }, { "Bounce Trap", "Launch Trap" },
        { "Spring Launch Trap", "Launch Trap" },
        { "Rust Trap", "Rust Trap" }, { "Break Trap", "Rust Trap" }, { "Durability Trap", "Rust Trap" },
        { "Horde Trap", "Monster Pack Trap" }, { "Army Trap", "Monster Pack Trap" },
    };

    static ArchipelagoLinks()
    {
        foreach (var trap in ArchipelagoExtras.TrapNames) TrapLinkAliases[trap] = trap;
    }

    public static bool Connected => session != null;

    public static void OnConnected(ArchipelagoSession newSession, string slotName, Dictionary<string, object> slotData)
    {
        session = newSession;
        slot = slotName;
        deathsSinceSent = 0;
        deathLinkMode = slotData != null && slotData.TryGetValue("death_link_mode", out var mode) && mode is string m ? m : "kill";
        deathLinkAmnesty = GetInt(slotData, "death_link_amnesty");
        trapLink = GetInt(slotData, "trap_link") != 0;

        deathLinkService = session.CreateDeathLinkService();
        deathLinkService.OnDeathLinkReceived += dl => incomingDeaths.Enqueue(dl);
        SetDeathLink(GetInt(slotData, "death_link") != 0);
        if (trapLink) AddTag("TrapLink");
        session.Socket.PacketReceived += OnPacketReceived;

        ValheimRandomizer.Log.LogInfo($"[AP] Death Link: {(deathLink ? deathLinkMode : "off")}, amnesty {deathLinkAmnesty}; Trap Link: {(trapLink ? "on" : "off")}");
    }

    // Slot data booleans and numbers arrive as bool or Int64.
    private static int GetInt(Dictionary<string, object> slotData, string key)
    {
        if (slotData == null || !slotData.TryGetValue(key, out var value) || value == null) return 0;
        try { return value is bool b ? (b ? 1 : 0) : Convert.ToInt32(value, CultureInfo.InvariantCulture); }
        catch (Exception) { return 0; }
    }

    private static void AddTag(string tag)
    {
        var tags = session.ConnectionInfo.Tags ?? Array.Empty<string>();
        if (!tags.Contains(tag)) session.ConnectionInfo.UpdateConnectionOptions(tags.Concat(new[] { tag }).ToArray());
    }

    public static void SetDeathLink(bool on)
    {
        deathLink = on;
        if (deathLinkService == null) return;
        if (on) deathLinkService.EnableDeathLink();
        else deathLinkService.DisableDeathLink();
    }

    // ---------- Death Link ----------

    public static void OnLocalPlayerDied(Player player)
    {
        if (!deathLink || deathLinkService == null || Time.time < ignoreOwnDeathUntil) return;
        if (++deathsSinceSent <= deathLinkAmnesty)
        {
            int left = deathLinkAmnesty - deathsSinceSent + 1;
            messages.Enqueue($"Death Link: forgiven ({left} more {(left == 1 ? "death sends" : "deaths send")} one)");
            return;
        }
        deathsSinceSent = 0;

        string cause;
        var hit = LastHitRef(player);
        var attacker = hit?.GetAttacker();
        if (attacker != null && attacker != player)
            cause = $"{slot} was killed by {Localization.instance.Localize(attacker.m_name)} in Valheim";
        else if (hit != null && hit.m_hitType != HitData.HitType.Undefined)
            cause = $"{slot} died ({hit.m_hitType}) in Valheim";
        else
            cause = $"{slot} died in Valheim";
        deathLinkService.SendDeathLink(new DeathLink(slot, cause));
        messages.Enqueue("Death Link sent");
    }

    private static void ReceiveDeath(Player player, DeathLink dl)
    {
        var text = string.IsNullOrEmpty(dl.Cause) ? $"{dl.Source} died" : dl.Cause;
        ValheimRandomizer.Log.LogInfo($"[AP] Death Link received ({deathLinkMode}): {text}");
        player.Message(MessageHud.MessageType.Center, "Death Link: " + text);
        switch (deathLinkMode)
        {
            case "wounded":
                player.SetHealth(1f);
                break;
            case "trap":
                ArchipelagoExtras.QueueTrap(ArchipelagoExtras.TrapNames[UnityEngine.Random.Range(0, ArchipelagoExtras.TrapNames.Length)]);
                break;
            default:
                // Same as the game's "die" console command. This death isn't sent back out.
                ignoreOwnDeathUntil = Time.time + 10f;
                var hit = new HitData { m_hitType = HitData.HitType.Self };
                hit.m_damage.m_damage = 99999f;
                player.Damage(hit);
                break;
        }
    }

    // ---------- Trap Link ----------

    public static void SendTrapLink(string trap)
    {
        if (!trapLink || session == null) return;
        session.Socket.SendPacketAsync(new BouncePacket
        {
            Tags = new List<string> { "TrapLink" },
            Data = new Dictionary<string, JToken>
            {
                { "time", DateTimeOffset.UtcNow.ToUnixTimeMilliseconds() / 1000.0 },
                { "source", slot },
                { "trap_name", trap },
            },
        });
    }

    private static void OnPacketReceived(ArchipelagoPacketBase packet)
    {
        if (!trapLink || !(packet is BouncedPacket bounced) || bounced.Tags == null || !bounced.Tags.Contains("TrapLink")) return;
        if (bounced.Data == null || !bounced.Data.TryGetValue("trap_name", out var trapToken)) return;
        var source = bounced.Data.TryGetValue("source", out var s) ? s.ToString() : "?";
        if (source == slot) return;
        var trapName = trapToken.ToString();
        if (TrapLinkAliases.TryGetValue(trapName, out var trap))
        {
            ArchipelagoExtras.QueueTrap(trap);
            messages.Enqueue($"Trap Link: {trapName} from {source}");
        }
    }

    // ---------- Energy Link ----------

    private static string EnergyKey => $"EnergyLink{session.ConnectionInfo.Team}";

    private static double ToDouble(JToken token)
        => token == null || token.Type == JTokenType.Null ? 0 : token.ToObject<double>();

    public static string FormatEnergy(double joules)
    {
        string[] units = { "J", "kJ", "MJ", "GJ", "TJ", "PJ" };
        int i = 0;
        while (Math.Abs(joules) >= 1000 && i < units.Length - 1) { joules /= 1000; i++; }
        return $"{joules:0.##} {units[i]}";
    }

    public static void ShowEnergy()
    {
        session.DataStorage[Scope.Global, EnergyKey].GetAsync().ContinueWith(t =>
        {
            double pool = t.IsFaulted ? 0 : ToDouble(t.Result);
            messages.Enqueue($"Energy Link pool: {FormatEnergy(pool)} (worth {Math.Floor(pool / JoulesPerCoin):0} Coins)");
        });
    }

    public static string Deposit(Player player, int coins)
    {
        var inventory = player.GetInventory();
        int have = inventory.CountItems("$item_coins");
        coins = Math.Min(coins, have);
        if (coins <= 0) return "You have no Coins to deposit.";
        inventory.RemoveItem("$item_coins", coins);
        session.DataStorage[Scope.Global, EnergyKey] += (long)coins * JoulesPerCoin;
        return $"Deposited {coins} Coins ({FormatEnergy((double)coins * JoulesPerCoin)}) into Energy Link.";
    }

    public static string Withdraw(Player player, int coins)
    {
        var prefab = ObjectDB.instance ? ObjectDB.instance.GetItemPrefab("Coins") : null;
        if (!prefab || coins <= 0) return "Nothing to withdraw.";
        if (!player.GetInventory().CanAddItem(prefab, coins)) return "Not enough room in your inventory for that many Coins.";

        long want = coins * JoulesPerCoin;
        session.DataStorage[Scope.Global, EnergyKey] = session.DataStorage[Scope.Global, EnergyKey] - want
            + Operation.Max(0)
            + Callback.Add((original, value, _) =>
            {
                double taken = ToDouble(original) - ToDouble(value);
                int got = (int)Math.Floor(taken / JoulesPerCoin);
                double change = taken - (double)got * JoulesPerCoin;
                // Part of a coin's worth goes back into the pool.
                if (change > 0) session.DataStorage[Scope.Global, EnergyKey] += change;
                if (got > 0) incomingCoins.Enqueue(got);
                messages.Enqueue(got > 0 ? $"Withdrew {got} Coins from Energy Link." : "The Energy Link pool is empty.");
            });
        return "Withdrawing...";
    }

    // ---------- Main thread ----------

    public static void Tick(Player player)
    {
        while (messages.TryDequeue(out var message))
        {
            player.Message(MessageHud.MessageType.TopLeft, message);
            Chat.instance?.AddString("[AP] " + message);
        }

        while (incomingCoins.TryDequeue(out var coins))
        {
            var prefab = ObjectDB.instance ? ObjectDB.instance.GetItemPrefab("Coins") : null;
            if (prefab && player.GetInventory().AddItem(prefab, coins)) continue;
            // No room after all: put them back.
            if (session != null) session.DataStorage[Scope.Global, EnergyKey] += (long)coins * JoulesPerCoin;
            player.Message(MessageHud.MessageType.TopLeft, "No room for the Coins; they went back into Energy Link.");
        }

        if (!player.IsDead() && !player.IsTeleporting() && !player.InIntro() && !player.InCutscene() &&
            incomingDeaths.TryDequeue(out var dl))
        {
            ReceiveDeath(player, dl);
        }
    }

    public static string Status()
    {
        if (session == null) return "Not connected to Archipelago.";
        return $"Connected as {slot} (team {session.ConnectionInfo.Team}). " +
               $"Death Link: {(deathLink ? $"{deathLinkMode}, amnesty {deathLinkAmnesty}" : "off")}. " +
               $"Trap Link: {(trapLink ? "on" : "off")}.";
    }
}

// Chat command (type /ap in chat): /ap status | energy | deposit <coins> | withdraw <coins> | deathlink on|off
public class ArchipelagoCommand : ConsoleCommand
{
    public override string Name => "ap";
    public override string Help => "Archipelago: status, energy, deposit <coins>, withdraw <coins>, deathlink on|off";

    public override void Run(string[] args, Terminal context)
    {
        string Reply(string text) { context?.AddString("[AP] " + text); return text; }
        var sub = args.Length > 0 ? args[0].ToLowerInvariant() : "status";
        if (sub == "status" || sub == "help")
        {
            Reply(ArchipelagoLinks.Status());
            Reply("Commands: /ap status, /ap energy, /ap deposit <coins>, /ap withdraw <coins>, /ap deathlink on|off");
            return;
        }
        if (!ArchipelagoLinks.Connected) { Reply("Not connected to Archipelago."); return; }
        var player = Player.m_localPlayer;
        int amount = args.Length > 1 && int.TryParse(args[1], out var n) ? n : 0;
        switch (sub)
        {
            case "energy":
                ArchipelagoLinks.ShowEnergy();
                break;
            case "deposit":
                if (player == null || amount <= 0) { Reply("Usage: /ap deposit <coins>"); return; }
                Reply(ArchipelagoLinks.Deposit(player, amount));
                break;
            case "withdraw":
                if (player == null || amount <= 0) { Reply("Usage: /ap withdraw <coins>"); return; }
                Reply(ArchipelagoLinks.Withdraw(player, amount));
                break;
            case "deathlink":
                if (args.Length < 2 || (args[1] != "on" && args[1] != "off")) { Reply("Usage: /ap deathlink on|off"); return; }
                ArchipelagoLinks.SetDeathLink(args[1] == "on");
                Reply("Death Link " + args[1] + " for this session.");
                break;
            default:
                Reply("Unknown command. " + Help);
                break;
        }
    }
}
