#!/bin/bash
# Render one close-up still per look variant (A-D) on the Runpod GPU pod.
# Usage: render_pikachu_v4_mocks.sh FRAME SAMPLES PERCENT
set -euo pipefail
cd /workspace/blender-lab
FRAME=${1:-20}; SPP=${2:-128}; PCT=${3:-100}
for v in A B C D; do
  blender -b --python-exit-code 1 --python scripts/pikachu_v4.py -- --output mocks/$v \
    --variant $v --closeup --frames $FRAME --samples $SPP --percent $PCT --no-export > mocks-$v.log 2>&1
  grep -E "BODY_MESH|FRAME_COMPLETE" mocks-$v.log
done
echo MOCKS_DONE
