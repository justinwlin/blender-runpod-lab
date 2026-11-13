"""blender -b out/pixel-calico.blend -P scripts/render_hero.py -- <out_png> [samples] [res] [gpu]"""
import bpy, sys
a = sys.argv[sys.argv.index('--') + 1:]
sc = bpy.context.scene; sc.camera = bpy.data.objects['Hero']; bpy.data.objects['LightRig'].rotation_euler = (0, 0, 0)
sc.cycles.samples = int(a[1]) if len(a) > 1 else 200
sc.render.resolution_x = sc.render.resolution_y = int(a[2]) if len(a) > 2 else 1600
if 'gpu' in a:
    prefs = bpy.context.preferences.addons['cycles'].preferences; prefs.compute_device_type = 'OPTIX'; prefs.refresh_devices()
    for d in prefs.devices: d.use = d.type == 'OPTIX'
    sc.cycles.device = 'GPU'
sc.render.filepath = a[0]; bpy.ops.render.render(write_still=True)
