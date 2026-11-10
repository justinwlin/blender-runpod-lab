# Blender Runpod Lab

A private experiment for a repeatable Blender GPU render skill.

The first scene uses a porcelain plinth, an orange torus, a teal sphere, and a gold cube.
It needs no external textures or paid assets.

## First verified result

![First Light: a GPU-rendered studio scene](results/first-light.png)

Rendered on Runpod in EU-RO-1 with one RTX PRO 4000 Blackwell.
Blender 5.0.1 used Cycles and OptiX at 1600 × 1000.
The render call took 10.569 seconds. The temporary pod was then deleted.
The estimated compute cost was $0.0385, plus storage. This estimate is not an invoice.

The RTX 4090 was unavailable. RTX 5090 allocation attempts failed despite LOW catalog availability.
This result verifies the workflow on the fallback GPU, not 4090 or 5090 performance.

Download the [editable scene](results/first-light.blend) or inspect the [render metadata](results/render-metadata.json).

## Run the scene

Use a Linux Runpod GPU pod with NVIDIA graphics driver access.
Upload `scripts/` with SSH or SCP.

```sh
bash scripts/setup_blender.sh
blender -b --python scripts/render_demo.py -- --output results
```

The script saves a PNG, the Blender scene, and render metadata.
It fails if Blender cannot find an OptiX GPU. It does not silently render on the CPU.

## Project notes

- [Reference film notes](docs/reference-film.md)
- [Experiment record](docs/experiment.md)
- [Skill draft](SKILL.md)

Never commit API keys, SSH private keys, or raw account responses.
The `.local/` directory holds local connection files and is ignored by Git.
