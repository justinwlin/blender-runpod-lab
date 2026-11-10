#!/bin/bash
set -euo pipefail
cd /workspace/blender-lab
timeout 1200 blender -b --python-exit-code 1 --python scripts/pikachu_sleep.py -- --output results/pikachu > render.log 2>&1
python3 scripts/verify_pikachu_glb.py results/pikachu/pikachu-sleep.glb > results/pikachu/model-validation.json
python3 scripts/encode_animation.py results/pikachu results/pikachu/pikachu-sleep.mp4 > encode.log
ffmpeg -y -v error -i results/pikachu/pikachu-sleep.mp4 -filter_complex 'fps=12,scale=600:-1:flags=lanczos,split[a][b];[a]palettegen[p];[b][p]paletteuse' results/pikachu/preview.gif
ffmpeg -y -v error -i results/pikachu/pikachu-sleep.mp4 -vf 'fps=1,scale=280:-1,tile=5x1' -frames:v 1 results/pikachu/contact-sheet.png
cp results/pikachu/frames/frame_0001.png results/pikachu/poster.png
cp gpu.txt render.log encode.log results/pikachu/
cd results/pikachu
sha256sum pikachu-sleep.mp4 pikachu-sleep.blend pikachu-sleep.glb render-metadata.json preview.gif poster.png contact-sheet.png gpu.txt render.log encode.log > SHA256SUMS
cd ../..
tar -czf pikachu-result.tar.gz --exclude=frames -C results pikachu
sha256sum pikachu-result.tar.gz
