"""Pixel v3 short: build the set, lights, cameras and the keyframed performance around the v3 rig, save film.blend.
blender -b <out>/pixel-v3.blend -P scripts/v3/film.py -- <tex_dir> <out_blend>

Everything that must stay in sync (shots, cameras, sun, performance beats, ball) is driven from the SHOTS / beat
constants in this one file. Scale: metres. The cat lives in the 'CatWorld' empty (0.11 scale: about 23 cm tall).
"""
import bpy, sys, os, math, json
from mathutils import Vector, Matrix
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pixrig
TEX, OUT_BLEND = sys.argv[sys.argv.index('--') + 1:][:2]
sc = bpy.context.scene; rig = bpy.data.objects['PixelRigV3']; R = pixrig.Rig(rig)
sin, cos, rad = math.sin, math.cos, math.radians
FPS = 24; END = 624

# ============================================================== clock: shots (start frame, name, lens mm, f-stop)
SHOTS = [(0, 'S1_wide', 35, 4.0), (60, 'S2_ear', 85, 5.6), (90, 'S3_wake', 50, 5.6), (156, 'S4_walk', 40, 4.0),
         (246, 'S5_paw', 100, 8.0), (294, 'S6_play', 35, 4.0), (438, 'S7_settle', 50, 4.0), (534, 'S8_hold', 35, 4.0)]
# performance beats (frames)
T_WAKE, T_STAND, T_WALK0, T_WALK1 = 92, 118, 168, 238
T_TAP, T_CROUCH, T_POUNCE, T_LAND = 268, 298, 318, 332
T_BAT_R, T_BAT_L = 372, 400
T_LOOK, T_LIE, T_SLEEP = 478, 540, 596
CYCLE, DUTY, STRIDE = 20, 0.6, 0.62
WALK_DIST = STRIDE * (T_WALK1 - T_WALK0 - CYCLE * 0.5) / CYCLE     # trapezoid speed profile, half a cycle of ramps
JUMP = 0.55

# ============================================================== materials
def mat(name, color, rough=0.5, metal=0.0, **kw):
    m = bpy.data.materials.new(name); m.use_nodes = True; b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (*color, 1); b.inputs['Roughness'].default_value = rough; b.inputs['Metallic'].default_value = metal
    for k, v in kw.items(): b.inputs[k].default_value = v
    return m
def wood(name, dark, light, grain_axis='X', scale=1.0, rough=(0.32, 0.55)):
    m = bpy.data.materials.new(name); m.use_nodes = True; t = m.node_tree; b = t.nodes['Principled BSDF']
    tc = t.nodes.new('ShaderNodeTexCoord'); mp = t.nodes.new('ShaderNodeMapping')
    s = {'X': (0.35, 4.0, 4.0), 'Y': (4.0, 0.35, 4.0)}[grain_axis]; mp.inputs['Scale'].default_value = tuple(v * scale for v in s)
    nz = t.nodes.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 3.0; nz.inputs['Detail'].default_value = 6; nz.inputs['Distortion'].default_value = 1.2
    wv = t.nodes.new('ShaderNodeTexWave'); wv.wave_type = 'BANDS'; wv.bands_direction = 'Y' if grain_axis == 'X' else 'X'
    wv.inputs['Scale'].default_value = 2.2; wv.inputs['Distortion'].default_value = 5.0; wv.inputs['Detail'].default_value = 3; wv.inputs['Detail Scale'].default_value = 1.5
    mx = t.nodes.new('ShaderNodeMix'); mx.data_type = 'RGBA'; mx.inputs['A'].default_value = (*dark, 1); mx.inputs['B'].default_value = (*light, 1)
    ad = t.nodes.new('ShaderNodeMath'); ad.operation = 'MULTIPLY'
    rr = t.nodes.new('ShaderNodeMapRange'); rr.inputs['To Min'].default_value = rough[0]; rr.inputs['To Max'].default_value = rough[1]
    bp = t.nodes.new('ShaderNodeBump'); bp.inputs['Strength'].default_value = 0.08
    L = t.links.new
    L(tc.outputs['Object'], mp.inputs['Vector']); L(mp.outputs['Vector'], nz.inputs['Vector']); L(mp.outputs['Vector'], wv.inputs['Vector'])
    L(wv.outputs['Fac'], ad.inputs[0]); L(nz.outputs['Fac'], ad.inputs[1]); L(ad.outputs[0], mx.inputs['Factor'])
    L(mx.outputs['Result'], b.inputs['Base Color']); L(nz.outputs['Fac'], rr.inputs['Value']); L(rr.outputs['Result'], b.inputs['Roughness'])
    L(wv.outputs['Fac'], bp.inputs['Height']); L(bp.outputs['Normal'], b.inputs['Normal'])
    return m
M = dict(
    desk=wood('DeskWalnut', (0.045, 0.022, 0.012), (0.20, 0.10, 0.05), 'X'),
    floor=wood('FloorOak', (0.16, 0.10, 0.055), (0.36, 0.24, 0.14), 'Y', 0.5, (0.4, 0.6)),
    wall=mat('WallPaint', (0.62, 0.55, 0.46), 0.92), ceil=mat('Ceiling', (0.75, 0.72, 0.68), 0.95),
    trim=mat('TrimWhite', (0.80, 0.78, 0.72), 0.35), brass=mat('Brass', (0.78, 0.56, 0.24), 0.28, 1.0),
    mug=mat('MugCeramic', (0.05, 0.27, 0.32), 0.12, **{'Coat Weight': 0.6}), pot=mat('Terracotta', (0.52, 0.22, 0.12), 0.8),
    soil=mat('Soil', (0.05, 0.035, 0.025), 1.0), leaf=mat('Leaf', (0.06, 0.26, 0.07), 0.38, **{'Subsurface Weight': 0.25}),
    book1=mat('BookRed', (0.42, 0.07, 0.06), 0.6), book2=mat('BookNavy', (0.04, 0.08, 0.2), 0.6), book3=mat('BookMustard', (0.62, 0.42, 0.08), 0.6),
    paper=mat('Paper', (0.80, 0.77, 0.68), 0.8), pencil=mat('Pencil', (0.85, 0.55, 0.05), 0.4), graphite=mat('Graphite', (0.03, 0.03, 0.03), 0.4),
    ball=None, metal=mat('DarkMetal', (0.05, 0.05, 0.055), 0.4, 1.0))
bm = bpy.data.materials.new('Ball'); bm.use_nodes = True; t = bm.node_tree; b = t.nodes['Principled BSDF']
tc = t.nodes.new('ShaderNodeTexCoord'); sp = t.nodes.new('ShaderNodeSeparateXYZ'); ab = t.nodes.new('ShaderNodeMath'); ab.operation = 'ABSOLUTE'
lt = t.nodes.new('ShaderNodeMath'); lt.operation = 'LESS_THAN'; lt.inputs[1].default_value = 0.055
mx = t.nodes.new('ShaderNodeMix'); mx.data_type = 'RGBA'; mx.inputs['A'].default_value = (0.03, 0.30, 0.50, 1); mx.inputs['B'].default_value = (0.85, 0.80, 0.70, 1)
t.links.new(tc.outputs['Object'], sp.inputs[0]); t.links.new(sp.outputs['Z'], ab.inputs[0]); t.links.new(ab.outputs[0], lt.inputs[0])
t.links.new(lt.outputs[0], mx.inputs['Factor']); t.links.new(mx.outputs['Result'], b.inputs['Base Color'])
b.inputs['Roughness'].default_value = 0.35; b.inputs['Coat Weight'].default_value = 0.3; M['ball'] = bm

# ============================================================== set
SET = bpy.data.collections.new('Set'); sc.collection.children.link(SET)
def finish(o, m, bevel):
    for c in list(o.users_collection): c.objects.unlink(o)
    SET.objects.link(o)
    if m: o.data.materials.append(m)
    if bevel:
        bv = o.modifiers.new('Bevel', 'BEVEL'); bv.width = bevel; bv.segments = 3; bv.limit_method = 'ANGLE'
    return o
def box(name, size, loc, m, bevel=0.004, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc, rotation=rot); o = bpy.context.object; o.name = name
    o.scale = size; bpy.ops.object.transform_apply(scale=True); return finish(o, m, bevel)
def cyl(name, r, h, loc, m, bevel=0.003, verts=48, rot=(0, 0, 0), r2=None):
    if r2 is None: bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=h, vertices=verts, location=loc, rotation=rot)
    else: bpy.ops.mesh.primitive_cone_add(radius1=r, radius2=r2, depth=h, vertices=verts, location=loc, rotation=rot)
    o = bpy.context.object; o.name = name
    for p in o.data.polygons: p.use_smooth = len(p.vertices) == 4
    return finish(o, m, bevel)
RX0, RX1, RY0, RY1, RZ = -1.25, 2.3, -3.0, 0.48, 2.6      # room extents
DESK_Z = 0.74
box('Floor', (RX1 - RX0, RY1 - RY0, 0.05), ((RX0 + RX1) / 2, (RY0 + RY1) / 2, -0.025), M['floor'], 0)
box('Ceiling', (RX1 - RX0, RY1 - RY0, 0.05), ((RX0 + RX1) / 2, (RY0 + RY1) / 2, RZ + 0.025), M['ceil'], 0)
box('WallBack', (RX1 - RX0, 0.1, RZ), ((RX0 + RX1) / 2, RY1 + 0.05, RZ / 2), M['wall'], 0)
box('WallRight', (0.1, RY1 - RY0, RZ), (RX1 + 0.05, (RY0 + RY1) / 2, RZ / 2), M['wall'], 0)
box('WallFront', (RX1 - RX0, 0.1, RZ), ((RX0 + RX1) / 2, RY0 - 0.05, RZ / 2), M['wall'], 0)
# left wall with the window opening
WY0, WY1, WZ0, WZ1 = -1.05, 0.20, 0.92, 2.05
wx = RX0 - 0.05
box('WallL_low', (0.1, RY1 - RY0, WZ0), (wx, (RY0 + RY1) / 2, WZ0 / 2), M['wall'], 0)
box('WallL_top', (0.1, RY1 - RY0, RZ - WZ1), (wx, (RY0 + RY1) / 2, (RZ + WZ1) / 2), M['wall'], 0)
box('WallL_a', (0.1, WY0 - RY0, WZ1 - WZ0), (wx, (RY0 + WY0) / 2, (WZ0 + WZ1) / 2), M['wall'], 0)
box('WallL_b', (0.1, RY1 - WY1, WZ1 - WZ0), (wx, (WY1 + RY1) / 2, (WZ0 + WZ1) / 2), M['wall'], 0)
fw = 0.05                                                    # window frame, mullions, sill
for nm, sz, lc in (('FrTop', (0.07, WY1 - WY0 + 2 * fw, fw), (wx, (WY0 + WY1) / 2, WZ1)), ('FrBot', (0.07, WY1 - WY0 + 2 * fw, fw), (wx, (WY0 + WY1) / 2, WZ0)),
                   ('FrA', (0.07, fw, WZ1 - WZ0), (wx, WY0, (WZ0 + WZ1) / 2)), ('FrB', (0.07, fw, WZ1 - WZ0), (wx, WY1, (WZ0 + WZ1) / 2)),
                   ('MulV', (0.04, 0.035, WZ1 - WZ0), (wx, (WY0 + WY1) / 2, (WZ0 + WZ1) / 2)),
                   ('MulH1', (0.04, WY1 - WY0, 0.035), (wx, (WY0 + WY1) / 2, WZ0 + (WZ1 - WZ0) * 0.36)),
                   ('MulH2', (0.04, WY1 - WY0, 0.035), (wx, (WY0 + WY1) / 2, WZ0 + (WZ1 - WZ0) * 0.70)),
                   ('Sill', (0.20, WY1 - WY0 + 0.16, 0.035), (RX0 + 0.06, (WY0 + WY1) / 2, WZ0 - 0.03))):
    box('Win' + nm, sz, lc, M['trim'], 0.004)
box('Skirting', (RX1 - RX0, 0.02, 0.09), ((RX0 + RX1) / 2, RY1 - 0.01, 0.045), M['trim'], 0.003)
# desk
DX, DY = 1.6, 0.78
box('DeskTop', (DX, DY, 0.04), (0, 0.04, DESK_Z - 0.02), M['desk'], 0.006)
for sx_ in (-1, 1):
    for sy_ in (-1, 1): box(f'DeskLeg{sx_}{sy_}', (0.05, 0.05, DESK_Z - 0.04), (sx_ * (DX / 2 - 0.06), 0.04 + sy_ * (DY / 2 - 0.06), (DESK_Z - 0.04) / 2), M['desk'], 0.004)
box('DeskApron', (DX - 0.16, 0.02, 0.08), (0, 0.04 + DY / 2 - 0.07, DESK_Z - 0.08), M['desk'], 0.003)
# lamp (practical): brass base and stem, glowing dome
LAMP = Vector((0.58, 0.24, DESK_Z))
cyl('LampBase', 0.075, 0.018, LAMP + Vector((0, 0, 0.009)), M['brass'], 0.004)
cyl('LampStem', 0.012, 0.20, LAMP + Vector((0, 0, 0.118)), M['brass'], 0)
bpy.ops.mesh.primitive_uv_sphere_add(radius=0.115, segments=64, ring_count=32, location=LAMP + Vector((0, 0, 0.215))); dome = bpy.context.object; dome.name = 'LampDome'
import bmesh
bmh = bmesh.new(); bmh.from_mesh(dome.data); bmesh.ops.delete(bmh, geom=[v for v in bmh.verts if v.co.z < -0.012], context='VERTS'); bmh.to_mesh(dome.data); bmh.free()
dome.scale = (1, 1, 0.72)
for p in dome.data.polygons: p.use_smooth = True
so = dome.modifiers.new('Solid', 'SOLIDIFY'); so.thickness = 0.004
dm = bpy.data.materials.new('LampShade'); dm.use_nodes = True; t = dm.node_tree; b = t.nodes['Principled BSDF']
b.inputs['Base Color'].default_value = (0.95, 0.62, 0.32, 1); b.inputs['Roughness'].default_value = 0.4
b.inputs['Emission Color'].default_value = (1.0, 0.50, 0.20, 1); b.inputs['Emission Strength'].default_value = 1.5
b.inputs['Transmission Weight'].default_value = 0.3
finish(dome, dm, 0)
ld = bpy.data.lights.new('LampLight', 'POINT'); ld.energy = 3.0; ld.color = (1.0, 0.62, 0.34); ld.shadow_soft_size = 0.03
lamp_light = bpy.data.objects.new('LampLight', ld); SET.objects.link(lamp_light); lamp_light.location = LAMP + Vector((0, 0, 0.17))
# mug
MUG = Vector((-0.28, 0.27, DESK_Z))
mug = cyl('Mug', 0.042, 0.092, MUG + Vector((0, 0, 0.046)), M['mug'], 0)
bmh = bmesh.new(); bmh.from_mesh(mug.data); bmesh.ops.delete(bmh, geom=[f for f in bmh.faces if f.normal.z > 0.9], context='FACES'); bmh.to_mesh(mug.data); bmh.free()
s2 = mug.modifiers.new('Solid', 'SOLIDIFY'); s2.thickness = 0.005; s2.offset = 1; bv = mug.modifiers.new('Bevel', 'BEVEL'); bv.width = 0.0015; bv.segments = 2
bpy.ops.mesh.primitive_torus_add(major_radius=0.026, minor_radius=0.006, location=MUG + Vector((0.046, 0, 0.048)), rotation=(rad(90), 0, 0)); h_ = bpy.context.object; h_.name = 'MugHandle'
for p in h_.data.polygons: p.use_smooth = True
finish(h_, M['mug'], 0)
# books + notebook + pencil
BK = Vector((0.52, 0.04, DESK_Z))
box('Book1', (0.24, 0.17, 0.035), BK + Vector((0, 0, 0.0175)), M['book1'], 0.003, (0, 0, rad(8)))
box('Book2', (0.22, 0.155, 0.028), BK + Vector((0.005, 0.004, 0.049)), M['book2'], 0.003, (0, 0, rad(-5)))
box('Book3', (0.19, 0.14, 0.03), BK + Vector((-0.004, 0, 0.078)), M['book3'], 0.003, (0, 0, rad(14)))
box('Notebook', (0.21, 0.29, 0.012), (-0.50, -0.14, DESK_Z + 0.006), M['paper'], 0.002, (0, 0, rad(-12)))
cyl('Pencil', 0.004, 0.17, (-0.47, -0.10, DESK_Z + 0.016), M['pencil'], 0, 6, (rad(90), 0, rad(40)))
# plant
PL = Vector((-0.60, 0.26, DESK_Z))
cyl('Pot', 0.055, 0.10, PL + Vector((0, 0, 0.05)), M['pot'], 0.003, r2=0.07)
cyl('Soil', 0.064, 0.006, PL + Vector((0, 0, 0.094)), M['soil'], 0)
import random; random.seed(4)
for i in range(13):
    a = i * 2.39996; rr_ = 0.03 + 0.012 * (i % 4); hgt = 0.14 + 0.022 * i * 0.6 + random.uniform(0, 0.03); tilt = rad(35 + 5 * (i % 5))
    tip = PL + Vector((cos(a) * (rr_ + hgt * sin(tilt)), sin(a) * (rr_ + hgt * sin(tilt)), 0.095 + hgt * cos(tilt)))
    base = PL + Vector((cos(a) * rr_ * 0.4, sin(a) * rr_ * 0.4, 0.095)); mid = (base + tip) / 2; d = (tip - base)
    cyl(f'Stem{i}', 0.0022, d.length, mid, M['leaf'], 0, 8, d.to_track_quat('Z', 'Y').to_euler())
    bpy.ops.mesh.primitive_uv_sphere_add(radius=1, segments=24, ring_count=12, location=tip); lf = bpy.context.object; lf.name = f'Leaf{i}'
    lf.scale = (0.03, 0.045, 0.004); lf.rotation_euler = (tilt * 0.8, 0, a + rad(90))
    for p in lf.data.polygons: p.use_smooth = True
    finish(lf, M['leaf'], 0)
# framed portrait on the back wall
PIC = Vector((0.18, RY1 - 0.012, 1.42))
box('Frame', (0.46, 0.024, 0.46), PIC, M['desk'], 0.004)
bpy.ops.mesh.primitive_plane_add(size=0.40, location=PIC + Vector((0, -0.0135, 0)), rotation=(rad(90), 0, 0)); pic = bpy.context.object; pic.name = 'Portrait'
pm = bpy.data.materials.new('Portrait'); pm.use_nodes = True; t = pm.node_tree; im = t.nodes.new('ShaderNodeTexImage'); im.image = bpy.data.images.load(f'{TEX}/portrait.png')
t.links.new(im.outputs['Color'], t.nodes['Principled BSDF'].inputs['Base Color']); t.nodes['Principled BSDF'].inputs['Roughness'].default_value = 0.25
finish(pic, pm, 0)
box('Shelf', (0.7, 0.16, 0.025), (-0.55, RY1 - 0.08, 1.45), M['desk'], 0.004)
box('ShelfBookA', (0.035, 0.12, 0.19), (-0.80, RY1 - 0.08, 1.558), M['book2'], 0.002, (0, rad(-4), 0))
box('ShelfBookB', (0.03, 0.12, 0.17), (-0.76, RY1 - 0.08, 1.548), M['book3'], 0.002)
box('ShelfBookC', (0.04, 0.12, 0.20), (-0.72, RY1 - 0.08, 1.563), M['book1'], 0.002, (0, rad(3), 0))
cyl('ShelfPot', 0.045, 0.08, (-0.36, RY1 - 0.08, 1.503), M['mug'], 0.003, r2=0.055)

# ============================================================== cat placement
HEAD_DIR = rad(-60)                      # cat walks toward the window (left) and slightly toward the room
CS = Vector((0.36, 0.14, DESK_Z))
cw = bpy.data.objects.new('CatWorld', None); sc.collection.objects.link(cw); cw.location = CS; cw.scale = (0.11, 0.11, 0.11); cw.rotation_euler = (0, 0, HEAD_DIR)
rig.parent = cw
def world(p): return cw.matrix_world @ Vector(p) if False else (Matrix.Translation(CS) @ Matrix.Rotation(HEAD_DIR, 4, 'Z') @ Matrix.Scale(0.11, 4)) @ Vector(p)
BR = 0.17
bpy.ops.mesh.primitive_uv_sphere_add(radius=BR, segments=64, ring_count=32); ball = bpy.context.object; ball.name = 'Ball'; ball.parent = cw
for p in ball.data.polygons: p.use_smooth = True
ball.data.materials.append(M['ball']); ball.rotation_mode = 'XYZ'
# focus target: a helper bone on the face (a child of the head bone), followed by an empty the cameras focus on
bpy.context.view_layer.objects.active = rig; bpy.ops.object.mode_set(mode='EDIT')
fb = rig.data.edit_bones.new('focus'); fb.head = (0, -0.95, 1.28); fb.tail = (0, -0.95, 1.40); fb.parent = rig.data.edit_bones['head']; fb.use_deform = False
bpy.ops.object.mode_set(mode='OBJECT')
focus = bpy.data.objects.new('FocusHead', None); sc.collection.objects.link(focus)
cl_ = focus.constraints.new('COPY_LOCATION'); cl_.target = rig; cl_.subtarget = 'focus'
R = pixrig.Rig(rig)
for mname in ('PixelA', 'PixelB'): bpy.data.materials[mname].node_tree.nodes['Principled BSDF'].inputs['Subsurface Scale'].default_value = 0.004

# ============================================================== performance (cat units, armature space; cat faces -Y)
fr = R.foot_rest
Y1 = -WALK_DIST; Y2 = Y1 - JUMP
def body_y(f):
    """trapezoid speed profile for the walk: ramps of CYCLE/2 at both ends"""
    t0, t1, r = T_WALK0, T_WALK1, CYCLE / 2; v = STRIDE / CYCLE
    if f <= t0: return 0.0
    if f >= t1: return Y1
    if f < t0 + r: return -v * (f - t0) ** 2 / (2 * r)
    if f > t1 - r: return Y1 + v * (t1 - f) ** 2 / (2 * r)
    return -v * (r / 2 + (f - t0 - r))
LOAF_Z = -0.33
def loaf(f, sleepy=True):
    R.kloc(f, 'body', (0, 0, LOAF_Z) if f < 300 else (0, Y2, LOAF_Z)); R.krot(f, 'body'); R.krot(f, 'chest', rx=3)
def tail(f, lean=0, sway=0, curl=0, lag=0):
    """lean: tail base forward(+)/back(-); sway: sideways at the base; curl: per-bone sideways curl. Keys are offset per bone (overlap)."""
    for i in range(1, 9):
        R.krot(f + lag * (i - 1), f'tail{i}', rx=lean if i == 1 else lean * 0.08, ry=(sway if i == 1 else 0) + curl * (0.5 if i == 1 else 1))

# ---- S1/S2: asleep in a loaf, breathing, ear twitches
for f in (0, 1): loaf(f)
R.kblink(0, 1); R.kblink(42, 1); R.kblink(54, 0.32)      # asleep in the wide; drowsy eyes open just before the close-up
R.kblink(70, 0.26); R.kblink(79, 0.3); R.kblink(82, 1); R.kblink(86, 0.28)      # shot 2: half-lidded, ear twitches, one slow blink
R.krot(0, 'head', rx=10, ry=5, rz=-8); tail(0, lean=-78, curl=27)
for f in range(0, 92, 24):                        # breathing: slow chest swell
    R.kscale(f, 'chest', 1, 1, 1); R.kscale(f + 12, 'chest', 1.035, 1.0, 1.045)
    R.krot(f, 'head', rx=10, ry=5, rz=-8); R.krot(f + 13, 'head', rx=8.6, ry=5, rz=-8)
R.kscale(96, 'chest', 1, 1, 1)
for e in ('L', 'R'): R.krot(0, 'ear.' + e); R.krot(62, 'ear.' + e)
for f0 in (66, 78):                               # twitch: fast out, overshoot back, settle
    R.krot(f0, 'ear.L'); R.krot(f0 + 2, 'ear.L', ry=16, rx=10); R.krot(f0 + 5, 'ear.L', ry=-4, rx=-2); R.krot(f0 + 8, 'ear.L')
R.krot(84, 'ear.R'); R.krot(86, 'ear.R', ry=-12, rx=6); R.krot(89, 'ear.R', ry=3); R.krot(92, 'ear.R')

# ---- S3: wake (slow blink open, head lift with overshoot), stand and stretch
R.kblink(T_WAKE, 0.28); R.kblink(T_WAKE + 5, 0.9); R.kblink(T_WAKE + 9, 0.15); R.kblink(T_WAKE + 16, 0); R.kblink(T_WAKE + 40, 0); R.kblink(T_WAKE + 43, 1); R.kblink(T_WAKE + 46, 0)
R.krot(T_WAKE + 2, 'head', rx=8.6, ry=5, rz=-8); R.krot(T_WAKE + 12, 'head', rx=-8, ry=-3, rz=4); R.krot(T_WAKE + 17, 'head', rx=-3, ry=0, rz=10); R.krot(T_WAKE + 24, 'head', rx=-5, ry=2, rz=8)
for e, s in (('L', 1), ('R', -1)): R.krot(T_WAKE + 6, 'ear.' + e); R.krot(T_WAKE + 13, 'ear.' + e, rx=-10, ry=5 * s); R.krot(T_WAKE + 19, 'ear.' + e, rx=3); R.krot(T_WAKE + 24, 'ear.' + e)
S = T_STAND
loaf(S)
R.kloc(S + 5, 'body', (0, 0.02, LOAF_Z - 0.02)); R.kscale(S, 'body'); R.kscale(S + 5, 'body', 1.03, 1.0, 0.95)          # anticipation: sink
R.kloc(S + 13, 'body', (0, 0.10, 0.03)); R.krot(S + 13, 'body', rx=17); R.krot(S + 13, 'chest', rx=10); R.kscale(S + 13, 'body', 0.97, 1.08, 0.98)   # stretch: rump up, chest low
R.kloc(S + 21, 'body', (0, 0.12, 0.04)); R.krot(S + 21, 'body', rx=19); R.krot(S + 21, 'chest', rx=12); R.kscale(S + 21, 'body', 0.96, 1.10, 0.98)
R.kloc(S + 29, 'body', (0, -0.04, 0.05)); R.krot(S + 29, 'body', rx=-5); R.krot(S + 29, 'chest', rx=-4); R.kscale(S + 29, 'body', 1.02, 0.97, 1.03)   # overshoot up/forward
R.kloc(S + 35, 'body', (0, 0, 0)); R.krot(S + 35, 'body'); R.krot(S + 35, 'chest'); R.kscale(S + 35, 'body')
for l in ('FL', 'FR'):
    R.kfoot(S + 5, l, fr[l]); R.kfoot(S + 13, l, fr[l] + Vector((0, -0.30, 0))); R.kfoot(S + 21, l, fr[l] + Vector((0, -0.32, 0)))
    R.kfoot(S + 25, l, fr[l] + Vector((0, -0.15, 0.07))); R.kfoot(S + 29, l, fr[l])
for l in ('HL', 'HR'): R.kfoot(S, l, fr[l]); R.kfoot(S + 36, l, fr[l])
# head stays facing forward through the stretch (an earlier version tipped it back 26 degrees, which showed only the white chin)
R.krot(S + 4, 'head', rx=-5, ry=2, rz=8); R.krot(S + 14, 'head', rx=-9, rz=2); R.krot(S + 22, 'head', rx=-11, ry=3); R.krot(S + 31, 'head', rx=5); R.krot(S + 38, 'head', rx=0, rz=-6)
tail(S, lean=-78, curl=27); tail(S + 12, lean=-30, curl=8, lag=1); tail(S + 22, lean=8, curl=-3, lag=1); tail(S + 34, lean=0, curl=0, lag=1)

# ---- S4: notices the ball, walks to it (4-beat walk, IK feet planted)
A = 156
R.krot(A, 'head', rx=0, rz=-6); R.krot(A + 5, 'head', rx=8, rz=-3, ry=-4); R.krot(A + 8, 'head', rx=5, rz=-2, ry=7)      # double-take + tilt
for e, s in (('L', 1), ('R', -1)): R.krot(A, 'ear.' + e); R.krot(A + 5, 'ear.' + e, rx=-12, ry=4 * s); R.krot(A + 10, 'ear.' + e, rx=-6)
R.kloc(A + 4, 'body', (0, 0, 0)); R.kloc(T_WALK0 - 2, 'body', (0, 0.04, -0.05)); R.krot(T_WALK0 - 2, 'body', rx=3)     # anticipation: settle back before going
PHASE = {'HL': 0.0, 'FL': 0.25, 'HR': 0.5, 'FR': 0.75}
a_off = STRIDE * DUTY / 2
td_front = []
for l, ph in PHASE.items():
    R.kfoot(T_WALK0 - 3, l, fr[l]); last = fr[l].copy(); k = 0
    while True:
        lift = T_WALK0 + (k + ph) * CYCLE; td = lift + (1 - DUTY) * CYCLE
        if td > T_WALK1 + 4: break
        final = td + CYCLE > T_WALK1 + 4
        nxt = fr[l] + Vector((0, Y1 if final else body_y(td) - a_off, 0))
        R.kfoot(round(lift), l, last)                                              # planted until lift-off
        sw = td - lift                                                             # springy swing: toe-off, high passing pose, soft reach, then place
        R.kfoot(round(lift + sw * 0.22), l, last + Vector((0, 0.02, 0.11)))
        R.kfoot(round(lift + sw * 0.55), l, (last + nxt) / 2 + Vector((0, -0.05, 0.25)))
        R.kfoot(round(lift + sw * 0.85), l, nxt + Vector((0, -0.05, 0.07)))
        R.kfoot(round(td), l, nxt); last = nxt
        if l[0] == 'F': td_front.append((round(td), l))
        k += 1
    R.kfoot(T_WALK1 + 8, l, last)
for f in range(T_WALK0, T_WALK1 + 1, 2):                                           # body travel (y) on twos, with bob / roll / yaw layered on
    ph = (f - T_WALK0) / CYCLE * 2 * math.pi; amp = min(1, (f - T_WALK0) / 8, (T_WALK1 - f) / 8)
    # lower stance (knees stay bent) and a clear two-beat bounce
    R.kloc(f, 'body', (0.025 * amp * sin(ph + 0.6), body_y(f), amp * (-0.055 + 0.05 * cos(2 * ph + 0.4))))
    R.krot(f, 'body', rx=2.0 * amp + 2.5 * amp * sin(2 * ph), ry=4.5 * amp * sin(ph + 0.3), rz=5 * amp * sin(ph + 1.2))
    R.kscale(f, 'body', 1 + 0.02 * amp * cos(2 * ph + 0.4), 1.0, 1 - 0.03 * amp * cos(2 * ph + 0.4))
    R.krot(f, 'chest', rz=-6 * amp * sin(ph + 1.2), ry=-3 * amp * sin(ph + 0.3))
for f in range(T_WALK0, T_WALK1 + 1, 5):                                           # head: delayed counter-motion, eyes on the ball
    ph = (f - 3 - T_WALK0) / CYCLE * 2 * math.pi; amp = min(1, (f - T_WALK0) / 8, (T_WALK1 - f) / 8)
    R.krot(f, 'head', rx=7 + 3 * amp * cos(2 * ph), ry=-3 * amp * sin(ph), rz=-2 - 4 * amp * sin(ph + 1.2))
    for e, s in (('L', 1), ('R', -1)): R.krot(f + 2, 'ear.' + e, rx=-5 + 5 * amp * cos(2 * ph - 0.8), ry=2 * s * amp)
    tail(f, lean=6, sway=9 * amp * sin(ph + 2.0), curl=5 * amp * sin(ph + 1.0), lag=1)
E = T_WALK1
R.kscale(E + 6, 'body')
R.kloc(E + 4, 'body', (0, Y1 - 0.05, -0.03)); R.krot(E + 4, 'body', rx=5); R.kloc(E + 9, 'body', (0, Y1 + 0.015, 0.01)); R.krot(E + 9, 'body', rx=-1.5)   # stop: overshoot forward, rock back, settle
R.kloc(E + 14, 'body', (0, Y1, 0)); R.krot(E + 14, 'body'); R.krot(E + 6, 'chest'); R.krot(E + 6, 'head', rx=14, rz=-4); R.krot(E + 12, 'head', rx=10, rz=-6, ry=6)
tail(E + 6, lean=14, lag=1); tail(E + 14, lean=2, lag=1)

# ---- S5: curious tap with the front-right paw
def bat(f, leg, hit, weight=1.0, wind=10):
    """anticipation (weight shift + paw lifts back), strike through the hit point, follow-through, settle"""
    sgn = 1 if leg == 'FL' else -1; rest = fr[leg] + Vector((0, Ycur, 0)); hit = Vector(hit)
    R.kfoot(f - wind - 2, leg, rest); R.kfoot(f - wind + 4, leg, rest + Vector((0.02 * sgn, 0.06, 0.20)))
    R.kfoot(f - 3, leg, hit + Vector((0.10 * sgn, 0.14, 0.14))); R.kfoot(f, leg, hit + Vector((0, 0.05, 0.02)))
    R.kfoot(f + 3, leg, hit + Vector((-0.16 * sgn * weight, -0.06, -0.06))); R.kfoot(f + 8, leg, rest + Vector((0, -0.10, 0.12))); R.kfoot(f + 13, leg, rest)
    R.kloc(f - wind - 2, 'body', (0, Ycur, 0)); R.kloc(f - wind + 4, 'body', (-0.07 * sgn, Ycur + 0.04, -0.03)); R.kloc(f - 2, 'body', (-0.08 * sgn, Ycur + 0.02, -0.02))
    R.kloc(f + 3, 'body', (-0.03 * sgn, Ycur - 0.05, -0.04)); R.kloc(f + 13, 'body', (0, Ycur, 0))
    R.krot(f - wind + 4, 'body', ry=-5 * sgn, rx=-3); R.krot(f + 3, 'body', ry=3 * sgn, rx=4); R.krot(f + 13, 'body')
    R.krot(f - wind + 4, 'chest', rz=6 * sgn, rx=-5); R.krot(f + 3, 'chest', rz=-7 * sgn, rx=5); R.krot(f + 13, 'chest')
Ycur = Y1
B0 = Vector((-0.28, Y1 - 0.98, BR)); B1 = Vector((-0.27, Y1 - 1.28, BR))
bat(T_TAP, 'FR', B0 + Vector((0, 0.16, 0.05)), weight=0.3, wind=14)
R.krot(T_TAP - 14, 'head', rx=10, rz=-6, ry=6); R.krot(T_TAP - 4, 'head', rx=20, rz=-10, ry=-3); R.krot(T_TAP + 6, 'head', rx=13, rz=-8, ry=-8); R.krot(T_TAP + 16, 'head', rx=17, rz=-7, ry=4)
for e, s in (('L', 1), ('R', -1)): R.krot(T_TAP - 2, 'ear.' + e, rx=-6); R.krot(T_TAP + 2, 'ear.' + e, rx=8, ry=-6 * s); R.krot(T_TAP + 8, 'ear.' + e, rx=-8)
tail(T_TAP - 10, lean=2, lag=1); tail(T_TAP, lean=10, sway=-12, curl=-6, lag=1); tail(T_TAP + 12, lean=4, sway=10, curl=5, lag=1)

# ---- S6: crouch + wiggle (anticipation), pounce with stretch, land with squash, then bat the ball between the paws
C = T_CROUCH
R.kloc(C, 'body', (0, Y1, 0)); R.kscale(C, 'body')
R.kloc(C + 7, 'body', (0, Y1 + 0.10, -0.16)); R.krot(C + 7, 'body', rx=-7); R.kscale(C + 7, 'body', 1.05, 0.95, 0.90); R.krot(C + 7, 'chest', rx=10)
for i, f in enumerate(range(C + 8, C + 19, 3)):                                    # butt wiggle
    s = 1 if i % 2 == 0 else -1
    R.kloc(f, 'body', (0.035 * s, Y1 + 0.11, -0.17)); R.krot(f, 'body', rx=-8, rz=6 * s, ry=3 * s)
    tail(f, lean=-12, sway=16 * s, curl=7 * s, lag=1)
R.krot(C + 7, 'head', rx=4, rz=-6); R.krot(C + 16, 'head', rx=2, rz=-6)
for e in ('L', 'R'): R.krot(C + 7, 'ear.' + e, rx=10); R.krot(T_POUNCE, 'ear.' + e, rx=14)
P = T_POUNCE; L_ = T_LAND
R.kloc(P, 'body', (0, Y1 + 0.12, -0.18)); R.krot(P, 'body', rx=-8); R.kscale(P, 'body', 1.06, 0.93, 0.90)
R.kloc(P + 4, 'body', (0, Y1 - 0.12, 0.16)); R.krot(P + 4, 'body', rx=-16); R.kscale(P + 4, 'body', 0.93, 1.15, 0.96)                 # launch: stretch
R.kloc(P + 8, 'body', (0, Y1 - 0.34, 0.34)); R.krot(P + 8, 'body', rx=2); R.kscale(P + 8, 'body', 0.96, 1.08, 0.98)                    # apex
R.kloc(L_, 'body', (0, Y2 + 0.02, 0.02)); R.krot(L_, 'body', rx=14); R.kscale(L_, 'body', 0.95, 1.08, 0.98)                           # front paws reach the ball
R.kloc(L_ + 3, 'body', (0, Y2 - 0.03, -0.15)); R.krot(L_ + 3, 'body', rx=6); R.kscale(L_ + 3, 'body', 1.10, 0.96, 0.84)               # squash
R.kloc(L_ + 8, 'body', (0, Y2 + 0.01, 0.04)); R.krot(L_ + 8, 'body', rx=-3); R.kscale(L_ + 8, 'body', 0.98, 1.0, 1.04)               # rebound
R.kloc(L_ + 13, 'body', (0, Y2, 0)); R.krot(L_ + 13, 'body'); R.kscale(L_ + 13, 'body')
R.krot(P, 'chest', rx=10); R.krot(P + 4, 'chest', rx=-12); R.krot(L_, 'chest', rx=8); R.krot(L_ + 8, 'chest')
for l in ('FL', 'FR', 'HL', 'HR'):
    a0 = fr[l] + Vector((0, Y1, 0)); a1 = fr[l] + Vector((0, Y2, 0)); front = l[0] == 'F'
    R.kfoot(P - 1, l, a0)
    if front:
        R.kfoot(P + 3, l, a0 + Vector((0, -0.18, 0.22))); R.kfoot(P + 8, l, a0 + Vector((0, -0.62, 0.42)))
        R.kfoot(L_ - 1, l, a1 + Vector((0, -0.30, 0.10))); R.kfoot(L_ + 2, l, a1 + Vector((0, -0.22, 0))); R.kfoot(L_ + 12, l, a1 + Vector((0, -0.22, 0)))
        R.kfoot(L_ + 16, l, a1 + Vector((0, -0.10, 0.10))); R.kfoot(L_ + 20, l, a1)
    else:
        R.kfoot(P + 3, l, a0); R.kfoot(P + 8, l, a0 + Vector((0, -0.22, 0.34))); R.kfoot(L_ + 1, l, a1 + Vector((0, 0.05, 0.12))); R.kfoot(L_ + 4, l, a1)
R.krot(P + 2, 'head', rx=-12, rz=-4); R.krot(P + 8, 'head', rx=10); R.krot(L_ + 4, 'head', rx=24); R.krot(L_ + 10, 'head', rx=-14, rz=-8); R.krot(L_ + 16, 'head', rx=-6, rz=-14)
tail(P, lean=-14, lag=1); tail(P + 5, lean=-34, lag=1); tail(L_ + 2, lean=24, lag=1); tail(L_ + 10, lean=-8, lag=1); tail(L_ + 18, lean=4, lag=1)
for e in ('L', 'R'): R.krot(P + 5, 'ear.' + e, rx=18); R.krot(L_ + 3, 'ear.' + e, rx=-16); R.krot(L_ + 8, 'ear.' + e, rx=6); R.krot(L_ + 13, 'ear.' + e)
R.kblink(L_ - 2, 0); R.kblink(L_ + 2, 1); R.kblink(L_ + 6, 0)
Ycur = Y2
PR = Vector((-0.30, Y2 - 0.92, 0.42)); PL_ = Vector((0.30, Y2 - 0.92, 0.42))
bat(T_BAT_R, 'FR', PR, weight=1.0); bat(T_BAT_L, 'FL', PL_, weight=1.3)
R.kloc(T_BAT_L + 22, 'body', (0, Y2, 0)); R.krot(T_BAT_L + 22, 'body')
for f, s in ((T_BAT_R, 14), (T_BAT_L, -16)):                                      # tail counter-flick on each bat (secondary)
    tail(f - 6, lean=2, sway=-s * 0.6, curl=-s * 0.3, lag=1); tail(f + 2, lean=8, sway=s, curl=s * 0.6, lag=1); tail(f + 14, lean=2, sway=-s * 0.25, lag=1)
    for e in ('L', 'R'): R.krot(f - 3, 'ear.' + e, rx=-8); R.krot(f + 2, 'ear.' + e, rx=10); R.krot(f + 8, 'ear.' + e, rx=-3); R.krot(f + 14, 'ear.' + e)

# ---- ball: analytic projectile / roll, baked per frame (physics object, not a hand-keyed one)
F1 = Vector((-0.46, Y2 - 1.08, BR)); F2 = Vector((-0.40, Y2 - 1.00, BR)); MID = Vector((0.0, Y2 - 1.06, BR))
F3 = Vector((-0.95, Y2 - 1.18, BR)); F4 = Vector((-1.35, Y2 - 1.12, BR)); F5 = Vector((-1.55, Y2 - 1.07, BR)); F6 = Vector((-1.95, Y2 - 0.97, BR))
ARCS = [(T_LAND + 1, T_LAND + 15, B1, F1, 0.55), (T_LAND + 15, T_LAND + 27, F1, F2, 0.20), (T_LAND + 27, T_BAT_R, F2, PR, 0.24),
        (T_BAT_R, T_BAT_R + 14, PR, MID, 0.04), (T_BAT_R + 14, T_BAT_L, MID, PL_, 0.24),
        (T_BAT_L, T_BAT_L + 16, PL_, F3, 0.22), (T_BAT_L + 16, T_BAT_L + 28, F3, F4, 0.12), (T_BAT_L + 28, T_BAT_L + 36, F4, F5, 0.04)]
def ball_pos(f):
    if f <= T_TAP: return B0.copy()
    if f <= T_TAP + 24: u = (f - T_TAP) / 24; return B0.lerp(B1, 1 - (1 - u) ** 2)
    if f <= ARCS[0][0]: return B1.copy()
    for f0, f1, a, b_, h in ARCS:
        if f <= f1: u = (f - f0) / (f1 - f0); p = a.lerp(b_, u); p.z = a.z + (b_.z - a.z) * u + 4 * h * u * (1 - u); return p
    f0 = ARCS[-1][1]
    if f <= f0 + 44: u = (f - f0) / 44; return F5.lerp(F6, 1 - (1 - u) ** 2)
    return F6.copy()
rx_ = ry_ = 0.0; prev = ball_pos(0)
for f in range(0, END + 1):
    p = ball_pos(f); rx_ += -(p.y - prev.y) / BR; ry_ += (p.x - prev.x) / BR; prev = p
    ball.location = p; ball.rotation_euler = (rx_, ry_, 0.4); ball.keyframe_insert('location', frame=f); ball.keyframe_insert('rotation_euler', frame=f)

# ---- head tracks the ball through the play (keys on fours, looking where the ball was two frames ago = slight lag)
def aim(f, lagf=2, gain=0.85):
    p = ball_pos(f - lagf); hy = body_at[1] - 0.45; d = p - Vector((0, hy, 1.30))
    yaw = math.degrees(math.atan2(d.x, -d.y)) * gain; pitch = math.degrees(math.atan2(-d.z, math.hypot(d.x, d.y))) * 0.8
    return max(-10, min(24, pitch)), max(-38, min(38, yaw))      # a head, not an owl: keep the neck within a believable range
body_at = (0, Y2, 0)
for f in range(T_LAND + 20, T_LOOK - 6, 4):
    pitch, yaw = aim(f); R.krot(f, 'head', rx=pitch - 6, rz=yaw, ry=-yaw * 0.25)

# ---- S7: watches the ball roll away, then looks up to the window light; slow blink
K = T_LOOK
R.krot(K - 4, 'head', rx=14, rz=-40, ry=10); R.krot(K + 8, 'head', rx=-16, rz=6, ry=-4); R.krot(K + 13, 'head', rx=-12, rz=1, ry=0); R.krot(K + 40, 'head', rx=-13, rz=2, ry=3)
for e, s in (('L', 1), ('R', -1)): R.krot(K, 'ear.' + e); R.krot(K + 8, 'ear.' + e, rx=10, ry=3 * s); R.krot(K + 14, 'ear.' + e, rx=-4); R.krot(K + 20, 'ear.' + e)
R.kblink(K + 22, 0); R.kblink(K + 27, 1); R.kblink(K + 33, 0)
for f in range(T_BAT_L + 30, T_LIE, 14):
    s = 1 if ((f - T_BAT_L) // 14) % 2 == 0 else -1; tail(f, lean=3, sway=9 * s, curl=5 * s, lag=2)

# ---- S8: lies back down into a loaf, tail wraps, eyes close
Z = T_LIE
R.kloc(Z, 'body', (0, Y2, 0)); R.kloc(Z + 8, 'body', (0, Y2, 0.03)); R.krot(Z + 8, 'body', rx=-2)                         # anticipation up
R.kloc(Z + 24, 'body', (0, Y2 + 0.03, LOAF_Z - 0.03)); R.krot(Z + 24, 'body', rx=2); R.kscale(Z + 16, 'body'); R.kscale(Z + 25, 'body', 1.05, 1.0, 0.93)
R.kloc(Z + 32, 'body', (0, Y2, LOAF_Z)); R.krot(Z + 32, 'body'); R.kscale(Z + 32, 'body')
R.krot(Z + 2, 'head', rx=-13, rz=2, ry=3); R.krot(Z + 20, 'head', rx=4, rz=6); R.krot(Z + 30, 'head', rx=-6, rz=12, ry=4); R.krot(Z + 50, 'head', rx=10, rz=8, ry=6); R.krot(END, 'head', rx=18, rz=8, ry=6)
tail(Z + 4, lean=3, lag=1); tail(Z + 26, lean=-60, curl=-14, lag=1); tail(Z + 44, lean=-78, curl=-27, lag=1)
R.kblink(T_SLEEP - 30, 0); R.kblink(T_SLEEP - 22, 0.5); R.kblink(T_SLEEP - 14, 0.3); R.kblink(T_SLEEP, 1)
for f in range(Z + 36, END + 1, 24): R.kscale(f, 'chest', 1, 1, 1); R.kscale(f + 12, 'chest', 1.035, 1.0, 1.045)

# ============================================================== lights: window sun (animated), sky, volume, practical
sun = bpy.data.lights.new('Sun', 'SUN'); sun.angle = rad(1.6); sun_o = bpy.data.objects.new('Sun', sun); SET.objects.link(sun_o)
def sun_at(f, elev, azim, strength, color):
    d = Vector((cos(rad(elev)) * cos(rad(azim)), cos(rad(elev)) * sin(rad(azim)), -sin(rad(elev))))      # travel direction
    sun_o.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler(); sun.energy = strength; sun.color = color
    sun_o.keyframe_insert('rotation_euler', frame=f); sun.keyframe_insert('energy', frame=f); sun.keyframe_insert('color', frame=f)
sun_at(0, 27, 16, 5.5, (1.0, 0.80, 0.58)); sun_at(300, 21, 14, 5.0, (1.0, 0.70, 0.45)); sun_at(END, 13, 11, 3.6, (1.0, 0.52, 0.28))
w = bpy.data.worlds.new('Sky'); sc.world = w; w.use_nodes = True; t = w.node_tree; bg = t.nodes['Background']
tcw = t.nodes.new('ShaderNodeTexCoord'); spw = t.nodes.new('ShaderNodeSeparateXYZ'); rmp = t.nodes.new('ShaderNodeValToRGB')
rmp.color_ramp.elements[0].position = 0.45; rmp.color_ramp.elements[0].color = (1.0, 0.62, 0.36, 1); rmp.color_ramp.elements[1].position = 0.9; rmp.color_ramp.elements[1].color = (0.30, 0.42, 0.72, 1)
mrw = t.nodes.new('ShaderNodeMapRange'); mrw.inputs['From Min'].default_value = -1; mrw.inputs['From Max'].default_value = 1
t.links.new(tcw.outputs['Generated'], spw.inputs[0]); t.links.new(spw.outputs['Z'], mrw.inputs['Value']); t.links.new(mrw.outputs['Result'], rmp.inputs['Fac']); t.links.new(rmp.outputs['Color'], bg.inputs['Color'])
bg.inputs['Strength'].default_value = 1.6; bg.inputs['Strength'].keyframe_insert('default_value', frame=0)
bg.inputs['Strength'].default_value = 0.9; bg.inputs['Strength'].keyframe_insert('default_value', frame=END)
ld.energy = 2.2; ld.keyframe_insert('energy', frame=0); ld.energy = 4.5; ld.keyframe_insert('energy', frame=END)
# soft room fill so shadows do not go to black (bounce stand-in), cool
fl_ = bpy.data.lights.new('RoomFill', 'AREA'); fl_.energy = 14; fl_.size = 2.0; fl_.color = (0.75, 0.82, 1.0)
fo = bpy.data.objects.new('RoomFill', fl_); SET.objects.link(fo); fo.location = (0.9, -2.0, 2.2); fo.rotation_euler = (Vector((0, 0, 0.8)) - Vector(fo.location)).to_track_quat('-Z', 'Y').to_euler()
# volume for the light shafts
vol = box('Haze', (RX1 - RX0 - 0.02, RY1 - RY0 - 0.02, RZ - 0.02), ((RX0 + RX1) / 2, (RY0 + RY1) / 2, RZ / 2), None, 0)
vm = bpy.data.materials.new('Haze'); vm.use_nodes = True; t = vm.node_tree; t.nodes.clear()
vs = t.nodes.new('ShaderNodeVolumeScatter'); vs.inputs['Density'].default_value = 0.045; vs.inputs['Anisotropy'].default_value = 0.55; vs.inputs['Color'].default_value = (1, 0.96, 0.9, 1)
vo = t.nodes.new('ShaderNodeOutputMaterial'); t.links.new(vs.outputs[0], vo.inputs['Volume']); vol.data.materials.append(vm); vol.display_type = 'WIRE'

# ============================================================== cameras: one per shot, eased dolly moves, DOF on the face / ball
hdir = Vector((sin(HEAD_DIR), -cos(HEAD_DIR), 0)); pdir = Vector((-hdir.y, hdir.x, 0))      # heading, and the room-front side of the path
if pdir.y > 0: pdir = -pdir
def catpos(y): return CS + hdir * (-y * 0.11)                                              # world position of the cat at body offset y
C0, C1, C2 = catpos(0), catpos(Y1), catpos(Y2)
HEADH = Vector((0, 0, 0.145))
def cam(name, lens, fstop, keys, focus_obj=None, focus_dist=None):
    """keys: [(frame, position, look_at)]; bezier-eased between keys"""
    c = bpy.data.cameras.new(name); c.lens = lens; c.sensor_width = 36; c.dof.use_dof = True; c.dof.aperture_fstop = fstop
    o = bpy.data.objects.new(name, c); sc.collection.objects.link(o)
    tgt = bpy.data.objects.new(name + '_aim', None); sc.collection.objects.link(tgt)
    tr = o.constraints.new('TRACK_TO'); tr.target = tgt; tr.track_axis = 'TRACK_NEGATIVE_Z'; tr.up_axis = 'UP_Y'
    for f, p, a in keys:
        o.location = p; tgt.location = a; o.keyframe_insert('location', frame=f); tgt.keyframe_insert('location', frame=f)
    if focus_obj: c.dof.focus_object = focus_obj
    else: c.dof.focus_object = tgt
    return o
CAMS = {
 'S1_wide': cam('S1_wide', 35, 4.0, [(0, Vector((0.10, -1.72, 1.22)), C0 + Vector((-0.42, 0, 0.16))), (60, Vector((0.14, -1.56, 1.17)), C0 + Vector((-0.40, 0, 0.14)))], focus),
 'S2_ear': cam('S2_ear', 85, 5.6, [(60, C0 + hdir * 0.64 + pdir * 0.30 + Vector((0, 0, 0.078)), C0 + hdir * 0.06 + Vector((0, 0, 0.108))), (90, C0 + hdir * 0.60 + pdir * 0.36 + Vector((0, 0, 0.084)), C0 + hdir * 0.06 + Vector((0, 0, 0.106)))], focus),
 'S3_wake': cam('S3_wake', 50, 2.8, [(90, C0 + hdir * 0.78 + pdir * 0.30 + Vector((0, 0, 0.15)), C0 + HEADH + Vector((0, 0, -0.03))), (156, C0 + hdir * 0.60 + pdir * 0.20 + Vector((0, 0, 0.19)), C0 + HEADH + Vector((0, 0, 0.0)))], focus),
 'S4_walk': cam('S4_walk', 40, 2.8, [(156, C0 + pdir * 0.78 + hdir * 0.22 + Vector((0, 0, 0.11)), C0 + Vector((0, 0, 0.12))), (246, C1 + pdir * 0.74 + hdir * 0.30 + Vector((0, 0, 0.10)), C1 + Vector((0, 0, 0.12)))], focus),
 'S5_paw': cam('S5_paw', 100, 8.0, [(246, C1 + hdir * 0.66 + pdir * 0.20 + Vector((0, 0, 0.038)), C1 + hdir * 0.115 + Vector((0, 0, 0.022))), (294, C1 + hdir * 0.62 + pdir * 0.16 + Vector((0, 0, 0.042)), C1 + hdir * 0.13 + Vector((0, 0, 0.022)))], ball),
 'S6_play': cam('S6_play', 35, 2.8, [(294, C2 + hdir * 0.62 + pdir * 0.30 + Vector((0, 0, 0.07)), C1 + Vector((0, 0, 0.11))), (340, C2 + hdir * 0.56 + pdir * 0.26 + Vector((0, 0, 0.08)), C2 + Vector((0, 0, 0.10))), (438, C2 + hdir * 0.50 + pdir * 0.34 + Vector((0, 0, 0.10)), C2 + Vector((0, 0, 0.11)))], focus),
 'S7_settle': cam('S7_settle', 50, 2.2, [(438, C2 + hdir * 0.74 + pdir * 0.34 + Vector((0, 0, 0.13)), C2 + hdir * 0.04 + Vector((0, 0, 0.12))), (534, C2 + hdir * 0.58 + pdir * 0.22 + Vector((0, 0, 0.15)), C2 + hdir * 0.05 + Vector((0, 0, 0.135)))], focus),
 'S8_hold': cam('S8_hold', 35, 4.0, [(534, Vector((0.62, -1.40, 1.20)), C2 + Vector((-0.30, 0.05, 0.14))), (END, Vector((0.72, -1.62, 1.30)), C2 + Vector((-0.30, 0.05, 0.16)))], focus)}
for i, (f, name, lens, fstop) in enumerate(SHOTS):
    mk = sc.timeline_markers.new(name, frame=f); mk.camera = CAMS[name]; CAMS[name].data.dof.aperture_fstop = fstop; CAMS[name].data.lens = lens
sc.camera = CAMS['S1_wide']

# ============================================================== render settings
sc.frame_start = 0; sc.frame_end = END - 1; sc.render.fps = FPS
sc.render.engine = 'CYCLES'; sc.cycles.samples = 192; sc.cycles.use_adaptive_sampling = True; sc.cycles.adaptive_threshold = 0.02
sc.cycles.use_denoising = True; sc.cycles.denoiser = 'OPENIMAGEDENOISE'
sc.view_settings.view_transform = 'AgX'; sc.view_settings.look = 'AgX - Medium High Contrast'; sc.view_settings.exposure = 0.0
sc.render.resolution_x, sc.render.resolution_y = 1920, 1080; sc.render.film_transparent = False
sc.render.use_motion_blur = True; sc.render.motion_blur_shutter = 0.5; sc.render.use_persistent_data = True
sc.cycles.max_bounces = 8; sc.cycles.volume_bounces = 0; sc.cycles.seed = 7
sc.render.image_settings.file_format = 'PNG'; sc.render.image_settings.color_depth = '8'
bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=OUT_BLEND)
json.dump({'fps': FPS, 'end': END, 'shots': SHOTS, 'beats': dict(wake=T_WAKE, stand=T_STAND, walk=(T_WALK0, T_WALK1), tap=T_TAP, crouch=T_CROUCH, pounce=T_POUNCE, land=T_LAND, bat_r=T_BAT_R, bat_l=T_BAT_L, look=T_LOOK, lie=T_LIE, sleep=T_SLEEP)},
          open(OUT_BLEND.replace('.blend', '_timeline.json'), 'w'), indent=1)
print('FILM_DONE walk_dist', WALK_DIST)
