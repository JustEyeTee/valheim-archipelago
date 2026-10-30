#!/usr/bin/env bash
# Generates test seeds with a local Archipelago checkout and checks each one is beatable.
#   tools/test_generate.sh [goal] [seeds]      e.g. tools/test_generate.sh fader 10
#   EXTRA_OPTIONS='include_deep_north: true' tools/test_generate.sh fader 5   (extra lines under Valheim:)
# AP_DIR defaults to ../archipelago-0.6.4 (a venv in .venv, see notes in the project memory).
set -euo pipefail
cd "$(dirname "$0")/.."
goal=${1:-fader}; seeds=${2:-5}
ap=${AP_DIR:-$(cd .. && pwd)/archipelago-0.6.4}
work=$(mktemp -d); trap 'rm -rf "$work"' EXIT

./build.sh >/dev/null
mkdir -p "$ap/custom_worlds" "$work/players" "$work/out"
cp dist/stage/valheimapworld.apworld "$ap/custom_worlds/"
{ printf 'name: Tester\ngame: Valheim\nValheim:\n  goal: %s\n' "$goal"
  [ -n "${EXTRA_OPTIONS:-}" ] && printf '  %s\n' "$EXTRA_OPTIONS"; } > "$work/players/test.yaml"

fails=0
for seed in $(seq 1 "$seeds"); do
  rm -rf "$work/out"/*
  if ! (cd "$ap" && SKIP_REQUIREMENTS_UPDATE=1 timeout 300 .venv/bin/python Generate.py \
          --player_files_path "$work/players" --outputpath "$work/out" --seed "$seed" --spoiler 2 \
          < /dev/null > "$work/log" 2>&1); then
    echo "seed $seed: GENERATION FAILED"; tail -5 "$work/log"; fails=$((fails+1)); continue
  fi
  spoiler=$(cd "$work/out" && python3 -I -c 'import zipfile,glob; z=zipfile.ZipFile(glob.glob("*.zip")[0]); print(z.read([n for n in z.namelist() if n.endswith("_Spoiler.txt")][0]).decode())')
  spheres=$(printf '%s\n' "$spoiler" | grep -c -E '^[0-9]+: \{')
  if printf '%s\n' "$spoiler" | grep -q 'Defeat .*: Victory'; then
    echo "seed $seed: ok ($spheres spheres)"
  else
    echo "seed $seed: NO VICTORY IN PLAYTHROUGH"; fails=$((fails+1))
  fi
done
[ "$fails" -eq 0 ] && echo "all $seeds seeds beatable (goal: $goal)" || { echo "$fails of $seeds failed"; exit 1; }
