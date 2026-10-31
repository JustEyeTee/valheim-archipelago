using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using Newtonsoft.Json.Linq;
using UnityEngine;

// Which of the seed's checks are in logic now, from logic.tsv (embedded in the DLL; written by
// tools/gen_mod_logic.py from the APWorld): each check's tier gates, research prerequisites, boss gates,
// combat era and comfort level. Items count when they're in the world: a research once it's unlocked (so
// progressive items count too), a boss drop once received, a boss once its trophy check is done.
// Shown by the logic panel (LogicPanelKey, F8 by default) and /ap logic.
public static class ArchipelagoLogic
{
    private static readonly Dictionary<string, (int tier, string[] needs)> Locations =
        new Dictionary<string, (int, string[])>();
    private static readonly Dictionary<int, string[]> Tiers = new Dictionary<int, string[]>();
    private static readonly Dictionary<string, Dictionary<string, string[]>> Combat =
        new Dictionary<string, Dictionary<string, string[]>>();
    private static readonly List<(string key, int comfort, string[] needs)> ComfortPieces =
        new List<(string, int, string[])>();
    private static string[] shelter = Array.Empty<string>();
    private static readonly Dictionary<string, (string trophy, string drop)> Bosses =
        new Dictionary<string, (string, string)>();

    // The seed's combat_logic: 0 off, 1 armor and a weapon, 2 also a bow or crossbow.
    private static int combatMode = 1;

    // Token -> in logic, for one evaluation (the same tier and boss tokens come up for many checks).
    private static readonly Dictionary<string, bool> cache = new Dictionary<string, bool>();

    static ArchipelagoLogic()
    {
        using (var stream = typeof(ArchipelagoLogic).Assembly.GetManifestResourceStream("logic.tsv"))
        using (var reader = new StreamReader(stream))
        {
            string line;
            while ((line = reader.ReadLine()) != null)
            {
                if (line.Length == 0 || line.StartsWith("#", StringComparison.Ordinal)) continue;
                var cols = line.Split('\t');
                switch (cols[0])
                {
                    case "tier": Tiers[int.Parse(cols[1])] = Split(cols[2]); break;
                    case "location": Locations[cols[1]] = (int.Parse(cols[2]), Split(cols[3])); break;
                    case "combat":
                        if (!Combat.TryGetValue(cols[1], out var kinds)) Combat[cols[1]] = kinds = new Dictionary<string, string[]>();
                        kinds[cols[2]] = Split(cols[3]);
                        break;
                    case "comfort": ComfortPieces.Add((cols[1], int.Parse(cols[2]), Split(cols[3]))); break;
                    case "shelter": shelter = Split(cols[1]); break;
                    case "boss": Bosses[cols[1]] = (cols[2], cols.Length > 3 ? cols[3] : ""); break;
                }
            }
        }
    }

    private static string[] Split(string text) =>
        text.Split(new[] { '|' }, StringSplitOptions.RemoveEmptyEntries);

    public static void Load(Dictionary<string, object> slotData)
    {
        combatMode = 1;
        try
        {
            if (slotData != null && slotData.TryGetValue("options", out var raw) && raw != null)
            {
                var options = raw as JObject ?? JObject.FromObject(raw);
                combatMode = options["combat_logic"]?.Value<int>() ?? 1;
            }
        }
        catch (Exception ex)
        {
            ValheimRandomizer.Log.LogWarning("[AP] Couldn't read combat_logic from the slot data: " + ex.Message);
        }
    }

    private static bool Has(string item)
    {
        if (ValheimRandomizer.archipelagoToResearch.TryGetValue(item, out var researchId))
            return ValheimRandomizer.IsResearchUnlocked(researchId);
        return ArchipelagoConnection.ReceivedCount(item) > 0;
    }

    private static bool Defeated(string boss) =>
        Bosses.TryGetValue(boss, out var b) && ArchipelagoConnection.IsLocationDone(b.trophy);

    private static bool Token(string token)
    {
        if (cache.TryGetValue(token, out var known)) return known;
        bool result;
        int colon = token.IndexOf(':');
        string kind = colon > 0 ? token.Substring(0, colon) : "", arg = colon > 0 ? token.Substring(colon + 1) : token;
        switch (kind)
        {
            case "tier": result = !Tiers.TryGetValue(int.Parse(arg), out var tierNeeds) || All(tierNeeds); break;
            case "boss":
                result = Defeated(arg) || (Bosses.TryGetValue(arg, out var b) && b.drop.Length > 0 && Has(b.drop));
                break;
            case "kill": result = Defeated(arg); break;
            case "combat": result = CombatReady(arg); break;
            case "comfort": result = Comfort() >= int.Parse(arg); break;
            case "altarkey": result = ArchipelagoAltars.HasKey(arg); break;
            default: result = Has(token); break;
        }
        cache[token] = result;
        return result;
    }

    private static bool All(IEnumerable<string> tokens) => tokens.All(Token);

    private static bool CombatReady(string era)
    {
        if (combatMode == 0 || !Combat.TryGetValue(era, out var gear)) return true;
        bool Any(string kind) => !gear.TryGetValue(kind, out var items) || items.Length == 0 || items.Any(Has);
        return Any("armor") && Any("weapons") && (combatMode < 2 || Any("ranged"));
    }

    // The game's comfort: 1, plus 1 under a roof, plus the best piece of each comfort group you can build.
    private static int Comfort()
    {
        if (!All(shelter)) return 1;
        var best = new Dictionary<string, int>();
        foreach (var (key, comfort, needs) in ComfortPieces)
        {
            if ((!best.TryGetValue(key, out var have) || comfort > have) && All(needs)) best[key] = comfort;
        }
        return 2 + best.Values.Sum();
    }

    public static bool InLogic(string location)
    {
        if (!Locations.TryGetValue(location, out var rule)) return true;
        return Token("tier:" + rule.tier) && All(rule.needs);
    }

    // What a check still lacks, as the smallest things to get: items, bosses, gear for a fight, a comfort level
    // (a tier's gate is opened up into what it needs).
    private static void Lacking(string token, HashSet<string> into)
    {
        if (Token(token)) return;
        if (token.StartsWith("tier:", StringComparison.Ordinal) && Tiers.TryGetValue(int.Parse(token.Substring(5)), out var needs))
        {
            foreach (var need in needs) Lacking(need, into);
            return;
        }
        into.Add(token);
    }

    // The things that would each put the most checks in logic on their own: (what, how many checks).
    public static List<(string what, int checks)> Next { get; private set; } = new List<(string, int)>();

    public static string NextLine() => "Best to get next: " + string.Join(", ", Next.Select(n =>
        $"{Describe(n.what)} (opens {n.checks} more)"));

    public static string Describe(string token)
    {
        int colon = token.IndexOf(':');
        string arg = colon > 0 ? token.Substring(colon + 1) : token;
        switch (colon > 0 ? token.Substring(0, colon) : "")
        {
            case "boss": return $"defeat {arg} (or receive its drop)";
            case "kill": return $"defeat {arg}";
            case "combat": return $"{arg} gear (armor and a weapon)";
            case "comfort": return $"comfort {arg}";
            case "altarkey": return $"{arg}'s Altar Key";
            default: return ValheimRandomizer.archipelagoToResearch.ContainsKey(token) ? $"{token} research" : token;
        }
    }

    // The seed's missing checks split into in logic and not, by category ("Obtain", "Research"...).
    public static (List<string> inLogic, int outOfLogic) Missing(string category = null)
    {
        cache.Clear();
        var inLogic = new List<string>();
        int outOfLogic = 0;
        if (ZoneSystem.instance == null) return (inLogic, 0);
        var unlocks = new Dictionary<string, int>();
        foreach (var name in ArchipelagoLinks.MissingNames())
        {
            if (category != null && !string.Equals(ArchipelagoLinks.Category(name), category, StringComparison.OrdinalIgnoreCase)) continue;
            if (InLogic(name))
            {
                inLogic.Add(name);
                continue;
            }
            outOfLogic++;
            if (!Locations.TryGetValue(name, out var rule)) continue;
            var lacking = new HashSet<string>();
            Lacking("tier:" + rule.tier, lacking);
            foreach (var need in rule.needs) Lacking(need, lacking);
            if (lacking.Count == 1)
            {
                var only = lacking.First();
                unlocks[only] = unlocks.TryGetValue(only, out var n) ? n + 1 : 1;
            }
        }
        Next = unlocks.OrderByDescending(u => u.Value).ThenBy(u => u.Key).Take(3).Select(u => (u.Key, u.Value)).ToList();
        inLogic.Sort(StringComparer.Ordinal);
        return (inLogic, outOfLogic);
    }
}

// The logic panel: the checks in logic now, by category, on the right of the screen while a world is loaded.
public class ArchipelagoLogicPanel : MonoBehaviour
{
    private const float RefreshSeconds = 2f;

    private bool open;
    private float nextRefresh;
    private string text = "";
    private GUIStyle style;

    private void Update()
    {
        if (ValheimRandomizer.logicPanelKey.Value.IsDown() && Player.m_localPlayer != null &&
            !(Chat.instance && Chat.instance.HasFocus()) && !Console.IsVisible() && !TextInput.IsVisible())
        {
            open = !open;
            nextRefresh = 0f;
        }
        if (open && Time.unscaledTime >= nextRefresh)
        {
            nextRefresh = Time.unscaledTime + RefreshSeconds;
            text = Build();
        }
    }

    // A glance: how many checks you can do now, what to get to open up the most, and how many of each kind.
    private static string Build()
    {
        if (!ArchipelagoLinks.Connected) return "Not connected.";
        var (inLogic, _) = ArchipelagoLogic.Missing();
        var lines = new List<string> { $"{inLogic.Count} checks you can do now" };
        if (ArchipelagoLogic.Next.Count > 0) lines.Add(ArchipelagoLogic.NextLine());
        lines.Add(string.Join(" · ", inLogic.GroupBy(ArchipelagoLinks.Category).OrderByDescending(g => g.Count())
            .ThenBy(g => g.Key).Select(g => $"{g.Key} {g.Count()}")));
        lines.Add($"{ValheimRandomizer.logicWindowKey.Value}: the full list");
        return string.Join("\n", lines);
    }

    private void OnGUI()
    {
        if (!open || Player.m_localPlayer == null) return;
        // Out of the way of the game's own screens.
        if (InventoryGui.IsVisible() || Menu.IsVisible() || StoreGui.IsVisible() || Minimap.IsOpen()) return;
        if (style == null)
        {
            style = new GUIStyle(GUI.skin.box) { alignment = TextAnchor.UpperLeft, wordWrap = true, fontSize = 14 };
            style.normal.textColor = Color.white;
        }
        // On the right, below the minimap and the status effects beside it.
        float width = Mathf.Min(420f, Screen.width * 0.3f);
        var content = new GUIContent("Archipelago (" + ValheimRandomizer.logicPanelKey.Value + ")\n" + text);
        float height = style.CalcHeight(content, width);
        GUI.Box(new Rect(Screen.width - width - 16f, Screen.height * 0.30f, width, height), content, style);
    }
}

// The logic window (LogicWindowKey, F9 by default): every check in logic now, by category, with the mouse
// free to scroll and to ask the server for a hint on one (!hint_location, which costs hint points).
public class ArchipelagoLogicWindow : MonoBehaviour
{
    private const float RefreshSeconds = 2f;

    public static bool IsOpen { get; private set; }

    private Rect window = new Rect(80, 80, 560, 620);
    private Vector2 scroll;
    private string category = "All";
    private float nextRefresh;
    private List<string> inLogic = new List<string>();
    private int outOfLogic;
    private string message = "";
    private string nextCategory, nextMessage;
    private bool showPassive, nextShowPassive;
    private bool hintsView, nextHintsView;
    private bool showFound, nextShowFound;

    // Checks that come by themselves as you play (skill levels, exploring, comfort), hidden unless asked for.
    private static readonly HashSet<string> Passive = new HashSet<string> { "Skill", "Explore", "Comfort" };

    private void Update()
    {
        bool toggle = ValheimRandomizer.logicWindowKey.Value.IsDown() && Player.m_localPlayer != null &&
                      !(Chat.instance && Chat.instance.HasFocus()) && !Console.IsVisible() && !TextInput.IsVisible();
        if (toggle || (IsOpen && Player.m_localPlayer == null))
        {
            SetOpen(!IsOpen && toggle);
        }
        // Clicks change what's drawn only from the next frame, so IMGUI's layout and draw passes agree.
        if (nextCategory != null) { category = nextCategory; nextCategory = null; scroll = Vector2.zero; }
        if (nextMessage != null) { message = nextMessage; nextMessage = null; }
        if (nextShowPassive != showPassive) { showPassive = nextShowPassive; category = "All"; scroll = Vector2.zero; }
        if (nextHintsView != hintsView) { hintsView = nextHintsView; scroll = Vector2.zero; }
        if (nextShowFound != showFound) { showFound = nextShowFound; scroll = Vector2.zero; }
        if (IsOpen && Time.unscaledTime >= nextRefresh)
        {
            nextRefresh = Time.unscaledTime + RefreshSeconds;
            (inLogic, outOfLogic) = ArchipelagoLinks.Connected ? ArchipelagoLogic.Missing() : (new List<string>(), 0);
        }
    }

    private void LateUpdate()
    {
        if (!IsOpen) return;
        ZCursor.LockState = CursorLockMode.None;
        ZCursor.Show();
    }

    private void SetOpen(bool open)
    {
        if (open == IsOpen) return;
        IsOpen = open;
        nextRefresh = 0f;
        message = "";
        if (!open && !InventoryGui.IsVisible() && !Menu.IsVisible())
        {
            ZCursor.LockState = CursorLockMode.Locked;
            ZCursor.Hide();
        }
    }

    private void OnGUI()
    {
        if (!IsOpen) return;
        string title = hintsView ? $"Archipelago: {ArchipelagoLinks.Hints.Count(h => !h.Found)} hints not found yet"
            : $"Archipelago: {inLogic.Count} checks you can do now";
        window = GUILayout.Window(GetInstanceID(), window, Draw, title);
    }

    private void Draw(int id)
    {
        if (!ArchipelagoLinks.Connected)
        {
            GUILayout.Label("Not connected to Archipelago.");
        }
        else
        {
            var hints = ArchipelagoLinks.Hints;
            int view = GUILayout.Toolbar(hintsView ? 1 : 0, new[] { $"Checks ({inLogic.Count})", $"Hints ({hints.Count(h => !h.Found)} to find)" });
            if ((view == 1) != hintsView) nextHintsView = view == 1;
            if (hintsView) DrawHints(hints);
            else DrawChecks();
        }
        GUILayout.BeginHorizontal();
        GUILayout.Label($"{ValheimRandomizer.logicWindowKey.Value} or Close closes it.");
        GUILayout.FlexibleSpace();
        if (GUILayout.Button("Close", GUILayout.Width(80))) SetOpen(false);
        GUILayout.EndHorizontal();
        GUI.DragWindow(new Rect(0, 0, 10000, 22));
    }

    private void DrawChecks()
    {
        var shown = inLogic.Where(n => showPassive || !Passive.Contains(ArchipelagoLinks.Category(n))).ToList();
        var categories = new[] { "All" }.Concat(shown.GroupBy(ArchipelagoLinks.Category).OrderByDescending(g => g.Count())
            .ThenBy(g => g.Key).Select(g => g.Key)).ToArray();
        int selected = Math.Max(0, Array.IndexOf(categories, category));
        int clicked = GUILayout.SelectionGrid(selected, categories.Select(c => c == "All" ? $"All ({shown.Count})" :
            $"{c} ({shown.Count(n => ArchipelagoLinks.Category(n) == c)})").ToArray(), 5);
        if (clicked != selected) nextCategory = categories[clicked];
        bool passive = GUILayout.Toggle(showPassive, $" Also show skill, exploration and comfort checks ({inLogic.Count - inLogic.Count(n => !Passive.Contains(ArchipelagoLinks.Category(n)))}; they come as you play)");
        if (passive != showPassive) nextShowPassive = passive;

        scroll = GUILayout.BeginScrollView(scroll, GUILayout.Height(400));
        foreach (var name in shown.Where(n => category == "All" || ArchipelagoLinks.Category(n) == category))
        {
            GUILayout.BeginHorizontal();
            // In a kind's own tab, "Obtain: Flint" reads as "Flint".
            GUILayout.Label(category != "All" && name.Contains(": ") ? name.Substring(name.IndexOf(": ", StringComparison.Ordinal) + 2) : name);
            GUILayout.FlexibleSpace();
            if (GUILayout.Button("Hint", GUILayout.Width(60)))
            {
                ArchipelagoLinks.Say("!hint_location " + name);
                nextMessage = $"Asked for a hint on {name} (costs hint points). It shows in the Hints tab.";
            }
            GUILayout.EndHorizontal();
        }
        GUILayout.EndScrollView();
        GUILayout.Label(message);  // always drawn (maybe empty), so the layout doesn't change
        GUILayout.Label(ArchipelagoLogic.Next.Count > 0 ? ArchipelagoLogic.NextLine() : "");
    }

    private void DrawHints(List<ArchipelagoLinks.HintRow> hints)
    {
        bool show = GUILayout.Toggle(showFound, $" Also show hints already found ({hints.Count(h => h.Found)})");
        if (show != showFound) nextShowFound = show;
        scroll = GUILayout.BeginScrollView(scroll, GUILayout.Height(440));
        if (hints.Count == 0) GUILayout.Label("No hints yet. Ask for one with a check's Hint button, !hint <item> in chat, or /ap shop hint at a trader.");
        // Not found first; then items for you before the ones your checks hold for others.
        foreach (var h in hints.Where(h => showFound || !h.Found).OrderBy(h => h.Found).ThenByDescending(h => h.ForMe)
                     .ThenByDescending(h => h.Status == "priority"))
        {
            GUILayout.BeginHorizontal();
            GUILayout.Label(h.Found ? "found" : h.ForMe ? "to find" : "to send", GUILayout.Width(55));
            GUILayout.Label(h.Text);
            GUILayout.FlexibleSpace();
            GUILayout.Label(h.Status, GUILayout.Width(70));
            GUILayout.EndHorizontal();
        }
        GUILayout.EndScrollView();
        GUILayout.Label("\"Your ...\" hints are checks of yours that hold someone else's item.");
    }
}
