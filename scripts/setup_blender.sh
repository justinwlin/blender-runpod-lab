#!/usr/bin/env bash
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive
# Some pod networks stall on HTTP Ubuntu mirrors. Use HTTPS and bounded retries.
if [ -f /etc/apt/sources.list.d/ubuntu.sources ]; then
  sed -i 's|http://archive.ubuntu.com|https://archive.ubuntu.com|g; s|http://security.ubuntu.com|https://security.ubuntu.com|g' /etc/apt/sources.list.d/ubuntu.sources
fi
apt-get -o Acquire::http::Timeout=20 -o Acquire::https::Timeout=20 -o Acquire::Retries=1 update -qq
apt-get install -y --no-install-recommends ca-certificates curl xz-utils libxrender1 libxi6 libxkbcommon0 libsm6 libgl1 libegl1 libxfixes3 libxxf86vm1 libdbus-1-3
mkdir -p /opt/blender
archive=blender-5.0.1-linux-x64.tar.xz
checksum=8019580ee1b7262e505f4196a00237ccf743c88d205b38d34201510676e60b09
if [ ! -x /opt/blender/blender-5.0.1-linux-x64/blender ]; then
  cd /opt/blender
  curl --fail --location --retry 3 --output "$archive" "https://download.blender.org/release/Blender5.0/$archive"
  echo "$checksum  $archive" | sha256sum --check -
  tar -xf "$archive"
  rm "$archive"
fi
ln -sfn /opt/blender/blender-5.0.1-linux-x64/blender /usr/local/bin/blender
blender --version
nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv
