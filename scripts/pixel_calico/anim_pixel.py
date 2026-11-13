"""Animate + render Pixel. blender -b out/pixel-rigged.blend -P scripts/anim_pixel.py -- <clip> <gate|full> <out_dir>
clips: walk (24f loop), ball (72f loop), idle (96f loop). 24 fps. Poses are procedural functions of the frame,
baked to keyframes on every frame, so every clip loops exactly."""
import bpy, sys, math, numpy as np
from mathutils import Matrix, Vector, Euler
clip, mode, OUT = sys.argv[sys.argv.index('--') + 1:][:3]
sc = bpy.context.scene; rig = bpy.data.objects['PixelRig']; cat = bpy.data.objects['Pixel']
X0 = -0.14; TAU = 2 * math.pi
LENGTH = {'walk': 24, 'ball': 72, 'idle': 96}[clip]
sin, cos = math.sin, math.cos

# ---------- pose helpers: rotations/offsets are given in armature (world) axes, converted to bone-local
REST = {b.name: b.matrix_local.to_3x3() for b in rig.data.bones}
for pb in rig.pose.bones: pb.rotation_mode = 'QUATERNION'
def rot(name, rx=0, ry=0, rz=0):
    """degrees. +rx = nod forward (cat faces -Y), +ry = lean to the cat's left (+X), +rz = turn to the cat's left"""
    R = Euler((math.radians(rx), math.radians(ry), math.radians(rz)), 'XYZ').to_matrix()
    B = REST[name]; rig.pose.bones[name].rotation_quaternion = (B.inverted() @ R @ B).to_quaternion()
def loc(name, d): rig.pose.bones[name].location = REST[name].inverted() @ Vector(d)
def scl(name, along, across): rig.pose.bones[name].scale = (across, along, across)   # bone Y is its length axis
def pulse(f, f0, width):       # smooth cyclic bump centred on f0
    d = (f - f0 + LENGTH / 2) % LENGTH - LENGTH / 2; return math.exp(-(d / width) ** 2)
def swing(f, f0, width):       # antisymmetric cyclic pulse: -1 just before f0, +1 just after
    d = (f - f0 + LENGTH / 2) % LENGTH - LENGTH / 2; x = d / width; return x * math.exp(0.5 - x * x / 2)

# ---------- stage for animation: opaque floor with dots, no transparent film
sc.render.film_transparent = False
fl = bpy.data.objects['Floor']; fl.is_shadow_catcher = False; fl.scale = (40, 40, 1)   # horizon out of frame
fm = bpy.data.materials.new('FloorDots'); fm.use_nodes = True; nt = fm.node_tree; bs = nt.nodes['Principled BSDF']
tc = nt.nodes.new('ShaderNodeTexCoord'); mp = nt.nodes.new('ShaderNodeMapping')
DOT = 0.6; FS = 40; mp.inputs['Scale'].default_value = (FS / DOT, FS / DOT, 1)   # object coords shrink with the floor scale
fr = nt.nodes.new('ShaderNodeVectorMath'); fr.operation = 'FRACTION'
sb = nt.nodes.new('ShaderNodeVectorMath'); sb.operation = 'SUBTRACT'; sb.inputs[1].default_value = (0.5, 0.5, 0)
ml = nt.nodes.new('ShaderNodeVectorMath'); ml.operation = 'MULTIPLY'; ml.inputs[1].default_value = (1, 1, 0)
ln = nt.nodes.new('ShaderNodeVectorMath'); ln.operation = 'LENGTH'
lt = nt.nodes.new('ShaderNodeMath'); lt.operation = 'LESS_THAN'; lt.inputs[1].default_value = 0.13
mx = nt.nodes.new('ShaderNodeMix'); mx.data_type = 'RGBA'
mx.inputs['A'].default_value = (0.72, 0.82, 0.93, 1); mx.inputs['B'].default_value = (0.60, 0.73, 0.89, 1)
nt.links.new(tc.outputs['Object'], mp.inputs['Vector']); nt.links.new(mp.outputs['Vector'], fr.inputs[0])
nt.links.new(fr.outputs['Vector'], sb.inputs[0]); nt.links.new(sb.outputs['Vector'], ml.inputs[0])
nt.links.new(ml.outputs['Vector'], ln.inputs[0]); nt.links.new(ln.outputs['Value'], lt.inputs[0])
nt.links.new(lt.outputs['Value'], mx.inputs['Factor']); nt.links.new(mx.outputs['Result'], bs.inputs['Base Color'])
bs.inputs['Roughness'].default_value = 0.9
fl.data.materials.clear(); fl.data.materials.append(fm)
bg = sc.world.node_tree.nodes['Background']; bg.inputs[0].default_value = (0.9, 0.94, 1, 1); bg.inputs[1].default_value = 0.7

# ---------- blink: black lid sweeps down over the eye disc, driven by one animated value in the material
nt = bpy.data.materials['PixelFlat'].node_tree; bsdf = nt.nodes['Principled BSDF']
ev = nt.nodes.new('ShaderNodeAttribute'); ev.attribute_name = 'EyeV'
egn = [x for x in nt.nodes if x.type == 'ATTRIBUTE' and x.attribute_name == 'EyeGloss'][0]
col = [x for x in nt.nodes if x.type == 'ATTRIBUTE' and x.attribute_name == 'PixelColor'][0]
gt = nt.nodes.new('ShaderNodeMath'); gt.operation = 'GREATER_THAN'; gt.name = 'BlinkThreshold'; gt.inputs[1].default_value = 1.0
mu = nt.nodes.new('ShaderNodeMath'); mu.operation = 'MULTIPLY'
lid = nt.nodes.new('ShaderNodeMix'); lid.data_type = 'RGBA'; lid.inputs['B'].default_value = (0.0116, 0.0109, 0.0109, 1)
nt.links.new(ev.outputs['Fac'], gt.inputs[0]); nt.links.new(gt.outputs['Value'], mu.inputs[0]); nt.links.new(egn.outputs['Fac'], mu.inputs[1])
nt.links.new(mu.outputs['Value'], lid.inputs['Factor']); nt.links.new(col.outputs['Color'], lid.inputs['A'])
nt.links.new(lid.outputs['Result'], bsdf.inputs['Base Color'])
mr = [x for x in nt.nodes if x.type == 'MAP_RANGE'][0]
sub = nt.nodes.new('ShaderNodeMath'); sub.operation = 'SUBTRACT'
nt.links.new(egn.outputs['Fac'], sub.inputs[0]); nt.links.new(mu.outputs['Value'], sub.inputs[1]); nt.links.new(sub.outputs['Value'], mr.inputs['Value'])
def blink(amount): gt.inputs[1].default_value = 1.0 - 1.05 * amount   # 0 open, 1 closed

# ---------- follow rig (camera + lights travel with the cat in the walk)
follow = bpy.data.objects.new('Follow', None); sc.collection.objects.link(follow)
bpy.data.objects['LightRig'].parent = follow; bpy.data.objects['LightRig'].rotation_euler = (0, 0, 0)
def camera(az, el, dist, look, lens=60):
    c = bpy.data.cameras.new('AnimCam'); c.lens = lens; o = bpy.data.objects.new('AnimCam', c); sc.collection.objects.link(o)
    a, e = math.radians(az), math.radians(el); d = Vector((sin(a) * cos(e), -cos(a) * cos(e), sin(e)))
    o.location = Vector(look) + d * dist; o.rotation_euler = (-d).to_track_quat('-Z', 'Y').to_euler(); o.parent = follow; sc.camera = o

# ---------- ball
ball = None; BR = 0.17
def make_ball():
    global ball
    bpy.ops.mesh.primitive_uv_sphere_add(radius=BR, segments=48, ring_count=24); ball = bpy.context.object; ball.name = 'Ball'
    for p in ball.data.polygons: p.use_smooth = True
    m = bpy.data.materials.new('Ball'); m.use_nodes = True; t = m.node_tree; b = t.nodes['Principled BSDF']
    tc = t.nodes.new('ShaderNodeTexCoord'); sp = t.nodes.new('ShaderNodeSeparateXYZ'); ab = t.nodes.new('ShaderNodeMath'); ab.operation = 'ABSOLUTE'
    l2 = t.nodes.new('ShaderNodeMath'); l2.operation = 'LESS_THAN'; l2.inputs[1].default_value = BR * 0.35
    mx = t.nodes.new('ShaderNodeMix'); mx.data_type = 'RGBA'
    mx.inputs['A'].default_value = (0.05, 0.42, 0.62, 1); mx.inputs['B'].default_value = (0.85, 0.85, 0.85, 1)
    t.links.new(tc.outputs['Object'], sp.inputs[0]); t.links.new(sp.outputs['Z'], ab.inputs[0]); t.links.new(ab.outputs['Value'], l2.inputs[0])
    t.links.new(l2.outputs['Value'], mx.inputs['Factor']); t.links.new(mx.outputs['Result'], b.inputs['Base Color']); b.inputs['Roughness'].default_value = 0.45
    ball.data.materials.append(m); ball.rotation_mode = 'XYZ'

# ---------- the clips
def tail_sway(f, period, amp, lift=0.0):
    """free tail (v2): a travelling wave down the chain, biased outward so it never swings into the body"""
    for i in range(1, 7):
        ph = TAU * f / period - 0.6 * (i - 1); k = 0.35 + 0.13 * i
        rot(f'tail{i}', rz=amp * k * (0.45 + 0.55 * sin(ph)), rx=-lift if i == 3 else 0)

def walk(f):
    p = f / LENGTH; s, c, s2, c2 = sin(TAU * p), cos(TAU * p), sin(2 * TAU * p), cos(2 * TAU * p)
    D = 0.6
    follow.location = (0, -D * p, 0)
    loc('root', (0, -D * p, 0.035 * (1 - c2) / 2)); rot('root', ry=5.5 * s, rz=4.5 * c, rx=3)
    scl('root', 1 - 0.025 * c2, 1 + 0.012 * c2)
    rot('spine', ry=-2.5 * s); rot('chest', ry=-2.5 * s, rz=-3 * c)
    rot('head', ry=-3.5 * s, rz=-3 * c, rx=2.5 * c2 - 2)
    for nm, sg in (('R', 1), ('L', -1)):
        rot(f'arm.{nm}', rx=-26 * s * sg); rot(f'paw.{nm}', rx=22 * max(0, c * sg) - 6)
        rot(f'foot.{nm}', rx=9 * s * sg); loc(f'foot.{nm}', (0, 0, 0.03 * max(0, -c * sg)))
        rot(f'ear.{nm}', rx=5 * cos(2 * TAU * p + 0.7), ry=2 * sg * s2)
    tail_sway(f, LENGTH, 6, lift=3)
    blink(0)

HIT_R, HIT_L = 0, 36
PA, PB = Vector((X0 - 0.40, -0.98, 0.42)), Vector((X0 + 0.42, -0.98, 0.42))   # where the right / left paw meets the ball
def ball_pos(f):
    f = f % LENGTH
    a, b, u = (PA, PB, f / 36) if f < 36 else (PB, PA, (f - 36) / 36)
    p = a.lerp(b, u); k = 1 - abs(2 * u - 1)
    p.z = BR + (a.z - BR) * (1 - k * k); p.y -= 0.10 * math.sin(math.pi * u)
    return p
def ballplay(f):
    bp = ball_pos(f); ball.location = bp
    u = (f % 36) / 36; x_tr = (PB.x - PA.x) * (u if f % LENGTH < 36 else 1 - u)
    ball.rotation_euler = (0.6, x_tr / BR, 0.3)
    side = (bp.x - X0) / 0.42                       # -1 ball at right paw, +1 at left paw
    aR, aL = pulse(f, HIT_R, 6.5), pulse(f, HIT_L, 6.5); hop = aR + aL
    loc('root', (0.03 * side, 0, 0.05 * hop)); rot('root', ry=5 * side, rx=4 + 3 * hop)
    scl('root', 1 + 0.03 * hop - 0.015, 1 - 0.012 * hop)
    rot('spine', ry=2 * side, rx=3); rot('chest', rz=6 * side, rx=4)
    yaw = math.degrees(math.atan2(bp.x - X0, -(bp.y + 0.2))) * 0.75; pitch = 16 - 22 * (bp.z - BR)
    rot('head', rz=yaw - 6 * side, rx=pitch, ry=4 * side)
    rot('arm.R', rx=-64 * aR, rz=22 * swing(f, HIT_R, 4.5) * aR ** 0.3, ry=-8 * aR); rot('paw.R', rx=-10 * aR)
    rot('arm.L', rx=-64 * aL, rz=-22 * swing(f, HIT_L, 4.5) * aL ** 0.3, ry=8 * aL); rot('paw.L', rx=-10 * aL)
    rot('foot.R', rx=0); rot('foot.L', rx=0)
    for nm, sg in (('R', 1), ('L', -1)): rot(f'ear.{nm}', rx=-6 * hop + 3 * sin(TAU * f / 36), ry=3 * sg * hop)
    tail_sway(f, 36, 9, lift=6)
    blink(pulse(f, 20, 2.2))

def idle(f):
    br = sin(TAU * f / 48)
    loc('root', (0, 0, 0)); rot('root')
    scl('spine', 1 + 0.018 * br, 1 + 0.022 * br); scl('chest', 1 + 0.012 * br, 1 + 0.015 * br)
    rot('chest', rx=-1.2 * br)
    rot('head', ry=4 * sin(TAU * f / 96), rz=7 * sin(TAU * f / 96 + 1.0), rx=-1.5 * br + 2)
    rot('ear.R', rz=-14 * pulse(f, 30, 2.5), rx=6 * pulse(f, 30, 2.5)); rot('ear.L', rz=14 * pulse(f, 70, 2.5), rx=6 * pulse(f, 73, 2.5))
    for nm in ('arm.R', 'arm.L', 'paw.R', 'paw.L', 'foot.R', 'foot.L'): rot(nm)
    tail_sway(f, 48, 8, lift=7)
    blink(max(pulse(f, 20, 2.2), pulse(f, 60, 2.2), pulse(f, 65.5, 2.2)))

fn = {'walk': walk, 'ball': ballplay, 'idle': idle}[clip]
if clip == 'ball': make_ball(); camera(-20, 14, 7.9, (X0 + 0.02, -0.38, 0.84))
elif clip == 'walk': camera(-38, 13, 7.7, (X0, -0.05, 1.02))
else: camera(-24, 13, 7.3, (X0, 0.0, 1.02))

sc.render.fps = 24; sc.frame_start = 0; sc.frame_end = LENGTH - 1
for f in range(0, LENGTH + 1):
    fn(f)
    for pb in rig.pose.bones:
        pb.keyframe_insert('rotation_quaternion', frame=f); pb.keyframe_insert('location', frame=f); pb.keyframe_insert('scale', frame=f)
    follow.keyframe_insert('location', frame=f); gt.inputs[1].keyframe_insert('default_value', frame=f)
    if ball: ball.keyframe_insert('location', frame=f); ball.keyframe_insert('rotation_euler', frame=f)

# ---------- render (Cycles on the GPU when there is one)
sc.render.engine = 'CYCLES'
prefs = bpy.context.preferences.addons['cycles'].preferences
dev = 'CPU'
for t in ('OPTIX', 'CUDA'):
    try:
        prefs.compute_device_type = t; prefs.refresh_devices()
        gpus = [d for d in prefs.devices if d.type == t]
        if gpus:
            for d in prefs.devices: d.use = d.type == t
            dev = 'GPU'; print('render device', t, [d.name for d in gpus], flush=True); break
    except Exception as e: print('no', t, e)
sc.cycles.device = dev; sc.cycles.use_denoising = True; sc.render.use_persistent_data = True
sc.render.image_settings.file_format = 'PNG'
if mode == 'gate':
    sc.cycles.samples = 24; sc.render.resolution_x, sc.render.resolution_y = 960, 540
    frames = [round(i * LENGTH / 8) for i in range(8)]
else:
    sc.cycles.samples = 64; sc.render.resolution_x, sc.render.resolution_y = 960, 540
    frames = list(range(LENGTH)); bpy.ops.wm.save_as_mainfile(filepath=f'{OUT}/{clip}.blend')
import time; t0 = time.time()
for f in frames:
    sc.frame_set(f); sc.render.filepath = f'{OUT}/{clip}_{mode}/{f:04d}.png'; bpy.ops.render.render(write_still=True)
print(f'RENDERED {clip} {mode} frames={len(frames)} secs={time.time() - t0:.1f} per_frame={(time.time() - t0) / len(frames):.2f}', flush=True)
