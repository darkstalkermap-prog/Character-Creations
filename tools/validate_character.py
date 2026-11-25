"""Validate portable asset data, including animation channels and normalized skin weights."""
from pathlib import Path
import json,struct,math,hashlib
root=Path(__file__).resolve().parents[1]
p=root/'characters/giantborn-wanderer/exports/wanderer.glb'
b=p.read_bytes()
magic,version,length=struct.unpack_from('<4sII',b)
assert magic==b'glTF' and version==2 and length==len(b)
n=struct.unpack_from('<I',b,12)[0];d=json.loads(b[20:20+n])
bin_start=20+n+8
def values(index):
    a=d['accessors'][index];v=d['bufferViews'][a['bufferView']]
    count={'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4,'MAT4':16}[a['type']]
    fmt={5126:'f',5125:'I',5123:'H',5121:'B'}[a['componentType']]
    size=struct.calcsize('<'+fmt)*count
    start=bin_start+v.get('byteOffset',0)+a.get('byteOffset',0)
    for i in range(a['count']):yield struct.unpack_from('<'+fmt*count,b,start+i*v.get('byteStride',size))
animations=[a['name'] for a in d.get('animations',[])]
assert len(animations)==28,animations
for a in d['animations']:
    for s in a['samplers']:
        ts=[x[0] for x in values(s['input'])]
        assert all(t2>t1 for t1,t2 in zip(ts,ts[1:])),a['name']
        assert all(math.isfinite(v) for row in values(s['output']) for v in row)
vertices=0
for mesh in d['meshes']:
    for primitive in mesh['primitives']:
        attrs=primitive['attributes'];vertices+=d['accessors'][attrs['POSITION']]['count']
        assert 'COLOR_0' not in attrs,'Game mask exported as display colour'
        for row in values(attrs['POSITION']):assert all(math.isfinite(v) for v in row)
        if 'WEIGHTS_0' in attrs:
            for row in values(attrs['WEIGHTS_0']):assert abs(sum(row)-1)<.002
assert len(d['skins'][0]['joints'])==71
report={'status':'passed','vertices':vertices,'bones':71,'animations':animations,'materials':len(d['materials']),'embedded_images':len(d.get('images',[])),'sha256':hashlib.sha256(b).hexdigest(),'checks':['GLB structure','finite positions and animation values','increasing key times','normalized skin weights','71 bones','28 clips','no game masks used as vertex colours']}
(root/'characters/giantborn-wanderer/validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
