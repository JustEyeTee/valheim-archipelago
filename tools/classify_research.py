"""Fills mod/research.tsv's `kind` column (the last one) from what each research unlocks, using the game data
(gamedb.json from tools/scan_game_data.py):
    equipment  weapons, armor, shields, capes, tools, ammo, trinkets, torches (with any materials they bring)
    building   building pieces and crafting stations
    material   materials only (Bronze, Nails, Ceramic Plates...)
Only equipment researches are locked unless item_sanity is on; the others are known from the start.
Run after adding researches:  python3 tools/classify_research.py [path/to/gamedb.json]
"""
import json
import pathlib
import sys

root = pathlib.Path(__file__).resolve().parent.parent
gamedb = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else root.parent / "valheim-archipelago-refs" / "gamedb.json")
db = json.load(open(gamedb))
items, pieces = db["items"], db["pieces"]

# ItemDrop.ItemData.ItemType values a player equips (Ammo is 9; AmmoNonEquipable 23, Material 1, Consumable 2,
# Trophy 13, Misc 16 and Fish 21 are not).
EQUIPPABLE = {3, 4, 5, 6, 7, 9, 11, 12, 14, 15, 17, 18, 19, 20, 22, 24}

path = root / "mod" / "research.tsv"
lines = path.read_text().split("\n")
counts = {}
for i, line in enumerate(lines):
    if not line:
        continue
    cols = line.split("\t")
    if line.startswith("#"):
        if len(cols) < 11:
            cols.append("kind")
        lines[i] = "\t".join(cols)
        continue
    cols = cols + [""] * (11 - len(cols))  # the kind column is the 11th; later ones (biome) are kept
    gated = [g for g in cols[6].split("|") if g]
    unknown = [g for g in gated if g not in items and g not in pieces]
    if unknown:
        sys.exit(f"{cols[2]}: not in the game data: {unknown}")
    types = {items[g]["itemType"] for g in gated if g in items}
    if types & EQUIPPABLE:
        kind = "equipment"
    elif any(g in pieces for g in gated):
        kind = "building"
    else:
        kind = "material"
    cols[10] = kind
    counts[kind] = counts.get(kind, 0) + 1
    lines[i] = "\t".join(cols)
path.write_text("\n".join(lines))
print(counts)
