"""Vinyl-toy silver tabby cat, preview experiment (vinyl-v1).

Deterministic bpy script: one fused metaball body, voxel remesh + smooth,
socketed eyes, matte vinyl materials, Cycles OptiX preview renders.
Proportions are named constants and asserted against the finished mesh.
"""
import argparse
import json
import math
import sys
import time
from pathlib import Path

import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from contact_sheet import render_views

VERSION = 'vinyl-v1'
SEED = 7

# --- Named proportions (source of truth) -----------------------------------
# Units are metres. The finished cat, including ears, should stand ~1.70 tall
# with the head (ears included) about 58% of that height — a vinyl chibi.
TOTAL_HEIGHT = 1.70
HEAD_RATIO = 0.58
HEAD_RADIUS = 0.455
HEAD_SCALE = (1.06, 0.90, 1.00)  # wider than deep, sides slightly flattened
HEAD_Z = 1.04
HEAD_Y = 0.03

CHEEK_R, CHEEK_X, CHEEK_Y, CHEEK_Z = 0.20, 0.27, 0.16, 0.94
MUZZLE_R, MUZZLE_Y, MUZZLE_Z = 0.15, 0.36, 0.86
CHIN_R, CHIN_Y, CHIN_Z = 0.075, 0.28, 0.74
NECK_R, NECK_Z = 0.22, 0.68

BODY_R = 0.30
BODY_SCALE = (1.00, 0.78, 1.18)
BODY_Y, BODY_Z = 0.03, 0.40

# Arms and paws: short nubs hanging slightly outward.
ARM = dict(shoulder=(0.30, 0.08, 0.58, 0.13),
           mid=(0.40, 0.07, 0.40, 0.12),
           paw=(0.45, 0.09, 0.22, 0.105))
FOOT = dict(x=0.155, y=0.10, z=0.12, r=0.13)
TAIL = dict(y=-0.40, z=0.28, r=0.135)

# Ears: a short chain of balls pointing up and out.
EAR_BASE = (0.20, -0.02, 1.36)
EAR_DIR = (0.10, -0.03, 0.26)
EAR_RADII = (0.125, 0.09, 0.05)

# Centre bangs tuft.
BANGS = [((0.00, 0.22, 1.38), 0.075),
         ((0.00, 0.18, 1.48), 0.055),
         ((0.00, 0.14, 1.55), 0.035)]

# Eyes: vinyl-cute, larger than the five-widths portrait rule.
# head width ≈ 2 * HEAD_RADIUS * HEAD_SCALE[0] = 0.965
EYE_R = 0.125
EYE_X, EYE_Y, EYE_Z = 0.155, 0.32, 1.02
EYE_WIDTHS_ACROSS = (2 * HEAD_RADIUS * HEAD_SCALE[0]) / (2 * EYE_R)
IRIS_R = 0.078
PUPIL_R = 0.038

# Materials (linear-ish preview colours; AgX will tone them).
SILVER = (0.78, 0.79, 0.81)
STRIPE = (0.50, 0.51, 0.53)
CARDIGAN = (0.70, 0.71, 0.73)
TEE = (0.05, 0.05, 0.055)
CHEVRON = (0.82, 0.83, 0.85)
BLACK = (0.02, 0.02, 0.022)
PINK = (0.86, 0.48, 0.52)
INNER_EAR = (0.88, 0.68, 0.70)
AMBER = (0.62, 0.34, 0.10)
CREAM = (0.93, 0.89, 0.82)
SCLERA = (0.96, 0.95, 0.93)

assert 0.55 <= HEAD_RATIO <= 0.62
assert 3.2 <= EYE_WIDTHS_ACROSS <= 4.2
assert HEAD_SCALE[1] < HEAD_SCALE[0]
assert ARM['paw'][3] < HEAD_RADIUS * 0.30
assert TAIL['r'] < BODY_R * 0.55

# --- CLI -------------------------------------------------------------------
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output', type=Path, default=Path('results/cat-persona/vinyl-v1'))
parser.add_argument('--res', type=int, default=1080)
parser.add_argument('--samples', type=int, default=32)
parser.add_argument('--contact-res', type=int, default=720)
parser.add_argument('--save-blend', action='store_true')
parser.add_argument('--engine', choices=['CYCLES', 'BLENDER_EEVEE'], default='CYCLES')
parser.add_argument('--cpu', action='store_true', help='Force Cycles CPU (no OptiX).')
args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else [])
out = args.output.resolve()
out.mkdir(parents=True, exist_ok=True)
started = time.perf_counter()

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.engine = args.engine
scene.render.resolution_x = scene.render.resolution_y = args.res
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = 'PNG'
scene.render.image_settings.color_mode = 'RGB'
scene.render.film_transparent = False
scene.view_settings.view_transform = 'AgX'
scene.view_settings.look = 'None'
scene.view_settings.exposure = 0.15
scene.view_settings.gamma = 1.0

backend = 'EEVEE'
if args.engine == 'CYCLES':
    scene.cycles.samples = args.samples
    scene.cycles.use_adaptive_sampling = True
    scene.cycles.adaptive_threshold = 0.05
    scene.cycles.use_denoising = True
    scene.cycles.denoiser = 'OPENIMAGEDENOISE'
    scene.cycles.max_bounces = 6
    scene.cycles.transparent_max_bounces = 4
    scene.render.use_persistent_data = True
    if args.cpu:
        scene.cycles.device = 'CPU'
        backend = 'CYCLES CPU'
    else:
        prefs = bpy.context.preferences.addons['cycles'].preferences
        prefs.compute_device_type = 'OPTIX'
        prefs.refresh_devices()
        for d in prefs.devices:
            d.use = d.type == 'OPTIX'
        if not any(d.use and d.type == 'OPTIX' for d in prefs.devices):
            raise RuntimeError('OptiX required; pass --cpu for an explicit Cycles CPU preview')
        scene.cycles.device = 'GPU'
        backend = 'OPTIX'
        print('RENDER_DEVICE', [(d.name, d.type) for d in prefs.devices if d.use])
else:
    scene.eevee.taa_render_samples = args.samples


# --- Helpers ---------------------------------------------------------------
def vinyl(name, color, rough=0.48, sss=0.12, sheen=0.0, spec=0.45):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes['Principled BSDF']
    bsdf.inputs['Base Color'].default_value = (*color, 1)
    bsdf.inputs['Roughness'].default_value = rough
    if 'Specular IOR Level' in bsdf.inputs:
        bsdf.inputs['Specular IOR Level'].default_value = spec
    elif 'Specular' in bsdf.inputs:
        bsdf.inputs['Specular'].default_value = spec
    if sss and 'Subsurface Weight' in bsdf.inputs:
        bsdf.inputs['Subsurface Weight'].default_value = sss
        if 'Subsurface Radius' in bsdf.inputs:
            bsdf.inputs['Subsurface Radius'].default_value = (0.35, 0.18, 0.14)
    if sheen and 'Sheen Weight' in bsdf.inputs:
        bsdf.inputs['Sheen Weight'].default_value = sheen
        if 'Sheen Roughness' in bsdf.inputs:
            bsdf.inputs['Sheen Roughness'].default_value = 0.5
    return mat


def active(obj):
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj


def apply_mod(obj, name):
    active(obj)
    bpy.ops.object.modifier_apply(modifier=name)


def shade_smooth(obj):
    for p in obj.data.polygons:
        p.use_smooth = True


def mesh_from_primitive(name, op, loc, scale, mat, **kw):
    op(location=loc, **kw)
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if mat:
        obj.data.materials.append(mat)
    shade_smooth(obj)
    return obj


silver = vinyl('Vinyl silver', SILVER, rough=0.50, sss=0.15)
stripe_mat = vinyl('Tabby stripe', STRIPE, rough=0.52, sss=0.08)
cardigan_mat = vinyl('Cardigan knit', CARDIGAN, rough=0.58, sss=0.04, sheen=0.18)
tee_mat = vinyl('Black tee', TEE, rough=0.55, sss=0.0, sheen=0.05)
chevron_mat = vinyl('Tee chevron', CHEVRON, rough=0.5, sss=0.0)
black_mat = vinyl('Black plastic', BLACK, rough=0.28, sss=0.0, spec=0.55)
pink_mat = vinyl('Pink vinyl', PINK, rough=0.35, sss=0.2)
ear_mat = vinyl('Inner ear', INNER_EAR, rough=0.45, sss=0.2)
sclera_mat = vinyl('Sclera', SCLERA, rough=0.22, sss=0.05, spec=0.6)
iris_mat = vinyl('Amber iris', AMBER, rough=0.25, sss=0.0, spec=0.5)
pupil_mat = vinyl('Pupil', (0.01, 0.01, 0.01), rough=0.18, sss=0.0)
highlight_mat = vinyl('Eye highlight', (1, 1, 1), rough=0.05, sss=0.0, spec=1)
cornea_mat = vinyl('Cornea', (1, 1, 1), rough=0.04, sss=0.0, spec=1)
# Give the cornea a glassy transmission if the socket exists.
if 'Transmission Weight' in cornea_mat.node_tree.nodes['Principled BSDF'].inputs:
    cornea_mat.node_tree.nodes['Principled BSDF'].inputs['Transmission Weight'].default_value = 0.85
    cornea_mat.node_tree.nodes['Principled BSDF'].inputs['IOR'].default_value = 1.4
    cornea_mat.node_tree.nodes['Principled BSDF'].inputs['Alpha'].default_value = 0.15
    cornea_mat.blend_method = 'BLEND'


# --- Stage 1–2: metaball blockout, fused into one skin ---------------------
mb = bpy.data.metaballs.new('VinylBody')
mb.resolution = 0.028
mb.render_resolution = 0.022
mb.threshold = 0.55
body_meta = bpy.data.objects.new('VinylBody', mb)
scene.collection.objects.link(body_meta)


def add_ball(co, radius, stiffness=2.0, negative=False, typ='BALL', size=None):
    e = mb.elements.new()
    e.type = typ
    e.co = co
    e.radius = radius
    e.stiffness = stiffness
    e.use_negative = negative
    if size:
        e.size_x, e.size_y, e.size_z = size
    return e


# Head: slightly wider ellipsoid + cheeks, muzzle, chin.
add_ball((0, HEAD_Y, HEAD_Z), HEAD_RADIUS, typ='ELLIPSOID',
         size=(HEAD_RADIUS * HEAD_SCALE[0],
               HEAD_RADIUS * HEAD_SCALE[1],
               HEAD_RADIUS * HEAD_SCALE[2]))
add_ball((-CHEEK_X, CHEEK_Y, CHEEK_Z), CHEEK_R)
add_ball((CHEEK_X, CHEEK_Y, CHEEK_Z), CHEEK_R)
add_ball((0, MUZZLE_Y, MUZZLE_Z), MUZZLE_R, typ='ELLIPSOID', size=(0.16, 0.17, 0.12))
add_ball((0, CHIN_Y, CHIN_Z), CHIN_R)
add_ball((0, 0.02, HEAD_Z + 0.16), 0.28)  # crown volume
# Eye sockets (negative), slightly in front of the face so only a lens shows.
add_ball((-EYE_X, EYE_Y + 0.06, EYE_Z), EYE_R * 0.95, stiffness=2.4, negative=True)
add_ball((EYE_X, EYE_Y + 0.06, EYE_Z), EYE_R * 0.95, stiffness=2.4, negative=True)
# Brow ridges so the sockets read as lids, not holes.
add_ball((-EYE_X, EYE_Y - 0.02, EYE_Z + 0.10), 0.09, stiffness=2.2)
add_ball((EYE_X, EYE_Y - 0.02, EYE_Z + 0.10), 0.09, stiffness=2.2)

# Ears and bangs.
for sign in (-1, 1):
    for t, r in zip((0.0, 0.5, 1.0), EAR_RADII):
        co = (sign * (EAR_BASE[0] + EAR_DIR[0] * t),
              EAR_BASE[1] + EAR_DIR[1] * t,
              EAR_BASE[2] + EAR_DIR[2] * t)
        add_ball(co, r, stiffness=2.2)
for co, r in BANGS:
    add_ball(co, r, stiffness=2.3)

# Neck blend + bean body + nubby limbs + ball tail.
add_ball((0, 0.05, NECK_Z), NECK_R)
add_ball((0, BODY_Y, BODY_Z), BODY_R, typ='ELLIPSOID',
         size=(BODY_R * BODY_SCALE[0], BODY_R * BODY_SCALE[1], BODY_R * BODY_SCALE[2]))
add_ball((0, BODY_Y + 0.04, 0.52), 0.24)  # chest
for sign in (-1, 1):
    for key in ('shoulder', 'mid', 'paw'):
        x, y, z, r = ARM[key]
        add_ball((sign * x, y, z), r)
    add_ball((sign * FOOT['x'], FOOT['y'], FOOT['z']), FOOT['r'])
add_ball((0, TAIL['y'], TAIL['z']), TAIL['r'])

bpy.context.view_layer.update()
active(body_meta)
bpy.ops.object.convert(target='MESH')
body = bpy.context.object
body.name = 'VinylCat'
body.data.materials.append(silver)
shade_smooth(body)

# Fuse further and even out the converted metaball tessellation.
remesh = body.modifiers.new('Fuse', 'REMESH')
remesh.mode = 'VOXEL'
remesh.voxel_size = 0.012
remesh.use_smooth_shade = True
apply_mod(body, 'Fuse')
smooth = body.modifiers.new('Relax', 'CORRECTIVE_SMOOTH')
smooth.iterations = 12
smooth.factor = 0.5
smooth.use_only_smooth = True
smooth.use_pin_boundary = False
apply_mod(body, 'Relax')
shade_smooth(body)

# Sit the feet on the ground and record bounds.
def bounds(obj):
    corners = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
    lo = Vector(tuple(min(v[i] for v in corners) for i in range(3)))
    hi = Vector(tuple(max(v[i] for v in corners) for i in range(3)))
    return lo, hi, (lo + hi) * 0.5, hi - lo


lo, hi, mid, size = bounds(body)
body.location.z -= lo.z
bpy.context.view_layer.update()
active(body)
bpy.ops.object.transform_apply(location=True, rotation=False, scale=False)
lo, hi, mid, size = bounds(body)
height = size.z
head_span = height  # refined after we measure the neck; used in asserts below
# Head including ears is the top portion; use the neck plane as a split.
neck_z = NECK_Z - lo.z if lo.z < 0 else NECK_Z
# After grounding, original z=0 is now at -original_lo.z; elements were in world z already
# and we subtracted original lo.z, so HEAD_Z shifts by the same delta (which is already applied
# because we applied the location). Current coordinates are grounded.
assert 1.45 <= height <= 1.95, f'unexpected height {height:.3f}'
head_height = height - 0.62  # body+legs occupy ~0.62 after grounding; asserted loosely
# Recompute head ratio from the highest vertex vs a mid-torso cut.
zs = [v.co.z for v in body.data.vertices]
xs = [v.co.x for v in body.data.vertices]
torso_cut = 0.70
head_h = max(zs) - torso_cut
ratio = head_h / height
assert 0.48 <= ratio <= 0.70, f'head ratio {ratio:.3f} off target {HEAD_RATIO}'
print(f'PROPORTIONS height={height:.3f} head_ratio={ratio:.3f} width={size.x:.3f} depth={size.y:.3f} verts={len(body.data.vertices)}')


def front_y(x, z, start=2.0):
    hit, loc, normal, index = body.ray_cast(Vector((x, start, z)), Vector((0, -1, 0)))
    return loc.y if hit else 0.35


def back_y(x, z, start=-2.0):
    hit, loc, normal, index = body.ray_cast(Vector((x, start, z)), Vector((0, 1, 0)))
    return loc.y if hit else -0.3


# --- Face, clothes, accessories --------------------------------------------
def sphere(name, loc, scale, mat):
    return mesh_from_primitive(name, bpy.ops.mesh.primitive_uv_sphere_add, loc, scale, mat, radius=1, segments=32, ring_count=16)


def ellipsoid(name, loc, scale, mat, segments=24):
    return mesh_from_primitive(name, bpy.ops.mesh.primitive_uv_sphere_add, loc, scale, mat, radius=1, segments=segments, ring_count=max(12, segments // 2))


# Eyes sit in the recessed sockets; only a lens-shaped front is visible.
for sign, side in ((-1, 'L'), (1, 'R')):
    fy = front_y(sign * EYE_X, EYE_Z) - 0.02
    eye_loc = (sign * EYE_X, fy, EYE_Z)
    # Slightly flattened globe, mostly buried in the socket.
    sclera = sphere(f'Sclera.{side}', eye_loc, (EYE_R, EYE_R * 0.72, EYE_R), sclera_mat)
    iris = sphere(f'Iris.{side}', (sign * EYE_X, fy + EYE_R * 0.28, EYE_Z),
                  (IRIS_R, IRIS_R * 0.25, IRIS_R), iris_mat)
    pupil = sphere(f'Pupil.{side}', (sign * EYE_X, fy + EYE_R * 0.40, EYE_Z),
                   (PUPIL_R, PUPIL_R * 0.2, PUPIL_R), pupil_mat)
    highlight = sphere(f'Highlight.{side}',
                       (sign * EYE_X - 0.03, fy + EYE_R * 0.50, EYE_Z + 0.035),
                       (0.022, 0.012, 0.028), highlight_mat)
    # Thin glossy cornea over the visible lens.
    cornea = sphere(f'Cornea.{side}', eye_loc, (EYE_R * 1.04, EYE_R * 0.78, EYE_R * 1.04), cornea_mat)
    # Simple upper lid: a small silver torus-like sausage sitting on the socket rim.
    lid = ellipsoid(f'UpperLid.{side}', (sign * EYE_X, fy + 0.01, EYE_Z + EYE_R * 0.72),
                    (EYE_R * 1.05, 0.035, 0.045), silver, segments=16)

# Pink nose and a tiny mouth crease.
nose_y = front_y(0, MUZZLE_Z) + 0.02
sphere('Nose', (0, nose_y, MUZZLE_Z + 0.01), (0.045, 0.032, 0.028), pink_mat)

# Mouth: a short beveled curve.
def bevel_curve(name, points, radius, mat, closed=False):
    curve = bpy.data.curves.new(name, 'CURVE')
    curve.dimensions = '3D'
    curve.resolution_u = 8
    curve.bevel_depth = radius
    curve.bevel_resolution = 4
    curve.fill_mode = 'FULL'
    spline = curve.splines.new('BEZIER')
    spline.bezier_points.add(len(points) - 1)
    if closed:
        spline.use_cyclic_u = True
    for bp, co in zip(spline.bezier_points, points):
        bp.co = co
        bp.handle_left_type = bp.handle_right_type = 'AUTO'
    obj = bpy.data.objects.new(name, curve)
    scene.collection.objects.link(obj)
    obj.data.materials.append(mat)
    return obj


mouth_z = MUZZLE_Z - 0.07
my = front_y(0, mouth_z) + 0.01
bevel_curve('Mouth', [(-0.045, my, mouth_z + 0.008), (0, my + 0.004, mouth_z - 0.004),
                      (0.045, my, mouth_z + 0.008)], 0.006, black_mat)

# Inner ears: smaller pink ellipsoids aimed the same way as the ear chain.
for sign, side in ((-1, 'L'), (1, 'R')):
    mid = (sign * (EAR_BASE[0] + EAR_DIR[0] * 0.35),
           EAR_BASE[1] + EAR_DIR[1] * 0.35 + 0.03,
           EAR_BASE[2] + EAR_DIR[2] * 0.35)
    inner = ellipsoid(f'InnerEar.{side}', mid, (0.055, 0.03, 0.10), ear_mat, segments=16)

# Three forehead tabby stripes, shrink-wrapped onto the head.
def stripe(name, x, z, sx, sz):
    y = front_y(x, z) + 0.02
    obj = ellipsoid(name, (x, y, z), (sx, 0.02, sz), stripe_mat, segments=16)
    wrap = obj.modifiers.new('OnHead', 'SHRINKWRAP')
    wrap.target = body
    wrap.wrap_method = 'PROJECT'
    wrap.use_project_y = True
    wrap.use_negative_direction = True
    wrap.use_positive_direction = False
    wrap.offset = 0.004
    apply_mod(obj, 'OnHead')
    shade_smooth(obj)
    return obj


# Centre stripe slightly longer; flanking stripes shorter and angled out.
stripe('Stripe.C', 0.00, HEAD_Z + 0.16, 0.028, 0.13)
stripe('Stripe.L', -0.085, HEAD_Z + 0.15, 0.024, 0.11)
stripe('Stripe.R', 0.085, HEAD_Z + 0.15, 0.024, 0.11)

# Oversized rectangular glasses with a bridge and short temples.
def rounded_rect_frame(name, cx, cy, cz, w, h, corner, thick, depth, mat):
    pts = []
    segs = 4
    corners = [(-w + corner, -h + corner, 225), (w - corner, -h + corner, 315),
               (w - corner, h - corner, 45), (-w + corner, h - corner, 135)]
    # Build in XZ, Y is the facing axis. We'll place points in world after.
    arcs = []
    for ox, oz, start_deg in [(-w + corner, -h + corner, 180),
                              (w - corner, -h + corner, 270),
                              (w - corner, h - corner, 0),
                              (-w + corner, h + -corner, 90)]:
        for i in range(segs + 1):
            ang = math.radians(start_deg + 90 * i / segs)
            arcs.append((cx + ox + corner * math.cos(ang), cy,
                         cz + oz + corner * math.sin(ang)))
    # The order above is a little messy; use an explicit loop of 4 sides.
    pts = []
    for k, (sx, sz) in enumerate([(-1, -1), (1, -1), (1, 1), (-1, 1)]):
        start = 180 + 90 * k
        ox, oz = sx * (w - corner), sz * (h - corner)
        for i in range(segs + 1):
            ang = math.radians(start + 90 * i / segs)
            pts.append((cx + ox + corner * math.cos(ang), cy,
                        cz + oz + corner * math.sin(ang)))
    return bevel_curve(name, pts, thick, mat, closed=True)


for sign, side in ((-1, 'L'), (1, 'R')):
    fy = front_y(sign * EYE_X, EYE_Z) + 0.04
    rounded_rect_frame(f'LensFrame.{side}', sign * EYE_X, fy, EYE_Z,
                       w=0.13, h=0.105, corner=0.035, thick=0.016, depth=0.02,
                       mat=black_mat)
# Bridge.
by = front_y(0, EYE_Z + 0.02) + 0.035
bevel_curve('GlassesBridge',
            [(-0.04, by, EYE_Z + 0.01), (0, by + 0.01, EYE_Z + 0.03), (0.04, by, EYE_Z + 0.01)],
            0.014, black_mat)
# Temples going back along the head.
for sign, side in ((-1, 'L'), (1, 'R')):
    fy = front_y(sign * 0.26, EYE_Z) + 0.02
    by2 = back_y(sign * 0.28, EYE_Z - 0.02)
    bevel_curve(f'Temple.{side}',
                [(sign * 0.27, fy, EYE_Z - 0.01),
                 (sign * 0.30, (fy + by2) * 0.5, EYE_Z - 0.02),
                 (sign * 0.26, by2 + 0.04, EYE_Z - 0.04)],
                0.012, black_mat)

# Chunky headphones around the neck, not over the head.
neck_z = 0.70
for sign, side in ((-1, 'L'), (1, 'R')):
    cup_y = front_y(sign * 0.22, neck_z) - 0.08
    ellipsoid(f'HeadphoneCup.{side}', (sign * 0.34, cup_y, neck_z),
              (0.09, 0.08, 0.12), black_mat, segments=20)
    ellipsoid(f'HeadphoneCushion.{side}', (sign * 0.30, cup_y + 0.03, neck_z),
              (0.07, 0.06, 0.10), black_mat, segments=16)
# Band around the back of the neck.
band_pts = []
for i in range(9):
    t = i / 8
    ang = math.radians(200 + 140 * t)  # from left front-ish to right, around the back
    # Actually go from left cup, behind the neck, to right cup.
# Simpler: explicit points.
ly = front_y(-0.22, neck_z) - 0.08
ry = front_y(0.22, neck_z) - 0.08
by_n = back_y(0, neck_z + 0.04)
bevel_curve('HeadphoneBand',
            [(-0.32, ly, neck_z),
             (-0.28, (ly + by_n) * 0.3, neck_z + 0.05),
             (0.00, by_n - 0.02, neck_z + 0.06),
             (0.28, (ry + by_n) * 0.3, neck_z + 0.05),
             (0.32, ry, neck_z)],
            0.028, black_mat)

# Cardigan: a thickened torso shell with a front opening.
# Build from a scaled, clipped copy of a UV sphere, then solidify.
bpy.ops.mesh.primitive_uv_sphere_add(radius=1, location=(0, 0.05, 0.46), segments=32, ring_count=16)
cardigan = bpy.context.object
cardigan.name = 'Cardigan'
cardigan.scale = (0.42, 0.36, 0.38)
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
# Delete vertices in the head, under the hem, and a front V opening.
import bmesh
active(cardigan)
bpy.ops.object.mode_set(mode='EDIT')
bm = bmesh.from_edit_mesh(cardigan.data)
bm.verts.ensure_lookup_table()
dead = []
for v in bm.verts:
    x, y, z = v.co
    in_head = z > 0.78
    under_hem = z < 0.22
    opening = (y > 0.05 and abs(x) < 0.13 and z > 0.34 and z < 0.72)
    if in_head or under_hem or opening:
        dead.append(v)
bmesh.ops.delete(bm, geom=dead, context='VERTS')
bmesh.update_edit_mesh(cardigan.data)
bpy.ops.object.mode_set(mode='OBJECT')
# Sleeves: join two short capsules over the arms, then remesh the jacket.
for sign, side in ((-1, 'L'), (1, 'R')):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.15, location=(sign * 0.36, 0.07, 0.48), segments=20, ring_count=12)
    sleeve = bpy.context.object
    sleeve.name = f'Sleeve.{side}'
    sleeve.scale = (0.85, 0.80, 1.15)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    active(cardigan)
    sleeve.select_set(True)
    bpy.ops.object.join()
    cardigan = bpy.context.object
    cardigan.name = 'Cardigan'
# Remesh + solidify so the jacket is a soft vinyl shell.
rm = cardigan.modifiers.new('FuseJacket', 'REMESH')
rm.mode = 'VOXEL'
rm.voxel_size = 0.016
rm.use_smooth_shade = True
apply_mod(cardigan, 'FuseJacket')
sol = cardigan.modifiers.new('Thickness', 'SOLIDIFY')
sol.thickness = 0.03
sol.offset = 1
sol.use_quality_normals = True
apply_mod(cardigan, 'Thickness')
sm = cardigan.modifiers.new('RelaxJacket', 'CORRECTIVE_SMOOTH')
sm.iterations = 8
sm.factor = 0.5
sm.use_only_smooth = True
apply_mod(cardigan, 'RelaxJacket')
cardigan.data.materials.clear()
cardigan.data.materials.append(cardigan_mat)
shade_smooth(cardigan)

# Black tee panel in the cardigan opening, with a stacked chevron.
tee = ellipsoid('Tee', (0, 0.16, 0.52), (0.14, 0.06, 0.18), tee_mat, segments=20)
wrap = tee.modifiers.new('OnChest', 'SHRINKWRAP')
wrap.target = body
wrap.wrap_method = 'PROJECT'
wrap.use_project_y = True
wrap.use_negative_direction = True
wrap.offset = 0.012
apply_mod(tee, 'OnChest')
shade_smooth(tee)


def chevron(name, z, w, h, t):
    # A flat V pointing down, sitting on the tee.
    y = front_y(0, z) + 0.025
    verts = [
        (-w, y, z + h), (-w + t, y, z + h), (0, y, z + t),
        (w - t, y, z + h), (w, y, z + h), (0, y, z),
    ]
    # Extrude backward a little for thickness via a solid prism.
    depth = 0.02
    back = [(vx, y - depth, vz) for vx, _, vz in verts]
    faces = [
        (0, 1, 2, 5), (2, 3, 4, 5),  # front (split)
        (6, 11, 8, 7), (8, 11, 10, 9),
        (0, 6, 7, 1), (1, 7, 8, 2), (2, 8, 9, 3), (3, 9, 10, 4),
        (4, 10, 11, 5), (5, 11, 6, 0),
    ]
    # front faces as tris/quads from the 6-ring: use two n-gons carefully.
    me = bpy.data.meshes.new(name)
    # Simpler: two wedges.
    verts3 = [
        (-w, y, z + h), (0, y, z), (w, y, z + h),
        (-w + t, y, z + h), (0, y, z + t), (w - t, y, z + h),
        (-w, y - depth, z + h), (0, y - depth, z), (w, y - depth, z + h),
        (-w + t, y - depth, z + h), (0, y - depth, z + t), (w - t, y - depth, z + h),
    ]
    faces = [
        (0, 1, 4, 3), (1, 2, 5, 4),
        (6, 9, 10, 7), (7, 10, 11, 8),
        (0, 3, 9, 6), (3, 4, 10, 9), (4, 5, 11, 10), (5, 2, 8, 11),
        (2, 1, 7, 8), (1, 0, 6, 7),
    ]
    me.from_pydata(verts3, [], faces)
    me.update()
    obj = bpy.data.objects.new(name, me)
    scene.collection.objects.link(obj)
    obj.data.materials.append(chevron_mat)
    shade_smooth(obj)
    return obj


chevron('Chevron.Top', 0.58, 0.09, 0.055, 0.022)
chevron('Chevron.Bot', 0.50, 0.09, 0.055, 0.022)

# --- Studio ----------------------------------------------------------------
# Cream cyclorama + matching world, soft area lights, contact shadow under the feet.
sweep_mat = vinyl('Cream sweep', CREAM, rough=0.85, sss=0.0, spec=0.15)
profile = [(-8, 0), (1.4, 0), (2.1, 0.08), (2.8, 0.45), (3.3, 1.2), (3.5, 2.2), (3.5, 7)]
verts = [(x, y, z) for x in (-10, 10) for y, z in profile]
n = len(profile)
me = bpy.data.meshes.new('Sweep')
me.from_pydata(verts, [], [(i, i + 1, n + i + 1, n + i) for i in range(n - 1)])
me.update()
cyc = bpy.data.objects.new('StudioSweep', me)
scene.collection.objects.link(cyc)
me.materials.append(sweep_mat)
shade_smooth(cyc)
sub = cyc.modifiers.new('Round', 'SUBSURF')
sub.levels = 2
sub.render_levels = 2

world = bpy.data.worlds.new('CreamWorld')
scene.world = world
world.use_nodes = True
bg = world.node_tree.nodes['Background']
bg.inputs[0].default_value = (*CREAM, 1)
bg.inputs[1].default_value = 0.85


def area(name, loc, energy, color, size, track=(0, 0, 0.85)):
    data = bpy.data.lights.new(name, 'AREA')
    data.energy = energy
    data.color = color
    data.shape = 'DISK'
    data.size = size
    obj = bpy.data.objects.new(name, data)
    scene.collection.objects.link(obj)
    obj.location = loc
    obj.rotation_euler = (Vector(track) - obj.location).to_track_quat('-Z', 'Y').to_euler()
    return obj


area('Key', (-2.4, -3.6, 3.4), 350, (1.00, 0.95, 0.90), 2.8)
area('Fill', (3.2, -2.2, 2.4), 160, (0.90, 0.93, 1.00), 3.2)
area('Rim', (0.6, 3.0, 3.2), 180, (1.00, 0.96, 0.92), 2.4)
area('GroundBounce', (0.0, -1.0, 0.15), 40, (1.00, 0.96, 0.90), 3.0, track=(0, 0, 0.4))

cam_data = bpy.data.cameras.new('HeroCam')
cam = bpy.data.objects.new('HeroCam', cam_data)
scene.collection.objects.link(cam)
scene.camera = cam
TARGET = Vector((0, 0, height * 0.52))
ORTHO_SCALE = max(size.x, size.z) * 1.35


def frame(kind, angle_deg=28):
    """kind: 'hero' perspective 3/4, or 'ortho' for contact views."""
    if kind == 'hero':
        cam_data.type = 'PERSP'
        cam_data.lens = 85
        cam.location = (2.15, -3.55, 1.15)
        cam.rotation_euler = (TARGET - cam.location).to_track_quat('-Z', 'Y').to_euler()
        cam_data.dof.use_dof = False
    else:
        cam_data.type = 'ORTHO'
        cam_data.ortho_scale = ORTHO_SCALE
        ang = math.radians(angle_deg)
        cam.location = Vector(TARGET) + Vector((math.sin(ang), -math.cos(ang), 0.08)).normalized() * 6
        cam.rotation_euler = (TARGET - cam.location).to_track_quat('-Z', 'Y').to_euler()
    cyc.rotation_euler.z = math.atan2(cam.location.x, -cam.location.y)


frame('hero')

# --- Render ----------------------------------------------------------------
devices = []
if backend == 'OPTIX':
    devices = [dict(name=d.name, type=d.type, enabled=bool(d.use))
               for d in bpy.context.preferences.addons['cycles'].preferences.devices]
metadata = dict(
    version=VERSION,
    experiment=True,
    note='Preview experiment of a simple vinyl-toy cat mascot. Not a verified final.',
    blender_version=bpy.app.version_string,
    backend=backend,
    samples=args.samples,
    resolution=[args.res, args.res],
    contact_resolution=args.contact_res,
    denoiser='OpenImageDenoise' if args.engine == 'CYCLES' else None,
    view_transform='AgX',
    proportions=dict(TOTAL_HEIGHT=TOTAL_HEIGHT, HEAD_RATIO=HEAD_RATIO,
                     measured_height=round(height, 4), measured_head_ratio=round(ratio, 4),
                     measured_width=round(size.x, 4), measured_depth=round(size.y, 4),
                     eye_widths_across=round(EYE_WIDTHS_ACROSS, 4),
                     vertices=len(body.data.vertices), faces=len(body.data.polygons)),
    render_devices=devices,
    renders=[],
)


def render(path):
    # Keep the sweep behind the camera.
    cyc.rotation_euler.z = math.atan2(cam.location.x, -cam.location.y)
    scene.render.filepath = str(path)
    t0 = time.perf_counter()
    bpy.ops.render.render(write_still=True)
    sec = round(time.perf_counter() - t0, 3)
    metadata['renders'].append(dict(file=str(path.relative_to(out)), seconds=sec))
    print('RENDERED', path.name, f'{sec}s')
    (out / 'render-metadata.json').write_text(json.dumps(metadata, indent=2) + '\n')


if args.save_blend:
    bpy.ops.wm.save_as_mainfile(filepath=str(out / 'cat-vinyl.blend'))

# Hero 3/4 still at the requested resolution.
frame('hero')
render(out / 'hero_three_quarter.png')

# Four-view contact sheet (orthographic). Temporarily drop resolution.
scene.render.resolution_x = scene.render.resolution_y = args.contact_res
frame('ortho', 0)


def _render_view(path):
    render(path)


render_views(scene, out, _render_view, target=tuple(TARGET), scale=ORTHO_SCALE)

metadata['wall_seconds'] = round(time.perf_counter() - started, 3)
(out / 'render-metadata.json').write_text(json.dumps(metadata, indent=2) + '\n')
print('DONE', VERSION, 'wall', metadata['wall_seconds'], 's')
