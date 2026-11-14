"""Title card overlay (transparent 1920x1080 PNG). python scripts/v3/make_title.py <out.png> <serif.ttf> <sans.ttf>"""
import sys
from PIL import Image, ImageDraw, ImageFont, ImageFilter
out, serif, sans = sys.argv[1:4]; W, H = 1920, 1080
im = Image.new('RGBA', (W, H), (0, 0, 0, 0))
f1 = ImageFont.truetype(serif, 190); f2 = ImageFont.truetype(sans, 30)
try: f1.set_variation_by_axes([144, 500, 100, 0][:len(f1.get_variation_axes())])
except Exception: pass
sh = Image.new('RGBA', (W, H), (0, 0, 0, 0)); ds = ImageDraw.Draw(sh)
x, y = 150, 560
ds.text((x + 4, y + 6), 'Pixel', font=f1, fill=(20, 10, 5, 150)); ds.text((x + 6, y + 232), 'G O L D E N   H O U R', font=f2, fill=(20, 10, 5, 150))
im.alpha_composite(sh.filter(ImageFilter.GaussianBlur(10)))
d = ImageDraw.Draw(im)
d.text((x, y), 'Pixel', font=f1, fill=(255, 244, 228, 255)); d.text((x + 6, y + 230), 'G O L D E N   H O U R', font=f2, fill=(255, 226, 190, 235))
im.save(out)
