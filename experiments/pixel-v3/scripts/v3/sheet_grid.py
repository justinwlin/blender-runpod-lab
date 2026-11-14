"""python sheet_grid.py out.jpg cols bg file1 file2 ...   (bg: white | none)"""
import sys
from PIL import Image
out, cols, bg = sys.argv[1], int(sys.argv[2]), sys.argv[3]; fs = sys.argv[4:]
ims = [Image.open(f).convert('RGBA') for f in fs]; w, h = ims[0].size; rows = (len(ims) + cols - 1) // cols
S = Image.new('RGBA', (w * cols, h * rows), (255, 255, 255, 255))
for i, im in enumerate(ims): S.alpha_composite(im.resize((w, h)), ((i % cols) * w, (i // cols) * h))
S.convert('RGB').save(out, quality=90)
