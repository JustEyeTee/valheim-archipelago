using System;
using System.Collections.Concurrent;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Threading;
using Archipelago.MultiClient.Net;
using Archipelago.MultiClient.Net.Enums;
using UnityEngine;

// What each of this slot's checks gives, the way other Archipelago games' shops show it: scouted from the server
// when you connect (no hints are made), and shown on the Research Bench's recipes (a "Sends:" line and the
// reward's icon), in the message when you craft one, and on traders' buy checks. Crafting "Bows Tier 1" sends
// whatever is at that check; the bows themselves come with the "Bows Tier 1" item, wherever it is.
public static class ArchipelagoRewards
{
    public class Reward
    {
        public string Item, Player, Game;
        public ItemFlags Flags;
        public bool Own;
    }

    // Location name -> its reward. Filled on the network thread; read on the main thread.
    private static readonly ConcurrentDictionary<string, Reward> rewards = new ConcurrentDictionary<string, Reward>();
    private static int version, appliedVersion = -1;

    public static void Scout(ArchipelagoSession session)
    {
        Clear();
        long[] ids = session.Locations.AllLocations.ToArray();
        int me = session.ConnectionInfo.Slot;
        if (ids.Length == 0) return;
        session.Locations.ScoutLocationsAsync(HintCreationPolicy.None, ids).ContinueWith(task =>
        {
            if (task.IsFaulted || task.IsCanceled || task.Result == null)
            {
                ValheimRandomizer.Log.LogWarning("[AP] Couldn't look up what the checks give: " + task.Exception?.GetBaseException().Message);
                return;
            }
            foreach (var info in task.Result.Values)
            {
                if (info.LocationName == null) continue;
                rewards[info.LocationName] = new Reward
                {
                    Item = info.ItemDisplayName, Player = info.Player?.Name ?? "someone", Game = info.ItemGame,
                    Flags = info.Flags, Own = info.Player != null && info.Player.Slot == me,
                };
            }
            Interlocked.Increment(ref version);
            ValheimRandomizer.Log.LogInfo($"[AP] Looked up what {rewards.Count} checks give");
        });
    }

    public static void Clear()
    {
        rewards.Clear();
        Interlocked.Increment(ref version);
    }

    public static bool TryGet(string location, out Reward reward) => rewards.TryGetValue(location, out reward);

    private static string Kind(ItemFlags flags) =>
        (flags & ItemFlags.Advancement) != 0 ? "progression" : (flags & ItemFlags.NeverExclude) != 0 ? "useful"
        : (flags & ItemFlags.Trap) != 0 ? "trap" : "filler";

    // "your Progressive Axes (progression)", "Mawff's Lantern (Hollow Knight, useful)".
    public static string Describe(Reward r) =>
        r.Own ? $"your {r.Item} ({Kind(r.Flags)})" : $"{r.Player}'s {r.Item} ({r.Game}, {Kind(r.Flags)})";

    // Main thread, every couple of seconds in a randomized world: puts the rewards on the Research Bench's recipes
    // once they've arrived (and puts the recipes back after a disconnect).
    public static void Apply()
    {
        int now = Volatile.Read(ref version);
        if (now == appliedVersion || ObjectDB.instance == null) return;
        appliedVersion = now;
        foreach (var research in RandomizerUtils.ResearchLooks)
        {
            var drop = ObjectDB.instance.GetItemPrefab(research.Key)?.GetComponent<ItemDrop>();
            if (drop == null || !ValheimRandomizer.researchToArchipelago.TryGetValue(research.Key, out var location)) continue;
            var shared = drop.m_itemData.m_shared;
            var (description, icon) = research.Value;
            if (TryGet(location, out var reward))
            {
                shared.m_description = $"<color=#e8a33d>Sends:</color> {Describe(reward)}\n\n{description}";
                var rewardIcon = Icon(reward);
                shared.m_icons = new[] { rewardIcon ? rewardIcon : icon };
            }
            else
            {
                shared.m_description = description;
                shared.m_icons = new[] { icon };
            }
        }
    }

    // Your own Valheim items show as themselves (a research, a progressive item's first tier, a trophy boost, a
    // bundle, tool or boss drop); anything else as Archipelago's logo, coloured by kind.
    private static Sprite Icon(Reward r)
    {
        if (r.Own)
        {
            string item = ArchipelagoConnection.ProgressiveMembers(r.Item).FirstOrDefault() ?? r.Item;
            if (item.StartsWith("Trophy: ", StringComparison.Ordinal)) return PrefabIcon(item.Substring("Trophy: ".Length));
            if (ValheimRandomizer.archipelagoToResearch.TryGetValue(item, out var id) && RandomizerUtils.ResearchLooks.TryGetValue(id, out var look))
                return look.icon;
            var prefab = ArchipelagoExtras.ItemPrefab(item);
            if (prefab != null) return PrefabIcon(prefab);
        }
        return ApIcon((r.Flags & ItemFlags.Advancement) != 0 ? "progression" : (r.Flags & ItemFlags.NeverExclude) != 0 ? "useful" : "filler");
    }

    private static Sprite PrefabIcon(string prefab)
    {
        var icons = ObjectDB.instance?.GetItemPrefab(prefab)?.GetComponent<ItemDrop>()?.m_itemData.m_shared.m_icons;
        return icons != null && icons.Length > 0 ? icons[0] : null;
    }

    private static readonly Dictionary<string, Sprite> apIcons = new Dictionary<string, Sprite>();

    private static Sprite ApIcon(string kind)
    {
        if (apIcons.TryGetValue(kind, out var sprite) && sprite) return sprite;
        using (var stream = typeof(ArchipelagoRewards).Assembly.GetManifestResourceStream($"ap_icons/{kind}.png"))
        {
            if (stream == null) return null;
            var bytes = new byte[stream.Length];
            stream.Read(bytes, 0, bytes.Length);
            var texture = new Texture2D(2, 2, TextureFormat.RGBA32, false);
            texture.LoadImage(bytes);
            sprite = Sprite.Create(texture, new Rect(0, 0, texture.width, texture.height), new Vector2(0.5f, 0.5f));
        }
        apIcons[kind] = sprite;
        return sprite;
    }
}
