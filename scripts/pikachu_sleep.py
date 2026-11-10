"""Reference-inspired sleeping Pikachu. All renders require a remote OptiX GPU."""
import bpy, math, json, time, argparse, sys
from pathlib import Path
from mathutils import Vector
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,default=Path('results/pikachu'));p.add_argument('--frames',default='');a=p.parse_args(sys.argv[sys.argv.index('--')+1:]);out=a.output.resolve();(out/'frames').mkdir(parents=True,exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True);s=bpy.context.scene;s.render.engine='CYCLES';s.cycles.samples=48;s.cycles.use_denoising=True;s.cycles.adaptive_threshold=.035;s.render.use_persistent_data=True
prefs=bpy.context.preferences.addons['cycles'].preferences;prefs.compute_device_type='OPTIX';prefs.refresh_devices();devices=[]
for d in prefs.devices:d.use=d.type=='OPTIX';devices.append(dict(name=d.name,type=d.type,enabled=bool(d.use)))
assert any(d['enabled'] for d in devices),'OptiX GPU required';s.cycles.device='GPU';s.render.resolution_x=1200;s.render.resolution_y=1200;s.render.resolution_percentage=100;s.render.fps=24;s.frame_start=1;s.frame_end=120;s.render.image_settings.file_format='PNG';s.render.image_settings.color_mode='RGB';s.view_settings.view_transform='AgX';s.view_settings.look='AgX - Medium High Contrast';s.view_settings.exposure=-.15
s.world=bpy.data.worlds.new('Cream studio');s.world.use_nodes=True;s.world.node_tree.nodes['Background'].inputs[0].default_value=(.82,.88,1,1);s.world.node_tree.nodes['Background'].inputs[1].default_value=.4

def mat(n,c,rough=.38,metal=0):
 m=bpy.data.materials.new(n);m.diffuse_color=(*c,1);m.use_nodes=True;b=m.node_tree.nodes['Principled BSDF'];b.inputs['Base Color'].default_value=(*c,1);b.inputs['Roughness'].default_value=rough;b.inputs['Metallic'].default_value=metal;return m
yellow=mat('Pikachu golden yellow',(1,.52,.001));black=mat('Soft ink',(.012,.025,.041));red=mat('Vermilion ball',(0.84,.035,.018),.24);white=mat('Porcelain white',(.94,.96,1),.24);cheek=mat('Rosy cheeks',(.98,.09,.045));brown=mat('Warm tail base',(.35,.13,.035));blue=mat('Sleep bubble',(.14,.65,.95),.19,.15);floor=mat('Warm white backdrop',(.9,.87,.80),.65)

def empty(n,loc=(0,0,0),parent=None):
 bpy.ops.object.empty_add(location=loc);o=bpy.context.object;o.name=n;o.parent=parent;return o

def uv(n,loc,scale,m,parent=None):
 bpy.ops.mesh.primitive_uv_sphere_add(segments=48,ring_count=24,location=loc);o=bpy.context.object;o.name=n;o.scale=scale;o.data.materials.append(m);o.parent=parent
 for f in o.data.polygons:f.use_smooth=True
 return o

def curve(n,points,r,m,parent=None):
 c=bpy.data.curves.new(n,'CURVE');c.dimensions='3D';c.bevel_depth=r;c.bevel_resolution=4;sp=c.splines.new('BEZIER');sp.bezier_points.add(len(points)-1)
 for b,co in zip(sp.bezier_points,points):b.co=co;b.handle_left_type='AUTO';b.handle_right_type='AUTO'
 o=bpy.data.objects.new(n,c);s.collection.objects.link(o);o.data.materials.append(m);o.parent=parent;return o

def cylinder(n,loc,r,depth,m,parent=None):
 bpy.ops.mesh.primitive_cylinder_add(vertices=64,radius=r,depth=depth,location=loc,rotation=(math.pi/2,0,0));o=bpy.context.object;o.name=n;o.data.materials.append(m);o.parent=parent;mod=o.modifiers.new('Rounded edges','BEVEL');mod.width=.025;mod.segments=3;o.modifiers.new('Normals','WEIGHTED_NORMAL');return o

rig=empty('Whole toy rock',(0,0,1.04));ball=uv('Two-tone Poke Ball',(0,0,0),(1,1,1),red,rig);ball.data.materials.append(white);ball.data.materials.append(black)
for poly in ball.data.polygons:
 z=sum(ball.data.vertices[i].co.z for i in poly.vertices)/len(poly.vertices);poly.material_index=2 if abs(z)<.075 else (0 if z>0 else 1)
cylinder('Button black rim',(0,-1.005,0),.245,.10,black,rig);cylinder('Button white face',(0,-1.075,0),.177,.05,white,rig);cylinder('Button inset',(0,-1.108,0),.105,.025,white,rig)
pika=empty('Sleeping Pikachu',(0,0,0),rig)
body=uv('Soft round body',(.35,.10,1.30),(.76,.48,.48),yellow,pika)
head=uv('Sleeping head',(-.45,-.18,1.53),(.68,.53,.60),yellow,pika)
# Eyes are short curved lids on the front of the head.
curve('Left closed eyelid',[(-.91,-.577,1.58),(-.84,-.643,1.51),(-.72,-.685,1.50)],.028,black,pika)
curve('Right closed eyelid',[(-.40,-.70,1.61),(-.30,-.706,1.55),(-.18,-.663,1.57)],.028,black,pika)
uv('Left cheek',(-.91,-.573,1.36),(.115,.032,.10),cheek,pika)
uv('Right cheek',(-.18,-.653,1.36),(.12,.035,.105),cheek,pika)
uv('Tiny nose',(-.62,-.726,1.42),(.048,.035,.035),black,pika)
curve('Content smile',[(-.65,-.707,1.31),(-.59,-.728,1.28),(-.52,-.71,1.30)],.016,black,pika)
# Forepaws drape onto the ball; rear paws rest beside the body.
uv('Front paw left',(-.55,-.67,.99),(.15,.16,.30),yellow,pika)
uv('Front paw right',(.11,-.67,1.02),(.16,.16,.29),yellow,pika)
uv('Rear paw',(.85,-.10,1.08),(.22,.24,.22),yellow,pika)
# Tapered ears with a shared yellow-to-black surface, rather than separate caps.
def ear(n,base,tip):
 axis=Vector(tip)-Vector(base);length=axis.length;verts=[];faces=[];rings=24;segments=32
 for j in range(rings+1):
  u=j/rings;width=.17*math.sin(math.pi*u)**.7+.007
  for i in range(segments):
   ang=2*math.pi*i/segments;verts.append((width*math.cos(ang),width*.59*math.sin(ang),u*length))
 for j in range(rings):
  for i in range(segments):k=j*segments+i;faces.append((k,j*segments+(i+1)%segments,(j+1)*segments+(i+1)%segments,k+segments))
 mesh=bpy.data.meshes.new(n);mesh.from_pydata(verts,[],faces);mesh.materials.append(yellow);mesh.materials.append(black);o=bpy.data.objects.new(n,mesh);s.collection.objects.link(o);o.location=base;o.rotation_euler=axis.to_track_quat('Z','Y').to_euler();o.parent=pika
 for f in mesh.polygons:f.use_smooth=True;f.material_index=1 if f.center.z>length*.72 else 0
 # Mesh polygon centers need update before assignment.
 mesh.update()
 for f in mesh.polygons:f.material_index=1 if sum(mesh.vertices[i].co.z for i in f.vertices)/len(f.vertices)>length*.72 else 0
 return o
left_ear=ear('Left long black-tipped ear',(-.73,.0,1.91),(-.42,.10,3.03))
right_ear=ear('Right long black-tipped ear',(-.18,.08,1.94),(.41,.17,2.94))
# Extruded lightning tail behind the body, with a rounded toy edge.
points=[(.65,1.18),(1.15,1.65),(1.35,1.45),(1.65,1.80),(2.12,1.12),(1.72,.98),(1.45,1.48),(1.26,1.25),(1.08,1.46),(.8,1.05)]
verts=[(x,y,z) for y in [.20,.38] for x,z in points];n=len(points);faces=[tuple(range(n-1,-1,-1)),tuple(range(n,2*n))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
mesh=bpy.data.meshes.new('Tail mesh');mesh.from_pydata(verts,[],faces);mesh.materials.append(yellow);tail=bpy.data.objects.new('Lightning bolt tail',mesh);s.collection.objects.link(tail);tail.parent=pika;mod=tail.modifiers.new('Soft toy edges','BEVEL');mod.width=.025;mod.segments=3;tail.modifiers.new('Normals','WEIGHTED_NORMAL')
bubble=uv('Blue sleep bubble',(-1.30,-.27,1.48),(.22,.16,.22),blue,pika)
uv('Bubble highlight',(-1.39,-.405,1.56),(.045,.018,.065),white,pika)
# Warm studio plinth and a few toy-like confetti pieces.
bpy.ops.mesh.primitive_plane_add(size=200);bpy.context.object.name='White seamless floor';bpy.context.object.data.materials.append(floor)
for i,(x,y,rr) in enumerate([(-1.6,-.2,.085),(1.65,-.3,.07),(-1.30,.60,.055),(1.45,.8,.05)]):uv('Small confetti bead',(x,y,rr),(rr,rr,rr),blue if i%2 else red)
# Exact 120-frame loop. The next frame repeats the first pose.
for f in range(1,122):
 phase=2*math.pi*(f-1)/120;rock=.14*math.sin(phase);rig.rotation_euler.y=rock;rig.location.x=.12*math.sin(phase);rig.location.z=1.04+.065*(1-math.cos(phase*2))
 pika.scale=(1,1,1+.018*math.sin(phase*2));pika.rotation_euler.y=.025*math.sin(phase-.4)
 bubble.scale=(.22*(1+.18*math.sin(phase)),.16*(1+.18*math.sin(phase)),.22*(1+.18*math.sin(phase)))
 for o,props in [(rig,['location','rotation_euler']),(pika,['scale','rotation_euler']),(bubble,['scale'])]:
  for prop in props:o.keyframe_insert(data_path=prop,frame=f)
for name,loc,power,size in [('Large warm key',(-3,-4,7),1000,5),('Soft rim',(3,3,6),1200,4),('Front fill',(1,-5,3),180,3)]:
 bpy.ops.object.light_add(type='AREA',location=loc);o=bpy.context.object;o.name=name;o.data.energy=power;o.data.shape='DISK';o.data.size=size;o.rotation_euler=(Vector((0,0,2))-o.location).to_track_quat('-Z','Y').to_euler()
bpy.ops.object.camera_add(location=(3.7,-10,4.4));cam=bpy.context.object;cam.rotation_euler=(Vector((.15,0,1.95))-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO';cam.data.ortho_scale=5.6;s.camera=cam
# Convert face curves to meshes so the GLB preserves the eyes and smile.
bpy.ops.object.select_all(action='DESELECT')
curves=[o for o in s.objects if o.type=='CURVE']
for o in curves:o.select_set(True)
if curves:
 bpy.context.view_layer.objects.active=curves[0];bpy.ops.object.convert(target='MESH')
s.frame_set(1);bpy.ops.wm.save_as_mainfile(filepath=str(out/'pikachu-sleep.blend'))
# Export one combined five-second animation in the portable GLB model.
if not a.frames:
 bpy.ops.object.select_all(action='DESELECT')
 for o in [rig]+list(rig.children_recursive):o.select_set(True)
 s.frame_end=121
 bpy.ops.export_scene.gltf(filepath=str(out/'pikachu-sleep.glb'),export_format='GLB',use_selection=True,export_animations=True,export_animation_mode='SCENE',export_anim_scene_split_object=False,export_frame_range=True)
 s.frame_end=120
frames=[int(f) for f in a.frames.split(',')] if a.frames else list(range(1,121));start=time.monotonic();timings=[]
for f in frames:
 s.frame_set(f);s.render.filepath=str(out/'frames'/f'frame_{f:04d}.png');t=time.monotonic();bpy.ops.render.render(write_still=True);timings.append(dict(frame=f,seconds=round(time.monotonic()-t,3)));print('FRAME_COMPLETE '+json.dumps(timings[-1]),flush=True)
meta=dict(blender=bpy.app.version_string,backend='OPTIX',devices=devices,resolution=[1200,1200],fps=24,frames=frames,render_seconds=round(time.monotonic()-start,3),frame_timings=timings,loop_period_frames=120)
(out/'render-metadata.json').write_text(json.dumps(meta,indent=2));print('COMPLETE',flush=True)
