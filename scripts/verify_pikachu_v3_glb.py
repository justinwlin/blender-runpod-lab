"""Check the v3 GLB: skinned rig, named parts, one animation, 4.5 s loop, matching endpoints."""
import json, struct, sys
from pathlib import Path

raw = Path(sys.argv[1]).read_bytes()
magic, version, size = struct.unpack_from('<4sII', raw)
assert magic == b'glTF' and version == 2 and size == len(raw)
json_size, json_type = struct.unpack_from('<II', raw, 12)
assert json_type == 0x4E4F534A
g = json.loads(raw[20:20 + json_size])
binary = raw[20 + json_size + 8:]
names = {n.get('name') for n in g['nodes']}
for n in ['Pikachu body', 'Lightning tail', 'Near eye closed', 'Far eye closed', 'ear.near', 'ear.far',
          'Sleep bubble', 'Poke Ball shell', 'Ball roll', 'head', 'tail']:
    assert n in names, n
assert len(g.get('skins', [])) == 1, 'expected one skinned rig'
assert any('COLOR_0' in pr['attributes'] for m in g['meshes'] for pr in m['primitives']), 'painted vertex colors missing'
assert len(g.get('animations', [])) == 1, 'expected one combined animation'


def values(index):
    a = g['accessors'][index]
    v = g['bufferViews'][a['bufferView']]
    assert a['componentType'] == 5126
    count = {'SCALAR': 1, 'VEC3': 3, 'VEC4': 4}[a['type']]
    offset = v.get('byteOffset', 0) + a.get('byteOffset', 0)
    stride = v.get('byteStride', count * 4)
    return [struct.unpack_from('<' + 'f' * count, binary, offset + i * stride) for i in range(a['count'])]


anim = g['animations'][0]
durations, worst, moving = [], 0.0, 0
for ch in anim['channels']:
    sm = anim['samplers'][ch['sampler']]
    t = values(sm['input'])
    durations.append(t[-1][0] - t[0][0])
    out = values(sm['output'])
    first, last = out[0], out[-1]
    if len(first) == 4:
        err = min(max(abs(x - y) for x, y in zip(first, last)), max(abs(x + y) for x, y in zip(first, last)))
    else:
        err = max(abs(x - y) for x, y in zip(first, last))
    worst = max(worst, err)
    if max(max(abs(a - b) for a, b in zip(o, first)) for o in out) > 1e-3:
        moving += 1
assert worst < 1e-4, ('loop gap', worst)
assert abs(max(durations) - 4.5) < 1e-3, durations
assert moving >= 8, ('too few moving channels', moving)
print(json.dumps(dict(nodes=len(g['nodes']), meshes=len(g['meshes']), skins=len(g['skins']),
                      animations=1, channels=len(anim['channels']), moving_channels=moving,
                      duration_seconds=round(max(durations), 4), loop_endpoint_max_error=worst), indent=2))
