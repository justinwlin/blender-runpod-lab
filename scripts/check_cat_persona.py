"""Check saved persona proportions, skinning, blink and loop; render the closed-eye pose."""
import json
from pathlib import Path
import time

import bpy
from mathutils import Vector

s = bpy.context.scene
rig = bpy.data.objects['Cat persona rig']
result = {'bones': [b.name for b in rig.data.bones],
          'mesh_objects': len([o for o in s.objects if o.type == 'MESH']),
          'rigged_meshes': len([o for o in s.objects if any(m.type == 'ARMATURE' for m in o.modifiers)])}
poses = {}
for f in [1, 21, 49]:
    s.frame_set(f)
    bpy.context.view_layer.update()
    poses[f] = [list(v) for b in rig.pose.bones for v in b.matrix]
result['loop_max_matrix_error'] = max(abs(a-b) for va, vb in zip(poses[1], poses[49]) for a, b in zip(va, vb))
result['blink_at_49'] = {o.name: o.data.shape_keys.key_blocks['Blink'].value
                         for o in s.objects if o.type == 'MESH' and o.data.shape_keys}
s.frame_set(1)
bpy.context.view_layer.update()

def width(objects, zmin=None):
    if zmin is None:
        xs = [(o.matrix_world @ Vector(co)).x for o in objects for co in o.bound_box]
    else:
        xs=[]
        depsgraph=bpy.context.evaluated_depsgraph_get()
        for o in objects:
            evaluated=o.evaluated_get(depsgraph)
            mesh=evaluated.to_mesh()
            for v in mesh.vertices:
                co=evaluated.matrix_world @ v.co
                if co.z>=zmin: xs.append(co.x)
            evaluated.to_mesh_clear()
    return max(xs)-min(xs)

result['round_head_width'] = width([bpy.data.objects['Round tabby head']])
result['head_width'] = width([o for o in s.objects if o.name=='Round tabby head' or o.name.startswith('Uneven cheek fluff')])
result['sleeves_outer_width'] = width([bpy.data.objects['Tapered knit sleeve.'+side] for side in ['L', 'R']])
result['shoulders_width'] = width([bpy.data.objects['Tapered knit sleeve.'+side] for side in ['L','R']], zmin=1.83)
result['head_to_shoulders_width_ratio'] = result['head_width']/result['shoulders_width']
s.frame_set(21)
result['blink_at_21'] = {o.name: o.data.shape_keys.key_blocks['Blink'].value
                         for o in s.objects if o.type == 'MESH' and o.data.shape_keys}
assert result['loop_max_matrix_error'] < 1e-6
assert all(v == 1 for v in result['blink_at_21'].values())
assert all(v == 0 for v in result['blink_at_49'].values())
print('Proportions:', result['round_head_width'], result['head_width'], result['shoulders_width'])
assert result['head_to_shoulders_width_ratio'] >= .98
s.render.resolution_x = s.render.resolution_y = 480
s.render.filepath = 'results/cat-persona/blink-check.png'
t = time.perf_counter()
bpy.ops.render.render(write_still=True)
result['blink_render_seconds'] = round(time.perf_counter()-t, 3)
Path('results/cat-persona/rig-check.json').write_text(json.dumps(result, indent=2)+'\n')
print(json.dumps(result, indent=2))
