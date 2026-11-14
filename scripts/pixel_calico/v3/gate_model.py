"""Model + rig gate: turnaround of the v3 Pixel in 3 poses (stand, mid-walk, paw raised), plus a wireframe turnaround.
blender -b <out>/pixel-v3.blend -P scripts/v3/gate_model.py -- <gates_dir>"""
import bpy, sys, os, math
from mathutils import Vector
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pixrig
OUT = sys.argv[sys.argv.index('--') + 1]; sc = bpy.context.scene
rig = bpy.data.objects['PixelRigV3']; R = pixrig.Rig(rig)
w = bpy.data.worlds.new('W'); sc.world = w; w.use_nodes = True
w.node_tree.nodes['Background'].inputs[0].default_value = (1, 1, 1, 1); w.node_tree.nodes['Background'].inputs[1].default_value = 0.45
bpy.ops.mesh.primitive_plane_add(size=80); fl = bpy.context.object; fl.is_shadow_catcher = True; sc.render.film_transparent = True
ctr = Vector((0, -0.1, 1.05))
lr = bpy.data.objects.new('LightRig', None); sc.collection.objects.link(lr)
for nm, loc, e, s in (('Key', (-3.5, -4.5, 5), 260, 4), ('Fill', (4.5, -3, 2.5), 90, 5), ('Rim', (1.5, 5, 4), 160, 3)):
    l = bpy.data.lights.new(nm, 'AREA'); l.energy = e; l.size = s; o = bpy.data.objects.new(nm, l); sc.collection.objects.link(o)
    o.location = loc; o.rotation_euler = (ctr - Vector(loc)).to_track_quat('-Z', 'Y').to_euler(); o.parent = lr
cam = bpy.data.cameras.new('C'); cam.type = 'ORTHO'; cam.ortho_scale = 3.3; co = bpy.data.objects.new('C', cam); sc.collection.objects.link(co); sc.camera = co
VIEWS = {'front': 0, 'three_quarter': -35, 'side': -90, 'back': 180}
def shoot(tag):
    for k, az in VIEWS.items():
        a, e = math.radians(az), math.radians(6); d = Vector((math.sin(a) * math.cos(e), -math.cos(a) * math.cos(e), math.sin(e)))
        co.location = ctr + d * 10; co.rotation_euler = (-d).to_track_quat('-Z', 'Y').to_euler(); lr.rotation_euler = (0, 0, a)
        sc.render.filepath = f'{OUT}/model_{tag}_{k}.png'; bpy.ops.render.render(write_still=True)
pixrig.gpu(sc, 64); sc.view_settings.view_transform = 'Standard'; sc.render.resolution_x = sc.render.resolution_y = 720

def stand(): R.reset()
def midwalk():
    R.reset(); fr = R.foot_rest
    R.loc('body', (0, 0, 0.03)); R.rot('body', ry=3, rz=-4); R.rot('chest', rz=6)
    R.foot('FL', fr['FL'] + Vector((0, -0.20, 0.12))); R.foot('HR', fr['HR'] + Vector((0, -0.16, 0.09)))
    R.foot('FR', fr['FR'] + Vector((0, 0.17, 0))); R.foot('HL', fr['HL'] + Vector((0, 0.17, 0)))
    R.rot('head', rz=-6, ry=-3, rx=3)
    for i in range(1, 9): R.rot(f'tail{i}', rz=5 * math.sin(i * 0.7), rx=-2)
def pawup():
    R.reset(); fr = R.foot_rest
    R.loc('body', (0.06, 0.04, -0.02)); R.rot('body', ry=5, rx=-6); R.rot('chest', rx=-8, rz=-5)
    R.foot('FR', (-0.16, -0.86, 0.62)); R.rot('head', rz=-14, rx=10, ry=-8)
    R.rot('ear.L', ry=8); R.rot('ear.R', ry=-10, rx=6); R.blink(0.45)
    for i in range(1, 9): R.rot(f'tail{i}', rx=4, rz=-7)
for tag, fn in (('stand', stand), ('midwalk', midwalk), ('pawup', pawup)):
    fn(); bpy.context.view_layer.update(); shoot(tag)
# wireframe turnaround of the base cage (no subdivision), clay + dark wire
stand()
clay = bpy.data.materials.new('Clay'); clay.use_nodes = True; clay.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (0.62, 0.66, 0.72, 1)
wire = bpy.data.materials.new('Wire'); wire.use_nodes = True; wire.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (0.02, 0.02, 0.03, 1)
for o in sc.objects:
    if o.type != 'MESH' or o == fl: continue
    for m in o.modifiers:
        if m.type in ('SUBSURF', 'SOLIDIFY'): m.show_render = False
    o.data.materials.clear(); o.data.materials.append(clay); o.data.materials.append(wire)
    wm = o.modifiers.new('Wire', 'WIREFRAME'); wm.thickness = 0.006; wm.use_replace = False; wm.material_offset = 1
shoot('wire')
print('GATE_MODEL_DONE')
