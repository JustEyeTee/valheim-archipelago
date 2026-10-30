from dataclasses import dataclass

from Options import Choice, NamedRange, PerGameCommonOptions, Toggle


class Goal(Choice):
    """
    The boss you must defeat to win. You win when you pick up that boss's trophy.
    Earlier bosses make a shorter game; Fader is the full game.
    """
    display_name = "Goal"
    option_eikthyr = 0
    option_the_elder = 1
    option_bonemass = 2
    option_moder = 3
    option_yagluth = 4
    option_the_queen = 5
    option_fader = 6
    default = option_fader


# Goal option -> (boss name, trophy prefab the mod watches for)
GOAL_BOSSES = {
    Goal.option_eikthyr: ("Eikthyr", "TrophyEikthyr"),
    Goal.option_the_elder: ("The Elder", "TrophyTheElder"),
    Goal.option_bonemass: ("Bonemass", "TrophyBonemass"),
    Goal.option_moder: ("Moder", "TrophyDragonQueen"),
    Goal.option_yagluth: ("Yagluth", "TrophyGoblinKing"),
    Goal.option_the_queen: ("The Queen", "TrophySeekerQueen"),
    Goal.option_fader: ("Fader", "TrophyFader"),
}


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


class IncludeDeepNorth(Toggle):
    """
    Adds the Deep North (after Ashlands) as a final tier: a Frost Foundry research to get
    there, 19 Deep North researches (Nord weapons and armor, Timber buildings, new station
    upgrades) and 9 Deep North trophies. Only applies when the goal is Fader.
    """
    display_name = "Include Deep North"


@dataclass
class ValheimOptions(PerGameCommonOptions):
    goal: Goal
    research_cost_percent: ResearchCostPercent
    include_deep_north: IncludeDeepNorth
