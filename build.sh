#!/usr/bin/env bash
# Builds the mod from source and packages a test release into dist/:
#   dist/ValheimArchipelagoRandomizer-<commit>.zip
#     ValheimArchipelagoRandomizer/   -> copy into BepInEx/plugins/
#     valheimapworld.apworld          -> install with the Archipelago Launcher
# Newtonsoft.Json.dll is upstream's file as shipped; the game loads its own copy first.
set -euo pipefail
cd "$(dirname "$0")"
export DOTNET_NOLOGO=1 DOTNET_CLI_TELEMETRY_OPTOUT=1

dotnet build src/ValheimRandomizer.csproj -c Release -nologo -v quiet
out=src/bin/Release/netstandard2.1
tag=$(git rev-parse --short HEAD)$(git diff --quiet HEAD -- mod src valheimapworld || echo -dirty)
stage=dist/stage
rm -rf "$stage" && mkdir -p "$stage/ValheimArchipelagoRandomizer"
cp "$out/ValheimRandomizer.dll" "$out/Archipelago.MultiClient.Net.dll" \
   mod/Newtonsoft.Json.dll mod/research.tsv mod/trophies.tsv \
   "$stage/ValheimArchipelagoRandomizer/"
(cd valheimapworld && rm -f ../dist/stage/valheimapworld.apworld &&
  mkdir -p ../dist/stage/apw/valheimapworld && cp ./*.py ../dist/stage/apw/valheimapworld/ &&
  cd ../dist/stage/apw && python3 -I -m zipfile -c ../valheimapworld.apworld valheimapworld) && rm -rf "$stage/apw"
zip="dist/ValheimArchipelagoRandomizer-$tag.zip"
rm -f "$zip" && (cd "$stage" && python3 -I -m zipfile -c "../$(basename "$zip")" ValheimArchipelagoRandomizer valheimapworld.apworld)
echo "$zip"
