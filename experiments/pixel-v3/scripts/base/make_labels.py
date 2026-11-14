"""Turn the prepped RGBA view art (out/in/*.png, 1024px) into clean palette-label maps for projection.
Labels: 0 white, 1 black, 2 orange, 3 iris, 4 inner-ear salmon, 5 nose pink, 255 no-data.
Removes the cartoon outline (silhouette band + thin interior lines) so it does not get projected as black streaks.
Run from the project dir: python scripts/make_labels.py [in_dir/ out_dir/]  (needs numpy, scipy, Pillow)"""
import numpy as np
from PIL import Image
from scipy import ndimage as ndi
import sys
IN, OUT = (sys.argv[1:3] + ['out/in/', 'out/labels/'][len(sys.argv[1:3]):]) if len(sys.argv) > 1 else ('out/in/', 'out/labels/')
PAL = np.array([(255,255,255),(0x1C,0x1B,0x1B),(0xF4,0xA0,0x68),(0xB6,0xC3,0x71),(0xE0,0x90,0x72),(0xF3,0x95,0x98)], np.uint8)
OUTLINE = 12      # px band at the silhouette treated as outline
LINE_R = 9        # black structures thinner than ~2*LINE_R px are treated as drawn lines

def disk(r):
    y, x = np.ogrid[-r:r+1, -r:r+1]; return x*x + y*y <= r*r

def classify(rgb, eye_circles=(), nose_box=None):
    r, g, b = [rgb[..., i].astype(int) for i in range(3)]
    mx = np.maximum(np.maximum(r, g), b); mn = np.minimum(np.minimum(r, g), b); sat = mx - mn
    H, W = r.shape; yy, xx = np.mgrid[0:H, 0:W]
    lab = np.where(mx > 120, 0, 1).astype(np.uint8)            # achromatic: white / black
    chroma = (sat >= 45) & (mx >= 170)
    # pale blue shadow under the chin counts as white fur
    blueish = (b >= r) & (b >= g - 5)
    warm = chroma & ~blueish & (r > g + 15)
    ear = warm & ((r - g) > 100)                               # red-salmon inner ear vs orange (r-g ~ 85)
    lab[warm] = 2
    # salmon only in large blobs (real inner ears), never speckle rims
    cl, n = ndi.label(ear)
    if n:
        sz = ndi.sum(ear, cl, range(1, n + 1)); big = np.isin(cl, 1 + np.where(sz > 700)[0])
        big = ndi.binary_closing(big, disk(4)); lab[big & (lab != 1)] = 4
    lab[(sat >= 45) & (mx < 170) & (mx > 120)] = 1             # dark chromatic fringe -> black
    for cx, cy, rad in eye_circles:
        m = (xx - cx) ** 2 + (yy - cy) ** 2 <= rad * rad
        lab[m & (sat >= 30) & (g >= r - 12) & (mx > 70)] = 3   # olive / green iris
    if nose_box:
        x0, y0, x1, y1 = nose_box; m = np.zeros_like(chroma); m[y0:y1, x0:x1] = True
        lab[m & (sat >= 40) & (r > 180) & (abs(g - b) < 40)] = 5
    return lab

def fill_from(lab, bad):
    """replace bad pixels with the label of the nearest good pixel"""
    idx = ndi.distance_transform_edt(bad, return_distances=False, return_indices=True)
    return lab[idx[0], idx[1]]

def process(name, eye_circles=(), nose_box=None, keep_boxes=(), nodata_boxes=(), no_white=False):
    im = np.asarray(Image.open(IN + name + '.png').convert('RGBA'))
    alpha = im[..., 3] > 128
    lab = classify(im[..., :3], eye_circles, nose_box)
    lab = ndi.median_filter(lab, 3)
    # 1) silhouette outline band -> take the colour just inside it
    depth = ndi.distance_transform_edt(alpha)
    lab = fill_from(lab, depth < OUTLINE)
    # 2) thin interior black lines (legs, toes, folds) -> nearest non-line colour; keep face features
    black = lab == 1
    thin = black & ~ndi.binary_opening(black, disk(LINE_R))
    keep = np.zeros_like(black)
    for x0, y0, x1, y1 in keep_boxes: keep[y0:y1, x0:x1] = True
    thin &= ~keep
    lab = fill_from(lab, thin)
    lab = ndi.median_filter(lab, 5)
    if no_white: lab[lab == 0] = 1   # generated back view: stray white slivers are artefacts
    out = lab.copy()
    for x0, y0, x1, y1 in nodata_boxes: out[y0:y1, x0:x1] = 255
    ys, xs = np.where(alpha)
    np.savez(OUT + name + '.npz', lab=out, bbox=np.array([xs.min(), ys.min(), xs.max(), ys.max()]))
    vis = PAL[np.minimum(out, 5)]; vis[out == 255] = (255, 0, 255)
    Image.fromarray(vis).save(OUT + name + '_labels.png')
    print(name, 'bbox', xs.min(), ys.min(), xs.max(), ys.max(), 'counts', np.bincount(out.ravel(), minlength=6)[:6])

process('front', eye_circles=[(300, 389, 78), (538, 389, 78)], nose_box=(375, 410, 465, 475),
        keep_boxes=[(205, 295, 635, 525)])
# side: the eye and muzzle come from the front projection only, so blank them here
process('side', eye_circles=[(762, 392, 80)], keep_boxes=[(680, 300, 890, 500)],
        nodata_boxes=[(690, 318, 840, 466), (800, 400, 895, 500)])
process('back', no_white=True)
