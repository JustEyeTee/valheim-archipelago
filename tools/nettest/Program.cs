// Exercises the mod's network calls against a live MultiServer: login + slot data, Trap Link
// bounce, Death Link, Energy Link deposit and atomic withdraw, hints and the message log.
using Archipelago.MultiClient.Net;
using Archipelago.MultiClient.Net.BounceFeatures.DeathLink;
using Archipelago.MultiClient.Net.Enums;
using Archipelago.MultiClient.Net.MessageLog.Messages;
using Archipelago.MultiClient.Net.Models;
using Archipelago.MultiClient.Net.Packets;
using Newtonsoft.Json.Linq;

int port = int.Parse(args[0]);
ArchipelagoSession Login(string slot)
{
    var s = ArchipelagoSessionFactory.CreateSession("127.0.0.1", port);
    var r = s.TryConnectAndLogin("Valheim", slot, ItemsHandlingFlags.AllItems);
    if (!r.Successful) throw new Exception(slot + ": " + string.Join("; ", ((LoginFailure)r).Errors));
    var sd = ((LoginSuccessful)r).SlotData;
    Console.WriteLine($"{slot} logged in; slot data death_link={sd["death_link"]} trap_link={sd["trap_link"]} mode={sd["death_link_mode"]} goal={sd["goal_trophy"]}");
    // Goal conditions, read the way ArchipelagoGoal.Load reads them.
    var goal = sd["goal"] as JObject ?? JObject.FromObject(sd["goal"]);
    foreach (var name in goal["conditions"]!.Values<string>())
    {
        var targets = (goal["targets"] as JObject)?[name]?.Values<string>().ToList() ?? new List<string?>();
        Console.WriteLine($"  goal condition {name}: need {(goal["needed"] as JObject)?[name]?.Value<int>()} of " +
                          $"{(targets.Count > 0 ? targets.Count + " (" + string.Join(", ", targets.Take(3)) + "...)" : "received")}");
    }
    Console.WriteLine($"  skill_level={goal["skill_level"]?.Value<int>()}");
    return s;
}
var a = Login("VikingA");
var b = Login("VikingB");

foreach (var (name, s) in new[] { ("A", a), ("B", b) })
{
    s.MessageLog.OnMessageReceived += m =>
    {
        string kind = m switch { HintItemSendLogMessage => "hint", ItemSendLogMessage => "item", _ => m.GetType().Name };
        Console.WriteLine($"  [{name} log:{kind}] {m}");
    };
    s.ConnectionInfo.UpdateConnectionOptions(s.ConnectionInfo.Tags.Concat(new[] { "TrapLink" }).ToArray());
}
var dlA = a.CreateDeathLinkService(); dlA.EnableDeathLink();
var dlB = b.CreateDeathLinkService(); dlB.EnableDeathLink();
dlB.OnDeathLinkReceived += dl => Console.WriteLine($"B got Death Link: source={dl.Source} cause={dl.Cause}");
b.Socket.PacketReceived += p =>
{
    if (p is BouncedPacket bp && bp.Tags.Contains("TrapLink"))
        Console.WriteLine($"B got Trap Link: {bp.Data["trap_name"]} from {bp.Data["source"]}");
};
Thread.Sleep(1000);

// Trap Link, exactly as ArchipelagoLinks.SendTrapLink builds it
a.Socket.SendPacketAsync(new BouncePacket
{
    Tags = new List<string> { "TrapLink" },
    Data = new Dictionary<string, JToken> { { "time", DateTimeOffset.UtcNow.ToUnixTimeMilliseconds() / 1000.0 },
                                            { "source", "VikingA" }, { "trap_name", "Floor Is Lava Trap" } },
});
dlA.SendDeathLink(new DeathLink("VikingA", "VikingA was killed by Troll in Valheim"));
Thread.Sleep(1500);

// Energy Link: A deposits 5 coins (5 MJ), B withdraws 3, then asks for 10 more than is left
const long J = 1_000_000;
string key = $"EnergyLink{a.ConnectionInfo.Team}";
a.DataStorage[Scope.Global, key].Initialize(0);   // as the mod does on connect
b.DataStorage[Scope.Global, key].Initialize(0);
Thread.Sleep(500);
a.DataStorage[Scope.Global, key] += 5 * J;
Thread.Sleep(800);
Console.WriteLine($"pool after deposit {b.DataStorage[Scope.Global, key].GetAsync().Result}");
var pending = new System.Collections.Concurrent.ConcurrentDictionary<string, int>();
b.Socket.PacketReceived += p =>
{
    if (p is SetReplyPacket r && r.AdditionalArguments != null && r.AdditionalArguments.TryGetValue("valheim_withdraw", out var id)
        && pending.TryRemove(id.ToString(), out var coins))
    {
        double taken = (r.OriginalValue?.ToObject<double>() ?? 0) - r.Value.ToObject<double>();
        Console.WriteLine($"B withdraw {coins}: got {Math.Floor(taken / J)} coins (pool {r.OriginalValue} -> {r.Value})");
    }
};
void Withdraw(int coins)
{
    var id = Guid.NewGuid().ToString("N");
    pending[id] = coins;
    b.DataStorage[Scope.Global, key] = b.DataStorage[Scope.Global, key] - coins * J + Operation.Max(0)
        + Callback.Add((o, n, _) => { }) + AdditionalArgument.Add("valheim_withdraw", id);
    Thread.Sleep(800);
}
Withdraw(3);
Withdraw(10);
Console.WriteLine($"pool now {b.DataStorage[Scope.Global, key].GetAsync().Result}");

// A tracks its hints (the F9 window's Hints tab): both the ones for its items and the ones at its checks.
Hint[] aHints = Array.Empty<Hint>();
a.DataStorage.TrackHints(h => aHints = h);
void ShowHints(string when)
{
    Console.WriteLine($"A's hints {when}: {aHints.Length}");
    foreach (var h in aHints.OrderBy(h => h.LocationId))
        Console.WriteLine($"  {a.Items.GetItemName(h.ItemId, "Valheim")} for {a.Players.GetPlayerAlias(h.ReceivingPlayer)} at " +
            $"{a.Players.GetPlayerAlias(h.FindingPlayer)}'s {a.Locations.GetLocationNameFromId(h.LocationId, "Valheim")}: " +
            $"{(h.Found ? "found" : h.Status.ToString())}");
}

// A check from B (a location in B's seed), and a hint for A
var loc = b.Locations.AllMissingLocations.First();
Console.WriteLine($"B checks {b.Locations.GetLocationNameFromId(loc, "Valheim")}");
b.Locations.CompleteLocationChecks(loc);
a.Say("!hint Crafting");
Thread.Sleep(2000);
Console.WriteLine($"A: {a.Locations.AllLocations.Count} locations, {a.Locations.AllMissingLocations.Count} missing");

// Hint shop: A scouts one of its own locations as a hint (no hint points), announced to everyone.
var shopLoc = a.Locations.AllMissingLocations.Last();
Console.WriteLine($"A buys a hint for {a.Locations.GetLocationNameFromId(shopLoc, "Valheim")}");
var scouted = a.Locations.ScoutLocationsAsync(HintCreationPolicy.CreateAndAnnounceOnce, shopLoc).Result;
foreach (var info in scouted.Values) Console.WriteLine($"  scouted: {info.ItemName} for {info.Player.Name}");
Thread.Sleep(2000);
ShowHints("after the hint shop");
a.Locations.CompleteLocationChecks(shopLoc);
Thread.Sleep(1500);
ShowHints("after A checks the shop's location");

// Testing: the server's item cheat (what /ap give uses) sends A an item the normal way.
int before = a.Items.AllItemsReceived.Count;
a.Say("!getitem Burning Trap");
Thread.Sleep(2000);
var cheated = a.Items.AllItemsReceived.Skip(before).Select(i => i.ItemName).ToList();
Console.WriteLine($"A asked for Burning Trap: received {(cheated.Count > 0 ? string.Join(", ", cheated) : "nothing")}");
