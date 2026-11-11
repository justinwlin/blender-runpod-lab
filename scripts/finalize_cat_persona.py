"""Assemble final persona sheets, encode/verify idle, and optionally prune raw intermediates.

Run after rendering: python3 scripts/finalize_cat_persona.py --prune
The verified MP4 and sheets remain usable after the source frame PNGs are removed.
"""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import time

from PIL import Image, ImageDraw

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output', type=Path, default=Path('results/cat-persona'))
parser.add_argument('--before-front', type=Path, help='Prior three-quarter still for the compact comparison')
parser.add_argument('--before-back', type=Path, help='Prior back still for the compact comparison')
parser.add_argument('--prune', action='store_true', help='Remove raw frames and historical look folders after video validation')
a = parser.parse_args()
r = a.output


def sheet(paths, labels, path, columns, size=640):
    rows = (len(paths)+columns-1)//columns
    canvas = Image.new('RGB', (columns*size, rows*(size+24)), (42, 44, 47))
    draw = ImageDraw.Draw(canvas)
    for i, (source, label) in enumerate(zip(paths, labels)):
        with Image.open(source) as im:
            x, y = i % columns*size, i // columns*(size+24)
            canvas.paste(im.convert('RGB').resize((size, size)), (x, y))
            draw.text((x+8, y+size+6), label, fill='white')
    canvas.save(path, optimize=True)


views = ['front', 'three_quarter', 'side', 'back']
sheet([r/(v+'.png') for v in views], views, r/'contact-sheet.png', 4)
if a.before_front and a.before_back:
    sheet([a.before_front, r/'three_quarter.png', a.before_back, r/'back.png'],
          ['Before: 3/4', 'Final: 3/4', 'Before: back', 'Final: back'],
          r/'iteration-comparison.png', 4, 320)
meta = json.loads((r/'idle/render-metadata.json').read_text())
assert [x['frame'] for x in meta['renders']] == list(range(1, 49))
assert meta['fps'] == 24
frames = [r/'idle/frames'/f'{i:04d}.png' for i in range(1, 49)]
encode_seconds = None
if any(p.exists() for p in frames):
    assert all(p.is_file() for p in frames), 'Idle source sequence is incomplete'
    sheet(frames, [p.stem for p in frames], r/'idle-contact.png', 6, 180)
    start = time.perf_counter()
    subprocess.run(['ffmpeg', '-y', '-v', 'error', '-framerate', '24', '-start_number', '1',
                    '-i', str(r/'idle/frames/%04d.png'), '-frames:v', '48', '-c:v', 'libx264',
                    '-crf', '18', '-preset', 'slow', '-pix_fmt', 'yuv420p', '-movflags',
                    '+faststart', str(r/'idle-test.mp4')], check=True)
    encode_seconds = time.perf_counter()-start
else:
    assert (r/'idle-contact.png').is_file(), 'Retained idle contact sheet missing'
probe = json.loads(subprocess.check_output(['ffprobe', '-v', 'error', '-show_streams',
                                          '-show_format', '-of', 'json', str(r/'idle-test.mp4')]))
v = next(s for s in probe['streams'] if s['codec_type'] == 'video')
assert (v['width'], v['height']) == tuple(meta['resolution'])
assert v['nb_frames'] == '48' and v['r_frame_rate'] == '24/1'
assert float(probe['format']['duration']) == 2
summary = dict(video='idle-test.mp4', resolution=meta['resolution'], frames=48, fps=24,
               duration_seconds=2, render_seconds=round(sum(x['seconds'] for x in meta['renders']), 3),
               frame_seconds_min=min(x['seconds'] for x in meta['renders']),
               frame_seconds_max=max(x['seconds'] for x in meta['renders']))
if encode_seconds is None and (r/'video-check.json').exists():
    encode_seconds = json.loads((r/'video-check.json').read_text()).get('encode_seconds')
summary['encode_seconds'] = round(encode_seconds, 3) if encode_seconds is not None else None
(r/'video-check.json').write_text(json.dumps(summary, indent=2)+'\n')
if a.prune:
    archive_path = r/'development-metadata.json'
    archive = json.loads(archive_path.read_text()) if archive_path.exists() else {}
    obsolete = ['iteration-1', 'iteration-2', 'iteration-3', 'feedback-1']
    for folder in obsolete:
        if (r/folder).exists():
            for path in sorted((r/folder).rglob('render-metadata.json')):
                archive[str(path.parent.relative_to(r))] = json.loads(path.read_text())
    archive_path.write_text(json.dumps(archive, indent=2)+'\n')
    assert (r/'iteration-comparison.png').is_file(), 'Create the single comparison before pruning'
    for folder in obsolete+['idle/frames']:
        if (r/folder).exists():
            shutil.rmtree(r/folder)
    for name in ['idle-contact-1.png', 'idle-contact-2.png', 'cat-persona.blend1']:
        (r/name).unlink(missing_ok=True)
    for path in r.rglob('*.png'):
        with Image.open(path) as im:
            im.save(path, optimize=True)
    summary['retained_bytes'] = sum(p.stat().st_size for p in r.rglob('*') if p.is_file())
    assert summary['retained_bytes'] < 12_000_000, 'Result directory exceeds the 12 MB budget'
    (r/'video-check.json').write_text(json.dumps(summary, indent=2)+'\n')
print(json.dumps(summary, indent=2))
