from typing import Any, Dict

from BaseClasses import Item, ItemClassification, Location
from worlds.AutoWorld import World
from worlds.generic.Rules import add_rule

from .Regions import create_regions, region_data_table
from .Locations import create_locations, location_table
from .Items import create_items, item_table
from .Options import ValheimOptions, GOAL_BOSSES
from .research_data import RESEARCH_PREREQS

# Every item some rule depends on: research prerequisites and the region (tier) gates.
LOGIC_ITEMS = frozenset(
    {name for reqs in RESEARCH_PREREQS.values() for name in reqs}
    | {name for region in region_data_table.values()
       for connection in region.connections for name in connection.required_items}
)


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

    def create_regions(self):
        """
        Creates regions and locations for the world.
        `create_regions` internally calls `create_locations`.
        """
        create_regions(self)
        create_locations(self)

        # Goal: an event at the goal boss's trophy, reachable exactly when that trophy is.
        boss, trophy = GOAL_BOSSES[self.options.goal.value]
        trophy_location = self.get_location(f"Trophy: {trophy}")
        goal = Location(self.player, f"Defeat {boss}", None, trophy_location.parent_region)
        goal.place_locked_item(Item("Victory", ItemClassification.progression, None, self.player))
        trophy_location.parent_region.locations.append(goal)

    def create_items(self):
        """
        Populates the item pool with items for the world.
        """
        create_items(self, LOGIC_ITEMS)

    def set_rules(self):
        # The mod keeps a research's recipe locked until all of its prerequisites are received.
        for location_name, prereqs in RESEARCH_PREREQS.items():
            if prereqs:
                add_rule(self.get_location(location_name),
                         lambda state, reqs=prereqs: state.has_all(reqs, self.player))
        self.multiworld.completion_condition[self.player] = lambda state: state.has("Victory", self.player)

    def fill_slot_data(self) -> Dict[str, Any]:
        return {
            "goal_trophy": GOAL_BOSSES[self.options.goal.value][1],
        }
