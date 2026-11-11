---
name: blender-runpod-lab
description: Render Blender scenes on Runpod GPUs, return visible image or animation results, and record device, timing, and cleanup evidence. Use for remote Blender render experiments and small render-farm jobs.
---

# Blender on Runpod

Use this repository as a small render experiment before a larger farm run.
Read [the experiment record](docs/experiment.md) for verified results and known limits.
Read [the film reference](docs/reference-film.md) only when the user asks about frame distribution or the original example.

## Access and cost

Check the connected Runpod tools and local CLI separately. MCP access does not imply a valid local API key.
Use MCP for infrastructure when it works. Direct SSH and SCP can use a task-specific SSH key without CLI API access.
Inject the public key through PUBLIC_KEY at creation. Wait for direct SSH details after the container starts.
The SSH proxy may reject a key that is only configured inside the pod. Account keys need not change for direct SSH.
Keep private keys and connection state in `.local/`. Never commit credentials or raw account responses.

Read the live GPU catalog and state the selected hourly rate before pod creation.
Check GPU count, cloud tier, CUDA version, and data center together.
Respect the user's GPU choice and budget. A LOW catalog result does not reserve a GPU.
Treat a capacity error as a failed allocation. Do not repeat the same request without new capacity evidence.
Ask before replacing an explicitly required GPU family unless the user already authorized alternatives.
If the user permits a higher price, check larger RTX GPUs and all compatible regions before declaring capacity blocked.
A failed allocation for one GPU does not establish that Runpod has no capacity.
If the user requires Runpod, keep every render and video encode on Runpod. Do not use a local fallback.

Record the ID of every pod created for the task. Delete only those pods, after verified output retrieval.
Use a platform termination schedule when available. Do not claim that a shell timeout limits pod billing.
If automatic termination is unavailable, state that limit and keep an explicit cleanup step.

## Small render

1. Prefer a maintained Blender image when one fits the required version and GPU.
2. Otherwise use a known Linux base with NVIDIA driver libraries exposed to the container.
3. Upload `scripts/` through SSH or SCP.
4. Run `bash scripts/setup_blender.sh` to install the pinned Blender binary and verify its checksum.
5. Run `blender -b --python scripts/render_demo.py -- --output results`.
6. Download the PNG, `.blend` file, metadata, and relevant logs.
7. Inspect the image. Check that metadata lists an enabled OptiX GPU and a complete render.
8. Delete the task pod. Confirm that it is absent or returns 404.

The demo script refuses a silent CPU fallback. A started pod or a successful package install is not a render result.
Use the same Blender release and add-on versions as an existing user scene.
Copy linked assets and baked simulation caches as well as the `.blend` file.

## Short animation

Use `scripts/penguin_animation.py` as a self-contained example.
Inspect selected local previews before a full render.
The default backend is OptiX. `--metal` explicitly selects the Apple GPU; `--cpu` explicitly selects the CPU.
Report a local fallback clearly. Do not label local frames as a cloud GPU result.
Use `scripts/encode_animation.py SOURCE DESTINATION.mp4` to check and encode the complete sequence.
Read [the animation record](docs/penguin-animation.md) for the verified workflow.

## Multiple GPUs

One process can use multiple supported GPUs for one frame. Separate workers can render different frames from one scene.
For independent workers, use a shared frame manifest with no duplicates or gaps.
Interleaved assignment is `frames[worker_index::worker_count]`; contiguous ranges are also valid.
Bake stateful simulations first. Keep assets, seeds, camera cuts, output settings, and color transforms identical.
Verify frame completeness before video assembly. Benchmark one representative frame before renting a fleet.

## Report

Return the visible result, source scene, GPU model, Blender version, backend, resolution, and measured render time.
Use nvidia-smi for GPU memory. Do not assume the control API's gpu.memory field reports VRAM.
Separate setup duration, render duration, billed duration, and estimated cost.
State whether cleanup succeeded. If no render ran, report that fact and the actual blocker.

## High-fidelity character pipeline

Follow the staged, contact-sheet workflow in [Sophie's high-fidelity 3D model guide](https://github.com/sophie-zxy/high-fidelity-3d-model), adapted to the supplied species and pose. Use one mirrored Skin cage, subdivided cube or traced silhouette; fuse one continuous skin; sculpt primary, secondary and tertiary forms; retopologize to clean quads before adding the dressed/material look. Judge front, side, top and three-quarter silhouettes at every gate, write a short critique, and correct defects before proceeding. Never label a gray blockout finished.

Keep mascot proportions in named parameters with assertions. Flatten and socket layered eyes behind overlapping lids, use tapered Bezier tails/whiskers, and keep paw grooves in the fused skin. `scripts/contact_sheet.py` renders reusable views from any saved Blender scene or named object's bounds; ordinary Python with Pillow assembles the images alongside a concept reference. Export GLB and validate it through a factory-startup fresh import. State where human sculpting, intentional facial loops and deformation testing are still needed. User-provided host, budget, preview-only and infrastructure restrictions override the generic remote-render workflow above.
