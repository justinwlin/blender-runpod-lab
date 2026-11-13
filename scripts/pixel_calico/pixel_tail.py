"""Shared definition of Pixel's rebuilt tail (v2): one tapered tube from the back, around the cat's left side
(viewer's right in the front view), curling forward to rest by the front paws. Used by build_pixel.py and rig_pixel.py."""
import numpy as np
X0 = -0.14                      # body centre line in the recentred mesh
# centre-line control points (x, y, z) and tube radius at each
PATH = [(0.00, 0.44, 0.24, 0.13), (0.20, 0.62, 0.18, 0.155), (0.46, 0.48, 0.175, 0.17), (0.66, 0.18, 0.175, 0.17),
        (0.69, -0.14, 0.17, 0.165), (0.57, -0.40, 0.16, 0.155), (0.36, -0.55, 0.145, 0.14), (0.20, -0.60, 0.125, 0.12)]
N_BONES = 6
BODY_C = (X0, 0.06)             # footprint ellipse the fused tail ring is clamped back to
def body_radii(z):
    t = np.clip(z / 0.6, 0, 1); return 0.62 - 0.06 * t, 0.68 - 0.08 * t

def centreline(n=72):
    """Catmull-Rom through PATH, resampled to n points evenly spaced in arc length. returns (pts[n,3], radius[n], s[n] in 0..1)"""
    P = np.array(PATH, float); P = np.vstack([2 * P[0] - P[1], P, 2 * P[-1] - P[-2]])
    out = []
    for i in range(1, len(P) - 2):
        for t in np.linspace(0, 1, 24, endpoint=False):
            a, b, c, d = P[i - 1], P[i], P[i + 1], P[i + 2]
            out.append(0.5 * ((2 * b) + (-a + c) * t + (2 * a - 5 * b + 4 * c - d) * t * t + (-a + 3 * b - 3 * c + d) * t ** 3))
    out.append(P[-2]); out = np.array(out)
    seg = np.linalg.norm(np.diff(out[:, :3], axis=0), axis=1); L = np.concatenate([[0], np.cumsum(seg)]); L /= L[-1]
    s = np.linspace(0, 1, n); res = np.stack([np.interp(s, L, out[:, k]) for k in range(4)], 1)
    return res[:, :3], res[:, 3], s

def bone_nodes():
    pts, _, s = centreline(200)
    return [tuple(np.array([np.interp(v, s, pts[:, k]) for k in range(3)])) for v in np.linspace(0.04, 1.0, N_BONES + 1)]

def tube(seg=28, n=72, cap=7):
    """returns verts[m,3], faces(list of quads/tris), s per vert (0 base .. 1 tip)"""
    pts, rad, s = centreline(n)
    tan = np.gradient(pts, axis=0); tan /= np.linalg.norm(tan, axis=1)[:, None]
    up = np.array([0, 0, 1.0]); side = np.cross(tan, up); side /= np.linalg.norm(side, axis=1)[:, None]; nrm = np.cross(side, tan)
    rings, sv = [], []
    ang = np.linspace(0, 2 * np.pi, seg, endpoint=False)
    def ring(c, r, sd, nm): return c[None] + r * (np.cos(ang)[:, None] * sd[None] + np.sin(ang)[:, None] * nm[None])
    for i in range(n): rings.append(ring(pts[i], rad[i], side[i], nrm[i])); sv.append(s[i])
    for j in range(1, cap + 1):           # hemispherical tip cap
        a = j / (cap + 1) * np.pi / 2
        rings.append(ring(pts[-1] + tan[-1] * rad[-1] * np.sin(a), rad[-1] * np.cos(a), side[-1], nrm[-1])); sv.append(1.0)
    V = np.vstack(rings + [(pts[-1] + tan[-1] * rad[-1])[None], pts[0][None]]); S = np.concatenate([np.repeat(sv, seg), [1.0, 0.0]])
    F = []; R = len(rings)
    for i in range(R - 1):
        for k in range(seg):
            a, b = i * seg + k, i * seg + (k + 1) % seg; F.append((a, b, b + seg, a + seg))
    tip, base = R * seg, R * seg + 1
    for k in range(seg):
        F.append(((R - 1) * seg + k, (R - 1) * seg + (k + 1) % seg, tip)); F.append(((k + 1) % seg, k, base))
    return V, F, S, ang

def tail_labels(V, S, seg):
    """palette labels per vertex: 1 black, 2 orange patches (tip stays black)"""
    k = np.arange(len(V)) % seg; phi = 2 * np.pi * k / seg
    f = np.sin(11 * S + 0.8) * np.cos(phi - 1.2 + 5 * S) + 0.55 * np.sin(27 * S + 2 * phi) + 0.35 * np.cos(41 * S - 3 * phi)
    lab = np.where((f > 0.62) & (S > 0.10) & (S < 0.86), 2, 1).astype(np.uint8); lab[-2:] = 1
    return lab
