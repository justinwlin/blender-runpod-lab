# Sleeping Pikachu on a Poke Ball

The user supplied a 2D GIF of Pikachu asleep on a Poke Ball.
The reference has 225 frames and lasts 4.5 seconds.
This scene is a new 3D interpretation of that reference, with a soft toy style.
It uses procedural geometry and materials, without external models or textures.

The five-second loop has gentle ball movement, breathing, and a small blue sleep bubble.
The scene has 120 output frames at 24 fps and 1200 × 1200 resolution.
Frame 121 repeats the first pose. The GLB export includes that key for a five-second animation.
The editable Blender scene retains the materials, lights, camera, geometry, and keyframes.
The GLB contains the character and ball with animation, without the studio environment.

## Remote workflow

The user required Runpod for this workflow.
One RTX PRO 6000 Blackwell Server Edition was allocated in EU-RO-1 at $2.49 per hour.
The pod ID was `hq8gpe2xuoh7ht`.
All preview and final renders, model exports, and video encode ran on this pod.
The local computer only prepared scripts, inspected downloaded images, and checked downloaded files.

The first preview exposed an overlap in the tail polygon and raised back stripes.
The corrected preview removed those defects before the full render.
Face curves were converted to meshes so that the GLB preserves the eyes and smile.

## Repeat

```sh
bash scripts/setup_blender.sh
apt-get install -y ffmpeg
blender -b --python-exit-code 1 --python scripts/pikachu_sleep.py -- --frames 1,31 --output preview
bash scripts/render_pikachu_remote.sh
```

The remote script assumes `/workspace/blender-lab` and an installed OptiX-compatible NVIDIA GPU.
The scene script refuses a CPU fallback.

## Model checks

The GLB contains 20 meshes and one combined animation with five transform channels.
Its duration is five seconds. Every animated transform matches at the first and last keys.
The model includes both closed eyes, both ears, the head, and the lightning tail.
Use `scripts/verify_pikachu_glb.py` to repeat these checks.
Blender's scene export initially split motion by object; `export_anim_scene_split_object=False` produced the combined animation.

## Verified result and cleanup

Blender 5.0.1 used OptiX on RTX PRO 6000 Blackwell Server Edition.
The final 120 frames took 394.342 seconds. The MP4 check confirmed five seconds at 24 fps and 1200 × 1200 pixels.
All downloaded output files matched their remote SHA-256 checksums.
The contact sheet confirmed the character, ball, and motion in the encoded video.
The downloaded GLB passed the model and loop checks.

The pod was created at 03:22:10 UTC on 2026-11-10.
Deletion returned 204. A subsequent read returned 404 at 03:33:37 UTC.
Estimated compute cost was $0.4751, plus storage. This is not an invoice.
The allocation estimate includes setup, preview, model export, and download time.
