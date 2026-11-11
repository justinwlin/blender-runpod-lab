"""Reusable Blender contact views and ordinary-Python sheet assembly.

Render any saved scene: blender -b scene.blend --python scripts/contact_sheet.py -- --output DIR
Assemble locally: python3 scripts/contact_sheet.py --assemble DIR --concept IMAGE
"""
import argparse
import math
from pathlib import Path
import sys


def render_views(scene, output, render, target=(0, 0, 2.25), scale=5.2):
    from mathutils import Vector
    camera = scene.camera
    camera.data.type = 'ORTHO'
    camera.data.ortho_scale = scale
    for name, direction in [('front',(0,-1,.04)),('side',(1,0,.04)),
                            ('top',(0,-.001,1)),('three_quarter',(.57,-.82,.10))]:
        camera.location = Vector(target)+Vector(direction).normalized()*10
        camera.rotation_euler = (Vector(target)-camera.location).to_track_quat('-Z','Y').to_euler()
        render(Path(output)/(name+'.png'))


def assemble(folder, concept=None, size=320):
    from PIL import Image, ImageDraw
    folder = Path(folder)
    names = ['front','side','top','three_quarter']
    height = size+24+(int(size*4*9/16) if concept else 0)
    result = Image.new('RGB',(size*4,height),(55,55,58))
    draw = ImageDraw.Draw(result)
    for i,name in enumerate(names):
        with Image.open(folder/(name+'.png')) as im:
            result.paste(im.convert('RGB').resize((size,size)),(i*size,0))
        draw.text((i*size+8,size+6),name,fill='white')
    if concept:
        with Image.open(concept) as im:
            result.paste(im.convert('RGB').resize((size*4,height-size-24)),(0,size+24))
    result.save(folder/'contact.png',optimize=True)


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--assemble',type=Path)
    parser.add_argument('--output',type=Path,default=Path('contact'))
    parser.add_argument('--concept',type=Path)
    parser.add_argument('--size',type=int,default=240)
    parser.add_argument('--object',help='Object whose bounds determine framing in Blender')
    parser.add_argument('--res',type=int,default=640)
    args=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else sys.argv[1:])
    if args.assemble:
        assemble(args.assemble,args.concept,args.size)
    else:
        import bpy
        from mathutils import Vector
        scene=bpy.context.scene
        scene.render.resolution_x=scene.render.resolution_y=args.res
        scene.render.resolution_percentage=100
        args.output.mkdir(parents=True,exist_ok=True)
        target=(0,0,2.25);scale=5.2
        if args.object:
            obj=bpy.data.objects[args.object]
            corners=[obj.matrix_world@Vector(p) for p in obj.bound_box]
            lo=Vector(tuple(min(v[i] for v in corners) for i in range(3)))
            hi=Vector(tuple(max(v[i] for v in corners) for i in range(3)))
            target=(lo+hi)*.5;scale=max(hi-lo)*1.2
        def render(path):
            scene.render.filepath=str(path)
            bpy.ops.render.render(write_still=True)
        render_views(scene,args.output,render,target,scale)
