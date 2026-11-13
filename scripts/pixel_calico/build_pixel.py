"""Import the chosen Hunyuan3D mesh, project the palette-label maps onto it as vertex colours,
set up material / lights / cameras, save the .blend and render the 4-view contact-sheet tiles.
v2: the Hunyuan mesh fuses the tail into a ring around the whole base. The ring is clamped back onto the body
footprint, the body is voxel-remeshed, and a separate tapered tail object (pixel_tail.py) is added.
blender -b -P scripts/build_pixel.py -- <glb> <labels_dir> <out_dir> [gpu]"""
import bpy, sys, os, math, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pixel_tail as PT
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree
ARGS = sys.argv[sys.argv.index('--') + 1:]; glb, LAB, OUT = ARGS[:3]; GPU = 'gpu' in ARGS
PAL_HEX = ['FFFFFF', '1C1B1B', 'F4A068', 'B6C371', 'E09072', 'F39598']
def lin(h):
    c = [int(h[i:i+2], 16) / 255 for i in (0, 2, 4)]
    return [x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c] + [1.0]
PAL = np.array([lin(h) for h in PAL_HEX], np.float32)
PAL[0, :3] = 0.85
SMOOTH_ITERS = 6
EYES_PX = [(300, 389), (538, 389)]; EYE_R_PX = 64   # eye centres / radius in the 1024px front art
PAW_Z, PAW_Y, PAW_X = 0.27, -0.22, 0.56   # region (fraction of height, world y, world x) forced white   # pure 1.0 white clips under studio light; keep it a soft white

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
bpy.ops.import_scene.gltf(filepath=glb)
ob = [o for o in sc.objects if o.type == 'MESH'][0]
bpy.context.view_layer.objects.active = ob; ob.select_set(True)
bpy.ops.object.parent_clear(type='CLEAR_KEEP_TRANSFORM')
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
for o in list(sc.objects):
    if o != ob: bpy.data.objects.remove(o)
ob.name = 'Pixel'; me = ob.data; me.name = 'PixelMesh'
n = len(me.vertices)
co = np.empty(n * 3, np.float32); me.vertices.foreach_get('co', co); co = co.reshape(-1, 3)
co[:, 2] -= co[:, 2].min(); co[:, 0] -= (co[:, 0].min() + co[:, 0].max()) / 2
me.vertices.foreach_set('co', co.ravel()); me.update()
# projection fit uses the ORIGINAL silhouette (the art includes the tail), so record extents before the tail fix
EXT = {'x': (co[:, 0].min(), co[:, 0].max()), 'y': (co[:, 1].min(), co[:, 1].max()), 'z': (0.0, co[:, 2].max())}
# --- tail fix: clamp the fused tail ring / side lumps onto the body footprint ellipse, then voxel-remesh
def smooth01(x): x = np.clip(x, 0, 1); return x * x * (3 - 2 * x)
dx, dy = co[:, 0] - PT.BODY_C[0], co[:, 1] - PT.BODY_C[1]; rad = np.hypot(dx, dy); th = np.arctan2(dy, dx)
# body profile just above the tail ring (z 0.50-0.58), per angle: the base is clamped to this (slightly flared) outline
NB = 90; bins = ((th + np.pi) / (2 * np.pi) * NB).astype(int) % NB; ref = (co[:, 2] > 0.50) & (co[:, 2] < 0.58)
prof = np.array([rad[ref & (bins == i)].max() if (ref & (bins == i)).any() else np.nan for i in range(NB)])
prof = np.where(np.isnan(prof), np.nanmean(prof), prof)
for _ in range(4): prof = (np.roll(prof, 1) + 2 * prof + np.roll(prof, -1)) / 4
fb = (th + np.pi) / (2 * np.pi) * NB - 0.5; i0 = np.floor(fb).astype(int); w1 = fb - i0
limit = (prof[i0 % NB] * (1 - w1) + prof[(i0 + 1) % NB] * w1) * (1 + 0.03 * smooth01((0.5 - co[:, 2]) / 0.5)) * (1 - 0.13 * smooth01((0.14 - co[:, 2]) / 0.14) ** 2)   # slight flare, rounded bottom edge
strength = smooth01((co[:, 1] + 0.30) / 0.12) * smooth01((0.60 - co[:, 2]) / 0.08)     # leave front paws / chest / upper body alone
# compress (not collapse) what sticks out, so the squashed tail keeps a thin ordered shell the voxel remesh can resolve
target = limit + 0.02 * np.tanh((rad - limit) / 0.1)
k = np.where(rad > limit, 1 + (target / np.maximum(rad, 1e-6) - 1) * strength, 1.0)
co[:, 0] = PT.BODY_C[0] + dx * k; co[:, 1] = PT.BODY_C[1] + dy * k
print('tail clamp moved', int((k < 0.999).sum()), 'verts', flush=True)
me.vertices.foreach_set('co', co.ravel()); me.update()
me.remesh_voxel_size = 0.008; bpy.ops.object.voxel_remesh()
me = ob.data; n = len(me.vertices)
co = np.empty(n * 3, np.float32); me.vertices.foreach_get('co', co); co = co.reshape(-1, 3)
ed0 = np.empty(len(me.edges) * 2, np.int32); me.edges.foreach_get('vertices', ed0); ed0 = ed0.reshape(-1, 2)
ax, by = PT.body_radii(co[:, 2]); r = np.hypot((co[:, 0] - PT.BODY_C[0]) / ax, (co[:, 1] - PT.BODY_C[1]) / by)
band = (smooth01((r - 0.70) / 0.12) * smooth01((0.66 - co[:, 2]) / 0.12) * smooth01((co[:, 1] + 0.34) / 0.12))[:, None]
deg0 = np.zeros(n, np.float32); np.add.at(deg0, ed0[:, 0], 1); np.add.at(deg0, ed0[:, 1], 1)
for _ in range(120):     # relax the clamped band so the haunch reads as a soft seated body, not a cut wall
    acc = np.zeros_like(co); np.add.at(acc, ed0[:, 0], co[ed0[:, 1]]); np.add.at(acc, ed0[:, 1], co[ed0[:, 0]])
    co = co + 0.6 * band * (acc / deg0[:, None] - co)
co[:, 2] = np.maximum(co[:, 2], 0)
me.vertices.foreach_set('co', co.ravel()); me.update()
for p in me.polygons: p.use_smooth = True
no = np.empty(n * 3, np.float32); me.vertices.foreach_get('normal', no); no = no.reshape(-1, 3)
print('verts', n, 'bounds', co.min(0), co.max(0), flush=True)

bvh = BVHTree.FromObject(ob, bpy.context.evaluated_depsgraph_get())
# view: (label file, direction surface->camera, world axis of image-right, mirror art, weight)
VIEWS = [('front', (0, -1, 0), (1, 0, 0), False, 1.3),
         ('side',  (-1, 0, 0), (0, -1, 0), False, 1.0),   # art shows the cat's right side, facing image-right
         ('back',  (0, 1, 0), (-1, 0, 0), True, 1.0),     # generated back art has the tail on the wrong side -> mirror
         ('side',  (1, 0, 0), (0, 1, 0), True, 0.45)]     # no left-side art: mirrored right side, low priority
best_w = np.zeros(n, np.float32); label = np.full(n, 255, np.uint8)
for name, d, ua, mirror, wt in VIEWS:
    z = np.load(f'{LAB}/{name}.npz'); L = z['lab']; x0, y0, x1, y1 = [float(v) for v in z['bbox']]
    if mirror:
        L = L[:, ::-1]; W = L.shape[1]; x0, x1 = W - 1 - x1, W - 1 - x0
    d = np.array(d, np.float32); u = co @ np.array(ua, np.float32)
    lo, hi = EXT['x' if ua[0] else 'y']; umin, umax = (lo, hi) if sum(ua) > 0 else (-hi, -lo)
    px = x0 + (u - umin) / (umax - umin) * (x1 - x0)
    py = y1 - co[:, 2] / EXT['z'][1] * (y1 - y0)
    lab = L[np.clip(py.round().astype(int), 0, L.shape[0] - 1), np.clip(px.round().astype(int), 0, L.shape[1] - 1)]
    w = (no @ d) * wt
    cand = np.where((w > best_w + 0.0) & (w > 0.02) & (lab != 255))[0]
    dv = Vector(d.tolist()); vis = 0
    for i in cand:
        o = Vector(co[i].tolist()) + Vector(no[i].tolist()) * 2e-3 + dv * 2e-3
        if bvh.ray_cast(o, dv)[0] is None:
            best_w[i] = w[i]; label[i] = lab[i]; vis += 1
    print(name, 'candidates', len(cand), 'visible', vis, flush=True)
# face features only where the front view sees them well; underside is white
un = np.where(label == 255)[0]; kn = np.where(label != 255)[0]
print('unlabelled', len(un), flush=True)
kd = KDTree(len(kn))
for j, i in enumerate(kn): kd.insert(co[i].tolist(), j)
kd.balance()
for i in un: label[i] = label[kn[kd.find(co[i].tolist())[1]]]
# a couple of majority-vote passes over mesh edges to remove single-vertex noise
ed = np.empty(len(me.edges) * 2, np.int32); me.edges.foreach_get('vertices', ed); ed = ed.reshape(-1, 2)
onehot = np.eye(6, dtype=np.float32)[label]
deg = np.zeros(n, np.float32); np.add.at(deg, ed[:, 0], 1); np.add.at(deg, ed[:, 1], 1)
for _ in range(SMOOTH_ITERS):   # diffuse the one-hot labels along edges, then re-quantize: rounds off projection stair-steps
    acc = np.zeros_like(onehot); np.add.at(acc, ed[:, 0], onehot[ed[:, 1]]); np.add.at(acc, ed[:, 1], onehot[ed[:, 0]])
    onehot = 0.5 * onehot + 0.5 * acc / np.maximum(deg, 1)[:, None]
# the clamped base band is near-vertical remeshed wall where the projected (old tail) art turns to speckle: smooth it hard
bandm = ((co[:, 2] < 0.46) & (co[:, 1] > -0.15)).astype(np.float32)[:, None]
for _ in range(60):
    acc = np.zeros_like(onehot); np.add.at(acc, ed[:, 0], onehot[ed[:, 1]]); np.add.at(acc, ed[:, 1], onehot[ed[:, 0]])
    onehot = onehot + bandm * 0.6 * (acc / np.maximum(deg, 1)[:, None] - onehot)
label = onehot.argmax(1).astype(np.uint8)
# front paws / lower front legs are white in the art; leftover leg-line blobs and the side art's tail land there
H0 = co[:, 2].max()
paw = (label == 1) & (co[:, 2] < PAW_Z * H0) & (co[:, 1] < PAW_Y) & (co[:, 0] < PAW_X)
print('paw whitening', int(paw.sum()), flush=True); label[paw] = 0
np.save(f'{OUT}/vertex_labels.npy', label)
print('label counts', np.bincount(label, minlength=6), flush=True)

ca = me.color_attributes.new('PixelColor', 'FLOAT_COLOR', 'POINT')
ca.data.foreach_set('color', PAL[label].ravel())
# eye mask (iris + enclosed pupil region) for a glossy eye
ea = me.attributes.new('EyeGloss', 'FLOAT', 'POINT')
eye = np.zeros(n, np.float32)
fz = np.load(f'{LAB}/front.npz')['bbox'].astype(float); sx = (EXT['x'][1] - EXT['x'][0]) / (fz[2] - fz[0]); sz = EXT['z'][1] / (fz[3] - fz[1])
for ex, ey in EYES_PX:
    wx = EXT['x'][0] + (ex - fz[0]) * sx; wz = (fz[3] - ey) * sz
    eye[(np.hypot(co[:, 0] - wx, co[:, 2] - wz) < EYE_R_PX * sx) & (no[:, 1] < -0.15) & (co[:, 1] < 0)] = 1
ea.data.foreach_set('value', eye)

mat = bpy.data.materials.new('PixelFlat'); mat.use_nodes = True; nt = mat.node_tree
bsdf = nt.nodes['Principled BSDF']
at = nt.nodes.new('ShaderNodeAttribute'); at.attribute_name = 'PixelColor'
nt.links.new(at.outputs['Color'], bsdf.inputs['Base Color'])
eg = nt.nodes.new('ShaderNodeAttribute'); eg.attribute_name = 'EyeGloss'
mr = nt.nodes.new('ShaderNodeMapRange'); mr.inputs['To Min'].default_value = 0.6; mr.inputs['To Max'].default_value = 0.08
nt.links.new(eg.outputs['Fac'], mr.inputs['Value']); nt.links.new(mr.outputs['Result'], bsdf.inputs['Roughness'])
me.materials.clear(); me.materials.append(mat)

# --- the new tail: its own object, same flat material, black with orange patches
TV, TF, TS, _ = PT.tube(); SEG = 28
tm = bpy.data.meshes.new('PixelTailMesh'); tm.from_pydata(TV.tolist(), [], TF); tm.update()
for p in tm.polygons: p.use_smooth = True
tail = bpy.data.objects.new('PixelTail', tm); sc.collection.objects.link(tail)
tc = tm.color_attributes.new('PixelColor', 'FLOAT_COLOR', 'POINT'); tc.data.foreach_set('color', PAL[PT.tail_labels(TV, TS, SEG)].ravel())
ta = tm.attributes.new('TailS', 'FLOAT', 'POINT'); ta.data.foreach_set('value', TS.astype(np.float32))
sub = tail.modifiers.new('Subsurf', 'SUBSURF'); sub.levels = 1; sub.render_levels = 2
tm.materials.append(mat)

# --- stage: floor/backdrop, lights, cameras
H = float(co[:, 2].max()); ctr = Vector((0, 0.0, H * 0.5))
bpy.ops.mesh.primitive_plane_add(size=60, location=(0, 0, 0)); fl = bpy.context.object; fl.name = 'Floor'
fm = bpy.data.materials.new('Backdrop'); fm.use_nodes = True
fm.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (0.80, 0.86, 0.93, 1)
fm.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value = 0.9
fl.data.materials.append(fm); fl.is_shadow_catcher = True; sc.render.film_transparent = True
w = bpy.data.worlds.new('World'); sc.world = w; w.use_nodes = True
bg = w.node_tree.nodes['Background']; bg.inputs[0].default_value = (1, 1, 1, 1); bg.inputs[1].default_value = 0.35
def area(name, loc, energy, size):
    l = bpy.data.lights.new(name, 'AREA'); l.energy = energy; l.size = size
    o = bpy.data.objects.new(name, l); sc.collection.objects.link(o); o.location = loc
    o.rotation_euler = (ctr - Vector(loc)).to_track_quat('-Z', 'Y').to_euler(); return o
rig = bpy.data.objects.new('LightRig', None); sc.collection.objects.link(rig)
for o in (area('Key', (-3.5, -4.5, 5.0), 260, 4), area('Fill', (4.5, -3.0, 2.5), 90, 5), area('Rim', (1.5, 5.0, 4.0), 160, 3)):
    o.parent = rig
def camera(name, az, el, ortho=None, lens=85, dist=9.0, look=None):
    c = bpy.data.cameras.new(name)
    if ortho: c.type = 'ORTHO'; c.ortho_scale = ortho
    else: c.lens = lens
    o = bpy.data.objects.new(name, c); sc.collection.objects.link(o)
    a, e = math.radians(az), math.radians(el); tgt = look or ctr
    dvec = Vector((math.sin(a) * math.cos(e), -math.cos(a) * math.cos(e), math.sin(e)))
    o.location = tgt + dvec * dist; o.rotation_euler = (-dvec).to_track_quat('-Z', 'Y').to_euler(); return o
sheet = {'front': 0, 'three_quarter': -35, 'side': -90, 'back': 180}   # same order/facing as the turnaround sheet
cams = {k: camera('Sheet_' + k, az, 4, ortho=H * 1.25) for k, az in sheet.items()}
hero = camera('Hero', -28, 12, lens=85, dist=6.8, look=ctr + Vector((0.1, 0, -0.03)))

sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.samples = 48; sc.cycles.use_denoising = True
if GPU:
    prefs = bpy.context.preferences.addons['cycles'].preferences; prefs.compute_device_type = 'OPTIX'; prefs.refresh_devices()
    for d in prefs.devices: d.use = d.type == 'OPTIX'
    sc.cycles.device = 'GPU'; sc.cycles.samples = 128
sc.view_settings.view_transform = 'Standard'
sc.render.resolution_x = sc.render.resolution_y = 720
sc.camera = hero
bpy.ops.wm.save_as_mainfile(filepath=f'{OUT}/pixel-calico.blend')
for k, c in cams.items():
    sc.camera = c; rig.rotation_euler = (0, 0, math.radians(sheet[k]))   # light follows the camera for even tiles
    sc.render.filepath = f'{OUT}/sheet/{k}.png'; bpy.ops.render.render(write_still=True)
print('BUILD_DONE')
