import sys, glob
from PIL import Image
d, out = sys.argv[1:3]; fs = sorted(glob.glob(d + '/*.png')); ims = [Image.open(f).convert('RGB') for f in fs]
w, h = ims[0].size; cols = 4; rows = (len(ims) + cols - 1) // cols; S = Image.new('RGB', (w * cols, h * rows))
for i, im in enumerate(ims): S.paste(im, ((i % cols) * w, (i // cols) * h))
S.save(out)
