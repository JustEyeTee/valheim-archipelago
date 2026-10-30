"""Draws thunderstore/icon.png (256x256, Thunderstore's required size). No game art is used.
    python tools/make_icon.py        (needs Pillow, e.g. the Archipelago venv's python)"""
import math
import pathlib

from PIL import Image, ImageDraw, ImageFont

out = pathlib.Path(__file__).resolve().parent.parent / "thunderstore" / "icon.png"
size = 256
img = Image.new("RGBA", (size, size), (24, 28, 38, 255))
draw = ImageDraw.Draw(img)
# A ring of six coloured segments around a dark centre, like a multiworld of games.
colours = [(201, 72, 64), (227, 166, 54), (106, 178, 82), (64, 160, 201), (122, 94, 199), (199, 84, 160)]
for i, colour in enumerate(colours):
    draw.pieslice((18, 18, 238, 238), i * 60 - 90 + 3, (i + 1) * 60 - 90 - 3, fill=colour)
draw.ellipse((52, 52, 204, 204), fill=(24, 28, 38, 255))
# A bearded axe: a haft, a blade with a curved edge, and the beard hooking down.
draw.line((140, 70, 140, 200), fill=(196, 160, 110), width=11)
edge = [(186 + 14 * math.cos(a), 104 + 40 * math.sin(a)) for a in [math.radians(d) for d in range(-90, 91, 10)]]
blade = [(146, 86), (172, 70)] + edge + [(170, 150), (158, 128), (146, 118)]
draw.polygon(blade, fill=(225, 230, 238))
draw.line((146, 86, 146, 118), fill=(150, 156, 166), width=3)
font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 30)
text = "AP"
box = draw.textbbox((0, 0), text, font=font)
draw.text((100 - (box[2] - box[0]) / 2, 118), text, font=font, fill="white")
img.save(out)
print(out)
