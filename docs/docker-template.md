# Blender 5.0.1 Runpod image and template

A reusable GPU pod image that already has Blender, the X/GL libraries it needs, SSH, JupyterLab, and the open-source [MCP for Blender](https://github.com/ahujasid/blender-mcp) addon. The goal is to skip the first-boot `apt` / Blender-download stall that blocked earlier previews.

This is the **default way to run Blender on Runpod** for this repo. It is infrastructure for experiments, not a verified production render farm.

## Image

| Tag | Purpose |
| --- | --- |
| `ghcr.io/justinwlin/blender-runpod:5.0.1` | Pinned release, prefer this |
| `ghcr.io/justinwlin/blender-runpod:latest` | Same build, moving tag |

**Digest (MCP path + X11 fixes baked in):** `sha256:295342ad1a991c83c9b2814e1d2de9851a8897849cfda64769c4189d465b9304`

The package must stay **public** so Runpod can pull it without a registry credential. Anonymous pulls of `:5.0.1` and `:latest` have been verified against that digest.

**Base:** `nvidia/cuda:12.4.1-runtime-ubuntu22.04`

**Blender:** official `5.0.1` linux-x64 tarball. The build verifies SHA-256 `8019580ee1b7262e505f4196a00237ccf743c88d205b38d34201510676e60b09` before extract and fails if it does not match.

**MCP addon:** `addon.py` from `ahujasid/blender-mcp` at commit `2e4b0bc294694b1570d76ed01be657c22e6d02a0`, installed as `blender_mcp.py` in Blender's real bundled addons path (`5.0/scripts/addons`).

**Also installed:** `libxrender1`, `libxi6`, `libxkbcommon0`, `libsm6`, `libice6`, `libxext6`, `libxxf86vm1`, `libxfixes3`, `libgl1`, `libegl1`, `libdbus-1-3` and their dependencies, plus `openssh-server`, `python3`, `ffmpeg`, `git`, `xvfb`, and `jupyterlab`.

Sources live in [`docker/blender/`](../docker/blender/).

## How the image is built

There is no Docker daemon on the usual agent box, so images are built by GitHub Actions and pushed to GHCR.

- Workflow: [`.github/workflows/blender-image.yml`](../.github/workflows/blender-image.yml)
- Triggers: pushes to `main` or `cat-persona` that touch `docker/blender/**` or the workflow file, and `workflow_dispatch`
- Permissions used: `contents: read`, `packages: write` (the default `GITHUB_TOKEN`)
- After a successful push the workflow tries to set the GHCR package visibility to public, then **confirms an anonymous pull**. The visibility API 404s for this user package with `GITHUB_TOKEN`; that must not fail the job. Packages linked to this public repo are already public.

**Measured build time:** about **6 minutes** on GitHub-hosted `ubuntu-latest` (first successful push). Later rebuilds can be faster when Buildx cache hits.

To rebuild by hand once a machine has Docker:

```sh
docker build -t ghcr.io/justinwlin/blender-runpod:5.0.1 docker/blender
```

## Faster rebuilds with Depot

Depot is the faster rebuild path when you need to iterate on the Dockerfile. It is **not** how the current published image was built.

1. Install the official CLI to `~/.local/bin`: `curl -fsSL https://depot.dev/install-cli.sh | DEPOT_INSTALL_DIR="$HOME/.local/bin" sh`
2. Authenticate with an org-authorized `DEPOT_TOKEN` (or `depot login`).
3. `depot projects list`, or `depot projects create` a project named `blender-runpod`, then `depot init` so this repo has a `depot.json` with that project's id (the id is not a secret).
4. Log in to GHCR (`echo "$GH_TOKEN" | docker login ghcr.io -u USERNAME --password-stdin`; the token needs `write:packages`).
5. From the repo root:

```sh
depot build --platform linux/amd64 --push \
  -t ghcr.io/justinwlin/blender-runpod:5.0.1 \
  -t ghcr.io/justinwlin/blender-runpod:latest \
  docker/blender
```

A `depot.json` is not in the repo yet. A `DEPOT_TOKEN` present on the agent box was not authorized to list or create Depot projects (`permission_denied: Not authorized` even when passed with `depot projects list --token`). What is needed: an org-authorized Depot token or a `depot login` that can create a project named `blender-runpod`, then `depot init`.

## Entrypoint

[`docker/blender/entrypoint.sh`](../docker/blender/entrypoint.sh) starts, in order:

1. **sshd** on port 22. If `PUBLIC_KEY` is set (Runpod does this when the template has `startSsh`), it is appended to `/root/.ssh/authorized_keys`. Host keys are generated on first boot.
2. **JupyterLab** on 8888, unless `START_JUPYTER=0`. The token is `JUPYTER_TOKEN` or, if that is empty, Runpod's injected `JUPYTER_PASSWORD`.
3. A simple **`python3 -m http.server`** of `/workspace` on 8080, unless `START_PREVIEW=0`.
4. **Blender MCP** on 9876, unless `START_BLENDER_MCP=0`.

The official addon [refuses to start under `blender -b`](https://github.com/ahujasid/blender-mcp): it needs Blender's GUI timer thread to run commands. The entrypoint therefore launches `xvfb-run blender --python /opt/blender/start_mcp.py` (a virtual display, not background mode), forces X11 (`XDG_RUNTIME_DIR`, `XDG_SESSION_TYPE=x11`, `GDK_BACKEND=x11`, `WAYLAND_DISPLAY` unset), and binds `0.0.0.0:9876` with remote connections allowed.

The addon itself has **no authentication**, so treat 9876 as a trusted-network port. Prefer an **SSH tunnel** rather than publishing 9876 to the public internet:

```sh
ssh -N -L 9876:127.0.0.1:9876 <pod-ssh-host>
```

Then point the MCP client at `localhost:9876`.

`blender` on `PATH` is still the headless CLI: `blender -b --python your_script.py` is the right way to batch-render (Cycles / OptiX). That is a separate process from the MCP server.

PID 1 then `sleep infinity` so the container stays up if a helper exits. Logs: `/var/log/jupyter.log`, `/var/log/preview-http.log`, `/var/log/blender-mcp.log`.

## Port map

These ports are opened by default on the personal-account Runpod template `blender-5.0.1`.

| Port | Protocol (Runpod) | Service |
| --- | --- | --- |
| 22 | `tcp` | SSH (`sshd`, key-only, `PUBLIC_KEY`) |
| 8888 | `http` | JupyterLab |
| 9876 | `tcp` | Blender MCP socket (JSON, official addon; no auth — use an SSH tunnel) |
| 8080 | `http` | `/workspace` static file preview |
| 8188 | `http` | Spare (not started by the entrypoint) |
| 6006 | `http` | Spare (not started by the entrypoint) |

9876 is a raw TCP socket, not an HTTP service, so the template publishes it as `9876/tcp`.

## Runpod template

A **private** pod template on the **personal** Runpod account — not the work account — is named `blender-5.0.1`:

- Image: `ghcr.io/justinwlin/blender-runpod:5.0.1`
- Ports: `22/tcp,8888/http,9876/tcp,8080/http,8188/http,6006/http`
- `startSsh`: true (injects `PUBLIC_KEY`)
- Container disk: 50 GB (the image is a CUDA runtime plus a full Blender tree)
- The template itself is not marked public (it is only on the personal account)

### How to launch a pod from it

In the personal Runpod console, create a GPU pod from template `blender-5.0.1`, or via the GraphQL API with `templateId` set to that template and a GPU type such as `NVIDIA L40S` or `NVIDIA GeForce RTX 4090`. Pass `startSsh: true` and a `PUBLIC_KEY` if the template injection is not enough. After SSH is up:

```sh
# Blender + OptiX
blender --version
blender -b --python-expr "import bpy; p=bpy.context.preferences.addons['cycles'].preferences; p.compute_device_type='OPTIX'; p.refresh_devices(); print([(d.name,d.type) for d in p.devices])"

# MCP socket (give Xvfb / the addon a few seconds after boot). Prefer this
# over a public 9876, via an SSH tunnel to localhost.
python3 - <<'PY'
import json, socket
s = socket.create_connection(('127.0.0.1', 9876), timeout=5)
s.sendall(json.dumps({'type':'ping'}).encode())
print(s.recv(4096).decode())
PY
```

A successful ping returns a JSON object with `"pong": true`.

## Measured timings and GPU prices

Verified on the personal account, 10 Nov 2026 (evening, America/New_York):

| Measurement | Result |
| --- | --- |
| GitHub Actions image build and GHCR push | about **6 minutes** |
| Pod launch from this template to SSH ready | about **72 seconds** |
| Blender CLI + OptiX after SSH | immediate (baked into the image) |
| L40S Cycles OptiX preview, 32 samples, 1080px hero + 720px 4-view | about **34 seconds** wall |

Hourly prices seen on that account (on-demand, not a quote):

| GPU | Price seen |
| --- | --- |
| NVIDIA GeForce RTX 4090 (secure) | **$0.89/hr** |
| NVIDIA L40S (secure) | **$1.09/hr** |

Community-cloud 4090 and L40S were sometimes listed cheaper but were not actually available when requested.

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

## Gotchas

- **Bake the X/GL libraries into the image.** Bare CUDA / pytorch Runpod images often lack `libxrender1`, `libxi6`, `libxkbcommon0`, `libsm6`, `libice6`, and friends. On a live pod, `apt-get update` against HTTP Ubuntu mirrors can hang for many minutes, so installing those libs at boot is a poor plan.
- **The Blender 5.0.1 tarball has no `scripts/addons` directory.** It ships `addons_core`. The image must `mkdir` `5.0/scripts/addons` before installing the MCP addon.
- **A naive `find -name scripts` hits CPython's `venv/scripts` first.** The addon landed there on the first bake, and Blender never loaded it (`No module named 'blender_mcp'`). Install explicitly into `/opt/blender/blender-5.0.1-linux-x64/5.0/scripts/addons`.
- **The official blender-mcp addon refuses `blender -b`.** Commands need Blender's GUI timer thread. Start it as `xvfb-run blender --python /opt/blender/start_mcp.py`. Also set `XDG_RUNTIME_DIR`, force X11 (`XDG_SESSION_TYPE=x11`, `GDK_BACKEND=x11`), and unset `WAYLAND_DISPLAY` — otherwise Blender 5 tries Wayland and exits with `XDG_RUNTIME_DIR not set`.
- **The GHCR visibility API 404s** with `GITHUB_TOKEN` on `PUT /user/packages/container/blender-runpod/visibility`. Packages linked to this public repo are already public; confirm with an anonymous GHCR pull rather than treating the 404 as a failed publish.
- **MCP has no auth.** Keep 9876 off the public internet and use an SSH tunnel.

## Character previews

Batch character scripts still run with `blender -b --python …` on a pod from this template. Earlier scripted cat attempts (v1, v2, vinyl-v1) are recorded on the `cat-persona` branch and summarized in [Lessons: character modeling](lessons-character-modeling.md). They are not on `main` and are not a verified look.
