"""Check the exported model, combined animation, and loop endpoints."""
import json, struct, sys, math
from pathlib import Path
raw=Path(sys.argv[1]).read_bytes();magic,version,size=struct.unpack_from('<4sII',raw)
assert magic==b'glTF' and version==2 and size==len(raw)
json_size,json_type=struct.unpack_from('<II',raw,12);assert json_type==0x4E4F534A
g=json.loads(raw[20:20+json_size]);binary_start=20+json_size+8;binary=raw[binary_start:]
assert len(g.get('meshes',[]))>=20
assert len(g.get('animations',[]))==1
names={n.get('name') for n in g['nodes']}
for n in ['Sleeping head','Left long black-tipped ear','Right long black-tipped ear','Lightning bolt tail','Left closed eyelid','Right closed eyelid']:
 assert n in names,n

def values(index):
 a=g['accessors'][index];v=g['bufferViews'][a['bufferView']];assert a['componentType']==5126
 count={'SCALAR':1,'VEC3':3,'VEC4':4}[a['type']];offset=v.get('byteOffset',0)+a.get('byteOffset',0);stride=v.get('byteStride',count*4)
 return [struct.unpack_from('<'+'f'*count,binary,offset+i*stride) for i in range(a['count'])]
anim=g['animations'][0];durations=[]
for sampler in anim['samplers']:
 times=values(sampler['input']);durations.append(times[-1][0]-times[0][0]);poses=values(sampler['output']);first,last=poses[0],poses[-1]
 err=min(max(abs(x-y) for x,y in zip(first,last)),max(abs(x+y) for x,y in zip(first,last))) if len(first)==4 else max(abs(x-y) for x,y in zip(first,last))
 assert err<1e-4,('Loop gap',err)
assert abs(max(durations)-5)<1e-4,durations
print(json.dumps(dict(meshes=len(g['meshes']),animations=len(g['animations']),channels=len(anim['channels']),duration_seconds=max(durations),loop_endpoints_match=True),indent=2))
