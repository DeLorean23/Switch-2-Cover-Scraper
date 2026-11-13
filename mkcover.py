# Creates the Ports cover: DeLorean cover with the project name in the bottom bar.
#   python3 mkcover.py <DeLorean cover 600x600> assets/cover.jpg "Switch 2 Cover Scraper" [font size]
import sys
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont
src, out, text = sys.argv[1], sys.argv[2], sys.argv[3]
im = Image.open(src).convert("RGB")
s = im.size[0] / 800.0
P = lambda pts: [(round(x * s), round(y * s)) for x, y in pts]
d = ImageDraw.Draw(im)
# clear the inner part of the bottom bar (dark interior)
d.polygon(P([(86, 672), (714, 672), (729, 700), (714, 729), (86, 729), (71, 700)]), fill=(6, 4, 14))
font = ImageFont.truetype("/usr/share/fonts/truetype/google-fonts/Poppins-BoldItalic.ttf",
                          int(int(sys.argv[4]) if len(sys.argv) > 4 else 50 * s))
bb = d.textbbox((0, 0), text, font=font)
w, h = bb[2] - bb[0], bb[3] - bb[1]
x, y = round(400 * s) - w // 2 - bb[0], round(700 * s) - h // 2 - bb[1]
glow = Image.new("RGB", im.size, (0, 0, 0))
ImageDraw.Draw(glow).text((x, y), text, font=font, fill=(255, 40, 200))
glow = glow.filter(ImageFilter.GaussianBlur(5 * s))
im = ImageChops.add(im, glow)
mask = Image.new("L", im.size, 0)
ImageDraw.Draw(mask).text((x, y), text, font=font, fill=255)
grad = Image.new("RGB", im.size)
gd = ImageDraw.Draw(grad)
for yy in range(im.size[1]):
    t = min(max((yy - (y + bb[1])) / max(h, 1), 0), 1)
    gd.line([(0, yy), (im.size[0], yy)], fill=(255, int(255 - 90 * t), int(255 - 40 * t)))
im.paste(grad, (0, 0), mask)
edge = ImageChops.subtract(mask.filter(ImageFilter.MaxFilter(3)), mask)
im.paste((200, 30, 170), (0, 0), edge)
im.save(out, quality=92)
