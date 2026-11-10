#!/bin/bash
set -euo pipefail
cd /workspace/blender-lab
timeout 900 blender -b --python-exit-code 1 --python scripts/ball_wall.py -- --output results/ball > render.log 2>&1
python3 scripts/encode_animation.py results/ball results/ball/ball-wall.mp4 > encode.log
ffmpeg -y -v error -i results/ball/ball-wall.mp4 -filter_complex 'fps=12,scale=640:-1:flags=lanczos,split[a][b];[a]palettegen[p];[b][p]paletteuse' results/ball/preview.gif
ffmpeg -y -v error -i results/ball/ball-wall.mp4 -vf 'fps=2,scale=320:-1,tile=5x2' -frames:v 1 results/ball/contact-sheet.png
cp results/ball/frames/frame_0043.png results/ball/poster.png
cp gpu.txt render.log encode.log results/ball/
cd results/ball
sha256sum ball-wall.mp4 ball-wall.blend render-metadata.json preview.gif poster.png contact-sheet.png gpu.txt render.log encode.log > SHA256SUMS
cd ../..
tar -czf ball-result.tar.gz --exclude=frames -C results ball
sha256sum ball-result.tar.gz
