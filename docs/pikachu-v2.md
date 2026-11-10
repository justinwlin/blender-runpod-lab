# Sleeping Pikachu v2

Version 2 replaces the rejected prototype in `results/pikachu/`. The old result stays for comparison.
Script: `scripts/pikachu_v2.py`. Result: `results/pikachu-v2/`.
See `comparison-v1-v2.png` for the two posters side by side.

## What changed

1. Body: one connected mesh made from blended metaballs (head, cheek puffs, body, rump, paws, feet). The parts no longer look like separate ellipsoids.
2. Proportions: a large round head, a short body, and a smaller ball, close to the reference.
3. Ears: lofted, slightly cupped, drooping ears with ink tips on a clean ring boundary.
4. Tail: a rounded zig-zag bolt from a beveled curve, turned toward the camera.
5. Face: closed smile eyes, cheeks, nose, and mouth are ray-cast onto the head surface, so they sit on the skin.
6. Sleep bubble: a teardrop whose tip touches the nose, with a glint.
7. Look: saturated yellow and red with the Khronos PBR Neutral view transform, a warm cream cyclorama, and toy confetti from the reference.
8. Rig: an armature with root, body, head, two ears, tail, and bubble bones. The body is skinned with smooth weights. The paws stay planted.

## Motion

The loop is 108 frames at 24 fps (4.5 s), the same period as the reference GIF.

1. The ball rocks forward and back with soft holds, and rolls without slipping on the floor.
2. Pikachu rides the top of the ball and leans with it.
3. The ears and tail follow late, with drag from the swing speed. The near ear twitches once per loop.
4. The body breathes. The head sinks on the exhale.
5. The bubble swells on the exhale and shrinks on the inhale, with a small wobble.

All motion uses periodic functions of the loop phase. Frame 109 equals frame 1, and the GLB check measured a loop error of 0.0.

## Outputs

| File | Content |
| --- | --- |
| `pikachu-v2-loop.mp4` | 1440 × 1080, 108 frames, 4.5 s, seamless loop |
| `pikachu-v2-4x.mp4` | The same loop, 4 times (18 s) |
| `pikachu-v2.gif` | 720 px loop preview |
| `pikachu-v2.glb` | Skinned, animated model (1 skin, 1 animation, 4.5 s) |
| `pikachu-v2.blend` | Editable scene with rig, materials, lights, and camera |
| `poster.png`, `contact-sheet.png` | Stills |

## Runpod record

1. All previews, the final render, the GLB export, and the encode ran on pod `an1hrtsf94ybhg`.
2. GPU: RTX PRO 6000 Blackwell Server Edition, SECURE, EUR-IS-2, $2.49/hour. The first create request succeeded.
3. Final render: Cycles OptiX, 128 samples with denoise, 508 s for 108 frames.
4. Allocation time was about 24 minutes, approximately $1.00 plus storage.
5. The local tarball SHA-256 matched the remote value. All per-file checksums passed.
6. The pod was deleted. A follow-up GET returned 404.

## Repeat on a pod

```sh
bash scripts/setup_blender.sh
bash scripts/render_pikachu_v2_remote.sh
```

Quick preview: `blender -b --python-exit-code 1 --python scripts/pikachu_v2.py -- --output previews/p --percent 50 --samples 32 --frames 1,28,55,82 --no-export`.
