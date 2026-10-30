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

# Every item some rule depends on: research prerequisites and the region (tier) gates.
LOGIC_ITEMS = frozenset(
    {name for reqs in RESEARCH_PREREQS.values() for name in reqs}
    | {name for region in region_data_table.values()
       for connection in region.connections for name in connection.required_items}
)

DEEP_NORTH_TIER = 12

# Resource bundles (delivered to the Archipelago Chest) and traps, from the item table.
FILLER_ITEMS = tuple(item.item_name for item in item_data_table if item.game_id.startswith("filler:"))
TRAP_ITEMS = tuple(item.item_name for item in item_data_table if item.game_id.startswith("trap:"))

# Location (and same-named item) -> tier number, from its region ("Tier4" -> 4).
LOCATION_TIERS = {location.user_friendly_name: int(location.region[len("Tier"):])
                  for location in location_data_table}


def goal_scope(goal_tier: int) -> frozenset:
    """
    Researches and trophies that belong in a game ending at `goal_tier`: everything up to that
    tier, minus any research that needs a prerequisite from a later tier (repeated, since
    dropping one research can strand another). Each name is both a location and an item.
    """
    scope = {name for name, tier in LOCATION_TIERS.items() if tier <= goal_tier}
    while True:
        stranded = {name for name in scope if any(p not in scope for p in RESEARCH_PREREQS.get(name, ()))}
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
        if not self.options.biome_checks:
            self.scope = frozenset(name for name in self.scope if not name.startswith("Biome: "))

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

        # Checks without a same-named item (biomes) are filled with bundles and traps.
        missing = len(self.multiworld.get_unfilled_locations(self.player)) - \
            sum(1 for item in self.multiworld.itempool if item.player == self.player)
        traps = round(missing * self.options.trap_percentage.value / 100)
        for i in range(missing):
            name = self.random.choice(TRAP_ITEMS) if i < traps else self.get_filler_item_name()
            self.multiworld.itempool.append(self.create_item(name))

    def create_item(self, name: str) -> Item:
        classification = ItemClassification.trap if name in TRAP_ITEMS else \
            ItemClassification.filler if name in FILLER_ITEMS else \
            ItemClassification.progression if name in LOGIC_ITEMS else ItemClassification.useful
        return Item(name, classification, item_table[name], self.player)

    def get_filler_item_name(self) -> str:
        return self.random.choice(FILLER_ITEMS)

    def set_rules(self):
        # The mod keeps a research's recipe locked until all of its prerequisites are received.
        for location_name, prereqs in RESEARCH_PREREQS.items():
            if prereqs and location_name in self.scope:
                add_rule(self.get_location(location_name),
                         lambda state, reqs=prereqs: state.has_all(reqs, self.player))
        self.multiworld.completion_condition[self.player] = lambda state: state.has("Victory", self.player)

    def fill_slot_data(self) -> Dict[str, Any]:
        return {
            "goal_trophy": self.goal_trophy,
            "research_cost_percent": self.options.research_cost_percent.value,
        }
