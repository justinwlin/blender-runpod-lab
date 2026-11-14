#!/bin/sh
# post.sh <frames_dir> <title.png> <out.mp4>: finishing pass on the rendered frames with ffmpeg.
# bloom (blurred highlights screened back), gentle warm grade, vignette, film grain, title fade-in, fade in/out. Silent.
set -e
FR=$1; TITLE=$2; OUT=$3; N=$(ls $FR/*.png | wc -l)
ffmpeg -y -loglevel error -framerate 24 -i $FR/%04d.png -loop 1 -framerate 24 -i $TITLE -filter_complex "
[0:v]format=gbrp,split=2[base][hl];
[hl]colorlevels=rimin=0.72:gimin=0.72:bimin=0.72,gblur=sigma=22[glow];
[base][glow]blend=all_mode=screen:all_opacity=0.32,
eq=contrast=1.06:saturation=1.10:gamma=1.02,colorbalance=rs=0.02:bs=-0.03:rm=0.015:bm=-0.02:rh=0.02:bh=-0.03,
vignette=angle=PI/5.5,noise=alls=6:allf=t+u[graded];
[1:v]format=rgba,fade=t=in:st=23.4:d=1.0:alpha=1[title];
[graded][title]overlay=0:0:shortest=1,fade=t=in:st=0:d=0.5,fade=t=out:st=$(awk "BEGIN{print $N/24-0.75}"):d=0.75,format=yuv420p[v]" \
 -map "[v]" -frames:v $N -c:v libx264 -preset slow -crf 15 -movflags +faststart $OUT
echo "post: $N frames -> $OUT"
