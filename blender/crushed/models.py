"""Remastered objects: a real Blender model (assets/models/<name>/model.glb) used in place of the code-built one.

The local AI's remaster job (ai/remaster.py, on the Mac) makes these in Blender: a reference sheet from the drawing
room, a shape from the sculptor, the sheet projected onto the shape as its texture, scaled to the real object's size.
They land in assets/models_pending/ first; only approved ones are moved to assets/models/ and used here.
Every file is hashed into the manifest, so the frozen collection says exactly which models built it.
"""
import glob
import hashlib
import os

import bpy

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MODELS = os.path.join(ROOT, "assets", "models")


def path(name):
    p = os.path.join(MODELS, name, "model.glb")
    return p if os.path.exists(p) else None


def hashes():
    out = {}
    for f in sorted(glob.glob(os.path.join(MODELS, "*", "model.glb"))):
        with open(f, "rb") as fh:
            out["models/" + os.path.basename(os.path.dirname(f))] = hashlib.sha256(fh.read()).hexdigest()
    return out


def load(name, coll):
    """Import the model and return it as one mesh object, linked into coll, centered, in meters."""
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=path(name))
    new = [o for o in bpy.data.objects if o not in before]
    meshes = [o for o in new if o.type == "MESH"]
    for o in new:
        for c in list(o.users_collection):
            c.objects.unlink(o)
    for o in meshes:                      # bake each part's placement into its vertices, then join into one
        o.data = o.data.copy()
        o.data.transform(o.matrix_world)
        o.matrix_world.identity()
    ob = meshes[0]
    if len(meshes) > 1:
        coll.objects.link(ob)
        for o in meshes[1:]:
            coll.objects.link(o)
        with bpy.context.temp_override(active_object=ob, selected_editable_objects=meshes):
            bpy.ops.object.join()
    else:
        coll.objects.link(ob)
    for o in new:
        if o != ob and o.name in bpy.data.objects and not o.users_collection:
            bpy.data.objects.remove(o)
    ob.name = name
    return ob
