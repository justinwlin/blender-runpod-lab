"""Render frames of film.blend (gates and the farm use the same script).
blender -b film.blend -P scripts/v3/render.py -- <out_dir> <frames> [samples=192] [scale=100] [hidecat] [novol]
frames: comma list '0,75,120', a list file '@frames.txt', or a range with step and offset 'start:end:step:offsets' e.g. 0:624:5:1+2 (every-Nth split: this pod takes residues 1 and 2 of 5)."""
import bpy, sys, os, time, json
a = sys.argv[sys.argv.index('--') + 1:]; out, spec = a[0], a[1]
opt = dict(x.split('=') for x in a[2:] if '=' in x); flags = [x for x in a[2:] if '=' not in x]
sc = bpy.context.scene
if ':' in spec:
    s, e, st = [int(v) for v in spec.split(':')[:3]]; offs = [int(v) for v in spec.split(':')[3].split('+')]; frames = [f for f in range(s, e) if (f - s) % st in offs]
elif spec.startswith('@'): frames = [int(v) for v in open(spec[1:]).read().replace(',', ' ').split()]      # explicit list file
else: frames = [int(v) for v in spec.split(',')]
prefs = bpy.context.preferences.addons['cycles'].preferences; prefs.compute_device_type = 'OPTIX'; prefs.refresh_devices()
for d in prefs.devices: d.use = d.type == 'OPTIX'
sc.cycles.device = 'GPU'; sc.cycles.samples = int(opt.get('samples', 192)); sc.render.resolution_percentage = int(opt.get('scale', 100))
if 'hidecat' in flags:
    for o in bpy.data.objects:
        if o.name.startswith(('Head', 'Ear.', 'Body', 'Neck', 'Leg.', 'Tail', 'Lid.', 'Ball')): o.hide_render = True
if 'novol' in flags: bpy.data.objects['Haze'].hide_render = True
os.makedirs(out, exist_ok=True); log = []
for f in frames:
    path = f'{out}/{f:04d}.png'
    if os.path.exists(path) and os.path.getsize(path) > 10000: continue          # resumable
    t0 = time.time(); sc.frame_set(f); sc.render.filepath = path; bpy.ops.render.render(write_still=True)
    log.append((f, round(time.time() - t0, 2))); print('FRAME', f, sc.camera.name, round(time.time() - t0, 2), 's', flush=True)
json.dump(log, open(f'{out}/times_{frames[0]}_{len(frames)}.json', 'w'))
print('RENDER_DONE', len(log))
