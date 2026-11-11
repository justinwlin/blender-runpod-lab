# Blender 5.0.1 Runpod image and template

A reusable GPU pod image that already has Blender, the X/GL libraries it needs, SSH, JupyterLab, and the open-source [MCP for Blender](https://github.com/ahujasid/blender-mcp) addon. The goal is to skip the first-boot `apt` / Blender-download stall that blocked earlier cat-persona previews.

This is infrastructure for experiments (including the vinyl-toy cat preview). It is not a verified production render farm.

## Image

| Tag | Purpose |
| --- | --- |
| `ghcr.io/justinwlin/blender-runpod:5.0.1` | Pinned release, prefer this |
| `ghcr.io/justinwlin/blender-runpod:latest` | Same build, moving tag |

The package must be **public** so Runpod can pull it without a registry credential.

**Base:** `nvidia/cuda:12.4.1-runtime-ubuntu22.04`

**Blender:** official `5.0.1` linux-x64 tarball. The build verifies SHA-256 `8019580ee1b7262e505f4196a00237ccf743c88d205b38d34201510676e60b09` before extract and fails if it does not match.

**MCP addon:** `addon.py` from `ahujasid/blender-mcp` at commit `2e4b0bc294694b1570d76ed01be657c22e6d02a0`, installed as `blender_mcp.py` in Blender's bundled addons path.

**Also installed:** `libxrender1`, `libxi6`, `libxkbcommon0`, `libsm6`, `libice6`, `libxext6`, `libxxf86vm1`, `libxfixes3`, `libgl1`, `libegl1`, `libdbus-1-3` and their dependencies, plus `openssh-server`, `python3`, `ffmpeg`, `git`, `xvfb`, and `jupyterlab`.

Sources live in [`docker/blender/`](../docker/blender/).

## How the image is built

There is no Docker daemon on the usual agent box, so images are built by GitHub Actions and pushed to GHCR.

- Workflow: [`.github/workflows/blender-image.yml`](../.github/workflows/blender-image.yml)
- Triggers: pushes to `main` or `cat-persona` that touch `docker/blender/**` or the workflow file, and `workflow_dispatch`
- Permissions used: `contents: read`, `packages: write` (the default `GITHUB_TOKEN`)
- After a successful push the workflow tries to set the GHCR package visibility to **public**. If that step fails, stop and change visibility in the GitHub Packages settings for `blender-runpod`; do not publish the same image to another registry as a workaround.

To rebuild by hand once a machine has Docker:

```sh
docker build -t ghcr.io/justinwlin/blender-runpod:5.0.1 docker/blender
```

## Entrypoint

[`docker/blender/entrypoint.sh`](../docker/blender/entrypoint.sh) starts, in order:

1. **sshd** on port 22. If `PUBLIC_KEY` is set (Runpod does this when the template has `startSsh`), it is appended to `/root/.ssh/authorized_keys`. Host keys are generated on first boot.
2. **JupyterLab** on 8888, unless `START_JUPYTER=0`. The token is `JUPYTER_TOKEN` or, if that is empty, Runpod's injected `JUPYTER_PASSWORD`.
3. A simple **`python3 -m http.server`** of `/workspace` on 8080, unless `START_PREVIEW=0`.
4. **Blender MCP** on 9876, unless `START_BLENDER_MCP=0`.

The official addon [refuses to start under `blender -b`](https://github.com/ahujasid/blender-mcp): it needs Blender's GUI timer thread to run commands. The entrypoint therefore launches `xvfb-run blender --python /opt/blender/start_mcp.py` (a virtual display, not background mode) and binds `0.0.0.0:9876` with remote connections allowed. The addon itself has no authentication, so treat 9876 as a trusted-network port and prefer an SSH tunnel when you are not on the pod.

`blender` on `PATH` is still the headless CLI: `blender -b --python your_script.py` is the right way to batch-render (Cycles / OptiX). That is a separate process from the MCP server.

PID 1 then `sleep infinity` so the container stays up if a helper exits. Logs: `/var/log/jupyter.log`, `/var/log/preview-http.log`, `/var/log/blender-mcp.log`.

## Port map

These ports are opened by default on the personal-account Runpod template `blender-5.0.1`.

| Port | Protocol (Runpod) | Service |
| --- | --- | --- |
| 22 | `tcp` | SSH (`sshd`, key-only, `PUBLIC_KEY`) |
| 8888 | `http` | JupyterLab |
| 9876 | `tcp` | Blender MCP socket (JSON, official addon) |
| 8080 | `http` | `/workspace` static file preview |
| 8188 | `http` | Spare (not started by the entrypoint) |
| 6006 | `http` | Spare (not started by the entrypoint) |

9876 is a raw TCP socket, not an HTTP service, so the template publishes it as `9876/tcp`.

## Runpod template

Create (or reuse) a **private** pod template on the personal Runpod account — not the work account — named `blender-5.0.1`:

- Image: `ghcr.io/justinwlin/blender-runpod:5.0.1`
- Ports: `22/tcp,8888/http,9876/tcp,8080/http,8188/http,6006/http`
- `startSsh`: true (injects `PUBLIC_KEY`)
- Container disk: 50 GB (the image is a CUDA runtime plus a full Blender tree)
- Do not mark the template public unless you intend every Runpod user to see it

Launch a GPU pod from that template. After SSH is up:

```sh
# Blender + OptiX
blender --version
blender -b --python-expr "import bpy; p=bpy.context.preferences.addons['cycles'].preferences; p.compute_device_type='OPTIX'; p.refresh_devices(); print([(d.name,d.type) for d in p.devices])"

# MCP socket (give Xvfb / addon a few seconds after boot)
python3 - <<'PY'
import json, socket
s = socket.create_connection(('127.0.0.1', 9876), timeout=5)
s.sendall(json.dumps({'type':'ping'}).encode())
print(s.recv(4096).decode())
PY
```

A successful ping returns a JSON object with `"pong": true`.

## Environment variables

| Variable | Default | Meaning |
| --- | --- | --- |
| `PUBLIC_KEY` | (unset) | SSH public key appended at boot |
| `START_JUPYTER` | `1` | Set `0` to skip JupyterLab |
| `START_BLENDER_MCP` | `1` | Set `0` to skip the MCP blender process |
| `START_PREVIEW` | `1` | Set `0` to skip the 8080 file server |
| `BLENDER_MCP_PORT` | `9876` | Addon listen port |
| `BLENDER_MCP_HOST` | `0.0.0.0` | Addon bind address |
| `JUPYTER_TOKEN` / `JUPYTER_PASSWORD` | empty | Jupyter access token |
| `NVIDIA_DRIVER_CAPABILITIES` | `compute,utility,graphics` | Needed for OptiX |

## Vinyl-cat preview

The first consumer of this image is the simple vinyl-toy cat script, `scripts/build_cat_vinyl.py` (experiment, `vinyl-v1`). On a pod from this template:

```sh
blender -b --factory-startup --python-exit-code 1 \
  --python scripts/build_cat_vinyl.py -- \
  --output results/cat-persona/vinyl-v1 --res 1080 --samples 32 --contact-res 720 --save-blend
```
