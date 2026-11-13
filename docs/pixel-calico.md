# Pixel the calico cat: image-to-3D, flat-colour projection, rig and animation

End-to-end record of how the Pixel mascot model, renders and animation clips were made (13 Nov 2026). Scripts are in [`scripts/pixel_calico/`](../scripts/pixel_calico/) (the commands below assume they are copied to `scripts/` in a working directory). No media is stored in git.

Reference art: [justinwlin/pixel-mascot](https://github.com/justinwlin/pixel-mascot) (`reference/pixel-turnaround-original.jpg` is the source of truth; `turnaround/pixel-turnaround-sheet.jpg` supplies the back view).

## Pipeline at a glance

| Step | Tool | Where | Script |
| --- | --- | --- | --- |
| 1. Multi-view image to mesh | Hunyuan3D-2mv | L40S pod | `gen.py` |
| 2. Pick a mesh | Blender clay previews | CPU | `inspect_meshes.py` |
| 3. Art to palette label maps | numpy / scipy | CPU | `make_labels.py` |
| 4. Tail fix, colour projection, material, stage, contact sheet | Blender 5.0.1 | A5000 pod | `build_pixel.py`, `pixel_tail.py`, `sheet.py` |
| 5. Hero render | Cycles OptiX | A5000 pod | `render_hero.py`, `composite_hero.py` |
| 6. Rig | Blender (bone heat on a proxy) | A5000 pod | `rig_pixel.py` |
| 7. Animate and render clips | Cycles OptiX, ffmpeg | A5000 pod | `anim_pixel.py`, `gate_sheet.py`, `encode.sh` |

## 1. Image to 3D (Hunyuan3D-2mv)

- Model: `tencent/Hunyuan3D-2mv`, subfolder `hunyuan3d-dit-v2-mv`, variant `fp16`; 50 inference steps, octree resolution 380, `num_chunks` 20000. Shape only, no Hunyuan3D-Paint (it needs a compiled `custom_rasterizer`, and the image has no gcc/nvcc).
- Inputs: front and side views cropped from the original sheet, back view from the generated turnaround sheet, white background removed to alpha, padded to square 1024 px (`gen.py`, crop boxes inside).
- `gen.py` runs three view combinations x two seeds (12345, 7): `A` front + mirrored side as `left` + back, `B` front + side as `right` + back, `C` front + mirrored side as `left`.
- Environment on the pod: template `blender-5.0.1`, torch 2.5.1 + torchvision 0.20.1 (cu124), Hunyuan3D-2 installed with `pip install -e .`. A too-new diffusers fails with `module 'torch' has no attribute 'accelerator'`; the intended pin was `diffusers==0.31.0 transformers==4.46.3`. **Not verified:** the six meshes were produced by the session before this one, and that pod was terminated before its `pip` state or log could be read, so the exact diffusers/transformers versions that produced the meshes are unconfirmed.
- Timing from file timestamps: about 30 s per mesh on the L40S.
- Result: all six meshes were smooth, fused, recognisably the mascot (ears, eye sockets, nose, mouth, toes). None was blocky. This confirms the recommendation in [lessons-character-modeling.md](lessons-character-modeling.md).

### View convention

- Chosen mesh: `B_front_right_back_s12345` (original side art, cat facing image-right, passed as `right`). Picked for the cleanest face relief.
- `A` (mirrored side passed as `left`) and `C` gave near-identical, equally valid cats. Both conventions work; this run does not single one out as "the" correct one.
- After glTF import into Blender the cat faces -Y, +Z is up, and the cat's left is +X.

### What Hunyuan got wrong: the tail

The reference art is inconsistent about the tail (front view: tail on the viewer's right; side and generated back views: on the other side). Hunyuan resolved that by fusing the tail into a **ring around the whole base**, with lumps on both sides. That was rejected on review ("the tail doesn't make sense") and fixed in step 4 (v2).

## 2. Label maps (`make_labels.py`)

Each prepped view is quantised to six labels (white, black, orange, iris, inner-ear salmon, nose pink) with simple colour rules rather than nearest-palette distance, because anti-aliased black/white and black/orange edges otherwise land on the olive iris colour. Then:

- the silhouette outline band (12 px) is replaced by the colour just inside it;
- thin interior black lines (legs, toes, folds) are removed by a morphological opening, except inside a face box that keeps the eyes and mouth;
- inner-ear salmon is only allowed in large blobs; iris and nose pink only inside eye circles / a nose box;
- in the side view the eye and muzzle are blanked to "no data" so those features come from the front projection only (otherwise you get double eyes);
- stray white in the generated back view is forced to black.

Without the outline removal the cartoon outline projects as black streaks on every surface that is grazing to the view.

## 3. Geometry fix, projection and material (`build_pixel.py`, `pixel_tail.py`)

1. Import the GLB, apply transforms, put the feet on z = 0. Record the silhouette extents of the **original** mesh: the art-to-mesh fit is a plain bounding-box fit per view, and the art includes the tail.
2. **Tail fix (v2).** Measure the body outline just above the tail ring (z 0.50-0.58, per angle around the body axis). Compress everything below that sticks out past this outline back onto it (front paws and chest excluded), keeping a thin ordered shell rather than collapsing to zero thickness. Voxel-remesh the body at 0.008 to merge the squashed layers into one watertight surface, then relax the clamped band (120 Laplacian iterations) so the haunch reads as a soft seated body.
   - First attempt clamped to a fixed ellipse: it left a boxy ledge. Collapsing to zero thickness left comb-like remesh noise. Both are fixed by the measured profile + thin shell.
3. **New tail.** `pixel_tail.py` defines one tapered tube (Catmull-Rom centre line, 8 control points, radius 0.13 to 0.17 to 0.12, hemispherical tip) from the back, around the cat's left side (viewer's right in the front view), curling forward to rest by the front paws. It is a separate object with a subdivision modifier, black with a few procedural orange patches, black tip.
4. **Projection.** For each view (front, right side, mirrored back, and a low-priority mirrored side for the unseen left flank) every vertex samples the label map orthographically; the view that faces the vertex best and is not occluded (BVH ray cast) wins. Unlabelled vertices copy the nearest labelled one. Labels are diffused along mesh edges and re-quantised (6 iterations everywhere, 60 in the clamped base band) to round off stair-steps. The front paws are forced white.
5. **Material.** One Principled material reading the `PixelColor` vertex colour attribute, roughness 0.6; an `EyeGloss` mask makes the eye discs glossy. Palette is the README hex values converted to linear; white is rendered at 0.85 albedo so it does not clip.
6. **Stage.** Three area lights (key/fill/rim) on a rig that turns with the contact-sheet camera, white world light, shadow-catcher floor with transparent film; Standard view transform so the flat colours stay true.

Known limits: colour is per-vertex, so patch edges are slightly stair-stepped close up; the left flank has no reference art; the underside and toe beans are not painted; the voxel remesh softens fine relief a little; no UVs or retopology.

## 4. Rig (`rig_pixel.py`)

- 13 body bones: root, hips, spine, chest, head, two ears, two-bone front legs, hind feet; plus a 6-bone tail chain.
- Bone heat (automatic weights) is run on a **proxy**: the body voxel-remeshed at 0.018 and decimated to about 12k vertices, which is manifold and fast. Weights are then transferred to the render mesh with Data Transfer (nearest face interpolated).
- Patches where the sculpt is fused: ears get a ramp along the ear axis; everything above the chin follows the head through a wide blend (a narrow one tore the neck crease); the two front legs, fused along the midline, have their total leg weight re-split left/right by x and upper/lower by height.
- The tail is a separate object, so its weights are analytic (tent functions along the tube parameter) and the tail bones are added after bone heat so the body never follows them.
- A shader blink: an `EyeV` attribute (0 bottom to 1 top of each eye disc) is compared with one animated value so a black lid sweeps down.

## 5. Animation and rendering (`anim_pixel.py`)

Poses are procedural functions of the frame, baked to keyframes on every frame at 24 fps, so each clip loops exactly.

- **walk** (24-frame cycle): the sculpt is a sitting cat, so this is a toy-like sitting waddle, not an anatomical quadruped walk: alternating front-paw steps, body rock and bob with squash, counter-rotating head, ear bounce, tail wave. The camera and lights follow; floor dots are spaced at one stride so the loop is seamless.
- **ball** (72-frame cycle): a ball bounces between the two front paws; the cat tracks it with its head, bats it with alternating paws with a small hop, tail flicks, one blink.
- **idle** (96-frame cycle): breathing, slow head tilt, ear twitches, tail sway, blinks.

Gate before every full render: 8 frames per clip at 24 samples, checked for tearing. That caught smeared front legs (fixed by the leg re-split), a mis-scaled floor pattern, and the neck streak.

Render: Cycles OptiX on an RTX A5000, 960x540, 64 samples + OIDN, persistent data. `encode.sh` loops the cycles into H.264 MP4s (walk x5 = 5 s, ball x2 = 6 s, idle x1 = 4 s).

## Commands

```sh
# on the GPU pod that has Hunyuan3D-2 installed, from the Hunyuan3D-2 checkout
HF_HUB_ENABLE_HF_TRANSFER=1 python3 gen.py

# anywhere with Blender 5.0.1 (add "gpu" on a pod); run from the project dir with scripts/, out/glb, out/in
blender -b -P scripts/inspect_meshes.py -- out/glb out/inspect
python scripts/make_labels.py out/in/ out/labels/
blender -b -P scripts/build_pixel.py -- out/glb/B_front_right_back_s12345.glb out/labels "$PWD/v2" gpu
python scripts/sheet.py v2
blender -b v2/pixel-calico.blend -P scripts/render_hero.py -- "$PWD/v2/hero_rgba.png" 256 1600 gpu
python scripts/composite_hero.py v2/hero_rgba.png v2/hero.png
blender -b v2/pixel-calico.blend -P scripts/rig_pixel.py -- "$PWD/v2/pixel-rigged.blend"
for c in walk ball idle; do
  blender -b v2/pixel-rigged.blend -P scripts/anim_pixel.py -- $c gate "$PWD/v2/anim"   # check frames first
  blender -b v2/pixel-rigged.blend -P scripts/anim_pixel.py -- $c full "$PWD/v2/anim"
done
sh scripts/encode.sh "$PWD/v2/anim"
```

`build_pixel.py` needs `mkdir -p <out>/sheet` first. Blender output paths should be absolute.

## Timings

| Step | Hardware | Time |
| --- | --- | --- |
| Hunyuan3D-2mv, one mesh (50 steps, octree 380) | L40S | about 30 s (from file timestamps) |
| Clay previews of 6 meshes, 5 views each | 8-core CPU | 30 s |
| Label maps | CPU | a few seconds |
| v1 build incl. 4 contact tiles (720 px, 48 samples) | 8-core CPU | 43 s |
| v1 hero, 1600 px, 200 samples + OIDN | 8-core CPU | about 2 min |
| v2 build incl. remesh and 4 contact tiles (128 samples) | RTX A5000 | about 25 s |
| v2 hero, 1600 px, 256 samples + OIDN | RTX A5000 | 27 s |
| Rig (proxy bone heat + transfer) | pod CPU | about 12 s |
| Gate frames, 960x540, 24 samples | RTX A5000 | about 3.7 s per frame |
| Full clips, 960x540, 64 samples, three clips sharing one GPU | RTX A5000 | walk 24 f in 236 s, ball 72 f in 585 s, idle 96 f in 689 s (7-10 s per frame; about 11.5 min wall for all three) |

Most of the per-frame time is scene sync and BVH rebuild for the deforming mesh, not sampling, so a bigger GPU would not have helped much. Larger GPUs (up to an H200) and up to three pods were offered late in the run; they were not used because the final renders had already finished on the single A5000.

## What failed or needed a second pass

- **Hunyuan tail ring** (above): fixed by clamp + remesh + a separate tail.
- **Nearest-palette quantisation** put olive "iris" pixels on every black/white edge: replaced by rule-based classification with region limits.
- **Projecting the outline**: black streaks on grazing surfaces until the outline band and thin lines were stripped from the label maps.
- **Eye gloss mask** from the iris vertices' centroid picked up stray iris vertices and made half the face glossy: now placed from the known eye centres in the front art.
- **First lighting pass** was about 4x overexposed (orange went yellow, black went grey).
- **Bone heat on the two fused front legs** smeared one leg into the other: fixed by re-splitting the leg weights by x.
- **Generated back view** has the tail on the wrong side and stray white slivers: the art is mirrored and white is dropped.
- **SSH sessions to the pod dropped twice** during long foreground commands; long renders are now started with `nohup` and polled.

## Costs

Billed-duration estimates, not invoices.

| Pod | GPU | $/hr | Runtime | Cost | Used for |
| --- | --- | --- | --- | --- | --- |
| pixel-calico-cat | L40S (secure) | 1.09 | about 20 min for its last boot cycle (earlier time by the previous session unknown) | about $0.37 | Hunyuan3D-2mv mesh generation. Terminated. |
| pixel-calico-anim | RTX A5000 (secure) | 0.27 | created 22:12 UTC 13 Nov 2026; about 70 min when the final clips were copied back | about $0.32 so far | v2 build, hero, rig, all animation renders. Left running on request. |

Total for this work: under $1 of roughly $10 budgeted. The A5000 was picked as the cheapest available card; it was plenty for these previews.

The first pod was terminated as soon as the meshes were copied off it, a few minutes before an instruction to keep it running arrived. Its Hunyuan3D-2 install and model cache went with it, so generating new meshes means repeating that setup (clone, `pip install -e .`, pin diffusers/transformers, model download).
