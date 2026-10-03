"""SAVING A FINISHED MODEL SO IT OPENS ANYWHERE - the save step every builder in this folder shares.

    import saveall
    saveall.blend(out, name)                 every picture packed INSIDE the .blend, then saved
    ... the builder exports its .glb ...
    saveall.rest(out, name, "lathe")         .fbx with its pictures inside it, .usdc (+ its textures/ folder),
                                             and made.json

Why: the pictures used to be linked by their full path on this Mac (the build folder). Copied to the Asset Library,
the files kept pointing back into the build folder, and after a Redo moved that folder aside every texture showed
pink. Packed and embedded, the .blend and .fbx carry their own pictures and open anywhere.

made.json: what this build wrote - the size and fingerprint (sha1) of each file - and what it could not write and
why. A file left over from an older build has a different fingerprint, so it is never taken for this build's.
"""
import os as _os, sys as _sys  # noqa: E401
_sys.path.append(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import jsonsafe  # noqa: E402,F401  (numpy numbers are saved as plain numbers - see jsonsafe.py)
import hashlib
import json
import os
import time

import bpy

STARTED = None          # when this build began saving (every file it writes is newer)


def _fingerprint(p):
    h = hashlib.sha1()
    with open(p, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return {"bytes": os.path.getsize(p), "sha1": h.hexdigest()}


def blend(out, name):
    """Packs every picture the model uses into the .blend and saves it. A picture that can't be packed (its file is
    gone) stops the build here, with its name - it would show pink everywhere else."""
    global STARTED
    STARTED = time.time()
    bpy.ops.file.pack_all()
    loose = [img.name for img in bpy.data.images
             if img.users and img.source in ("FILE", "TILED", "SEQUENCE") and not img.packed_file]
    if loose:
        raise RuntimeError("these pictures could not be packed into the .blend (their files are missing): "
                           + ", ".join(loose))
    p = os.path.join(out, name + ".blend")
    bpy.ops.wm.save_as_mainfile(filepath=p)
    return p


def rest(out, name, tag, selected=True, extras=()):
    """The .fbx (pictures embedded in it) and the .usdc (as before, its pictures written fresh into textures/ next
    to it), then made.json. extras: other files this build wrote into out (e.g. physics.json) to fingerprint too."""
    base = os.path.join(out, name)
    failed = {}
    calls = (("fbx", lambda p: bpy.ops.export_scene.fbx(filepath=p, use_selection=selected, path_mode="COPY",
                                                         embed_textures=True)),
             ("usdc", lambda p: bpy.ops.wm.usd_export(filepath=p, selected_objects_only=selected,
                                                      overwrite_textures=True)))
    for fmt, call in calls:
        try:
            call(base + "." + fmt)
        except Exception as e:
            failed[fmt] = str(e)[:300]
            print(f"[{tag}] {fmt} export unavailable here: {e}")
    since = (STARTED or time.time()) - 2
    files = {}
    for ext in ("blend", "glb", "fbx", "usdc"):
        p = base + "." + ext
        if ext in failed:
            continue
        if not os.path.exists(p):
            failed[ext] = "not written"
        elif os.path.getmtime(p) < since:
            failed[ext] = "the file there is from an older build (this build did not write it)"
        else:
            files[ext] = _fingerprint(p)
    for x in extras:
        p = os.path.join(out, x)
        if os.path.exists(p):
            files[x] = _fingerprint(p)
    json.dump({"name": name, "by": tag, "started": STARTED, "at": time.time(), "files": files, "failed": failed},
              open(os.path.join(out, "made.json"), "w"), indent=1)
    for ext, why in failed.items():
        print(f"[{tag}] {ext}: {why}")
    return files, failed
