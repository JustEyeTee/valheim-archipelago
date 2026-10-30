"""Draws docs/social-preview.png (1280x640), the card GitHub and Discord show for links to the repository: the
mod's icon and the project's name. Upload it in the repository's Settings > General > Social preview.
    python tools/make_social.py      (needs Pillow, e.g. the Archipelago venv's python)"""
import json
import pathlib

from PIL import Image, ImageDraw, ImageFont

root = pathlib.Path(__file__).resolve().parent.parent
version = json.load(open(root / "valheimapworld" / "archipelago.json"))["world_version"]
W, H = 1280, 640
BOLD, REGULAR = "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

img = Image.new("RGB", (W, H), (17, 23, 21))  # the pages' dark "fjord" background
draw = ImageDraw.Draw(img)
# A warm band along the bottom, the pages' mead amber.
for y in range(H - 140, H):
    t = (y - (H - 140)) / 140
    draw.line((0, y, W, y), fill=(int(17 + (58 - 17) * t), int(23 + (46 - 23) * t), int(21 + (24 - 21) * t)))

icon = Image.open(root / "thunderstore" / "icon.png").convert("RGBA").resize((300, 300), Image.LANCZOS)
corners = Image.new("L", icon.size, 0)  # a rounded tile, like an app icon
ImageDraw.Draw(corners).rounded_rectangle((0, 0, 299, 299), radius=48, fill=255)
img.paste(icon, (90, 150), corners)

x = 450
draw.text((x, 170), "Valheim", font=ImageFont.truetype(BOLD, 96), fill=(229, 236, 232))
draw.text((x, 275), "Archipelago", font=ImageFont.truetype(BOLD, 96), fill=(227, 165, 64))
draw.text((x, 400), "A randomizer mod and APWorld for Archipelago,", font=ImageFont.truetype(REGULAR, 30), fill=(152, 168, 161))
draw.text((x, 440), "the multi-game randomizer", font=ImageFont.truetype(REGULAR, 30), fill=(152, 168, 161))
draw.text((90, H - 70), f"Valheim 1.0.21 (Deep North)  ·  APWorld {version}  ·  github.com/JustEyeTee/valheim-archipelago",
          font=ImageFont.truetype(REGULAR, 24), fill=(214, 224, 219))

out = root / "docs" / "social-preview.png"
img.save(out, optimize=True)
print(f"wrote {out} ({W}x{H})")
