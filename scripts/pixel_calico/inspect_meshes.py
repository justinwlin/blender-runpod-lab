# Render each candidate GLB from 4 angles with a clay material (Cycles CPU) for mesh selection.
import bpy, sys, glob, os, math
from mathutils import Vector
src, dst = sys.argv[sys.argv.index('--')+1:][:2]
sc = bpy.context.scene
sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.samples = 12; sc.cycles.use_denoising = True
sc.render.resolution_x = sc.render.resolution_y = 420
w = bpy.data.worlds.new('w'); sc.world = w; w.use_nodes = True
w.node_tree.nodes['Background'].inputs[0].default_value = (1, 1, 1, 1)
w.node_tree.nodes['Background'].inputs[1].default_value = 0.6
clay = bpy.data.materials.new('clay'); clay.use_nodes = True
clay.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (0.55, 0.6, 0.7, 1)
for f in sorted(glob.glob(src + '/*.glb')):
    bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete()
    bpy.ops.import_scene.gltf(filepath=f)
    obs = [o for o in sc.objects if o.type == 'MESH']
    o = obs[0]
    pts = [o.matrix_world @ Vector(c) for c in o.bound_box]
    mn = Vector([min(p[i] for p in pts) for i in range(3)]); mx = Vector([max(p[i] for p in pts) for i in range(3)])
    print('MESH', os.path.basename(f), len(o.data.vertices), len(o.data.polygons), [round(x, 3) for x in mn], [round(x, 3) for x in mx], flush=True)
    o.data.materials.clear(); o.data.materials.append(clay)
    for p in o.data.polygons: p.use_smooth = True
    ctr = (mn + mx) / 2; r = (mx - mn).length / 2
    sun = bpy.data.lights.new('s', 'SUN'); sun.energy = 3; so = bpy.data.objects.new('s', sun); sc.collection.objects.link(so)
    cam = bpy.data.cameras.new('c'); cam.type = 'ORTHO'; cam.ortho_scale = r * 2.1
    co = bpy.data.objects.new('c', cam); sc.collection.objects.link(co); sc.camera = co
    # az 0 = camera on -Y looking +Y (Blender "front")
    for name, az in (('front', 0), ('q3', 40), ('right', 90), ('back', 180), ('left', 270)):
        a = math.radians(az)
        d = Vector((math.sin(a), -math.cos(a), 0.15)).normalized()
        co.location = ctr + d * r * 4
        co.rotation_euler = (-d).to_track_quat('-Z', 'Y').to_euler()
        so.rotation_euler = (Vector((d.x - 0.4 * d.y, d.y + 0.4 * d.x, 0.8))).to_track_quat('Z', 'Y').to_euler()
        sc.render.filepath = f"{dst}/{os.path.basename(f)[:-4]}_{name}.png"
        bpy.ops.render.render(write_still=True)
