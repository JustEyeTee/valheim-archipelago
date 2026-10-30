#!/usr/bin/env bash
# Regenerates docs/Valheim.yaml, the options template, with Archipelago's own template generator
# (every option with its description, grouped, defaults weighted 50). Run before a release.
#   tools/gen_template.sh
set -euo pipefail
cd "$(dirname "$0")/.."
ap=${AP_DIR:-$(cd .. && pwd)/archipelago-0.6.8}
work=$(mktemp -d); trap 'rm -rf "$work"' EXIT
./build.sh >/dev/null
cp dist/stage/valheimapworld.apworld "$ap/custom_worlds/"
(cd "$ap" && SKIP_REQUIREMENTS_UPDATE=1 .venv/bin/python -c \
  "import sys, Options, worlds; Options.generate_yaml_templates(sys.argv[1], False)" "$work" < /dev/null > /dev/null 2>&1)
# The template asks for the Archipelago version that generated it; any version from the minimum works.
minimum=$(python3 -I -c 'import json; print(json.load(open("valheimapworld/archipelago.json"))["minimum_ap_version"])')
sed -E "s/^(  version: )[0-9.]+( # Version of Archipelago)/\1$minimum\2/" "$work/Valheim.yaml" > docs/Valheim.yaml
echo "docs/Valheim.yaml regenerated"
