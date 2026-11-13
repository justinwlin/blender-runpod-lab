"""Print slice statistics / ASCII footprints of the Pixel mesh to place rig bones. blender -b <blend> -P analyze_geo.py"""
import bpy, numpy as np
me = bpy.data.objects['Pixel'].data; n = len(me.vertices)
co = np.empty(n * 3, np.float32); me.vertices.foreach_get('co', co); co = co.reshape(-1, 3)
print('bounds', co.min(0), co.max(0))
def ascii(mask, a, b, la, lb, res=0.05):
    pts = co[mask]; xs = np.arange(-0.95, 0.95, res)
    print(f'--- rows {lb} top=max, cols {la} -0.95..0.95 ---')
    brange = np.arange(pts[:, b].max(), pts[:, b].min() - res, -res)
    for v in brange:
        row = pts[(pts[:, b] <= v) & (pts[:, b] > v - res)]
        h = np.histogram(row[:, a], bins=np.append(xs, 0.95))[0]
        print(f'{v:6.2f} ' + ''.join('#' if c else '.' for c in h))
for z0, z1 in ((0.0, 0.08), (0.15, 0.22), (0.35, 0.42), (0.6, 0.66), (0.9, 0.95), (1.05, 1.1)):
    print(f'=== top-down slice z {z0}-{z1} (y rows, top=+Y back of cat; x cols) ===')
    ascii((co[:, 2] >= z0) & (co[:, 2] < z1), 0, 1, 'x', 'y')
print('=== side slice |x|<0.03 (z rows, y cols; cat faces -Y = left) ===')
ascii(np.abs(co[:, 0]) < 0.03, 1, 2, 'y', 'z')
print('=== front slice y in -0.5..-0.44 (z rows, x cols) ===')
ascii((co[:, 1] > -0.5) & (co[:, 1] < -0.44), 0, 2, 'x', 'z')
