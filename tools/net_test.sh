#!/usr/bin/env bash
# Network test against a live MultiServer: generates a 2-player Valheim seed, hosts it on
# 127.0.0.1 and runs tools/nettest (the mod's client library and calls): login and slot data,
# goal conditions, Trap Link, Death Link, Energy Link deposit and withdraw, hints and the item feed.
#   tools/net_test.sh
set -euo pipefail
cd "$(dirname "$0")/.."
ap=${AP_DIR:-$(cd .. && pwd)/archipelago-0.6.8}
port=${PORT:-38997}
work=$(mktemp -d); server=""
# The server saves the game as it shuts down: wait for it before removing its folder.
trap '[ -n "$server" ] && { kill "$server"; wait "$server"; } 2>/dev/null; rm -rf "$work"' EXIT

APWORLD_ONLY=1 ./build.sh >/dev/null
mkdir -p "$ap/custom_worlds" && cp dist/stage/valheimapworld.apworld "$ap/custom_worlds/"
mkdir -p "$work/players" "$work/out"
for p in A B; do
  printf 'name: Viking%s\ngame: Valheim\nValheim:\n  goal: eikthyr\n  death_link: true\n  trap_link: true\n' "$p" > "$work/players/$p.yaml"
done
# A has goal conditions (B keeps the default, Goal Boss).
printf '  goal_conditions: ["Goal Boss", "Relic Hunt", "Trophy Hunt", "Skill Master"]\n' >> "$work/players/A.yaml"
(cd "$ap" && SKIP_REQUIREMENTS_UPDATE=1 .venv/bin/python Generate.py --player_files_path "$work/players" \
   --outputpath "$work/out" --seed 21 < /dev/null > "$work/gen.log" 2>&1)
(cd "$ap" && SKIP_REQUIREMENTS_UPDATE=1 exec .venv/bin/python MultiServer.py --host 127.0.0.1 --port "$port" \
   "$work"/out/AP_*.zip < /dev/null > "$work/server.log" 2>&1) &
server=$!
for _ in $(seq 1 90); do ss -ltn | grep -q ":$port " && break; sleep 1; done
dotnet build tools/nettest -c Release -v q -o "$work/client" > /dev/null
timeout 60 dotnet "$work/client/client.dll" "$port" | grep -v "TagsChangedLogMessage"
if grep -q "TypeError\|InvalidPacket" "$work/server.log"; then
  echo "SERVER ERRORS:"; grep -B2 "TypeError\|InvalidPacket" "$work/server.log"; exit 1
fi
echo "no server errors"
