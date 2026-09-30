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


def lights(sc):
    # big soft key from front-left, cool rim from behind-right, overhead box, low warm kicker
    _area(sc, "key", (-1.2, -1.3, 1.5), 0.8, 190, (1.0, 0.96, 0.9))
    _area(sc, "top", (0.1, 0.1, 1.4), 0.7, 65, (1.0, 1.0, 1.0))
    _area(sc, "rim", (1.1, 1.4, 0.7), 0.5, 210, (0.75, 0.85, 1.0))
    _area(sc, "kick", (1.6, -0.6, 0.35), 0.5, 45, (1.0, 0.85, 0.7))
    # the pool of light on the floor; the frame edges fall off to black
    s = bpy.data.lights.new("pool", "SPOT")
    s.energy = 40
    s.spot_size = math.radians(48)
    s.spot_blend = 1.0
    s.shadow_soft_size = 0.35
    ob = bpy.data.objects.new("pool", s)
    sc.collection.objects.link(ob)
    ob.location = (0.25, -0.4, 1.9)
    ob.rotation_euler = (Vector((0, 0, 0)) - ob.location).to_track_quat("-Z", "Y").to_euler()


def world(sc):
    w = bpy.data.worlds.new("world")
    sc.world = w
    nt = w.node_tree
    bg = nt.nodes.get("Background") or nt.nodes.new("ShaderNodeBackground")
    bg.inputs["Color"].default_value = (0.0, 0.0, 0.0, 1)
    bg.inputs["Strength"].default_value = 0.0
    out = nt.nodes.get("World Output") or nt.nodes.new("ShaderNodeOutputWorld")
    nt.links.new(bg.outputs[0], out.inputs[0])


def floor(sc, rng):
    me = bpy.data.meshes.new("floor")
    s = 4.0
    me.from_pydata([(-s, -s, 0), (s, -s, 0), (s, s, 0), (-s, s, 0)], [], [(0, 1, 2, 3)])
    ob = bpy.data.objects.new("floor", me)
    sc.collection.objects.link(ob)
    me.materials.append(mat.get(("floor", {}), rng))
    return ob


def render_settings(sc, res=1024, samples=96, fast=False):
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
    vs.exposure = 0.0


def build(sc, rng, res=1024, samples=96, fast=False):
    world(sc)
    camera(sc)
    lights(sc)
    floor(sc, rng)
    render_settings(sc, res, samples, fast)
