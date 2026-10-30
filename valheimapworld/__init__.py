import logging
from typing import Any, Dict

from BaseClasses import Item, ItemClassification, Location
from worlds.AutoWorld import World
from worlds.generic.Rules import add_rule

from .Regions import create_regions, region_data_table
from .Locations import create_locations, location_table, location_data_table
from .Items import create_items, item_table, item_data_table
from .Options import ValheimOptions, Goal, GOAL_BOSSES
from .research_data import RESEARCH_PREREQS
from .check_data import CHECKS
from .boss_data import BOSS_ORDER, RESEARCH_COST_BOSSES, RESEARCH_USE_BOSSES, CHECK_BOSSES

# Location -> research items it needs beyond its tier: research prerequisites, and the
# stations some obtain checks need (Bloodgold needs the Frost Foundry).
CHECK_REQS = {name: reqs for _, name, _, reqs in CHECKS if reqs}
LOCATION_REQS = {**RESEARCH_PREREQS, **CHECK_REQS}

# Boss -> its trophy location; defeating it is an event there ("Eikthyr Defeated").
BOSS_TROPHIES = {boss: f"Trophy: {trophy}" for boss, trophy in GOAL_BOSSES.values()}


def bosses_to_use(items) -> set:
    return {boss for item in items for boss in RESEARCH_USE_BOSSES.get(item, ())}


# Location -> bosses that must be defeated first (their drops go into it): a research's cost,
# an item to obtain, the unlocks a check's required research gives, and Bonemass, whose altar
# takes Withered Bones from the Sunken Crypts (The Elder's Swamp Key).
LOCATION_BOSSES = {
    location.user_friendly_name: frozenset(
        set(RESEARCH_COST_BOSSES.get(location.user_friendly_name, ()))
        | set(CHECK_BOSSES.get(location.user_friendly_name, ()))
        | bosses_to_use(CHECK_REQS.get(location.user_friendly_name, ()))
        | ({"The Elder"} if location.user_friendly_name == "Trophy: TrophyBonemass" else set()))
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

DEEP_NORTH_TIER = 12

TRACKER_OPTIONS = ("goal", "include_deep_north", "biome_checks", "obtain_checks", "exploration_checks",
                   "kill_checks", "skill_checks", "discovery_checks", "build_checks", "eat_checks",
                   "fishing_checks", "taming_checks", "trader_checks")

# Resource bundles (delivered to the Archipelago Chest) and traps, from the item table.
FILLER_ITEMS = tuple(item.item_name for item in item_data_table if item.game_id.startswith("filler:"))
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
    region = {location.user_friendly_name: location.region for location in location_data_table}
    scope = {name for name, tier in LOCATION_TIERS.items()
             if tier <= goal_tier and LOCATION_BOSSES[name] | REGION_BOSSES[region[name]] <= earlier}
    while True:
        stranded = {name for name in scope if any(p not in scope for p in LOCATION_REQS.get(name, ()))}
        if not stranded:
            return frozenset(scope)
        scope -= stranded


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
        scope_tier = LOCATION_TIERS[f"Trophy: {self.goal_trophy}"]
        if self.options.include_deep_north:
            if self.options.goal == Goal.option_fader:
                scope_tier = DEEP_NORTH_TIER
            else:
                logging.warning(f"Valheim: {self.player_name} has include_deep_north on, but it only "
                                f"applies with goal: fader, so it is ignored.")
        self.scope = goal_scope(scope_tier, self.goal_boss)
        off = tuple(prefix for prefix, option in (("Biome: ", self.options.biome_checks),
                                                  ("Obtain: ", self.options.obtain_checks),
                                                  ("Explore: ", self.options.exploration_checks),
                                                  ("Kill: ", self.options.kill_checks),
                                                  ("Discover: ", self.options.discovery_checks),
                                                  ("Build: ", self.options.build_checks),
                                                  ("Eat: ", self.options.eat_checks),
                                                  ("Catch: ", self.options.fishing_checks),
                                                  ("Tame: ", self.options.taming_checks),
                                                  ("Buy: ", self.options.trader_checks)) if not option)
        if off:
            self.scope = frozenset(name for name in self.scope if not name.startswith(off))
        # "Skill: Woodcutting 30" -> level 30
        max_level = self.options.skill_checks.value
        self.scope = frozenset(name for name in self.scope
                               if not name.startswith("Skill: ") or int(name.rsplit(" ", 1)[1]) <= max_level)

    def create_regions(self):
        """
        Creates regions and locations for the world.
        `create_regions` internally calls `create_locations`.
        """
        create_regions(self)
        create_locations(self, self.scope)

        # An event at each boss's trophy, reachable exactly when that trophy is: "Eikthyr
        # Defeated", which later progress needs, and Victory for the goal boss.
        self.boss_events = []
        for boss in BOSS_ORDER[:BOSS_ORDER.index(self.goal_boss) + 1]:
            trophy_location = self.get_location(BOSS_TROPHIES[boss])
            event = Location(self.player, f"Defeat {boss}", None, trophy_location.parent_region)
            name = "Victory" if boss == self.goal_boss else f"{boss} Defeated"
            event.place_locked_item(Item(name, ItemClassification.progression, None, self.player))
            trophy_location.parent_region.locations.append(event)
            self.boss_events.append((event, trophy_location))

    def create_items(self):
        """
        Populates the item pool with items for the world.
        """
        create_items(self, self.scope, LOGIC_ITEMS)

        # Checks without a same-named item (biome, obtain, explore, kill, skill, discover) are
        # filled with traps, then boosts, then bundles.
        missing = len(self.multiworld.get_unfilled_locations(self.player)) - \
            sum(1 for item in self.multiworld.itempool if item.player == self.player)
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
            ItemClassification.progression if name in LOGIC_ITEMS else ItemClassification.useful
        return Item(name, classification, item_table[name], self.player)

    def get_filler_item_name(self) -> str:
        return self.random.choice(FILLER_ITEMS)

    def set_rules(self):
        # The mod keeps a research's recipe locked until all of its prerequisites are received;
        # some obtain checks need a station's research too.
        for location_name, prereqs in LOCATION_REQS.items():
            if prereqs and location_name in self.scope:
                add_rule(self.get_location(location_name),
                         lambda state, reqs=prereqs: state.has_all(reqs, self.player))

        # Boss drops: locations and tier entrances that need a boss defeated first.
        for location_name in self.scope:
            bosses = LOCATION_BOSSES[location_name]
            if bosses:
                add_rule(self.get_location(location_name),
                         lambda state, events=[f"{b} Defeated" for b in bosses]: state.has_all(events, self.player))
        for region_name, bosses in ENTRANCE_BOSSES.items():
            if bosses:
                entrance = self.get_region(region_name).entrances[0]
                add_rule(entrance, lambda state, events=[f"{b} Defeated" for b in bosses]: state.has_all(events, self.player))
        for event, trophy_location in self.boss_events:
            event.access_rule = trophy_location.access_rule

        self.multiworld.completion_condition[self.player] = lambda state: state.has("Victory", self.player)

    def fill_slot_data(self) -> Dict[str, Any]:
        return {
            # Everything that decides which locations exist and their logic, for Universal Tracker.
            "options": self.options.as_dict(*TRACKER_OPTIONS),
            "goal_trophy": self.goal_trophy,
            "research_cost_percent": self.options.research_cost_percent.value,
            "death_link": bool(self.options.death_link.value),
            "death_link_mode": self.options.death_link_mode.current_key,
            "death_link_amnesty": self.options.death_link_amnesty.value,
            "trap_link": bool(self.options.trap_link.value),
        }
