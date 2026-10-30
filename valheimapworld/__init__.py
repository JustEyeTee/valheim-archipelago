from typing import Any, Dict

from BaseClasses import Item, ItemClassification, Location, LocationProgressType, Tutorial
from worlds.AutoWorld import WebWorld, World
from worlds.generic.Rules import add_rule

from .Regions import create_regions, region_data_table
from .Locations import create_locations, location_table, location_data_table
from .Items import create_items, item_table, item_data_table
from .Options import (ValheimOptions, CombatLogic, ExplorationCheckSpacing, SkillCheckSpacing, GOAL_BOSSES,
                      option_groups, options_presets)
from .combat_data import COMBAT_ERAS, COMBAT_GATES, COMBAT_ITEMS
from .research_data import RESEARCH_PREREQS
from .check_data import CHECKS
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


TRACKER_OPTIONS = ("goal", "combat_logic", "boss_items", "biome_checks", "obtain_checks", "exploration_checks",
                   "exploration_check_spacing", "skill_check_spacing",
                   "kill_checks", "skill_checks", "discovery_checks", "build_checks", "eat_checks",
                   "fishing_checks", "taming_checks", "trader_checks")

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
        "Tools": set(GEAR_ITEMS),
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
                                                  ("Buy: ", self.options.trader_checks)) if not option)
        if off:
            self.scope = frozenset(name for name in self.scope if not name.startswith(off))
        self.scope = frozenset(name for name in self.scope if self.wanted(name))

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
        return True

    def create_regions(self):
        """
        Creates regions and locations for the world.
        `create_regions` internally calls `create_locations`.
        """
        create_regions(self)
        create_locations(self, self.scope)
        # Long grinds never hold progression: skill levels above 30, exploration past 6%.
        for location in self.multiworld.get_locations(self.player):
            name = location.name
            if (name.startswith("Skill: ") and int(name.rsplit(" ", 1)[1]) > 30) or \
                    (name.startswith("Explore: ") and float(name[len("Explore: "):].split("%")[0]) > 6):
                location.progress_type = LocationProgressType.EXCLUDED

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
        create_items(self, self.scope, self.logic_items)
        earlier = BOSS_ORDER[:BOSS_ORDER.index(self.goal_boss)]
        if self.options.boss_items:
            for boss in earlier:
                if boss in BOSS_DROP_ITEMS:
                    self.multiworld.itempool.append(self.create_item(BOSS_DROP_ITEMS[boss]))
        if self.options.gear_items:
            for gear in GEAR_ITEMS:
                if ITEM_TIERS[gear] <= self.scope_tier:
                    self.multiworld.itempool.append(self.create_item(gear))
        if self.options.starter_kit:
            self.multiworld.push_precollected(self.create_item("Starter Kit"))

        # Checks without a same-named item (biome, obtain, explore, kill, skill, discover) are
        # filled with traps, then boosts, then bundles.
        missing = len(self.multiworld.get_unfilled_locations(self.player)) - \
            sum(1 for item in self.multiworld.itempool if item.player == self.player)
        if missing < 0:
            # More items than checks (a small goal with few extra checks): drop tools first.
            for item in [i for i in self.multiworld.itempool if i.player == self.player and i.name in GEAR_ITEMS][:-missing]:
                self.multiworld.itempool.remove(item)
            missing = 0
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
            or name in BOSS_DROP_ITEMS.values() \
            else ItemClassification.useful
        return Item(name, classification, item_table[name], self.player)

    def get_filler_item_name(self) -> str:
        # Bundles from the goal's era or earlier (no Black Metal in an Eikthyr game). Item link
        # groups never run generate_early, so they only get the basic bundles.
        tier = getattr(self, "scope_tier", 0)
        return self.random.choice([name for name in FILLER_ITEMS if ITEM_TIERS.get(name, 0) <= tier])

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
                add_rule(self.get_location(location_name), boss_rule(bosses, self.player))
        for region_name, bosses in ENTRANCE_BOSSES.items():
            if bosses:
                add_rule(self.get_region(region_name).entrances[0], boss_rule(bosses, self.player))
        # Combat readiness: armor, a weapon (and with strict, a bow or crossbow) from the era each fight
        # expects, among the gear that's in this seed.
        if self.options.combat_logic:
            kinds = ("armor", "weapons", "ranged") if self.options.combat_logic == CombatLogic.option_strict \
                else ("armor", "weapons")
            for gate, era in COMBAT_GATES.items():
                needs = [names for names in ([n for n in COMBAT_ERAS[era][k] if n in self.scope] for k in kinds) if names]
                if not needs:
                    continue
                rule = lambda state, needs=needs: all(state.has_any(names, self.player) for names in needs)
                if gate.startswith("Tier"):
                    add_rule(self.get_region(gate).entrances[0], rule)
                elif gate in self.scope:
                    add_rule(self.get_location(gate), rule)

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
