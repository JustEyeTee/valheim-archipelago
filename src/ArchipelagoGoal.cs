using System;
using System.Collections.Generic;
using System.Linq;
using Newtonsoft.Json.Linq;

// The room's goal: one or more conditions (defeat the goal boss, collect trophies, return Hildir's
// chests...), all of which have to be done to win. Each comes from the slot data as its targets and
// how many of them are needed. Rooms from before goal conditions send none; for those, picking up
// the goal trophy wins.
internal static class ArchipelagoGoal
{
    public const string RelicName = "Forsaken Relic";

    // Skill Master: the level is kept in the world, so co-op players' mods (which aren't connected and
    // have no slot data) mark their skills too. A skill that reached it gets its own key.
    private const string SkillLevelKey = "ap_goal_skill_level";
    private const string SkillKey = "ap_goal_skill:";

    private static readonly Dictionary<string, string> HildirQuests = new Dictionary<string, string>
    {
        { "Hildir1", "Smouldering Tomb" }, { "Hildir2", "Howling Cavern" }, { "Hildir3", "Sealed Tower" },
    };

    private class Condition
    {
        public string Name;
        public List<string> Targets;
        public int Needed;
        public int Progress = -1; // last count seen; -1 until the first check after connecting
    }

    private static readonly List<Condition> conditions = new List<Condition>();
    private static int skillLevel;

    public static bool HasConditions => conditions.Count > 0;

    public static void Load(Dictionary<string, object> slotData)
    {
        conditions.Clear();
        skillLevel = 0;
        if (slotData == null || !slotData.TryGetValue("goal", out var raw) || raw == null) return;
        try
        {
            var goal = raw as JObject ?? JObject.FromObject(raw);
            var targets = goal["targets"] as JObject;
            var needed = goal["needed"] as JObject;
            foreach (var name in goal["conditions"].Values<string>())
            {
                conditions.Add(new Condition
                {
                    Name = name,
                    Targets = targets?[name]?.Values<string>().ToList() ?? new List<string>(),
                    Needed = needed?[name]?.Value<int>() ?? 1,
                });
            }
            skillLevel = goal["skill_level"]?.Value<int>() ?? 0;
        }
        catch (Exception ex)
        {
            ValheimRandomizer.Log.LogWarning("[AP] Couldn't read the goal from the slot data: " + ex.Message);
            conditions.Clear();
        }
        ValheimRandomizer.Log.LogInfo("[AP] Goal: " + string.Join(", ", conditions.Select(c => $"{c.Name} ({c.Needed})")));
    }

    private static int Count(Condition condition, Func<string, int> received)
    {
        switch (condition.Name)
        {
            case "Relic Hunt":
                return received(RelicName);
            case "Skill Master":
                return condition.Targets.Count(t => ArchipelagoExtras.SkillOf(t) is Skills.SkillType skill &&
                                                    ZoneSystem.instance.GetGlobalKey(SkillKey + skill.ToString().ToLowerInvariant()));
            case "Hildir's Quests":
                return condition.Targets.Count(key => ZoneSystem.instance.GetGlobalKey(key));
            default:
                // Goal Boss, All Bosses, Trophy Hunt, Researcher, Explorer: checks (sent or waiting to be).
                return condition.Targets.Count(ArchipelagoConnection.IsLocationDone);
        }
    }

    // Called every couple of seconds while connected with a world loaded: shows progress and sends the
    // goal once every condition is done.
    public static void Check(Func<string, int> received)
    {
        if (!HasConditions || ZoneSystem.instance == null) return;
        var player = Player.m_localPlayer;

        if (skillLevel > 0 && (!ZoneSystem.instance.GetGlobalKey(SkillLevelKey, out var level) || level != skillLevel.ToString()))
        {
            ZoneSystem.instance.SetGlobalKey($"{SkillLevelKey} {skillLevel}");
        }

        int done = 0;
        foreach (var condition in conditions)
        {
            int count = Count(condition, received);
            if (condition.Progress >= 0 && count > condition.Progress && condition.Progress < condition.Needed && player != null)
            {
                if (count >= condition.Needed)
                {
                    player.Message(MessageHud.MessageType.Center, $"Goal: {condition.Name} done!");
                }
                else
                {
                    player.Message(MessageHud.MessageType.TopLeft, $"Goal: {condition.Name} {count}/{condition.Needed}");
                }
            }
            condition.Progress = count;
            if (count >= condition.Needed) done++;
        }
        if (done == conditions.Count) ArchipelagoConnection.CompleteGame();
    }

    // Skill Master: marks each skill of the local player at the goal's level (any player with the mod).
    public static void MarkSkills(Player player)
    {
        if (ZoneSystem.instance == null || !ZoneSystem.instance.GetGlobalKey(SkillLevelKey, out var value) ||
            !int.TryParse(value, out var level) || level <= 0) return;
        foreach (var skill in player.GetSkills().GetSkillList())
        {
            var type = skill.m_info.m_skill;
            var key = SkillKey + type.ToString().ToLowerInvariant();
            if (!ZoneSystem.instance.GetGlobalKey(key) && player.GetSkills().GetSkillLevel(type) >= level)
            {
                ZoneSystem.instance.SetGlobalKey(key);
            }
        }
    }

    // For /ap goal.
    public static string Status(Func<string, int> received)
    {
        if (!HasConditions) return "Goal: pick up " + ArchipelagoConnection.GoalTrophy + ".";
        if (ZoneSystem.instance == null) return "Goal: load your world to see your progress.";
        var lines = new List<string> { conditions.Count == 1 ? "Goal:" : $"Goal (all {conditions.Count} of these):" };
        foreach (var condition in conditions)
        {
            int count = Count(condition, received);
            string line = $"  {condition.Name}: {Math.Min(count, condition.Needed)}/{condition.Needed}";
            if (count >= condition.Needed) line += " (done)";
            else if (condition.Name == "Skill Master") line += $" skills at level {skillLevel}";
            else if (condition.Name == "Explorer") line += $" ({condition.Targets[0].Replace("Explore: ", "")})";
            else if (condition.Name == "Great Hall")
                line += $" (comfort {condition.Targets[0].Replace("Comfort: Level ", "")}; here: " +
                        (Player.m_localPlayer ? SE_Rested.CalculateComfortLevel(Player.m_localPlayer).ToString() : "?") + ")";
            else if (condition.Name == "Hildir's Quests")
                line += " left: " + string.Join(", ", condition.Targets.Where(k => !ZoneSystem.instance.GetGlobalKey(k))
                    .Select(k => HildirQuests.TryGetValue(k, out var place) ? place : k));
            else if (condition.Name == "All Bosses" || condition.Name == "Goal Boss")
                line += " left: " + string.Join(", ", condition.Targets.Where(t => !ArchipelagoConnection.IsLocationDone(t))
                    .Select(BossName));
            lines.Add(line);
        }
        return string.Join("\n", lines);
    }

    private static readonly Dictionary<string, string> BossTrophies = new Dictionary<string, string>
    {
        { "TrophyEikthyr", "Eikthyr" }, { "TrophyTheElder", "The Elder" }, { "TrophyBonemass", "Bonemass" },
        { "TrophyDragonQueen", "Moder" }, { "TrophyGoblinKing", "Yagluth" }, { "TrophySeekerQueen", "The Queen" },
        { "TrophyFader", "Fader" },
    };

    private static string BossName(string location)
    {
        if (location == "Obtain: Sacrificial Blood") return "Kall Fimbulbringer";
        var trophy = location.Replace("Trophy: ", "");
        return BossTrophies.TryGetValue(trophy, out var boss) ? boss : trophy;
    }
}
