"""Run with Blender: blender -b --python scripts/render_demo.py -- --output results"""
import argparse
import json
import math
import subprocess
import sys
import time
from pathlib import Path

import bpy
from mathutils import Vector


def material(name, color, metallic=0.0, roughness=0.4):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    shader = mat.node_tree.nodes.get('Principled BSDF')
    shader.inputs['Base Color'].default_value = (*color, 1)
    shader.inputs['Metallic'].default_value = metallic
    shader.inputs['Roughness'].default_value = roughness
    return mat


def aim(obj, point):
    obj.rotation_euler = (Vector(point) - obj.location).to_track_quat('-Z', 'Y').to_euler()


def area(name, position, target, energy, color, size):
    bpy.ops.object.light_add(type='AREA', location=position)
    light = bpy.context.object
    light.name = name
    light.data.energy = energy
    light.data.color = color
    light.data.shape = 'DISK'
    light.data.size = size
    aim(light, target)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, default=Path('results'))
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else [])
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    preferences = bpy.context.preferences.addons['cycles'].preferences
    preferences.compute_device_type = 'OPTIX'
    preferences.refresh_devices()
    devices = []
    for device in preferences.devices:
        device.use = device.type == 'OPTIX'
        devices.append({'name': device.name, 'type': device.type, 'enabled': bool(device.use)})
    if not any(d['enabled'] for d in devices):
        raise RuntimeError('No OptiX GPU found. Refuse a silent CPU fallback.')
    scene.cycles.device = 'GPU'
    scene.cycles.samples = 128
    scene.cycles.adaptive_threshold = 0.01
    scene.cycles.use_denoising = True
    scene.cycles.denoiser = 'OPENIMAGEDENOISE'
    scene.cycles.seed = 42
    scene.render.resolution_x = 1600
    scene.render.resolution_y = 1000
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGB'
    scene.view_settings.view_transform = 'AgX'
    scene.world = bpy.data.worlds.new('Studio world')
    scene.world.use_nodes = True
    scene.world.node_tree.nodes['Background'].inputs[0].default_value = (0.11, 0.15, 0.20, 1)
    scene.world.node_tree.nodes['Background'].inputs[1].default_value = 0.25

    floor = material('Warm sand', (0.48, 0.42, 0.33), roughness=0.56)
    stone = material('Porcelain', (0.76, 0.79, 0.77), roughness=0.3)
    orange = material('Tangerine satin', (0.80, 0.13, 0.025), metallic=0.3, roughness=0.23)
    teal = material('Deep teal metal', (0.018, 0.24, 0.26), metallic=0.72, roughness=0.22)
    gold = material('Champagne metal', (0.60, 0.40, 0.16), metallic=0.85, roughness=0.19)
    bpy.ops.mesh.primitive_plane_add(size=200)
    bpy.context.object.data.materials.append(floor)

    bpy.ops.mesh.primitive_cylinder_add(vertices=128, radius=2.3, depth=0.32, location=(0, 0, 0.16))
    plinth = bpy.context.object
    plinth.name = 'Porcelain display plinth'
    plinth.data.materials.append(stone)
    bevel = plinth.modifiers.new('Soft edge', 'BEVEL')
    bevel.width = 0.08
    bevel.segments = 4
    plinth.modifiers.new('Weighted normals', 'WEIGHTED_NORMAL')

    bpy.ops.mesh.primitive_torus_add(major_radius=0.87, minor_radius=0.26,
        major_segments=96, minor_segments=40, location=(-0.6, 0.3, 1.45),
        rotation=(math.radians(75), math.radians(-12), math.radians(-18)))
    ring = bpy.context.object
    ring.name = 'Tangerine orbit'
    ring.data.materials.append(orange)
    for polygon in ring.data.polygons:
        polygon.use_smooth = True

    bpy.ops.mesh.primitive_uv_sphere_add(segments=96, ring_count=64, radius=0.63, location=(0.95, 0.18, 0.95))
    sphere = bpy.context.object
    sphere.name = 'Teal sphere'
    sphere.data.materials.append(teal)
    for polygon in sphere.data.polygons:
        polygon.use_smooth = True

    bpy.ops.mesh.primitive_cube_add(size=0.85, location=(-0.45, -0.86, 0.8), rotation=(0, 0, math.radians(-18)))
    cube = bpy.context.object
    cube.name = 'Gold rounded cube'
    cube.data.materials.append(gold)
    bevel = cube.modifiers.new('Rounded corners', 'BEVEL')
    bevel.width = 0.13
    bevel.segments = 6
    cube.modifiers.new('Weighted normals', 'WEIGHTED_NORMAL')

    area('Large warm key', (-3.5, -4, 6.5), (0, 0, 0.7), 950, (1, 0.81, 0.63), 4.0)
    area('Cool rim', (3, 2.5, 4.7), (0, 0, 1.0), 1200, (0.6, 0.83, 1), 3.0)
    area('Soft front fill', (1, -4, 3), (0, 0, 1), 180, (1, 0.94, 0.85), 3.5)
    bpy.ops.object.camera_add(location=(5.8, -8.5, 5.8))
    camera = bpy.context.object
    aim(camera, (0, 0, 1.0))
    camera.data.type = 'ORTHO'
    camera.data.ortho_scale = 6.8
    scene.camera = camera
    scene.render.filepath = str(out / 'first-light.png')
    bpy.ops.wm.save_as_mainfile(filepath=str(out / 'first-light.blend'))
    started = time.monotonic()
    bpy.ops.render.render(write_still=True)
    elapsed = time.monotonic() - started
    gpu_info = subprocess.check_output(['nvidia-smi', '--query-gpu=name,driver_version,memory.total', '--format=csv,noheader'], text=True).strip()
    metadata = {'blender_version': bpy.app.version_string, 'engine': 'CYCLES',
        'backend': 'OPTIX', 'devices': devices, 'nvidia_smi': gpu_info,
        'resolution': [1600, 1000], 'max_samples': 128, 'adaptive_threshold': 0.01,
        'render_seconds': round(elapsed, 3), 'image': 'first-light.png', 'scene': 'first-light.blend'}
    (out / 'render-metadata.json').write_text(json.dumps(metadata, indent=2) + '\n')
    print('RENDER_COMPLETE ' + json.dumps(metadata), flush=True)


if __name__ == '__main__':
    main()
