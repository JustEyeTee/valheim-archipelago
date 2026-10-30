using System.Collections.Generic;
using System.Linq;

// boss_altar_keys: a boss's altar takes no offering until that boss's Altar Key is received. The seed's setting
// and the keys received are kept in the world (per slot with separate co-op slots), so the altars stay sealed
// for players who aren't connected too.
internal static class ArchipelagoAltars
{
    private const string EnabledKey = "ap_altar_keys";
    private const string KeyPrefix = "ap_altar:";
    private const string KeySuffix = "'s Altar Key";
    private const string SeedKey = "ap_altar_seed";

    // The boss an altar summons (OfferingBowl.m_bossPrefab) -> the boss's name in the seed.
    private static readonly Dictionary<string, string> Bosses = new Dictionary<string, string>
    {
        { "Eikthyr", "Eikthyr" }, { "gd_king", "The Elder" }, { "Bonemass", "Bonemass" }, { "Dragon", "Moder" },
        { "GoblinKing", "Yagluth" }, { "SeekerQueen", "The Queen" }, { "Fader", "Fader" },
        { "FrozenKing", "Kall Fimbulbringer" }, { "vfx_LastBossGate_destroyed", "Kall Fimbulbringer" },
    };

    private static string Tag(string boss) => KeyPrefix + boss.ToLowerInvariant().Replace(' ', '_');

    public static IEnumerable<string> KeyNames => Bosses.Values.Distinct().Select(boss => boss + KeySuffix);

    public static bool IsAltarKey(string itemName) => itemName.EndsWith(KeySuffix) && Bosses.ContainsValue(itemName.Substring(0, itemName.Length - KeySuffix.Length));

    // The connected seed's setting replaces the world's; keys received in another seed (a reused world) are dropped.
    public static void OnConnected(bool enabled, string seed)
    {
        var zones = ZoneSystem.instance;
        string enabledKey = ArchipelagoCoop.Scoped(EnabledKey), seedKey = ArchipelagoCoop.Scoped(SeedKey);
        if (!enabled)
        {
            if (zones.GetGlobalKey(enabledKey)) zones.RemoveGlobalKey(enabledKey);
            return;
        }
        if (!zones.GetGlobalKey(seedKey, out var stored) || stored != seed)
        {
            foreach (var key in zones.GetGlobalKeys().ToList())
            {
                if (key.StartsWith(KeyPrefix) && ArchipelagoCoop.IsMine(key, out _)) zones.RemoveGlobalKey(key);
            }
            zones.SetGlobalKey($"{seedKey} {seed}");
        }
        if (!zones.GetGlobalKey(enabledKey)) zones.SetGlobalKey(enabledKey);
    }

    public static void OnReceived(string itemName)
    {
        var boss = itemName.Substring(0, itemName.Length - KeySuffix.Length);
        ZoneSystem.instance.SetGlobalKey(ArchipelagoCoop.Scoped(Tag(boss)));
        Player.m_localPlayer?.Message(MessageHud.MessageType.Center, $"Archipelago: {itemName}! {boss}'s altar is open to you.");
    }

    public static bool HasKey(string boss) =>
        ZoneSystem.instance != null && (!ZoneSystem.instance.GetGlobalKey(ArchipelagoCoop.Scoped(EnabledKey)) ||
                                        ZoneSystem.instance.GetGlobalKey(ArchipelagoCoop.Scoped(Tag(boss))));

    // Whether this altar takes offerings; if not, says which key it needs.
    public static bool Open(OfferingBowl bowl, Humanoid user)
    {
        if (!ValheimRandomizer.Randomized || bowl == null || bowl.m_bossPrefab == null) return true;
        if (!Bosses.TryGetValue(bowl.m_bossPrefab.name, out var boss) || HasKey(boss)) return true;
        if (user == Player.m_localPlayer)
            Player.m_localPlayer.Message(MessageHud.MessageType.Center, $"The altar is sealed: it needs {boss}{KeySuffix}");
        return false;
    }
}
