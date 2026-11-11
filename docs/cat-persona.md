# Silver tabby cat persona (v1, rejected experiment)

> **Status: rejected experiment.** Justin reviewed `front.png` and rejected this v1 look as low fidelity (blocky primitive assembly, helmet-like hair, head and body do not flow, face lacks charm). It is kept as a record of the first pass. A v2 rebuild follows.

Script: `scripts/build_cat_persona.py`. Outputs: `results/cat-persona/`. Reference: `results/cat-persona/concept.jpg`. Current revision: **feedback-2**. The README links here.

The final look has a large chibi head, sleepy amber eyes, rectangular black glasses, sculpted silver crown/bangs, and cream muzzle and paws. A warm gray-beige cardigan with tapered sleeves covers a charcoal zip hoodie and black crew tee with a broken brushstroke chevron. Headphones and cable rest around the neck. The striped tail curves up to a tapered cream tip. No particle hair is used.

## Verified

Blender **5.0.1**, build hash **a3db93c5b259**, built 2025-12-16. All task renders ran locally on the eight-core CPU box, with no paid service. EEVEE uses software graphics here. Construction starts from an empty factory file and a fixed seed. AgX, three-point lighting, a camera-following studio sweep, UV-aligned knit ribs, sheen/noise fur relief, and a simple animated armature are present.

The head and muzzle are voxel-unioned and smoothed into one continuous mesh. A feathered cream attribute blends into the silver face, rather than assigning a separate cream mask surface. Soft painted attributes supply forehead M and cheek markings. The light silver shader uses mid-gray, wavy, eased tabby bands on the legs, ears and tail. The back of the head has short silver fur and five short crown tufts; the full-length hair cap and long rear locks are gone. The eyes, glasses, headphones, garments, tee and city setup retain the previous pass's designs.

The head remains 23% larger and the torso 17% shorter than the initial model. Geometry and bone rest positions share those transforms. The studio uses an orthographic camera; dusk uses an 80 mm perspective camera, face focus and strong DOF, grounded buildings along a continuous street, warm/cool window spheres, street lamps and a purple-to-orange sky.

Final mode requires an OptiX GPU and refuses CPU fallback. `--preview` explicitly selects denoised Cycles CPU; `--eevee` selects EEVEE. Preview defaults: 640 square, 12 samples. Final defaults: 1440 × 1080, 128 samples. `--res N` overrides both dimensions; `--frames a-b` selects an inclusive idle range in 1–48. Each render metadata file records version, backend, preview flag, resolution, samples, revision, proportions and individual render seconds. A new run replaces that directory's metadata.

Exact final commands, from the repository root:

```sh
B=$BLENDER_DIR/blender-5.0.1-linux-x64/blender
"$B" -b --factory-startup --threads 8 --python-exit-code 1 --python scripts/build_cat_persona.py -- --eevee --res 640 --samples 24 --stills --save-blend --output results/cat-persona
"$B" -b --factory-startup --threads 8 --python-exit-code 1 --python scripts/build_cat_persona.py -- --eevee --res 640 --samples 32 --backdrop dusk --output results/cat-persona/dusk
"$B" -b --factory-startup --threads 8 --python-exit-code 1 --python scripts/build_cat_persona.py -- --eevee --res 480 --samples 12 --idle --frames 1-48 --output results/cat-persona/idle
"$B" -b results/cat-persona/cat-persona.blend --threads 4 --python-exit-code 1 --python scripts/check_cat_persona.py
"$B" -b --factory-startup --threads 4 --python-exit-code 1 --python scripts/build_cat_persona.py -- --preview --res 160 --samples 2 --output results/cat-persona/cycles-check
python3 scripts/finalize_cat_persona.py --prune
# Expected failure on this CPU box:
"$B" -b --factory-startup --threads 8 --python-exit-code 1 --python scripts/build_cat_persona.py -- --output results/cat-persona/guard-check
```

`check_cat_persona.py` checks proportions, loop closure and both blink keys, then renders the closed-eye pose. `finalize_cat_persona.py` remains useful: it assembles the final sheets, encodes the complete sequence with ffmpeg, validates the MP4 with ffprobe, and prunes raw frames only after successful validation. It uses H.264, CRF 18, slow preset, yuv420p and faststart. After pruning, it can revalidate the retained video without source PNGs. Its optional `--before-front` and `--before-back` inputs create the one downsized before/after image before those development inputs are discarded. The image compares three-quarter and back views from the previous pass with this final pass.

The loop is 48 frames at 24 fps. Frame 49 is the mathematical duplicate of frame 1 and is excluded from the encode. Breathing, head tilt and tail swish are periodic; eyelid keys blink over frames 19–23. Mesh parts use bone vertex groups; the continuous tail blends across three bones.

### Look development and retained evidence

The initial three passes established the outfit, corrected the glasses and stripe frequency, and replaced oval cardigan fronts. The next three passes enlarged the head, shortened the torso, rebuilt the cardigan and hoodie as curved shells, added painted tee flecks and a tapered tail, and established the grounded dusk street.

This final pass removed the dark face-framing hair cap, fused the muzzle into the head, feathered its cream coloring, raised the fur value, reduced stripe contrast, replaced raised face marks with soft painted markings, reduced cheek fluff to two rounded tapered tufts per side, and shortened the rear hair. After viewing all four turnarounds, cheek-mark visibility and tuft angles were refined before the final render. All final stills, dusk and closed-eye images were opened. All 48 idle frames were inspected in the retained idle sheet.

Full look-development image folders and source snapshots have been removed. Their timing metadata is consolidated in `development-metadata.json`; the single visual history is `iteration-comparison.png`. Raw idle PNGs are intentionally not retained. The reference image remains intact.

| Final CPU preview work | Resolution | Samples | Render-call total |
| --- | --- | --- | --- |
| Four final turnarounds | 640 × 640 | 24 | 38.562 s |
| Final dusk | 640 × 640 | 32 | 18.891 s |
| 48-frame idle | 480 × 480 | 12 | 242.292 s |
| Cycles CPU smoke render | 160 × 160 | 2 | 0.620 s |

Final turnaround + dusk + idle render time: **299.745 seconds**. Idle frames took **4.461–6.030 s** each; H.264 encoding took **0.270 s**. ffprobe confirmed **480 × 480, 48 frames, 24 fps, 2.000 seconds**. The closed-eye render took **8.047 s**.

Rig: **12 bones**, **205 rigged meshes**; frame-1/frame-49 maximum matrix difference **8.573e-18**; blink keys 1 at frame 21 and 0 at frame 49. Head including cheek fur / shoulder width is **1.051**. The default OptiX guard returned exit code 1 on this CPU box.

Retained result size: **7.66 MB (7.31 MiB)**, below the 12 MB target, including the reference. The one blend is **1.95 MiB**. The single comparison is **1280 × 344**. Raw frame PNGs, full iteration image folders, duplicate idle sheets and blend backups were pruned after MP4 validation. Metadata/logs preserve timings; render-call seconds exclude scene build and encoding and are not a controlled benchmark.


Retained files under `results/cat-persona/`:

- `concept.jpg`: original supplied reference.
- `front.png`, `three_quarter.png`, `side.png`, `back.png`, `contact-sheet.png`: final 640-square stills and labeled turnaround.
- `dusk/dusk.png`, `dusk/render-metadata.json`: final city portrait and timing record.
- `idle-test.mp4`, `idle-contact.png`, `idle/render-metadata.json`, `video-check.json`: final two-second idle, compact 48-frame inspection sheet and verification records.
- `cat-persona.blend`: one editable scene with the rig, materials and idle animation.
- `iteration-comparison.png`: one downsized before/after image; `development-metadata.json`: consolidated historical render metadata.
- `blink-check.png`, `rig-check.json`, `render-metadata.json`: rig/closed-eye checks and turnaround timings.
- `cycles-check/three_quarter.png`, `cycles-check/render-metadata.json`: explicit Cycles CPU smoke preview and its timing record.
- `logs/`: execution and development logs.

## Experimental / not verified

GPU final rendering, arbitrary posing, export and production deformation remain unverified. The outfit uses curved overlapping solids, without cloth simulation. Arms are covered by sleeves. Glasses have empty lens openings. Crown and bangs remain broad sculpted clumps rather than the concept's fine layered fur; the short rear fur is a deliberate simplification. The forehead markings are partly covered by bangs and glasses. The graphic interprets the reference print. City details are deliberately simple and defocused. CPU EEVEE previews may be grainy and do not establish final Cycles quality.

## ESTIMATED GPU cost — not measured for this cat

Rates supplied in the brief: RTX PRO 4000 **$0.57/hour**, RTX PRO 6000 **$2.49/hour**. These are assumptions, not current-price verification. No GPU service was used for this task.

Measured repository references, all Cycles OptiX, 128 samples, 1440 × 1080 on RTX PRO 6000:

- [Pikachu v2](pikachu-v2.md), [render metadata](../results/pikachu-v2/render-metadata.json): **508.226 / 108 = 4.706 s/frame**.
- [Pikachu v3](pikachu-v3.md), [render metadata](../results/pikachu-v3/render-metadata.json): **503.962 / 108 = 4.666 s/frame**. Use **4.69 s/frame** as the simpler-scene baseline.
- [Pikachu v4, soft plush fur](pikachu-v4.md), [render metadata](../results/pikachu-v4/render-metadata.json), `frame_timings_main`: **486.058 seconds for 17 measured frames = 28.59165 s/frame**, range **17.892–31.216 s/frame**. The complete animation has 108 frames split across four workers, but this metadata array contains only the main worker's 17 timings; 486.058 is not the full animation's wall time. This fur-heavy mean is the upper-bound planning reference, about **6.10×** the v2/v3 baseline, not a guaranteed ceiling for an unmeasured cat scene.

The **ESTIMATE** below brackets RTX PRO 6000 performance between **4.69 and 28.59165 s/frame** using those measured references. No RTX PRO 4000 comparison was measured: its **ESTIMATE** assumes **2–4×** the 6000 render time.

| Work, 1440 × 1080 at 128 samples | RTX PRO 6000 ESTIMATE | RTX PRO 4000 ESTIMATE |
| --- | --- | --- |
| One still | 4.69–28.59 s; $0.0032–0.0198 | 9.38–114.37 s; $0.0015–0.0181 |
| 48-frame idle | 225.12–1372.40 s; $0.156–0.949 | 450.24–5489.60 s; $0.071–0.869 |
| Four turnarounds + dusk + idle, 53 frames | 248.57–1515.36 s; $0.172–1.048 | 497.14–6061.43 s; $0.079–0.960 |

Arithmetic for 53 frames: `53 × (4.69 to 28.59165) / 3600 × $2.49` for the 6000. Multiply the lower seconds by 2 and upper seconds by 4, then use `$0.57`, for the 4000. These are render-only **ESTIMATES**. A hypothetical five-minute startup/inspection allowance adds `5/60 × rate`, or **$0.0475** / **$0.2075** for 4000 / 6000, before storage and billing increments.

## v2 (rejected experiment, stopped early)

Status: **rejected by Justin at the dressed-preview stage and stopped**. Kept for reference only; not a verified result.

Spec followed: [Sophie's high-fidelity 3D model guide](https://github.com/sophie-zxy/high-fidelity-3d-model) (commit f896171), §2 five-stage pipeline, §5 four classic mistakes, §9 hard rules, §11 done checklist.

### Verified
- `scripts/build_cat_persona_v2.py` runs headless on pinned Blender 5.0.1 and stops after each gate with `--stage N`; proportions are named constants with asserts.
- `scripts/contact_sheet.py` renders front / side / top / three-quarter contact sheets of any saved scene.
- Gates completed: stage 1 (mirrored Skin-cage blockout), stage 2 (voxel-remesh fuse into one skin), stage 3 (scripted primary/secondary/tertiary offsets), stage 4 (QuadriFlow quads + armature weights). Contact sheets and critiques: `results/cat-persona/v2/stage-N/`.
- A first dressed preview contact sheet, `.blend` and `.glb`: `results/cat-persona/v2/preview/`.
- Render host: one Runpod CPU pod (cpu3c, 32 vCPU, $0.96/hr, about 37 min). A Runpod RTX 4090 pod ($0.89/hr, about 24 min) was set up for the hero render but never rendered. Total spend about $0.94.

### Experimental / why it was rejected
- The dressed preview reads as a white blob with a pasted-on face: fur colour and tabby stripes are missing, hair is a thin strip instead of messy clumps, the head lacks the concept's big rounded silhouette, and the clothes read as thin shells.
- Scripted bmesh offsets cannot stand in for a sculpt pass (guide §10). The head, jowls, back of skull and the hair would need a human sculpt pass, or a clean base mesh (guide §8), to reach the concept.
- No hero Cycles still, side-by-side, or idle mp4 were rendered.
