-- Archipelago autotracking (PopTracker's built-in AP client).
ScriptHost:LoadScript("scripts/item_mapping.lua")
ScriptHost:LoadScript("scripts/location_mapping.lua")

CUR_INDEX = -1

local function find(code)
  return Tracker:FindObjectForCode(code)
end

function onClear(slot_data)
  CUR_INDEX = -1
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
