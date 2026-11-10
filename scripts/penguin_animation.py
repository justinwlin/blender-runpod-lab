"""A five-second, deterministic penguin animation. No external assets required."""
import argparse
import json
import math
import random
import sys
import time
from pathlib import Path

import bpy
from mathutils import Vector

FPS = 24
FRAME_COUNT = 120


def mat(name, color, roughness=0.4, metallic=0):
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    shader = material.node_tree.nodes.get('Principled BSDF')
    shader.inputs['Base Color'].default_value = (*color, 1)
    shader.inputs['Roughness'].default_value = roughness
    shader.inputs['Metallic'].default_value = metallic
    return material


def ellipsoid(name, location, scale, material, parent=None, segments=40):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=segments, ring_count=24, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    obj.data.materials.append(material)
    for face in obj.data.polygons:
        face.use_smooth = True
    if parent:
        obj.parent = parent
    return obj


def cylinder(name, location, radius, depth, material):
    bpy.ops.mesh.primitive_cylinder_add(vertices=96, radius=radius, depth=depth, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.data.materials.append(material)
    bevel = obj.modifiers.new('Soft snowy edge', 'BEVEL')
    bevel.width = min(depth * 0.4, 0.14)
    bevel.segments = 4
    obj.modifiers.new('Weighted normals', 'WEIGHTED_NORMAL')
    return obj


def ring(name, center, major, minor, material):
    bpy.ops.mesh.primitive_torus_add(major_segments=64, minor_segments=12,
        location=center, major_radius=major, minor_radius=minor)
    obj = bpy.context.object
    obj.name = name
    obj.data.materials.append(material)
    for face in obj.data.polygons:
        face.use_smooth = True
    return obj


def aim(obj, point):
    obj.rotation_euler = (Vector(point) - obj.location).to_track_quat('-Z', 'Y').to_euler()


def light(name, position, energy, color, size):
    bpy.ops.object.light_add(type='AREA', location=position)
    obj = bpy.context.object
    obj.name = name
    obj.data.energy = energy
    obj.data.color = color
    obj.data.shape = 'DISK'
    obj.data.size = size
    aim(obj, (0, 0, 0))


def smooth(value):
    value = max(0.0, min(1.0, value))
    return value * value * (3 - 2 * value)


def key(obj, frame):
    for field in ('location', 'rotation_euler', 'scale'):
        obj.keyframe_insert(data_path=field, frame=frame)


def build_scene(out, preview):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    scene.cycles.samples = 20 if preview else 64
    scene.cycles.adaptive_threshold = 0.035 if preview else 0.025
    scene.cycles.use_denoising = True
    scene.cycles.denoiser = 'OPENIMAGEDENOISE'
    scene.cycles.seed = 11
    scene.cycles.max_bounces = 6
    scene.cycles.diffuse_bounces = 3
    scene.cycles.glossy_bounces = 3
    scene.render.resolution_x = 768 if preview else 1280
    scene.render.resolution_y = 576 if preview else 960
    scene.render.resolution_percentage = 100
    scene.render.fps = FPS
    scene.frame_start = 1
    scene.frame_end = FRAME_COUNT
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGB'
    scene.view_settings.view_transform = 'AgX'
    scene.world = bpy.data.worlds.new('Pastel arctic sky')
    scene.world.use_nodes = True
    scene.world.node_tree.nodes['Background'].inputs[0].default_value = (0.56, 0.76, 0.84, 1)
    scene.world.node_tree.nodes['Background'].inputs[1].default_value = 0.45
    snow = mat('Marshmallow snow', (0.86, 0.96, 1), 0.62)
    ice = mat('Blue ice edge', (0.18, 0.55, 0.73), 0.3)
    navy = mat('Velvet midnight feathers', (0.014, 0.035, 0.072), 0.37)
    white = mat('Warm fluffy belly', (0.95, 0.94, 0.86), 0.5)
    orange = mat('Mango beak and feet', (1, 0.32, 0.035), 0.35)
    black = mat('Glossy curious eyes', (0.004, 0.009, 0.016), 0.12)
    blush = mat('Peach cheeks', (1, 0.30, 0.25), 0.5)
    coral = mat('Coral scarf', (0.9, 0.08, 0.09), 0.5)
    water = mat('Turquoise water', (0.025, 0.40, 0.56), 0.23, 0.18)
    foam = mat('Pale aqua splash', (0.37, 0.83, 0.96), 0.19, 0.08)

    # Opaque water hides the character below the surface without a fluid simulation.
    bpy.ops.mesh.primitive_plane_add(size=200, location=(0, 0, -0.22))
    bpy.context.object.name = 'Calm turquoise sea'
    bpy.context.object.data.materials.append(water)
    cylinder('Thick blue ice floe', (-2.35, 0, -0.08), 2.55, 0.42, ice)
    cylinder('Soft snow cap', (-2.35, 0, 0.12), 2.57, 0.23, snow)

    # Snowball details and two distant floating ice pieces provide depth.
    for i, (x, y, s) in enumerate([(-3.5, 1.2, .3), (-2.9, 1.7, .2), (-4, -.3, .22), (-3.8, .6, .13)]):
        ellipsoid('Snow puff %d' % i, (x, y, .25), (s, s, s * .6), snow)
    cylinder('Far ice floe', (2.5, 4.2, -.10), 1.0, .26, snow)
    cylinder('Small far ice floe', (-3.5, 5.0, -.13), .75, .22, snow)
    for i, (x, y, s) in enumerate([(2.5, 4.2, .42), (-3.6, 5, .25)]):
        ellipsoid('Distant snow mound %d' % i, (x, y, .02), (s, s*.8, s*.7), snow)

    root = bpy.data.objects.new('Pip the penguin - animation root', None)
    scene.collection.objects.link(root)
    ellipsoid('Round penguin body', (0, 0, .82), (.49, .43, .67), navy, root)
    ellipsoid('Cream tummy', (.315, -.005, .79), (.235, .355, .50), white, root)
    ellipsoid('Round penguin head', (.025, 0, 1.40), (.43, .41, .43), navy, root)
    for side in (-1, 1):
        ellipsoid('Face patch %s' % side, (.335, side*.18, 1.40), (.145, .185, .255), white, root)
    eyes = []
    for side in (-1, 1):
        eye = ellipsoid('Eye %s' % side, (.465, side*.20, 1.48), (.065, .066, .09), black, root)
        eyes.append(eye)
        ellipsoid('Eye sparkle %s' % side, (.513, side*.20-.019, 1.512), (.019, .019, .024), snow, root, 24)
        ellipsoid('Rosy cheek %s' % side, (.416, side*.30, 1.345), (.035, .075, .043), blush, root, 24)
    beak = ellipsoid('Little mango beak', (.53, 0, 1.315), (.22, .14, .095), orange, root)
    feet = []
    wings = []
    for side in (-1, 1):
        foot = ellipsoid('Paddle foot %s' % side, (.16, side*.245, .075), (.29, .18, .075), orange, root)
        feet.append(foot)
        wing = ellipsoid('Flipper %s' % side, (-.035, side*.455, .84), (.14, .105, .43), navy, root)
        wing.rotation_euler.x = side * -.15
        wings.append(wing)
    scarf = ring('Red wool scarf', (0, 0, 1.16), .365, .075, coral)
    scarf.scale.x = 1.10
    scarf.parent = root
    tail = ellipsoid('Scarf tail', (.20, -.43, .91), (.10, .055, .26), coral, root)
    tail.rotation_euler.y = -.25

    rng = random.Random(23)
    drops = []
    splash_center = Vector((1.6, 0, -.19))
    for i in range(22):
        angle = 2 * math.pi * i / 22
        radius = rng.uniform(.45, 1.2)
        height = rng.uniform(.5, 1.4)
        size = rng.uniform(.045, .095)
        drop = ellipsoid('Splash drop %02d' % i, splash_center, (size, size, size*1.7), foam, segments=24)
        drops.append((drop, angle, radius, height, size))
    ripples = [ring('Splash ripple %d' % i, splash_center, 1, .018, foam) for i in range(3)]
    for i in range(3):
        ripple = ring('Idle sea ripple %d' % i, (2.8+i*.3, -2.6+i*.2, -.215), .32+i*.15, .008, foam)
        ripple.scale.y = .7

    # Each frame has explicit transforms, so frame jobs can run in any order.
    for frame in range(1, FRAME_COUNT + 1):
        t = (frame - 1) / FPS
        phase = 2 * math.pi * (t - .25) * 2.4
        walking = .25 <= t < 2.50
        progress = smooth((t - .25) / 2.25)
        root.location = (-2.45 + 2.30 * progress, 0, .24)
        root.rotation_euler = (0, 0, -.06)
        root.scale = (1, 1, 1)
        if walking:
            root.location.y = .065 * math.sin(phase)
            root.location.z += .045 * abs(math.sin(phase))
            root.rotation_euler.x = .11 * math.sin(phase)
            root.rotation_euler.z = -.06 + .065 * math.sin(phase)
        if 2.50 <= t < 3.05:
            q = smooth((t-2.50)/.55)
            root.location.x = -.15 + .43*q
            root.rotation_euler.y = .10 + .45*q + .08*math.sin((t-2.5)*32)
            root.scale.z = 1 - .10*math.sin(q*math.pi)
        elif 3.05 <= t < 3.65:
            q = (t-3.05)/.60
            root.location.x = .28 + 1.40*q
            root.location.z = .24 + .5*math.sin(q*math.pi) - 2.35*q*q
            root.rotation_euler.y = .55 + .9*math.sin(q*math.pi)
            root.rotation_euler.x = .10*math.sin(q*math.pi)
        elif 3.65 <= t < 4.10:
            root.location = (1.68, 0, -2.1)
        elif t >= 4.10:
            q = smooth((t-4.10)/.45)
            root.location = (1.68, 0, -2.1 + 1.05*q + .04*math.sin((t-4.1)*10)*q)
            root.rotation_euler = (0, -.08, -.28*q)
        key(root, frame)
        for i, side in enumerate((-1, 1)):
            foot = feet[i]
            foot.location = (.16, side*.245, .075)
            foot.rotation_euler = (0, 0, side*.14)
            if walking:
                lift = max(0, math.sin(phase + i*math.pi))
                foot.location.x += .12*math.cos(phase + i*math.pi)
                foot.location.z += .13*lift
                foot.rotation_euler.y = -.35*lift
            key(foot, frame)
            wing = wings[i]
            flap = .12*math.sin(phase + i*math.pi) if walking else .02
            if 2.50 <= t < 3.65:
                flap = .75 + .25*math.sin(t*35)
            if t >= 4.35:
                flap = .4 + .25*math.sin(t*15)
            wing.rotation_euler.x = -side*(.15 + flap)
            wing.rotation_euler.y = .12*math.sin(phase) if walking else 0
            key(wing, frame)
            eye = eyes[i]
            blink = abs(t-.15) < .04 or abs(t-1.8) < .04
            wink = i == 0 and 4.65 < t < 4.78
            eye.scale = (.065, .066, .012 if blink or wink else (.11 if 2.6<t<3.5 else .09))
            key(eye, frame)
        tail.rotation_euler.x = .14*math.sin(t*12)
        key(tail, frame)
        for drop, angle, radius, height, size in drops:
            q = (t-3.53)/.83
            visible = 0 < q < 1
            if visible:
                drop.location = splash_center + Vector((math.cos(angle)*radius*q, math.sin(angle)*radius*q, 4*height*q*(1-q)))
                shrink = min(1, q*8, (1-q)*6)
                drop.scale = (size*shrink, size*shrink, size*1.7*shrink)
            else:
                drop.scale = (.0001,)*3
            key(drop, frame)
        for i, ripple in enumerate(ripples):
            q = (t-3.53-i*.13)/1.5
            if 0 < q < 1:
                radius = .15 + q*1.7
                ripple.scale = (radius, radius, max(.03, 1-q))
            else:
                ripple.scale = (.0001,)*3
            key(ripple, frame)

    light('Warm softbox sun', (-3, -4, 8), 1250, (1, .87, .72), 5)
    light('Cool arctic rim', (3, 4, 6), 1550, (.60, .84, 1), 4)
    light('Face fill', (5, -6, 4), 350, (1, .96, .9), 4)
    bpy.ops.object.camera_add(location=(7.3, -11.5, 7.3))
    camera = bpy.context.object
    camera.name = 'Playful three-quarter camera'
    aim(camera, (-.7, 0, .50))
    camera.data.type = 'ORTHO'
    camera.data.ortho_scale = 8.0
    scene.camera = camera
    scene.render.film_transparent = False
    scene.render.filepath = str(out / 'frames' / 'frame_')
    scene.frame_set(1)
    return scene


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, default=Path('results/penguin'))
    parser.add_argument('--preview', action='store_true')
    parser.add_argument('--metal', action='store_true', help='Use the local Apple GPU')
    parser.add_argument('--cpu', action='store_true', help='Explicit full-quality local CPU render')
    parser.add_argument('--frames', default='')
    args = parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
    out = args.output.resolve()
    (out / 'frames').mkdir(parents=True, exist_ok=True)
    scene = build_scene(out, args.preview)
    devices = []
    if args.preview or args.cpu:
        scene.cycles.device = 'CPU'
    else:
        prefs = bpy.context.preferences.addons['cycles'].preferences
        backend = 'METAL' if args.metal else 'OPTIX'
        prefs.compute_device_type = backend
        prefs.refresh_devices()
        for device in prefs.devices:
            device.use = device.type == backend
            devices.append({'name':device.name, 'type':device.type, 'enabled':bool(device.use)})
        if not any(d['enabled'] for d in devices):
            raise RuntimeError('No requested GPU. Refuse CPU fallback.')
        scene.cycles.device = 'GPU'
    bpy.ops.wm.save_as_mainfile(filepath=str(out / 'penguin.blend'))
    frames = [int(f) for f in args.frames.split(',')] if args.frames else list(range(1, FRAME_COUNT+1))
    started = time.monotonic()
    timings = []
    for frame in frames:
        scene.frame_set(frame)
        scene.render.filepath = str(out / 'frames' / ('frame_%04d.png' % frame))
        start = time.monotonic()
        bpy.ops.render.render(write_still=True)
        timings.append({'frame':frame,'seconds':round(time.monotonic()-start,3)})
        print('FRAME_COMPLETE '+json.dumps(timings[-1]), flush=True)
    record = {'blender':bpy.app.version_string,'preview':args.preview,'backend':'CPU' if args.preview or args.cpu else ('METAL' if args.metal else 'OPTIX'),
        'devices':devices,'resolution':[scene.render.resolution_x,scene.render.resolution_y],
        'fps':FPS,'frames':frames,'render_seconds':round(time.monotonic()-started,3),'frame_timings':timings}
    (out/'render-metadata.json').write_text(json.dumps(record,indent=2)+'\n')
    print('ANIMATION_COMPLETE '+json.dumps(record),flush=True)


if __name__ == '__main__':
    main()
