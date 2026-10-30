"""Builds the comfort data from the game database: valheimapworld/comfort_data.py (each comfort piece and
what building it needs) and the comfort rows of mod/checks.tsv (one per comfort level, at the earliest tier
it can be reached). Run tools/gen_apworld_data.py afterwards.

    python3 tools/gen_comfort_data.py ~/projects/valheim-archipelago-refs/gamedb.json

How the game counts comfort (SE_Rested.CalculateComfortLevel): 1, plus 1 when sheltered, plus (only when
sheltered) the comfort of the pieces within 10 m: the best piece of each comfort group (Fire, Bed, Banner,
Chair...), and every differently-named piece that has no group.

The database has every Piece in the game files, not just what you can build: copies placed in world
locations ("hearth (1)", "fire_pit_haldor"), camp decoration and seasonal pieces. Logic only counts a piece
that is gated by a research or built at a crafting station, isn't a numbered copy or seasonal, and, when
another piece with the same name is research-gated, is that gated one.

A piece counts in logic when its research (if one gates it) and its crafting station's research are
received and each of its materials can be obtained (its "Obtain:" check's rules). A piece with a material
that has no obtain check is left out, which only makes logic expect less comfort than you can get.
"""
import csv
import json
import pathlib
import sys

root = pathlib.Path(__file__).resolve().parent.parent
db = json.load(open(sys.argv[1]))

GROUPS = ["None", "Fire", "Bed", "Banner", "Chair", "Table", "Carpet", "Display", "Decor", "Garland", "Lantern",
          "Leisure"]
# Only buildable during holiday events.
SEASONAL = ("piece_CelebrationGarland", "piece_FairylightGarland", "piece_xmastree", "piece_jackoturnip",
            "piece_maypole", "piece_gift1", "piece_gift2", "piece_gift3", "piece_mistletoe", "piece_xmascrown",
            "piece_xmasgarland")
SHELTER_PIECE = "wood_roof"  # the thatch roof: the first roof you can build
COMFORT_ROW = "comfort"

research = {}  # piece or station prefab -> (research display name, research tier)
for r in csv.reader(open(root / "mod" / "research.tsv", newline=""), delimiter="\t"):
    if not r or r[0].startswith("#"):
        continue
    for prefab in filter(None, r[6].split("|")):
        research[prefab] = (r[2], int(r[7]))

check_rows = [r for r in csv.reader(open(root / "mod" / "checks.tsv", newline=""), delimiter="\t")]
obtain = {r[1]: (r[2], int(r[3])) for r in check_rows if r and r[0] == "obtain"}  # item prefab -> (location, tier)



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


def needs(prefab):
    """(research items, obtain checks, tier) to build a piece, or None if a material has no obtain check."""
    piece = db["pieces"][prefab]
    materials = [i["item"] for i in piece["ingredients"]]
    if any(m not in obtain for m in materials):
        skipped.append((prefab, [m for m in materials if m not in obtain]))
        return None
    gates = [g for g in (research.get(prefab), research.get(piece.get("station")) if piece.get("station") else None) if g]
    tier = max([obtain[m][1] for m in materials] + [t for _, t in gates])
    return tuple(sorted({name for name, _ in gates})), tuple(sorted({obtain[m][0] for m in materials})), tier


def buildable(prefab, piece):
    return (" (" not in prefab and prefab not in SEASONAL and (prefab in research or piece.get("station"))
            and (prefab in research or piece["name"] not in gated_names))


gated_names = {db["pieces"][p]["name"] for p in research if p in db["pieces"]}
pieces, skipped = [], []
for prefab, piece in sorted(db["pieces"].items()):
    if (piece.get("comfort") or 0) <= 0 or not piece.get("enabled", 1) or not piece.get("ingredients") \
            or not buildable(prefab, piece):
        continue
    need = needs(prefab)
    if need:
        pieces.append((prefab, piece["name"], piece["comfort"], GROUPS[piece.get("comfort_group") or 0], *need))
shelter = needs(SHELTER_PIECE)


def best(tier):
    """The most comfort reachable with the pieces available by this tier (sheltered)."""
    by_group, ungrouped = {}, {}
    for _, name, comfort, group, _, _, piece_tier in pieces:
        if piece_tier > tier:
            continue
        if group == "None":
            ungrouped[name] = max(ungrouped.get(name, 0), comfort)
        else:
            by_group[group] = max(by_group.get(group, 0), comfort)
    return 2 + sum(by_group.values()) + sum(ungrouped.values())


levels = {}  # comfort level -> earliest tier
for tier in range(shelter[2], 13):
    for level in range(2, best(tier) + 1):
        levels.setdefault(level, tier)

out = ["# Generated by tools/gen_comfort_data.py from the game database. Do not edit by hand.",
       "",
       f"# Building a roof ({SHELTER_PIECE}; comfort only counts when sheltered): (research items, obtain checks, tier)",
       f"SHELTER = {shelter!r}",
       "",
       "# The most comfort logic can count on, in the full game.",
       f"MAX_COMFORT = {max(levels)}",
       "",
       "# (piece prefab, display token, comfort, comfort group, research items for it and its crafting station,",
       "#  obtain checks for its materials, tier)",
       "COMFORT_PIECES = ("]
out += [f"    {p!r}," for p in pieces]
out += [")", ""]
(root / "valheimapworld" / "comfort_data.py").write_text("\n".join(out))

comfort_rows = [[COMFORT_ROW, str(level), f"Comfort: Level {level}", str(tier), ""] for level, tier in sorted(levels.items())]
with open(root / "mod" / "checks.tsv", "w", newline="") as f:
    csv.writer(f, delimiter="\t", lineterminator="\n").writerows(replace_rows(check_rows, (COMFORT_ROW,), comfort_rows))

print(f"{len(pieces)} comfort pieces; levels {min(levels)}-{max(levels)}: "
      + ", ".join(f"{level}@T{tier}" for level, tier in sorted(levels.items())))
for prefab, missing in skipped:
    print(f"  left out {prefab}: no obtain check for {missing}")
