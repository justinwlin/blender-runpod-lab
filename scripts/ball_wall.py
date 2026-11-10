"""Five-second wall impact test. Runpod OptiX only; no CPU fallback."""
import bpy, math, json, time, argparse, sys
from pathlib import Path
from mathutils import Vector
p=argparse.ArgumentParser(); p.add_argument('--output',type=Path,default=Path('results/ball'));p.add_argument('--frames',default='')
a=p.parse_args(sys.argv[sys.argv.index('--')+1:]); out=a.output.resolve();(out/'frames').mkdir(parents=True,exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
s=bpy.context.scene;s.render.engine='CYCLES';s.cycles.samples=48;s.cycles.use_denoising=True;s.cycles.adaptive_threshold=.03
prefs=bpy.context.preferences.addons['cycles'].preferences;prefs.compute_device_type='OPTIX';prefs.refresh_devices()
devices=[]
for d in prefs.devices:
 d.use=d.type=='OPTIX';devices.append(dict(name=d.name,type=d.type,enabled=bool(d.use)))
assert any(d['enabled'] for d in devices),'An OptiX GPU is required'
s.cycles.device='GPU';s.render.resolution_x=1280;s.render.resolution_y=720;s.render.resolution_percentage=100;s.render.fps=24;s.frame_start=1;s.frame_end=120
s.render.image_settings.file_format='PNG';s.render.image_settings.color_mode='RGB';s.view_settings.view_transform='AgX'
s.world=bpy.data.worlds.new('Studio world');s.world.color=(.22,.22,.22)
def mat(name,color,rough=.35):
 m=bpy.data.materials.new(name);m.diffuse_color=(*color,1);m.use_nodes=True;n=m.node_tree.nodes['Principled BSDF'];n.inputs['Base Color'].default_value=(*color,1);n.inputs['Roughness'].default_value=rough;return m
floor=mat('Warm cream floor',(.68,.61,.48),.55);wall=mat('Teal wall',(.035,.30,.34));orange=mat('Tangerine rubber',(.95,.12,.025),.27);white=mat('Cream stripe',(.98,.88,.61));dark=mat('Dark floor marks',(.10,.15,.17))
def cube(name,loc,scale,m,bevel=.08):
 bpy.ops.mesh.primitive_cube_add(size=1,location=loc);o=bpy.context.object;o.name=name;o.scale=scale;bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);o.data.materials.append(m)
 if bevel: mod=o.modifiers.new('Soft edges','BEVEL');mod.width=bevel;mod.segments=4;o.modifiers.new('Normals','WEIGHTED_NORMAL')
 return o
cube('Studio floor',(0,0,-.15),(200,200,.3),floor)
cube('Impact wall',(2.65,0,1.8),(.3,4.4,3.6),wall)
for i in range(7): cube('Distance marker',(-3+i*.8,-1.25,.006),(.025,.25,.012),dark,.003)
bpy.ops.object.empty_add();root=bpy.context.object;root.name='Ball squash and travel'
bpy.ops.mesh.primitive_uv_sphere_add(segments=64,ring_count=32,radius=.5);ball=bpy.context.object;ball.name='Orange ball';ball.data.materials.append(orange);ball.parent=root
for f in ball.data.polygons:f.use_smooth=True
for rotation in [(0,0,0),(math.pi/2,0,0)]:
 bpy.ops.mesh.primitive_torus_add(major_radius=.498,minor_radius=.018,major_segments=64,minor_segments=12,rotation=rotation);o=bpy.context.object;o.parent=root;o.data.materials.append(white)
# Analytical contact at t=1.75: wall face x=2.5, sphere center x=2.0.
# Squash preserves contact and approximate volume. Floor arcs decay after impact.
records=[]
for frame in range(1,121):
 t=(frame-1)/24;impact=1.75
 x=-3+5*t/impact if t<=impact else 2-1.52*(t-impact)
 squash=.26*math.exp(-((t-impact)/.065)**2)
 sx=1-squash;sy=1/math.sqrt(sx);sz=sy
 if abs(t-impact)<.2:x+=.5*squash
 height=1.15*abs(math.sin(math.pi*t/.875)) if t<=impact else .9*math.exp(-.6*(t-impact))*abs(math.sin(math.pi*(t-impact)/.85))
 root.location=(x,0,.5*sz+height);root.scale=(sx,sy,sz)
 ball.rotation_euler.y=t*3
 for prop in ['location','scale']:root.keyframe_insert(data_path=prop,frame=frame)
 ball.keyframe_insert(data_path='rotation_euler',frame=frame)
 records.append(dict(frame=frame,x=x,z=root.location.z,wall_clearance=2.5-(x+.5*sx),floor_clearance=root.location.z-.5*sz))
assert min(r['wall_clearance'] for r in records)>-1e-6
assert min(r['floor_clearance'] for r in records)>-1e-6
for name,loc,power,size in [('Key',(-3,-4,7),1400,5),('Rim',(1,3,6),1100,4),('Fill',(-4,2,3),500,4)]:
 bpy.ops.object.light_add(type='AREA',location=loc);o=bpy.context.object;o.name=name;o.data.energy=power;o.data.shape='DISK';o.data.size=size;o.rotation_euler=(Vector((0,0,1))-o.location).to_track_quat('-Z','Y').to_euler()
bpy.ops.object.camera_add(location=(-7,-12,6));cam=bpy.context.object;cam.rotation_euler=(Vector((-.2,0,1))-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO';cam.data.ortho_scale=9.5;s.camera=cam
s.frame_set(1);bpy.ops.wm.save_as_mainfile(filepath=str(out/'ball-wall.blend'))
frames=[int(f) for f in a.frames.split(',')] if a.frames else list(range(1,121));start=time.monotonic();timings=[]
for f in frames:
 s.frame_set(f);s.render.filepath=str(out/'frames'/f'frame_{f:04d}.png');t=time.monotonic();bpy.ops.render.render(write_still=True);timings.append(dict(frame=f,seconds=round(time.monotonic()-t,3)));print('FRAME_COMPLETE '+json.dumps(timings[-1]),flush=True)
meta=dict(blender=bpy.app.version_string,backend='OPTIX',devices=devices,resolution=[1280,720],fps=24,frames=frames,render_seconds=round(time.monotonic()-start,3),frame_timings=timings,collision_test={'minimum_wall_clearance':min(r['wall_clearance'] for r in records),'minimum_floor_clearance':min(r['floor_clearance'] for r in records)},animation='Analytical keyed motion, not a rigid-body simulation')
(out/'render-metadata.json').write_text(json.dumps(meta,indent=2));print('COMPLETE',flush=True)
