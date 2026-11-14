"""Pixel v3: rebuild the mascot as clean, rig-ready, all-quad parts in a standing pose, with UVs, a baked calico
texture atlas (toe beans included), real eyelids (shape keys) and a deform skeleton with IK legs.

  head   quad sphere shrink-wrapped (radial ray cast) onto the Hunyuan head; colours projected per pixel from the art
  ears, body, 4 legs, tail   modelled parametrically from the same all-quad cube topology
  eyelids   thin patches that follow the head surface, shape key 'Blink'

blender -b <v2/pixel-calico.blend> -P scripts/v3/build_v3.py -- <labels_dir> <tex_dir> <out_dir> [gpu]
"""
import bpy, sys, os, math, numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import quadparts as Q
ARGS = sys.argv[sys.argv.index('--') + 1:]; LAB, TEX, OUT = ARGS[:3]; GPU = 'gpu' in ARGS
sc = bpy.context.scene
smooth01 = Q.smooth01
def lin(h): c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]; return tuple(x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c) + (1.0,)

# ------------------------------------------------------------------ source: the v2 body (Hunyuan surface + palette)
src = bpy.data.objects['Pixel']; sme = src.data; sn = len(sme.vertices)
sco = np.empty(sn * 3, np.float32); sme.vertices.foreach_get('co', sco); sco = sco.reshape(-1, 3)
scol = np.empty(sn * 4, np.float32); sme.color_attributes['PixelColor'].data.foreach_get('color', scol); scol = scol.reshape(-1, 4)
bvh = BVHTree.FromObject(src, bpy.context.evaluated_depsgraph_get())
kd = KDTree(sn)
for i in range(sn): kd.insert(sco[i].tolist(), i)
kd.balance()
# silhouette extents of the ORIGINAL Hunyuan mesh (the art-to-mesh fit); constants from the v1 build log
EXT = {'x': (-0.8531517, 0.8531517), 'y': (-0.8823799, 0.8693611), 'z': 1.9928646}
XC = -0.17                                   # head centre line in v2 coordinates
HC = np.array([XC, -0.22, 1.36])             # ray origin inside the head
T_HEAD = np.array([0.17, -0.23, -0.06])      # moves the head group onto the new standing body

def ear_axis(side):
    m = (sco[:, 0] < XC) if side < 0 else (sco[:, 0] > XC)
    tip = sco[m][sco[m][:, 2].argmax()].astype(float)
    return tip + np.array([-side * 0.10, 0.02, -0.36]), tip
EARS = {'R': ear_axis(-1), 'L': ear_axis(+1)}

# ------------------------------------------------------------------ head: quad sphere shrink-wrapped radially
NH = 40
P, quads, fids, fuv = Q.cube_grid(NH, NH, NH); D = Q.spherify(P); D /= np.linalg.norm(D, axis=1)[:, None]
rad = np.full(len(D), np.nan)
for i, d in enumerate(D):
    loc, nrm, _, dist = bvh.ray_cast(Vector(HC.tolist()), Vector(d.tolist()), 1.3)
    if loc is None: continue
    dx = abs(loc.x - XC)
    if loc.z < 0.95: continue                              # below the chin crease: that is chest, not head
    if loc.z > 1.84 - 0.9 * dx * dx: continue              # ear shells (rebuilt as their own parts)
    rad[i] = dist
E = np.unique(np.sort(np.concatenate([quads[:, [0, 1]], quads[:, [1, 2]], quads[:, [2, 3]], quads[:, [3, 0]]]), axis=1), axis=0)
miss = np.isnan(rad); print('head rays', len(D), 'missed (neck/ears, filled by relaxation)', int(miss.sum()), flush=True)
rad[miss] = np.nanmedian(rad); deg = np.zeros(len(D)); np.add.at(deg, E[:, 0], 1); np.add.at(deg, E[:, 1], 1)
for _ in range(600):                                        # harmonic fill of the missed directions
    acc = np.zeros(len(D)); np.add.at(acc, E[:, 0], rad[E[:, 1]]); np.add.at(acc, E[:, 1], rad[E[:, 0]])
    rad[miss] = (acc / deg)[miss]
for _ in range(2):                                          # take the voxel-remesh grain off the surface
    acc = np.zeros(len(D)); np.add.at(acc, E[:, 0], rad[E[:, 1]]); np.add.at(acc, E[:, 1], rad[E[:, 0]])
    rad = 0.6 * rad + 0.4 * acc / deg
HV = HC[None] + rad[:, None] * D                            # head vertices in v2 coordinates

PARTS = []      # dicts: name, P (rest coords), quads, uv (per quad corner), atlas ('A'/'B'), attrs {name: (type, data)}
def part(name, Pv, quads, fids, fuv, atlas, rect, part_id, attrs=None, subsurf=2):
    a = {'Part': ('FLOAT', np.full(len(Pv), part_id, np.float32)), 'RestCo': ('FLOAT_VECTOR', Pv.astype(np.float32))}
    a.update(attrs or {})
    PARTS.append(dict(name=name, P=Pv, quads=quads, uv=Q.atlas_uv(fids, fuv, rect), atlas=atlas, attrs=a, subsurf=subsurf))

def make_object(p):
    me = bpy.data.meshes.new(p['name'] + 'Mesh'); me.from_pydata(p['P'].tolist(), [], p['quads'].tolist()); me.update()
    for poly in me.polygons: poly.use_smooth = True
    uvl = me.uv_layers.new(name='UVMap'); uvl.data.foreach_set('uv', p['uv'].astype(np.float32).ravel())
    for nm, (typ, data) in p['attrs'].items():
        at = me.attributes.new(nm, typ, 'POINT')
        at.data.foreach_set({'FLOAT': 'value', 'FLOAT_VECTOR': 'vector', 'FLOAT_COLOR': 'color'}[typ], np.asarray(data, np.float32).ravel())
    ob = bpy.data.objects.new(p['name'], me); sc.collection.objects.link(ob); p['ob'] = ob; return ob

# head normals (needed for the projection) from a temporary mesh at v2 coordinates
tmp = bpy.data.meshes.new('tmp'); tmp.from_pydata(HV.tolist(), [], quads.tolist()); tmp.update()
HN = np.empty(len(HV) * 3, np.float32); tmp.vertices.foreach_get('normal', HN); HN = HN.reshape(-1, 3); bpy.data.meshes.remove(tmp)
if (HN * D).sum() < 0: HN = -HN; quads = quads[:, ::-1]; fuv = fuv[:, ::-1]
# which art view colours each head vertex (same rule as v1/v2: best-facing, unoccluded, has data), kept as soft weights
VIEWS = [('front', (0, -1, 0), (1, 0, 0), False, 1.3), ('side', (-1, 0, 0), (0, -1, 0), False, 1.0),
         ('back', (0, 1, 0), (-1, 0, 0), True, 1.0), ('side', (1, 0, 0), (0, 1, 0), True, 0.45)]
best = np.zeros(len(HV), np.float32); win = np.full(len(HV), -1)
for k, (name, d, ua, mirror, wt) in enumerate(VIEWS):
    z = np.load(f'{LAB}/{name}.npz'); L = z['lab']; x0, y0, x1, y1 = [float(v) for v in z['bbox']]
    if mirror: L = L[:, ::-1]; W_ = L.shape[1]; x0, x1 = W_ - 1 - x1, W_ - 1 - x0
    d = np.array(d, np.float32); u = HV @ np.array(ua, float)
    lo, hi = EXT['x' if ua[0] else 'y']; umin, umax = (lo, hi) if sum(ua) > 0 else (-hi, -lo)
    px = x0 + (u - umin) / (umax - umin) * (x1 - x0); py = y1 - HV[:, 2] / EXT['z'] * (y1 - y0)
    lab = L[np.clip(py.round().astype(int), 0, L.shape[0] - 1), np.clip(px.round().astype(int), 0, L.shape[1] - 1)]
    w = (HN @ d) * wt; dv = Vector(d.tolist())
    for i in np.where((w > best) & (w > 0.02) & (lab != 255))[0]:
        if bvh.ray_cast(Vector(HV[i].tolist()) + Vector(HN[i].tolist()) * 4e-3 + dv * 4e-3, dv)[0] is None: best[i] = w[i]; win[i] = k
one = np.zeros((len(HV), 5), np.float32); one[np.arange(len(HV)), np.where(win < 0, 4, win)] = 1
for _ in range(3):
    acc = np.zeros_like(one); np.add.at(acc, E[:, 0], one[E[:, 1]]); np.add.at(acc, E[:, 1], one[E[:, 0]])
    one = 0.5 * one + 0.5 * acc / deg[:, None]
fallcol = np.array([scol[kd.find(v.tolist())[1]] for v in HV], np.float32)
# the fallback colours come from v2 vertex colours, which still carry speckle: diffuse them into clean patches
pal3 = np.array([[0.85, 0.85, 0.85], list(lin('1C1B1B')[:3]), list(lin('F4A068')[:3])], np.float32)
fl_lab = ((fallcol[:, None, :3] - pal3[None]) ** 2).sum(2).argmin(1); foh = np.eye(3, dtype=np.float32)[fl_lab]
for _ in range(25):
    acc = np.zeros_like(foh); np.add.at(acc, E[:, 0], foh[E[:, 1]]); np.add.at(acc, E[:, 1], foh[E[:, 0]])
    foh = 0.5 * foh + 0.5 * acc / deg[:, None]
fallcol = np.concatenate([pal3[foh.argmax(1)], np.ones((len(HV), 1), np.float32)], 1)
print('head view winners', np.bincount(np.where(win < 0, 4, win), minlength=5), flush=True)
part('Head', HV + T_HEAD, quads, fids, fuv, 'A', (0, 0.35, 1, 1), 3, subsurf=1, attrs={
    'ProjCo': ('FLOAT_VECTOR', HV), 'ViewW': ('FLOAT_COLOR', one[:, :4]), 'Fallback': ('FLOAT', one[:, 4]), 'FallbackCol': ('FLOAT_COLOR', fallcol)})

# ------------------------------------------------------------------ ears: flattened tapered quad shells, concave pink inner
for nm, (base, tip) in EARS.items():
    side = 1 if nm == 'L' else -1
    axis = tip - base; axis /= np.linalg.norm(axis); b0 = base - axis * 0.10; Lr = np.linalg.norm(tip - b0)
    nf = np.array([side * 0.35, -1, 0.1]); nf /= np.linalg.norm(nf)
    e1 = np.cross(axis, nf); e1 /= np.linalg.norm(e1); e2 = np.cross(e1, axis)
    if e2[1] > 0: e2 = -e2
    Pc, qd, fi, fu = Q.cube_grid(8, 4, 12); u, v, t, r = Q.disc(Pc)
    w = 0.25 * (1 - t) ** 0.7 + 0.026; h = 0.07 * (1 - t) + 0.028
    bump = smooth01(t / 0.15) * smooth01((0.92 - t) / 0.3)
    pos = b0[None] + axis[None] * (Lr * t)[:, None] + (w * u)[:, None] * e1[None] + (h * v)[:, None] * e2[None]
    pos -= e2[None] * (0.05 * smooth01(v) * (1 - u * u) * bump)[:, None]
    pos += axis[None] * (np.where(Pc[:, 2] > 0.999, 0.03 * np.sqrt(np.clip(1 - r * r, 0, 1)), 0))[:, None]
    inner = smooth01((v - 0.5) / 0.12) * smooth01((0.80 - np.abs(u)) / 0.12) * smooth01((t - 0.05) / 0.08) * smooth01((0.90 - t) / 0.1)
    part('Ear.' + nm, pos + T_HEAD, qd, fi, fu, 'B', (0.5, 0.5, 0.75, 1) if nm == 'L' else (0.75, 0.5, 1, 1), 4,
         attrs={'EarInner': ('FLOAT', inner), 'AxisT': ('FLOAT', t)})

# ------------------------------------------------------------------ body: superellipsoid on the cube-sphere topology
BC = np.array([0, 0.05, 0.78])
Pc, qd, fi, fu = Q.cube_grid(16, 22, 14); d = Q.spherify(Pc)
# one smooth torso: straight belly, gently arched back, a touch fuller at the chest. No dips (an earlier version raised
# the chest and tucked the rear, which read as a broken waist).
rear = smooth01((d[:, 1] - 0.05) / 0.9)                       # 0 at mid-body -> 1 at the rump
body = np.stack([0.50 * d[:, 0] * (1 + 0.03 * -d[:, 1]) * (1 - 0.13 * rear), 0.76 * d[:, 1], 0.44 * d[:, 2] * (1 - 0.10 * rear)], 1)   # slim waist / hips that flow into the rump
body[:, 2] = np.where(body[:, 2] < 0, body[:, 2] * 0.88, body[:, 2])
body[:, 2] += 0.035 * (1 - d[:, 1] ** 2)
part('Body', body + BC, qd, fi, fu, 'A', (0, 0, 0.7, 0.35), 0)
def body_level(p):
    """implicit torso: returns (level, q, offset) with level < 1 inside the body surface, q = p - centre - arch offset"""
    q = p - BC[None]; dy = np.clip(q[:, 1] / 0.76, -1, 1); off = np.stack([np.zeros(len(p)), np.zeros(len(p)), 0.035 * (1 - dy ** 2)], 1)
    q = q - off; rr = smooth01((dy - 0.05) / 0.9)
    sx = 0.50 * (1 + 0.03 * -dy) * (1 - 0.13 * rr); sz = 0.44 * (1 - 0.10 * rr) * np.where(q[:, 2] < 0, 0.88, 1.0)
    return np.sqrt((q[:, 0] / sx) ** 2 + (q[:, 1] / 0.76) ** 2 + (q[:, 2] / sz) ** 2), q, off
# neck: a soft tapered bridge so the head flows into the chest instead of sitting on it
NECK_A, NECK_B = np.array([0, -0.26, 0.92]), np.array([0, -0.46, 1.26])
Pc, qd, fi, fu = Q.cube_grid(10, 10, 8); u, v, t, r = Q.disc(Pc)
cen = NECK_A[None] + (NECK_B - NECK_A)[None] * t[:, None]
neck = cen + np.stack([(0.44 - 0.07 * t) * u, (0.40 - 0.07 * t) * v, np.zeros_like(u)], 1)
dome = np.sqrt(np.clip(1 - r * r, 0, 1))
neck[:, 2] += np.where(Pc[:, 2] > 0.999, 0.10 * dome, 0) - np.where(Pc[:, 2] < -0.999, 0.10 * dome, 0)
part('Neck', neck, qd, fi, fu, 'A', (0.7, 0, 1, 0.35), 0, attrs={'AxisT': ('FLOAT', t)})

# ------------------------------------------------------------------ legs: quad-capped tubes with a paw, edge loops through the knee
LEGS = {'FL': (0.28, -0.40), 'FR': (-0.28, -0.40), 'HL': (0.28, 0.48), 'HR': (-0.28, 0.48)}
HIP_Z, KNEE_Z, ANKLE_Z, LEG_TOP = 0.50, 0.28, 0.06, 0.74
for i, (nm, (lx, ly)) in enumerate(LEGS.items()):
    front = nm[0] == 'F'; sidex = 1 if lx > 0 else -1
    Pc, qd, fi, fu = Q.cube_grid(10, 10, 20); u, v, t, r = Q.disc(Pc)
    top = LEG_TOP if front else LEG_TOP - 0.08; z = 0.03 + t * (top - 0.03)
    g = lambda c, w_: np.exp(-((z - c) / w_) ** 2)
    # centre line: paw set forward, a slight elbow (front) or hock + forward thigh (hind)
    yc = ly - 0.07 * smooth01((0.16 - z) / 0.16) + (0.035 * g(0.40, 0.16) if front else 0.06 * g(0.24, 0.11) - 0.07 * g(0.56, 0.2))
    xc = lx - sidex * (0.07 if front else 0.10) * smooth01((z - 0.35) / 0.4)
    R = 0.122 + 0.068 * smooth01((0.13 - z) / 0.13) + (0.17 if front else 0.13) * smooth01((z - 0.16) / 0.58) ** 1.25      # slim ankle, paw flare, soft thigh (hind kept slim so the hips do not bulge)        # ankle -> soft thigh / shoulder
    ey = 1 + 0.28 * smooth01((0.14 - z) / 0.14) + (0.10 if front else 0.14) * smooth01((z - 0.3) / 0.4)
    phi = np.arctan2(u, -v)                                                                          # 0 at the front of the paw
    toes = 1 + 0.085 * np.cos(3.3 * phi) * smooth01((1.25 - np.abs(phi)) / 0.3) * smooth01((0.12 - z) / 0.08) * (r > 0.6)
    pos = np.stack([xc + R * toes * u, yc + R * ey * toes * v, z], 1)
    dome = np.sqrt(np.clip(1 - r * r, 0, 1))
    pos[:, 2] += np.where(Pc[:, 2] > 0.999, (0.12 if front else 0.05) * dome, 0) - np.where(Pc[:, 2] < -0.999, 0.03 * dome, 0)
    # tuck the top of the leg just under the torso skin: no exposed rim / cup where the leg meets the body,
    # the leg emerges from the body surface at a shallow angle instead
    lvl, q, off = body_level(pos); wgt = smooth01((pos[:, 2] - 0.34) / 0.16)
    tgt = np.minimum(lvl, 0.95); k = 1 + (tgt / np.maximum(lvl, 1e-6) - 1) * wgt
    pos = BC[None] + off + q * k[:, None]
    sole = (Pc[:, 2] < -0.999).astype(np.float32)
    suv = np.stack([0.5 + 0.44 * u, 0.5 - 0.44 * v, sole], 1)          # beans image: top = toes = front (-Y)
    part('Leg.' + nm, pos, qd, fi, fu, 'B', (0.25 * i, 0, 0.25 * (i + 1), 0.5), 1, attrs={'SoleUV': ('FLOAT_VECTOR', suv)})

# ------------------------------------------------------------------ tail: tube along an upright S curve
TAIL_CTRL = [(0, 0.56, 0.93, 0.165), (0, 0.86, 1.10, 0.145), (0, 1.06, 1.40, 0.14), (0, 1.08, 1.72, 0.13), (0, 0.98, 1.98, 0.12), (0, 0.80, 2.12, 0.105)]
N_TAIL = 8
Pc, qd, fi, fu = Q.cube_grid(4, 4, 40); u, v, t, r = Q.disc(Pc)
cl = Q.catmull(TAIL_CTRL, 400); ts = np.linspace(0, 1, 400)
c = np.stack([np.interp(t, ts, cl[:, k]) for k in range(4)], 1)
tan = np.stack([np.interp(t, ts, np.gradient(cl[:, k], ts)) for k in range(3)], 1); tan /= np.linalg.norm(tan, axis=1)[:, None]
e1 = np.array([1.0, 0, 0]); e2 = np.cross(tan, e1)
pos = c[:, :3] + (c[:, 3] * u)[:, None] * e1[None] + (c[:, 3] * v)[:, None] * e2
dome = np.sqrt(np.clip(1 - r * r, 0, 1)) * c[:, 3] * 0.9
pos += tan * (np.where(Pc[:, 2] > 0.999, dome, 0) - np.where(Pc[:, 2] < -0.999, dome, 0))[:, None]
part('Tail', pos, qd, fi, fu, 'B', (0, 0.5, 0.5, 1), 2, attrs={'TailS': ('FLOAT', t)})
tail_nodes = [tuple(np.array([np.interp(s, ts, cl[:, k]) for k in range(3)])) for s in np.linspace(0, 1, N_TAIL + 1)]

for p in PARTS: make_object(p)

# ------------------------------------------------------------------ eyelids: patches on the head surface, shape key 'Blink'
fz = np.load(f'{LAB}/front.npz')['bbox'].astype(float)
sx = (EXT['x'][1] - EXT['x'][0]) / (fz[2] - fz[0]); sz = EXT['z'] / (fz[3] - fz[1])
EYE_PX = ((300, 389), (538, 389)); LFRONT = np.load(f'{LAB}/front.npz')['lab']
EYES = [(EXT['x'][0] + (ex - fz[0]) * sx, (fz[3] - ey) * sz) for ex, ey in ((300, 389), (538, 389))]; EYE_R = 64 * sx
lids = []
for k, (cx, cz) in enumerate(EYES):
    na, nb = 32, 12; R = EYE_R * 1.06; verts = {True: [], False: []}; lid_px = []      # fine grid: crisp colour edges on the lid
    for closed in (False, True):
        for j in range(nb + 1):
            for i in range(na + 1):
                a = -0.985 + 1.97 * i / na; half = R * math.sqrt(1 - a * a); b = j / nb * (1.03 if closed else 0.045)      # open = a thin lash line, not a heavy brow
                x, z = cx + R * a, (cz + half) + (-2 * half) * b
                loc, nrm, _, _ = bvh.ray_cast(Vector((x, -2.0, z)), Vector((0, 1, 0)))
                if loc is None: loc, nrm = Vector((x, HC[1] - 0.6, z)), Vector((0, -1, 0))
                verts[closed].append(np.array(loc + nrm * 0.007) + T_HEAD)
                if closed: lid_px.append((fz[0] + (x - EXT['x'][0]) / sx, fz[3] - z / sz, j))
    faces = [(j * (na + 1) + i, j * (na + 1) + i + 1, (j + 1) * (na + 1) + i + 1, (j + 1) * (na + 1) + i) for j in range(nb) for i in range(na)]
    me = bpy.data.meshes.new(f'LidMesh{k}'); me.from_pydata([v.tolist() for v in verts[False]], [], faces); me.update()
    for poly in me.polygons: poly.use_smooth = True
    ob = bpy.data.objects.new('Lid.R' if k == 0 else 'Lid.L', me); sc.collection.objects.link(ob)
    ob.shape_key_add(name='Basis'); sk = ob.shape_key_add(name='Blink')
    for i, v in enumerate(verts[True]): sk.data[i].co = v.tolist()
    # lid colour = the nearest fur around the eye (sampled from the front art just outside the eye disc), with a dark lash line
    # along the lower edge, so a closed eye reads as a closed eye and not as a black bulge
    ex, ey = EYE_PX[k]; lc = []
    for px, py, j in lid_px:
        dxp, dyp = px - ex, py - ey; r_ = math.hypot(dxp, dyp)
        if r_ < 92:                                         # nearest fur just outside the eye disc: patch edges continue across the lid
            if r_ < 4: dxp, dyp, r_ = 0.0, -1.0, 1.0
            px, py = ex + dxp / r_ * 92, ey + dyp / r_ * 92
        lab_ = int(LFRONT[int(np.clip(round(py), 0, LFRONT.shape[0] - 1)), int(np.clip(round(px), 0, LFRONT.shape[1] - 1))])
        c = (0.85, 0.85, 0.85, 1) if lab_ == 0 else (lin('F4A068') if lab_ == 2 else lin('1C1B1B'))
        lc.append(lin('1C1B1B') if j == nb else c)
    la = me.attributes.new('LidCol', 'FLOAT_COLOR', 'POINT'); la.data.foreach_set('color', np.array(lc, np.float32).ravel())
    sk.slider_min, sk.slider_max = 0, 1; lids.append(ob)

# ------------------------------------------------------------------ bake the calico atlas (projection + procedural patches) and an eye-gloss mask
def node(nt, typ, **kw):
    n = nt.nodes.new(typ)
    for k, v in kw.items(): setattr(n, k, v)
    return n
def math_(nt, op, a, b=None, clamp=False):
    n = node(nt, 'ShaderNodeMath', operation=op, use_clamp=clamp)
    for sock, val in ((0, a), (1, b)):
        if val is None: continue
        if isinstance(val, (int, float)): n.inputs[sock].default_value = val
        else: nt.links.new(val, n.inputs[sock])
    return n.outputs[0]
def mix(nt, fac, a, b):
    n = node(nt, 'ShaderNodeMix', data_type='RGBA')
    for sock, val in (('Factor', fac), ('A', a), ('B', b)):
        if isinstance(val, (int, float)): n.inputs[sock].default_value = val
        elif isinstance(val, tuple): n.inputs[sock].default_value = val
        else: nt.links.new(val, n.inputs[sock])
    return n.outputs['Result']
WHITE, BLACK, ORANGE, SALMON = (0.85, 0.85, 0.85, 1), lin('1C1B1B'), lin('F4A068'), lin('E09072')

bm = bpy.data.materials.new('BakeSrc'); bm.use_nodes = True; nt = bm.node_tree; nt.nodes.clear()
attr = lambda name: node(nt, 'ShaderNodeAttribute', attribute_name=name)
rc = attr('RestCo'); sep = node(nt, 'ShaderNodeSeparateXYZ'); nt.links.new(rc.outputs['Vector'], sep.inputs[0])
def noise(scale, detail, off):
    mp = node(nt, 'ShaderNodeMapping'); mp.inputs['Location'].default_value = off; nt.links.new(rc.outputs['Vector'], mp.inputs['Vector'])
    n = node(nt, 'ShaderNodeTexNoise', noise_dimensions='3D'); n.inputs['Scale'].default_value = scale; n.inputs['Detail'].default_value = detail
    nt.links.new(mp.outputs['Vector'], n.inputs['Vector']); return n.outputs['Fac']
n1, n2, n3 = noise(2.3, 0.0, (5.3, 1.7, 8.1)), noise(13.0, 1.0, (0, 0, 0)), noise(1.4, 0.0, (9.2, 4.4, 6.0))
big = math_(nt, 'GREATER_THAN', n1, 0.50); speck = math_(nt, 'MULTIPLY', math_(nt, 'GREATER_THAN', n2, 0.70), math_(nt, 'GREATER_THAN', n1, 0.47))
omask = big; coloured = mix(nt, omask, BLACK, ORANGE)        # big clean-edged orange blobs in black, no splatter
# body: white belly and chest; the line climbs toward the chest and wobbles
wob = math_(nt, 'SUBTRACT', n3, 0.5)
belly = math_(nt, 'LESS_THAN', sep.outputs['Z'], math_(nt, 'ADD', 0.70, math_(nt, 'MULTIPLY', wob, 0.34)))            # white belly / legs / paws
# white chest and throat: everything in front of a line that leans forward with height
yfront = math_(nt, 'ADD', math_(nt, 'ADD', -0.40, math_(nt, 'MULTIPLY', math_(nt, 'SUBTRACT', sep.outputs['Z'], 1.0), -0.35)), math_(nt, 'MULTIPLY', wob, 0.30))
chestw = math_(nt, 'LESS_THAN', sep.outputs['Y'], yfront)
body_c = mix(nt, math_(nt, 'MAXIMUM', belly, chestw), coloured, WHITE)
# legs: toe beans on the soles
so = attr('SoleUV'); ssep = node(nt, 'ShaderNodeSeparateXYZ'); nt.links.new(so.outputs['Vector'], ssep.inputs[0])
beans = node(nt, 'ShaderNodeTexImage', image=bpy.data.images.load(f'{TEX}/beans.png'), extension='EXTEND'); nt.links.new(so.outputs['Vector'], beans.inputs['Vector'])
# white socks with a soft wobbly top; thighs / shoulders above them carry the body's calico so leg and torso read as one coat
sock = math_(nt, 'LESS_THAN', sep.outputs['Z'], math_(nt, 'ADD', 0.40, math_(nt, 'MULTIPLY', wob, 0.36)))
leg_coat = mix(nt, math_(nt, 'MAXIMUM', sock, chestw), coloured, WHITE)
leg_c = mix(nt, math_(nt, 'GREATER_THAN', ssep.outputs['Z'], 0.5), leg_coat, beans.outputs['Color'])
# tail: black with orange patches, black tip
tail_c = mix(nt, math_(nt, 'GREATER_THAN', attr('TailS').outputs['Fac'], 0.86), coloured, BLACK)
# ears: black outside (a few orange specks on the cat's left ear, as in the art), salmon inside
ear_out = mix(nt, math_(nt, 'MULTIPLY', speck, math_(nt, 'GREATER_THAN', sep.outputs['X'], 0.0)), BLACK, ORANGE)
ear_c = mix(nt, math_(nt, 'GREATER_THAN', attr('EarInner').outputs['Fac'], 0.5), ear_out, SALMON)
# head: per-pixel projection of the four art views, chosen by the per-vertex view weights
pc = attr('ProjCo'); psep = node(nt, 'ShaderNodeSeparateXYZ'); nt.links.new(pc.outputs['Vector'], psep.inputs[0])
vv = math_(nt, 'DIVIDE', psep.outputs['Z'], EXT['z'])
def view_tex(img, coord, lo, hi, sign):
    u = math_(nt, 'DIVIDE', math_(nt, 'SUBTRACT', coord, lo), hi - lo) if sign > 0 else math_(nt, 'DIVIDE', math_(nt, 'SUBTRACT', hi, coord), hi - lo)
    cb = node(nt, 'ShaderNodeCombineXYZ'); nt.links.new(u, cb.inputs['X']); nt.links.new(vv, cb.inputs['Y'])
    t = node(nt, 'ShaderNodeTexImage', image=bpy.data.images.load(f'{TEX}/{img}.png'), extension='EXTEND', interpolation='Cubic')
    nt.links.new(cb.outputs[0], t.inputs['Vector']); return t.outputs['Color']
cols = [view_tex('front', psep.outputs['X'], *EXT['x'], +1), view_tex('side', psep.outputs['Y'], *EXT['y'], -1),
        view_tex('back_m', psep.outputs['X'], *EXT['x'], -1), view_tex('side_m', psep.outputs['Y'], *EXT['y'], +1)]
vw = attr('ViewW'); wsep = node(nt, 'ShaderNodeSeparateColor'); nt.links.new(vw.outputs['Color'], wsep.inputs[0])
ws = [math_(nt, 'POWER', s, 8.0) for s in (wsep.outputs[0], wsep.outputs[1], wsep.outputs[2], vw.outputs['Alpha'])]
acc = None; tot = None
for wgt, colr in zip(ws, cols):
    sc_ = node(nt, 'ShaderNodeVectorMath', operation='SCALE'); nt.links.new(colr, sc_.inputs[0]); nt.links.new(wgt, sc_.inputs['Scale'])
    if acc is None: acc, tot = sc_.outputs[0], wgt
    else:
        ad = node(nt, 'ShaderNodeVectorMath', operation='ADD'); nt.links.new(acc, ad.inputs[0]); nt.links.new(sc_.outputs[0], ad.inputs[1]); acc = ad.outputs[0]
        tot = math_(nt, 'ADD', tot, wgt)
dv_ = node(nt, 'ShaderNodeVectorMath', operation='SCALE'); nt.links.new(acc, dv_.inputs[0]); nt.links.new(math_(nt, 'DIVIDE', 1.0, math_(nt, 'MAXIMUM', tot, 1e-5)), dv_.inputs['Scale'])
head_c = mix(nt, math_(nt, 'MAXIMUM', attr('Fallback').outputs['Fac'], math_(nt, 'LESS_THAN', tot, 1e-4)), dv_.outputs[0], attr('FallbackCol').outputs['Color'])
# pick the branch for this part
pid = attr('Part').outputs['Fac']; col = body_c
for k, cc in ((1, leg_c), (2, tail_c), (3, head_c), (4, ear_c)):
    col = mix(nt, math_(nt, 'LESS_THAN', math_(nt, 'ABSOLUTE', math_(nt, 'SUBTRACT', pid, float(k))), 0.5), col, cc)
# eye-gloss mask (crisp circles in the front projection)
gl = None
for cx, cz in EYES:
    d2 = math_(nt, 'ADD', math_(nt, 'POWER', math_(nt, 'SUBTRACT', psep.outputs['X'], cx), 2.0), math_(nt, 'POWER', math_(nt, 'SUBTRACT', psep.outputs['Z'], cz), 2.0))
    m = math_(nt, 'LESS_THAN', d2, (EYE_R * 0.97) ** 2); gl = m if gl is None else math_(nt, 'MAXIMUM', gl, m)
gl = math_(nt, 'MULTIPLY', math_(nt, 'MULTIPLY', gl, math_(nt, 'LESS_THAN', psep.outputs['Y'], HC[1] - 0.2)), math_(nt, 'GREATER_THAN', pid, 2.5))
gl = math_(nt, 'MULTIPLY', gl, math_(nt, 'LESS_THAN', pid, 3.5))
em = node(nt, 'ShaderNodeEmission'); outn = node(nt, 'ShaderNodeOutputMaterial'); nt.links.new(em.outputs[0], outn.inputs['Surface'])
target = node(nt, 'ShaderNodeTexImage'); nt.nodes.active = target

sc.render.engine = 'CYCLES'; sc.cycles.samples = 4; sc.cycles.use_denoising = False
if GPU:
    prefs = bpy.context.preferences.addons['cycles'].preferences; prefs.compute_device_type = 'OPTIX'; prefs.refresh_devices()
    for dd in prefs.devices: dd.use = dd.type == 'OPTIX'
    sc.cycles.device = 'GPU'
src.hide_render = True
SIZE = {'A': 4096, 'B': 4096}
imgs = {k: bpy.data.images.new('atlas' + k, s, s, alpha=False) for k, s in SIZE.items()}
masks = {'A': bpy.data.images.new('maskA', 2048, 2048, alpha=False, is_data=True)}
def bake(source, images):
    nt.links.new(source, em.inputs['Color'])
    for p in PARTS:
        if p['atlas'] not in images: continue
        ob = p['ob']; ob.data.materials.clear(); ob.data.materials.append(bm)
        target.image = images[p['atlas']]; nt.nodes.active = target
        bpy.ops.object.select_all(action='DESELECT'); ob.select_set(True); bpy.context.view_layer.objects.active = ob
        bpy.ops.object.bake(type='EMIT', margin=8, use_clear=False)
bake(col, imgs); bake(gl, masks)
os.makedirs(OUT + '/tex', exist_ok=True)
for im, nm in ((imgs['A'], 'atlasA'), (imgs['B'], 'atlasB'), (masks['A'], 'maskA')):
    im.filepath_raw = f'{OUT}/tex/{nm}.png'; im.file_format = 'PNG'; im.save()
print('baked', flush=True)

# ------------------------------------------------------------------ final materials: baked UV texture + soft toy look-dev
def final_mat(name, atlas, mask=None):
    m = bpy.data.materials.new(name); m.use_nodes = True; t = m.node_tree; b = t.nodes['Principled BSDF']
    im = node(t, 'ShaderNodeTexImage', image=atlas); t.links.new(im.outputs['Color'], b.inputs['Base Color'])
    b.inputs['Roughness'].default_value = 0.55; b.inputs['Sheen Weight'].default_value = 0.25; b.inputs['Sheen Roughness'].default_value = 0.5
    b.inputs['Subsurface Weight'].default_value = 0.12; b.inputs['Subsurface Radius'].default_value = (1.0, 0.45, 0.3); b.inputs['Subsurface Scale'].default_value = 0.012
    t.links.new(im.outputs['Color'], b.inputs['Sheen Tint'])
    if mask:
        mk = node(t, 'ShaderNodeTexImage', image=mask)
        r = node(t, 'ShaderNodeMapRange'); r.inputs['To Min'].default_value = 0.55; r.inputs['To Max'].default_value = 0.04
        t.links.new(mk.outputs['Color'], r.inputs['Value']); t.links.new(r.outputs['Result'], b.inputs['Roughness'])
        t.links.new(mk.outputs['Color'], b.inputs['Coat Weight']); b.inputs['Coat Roughness'].default_value = 0.03
        s = node(t, 'ShaderNodeMapRange'); s.inputs['To Min'].default_value = 0.12; s.inputs['To Max'].default_value = 0.0
        t.links.new(mk.outputs['Color'], s.inputs['Value']); t.links.new(s.outputs['Result'], b.inputs['Subsurface Weight'])
    return m
MAT = {'A': final_mat('PixelA', imgs['A'], masks['A']), 'B': final_mat('PixelB', imgs['B'])}
lidm = bpy.data.materials.new('PixelLid'); lidm.use_nodes = True; lb = lidm.node_tree.nodes['Principled BSDF']
lb.inputs['Base Color'].default_value = BLACK; lb.inputs['Roughness'].default_value = 0.55; lb.inputs['Sheen Weight'].default_value = 0.25
la_ = node(lidm.node_tree, 'ShaderNodeAttribute', attribute_name='LidCol'); lidm.node_tree.links.new(la_.outputs['Color'], lb.inputs['Base Color'])
for p in PARTS: p['ob'].data.materials.clear(); p['ob'].data.materials.append(MAT[p['atlas']])
for ob in lids: ob.data.materials.append(lidm)
bpy.data.objects.remove(src)
for o in list(sc.objects):
    if o.name not in [p['name'] for p in PARTS] + [l.name for l in lids]: bpy.data.objects.remove(o)

# ------------------------------------------------------------------ skeleton
arm = bpy.data.armatures.new('PixelRigV3'); rig = bpy.data.objects.new('PixelRigV3', arm); sc.collection.objects.link(rig)
bpy.context.view_layer.objects.active = rig; bpy.ops.object.mode_set(mode='EDIT')
def bone(name, h, t, parent=None, connect=False, deform=True):
    b = arm.edit_bones.new(name); b.head = Vector(h); b.tail = Vector(t); b.roll = 0; b.use_deform = deform
    if parent: b.parent = arm.edit_bones[parent]; b.use_connect = connect
    return b
bone('root', (0, 0, 0), (0, 0, 0.25), deform=False)
bone('body', (0, 0.55, 0.80), (0, 0.05, 0.80), 'root')
bone('chest', (0, 0.05, 0.80), (0, -0.50, 0.84), 'body', True)
hb = bone('head', (0, -0.40, 1.02), (0, -0.45, 1.75), 'chest'); hb.inherit_scale = 'NONE'
for nm, (base, tip) in EARS.items(): bone('ear.' + nm, base + T_HEAD, tip + T_HEAD, 'head')
for i in range(N_TAIL): bone(f'tail{i + 1}', tail_nodes[i], tail_nodes[i + 1], 'body' if i == 0 else f'tail{i}', i > 0)
for nm, (lx, ly) in LEGS.items():
    kb = 0.045 if nm[0] == 'F' else -0.045            # front elbows point back, hind knees forward: sets the IK bend direction
    bone('thigh.' + nm, (lx, ly, HIP_Z), (lx, ly + kb, KNEE_Z), 'chest' if nm[0] == 'F' else 'body')
    bone('shin.' + nm, (lx, ly + kb, KNEE_Z), (lx, ly, ANKLE_Z), 'thigh.' + nm, True)
    bone('footik.' + nm, (lx, ly, ANKLE_Z), (lx, ly - 0.15, ANKLE_Z), 'root', deform=False)
bpy.ops.object.mode_set(mode='OBJECT')
for nm in LEGS:
    c = rig.pose.bones['shin.' + nm].constraints.new('IK'); c.target = rig; c.subtarget = 'footik.' + nm; c.chain_count = 2; c.use_stretch = False
for pb in rig.pose.bones: pb.rotation_mode = 'XYZ'

def bind(ob, weights, subsurf):
    """weights: {bone: array per vertex}"""
    for bn, w in weights.items():
        g = ob.vertex_groups.new(name=bn); wq = np.round(np.asarray(w, float), 3)
        for val in np.unique(wq[wq > 0]): g.add(np.where(wq == val)[0].tolist(), float(val), 'REPLACE')
    ob.parent = rig; md = ob.modifiers.new('Armature', 'ARMATURE'); md.object = rig
    if subsurf: s = ob.modifiers.new('Subsurf', 'SUBSURF'); s.levels = min(subsurf, 1); s.render_levels = subsurf
for p in PARTS:
    nm, Pv = p['name'], p['P']; n = len(Pv); ones = np.ones(n)
    if nm == 'Head': w = {'head': ones}
    elif nm.startswith('Ear'):
        we = smooth01((p['attrs']['AxisT'][1] - 0.05) / 0.22); w = {'ear.' + nm[-1]: we, 'head': 1 - we}
    elif nm == 'Body': wc = smooth01((0.32 - Pv[:, 1]) / 0.62); w = {'chest': wc, 'body': 1 - wc}
    elif nm == 'Neck': wh = smooth01((p['attrs']['AxisT'][1] - 0.25) / 0.6); w = {'head': wh, 'chest': 1 - wh}
    elif nm.startswith('Leg'):
        ws_ = smooth01((KNEE_Z + 0.07 - Pv[:, 2]) / 0.14); wb = smooth01((Pv[:, 2] - 0.50) / 0.20)       # the soft top of the leg stays with the torso
        w = {'shin.' + nm[-2:]: ws_, 'thigh.' + nm[-2:]: (1 - ws_) * (1 - wb), ('chest' if nm[1] == 'F' else 'body'): wb}
    elif nm == 'Tail':
        uu = p['attrs']['TailS'][1] * N_TAIL - 0.5; w = {}
        for i in range(N_TAIL):
            wi = np.clip(1 - np.abs(uu - i), 0, 1)
            if i == 0: wi = np.where(uu < 0, 1, wi)
            if i == N_TAIL - 1: wi = np.where(uu > i, 1, wi)
            w[f'tail{i + 1}'] = wi
    bind(p['ob'], w, p['subsurf'])
for ob in lids:
    bind(ob, {'head': np.ones(len(ob.data.vertices))}, 0)
    so_ = ob.modifiers.new('Solidify', 'SOLIDIFY'); so_.thickness = 0.006; so_.offset = -1      # thin lids that hug the eye, not goggles

rig['pixel_v3'] = {'hip_z': HIP_Z, 'knee_z': KNEE_Z, 'ankle_z': ANKLE_Z}
for im in list(bpy.data.images):
    if im.users == 0: bpy.data.images.remove(im)
bpy.ops.file.pack_all()        # textures travel inside the .blend to every render pod
bpy.ops.wm.save_as_mainfile(filepath=f'{OUT}/pixel-v3.blend')
quads_total = sum(len(p['quads']) for p in PARTS)
print('PARTS', [(p['name'], len(p['P']), len(p['quads'])) for p in PARTS], 'total quads', quads_total, 'tris 0', flush=True)
print('BUILD_V3_DONE')
