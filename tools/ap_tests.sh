#!/usr/bin/env bash
# Runs Archipelago's own test suites (general, options, multiworld, programs, webhost) for this world:
# the checks every world is expected to pass (ids, names and groups, fill, manifest, docs pages...).
# Needs pytest, pytest-subtests and WebHostLib/requirements.txt in the Archipelago venv.
#   tools/ap_tests.sh            AP_DIR=~/projects/archipelago-0.6.4 tools/ap_tests.sh
set -euo pipefail
cd "$(dirname "$0")/.."
ap=${AP_DIR:-$(cd .. && pwd)/archipelago-0.6.8}
installed="$ap/custom_worlds/valheimapworld.apworld"
# The tests run the world from a source folder; an installed .apworld would register twice.
trap 'rm -rf "$ap/worlds/valheimapworld"; [ -f "$installed.bak" ] && mv "$installed.bak" "$installed"' EXIT
[ -f "$installed" ] && mv "$installed" "$installed.bak"
rm -rf "$ap/worlds/valheimapworld" && cp -r valheimapworld "$ap/worlds/" && rm -rf "$ap/worlds/valheimapworld/__pycache__"
cd "$ap" && SKIP_REQUIREMENTS_UPDATE=1 AP_TEST_WORLDS=valheimapworld .venv/bin/python -m pytest \
  test/general test/options test/multiworld test/programs test/webhost -q -p no:cacheprovider --continue-on-collection-errors
