"""Pose a T-posed bunny-costume figure (an unrigged .glb) into pin-up poses and render each one, background clear,
for the magazine covers in UNDER THE MATTRESS. The renders go to assets/figures/; tex.mag_cover lays them
on the cover under the masthead.

    python3 blender/pose_cover_figure.py path/to/figure.glb

The model isn't rigged, so the arms are bent here directly: every arm vertex follows the shoulder and elbow by how
far down the arm it sits (a smooth blend near each joint). Measured for a figure facing +X, arms out along Y, 1 m
tall, centered on the origin (what the uploaded model is).
"""
import math
import os
import sys

import bpy
import numpy as np
from mathutils import Euler, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(HERE), "assets", "figures")

SHOULDER = (-0.02, 0.095, 0.245)
UPPER = 0.125                      # shoulder to elbow


def ramp(x, a, b):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


def rx(deg):
    a = math.radians(deg)
    c, s = math.cos(a), math.sin(a)
    return np.array([[1, 0, 0], [0, c, -s], [0, s, c]])


def rz(deg):
    a = math.radians(deg)
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])


def pose_arm(v, side, shoulder_deg, elbow_deg, swing_deg=0.0):
    """side +1 = the arm along +Y. shoulder_deg: negative lowers it (for +Y). elbow_deg: extra bend at the elbow.
    swing_deg turns the whole arm forward/back around the vertical axis."""
    s = side
    ps = np.array([SHOULDER[0], s * SHOULDER[1], SHOULDER[2]])
    pe = ps + np.array([0, s * UPPER, 0])
    sy = s * v[:, 1]
    w_arm = ramp(sy, 0.09, 0.125) * ramp(v[:, 2], 0.195, 0.212)
    w_fore = ramp(sy, 0.205, 0.235) * (w_arm > 0)
    re = rx(s * elbow_deg)
    v1 = v + w_fore[:, None] * (((v - pe) @ re.T + pe) - v)
    rs = rz(s * swing_deg) @ rx(s * shoulder_deg)
    return v1 + w_arm[:, None] * (((v1 - ps) @ rs.T + ps) - v1)


POSES = {
    # hand on the hip, the other behind the head
    "hip_head": [(+1, -45, -80, 8), (-1, 50, 105, -6)],
    "head_hip": [(+1, 50, 105, -6), (-1, -45, -80, 8)],
    # both hands behind the head
    "both_head": [(+1, 52, 108, -6), (-1, 52, 108, -6)],
    # both hands on the hips
    "both_hip": [(+1, -45, -80, 8), (-1, -45, -80, 8)],
}
# note on signs: pose_arm mirrors with `side`, so the same numbers mean the same pose on either arm.
VIEWS = {"three_quarter": (35, 4), "front": (8, 2), "other_side": (-30, 6)}


def main():
    glb = sys.argv[-1]
    os.makedirs(OUT, exist_ok=True)
    for pose, arms in POSES.items():
        for view, (az, el) in VIEWS.items():
            if view == "front" and pose in ("head_hip",):
                continue
            render(glb, pose, arms, view, az, el)


def render(glb, pose, arms, view, az, el):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=glb)
    ob = [o for o in bpy.data.objects if o.type == "MESH"][0]
    me = ob.data
    M = np.array(ob.matrix_world)
    n = len(me.vertices)
    co = np.empty(n * 3)
    me.vertices.foreach_get("co", co)
    v = co.reshape(-1, 3) @ M[:3, :3].T + M[:3, 3]
    for side, sh, elb, sw in arms:
        v = pose_arm(v, side, sh, elb, sw)
    inv = np.linalg.inv(M)
    me.vertices.foreach_set("co", (v @ inv[:3, :3].T + inv[:3, 3]).ravel())
    me.update()
    # a touch of hip sway: lean the whole figure a few degrees
    ob.rotation_euler.rotate(Euler((math.radians(3), 0, 0)))
    sc = bpy.context.scene
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
    sc.collection.objects.link(cam)
    sc.camera = cam
    cam.data.lens = 85
    a, e = math.radians(az), math.radians(el)
    d = Vector((math.cos(a) * math.cos(e), math.sin(a) * math.cos(e), math.sin(e)))
    tgt = Vector((0, 0, 0.04))
    cam.location = tgt + d * 2.75
    cam.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
    for name, loc, power, col, size in (("key", (2.2, 1.6, 1.6), 260, (1.0, 0.9, 0.82), 1.2),
                                         ("fill", (2.0, -2.0, 0.4), 70, (0.85, 0.9, 1.0), 1.5),
                                         ("rim", (-1.8, -0.8, 1.4), 320, (1.0, 0.75, 0.85), 0.6),
                                         ("rim2", (-1.6, 1.4, 0.9), 220, (1.0, 0.95, 0.9), 0.6)):
        l = bpy.data.lights.new(name, "AREA")
        l.energy, l.color, l.size = power, col, size
        lo = bpy.data.objects.new(name, l)
        sc.collection.objects.link(lo)
        lo.location = loc
        lo.rotation_euler = (Vector((0, 0, 0)) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    w = bpy.data.worlds.new("w")
    sc.world = w
    w.use_nodes = True
    w.node_tree.nodes["Background"].inputs[1].default_value = 0.3
    sc.render.engine = "CYCLES"
    sc.cycles.samples = int(os.environ.get("POSE_SAMPLES", 64))
    sc.cycles.use_denoising = True
    sc.render.film_transparent = True
    sc.render.resolution_x, sc.render.resolution_y = 600, 900
    sc.render.image_settings.color_mode = "RGBA"
    sc.view_settings.view_transform = "AgX"
    sc.render.filepath = os.path.join(OUT, f"{pose}_{view}.png")
    bpy.ops.render.render(write_still=True)
    print("[pose]", sc.render.filepath)


if __name__ == "__main__":
    main()
