#!/bin/sh
# finish_shot.sh <comfy_output_dir> <first film frame> <work_dir> <name> [pull]: colour-lock + composite the AI frames over the
# render, then encode the result, the matching render clip and a side-by-side. Run on the pod.
AI=$1; FIRST=$2; WD=$3; NAME=$4; PULL=${5:-0.85}; N=$(ls $AI/*.png | wc -l)
R=/workspace/pc/v3/post/final_frames; M=/workspace/ai/matte
cd /workspace/pc && python3 scripts/ai_pass/colorlock.py $AI $R $M $WD/locked first=$FIRST pull=$PULL || exit 1
cd $WD
ffmpeg -y -loglevel error -framerate 24 -start_number $FIRST -i locked/%04d.png -c:v libx264 -crf 17 -pix_fmt yuv420p ${NAME}_locked.mp4
ffmpeg -y -loglevel error -framerate 24 -start_number $FIRST -i $R/%04d.png -frames:v $N -vf scale=1280:720 -c:v libx264 -crf 17 -pix_fmt yuv420p ${NAME}_render.mp4
ffmpeg -y -loglevel error -i ${NAME}_render.mp4 -i ${NAME}_locked.mp4 -filter_complex hstack -c:v libx264 -crf 18 -pix_fmt yuv420p ${NAME}_side_by_side.mp4
echo FINISH_DONE $N
