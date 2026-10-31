"""Gives every check a biome: the earliest biome, in progression order, where the check can be done.

    python3 tools/gen_check_biomes.py ~/projects/valheim-archipelago-refs/gamedb.json

Writes (rerunnable: an existing `biome` column is replaced, never duplicated):
  mod/checks.tsv         a last column `biome` on every row
  mod/research.tsv       a last column `biome` on every row: the biome of the research's cost (column 6)
  mod/research_unlock_biomes.tsv  research -> the earliest biome where something it unlocks can be made
  mod/trophy_biomes.tsv  trophy -> biome for the APWorld's "Trophy: <prefab>" locations, which live in
                         valheimapworld/Locations.py, not in checks.tsv
The APWorld's own "Biome: X" locations (also only in Locations.py) are simply biome X.

Progression order: Meadows 0, BlackForest 1, Swamp 2, Ocean 2, Mountain 3, Plains 4, Mistlands 5, AshLands 6,
DeepNorth 7. Swamp and Ocean share rank 2; to pick a name the script orders Ocean just after Swamp (so an item
found in both is "Swamp", a dish needing a Swamp and an Ocean ingredient is "Ocean").

How an item's biome is found (the earliest of all its sources; a source needing several things is as late as the
latest of them). The game database lists no contents of world locations or dungeons, so what only comes from
inside them is in the explicit tables below, and every check whose biome depends on one of those is printed.
  creature drops   the creature's biome: its spawn lists (spawns needing no world key); otherwise the
                   location that holds it (CREATURE_LOCATIONS / CREATURE_BIOMES); otherwise, as a fallback,
                   a spawn that needs a boss key (no earlier than that boss's biome); bosses are BOSS_BIOMES
  world objects    vegetation lists (trees, rocks, bushes, pickables) with their biome, following
                   what breaking them spawns; a tool tier above 0 needs a tool of that tier (the earliest
                   axe or pickaxe with it); tree logs are TREE_LOGS (the database has no TreeBase logs)
  fish             the fish's spawn biome, plus the Fishing Rod and the fish's bait
  traders          the trader's camp biome, no earlier than the boss key the stock item needs
  chests           treasure chest loot, by the chest's biome (CHEST_BIOMES)
  crafting         recipes, pieces and conversions (smelters, kilns, cooking stations, oven, fermenter,
                   windmill, spinning wheel...; CONVERSIONS): every ingredient plus the crafting station
  crops            a crop from planting its seed (sapling piece) with the Cultivator, where the plant can grow
  LOCATION_ITEMS   items found only inside locations (dungeon pickables, ore in special rocks...)
"""
import csv
import json
import pathlib
import re
import sys
from collections import Counter, defaultdict

root = pathlib.Path(__file__).resolve().parent.parent
db = json.load(open(sys.argv[1] if len(sys.argv) > 1 else
                    root.parent / "valheim-archipelago-refs" / "gamedb.json"))

# ---------------------------------------------------------------------------------------------------------
# Biomes
# ---------------------------------------------------------------------------------------------------------
ORDER = ["Meadows", "BlackForest", "Swamp", "Ocean", "Mountain", "Plains", "Mistlands", "AshLands", "DeepNorth"]
RANK = {"Meadows": 0, "BlackForest": 1, "Swamp": 2, "Ocean": 2, "Mountain": 3, "Plains": 4, "Mistlands": 5,
        "AshLands": 6, "DeepNorth": 7}
B = {name: i for i, name in enumerate(ORDER)}  # biome name -> its place in ORDER (what min/max compare)
INF = len(ORDER)                                # not obtainable from anything the script knows
BITS = {1: "Meadows", 2: "Swamp", 4: "Mountain", 8: "BlackForest", 16: "Plains", 32: "AshLands", 64: "DeepNorth",
        256: "Ocean", 512: "Mistlands"}  # Heightmap.Biome


def from_mask(mask):
    """The earliest biome in a Heightmap.Biome mask (None for 0 / -1 / only unknown bits)."""
    if not mask or mask < 0:
        return None
    found = [B[name] for bit, name in BITS.items() if mask & bit]
    return min(found) if found else None


def name(b):
    return ORDER[b] if b < INF else "UNRESOLVED"


def strip_copy(prefab):
    """'Rock_7 (2)' -> 'Rock_7' (a numbered copy of a prefab inside another one)."""
    return re.sub(r" \(\d+\)$", "", prefab or "")


# ---------------------------------------------------------------------------------------------------------
# Explicit tables, for what the game database can't tell. Every check that one of these decides is printed.
# ---------------------------------------------------------------------------------------------------------
# The bosses (as given; each boss's fight is in its biome).
BOSS_BIOMES = {"Eikthyr": "Meadows", "gd_king": "BlackForest", "Bonemass": "Swamp", "Dragon": "Mountain",
               "GoblinKing": "Plains", "SeekerQueen": "Mistlands", "Fader": "AshLands", "FrozenKing": "DeepNorth",
               "FrozenKing_p3": "DeepNorth"}
# Creatures the database has drops for but that are not real enemies (test/aspect/odd boss variants): ignored.
CREATURE_IGNORE = {"DvergerTest", "TrainingDummy", "Hive", "TheHive", "Charred_Melee_Fader", "Charred_Archer_Fader",
                   "Skeleton_aspect", "BlobAspect"}
# Dungeon / location-only creatures (not in any spawn list) -> the location (name prefix) that holds them.
CREATURE_LOCATIONS = {
    "Skeleton": "Crypt",                  # Burial Chambers (its world spawn needs Bonemass dead)
    "Skeleton_NoArcher": "Crypt",         # Burial Chambers
    "Skeleton_Poison": "Crypt",           # Rancid Remains: Burial Chambers
    "Ghost": "Crypt",                     # Burial Chambers
    "Skeleton_Hildir": "Hildir_crypt",    # Brenna: Smouldering Tomb
    "Fenring_Cultist": "MountainCave",    # Cultist: Frost Caves
    "Fenring_Cultist_Hildir": "Hildir_cave",  # Geirrhafa: Howling Cavern
    "GoblinBruteBros": "Hildir_plainsfortress",  # Thungr: Sealed Tower
    "GoblinShaman_Hildir": "Hildir_plainsfortress",  # Zil: Sealed Tower
    "GoblinBrute_Hildir": "Hildir_plainsfortress",
    "GoblinShaman": "GoblinCamp",         # Fuling Shaman: Fuling Villages
    "GoblinArcher": "GoblinCamp",
    "Charred_Mage": "CharredFortress",    # Charred Warlock: Charred Fortress
    "Morgen": "MorgenHole",               # sleeping Morgen: Putrid Holes
    "BlobTar": "TarPit",                  # Growth: tar pits
    "DvergerMage": "Mistlands_DvergrTownEntrance", "DvergerMageFire": "Mistlands_DvergrTownEntrance",
    "DvergerMageIce": "Mistlands_DvergrTownEntrance", "DvergerMageSupport": "Mistlands_DvergrTownEntrance",
}
# Location-only creatures whose location the database doesn't name: their biome, from the game.
CREATURE_BIOMES = {
    "Surtling": "Swamp",        # fire geysers in the Swamp (the spawn-list entries are disabled)
    "Ulv": "Mountain",          # Mountains at night, around ruins
    "Hen": "Plains",            # hatched from an Egg (Haldor sells them once Yagluth is dead); wild ones in Mistlands
    "Chicken": "Plains",        # the same, grown up
    "BlobFrost": "DeepNorth",   # Frost Blob
    "ElakingMole": "DeepNorth",  # Eyeless One
    "BogWitchKvastur": "Swamp",  # Kvastur, near the Bog Witch
    "GoblinDeepNorth": "DeepNorth", "DvergerDeepNorth": "DeepNorth", "JotunWarriorDualWield": "DeepNorth",
    "Frysling": "DeepNorth",    # drops Frost Cores
    "FallenWarrior": "DeepNorth",  # drops the Thunderblood / Frostfire orbs
}
# Variant suffixes that are the same creature in another state.
VARIANT_SUFFIXES = ("_sleeping", "_noarcher", "_nochest", "_NonSleeping", "_Ranged")
# World keys -> the biome they mean (besides each boss's defeat key, which comes from the boss list).
KEY_BIOMES = {"defeated_serpent": "Ocean", "defeated_writhan": "Swamp", "KilledTroll": "BlackForest",
              "killed_surtling": "Swamp", "jotun_killed": "DeepNorth"}
KEY_LOCATIONS = {"Hildir1": "Hildir_crypt", "Hildir2": "Hildir_cave", "Hildir3": "Hildir_plainsfortress"}  # chests
# Trader prefab -> its camp location.
TRADER_LOCATIONS = {"Haldor": "Vendor_BlackForest", "Hildir": "Hildir_camp", "BogWitch": "BogWitch_Camp"}
# Locations missing from the location lists.
LOCATION_BIOMES = {"DN_Bossroom": "DeepNorth"}  # the First Prison (the list entry is "bosslocation")
# Chest prefab -> the location prefix or biome it's in.
CHEST_BIOMES = {
    "TreasureChest_meadows": "Meadows", "TreasureChest_meadows_01": "Meadows", "TreasureChest_meadows_02": "Meadows",
    "TreasureChest_meadows_buried": "Meadows", "TreasureChest_meadows_combat": "Meadows",
    "TreasureChest_blackforest": "BlackForest", "TreasureChest_forestcrypt": "loc:Crypt",
    "TreasureChest_fCrypt": "loc:Crypt", "TreasureChest_trollcave": "loc:TrollCave", "TreasureChest_swamp": "Swamp",
    "TreasureChest_sunkencrypt": "loc:SunkenCrypt", "TreasureChest_mountains": "Mountain",
    "TreasureChest_mountaincave": "loc:MountainCave", "TreasureChest_heath": "Plains",
    "TreasureChest_plains_stone": "Plains", "TreasureChest_dvergrtown": "loc:Mistlands_DvergrTownEntrance",
    "TreasureChest_dvergrtower": "Mistlands", "TreasureChest_dvergr_loose_stone": "Mistlands",
    "TreasureChest_ashland_stone": "AshLands", "TreasureChest_charredfortress": "loc:CharredFortress",
    "TreasureChest_deepnorth_village": "DeepNorth", "loot_deepNorth_Granary": "DeepNorth",
    "loot_deepNorth_TimberHall": "DeepNorth",
}
# Tree prefab -> the logs it falls into and what they split into (TreeBase/TreeLog aren't in the database).
TREE_LOGS = {"Beech1": ["Wood"], "FirTree": ["Wood"], "Pinetree_01": ["Wood", "RoundLog"],
             "Birch1": ["FineWood"], "Birch2": ["FineWood"], "Birch1_aut": ["FineWood"], "Birch2_aut": ["FineWood"],
             "Oak1": ["Wood", "FineWood"], "SwampTree1": ["ElderBark"], "YggaShoot1": ["YggdrasilWood"],
             "YggaShoot2": ["YggdrasilWood"], "YggaShoot3": ["YggdrasilWood"], "SnowFirTree": ["Frostwood"],
             "SnowFirTree 2": ["Frostwood"], "Pinetree_Snow": ["Frostwood"]}
# Items found only inside world locations or dungeons (the database has no location contents) -> biome or
# location prefix. Only used as one more source; an earlier source from the data still wins.
LOCATION_ITEMS = {
    "MushroomYellow": "loc:Crypt",       # Burial Chambers and Troll Caves
    "SurtlingCore": "loc:Crypt",         # core stands in Burial Chambers
    "BoneFragments": "loc:Crypt",        # remains in Burial Chambers
    "Honey": "Meadows", "QueenBee": "Meadows",  # wild beehives in Meadows ruins
    "DragonEgg": "Mountain",             # Moder's eggs on Mountain peaks
    "OnionSeeds": "Mountain",            # wild onions in the Mountains
    "Barley": "loc:GoblinCamp", "Flax": "loc:GoblinCamp",  # Fuling villages' fields
    "Tar": "Plains",                     # tar pits
    "BlackCore": "Mistlands",            # Dvergr ruins
    "DvergrNeedle": "Mistlands",         # Dvergr extractors at Mistlands excavations
    "JuteBlue": "Mistlands",             # Dvergr structures
    "Wisp": "Mistlands",                 # caught at night in the Mistlands (Wisp Fountain, wisp torches)
    "WolfClaw": "loc:MountainCave", "WolfHairBundle": "loc:MountainCave",  # Frost Caves
    "RoyalJelly": "loc:Mistlands_DvergrTownEntrance",  # Infested Mines
    "FlametalOreNew": "AshLands",        # flametal veins (the vegetation entry is disabled)
    "AsksvinCarrionNeck": "AshLands", "AsksvinCarrionPelvic": "AshLands", "AsksvinCarrionRibcage": "AshLands",
    "AsksvinCarrionSkull": "AshLands",   # Asksvin carrion piles
    "Vineberry": "AshLands", "Fiddleheadfern": "AshLands", "BellFragment": "loc:CharredFortress",
    "GoldOre": "DeepNorth", "HatefulBlood": "DeepNorth", "OatSeeds": "DeepNorth", "PoteitrSeeds": "DeepNorth",
    "Amber": "Meadows",                  # treasure chests (also below)
}
# Upgrade tokens (Upgrader0Weapon...): found in treasure chests, but listed with amount 1 even in the Hammer's
# and the Stone Axe's recipes, so they look like upgrade-only ingredients (as audit_tiers.py treats them): ignored.
IGNORED_INGREDIENT = re.compile(r"^Upgrader\d+(Weapon|Armor)$")
# Recipes that take any one of their ingredients (Recipe.m_requireOnlyOneIngredient isn't in the database).
ANY_ONE_RECIPES = {"Recipe_Fish1"}
# Station conversions: output <- (input, station piece[, biome the station must stand in]). None input: the
# station makes it by itself.
CONVERSIONS = [
    ("Copper", "CopperOre", "smelter"), ("Tin", "TinOre", "smelter"), ("Iron", "IronScrap", "smelter"),
    ("Iron", "IronOre", "smelter"), ("Silver", "SilverOre", "smelter"),
    ("BlackMetal", "BlackMetalScrap", "blastfurnace"), ("FlametalNew", "FlametalOreNew", "blastfurnace"),
    ("Gold", "GoldOre", "piece_FrostFoundry"),
    ("Coal", "Wood", "charcoal_kiln"), ("Eitr", "Softtissue", "eitrrefinery"),
    ("BarleyFlour", "Barley", "windmill"), ("LinenThread", "Flax", "piece_spinningwheel"),
    ("Honey", None, "piece_beehive"), ("Sap", None, "piece_sapcollector", "Mistlands"),
    ("CookedMeat", "RawMeat", "piece_cookingstation"), ("CookedDeerMeat", "DeerMeat", "piece_cookingstation"),
    ("NeckTailGrilled", "NeckTail", "piece_cookingstation"), ("CookedBjornMeat", "BjornMeat", "piece_cookingstation"),
    ("FishCooked", "FishRaw", "piece_cookingstation"), ("SerpentMeatCooked", "SerpentMeat", "piece_cookingstation"),
    ("CookedWolfMeat", "WolfMeat", "piece_cookingstation"),
    ("CookedLoxMeat", "LoxMeat", "piece_cookingstation_iron"), ("CookedHareMeat", "HareMeat", "piece_cookingstation_iron"),
    ("CookedBugMeat", "BugMeat", "piece_cookingstation_iron"), ("CookedChickenMeat", "ChickenMeat", "piece_cookingstation_iron"),
    ("CookedAsksvinMeat", "AsksvinMeat", "piece_cookingstation_iron"),
    ("CookedVoltureMeat", "VoltureMeat", "piece_cookingstation_iron"),
    ("CookedMooseMeat", "MooseMeat", "piece_cookingstation_iron"),
    ("CookedSealBlubber", "SealBlubber", "piece_cookingstation_iron"),
    ("Bread", "BreadDough", "piece_oven"), ("LoxPie", "LoxPieUncooked", "piece_oven"),
    ("FishAndBread", "FishAndBreadUncooked", "piece_oven"), ("MisthareSupreme", "MisthareSupremeUncooked", "piece_oven"),
    ("MagicallyStuffedShroom", "MagicallyStuffedShroomUncooked", "piece_oven"),
    ("HoneyGlazedChicken", "HoneyGlazedChickenUncooked", "piece_oven"),
    ("PiquantPie", "PiquantPieUncooked", "piece_oven"), ("RoastedCrustPie", "RoastedCrustPieUncooked", "piece_oven"),
]
# Dungeon treasure chests (loot checks) -> the dungeon (as in tools/gen_world_checks.py).
LOOT_LOCATIONS = {"TreasureChest_forestcrypt": "Crypt", "TreasureChest_trollcave": "TrollCave",
                  "TreasureChest_sunkencrypt": "SunkenCrypt", "TreasureChest_mountaincave": "MountainCave",
                  "TreasureChest_dvergrtown": "Mistlands_DvergrTownEntrance",
                  "TreasureChest_charredfortress": "CharredFortress"}
# The game-rule kinds the task fixes.
FIXED_KINDS = {"comfort": "Meadows", "explore": "Meadows"}
# Set True to give comfort rows the earliest biome whose buildable pieces reach that comfort level instead.
COMFORT_FROM_PIECES = True

# ---------------------------------------------------------------------------------------------------------
# Locations
# ---------------------------------------------------------------------------------------------------------
location_entries = [e for lst in db["locations"]["lists"] for e in lst["entries"]]


def location_biome(prefix):
    """The earliest biome of the world locations whose name starts with prefix (enabled ones first)."""
    if prefix in LOCATION_BIOMES:
        return B[LOCATION_BIOMES[prefix]], f"override: location {prefix} = {LOCATION_BIOMES[prefix]}"
    for enabled in (1, 0):
        found = [from_mask(e["biome"]) for e in location_entries
                 if (e.get("name") or e.get("prefabName") or "").startswith(prefix) and bool(e.get("enable")) == enabled
                 and from_mask(e["biome"]) is not None]
        if found:
            return min(found), None if enabled else f"fallback: location {prefix} only in disabled list entries"
    return INF, f"UNRESOLVED location {prefix}"


def biome_or_location(spec):
    """'Swamp' or 'loc:Crypt' -> (biome, note)."""
    if spec.startswith("loc:"):
        b, _ = location_biome(spec[4:])
        return b, spec[4:]
    return B[spec], spec


# ---------------------------------------------------------------------------------------------------------
# Creatures
# ---------------------------------------------------------------------------------------------------------
key_biome = {k: B[v] for k, v in KEY_BIOMES.items()}
for creature, c in db["creatures"].items():
    if c.get("defeatSetGlobalKey") and creature in BOSS_BIOMES:
        key_biome[c["defeatSetGlobalKey"]] = B[BOSS_BIOMES[creature]]
for k, loc in KEY_LOCATIONS.items():
    key_biome[k] = location_biome(loc)[0]

spawns = defaultdict(list)  # creature -> [(biome, required key)]
for entries in db["spawns"].values():
    for s in entries:
        if s.get("enabled") and from_mask(s.get("biome")) is not None:
            spawns[s["prefab"]].append((from_mask(s["biome"]), s.get("required_global_key") or ""))

_creature_cache = {}


def creature_biome(creature):
    """(biome, note) where a creature can first be met; note is None when it's straight from the spawn lists."""
    creature = strip_copy(creature)
    if creature in _creature_cache:
        return _creature_cache[creature]
    _creature_cache[creature] = (INF, "cycle")
    result = (INF, f"UNRESOLVED creature {creature}")
    if creature in BOSS_BIOMES:
        result = (B[BOSS_BIOMES[creature]], None)
    elif creature not in CREATURE_IGNORE:
        options = [(b, None) for b, key in spawns.get(creature, []) if not key]
        if creature in CREATURE_LOCATIONS:
            b, _ = location_biome(CREATURE_LOCATIONS[creature])
            options.append((b, f"override: creature {creature} in {CREATURE_LOCATIONS[creature]} ({name(b)})"))
        if creature in CREATURE_BIOMES:
            options.append((B[CREATURE_BIOMES[creature]], f"override: creature {creature} = {CREATURE_BIOMES[creature]}"))
        if not options:
            for suffix in VARIANT_SUFFIXES:
                if creature.endswith(suffix):
                    b, note = creature_biome(creature[:-len(suffix)])
                    if b < INF:
                        options.append((b, note))
        if not options:
            keyed = [(max(b, key_biome.get(key, INF)), key) for b, key in spawns.get(creature, []) if key]
            if keyed:
                b, key = min(keyed)
                options.append((b, f"fallback: creature {creature} only spawns once {key} is set"))
        if options:
            result = min(options, key=lambda o: (o[0], o[1] is not None))
    _creature_cache[creature] = result
    return result


# ---------------------------------------------------------------------------------------------------------
# The source graph: node -> alternatives (base biome, dependencies, note). A node is an item prefab,
# "piece:<prefab>" or "tool:<skill>:<tier>". Its biome = min over alternatives of max(base, its deps).
# ---------------------------------------------------------------------------------------------------------
alts = defaultdict(list)


def add(node, base, deps=(), note=None):
    if node:
        alts[node].append((base, tuple(d for d in deps if d), note))


# Creature drops.
for creature, drops in db["drops"].items():
    b, note = creature_biome(creature)
    if b >= INF:
        continue
    for d in drops:
        if d.get("item"):
            add(d["item"], b, (), note and f"{note} (drops {d['item']})")

# Tools: "tool:7:2" = any axe (skill 7; 12 = pickaxe) of tool tier 2 or better.
TOOL_SKILLS = {7: "axe", 12: "pickaxe"}
for prefab, item in db["items"].items():
    if " (" not in prefab and item.get("skillType") in TOOL_SKILLS and item.get("itemType") in (3, 14):
        for tier in range(1, (item.get("toolTier") or 0) + 1):
            add(f"tool:{item['skillType']}:{tier}", 0, (prefab,))
AXE_OBJECT = re.compile(r"tree|birch|oak|beech|fir|pine|ygga|stubbe|log|stump|branch|bush|shrub", re.I)


def tool_for(prefab, tier):
    if not tier:
        return None
    return f"tool:{7 if AXE_OBJECT.search(prefab) else 12}:{tier}"


def yields(prefab, tier=0, seen=()):
    """(item, tool tier needed) for everything breaking/picking a world object gives, following what it spawns."""
    out = []
    if not prefab or prefab in seen:
        return out
    seen += (prefab,)
    tt = db["tool_tiers"].get(prefab)
    if tt:
        tier = max(tier, tt.get("min_tool_tier") or 0)
        out += [(d["item"], tier) for d in tt["drops"] if d.get("item")]
        out += yields(tt.get("spawn_when_destroyed"), tier, seen)
    out += [(d["item"], tier) for d in db["destroy_drops"].get(prefab, []) if d.get("item")]
    if prefab in db["pickables"] and db["pickables"][prefab].get("item"):
        out.append((db["pickables"][prefab]["item"], 0))
    out += [(log, tier) for log in TREE_LOGS.get(prefab, [])]
    if prefab in db["items"] and not tt and prefab not in db["destroy_drops"]:
        out.append((prefab, tier))  # an item placed in the world as-is (Ice spawned from frozen things)
    return out


for entries in db["vegetation"].values():
    for v in entries:
        b = from_mask(v.get("biome"))
        if not v.get("enabled") or b is None:
            continue
        for item, tier in yields(v["prefab"]):
            note = f"override: TREE_LOGS {v['prefab']}" if item in TREE_LOGS.get(v["prefab"], []) else None
            add(item, b, (tool_for(v["prefab"], tier),), note)

# Fish: where they swim, the Fishing Rod and their bait.
for fish, baits in db["fish"].items():
    fish = strip_copy(fish)
    for b, key in spawns.get(fish, []):
        for bait in {x["bait"] for x in baits if x.get("bait")}:
            add(fish, max(b, key_biome.get(key, 0) if key else 0), ("FishingRod", bait))
add("Fish4_cave", B["Mountain"], ("FishingRod", "FishingBaitCave"),
    "override: Tetra (Fish4_cave) swims in Frost Cave pools (Mountain)")

# Traders.
trader_biome = {}
for trader, stock in db["traders"].items():
    loc = TRADER_LOCATIONS.get(trader)
    tb, _ = location_biome(loc) if loc else (INF, None)
    trader_biome[trader] = tb
    for s in stock:
        if s.get("item"):
            kb = key_biome.get(s["key"], INF) if s.get("key") else 0
            add(s["item"], max(tb, kb), (), None if kb < INF else f"UNKNOWN trader key {s['key']}")


def trader_source(item):
    """The earliest biome a trader sells item in (camp biome and its required key)."""
    found = []
    for trader, stock in db["traders"].items():
        for s in stock:
            if s.get("item") == item:
                kb = key_biome.get(s["key"], INF) if s.get("key") else 0
                found.append((max(trader_biome[trader], kb), trader, s.get("key") or ""))
    return min(found) if found else (INF, None, "")


# Treasure chests.
for chest, c in db["containers"].items():
    spec = CHEST_BIOMES.get(strip_copy(chest))
    if spec:
        b, where = biome_or_location(spec)
        for d in c["loot"]:
            if d.get("item"):
                add(d["item"], b, (), f"override: chest {strip_copy(chest)} in {where}")

# Location-only items.
for item, spec in LOCATION_ITEMS.items():
    b, where = biome_or_location(spec)
    add(item, b, (), f"override: LOCATION_ITEMS {item} in {where}")

# Recipes and pieces. An ingredient with amount 0 is only needed to upgrade the item (amount per level).


def needed(ingredient):
    return ingredient.get("item") and ingredient.get("amount") != 0 and not IGNORED_INGREDIENT.match(ingredient["item"])


for rname, r in db["recipes"].items():
    if not r.get("item") or not r.get("enabled"):
        continue
    ings = [i["item"] for i in r["ingredients"] if needed(i)]
    station = f"piece:{r['station']}" if r.get("station") else None
    if rname in ANY_ONE_RECIPES:
        for i in ings:
            add(r["item"], 0, (i, station))
    else:
        add(r["item"], 0, (*ings, station))
for prefab, p in db["pieces"].items():
    if not p.get("enabled", 1) or not p.get("ingredients"):
        continue
    ings = [i["item"] for i in p["ingredients"] if needed(i)]
    add(f"piece:{prefab}", 0, (*ings, f"piece:{p['station']}" if p.get("station") else None))
for out, inp, station, *where in CONVERSIONS:
    add(out, B[where[0]] if where else 0, (inp, f"piece:{station}"))
# Meads: tapped from a Fermenter from their mead base (MeadHealthMinor <- MeadBaseHealthMinor).
for r in db["recipes"].values():
    base = r.get("item") or ""
    if base.startswith("MeadBase"):
        add("Mead" + base[len("MeadBase"):], 0, (base, "piece:fermenter"))
        meads = [i for i in db["items"] if i.lower() == ("Mead" + base[len("MeadBase"):]).lower()]
        for m in meads:
            add(m, 0, (base, "piece:fermenter"))

# Crops: plant the seed piece with the Cultivator where it grows; pick what grows.
plant_biome = {}
for sapling, plant in db["plants"].items():
    sapling = strip_copy(sapling)
    pb = from_mask(plant.get("biome"))
    if pb is None:
        continue
    plant_biome[sapling] = min(pb, plant_biome.get(sapling, INF))
    for grown in plant.get("grows") or []:
        item = db["pickables"].get(grown, {}).get("item")
        if item:
            add(item, pb, (f"piece:{sapling}", "Cultivator"))

# ---------------------------------------------------------------------------------------------------------
# Solve: relax until nothing gets earlier.
# ---------------------------------------------------------------------------------------------------------
value = defaultdict(lambda: INF)
changed = True
while changed:
    changed = False
    for node, options in alts.items():
        best = min(max([base] + [value[d] for d in deps]) for base, deps, _ in options)
        if best < value[node]:
            value[node] = best
            changed = True

_why_cache = {}


def why(node, stack=()):
    """The override/fallback notes on the path that decides a node's biome."""
    if node in _why_cache:
        return _why_cache[node]
    if node in stack or value[node] >= INF:
        return set()
    v = value[node]
    winners = [o for o in alts.get(node, []) if max([o[0]] + [value[d] for d in o[1]]) == v]
    if not winners:
        return set()
    # Prefer a winning source without an override, then the one with the fewest overridden deps.
    scored = []
    for base, deps, note in winners:
        notes = set()
        if note and base == v:
            notes.add(note)
        for d in deps:
            if value[d] == v:
                notes |= why(d, stack + (node,))
        scored.append((len(notes), sorted(notes)))
    result = set(min(scored)[1])
    _why_cache[node] = result
    return result


def missing(node, stack=()):
    """The unobtainable things that keep an unresolved node unresolved (no source at all)."""
    if value[node] < INF or node in stack:
        return set()
    if not alts.get(node):
        return {node}
    found = set()
    for base, deps, _ in alts[node]:
        for d in deps:
            found |= missing(d, stack + (node,))
    return found


def node_biome(node):
    if value[node] >= INF:
        return INF, {f"UNRESOLVED: nothing gives {sorted(missing(node))}"}
    return value[node], why(node)


def combine(*parts):
    """max of (biome, notes) pairs, keeping the notes of the parts that decide it."""
    parts = [p for p in parts if p]
    b = max(p[0] for p in parts)
    notes = set()
    for p in parts:
        if p[0] == b:
            notes |= set(p[1]) if not isinstance(p[1], str) else {p[1]}
    return b, {n for n in notes if n}


# ---------------------------------------------------------------------------------------------------------
# Researches: the biome of their cost.
# ---------------------------------------------------------------------------------------------------------
research_path = root / "mod" / "research.tsv"
research_lines = research_path.read_text().split("\n")
RESEARCH_COLS = 11
research_biome = {}  # display name -> (biome, notes)
research_gated = {}  # display name -> prefabs it unlocks
for line in research_lines:
    if not line or line.startswith("#"):
        continue
    cols = line.split("\t")[:RESEARCH_COLS]
    costs = [c.split(":")[0] for c in cols[5].split("|") if c]
    research_biome[cols[2]] = combine((0, set()), *(node_biome(c) for c in costs))
    research_gated[cols[2]] = [g for g in cols[6].split("|") if g]

# Skills trained with something no research unlocks: what you need first.
SKILL_TOOLS = {"Fishing": "FishingRod", "Ride": "SaddleLox"}

# ---------------------------------------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------------------------------------
checks_path = root / "mod" / "checks.tsv"
check_lines = checks_path.read_text().split("\n")
CHECK_COLS = 5

pieces_db = db["pieces"]


def comfort_levels():
    """Comfort level -> earliest biome reaching it (as tools/gen_comfort_data.py counts comfort)."""
    seasonal = ("piece_CelebrationGarland", "piece_FairylightGarland", "piece_xmastree", "piece_jackoturnip",
                "piece_maypole", "piece_gift1", "piece_gift2", "piece_gift3", "piece_mistletoe", "piece_xmascrown",
                "piece_xmasgarland")
    gated = {g for line in research_lines if line and not line.startswith("#")
             for g in line.split("\t")[6].split("|") if g}
    gated_names = {pieces_db[g]["name"] for g in gated if g in pieces_db}
    candidates = []
    for prefab, p in pieces_db.items():
        if (p.get("comfort") or 0) <= 0 or not p.get("enabled", 1) or not p.get("ingredients") or " (" in prefab \
                or prefab in seasonal or not (prefab in gated or p.get("station")) \
                or (prefab not in gated and p["name"] in gated_names):
            continue
        candidates.append((value[f"piece:{prefab}"], p["name"], p["comfort"], p.get("comfort_group") or 0))
    shelter = value["piece:wood_roof"]
    levels = {}
    for b in range(shelter, INF):
        by_group, ungrouped = {}, {}
        for pb, pname, comfort, group in candidates:
            if pb > b:
                continue
            if group == 0:
                ungrouped[pname] = max(ungrouped.get(pname, 0), comfort)
            else:
                by_group[group] = max(by_group.get(group, 0), comfort)
        for level in range(2, 2 + sum(by_group.values()) + sum(ungrouped.values()) + 1):
            levels.setdefault(level, b)
    return levels


comfort_biome = comfort_levels()
raid_db = db["raids"]


def check_biome(kind, key, requires):
    """(biome, notes) for one checks.tsv row."""
    if kind in FIXED_KINDS and not (kind == "comfort" and COMFORT_FROM_PIECES):
        return B[FIXED_KINDS[kind]], set()
    if kind == "comfort":
        return comfort_biome.get(int(key), INF), set()
    if kind in ("obtain", "eat", "catch", "kill", "brew"):
        # kill: the key is the trophy, which only creatures drop; brew: the mead, from its base in a Fermenter.
        return node_biome(key)
    if kind == "build":
        return node_biome(f"piece:{key}")
    if kind == "plant":
        parts = [node_biome(f"piece:{key}"), node_biome("Cultivator")]
        if key in plant_biome:
            parts.append((plant_biome[key], set()))
        return combine(*parts)
    if kind == "tame":
        b, note = creature_biome(key)
        return b, {note} if note else set()
    if kind == "buy":
        tb, trader, tkey = trader_source(key)
        return combine((tb, set() if trader else {f"UNRESOLVED: no trader sells {key}"}), node_biome(key))
    if kind == "discover" or kind == "read":
        b, note = location_biome(key)
        return b, {note} if note else set()
    if kind == "loot":
        b, note = location_biome(LOOT_LOCATIONS[key]) if key in LOOT_LOCATIONS else (INF, f"UNRESOLVED chest {key}")
        return b, {note} if note else set()
    if kind == "vegvisir":
        b, note = location_biome(key)
        return b, {f"fallback: Vegvisir placed in the biome of the boss location it reveals ({key})"} | (
            {note} if note else set())
    if kind == "raid":
        event = raid_db.get(key)
        if not event:
            return INF, {f"UNRESOLVED raid {key}"}
        parts = [(from_mask(event["biome"]) or 0, set())]
        parts += [(key_biome.get(k, INF), set() if k in key_biome else {f"UNKNOWN raid key {k}"})
                  for k in event.get("required_keys") or []]
        return combine(*parts)
    if kind == "skill":
        # The research items come from the multiworld, so what counts is making something they unlock to
        # train with: the earliest one to make (not the research's own cost).
        reqs = [q for q in requires.split("|") if q]
        missing = [q for q in reqs if q not in research_biome]
        gated = [node_biome(f"piece:{g}" if g in db["pieces"] else g) for q in reqs for g in research_gated.get(q, ())]
        tool = SKILL_TOOLS.get(key.split(":")[0])
        return combine((0, set()),
                       min(gated, key=lambda part: part[0]) if gated else None,
                       node_biome(tool) if tool else None,
                       *((INF, {f"UNRESOLVED research {q}"}) for q in missing))
    return INF, {f"UNRESOLVED kind {kind}"}


def write_column(lines, ncols, header_start, values):
    """lines with a last `biome` column (replacing one that's there); values: one per data row, in order."""
    out, i = [], 0
    for line in lines:
        if not line:
            out.append(line)
            continue
        cols = line.split("\t")
        if line.startswith("#"):
            if line.startswith(header_start):
                cols = cols[:ncols] + ["biome"]
            out.append("\t".join(cols))
            continue
        if len(cols) not in (ncols, ncols + 1):
            sys.exit(f"unexpected column count {len(cols)}: {line[:80]}")
        out.append("\t".join(cols[:ncols] + [values[i]]))
        i += 1
    assert i == len(values)
    return out


check_rows, check_results = [], []
for line in check_lines:
    if not line or line.startswith("#"):
        continue
    cols = line.split("\t")[:CHECK_COLS]
    b, notes = check_biome(cols[0], cols[1], cols[4])
    check_rows.append(cols)
    check_results.append((b, notes))

research_rows = [line.split("\t")[:RESEARCH_COLS] for line in research_lines if line and not line.startswith("#")]

# Trophy locations (valheimapworld/Locations.py, read only).
trophies = re.findall(r"^Trophy,Trophy: (\w+),", (root / "valheimapworld" / "Locations.py").read_text(), re.M)
trophy_results = [node_biome(t) for t in trophies]

unresolved = [(r[2], n) for r, (b, n) in zip(check_rows, check_results) if b >= INF]
unresolved += [(f"Research {r[2]}", research_biome[r[2]][1]) for r in research_rows if research_biome[r[2]][0] >= INF]
unresolved += [(f"Trophy: {t}", n) for t, (b, n) in zip(trophies, trophy_results) if b >= INF]
if unresolved:
    for what, notes in unresolved:
        print(f"UNRESOLVED {what}: {sorted(notes)}")
    sys.exit("some checks have no biome; add the missing source to an override table")

checks_path.write_text("\n".join(write_column(check_lines, CHECK_COLS, "# kind\t",
                                              [name(b) for b, _ in check_results])))
research_path.write_text("\n".join(write_column(research_lines, RESEARCH_COLS, "# iconFromItemPrefab\t",
                                                [name(research_biome[r[2]][0]) for r in research_rows])))
# A research item (as opposed to its check at the Research Bench) is worth having where something it unlocks can
# be made: the earliest of those. An Eikthyr game has Axes Tier 1 (the Stone Axe) though its research costs
# Greydwarf Eyes.
unlock_biome = {}
for r in research_rows:
    made = [node_biome(f"piece:{g}" if g in db["pieces"] else g)[0] for g in research_gated.get(r[2], ())]
    made = [b for b in made if b < INF]
    unlock_biome[r[2]] = min(made) if made else research_biome[r[2]][0]
    if not made:
        print(f"  research {r[2]}: nothing it unlocks resolves; its item goes by its cost")
(root / "mod" / "research_unlock_biomes.tsv").write_text(
    "# Generated by tools/gen_check_biomes.py: the earliest biome where something each research unlocks can be made.\n"
    "#research\tbiome\n" + "".join(f"{r[2]}\t{name(unlock_biome[r[2]])}\n" for r in research_rows))
(root / "mod" / "trophy_biomes.tsv").write_text(
    "# Generated by tools/gen_check_biomes.py: the biome of each APWorld \"Trophy: <prefab>\" location.\n"
    "#trophy\tbiome\n" + "".join(f"{t}\t{name(b)}\n" for t, (b, _) in zip(trophies, trophy_results)))

# ---------------------------------------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------------------------------------
everything = [(r[0], r[2], b, n) for r, (b, n) in zip(check_rows, check_results)]
everything += [("research", f"Research: {r[2]}", research_biome[r[2]][0], research_biome[r[2]][1]) for r in research_rows]
everything += [("trophy", f"Trophy: {t}", b, n) for t, (b, n) in zip(trophies, trophy_results)]

kinds = list(dict.fromkeys(k for k, *_ in everything))
counts = Counter((k, b) for k, _, b, _ in everything)
print("Checks per biome and kind (research and trophy: Locations.py locations, not checks.tsv rows):")
print(f"{'kind':10}" + "".join(f"{n[:7]:>8}" for n in ORDER) + f"{'total':>8}")
for k in kinds:
    print(f"{k:10}" + "".join(f"{counts[(k, b)] or '':>8}" for b in range(len(ORDER)))
          + f"{sum(counts[(k, b)] for b in range(len(ORDER))):>8}")
print(f"{'all':10}" + "".join(f"{sum(counts[(k, b)] for k in kinds):>8}" for b in range(len(ORDER)))
      + f"{len(everything):>8}")

for b in (B["Meadows"], B["BlackForest"]):
    print(f"\n=== {ORDER[b]} ===")
    skills = defaultdict(list)
    for k, label, bb, _ in everything:
        if bb != b:
            continue
        if k == "skill":
            skill, level = label[len("Skill: "):].rsplit(" ", 1)
            skills[skill].append(int(level))
            continue
        print(f"  {k:9} {label}")
    for skill, levels in skills.items():
        print(f"  {'skill':9} Skill: {skill} {min(levels)}-{max(levels)} ({len(levels)} rows)")

print("\n=== Biomes decided by an override or fallback ===")
seen_skill = set()
for k, label, b, notes in everything:
    if not notes:
        continue
    if k == "skill":
        group = (label.rsplit(" ", 1)[0], b, tuple(sorted(notes)))
        if group in seen_skill:
            continue
        seen_skill.add(group)
        label = group[0] + " (all levels)"
    print(f"  {name(b):11} {label}: " + "; ".join(sorted(notes)))

print("\nComfort levels by the pieces you can build"
      + (" (used)" if COMFORT_FROM_PIECES else " (not used: comfort rows are Meadows)") + ": "
      + ", ".join(f"{lvl}:{name(b)}" for lvl, b in sorted(comfort_biome.items())))
print(f"\nwrote mod/checks.tsv ({len(check_rows)} rows), mod/research.tsv ({len(research_rows)} rows), "
      f"mod/trophy_biomes.tsv ({len(trophies)} rows)")
