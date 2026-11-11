"""Deterministic silver tabby persona. CPU rendering requires --preview or --eevee."""
import argparse
import json
import math
import random
import sys
import time
from pathlib import Path

import bpy
from mathutils import Matrix, Vector

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--output', type=Path, default=Path('results/cat-persona'))
g = p.add_mutually_exclusive_group()
g.add_argument('--preview', action='store_true')
g.add_argument('--eevee', action='store_true')
p.add_argument('--res', type=int)
p.add_argument('--samples', type=int)
p.add_argument('--backdrop', choices=['studio', 'dusk'], default='studio')
p.add_argument('--stills', action='store_true')
p.add_argument('--idle', action='store_true')
p.add_argument('--frames', default='1-48')
p.add_argument('--save-blend', action='store_true')
a = p.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
if a.res is not None and a.res < 16:
    p.error('--res must be at least 16')
if a.samples is not None and a.samples < 1:
    p.error('--samples must be positive')
preview = a.preview or a.eevee
out = a.output.resolve()
out.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
s = bpy.context.scene
s.render.engine = 'CYCLES'
samples = a.samples or (12 if preview else 128)
backend = 'CPU'
if a.eevee:
    s.render.engine = 'BLENDER_EEVEE'
    s.eevee.taa_render_samples = samples
    backend = 'EEVEE CPU software'
else:
    s.cycles.samples = samples
    s.cycles.use_denoising = True
    if not preview:
        prefs = bpy.context.preferences.addons['cycles'].preferences
        prefs.compute_device_type = 'OPTIX'
        prefs.refresh_devices()
        for d in prefs.devices:
            d.use = d.type == 'OPTIX'
        if not any(d.use and d.type == 'OPTIX' for d in prefs.devices):
            raise RuntimeError('OptiX GPU required; select --preview or --eevee explicitly for CPU previews')
        s.cycles.device = 'GPU'
        backend = 'OPTIX'
    else:
        s.cycles.device = 'CPU'
s.render.resolution_x = a.res or (640 if preview else 1440)
s.render.resolution_y = a.res or (640 if preview else 1080)
s.render.resolution_percentage = 100
s.render.image_settings.file_format = 'PNG'
s.render.fps = 24
s.frame_start, s.frame_end = 1, 48
s.view_settings.view_transform = 'AgX'
s.view_settings.exposure = -.45
random.seed(17)
parts = []

def mat(name, color, fur=False, knit=False):
    m = bpy.data.materials.new(name)
    m.diffuse_color = (*color, 1)
    m.use_nodes = True
    n, l = m.node_tree.nodes, m.node_tree.links
    b = n.get('Principled BSDF')
    b.inputs['Base Color'].default_value = (*color, 1)
    b.inputs['Roughness'].default_value = .75 if fur or knit else .4
    b.inputs['Sheen Weight'].default_value = .18 if fur or knit else .05
    if fur or knit:
        tex = n.new('ShaderNodeTexCoord')
        noise = n.new('ShaderNodeTexNoise')
        noise.inputs['Scale'].default_value = 110 if fur else 180
        l.new(tex.outputs['Generated'], noise.inputs['Vector'])
        bump = n.new('ShaderNodeBump')
        bump.inputs['Strength'].default_value = .12 if fur else .10
        bump.inputs['Distance'].default_value = .009 if fur else .004
        l.new(noise.outputs['Fac'], bump.inputs['Height'])
        l.new(bump.outputs['Normal'], b.inputs['Normal'])
        wave = n.new('ShaderNodeTexWave')
        wave.wave_type = 'BANDS'
        wave.bands_direction = 'Z' if fur else 'X'
        wave.inputs['Scale'].default_value = .85 if fur else 85
        wave.inputs['Distortion'].default_value = 2.4 if fur else .12
        l.new(tex.outputs['Generated' if fur else 'UV'], wave.inputs['Vector'])
        if fur:
            ramp = n.new('ShaderNodeValToRGB')
            ramp.color_ramp.interpolation = 'EASE'
            ramp.color_ramp.elements[0].position = .16
            ramp.color_ramp.elements[0].color = (*(v*.64 for v in color), 1)
            ramp.color_ramp.elements[1].position = .84
            ramp.color_ramp.elements[1].color = (*color, 1)
            l.new(wave.outputs['Color'], ramp.inputs[0])
            l.new(ramp.outputs[0], b.inputs['Base Color'])
        else:
            l.new(wave.outputs['Color'], bump.inputs['Height'])
    return m

silver = mat('Silver tabby | soft irregular bands', (.34,.34,.365), fur=True)
hair_variants=[]
for i in range(6):
    h=mat('Silver locks root-to-tip %d'%i,(.16+i*.013,.18+i*.013,.21+i*.013))
    n,l=h.node_tree.nodes,h.node_tree.links
    attr=n.new('ShaderNodeAttribute'); attr.attribute_name='strand_t'
    ramp=n.new('ShaderNodeValToRGB')
    ramp.color_ramp.elements[0].position=.05
    ramp.color_ramp.elements[0].color=(.105+i*.004,.115+i*.004,.135+i*.005,1)
    ramp.color_ramp.elements[1].position=.65
    ramp.color_ramp.elements[1].color=(.26+i*.014,.275+i*.014,.30+i*.015,1)
    l.new(attr.outputs['Fac'],ramp.inputs[0]);l.new(ramp.outputs['Color'],n['Principled BSDF'].inputs['Base Color'])
    n['Principled BSDF'].inputs['Roughness'].default_value=.63
    tex=n.new('ShaderNodeTexCoord');stretch=n.new('ShaderNodeVectorMath');stretch.operation='MULTIPLY'
    stretch.inputs[1].default_value=(18,.8,1);l.new(tex.outputs['UV'],stretch.inputs[0])
    noise=n.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=4
    l.new(stretch.outputs['Vector'],noise.inputs['Vector'])
    bump=n.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.14;bump.inputs['Distance'].default_value=.008
    l.new(noise.outputs['Fac'],bump.inputs['Height']);l.new(bump.outputs['Normal'],n['Principled BSDF'].inputs['Normal'])
    mix=n.new('ShaderNodeMixRGB');mix.blend_type='MULTIPLY';mix.inputs[0].default_value=.25
    l.new(ramp.outputs['Color'],mix.inputs[1]);l.new(noise.outputs['Fac'],mix.inputs[2])
    l.new(mix.outputs[0],n['Principled BSDF'].inputs['Base Color'])
    hair_variants.append(h)
hair=hair_variants[2]
mark=mat('Charcoal tabby markings',(.085,.095,.115))
cream = mat('Warm cream paws and muzzle', (.68,.63,.54))
pink = mat('Dusty rose inner ears and nose', (.58,.28,.29))
black = mat('Soft black frame', (.012,.016,.022))
hood = mat('Charcoal hoodie', (.045,.052,.065), knit=True)
knit = mat('Light gray cardigan rib knit', (.584,.546,.503), knit=True)
rib = mat('Cardigan cuffs and edging', (.46,.425,.385), knit=True)
amber = mat('Warm amber iris', (.55,.27,.055))
white = mat('Eye ivory', (.85,.82,.71))
shine = mat('Catchlights', (.98,.98,.95))
graphic = mat('Brushstroke gray', (.31,.33,.35))

def register(o, name, material, bone):
    o.name = name
    o.data.materials.append(material)
    if o.type == 'MESH':
        for f in o.data.polygons: f.use_smooth = True
    if bone: parts.append((o,bone))
    return o

def ball(name, loc, scale, material, bone='spine'):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=20, location=loc)
    o = bpy.context.object
    o.scale = scale
    return register(o,name,material,bone)

def tube(name, points, radius, material, bone='spine', cyclic=False):
    c = bpy.data.curves.new(name,'CURVE')
    c.dimensions='3D'
    c.bevel_depth=radius
    c.bevel_resolution=3
    sp=c.splines.new('BEZIER')
    sp.bezier_points.add(len(points)-1)
    for b, co in zip(sp.bezier_points, points):
        b.co=co
        b.handle_left_type=b.handle_right_type='AUTO'
    sp.use_cyclic_u=cyclic
    o=bpy.data.objects.new(name,c)
    s.collection.objects.link(o)
    return register(o,name,material,bone)

def lock(name, points, widths, material, bone='head', aspect=.48):
    if bone=='head' and ('hair' in material.name.lower() or material.name.startswith('Silver locks')):
        near=Vector(points[-2]).lerp(Vector(points[-1]),.78)
        points=list(points[:-1])+[tuple(near),points[-1]]
        widths=list(widths[:-1])+[widths[-2]*.22,widths[-1]]
    verts=[]
    for i, pt in enumerate(points):
        tangent=Vector(points[min(i+1,len(points)-1)])-Vector(points[max(0,i-1)])
        tangent.normalize()
        u=tangent.cross(Vector((0,1,0))).normalized()
        if u.length < .1: u=Vector((1,0,0))
        v=tangent.cross(u).normalized()
        for j in range(12):
            ang=j*math.tau/12
            verts.append(Vector(pt)+widths[i]*(math.cos(ang)*u+aspect*math.sin(ang)*v))
    faces=[]
    for i in range(len(points)-1):
        for j in range(12):
            q=i*12+j; r=i*12+(j+1)%12
            faces.append((q,r,r+12,q+12))
    faces.extend([tuple(range(11,-1,-1)),tuple((len(points)-1)*12+j for j in range(12))])
    me=bpy.data.meshes.new(name); me.from_pydata(verts,[],faces); me.update()
    attr=me.attributes.new('strand_t','FLOAT','POINT')
    for i,d in enumerate(attr.data): d.value=(i//12)/(len(points)-1)
    uv=me.uv_layers.new(name='Strand UV')
    for loop in me.loops:
        vi=loop.vertex_index;uv.data[loop.index].uv=((vi%12)/12,(vi//12)/(len(points)-1))
    o=bpy.data.objects.new(name,me); s.collection.objects.link(o)
    register(o,name,material,bone)
    sub=o.modifiers.new('Soft sculpted clump','SUBSURF'); sub.levels=2
    return o

def surface(name, verts, faces, material, bone='spine', uvs=None, solid=.0, subdivision=2):
    me=bpy.data.meshes.new(name); me.from_pydata(verts,[],faces); me.update()
    if uvs:
        uv=me.uv_layers.new(name='Knit UV')
        for loop in me.loops: uv.data[loop.index].uv=uvs[loop.vertex_index]
    o=bpy.data.objects.new(name,me); s.collection.objects.link(o)
    register(o,name,material,bone)
    if subdivision:
        sub=o.modifiers.new('Soft tailored surface','SUBSURF'); sub.levels=subdivision
    if solid:
        mod=o.modifiers.new('Garment thickness','SOLIDIFY');mod.thickness=solid
    return o


def garment(name, rings, material, bone='spine', opening=.53, sleeve=False):
    verts=[];uvs=[];steps=40
    cols=steps if sleeve else steps+1
    for i,(cx,cy,z,rx,ry) in enumerate(rings):
        for j in range(cols):
            u=j/steps
            theta=u*math.tau if sleeve else opening+u*(math.tau-2*opening)
            # A small, low-frequency fold breaks the perfect cylindrical silhouette.
            fold=1+.018*math.sin(theta*5+i*.8)
            verts.append((cx+rx*math.sin(theta)*fold,cy-ry*math.cos(theta)*fold,z))
            uvs.append((u,i/(len(rings)-1)))
    faces=[]
    for i in range(len(rings)-1):
        for j in range(steps):
            k=(j+1)%cols
            faces.append((i*cols+j,i*cols+k,(i+1)*cols+k,(i+1)*cols+j))
    return surface(name,verts,faces,material,bone,uvs,.03)


def cardigan_edge(sign):
    return [(sign*rx*math.sin(.53),cy-ry*math.cos(.53)-.015,z) for cx,cy,z,rx,ry in card_rings]


# Front faces negative Y. Approx. three head heights including ears.
ball('Body under clothes',(0,0,1.78),(.49,.25,.69),hood)
for side, sign in [('L',1),('R',-1)]:
    x=sign*.32
    ball('Striped leg.'+side,(x,.02,.57),(.235,.25,.57),silver,'leg.'+side)
    ball('Cream foot.'+side,(x,-.13,.17),(.26,.35,.17),cream,'leg.'+side)
    for k in [-1,0,1]:
        tube('Toe seam',[(x+k*.10,-.449,.13),(x+k*.10,-.45,.21)],.008,rib,'leg.'+side)
# An open, curved garment shell wraps continuously around the back.
card_rings=[(0,.02,1.00,.62,.40),(0,.02,1.06,.65,.42),
            (0,.02,1.22,.65,.425),(0,.02,1.60,.63,.41),
            (0,.02,1.95,.60,.38),(0,.02,2.20,.62,.35),
            (0,.02,2.37,.52,.29),(0,.02,2.46,.36,.245)]
garment('Soft open cardigan',card_rings,knit)
garment('Continuous ribbed cardigan hem',[(0,.02,1.00,.625,.405),(0,.02,1.03,.65,.425),
        (0,.02,1.12,.65,.425),(0,.02,1.15,.645,.42)],rib)
for side,sign in [('L',1),('R',-1)]:
    tube('Soft cardigan edging.'+side,cardigan_edge(sign),.032,rib)
    sleeve=[(sign*.61,0,2.42,.065,.10),(sign*.69,0,2.35,.20,.235),
            (sign*.77,.015,2.18,.245,.26),(sign*.80,.005,1.91,.235,.25),
            (sign*.82,-.01,1.62,.215,.23),(sign*.83,-.02,1.43,.20,.215),
            (sign*.84,-.02,1.37,.205,.218),(sign*.84,-.02,1.34,.185,.20),
            (sign*.85,-.035,1.25,.175,.185)]
    garment('Tapered knit sleeve.'+side,sleeve,knit,'arm.'+side,sleeve=True)
    garment('Rib cuff.'+side,[(sign*.85,-.035,1.15,.17,.18),(sign*.85,-.035,1.18,.18,.19),
            (sign*.85,-.035,1.29,.18,.19),(sign*.85,-.035,1.32,.175,.185)],rib,'arm.'+side,sleeve=True)
    ball('Cream hand.'+side,(sign*.85,-.06,1.045),(.15,.18,.20),cream,'arm.'+side)
    ball('Thumb.'+side,(sign*.75,-.17,1.07),(.075,.09,.115),cream,'arm.'+side)
    # Curved pocket welts follow the garment rather than flat cube flaps.
    tube('Pocket welt.'+side,[(sign*.39,-.365,1.51),(sign*.48,-.31,1.52),(sign*.57,-.23,1.54)],.018,rib)
    # Distinct charcoal zip hoodie panels show through the open cardigan.
    verts=[]
    for z,inner,outer in [(1.08,.19,.35),(1.40,.20,.35),(1.80,.21,.35),(2.16,.22,.34),(2.38,.27,.32)]:
        verts.extend([(sign*inner,-.393,z),(sign*outer,-.255,z)])
    surface('Charcoal hoodie front.'+side,verts,[(0,1,3,2),(2,3,5,4),(4,5,7,6),(6,7,9,8)],hood,
            uvs=[(j%2,j//2/4) for j in range(10)],solid=.025)
    tube('Hoodie zipper tape.'+side,[(sign*.19,-.42,1.09),(sign*.20,-.43,1.70),(sign*.23,-.43,2.30)],.022,hood)
    for i in range(22):
        z=1.10+i*.052
        ball('Hoodie zipper tooth',(sign*(.19+.03*(z-1.1)),-.447,z),(.009,.009,.012),graphic)
    tube('Hoodie drawstring.'+side,[(sign*.29,-.40,2.42),(sign*.33,-.46,2.08),(sign*.31,-.45,1.72)],.014,graphic)
    ball('Drawstring metal end',(sign*.31,-.45,1.70),(.018,.018,.045),black)
# A shallow chest patch, with a curved crew neck cutout and no oval bulge.
verts=[];faces=[]
for i in range(7):
    t=i/6
    for j in range(13):
        x=-.36+j*.06
        top=2.23+.12*(abs(x)/.36)**2
        verts.append((x,-.39+.045*(x/.36)**2,1.10+t*(top-1.10)))
for i in range(6):
    for j in range(12):
        q=i*13+j;faces.append((q,q+1,q+14,q+13))
surface('Flat black crew tee',verts,faces,black,solid=.015)
tube('Crew neckline',[(-.30,-.36,2.33),(-.17,-.388,2.26),(0,-.40,2.23),(.17,-.388,2.26),(.30,-.36,2.33)],.022,black)
# Many irregular tapered paint dashes suggest a broken chevron, not tubular V lines.
for row in range(3):
    for sign in [-1,1]:
        for j in range(10):
            t=j/9; x=sign*(.22*(1-t)+random.uniform(-.015,.015))
            z=1.91-row*.17-.23*t+random.uniform(-.026,.026)
            w=random.uniform(.012,.031);h=random.uniform(.018,.055)
            vs=[(x-w,-.414,z-h),(x+w*.4,-.415,z-h*.3),(x+w,-.414,z+h),(x-w*.35,-.414,z+h*.5)]
            surface('Dry brush chevron fleck',vs,[(0,1,2,3)],graphic,subdivision=0)
# The dropped hood is a large cupped fabric shell behind the neck.
hood_rings=[(0,.28,1.82,.06,.05),(0,.32,1.92,.32,.18),(0,.35,2.12,.53,.30),
            (0,.30,2.38,.59,.33),(0,.22,2.55,.50,.29),(0,.20,2.58,.47,.27)]
garment('Large bunched hood down',hood_rings,hood,opening=.95)
tube('Hood rolled rim',[(-.46,-.02,2.50),(-.48,.34,2.58),(0,.53,2.55),(.48,.34,2.58),(.46,-.02,2.50)],.065,hood)
tube('Hood back fold',[(-.37,.59,2.36),(0,.65,2.10),(.37,.59,2.36)],.025,hood)
ball('Neck',(0,0,2.54),(.27,.24,.28),cream)
# A continuous head/muzzle surface removes the separate face-mask outline.
head_obj=ball('Round tabby head',(0,0,3.10),(.79,.54,.67),silver,'head')
muzzle_obj=ball('Muzzle fusion volume',(0,-.46,2.87),(.46,.16,.26),silver,'head')
parts[:]=[(o,bn) for o,bn in parts if o not in (head_obj,muzzle_obj)]
bpy.ops.object.select_all(action='DESELECT')
head_obj.select_set(True);muzzle_obj.select_set(True);bpy.context.view_layer.objects.active=head_obj
bpy.ops.object.join()
bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
remesh=head_obj.modifiers.new('Continuous rounded muzzle','REMESH');remesh.mode='VOXEL';remesh.voxel_size=.022
bpy.ops.object.modifier_apply(modifier=remesh.name)
smooth=head_obj.modifiers.new('Blend jowls into cheeks','SMOOTH');smooth.factor=.65;smooth.iterations=7
bpy.ops.object.modifier_apply(modifier=smooth.name)
for face in head_obj.data.polygons: face.use_smooth=True
parts.append((head_obj,'head'))
face_mat=silver.copy();face_mat.name='Silver head with feathered cream and soft painted tabby'
n,l=face_mat.node_tree.nodes,face_mat.node_tree.links;b=n['Principled BSDF']
ink=n.new('ShaderNodeAttribute');ink.attribute_name='face_ink'
mix=n.new('ShaderNodeMixRGB');mix.inputs[1].default_value=(.34,.34,.365,1);mix.inputs[2].default_value=(.19,.195,.215,1)
l.new(ink.outputs['Fac'],mix.inputs[0])
mask=n.new('ShaderNodeAttribute');mask.attribute_name='cream_mask'
blend=n.new('ShaderNodeMixRGB');blend.inputs[2].default_value=(.68,.63,.54,1)
l.new(mix.outputs[0],blend.inputs[1]);l.new(mask.outputs['Fac'],blend.inputs[0]);l.new(blend.outputs[0],b.inputs['Base Color'])
head_obj.data.materials.clear();head_obj.data.materials.append(face_mat)
cream_attr=head_obj.data.attributes.new('cream_mask','FLOAT','POINT')
ink_attr=head_obj.data.attributes.new('face_ink','FLOAT','POINT')
mark_paths=[([(-.28,3.43),(-.19,3.58),(-.11,3.39),(0,3.52),(.11,3.39),(.19,3.58),(.28,3.43)],.025)]
for sign in [-1,1]:
    mark_paths.extend([([(sign*.42,3.09),(sign*.58,3.045),(sign*.74,3.10)],.032),
                       ([(sign*.44,2.97),(sign*.60,2.92),(sign*.73,2.96)],.036)])
def line_distance_sq(x,z,points):
    best=100
    for (ax,az),(bx,bz) in zip(points,points[1:]):
        dx,dz=bx-ax,bz-az
        t=max(0,min(1,((x-ax)*dx+(z-az)*dz)/(dx*dx+dz*dz)))
        best=min(best,(x-ax-t*dx)**2+(z-az-t*dz)**2)
    return best
for vertex in head_obj.data.vertices:
    x,y,z=vertex.co
    front=max(0,min(1,(-y-.20)/.19))
    cream_attr.data[vertex.index].value=front*math.exp(-((x/.45)**4+((z-2.79)/.34)**4))
    paint_front=max(0,min(1,(-y-.08)/.22))
    paint=max(math.exp(-line_distance_sq(x,z,pts)/(width*width*2)) for pts,width in mark_paths)*paint_front*.90
    if y>.15:
        # Much softer broken bands on the short fur at the rear of the head.
        paint=max(paint,.22*math.exp(-((z-3.10-.025*math.sin(x*16))/.065)**2))
    ink_attr.data[vertex.index].value=paint
for sign in [-1,1]:
    for i,(z,reach,width) in enumerate([(3.03,.86,.075),(2.89,.81,.060)]):
        lock('Uneven cheek fluff',[(sign*.62,-.19,z+.015),(sign*.74,-.18,z-.01),
             (sign*reach,-.12,z+(-.005 if i==0 else -.025))],
             [width,width*.60,.001],face_mat,aspect=.85)
for side, sign in [('L',1),('R',-1)]:
    lock('Outer ear.'+side,[(sign*.53,.01,3.48),(sign*.65,.015,3.82),(sign*.70,.02,4.05)],[.29,.20,.012],silver,'ear.'+side)
    lock('Pink ear inset.'+side,[(sign*.54,-.105,3.56),(sign*.65,-.09,3.82),(sign*.69,-.025,3.98)],[.17,.12,.005],pink,'ear.'+side)
    x=sign*.32
    ball('Eye ivory.'+side,(x,-.495,3.13),(.252,.09,.185),white,'head')
    ball('Amber iris.'+side,(x,-.575,3.105),(.112,.033,.126),amber,'head')
    ball('Pupil.'+side,(x,-.602,3.11),(.045,.016,.09),black,'head')
    ball('Eye glint.'+side,(x-.025,-.619,3.16),(.026,.009,.03),shine,'head')
    lid=ball('Sleepy upper eyelid.'+side,(x,-.55,3.255),(.26,.085,.108),silver,'head')
    lid.shape_key_add(name='Basis')
    key=lid.shape_key_add(name='Blink')
    for v in key.data: v.co.z=v.co.z*1.65-1.1
    for f,val in [(1,0),(19,0),(21,1),(23,0),(49,0)]:
        key.value=val; key.keyframe_insert('value',frame=f)
    tube('Upper lash.'+side,[(x-.23,-.603,3.22),(x,-.63,3.23),(x+.23,-.603,3.22)],.019,black,'head')
    # Rounded rectangular glasses, empty lenses keep the amber eyes legible.
    pts=[(x-.23,-.66,3.28),(x+.21,-.66,3.28),(x+.25,-.66,3.24),(x+.22,-.665,3.015),(x+.18,-.665,2.99),(x-.19,-.665,2.99),(x-.23,-.665,3.02),(x-.255,-.66,3.24)]
    tube('Glasses frame.'+side,pts,.029,black,'head',True)
    tube('Glasses temple.'+side,[(sign*.58,-.64,3.25),(sign*.75,-.23,3.28),(sign*.69,.17,3.20)],.024,black,'head')
tube('Glasses bridge',[(-.075,-.67,3.20),(0,-.69,3.235),(.075,-.67,3.20)],.024,black,'head')
ball('Pink nose',(0,-.647,2.965),(.075,.036,.048),pink,'head')
tube('Cat mouth',[(-.13,-.607,2.855),(-.065,-.635,2.84),(0,-.646,2.88),(.065,-.635,2.84),(.13,-.607,2.855)],.012,black,'head')
hair_base=mat('Crown silver root undercoat',(.22,.235,.255))
ball('Crown-only hair foundation',(0,.06,3.66),(.61,.39,.24),hair_base,'head')
bangs=[
    ([(.16,-.10,3.73),(-.05,-.38,3.82),(-.34,-.53,3.63),(-.54,-.55,3.40),(-.68,-.43,3.27)],[.07,.18,.20,.12,.002]),
    ([(.20,-.12,3.75),(.07,-.41,3.77),(-.13,-.57,3.56),(-.25,-.59,3.31),(-.31,-.55,3.24)],[.06,.17,.18,.10,.002]),
    ([(.27,-.08,3.72),(.30,-.39,3.77),(.19,-.56,3.54),(.08,-.60,3.28),(.04,-.57,3.23)],[.08,.18,.16,.085,.002]),
    ([(.28,-.02,3.72),(.51,-.29,3.75),(.57,-.47,3.53),(.63,-.50,3.32),(.73,-.38,3.22)],[.07,.19,.17,.10,.002]),
    ([(-.06,-.05,3.75),(-.30,-.27,3.78),(-.56,-.41,3.54),(-.74,-.32,3.35),(-.84,-.22,3.33)],[.09,.18,.17,.09,.002]),
    ([(.39,.06,3.64),(.65,-.14,3.62),(.73,-.31,3.40),(.79,-.24,3.16)],[.09,.20,.15,.002])]
for i,(pts,widths) in enumerate(bangs):
    lock('Large swept bang %02d'%i,pts,widths,hair_variants[i])
for i in range(6):
    x=-.38+i*.14
    lock('Messy crown sweep %02d'%i,[(x+.18,.16,3.57),(x+.12,.06,3.86),
         (x-.13,-.03,3.94+random.uniform(-.07,.07)),(x-.30,-.07,3.84+random.uniform(-.08,.03))],
         [.10,.16,.105,.002],hair_variants[(i+2)%6])
for i in range(5):
    phi=-1.35+i*.675
    points=[]
    for j,lat in enumerate([.25,.63,.98,1.27+random.uniform(-.10,.12)]):
        angle=phi+.20*j/3
        points.append((.73*math.sin(lat)*math.sin(angle),.07+.49*math.sin(lat)*math.cos(angle),3.25+.59*math.cos(lat)))
    lock('Short rear crown tuft %02d'%i,points,[.06,.16,.13,.002],hair_variants[(i+1)%6])
# Headphones visibly separate from the clothing.
tube('Headphones neck band',[(-.46,-.22,2.40),(-.43,.18,2.56),(0,.35,2.60),(.43,.18,2.56),(.46,-.22,2.40)],.055,black)
for sign in [-1,1]:
    ball('Headphone cushion',(sign*.44,-.36,2.38),(.16,.15,.24),black)
    ball('Headphone earcup',(sign*.47,-.47,2.38),(.135,.065,.20),hood)
    tube('Headphone trim',[(sign*.47+.09*math.cos(t*math.tau/16),-.535,2.38+.15*math.sin(t*math.tau/16)) for t in range(16)],.012,graphic,cyclic=True)
tube('Headphone cable',[(-.43,-.49,2.23),(-.36,-.51,1.75),(-.19,-.46,.94),(.10,-.44,.87),(.22,-.43,1.48)],.013,black)
# One round, tapering tail loft; the cream tip shares its continuous topology.
tailpts=[(0,.30,1.10),(.24,.49,.91),(.58,.56,.70),(.90,.54,.74),
         (1.10,.47,.95),(1.16,.40,1.19),(1.14,.35,1.35),(1.08,.33,1.43)]
tail_mesh=lock('Continuous fluffy striped tail',tailpts,[.14,.17,.18,.18,.16,.13,.075,.003],silver,'tail.0',aspect=1)
tail_mesh.data.materials.append(cream)
for face in tail_mesh.data.polygons:
    if face.index>=5*12: face.material_index=1

for i in range(7):
    ang=i*math.tau/7
    dx=.055*math.cos(ang);dy=.055*math.sin(ang)
    lock('Tapered cream tail tuft',[(1.15+dx,.39+dy,1.22),(1.14+dx,.35+dy,1.35),
         (1.08+dx*.5,.33+dy*.5,1.45+random.uniform(-.02,.035))],[.025,.022,.001],cream,'tail.2',aspect=1)

# Apply the same proportional remap to geometry and rest bones, preserving facial design.
HEAD_SCALE=1.23
TORSO_SCALE=.83
HEAD_PIVOT=1+(2.5-1)*TORSO_SCALE
head_map=Matrix.Translation((0,0,HEAD_PIVOT)) @ Matrix.Scale(HEAD_SCALE,4) @ Matrix.Translation((0,0,-2.5))
body_map=Matrix.Translation((0,0,1)) @ Matrix.Diagonal((.95,1,TORSO_SCALE,1)) @ Matrix.Translation((0,0,-1))
def rest_point(pt,bn):
    m=head_map if bn=='head' or bn.startswith('ear.') else body_map if bn=='spine' or bn.startswith('arm.') else Matrix.Identity(4)
    return m @ Vector(pt)
bpy.context.view_layer.update()
for o,bn in parts:
    if bn=='head' or bn.startswith('ear.'): o.matrix_world=head_map @ o.matrix_world
    elif bn=='spine' or bn.startswith('arm.'): o.matrix_world=body_map @ o.matrix_world
# Armature and per-part rigid weights via armature modifiers.
arm=bpy.data.armatures.new('Persona skeleton')
rig=bpy.data.objects.new('Cat persona rig',arm); s.collection.objects.link(rig)
bpy.context.view_layer.objects.active=rig; rig.select_set(True)
bpy.ops.object.mode_set(mode='EDIT')
def bone(name,head,tail,parent=None):
    b=arm.edit_bones.new(name); b.head=rest_point(head,name); b.tail=rest_point(tail,name)
    if parent: b.parent=arm.edit_bones[parent]
bone('root',(0,0,0),(0,0,.4))
bone('spine',(0,0,1.1),(0,0,2.5),'root')
bone('head',(0,0,2.5),(0,0,3.6),'spine')
for side,sign in [('L',1),('R',-1)]:
    bone('ear.'+side,(sign*.53,0,3.48),(sign*.70,0,4.05),'head')
    bone('arm.'+side,(sign*.64,0,2.2),(sign*.86,0,1.0),'spine')
    bone('leg.'+side,(sign*.32,0,1),(sign*.32,0,.15),'root')
for i in range(3): bone('tail.%d'%i,tailpts[i*2],tailpts[min(i*2+2,len(tailpts)-1)],'root' if i==0 else 'tail.%d'%(i-1))
bpy.ops.object.mode_set(mode='OBJECT')
for o,bn in parts:
    # Convert curves before assigning vertex groups; bake world coordinates.
    bpy.ops.object.select_all(action='DESELECT'); o.select_set(True); bpy.context.view_layer.objects.active=o
    if o.type=='CURVE': bpy.ops.object.convert(target='MESH')
    bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
    if o==tail_mesh:
        groups=[o.vertex_groups.new(name='tail.%d'%i) for i in range(3)]
        for v in o.data.vertices:
            t=max(0,min(2,v.co.x*2.5))
            lo=min(1,int(t)); frac=t-lo
            groups[lo].add([v.index],1-frac,'REPLACE'); groups[lo+1].add([v.index],frac,'REPLACE')
    else:
        vg=o.vertex_groups.new(name=bn); vg.add(list(range(len(o.data.vertices))),1,'REPLACE')
    mod=o.modifiers.new('Persona rigid part rig','ARMATURE'); mod.object=rig
for f in range(1,50):
    phase=(f-1)*math.tau/48
    for bn in ['spine','head','tail.0','tail.1','tail.2']:
        b=rig.pose.bones[bn]; b.rotation_mode='XYZ'
        if bn=='spine':
            b.scale=(1+math.sin(phase)*.009,1+math.sin(phase)*.012,1+math.sin(phase)*.009)
            b.keyframe_insert('scale',frame=f)
        else:
            b.rotation_euler=(0,.035*math.sin(phase),.025*math.sin(phase)) if bn=='head' else (0,.13*math.sin(phase-int(bn[-1])*.4),.10*math.sin(phase))
            b.keyframe_insert('rotation_euler',frame=f)
s.frame_set(1)
# Floor and curved studio sweep.
floor=mat('Neutral gray sweep',(.26,.27,.29))
profile=[(-12,0),(2,0),(3,.15),(4,.6),(4.7,1.4),(5,2.5),(5,8)]
verts=[(x,y,z) for x in [-20,20] for y,z in profile]
n=len(profile); faces=[(i,i+1,n+i+1,n+i) for i in range(n-1)]
me=bpy.data.meshes.new('Sweep'); me.from_pydata(verts,[],faces); me.update()
o=bpy.data.objects.new('Studio cyclorama',me); s.collection.objects.link(o); register(o,o.name,floor,None)
sweep=o
sub=o.modifiers.new('Sweep smooth','SUBSURF'); sub.levels=2
world=bpy.data.worlds.new('Studio ambient'); s.world=world; world.use_nodes=True
world.node_tree.nodes['Background'].inputs[0].default_value=(.24,.26,.31,1)
world.node_tree.nodes['Background'].inputs[1].default_value=.3

def area(name,loc,power,color,size):
    d=bpy.data.lights.new(name,'AREA'); d.energy=power; d.color=color; d.shape='DISK'; d.size=size
    o=bpy.data.objects.new(name,d); s.collection.objects.link(o); o.location=loc
    o.rotation_euler=(Vector((0,0,2))-o.location).to_track_quat('-Z','Y').to_euler()
area('Key',(-3,-4,7),500,(1,.88,.77),4)
area('Fill',(4,-2,4),280,(.75,.85,1),3)
area('Rim',(1,3,6),650,(1,.88,.74),3)
if a.backdrop=='dusk':
    # Camera-space city blocks share a ground plane, with a street receding behind the cat.
    sweep.hide_render=True
    street=mat('Dusk street asphalt',(.035,.038,.055))
    buildings=mat('Dusk blue charcoal buildings',(.022,.026,.049))
    pavement=mat('Dusk pavement',(.065,.06,.075))
    sky=bpy.data.materials.new('Purple to orange luminous sky');sky.use_nodes=True
    n,l=sky.node_tree.nodes,sky.node_tree.links;n.clear()
    tex=n.new('ShaderNodeTexCoord');sep=n.new('ShaderNodeSeparateXYZ');ramp=n.new('ShaderNodeValToRGB')
    l.new(tex.outputs['Generated'],sep.inputs[0]);l.new(sep.outputs['Z'],ramp.inputs[0])
    ramp.color_ramp.elements[0].color=(.48,.16,.055,1)
    ramp.color_ramp.elements[1].position=.50;ramp.color_ramp.elements[1].color=(.035,.014,.13,1)
    mid=ramp.color_ramp.elements.new(.19);mid.color=(.18,.065,.16,1)
    em=n.new('ShaderNodeEmission');l.new(ramp.outputs['Color'],em.inputs['Color'])
    output=n.new('ShaderNodeOutputMaterial');l.new(em.outputs[0],output.inputs['Surface'])
    def city_point(u,v,z):
        angle=math.radians(18)
        return (u*math.cos(angle)-v*math.sin(angle),u*math.sin(angle)+v*math.cos(angle),z)
    def block(name,u,v,width,depth,height,material,base=0):
        bpy.ops.mesh.primitive_cube_add(size=2,location=city_point(u,v,base+height/2))
        o=bpy.context.object;o.scale=(width/2,depth/2,height/2);o.rotation_euler.z=math.radians(18)
        return register(o,name,material,None)
    block('Continuous ground and street',0,0,100,100,.08,street,base=-.10)
    for sign in [-1,1]:
        block('Raised sidewalk',sign*4,8,4,24,.10,pavement)
    block('Luminous distant sky',0,27,90,.10,24,sky)
    light_mats=[]
    for name,color,energy in [('Warm amber',(1,.40,.08),5),('Warm white',(1,.70,.36),4),('Cool blue',(.20,.43,1),3)]:
        m=mat(name+' city lights',color)
        b=m.node_tree.nodes['Principled BSDF'];b.inputs['Emission Color'].default_value=(*color,1)
        b.inputs['Emission Strength'].default_value=energy;light_mats.append(m)
    for sign in [-1,1]:
        for row in range(6):
            u=sign*random.uniform(2.6,4.4);v=4.4+row*2.15
            width=random.uniform(.9,1.7);depth=random.uniform(.8,1.5);height=random.uniform(3.4,7.2)
            block('Grounded city building',u,v,width,depth,height,buildings)
            for col in range(4):
                for level in range(int(height/.42)-1):
                    if random.random()<.35:continue
                    x=u+(col-1.5)*width/4
                    z=.45+level*.42
                    m=light_mats[2 if random.random()<.15 else random.randrange(2)]
                    radius=random.uniform(.025,.045)
                    ball('Distant glowing window',city_point(x,v-depth/2-.025,z),(radius,radius,radius),m,None)
            # Street lamps recede along both sidewalks.
            u=sign*1.92;v=3.5+row*2.2
            tube('Streetlamp pole',[city_point(u,v,0),city_point(u,v,2.4)],.022,buildings,None)
            tube('Streetlamp arm',[city_point(u,v,2.4),city_point(u-sign*.20,v,2.48)],.025,buildings,None)
            ball('Warm streetlamp bokeh',city_point(u-sign*.20,v,2.46),(.07,.07,.07),light_mats[0],None)
    for i in range(9):
        u=-6+i*1.5;v=21;height=random.uniform(3.5,8)
        block('Distant skyline',u,v,1.1,1,height,buildings)
    world.node_tree.nodes['Background'].inputs[0].default_value=(.065,.045,.14,1)
    world.node_tree.nodes['Background'].inputs[1].default_value=.25
d=bpy.data.cameras.new('Portrait camera'); cam=bpy.data.objects.new('Portrait camera',d); s.collection.objects.link(cam); s.camera=cam
d.type='ORTHO'; d.ortho_scale=4.8
if a.backdrop=='dusk':
    d.type='PERSP';d.lens=80
    d.dof.use_dof=True;d.dof.aperture_fstop=.45;d.dof.aperture_blades=8

def view(angle):
    sweep.rotation_euler.z=angle
    r=10.5 if a.backdrop=='dusk' else 9
    cam.location=(r*math.sin(angle),-r*math.cos(angle),3.05)
    target=Vector((0,0,2.05)); cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler()
    face=Vector((0,-.70,3.0))
    forward=(target-cam.location).normalized()
    d.dof.focus_distance=(face-cam.location).dot(forward)
view(math.radians(18))
metadata={'blender_version':bpy.app.version_string,'backend':backend,'preview':preview,'resolution':[s.render.resolution_x,s.render.resolution_y],'samples':samples,'backdrop':a.backdrop,'fps':24,'loop_period_frames':48,'revision':'feedback-2','head_scale':HEAD_SCALE,'torso_scale':TORSO_SCALE,'renders':[]}
def render(path):
    s.render.filepath=str(path); t=time.perf_counter(); bpy.ops.render.render(write_still=True)
    metadata['renders'].append({'file':str(path.relative_to(out)),'frame':s.frame_current,'seconds':round(time.perf_counter()-t,3)})
    (out/'render-metadata.json').write_text(json.dumps(metadata,indent=2)+'\n')
if a.save_blend: bpy.ops.wm.save_as_mainfile(filepath=str(out/'cat-persona.blend'))
if a.stills:
    for name,angle in [('front',0),('three_quarter',35),('side',90),('back',180)]:
        view(math.radians(angle)); render(out/(name+'.png'))
elif not a.idle: render(out/('dusk.png' if a.backdrop=='dusk' else 'three_quarter.png'))
if a.idle:
    view(math.radians(18)); (out/'frames').mkdir(exist_ok=True)
    first,last=map(int,a.frames.split('-'))
    if not 1<=first<=last<=48: raise ValueError('--frames must be an inclusive range within 1-48')
    for f in range(first,last+1): s.frame_set(f); render(out/'frames'/('%04d.png'%f))
