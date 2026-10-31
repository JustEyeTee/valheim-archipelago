using System;
using System.IO;
using System.Linq;
using UnityEngine;

// For a dedicated test server: whoever runs the server can drop items or creatures beside a player, or show a
// message to everyone, by appending lines to the file named by the AP_ADMIN_QUEUE environment variable:
//     spawn <player|*> <prefab> [count]     e.g. spawn TestViking TrophyDeer 2, spawn * Greyling 3
//     say <text>
//     players
// Only active on a dedicated server with that variable set; players' games never have it.
public class ArchipelagoServerAdmin : MonoBehaviour
{
    private const float PollSeconds = 1f;

    private string queue;
    private float nextPoll;

    public static void Install(GameObject go)
    {
        string path = Environment.GetEnvironmentVariable("AP_ADMIN_QUEUE");
        if (string.IsNullOrEmpty(path)) return;
        go.AddComponent<ArchipelagoServerAdmin>().queue = path;
        ValheimRandomizer.Log.LogInfo($"[AP] Server admin commands read from {path}");
    }

    private void Update()
    {
        if (Time.unscaledTime < nextPoll) return;
        nextPoll = Time.unscaledTime + PollSeconds;
        if (ZNet.instance == null || !ZNet.instance.IsDedicated() || ZNetScene.instance == null || !File.Exists(queue)) return;

        // Take the file away before reading it, so a line appended meanwhile goes into a new one.
        string taken = queue + ".taken";
        string[] lines;
        try
        {
            File.Delete(taken);
            File.Move(queue, taken);
            lines = File.ReadAllLines(taken);
            File.Delete(taken);
        }
        catch (Exception e)
        {
            ValheimRandomizer.Log.LogWarning($"[AP] Couldn't read admin commands: {e.Message}");
            return;
        }
        foreach (var line in lines.Select(l => l.Trim()).Where(l => l.Length > 0))
        {
            try { Run(line); }
            catch (Exception e) { ValheimRandomizer.Log.LogWarning($"[AP] Admin command '{line}' failed: {e.Message}"); }
        }
    }

    private static void Run(string line)
    {
        var words = line.Split(new[] { ' ' }, StringSplitOptions.RemoveEmptyEntries);
        switch (words[0].ToLowerInvariant())
        {
            case "say":
                ZRoutedRpc.instance.InvokeRoutedRPC(ZRoutedRpc.Everybody, "ShowMessage", (int)MessageHud.MessageType.Center,
                    line.Substring(line.IndexOf(' ') + 1));
                ValheimRandomizer.Log.LogInfo($"[AP] Admin: said '{line.Substring(line.IndexOf(' ') + 1)}'");
                break;
            case "players":
                ValheimRandomizer.Log.LogInfo("[AP] Admin: players " + string.Join(", ",
                    ZNet.instance.GetPeers().Select(p => $"{p.m_playerName} at {p.m_refPos:F0}")));
                break;
            case "spawn" when words.Length >= 3:
                int count = words.Length >= 4 && int.TryParse(words[3], out var n) ? Mathf.Clamp(n, 1, 500) : 1;
                Spawn(words[1], words[2], count);
                break;
            default:
                ValheimRandomizer.Log.LogWarning($"[AP] Admin: unknown command '{line}' (spawn <player|*> <prefab> [count], say <text>, players)");
                break;
        }
    }

    private static void Spawn(string who, string prefabName, int count)
    {
        var prefab = ZNetScene.instance.GetPrefab(prefabName);
        if (prefab == null)
        {
            ValheimRandomizer.Log.LogWarning($"[AP] Admin: no prefab named '{prefabName}'");
            return;
        }
        var peers = ZNet.instance.GetPeers().Where(p => who == "*" ||
            string.Equals(p.m_playerName, who, StringComparison.OrdinalIgnoreCase)).ToList();
        if (peers.Count == 0)
        {
            ValheimRandomizer.Log.LogWarning($"[AP] Admin: no player named '{who}' online");
            return;
        }
        var drop = prefab.GetComponent<ItemDrop>();
        foreach (var peer in peers)
        {
            // Items stack into as few drops as they can; creatures come one each.
            int perDrop = drop != null ? Math.Max(1, drop.m_itemData.m_shared.m_maxStackSize) : 1;
            for (int left = count; left > 0; left -= perDrop)
            {
                var offset = UnityEngine.Random.insideUnitCircle * (drop != null ? 1f : 4f);
                var go = Instantiate(prefab, peer.m_refPos + new Vector3(offset.x, 1.5f, offset.y), Quaternion.identity);
                go.GetComponent<ItemDrop>()?.SetStack(Math.Min(left, perDrop));
            }
            ValheimRandomizer.Log.LogInfo($"[AP] Admin: spawned {count} {prefabName} at {peer.m_playerName}");
        }
    }
}
