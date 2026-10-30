using System;
using System.Collections.Concurrent;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using Archipelago.MultiClient.Net;
using Archipelago.MultiClient.Net.BounceFeatures.DeathLink;
using Archipelago.MultiClient.Net.Enums;
using Archipelago.MultiClient.Net.MessageLog.Messages;
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
    // Energy Link withdrawals waiting for the server's reply (by the id sent with the request).
    private static readonly ConcurrentDictionary<string, int> pendingWithdrawals = new ConcurrentDictionary<string, int>();
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

    public static void OnDisconnected()
    {
        if (session != null)
        {
            session.Socket.PacketReceived -= OnPacketReceived;
            session.MessageLog.OnMessageReceived -= OnMessageReceived;
        }
        session = null;
        deathLinkService = null;
    }

    public static void OnConnected(ArchipelagoSession newSession, string slotName, Dictionary<string, object> slotData)
    {
        session = newSession;
        slot = slotName;
        deathsSinceSent = 0;
        deathLinkMode = slotData != null && slotData.TryGetValue("death_link_mode", out var mode) && mode is string m ? m : "kill";
        deathLinkAmnesty = GetInt(slotData, "death_link_amnesty");
        trapLink = GetInt(slotData, "trap_link") != 0;
        hintShopPrice = GetInt(slotData, "hint_shop_price");
        shopPending = false;

        deathLinkService = session.CreateDeathLinkService();
        deathLinkService.OnDeathLinkReceived += dl => incomingDeaths.Enqueue(dl);
        SetDeathLink(GetInt(slotData, "death_link") != 0);
        if (trapLink) AddTag("TrapLink");
        session.Socket.PacketReceived += OnPacketReceived;
        session.MessageLog.OnMessageReceived += OnMessageReceived;
        // Data storage operations on a key that doesn't exist yet fail on the server (it adds to
        // a null default), so make sure the team's pool exists; this never changes a set value.
        session.DataStorage[Scope.Global, EnergyKey].Initialize(0);

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

    // ---------- Item feed ----------

    private static void OnMessageReceived(LogMessage message)
    {
        switch (message)
        {
            case HintItemSendLogMessage hint when hint.IsRelatedToActivePlayer:
                if (ValheimRandomizer.showItemFeed.Value) messages.Enqueue("Hint: " + hint);
                break;
            case ItemSendLogMessage send when send.IsRelatedToActivePlayer:
                if (!ValheimRandomizer.showItemFeed.Value) break;
                var item = send.Item.ItemDisplayName ?? send.Item.ItemName;
                if (send.IsSenderTheActivePlayer && send.IsReceiverTheActivePlayer)
                    messages.Enqueue($"Found your own {item}");
                else if (send.IsReceiverTheActivePlayer)
                    messages.Enqueue($"Received {item} from {send.Sender.Alias}");
                else
                    messages.Enqueue($"Sent {item} to {send.Receiver.Alias}");
                break;
            case ChatLogMessage chat:
                // Runs on the network thread: the session may have just been dropped (Disconnect).
                var current = session;
                if (current != null && ValheimRandomizer.showChat.Value && chat.Player.Slot != current.ConnectionInfo.Slot)
                    messages.Enqueue(chat.ToString());
                break;
            default:
                // Replies to /ap hint and /ap say commands, and server announcements.
                var type = message.GetType().Name;
                if (type == "CommandResultLogMessage" || type == "ServerChatLogMessage") messages.Enqueue(message.ToString());
                break;
        }
    }

    private static readonly string[] FakeItems =
        { "Swamp Key", "Wishbone", "Smelter", "Forge", "Iron Armor", "Pickaxes Tier 2", "Artisan Table", "Torn Spirit" };

    public static string FakeItemMessage()
    {
        var item = FakeItems[UnityEngine.Random.Range(0, FakeItems.Length)];
        var others = session?.Players.AllPlayers.Where(p => p.Slot > 0 && p.Slot != session.ConnectionInfo.Slot).ToList();
        var sender = others != null && others.Count > 0 ? others[UnityEngine.Random.Range(0, others.Count)].Alias : "Archipelago";
        return $"Received {item} from {sender}";
    }

    // ---------- Checks and hints ----------

    public static string Category(string location)
    {
        int colon = location.IndexOf(':');
        return colon > 0 ? location.Substring(0, colon) : "Research";
    }

    public static string CheckSummary()
    {
        var missing = session.Locations.AllMissingLocations
            .Select(id => session.Locations.GetLocationNameFromId(id, "Valheim") ?? id.ToString()).ToList();
        int total = session.Locations.AllLocations.Count;
        var byCategory = missing.GroupBy(Category).OrderBy(g => g.Key)
            .Select(g => $"{g.Key} {g.Count()}");
        return $"{total - missing.Count}/{total} checks done. Left: " + string.Join(", ", byCategory) +
               ". /ap missing <category> lists them.";
    }

    public static IEnumerable<string> MissingNames() => session == null ? Enumerable.Empty<string>() :
        session.Locations.AllMissingLocations.Select(id => session.Locations.GetLocationNameFromId(id, "Valheim") ?? id.ToString());

    public static IEnumerable<string> MissingIn(string category)
    {
        return session.Locations.AllMissingLocations
            .Select(id => session.Locations.GetLocationNameFromId(id, "Valheim") ?? id.ToString())
            .Where(name => string.Equals(Category(name), category, StringComparison.OrdinalIgnoreCase))
            .OrderBy(name => name);
    }

    public static void Say(string text) => session.Say(text);

    // ---------- Hint shop ----------
    // By a trader, pay Coins to reveal one of your checks that's in logic as a hint for everyone (scouting your
    // own location with a hint costs no hint points). A check bought once isn't offered again.
    // A fixed price: dear early on, when Coins are few, and easier as they pile up.
    private static int hintShopPrice;
    private const float ShopDistance = 10f;

    public static string ShopHint(Player player, string category)
    {
        if (hintShopPrice <= 0) return "The hint shop is closed in this game (hint_shop_price is 0).";
        if (player == null) return "Load your world first.";
        if (!ArchipelagoConnection.IsConnected || !session.Socket.Connected) return "Not connected to Archipelago.";
        if (shopPending) return "Your last hint is still on its way.";
        bool nearTrader = UnityEngine.Object.FindObjectsByType<Trader>(FindObjectsSortMode.None)
            .Any(t => t && Vector3.Distance(t.transform.position, player.transform.position) <= ShopDistance);
        if (!nearTrader) return "Stand by a trader (Haldor, Hildir or the Bog Witch) to shop.";
        var inventory = player.GetInventory();
        int coins = inventory.CountItems("$item_coins");
        int price = hintShopPrice;
        if (coins < price) return $"A hint costs {price} Coins; you have {coins}.";

        string Bought(string name) => ArchipelagoCoop.Scoped("ap_shophint:" + name.ToLowerInvariant().Replace(' ', '_'));
        var choices = ArchipelagoLogic.Missing(category).inLogic.Where(n => !ZoneSystem.instance.GetGlobalKey(Bought(n))).ToList();
        if (choices.Count == 0)
            return category == null ? "Nothing in logic is left to hint." : $"Nothing in logic is left to hint in '{category}'.";
        var name = choices[UnityEngine.Random.Range(0, choices.Count)];
        long id = session.Locations.GetLocationIdFromName("Valheim", name);
        if (id < 0) return "That check isn't in this seed.";

        // Paid once the server has made the hint (the reply comes on the network thread; paying is done on the
        // main thread, in Tick), so a lost connection costs nothing.
        shopPending = true;
        session.Locations.ScoutLocationsAsync(HintCreationPolicy.CreateAndAnnounceOnce, id).ContinueWith(task =>
            shopResults.Enqueue(() =>
            {
                shopPending = false;
                var me = Player.m_localPlayer;
                if (task.IsFaulted || task.IsCanceled || task.Result == null || task.Result.Count == 0)
                {
                    me?.Message(MessageHud.MessageType.Center, "Archipelago: the hint shop couldn't reach the server; nothing was paid.");
                    return;
                }
                me?.GetInventory().RemoveItem("$item_coins", price);
                ZoneSystem.instance?.SetGlobalKey(Bought(name));
                me?.Message(MessageHud.MessageType.Center, $"Archipelago: paid {price} Coins for a hint on {name}.");
            }));
        return $"Asking the server for a hint on {name}...";
    }

    private static bool shopPending;
    private static readonly ConcurrentQueue<Action> shopResults = new ConcurrentQueue<Action>();

    public static string ShopInfo() => hintShopPrice <= 0 ? "The hint shop is closed in this game." :
        $"Hint shop: by a trader, /ap shop hint [category] pays {hintShopPrice} Coins to reveal one of your checks in logic.";

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
        if (packet is SetReplyPacket reply)
        {
            OnSetReply(reply);
            return;
        }
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

        // Subtract and clamp at 0 in one server operation, so two games withdrawing at once
        // can't both take the same energy. The library's own reply callback never fires (it
        // expects its reference as a GUID token, but replies carry it as a string), so the
        // request carries our id and OnSetReply handles the reply; the empty callback is what
        // asks the server for a reply.
        var id = Guid.NewGuid().ToString("N");
        pendingWithdrawals[id] = coins;
        long want = coins * JoulesPerCoin;
        session.DataStorage[Scope.Global, EnergyKey] = session.DataStorage[Scope.Global, EnergyKey] - want
            + Operation.Max(0)
            + Callback.Add((original, value, _) => { })
            + AdditionalArgument.Add("valheim_withdraw", id);
        return "Withdrawing...";
    }

    private static void OnSetReply(SetReplyPacket reply)
    {
        if (reply.AdditionalArguments == null || !reply.AdditionalArguments.TryGetValue("valheim_withdraw", out var idToken) ||
            !pendingWithdrawals.TryRemove(idToken.ToString(), out _)) return;
        double taken = ToDouble(reply.OriginalValue) - ToDouble(reply.Value);
        int got = (int)Math.Floor(taken / JoulesPerCoin);
        double change = taken - (double)got * JoulesPerCoin;
        // Part of a coin's worth goes back into the pool. (Network thread: the session may have just been dropped;
        // the Coins are still paid out.)
        var current = session;
        if (change > 0 && current != null) current.DataStorage[Scope.Global, EnergyKey] += change;
        if (got > 0) incomingCoins.Enqueue(got);
        messages.Enqueue(got > 0 ? $"Withdrew {got} Coins from Energy Link." : "The Energy Link pool is empty.");
    }

    // ---------- Main thread ----------

    public static void Tick(Player player)
    {
        while (shopResults.TryDequeue(out var shopResult)) shopResult();
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

// Chat command (type /ap in chat): /ap status | goal | logic [category] | shop [hint [category]] | checks | missing <category> | hint <item> | say <text> |
// energy | deposit <coins> | withdraw <coins> | deathlink on|off
public class ArchipelagoCommand : ConsoleCommand
{
    public override string Name => "ap";
    public override string Help =>
        "Archipelago: status, goal, logic [category], shop, checks, missing <category>, hint <item>, say <text>, energy, deposit <coins>, withdraw <coins>, deathlink on|off";

    public override void Run(string[] args, Terminal context)
    {
        string Reply(string text) { context?.AddString("[AP] " + text); return text; }
        var sub = args.Length > 0 ? args[0].ToLowerInvariant() : "status";
        if (sub == "status" || sub == "help")
        {
            Reply(ArchipelagoLinks.Status());
            if (ZoneSystem.instance != null) Reply(ArchipelagoCoop.Describe());
            Reply("Commands: /ap goal, /ap logic [category], /ap shop, /ap checks, /ap missing <category>, /ap hint <item>, /ap say <text>, " +
                  "/ap energy, /ap deposit <coins>, /ap withdraw <coins>, /ap deathlink on|off");
            return;
        }
        if (!ArchipelagoLinks.Connected) { Reply("Not connected to Archipelago."); return; }
        var player = Player.m_localPlayer;
        int amount = args.Length > 1 && int.TryParse(args[1], out var n) ? n : 0;
        string rest = string.Join(" ", args.Skip(1));
        switch (sub)
        {
            case "goal":
                foreach (var line in ArchipelagoGoal.Status(ArchipelagoConnection.ReceivedCount).Split('\n')) Reply(line);
                break;
            case "shop":
                if (args.Length < 2 || args[1].ToLowerInvariant() != "hint") { Reply(ArchipelagoLinks.ShopInfo()); return; }
                Reply(ArchipelagoLinks.ShopHint(player, args.Length > 2 ? string.Join(" ", args.Skip(2)) : null));
                break;
            case "logic":
                if (rest.Length == 0)
                {
                    var (all, notYet) = ArchipelagoLogic.Missing();
                    Reply($"In logic now: {all.Count} (not yet: {notYet}). " + string.Join(", ",
                          all.GroupBy(ArchipelagoLinks.Category).OrderBy(g => g.Key).Select(g => $"{g.Key} {g.Count()}")) +
                          $". /ap logic <category> lists them; {ValheimRandomizer.logicPanelKey.Value} shows the panel.");
                    if (ArchipelagoLogic.Next.Count > 0) Reply(ArchipelagoLogic.NextLine());
                    return;
                }
                var (names2, later) = ArchipelagoLogic.Missing(rest);
                Reply(names2.Count == 0 ? $"Nothing in logic in '{rest}' ({later} not yet)." :
                      $"{names2.Count} in logic ({later} not yet): " + string.Join(", ", names2.Take(40)) + (names2.Count > 40 ? ", ..." : ""));
                break;
            case "checks":
                Reply(ArchipelagoLinks.CheckSummary());
                break;
            case "missing":
                if (rest.Length == 0) { Reply("Usage: /ap missing <category>, e.g. /ap missing obtain (see /ap checks)"); return; }
                var names = ArchipelagoLinks.MissingIn(rest).ToList();
                Reply(names.Count == 0 ? $"Nothing left in '{rest}'." : $"{names.Count} left: " + string.Join(", ", names.Take(40)) +
                      (names.Count > 40 ? ", ..." : ""));
                break;
            case "hint":
                if (rest.Length == 0) { Reply("Usage: /ap hint <item name>"); return; }
                ArchipelagoLinks.Say("!hint " + rest);
                break;
            case "say":
                if (rest.Length == 0) { Reply("Usage: /ap say <text>"); return; }
                ArchipelagoLinks.Say(rest);
                break;
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
