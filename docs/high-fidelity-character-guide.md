# Notes: How to Create a Better, High-Fidelity 3D Model

Source: an article shared on 2026-11-10 by a collaborator's agent, titled "How to Create a Better, High-Fidelity 3D Model" (a practical guide to prompting an AI agent for Blender characters).
Full guide: [sophie-zxy/high-fidelity-3d-model](https://github.com/sophie-zxy/high-fidelity-3d-model) (README, commit f896171). It has sections on what makes a character cute, the four classic mistakes (eyes, whiskers, tail, whole body), fur and colour, rigging with Rigify, driving the agent, base meshes, a copy-paste agent prompt (section 9), honest limits, and a done checklist (section 11). Read it there; this file only summarizes it.
These are claims from the article, not results measured in this repository.

## Core rule

Do not build a character by stacking primitives such as spheres and cones. Stacked primitives leave visible seams and perfect circles in the silhouette. Fuse the parts into one continuous mesh instead.

## Five-stage pipeline (gate after each stage)

1. **Blockout.** Build one low-poly base mesh. Use a Mirror modifier before Subdivision Surface. Check proportions against front and side references.
2. **Fuse.** Merge the parts into one skin with a voxel remesh or metaballs.
3. **Sculpt.** Use three passes: big forms, then anatomy, then detail.
4. **Retopologise.** Rebuild the mesh as clean quads if the character will animate.
5. **Script it.** Drive every step from a versioned Python script. The agent re-renders and inspects the result after each step.

## Review gate

After each stage, render a contact sheet with front, side, top and three-quarter views. Judge the silhouette before adding detail. Never call a grey blockout "finished."

## How this repo applies it

The cat persona v2 rebuild on the `cat-persona` branch follows this pipeline. v1 was assembled from primitives and was rejected because of that. Contact sheets for each stage go in `results/cat-persona/v2/stage-N/`.

## Key extras from the full guide

- Eyes: five eye-widths across the face. Sink the eyes into sockets so only an almond shape shows, overlap them with eyelids, flatten them front to back, and build them in layers.
- Tail and whiskers: use tapered Bezier curves with per-point radius, never uniform cylinders. Rig the tail with a 5-8 bone Spline IK chain.
- Silhouette is species: if the side view is longer than it is tall for a short, round character, fix the blockout first.
- Fur: start with no strands (sheen plus painted variation), then shell tufts, and use Hair Curves only if needed.
- Limits: fine sculpting can't be reliably scripted headless, so budget for a human sculpt pass or start from a clean base mesh.
- Done means the script reruns from scratch, the mesh is one fused body, the four-view contact sheet is clean, and the .glb passes a fresh-import check.
