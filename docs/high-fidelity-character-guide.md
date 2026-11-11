# Notes: How to Create a Better, High-Fidelity 3D Model

Source: an article shared on 2026-11-10 by a collaborator's agent, titled "How to Create a Better, High-Fidelity 3D Model" (a practical guide to prompting an AI agent for Blender characters).
Status: **partial notes.** The copy received was cut off in section 2, so the later sections (what makes a character cute, four classic mistakes, fur and colour, starting from a base mesh, the copy-paste agent prompt in section 9, honest limits, and the done checklist) are not captured yet.
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
