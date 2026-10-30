from dataclasses import dataclass

from Options import Choice, DeathLink, DefaultOnToggle, NamedRange, OptionGroup, OptionSet, PerGameCommonOptions, Range, Toggle


class Goal(Choice):
    """
    How far the game goes: the boss whose era ends it. Kall Fimbulbringer, in the Deep North, is
    the full game; Fader ends it after the Ashlands, and earlier bosses make shorter games. Only
    checks and items up to this era are in the game. By default you win by defeating this boss
    (you win when you pick up its trophy; Kall Fimbulbringer has none, so his Sacrificial
    Blood); goal_conditions can change or add to what you have to do.
    """
    display_name = "Goal"
    option_eikthyr = 0
    option_the_elder = 1
    option_bonemass = 2
    option_moder = 3
    option_yagluth = 4
    option_the_queen = 5
    option_fader = 6
    option_kall_fimbulbringer = 7
    default = option_kall_fimbulbringer


# Goal option -> (boss name, trophy prefab the mod watches for)
GOAL_BOSSES = {
    Goal.option_eikthyr: ("Eikthyr", "TrophyEikthyr"),
    Goal.option_the_elder: ("The Elder", "TrophyTheElder"),
    Goal.option_bonemass: ("Bonemass", "TrophyBonemass"),
    Goal.option_moder: ("Moder", "TrophyDragonQueen"),
    Goal.option_yagluth: ("Yagluth", "TrophyGoblinKing"),
    Goal.option_the_queen: ("The Queen", "TrophySeekerQueen"),
    Goal.option_fader: ("Fader", "TrophyFader"),
    Goal.option_kall_fimbulbringer: ("Kall Fimbulbringer", "FrozenKingDrop"),
}


class GoalConditions(OptionSet):
    """
    What you have to do to win, within the goal's era. Pick any combination: you win once all of
    them are done. Leave it empty to just defeat the goal boss.
    Goal Boss: defeat the goal boss.
    All Bosses: defeat every boss in the era (any order).
    Relic Hunt: receive relic_hunt_percent of the relic_hunt_total Forsaken Relics spread
      through the multiworld.
    Trophy Hunt: collect trophy_hunt_percent of the trophies you can get in the era.
    Researcher: craft researcher_percent of the researches in the era.
    Explorer: uncover explorer_percent of the world map.
    Skill Master: raise skill_master_count skills to skill_master_level (from the skills you can
      train in the era).
    Hildir's Quests: return each chest Hildir asks for that's in the era (from The Elder's era
      on: the Smouldering Tomb; then the Howling Cavern in the Mountains; then the Sealed Tower in
      the Plains).
    A condition with nothing to do in the era (Hildir's Quests in an Eikthyr game) is dropped.
    """
    display_name = "Goal Conditions"
    valid_keys = ["Goal Boss", "All Bosses", "Relic Hunt", "Trophy Hunt", "Researcher", "Explorer",
                  "Skill Master", "Hildir's Quests"]
    default = frozenset({"Goal Boss"})


class RelicHuntTotal(Range):
    """
    Relic Hunt: how many Forsaken Relics are placed in the multiworld (they take the place of filler).
    """
    display_name = "Relic Hunt Total"
    range_start = 1
    range_end = 50
    default = 20


class RelicHuntPercent(Range):
    """
    Relic Hunt: the percentage of the relics you have to receive (rounded up).
    """
    display_name = "Relic Hunt Percent"
    range_start = 1
    range_end = 100
    default = 75


class TrophyHuntPercent(Range):
    """
    Trophy Hunt: the percentage of the trophies you can get in the goal's era (creatures and bosses) that
    you have to collect (rounded up).
    """
    display_name = "Trophy Hunt Percent"
    range_start = 1
    range_end = 100
    default = 50


class ResearcherPercent(Range):
    """
    Researcher: the percentage of the goal era's researches you have to craft (rounded up).
    """
    display_name = "Researcher Percent"
    range_start = 1
    range_end = 100
    default = 75


class ExplorerPercent(Range):
    """
    Explorer: how much of the world map you have to uncover, in percent. Walking 1 km uncovers about
    0.06% of the world; sailing is faster. Larger percentages need a boat in logic.
    """
    display_name = "Explorer Percent"
    range_start = 1
    range_end = 20
    default = 5


class SkillMasterCount(Range):
    """
    Skill Master: how many skills you have to raise to skill_master_level. Lowered to the number of skills
    you can train in the goal's era if it's more.
    """
    display_name = "Skill Master Count"
    range_start = 1
    range_end = 24
    default = 5


class SkillMasterLevel(Range):
    """
    Skill Master: the level those skills have to reach.
    """
    display_name = "Skill Master Level"
    range_start = 1
    range_end = 100
    default = 50


class ResearchCostPercent(NamedRange):
    """
    Scales how many materials each research costs at the Research Bench, as a percentage.
    Every ingredient still costs at least 1, so 1 makes every research cost 1 of each.
    """
    display_name = "Research Cost Percent"
    range_start = 1
    range_end = 200
    default = 100
    special_range_names = {
        "minimal": 1,
        "quarter": 25,
        "half": 50,
        "normal": 100,
        "double": 200,
    }


class BiomeChecks(DefaultOnToggle):
    """
    Adds a check for entering each biome for the first time (Black Forest, Swamp, Mountains,
    Ocean, Plains, Mistlands, Ashlands, and Deep North in a Kall game), up to the goal's tier.
    These checks are filled with resource bundles and traps; bundles arrive in an
    Archipelago Chest you build with the Hammer.
    """
    display_name = "Biome Checks"


class ObtainChecks(DefaultOnToggle):
    """
    Adds a check for getting each of 93 materials and ingredients for the first time, by
    picking it up or crafting it (Flint, Copper Ore, Bronze, Silver, Black Metal...), up to the
    goal's tier. These checks are filled with resource bundles and traps.
    """
    display_name = "Obtain Checks"


class ExplorationChecks(NamedRange):
    """
    Adds checks for exploring the world map, up to this percentage of the world (0 turns them off),
    spaced by exploration_check_spacing. Walking 1 km uncovers about 0.06% of the world; sailing is
    faster. Larger percentages come later in logic, and checks past 6% never hold progression items.
    """
    display_name = "Exploration Checks"
    range_start = 0
    range_end = 20
    default = 6
    special_range_names = {"off": 0, "light": 2, "normal": 6, "far": 10, "everything": 20}


class ExplorationCheckSpacing(Choice):
    """
    How far apart exploration checks are.
    half_percent: 0.25%, then every half percent.
    one_percent: 0.25%, 0.5%, then every percent.
    two_percent: 0.5%, 1%, then every second percent.
    """
    display_name = "Exploration Check Spacing"
    option_half_percent = 0
    option_one_percent = 1
    option_two_percent = 2
    default = option_one_percent


class KillChecks(Toggle):
    """
    Adds a check for the first kill of each kind of creature (Neck, Greydwarf, Troll, Draugr,
    Wolf, Lox, Seeker, Morgen...), up to the goal's tier. Bosses are left out, since their
    trophies already are checks. These checks are filled with resource bundles and traps.
    """
    display_name = "Kill Checks"


class SkillChecks(NamedRange):
    """
    Adds checks for raising each skill (Woodcutting, Swords, Running, Fishing...) up to this level (skills
    go to 100; 0 turns these checks off), spaced by skill_check_spacing. Each skill's checks start once you
    can train it: Pickaxes after Eikthyr's antler, Farming once you have the Cultivator (bronze), Riding in
    the Plains, magic in the Mistlands. Skill checks above level 30 never hold progression items.
    """
    display_name = "Skill Checks"
    range_start = 0
    range_end = 100
    default = 20
    special_range_names = {"off": 0, "level_10": 10, "level_20": 20, "level_30": 30, "level_50": 50, "level_100": 100}


class SkillCheckSpacing(Choice):
    """
    Which skill levels are checks: every 10 levels (10, 20, 30...), every 20 levels (20, 40, 60...) or every
    25 levels (25, 50, 75, 100).
    """
    display_name = "Skill Check Spacing"
    option_every_10 = 0
    option_every_20 = 1
    option_every_25 = 2
    default = option_every_10


class DiscoveryChecks(DefaultOnToggle):
    """
    Adds a check for reaching each kind of dungeon and landmark for the first time: Burial
    Chamber, Troll Cave, Sunken Crypt, Frost Cave, Fuling Village, Infested Mine, Charred
    Fortress, the traders and every boss altar, up to the goal's tier.
    """
    display_name = "Discovery Checks"


class BuildChecks(DefaultOnToggle):
    """
    Adds a check for placing each crafting station, boat and portal for the first time
    (Workbench, Forge, Smelter, Karve, Portal, Blast Furnace, Galdr Table...: 29 kinds), up to
    the goal's tier.
    """
    display_name = "Build Checks"


class EatChecks(DefaultOnToggle):
    """
    Adds a check for eating each of 51 foods for the first time, from Raspberries to Lox Meat
    Pie, up to the goal's tier.
    """
    display_name = "Eat Checks"


class FishingChecks(DefaultOnToggle):
    """
    Adds a check for catching each of the 12 kinds of fish, up to the goal's tier. A fishing
    rod and bait are sold by Haldor; biome bait is made at the Food Preparation Table.
    """
    display_name = "Fishing Checks"


class TamingChecks(DefaultOnToggle):
    """
    Adds a check for taming each tameable animal: Boar, Wolf, Lox, Hen, Asksvin and Moose, up
    to the goal's tier.
    """
    display_name = "Taming Checks"


class TraderChecks(DefaultOnToggle):
    """
    Adds a check for buying each of 14 items from Haldor and Hildir (Fishing Rod, Megingjord,
    Ymir Flesh, Egg...), up to the goal's tier.
    """
    display_name = "Trader Checks"


class BossItems(DefaultOnToggle):
    """
    Puts the drops of the bosses before your goal into the item pool, delivered to your
    Archipelago Chest: Hard Antler (Eikthyr), Swamp Key (The Elder), Wishbone (Bonemass),
    3 Dragon Tears (Moder), Torn Spirit (Yagluth) and Majestic Carapace (The Queen). Logic
    then lets you use either the boss kill or the received drop, so another player can
    open the Sunken Crypts for you. Haldor's boss-unlocked stock still needs the kill.
    """
    display_name = "Boss Items"


class GearItems(DefaultOnToggle):
    """
    Puts tools from your goal's era into the item pool (one each), delivered to your
    Archipelago Chest: Flint Axe, Antler Pickaxe, Bronze, Iron and Black Metal Axe and
    Pickaxe. Resource bundles also include your era's metals and woods (Copper, Bronze,
    Iron, Silver, Black Metal...), never past your goal.
    """
    display_name = "Gear Items"


class StarterKit(DefaultOnToggle):
    """
    Start with a Club, a Stone Axe, a Torch and 10 Raspberries in your inventory.
    """
    display_name = "Starter Kit"


class CombatLogic(Choice):
    """
    Whether logic expects you to be equipped for each fight before sending you into it: entering
    the Swamp, Mountains, Plains, Mistlands, Ashlands and Deep North, and fighting each boss, need
    armor and a weapon from the era before (Black Forest armor and weapons for the Swamp, iron gear
    for the Mountains, and so on).
    off: only tools, stations and boss drops count.
    normal: armor and a weapon.
    strict: armor, a weapon, and a bow or crossbow.
    """
    display_name = "Combat Logic"
    option_off = 0
    option_normal = 1
    option_strict = 2
    default = option_normal


class TrapPercentage(Range):
    """
    Percentage of the extra items (the items beyond one per research and trophy) that are
    traps instead of resource bundles. See excluded_traps for the list.
    """
    display_name = "Trap Percentage"
    range_start = 0
    range_end = 100
    default = 20


class ExcludedTraps(OptionSet):
    """
    Traps that are never placed. The traps:
    Greydwarf Ambush Trap, Skeleton Ambush Trap: 3 of them spawn around you.
    Monster Pack Trap: a pack of whatever lives in the biome you're in (Draugr in the Swamp,
      Wolves in the Mountains, Fulings in the Plains...).
    Bat Swarm Trap: 6 bats.
    Raid Trap: a raid you're ready for starts (only when you host the world).
    Thunderstorm Trap, Blizzard Trap: 2 minutes of storm or freezing snowstorm.
    Lightning Strike Trap: lightning hits where you stand.
    Floor Is Lava Trap: for 30 seconds the ground burns you; stand on something you built
      (or a boat), or keep jumping.
    Burning Trap, Poison Trap, Frost Trap: damage over time (Frost also slows you).
    Soaked Trap: you're wet. Tar Trap: you're covered in tar and slowed.
    Famine Trap: your food is gone. Butterfingers Trap: everything is unequipped.
    Heavy Load Trap: 50 Stone in your pockets. Launch Trap: you're thrown into the air.
    Rust Trap: your equipped gear loses half its durability.
    Meteor Shower Trap: an Ashlands meteor shower for a minute, wherever you are.
    Fake Item Trap: a message that you received an item; nothing arrives.
    """
    display_name = "Excluded Traps"
    valid_keys = frozenset({
        "Greydwarf Ambush Trap", "Skeleton Ambush Trap", "Monster Pack Trap", "Bat Swarm Trap", "Raid Trap",
        "Thunderstorm Trap", "Blizzard Trap", "Lightning Strike Trap", "Floor Is Lava Trap", "Burning Trap",
        "Poison Trap", "Frost Trap", "Soaked Trap", "Tar Trap", "Famine Trap", "Butterfingers Trap",
        "Heavy Load Trap", "Launch Trap", "Rust Trap", "Meteor Shower Trap", "Fake Item Trap",
    })


class BoostPercentage(Range):
    """
    Percentage of the extra items that are boosts instead of resource bundles: Combat,
    Woodcutting and Mining Training (+5 skill levels) and Rested, Eikthyr's and Moder's
    Blessings (a timed buff). Traps are taken first, then boosts, and the rest are bundles.
    """
    display_name = "Boost Percentage"
    range_start = 0
    range_end = 100
    default = 20


class DeathLinkMode(Choice):
    """
    What happens to you when someone else's Death Link arrives.
    kill: you die (and lose skills and drop your items, as with any death).
    wounded: your health drops to 1.
    trap: a random trap goes off instead.
    """
    display_name = "Death Link Mode"
    option_kill = 0
    option_wounded = 1
    option_trap = 2
    default = option_kill


class DeathLinkAmnesty(Range):
    """
    How many of your own deaths are forgiven before one is sent out over Death Link. 0 sends
    every death; 2 sends every third death.
    """
    display_name = "Death Link Amnesty"
    range_start = 0
    range_end = 10
    default = 0


class TrapLink(Toggle):
    """
    Trap Link: when you receive a trap it is also sent to the other Trap Link games in the
    multiworld, and their traps reach you (as the closest Valheim trap; unknown traps are
    ignored).
    """
    display_name = "Trap Link"


@dataclass
class ValheimOptions(PerGameCommonOptions):
    goal: Goal
    goal_conditions: GoalConditions
    relic_hunt_total: RelicHuntTotal
    relic_hunt_percent: RelicHuntPercent
    trophy_hunt_percent: TrophyHuntPercent
    researcher_percent: ResearcherPercent
    explorer_percent: ExplorerPercent
    skill_master_count: SkillMasterCount
    skill_master_level: SkillMasterLevel
    research_cost_percent: ResearchCostPercent
    combat_logic: CombatLogic
    biome_checks: BiomeChecks
    obtain_checks: ObtainChecks
    exploration_checks: ExplorationChecks
    exploration_check_spacing: ExplorationCheckSpacing
    kill_checks: KillChecks
    skill_checks: SkillChecks
    skill_check_spacing: SkillCheckSpacing
    discovery_checks: DiscoveryChecks
    build_checks: BuildChecks
    eat_checks: EatChecks
    fishing_checks: FishingChecks
    taming_checks: TamingChecks
    trader_checks: TraderChecks
    boss_items: BossItems
    gear_items: GearItems
    starter_kit: StarterKit
    trap_percentage: TrapPercentage
    excluded_traps: ExcludedTraps
    boost_percentage: BoostPercentage
    death_link: DeathLink
    death_link_mode: DeathLinkMode
    death_link_amnesty: DeathLinkAmnesty
    trap_link: TrapLink


# How the options are grouped on the website and in generated templates.
option_groups = [
    OptionGroup("Goal", [Goal, GoalConditions, RelicHuntTotal, RelicHuntPercent, TrophyHuntPercent, ResearcherPercent,
                         ExplorerPercent, SkillMasterCount, SkillMasterLevel, ResearchCostPercent, CombatLogic]),
    OptionGroup("Checks", [BiomeChecks, ObtainChecks, ExplorationChecks, ExplorationCheckSpacing, KillChecks,
                           SkillChecks, SkillCheckSpacing, DiscoveryChecks,
                           BuildChecks, EatChecks, FishingChecks, TamingChecks, TraderChecks]),
    OptionGroup("Items", [BossItems, GearItems, StarterKit, BoostPercentage]),
    OptionGroup("Traps", [TrapPercentage, ExcludedTraps]),
    OptionGroup("Links", [DeathLink, DeathLinkMode, DeathLinkAmnesty, TrapLink]),
]

options_presets = {
    "Quick Eikthyr run": {"goal": "eikthyr", "research_cost_percent": 25},
    "The Elder run": {"goal": "the_elder", "research_cost_percent": 50},
    "Full game": {"goal": "kall_fimbulbringer"},
    "Relic hunt to Moder": {"goal": "moder", "goal_conditions": ["Relic Hunt"]},
    "Trophy and Hildir hunt to Yagluth": {"goal": "yagluth", "goal_conditions": ["Trophy Hunt", "Hildir's Quests"]},
    "Full game with every check": {"goal": "kall_fimbulbringer", "kill_checks": True, "skill_checks": 100,
                                   "exploration_checks": 20},
}
