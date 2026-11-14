"""Posing helpers for the Pixel v3 rig. All values are given in armature-space axes (cat faces -Y, +Z up, cat's left = +X):
  rot(+rx) nods forward/down, rot(+ry) rolls to the cat's left, rot(+rz) turns to the cat's left."""
import bpy, math
from mathutils import Euler, Vector, Quaternion
LEGS = ('FL', 'FR', 'HL', 'HR')
class Rig:
    def __init__(self, rig):
        self.rig = rig; self.B = {b.name: b.matrix_local.to_3x3() for b in rig.data.bones}
        self.head = {b.name: b.head_local.copy() for b in rig.data.bones}
        self.last_q = {}
        for pb in rig.pose.bones: pb.rotation_mode = 'QUATERNION'
        self.foot_rest = {l: self.head['footik.' + l].copy() for l in LEGS}
        self.lids = [o for o in bpy.data.objects if o.name.startswith('Lid.')]
    def rot(self, name, rx=0, ry=0, rz=0):
        R = Euler((math.radians(rx), math.radians(ry), math.radians(rz)), 'XYZ').to_matrix(); B = self.B[name]
        q = (B.inverted() @ R @ B).to_quaternion()
        if name in self.last_q and q.dot(self.last_q[name]) < 0: q.negate()      # keep keyframes on the same hemisphere
        self.last_q[name] = q.copy(); self.rig.pose.bones[name].rotation_quaternion = q
    def loc(self, name, d): self.rig.pose.bones[name].location = self.B[name].inverted() @ Vector(d)
    def scale(self, name, sx=1, sy=1, sz=1):
        B = self.B[name]; w = (sx, sy, sz)
        self.rig.pose.bones[name].scale = [sum(abs(B[j][i]) * w[j] for j in range(3)) / sum(abs(B[j][i]) for j in range(3)) for i in range(3)]
    def foot(self, leg, pos): self.loc('footik.' + leg, Vector(pos) - self.foot_rest[leg])
    def blink(self, v):
        for o in self.lids: o.data.shape_keys.key_blocks['Blink'].value = v
    # --- per-channel keyframing: each control is keyed on its own frames, so overlap / offsets are authored directly
    def krot(self, f, name, rx=0, ry=0, rz=0): self.rot(name, rx, ry, rz); self.rig.pose.bones[name].keyframe_insert('rotation_quaternion', frame=f)
    def kloc(self, f, name, d): self.loc(name, d); self.rig.pose.bones[name].keyframe_insert('location', frame=f)
    def kscale(self, f, name, sx=1, sy=1, sz=1): self.scale(name, sx, sy, sz); self.rig.pose.bones[name].keyframe_insert('scale', frame=f)
    def kfoot(self, f, leg, pos): self.foot(leg, pos); self.rig.pose.bones['footik.' + leg].keyframe_insert('location', frame=f)
    def kblink(self, f, v):
        self.blink(v)
        for o in self.lids: o.data.shape_keys.key_blocks['Blink'].keyframe_insert('value', frame=f)
    def reset(self):
        for pb in self.rig.pose.bones: pb.location = (0, 0, 0); pb.rotation_quaternion = (1, 0, 0, 0); pb.scale = (1, 1, 1)
        self.blink(0); self.last_q = {}
    def key(self, frame, interp='BEZIER'):
        for pb in self.rig.pose.bones:
            for path in ('location', 'rotation_quaternion', 'scale'): pb.keyframe_insert(path, frame=frame)
        for o in self.lids: o.data.shape_keys.key_blocks['Blink'].keyframe_insert('value', frame=frame)

def gpu(sc, samples):
    sc.render.engine = 'CYCLES'; prefs = bpy.context.preferences.addons['cycles'].preferences
    try:
        prefs.compute_device_type = 'OPTIX'; prefs.refresh_devices()
        if any(d.type == 'OPTIX' for d in prefs.devices):
            for d in prefs.devices: d.use = d.type == 'OPTIX'
            sc.cycles.device = 'GPU'
    except Exception as e: print('no OptiX, CPU render:', e)
    sc.cycles.samples = samples; sc.cycles.use_denoising = True
