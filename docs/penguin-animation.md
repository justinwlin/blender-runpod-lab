# Pip takes a dip

This five-second animation shows a small penguin with a coral scarf.
Pip walks across an ice floe, loses balance, falls into the sea, and returns with a wink.
The scene uses procedural geometry, materials, lights, and keyed transforms.
The splash uses animated droplets and rings. It does not use a fluid simulation.
No external models, textures, or audio are required. The video is silent.

## Render workflow

1. Generate four preview frames locally with `--preview --frames 24,68,85,113`.
2. Inspect the walk, fall, and final pose.
3. Check live Runpod capacity and quote the hourly rate.
4. Allocate a GPU if capacity permits.
5. Render all 120 frames and check the frame sequence.
6. Encode H.264 video at 24 frames per second.
7. Verify the frame count, duration, and resolution with ffprobe.

For this run, allocation failed for RTX PRO 4000 Blackwell and RTX 5090 in EU-RO-1.
Both requests selected the advertised CUDA 13.2 capacity.
The catalog showed LOW capacity, but neither request created a pod.
This animation therefore used the local Apple M4 Pro GPU through Metal.
There was no Runpod charge for this animation.
The earlier static image remains the verified remote OptiX test.

## Repeat the render

On an Apple Silicon Mac:

```sh
/Applications/Blender.app/Contents/MacOS/Blender -b \
  --python scripts/penguin_animation.py -- --metal --output .local/penguin-final
python3 scripts/encode_animation.py .local/penguin-final results/penguin/pip-takes-a-dip.mp4
```

On a compatible NVIDIA pod, omit `--metal` to require OptiX.
Use `--cpu` only for an explicit CPU render.
Use `--preview` for low-resolution CPU previews.
Each frame has explicit transforms, so separate workers can render independent frames with `--frames`.
The default final resolution is 1280 × 960, with 64 samples and denoise enabled.

The result directory contains the video, poster, editable Blender scene, and measured render metadata.

## Measured result

Blender 5.2.3 LTS rendered 120 frames through METAL in 501.377 seconds.
This duration includes the slow first Metal frame, but excludes scene construction and video encode.
ffprobe confirmed 120 frames, 24 fps, 1280 × 960, and exactly 5.000 seconds.
A contact sheet from the encoded MP4 confirmed the walk, fall, splash, and return to the surface.
