"""The fixed stage. Same camera, same floor, same lights, same cube size.

Nothing here may depend on the token seed: the silhouette is the brand.
"""
import math

import bpy
from mathutils import Vector

from . import mat

CUBE = 0.3048            # 12 inches, the only size there is
H = CUBE / 2
AZIMUTH = math.radians(38)
ELEVATION = math.radians(27)
ORTHO_SCALE = 0.7


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    mat._CACHE.clear()
    sc = bpy.context.scene
    sc.unit_settings.system = "METRIC"
    return sc


def camera(sc):
    cam = bpy.data.cameras.new("cam")
    cam.type = "ORTHO"
    cam.ortho_scale = ORTHO_SCALE
    cam.clip_end = 100
    ob = bpy.data.objects.new("cam", cam)
    sc.collection.objects.link(ob)
    target = Vector((0, 0, H * 0.92))
    d = Vector((math.sin(AZIMUTH) * math.cos(ELEVATION), -math.cos(AZIMUTH) * math.cos(ELEVATION),
                math.sin(ELEVATION)))
    ob.location = target + d * 20
    ob.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
    sc.camera = ob
    return ob


def _area(sc, name, loc, size, power, color=(1, 1, 1), target=(0, 0, 0.15), spread=180, shape="SQUARE"):
    l = bpy.data.lights.new(name, "AREA")
    l.size = size
    l.shape = shape
    l.energy = power
    l.color = color
    l.spread = math.radians(spread)
    ob = bpy.data.objects.new(name, l)
    sc.collection.objects.link(ob)
    ob.location = loc
    ob.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    return ob


def lights(sc, look="studio"):
    if look == "showroom":
        # dark room, cool key, a cyan edge light from behind-right and a magenta one from behind-left
        _area(sc, "key", (-1.2, -1.3, 1.5), 0.8, 150, (0.86, 0.92, 1.0))
        _area(sc, "top", (0.1, 0.1, 1.4), 0.7, 40, (1.0, 1.0, 1.0))
        _area(sc, "rim", (1.1, 1.4, 0.7), 0.5, 420, (0.25, 0.85, 1.0))
        _area(sc, "rim2", (-1.3, 1.2, 0.7), 0.5, 330, (1.0, 0.2, 0.65))
        _area(sc, "kick", (1.6, -0.6, 0.35), 0.5, 30, (1.0, 0.85, 0.7))
        pool = 26
    elif look == "studio":
        # the cube is the showpiece: warm key, a faint cool edge light, a whisper of warm from the other side,
        # and a neutral pool on the floor. Nothing colored enough to tint the block or the floor.
        _area(sc, "key", (-1.2, -1.3, 1.5), 0.8, 175, (1.0, 0.97, 0.93))
        _area(sc, "top", (0.1, 0.1, 1.4), 0.7, 55, (1.0, 1.0, 1.0))
        _area(sc, "rim", (1.1, 1.4, 0.7), 0.5, 260, (0.82, 0.9, 1.0))
        _area(sc, "rim2", (-1.3, 1.2, 0.7), 0.5, 90, (1.0, 0.92, 0.85))
        _area(sc, "kick", (1.6, -0.6, 0.35), 0.5, 35, (1.0, 0.88, 0.75))
        pool = 22
    elif look == "daylight":
        # big soft boxes, almost no colored light: a product shot on a bright sweep
        _area(sc, "key", (-1.4, -1.5, 1.7), 1.6, 430, (1.0, 0.97, 0.92))
        _area(sc, "fill", (1.6, -1.0, 0.9), 1.4, 170, (0.9, 0.95, 1.0))
        _area(sc, "top", (0.1, 0.1, 1.6), 1.4, 210, (1.0, 1.0, 1.0))
        _area(sc, "rim", (1.1, 1.4, 0.7), 0.8, 130, (1.0, 1.0, 1.0))
        pool = 0
    else:
        # big soft key from front-left, cool rim from behind-right, overhead box, low warm kicker
        _area(sc, "key", (-1.2, -1.3, 1.5), 0.8, 190, (1.0, 0.96, 0.9))
        _area(sc, "top", (0.1, 0.1, 1.4), 0.7, 65, (1.0, 1.0, 1.0))
        _area(sc, "rim", (1.1, 1.4, 0.7), 0.5, 210, (0.75, 0.85, 1.0))
        _area(sc, "kick", (1.6, -0.6, 0.35), 0.5, 45, (1.0, 0.85, 0.7))
        pool = 40
    if not pool:
        return
    # the pool of light on the floor; the frame edges fall off to black
    s = bpy.data.lights.new("pool", "SPOT")
    s.energy = pool
    s.spot_size = math.radians(48)
    s.spot_blend = 1.0
    s.shadow_soft_size = 0.35
    ob = bpy.data.objects.new("pool", s)
    sc.collection.objects.link(ob)
    ob.location = (0.25, -0.4, 1.9)
    ob.rotation_euler = (Vector((0, 0, 0)) - ob.location).to_track_quat("-Z", "Y").to_euler()


def world(sc, strength=1.0):
    """Black to the camera. To reflections, a studio: a bright ceiling, a dim horizon and
    one long softbox, so chrome, gold, CRT glass and glossy plastic have something to show."""
    w = bpy.data.worlds.new("world")
    w.use_nodes = True       # Blender 4.x needs this for a node tree; 5.x always has one
    sc.world = w
    nt = w.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputWorld")
    bg = nt.nodes.new("ShaderNodeBackground")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(tc.outputs["Generated"], sep.inputs[0])
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    els = ramp.color_ramp.elements
    els[0].position, els[0].color = 0.0, (0.0, 0.0, 0.0, 1)
    els[1].position, els[1].color = 1.0, (0.55, 0.56, 0.6, 1)
    e = els.new(0.45)
    e.color = (0.0, 0.0, 0.0, 1)
    e = els.new(0.6)
    e.color = (0.06, 0.06, 0.065, 1)
    nt.links.new(sep.outputs["Z"], ramp.inputs["Fac"])
    # a long softbox off to the key side
    strip = nt.nodes.new("ShaderNodeMath")
    strip.operation = "MULTIPLY"
    a = nt.nodes.new("ShaderNodeMapRange")
    a.inputs["From Min"].default_value, a.inputs["From Max"].default_value = -0.75, -0.6
    b = nt.nodes.new("ShaderNodeMapRange")
    b.inputs["From Min"].default_value, b.inputs["From Max"].default_value = 0.2, 0.35
    nt.links.new(sep.outputs["X"], a.inputs["Value"])
    nt.links.new(sep.outputs["Z"], b.inputs["Value"])
    nt.links.new(a.outputs[0], strip.inputs[0])
    nt.links.new(b.outputs[0], strip.inputs[1])
    add = nt.nodes.new("ShaderNodeMix")
    add.data_type = "RGBA"
    add.blend_type = "ADD"
    nt.links.new(strip.outputs[0], add.inputs[0])
    nt.links.new(ramp.outputs["Color"], add.inputs[6])
    add.inputs[7].default_value = (1.4, 1.35, 1.3, 1)
    nt.links.new(add.outputs[2], bg.inputs["Color"])
    bg.inputs["Strength"].default_value = strength
    nt.links.new(bg.outputs[0], out.inputs["Surface"])
    # reflections only: the frame edges stay black and the floor stays lit by the lights alone
    vis = w.cycles_visibility
    vis.camera = False
    vis.diffuse = False
    vis.transmission = True
    vis.glossy = True
    vis.scatter = False


def floor(sc, rng):
    me = bpy.data.meshes.new("floor")
    s = 4.0
    me.from_pydata([(-s, -s, 0), (s, -s, 0), (s, s, 0), (-s, s, 0)], [], [(0, 1, 2, 3)])
    ob = bpy.data.objects.new("floor", me)
    sc.collection.objects.link(ob)
    me.materials.append(mat.get(("floor", {}), rng))
    return ob


DEVICE = {"want": "auto", "used": None}     # set from --device; "used" says what actually rendered


def use_gpu(sc):
    """Switch Cycles to the best GPU backend this machine offers. Returns its name, or None (CPU)."""
    try:
        prefs = bpy.context.preferences.addons["cycles"].preferences
    except KeyError:
        return None
    for backend in ("METAL", "OPTIX", "CUDA", "HIP", "ONEAPI"):
        try:
            prefs.compute_device_type = backend
            prefs.get_devices()
        except (TypeError, RuntimeError):
            continue
        gpus = [d for d in prefs.devices if d.type != "CPU"]
        if gpus:
            for d in prefs.devices:
                d.use = d.type != "CPU"
            sc.cycles.device = "GPU"
            return backend
    return None


def render_settings(sc, res=1024, samples=96, fast=False, exposure=0.0):
    r = sc.render
    r.engine = "CYCLES"
    r.resolution_x = r.resolution_y = res
    r.resolution_percentage = 100
    r.film_transparent = False
    r.image_settings.file_format = "PNG"
    r.image_settings.color_mode = "RGB"
    r.use_persistent_data = True
    cy = sc.cycles
    cy.device = "CPU"
    if DEVICE["want"] != "cpu":
        DEVICE["used"] = use_gpu(sc)
    cy.samples = samples
    cy.use_adaptive_sampling = True
    cy.adaptive_threshold = 0.02 if not fast else 0.05
    cy.use_denoising = True
    try:
        cy.denoiser = "OPENIMAGEDENOISE"
    except TypeError:
        pass
    cy.max_bounces = 8
    cy.diffuse_bounces = 3
    cy.glossy_bounces = 4
    cy.transmission_bounces = 8
    cy.transparent_max_bounces = 8
    cy.caustics_reflective = False
    cy.caustics_refractive = False
    cy.sample_clamp_indirect = 8.0
    cy.blur_glossy = 1.0
    vs = sc.view_settings
    try:
        vs.view_transform = "AgX"
        for look in ("AgX - Punchy", "Punchy", "AgX - Medium High Contrast", "Medium High Contrast"):
            try:
                vs.look = look
                break
            except TypeError:
                continue
    except TypeError:
        vs.view_transform = "Filmic"
    vs.exposure = exposure


def build(sc, rng, res=1024, samples=96, fast=False, look="studio"):
    mat.LOOK["name"] = look
    world(sc, {"showroom": 0.7, "studio": 0.85, "daylight": 1.5}.get(look, 1.0))
    camera(sc)
    lights(sc, look)
    floor(sc, rng)
    render_settings(sc, res, samples, fast, {"daylight": 0.25}.get(look, 0.0))
