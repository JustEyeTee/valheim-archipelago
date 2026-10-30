from dataclasses import dataclass

from Options import Choice, PerGameCommonOptions


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


@dataclass
class ValheimOptions(PerGameCommonOptions):
    goal: Goal
