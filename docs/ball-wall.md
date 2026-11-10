# Ball and wall: Runpod-only animation test

This five-second test shows an orange rubber ball bounce toward a teal wall, compress at contact, and bounce back.
The scene uses keyed analytical motion. It is an animation test, not a rigid-body physics simulation.
The script checks the base sphere's clearance from the wall and floor for all 120 frames.
Decorative stripe geometry is not included in the clearance check.

The user required Runpod for this test and authorized a more expensive GPU.
The live catalog showed LOW capacity for RTX PRO 6000 Blackwell Server Edition across seven regions.
One allocation request used all seven regions. Runpod allocated the GPU in US-NC-1 at $2.49 per hour.
The pod ID was `rxe6nzqe3boze6`.
No local Blender render or video encode was used for this test.
The pod rendered the preview, final frames, MP4, GIF, poster, and contact sheet.

## Setup findings

The Ubuntu HTTP package update stalled on this host.
HTTPS access worked. The setup continued after switching the Ubuntu sources to HTTPS and setting bounded network timeouts.
The first preview found that the empty Blender scene had no world. The script now creates one explicitly.
Use `--python-exit-code 1` so Python errors produce a failed Blender process.

## Repeat

```sh
bash scripts/setup_blender.sh
apt-get install -y ffmpeg
blender -b --python-exit-code 1 --python scripts/ball_wall.py -- --output results/ball
python3 scripts/encode_animation.py results/ball results/ball/ball-wall.mp4
```

The complete remote job is in `scripts/render_ball_remote.sh`. It assumes `/workspace/blender-lab` on the pod.

The scene script requires an OptiX GPU and has no local fallback option.
Render selected frames with `--frames 1,43,60` before the full sequence.
Verify the downloaded artifact checksums before deleting the pod.

## Verified result

Blender 5.0.1 used OptiX on the RTX PRO 6000 Blackwell Server Edition.
The final 120 frames took 340.972 seconds at 1280 × 720.
The MP4 check confirmed exactly five seconds at 24 fps.
All downloaded files matched their remote SHA-256 checksums.
The contact sheet confirmed motion toward the wall and back from it.
The base sphere reached zero clearance at contact and never had negative clearance.

The pod was created at 02:37:54 UTC and deletion was verified at 02:49:06 UTC on 2026-11-10.
Deletion returned 204. A subsequent read returned 404.
Estimated compute cost was $0.4643, plus storage. This estimate is not an invoice.
Setup and preview time are included in this allocation estimate.
