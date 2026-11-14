"""Render a cat matte (white = Pixel, black = everything else) from the film scene, same cameras and animation.
blender -b film.blend -P scripts/ai_pass/matte_pass.py -- <out_dir> <start> <end> [width height]
Used to composite the AI-restyled cat back over the untouched Blender render (set, props and light stay exact)."""
import bpy, sys, os
a = sys.argv[sys.argv.index('--') + 1:]; out, s, e = a[0], int(a[1]), int(a[2]); W, H = (int(a[3]), int(a[4])) if len(a) > 4 else (1280, 720)
sc = bpy.context.scene
def emit(name, v):
    m = bpy.data.materials.new(name); m.use_nodes = True; t = m.node_tree; t.nodes.clear()
    em = t.nodes.new('ShaderNodeEmission'); em.inputs['Color'].default_value = (v, v, v, 1); o = t.nodes.new('ShaderNodeOutputMaterial'); t.links.new(em.outputs[0], o.inputs['Surface']); return m
white, black = emit('MatteWhite', 1.0), emit('MatteBlack', 0.0)
CAT = ('Head', 'Ear.', 'Body', 'Neck', 'Leg.', 'Tail', 'Lid.')
for o in bpy.data.objects:
    if o.type != 'MESH': continue
    if o.name == 'Haze': o.hide_render = True; continue
    m = white if o.name.startswith(CAT) else black
    if not o.data.materials: o.data.materials.append(m)
    for i in range(len(o.material_slots)): o.material_slots[i].material = m
for c in bpy.data.cameras: c.dof.use_dof = False
sc.world.node_tree.nodes['Background'].inputs['Strength'].default_value = 0
for l in bpy.data.lights: l.energy = 0
sc.render.use_motion_blur = False; sc.cycles.samples = 8; sc.cycles.use_denoising = False; sc.cycles.use_adaptive_sampling = False
sc.view_settings.view_transform = 'Standard'; sc.view_settings.look = 'None'
sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = W, H, 100
prefs = bpy.context.preferences.addons['cycles'].preferences; prefs.compute_device_type = 'OPTIX'; prefs.refresh_devices()
for d in prefs.devices: d.use = d.type == 'OPTIX'
sc.cycles.device = 'GPU'; os.makedirs(out, exist_ok=True)
for f in range(s, e + 1):
    sc.frame_set(f); sc.render.filepath = f'{out}/{f:04d}.png'; bpy.ops.render.render(write_still=True)
print('MATTE_DONE', e - s + 1)
