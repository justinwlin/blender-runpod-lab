"""Composite the AI-restyled cat over the untouched Blender render using the cat matte.
python composite.py <ai_dir> <render_dir> <matte_dir> <out_dir> first=<render frame of AI frame 1> [grow=7] [feather=5] [size=1280x720]
AI frames are ComfyUI SaveImage files (sorted by name); render and matte frames are %04d.png by film frame number.
The matte is grown (fur sticks out past the smooth silhouette) and feathered."""
import sys, os, glob
from PIL import Image, ImageFilter
ai, rd, md, out = sys.argv[1:5]; opt = dict(a.split('=') for a in sys.argv[5:])
first = int(opt['first']); grow = int(opt.get('grow', 7)); feather = float(opt.get('feather', 5)); W, H = [int(v) for v in opt.get('size', '1280x720').split('x')]
os.makedirs(out, exist_ok=True); files = sorted(glob.glob(ai + '/*.png'))
for i, f in enumerate(files):
    n = first + i
    a = Image.open(f).convert('RGB').resize((W, H), Image.LANCZOS)
    r = Image.open(f'{rd}/{n:04d}.png').convert('RGB').resize((W, H), Image.LANCZOS)
    m = Image.open(f'{md}/{n:04d}.png').convert('L').resize((W, H), Image.BILINEAR)
    if grow > 0: m = m.filter(ImageFilter.MaxFilter(grow * 2 + 1))
    if feather > 0: m = m.filter(ImageFilter.GaussianBlur(feather))
    Image.composite(a, r, m).save(f'{out}/{n:04d}.png')
print('COMPOSITED', len(files), 'frames ->', out)
