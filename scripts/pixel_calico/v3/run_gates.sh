#!/bin/sh
# run_gates.sh <round>: rebuild model + film, render model / set / shot gates, a walk playblast and one full-quality test frame.
# Earlier rounds are archived (never deleted): v3/gates -> v3/gates_r<N>
cd /workspace/pc; R=$1
[ -d v3/gates ] && mv v3/gates v3/gates_r$R; mkdir -p v3/gates
B="blender -b --python-exit-code 1"
$B v2/pixel-calico.blend -P scripts/v3/build_v3.py -- out/labels /workspace/pc/out/v3/tex /workspace/pc/v3 gpu 2>&1 | grep -E "PARTS|BUILD_V3_DONE|Error|Traceback|^  File"
$B v3/pixel-v3.blend -P scripts/v3/film.py -- /workspace/pc/out/v3/tex /workspace/pc/v3/film.blend 2>&1 | grep -E "FILM_DONE|Error|Traceback|^  File"
$B v3/pixel-v3.blend -P scripts/v3/gate_model.py -- /workspace/pc/v3/gates 2>&1 | grep -E "GATE_MODEL_DONE|Error|Traceback|^  File"
$B v3/film.blend -P scripts/v3/render.py -- /workspace/pc/v3/gates/set 0,534 samples=64 scale=50 hidecat 2>&1 | grep -E "FRAME|Error|Traceback|^  File"
$B v3/film.blend -P scripts/v3/render.py -- /workspace/pc/v3/gates/shots 0,75,104,140,200,270,326,372,490,600 samples=64 scale=50 2>&1 | grep -E "FRAME|Error|Traceback|^  File"
$B v3/film.blend -P scripts/v3/render.py -- /workspace/pc/v3/gates/walk 160:250:1:0 samples=24 scale=34 novol 2>&1 | grep -E "RENDER_DONE|Error|Traceback|^  File"
ffmpeg -y -loglevel error -framerate 24 -start_number 160 -i v3/gates/walk/%04d.png -c:v libx264 -pix_fmt yuv420p -crf 18 -vf "scale=trunc(iw/2)*2:trunc(ih/2)*2" v3/gates/playblast_walk.mp4
$B v3/film.blend -P scripts/v3/render.py -- /workspace/pc/v3/gates/final_test 200,326 samples=192 scale=100 2>&1 | grep -E "FRAME|Error|Traceback|^  File"
echo GATES_DONE
