"""Writes Valheim's English strings ({token without $: text}) from the game's localization CSVs.

    python tools/extract_localization.py <valheim_server_Data dir> <out.json>
"""
import csv
import io
import json
import sys

import UnityPy

env = UnityPy.load(f"{sys.argv[1]}/resources.assets")
english = {}
for obj in env.objects:
    if obj.type.name != "TextAsset":
        continue
    asset = obj.read()
    if not asset.m_Name.startswith("localization"):
        continue
    text = asset.m_Script if isinstance(asset.m_Script, str) else asset.m_Script.decode("utf-8", "replace")
    rows = list(csv.reader(io.StringIO(text.lstrip("﻿"))))
    if not rows or "English" not in rows[0]:
        continue
    col = rows[0].index("English")
    for row in rows[1:]:
        if len(row) > col and row[0] and row[col]:
            english.setdefault(row[0], row[col])
json.dump(english, open(sys.argv[2], "w"), indent=0, ensure_ascii=False)
print(f"{len(english)} English strings")
