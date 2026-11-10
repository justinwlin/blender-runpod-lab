#!/bin/bash
# Final v4 render (look A, leaf ears, soft fur) on the Runpod GPU pod. Run from /workspace/blender-lab.
set -euo pipefail
cd /workspace/blender-lab
OUT=results/pikachu-v4
rm -rf "${OUT:?}"
nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv > gpu.txt
timeout 14000 blender -b --python-exit-code 1 --python scripts/pikachu_v4.py -- --output $OUT --samples 128 --variant A --ears leaf > render.log 2>&1
python3 scripts/verify_pikachu_v3_glb.py $OUT/pikachu-v4.glb > $OUT/model-validation.json
n=$(ls $OUT/frames/frame_*.png | wc -l); test "$n" -eq 108
ffmpeg -y -v error -framerate 24 -i $OUT/frames/frame_%04d.png -frames:v 108 -c:v libx264 -crf 16 -preset slow -pix_fmt yuv420p -movflags +faststart $OUT/pikachu-v4-loop.mp4
ffmpeg -y -v error -stream_loop 3 -i $OUT/pikachu-v4-loop.mp4 -c copy $OUT/pikachu-v4-4x.mp4
ffprobe -v error -show_entries stream=nb_frames,width,height,r_frame_rate:format=duration -of json $OUT/pikachu-v4-loop.mp4 > $OUT/video-probe.json
ffmpeg -y -v error -framerate 24 -i $OUT/frames/frame_%04d.png -filter_complex 'scale=720:-1:flags=lanczos,split[a][b];[a]palettegen=stats_mode=diff[p];[b][p]paletteuse=dither=sierra2_4a' -loop 0 $OUT/pikachu-v4.gif
ffmpeg -y -v error -i $OUT/frames/frame_%04d.png -vf 'select=not(mod(n\,9)),scale=360:-1,tile=4x3' -frames:v 1 $OUT/contact-sheet.png
cp $OUT/frames/frame_0001.png $OUT/poster.png
cp gpu.txt render.log $OUT/
cd $OUT
sha256sum pikachu-v4-loop.mp4 pikachu-v4-4x.mp4 pikachu-v4.gif pikachu-v4.glb pikachu-v4.blend poster.png contact-sheet.png render-metadata.json model-validation.json video-probe.json gpu.txt render.log > SHA256SUMS
cd ..
tar -czf pikachu-v4-result.tar.gz --exclude=frames pikachu-v4
sha256sum pikachu-v4-result.tar.gz
echo DONE
