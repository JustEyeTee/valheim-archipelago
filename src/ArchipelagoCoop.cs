using System;
using System.Collections.Generic;
using System.Linq;

// Co-op modes, chosen per world: the first player connected in a world picks one when asked (ArchipelagoCoopPrompt);
// it's stored in the world (world key "ap_coop shared" or "ap_coop separate") and the world keeps it for good.
//   shared:   one Archipelago slot for the world. One player connects; everyone's checks count for that slot,
//             and every received research unlocks for everyone. Worlds from before co-op modes are shared.
//   separate: each player connects to their own slot. Everything the mod keeps in the world (researches
//             received and crafted, checks done, goal progress) is kept per slot, so each player has their
//             own unlocks, checks, goal and Archipelago Chest.
// Per-slot keys are the shared key with "@<slot>" appended (the slot name lowercased, spaces as underscores).
internal static class ArchipelagoCoop
{
    public const string ModeKey = "ap_coop";
    public const string Shared = "shared";
    public const string Separate = "separate";

    public static bool IsSeparate =>
        ZoneSystem.instance != null && ZoneSystem.instance.GetGlobalKey(ModeKey, out var mode) && mode == Separate;

    // This player's slot: the connected one, or (offline) the one in the config.
    public static string Slot => ArchipelagoConnection.SlotName ?? ValheimRandomizer.archipelagoSlot.Value ?? "";

    private static string tagFor, tag;
    public static string Tag(string slot)
    {
        if (slot != tagFor)
        {
            tagFor = slot;
            tag = new string(slot.ToLowerInvariant().Select(c => c == ' ' || c == '@' ? '_' : c).ToArray());
        }
        return tag;
    }

    // A key the mod keeps in the world, for this player's slot.
    public static string Scoped(string key) => IsSeparate ? key + "@" + Tag(Slot) : key;

    // Whether per-slot keys can be written: a connected player chooses the world's mode when asked, and the
    // choice comes back from the server a moment later; until then a key could go under the wrong mode. A
    // player who isn't connected never chooses, and a world without a mode is shared.
    public static bool Ready
    {
        get
        {
            if (ZoneSystem.instance == null) return false;
            if (ZoneSystem.instance.GetGlobalKey(ModeKey) || !ArchipelagoConnection.IsConnected) return true;
            ChooseMode();
            return ZoneSystem.instance.GetGlobalKey(ModeKey);
        }
    }

    // One-time events (a kill, a research crafted...) that came before the mode was known, replayed after; they
    // belong to the world they happened in.
    private static readonly Queue<Action> waiting = new Queue<Action>();
    private static ZoneSystem waitingWorld;

    public static void WhenReady(Action action)
    {
        if (ZoneSystem.instance != waitingWorld)
        {
            waiting.Clear();
            waitingWorld = ZoneSystem.instance;
        }
        if (Ready)
        {
            Replay();  // earlier events first (also when the player disconnected before the next flush)
            if (waiting.Count == 0)
            {
                action();
                return;
            }
        }
        waiting.Enqueue(action);
    }

    private static bool replaying;

    public static void Replay()
    {
        if (ZoneSystem.instance != waitingWorld) waiting.Clear();
        if (replaying) return;  // a replayed check flushes, which replays: the loop below already does that
        replaying = true;
        try
        {
            while (waiting.Count > 0 && Ready) waiting.Dequeue()();
        }
        finally
        {
            replaying = false;
        }
    }

    // For keys read back from the world: whether one belongs to this slot (separate) or is a plain key
    // (shared), and the key without its slot.
    public static bool IsMine(string key, out string unscoped)
    {
        int at = key.LastIndexOf('@');
        if (!IsSeparate)
        {
            unscoped = key;
            return at < 0;
        }
        unscoped = at < 0 ? key : key.Substring(0, at);
        return at >= 0 && key.Substring(at + 1) == Tag(Slot);
    }

    // Whether the connected player is being asked to pick this world's mode (ArchipelagoCoopPrompt).
    public static bool Asking { get; private set; }

    // Called once a connected player has a world loaded: a world without a mode asks this player for one.
    public static void ChooseMode()
    {
        if (ZoneSystem.instance == null || ZoneSystem.instance.GetGlobalKey(ModeKey)) { Asking = false; return; }
        // Worlds already played before co-op modes existed stay shared.
        if (ZoneSystem.instance.GetGlobalKey("ap_world")) SetMode(Shared);
        else if (!Asking) { Asking = true; ValheimRandomizer.Log.LogInfo("[AP] This world has no co-op mode yet: asking"); }
    }

    public static void SetMode(string mode)
    {
        Asking = false;
        if (ZoneSystem.instance == null || ZoneSystem.instance.GetGlobalKey(ModeKey)) return;
        ZoneSystem.instance.SetGlobalKey($"{ModeKey} {mode}");
        ValheimRandomizer.Log.LogInfo($"[AP] This world's co-op mode: {mode}");
    }

    public static string Describe() => IsSeparate
        ? $"Co-op: separate slots (you are {Slot})."
        : "Co-op: shared slot (one player connects; everyone's checks count).";
}
