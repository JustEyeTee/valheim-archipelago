"""Draws mod/ap_icons/*.png from Archipelago's logo (data/icon.png, MIT, see THIRD_PARTY_NOTICES.md): the icon the
Research Bench and traders show for a check whose reward isn't one of your own Valheim items. Colour for
progression, dark blue for useful, grey for filler and traps, as other Archipelago games show them.
    ~/projects/archipelago-0.6.8/.venv/bin/python tools/make_ap_icons.py ~/projects/archipelago-0.6.8
"""
import pathlib
import sys

from PIL import Image, ImageOps

root = pathlib.Path(__file__).resolve().parent.parent
logo = Image.open(pathlib.Path(sys.argv[1]) / "data" / "icon.png").convert("RGBA").resize((64, 64), Image.LANCZOS)
alpha = logo.getchannel("A")
grey = ImageOps.grayscale(logo)
out = root / "mod" / "ap_icons"
out.mkdir(exist_ok=True)
logo.save(out / "progression.png")
for name, dark, light in (("useful", (16, 32, 88), (110, 150, 235)), ("filler", (60, 60, 64), (200, 200, 205))):
    tinted = ImageOps.colorize(ImageOps.autocontrast(grey), dark, light).convert("RGBA")
    tinted.putalpha(alpha)
    tinted.save(out / f"{name}.png")
print("wrote", sorted(p.name for p in out.iterdir()))
