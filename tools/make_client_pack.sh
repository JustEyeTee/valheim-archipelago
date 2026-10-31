#!/bin/bash
# Builds dist/ValheimArchipelago-ClientPack-<version>.zip: BepInExPack Valheim, Jotunn and this mod in one zip,
# extracted straight into the Valheim folder (for players who don't use a mod manager). Run ./build.sh first.
#     tools/make_client_pack.sh [version]      (default: the APWorld's world_version)
set -euo pipefail
cd "$(dirname "$0")/.."

BEPINEX=5.4.2360
JOTUNN=2.30.2
version=${1:-$(python3 -c "import json; print(json.load(open('valheimapworld/archipelago.json'))['world_version'])")}
mod=$(ls -t dist/ValheimArchipelagoRandomizer-*.zip | head -1)

work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
curl -fsSL -o "$work/bep.zip" "https://thunderstore.io/package/download/denikson/BepInExPack_Valheim/$BEPINEX/"
curl -fsSL -o "$work/jot.zip" "https://thunderstore.io/package/download/ValheimModding/Jotunn/$JOTUNN/"
mkdir -p "$work/bep" "$work/jot" "$work/mod" "$work/pack/BepInEx/plugins/Jotunn" "$work/pack/BepInEx/plugins/ValheimArchipelago"
unzip -q "$work/bep.zip" -d "$work/bep"
unzip -q "$work/jot.zip" -d "$work/jot" 2>/dev/null || true  # Jotunn's zip uses backslashes in its paths
unzip -q "$mod" -d "$work/mod"

cp -r "$work/bep/BepInExPack_Valheim/." "$work/pack/"
cp "$work/jot/plugins\\Jotunn.dll" "$work/pack/BepInEx/plugins/Jotunn/" 2>/dev/null || cp "$work/jot/plugins/Jotunn.dll" "$work/pack/BepInEx/plugins/Jotunn/"
cp "$work"/mod/BepInEx/plugins/* "$work/pack/BepInEx/plugins/ValheimArchipelago/"
cp LICENSE "$work/pack/BepInEx/plugins/ValheimArchipelago/"
cp THIRD_PARTY_NOTICES.md "$work/pack/BepInEx/plugins/ValheimArchipelago/"

cat > "$work/pack/ValheimArchipelago-INSTALL.txt" <<EOF
Valheim Archipelago $version: client pack

1. In Steam, right-click Valheim > Manage > Browse local files.
2. Extract everything in this zip into that folder (next to valheim.exe), replacing files if asked.
3. Start Valheim normally. The Archipelago window shows on the main menu and the pause menu.

To remove it, delete the BepInEx folder, winhttp.dll and doorstop_config.ini from the Valheim folder.

Contents:
- BepInExPack Valheim $BEPINEX (BepInEx, LGPL-2.1: https://github.com/BepInEx/BepInEx), the mod loader.
- Jotunn $JOTUNN (MIT: https://github.com/Valheim-Modding/Jotunn), a modding library.
- Valheim Archipelago (CC0: https://github.com/JustEyeTee/valheim-archipelago), in BepInEx/plugins/ValheimArchipelago.
  Most of its code, tools and documentation were written by Claude, an AI model made by Anthropic, at
  JustEyeTee's direction.
EOF

out="dist/ValheimArchipelago-ClientPack-$version.zip"
rm -f "$out"
(cd "$work/pack" && zip -qr - .) > "$out"
echo "$out"
