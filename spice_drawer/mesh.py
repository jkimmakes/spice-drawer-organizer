"""Read-only STL topology/bed checks; optionally check jar footprint coverage.

The reference is an assumed collision envelope, not a physical mass model.
Footprint containment does NOT prove the jar cannot pivot inside its cradle.
"""

import argparse
from collections import Counter
import json
import math
from pathlib import Path
import struct


def read_mesh(path):
    raw = Path(path).read_bytes()
    count, = struct.unpack_from('<I', raw, 80)
    assert len(raw) == 84 + count * 50, 'Expected binary STL'
    vertices, faces, lookup = [], [], {}
    for i in range(count):
        rec = struct.unpack_from('<12fH', raw, 84 + i * 50)
        face = []
        for j in range(3):
            v = tuple(round(x, 5) for x in rec[3 + j * 3:6 + j * 3])
            if v not in lookup:
                lookup[v] = len(vertices)
                vertices.append(v)
            face.append(lookup[v])
        assert len(set(face)) == 3, 'Degenerate triangle'
        faces.append(face)
    return vertices, faces


def verify(vertices, faces, expected_components=1, on_bed=True):
    edges, directed = Counter(), Counter()
    parent = list(range(len(vertices)))

    def root(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    volume = 0
    for face in faces:
        for a, b in zip(face, face[1:] + face[:1]):
            edges[tuple(sorted((a, b)))] += 1
            directed[a, b] += 1
            parent[root(a)] = root(b)
        a, b, c = [vertices[i] for i in face]
        cross = (b[1] * c[2] - b[2] * c[1],
                 b[2] * c[0] - b[0] * c[2],
                 b[0] * c[1] - b[1] * c[0])
        volume += sum(a[i] * cross[i] for i in range(3)) / 6
    assert all(n == 2 for n in edges.values()), 'Nonmanifold/open edge'
    assert all(directed[b, a] == n for (a, b), n in directed.items()), 'Winding'
    components = len({root(i) for i in parent})
    assert components == expected_components, (
        f'Expected {expected_components} components, got {components}')
    component_vertices = {}
    for i, vertex in enumerate(vertices):
        component_vertices.setdefault(root(i), []).append(vertex)
    assert volume > 0, 'Inverted or empty volume'
    bounds = [[min(v[k] for v in vertices), max(v[k] for v in vertices)]
              for k in range(3)]
    result = dict(triangles=len(faces), components=components, closed=True,
                consistent_winding=True, bounds_mm=bounds,
                size_mm=[round(b - a, 3) for a, b in bounds],
                solid_volume_cm3=round(volume / 1000, 3))
    if components > 1:
        result['component_min_z_mm'] = [min(v[2] for v in vs)
                                        for vs in component_vertices.values()]
        if on_bed:
            assert all(abs(z) < 0.0001 for z in result['component_min_z_mm']), (
                'Every printed component must rest at Z=0')
    return result


def cross2(a, b, c):
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])


def hull2(points):
    points = sorted(set(points))
    chains = []
    for seq in (points, reversed(points)):
        chain = []
        for p in seq:
            while len(chain) >= 2 and cross2(chain[-2], chain[-1], p) <= 0:
                chain.pop()
            chain.append(p)
        chains.append(chain[:-1])
    return chains[0] + chains[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stl')
    parser.add_argument('--reference', help='Posed jar STL, not the print part')
    parser.add_argument('--components', type=int, default=1)
    parser.add_argument('--reference-components', type=int, default=1)
    args = parser.parse_args()
    vertices, faces = read_mesh(args.stl)
    result = verify(vertices, faces, args.components)
    assert abs(result['bounds_mm'][2][0]) < 0.0001, 'Print must start at Z=0'
    if args.reference:
        reference, ref_faces = read_mesh(args.reference)
        verify(reference, ref_faces, args.reference_components, on_bed=False)
        footprint = hull2([(x, y) for x, y, z in vertices if abs(z) < 0.0001])
        assert len(footprint) >= 3
        margin = min(cross2(a, b, p) / math.hypot(b[0] - a[0], b[1] - a[1])
                     for a, b in zip(footprint, footprint[1:] + footprint[:1])
                     for p in reference)
        result['reference_projection_margin_mm'] = round(margin, 3)
        result['nominal_loaded_height_mm'] = round(max(p[2] for p in reference), 3)
        assert margin >= -0.001, 'Reference extends outside bed support polygon'
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
