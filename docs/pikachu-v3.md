# Sleeping Pikachu v3

Version 3 answers the feedback on v2: "more like the anime, and less bubble primitive shapes".
Script: `scripts/pikachu_v3.py`. Result: `results/pikachu-v3/`. Compare in `comparison-v2-v3.png`.
The rig, motion, ball, set, lights, and camera are the same as v2.

## What changed

1. The body is one signed-distance-field sculpt, meshed with marching cubes (scikit-image), relaxed, and decimated to 160k faces. Metaballs are gone.
2. The anatomy is closer to the anime: a wide head with lower jowls and a small muzzle, a chest and hips, short tapered arms with paws, thighs, and feet.
3. The ears are part of the same surface, with a smooth fillet into the head. They are flattened, tapered, and slightly curled. The ears are skinned to the ear bones.
4. The cheeks, ink ear tips, and two brown back stripes are painted into a vertex color attribute. The GLB carries this as `COLOR_0`.
5. The tail has a brown base, as in the anime.
6. The belly rests on the ball, and the paws grip its surface.

## Checks

- GLB: 1 skin, 1 animation, 4.5 s, 11 moving channels, loop endpoint error 0.0, vertex colors present.
- Video: 1440 × 1080, 108 frames, 24 fps, 4.5 s.
- All per-file SHA-256 checks passed after download.

## Runpod record

All previews and the final render ran on pod `sffip466p50hwc` (RTX PRO 6000 Blackwell Server Edition, US-NC-2, $2.49/hour).
The final render took 504 s (OptiX, 128 samples). The pod ran about 15 minutes, approximately $0.60.
The pod was deleted, and a follow-up GET returned 404.

## Repeat on a pod

```sh
bash scripts/setup_blender.sh
/opt/blender/blender-5.0.1-linux-x64/5.0/python/bin/python3.11 -m pip install scikit-image
bash scripts/render_pikachu_v3_remote.sh
```
