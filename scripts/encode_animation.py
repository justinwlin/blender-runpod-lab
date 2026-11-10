#!/usr/bin/env python3
"""Verify the frame sequence, then create a five-second H.264 video."""
import argparse
import json
from pathlib import Path
import subprocess

parser = argparse.ArgumentParser()
parser.add_argument('source', type=Path)
parser.add_argument('destination', type=Path)
args = parser.parse_args()
meta = json.loads((args.source / 'render-metadata.json').read_text())
frames = meta['frames']
if frames != list(range(1, 121)) or meta['fps'] != 24:
    raise SystemExit('Expected 120 contiguous frames at 24 fps.')
missing = [f for f in frames if not (args.source / 'frames' / f'frame_{f:04d}.png').is_file()]
if missing:
    raise SystemExit(f'Missing frames: {missing}')
args.destination.parent.mkdir(parents=True, exist_ok=True)
subprocess.run(['ffmpeg', '-y', '-v', 'error', '-framerate', '24', '-start_number', '1',
    '-i', str(args.source / 'frames' / 'frame_%04d.png'), '-frames:v', '120',
    '-c:v', 'libx264', '-crf', '18', '-preset', 'slow', '-pix_fmt', 'yuv420p',
    '-movflags', '+faststart', str(args.destination)], check=True)
probe = json.loads(subprocess.check_output(['ffprobe', '-v', 'error', '-show_streams',
    '-show_format', '-of', 'json', str(args.destination)]))
video = next(s for s in probe['streams'] if s['codec_type'] == 'video')
assert int(video['nb_frames']) == 120, video
assert abs(float(probe['format']['duration']) - 5) < .01, probe
assert [video['width'], video['height']] == meta['resolution'], video
print(json.dumps({'video': str(args.destination), 'frames': 120, 'seconds': 5,
                  'resolution': meta['resolution'], 'backend': meta['backend']}, indent=2))
