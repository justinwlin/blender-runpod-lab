#!/bin/sh
# run_cut.sh <round>: rebuild model + film, then gate stills and a whole-cut playblast (every 2nd frame, low res) into v3/cut_r<round>/
cd /workspace/pc; R=$1; O=/workspace/pc/v3/cut_r$R; mkdir -p $O
B="blender -b --python-exit-code 1"
$B v2/pixel-calico.blend -P scripts/v3/build_v3.py -- out/labels /workspace/pc/out/v3/tex /workspace/pc/v3 gpu 2>&1 | grep -E "BUILD_V3_DONE|Error|Traceback|^  File"
$B v3/pixel-v3.blend -P scripts/v3/film.py -- /workspace/pc/out/v3/tex /workspace/pc/v3/film.blend 2>&1 | grep -E "FILM_DONE|Error|Traceback|^  File"
$B v3/film.blend -P scripts/v3/render.py -- $O/shots 30,75,104,140,200,270,326,372,404,490,560,610 samples=64 scale=50 2>&1 | grep -E "FRAME|Error|Traceback|^  File"
echo STILLS_DONE
$B v3/film.blend -P scripts/v3/render.py -- $O/play 0:624:2:0 samples=16 scale=25 novol 2>&1 | grep -E "RENDER_DONE|Error|Traceback|^  File"
ls $O/play/*.png | sort | awk '{printf "file %s\nduration 0.0833333\n", $1}' > $O/play.txt
ffmpeg -y -loglevel error -f concat -safe 0 -i $O/play.txt -c:v libx264 -pix_fmt yuv420p -crf 20 -vf "scale=960:540:flags=lanczos" -r 24 $O/playblast_cut.mp4
echo CUT_DONE
