# Blender 5.0.1 + OptiX-ready CUDA runtime for Runpod GPU pods.
# Built and published by .github/workflows/blender-image.yml
#   ghcr.io/justinwlin/blender-runpod:5.0.1
#   ghcr.io/justinwlin/blender-runpod:latest
FROM nvidia/cuda:12.4.1-runtime-ubuntu22.04

ARG BLENDER_VERSION=5.0.1
ARG BLENDER_SHA256=8019580ee1b7262e505f4196a00237ccf743c88d205b38d34201510676e60b09
# Pinned addon from https://github.com/ahujasid/blender-mcp (MCP for Blender)
ARG BLENDER_MCP_SHA=2e4b0bc294694b1570d76ed01be657c22e6d02a0

ENV DEBIAN_FRONTEND=noninteractive \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    BLENDER_VERSION=${BLENDER_VERSION} \
    NVIDIA_VISIBLE_DEVICES=all \
    NVIDIA_DRIVER_CAPABILITIES=compute,utility,graphics \
    START_JUPYTER=1 \
    START_BLENDER_MCP=1 \
    BLENDER_MCP_PORT=9876 \
    JUPYTER_PORT=8888 \
    PREVIEW_PORT=8080

RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates curl wget xz-utils git \
        openssh-server \
        python3 python3-pip python3-venv \
        ffmpeg \
        xvfb xauth \
        libxrender1 libxi6 libxkbcommon0 libxkbcommon-x11-0 xkb-data \
        libsm6 libice6 libxext6 libxxf86vm1 libxfixes3 \
        libgl1 libegl1 libgl1-mesa-dri libglx-mesa0 \
        libdbus-1-3 libx11-6 libxcb1 libxau6 libxdmcp6 libbsd0 \
        x11-common \
    && rm -rf /var/lib/apt/lists/* \
    && mkdir -p /var/run/sshd /root/.ssh /workspace /opt/blender \
    && chmod 700 /root/.ssh \
    && sed -i 's/#\?PermitRootLogin.*/PermitRootLogin prohibit-password/' /etc/ssh/sshd_config \
    && sed -i 's/#\?PasswordAuthentication.*/PasswordAuthentication no/' /etc/ssh/sshd_config \
    && sed -i 's/#\?PubkeyAuthentication.*/PubkeyAuthentication yes/' /etc/ssh/sshd_config

# Optional JupyterLab for the 8888/http port. Kept as a separate layer so a
# failed pip does not force a Blender re-download.
RUN pip3 install --no-cache-dir 'jupyterlab>=4,<5'

# Official Blender tarball; the SHA-256 is verified before extract.
RUN cd /opt/blender \
    && curl --fail --location --retry 3 --output blender.tar.xz \
         "https://download.blender.org/release/Blender${BLENDER_VERSION%.*}/blender-${BLENDER_VERSION}-linux-x64.tar.xz" \
    && echo "${BLENDER_SHA256}  blender.tar.xz" | sha256sum --check - \
    && tar -xf blender.tar.xz \
    && rm blender.tar.xz \
    && ln -sfn "/opt/blender/blender-${BLENDER_VERSION}-linux-x64/blender" /usr/local/bin/blender \
    && blender --version

# Blender's bundled CPython needs `requests` for the MCP addon.
# Path is 5.0/python for the 5.0.x series.
RUN BLENDER_PY=$(find /opt/blender/blender-${BLENDER_VERSION}-linux-x64 -path '*/python/bin/python3*' -type f | head -n1) \
    && test -n "$BLENDER_PY" \
    && "$BLENDER_PY" -m ensurepip --upgrade \
    && "$BLENDER_PY" -m pip install --no-cache-dir requests

# Official addon, installed under Blender's real bundled addons path
# (5.0/scripts/addons). A naive `find -name scripts` can hit CPython's
# venv/scripts first, which Blender will not load. Blender 5 also ships
# addons_core but not an empty scripts/addons directory, so create it.
# Major.minor dir for 5.0.1 is 5.0.
RUN ADDONS="/opt/blender/blender-${BLENDER_VERSION}-linux-x64/${BLENDER_VERSION%.*}/scripts/addons" \
    && mkdir -p "$ADDONS" \
    && curl --fail --location --retry 3 --output "$ADDONS/blender_mcp.py" \
         "https://raw.githubusercontent.com/ahujasid/blender-mcp/${BLENDER_MCP_SHA}/addon.py" \
    && test -s "$ADDONS/blender_mcp.py"

COPY start_mcp.py /opt/blender/start_mcp.py
COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod 755 /usr/local/bin/entrypoint.sh /opt/blender/start_mcp.py

WORKDIR /workspace
EXPOSE 22 8888 9876 8080 8188 6006
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
