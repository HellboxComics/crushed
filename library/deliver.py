"""THE DELIVERY CHECK: before an asset folder goes into your Asset Library, every file in it is opened again from
scratch, the way another program would open it. The folder is filed only if every one of them opens whole.

    python deliver.py <folder> [name]     prints the check (JSON); ends with an error code if it failed
    import deliver; deliver.verify(folder) -> {"ok", "files", "missing", "problems", "not_possible"}

Each 3D file is opened in a fresh Blender (its own process - nothing carried over from the build):
  .blend  every picture is packed inside it and loads; it links to no other .blend
  .glb    opens, has mesh parts, its pictures load
  .fbx    opens, has mesh parts, its pictures are embedded in it (not linked to a file somewhere else) and load
  .obj    opens with its .mtl; every picture the .mtl names is in this folder (a relative path) and loads
  .usdc   opens, has mesh parts; every picture it names is in this folder and loads
  .3ds    Blender 5 has no 3D Studio reader, so the file is read here chunk by chunk: every length adds up, every
          face points at a real vertex, one smoothing entry per face, its pictures are in this folder
  .ma     read here: every node it connects exists, every mesh's numbers add up, picture paths are relative and
          the pictures are there
  textures/   every map as a PNG and a JPG pair        previews/   every picture as a PNG and a JPG pair
Not possible on this Mac (never reported as present): .max and .c4d - see NOT_POSSIBLE.
"""
import json
import os
import re
import struct
import subprocess
import sys

PY = sys.executable
FORMATS = ("blend", "fbx", "glb", "usdc", "obj", "mtl", "3ds", "ma")
NOT_POSSIBLE = {
    ".max": "only 3ds Max itself can write a .max file, and 3ds Max does not run on a Mac. "
            "3ds Max opens the .fbx (and the .3ds and .obj) in this folder.",
    ".c4d": "writing a .c4d file needs Cinema 4D itself or Maxon's Cineware library, which needs your own sign-up "
            "with Maxon. Cinema 4D opens the .fbx (and the .obj and .3ds) in this folder.",
}
OPEN_TIMEOUT = 300          # seconds for Blender to open one file


def _inside(folder, p):
    f, q = os.path.realpath(folder), os.path.realpath(p)
    return q == f or q.startswith(f + os.sep)


def _is_abs(p):
    return os.path.isabs(p) or bool(re.match(r"^[A-Za-z]:[\\/]", p)) or p.startswith("\\\\")


def _find(folder, rel):
    """rel inside folder, matching upper/lower case loosely (the Mac's disk ignores case; 3D Studio names are
    upper case). -> the real path or None"""
    rel = rel.replace("\\", "/")
    p = os.path.join(folder, rel)
    if os.path.exists(p):
        return p
    cur = folder
    for part in rel.split("/"):
        if not os.path.isdir(cur):
            return None
        hit = next((n for n in os.listdir(cur) if n.lower() == part.lower()), None)
        if not hit:
            return None
        cur = os.path.join(cur, hit)
    return cur


# ---------------------------------------------------------------- inside the fresh Blender (python deliver.py --open)
def _open_in_blender(kind, path, folder):
    import bpy
    out = {"kind": kind, "meshes": 0, "faces": 0, "pictures": [], "problems": []}
    P = out["problems"]
    if kind == "blend":
        bpy.ops.wm.open_mainfile(filepath=path, load_ui=False)
        if len(bpy.data.libraries):
            P.append("it links to other .blend files (" + ", ".join(l.filepath for l in bpy.data.libraries) +
                     ") - it would break when moved")
    else:
        bpy.ops.wm.read_factory_settings(use_empty=True)
        {"glb": lambda: bpy.ops.import_scene.gltf(filepath=path),
         "fbx": lambda: bpy.ops.import_scene.fbx(filepath=path),
         "obj": lambda: bpy.ops.wm.obj_import(filepath=path),
         "usdc": lambda: bpy.ops.wm.usd_import(filepath=path)}[kind]()
    meshes = [o for o in bpy.data.objects if o.type == "MESH"]
    out["meshes"] = len(meshes)
    out["faces"] = sum(len(o.data.polygons) for o in meshes)
    if not meshes or not out["faces"]:
        P.append("it opens with no 3D parts in it")
    for img in bpy.data.images:
        if img.type != "IMAGE" or img.source not in ("FILE", "TILED", "SEQUENCE"):
            continue
        fp = bpy.path.abspath(img.filepath) if img.filepath else ""
        packed = img.packed_file is not None
        try:
            w, h = img.size[0], img.size[1]          # reading the size loads the picture
        except Exception:
            w = h = 0
        out["pictures"].append({"name": img.name, "packed": packed, "path": fp, "size": [w, h]})
        where = f"picture '{img.name}'"
        if kind in ("blend", "fbx", "glb") and not packed:
            P.append(f"{where} is not inside the file - it points to {fp or 'nothing'}, which breaks when the "
                     f"folder moves")
        elif kind in ("obj", "usdc") and not packed:
            if not fp or not os.path.exists(fp):
                P.append(f"{where} is missing (it names {img.filepath or 'nothing'})")
            elif not _inside(folder, fp):
                P.append(f"{where} points outside this folder ({fp}), which breaks when the folder moves")
        if not w or not h:
            P.append(f"{where} does not load")
    if kind == "glb":
        out["contract"] = _contract_in_blender(meshes, os.path.splitext(os.path.basename(path))[0])
        P += out["contract"]["problems"]
    return out


def _contract_in_blender(meshes, asset):
    """THE DELIVERABLE CONTRACT, checked on the re-imported .glb (audit 2026-10-04, RC8): every part has a UV map,
    carries its physics (part, material_kind), is a Principled material, and its pictures are named by what they
    are (<asset>_<part>_<map>). The size is checked outside, against the catalog (verify size_m)."""
    import bpy
    c = {"parts": {}, "problems": [], "bbox_m": None}
    lo = [1e9] * 3
    hi = [-1e9] * 3
    for o in meshes:
        me = o.data
        rec = {"uv": bool(me.uv_layers), "part": o.get("part"), "material_kind": o.get("material_kind"),
               "materials": [s.material.name for s in o.material_slots if s.material], "pictures": []}
        if not rec["uv"]:
            c["problems"].append(f"part '{o.name}' has no UV map")
        if not rec["part"] or not rec["material_kind"]:
            c["problems"].append(f"part '{o.name}' carries no physics (part / material_kind)")
        for sl in o.material_slots:
            m = sl.material
            if not m:
                continue
            if not m.use_nodes or not any(n.type == "BSDF_PRINCIPLED" for n in m.node_tree.nodes):
                c["problems"].append(f"part '{o.name}': material '{m.name}' is not a Principled BSDF")
                continue
            for n in m.node_tree.nodes:
                if n.type == "TEX_IMAGE" and n.image:
                    nm = n.image.name
                    rec["pictures"].append(nm)
                    stem = os.path.splitext(nm)[0]
                    if not (stem.startswith(asset + "_") and stem.rsplit("_", 1)[-1] in ("base", "mr", "normal", "coat")):
                        c["problems"].append(f"part '{o.name}': picture '{nm}' is not named <asset>_<part>_<map>")
        if not o.get("beyond_size"):
            for v in o.bound_box:
                w = o.matrix_world @ __import__("mathutils").Vector(v)
                for i in range(3):
                    lo[i], hi[i] = min(lo[i], w[i]), max(hi[i], w[i])
        c["parts"][o.name] = rec
    if lo[0] < 1e8:
        c["bbox_m"] = [round(hi[i] - lo[i], 5) for i in range(3)]
    c["problems"] = sorted(set(c["problems"]))[:20]
    return c


def _blender(kind, path, folder, timeout=OPEN_TIMEOUT):
    """-> (result dict or None, problems)"""
    try:
        r = subprocess.run([PY, os.path.abspath(__file__), "--open", kind, path, folder],
                           capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return None, [f"Blender took longer than {timeout // 60} minutes to open it and was stopped"]
    line = next((l for l in reversed((r.stdout or "").splitlines()) if l.startswith("DELIVER_RESULT ")), None)
    if not line:
        tail = " ".join(((r.stderr or "") + (r.stdout or "")).strip().splitlines()[-3:])[-300:]
        return None, [f"Blender could not open it (exit code {r.returncode}): {tail}"]
    d = json.loads(line[len("DELIVER_RESULT "):])
    return d, d.get("problems", [])


# ---------------------------------------------------------------- .3ds, read chunk by chunk
_CONTAINERS = {0x4D4D, 0x3D3D, 0x4100, 0xAFFF, 0xA010, 0xA020, 0xA030, 0xA200, 0xA204, 0xA210, 0xA220, 0xA230,
               0xA33A, 0xA33C, 0xB000}


def _check_3ds(path, folder):
    data = open(path, "rb").read()
    info = {"objects": 0, "vertices": 0, "faces": 0, "smooth_faces": 0, "materials": [], "pictures": []}
    P = []
    if len(data) < 6:
        return info, ["it is too small to be a 3D Studio file"]
    cid, ln = struct.unpack_from("<HI", data, 0)
    if cid != 0x4D4D:
        P.append("it does not start like a 3D Studio file")
    if ln != len(data):
        P.append(f"it says it is {ln} bytes long but it is {len(data)}")
    st = {"nv": None, "nf": None, "used": set()}

    def cstr(off, end):
        z = data.find(b"\0", off, end)
        if z < 0:
            raise ValueError("a name with no end marker")
        return data[off:z].decode("ascii", "replace"), z + 1

    def walk(off, end):
        while off < end:
            if end - off < 6:
                P.append(f"{end - off} stray bytes at byte {off}")
                return
            cid, ln = struct.unpack_from("<HI", data, off)
            if ln < 6 or off + ln > end:
                P.append(f"the piece 0x{cid:04X} at byte {off} has a wrong length ({ln})")
                return
            b, e = off + 6, off + ln
            try:
                if cid in _CONTAINERS:
                    walk(b, e)
                elif cid == 0x4000:                                   # an object: its name, then its mesh
                    _, p = cstr(b, e)
                    info["objects"] += 1
                    st["nv"] = st["nf"] = None
                    walk(p, e)
                elif cid == 0x4110:                                   # vertices
                    n, = struct.unpack_from("<H", data, b)
                    if 2 + 12 * n != ln - 6:
                        P.append(f"a vertex list at byte {off} says {n} vertices but holds a different amount")
                    else:
                        vals = struct.unpack_from(f"<{3 * n}f", data, b + 2)
                        if any(v != v or abs(v) > 1e9 for v in vals):
                            P.append(f"a vertex list at byte {off} holds broken numbers")
                    st["nv"] = n
                    info["vertices"] += n
                elif cid == 0x4140:                                   # UVs: one per vertex
                    n, = struct.unpack_from("<H", data, b)
                    if 2 + 8 * n != ln - 6:
                        P.append(f"a UV list at byte {off} says {n} but holds a different amount")
                    if st["nv"] is not None and n != st["nv"]:
                        P.append(f"a UV list at byte {off} has {n} UVs for {st['nv']} vertices")
                elif cid == 0x4120:                                   # faces, then their material + smoothing
                    n, = struct.unpack_from("<H", data, b)
                    need = 2 + 8 * n
                    if need > ln - 6:
                        P.append(f"a face list at byte {off} says {n} faces but is too short")
                    else:
                        idx = struct.unpack_from(f"<{4 * n}H", data, b + 2)
                        top = max((v for i, v in enumerate(idx) if i % 4 != 3), default=-1)
                        if st["nv"] is None or top >= st["nv"]:
                            P.append(f"a face list at byte {off} points at vertex {top}, which does not exist")
                        st["nf"] = n
                        info["faces"] += n
                        walk(b + need, e)
                elif cid == 0x4130:                                   # which faces use which material
                    name, p = cstr(b, e)
                    n, = struct.unpack_from("<H", data, p)
                    if p + 2 + 2 * n != e:
                        P.append(f"the material list for '{name}' at byte {off} has a wrong length")
                    elif n and st["nf"] is not None and max(struct.unpack_from(f"<{n}H", data, p + 2)) >= st["nf"]:
                        P.append(f"the material list for '{name}' points at a face that does not exist")
                    st["used"].add(name)
                elif cid == 0x4150:                                   # smoothing groups: one per face
                    if st["nf"] is None or ln - 6 != 4 * st["nf"]:
                        P.append(f"the smoothing list at byte {off} does not have one entry per face")
                    else:
                        info["smooth_faces"] += sum(1 for g in struct.unpack_from(f"<{st['nf']}I", data, b) if g)
                elif cid == 0xA000:
                    info["materials"].append(cstr(b, e)[0])
                elif cid == 0xA300:                                   # a picture's file name
                    name = cstr(b, e)[0]
                    info["pictures"].append(name)
                    if _is_abs(name):
                        P.append(f"picture {name} is a full path on one computer - it breaks when moved")
                    elif not _find(folder, name):
                        P.append(f"picture {name} is not in the folder")
            except (struct.error, ValueError) as ex:
                P.append(f"the piece 0x{cid:04X} at byte {off} cannot be read: {ex}")
            off = e
    walk(6, min(ln, len(data)))
    if not info["objects"] or not info["faces"]:
        P.append("it holds no 3D parts")
    for m in sorted(st["used"] - set(info["materials"])):
        P.append(f"faces use the material '{m}', which the file does not define")
    return info, P


# ---------------------------------------------------------------- .ma (Maya ASCII), read as text
def _check_ma(path, folder):
    txt = open(path, encoding="utf-8", errors="replace").read()
    info = {"meshes": 0, "vertices": 0, "faces": 0, "hard_edges": 0, "soft_edges": 0, "materials": 0,
            "pictures": []}
    P = []
    if not txt.startswith("//Maya ASCII"):
        P.append("it does not start like a Maya ASCII file")
    nodes = {}
    for m in re.finditer(r'^createNode (\w+) -n "([^"]+)"', txt, re.M):
        if m.group(2) in nodes:
            P.append(f"the node '{m.group(2)}' is made twice")
        nodes[m.group(2)] = m.group(1)
    info["materials"] = sum(1 for t in nodes.values() if t == "shadingEngine")
    for m in re.finditer(r'^connectAttr "([^"]+)" "([^"]+)"', txt, re.M):
        for side in (m.group(1), m.group(2)):
            n = side.split(".")[0]
            if not n.startswith(":") and n not in nodes:
                P.append(f"a connection names the node '{n}', which the file never makes")
    for m in re.finditer(r'setAttr "\.(?:fileTextureName|ftn)" -type "string" "([^"]*)";', txt):
        p = m.group(1)
        info["pictures"].append(p)
        if _is_abs(p):
            P.append(f"picture {p} is a full path on one computer - it breaks when moved")
        elif not _find(folder, p):
            P.append(f"picture {p} is not in the folder")
    if sum(1 for t in nodes.values() if t == "file") != len(info["pictures"]):
        P.append("a picture node has no picture file set")
    for blk in re.split(r"(?m)^(?=createNode )", txt):
        if not blk.startswith("createNode mesh"):
            continue
        nm = re.match(r'createNode mesh -n "([^"]+)"', blk)
        nm = nm.group(1) if nm else "?"
        info["meshes"] += 1
        try:
            vt = re.search(r'setAttr -s (\d+) "\.vt\[0:(\d+)\]" ([^;]*);', blk)
            ed = re.search(r'setAttr -s (\d+) "\.ed\[0:(\d+)\]" ([^;]*);', blk)
            fc = re.search(r'setAttr -s (\d+) "\.fc\[0:(\d+)\]" -type "polyFaces" ([^;]*);', blk)
            uv = re.search(r'setAttr -s (\d+) "\.uvst\[0\]\.uvsp\[0:(\d+)\]" -type "float2" ([^;]*);', blk)
            if not (vt and ed and fc):
                P.append(f"mesh {nm} is missing its points, edges or faces")
                continue
            nv, ne, nf = int(vt.group(1)), int(ed.group(1)), int(fc.group(1))
            if len(vt.group(3).split()) != 3 * nv:
                P.append(f"mesh {nm}: {nv} points declared, a different amount written")
            ev = [int(x) for x in ed.group(3).split()]
            if len(ev) != 3 * ne:
                P.append(f"mesh {nm}: {ne} edges declared, a different amount written")
            elif ev and max(ev[0::3] + ev[1::3]) >= nv:
                P.append(f"mesh {nm}: an edge points at a point that does not exist")
            info["hard_edges"] += sum(1 for h in ev[2::3] if h == 0)
            info["soft_edges"] += sum(1 for h in ev[2::3] if h == 1)
            fs = re.findall(r"f 3 (-?\d+) (-?\d+) (-?\d+) mu 0 3 (\d+) (\d+) (\d+)", fc.group(3))
            if len(fs) != nf:
                P.append(f"mesh {nm}: {nf} faces declared, {len(fs)} written")
            nuv = int(uv.group(1)) if uv else 0
            for f in fs:
                if any((int(e) if int(e) >= 0 else -int(e) - 1) >= ne for e in f[:3]):
                    P.append(f"mesh {nm}: a face points at an edge that does not exist")
                    break
                if any(int(u) >= nuv for u in f[3:]):
                    P.append(f"mesh {nm}: a face points at a UV that does not exist")
                    break
            info["vertices"] += nv
            info["faces"] += nf
        except ValueError as ex:
            P.append(f"mesh {nm} cannot be read: {ex}")
    if not info["meshes"]:
        P.append("it holds no 3D parts")
    return info, P


# ---------------------------------------------------------------- .mtl and the .obj's link to it
def _check_mtl(path, folder):
    info, P = {"materials": 0, "pictures": []}, []
    for line in open(path, encoding="utf-8", errors="replace"):
        parts = line.split()
        if not parts:
            continue
        if parts[0] == "newmtl":
            info["materials"] += 1
        elif parts[0].lower().startswith(("map_", "bump", "disp", "norm", "refl")):
            p = parts[-1]
            info["pictures"].append(p)
            if _is_abs(p) or ".." in p.replace("\\", "/").split("/"):
                P.append(f"picture {p} is not a path inside this folder - it breaks when moved")
            elif not _find(folder, p):
                P.append(f"picture {p} is not in the folder")
    return info, P


def _obj_names_mtl(obj, mtl):
    with open(obj, encoding="utf-8", errors="replace") as f:
        for _, line in zip(range(200), f):
            if line.startswith("mtllib"):
                return line.split(None, 1)[1].strip() == os.path.basename(mtl)
    return False


# ---------------------------------------------------------------- PNG + JPG pairs
def _pairs(d, what):
    """Every picture in d as a PNG and a JPG of the same name and size. -> (info, missing, problems)"""
    from PIL import Image
    info, missing, P = {"pairs": 0}, [], []
    if not os.path.isdir(d):
        return info, [what + "/"], []
    files = [f for f in os.listdir(d) if os.path.isfile(os.path.join(d, f)) and not f.startswith(".")]
    stems = {}
    for f in files:
        stem, ext = os.path.splitext(f)
        if ext.lower() in (".png", ".jpg", ".jpeg"):
            stems.setdefault(stem, {})[".jpg" if ext.lower() == ".jpeg" else ext.lower()] = f
        elif ext.lower() in (".tif", ".tiff", ".exr", ".hdr", ".tga", ".bmp", ".webp"):
            P.append(f"{what}/{f} is not a PNG or JPG")
    for stem, have in sorted(stems.items()):
        for ext in (".png", ".jpg"):
            if ext not in have:
                missing.append(f"{what}/{stem}{ext}")
        if len(have) == 2:
            try:
                sizes = []
                for f in have.values():
                    with Image.open(os.path.join(d, f)) as im:
                        im.load()
                        sizes.append(im.size)
                if sizes[0] != sizes[1]:
                    P.append(f"{what}/{stem}: the PNG and the JPG are different sizes")
                else:
                    info["pairs"] += 1
            except Exception as ex:
                P.append(f"{what}/{stem}: a picture does not open ({ex})")
    if not stems:
        missing.append(f"{what}/ (no pictures in it)")
    return info, missing, P


# ---------------------------------------------------------------- the whole folder
def verify(folder, name=None, timeout=OPEN_TIMEOUT, size_m=None):
    folder = os.path.abspath(folder)
    res = {"ok": False, "folder": folder, "name": name, "files": {}, "missing": [], "problems": [],
           "not_possible": dict(NOT_POSSIBLE)}
    if not os.path.isdir(folder):
        res["problems"].append(f"the folder {folder} does not exist")
        return res
    if not name:
        blends = [f[:-6] for f in os.listdir(folder) if f.endswith(".blend")]
        name = blends[0] if len(blends) == 1 else os.path.basename(folder)
    res["name"] = name

    def note(fname, info, probs):
        res["files"][fname] = dict(info or {}, ok=not probs, problems=list(probs))
        res["problems"] += [f"{fname}: {p}" for p in probs]

    present = {}
    for ext in FORMATS:
        p = os.path.join(folder, f"{name}.{ext}")
        if not os.path.isfile(p):
            res["missing"].append(f"{name}.{ext}")
        elif os.path.getsize(p) == 0:
            note(f"{name}.{ext}", {}, ["it is empty (0 bytes)"])
        else:
            present[ext] = p
    blend_pics = None
    for ext in ("blend", "glb", "fbx", "obj", "usdc"):
        if ext not in present:
            continue
        d, probs = _blender(ext, present[ext], folder, timeout)
        info = {k: d[k] for k in ("meshes", "faces")} if d else {}
        if d:
            info["pictures"] = len(d["pictures"])
            if ext == "blend":
                blend_pics = len(d["pictures"])
            elif ext in ("glb", "fbx") and blend_pics and not d["pictures"]:
                probs = probs + ["it carries none of the model's pictures"]
            if ext == "glb" and d.get("contract"):
                info["contract"] = {"parts": len(d["contract"]["parts"]), "bbox_m": d["contract"].get("bbox_m")}
                bb = d["contract"].get("bbox_m")
                if size_m and bb:                       # real size, as the catalog says, once more on the re-import
                    want = sorted(float(x) for x in size_m[:3] if x)
                    got = sorted(bb)[-len(want):]
                    off = max(abs(g - w) / w for g, w in zip(got, want)) if want else 0
                    if off > 0.03:
                        probs = probs + [f"re-imported size {[round(x * 1000, 1) for x in bb]} mm is {off * 100:.0f}% off "
                                         f"the catalog's {[round(x * 1000, 1) for x in size_m[:3]]} mm"]
        note(f"{name}.{ext}", info, probs)
    if "obj" in present and "mtl" in present and not _obj_names_mtl(present["obj"], present["mtl"]):
        res["problems"].append(f"{name}.obj: it does not name {name}.mtl as its material file")
    for ext, fn in (("mtl", _check_mtl), ("3ds", _check_3ds), ("ma", _check_ma)):
        if ext in present:
            try:
                info, probs = fn(present[ext], folder)
            except Exception as ex:
                info, probs = {}, [f"it cannot be read: {ex}"]
            note(f"{name}.{ext}", info, probs)
    for sub in ("textures", "previews"):
        info, miss, probs = _pairs(os.path.join(folder, sub), sub)
        if sub == "textures" and not blend_pics and miss == ["textures/ (no pictures in it)"]:
            miss = []                                   # a model with no pictures at all needs no textures
        res["missing"] += miss
        note(sub + "/", info, probs)
    res["ok"] = not res["missing"] and not res["problems"]
    return res


# ---------------------------------------------------------------- helpers for putting a folder together (run.py)
def sha1(p):
    import hashlib
    h = hashlib.sha1()
    with open(p, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def picture_pair(src, dst_base):
    """src as dst_base.png (the same bytes when src is already a PNG) and dst_base.jpg (quality 92; any
    see-through part laid on neutral gray, since JPG can't hold it). -> [png, jpg]"""
    import shutil
    from PIL import Image
    png, jpg = dst_base + ".png", dst_base + ".jpg"
    with Image.open(src) as im:
        im.load()
        if im.format == "PNG":
            shutil.copy2(src, png)
        else:
            (im if im.mode in ("L", "LA", "RGB", "RGBA", "P") else im.convert("RGB")).save(png)
        if im.mode in ("I;16", "I;16B", "I;16L", "I", "F"):
            import numpy as np
            a = np.asarray(im).astype(float)
            im = Image.fromarray((np.clip(a / (65535.0 if a.max() > 255 else 255.0), 0, 1) * 255).astype("uint8"))
        if im.mode == "P":
            im = im.convert("RGBA")
        if im.mode in ("RGBA", "LA"):
            rgba = im.convert("RGBA")
            flat = Image.new("RGB", rgba.size, (128, 128, 128))
            flat.paste(rgba, mask=rgba.getchannel("A"))
        else:
            flat = im.convert("RGB")
        flat.save(jpg, "JPEG", quality=92)
    return [png, jpg]


_WHAT = {".blend": "Blender (every picture packed inside it - opens anywhere)",
         ".fbx": "FBX - opens in 3ds Max, Cinema 4D, Maya, Unity, Unreal (pictures embedded inside it)",
         ".glb": "glTF - web viewers and game engines (pictures inside it)",
         ".usdc": "USD - Apple Reality Composer, Pixar USD, NVIDIA Omniverse (pictures in textures/)",
         ".obj": "Wavefront OBJ - opens in almost everything (reads its materials from the .mtl)",
         ".mtl": "the .obj's materials: color, roughness, metal and normal pictures in textures/",
         ".3ds": "3D Studio - 3ds Max, Cinema 4D, Maya and most others (color pictures in textures/3ds/)",
         ".ma": "Maya ASCII - Maya 2020 or newer, on Maya's own Standard Surface material (pictures in textures/)",
         "physics.json": "how each part behaves when crushed",
         "made_of.json": "how the real one is made: its layers and materials",
         "README.txt": "this note"}
_PREVIEW = {"all_around": "the model from all around, in the same viewer as your phone page",
            "close_ups": "close-ups of the ends, seams and edges",
            "cutaway": "a quarter cut away, so the inside shows",
            "studio": "the four studio pictures",
            "made_from_photo": "the photo it was made from"}


def _describe(rel):
    base, ext = os.path.basename(rel), os.path.splitext(rel)[1].lower()
    stem = os.path.splitext(base)[0]
    if rel.startswith("textures/3ds/"):
        return "the same color picture under a short name, for the .3ds (see textures/names.txt)"
    if rel == "textures/names.txt":
        return "which short .3ds picture name is which texture map"
    if rel.startswith("textures/"):
        return "texture map " + ("(PNG, lossless)" if ext == ".png" else "(the same map as JPG)")
    if rel.startswith("previews/"):
        return _PREVIEW.get(stem, "check picture") + (" (PNG)" if ext == ".png" else " (JPG)")
    return _WHAT.get(base) or _WHAT.get(ext) or "file"


def dossier_lines(ds):
    """The research dossier's faces (where each side's artwork came from) and gaps, in plain words."""
    out = []
    faces = ds.get("faces") or {}
    items = faces.items() if isinstance(faces, dict) else \
        [(f.get("face") or f.get("side") or f.get("name") or "?", f) for f in faces if isinstance(f, dict)]
    for side, f in items:
        if isinstance(f, dict):
            src = f.get("source") or f.get("from") or f.get("what") or f.get("note") or "not recorded"
            url = f.get("page") or f.get("page_url") or f.get("url") or f.get("link") or ""
        else:
            src, url = str(f), ""
        out.append(f"  {side}: {src}")
        if url:
            out.append(f"      page: {url}")
    gaps = ds.get("gaps") or []
    if gaps:
        out += ["", "  What could not be found (made from the best evidence instead):"]
        for g in gaps:
            out.append("  - " + (g if isinstance(g, str) else str(g.get("what") or g.get("gap") or g.get("note") or
                                                                    json.dumps(g))))
    return out


def write_readme(folder, name, product, not_here, dossier=None):
    """README.txt listing exactly what is in the folder (walked from the disk, so it can't drift), what isn't and
    why, and - from the research dossier - where each side came from."""
    import time
    files = []
    for root, dirs, fs in os.walk(folder):
        dirs.sort()
        for f in sorted(fs):
            if not f.startswith("."):
                files.append(os.path.relpath(os.path.join(root, f), folder).replace(os.sep, "/"))
    if "README.txt" not in files:
        files.append("README.txt")
    w = max(len(f) for f in files) + 2
    L = [f"{product or name}", f"({name})", "", f"Put together and checked {time.strftime('%B %-d, %Y at %-I:%M %p')}. "
         "Real size, in meters. Every 3D file and picture below was opened again from scratch before this folder "
         "was filed.", "",
         "WHAT IS IN THIS FOLDER"]
    for f in files:
        p = os.path.join(folder, f)
        size = os.path.getsize(p) if os.path.exists(p) else 0
        mb = f"  ({size / 1048576:.1f} MB)" if size >= 1048576 else ""
        L.append(f"  {f.ljust(w)}{_describe(f)}{mb}")
    L += ["", "NOT IN THIS FOLDER, AND WHY"]
    for ext, why in NOT_POSSIBLE.items():
        L.append(f"  {ext}  - not possible on this Mac: {why}")
    for n in not_here:
        L.append(f"  {n}")
    L += ["", "OPENING IT",
          "  Pictures are found from this folder (textures/...), so keep the folder together when you move it.",
          "  Maya: if a picture shows missing, set the project to this folder (File > Set Project) and reopen."]
    if dossier:
        L += ["", "WHERE EACH SIDE CAME FROM"] + dossier_lines(dossier)
    open(os.path.join(folder, "README.txt"), "w").write("\n".join(L) + "\n")
    return files


def summary(res):
    """One plain line: why a check failed (or that it passed)."""
    if res.get("ok"):
        return "every file opened whole"
    bits = []
    if res.get("missing"):
        bits.append("missing " + ", ".join(res["missing"][:4]) + (" ..." if len(res["missing"]) > 4 else ""))
    if res.get("problems"):
        bits.append(res["problems"][0] + (f" (and {len(res['problems']) - 1} more)" if len(res["problems"]) > 1 else ""))
    return "; ".join(bits) or "unknown"


if __name__ == "__main__":
    if len(sys.argv) > 4 and sys.argv[1] == "--open":
        try:
            r = _open_in_blender(sys.argv[2], sys.argv[3], sys.argv[4])
        except Exception as e:
            r = {"problems": [f"it could not be opened: {e}"], "pictures": []}
        print("DELIVER_RESULT " + json.dumps(r), flush=True)
        sys.exit(0)
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    r = verify(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
    print(json.dumps(r, indent=1))
    print("[deliver]", "PASSED -" if r["ok"] else "FAILED -", summary(r))
    sys.exit(0 if r["ok"] else 1)
