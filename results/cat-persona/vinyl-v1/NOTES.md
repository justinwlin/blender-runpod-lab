# vinyl-v1 preview (experiment)

Quick Cycles OptiX preview of the simple vinyl-toy cat mascot, rendered from `scripts/build_cat_vinyl.py` on the `blender-5.0.1` Runpod template (Blender 5.0.1, AgX, 32 samples, OIDN). Not a verified final.

**Verdict: partly.** The new image/template/OptiX pipeline works and can turn around a still in seconds. This particular scripted model does **not** reach the cute look in `mascot/simple.jpg`.

## What matches
- Cream studio backdrop and soft product lighting
- Matte light-gray vinyl-like shader (too pale, but in the right family)
- Accessories are *present*: black glasses, a headphone band and cups, pink inner-ear / nose hints, a mouth line
- The *intent* of a chibi toy (big head, short limbs, ball tail) is in the constants

## What does not
- The body is unfused stacked spheres — the exact failure [Sophie's guide](https://github.com/sophie-zxy/high-fidelity-3d-model) warns about. The silhouette does not read as one toy
- Hero framing is awkward (almost back/underside); the figure is not planted on the ground
- Missing the things that make the reference cute: tabby forehead stripes, bangs tuft, readable cardigan and chevron tee, big amber eyes set in sockets
- Leftover floating spheres, clothes that do not read as a jacket

## What it would take
1. Stop after the fuse step and judge the contact-sheet silhouette *before* adding accessories. The metaball convert/remesh in this script did not produce one watertight skin (and the image build had also dropped the MCP addon into CPython's `venv/scripts` instead of Blender's `5.0/scripts/addons`).
2. A single continuous body — fixed metaball family/threshold + remesh, or a subdivided base mesh, or an image-to-3D base from `simple.jpg` (Rodin / Tripo / Meshy) that is then cleaned, shaded, and lit in Blender. The last of those is the more realistic path to the reference's appeal; guide §8 and §10 say scripted sculpting cannot invent a cute face by itself.
3. Only then: socketed eyes, glasses, headphones, and the cardigan/tee as separate clean meshes.

See `side-by-side.png`, `hero_three_quarter.png`, and `contact-sheet.png`.
