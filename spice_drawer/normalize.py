"""Weld sub-micron CAD slivers in generated binary STLs, with topology guards.

Five decimal places = 0.00001 mm, far below the designed 0.30 mm seam gap.
Never use this to compensate for a genuinely open or intersecting model.
"""
import argparse
import math
from pathlib import Path
import struct

from .mesh import verify


def normalize(path):
    raw = path.read_bytes()
    count, = struct.unpack_from('<I', raw, 80)
    assert len(raw) == 84+count*50, 'Expected a binary STL'
    vertices, lookup, faces = [], {}, []
    removed = 0
    for i in range(count):
        record = struct.unpack_from('<12fH', raw, 84+50*i)
        face = []
        for j in range(3):
            original = record[3+3*j:6+3*j]
            v = tuple(round(x, 5) for x in original)
            assert max(abs(a-b) for a,b in zip(original,v)) <= 0.0000051
            if v not in lookup:
                lookup[v] = len(vertices)
                vertices.append(v)
            face.append(lookup[v])
        if len(set(face)) < 3:
            removed += 1
        else:
            faces.append(face)
    # Remove vertices used only by collapsed faces before counting components.
    used = sorted({v for f in faces for v in f})
    remap = {old:new for new,old in enumerate(used)}
    vertices = [vertices[i] for i in used]
    faces = [[remap[i] for i in f] for f in faces]
    result = verify(vertices, faces)
    assert abs(result['bounds_mm'][2][0]) < 0.0001
    assert removed < count*0.01, 'Too many collapsed faces: inspect CAD geometry'
    output = bytearray(b'Submicron-welded OpenSCAD export'.ljust(80, b' '))
    output.extend(struct.pack('<I', len(faces)))
    for face in faces:
        a,b,c = [vertices[i] for i in face]
        u = [b[i]-a[i] for i in range(3)]
        v = [c[i]-a[i] for i in range(3)]
        n = [u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]]
        length = math.sqrt(sum(x*x for x in n))
        assert length > 0, 'Collinear face: inspect CAD geometry'
        output.extend(struct.pack('<12fH', *[x/length for x in n], *a, *b, *c, 0))
    # Validate the float32 round-trip before replacing this generated export.
    # In-memory round-trip uses the same vertex tolerance as the independent QA.
    decoded = [tuple(round(struct.unpack('<f',struct.pack('<f',x))[0],5)
                     for x in v) for v in vertices]
    assert len(set(decoded)) == len(decoded), 'Float32 precision merged vertices'
    verify(decoded,faces)
    path.write_bytes(output)
    print(path.name, f'{removed} sub-micron faces collapsed;', result)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stl', type=Path, nargs='+')
    for item in parser.parse_args().stl:
        normalize(item)
