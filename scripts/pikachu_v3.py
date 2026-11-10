"""Sleepy Pikachu on a rocking Poke Ball, version 3 (sculpted anime-style body).

Rebuilt from the reference GIF: one sculpted SDF body mesh with painted details, rigged head and
breathing, lofted ears with ink tips, a rounded lightning tail, surface-fitted face
details, a teardrop sleep bubble, and a 4.5-second seamless rock loop with lagged
ears and tail. Renders require an OptiX GPU; the script refuses CPU fallback.

Usage: blender -b --python-exit-code 1 --python scripts/pikachu_v2.py -- \
    --output results/pikachu-v3 [--percent 50] [--samples 16] [--frames 1,28] [--no-export]
"""
import argparse
import json
import math
import sys
import time
from pathlib import Path

import bpy
from mathutils import Matrix, Quaternion, Vector

# ---------------------------------------------------------------- arguments
ap = argparse.ArgumentParser()
ap.add_argument('--output', type=Path, default=Path('results/pikachu-v3'))
ap.add_argument('--frames', default='')
ap.add_argument('--percent', type=int, default=100)
ap.add_argument('--samples', type=int, default=128)
ap.add_argument('--no-export', action='store_true')
ap.add_argument('--no-render', action='store_true')
args = ap.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else [])
out = args.output.resolve()
(out / 'frames').mkdir(parents=True, exist_ok=True)

N = 108            # loop length: 4.5 s at 24 fps, same period as the reference GIF
FPS = 24
R = 0.86           # ball radius
YAW = math.radians(46)   # turn the face toward the camera

# ---------------------------------------------------------------- scene setup
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.engine = 'CYCLES'
scene.cycles.samples = args.samples
scene.cycles.use_adaptive_sampling = True
scene.cycles.adaptive_threshold = 0.02
scene.cycles.use_denoising = True
scene.cycles.max_bounces = 8
scene.cycles.transmission_bounces = 8
scene.render.use_persistent_data = True
scene.render.resolution_x = 1440
scene.render.resolution_y = 1080
scene.render.resolution_percentage = args.percent
scene.render.fps = FPS
scene.frame_start = 1
scene.frame_end = N
scene.render.image_settings.file_format = 'PNG'
scene.render.image_settings.color_mode = 'RGB'
scene.view_settings.view_transform = 'Khronos PBR Neutral'
scene.view_settings.exposure = -0.55

devices = []
if not args.no_render:
    prefs = bpy.context.preferences.addons['cycles'].preferences
    prefs.compute_device_type = 'OPTIX'
    prefs.refresh_devices()
    for d in prefs.devices:
        d.use = d.type == 'OPTIX'
        devices.append(dict(name=d.name, type=d.type, enabled=bool(d.use)))
    assert any(d['enabled'] for d in devices), 'OptiX GPU required'
    scene.cycles.device = 'GPU'

world = bpy.data.worlds.new('Cream studio')
scene.world = world
world.use_nodes = True
bg = world.node_tree.nodes['Background']
bg.inputs[0].default_value = (1.0, 0.97, 0.92, 1)
bg.inputs[1].default_value = 0.5


# ---------------------------------------------------------------- materials
def material(name, color, rough=0.45, coat=0.0, sss=0.0, sheen=0.0, transmission=0.0, ior=1.45):
    m = bpy.data.materials.new(name)
    m.diffuse_color = (*color, 1)
    m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (*color, 1)
    b.inputs['Roughness'].default_value = rough
    b.inputs['IOR'].default_value = ior
    if coat:
        b.inputs['Coat Weight'].default_value = coat
        b.inputs['Coat Roughness'].default_value = 0.08
    if sss:
        b.inputs['Subsurface Weight'].default_value = sss
        b.inputs['Subsurface Radius'].default_value = (0.9, 0.55, 0.25)
        b.inputs['Subsurface Scale'].default_value = 0.04
    if sheen:
        b.inputs['Sheen Weight'].default_value = sheen
        b.inputs['Sheen Roughness'].default_value = 0.4
    if transmission:
        b.inputs['Transmission Weight'].default_value = transmission
    return m


YELLOW = material('Pikachu yellow', (1.0, 0.62, 0.01), rough=0.5, sss=0.12, sheen=0.25)
INK = material('Ear tip ink', (0.018, 0.024, 0.045), rough=0.45)
FACE_INK = material('Face ink', (0.02, 0.022, 0.035), rough=0.3)
CHEEK = material('Cheek red', (0.95, 0.12, 0.07), rough=0.38, sss=0.1)
BALL_RED = material('Ball red', (0.80, 0.055, 0.025), rough=0.22, coat=0.6)
BALL_WHITE = material('Ball white', (0.90, 0.90, 0.92), rough=0.25, coat=0.6)
NAVY = material('Ball navy', (0.022, 0.04, 0.075), rough=0.35)
BUTTON_PINK = material('Button blush', (0.97, 0.62, 0.55), rough=0.3, coat=0.4)
BUBBLE = material('Sleep bubble', (0.10, 0.50, 1.0), rough=0.05, transmission=0.12, ior=1.33, coat=0.8)
FLOOR = material('Studio floor', (0.97, 0.95, 0.91), rough=0.8)
TOY_RED = material('Toy red', (0.88, 0.12, 0.05), rough=0.35, coat=0.3)
TOY_BLUE = material('Toy blue', (0.20, 0.62, 0.98), rough=0.35, coat=0.3)
TOY_YELLOW = material('Toy yellow', (1.0, 0.72, 0.04), rough=0.4)
BROWN = material('Tail base brown', (0.16, 0.05, 0.012), rough=0.5)
BODY_MAT = material('Pikachu painted fur', (1, 1, 1), rough=0.5, sss=0.10, sheen=0.25)
_n = BODY_MAT.node_tree.nodes
_ca = _n.new('ShaderNodeVertexColor')
_ca.layer_name = 'Col'
BODY_MAT.node_tree.links.new(_ca.outputs['Color'], _n['Principled BSDF'].inputs['Base Color'])
HIGHLIGHT = material('Bubble glint', (1, 1, 1), rough=0.1)
hl = HIGHLIGHT.node_tree.nodes['Principled BSDF']
hl.inputs['Emission Color'].default_value = (1, 1, 1, 1)
hl.inputs['Emission Strength'].default_value = 2.0


# ---------------------------------------------------------------- helpers
def link(obj):
    scene.collection.objects.link(obj)
    return obj


def empty(name, loc=(0, 0, 0), parent=None):
    o = link(bpy.data.objects.new(name, None))
    o.location = loc
    o.parent = parent
    return o


def mesh_object(name, verts, faces, mats, smooth=True):
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(v) for v in verts], [], faces)
    me.validate()
    for m in mats:
        me.materials.append(m)
    o = link(bpy.data.objects.new(name, me))
    if smooth:
        for p in me.polygons:
            p.use_smooth = True
    return o


def activate(o):
    bpy.ops.object.select_all(action='DESELECT')
    o.select_set(True)
    bpy.context.view_layer.objects.active = o


def apply_modifiers(o):
    activate(o)
    for m in list(o.modifiers):
        bpy.ops.object.modifier_apply(modifier=m.name)


def to_mesh(o):
    activate(o)
    bpy.ops.object.convert(target='MESH')
    return bpy.context.view_layer.objects.active


def uv_sphere(name, loc, scale, mat, segs=48, rings=24, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=segs, ring_count=rings, location=loc, rotation=rot)
    o = bpy.context.object
    o.name = name
    o.scale = scale
    o.data.materials.append(mat)
    bpy.ops.object.shade_smooth()
    return o


def look_rotation(z_axis, up_hint=Vector((0, 0, 1))):
    z = Vector(z_axis).normalized()
    x = up_hint.cross(z)
    if x.length < 1e-4:
        x = Vector((1, 0, 0)).cross(z)
    x.normalize()
    y = z.cross(x)
    return Matrix((x, y, z)).transposed()


def smoothstep(e0, e1, v):
    t = min(1.0, max(0.0, (v - e0) / (e1 - e0)))
    return t * t * (3 - 2 * t)


# ---------------------------------------------------------------- Poke Ball
def build_ball():
    bpy.ops.mesh.primitive_uv_sphere_add(segments=96, ring_count=48, radius=1.0)
    ball = bpy.context.object
    ball.name = 'Poke Ball shell'
    ball.data.materials.append(BALL_RED)
    ball.data.materials.append(BALL_WHITE)
    me = ball.data
    import bmesh
    bm = bmesh.new()
    bm.from_mesh(me)
    gap = 0.055
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if abs(f.calc_center_median().z) < gap], context='FACES')
    for f in bm.faces:
        f.material_index = 0 if f.calc_center_median().z > 0 else 1
        f.smooth = True
    # Roll the open rims inward so the seam reads as a soft moulded groove.
    rim = [e for e in bm.edges if e.is_boundary]
    ext = bmesh.ops.extrude_edge_only(bm, edges=rim)
    for v in [g for g in ext['geom'] if isinstance(g, bmesh.types.BMVert)]:
        v.co.x *= 0.955
        v.co.y *= 0.955
        v.co.z *= 0.75
    bm.to_mesh(me)
    bm.free()
    mod = ball.modifiers.new('Subdivide', 'SUBSURF')
    mod.levels = 1
    mod.render_levels = 1
    apply_modifiers(ball)

    bpy.ops.mesh.primitive_cylinder_add(vertices=128, radius=0.965, depth=0.13)
    band = bpy.context.object
    band.name = 'Poke Ball band'
    band.data.materials.append(NAVY)
    bpy.ops.object.shade_smooth()

    parts = [ball, band]

    def disc(name, radius, depth, y, mat, bevel):
        bpy.ops.mesh.primitive_cylinder_add(vertices=96, radius=radius, depth=depth,
                                            location=(0, y, 0), rotation=(math.pi / 2, 0, 0))
        o = bpy.context.object
        o.name = name
        o.data.materials.append(mat)
        b = o.modifiers.new('Rounded', 'BEVEL')
        b.width = bevel
        b.segments = 4
        b.limit_method = 'ANGLE'
        apply_modifiers(o)
        bpy.ops.object.shade_smooth_by_angle(angle=math.radians(40))
        parts.append(o)
        return o

    disc('Button ring', 0.30, 0.16, -0.93, NAVY, 0.03)
    disc('Button face', 0.215, 0.10, -1.02, BALL_WHITE, 0.035)
    disc('Button centre', 0.11, 0.05, -1.07, BUTTON_PINK, 0.018)
    return parts


# ---------------------------------------------------------------- Pikachu body (sculpted SDF)
# The body is one signed-distance field: anatomical ellipsoids and tapered limbs joined
# with smooth fillets, then meshed with marching cubes. Ears are part of the same surface.
# Cheeks, ear tips, and back stripes are painted into a vertex color attribute.
import numpy as np
from skimage.measure import marching_cubes

SINK = -0.22   # Pikachu settles slightly into the ball contact
HEAD_C = Vector((-0.42, 0.0, 0.68))
EAR_LEN = 0.95
EAR_FLAT = 0.40
EAR_DIR = {-1: Vector((0.82, -0.38, 0.44)).normalized(), 1: Vector((0.86, 0.30, 0.42)).normalized()}
EAR_BASE = {s: HEAD_C + Vector((0.10, s * 0.27, 0.36)) for s in (-1, 1)}
LIN_YELLOW = (1.0, 0.62, 0.01)
LIN_INK = (0.018, 0.024, 0.045)
LIN_BROWN = (0.16, 0.05, 0.012)
LIN_CHEEK = (0.95, 0.10, 0.06)


def _v(x):
    return np.asarray(x, dtype=np.float32)


def sd_ellipsoid(P, c, r):
    r = _v(r)
    q = (P - _v(c)) / r
    k0 = np.linalg.norm(q, axis=-1)
    k1 = np.linalg.norm(q / r, axis=-1)
    return k0 * (k0 - 1.0) / np.maximum(k1, 1e-6)


def sd_cone(P, a, b, ra, rb):
    a, b = _v(a), _v(b)
    ba = b - a
    h = np.clip(((P - a) @ ba) / float(ba @ ba), 0.0, 1.0)
    return np.linalg.norm(P - a - h[..., None] * ba, axis=-1) - (ra + (rb - ra) * h)


def smin(a, b, k):
    h = np.maximum(k - np.abs(a - b), 0.0) / k
    return np.minimum(a, b) - h * h * k * 0.25


def ear_frame(side):
    d = EAR_DIR[side]
    n = Vector((0, side, 0.25)).normalized()
    w = n.cross(d).normalized()
    n = d.cross(w).normalized()
    return d, w, n


def sd_ear(P, side):
    d, w, n = ear_frame(side)
    q = P - _v(EAR_BASE[side])
    u, s, t = q @ _v(d), q @ _v(w), q @ _v(n)
    # Slight backward curl: the tip bends toward the thickness axis.
    t = t + 0.10 * np.clip(u / EAR_LEN, 0, 1) ** 2
    Q = np.stack([u, s, t / EAR_FLAT], axis=-1)
    L = EAR_LEN
    a = sd_cone(Q, (0, 0, 0), (0.36 * L, 0, 0), 0.105, 0.16)
    b = sd_cone(Q, (0.36 * L, 0, 0), (L, 0, 0), 0.16, 0.008)
    return smin(a, b, 0.05) * EAR_FLAT


def pikachu_sdf(P):
    P = P - _v((0, 0, SINK))
    H = np.array(HEAD_C, dtype=np.float32)
    head = sd_ellipsoid(P, H, (0.44, 0.52, 0.43))
    for s in (-1, 1):
        head = smin(head, sd_ellipsoid(P, H + _v((-0.06, s * 0.20, -0.13)), (0.34, 0.33, 0.29)), 0.10)
    head = smin(head, sd_ellipsoid(P, H + _v((-0.36, 0, -0.12)), (0.11, 0.17, 0.10)), 0.08)
    body = sd_ellipsoid(P, (0.20, 0, 0.42), (0.46, 0.38, 0.33))
    body = smin(body, sd_ellipsoid(P, (-0.06, 0, 0.36), (0.26, 0.30, 0.26)), 0.12)
    body = smin(body, sd_ellipsoid(P, (0.50, 0, 0.40), (0.30, 0.38, 0.32)), 0.12)
    f = smin(head, body, 0.16)
    for s in (-1, 1):
        arm = sd_cone(P, (-0.14, s * 0.25, 0.36), (-0.44, s * 0.23, 0.14), 0.10, 0.078)
        arm = smin(arm, sd_ellipsoid(P, (-0.47, s * 0.23, 0.10), (0.095, 0.09, 0.065)), 0.04)
        f = smin(f, arm, 0.07)
        leg = sd_ellipsoid(P, (0.50, s * 0.27, 0.30), (0.24, 0.13, 0.20))
        leg = smin(leg, sd_ellipsoid(P, (0.72, s * 0.30, 0.18), (0.20, 0.10, 0.075)), 0.06)
        f = smin(f, leg, 0.10)
        f = smin(f, sd_ear(P, s), 0.07)
    return f


def sdf_surface_point(direction, center=HEAD_C):
    """March along a ray from the head centre to the first sign change of the field."""
    d = _v(Vector(direction).normalized())
    c = _v(center) + _v((0, 0, SINK))
    ts = np.linspace(0, 1.5, 3001, dtype=np.float32)
    vals = pikachu_sdf(c[None, :] + ts[:, None] * d[None, :])
    i = int(np.argmax(vals > 0))
    return c + ts[i] * d


def build_body():
    h = 0.007
    lo = np.array((-1.0, -0.85, -0.32 + SINK), dtype=np.float32)
    hi = np.array((1.25, 0.85, 1.55 + SINK), dtype=np.float32)
    axes = [np.arange(lo[i], hi[i], h, dtype=np.float32) for i in range(3)]
    G = np.stack(np.meshgrid(*axes, indexing='ij'), axis=-1)
    field = pikachu_sdf(G)
    del G
    verts, faces, _, _ = marching_cubes(field, level=0.0, spacing=(h, h, h))
    verts = verts.astype(np.float32) + lo
    # Orient faces outward: the signed volume must be positive.
    tri = verts[faces]
    vol = np.einsum('ij,ij->i', tri[:, 0], np.cross(tri[:, 1], tri[:, 2])).sum()
    if vol < 0:
        faces = faces[:, ::-1]
    colors = paint(verts)
    me = bpy.data.meshes.new('Pikachu body')
    me.from_pydata(verts.tolist(), [], faces.tolist())
    me.validate()
    attr = me.color_attributes.new('Col', 'FLOAT_COLOR', 'POINT')
    attr.data.foreach_set('color', colors.ravel())
    me.materials.append(BODY_MAT)
    body = link(bpy.data.objects.new('Pikachu body', me))
    sm = body.modifiers.new('Relax', 'SMOOTH')
    sm.factor = 0.5
    sm.iterations = 2
    dec = body.modifiers.new('Decimate', 'DECIMATE')
    dec.ratio = min(1.0, 160000 / len(faces))
    apply_modifiers(body)
    for p in body.data.polygons:
        p.use_smooth = True
    print('BODY_MESH', len(verts), len(faces), '->', len(body.data.polygons), flush=True)
    return body


def _sstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1)
    return t * t * (3 - 2 * t)


def paint(V):
    col = np.tile(_v(LIN_YELLOW), (len(V), 1))
    P = V - _v((0, 0, SINK))

    def mix(mask, c):
        col[:] = col * (1 - mask[:, None]) + _v(c)[None, :] * mask[:, None]

    # Ink ear tips, cut on a slight curve along the ear.
    for s in (-1, 1):
        d, w, n = ear_frame(s)
        q = P - _v(EAR_BASE[s])
        u, sw = q @ _v(d), q @ _v(w)
        near = (np.abs(q @ _v(n)) < 0.15) & (np.abs(sw) < 0.25)
        cut = 0.64 * EAR_LEN - 0.12 * (sw / 0.16) ** 2 * 0.25
        mix(_sstep(cut - 0.006, cut + 0.006, u) * near, LIN_INK)
    # Two brown stripes across the lower back.
    for xc in (0.36, 0.53):
        a, b = np.array((xc - 0.01, -0.24)), np.array((xc + 0.02, 0.24))
        ab = b - a
        t = np.clip(((P[:, :2] - a) @ ab) / (ab @ ab), 0, 1)
        dist = np.linalg.norm(P[:, :2] - (a + t[:, None] * ab), axis=1)
        m = _sstep(0.052, 0.044, dist) * _sstep(0.50, 0.58, P[:, 2])
        mix(m, LIN_BROWN)
    # Round red cheeks centred on the cheek surface.
    for s in (-1, 1):
        c = sdf_surface_point((-0.62, s * 0.78, -0.12))
        dist = np.linalg.norm(V - c, axis=1)
        mix(_sstep(0.125, 0.117, dist), LIN_CHEEK)
    return np.concatenate([col, np.ones((len(V), 1), dtype=np.float32)], axis=1)


def surface_point(body, direction, center=HEAD_C):
    """Ray-cast from outside the head toward its centre; returns hit point and normal."""
    d = Vector(direction).normalized()
    origin = center + Vector((0, 0, SINK)) + d * 3.0
    ok, loc, normal, _ = body.ray_cast(origin, -d)
    assert ok, ('surface miss', direction)
    return loc, normal


# ---------------------------------------------------------------- tail
TAIL_OUTLINE = [(0.00, 0.00), (0.11, -0.05), (0.31, 0.20), (0.245, 0.265), (0.51, 0.49),
                (0.43, 0.56), (0.84, 0.96), (0.45, 1.04), (0.215, 0.665), (0.295, 0.60),
                (0.075, 0.37), (0.155, 0.305), (-0.05, 0.065)]


def bolt_curve(name, outline, scale, extrude, bevel, mat):
    cu = bpy.data.curves.new(name, 'CURVE')
    cu.dimensions = '2D'
    cu.fill_mode = 'BOTH'
    cu.extrude = extrude
    cu.bevel_depth = bevel
    cu.bevel_resolution = 4
    sp = cu.splines.new('POLY')
    sp.points.add(len(outline) - 1)
    for p, (x, y) in zip(sp.points, outline):
        p.co = (x * scale, y * scale, 0, 1)
    sp.use_cyclic_u = True
    cu.materials.append(mat)
    o = link(bpy.data.objects.new(name, cu))
    o = to_mesh(o)
    bpy.ops.object.shade_smooth_by_angle(angle=math.radians(50))
    return o


def build_tail(base):
    tail = bolt_curve('Lightning tail', TAIL_OUTLINE, 1.02, 0.035, 0.03, YELLOW)
    tail.data.materials.append(BROWN)
    for poly in tail.data.polygons:
        if poly.center.y < 0.17:
            poly.material_index = 1
    # Curve was drawn in its XY plane; stand it up in Pikachu's XZ plane and
    # turn it toward the camera so the zig-zag reads clearly.
    tail.rotation_euler = (math.pi / 2, 0.42, -YAW * 0.75)
    tail.location = base
    bpy.context.view_layer.update()
    activate(tail)
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)
    return tail


# ---------------------------------------------------------------- face
def face_tube(name, body, dirs, radius, mat, lift=0.004):
    pts = []
    for d in dirs:
        loc, n = surface_point(body, d)
        pts.append(loc + n * lift)
    cu = bpy.data.curves.new(name, 'CURVE')
    cu.dimensions = '3D'
    cu.bevel_depth = radius
    cu.bevel_resolution = 6
    cu.use_fill_caps = True
    sp = cu.splines.new('NURBS')
    sp.points.add(len(pts) - 1)
    for p, c in zip(sp.points, pts):
        p.co = (*c, 1)
    sp.order_u = 3
    sp.use_endpoint_u = True
    sp.resolution_u = 16
    cu.materials.append(mat)
    o = to_mesh(link(bpy.data.objects.new(name, cu)))
    bpy.ops.object.shade_smooth()
    caps = []
    for c in (pts[0], pts[-1]):
        caps.append(uv_sphere(name + ' cap', c, (radius,) * 3, mat, 16, 8))
    bpy.ops.object.select_all(action='DESELECT')
    for c in caps:
        c.select_set(True)
    o.select_set(True)
    bpy.context.view_layer.objects.active = o
    bpy.ops.object.join()
    return o


def arc_dirs(center_dir, right, up, width, sag, count=7):
    c = Vector(center_dir).normalized()
    out = []
    for i in range(count):
        s = -1 + 2 * i / (count - 1)
        out.append(c + right * (s * width) + up * (sag * (1 - s * s)))
    return out


def surface_disc(name, body, direction, radius, depth, mat, lift):
    loc, n = surface_point(body, direction)
    o = uv_sphere(name, (0, 0, 0), (radius, radius, depth), mat, 48, 24)
    o.matrix_world = Matrix.Translation(loc + n * lift) @ look_rotation(n).to_4x4() @ Matrix.Diagonal((radius, radius, depth, 1))
    return o, loc, n


def build_face(body):
    parts = []
    fwd = Vector((-1, 0, 0))
    # Closed eyes: gentle downward smiles, like the reference.
    for side, name in ((-1, 'Near eye closed'), (1, 'Far eye closed')):
        centre = Vector((-0.80, side * (0.44 if side > 0 else 0.48), 0.30))
        right = Vector((0.18 * side, 1, 0)).normalized()
        up = Vector((0, 0, 1))
        dirs = arc_dirs(centre, right, up, 0.20, -0.07)
        parts.append(face_tube(name, body, dirs, 0.026, FACE_INK))
    # Cheeks: soft red discs that sit on the surface.
    # Cheeks are painted into the body vertex colors.
    nose, _, _ = surface_disc('Nose', body, (-1, 0.0, 0.08), 0.03, 0.022, FACE_INK, -0.006)
    nose.scale = (nose.scale.x * 1.3, nose.scale.y, nose.scale.z)
    parts.append(nose)
    # Small content smile under the nose.
    dirs = arc_dirs(Vector((-1, -0.02, -0.10)), Vector((0, 1, 0)), Vector((0, 0, 1)), 0.075, -0.035, 7)
    parts.append(face_tube('Mouth', body, dirs, 0.012, FACE_INK))
    nose_loc, nose_n = surface_point(body, (-1, 0.0, 0.08))
    return parts, nose_loc, nose_n


# ---------------------------------------------------------------- bubble
def build_bubble(anchor, direction):
    """Teardrop whose tip touches the nose; object origin sits at the tip."""
    rings, segs = 40, 40
    verts, faces = [], []
    for j in range(1, rings):
        th = math.pi * j / rings
        rho = math.sin(th) * math.sin(th / 2) ** 1.2
        zz = (1 - math.cos(th))      # 0 at tip, 2 at far end
        for i in range(segs):
            a = 2 * math.pi * i / segs
            verts.append((rho * math.cos(a), rho * math.sin(a), zz))
    tip = len(verts)
    verts.append((0, 0, 0))
    end = len(verts)
    verts.append((0, 0, 2))
    for j in range(rings - 2):
        for i in range(segs):
            a, b = j * segs + i, j * segs + (i + 1) % segs
            faces.append((a, a + segs, b + segs, b))
    last = (rings - 2) * segs
    for i in range(segs):
        faces.append((tip, i, (i + 1) % segs))
        faces.append((last + (i + 1) % segs, last + i, end))
    bub = mesh_object('Sleep bubble', [Vector(v) * 0.5 for v in verts], faces, [BUBBLE])
    bub.matrix_world = Matrix.Translation(anchor) @ look_rotation(direction).to_4x4()
    glint = uv_sphere('Bubble glint', (0, 0, 0), (0.09, 0.09, 0.05), HIGHLIGHT, 24, 12)
    glint.parent = bub
    glint.matrix_parent_inverse = Matrix()
    glint.location = (-0.2, -0.28, 0.78)
    return bub


# ---------------------------------------------------------------- floor and props
def build_set():
    # Seamless cyclorama: flat floor that curves up into a back wall.
    prof = [(-30, 0)] + [(5 + 4 * math.sin(a), 4 - 4 * math.cos(a))
                         for a in [i * (math.pi / 2) / 16 for i in range(17)]] + [(9, 30)]
    verts, faces = [], []
    for x in (-40, 40):
        for y, z in prof:
            verts.append((x, y, z))
    n = len(prof)
    for i in range(n - 1):
        faces.append((i, i + 1, n + i + 1, n + i))
    o = mesh_object('Studio cyclorama', verts, faces, [FLOOR])
    props = []
    # Small toys from the reference, laid out along the floor.
    def ring(loc, mat):
        bpy.ops.mesh.primitive_torus_add(major_radius=0.085, minor_radius=0.032, location=loc)
        t = bpy.context.object
        t.data.materials.append(mat)
        bpy.ops.object.shade_smooth()
        props.append(t)
    ring((-2.35, -0.25, 0.032), TOY_RED)
    ring((2.45, -0.15, 0.032), TOY_RED)
    for loc, rz in [((-1.75, -0.55, 0.0), 0.3), ((2.0, 0.45, 0.0), -0.4)]:
        b = bolt_curve('Floor bolt', TAIL_OUTLINE, 0.26, 0.02, 0.012, TOY_YELLOW)
        b.location = (loc[0], loc[1], 0.034)
        b.rotation_euler = (0, 0, rz)
        props.append(b)
    for loc, mat, r in [((-1.35, 0.35, 0.05), TOY_RED, 0.05), ((1.45, -0.6, 0.045), TOY_BLUE, 0.045),
                        ((-2.0, 0.9, 0.04), TOY_BLUE, 0.04), ((1.25, 0.7, 0.035), TOY_RED, 0.035)]:
        props.append(uv_sphere('Floor bead', loc, (r, r, r), mat, 24, 12))
    bpy.ops.mesh.primitive_cube_add(size=1, location=(1.85, -0.2, 0.03))
    cross = bpy.context.object
    cross.name = 'Floor cross'
    cross.scale = (0.2, 0.055, 0.055)
    bpy.ops.mesh.primitive_cube_add(size=1, location=(1.85, -0.2, 0.03))
    c2 = bpy.context.object
    c2.scale = (0.055, 0.2, 0.055)
    activate(cross)
    c2.select_set(True)
    bpy.ops.object.join()
    cross.rotation_euler.z = 0.6
    cross.data.materials.append(TOY_BLUE)
    bev = cross.modifiers.new('Soft', 'BEVEL')
    bev.width = 0.02
    bev.segments = 3
    props.append(cross)
    bpy.ops.mesh.primitive_cylinder_add(vertices=32, radius=0.045, depth=0.2,
                                        location=(-1.15, -0.75, 0.045), rotation=(0, math.pi / 2, 0.3))
    pill = bpy.context.object
    pill.name = 'Floor capsule'
    pill.data.materials.append(TOY_BLUE)
    bev = pill.modifiers.new('Round', 'BEVEL')
    bev.width = 0.04
    bev.segments = 6
    bpy.ops.object.shade_smooth()
    props.append(pill)
    return o, props


# ---------------------------------------------------------------- build
root = empty('Pikachu scene')
roll = empty('Ball roll', (0, 0, R), root)
ball_tilt = empty('Ball rest tilt', (0, 0, 0), roll)
for p in build_ball():
    p.parent = ball_tilt
ball_tilt.scale = (R, R, R)
seat = empty('Pikachu seat', (0, 0, 2 * R), root)
yaw = empty('Pikachu yaw', (0, 0, 0), seat)

body = build_body()
ear_dir = EAR_DIR
ear_base = {sd: EAR_BASE[sd] + Vector((0, 0, SINK)) for sd in (-1, 1)}
tail_base = Vector((0.72, 0.06, 0.36 + SINK))
tail = build_tail(tail_base)
face_parts, nose_loc, nose_n = build_face(body)
bubble_dir = (nose_n + Vector((-0.4, -0.25, -0.15))).normalized()
bubble = build_bubble(nose_loc + nose_n * 0.004, bubble_dir)
floor, props = build_set()

# ---------------------------------------------------------------- armature
arm_data = bpy.data.armatures.new('Pikachu rig')
arm = link(bpy.data.objects.new('Pikachu rig', arm_data))
activate(arm)
bpy.ops.object.mode_set(mode='EDIT')


def bone(name, head, tail_pt, parent=None):
    b = arm_data.edit_bones.new(name)
    b.head = head
    b.tail = tail_pt
    b.roll = 0
    if parent:
        b.parent = arm_data.edit_bones[parent]
    return b


bone('root', (0, 0, 0), (0, 0, 0.25))
bone('body', (0.30, 0, 0.02 + SINK), (0.30, 0, 0.50), 'root')
bone('head', (-0.10, 0, 0.40 + SINK), (-0.10, 0, 0.90), 'root')
for side, nm in ((-1, 'ear.near'), (1, 'ear.far')):
    bone(nm, ear_base[side], ear_base[side] + ear_dir[side].normalized() * 0.5, 'head')
bone('tail', tail_base, tail_base + Vector((0.4, 0, 0.55)), 'root')
bone('bubble', nose_loc, nose_loc + bubble_dir * 0.2, 'head')
bpy.ops.object.mode_set(mode='OBJECT')

# Skin the body: smooth head/body/root weights. Paws and feet stay planted.
names = ('root', 'body', 'head', 'ear.near', 'ear.far')
groups = {n: body.vertex_groups.new(name=n) for n in names}
for v in body.data.vertices:
    co = v.co
    w = {}
    for sd, nm in ((-1, 'ear.near'), (1, 'ear.far')):
        q = co - ear_base[sd]
        u = q.dot(ear_dir[sd])
        radial = (q - ear_dir[sd] * u).length
        w[nm] = smoothstep(0.02, 0.14, u) * smoothstep(0.30, 0.22, radial) if u > 0 else 0.0
    rest = 1 - max(w.values())
    wh = smoothstep(0.02, -0.32, co.x) * smoothstep(0.16 + SINK, 0.34 + SINK, co.z)
    wh = max(wh, smoothstep(0.80 + SINK, 1.0 + SINK, co.z) * smoothstep(0.25, -0.05, co.x))
    w['head'] = rest * wh
    w['body'] = rest * (1 - wh) * smoothstep(0.06 + SINK, 0.30 + SINK, co.z) * smoothstep(1.1, 0.75, abs(co.x - 0.3))
    w['root'] = max(0.0, 1 - sum(w.values()))
    for nm, wt in w.items():
        if wt > 1e-4:
            groups[nm].add([v.index], wt, 'REPLACE')
mod = body.modifiers.new('Rig', 'ARMATURE')
mod.object = arm
body.parent = arm


def bone_parent(o, bname):
    mw = o.matrix_world.copy()
    o.parent = arm
    o.parent_type = 'BONE'
    o.parent_bone = bname
    bpy.context.view_layer.update()
    o.matrix_world = mw


bone_parent(tail, 'tail')
for p in face_parts:
    bone_parent(p, 'head')
bone_parent(bubble, 'bubble')
arm.parent = yaw
yaw.rotation_euler.z = YAW
bpy.context.view_layer.update()

# ---------------------------------------------------------------- animation
TAU = 2 * math.pi
MID, AMP = -0.075, 0.205   # ball tilt: forward -0.28 rad, back +0.13 rad


def shaped(p):
    """Rock profile with soft holds at both ends of the swing; period 1."""
    c = math.cos(TAU * p)
    return math.copysign(abs(c) ** 0.6, c)


def tilt(p):
    return MID - AMP * shaped(p)


def dtilt(p, h=1e-3):
    return (tilt(p + h) - tilt(p - h)) / (2 * h)


def breath(p):
    """1 at full inhale (back pose), 0 at full exhale (forward pose)."""
    return 0.5 - 0.5 * math.cos(TAU * (p - 0.04))


def twitch(p, start=0.60, length=0.12):
    q = (p - start) % 1.0
    if q > length:
        return 0.0
    s = q / length
    return math.sin(TAU * 1.5 * s) * (1 - s) ** 2 * math.sin(math.pi * min(1, s * 4))


def rot_bone(pb, axis_arm, angle):
    b3 = pb.bone.matrix_local.to_3x3()
    q = Quaternion(axis_arm, angle).to_matrix()
    return (b3.inverted() @ q @ b3).to_quaternion()


pbs = arm.pose.bones
for pb in pbs:
    pb.rotation_mode = 'QUATERNION'
Y = Vector((0, 1, 0))
anim_objs = [roll, ball_tilt, seat, yaw, bubble]
ball_tilt.rotation_euler.y = 0.0

for f in range(1, N + 2):
    p = (f - 1) / N
    phi = tilt(p)
    # Ball rolls without slipping: the floor contact stays put.
    roll.location = (R * phi, 0, R)
    roll.rotation_euler = (0, phi, 0)
    # Pikachu rides the top of the ball and leans most of the way with it.
    seat_ang = 0.82 * phi
    seat.location = (R * phi + R * math.sin(seat_ang), 0, R + R * math.cos(seat_ang))
    seat.rotation_euler = (0, 0.88 * phi, 0)
    yaw.rotation_euler = (0, 0, YAW)

    b = breath(p)
    pbs['body'].scale = (1 + 0.025 * b, 1 + 0.045 * b, 1 + 0.025 * b)
    head_nod = -0.10 * (1 - b) + 0.04 + 0.35 * (tilt(p - 0.03) - MID) * 0.4
    pbs['head'].rotation_quaternion = rot_bone(pbs['head'], Y, head_nod)
    pbs['head'].location = (0, 0.015 * b, 0)

    # Ears and tail follow the rock late, with drag from the swing speed.
    lag = p - 0.07
    ear = 0.35 * (tilt(lag) - MID) + 0.022 * dtilt(lag)
    pbs['ear.near'].rotation_quaternion = rot_bone(pbs['ear.near'], Y, ear + 0.05)
    pbs['ear.far'].rotation_quaternion = rot_bone(pbs['ear.far'], Y, ear * 0.9 + 0.02)
    tw = twitch(p)
    if tw:
        pbs['ear.near'].rotation_quaternion = rot_bone(pbs['ear.near'], Vector((0, 0.35, 1)).normalized(), 0.22 * tw) @ \
            pbs['ear.near'].rotation_quaternion
    lag2 = p - 0.10
    tail_ang = 1.0 * (tilt(lag2) - MID) - 0.03 * dtilt(lag2)
    pbs['tail'].rotation_quaternion = rot_bone(pbs['tail'], Y, tail_ang)

    # Sleep bubble swells on the exhale and shrinks on the inhale, with a wobble.
    size = 0.07 + 0.50 * (1 - b) ** 1.6
    wob = 0.06 * math.sin(TAU * 3 * p) * (1 - b)
    bubble.scale = (size * (1 + wob), size * (1 - wob), size * (1 + 0.5 * wob))

    for o in (roll, seat, yaw):
        o.keyframe_insert('location', frame=f)
        o.keyframe_insert('rotation_euler', frame=f)
    bubble.keyframe_insert('scale', frame=f)
    pbs['body'].keyframe_insert('scale', frame=f)
    for n in ('head', 'ear.near', 'ear.far', 'tail'):
        pbs[n].keyframe_insert('rotation_quaternion', frame=f)
    pbs['head'].keyframe_insert('location', frame=f)

# ---------------------------------------------------------------- lights and camera
def area(name, loc, energy, size, color, target=(0, 0, 1.4)):
    bpy.ops.object.light_add(type='AREA', location=loc)
    o = bpy.context.object
    o.name = name
    o.data.energy = energy
    o.data.shape = 'DISK'
    o.data.size = size
    o.data.color = color
    o.rotation_euler = (Vector(target) - o.location).to_track_quat('-Z', 'Y').to_euler()
    return o


area('Key soft warm', (-4.5, -6.0, 7.0), 1300, 5.0, (1.0, 0.95, 0.88))
area('Fill cool', (6.0, -5.0, 2.5), 450, 5.0, (0.88, 0.93, 1.0))
area('Rim', (2.0, 5.0, 5.5), 1100, 3.0, (1.0, 0.97, 0.9), (0, 0, 1.8))
area('Top bounce', (0, -1, 9), 300, 6.0, (1, 1, 1))

bpy.ops.object.camera_add(location=(-0.05, -13.5, 3.4))
cam = bpy.context.object
cam.name = 'Camera'
cam.data.lens = 82
cam.data.dof.use_dof = True
cam.data.dof.focus_distance = 13.3
cam.data.dof.aperture_fstop = 8.0
cam.rotation_euler = (Vector((0.0, 0, 1.62)) - cam.location).to_track_quat('-Z', 'Y').to_euler()
scene.camera = cam

# ---------------------------------------------------------------- save and export
scene.frame_set(1)
bpy.ops.wm.save_as_mainfile(filepath=str(out / 'pikachu-v3.blend'))
if not args.no_export:
    bpy.ops.object.select_all(action='DESELECT')
    for o in [root] + list(root.children_recursive):
        if o.type in {'MESH', 'ARMATURE', 'EMPTY'}:
            o.select_set(True)
    scene.frame_end = N + 1
    bpy.ops.export_scene.gltf(filepath=str(out / 'pikachu-v3.glb'), export_format='GLB',
                              use_selection=True, export_animations=True,
                              export_animation_mode='SCENE', export_anim_scene_split_object=False,
                              export_frame_range=True, export_apply=True, export_skins=True)
    scene.frame_end = N

if args.no_render:
    sys.exit(0)
frames = [int(f) for f in args.frames.split(',')] if args.frames else list(range(1, N + 1))
start = time.monotonic()
timings = []
for f in frames:
    scene.frame_set(f)
    scene.render.filepath = str(out / 'frames' / f'frame_{f:04d}.png')
    t = time.monotonic()
    bpy.ops.render.render(write_still=True)
    timings.append(dict(frame=f, seconds=round(time.monotonic() - t, 3)))
    print('FRAME_COMPLETE ' + json.dumps(timings[-1]), flush=True)
meta = dict(blender=bpy.app.version_string, backend='OPTIX', devices=devices,
            resolution=[scene.render.resolution_x * args.percent // 100,
                        scene.render.resolution_y * args.percent // 100],
            samples=args.samples, fps=FPS, frames=frames, loop_period_frames=N,
            render_seconds=round(time.monotonic() - start, 3), frame_timings=timings)
(out / 'render-metadata.json').write_text(json.dumps(meta, indent=2))
print('COMPLETE', flush=True)
