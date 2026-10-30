#!/usr/bin/env bash
# Hosts a test room for playing the randomizer with any item on demand: generates a seed from a test YAML and
# runs Archipelago's server on it with item cheats on (the default for a room you host), so in the game
# `/ap give <item>` gets any item the normal way, through the server. See docs/TESTING.md.
#   tools/test_room.sh                                   tools/testing/solo-eikthyr.yaml on port 38281
#   tools/test_room.sh tools/testing/solo-elder.yaml     another YAML (or several: a folder of them)
#   PORT=38282 PASSWORD=secret tools/test_room.sh        another port; a password to join
#   GENERATE_ONLY=1 tools/test_room.sh                   only generate (prints the .zip to host elsewhere)
# The server runs in the foreground: type its commands here (/send TestViking Burning Trap, /send_location ...,
# /exit to stop). Rooms are kept in ~/valheim-test-rooms/ (the .zip can also be hosted from the Archipelago Launcher).
set -euo pipefail
cd "$(dirname "$0")/.."
ap=${AP_DIR:-$(cd .. && pwd)/archipelago-0.6.8}
port=${PORT:-38281}
yaml=${1:-tools/testing/solo-eikthyr.yaml}
room=~/valheim-test-rooms/$(date +%Y%m%d-%H%M%S)
mkdir -p "$room/players" "$room/out"

APWORLD_ONLY=1 ./build.sh >/dev/null
mkdir -p "$ap/custom_worlds" && cp dist/stage/valheimapworld.apworld "$ap/custom_worlds/"
if [ -d "$yaml" ]; then cp "$yaml"/*.yaml "$room/players/"; else cp "$yaml" "$room/players/"; fi
echo "Generating from $yaml..."
(cd "$ap" && SKIP_REQUIREMENTS_UPDATE=1 .venv/bin/python Generate.py --player_files_path "$room/players" \
   --outputpath "$room/out" < /dev/null > "$room/generate.log" 2>&1) || { tail -20 "$room/generate.log"; exit 1; }
zip=$(ls "$room"/out/AP_*.zip)
address=$(hostname -I 2>/dev/null | awk '{print $1}')
[ -n "$address" ] || address="this machine's address"
slots=$(grep -h '^name:' "$room"/players/*.yaml | sed 's/name: *//' | tr '\n' ' ')
password_line=""
[ -n "${PASSWORD:-}" ] && password_line="  Password: $PASSWORD"
cat <<INFO

Test room ready: $zip
  Connect from Valheim's Archipelago window: host $address, port $port, slot(s): $slots
$password_line
  In the game: /ap give <item>, /ap items <search> (see docs/TESTING.md). Here: /send <slot> <item>, /exit.

INFO
# GENERATE_ONLY=1: stop here (another user or machine hosts the .zip).
[ "${GENERATE_ONLY:-0}" = 1 ] && { echo "$zip"; exit 0; }
cd "$ap" && exec env SKIP_REQUIREMENTS_UPDATE=1 .venv/bin/python MultiServer.py --host 0.0.0.0 --port "$port" \
  ${PASSWORD:+--password "$PASSWORD"} "$zip"
