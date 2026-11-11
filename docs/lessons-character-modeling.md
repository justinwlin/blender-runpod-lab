# Lessons: character modeling

Honest findings from trying to build a cute chibi silver-tabby cat mascot in Blender with a headless, scripted agent. **Verified results stay in their own section.** Ideas that were not tried are listed separately at the end.

The reusable Runpod path for this work is the `blender-5.0.1` template, documented in [docker-template.md](docker-template.md). Sophie's modeling guide (what the scripts tried to follow) is summarized in [high-fidelity-character-guide.md](high-fidelity-character-guide.md) and lives in full at [sophie-zxy/high-fidelity-3d-model](https://github.com/sophie-zxy/high-fidelity-3d-model).

Rejected cat experiments and their images are kept on the `cat-persona` branch only. They were not merged into `main`.

## Verified

### Scripted primitive / metaball modeling did not reach the concept

Three scripted builds were judged against a concept or a simpler vinyl-toy turnaround. None of them looked right.

**v1 — stacked primitives (rejected).** Script: `scripts/build_cat_persona.py` on `cat-persona`. Notes and CPU previews: [docs/cat-persona.md](https://github.com/justinwlin/blender-runpod-lab/blob/cat-persona/docs/cat-persona.md), [results/cat-persona/](https://github.com/justinwlin/blender-runpod-lab/tree/cat-persona/results/cat-persona). The model was assembled from separate parts (blocky body, helmet-like hair, head and body that do not flow). It was rejected as low fidelity. This is the exact failure the high-fidelity guide warns about: seams and perfect primitive silhouettes.

**v2 — Sophie-guide staged pipeline (rejected, stopped early).** Script: `scripts/build_cat_persona_v2.py` on `cat-persona`. Stage contact sheets: [results/cat-persona/v2/](https://github.com/justinwlin/blender-runpod-lab/tree/cat-persona/results/cat-persona/v2). This followed the guide's five stages (mirrored Skin cage, voxel remesh fuse, scripted sculpt offsets, QuadriFlow, dressed preview) with named constants and a 4-view contact sheet after each gate. The dressed preview still read as a pale blob with a pasted-on face: missing tabby colour, thin hair, weak head silhouette, clothes as thin shells. Scripted bmesh offsets did not stand in for a sculpt pass (guide §10). No hero Cycles still was rendered; work stopped after the preview was rejected.

**vinyl-v1 — simple vinyl-toy preview (experiment, not a match).** Script: `scripts/build_cat_vinyl.py` on `cat-persona`. Outputs and a side-by-side against the vinyl reference: [results/cat-persona/vinyl-v1/](https://github.com/justinwlin/blender-runpod-lab/tree/cat-persona/results/cat-persona/vinyl-v1), including [NOTES.md](https://github.com/justinwlin/blender-runpod-lab/blob/cat-persona/results/cat-persona/vinyl-v1/NOTES.md) and [side-by-side.png](https://github.com/justinwlin/blender-runpod-lab/blob/cat-persona/results/cat-persona/vinyl-v1/side-by-side.png). A deterministic metaball body, remesh, matte vinyl materials, glasses, and headphones were rendered with Cycles OptiX (32 samples, 1080px hero, ~34 s wall on an L40S). The render pipeline worked. The body came out as unfused stacked spheres with awkward framing, no tabby stripes, no bangs, no readable cardigan or chevron tee, and no socketed amber eyes. It did not reach the cute vinyl look.

Shared lesson, verified across all three: **an agent driving bpy can light, render, and assemble contact sheets reliably, but it has not produced a cute, unified character body from primitives or metaballs alone.** Fusing on paper (voxel remesh / metaballs) is not enough if the contact-sheet silhouette still reads as stacked balls or a featureless blob.

### Costs per attempt (personal or local, as measured)

These are billed-duration estimates from the runs, not invoices. GPU hourly rates seen at the time are in [docker-template.md](docker-template.md).

| Attempt | Where | What was billed / measured | Approx. cost |
| --- | --- | --- | --- |
| v1 | Local CPU box, no paid pod | EEVEE / Cycles-CPU previews only | **$0** |
| v2 | Personal Runpod CPU ($0.96/hr, ~37 min) plus an RTX 4090 ($0.89/hr, ~24 min) that was set up but never rendered | Setup and staging only; no hero render | About **$0.94** |
| vinyl 4090 setup (abandoned mid-preview) | Personal RTX 4090 secure, $0.89/hr, ~9.6 min | Image and Blender setup, no finished look | About **$0.14** |
| vinyl-v1 preview + template smoke | Personal L40S secure, $1.09/hr, 156 s, plus the 4090 setup above | 32-sample OptiX preview after template launch | L40S about **$0.05**; session total about **$0.19** |

The `blender-5.0.1` image and template removed the first-boot Blender download and apt stall: launch to SSH was about **72 seconds**, and Blender + OptiX were ready immediately after SSH.

### What did work (infrastructure, not the character)

- Pinned Blender 5.0.1 (SHA-256 `8019580ee1b7262e505f4196a00237ccf743c88d205b38d34201510676e60b09`) with Cycles, OptiX, AgX, and OIDN.
- A baked GHCR image and personal-account template (`blender-5.0.1`) so a pod does not install Blender or X/GL libs at boot. See [docker-template.md](docker-template.md).
- Headless `bpy` scripts with named constants, contact sheets, and metadata.
- After a path/X11 fix, the official blender-mcp addon accepted a JSON `ping` on port 9876 under Xvfb.

## Not verified / recommended next path

These are recommendations, not measured results in this repo.

- **Recommended next path:** generate a 3D base from the approved vinyl (or concept) image with an image-to-3D model such as **Hunyuan3D** or **TRELLIS**, then use Blender for cleanup, retopo if it must move, materials, rigging, lighting, and rendering on the `blender-5.0.1` template. This matches how many “AI in Blender” demos actually get a good mesh (they do not freehand-sculpt in bpy).
- Other image-to-3D services (Rodin, Tripo, Meshy) are in the same class; they have not been tried here for this cat.
- A human sculpt pass on a fused blockout, as the guide’s limits section describes, is also untested in this repo.
- Starting from a ready-made base mesh (Sketchfab / similar) was not tried for this mascot.

Until one of those paths is actually run and judged against the reference, it remains an experiment, not a verified result.
