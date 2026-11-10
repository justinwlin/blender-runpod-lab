# Blender Runpod Lab

A private experiment for a repeatable Blender GPU render skill.

The first scene uses a porcelain plinth, an orange torus, a teal sphere, and a gold cube.
It needs no external textures or paid assets.

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
