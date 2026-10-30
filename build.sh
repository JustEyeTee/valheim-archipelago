#!/usr/bin/env bash
# Builds the mod from source and packages a test release into dist/:
#   dist/ValheimArchipelagoRandomizer-<commit>.zip
#     BepInEx/plugins/...      -> extract into the Valheim game folder. The mod reads
#                                 research.tsv/trophies.tsv from the plugins folder itself,
#                                 so these files must not go in a subfolder.
#     valheimapworld.apworld   -> install with the Archipelago Launcher
# Newtonsoft.Json.dll is upstream's file as shipped; the game loads its own copy first.
#
# FAST_TEST=1 ./build.sh makes a playtest build (zip name ends in -fasttest): every research
# costs 1 of each ingredient and the Research Bench costs 1 Wood + 1 Stone. The APWorld is
# unaffected, so the same generated room works with either build.
set -euo pipefail
cd "$(dirname "$0")"
export DOTNET_NOLOGO=1 DOTNET_CLI_TELEMETRY_OPTOUT=1
fast=${FAST_TEST:-0}

# --no-incremental: FastTest only changes a define, which incremental builds don't notice.
dotnet build src/ValheimRandomizer.csproj -c Release -nologo -v quiet --no-incremental \
  -p:FastTest=$([ "$fast" = 1 ] && echo true || echo false)
out=src/bin/Release/netstandard2.1
tag=$(git rev-parse --short HEAD)$(git diff --quiet HEAD -- mod src valheimapworld || echo -dirty)
[ "$fast" = 1 ] && tag+=-fasttest
stage=dist/stage
rm -rf "$stage" && mkdir -p "$stage/BepInEx/plugins"
cp "$out/ValheimRandomizer.dll" "$out/Archipelago.MultiClient.Net.dll" \
   mod/Newtonsoft.Json.dll mod/research.tsv mod/trophies.tsv \
   "$stage/BepInEx/plugins/"
if [ "$fast" = 1 ]; then
  # researchRecipeRequirements (6th column) is Item:Amount|Item:Amount; set every amount to 1
  python3 -I - "$stage/BepInEx/plugins/research.tsv" <<'EOF'
import sys
p = sys.argv[1]
lines = open(p, newline="").read().split("\n")
for i, line in enumerate(lines):
    if not line or line.startswith("#"):
        continue
    cols = line.split("\t")
    if len(cols) > 5 and cols[5].strip():
        cols[5] = "|".join(t.split(":")[0] + ":1" if t else t for t in cols[5].split("|"))
        lines[i] = "\t".join(cols)
open(p, "w", newline="").write("\n".join(lines))
EOF
fi
(cd valheimapworld && rm -f ../dist/stage/valheimapworld.apworld &&
  mkdir -p ../dist/stage/apw/valheimapworld && cp ./*.py archipelago.json ../dist/stage/apw/valheimapworld/ &&
  cd ../dist/stage/apw && python3 -I -m zipfile -c ../valheimapworld.apworld valheimapworld) && rm -rf "$stage/apw"
zip="dist/ValheimArchipelagoRandomizer-$tag.zip"
rm -f "$zip" && (cd "$stage" && python3 -I -m zipfile -c "../$(basename "$zip")" BepInEx valheimapworld.apworld)
echo "$zip"
