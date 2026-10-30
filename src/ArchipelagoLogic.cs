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

    // The seed's missing checks split into in logic and not, by category ("Obtain", "Research"...).
    public static (List<string> inLogic, int outOfLogic) Missing(string category = null)
    {
        cache.Clear();
        var inLogic = new List<string>();
        int outOfLogic = 0;
        if (ZoneSystem.instance == null) return (inLogic, 0);
        foreach (var name in ArchipelagoLinks.MissingNames())
        {
            if (category != null && !string.Equals(ArchipelagoLinks.Category(name), category, StringComparison.OrdinalIgnoreCase)) continue;
            if (InLogic(name)) inLogic.Add(name); else outOfLogic++;
        }
        inLogic.Sort(StringComparer.Ordinal);
        return (inLogic, outOfLogic);
    }
}

// The logic panel: the checks in logic now, by category, on the right of the screen while a world is loaded.
public class ArchipelagoLogicPanel : MonoBehaviour
{
    private const int NamesPerCategory = 6;
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

    private static string Build()
    {
        if (!ArchipelagoLinks.Connected) return "Archipelago: not connected.";
        var (inLogic, outOfLogic) = ArchipelagoLogic.Missing();
        var lines = new List<string> { $"In logic now: {inLogic.Count}   (not yet: {outOfLogic})" };
        foreach (var group in inLogic.GroupBy(ArchipelagoLinks.Category).OrderBy(g => g.Key))
        {
            var names = group.Select(n => n.Contains(": ") ? n.Substring(n.IndexOf(": ", StringComparison.Ordinal) + 2) : n).ToList();
            lines.Add($"{group.Key} ({names.Count}): " + string.Join(", ", names.Take(NamesPerCategory)) +
                      (names.Count > NamesPerCategory ? $", +{names.Count - NamesPerCategory} more" : ""));
        }
        lines.Add("/ap logic <category> lists a category.");
        return string.Join("\n", lines);
    }

    private void OnGUI()
    {
        if (!open || Player.m_localPlayer == null) return;
        if (style == null)
        {
            style = new GUIStyle(GUI.skin.box) { alignment = TextAnchor.UpperLeft, wordWrap = true, fontSize = 14 };
            style.normal.textColor = Color.white;
        }
        float width = Mathf.Min(520f, Screen.width * 0.4f);
        var content = new GUIContent("Archipelago logic (" + ValheimRandomizer.logicPanelKey.Value + ")\n" + text);
        float height = style.CalcHeight(content, width);
        GUI.Box(new Rect(Screen.width - width - 16f, 80f, width, height), content, style);
    }
}
