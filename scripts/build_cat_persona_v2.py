"""Gated silver-tabby rebuild: mirrored Skin cage, fused skin, sculpt, retopo, dressed look."""
import argparse
import json
import math
from pathlib import Path
import random
import sys
import time

import bpy
from mathutils import Vector

sys.path.insert(0,str(Path(__file__).resolve().parent))
from contact_sheet import render_views

# Mascot proportions: editable source of truth, before scene construction.
MASCOTS = {'silver_tabby': {
    'head_width': 2.15, 'head_depth': 1.62, 'skull_height': 1.64,
    'head_height_with_ears': 2.0, 'total_height': 4.75,
    'shoulder_width': 1.58, 'body_depth_width': .80, 'depth_gain': 2.30,
    'body_height': 2.75, 'eye_widths_across_head': 3.80,
    'eye_depth': .070, 'eye_center_x': .36, 'eye_z': 3.30,
    'eye_height': .195, 'iris_radius': .13, 'pupil_radius': .046,
    'paw_width': .44, 'whisker_radius': .002,
    'tail_points': [((0,.32,1.12),.85),((.35,.56,.73),1),((.78,.60,.62),.95),
                    ((1.14,.49,.83),.80),((1.27,.40,1.23),.58),((1.18,.36,1.43),.015)],
    'cage_points': [(0,0,1.15),(0,0,1.85),(0,0,2.48),(0,0,2.83),(0,0,3.43),(0,0,3.86),
        (.30,0,1.00),(.31,.015,.61),(.31,-.08,.23),(.31,-.25,.17),
        (.54,0,2.08),(.70,0,1.68),(.73,-.04,1.29),(.73,-.10,1.14),
        (.61,0,4.16),(.80,.01,4.75)],
    'cage_radii': [(.42,.29),(.48,.32),(.38,.30),(1.25,.93),(1.32,1.08),(.82,.70),
        (.23,.25),(.23,.26),(.25,.29),(.23,.18),(.24,.24),(.23,.25),(.17,.20),(.15,.18),(.22,.15),(.025,.025)],
}}
M = MASCOTS['silver_tabby']
CHIBI_EYE_WIDTHS = M['eye_widths_across_head']
EYE_W = M['head_width']/CHIBI_EYE_WIDTHS
assert 1.30 <= M['head_width']/M['shoulder_width'] <= 1.40
assert .38 <= M['head_height_with_ears']/M['total_height'] <= .44
assert .75 <= M['body_depth_width'] <= .85
assert abs(EYE_W*CHIBI_EYE_WIDTHS-M['head_width']) < 1e-8
assert M['eye_depth'] < EYE_W*.15 and 3.2 <= CHIBI_EYE_WIDTHS <= 4.2
assert M['head_depth'] < M['head_width'] and M['paw_width'] < M['head_width']*.25
assert 4 <= len(M['tail_points']) <= 6

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--engine',choices=['CYCLES','BLENDER_EEVEE'])
p.add_argument('--contact',action='store_true')
p.add_argument('--hero',action='store_true')
p.add_argument('--stage',type=int,choices=range(1,6),default=5)
p.add_argument('--output',type=Path,default=Path('results/cat-persona/v2'))
g=p.add_mutually_exclusive_group();g.add_argument('--preview',action='store_true');g.add_argument('--eevee',action='store_true')
p.add_argument('--res',type=int);p.add_argument('--samples',type=int)
p.add_argument('--backdrop',choices=['studio','dusk'],default='studio')
p.add_argument('--stills',action='store_true');p.add_argument('--idle',action='store_true')
p.add_argument('--frames',default='1-48');p.add_argument('--save-blend',action='store_true')
a=p.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
out=a.output.resolve();out.mkdir(parents=True,exist_ok=True)
started=time.perf_counter();random.seed(22)
bpy.ops.wm.read_factory_settings(use_empty=True)
s=bpy.context.scene;s.render.engine=a.engine or ('BLENDER_EEVEE' if a.eevee else 'CYCLES')
if a.engine=='BLENDER_EEVEE':a.eevee=True
if a.engine=='CYCLES' and a.eevee:p.error('--engine CYCLES conflicts with --eevee')
preview=a.preview or a.eevee;samples=a.samples or (32 if preview else 192)
backend='EEVEE CPU software' if a.eevee else 'CPU' if preview else 'OPTIX'
if a.eevee:s.eevee.taa_render_samples=samples
else:
    s.cycles.samples=samples;s.cycles.use_adaptive_sampling=True;s.cycles.adaptive_threshold=.02
    s.cycles.use_denoising=True;s.cycles.denoiser='OPENIMAGEDENOISE'
    s.cycles.max_bounces=8;s.cycles.transmission_bounces=6
    if preview:s.cycles.device='CPU'
    else:
        prefs=bpy.context.preferences.addons['cycles'].preferences;prefs.compute_device_type='OPTIX';prefs.refresh_devices()
        for d in prefs.devices:d.use=d.type=='OPTIX'
        if not any(d.use and d.type=='OPTIX' for d in prefs.devices):raise RuntimeError('OptiX required; use --preview for explicit Cycles CPU')
        s.cycles.device='GPU'
        print('RENDER_DEVICE',[(d.name,d.type) for d in prefs.devices if d.use])
s.render.resolution_x=s.render.resolution_y=a.res or (640 if preview else 1440)
s.render.resolution_percentage=100;s.render.image_settings.file_format='PNG';s.render.image_settings.color_mode='RGB'
s.render.fps=24;s.frame_start=1;s.frame_end=48
s.render.use_persistent_data=True
s.view_settings.view_transform='AgX';s.view_settings.exposure=-.25


def material(name,color,rough=.6):
    m=bpy.data.materials.new(name);m.use_nodes=True
    b=m.node_tree.nodes['Principled BSDF'];b.inputs['Base Color'].default_value=(*color,1);b.inputs['Roughness'].default_value=rough
    return m
clay=material('Neutral modeling clay',(.38,.38,.38))

def active(obj):
    bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj

def apply(obj,name):
    active(obj);bpy.ops.object.modifier_apply(modifier=name)

def smooth_mesh(obj):
    for f in obj.data.polygons:f.use_smooth=True

# Stage 1: one half-stick skeleton, mirrored before Skin and subdivision.
coords=M['cage_points']
edges=[(0,1),(1,2),(2,3),(3,4),(4,5),(0,6),(6,7),(7,8),(8,9),
       (1,10),(10,11),(11,12),(12,13),(5,14),(14,15)]
radii=M['cage_radii']
me=bpy.data.meshes.new('Mirrored biped stick cage');me.from_pydata(coords,edges,[]);me.update()
skin=bpy.data.objects.new('Unified cat skin',me);s.collection.objects.link(skin);active(skin)
mirror=skin.modifiers.new('01 Mirror half cage','MIRROR');mirror.use_clip=True;mirror.use_mirror_merge=True
sk=skin.modifiers.new('02 Skin skeleton','SKIN')
for v,r in zip(me.skin_vertices[0].data,radii):v.radius=r
me.skin_vertices[0].data[0].use_root=True
sub=skin.modifiers.new('03 Subdivision of cage','SUBSURF');sub.levels=2;sub.render_levels=2
skin.data.materials.append(clay);smooth_mesh(skin)
bpy.context.view_layer.update()
# Skin's rounded end caps otherwise leave a small gap beneath the feet.
base=skin.evaluated_get(bpy.context.evaluated_depsgraph_get())
skin.location.z=-min(v[2] for v in base.bound_box)
SHIFT=skin.location.z
active(skin);bpy.ops.object.transform_apply(location=True,rotation=False,scale=False)
if a.stage>=2:
    for mod in list(skin.modifiers):apply(skin,mod.name)
    mod=skin.modifiers.new('Fuse organic skin','REMESH');mod.mode='VOXEL';mod.voxel_size=.038
    apply(skin,mod.name)
    mod=skin.modifiers.new('Relax fused junctions','SMOOTH');mod.factor=.65;mod.iterations=8;apply(skin,mod.name)
    smooth_mesh(skin)
if a.stage>=3:
    # Three ordered sculpt passes; no material or accessory detail at this gate.
    for v in skin.data.vertices:
        x,y,z=v.co;z-=SHIFT
        # (a) broaden soft head and narrow the waist with smooth falloff.
        head=math.exp(-((z-3.4)/.70)**4)
        v.co.x*=1+.025*head
        t=max(0,min(1,(z-2.42)/.50));head_transition=t*t*(3-2*t)
        v.co.y*=1+(M['depth_gain']-1)*(1-head_transition)
        if z>2.52:
            center=Vector((0,0,3.34+SHIFT));delta=v.co-center
            q=Vector((delta.x/(M['head_width']/2),delta.y/(M['head_depth']/2),delta.z/(M['skull_height']/2)))
            length=q.length
            t=max(0,min(1,(z-2.52)/.34));weight=.96*t*t*(3-2*t)
            # The crown becomes a rounded skull; preserve the extruded ear tips.
            ear=max(0,min(1,(z-3.98)/.30))*max(0,min(1,(abs(x)-.42)/.22))
            weight*=1-ear
            if length>.1:v.co=v.co.lerp(center+delta/length,weight)
    for v in skin.data.vertices:
        x,y,z=v.co;z-=SHIFT
        # (b) softly projecting jowls, integrated cheek fluff and broad paws.
        if y<0:
            v.co.y-=.13*math.exp(-((x/.53)**2+((z-3.02)/.25)**2))*min(1,-y/.25)
        cheek=sum(math.exp(-((z-q)/.14)**2) for q in [2.98,3.15])
        v.co.x+=math.copysign(.025*cheek*math.exp(-((abs(x)-.75)/.20)**2),x)
        if z<.42:
            v.co.x+=math.copysign(.025*math.exp(-((z-.20)/.15)**2),x)
            if y<0:v.co.y-=.14*math.exp(-((z-.18)/.19)**2)
    for v in skin.data.vertices:
        x,y,z=v.co;z-=SHIFT
        # (c) tiny broad surface variation rather than separate primitive bumps.
        strength=.003*math.sin(x*19+z*7)*math.sin(y*21-z*9)
        v.co+=v.normal*strength
    mod=skin.modifiers.new('Sculpt polish','SMOOTH');mod.factor=.35;mod.iterations=3;apply(skin,mod.name)
    # Remove residual Skin-junction flares at the nape with a smooth depth envelope.
    for v in skin.data.vertices:
        z=v.co.z-SHIFT
        weight=math.exp(-((z-2.67)/.23)**4)
        radius=.30+.16*max(0,min(1,(z-2.63)/.38))
        v.co.y=(1-weight)*v.co.y+weight*radius*math.tanh(v.co.y/radius)
    # Match the named broad-head target after proportional sculpting.
    head_extent=max(abs(v.co.x) for v in skin.data.vertices if 2.9<v.co.z-SHIFT<4.03)
    factor=M['head_width']/(2*head_extent)
    for v in skin.data.vertices:
        t=max(0,min(1,(v.co.z-SHIFT-2.5)/.35))
        v.co.x*=1+(factor-1)*t
    smooth_mesh(skin)
if a.stage>=4:
    active(skin)
    bpy.ops.object.quadriflow_remesh(target_faces=6500,use_mesh_symmetry=True,use_preserve_sharp=False,use_preserve_boundary=False)
    smooth_mesh(skin)
    sub=skin.modifiers.new('Animation surface subdivision','SUBSURF');sub.levels=1;sub.render_levels=2
    bpy.context.view_layer.update()
    evaluated=skin.evaluated_get(bpy.context.evaluated_depsgraph_get())
    ground=min(v.co.z for v in evaluated.data.vertices)
    for v in skin.data.vertices:v.co.z-=ground
    SHIFT-=ground

# Clean-quads gate: skin the continuous body before adding any dressed look.
rig=None
if a.stage>=4:
    arm=bpy.data.armatures.new('Cat v2 skeleton');rig=bpy.data.objects.new('Cat v2 rig',arm);s.collection.objects.link(rig)
    active(rig);bpy.ops.object.mode_set(mode='EDIT')
    def bone(name,head,tail,parent=None):
        b=arm.edit_bones.new(name);b.head=(head[0],head[1],head[2]+SHIFT);b.tail=(tail[0],tail[1],tail[2]+SHIFT)
        if parent:b.parent=arm.edit_bones[parent]
    bone('root',(0,0,.1),(0,0,1.15))
    bone('spine',(0,0,1.15),(0,0,2.48),'root')
    bone('head',(0,0,2.48),(0,0,3.94),'spine')
    for side,sign in [('L',1),('R',-1)]:
        bone('arm.'+side,(sign*.53,0,2.10),(sign*.73,-.1,1.14),'spine')
        bone('leg.'+side,(sign*.30,0,1.10),(sign*.31,-.1,.18),'root')
        bone('ear.'+side,(sign*.58,0,4.02),(sign*.80,.01,4.75),'head')
    tail_rest=[(0,.30,1.12),(.42,.55,.82),(.86,.56,.80),(1.12,.46,1.18),(1.08,.38,1.45)]
    for i in range(4):bone('tail.%d'%i,tail_rest[i],tail_rest[i+1],'root' if i==0 else 'tail.%d'%(i-1))
    bpy.ops.object.mode_set(mode='OBJECT')
    groups={b.name:skin.vertex_groups.new(name=b.name) for b in arm.bones}
    def ease(lo,hi,x):
        t=max(0,min(1,(x-lo)/(hi-lo)));return t*t*(3-2*t)
    for vertex in skin.data.vertices:
        x,y,z=vertex.co;z-=SHIFT;weights={}
        hw=ease(2.50,2.83,z)
        aw=ease(.40,.64,abs(x))*(1-ease(2.10,2.45,z)) if z>1.05 else 0
        lw=1-ease(.92,1.25,z)
        ew=ease(3.94,4.26,z)*ease(.32,.55,abs(x))
        weights['head']=hw*(1-ew);weights['ear.L' if x>0 else 'ear.R']=hw*ew
        remain=1-hw;weights['arm.L' if x>0 else 'arm.R']=remain*aw
        weights['leg.L' if x>0 else 'leg.R']=remain*(1-aw)*lw
        weights['spine']=remain*(1-aw)*(1-lw)
        total=sum(weights.values())
        for name,value in weights.items():
            if value>1e-5:groups[name].add([vertex.index],value/total,'REPLACE')
    mod=skin.modifiers.new('Continuous skin deformation','ARMATURE');mod.object=rig
    # Armature acts on the retopology cage, subdivision smooths its deformation.
    active(skin)
    bpy.ops.object.modifier_move_up(modifier=mod.name)
    for frame in range(1,50):
        phase=(frame-1)*math.tau/48
        for name in ['spine','head']+['tail.%d'%i for i in range(4)]:
            b=rig.pose.bones[name];b.rotation_mode='XYZ'
            if name=='spine':
                b.scale=(1+.012*math.sin(phase),1+.018*math.sin(phase),1+.009*math.sin(phase));b.keyframe_insert('scale',frame=frame)
            else:
                b.rotation_euler=(0,.025*math.sin(phase),.025*math.sin(phase)) if name=='head' else (0,.12*math.sin(phase-int(name[-1])*.25),.08*math.sin(phase))
                b.keyframe_insert('rotation_euler',frame=frame)
    s.frame_set(1)

# Stage 5: actual separate garments and facial structures, after the retopology gate.
character=[skin]
if a.stage>=5:
    def point(co):return (co[0],co[1],co[2]+SHIFT)
    def own(o,name,mat,bone='spine'):
        o.name=name;o.data.materials.append(mat);character.append(o)
        if o.type=='MESH':smooth_mesh(o)
        if bone:
            bpy.context.view_layer.update();world_matrix=o.matrix_world.copy()
            o.parent=rig;o.parent_type='BONE';o.parent_bone=bone;o.matrix_world=world_matrix
        return o
    def sphere(name,co,scale,mat,bone='head'):
        bpy.ops.mesh.primitive_uv_sphere_add(segments=32,ring_count=20,location=point(co))
        o=bpy.context.object;o.scale=scale
        return own(o,name,mat,bone)
    def curve(name,points,radius,mat,bone='head',radii=None,closed=False):
        c=bpy.data.curves.new(name,'CURVE');c.dimensions='3D';c.resolution_u=16;c.bevel_depth=radius;c.bevel_resolution=4
        sp=c.splines.new('BEZIER');sp.bezier_points.add(len(points)-1)
        for i,(b,co) in enumerate(zip(sp.bezier_points,points)):
            b.co=point(co);b.handle_left_type=b.handle_right_type='AUTO';b.radius=radii[i] if radii else 1
        sp.use_cyclic_u=closed
        o=bpy.data.objects.new(name,c);s.collection.objects.link(o);return own(o,name,mat,bone)
    def mesh(name,verts,faces,mat,bone='head',sub=1):
        me=bpy.data.meshes.new(name);me.from_pydata([point(v) for v in verts],[],faces);me.update()
        o=bpy.data.objects.new(name,me);s.collection.objects.link(o);own(o,name,mat,bone)
        if sub:
            mod=o.modifiers.new('Soft sculpted finish','SUBSURF');mod.levels=sub;mod.render_levels=sub
        return o
    bpy.context.view_layer.update()
    evaluated=skin.evaluated_get(bpy.context.evaluated_depsgraph_get())
    def front(x,z):
        hit,loc,normal,index=skin.ray_cast(Vector((x,-4,z+SHIFT)),Vector((0,1,0)))
        return loc.y if hit else -.40
    def fabric(name,color):
        m=material(name,color,.72);n,l=m.node_tree.nodes,m.node_tree.links;b=n['Principled BSDF']
        b.inputs['Sheen Weight'].default_value=.42
        tex=n.new('ShaderNodeTexNoise');tex.inputs['Scale'].default_value=160
        bump=n.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.14;bump.inputs['Distance'].default_value=.006
        l.new(tex.outputs['Fac'],bump.inputs['Height']);l.new(bump.outputs[0],b.inputs['Normal'])
        return m
    fur=material('Silver fur with SSS and UV tabby',(.43,.45,.48),.65)
    n,l=fur.node_tree.nodes,fur.node_tree.links;b=n['Principled BSDF']
    b.inputs['Subsurface Weight'].default_value=.10;b.inputs['Subsurface Scale'].default_value=.065;b.inputs['Sheen Weight'].default_value=.25
    col=skin.data.color_attributes.new(name='FurColor',type='FLOAT_COLOR',domain='POINT')
    weights=skin.data.attributes.new('TabbyWeight','FLOAT','POINT')
    for vertex in skin.data.vertices:
        x,y,z=vertex.co;z-=SHIFT
        base=Vector((.25,.275,.31))
        frontmask=max(0,min(1,(-y-.08)/.35))
        muzzle=math.exp(-((x/.52)**4+((z-3.02)/.30)**4))*frontmask
        paw=(1-max(0,min(1,(z-.25)/.22)))
        tint=max(muzzle,paw)
        base=base.lerp(Vector((.77,.72,.64)),tint*.9)
        cheek=math.exp(-((abs(x)-.65)/.22)**2)*frontmask*(math.exp(-((z-3.23)/.04)**2)+math.exp(-((z-3.09)/.04)**2))
        base*=1-.20*min(1,cheek)
        blush=.12*math.exp(-((abs(x)-.54)/.12)**2-((z-3.15)/.07)**2)*frontmask
        base=base.lerp(Vector((.72,.35,.32)),blush)
        col.data[vertex.index].color=(*base,1)
        weights.data[vertex.index].value=.55 if z<1.2 or (abs(x)>.55 and z<2.3) else .12
    skin.data.color_attributes.active_color=col
    uv=skin.data.uv_layers.new(name='Cylindrical tabby UV')
    for loop in skin.data.loops:
        v=skin.data.vertices[loop.vertex_index].co
        uv.data[loop.index].uv=(math.atan2(v.x,-v.y)/math.tau+.5,(v.z-SHIFT)/M['total_height'])
    vc=n.new('ShaderNodeVertexColor');vc.layer_name='FurColor'
    tc=n.new('ShaderNodeTexCoord');wave=n.new('ShaderNodeTexWave');wave.bands_direction='Y'
    wave.inputs['Scale'].default_value=2.2;wave.inputs['Distortion'].default_value=2.2
    l.new(tc.outputs['UV'],wave.inputs['Vector'])
    ramp=n.new('ShaderNodeValToRGB');ramp.color_ramp.elements[0].color=(.60,.60,.60,1);ramp.color_ramp.elements[0].position=.22
    ramp.color_ramp.elements[1].position=.75
    l.new(wave.outputs[0],ramp.inputs[0])
    attr=n.new('ShaderNodeAttribute');attr.attribute_name='TabbyWeight'
    mix=n.new('ShaderNodeMixRGB');mix.blend_type='MULTIPLY';l.new(attr.outputs['Fac'],mix.inputs[0]);l.new(vc.outputs[0],mix.inputs[1]);l.new(ramp.outputs[0],mix.inputs[2]);l.new(mix.outputs[0],b.inputs['Base Color'])
    noise=n.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=110
    bump=n.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.12;bump.inputs['Distance'].default_value=.006
    l.new(noise.outputs['Fac'],bump.inputs['Height']);l.new(bump.outputs[0],b.inputs['Normal'])
    skin.data.materials.clear();skin.data.materials.append(fur)
    ivory=fabric('Warm ivory cardigan knit',(.59,.555,.50))
    charcoal=fabric('Charcoal zip hoodie',(.035,.042,.055))
    black=material('Soft black',(.009,.012,.018),.32)
    cream=material('Cream muzzle detail',(.70,.66,.58),.65)
    lidmat=material('Silver eyelid skin',(.30,.32,.35),.58);lidmat.node_tree.nodes['Principled BSDF'].inputs['Subsurface Weight'].default_value=.10
    pink=material('Warm pink pads and ear lining',(.64,.28,.29),.6);pink.node_tree.nodes['Principled BSDF'].inputs['Subsurface Weight'].default_value=.20
    ink=material('Dry brush gray',(.28,.30,.33),.8)
    glass=material('Real optical glass',(.97,.985,1),.025);gb=glass.node_tree.nodes['Principled BSDF'];gb.inputs['Transmission Weight'].default_value=1;gb.inputs['IOR'].default_value=1.45
    cornea=glass.copy();cornea.name='Cornea IOR 1.38';cornea.node_tree.nodes['Principled BSDF'].inputs['IOR'].default_value=1.38
    eye_white=material('Warm eye sclera',(.80,.77,.67),.25)
    amber=material('Amber iris gradient',(.60,.27,.045),.2)
    n,l=amber.node_tree.nodes,amber.node_tree.links;tc=n.new('ShaderNodeTexCoord');sep=n.new('ShaderNodeSeparateXYZ');ramp=n.new('ShaderNodeValToRGB')
    ramp.color_ramp.elements[0].color=(.85,.46,.08,1);ramp.color_ramp.elements[1].color=(.15,.045,.008,1)
    l.new(tc.outputs['Generated'],sep.inputs[0]);l.new(sep.outputs['Z'],ramp.inputs[0]);l.new(ramp.outputs[0],n['Principled BSDF'].inputs['Base Color'])
    gleam=material('Eye highlight',(.98,.98,.96),.05);gleam.node_tree.nodes['Principled BSDF'].inputs['Emission Color'].default_value=(.7,.7,.65,1);gleam.node_tree.nodes['Principled BSDF'].inputs['Emission Strength'].default_value=.4
    # Clothing uses thin offsets of the actual retopology surface, not boxes or tubes.
    def shell(name,kind,mat,offset):
        ids={};verts=[];faces=[]
        for poly in skin.data.polygons:
            c=poly.center;x,y,z=c.x,c.y,c.z-SHIFT
            if kind=='cardigan':ok=1.12<z<2.48 and not (abs(x)>.52 and z<1.42) and not (y<-.05 and abs(x)<.23+.06*max(0,z-2.1))
            elif kind=='tee':ok=1.17<z<2.31+.10*abs(x) and y<-.015 and abs(x)<.43
            elif kind=='hoodie':ok=1.16<z<2.47 and y<-.015 and .17<abs(x)<.42
            elif kind=='hood':ok=2.13<z<2.67 and y>.02 and abs(x)<.58
            elif kind=='cuffs':ok=1.36<z<1.49 and abs(x)>.54
            else:ok=1.12<z<1.26 and abs(x)<.56
            if not ok:continue
            face=[]
            for vi in poly.vertices:
                if vi not in ids:
                    v=skin.data.vertices[vi];co=v.co.copy();co+=v.normal*offset
                    if kind=='cardigan':co+=v.normal*(.012*math.sin(co.z*19+co.x*3));co.x*=1.025
                    if kind=='hood':co.y+=.13;co.z-=.12
                    ids[vi]=len(verts);verts.append((co.x,co.y,co.z-SHIFT))
                face.append(ids[vi])
            faces.append(tuple(face))
        obj=mesh(name,verts,faces,mat,'spine',2)
        solid=obj.modifiers.new('Thin fabric thickness','SOLIDIFY');solid.thickness=.028
        return obj
    shell('Black crew tee from torso','tee',black,.025)
    shell('Visible charcoal zip fronts','hoodie',charcoal,.065)
    shell('Oversized soft cardigan shell','cardigan',ivory,.10)
    shell('Ribbed sleeve cuffs','cuffs',ivory,.12)
    shell('Ribbed cardigan hem','hem',ivory,.115)
    shell('Bunched hood from shoulder surface','hood',charcoal,.12)
    for sign in [-1,1]:
        pts=[]
        for z in [1.15,1.45,1.85,2.15,2.40]:
            x=sign*(.23+.06*max(0,z-2.1));pts.append((x,front(x,z)-.145,z))
        curve('Cardigan soft opening edge',pts,.026,ivory,'spine')
        curve('Hoodie zipper',[(sign*.17,front(sign*.17,z)-.09,z) for z in [1.19,1.55,1.95,2.38]],.012,ink,'spine')
        curve('Hood drawstring',[(sign*.26,front(sign*.26,2.45)-.15,2.45),(sign*.31,front(sign*.31,2.1)-.17,2.1),(sign*.30,front(sign*.30,1.80)-.17,1.80)],.012,ink,'spine')
    curve('Crew neckline',[(x,front(x,2.30+.1*abs(x))-.045,2.30+.1*abs(x)) for x in [-.3,-.15,0,.15,.3]],.017,black,'spine')
    for row in range(3):
        for sign in [-1,1]:
            for j in range(8):
                t=j/7;x=sign*(.19*(1-t)+random.uniform(-.012,.012));z=1.98-row*.15-.18*t
                w=random.uniform(.012,.026);h=random.uniform(.02,.045);y=front(x,z)-.046
                mesh('Painterly chevron fleck',[(x-w,y,z-h),(x+w*.3,y-.002,z-h*.3),(x+w,y,z+h),(x-w*.4,y,z+h*.5)],[(0,1,2,3)],ink,'spine',0)
    # Flattened, layered, socketed eyes. Quad eyelid rings overlap both almond edges.
    for side,sign in [('L',1),('R',-1)]:
        x=sign*M['eye_center_x'];z=M['eye_z'];ys=front(x,z)
        sphere('Socketed flattened sclera.'+side,(x,ys-.008,z),(EYE_W/2,M['eye_depth'],M['eye_height']),eye_white)
        sphere('Iris disc.'+side,(x,ys-.080,z-.02),(M['iris_radius'],.015,.145),amber)
        sphere('Pupil proud of iris.'+side,(x,ys-.098,z-.02),(M['pupil_radius'],.010,.100),black)
        sphere('Glossy cornea dome.'+side,(x,ys-.088,z-.02),(.144,.033,.156),cornea)
        sphere('Large catchlight.'+side,(x-.037,ys-.129,z+.050),(.027,.008,.029),gleam)
        sphere('Small catchlight.'+side,(x+.034,ys-.126,z-.067),(.011,.006,.012),gleam)
        verts=[];faces=[];steps=48
        for ring in range(4):
            t=ring/3
            for j in range(steps):
                ang=j*math.tau/steps;dx=(EYE_W/2+.055*t)*math.cos(ang)
                dz=(.145+.075*t)*math.sin(ang)*( .74+.26*abs(math.sin(ang)))
                verts.append((x+dx,ys-.075+.08*t,z+dz))
        for ring in range(3):
            for j in range(steps):
                q=ring*steps+j;r=ring*steps+(j+1)%steps;faces.append((q,r,r+steps,q+steps))
        mesh('Three quad socket loops.'+side,verts,faces,lidmat,sub=1)
        lid=sphere('Sleepy upper lid.'+side,(x,ys-.067,z+.145),(EYE_W/2+.01,.075,.092),lidmat)
        lid.shape_key_add(name='Basis');key=lid.shape_key_add(name='Blink')
        for v in key.data:v.co.z=v.co.z*1.9-1.25
        for f,value in [(1,0),(19,0),(21,1),(23,0),(49,0)]:key.value=value;key.keyframe_insert('value',frame=f)
        curve('Upper lid lash.'+side,[(x-EYE_W*.45,ys-.104,z+.10),(x,ys-.145,z+.12),(x+EYE_W*.45,ys-.104,z+.10)],.014,black)
        fy=ys-.18;hw=EYE_W/2+.035
        framepts=[(x-hw+.035,fy,z+.20),(x+hw-.035,fy,z+.20),(x+hw,fy,z+.16),(x+hw-.025,fy,z-.16),(x+hw-.07,fy,z-.20),(x-hw+.07,fy,z-.20),(x-hw+.025,fy,z-.16),(x-hw,fy,z+.15)]
        curve('Rectangular glasses frame.'+side,framepts,.025,black,closed=True)
        sphere('Refractive glasses lens.'+side,(x,fy+.008,z),(.263,.009,.175),glass)
        curve('Glasses temple.'+side,[(sign*.65,fy,z+.15),(sign*.90,-.28,z+.17),(sign*.86,.20,z+.12)],.022,black)
        # Insets on the extruded triangular cat ears; their roots remain part of the fused skin.
        ey=front(sign*.68,4.16)
        sphere('Pink ear inset.'+side,(sign*.68,ey-.016,4.16),(.105,.022,.21),pink)
        for row in range(3):
            z0=3.07-row*.055;root=(sign*.36,front(sign*.36,z0)-.015,z0)
            curve('Drooping tapered whisker.'+side,[root,(sign*.70,root[1]-.06,z0+.035),(sign*1.00,root[1]-.04,z0+.005),(sign*(1.17+.04*row),root[1]+.01,z0-.055-.025*row)],M['whisker_radius'],cream,radii=[1,.8,.45,.015])
        for toe in [-.08,.08]:
            tx=sign*.31+toe
            curve('Fused paw toe groove',[(tx,front(tx,z)-.003,z) for z in [.16,.22,.28]],.005,ink,'leg.'+side)
        sphere('Pink sole toe beans.'+side,(sign*.31,-.14,.035),(.11,.12,.018),pink,'leg.'+side)
    ybridge=min(front(-M['eye_center_x'],M['eye_z']),front(M['eye_center_x'],M['eye_z']))-.19
    curve('Glasses bridge',[(-.065,ybridge,M['eye_z']+.04),(0,ybridge-.015,M['eye_z']+.07),(.065,ybridge,M['eye_z']+.04)],.024,black)
    ny=front(0,3.14)
    sphere('Small pink nose',(0,ny-.045,3.14),(.065,.043,.045),pink)
    curve('Tiny w mouth',[(x,front(x,3.035)-.016,z) for x,z in [(-.11,3.04),(-.055,3.01),(0,3.045),(.055,3.01),(.11,3.04)]],.009,black)
    # Sculpted, tapered locks root inside the scalp; no cap or helmet under them.
    hair_mats=[]
    for i in range(5):
        h=fabric('Silver lock tone %d'%i,(.26+i*.025,.28+i*.025,.31+i*.025));hair_mats.append(h)
    def lock(name,points,widths,mat):
        points=[tuple(p) for p in points]
        for j in range(1,len(points)):
            x,y,z=points[j]
            if 'back tuft' in name:
                hit,loc,normal,index=skin.ray_cast(Vector((x,4,z+SHIFT)),Vector((0,-1,0)))
                y=max(y,loc.y+.055) if hit else y
            else:y=min(y,front(x,z)-.075)
            points[j]=(x,y,z)
        verts=[];faces=[];sides=12
        for i,co in enumerate(points):
            direction=Vector(points[min(i+1,len(points)-1)])-Vector(points[max(0,i-1)])
            direction.normalize();u=direction.cross(Vector((0,1,0))).normalized();v=direction.cross(u).normalized()
            for j in range(sides):
                ang=j*math.tau/sides;verts.append(Vector(co)+widths[i]*(math.cos(ang)*u+.40*math.sin(ang)*v))
        for i in range(len(points)-1):
            for j in range(sides):
                q=i*sides+j;r=i*sides+(j+1)%sides;faces.append((q,r,r+sides,q+sides))
        faces.extend([tuple(range(sides-1,-1,-1)),tuple((len(points)-1)*sides+j for j in range(sides))])
        return mesh(name,verts,faces,mat,'head',2)
    for i in range(8):
        t=(i-3.5)/3.5;x=t*.72;direction=-1 if t<.2 else 1
        points=[(x*.25+.10,-.08,3.78),(x*.7,-.40,4.02-abs(t)*.10),
                (x+direction*.06,-.64,3.79-abs(t)*.08),(x+direction*.16,-.69,3.51+random.uniform(-.07,.08)),
                (x+direction*.21,-.60,3.40+random.uniform(-.06,.08))]
        lock('Rooted swept bang %02d'%i,points,[.035,.16,.16,.065,.001],hair_mats[i%5])
    for i in range(5):
        x=-.36+i*.17
        lock('Messy rooted crown %02d'%i,[(x+.13,.08,3.75),(x+.10,.02,4.10),(x-.13,-.06,4.20+random.uniform(-.06,.04)),(x-.26,-.07,4.10)],[.04,.14,.09,.001],hair_mats[(i+1)%5])
    for i in range(5):
        phi=-1.3+i*.65
        lock('Short back tuft %02d'%i,[(.35*math.sin(phi),.14,3.78),(.69*math.sin(phi),.43*math.cos(phi),3.93),(.80*math.sin(phi+.1),.62*math.cos(phi+.1),3.68),(.83*math.sin(phi+.15),.65*math.cos(phi+.15),3.52)],[.035,.15,.11,.001],hair_mats[(i+2)%5])
    # Headphones remain real separate objects around the neck.
    neck_y=min(front(-.4,2.43),front(.4,2.43))-.10
    curve('Neck headphone band',[(-.41,neck_y+.08,2.48),(-.43,.28,2.56),(0,.42,2.55),(.43,.28,2.56),(.41,neck_y+.08,2.48)],.047,black,'spine')
    for sign in [-1,1]:
        sphere('Headphone leather cushion',(sign*.40,neck_y,2.43),(.13,.13,.21),black,'spine')
        sphere('Headphone metal cup',(sign*.43,neck_y-.10,2.43),(.105,.045,.17),charcoal,'spine')
        curve('Headphone trim',[(sign*.43+.075*math.cos(j*math.tau/20),neck_y-.15,2.43+.13*math.sin(j*math.tau/20)) for j in range(20)],.008,ink,'spine',closed=True)
    curve('Headphone cable',[(-.40,neck_y-.15,2.24),(-.31,front(-.31,1.7)-.19,1.7),(-.10,-.48,1.05),(.14,-.46,1.02),(.22,front(.22,1.55)-.14,1.55)],.009,black,'spine')
    tailmat=material('Soft striped tail',(.44,.46,.49),.65);n,l=tailmat.node_tree.nodes,tailmat.node_tree.links
    tc=n.new('ShaderNodeTexCoord');wave=n.new('ShaderNodeTexWave');wave.bands_direction='Z';wave.inputs['Scale'].default_value=1.2;wave.inputs['Distortion'].default_value=2
    ramp=n.new('ShaderNodeValToRGB');ramp.color_ramp.elements[0].color=(.26,.28,.31,1);ramp.color_ramp.elements[1].color=(.53,.55,.58,1)
    l.new(tc.outputs['Generated'],wave.inputs['Vector']);l.new(wave.outputs[0],ramp.inputs[0]);l.new(ramp.outputs[0],n['Principled BSDF'].inputs['Base Color'])
    tail=curve('Tapered Bezier S tail',[co for co,radius in M['tail_points']],.18,tailmat,None,radii=[r for co,r in M['tail_points']])
    sphere('Soft cream tail tip',(1.20,.37,1.36),(.075,.07,.10),cream,None)
    bpy.context.view_layer.update()


# Neutral curved studio set is shared by every modeling gate.
floor=material('Warm studio sweep',(.29,.28,.27),.85)
profile=[(-12,0),(2,0),(3,.12),(4,.6),(4.7,1.4),(5,2.5),(5,9)]
verts=[(x,y,z-.035) for x in [-20,20] for y,z in profile];n=len(profile)
me=bpy.data.meshes.new('Cyc mesh');me.from_pydata(verts,[],[(i,i+1,n+i+1,n+i) for i in range(n-1)]);me.update()
cyc=bpy.data.objects.new('Studio sweep',me);s.collection.objects.link(cyc);me.materials.append(floor);smooth_mesh(cyc)
sub=cyc.modifiers.new('Sweep rounding','SUBSURF');sub.levels=2
world=bpy.data.worlds.new('Soft environment');s.world=world;world.use_nodes=True
world.node_tree.nodes['Background'].inputs[0].default_value=(.42,.46,.55,1);world.node_tree.nodes['Background'].inputs[1].default_value=.30

def area(name,loc,energy,color,size):
    d=bpy.data.lights.new(name,'AREA');d.energy=energy;d.color=color;d.shape='DISK';d.size=size
    o=bpy.data.objects.new(name,d);s.collection.objects.link(o);o.location=loc;o.rotation_euler=(Vector((0,0,2.3))-o.location).to_track_quat('-Z','Y').to_euler()
area('Large warm key',(-3,-4,7),500,(1,.86,.73),4)
area('Cool soft fill',(4,-2,4),280,(.75,.84,1),3)
area('Crown rim',(1,3,6),650,(1,.91,.78),3)
d=bpy.data.cameras.new('Portrait camera');cam=bpy.data.objects.new('Portrait camera',d);s.collection.objects.link(cam);s.camera=cam

def view(angle):
    d.type='ORTHO';d.ortho_scale=5.3;cam.location=(10*math.sin(angle),-10*math.cos(angle),3.2)
    cam.rotation_euler=(Vector((0,0,2.25))-cam.location).to_track_quat('-Z','Y').to_euler();cyc.rotation_euler.z=angle
view(math.radians(28))
if a.hero:
    d.type='PERSP';d.lens=80
    cam.location=(5.6,-10.5,3.4)
    target=Vector((0,0,2.30));cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler()
    d.dof.use_dof=True;d.dof.aperture_fstop=5.6
    d.dof.focus_distance=(Vector((0,-.65,3.43+SHIFT))-cam.location).dot((target-cam.location).normalized())
metadata=dict(render_devices=[dict(name=d.name,type=d.type,enabled=bool(d.use)) for d in bpy.context.preferences.addons['cycles'].preferences.devices] if backend=='OPTIX' else [],blender_version=bpy.app.version_string,backend=backend,preview=preview,stage=a.stage,
              resolution=[s.render.resolution_x,s.render.resolution_y],samples=samples,adaptive_threshold=.02,
              denoiser='OpenImageDenoise' if not a.eevee else None,fps=24,loop_period_frames=48,
              rig_bones=len(rig.data.bones) if rig else 0,vertices=len(skin.data.vertices),faces=len(skin.data.polygons),proportions=M,quad_faces=sum(len(f.vertices)==4 for f in skin.data.polygons),renders=[])
def render(path):
    # Keep the sweep behind the active camera for turnarounds, including contact views.
    if abs(cam.location.z-2.25)<9:cyc.rotation_euler.z=math.atan2(cam.location.x,-cam.location.y)
    s.render.filepath=str(path);t=time.perf_counter();bpy.ops.render.render(write_still=True)
    metadata['renders'].append(dict(file=str(path.relative_to(out)),frame=s.frame_current,seconds=round(time.perf_counter()-t,3)))
    (out/('hero-metadata.json' if a.hero else 'render-metadata.json')).write_text(json.dumps(metadata,indent=2)+'\n')
if a.stage>=5 and a.save_blend:
    active(rig);rig.select_set(True);copies=[]
    for obj in character:
        if obj.type=='CURVE':
            depsgraph=bpy.context.evaluated_depsgraph_get()
            data=bpy.data.meshes.new_from_object(obj.evaluated_get(depsgraph))
            clone=bpy.data.objects.new(obj.name+' export',data);s.collection.objects.link(clone);clone.matrix_world=obj.matrix_world
            clone.select_set(True);copies.append(clone)
        else:obj.select_set(True)
    lod=[]
    for obj in character:
        for mod in obj.modifiers:
            if mod.type=='SUBSURF':lod.append((mod,mod.levels));mod.levels=min(1,mod.levels)
    bpy.ops.export_scene.gltf(filepath=str(out/'cat-persona-v2.glb'),export_format='GLB',use_selection=True,export_animations=False)
    for mod,level in lod:mod.levels=level
    for obj in copies:bpy.data.objects.remove(obj,do_unlink=True)

if a.save_blend or a.stage<5:bpy.ops.wm.save_as_mainfile(filepath=str(out/'cat-persona-v2.blend'))
if a.stage<5 or a.contact:render_views(s,out,render,scale=5.3)
elif a.stills:
    for name,angle in [('front',0),('three_quarter',32),('side',90),('back',180)]:view(math.radians(angle));render(out/(name+'.png'))
else:render(out/('hero_three_quarter.png' if a.hero else 'three_quarter.png'))
