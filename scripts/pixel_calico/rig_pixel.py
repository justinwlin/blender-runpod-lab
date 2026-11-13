"""Rig Pixel: build a simple armature, get automatic (bone-heat) weights on a clean voxel-remeshed proxy,
transfer them to the render mesh, patch the fused regions (ears, head, front legs), give the separate tail
object an analytic 6-bone weight chain, save pixel-rigged.blend.
blender -b out/pixel-calico.blend -P scripts/rig_pixel.py -- <out_blend>"""
import bpy, sys, os, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pixel_tail as PT
from mathutils import Vector
out_blend = sys.argv[sys.argv.index('--') + 1]
sc = bpy.context.scene; ob = bpy.data.objects['Pixel']; me = ob.data; n = len(me.vertices)
co = np.empty(n * 3, np.float32); me.vertices.foreach_get('co', co); co = co.reshape(-1, 3)

X0 = PT.X0
# ear tips straight from the geometry
def ear(side):
    m = (co[:, 0] < X0) if side < 0 else (co[:, 0] > X0)
    tip = co[m][co[m][:, 2].argmax()]; base = Vector((tip[0] - side * 0.10, tip[1] + 0.02, tip[2] - 0.36))
    return base, Vector(tip.tolist()) - Vector((0, 0, 0.03))
earR, earL = ear(-1), ear(+1)
# name: (head, tail, parent, connected)
BONES = {
 'root':   ((X0, 0.10, 0.00), (X0, 0.10, 0.22), None),
 'hips':   ((X0, 0.10, 0.22), (X0, 0.02, 0.52), 'root'),
 'spine':  ((X0, 0.02, 0.52), (X0, -0.08, 0.78), 'hips'),
 'chest':  ((X0, -0.08, 0.78), (X0, -0.14, 0.96), 'spine'),
 'head':   ((X0, -0.14, 0.96), (X0, -0.20, 1.70), 'chest'),
 'ear.R':  (earR[0], earR[1], 'head'),
 'ear.L':  (earL[0], earL[1], 'head'),
 'arm.R':  ((X0 - 0.19, -0.30, 0.74), (X0 - 0.19, -0.40, 0.38), 'chest'),
 'paw.R':  ((X0 - 0.19, -0.40, 0.38), (X0 - 0.19, -0.47, 0.05), 'arm.R'),
 'arm.L':  ((X0 + 0.17, -0.30, 0.74), (X0 + 0.17, -0.40, 0.38), 'chest'),
 'paw.L':  ((X0 + 0.17, -0.40, 0.38), (X0 + 0.17, -0.47, 0.05), 'arm.L'),
 'foot.R': ((X0 - 0.42, -0.05, 0.12), (X0 - 0.42, -0.36, 0.07), 'hips'),
 'foot.L': ((X0 + 0.46, -0.10, 0.12), (X0 + 0.46, -0.36, 0.07), 'hips'),
}
arm = bpy.data.armatures.new('PixelRig'); rig = bpy.data.objects.new('PixelRig', arm); sc.collection.objects.link(rig)
bpy.context.view_layer.objects.active = rig; bpy.ops.object.mode_set(mode='EDIT')
for name, (h, t, par) in BONES.items():
    b = arm.edit_bones.new(name); b.head = Vector(h); b.tail = Vector(t); b.roll = 0
    if par: b.parent = arm.edit_bones[par]
bpy.ops.object.mode_set(mode='OBJECT')

# --- proxy for bone heat: voxel remesh makes the scan watertight/manifold, decimate keeps it fast
bpy.ops.object.select_all(action='DESELECT')
px = ob.copy(); px.data = ob.data.copy(); px.name = 'WeightProxy'; sc.collection.objects.link(px)
bpy.context.view_layer.objects.active = px; px.select_set(True)
px.data.remesh_voxel_size = 0.018; bpy.ops.object.voxel_remesh()
m = px.modifiers.new('d', 'DECIMATE'); m.ratio = 0.25; bpy.ops.object.modifier_apply(modifier='d')
print('proxy verts', len(px.data.vertices), flush=True)
rig.select_set(True); bpy.context.view_layer.objects.active = rig
bpy.ops.object.parent_set(type='ARMATURE_AUTO')
print('proxy groups', [g.name for g in px.vertex_groups], flush=True)
assert len(px.vertex_groups) == len(BONES), 'bone heat failed'

# --- transfer to the render mesh
bpy.ops.object.select_all(action='DESELECT')
for name in BONES: ob.vertex_groups.new(name=name)
ob.select_set(True); px.select_set(True); bpy.context.view_layer.objects.active = px
bpy.ops.object.data_transfer(data_type='VGROUP_WEIGHTS', vert_mapping='POLYINTERP_NEAREST',
                             layers_select_src='ALL', layers_select_dst='NAME', mix_mode='REPLACE')
# read weights into a dense array for patching
names = list(BONES); gi = {g.name: g.index for g in ob.vertex_groups}
W = np.zeros((n, len(names)), np.float32)
for v in me.vertices:
    for g in v.groups: W[v.index, g.group] = g.weight
col = {nm: gi[nm] for nm in names}

def smooth(x): return x * x * (3 - 2 * x)
# Patch 1: ears. Thin shells: give everything above the ear base to the ear bone with a soft ramp.
for nm, (base, tip) in (('ear.R', earR), ('ear.L', earL)):
    axis = (tip - base).normalized(); d = (co - np.array(base)) @ np.array(axis)
    side = (co[:, 0] < X0) if nm == 'ear.R' else (co[:, 0] > X0)
    w = smooth(np.clip((d + 0.06) / 0.16, 0, 1)) * side * (co[:, 2] > 1.5)
    W[:, col[nm]] = w
# Patch 2: the head is one rigid ball: everything above the chin line follows the head (no face melting)
hz = smooth(np.clip((co[:, 2] - 0.84) / 0.28, 0, 1))
ears = W[:, col['ear.R']] + W[:, col['ear.L']]
rest = [c for nm, c in col.items() if nm not in ('ear.R', 'ear.L', 'head')]
W[:, rest] *= (1 - hz)[:, None]
W[:, col['head']] = np.maximum(W[:, col['head']], hz) * (1 - ears)
# Patch 4: the two front legs are fused along the midline and bone heat smears them into each other.
# Re-split the total front-leg weight left/right by x (sharp but smooth), upper/lower by height.
legs = ['arm.R', 'paw.R', 'arm.L', 'paw.L']; legT = W[:, [col[k] for k in legs]].sum(1)
xm = X0 - 0.01; sL = smooth(np.clip((co[:, 0] - (xm - 0.03)) / 0.06, 0, 1)); pf = smooth(np.clip((0.46 - co[:, 2]) / 0.16, 0, 1))
W[:, col['arm.R']] = legT * (1 - sL) * (1 - pf); W[:, col['paw.R']] = legT * (1 - sL) * pf
W[:, col['arm.L']] = legT * sL * (1 - pf); W[:, col['paw.L']] = legT * sL * pf
# normalise
s = W.sum(1); W[s < 1e-6, col['hips']] = 1; W /= W.sum(1)[:, None]
W[W < 0.01] = 0; W /= W.sum(1)[:, None]
np.save(out_blend.replace('.blend', '_weights.npy'), W)
for g in list(ob.vertex_groups): ob.vertex_groups.remove(g)
for j, nm in enumerate(names):
    g = ob.vertex_groups.new(name=nm); idx = np.where(W[:, j] > 0)[0]
    # group by rounded weight to keep the number of API calls small
    wq = np.round(W[idx, j], 2)
    for val in np.unique(wq):
        g.add(idx[wq == val].tolist(), float(val), 'REPLACE')
    print(nm, len(idx), flush=True)
bpy.data.objects.remove(px)
# --- tail: its own object with an analytic weight chain (added after bone heat so the body never follows tail bones)
nodes = PT.bone_nodes(); bpy.ops.object.select_all(action='DESELECT')
bpy.context.view_layer.objects.active = rig; bpy.ops.object.mode_set(mode='EDIT')
for i in range(PT.N_BONES):
    b = arm.edit_bones.new(f'tail{i+1}'); b.head = Vector(nodes[i]); b.tail = Vector(nodes[i + 1]); b.roll = 0
    b.parent = arm.edit_bones['hips' if i == 0 else f'tail{i}']
bpy.ops.object.mode_set(mode='OBJECT')
tail = bpy.data.objects['PixelTail']; tm = tail.data; ts = np.empty(len(tm.vertices), np.float32); tm.attributes['TailS'].data.foreach_get('value', ts)
u = np.clip((ts - 0.04) / 0.96, 0, 1) * PT.N_BONES - 0.5           # bone-index coordinate, 0 at the middle of tail1
for i in range(PT.N_BONES):
    w = np.clip(1 - np.abs(u - i), 0, 1)
    if i == 0: w = np.where(u < 0, 1, w)
    if i == PT.N_BONES - 1: w = np.where(u > i, 1, w)
    g = tail.vertex_groups.new(name=f'tail{i+1}'); wq = np.round(w, 2)
    for val in np.unique(wq[wq > 0]): g.add(np.where(wq == val)[0].tolist(), float(val), 'REPLACE')
tail.parent = rig; tmd = tail.modifiers.new('Armature', 'ARMATURE'); tmd.object = rig
tail.modifiers.move(len(tail.modifiers) - 1, 0)      # armature before subsurf
ob.parent = rig; md = ob.modifiers.new('Armature', 'ARMATURE'); md.object = rig
# eye lid coordinate for the shader blink: 0 at the bottom of each eye disc, 1 at the top
eg = np.empty(n, np.float32); me.attributes['EyeGloss'].data.foreach_get('value', eg)
ev = np.zeros(n, np.float32)
for side in (co[:, 0] < X0, co[:, 0] >= X0):
    mk = (eg > 0.5) & side
    if mk.any(): z0, z1 = co[mk, 2].min(), co[mk, 2].max(); ev[mk] = (co[mk, 2] - z0) / (z1 - z0)
a = me.attributes.new('EyeV', 'FLOAT', 'POINT'); a.data.foreach_set('value', ev)
bpy.ops.wm.save_as_mainfile(filepath=out_blend)
print('RIG_DONE')
