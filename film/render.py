"""Render the hero film's shots with Blender (Cycles). cut.py then puts them together with the words.

    python3 film/render.py --out renders/film                       # full size, Mac GPU
    python3 film/render.py --out renders/film_rough --scale 0.25 --samples 8 --step 4   # quick rough cut

--step N renders every Nth frame of the moving shots (cut.py holds each one), for fast drafts.
Every shot is skipped if its frames are already there, so a stopped run picks up where it left off.
"""
import argparse
import math
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "blender"))
sys.path.insert(0, HERE)

import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402

import generate  # noqa: E402
from crushed import build, stage  # noqa: E402
import plan  # noqa: E402


def clear_lights():
    for ob in [o for o in bpy.data.objects if o.type == "LIGHT"]:
        bpy.data.objects.remove(ob, do_unlink=True)


def world_strength(sc, k):
    for n in sc.world.node_tree.nodes:
        if n.type == "BACKGROUND":
            n.inputs[1].default_value *= k


def area(sc, name, loc, size, power, color, target=(0, 0, 0.16)):
    return stage._area(sc, name, loc, size, power, color, target=target)


def point(sc, name, loc, power, color, radius=0.02):
    l = bpy.data.lights.new(name, "POINT")
    l.energy = power
    l.color = color
    l.shadow_soft_size = radius
    ob = bpy.data.objects.new(name, l)
    sc.collection.objects.link(ob)
    ob.location = loc
    return ob


ORANGE = (1.0, 0.42, 0.08)
PURPLE = (0.55, 0.18, 1.0)


def rig(sc, kind):
    """Lighting for each mood. The flicker of the dying bulb is added later in cut.py, frame by frame."""
    if kind == "studio":
        return                                   # the stage's own lights: the look every block is known by
    clear_lights()
    if kind == "dark":
        world_strength(sc, 0.04)
        point(sc, "bulb", (-0.22, -0.42, 0.42), 7, (1.0, 0.55, 0.22), 0.01)    # a bare bulb, front-left, low power
        area(sc, "edge", (0.5, 0.7, 0.35), 0.3, 6, PURPLE)
    elif kind == "silhouette":
        world_strength(sc, 0.0)
        area(sc, "rim_o", (-0.55, 0.75, 0.32), 0.25, 70, ORANGE)
        area(sc, "rim_p", (0.75, 0.55, 0.42), 0.25, 85, PURPLE)
    elif kind == "halloween":
        world_strength(sc, 0.18)
        area(sc, "key", (-0.9, -1.0, 0.55), 0.6, 70, ORANGE)
        area(sc, "fill", (1.0, -0.7, 0.25), 0.6, 30, (0.85, 0.9, 1.0))
        area(sc, "rim_p", (0.8, 1.0, 0.6), 0.4, 260, PURPLE)
        area(sc, "rim_g", (-1.0, 0.8, 0.3), 0.4, 30, (0.45, 1.0, 0.1))     # a little slime green from behind
        area(sc, "top", (0.0, 0.0, 1.3), 0.6, 18, (1, 1, 1))
        s = bpy.data.lights.new("pool", "SPOT")
        s.energy = 14
        s.spot_size = math.radians(40)
        s.spot_blend = 1.0
        s.color = ORANGE
        ob = bpy.data.objects.new("pool", s)
        sc.collection.objects.link(ob)
        ob.location = (0.1, -0.2, 1.8)
        ob.rotation_euler = (Vector((0, 0, 0)) - ob.location).to_track_quat("-Z", "Y").to_euler()


def perspective(sc):
    cam = sc.camera.data
    cam.type = "PERSP"
    cam.sensor_fit = "VERTICAL"
    cam.sensor_height = 24.0
    cam.clip_start = 0.005
    return sc.camera


def lens_for(vfov):
    return 12.0 / math.tan(math.radians(vfov) / 2)


def key_camera(ob, frame, loc, aim, vfov, dof=None):
    ob.location = loc
    ob.rotation_euler = (Vector(aim) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    ob.data.lens = lens_for(vfov)
    ob.keyframe_insert("location", frame=frame)
    ob.keyframe_insert("rotation_euler", frame=frame)
    ob.data.keyframe_insert("lens", frame=frame)
    ob.data.dof.use_dof = bool(dof)        # the camera is shared between shots: switch focus blur off again
    if dof:
        ob.data.dof.focus_distance = (Vector(aim) - Vector(loc)).length
        ob.data.dof.aperture_fstop = dof
        ob.data.dof.keyframe_insert("focus_distance", frame=frame)


def smooth(ob):
    """Ease in and out of every move: camera moves that start and stop gently read as 'filmed', not 'animated'."""
    for data in (ob, ob.data, ob.data.dof):
        for fc in build._fcurves(data) if getattr(data, "animation_data", None) else []:
            for kp in fc.keyframe_points:
                kp.interpolation = "BEZIER"
                kp.easing = "AUTO"


def setup_shot(sc, shot):
    rig(sc, shot["rig"])
    ob = perspective(sc)
    ob.data.shift_y = shot.get("shift", 0.0)
    n = shot["frames"]
    if "orbit" in shot:
        a0, a1, r, (z0, z1) = shot["orbit"]
        aim = shot["cam"][1]
        vfov = shot["cam"][2]
        for f in range(1, n + 1, max(1, n // 12)):
            t = (f - 1) / (n - 1)
            a = math.radians(a0 + (a1 - a0) * t)
            rr = r * (1 - 0.06 * t)                       # a slow push in while it turns
            key_camera(ob, f, (math.sin(a) * rr, -math.cos(a) * rr, z0 + (z1 - z0) * t), aim, vfov)
        key_camera(ob, n, (math.sin(math.radians(a1)) * r * 0.94, -math.cos(math.radians(a1)) * r * 0.94, z1),
                   aim, vfov)
        for fc in build._fcurves(ob):
            for kp in fc.keyframe_points:
                kp.interpolation = "LINEAR"
    else:
        (l0, a0, v0), (l1, a1, v1) = shot["cam"]
        dof = 5.6 if shot["rig"] == "dark" else None      # shallow focus on the close-ups
        key_camera(ob, 1, l0, a0, v0, dof)
        key_camera(ob, n, l1, a1, v1, dof)
        smooth(ob)
    sc.frame_start, sc.frame_end = 1, n


def montage_camera(sc):
    """The brand view (the same angle as every token image), widened to fill a 21:9 frame."""
    cam = sc.camera.data
    cam.type = "ORTHO"
    cam.sensor_fit = "VERTICAL"
    cam.ortho_scale = 0.62
    cam.shift_y = 0.07                       # sit the cube a little low, leaving the top for its name
    sc.frame_start = sc.frame_end = 1


def render_cube(cube, shots, out, scale, samples, step):
    todo = [s for s in shots if not done(s, out, step)]
    if not todo:
        return
    t0 = time.time()
    r = generate.token(cube)
    sc = build.build(r, res=256, samples=samples)
    sc.render.resolution_x = round(plan.W * scale)
    sc.render.resolution_y = round(plan.H * scale)
    sc.cycles.samples = samples
    for shot in todo:
        d = os.path.join(out, shot["name"])
        os.makedirs(d, exist_ok=True)
        if shot.get("still"):
            montage_camera(sc)
            sc.render.filepath = os.path.join(d, "0001.png")
            bpy.ops.render.render(write_still=True)
        else:
            setup_shot(sc, shot)
            sc.frame_step = step
            sc.render.filepath = os.path.join(d, "####")
            bpy.ops.render.render(animation=True)
        open(os.path.join(d, ".done"), "w").write(str(step))
        print(f"[film] {shot['name']} done ({time.time() - t0:.0f}s)", flush=True)


def done(shot, out, step):
    p = os.path.join(out, shot["name"], ".done")
    return os.path.exists(p) and int(open(p).read() or 1) <= step


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="renders/film")
    ap.add_argument("--scale", type=float, default=1.0)
    ap.add_argument("--samples", type=int, default=64)
    ap.add_argument("--step", type=int, default=1)
    ap.add_argument("--device", default="auto", choices=["auto", "cpu", "gpu"])
    ap.add_argument("--only", nargs="*", help="shot names to render (default: all)")
    a = ap.parse_args(argv)
    stage.DEVICE["want"] = a.device
    by_cube = {}
    for s in plan.SHOTS:
        by_cube.setdefault(s["cube"], []).append(s)
    for c in plan.MONTAGE:
        by_cube.setdefault(c, []).append(dict(name=f"m_{c:04d}", cube=c, still=True))
    for cube, shots in by_cube.items():
        if a.only:
            shots = [s for s in shots if s["name"] in a.only]
        if shots:
            render_cube(cube, shots, a.out, a.scale, a.samples, a.step)
    print(f"[film] all shots rendered -> {a.out}  (device: {stage.DEVICE['used'] or 'CPU'})")


if __name__ == "__main__":
    main()
