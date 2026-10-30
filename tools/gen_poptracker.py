"""Builds the PopTracker pack in poptracker/ from the APWorld's own tables, so the tracker's
logic is the generator's logic: tier gates, research prerequisites, station requirements
and boss gates (a boss counts as defeated when its trophy check is done, or its drop is
received).

Needs Archipelago's Python (for BaseClasses) and Pillow, e.g.:
    ~/projects/archipelago-0.6.8/.venv/bin/python tools/gen_poptracker.py ~/projects/archipelago-0.6.8

Layout: one map with a grid of pins, a row per tier and a column per kind of check; each
pin holds that tier's checks of that kind. Checks the connected seed doesn't have (options,
goal) are cleared when autotracking connects.
"""
import json
import pathlib
import re
import shutil
import sys

root = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(pathlib.Path(sys.argv[1]).resolve()))
sys.path.insert(0, str(root))

from PIL import Image, ImageDraw, ImageFont  # noqa: E402
from worlds.AutoWorld import AutoWorldRegister  # noqa: E402

# Archipelago loads an installed valheimapworld.apworld too; use this repo's copy instead.
AutoWorldRegister.world_types.pop("Valheim", None)
import valheimapworld as world  # noqa: E402
from valheimapworld.Locations import location_data_table, location_table  # noqa: E402
from valheimapworld.Items import item_table  # noqa: E402
from valheimapworld.Regions import region_data_table  # noqa: E402

out = root / "poptracker"
version = json.load(open(root / "valheimapworld" / "archipelago.json"))["world_version"]
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"


def code(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


def boss_code(boss: str) -> str:
    return "boss_" + code(boss)


# ---------- Items: everything logic looks at ----------
# (Comfort counts the researches that unlock comfort pieces and roofs.)
logic_items = sorted(world.LOGIC_ITEMS | world.COMBAT_ITEMS | {n for p in world.COMFORT_PIECES for n in p[4]}
                     | set(world.SHELTER[0]))
key_items = list(world.BOSS_DROP_ITEMS.values()) + list(world.ALTAR_KEYS.values())
bosses = list(world.BOSS_ORDER)
gate_items = []  # tier gate items in tier order, shown first
for region in region_data_table.values():
    for connection in region.connections:
        gate_items += [i for i in connection.required_items if i not in gate_items]


def icon(path, label, colour):
    image = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((2, 2, 61, 61), radius=10, fill=colour, outline=(240, 240, 240), width=2)
    words = label.split()
    text = "".join(w[0] for w in words if w[0].isalnum())[:3].upper() if len(words) > 1 else label[:3].upper()
    font = ImageFont.truetype(FONT, 22 if len(text) <= 2 else 18)
    box = draw.textbbox((0, 0), text, font=font)
    draw.text(((64 - box[2] + box[0]) / 2, (64 - box[3] + box[1]) / 2 - 2), text, font=font, fill="white")
    image.save(path)


if out.exists():
    shutil.rmtree(out)
for d in ("items", "locations", "layouts", "maps", "scripts", "images/items"):
    (out / d).mkdir(parents=True)

items_json = []
for name in logic_items:
    icon(out / f"images/items/{code(name)}.png", name, (40, 80, 140))
    items_json.append({"name": name, "type": "toggle", "img": f"images/items/{code(name)}.png", "codes": code(name)})
for name in key_items:
    icon(out / f"images/items/{code(name)}.png", name.lstrip("3 "), (150, 110, 20))
    items_json.append({"name": name, "type": "toggle", "img": f"images/items/{code(name)}.png", "codes": code(name)})
for boss in bosses:
    icon(out / f"images/items/{boss_code(boss)}.png", boss, (140, 30, 30))
    items_json.append({"name": f"{boss} Defeated", "type": "toggle", "img": f"images/items/{boss_code(boss)}.png",
                       "codes": boss_code(boss)})
json.dump(items_json, open(out / "items/items.json", "w"), indent=1)

# ---------- Locations ----------
# Tier region -> (items, bosses, combat eras) needed to get there, summed along the chain.
region_items, region_bosses, region_combat = {}, dict(world.REGION_BOSSES), {}
_region, _items, _combat = "Menu", [], []
while True:
    region_items[_region] = list(_items)
    region_combat[_region] = list(_combat)
    connections = region_data_table[_region].connections
    if not connections:
        break
    _items += [i for i in connections[0].required_items if i not in _items]
    _region = connections[0].destination
    if _region in world.COMBAT_GATES:
        _combat.append(world.COMBAT_GATES[_region])


def boss_token(token):
    return f"$kill|{code(world.boss_name(token))}" if token.startswith("kill:") else f"$boss|{code(token)}"


def rule(location):
    name = location.user_friendly_name
    codes = [code(i) for i in region_items[location.region] + list(world.LOCATION_REQS.get(name, ()))]
    tokens = sorted({boss_token(b) for b in world.LOCATION_BOSSES[name] | region_bosses[location.region]})
    eras = region_combat[location.region] + ([world.COMBAT_GATES[name]] if name in world.COMBAT_GATES else [])
    combat = [f"$combat|{code(era)}" for era in dict.fromkeys(eras)]
    comfort = [f"$comfort|{world.comfort_level(name)}"] if name.startswith(world.COMFORT) else []
    altar = [f"$altarkey|{code(world.ALTAR_GATED[name])}"] if name in world.ALTAR_GATED else []
    return ",".join(dict.fromkeys(codes + tokens + combat + comfort + altar))


def category(name):
    return name.split(":")[0] if ":" in name else "Research"


categories = ["Research", "Trophy", "Biome", "Discover", "Obtain", "Eat", "Catch", "Build", "Buy", "Tame", "Kill",
              "Skill", "Explore", "Comfort", "Read", "Vegvisir", "Plant", "Brew", "Loot"]
tiers = sorted({int(l.region[len("Tier"):]) for l in location_data_table})
CELL_W, CELL_H, LEFT, TOP = 110, 64, 90, 50
groups = {}
for location in location_data_table:
    tier = int(location.region[len("Tier"):])
    groups.setdefault((category(location.user_friendly_name), tier), []).append(location)

locations_json, location_codes = [], {}
for (cat, tier), members in sorted(groups.items(), key=lambda g: (categories.index(g[0][0]), g[0][1])):
    group = f"{cat} - Tier {tier}"
    sections = []
    for location in members:
        r = rule(location)
        sections.append({"name": location.user_friendly_name, "item_count": 1, **({"access_rules": [r]} if r else {})})
        location_codes[location_table[location.user_friendly_name]] = f"@{group}/{location.user_friendly_name}"
    locations_json.append({
        "name": group,
        "sections": sections,
        "map_locations": [{"map": "Overview", "x": LEFT + categories.index(cat) * CELL_W + CELL_W // 2,
                           "y": TOP + tiers.index(tier) * CELL_H + CELL_H // 2}],
    })
json.dump(locations_json, open(out / "locations/locations.json", "w"), indent=1)

# ---------- Map: the grid the pins sit on ----------
width, height = LEFT + len(categories) * CELL_W + 10, TOP + len(tiers) * CELL_H + 10
image = Image.new("RGB", (width, height), (28, 30, 34))
draw = ImageDraw.Draw(image)
font, small = ImageFont.truetype(FONT, 15), ImageFont.truetype(FONT, 12)
era = {0: "Meadows", 1: "Black Forest", 3: "Copper", 4: "Swamp", 6: "Iron", 7: "Mountains", 8: "Plains",
       9: "Mistlands", 11: "Ashlands", 12: "Deep North"}
for i, cat in enumerate(categories):
    draw.text((LEFT + i * CELL_W + 8, 18), cat, font=font, fill=(230, 230, 230))
for j, tier in enumerate(tiers):
    y = TOP + j * CELL_H
    draw.line((10, y, width - 10, y), fill=(60, 64, 70))
    draw.text((12, y + 12), f"Tier {tier}", font=font, fill=(230, 230, 230))
    if tier in era:
        draw.text((12, y + 34), era[tier], font=small, fill=(160, 160, 160))
image.save(out / "maps/overview.png")
json.dump([{"name": "Overview", "img": "maps/overview.png", "location_size": 34, "location_border_thickness": 2}],
          open(out / "maps/maps.json", "w"), indent=1)

# ---------- Layouts ----------
def rows(codes, per_row=10):
    return [codes[i:i + per_row] for i in range(0, len(codes), per_row)]


json.dump({
    "boss_grid": {"type": "itemgrid", "item_margin": "2,2", "item_size": 40,
                  "rows": [[boss_code(b) for b in bosses], [code(k) for k in key_items]]},
    "gate_grid": {"type": "itemgrid", "item_margin": "2,2", "item_size": 40, "rows": rows([code(i) for i in gate_items], 8)},
}, open(out / "layouts/items.json", "w"), indent=1)
json.dump({
    "tracker_default": {"type": "container", "background": "#1c1e22", "content": {
        "type": "dock", "dropshadow": True, "content": [
            {"type": "dock", "dock": "left", "v_alignment": "stretch", "content": [
                {"type": "group", "header": "Bosses and boss drops", "dock": "top", "content": {"type": "layout", "key": "boss_grid"}},
                {"type": "group", "header": "Tier gates", "dock": "top", "content": {"type": "layout", "key": "gate_grid"}},
            ]},
            {"type": "map", "maps": ["Overview"]},
        ]}},
    "tracker_broadcast": {"type": "group", "header": "Bosses", "content": {"type": "layout", "key": "boss_grid"}},
}, open(out / "layouts/tracker.json", "w"), indent=1)

# ---------- Scripts ----------
lua_str = lambda s: json.dumps(s)


def comfort_needs(items, tier):
    """A comfort piece's researches and the tier gates up to the tier its materials come from."""
    return list(dict.fromkeys(list(region_items[f"Tier{tier}"]) + list(items)))

(out / "scripts/item_mapping.lua").write_text(
    "-- Generated by tools/gen_poptracker.py\nITEM_MAPPING = {\n" +
    "".join(f"  [{item_table[n]}] = {lua_str(code(n))},\n" for n in logic_items + key_items) + "}\n")
trophies = {location_table[t]: boss_code(b) for b, t in world.BOSS_TROPHIES.items()}
(out / "scripts/location_mapping.lua").write_text(
    "-- Generated by tools/gen_poptracker.py\nLOCATION_MAPPING = {\n" +
    "".join(f"  [{i}] = {lua_str(c)},\n" for i, c in sorted(location_codes.items())) + "}\n" +
    "TROPHY_BOSS = {\n" + "".join(f"  [{i}] = {lua_str(c)},\n" for i, c in trophies.items()) + "}\n")
(out / "scripts/logic.lua").write_text(
    "-- Generated by tools/gen_poptracker.py\n"
    "BOSS_DROP = {\n" +
    "".join(f"  {code(b)} = {lua_str(code(i))},\n" for b, i in world.BOSS_DROP_ITEMS.items()) + "}\n"
    """
function has(item)
  return Tracker:ProviderCountForCode(item) > 0
end

-- A boss's drop: defeated (its trophy check done) or the drop received as an item.
function boss(name)
  return has("boss_" .. name) or (BOSS_DROP[name] ~= nil and has(BOSS_DROP[name]))
end

-- Only defeating it works (Haldor's boss-unlocked stock, Hens).
function kill(name)
  return has("boss_" .. name)
end

-- Combat logic (the seed's combat_logic option, read when autotracking connects): armor and a weapon
-- from an era, and with strict a bow or crossbow too. 0 = off, 1 = normal, 2 = strict.
COMBAT_MODE = 1

local function any_of(list)
  if #list == 0 then return true end
  for _, item in ipairs(list) do
    if has(item) then return true end
  end
  return false
end

function combat(era)
  if COMBAT_MODE == 0 then return true end
  local gear = COMBAT_ERAS[era]
  if not gear then return true end
  return any_of(gear.armor) and any_of(gear.weapons) and (COMBAT_MODE < 2 or any_of(gear.ranged))
end

-- boss_altar_keys (the seed's setting, read when autotracking connects): a boss's altar needs its key.
ALTAR_KEYS = false

function altarkey(key)
  return not ALTAR_KEYS or has(key)
end

-- Comfort (what the Rested effect shows): 1, plus 1 under a roof, plus the best piece of each comfort group
-- among those you can build. A piece needs its researches and the tier gates of the tier its materials are from.
local function has_all(list)
  for _, item in ipairs(list) do
    if not has(item) then return false end
  end
  return true
end

function comfort(level)
  level = tonumber(level)
  if not has_all(SHELTER) then return level <= 1 end
  local best, total = {}, 2
  for _, piece in ipairs(COMFORT_PIECES) do
    if piece.comfort > (best[piece.key] or 0) and has_all(piece.needs) then best[piece.key] = piece.comfort end
  end
  for _, c in pairs(best) do total = total + c end
  return total >= level
end
""" + "SHELTER = {" + ", ".join(lua_str(code(n)) for n in comfort_needs(world.SHELTER[0], world.SHELTER[2])) + "}\n"
    + "COMFORT_PIECES = {\n" + "".join(
        f"  {{ key = {lua_str(p[1] if p[3] == 'None' else p[3])}, comfort = {p[2]}, "
        f"needs = {{{', '.join(lua_str(code(n)) for n in comfort_needs(p[4], p[6]))}}} }},\n"
        for p in world.COMFORT_PIECES) + "}\n"
    + "COMBAT_ERAS = {\n" + "".join(
        f"  {code(era)} = {{ armor = {{{', '.join(lua_str(code(n)) for n in g['armor'])}}}, "
        f"weapons = {{{', '.join(lua_str(code(n)) for n in g['weapons'])}}}, "
        f"ranged = {{{', '.join(lua_str(code(n)) for n in g['ranged'])}}} }},\n"
        for era, g in world.COMBAT_ERAS.items()) + "}\n")
(out / "scripts/autotracking.lua").write_text("""-- Archipelago autotracking (PopTracker's built-in AP client).
ScriptHost:LoadScript("scripts/item_mapping.lua")
ScriptHost:LoadScript("scripts/location_mapping.lua")

CUR_INDEX = -1
-- progressive_items: each progressive item's researches in order (from slot data), and copies received.
PROGRESSIVE, PROGRESSIVE_COUNT = {}, {}

local function find(code)
  return Tracker:FindObjectForCode(code)
end

-- The pack's item code for a name (the same as the generator's code()).
local function code_of(name)
  return (name:lower():gsub("[^a-z0-9]+", "_"):gsub("^_+", ""):gsub("_+$", ""))
end

function onClear(slot_data)
  CUR_INDEX = -1
  PROGRESSIVE, PROGRESSIVE_COUNT = (slot_data and slot_data.progressive) or {}, {}
  ALTAR_KEYS = (slot_data and slot_data.boss_altar_keys) and true or false
  if slot_data and slot_data.options and slot_data.options.combat_logic ~= nil then
    COMBAT_MODE = slot_data.options.combat_logic
  end
  for _, code in pairs(ITEM_MAPPING) do
    local obj = find(code)
    if obj then obj.Active = false end
  end
  for _, code in pairs(TROPHY_BOSS) do
    local obj = find(code)
    if obj then obj.Active = false end
  end
  -- Checks this seed doesn't have (options, goal) are cleared; the rest are reset.
  local in_seed = {}
  for _, id in ipairs(Archipelago.MissingLocations or {}) do in_seed[id] = true end
  for _, id in ipairs(Archipelago.CheckedLocations or {}) do in_seed[id] = true end
  local know_seed = next(in_seed) ~= nil
  for id, code in pairs(LOCATION_MAPPING) do
    local obj = find(code)
    if obj then
      if know_seed and not in_seed[id] then obj.AvailableChestCount = 0 else obj.AvailableChestCount = obj.ChestCount end
    end
  end
end

function onItem(index, item_id, item_name, player_number)
  if index <= CUR_INDEX then return end
  CUR_INDEX = index
  local family = PROGRESSIVE[item_name]
  if family then
    PROGRESSIVE_COUNT[item_name] = (PROGRESSIVE_COUNT[item_name] or 0) + 1
    local research = family[PROGRESSIVE_COUNT[item_name]]
    local obj = research and find(code_of(research))
    if obj then obj.Active = true end
    return
  end
  local code = ITEM_MAPPING[item_id]
  if code then
    local obj = find(code)
    if obj then obj.Active = true end
  end
end

function onLocation(location_id, location_name)
  local code = LOCATION_MAPPING[location_id]
  if code then
    local obj = find(code)
    if obj and obj.AvailableChestCount > 0 then obj.AvailableChestCount = obj.AvailableChestCount - 1 end
  end
  local boss = TROPHY_BOSS[location_id]
  if boss then
    local obj = find(boss)
    if obj then obj.Active = true end
  end
end

Archipelago:AddClearHandler("valheim clear", onClear)
Archipelago:AddItemHandler("valheim item", onItem)
Archipelago:AddLocationHandler("valheim location", onLocation)
""")
(out / "init.lua").write_text("""Tracker:AddItems("items/items.json")
ScriptHost:LoadScript("scripts/logic.lua")
Tracker:AddMaps("maps/maps.json")
Tracker:AddLocations("locations/locations.json")
Tracker:AddLayouts("layouts/items.json")
Tracker:AddLayouts("layouts/tracker.json")
if PopVersion and PopVersion >= "0.18.0" then
  ScriptHost:LoadScript("scripts/autotracking.lua")
end
""")
json.dump({
    "name": "Valheim Archipelago",
    "game_name": "Valheim",
    "package_uid": "valheim_archipelago_justeyetee",
    "package_version": version,
    "author": "JustEyeTee",
    "min_poptracker_version": "0.25.0",
    "variants": {"standard": {"display_name": "Standard", "flags": ["ap"]}},
}, open(out / "manifest.json", "w"), indent=1)
print(f"{len(items_json)} items, {len(locations_json)} pins, {len(location_codes)} checks")
