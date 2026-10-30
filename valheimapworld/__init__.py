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

# Location -> research items it needs beyond its tier: research prerequisites, and the
# stations some obtain checks need (Bloodgold needs the Frost Foundry).
LOCATION_REQS = {**RESEARCH_PREREQS, **{name: reqs for _, name, _, reqs in CHECKS if reqs}}

# Every item some rule depends on: location requirements and the region (tier) gates.
LOGIC_ITEMS = frozenset(
    {name for reqs in LOCATION_REQS.values() for name in reqs}
    | {name for region in region_data_table.values()
       for connection in region.connections for name in connection.required_items}
)

DEEP_NORTH_TIER = 12

# Resource bundles (delivered to the Archipelago Chest) and traps, from the item table.
FILLER_ITEMS = tuple(item.item_name for item in item_data_table if item.game_id.startswith("filler:"))
TRAP_ITEMS = tuple(item.item_name for item in item_data_table if item.game_id.startswith("trap:"))
BOOST_ITEMS = tuple(item.item_name for item in item_data_table if item.game_id.startswith("boost:"))

# Location (and same-named item) -> tier number, from its region ("Tier4" -> 4).
LOCATION_TIERS = {location.user_friendly_name: int(location.region[len("Tier"):])
                  for location in location_data_table}


def goal_scope(goal_tier: int) -> frozenset:
    """
    Researches and trophies that belong in a game ending at `goal_tier`: everything up to that
    tier, minus any location that needs a research item from a later tier (repeated, since
    dropping one research can strand another). Each research and trophy name is both a
    location and an item; the extra checks are locations only.
    """
    scope = {name for name, tier in LOCATION_TIERS.items() if tier <= goal_tier}
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

    def generate_early(self):
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
        self.scope = goal_scope(scope_tier)
        off = tuple(prefix for prefix, option in (("Biome: ", self.options.biome_checks),
                                                  ("Obtain: ", self.options.obtain_checks),
                                                  ("Explore: ", self.options.exploration_checks),
                                                  ("Kill: ", self.options.kill_checks),
                                                  ("Discover: ", self.options.discovery_checks)) if not option)
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

        # Goal: an event at the goal boss's trophy, reachable exactly when that trophy is.
        trophy_location = self.get_location(f"Trophy: {self.goal_trophy}")
        goal = Location(self.player, f"Defeat {self.goal_boss}", None, trophy_location.parent_region)
        goal.place_locked_item(Item("Victory", ItemClassification.progression, None, self.player))
        trophy_location.parent_region.locations.append(goal)

    def create_items(self):
        """
        Populates the item pool with items for the world.
        """
        create_items(self, self.scope, LOGIC_ITEMS)

        # Checks without a same-named item (biome, obtain, explore, kill, skill, discover) are
        # filled with traps, then boosts, then bundles.
        missing = len(self.multiworld.get_unfilled_locations(self.player)) - \
            sum(1 for item in self.multiworld.itempool if item.player == self.player)
        traps = round(missing * self.options.trap_percentage.value / 100)
        boosts = min(missing - traps, round(missing * self.options.boost_percentage.value / 100))
        for i in range(missing):
            name = self.random.choice(TRAP_ITEMS) if i < traps else \
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
        self.multiworld.completion_condition[self.player] = lambda state: state.has("Victory", self.player)

    def fill_slot_data(self) -> Dict[str, Any]:
        return {
            "goal_trophy": self.goal_trophy,
            "research_cost_percent": self.options.research_cost_percent.value,
            "death_link": bool(self.options.death_link.value),
            "death_link_mode": self.options.death_link_mode.current_key,
            "death_link_amnesty": self.options.death_link_amnesty.value,
            "trap_link": bool(self.options.trap_link.value),
        }
