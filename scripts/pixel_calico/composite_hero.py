import sys, numpy as np
from PIL import Image
src, dst = sys.argv[1:3]
im = Image.open(src).convert('RGBA'); w, h = im.size
top, bot = np.array([222, 233, 245.]), np.array([246, 249, 253.])
g = top[None, :] + (bot - top)[None, :] * np.linspace(0, 1, h)[:, None]
bg = Image.fromarray(np.repeat(g[:, None, :], w, 1).astype(np.uint8)).convert('RGBA')
bg.alpha_composite(im); bg.convert('RGB').save(dst)
