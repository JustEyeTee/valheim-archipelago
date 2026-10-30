# Combat readiness: the gear (research items) each era's challenges expect. Every set lists gear from that
# era or the one before, all of it researched in an earlier tier than the gates that ask for it.
# Idea from xyzzy44's version of the randomizer (tier entrances that need armor and weapons).

COMBAT_ERAS = {
    "Meadows": {
        "armor": (),
        "weapons": ("Clubs Tier 1", "Axes Tier 1", "Blades Tier 1", "Spears Tier 1", "Knuckles Tier 1",
                    "Short Blades Tier 1"),
        "ranged": ("Bows Tier 1",),
    },
    "Black Forest": {
        "armor": ("Leather Armor", "Rag Armor", "Troll Armor", "Bear Armor"),
        "weapons": ("Clubs Tier 1", "Axes Tier 1", "Blades Tier 1", "Spears Tier 1", "Knuckles Tier 1",
                    "Short Blades Tier 1", "Sledgehammers Tier 1"),
        "ranged": ("Bows Tier 1",),
    },
    "Bronze": {
        "armor": ("Troll Armor", "Bear Armor", "Bronze Armor"),
        "weapons": ("Axes Tier 2", "Blades Tier 2", "Clubs Tier 2", "Spears Tier 2", "Polearms Tier 1",
                    "Sledgehammers Tier 1", "Short Blades Tier 2"),
        "ranged": ("Bows Tier 1", "Bows Tier 2"),
    },
    "Iron": {
        "armor": ("Bronze Armor", "Root Armor", "Iron Armor"),
        "weapons": ("Axes Tier 3", "Blades Tier 3", "Clubs Tier 3", "Spears Tier 3", "Polearms Tier 2",
                    "Battleaxes Tier 1", "Sledgehammers Tier 2", "Short Blades Tier 3"),
        "ranged": ("Bows Tier 2", "Bows Tier 3"),
    },
    "Silver": {
        "armor": ("Iron Armor", "Root Armor", "Wolf Armor", "Fenris Armor"),
        "weapons": ("Blades Tier 4", "Clubs Tier 4", "Spears Tier 4", "Battleaxes Tier 2", "Knuckles Tier 2",
                    "Short Blades Tier 4"),
        "ranged": ("Bows Tier 3", "Bows Tier 4"),
    },
    "Black Metal": {
        "armor": ("Wolf Armor", "Fenris Armor", "Padded Armor", "Vilebone Armor"),
        "weapons": ("Axes Tier 4", "Blades Tier 5", "Clubs Tier 5", "Battleaxes Tier 3", "Polearms Tier 3",
                    "Knuckles Tier 3", "Short Blades Tier 5", "Short Blades Tier 6"),
        "ranged": ("Bows Tier 4",),
    },
    "Mistlands": {
        "armor": ("Padded Armor", "Vilebone Armor", "Carapace Armor", "Eitr Armor"),
        "weapons": ("Spears Tier 5", "Blades Tier 6", "Battleaxes Tier 4", "Polearms Tier 4", "Axes Tier 5",
                    "Sledgehammers Tier 3", "Elemental Magic Tier 1", "Blood Magic Tier 1"),
        "ranged": ("Crossbows Tier 1", "Bows Tier 5"),
    },
    "Ashlands": {
        "armor": ("Carapace Armor", "Eitr Armor", "Flametal Armor", "Ask Armor", "Embla Armor"),
        "weapons": ("Blades Tier 7", "Blades Tier 8", "Battleaxes Tier 5", "Battleaxes Tier 6", "Clubs Tier 6",
                    "Clubs Tier 7", "Spears Tier 6", "Spears Tier 7", "Elemental Magic Tier 2",
                    "Elemental Magic Tier 3", "Blood Magic Tier 2"),
        "ranged": ("Bows Tier 6", "Bows Tier 7", "Crossbows Tier 2", "Crossbows Tier 3"),
    },
    "Deep North": {
        "armor": ("Protector Armor", "Vanguard Armor", "Caller Armor"),
        "weapons": ("Nord Weapons Tier 1", "Nord Weapons Tier 2", "Thunderblood Weapons", "Frostfire Weapons",
                    "Nord Staffs"),
        "ranged": ("Nord Bows and Crossbows",),
    },
}

# What each challenge asks for: entering a tier (a new biome) or a boss's goal location.
COMBAT_GATES = {
    "Trophy: TrophyEikthyr": "Meadows",
    "Trophy: TrophyTheElder": "Black Forest",
    "Tier4": "Black Forest",                 # into the Swamp
    "Trophy: TrophyBonemass": "Bronze",
    "Tier7": "Iron",                         # into the Mountains
    "Trophy: TrophyDragonQueen": "Iron",
    "Tier8": "Silver",                       # into the Plains
    "Trophy: TrophyGoblinKing": "Silver",
    "Tier9": "Black Metal",                  # into the Mistlands
    "Trophy: TrophySeekerQueen": "Black Metal",
    "Tier11": "Mistlands",                   # into the Ashlands
    "Trophy: TrophyFader": "Mistlands",
    "Tier12": "Ashlands",                    # into the Deep North
    "Obtain: Sacrificial Blood": "Deep North",
}

COMBAT_ITEMS = frozenset(name for era in COMBAT_ERAS.values() for kind in era.values() for name in kind)
