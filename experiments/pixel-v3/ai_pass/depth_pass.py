"""Render an exact depth control pass from the film scene (inverse depth, near = white), same cameras and animation.
blender -b film.blend -P scripts/ai_pass/depth_pass.py -- <out_dir> <start> <end> [width height]
Used as the 'depth' control video for the AI pass instead of an estimated depth map."""
import bpy, sys, os
a = sys.argv[sys.argv.index('--') + 1:]; out, s, e = a[0], int(a[1]), int(a[2]); W, H = (int(a[3]), int(a[4])) if len(a) > 4 else (1280, 720)
sc = bpy.context.scene
m = bpy.data.materials.new('DepthOverride'); m.use_nodes = True; t = m.node_tree; t.nodes.clear()
cd = t.nodes.new('ShaderNodeCameraData'); dv = t.nodes.new('ShaderNodeMath'); dv.operation = 'DIVIDE'; dv.inputs[0].default_value = 0.22; dv.use_clamp = True
em = t.nodes.new('ShaderNodeEmission'); o = t.nodes.new('ShaderNodeOutputMaterial')
t.links.new(cd.outputs['View Z Depth'], dv.inputs[1]); t.links.new(dv.outputs[0], em.inputs['Color']); t.links.new(em.outputs[0], o.inputs['Surface'])
bpy.context.view_layer.material_override = m
bpy.data.objects['Haze'].hide_render = True
for c in bpy.data.cameras: c.dof.use_dof = False
sc.world.node_tree.nodes['Background'].inputs['Strength'].default_value = 0
sc.render.use_motion_blur = False; sc.cycles.samples = 4; sc.cycles.use_denoising = False; sc.cycles.use_adaptive_sampling = False
sc.view_settings.view_transform = 'Standard'; sc.view_settings.look = 'None'
sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = W, H, 100
prefs = bpy.context.preferences.addons['cycles'].preferences; prefs.compute_device_type = 'OPTIX'; prefs.refresh_devices()
for d in prefs.devices: d.use = d.type == 'OPTIX'
sc.cycles.device = 'GPU'; os.makedirs(out, exist_ok=True)
for f in range(s, e + 1):
    sc.frame_set(f); sc.render.filepath = f'{out}/{f:04d}.png'; bpy.ops.render.render(write_still=True)
print('DEPTH_DONE', e - s + 1)
