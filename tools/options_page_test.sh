#!/usr/bin/env bash
# Checks the Options Builder's live counts against real generation: drives docs/options/index.html in a
# headless browser through several option sets, then builds each set's world with this repo's APWorld and
# compares the checks and items by kind. Run after changing options, checks or the item pool (and after
# tools/gen_options_page.py).
#   tools/options_page_test.sh       PLAYWRIGHT_PY=<python with playwright> AP_DIR=... tools/options_page_test.sh
set -euo pipefail
cd "$(dirname "$0")/.."
ap=${AP_DIR:-$(cd .. && pwd)/archipelago-0.6.8}
py=${PLAYWRIGHT_PY:-python3}
work=$(mktemp -d); trap 'rm -rf "$work"' EXIT
"$py" tools/options_page_test/page.py "file://$PWD/docs/options/index.html" "$work"
(cd "$ap" && SKIP_REQUIREMENTS_UPDATE=1 .venv/bin/python "$OLDPWD/tools/options_page_test/check.py" "$work/cases.json" < /dev/null 2>/dev/null) \
  | grep -E "MATCH|DIFFERENT|page |real |all match|differ"
