#!/bin/sh
# encode.sh <anim_dir>: loop the rendered cycles into MP4s (walk x5 = 5 s, ball x2 = 6 s, idle x1 = 4 s)
set -e; cd "$1"
enc() { clip=$1; loops=$2; n=$(ls ${clip}_full/*.png | wc -l); rm -rf seq_$clip; mkdir seq_$clip; i=0
  for l in $(seq 1 $loops); do for f in $(ls ${clip}_full/*.png | sort); do ln -s "$PWD/$f" seq_$clip/$(printf %05d $i).png; i=$((i+1)); done; done
  ffmpeg -y -loglevel error -framerate 24 -i seq_$clip/%05d.png -c:v libx264 -pix_fmt yuv420p -crf 16 -movflags +faststart pixel_$clip.mp4
  rm -rf seq_$clip; echo "$clip: $n frames x $loops loops -> pixel_$clip.mp4"; }
enc walk 5; enc ball 2; enc idle 1
