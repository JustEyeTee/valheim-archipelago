"""Writes the read, vegvisir, plant and loot rows of mod/checks.tsv from the game database. Run
tools/gen_apworld_data.py afterwards.

    python3 tools/gen_world_checks.py ~/projects/valheim-archipelago-refs/gamedb.json

read:     each biome's lore rune stones (a Runestone_* world location), sent when you read one there.
vegvisir: each boss's Vegvisir, sent when you read one; keyed by the boss location it reveals.
plant:    planting each crop and tree with the Cultivator (a sapling piece).
brew:     tapping each mead from a Fermenter (keyed by the mead), with the Mead ketill and the Fermenter.
loot:     opening a dungeon's treasure chest (Burial Chamber, Troll Cave, Sunken Crypt, Frost Cave,
          Infested Mine, Charred Fortress), keyed by the chest prefab, which only those dungeons have.

Tiers follow the rest of the logic: a biome's entry check, a boss altar's discover check, a dungeon's
discover check, for planting the latest of the seed's obtain check, the Cultivator and the biome, and for
brewing the latest of the ingredients' obtain checks, the Mead ketill and the Fermenter.
"""
import csv
import json
import pathlib
import sys

root = pathlib.Path(__file__).resolve().parent.parent
db = json.load(open(sys.argv[1]))

check_rows = [r for r in csv.reader(open(root / "mod" / "checks.tsv", newline=""), delimiter="\t")]
tier_of = {r[2]: int(r[3]) for r in check_rows if r and not r[0].startswith("#")}
# Item prefab -> the check for getting it (obtain checks, and catch checks for fish).
obtain = {r[1]: r[2] for r in check_rows if r and r[0] in ("obtain", "catch")}
research = {}  # piece prefab -> (research name, tier)
for r in csv.reader(open(root / "mod" / "research.tsv", newline=""), delimiter="\t"):
    if r and not r[0].startswith("#"):
        for prefab in filter(None, r[6].split("|")):
            research[prefab] = (r[2], int(r[7]))

# The biome entry checks' tiers (Biome: checks are the APWorld's own, not in checks.tsv); Meadows is 0.
BIOME_TIERS = {1: 0, 8: 0, 2: 4, 4: 6, 16: 7, 512: 9, 32: 11, 64: 12}
BIOME_NAMES = {1: "Meadows", 8: "Black Forest", 2: "Swamp", 4: "Mountains", 16: "Plains", 512: "Mistlands",
               32: "Ashlands", 64: "Deep North"}

def replace_rows(rows, kinds, new):
    """rows with those kinds' rows replaced by new ones. Location ids follow the order of checks.tsv, so a row
    that's already there keeps its place (updated), one that's gone is dropped, and a new one goes at the end."""
    by_key = {(n[0], n[1]): n for n in new}
    out, kept = [], set()
    for r in rows:
        if r and r[0] in kinds:
            if (r[0], r[1]) in by_key:
                out.append(by_key[(r[0], r[1])])
                kept.add((r[0], r[1]))
            continue
        out.append(r)
    while out and not out[-1]:
        out.pop()
    return out + [n for n in new if (n[0], n[1]) not in kept]


rows = []

# ---------- Rune stones: the lore stones of each Runestone_* location ----------
RUNESTONE_NAMES = {"Runestone_Boars": "Boars", "Runestone_Greydwarfs": "Greydwarfs", "Runestone_Draugr": "Draugr",
                   "Runestone_Swamps": "Swamp", "Runestone_BlackForest": "Black Forest"}
seen = set()
for lst in db["locations"]["lists"]:
    for entry in lst["entries"]:
        name = entry.get("name") or entry.get("prefabName")
        if not name or not name.startswith("Runestone_") or name in seen:
            continue
        seen.add(name)
        biome = entry["biome"]
        label = RUNESTONE_NAMES.get(name, BIOME_NAMES.get(biome, name[len("Runestone_"):]))
        rows.append(["read", name, f"Read: Runestone ({label})", str(BIOME_TIERS[biome]), ""])

# ---------- Vegvisirs: one per boss, keyed by the boss location they reveal ----------
BOSS_LOCATIONS = {"Eikthyrnir": ("Eikthyr", "Discover: Eikthyr's Altar"), "GDKing": ("The Elder", "Discover: The Elder's Altar"),
                  "Bonemass": ("Bonemass", "Discover: Bonemass's Altar"), "Dragonqueen": ("Moder", "Discover: Moder's Altar"),
                  "GoblinKing": ("Yagluth", "Discover: Yagluth's Altar"),
                  "Mistlands_DvergrBossEntrance1": ("The Queen", "Discover: Infested Citadel"),
                  "FaderLocation": ("Fader", "Discover: Fader's Altar"), "DN_Bossroom": ("Kall Fimbulbringer", "Discover: The First Prison")}
targets = {loc for v in db["vegvisirs"].values() for loc in v["locations"]}
for location, (boss, discover) in BOSS_LOCATIONS.items():
    if location in targets:
        rows.append(["vegvisir", location, f"Vegvisir: {boss}", str(tier_of[discover]), ""])

# ---------- Planting: crops and trees, with the Cultivator ----------
PLANT_NAMES = {"sapling_carrot": "Carrot", "sapling_seedcarrot": "Carrot (for seeds)", "sapling_turnip": "Turnip",
               "sapling_seedturnip": "Turnip (for seeds)", "sapling_onion": "Onion", "sapling_seedonion": "Onion (for seeds)",
               "sapling_barley": "Barley", "sapling_flax": "Flax", "sapling_magecap": "Magecap",
               "sapling_jotunpuffs": "Jotun Puffs", "sapling_oat": "Oats", "sapling_poteitr": "Poteitr",
               "sapling_Kale": "Kale", "sapling_seedkale": "Kale (for seeds)", "VineAsh_sapling": "Vineberry",
               "VineGreen_sapling": "Ashvine", "Beech_Sapling": "Beech", "Birch_Sapling": "Birch",
               "FirTree_Sapling": "Fir", "PineTree_Sapling": "Pine", "Oak_Sapling": "Oak"}
cultivator = research["Cultivator"]
skipped = []
for prefab, label in PLANT_NAMES.items():
    plant, piece = db["plants"].get(prefab), db["pieces"].get(prefab)
    if not plant or not piece:
        skipped.append((prefab, "not in the game data"))
        continue
    seeds = [i["item"] for i in piece["ingredients"]]
    if any(s not in obtain for s in seeds):
        skipped.append((prefab, f"no obtain check for {[s for s in seeds if s not in obtain]}"))
        continue
    biome_tier = min(t for bit, t in BIOME_TIERS.items() if plant["biome"] & bit)
    reqs = [cultivator[0]] + ([research[prefab][0]] if prefab in research else [])
    tier = max([tier_of[obtain[s]] for s in seeds] + [cultivator[1], biome_tier]
               + ([research[prefab][1]] if prefab in research else []))
    rows.append(["plant", prefab, f"Plant: {label}", str(tier), "|".join(reqs)])

# ---------- Brewing: each mead tapped from a Fermenter ----------
MEAD_NAMES = {"MeadBugRepellent": "Anti-Sting Concoction", "MeadBzerker": "Berserkir Mead",
              "MeadEitrLingering": "Lingering Eitr Mead", "MeadEitrMinor": "Minor Eitr Mead",
              "MeadFrostResist": "Frost Resistance Mead", "MeadHasty": "Tonic of Ratatosk",
              "MeadHealthLingering": "Lingering Healing Mead", "MeadHealthMajor": "Major Healing Mead",
              "MeadHealthMedium": "Medium Healing Mead", "MeadHealthMinor": "Minor Healing Mead",
              "MeadLightfoot": "Lightfoot Mead", "MeadPoisonResist": "Poison Resistance Mead",
              "MeadStaminaLingering": "Lingering Stamina Mead", "MeadStaminaMedium": "Medium Stamina Mead",
              "MeadStaminaMinor": "Minor Stamina Mead", "MeadStrength": "Mead of Troll Endurance",
              "MeadSwimmer": "Draught of Vananidir", "MeadTamer": "Brew of Animal Whispers", "MeadTasty": "Tasty Mead"}
brewing = [research["piece_MeadCauldron"], research["fermenter"]]
meads = {m.lower(): m for m in MEAD_NAMES}
for recipe in sorted(db["recipes"].values(), key=lambda r: r["item"] or ""):
    base = recipe["item"] or ""
    mead = meads.get(base.replace("MeadBase", "Mead").lower()) if base.startswith("MeadBase") else None
    if not mead:
        continue
    materials = [i["item"] for i in recipe["ingredients"]]
    if any(m not in obtain for m in materials):
        skipped.append((mead, f"no obtain check for {[m for m in materials if m not in obtain]}"))
        continue
    tier = max([tier_of[obtain[m]] for m in materials] + [t for _, t in brewing])
    rows.append(["brew", mead, f"Brew: {MEAD_NAMES[mead]}", str(tier), "|".join(name for name, _ in brewing)])

# ---------- Dungeon loot: the treasure chests only these dungeons have ----------
LOOT = {"TreasureChest_forestcrypt": ("Burial Chamber", "Discover: Burial Chamber"),
        "TreasureChest_trollcave": ("Troll Cave", "Discover: Troll Cave"),
        "TreasureChest_sunkencrypt": ("Sunken Crypt", "Discover: Sunken Crypt"),
        "TreasureChest_mountaincave": ("Frost Cave", "Discover: Frost Cave"),
        "TreasureChest_dvergrtown": ("Infested Mine", "Discover: Infested Mine"),
        "TreasureChest_charredfortress": ("Charred Fortress", "Discover: Charred Fortress")}
known = json.dumps(db)
for chest, (label, discover) in LOOT.items():
    if chest not in known:
        skipped.append((chest, "not in the game data"))
        continue
    rows.append(["loot", chest, f"Loot: {label}", str(tier_of[discover]), ""])

KINDS = ("read", "vegvisir", "plant", "brew", "loot")
with open(root / "mod" / "checks.tsv", "w", newline="") as f:
    csv.writer(f, delimiter="\t", lineterminator="\n").writerows(replace_rows(check_rows, KINDS, rows))

for kind in KINDS:
    print(f"{kind}: " + ", ".join(f"{r[2][r[2].index(': ') + 2:]} T{r[3]}" for r in rows if r[0] == kind))
for what, why in skipped:
    print(f"  left out {what}: {why}")
