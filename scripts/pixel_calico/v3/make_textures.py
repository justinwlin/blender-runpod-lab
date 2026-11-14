"""v3: turn the palette label maps into crisp, anti-aliased colour textures for per-pixel projection on the head,
plus a toe-bean decal. python scripts/v3/make_textures.py out/labels/ out/v3/tex/   (numpy, scipy, Pillow)"""
import sys, numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as ndi
LAB, OUT = sys.argv[1:3]; UP = 4; MIN_PATCH = 2600      # px at 1024: fur islands smaller than this are speckle
def lin2srgb(x): return np.where(x <= 0.0031308, x * 12.92, 1.055 * x ** (1 / 2.4) - 0.055)
def srgb2lin(c): c = np.array(c) / 255; return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
PAL = np.stack([srgb2lin(c) for c in [(255, 255, 255), (0x1C, 0x1B, 0x1B), (0xF4, 0xA0, 0x68), (0xB6, 0xC3, 0x71), (0xE0, 0x90, 0x72), (0xF3, 0x95, 0x98)]])
PAL[0] = 0.85            # soft white so it does not clip
def view(name, mirror, out):
    z = np.load(LAB + name + '.npz'); L = z['lab']; x0, y0, x1, y1 = [int(v) for v in z['bbox']]
    bad = L == 255
    if bad.any():
        idx = ndi.distance_transform_edt(bad, return_distances=False, return_indices=True); L = L[idx[0], idx[1]]
    L = np.where(L == 4, 1, L) if out != "ear" else L   # inner-ear salmon belongs to the separate ear parts, not the skull
    # clean, large patches only: drop the art's speckle/splatter (small fur-colour islands), keep the face features
    protect = np.zeros(L.shape, bool)
    if name == 'front': protect[300:525, 228:612] = True
    fur = np.isin(L, (0, 1, 2)) & ~protect; drop = np.zeros(L.shape, bool)
    for k in (0, 1, 2):
        cl, n = ndi.label((L == k) & fur)
        if n:
            sz = ndi.sum(np.ones(L.shape), cl, range(1, n + 1)); drop |= np.isin(cl, 1 + np.where(sz < MIN_PATCH)[0])
    if drop.any():
        idx = ndi.distance_transform_edt(drop | ~fur, return_distances=False, return_indices=True)
        L = np.where(drop, L[idx[0], idx[1]], L)
    sm = L.copy()
    for _ in range(2): sm = ndi.median_filter(sm, 11)
    L = np.where(fur & np.isin(sm, (0, 1, 2)), sm, L)
    L = L[y0:y1 + 1, x0:x1 + 1]
    if mirror: L = L[:, ::-1]
    # upsample each label's mask smoothly and blend the palette in linear light: anti-aliased, stair-step free edges
    acc = np.zeros((L.shape[0] * UP, L.shape[1] * UP, 3)); tot = np.zeros(acc.shape[:2])
    for k in range(6):
        m = ndi.zoom((L == k).astype(np.float32), UP, order=1); m = ndi.gaussian_filter(m, UP * 0.9)
        m = np.clip((m - 0.5) * 6 + 0.5, 0, 1)        # sharpen back to a ~1px soft edge
        acc += m[..., None] * PAL[k]; tot += m
    img = acc / np.maximum(tot, 1e-6)[..., None]
    Image.fromarray((lin2srgb(img) * 255 + 0.5).astype(np.uint8)).save(OUT + out + '.png'); print(out, img.shape)
view('front', False, 'front'); view('side', False, 'side'); view('back', True, 'back_m'); view('side', True, 'side_m')
# toe beans: one main pad + four toes, pink #F69B98 on soft white, toes toward the top of the image (= front of the paw)
S = 512; im = Image.new('RGB', (S, S), tuple(int(v) for v in lin2srgb(np.array([0.85] * 3)) * 255)); d = ImageDraw.Draw(im)
pink = (0xF6, 0x9B, 0x98)
def ell(cx, cy, rx, ry): d.ellipse([S * (cx - rx), S * (cy - ry), S * (cx + rx), S * (cy + ry)], fill=pink)
ell(0.5, 0.60, 0.17, 0.13); ell(0.40, 0.65, 0.09, 0.09); ell(0.60, 0.65, 0.09, 0.09)
for cx, cy in ((0.25, 0.40), (0.41, 0.29), (0.59, 0.29), (0.75, 0.40)): ell(cx, cy, 0.075, 0.09)
im = im.filter(__import__('PIL.ImageFilter', fromlist=['x']).GaussianBlur(1.5)); im.save(OUT + 'beans.png')
