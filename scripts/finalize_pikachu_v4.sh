#!/bin/bash
# Merge-and-encode step for the split v4 render. Frames 1-54 come from this pod;
# frames 55-108 are copied in from the worker pods before this runs.
set -euo pipefail
cd /workspace/blender-lab
OUT=results/pikachu-v4
python3 scripts/verify_pikachu_v3_glb.py $OUT/pikachu-v4.glb > $OUT/model-validation.json
for f in $(seq 1 108); do test -s $(printf "$OUT/frames/frame_%04d.png" $f); done
python3 - <<'PY'
import json, re, glob
timings = [json.loads(m) for m in re.findall(r'FRAME_COMPLETE (\{.*\})', open('render.log').read())]
parts = {}
for p in sorted(glob.glob('parts/*/render-metadata.json')):
    parts[p.split('/')[1]] = json.load(open(p))
meta = dict(blender='5.0.1', backend='OPTIX', resolution=[1440, 1080], samples=128, fps=24,
            frames=list(range(1, 109)), loop_period_frames=108, variant='A', ears='leaf', fur=True,
            split={'main pod ngmi1emlq44h2i': [t['frame'] for t in timings if t['frame'] <= 54]} |
                  {k: v['frames'] for k, v in parts.items()},
            devices={k: v['devices'] for k, v in parts.items()},
            frame_timings_main=[t for t in timings if t['frame'] <= 54])
json.dump(meta, open('results/pikachu-v4/render-metadata.json', 'w'), indent=2)
PY
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
