import logging
import math
from typing import Any, Callable, Dict, List

from BaseClasses import Item, ItemClassification, Location, LocationProgressType, Tutorial
from worlds.AutoWorld import WebWorld, World
from worlds.generic.Rules import add_rule

from .Regions import create_regions, region_data_table
from .Locations import create_locations, location_table, location_data_table
from .Items import create_items, item_table, item_data_table, PROGRESSIVE_FAMILIES
from .Options import (ValheimOptions, CombatLogic, ExplorationCheckSpacing, GoalConditions, SkillCheckSpacing,
                      GOAL_BOSSES, option_groups, options_presets)
from .combat_data import COMBAT_ERAS, COMBAT_GATES, COMBAT_ITEMS
from .research_data import RESEARCH_PREREQS
from .check_data import CHECKS
from .comfort_data import COMFORT_PIECES, SHELTER
from .boss_data import BOSS_ORDER, RESEARCH_COST_BOSSES, RESEARCH_USE_BOSSES, CHECK_BOSSES

# Location -> research items it needs beyond its tier: research prerequisites, and the
# stations some obtain checks need (Bloodgold needs the Frost Foundry).
CHECK_REQS = {name: reqs for _, name, _, reqs in CHECKS if reqs}
# Serpents are out at sea, which needs a real boat: the Karve (a Raft won't get you there).
CHECK_REQS["Trophy: TrophySerpent"] = ("Boat Tier 2",)
LOCATION_REQS = {**RESEARCH_PREREQS, **CHECK_REQS}

# Boss -> the location its defeat is an event at ("Eikthyr Defeated"): its trophy, or for Kall
# Fimbulbringer, who has none, picking up his Sacrificial Blood.
BOSS_TROPHIES = {boss: f"Trophy: {trophy}" for boss, trophy in GOAL_BOSSES.values()}
BOSS_TROPHIES["Kall Fimbulbringer"] = "Obtain: Sacrificial Blood"


def bosses_to_use(items) -> set:
    return {boss for item in items for boss in RESEARCH_USE_BOSSES.get(item, ())}


# The Sunken Crypts open with The Elder's Swamp Key: Bonemass's altar takes their Withered Bones, and
# Bonemass's Vegvisir and the crypt chests are inside.
# Raids come once the boss is actually dead (its drop as an item doesn't count): kill: tokens.
EXTRA_BOSSES = {"Trophy: TrophyBonemass": {"The Elder"}, "Vegvisir: Bonemass": {"The Elder"},
                "Loot: Sunken Crypt": {"The Elder"}, "Survive: Troll Raid": {"kill:The Elder"},
                **{f"Survive: {raid} Raid": {"kill:Bonemass"} for raid in ("Blob", "Ghost", "Skeleton", "Surtling", "Wolf")}}

# Location -> bosses that must be defeated first (their drops go into it): a research's cost,
# an item to obtain, the unlocks a check's required research gives, and EXTRA_BOSSES.
LOCATION_BOSSES = {
    location.user_friendly_name: frozenset(
        set(RESEARCH_COST_BOSSES.get(location.user_friendly_name, ()))
        | set(CHECK_BOSSES.get(location.user_friendly_name, ()))
        | bosses_to_use(CHECK_REQS.get(location.user_friendly_name, ()))
        | EXTRA_BOSSES.get(location.user_friendly_name, set()))
    for location in location_data_table
}

# Region -> bosses its entrance needs (to use the research items it requires), and the
# same summed along the chain of tiers up to it.
ENTRANCE_BOSSES = {connection.destination: frozenset(bosses_to_use(connection.required_items))
                   for region in region_data_table.values() for connection in region.connections}
REGION_BOSSES = {}
_region, _bosses = "Menu", frozenset()
while True:
    REGION_BOSSES[_region] = _bosses
    _next = region_data_table[_region].connections
    if not _next:
        break
    _region = _next[0].destination
    _bosses = _bosses | ENTRANCE_BOSSES[_region]

# Every item some rule depends on: location requirements and the region (tier) gates.
LOGIC_ITEMS = frozenset(
    {name for reqs in LOCATION_REQS.values() for name in reqs}
    | {name for region in region_data_table.values()
       for connection in region.connections for name in connection.required_items}
)


TRACKER_OPTIONS = ("goal", "progressive_items", "boss_altar_keys", "goal_conditions", "explorer_percent", "great_hall_comfort", "comfort_checks", "combat_logic", "boss_items", "biome_checks",
                   "obtain_checks", "exploration_checks",
                   "exploration_check_spacing", "skill_check_spacing",
                   "kill_checks", "skill_checks", "discovery_checks", "build_checks", "eat_checks",
                   "fishing_checks", "taming_checks", "trader_checks", "lore_checks", "farming_checks",
                   "brewing_checks", "dungeon_checks", "raid_checks")

# Resource bundles (delivered to the Archipelago Chest) and traps, from the item table.
FILLER_ITEMS = tuple(item.item_name for item in item_data_table if item.game_id.startswith("filler:"))
GEAR_ITEMS = tuple(item.item_name for item in item_data_table if item.game_id.startswith("gear:"))

# Boss -> its drop as an item, which works in place of defeating it.
BOSS_DROP_ITEMS = {"Eikthyr": "Hard Antler", "The Elder": "Swamp Key", "Bonemass": "Wishbone",
                   "Moder": "3 Dragon Tears", "Yagluth": "Torn Spirit", "The Queen": "Majestic Carapace"}

# Bundles and gear from later in the game: the earliest tier (goal scope) they're placed in.
# Anything not listed is available from the start.
ITEM_TIERS = {"10 Copper": 3, "10 Tin": 3, "10 Coal": 3, "3 Surtling Cores": 2, "10 Bronze": 4,
              "10 Finewood": 5, "10 Ancient Bark": 5, "10 Iron": 6, "10 Silver": 7, "5 Obsidian": 7,
              "10 Black Metal": 8, "10 Linen Thread": 9, "10 Yggdrasil Wood": 9, "10 Black Marble": 9,
              "5 Refined Eitr": 10, "10 Flametal": 11, "10 Ashwood": 11, "5 Bloodgold": 12,
              "Flint Axe": 1, "Antler Pickaxe": 3, "Bronze Axe": 4, "Bronze Pickaxe": 4, "Iron Axe": 6,
              "Iron Pickaxe": 6, "Black Metal Axe": 8, "Black Metal Pickaxe": 10}


def boss_name(token: str) -> str:
    return token[len("kill:"):] if token.startswith("kill:") else token


def boss_rule(tokens, player):
    """Every boss in `tokens` defeated, or its drop received (not for "kill:" ones)."""
    needs = [[f"{boss_name(t)} Defeated"] if t.startswith("kill:") or t not in BOSS_DROP_ITEMS
             else [f"{t} Defeated", BOSS_DROP_ITEMS[t]] for t in tokens]
    return lambda state: all(state.has_any(options, player) for options in needs)
TRAP_ITEMS = tuple(item.item_name for item in item_data_table if item.game_id.startswith("trap:"))
BOOST_ITEMS = tuple(item.item_name for item in item_data_table if item.game_id.startswith("boost:"))

# Location (and same-named item) -> tier number, from its region ("Tier4" -> 4).
LOCATION_TIERS = {location.user_friendly_name: int(location.region[len("Tier"):])
                  for location in location_data_table}


def goal_scope(goal_tier: int, goal_boss: str) -> frozenset:
    """
    Locations that belong in a game ending at `goal_tier` by defeating `goal_boss`: everything
    up to that tier that doesn't need the goal boss (or a later one) defeated first, since
    defeating it ends the game, minus any location that needs a research item from outside
    the scope (repeated, since dropping one research can strand another). Each research and
    trophy name is both a location and an item; the extra checks are locations only.
    """
    earlier = frozenset(BOSS_ORDER[:BOSS_ORDER.index(goal_boss)])
    later_bosses = {BOSS_TROPHIES[boss] for boss in BOSS_ORDER[BOSS_ORDER.index(goal_boss) + 1:]}
    region = {location.user_friendly_name: location.region for location in location_data_table}
    scope = {name for name, tier in LOCATION_TIERS.items()
             if tier <= goal_tier and name not in later_bosses
             and {boss_name(b) for b in LOCATION_BOSSES[name] | REGION_BOSSES[region[name]]} <= earlier}
    while True:
        stranded = {name for name in scope if any(p not in scope for p in LOCATION_REQS.get(name, ()))}
        if not stranded:
            return frozenset(scope)
        scope -= stranded


# Hildir's quests: the world key the game sets when her chest is handed in -> where you find her and
# the dungeon the chest is in (Brenna's Smouldering Tomb, Geirrhafa's Howling Cavern, Zil and
# Thungr's Sealed Tower).
HILDIR_QUESTS = {
    "Hildir1": ("Discover: Hildir's Camp", "Discover: Smouldering Tomb"),
    "Hildir2": ("Discover: Hildir's Camp", "Discover: Howling Cavern"),
    "Hildir3": ("Discover: Hildir's Camp", "Discover: Sealed Tower"),
}
RELIC = "Forsaken Relic"
MAP_ITEMS = tuple(item.item_name for item in item_data_table if item.game_id.startswith("map:") and item.item_name.startswith("Map to "))
MAP_FRAGMENT = "Map Fragment"

# boss_altar_keys: each boss's key, and the checks its altar gates (its fight; Kall's gate altar opens his prison).
ALTAR_KEYS = {boss: f"{boss}'s Altar Key" for boss in BOSS_ORDER}
ALTAR_GATED = {**{BOSS_TROPHIES[boss]: ALTAR_KEYS[boss] for boss in BOSS_ORDER},
               "Discover: The First Prison": ALTAR_KEYS["Kall Fimbulbringer"]}
COMFORT = "Comfort: Level "


def comfort_level(name: str) -> int:
    return int(name[len(COMFORT):])  # "Comfort: Level 7" -> 7


def best_comfort(pieces) -> int:
    """
    The comfort of standing sheltered among these pieces (the game's SE_Rested.CalculateComfortLevel): 1, plus
    1 for the shelter, plus the best piece of each comfort group and every differently-named ungrouped piece.
    """
    groups: Dict[str, int] = {}
    for _, name, comfort, group, *_ in pieces:
        key = name if group == "None" else group
        groups[key] = max(groups.get(key, 0), comfort)
    return 2 + sum(groups.values())


class ValheimWeb(WebWorld):
    tutorials = [Tutorial(
        "Multiworld Setup Guide",
        "A guide to setting up the Valheim randomizer for Archipelago.",
        "English",
        "setup_en.md",
        "setup/en",
        ["JustEyeTee"],
    )]
    option_groups = option_groups
    options_presets = options_presets
    bug_report_page = "https://github.com/JustEyeTee/valheim-archipelago/issues"


def _location_groups() -> Dict[str, set]:
    """By kind of check ("Obtain", "Trophy"... and "Research") and by tier ("Tier 4")."""
    groups: Dict[str, set] = {}
    for location in location_data_table:
        name = location.user_friendly_name
        kind = name.split(":")[0] if ":" in name else "Research"
        groups.setdefault(f"{kind} Checks", set()).add(name)
        groups.setdefault(f"Tier {location.region[len('Tier'):]}", set()).add(name)
    return groups


class ValheimWorld(World):
    """
    Valheim world integration for Archipelago.
    Regions and locations are created in `create_regions` (including a call to `create_locations`).
    Items are created in `create_items`.
    """
    game = "Valheim"
    options_dataclass = ValheimOptions
    options: ValheimOptions
    location_name_to_id = location_table
    item_name_to_id = item_table
    web = ValheimWeb()
    item_name_groups = {
        "Researches": {name for name in RESEARCH_PREREQS},
        "Trophies": {item.item_name for item in item_data_table if item.item_name.startswith("Trophy: ")},
        "Boss Drops": set(BOSS_DROP_ITEMS.values()),
        "Progressive Items": set(PROGRESSIVE_FAMILIES),
        "Tools": set(GEAR_ITEMS),
        "Maps": set(MAP_ITEMS) | {MAP_FRAGMENT},
        "Altar Keys": set(ALTAR_KEYS.values()),
        "Bundles": set(FILLER_ITEMS),
        "Traps": set(TRAP_ITEMS),
        "Boosts": set(BOOST_ITEMS),
        "Tier Gates": {name for region in region_data_table.values()
                       for connection in region.connections for name in connection.required_items},
    }
    location_name_groups = _location_groups()
    topology_present = True

    # Universal Tracker rebuilds this world from slot data instead of a YAML.
    ut_can_gen_without_yaml = True

    @staticmethod
    def interpret_slot_data(slot_data: Dict[str, Any]) -> Dict[str, Any]:
        return slot_data

    def generate_early(self):
        tracker = getattr(self.multiworld, "re_gen_passthrough", {}).get(self.game)
        if tracker:
            for name, value in tracker["options"].items():
                getattr(self.options, name).value = value

        # A lower goal ends the game earlier, so checks and items past the goal are left out
        # instead of sitting where they can never be reached.
        self.goal_boss, self.goal_trophy = GOAL_BOSSES[self.options.goal.value]
        # Kall Fimbulbringer's game runs through the Deep North (tier 12); every other goal ends before it.
        scope_tier = LOCATION_TIERS[BOSS_TROPHIES[self.goal_boss]]
        self.scope = goal_scope(scope_tier, self.goal_boss)
        # Comfort: the pieces this era can build, and the levels past what they add up to are left out.
        era = self.scope
        self.comfort_pieces = [p for p in COMFORT_PIECES
                               if p[-1] <= scope_tier and all(n in era for n in p[4] + p[5])]
        shelter_ok = all(n in era for n in SHELTER[0] + SHELTER[1])
        self.max_comfort = best_comfort(self.comfort_pieces) if shelter_ok else 1
        self.scope = frozenset(n for n in self.scope if not n.startswith(COMFORT) or comfort_level(n) <= self.max_comfort)
        self.era_scope = self.scope  # before the options below take checks out
        self.scope_tier = scope_tier
        # With combat logic, armor and weapons gate fights, so logic has to count them.
        self.logic_items = LOGIC_ITEMS | (COMBAT_ITEMS if self.options.combat_logic else frozenset())
        off = tuple(prefix for prefix, option in (("Biome: ", self.options.biome_checks),
                                                  ("Obtain: ", self.options.obtain_checks),
                                                  ("Kill: ", self.options.kill_checks),
                                                  ("Discover: ", self.options.discovery_checks),
                                                  ("Build: ", self.options.build_checks),
                                                  ("Eat: ", self.options.eat_checks),
                                                  ("Catch: ", self.options.fishing_checks),
                                                  ("Tame: ", self.options.taming_checks),
                                                  ("Buy: ", self.options.trader_checks),
                                                  ("Read: ", self.options.lore_checks),
                                                  ("Vegvisir: ", self.options.lore_checks),
                                                  ("Plant: ", self.options.farming_checks),
                                                  ("Brew: ", self.options.brewing_checks),
                                                  ("Loot: ", self.options.dungeon_checks),
                                                  ("Survive: ", self.options.raid_checks)) if not option)
        if off:
            self.scope = frozenset(name for name in self.scope if not name.startswith(off))
        self.scope = frozenset(name for name in self.scope if self.wanted(name))
        self.setup_goal()
        self.setup_progressive()

    def setup_progressive(self):
        """
        With progressive_items, each family's researches in this seed, in tier order: the k-th progressive item
        received unlocks the k-th of them, so a rule needing it needs k copies.
        """
        self.progressive: Dict[str, List[str]] = {}
        self.progressive_of: Dict[str, tuple] = {}  # research -> (progressive item, copies needed)
        if not self.options.progressive_items:
            return
        for family, members in PROGRESSIVE_FAMILIES.items():
            members = [m for m in members if m in self.scope]
            if members:
                self.progressive[family] = members
                for k, member in enumerate(members, 1):
                    self.progressive_of[member] = (family, k)
        self.logic_items = self.logic_items | {self.progressive_of[n][0] for n in self.logic_items
                                               if n in self.progressive_of}

    def has(self, state, name: str) -> bool:
        """Whether this item (a research, with progressive items enough copies of its family) is received."""
        progressive = self.progressive_of.get(name)
        if progressive:
            return state.has(progressive[0], self.player, progressive[1])
        return state.has(name, self.player)

    def has_all(self, state, names) -> bool:
        return all(self.has(state, name) for name in names)

    def has_any(self, state, names) -> bool:
        return any(self.has(state, name) for name in names)

    def setup_goal(self):
        """
        The goal conditions that have something to do in this era, and for the counted ones, what counts:
        the locations (in the era, whether or not an option left them out of the seed) whose rules say
        when each target can be done, and how many are needed.
        """
        era = self.era_scope
        self.era_bosses = BOSS_ORDER[:BOSS_ORDER.index(self.goal_boss) + 1]
        explore = [name for name in era if name.startswith("Explore: ")
                   and float(name[len("Explore: "):].split("%")[0]).is_integer()
                   and float(name[len("Explore: "):].split("%")[0]) <= self.options.explorer_percent.value]
        self.goal_targets: Dict[str, List[str]] = {
            "Trophy Hunt": sorted(name for name in era if name.startswith("Trophy: ")),
            "Researcher": sorted(name for name in era if name in RESEARCH_PREREQS),
            # A skill can be trained once its first check (level 10) can be done.
            "Skill Master": sorted(name for name in era if name.startswith("Skill: ") and name.endswith(" 10")),
            "Hildir's Quests": [quest for quest, places in HILDIR_QUESTS.items() if all(p in era for p in places)],
            "Explorer": [max(explore, key=lambda n: float(n[len("Explore: "):].split("%")[0]))] if explore else [],
            "Great Hall": [f"{COMFORT}{level}" for level in [min(self.options.great_hall_comfort.value, self.max_comfort)]
                           if f"{COMFORT}{level}" in era],
        }
        percent = {"Trophy Hunt": self.options.trophy_hunt_percent.value,
                   "Researcher": self.options.researcher_percent.value}
        self.goal_needed = {name: max(1, math.ceil(len(self.goal_targets[name]) * share / 100))
                            for name, share in percent.items()}
        self.goal_needed["Skill Master"] = min(self.options.skill_master_count.value,
                                               len(self.goal_targets["Skill Master"]))
        self.goal_needed["Hildir's Quests"] = len(self.goal_targets["Hildir's Quests"])
        self.goal_needed["Explorer"] = len(self.goal_targets["Explorer"])
        self.goal_needed["Great Hall"] = len(self.goal_targets["Great Hall"])

        conditions = set(self.options.goal_conditions.value) or {"Goal Boss"}
        for name in sorted(conditions):
            if name in self.goal_targets and not self.goal_targets[name]:
                logging.warning(f"Valheim: {self.player_name} has nothing to do for {name} in "
                                f"{self.goal_boss}'s era, so it isn't a goal condition.")
                conditions.discard(name)
        if "Great Hall" in conditions and self.options.great_hall_comfort.value > self.max_comfort:
            logging.warning(f"Valheim: {self.player_name}'s Great Hall goal is lowered to comfort "
                            f"{self.max_comfort}, the most in {self.goal_boss}'s era.")
        if "Explorer" in conditions:
            reached = self.goal_targets["Explorer"][0]
            if reached != f"Explore: {self.options.explorer_percent.value}% of the World":
                logging.warning(f"Valheim: {self.player_name}'s Explorer goal is lowered to "
                                f"{reached[len('Explore: '):]}, the most in {self.goal_boss}'s era.")
        self.goal_conditions = [name for name in GoalConditions.valid_keys if name in conditions] or ["Goal Boss"]
        # Relics are counted in create_items, once it's known how many fit.
        self.relics = 0
        # Comfort logic counts the researches that unlock comfort pieces, roofs and their stations.
        if "Great Hall" in self.goal_conditions or any(n.startswith(COMFORT) for n in self.scope):
            self.logic_items = self.logic_items | {n for p in self.comfort_pieces for n in p[4]} | set(SHELTER[0])

    def wanted(self, name: str) -> bool:
        """Whether a skill or exploration check is in by its level or percentage and the spacing options."""
        if name.startswith("Skill: "):
            level = int(name.rsplit(" ", 1)[1])  # "Skill: Woodcutting 30" -> 30
            step = {SkillCheckSpacing.option_every_10: 10, SkillCheckSpacing.option_every_20: 20,
                    SkillCheckSpacing.option_every_25: 25}[self.options.skill_check_spacing.value]
            return level <= self.options.skill_checks.value and level % step == 0
        if name.startswith("Explore: "):
            percent = float(name[len("Explore: "):].split("%")[0])  # "Explore: 2.5% of the World" -> 2.5
            spacing = self.options.exploration_check_spacing.value
            if spacing == ExplorationCheckSpacing.option_half_percent:
                kept = True
            elif spacing == ExplorationCheckSpacing.option_one_percent:
                kept = percent in (0.25, 0.5) or percent.is_integer()
            else:
                kept = percent in (0.5, 1) or (percent.is_integer() and percent % 2 == 0)
            return kept and percent <= self.options.exploration_checks.value
        if name.startswith(COMFORT):
            return comfort_level(name) <= self.options.comfort_checks.value
        return True

    def create_regions(self):
        """
        Creates regions and locations for the world.
        `create_regions` internally calls `create_locations`.
        """
        create_regions(self)
        create_locations(self, self.scope)
        # Long grinds never hold progression: skill levels above 30, exploration past 6%, and raids (random).
        for location in self.multiworld.get_locations(self.player):
            name = location.name
            if (name.startswith("Skill: ") and int(name.rsplit(" ", 1)[1]) > 30) or name.startswith("Survive: ") or \
                    (name.startswith("Explore: ") and float(name[len("Explore: "):].split("%")[0]) > 6):
                location.progress_type = LocationProgressType.EXCLUDED

        # An event at each boss's trophy, reachable exactly when that trophy is: "Eikthyr
        # Defeated", which later progress and the goal need.
        self.boss_events = []
        for boss in self.era_bosses:
            trophy_location = self.get_location(BOSS_TROPHIES[boss])
            event = Location(self.player, f"Defeat {boss}", None, trophy_location.parent_region)
            event.place_locked_item(Item(f"{boss} Defeated", ItemClassification.progression, None, self.player))
            trophy_location.parent_region.locations.append(event)
            self.boss_events.append((event, trophy_location))

        # The counted goal conditions: an event for each target, with the rules of the location it stands
        # for ("Trophy Hunt: Trophy: TrophyBoar" can be done when that trophy can), so logic can count them.
        self.goal_events = []
        region_of = {location.user_friendly_name: location.region for location in location_data_table}
        for condition in self.goal_conditions:
            for target in self.goal_targets.get(condition, ()):
                places = HILDIR_QUESTS.get(target, (target,))
                region = self.get_region(max((region_of[p] for p in places), key=lambda r: int(r[len("Tier"):])))
                event = Location(self.player, f"{condition}: {target}", None, region)
                event.place_locked_item(Item(f"{condition} Progress", ItemClassification.progression, None,
                                             self.player))
                region.locations.append(event)
                self.goal_events.append((event, places))

        menu = self.get_region("Menu")
        self.victory = Location(self.player, "Goal Complete", None, menu)
        self.victory.place_locked_item(Item("Victory", ItemClassification.progression, None, self.player))
        menu.locations.append(self.victory)

    def create_items(self):
        """
        Populates the item pool with items for the world.
        """
        create_items(self, self.scope - set(self.progressive_of), self.logic_items)
        for family, members in self.progressive.items():
            for _ in members:
                self.multiworld.itempool.append(self.create_item(family))
        earlier = BOSS_ORDER[:BOSS_ORDER.index(self.goal_boss)]
        if self.options.boss_items:
            for boss in earlier:
                if boss in BOSS_DROP_ITEMS:
                    self.multiworld.itempool.append(self.create_item(BOSS_DROP_ITEMS[boss]))
        if self.options.boss_altar_keys:
            for boss in self.era_bosses:
                self.multiworld.itempool.append(self.create_item(ALTAR_KEYS[boss]))
        if self.options.gear_items:
            for gear in GEAR_ITEMS:
                if ITEM_TIERS[gear] <= self.scope_tier:
                    self.multiworld.itempool.append(self.create_item(gear))
        if self.options.starter_kit:
            self.multiworld.push_precollected(self.create_item("Starter Kit"))

        # Checks without a same-named item (biome, obtain, explore, kill, skill, discover) are
        # filled with relics (for a Relic Hunt), then traps, then boosts, then bundles.
        missing = len(self.multiworld.get_unfilled_locations(self.player)) - \
            sum(1 for item in self.multiworld.itempool if item.player == self.player)
        if missing < 0:
            # More items than checks (a small goal with few extra checks): drop tools first.
            for item in [i for i in self.multiworld.itempool if i.player == self.player and i.name in GEAR_ITEMS][:-missing]:
                self.multiworld.itempool.remove(item)
            missing = 0
        if "Relic Hunt" in self.goal_conditions:
            room = missing + sum(1 for i in self.multiworld.itempool if i.player == self.player and i.name in GEAR_ITEMS)
            self.relics = min(self.options.relic_hunt_total.value, room)
            if self.relics < self.options.relic_hunt_total.value:
                logging.warning(f"Valheim: only {self.relics} of {self.player_name}'s "
                                f"{self.options.relic_hunt_total.value} relics fit among the checks.")
            if self.relics > missing:
                for item in [i for i in self.multiworld.itempool if i.player == self.player and i.name in GEAR_ITEMS][:self.relics - missing]:
                    self.multiworld.itempool.remove(item)
                missing = self.relics
            for _ in range(self.relics):
                self.multiworld.itempool.append(self.create_item(RELIC))
            missing -= self.relics
            self.goal_needed["Relic Hunt"] = max(1, math.ceil(self.relics * self.options.relic_hunt_percent.value / 100))
        # Maps (to each boss of the era, and fragments) take filler's place, as far as there's room.
        maps = ([f"Map to {boss}" for boss in self.era_bosses] if self.options.map_items else []) \
            + [MAP_FRAGMENT] * self.options.map_fragments.value
        for name in maps[:missing]:
            self.multiworld.itempool.append(self.create_item(name))
        missing -= min(missing, len(maps))
        allowed_traps = [trap for trap in TRAP_ITEMS if trap not in self.options.excluded_traps.value]
        traps = round(missing * self.options.trap_percentage.value / 100) if allowed_traps else 0
        boosts = min(missing - traps, round(missing * self.options.boost_percentage.value / 100))
        for i in range(missing):
            name = self.random.choice(allowed_traps) if i < traps else \
                self.random.choice(BOOST_ITEMS) if i < traps + boosts else self.get_filler_item_name()
            self.multiworld.itempool.append(self.create_item(name))

    def create_item(self, name: str) -> Item:
        classification = ItemClassification.trap if name in TRAP_ITEMS else \
            ItemClassification.filler if name in FILLER_ITEMS else \
            ItemClassification.progression if name in getattr(self, "logic_items", LOGIC_ITEMS) \
            or name in BOSS_DROP_ITEMS.values() or name == RELIC or name in ALTAR_KEYS.values() \
            else ItemClassification.useful
        return Item(name, classification, item_table[name], self.player)

    def get_filler_item_name(self) -> str:
        # Bundles from the goal's era or earlier (no Black Metal in an Eikthyr game). Item link
        # groups never run generate_early, so they only get the basic bundles.
        tier = getattr(self, "scope_tier", 0)
        return self.random.choice([name for name in FILLER_ITEMS if ITEM_TIERS.get(name, 0) <= tier])

    def location_rules(self, name: str) -> List[Callable]:
        """
        A location's rules beyond reaching its tier: its research prerequisites (the mod keeps a
        research's recipe locked until all of them are received; some obtain checks need a station's
        research too), the bosses whose drops it needs, and, with combat logic, the gear its fight needs.
        """
        rules = []
        prereqs = LOCATION_REQS.get(name)
        if prereqs:
            rules.append(lambda state, reqs=prereqs: self.has_all(state, reqs))
        bosses = LOCATION_BOSSES[name]
        if bosses:
            rules.append(boss_rule(bosses, self.player))
        if name in self.combat_rules:
            rules.append(self.combat_rules[name])
        if name.startswith(COMFORT):
            rules.append(lambda state, level=comfort_level(name): self.comfort(state) >= level)
        if self.options.boss_altar_keys and name in ALTAR_GATED:
            rules.append(lambda state, key=ALTAR_GATED[name]: state.has(key, self.player))
        return rules

    def comfort(self, state) -> int:
        """The most comfort you can build: pieces whose researches you have and whose materials you can get."""
        def can_build(items, obtains):
            return self.has_all(state, items) and all(
                state.can_reach_region(region, self.player) and all(rule(state) for rule in rules)
                for region, rules in (self.obtain_rules[o] for o in obtains))
        if not can_build(*SHELTER[:2]):
            return 1
        return best_comfort([p for p in self.comfort_pieces if can_build(p[4], p[5])])

    def set_rules(self):
        # Combat readiness: armor, a weapon (and with strict, a bow or crossbow) from the era each fight
        # expects, among the gear that's in this seed. Tier gates go on the tier's entrance.
        self.combat_rules = {}
        if self.options.combat_logic:
            kinds = ("armor", "weapons", "ranged") if self.options.combat_logic == CombatLogic.option_strict \
                else ("armor", "weapons")
            for gate, era in COMBAT_GATES.items():
                needs = [names for names in ([n for n in COMBAT_ERAS[era][k] if n in self.scope] for k in kinds) if names]
                if needs:
                    self.combat_rules[gate] = lambda state, needs=needs: \
                        all(self.has_any(state, names) for names in needs)

        # Comfort: where each material is obtained and that check's rules (whether or not it's in the seed).
        region_of = {location.user_friendly_name: location.region for location in location_data_table}
        self.obtain_rules = {o: (region_of[o], self.location_rules(o))
                             for p in self.comfort_pieces + [(None,) * 4 + SHELTER[:2]] for o in p[5]}

        for location_name in self.scope:
            for rule in self.location_rules(location_name):
                add_rule(self.get_location(location_name), rule)
        # Boss drops and combat on tier entrances.
        for region_name, bosses in ENTRANCE_BOSSES.items():
            if bosses:
                add_rule(self.get_region(region_name).entrances[0], boss_rule(bosses, self.player))
        for gate, rule in self.combat_rules.items():
            if gate.startswith("Tier"):
                add_rule(self.get_region(gate).entrances[0], rule)

        for event, trophy_location in self.boss_events:
            event.access_rule = trophy_location.access_rule
        for event, places in self.goal_events:
            for place in places:
                for rule in self.location_rules(place):
                    add_rule(event, rule)

        needs = []
        for condition in self.goal_conditions:
            if condition == "Goal Boss":
                needs.append(lambda state: state.has(f"{self.goal_boss} Defeated", self.player))
            elif condition == "All Bosses":
                needs.append(lambda state: state.has_all([f"{boss} Defeated" for boss in self.era_bosses], self.player))
            elif condition == "Relic Hunt":
                needs.append(lambda state: state.has(RELIC, self.player, self.goal_needed["Relic Hunt"]))
            else:
                needs.append(lambda state, condition=condition:
                             state.has(f"{condition} Progress", self.player, self.goal_needed[condition]))
        self.victory.access_rule = lambda state: all(need(state) for need in needs)
        self.multiworld.completion_condition[self.player] = lambda state: state.has("Victory", self.player)

    def fill_slot_data(self) -> Dict[str, Any]:
        return {
            # Everything that decides which locations exist and their logic, for Universal Tracker.
            "options": self.options.as_dict(*TRACKER_OPTIONS),
            "goal_trophy": self.goal_trophy,
            "goal": self.goal_slot_data(),
            "progressive": self.progressive,
            "hint_shop_price": self.options.hint_shop_price.value,
            "boss_altar_keys": bool(self.options.boss_altar_keys.value),
            "research_cost_percent": self.options.research_cost_percent.value,
            "death_link": bool(self.options.death_link.value),
            "death_link_mode": self.options.death_link_mode.current_key,
            "death_link_amnesty": self.options.death_link_amnesty.value,
            "trap_link": bool(self.options.trap_link.value),
        }

    def goal_slot_data(self) -> Dict[str, Any]:
        """
        What the mod checks to know the goal is done: for each condition, its targets and how many of them
        are needed. Targets are location names (done once that check is), except for Skill Master (a
        skill's first check, standing for the skill), Hildir's Quests (the world keys handing in her
        chests sets) and Relic Hunt (none: received relics are counted).
        """
        targets = {"Goal Boss": [BOSS_TROPHIES[self.goal_boss]],
                   "All Bosses": [BOSS_TROPHIES[boss] for boss in self.era_bosses],
                   "Relic Hunt": [], **self.goal_targets}
        needed = {"Goal Boss": 1, "All Bosses": len(self.era_bosses), **self.goal_needed}
        return {
            "conditions": self.goal_conditions,
            "targets": {condition: targets[condition] for condition in self.goal_conditions},
            "needed": {condition: needed[condition] for condition in self.goal_conditions},
            "skill_level": self.options.skill_master_level.value,
        }
