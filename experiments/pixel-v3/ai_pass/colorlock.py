"""Lock the AI cat's colours and patch layout to the render, and composite it over the untouched render.
python colorlock.py <ai_dir> <render_dir> <matte_dir> <out_dir> first=<film frame of AI frame 1> [size=1280x720]
       [chroma=1.0] [pull=0.6] [sigma=12] [grow=3] [feather=4] [ring=1]

Inside the cat matte:
  chroma (Cb, Cr) comes from the render (only black / orange / white exist there, so no green or pink tint can survive);
  luma keeps the AI's fur detail but its low frequencies are pulled toward the render's (pull), which restores the patch layout.
Outside the matte the render is used as is. 'ring' shifts the AI frame's colour so the area just around the cat matches the
render before blending, which removes the bright halo. The render is stable frame to frame, so the colours cannot drift."""
import sys, os, glob
import numpy as np
from PIL import Image, ImageFilter
ai, rd, md, out = sys.argv[1:5]; opt = dict(a.split('=') for a in sys.argv[5:])
first = int(opt['first']); W, H = [int(v) for v in opt.get('size', '1280x720').split('x')]
chroma, pull, sigma = float(opt.get('chroma', 1.0)), float(opt.get('pull', 0.6)), float(opt.get('sigma', 12))
grow, feather, ring = int(opt.get('grow', 3)), float(opt.get('feather', 4)), int(opt.get('ring', 1))
os.makedirs(out, exist_ok=True)
def arr(im): return np.asarray(im, np.float32)
def blur(a, s): return arr(Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(s)))
for i, f in enumerate(sorted(glob.glob(ai + '/*.png'))):
    n = first + i
    a_rgb = Image.open(f).convert('RGB').resize((W, H), Image.LANCZOS)
    r_rgb = Image.open(f'{rd}/{n:04d}.png').convert('RGB').resize((W, H), Image.LANCZOS)
    m_img = Image.open(f'{md}/{n:04d}.png').convert('L').resize((W, H), Image.BILINEAR)
    if ring:      # match the AI frame to the render in a ring just outside the cat, per channel
        q = m_img.resize((W // 4, H // 4), Image.BILINEAR)                             # quarter size: large max filters are slow
        outer = arr(q.filter(ImageFilter.MaxFilter(15)).resize((W, H), Image.BILINEAR)) / 255
        inner = arr(q.filter(ImageFilter.MaxFilter(5)).resize((W, H), Image.BILINEAR)) / 255
        rg = (outer > 0.5) & (inner < 0.5)
        if rg.sum() > 500:
            A = arr(a_rgb); R = arr(r_rgb); A += (R[rg].mean(0) - A[rg].mean(0)); a_rgb = Image.fromarray(np.clip(A, 0, 255).astype(np.uint8))
    A = arr(a_rgb.convert('YCbCr')); R = arr(r_rgb.convert('YCbCr'))
    core = arr(m_img.filter(ImageFilter.GaussianBlur(2))) / 255                         # where the render's cat actually is
    Y = A[..., 0] + pull * core * (blur(R[..., 0], sigma) - blur(A[..., 0], sigma))
    # chroma from the render, extended a little past the render's silhouette (normalised blur) so the fluffy fringe that
    # sticks out beyond the smooth mesh takes the neighbouring fur colour instead of keeping a pink / green cast
    wsum = blur(core * 255, 9) / 255 + 1e-4
    Cr = np.stack([blur(R[..., 1] * core, 9) / wsum, blur(R[..., 2] * core, 9) / wsum], -1)
    Cr = np.where(core[..., None] > 0.5, np.stack([blur(R[..., 1], 3), blur(R[..., 2], 3)], -1), Cr)
    wfr = arr(m_img.filter(ImageFilter.MaxFilter(2 * (grow + 6) + 1)).filter(ImageFilter.GaussianBlur(3))) / 255
    C = A[..., 1:] + chroma * wfr[..., None] * (Cr - A[..., 1:])
    locked = Image.fromarray(np.clip(np.dstack([Y, C]), 0, 255).astype(np.uint8), 'YCbCr').convert('RGB')
    m = m_img.filter(ImageFilter.MaxFilter(grow * 2 + 1)) if grow > 0 else m_img
    if feather > 0: m = m.filter(ImageFilter.GaussianBlur(feather))
    Image.composite(locked, r_rgb, m).save(f'{out}/{n:04d}.png')
print('COLORLOCKED', i + 1, 'frames ->', out)
