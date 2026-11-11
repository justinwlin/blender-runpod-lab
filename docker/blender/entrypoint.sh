#!/bin/bash
# Start sshd (Runpod PUBLIC_KEY), optional Jupyter, the Blender MCP socket
# under Xvfb, and a simple /workspace file server on 8080. Then stay up.
set -euo pipefail

mkdir -p /root/.ssh /var/run/sshd /workspace
chmod 700 /root/.ssh

if [ -n "${PUBLIC_KEY:-}" ]; then
  # Runpod injects the account's registered keys (and any env PUBLIC_KEY)
  # when startSsh is set on the template. We also honour the env var so
  # the image works without that injection.
  if ! grep -qxF "$PUBLIC_KEY" /root/.ssh/authorized_keys 2>/dev/null; then
    printf '%s\n' "$PUBLIC_KEY" >> /root/.ssh/authorized_keys
  fi
  chmod 600 /root/.ssh/authorized_keys
fi

# Host keys are generated at first boot so they are unique per pod.
if [ ! -f /etc/ssh/ssh_host_ed25519_key ]; then
  ssh-keygen -A
fi
/usr/sbin/sshd

if [ "${START_JUPYTER:-1}" = "1" ]; then
  JUPYTER_PORT="${JUPYTER_PORT:-8888}"
  # Runpod startJupyter injects JUPYTER_PASSWORD; accept JUPYTER_TOKEN too.
  TOKEN="${JUPYTER_TOKEN:-${JUPYTER_PASSWORD:-}}"
  nohup jupyter lab \
    --ip=0.0.0.0 \
    --port="$JUPYTER_PORT" \
    --no-browser \
    --allow-root \
    --ServerApp.token="${TOKEN}" \
    --ServerApp.password='' \
    --ServerApp.root_dir=/workspace \
    --ServerApp.allow_origin='*' \
    >/var/log/jupyter.log 2>&1 &
  echo "JupyterLab listening on ${JUPYTER_PORT}"
fi

if [ "${START_PREVIEW:-1}" = "1" ]; then
  PREVIEW_PORT="${PREVIEW_PORT:-8080}"
  nohup python3 -m http.server "$PREVIEW_PORT" --bind 0.0.0.0 --directory /workspace \
    >/var/log/preview-http.log 2>&1 &
  echo "Workspace file server listening on ${PREVIEW_PORT}"
fi

if [ "${START_BLENDER_MCP:-1}" = "1" ]; then
  # The official addon refuses blender -b (no main-thread timers).
  # A virtual display lets the socket server start and stay up.
  # Force X11: Blender 5 otherwise tries Wayland and exits if
  # XDG_RUNTIME_DIR is unset.
  mkdir -p /tmp/runtime-root
  chmod 700 /tmp/runtime-root
  export XDG_RUNTIME_DIR=/tmp/runtime-root
  export XDG_SESSION_TYPE=x11
  export GDK_BACKEND=x11
  unset WAYLAND_DISPLAY || true
  nohup xvfb-run --auto-servernum --server-args='-screen 0 1280x720x24' \
    env XDG_RUNTIME_DIR=/tmp/runtime-root XDG_SESSION_TYPE=x11 GDK_BACKEND=x11 \
    blender --python /opt/blender/start_mcp.py \
    >/var/log/blender-mcp.log 2>&1 &
  echo "Blender MCP starting on ${BLENDER_MCP_PORT:-9876} (see /var/log/blender-mcp.log)"
fi

echo "blender-runpod ready"
# Keep PID 1 alive even if a helper exits.
exec sleep infinity
