"""Repeat the accepted R4 skin; preserve R2 at exact panel/socket boundaries."""
import math
import struct
import numpy as np
from .profile import DATA, ORIGIN, PITCH

TRI = np.dtype([("normal", "<f4", (3,)), ("vertices", "<f4", (3, 3)), ("attribute", "<u2")])

def raster(path, xs, ys):
    triangles = np.fromfile(path, dtype=TRI, offset=84)["vertices"].astype(float)
    keep = (triangles[:, :, 0].max(axis=1) >= xs[0]) & (triangles[:, :, 0].min(axis=1) <= xs[-1]) \
        & (triangles[:, :, 1].max(axis=1) >= ys[0]) & (triangles[:, :, 1].min(axis=1) <= ys[-1])
    heights = np.zeros((len(ys), len(xs)))
    for a, b, c in triangles[keep]:
        d = (b[1]-c[1])*(a[0]-c[0])+(c[0]-b[0])*(a[1]-c[1])
        if abs(d) < 1e-10:
            continue
        i0 = max(0, np.searchsorted(xs, min(a[0], b[0], c[0])-1e-8))
        i1 = min(len(xs), np.searchsorted(xs, max(a[0], b[0], c[0])+1e-8, side="right"))
        j0 = max(0, np.searchsorted(ys, min(a[1], b[1], c[1])-1e-8))
        j1 = min(len(ys), np.searchsorted(ys, max(a[1], b[1], c[1])+1e-8, side="right"))
        if i0 == i1 or j0 == j1:
            continue
        x, y = xs[None, i0:i1], ys[j0:j1, None]
        u = ((b[1]-c[1])*(x-c[0])+(c[0]-b[0])*(y-c[1]))/d
        v = ((c[1]-a[1])*(x-c[0])+(a[0]-c[0])*(y-c[1]))/d
        w = 1-u-v
        z = np.where(np.minimum(np.minimum(u, v), w) >= -1e-8, u*a[2]+v*b[2]+w*c[2], 0)
        heights[j0:j1, i0:i1] = np.maximum(heights[j0:j1, i0:i1], z)
    return heights

def ease(t):
    t = np.clip(t, 0, 1)
    return t*t*t*(10-15*t+6*t*t)

def sample(data, x, y):
    sx, sy, z = data["x"], data["y"], data["z"]
    x, y = np.clip(x, sx[0], sx[-1]), np.clip(y, sy[0], sy[-1])
    ix = np.clip(np.searchsorted(sx, x, side="right")-1, 0, len(sx)-2)
    iy = np.clip(np.searchsorted(sy, y, side="right")-1, 0, len(sy)-2)
    tx, ty = (x-sx[ix])/(sx[ix+1]-sx[ix]), (y-sy[iy])/(sy[iy+1]-sy[iy])
    low = z[iy[:, None], ix[None, :]]*(1-tx)+z[iy[:, None], ix[None, :]+1]*tx
    high = z[iy[:, None]+1, ix[None, :]]*(1-tx)+z[iy[:, None]+1, ix[None, :]+1]*tx
    return low*(1-ty[:, None])+high*ty[:, None]

def periodic_surface(data, xs, ys):
    x = (xs-ORIGIN[0]) % PITCH[0]+ORIGIN[0]
    y = (ys-ORIGIN[1]) % PITCH[1]+ORIGIN[1]
    weight = ease((y-12)/38)[:, None]
    return sample(data, x, y+PITCH[1])*(1-weight)+sample(data, x, y)*weight

def distance_inside(mask, step, limit=7):
    sx, sy = step
    px, py = math.ceil(limit/sx), math.ceil(limit/sy)
    outside = np.pad(~mask, ((py, py), (px, px)), constant_values=True)
    distance = np.full(mask.shape, float(limit))
    for dy in range(-py, py+1):
        for dx in range(-px, px+1):
            d = math.hypot(dx*sx, dy*sy)
            if d <= limit:
                hit = outside[py+dy:py+dy+mask.shape[0], px+dx:px+dx+mask.shape[1]]
                distance = np.where(hit, np.minimum(distance, d), distance)
    return distance

def write_height_solid(path, xs, ys, z):
    ny, nx = z.shape
    xx, yy = np.meshgrid(xs, ys)
    top = np.stack([xx, yy, z], axis=-1).reshape(-1, 3)
    bottom = top.copy()
    bottom[:, 2] = 0
    points = np.concatenate([top, bottom])
    faces, count = [], nx*ny
    for j in range(ny-1):
        for i in range(nx-1):
            a = j*nx+i
            b, c, d = a+1, a+nx, a+nx+1
            faces.extend([(a,b,d), (a,d,c), (a+count,d+count,b+count), (a+count,c+count,d+count)])
    boundary = list(range(nx))+[j*nx+nx-1 for j in range(1,ny)] \
        + [(ny-1)*nx+i for i in range(nx-2,-1,-1)]+[j*nx for j in range(ny-2,0,-1)]
    for a, b in zip(boundary, boundary[1:]+boundary[:1]):
        faces.extend([(a+count,b+count,b), (a+count,b,a)])
    triangles = points[np.asarray(faces)]
    normal = np.cross(triangles[:,1]-triangles[:,0], triangles[:,2]-triangles[:,0])
    size = np.linalg.norm(normal, axis=1)
    if not np.all(size > 0):
        raise ValueError("Degenerate heightfield")
    records = np.zeros(len(triangles), dtype=TRI)
    records["normal"] = normal/size[:,None]
    records["vertices"] = triangles
    with path.open("wb") as output:
        output.write(b"Spice drawer R4 construction stock; do not print".ljust(80,b" "))
        output.write(struct.pack("<I", len(records)))
        output.write(records.tobytes())

def write_plate(path, files, bed, brim):
    """Pack exact independent parts in their existing print orientation."""
    packed, x, y, row_height = [], brim, brim, 0
    usable_w, usable_d = bed[0]-brim, bed[1]-brim
    gap = max(2*brim+1, 2)
    for file in files:
        records = np.fromfile(file, dtype=TRI, offset=84)
        lo = records["vertices"].min(axis=(0,1)); hi = records["vertices"].max(axis=(0,1))
        width, depth = (hi-lo)[:2]
        if width+2*brim > bed[0] or depth+2*brim > bed[1]:
            raise ValueError(f"Connector does not fit the printer: {file.name}")
        if x+width > usable_w+1e-6:
            x, y, row_height = brim, y+row_height+gap, 0
        if y+depth > usable_d+1e-6:
            return None
        records["vertices"] += np.array([x,y,0])-lo
        packed.append(records)
        x += width+gap
        row_height = max(row_height, depth)
    if not packed:
        return None
    records = np.concatenate(packed)
    with path.open("wb") as output:
        output.write(b"Exact unrotated spice drawer connectors".ljust(80,b" "))
        output.write(struct.pack("<I",len(records)))
        output.write(records.tobytes())
    return len(files)
