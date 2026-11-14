"""v3 geometry helpers: all-quad 'subdivided cube' topology mapped to spheres / capsules / tubes, with per-face UV islands."""
import numpy as np

def cube_grid(nx, ny, nz):
    """Surface of the cube [-1,1]^3 as welded quads. Returns P[n,3], quads[m,4], and per-quad (face_id, uv[4,2]) with uv in 0..1 per face."""
    idx = {}; P = []; quads = []; fids = []; fuv = []
    def vid(i, j, k):
        key = (i, j, k)
        if key not in idx: idx[key] = len(P); P.append((2 * i / nx - 1, 2 * j / ny - 1, 2 * k / nz - 1))
        return idx[key]
    def face(fid, na, nb, to_ijk, flip):
        for a in range(na):
            for b in range(nb):
                c = [(a, b), (a + 1, b), (a + 1, b + 1), (a, b + 1)]
                if flip: c = c[::-1]
                quads.append([vid(*to_ijk(x, y)) for x, y in c]); fids.append(fid); fuv.append([(x / na, y / nb) for x, y in c])
    face(0, ny, nz, lambda a, b: (nx, a, b), False)   # +X
    face(1, ny, nz, lambda a, b: (0, a, b), True)     # -X
    face(2, nx, nz, lambda a, b: (a, ny, b), True)    # +Y
    face(3, nx, nz, lambda a, b: (a, 0, b), False)    # -Y
    face(4, nx, ny, lambda a, b: (a, b, nz), False)   # +Z
    face(5, nx, ny, lambda a, b: (a, b, 0), True)     # -Z
    return np.array(P, float), np.array(quads), np.array(fids), np.array(fuv, float)

def spherify(P):
    x, y, z = P[:, 0], P[:, 1], P[:, 2]
    return np.stack([x * np.sqrt(1 - y * y / 2 - z * z / 2 + y * y * z * z / 3),
                     y * np.sqrt(1 - z * z / 2 - x * x / 2 + z * z * x * x / 3),
                     z * np.sqrt(1 - x * x / 2 - y * y / 2 + x * x * y * y / 3)], 1)

def disc(P):
    """cube -> unit cylinder coords: (u, v) on the unit disc, t in 0..1 along the axis, r = radial fraction"""
    x, y = P[:, 0], P[:, 1]
    u = x * np.sqrt(1 - y * y / 2); v = y * np.sqrt(1 - x * x / 2)
    return u, v, (P[:, 2] + 1) / 2, np.hypot(u, v)

def atlas_uv(fids, fuv, rect, pad=0.012):
    """place the 6 face islands of a part in a 3x2 grid inside rect=(u0,v0,u1,v1) of the shared atlas"""
    u0, v0, u1, v1 = rect; cw, ch = (u1 - u0) / 3, (v1 - v0) / 2
    out = np.empty_like(fuv)
    for f in range(6):
        m = fids == f; cu, cv = u0 + (f % 3) * cw, v0 + (f // 3) * ch
        out[m, :, 0] = cu + pad * cw + fuv[m, :, 0] * cw * (1 - 2 * pad); out[m, :, 1] = cv + pad * ch + fuv[m, :, 1] * ch * (1 - 2 * pad)
    return out

def smooth01(x): x = np.clip(x, 0, 1); return x * x * (3 - 2 * x)

def catmull(ctrl, n):
    """Catmull-Rom through ctrl[k, d], n samples evenly spaced in arc length (over the first 3 columns)"""
    P = np.array(ctrl, float); P = np.vstack([2 * P[0] - P[1], P, 2 * P[-1] - P[-2]]); out = []
    for i in range(1, len(P) - 2):
        for t in np.linspace(0, 1, 24, endpoint=False):
            a, b, c, d = P[i - 1], P[i], P[i + 1], P[i + 2]
            out.append(0.5 * ((2 * b) + (-a + c) * t + (2 * a - 5 * b + 4 * c - d) * t * t + (-a + 3 * b - 3 * c + d) * t ** 3))
    out.append(P[-2]); out = np.array(out)
    L = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(out[:, :3], axis=0), axis=1))]); L /= L[-1]
    s = np.linspace(0, 1, n); return np.stack([np.interp(s, L, out[:, k]) for k in range(out.shape[1])], 1)
