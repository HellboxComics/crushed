"""EVERY FORMAT, ONE FOLDER PER ASSET: from the finished .blend, writes the files other 3D programs open.

    python exports.py -- <asset>.blend <out_dir> <name>      (the Python that has Blender's bpy)

  <name>.blend  .fbx  .glb  .usdc   (written by the builder; the .blend and .fbx carry their pictures inside)
  <name>.obj + <name>.mtl          (Wavefront: opens in everything; .mtl = its materials, pictures in textures/)
  <name>.3ds                       (3D Studio: opens in 3ds Max, Cinema 4D, Maya and most others)
  <name>.ma                        (Maya ASCII)
  textures/<map>.png + .jpg        (every texture map: PNG lossless, JPG quality 92 - JPG has no see-through
                                    part, so any see-through area is laid on a neutral gray in the JPG)
  textures/3ds/*.PNG + names.txt   (the same maps under short 8.3 names, which 3D Studio files need; names.txt
                                    says which short name is which map)
  exports.json                     (what this run wrote and anything that failed - read by the delivery check)

Every run writes every file again (nothing from an older build is kept as if new) and stops with an error code
when anything failed, so a half-made set is never taken for a finished one.

Not here, and why: .max can only be written by 3ds Max itself; .c4d needs Maxon's Cineware library (with the
owner's sign-up). Both programs open the .fbx natively.

How the materials are wired, per format (Blender's own material is the truth for all of them):
  .mtl   map_Kd = base color; map_Pr / map_Pm = roughness / metalness read from one channel of the packed map
         (-imfchan g / b, the glTF layout these builders use); map_Bump -bm 1 = the normal map (Blender's own
         convention for OBJ normal maps)
  .3ds   base color map only (3D Studio has no roughness, metal or tangent-space normal maps); smoothing group 1
         on smooth faces, none on flat faces; vertices are split along sharp edges so those stay crisp too
  .ma    Maya's built-in standardSurface (Maya 2020 and newer; the same shader as Arnold's aiStandardSurface):
         file(sRGB).outColor -> baseColor; file(Raw).outColorG -> specularRoughness and .outColorB -> metalness
         (or .outColorR when the map is a plain gray roughness map); file(Raw).outAlpha -> bump2d.bumpValue with
         bumpInterp 1 (tangent-space normals), bump2d.outNormal -> normalCamera (Maya's standard normal-map
         wiring). Edges are hard where Blender's face is flat-shaded or the edge is marked sharp, soft elsewhere.
"""
import os as _os, sys as _sys  # noqa: E401
_sys.path.append(_os.path.dirname(_os.path.abspath(__file__)))
import jsonsafe  # noqa: E402,F401  (numpy numbers are saved as plain numbers - see jsonsafe.py)
import io
import json
import os
import re
import shutil
import struct
import sys
import time

import bpy
import numpy as np
from PIL import Image

argv = sys.argv[sys.argv.index("--") + 1:]
BLEND, OUT, NAME = argv[0], argv[1], argv[2]
STARTED = time.time()
TEX = os.path.join(OUT, "textures")
FAILED = []                  # (what, why) - anything here makes the run end with an error code
WROTE = []                   # every file this run wrote, relative to OUT
TEXTURES = {}                # Blender image name -> {"stem", "png", "jpg", "alpha"}


def say(*a):
    print("[exports]", *a, flush=True)


def _wrote(p):
    rel = os.path.relpath(p, OUT)
    if rel not in WROTE:
        WROTE.append(rel)


def _write_atomic(path, data, mode="wb"):
    """Writes the whole file next to its place, then swaps it in: an older file of that name is always replaced,
    and a half-written file never sits under the real name."""
    tmp = path + ".part"
    with open(tmp, mode) as f:
        f.write(data)
    os.replace(tmp, path)
    _wrote(path)


bpy.ops.wm.open_mainfile(filepath=os.path.abspath(BLEND))
os.makedirs(os.path.join(TEX, "3ds"), exist_ok=True)


# ---------------------------------------------------------------- the model, ready for every writer
def meshes():
    """Every mesh part, evaluated (modifiers applied), in world space, triangulated. Per triangle:
    (material index, smooth?, region, [(position, uv, vertex id) x3], [edge hard? x3]).
    region: smooth faces joined across soft edges share one region; a sharp edge (or a flat face) starts a new one,
    so writers that can't store per-edge hardness split vertices there instead."""
    import bmesh
    dg = bpy.context.evaluated_depsgraph_get()
    for ob in bpy.context.scene.objects:
        if ob.type != "MESH" or ob.hide_render:
            continue
        ev = ob.evaluated_get(dg)
        me = ev.to_mesh()
        bm = bmesh.new()
        bm.from_mesh(me)
        bm.verts.ensure_lookup_table()
        bm.faces.ensure_lookup_table()
        sharp = {frozenset((e.verts[0].index, e.verts[1].index)) for e in bm.edges if not e.smooth}
        parent = list(range(len(bm.faces)))           # smooth regions (union-find over soft edges)

        def root(i):
            while parent[i] != i:
                parent[i] = parent[parent[i]]
                i = parent[i]
            return i
        for e in bm.edges:
            lf = [f for f in e.link_faces if f.smooth]
            if e.smooth and len(lf) == len(e.link_faces) and len(lf) > 1:
                for f in lf[1:]:
                    parent[root(f.index)] = root(lf[0].index)
        reg = bm.faces.layers.int.new("crushed_region")
        for f in bm.faces:
            f[reg] = root(f.index)
        bmesh.ops.triangulate(bm, faces=bm.faces)
        bm.transform(ob.matrix_world)
        uvl = bm.loops.layers.uv.active
        tris = []
        for f in bm.faces:
            corners, hard = [], []
            for lp in f.loops:
                corners.append((tuple(lp.vert.co), tuple(lp[uvl].uv) if uvl else (0.0, 0.0), lp.vert.index))
                e = lp.edge
                key = frozenset((e.verts[0].index, e.verts[1].index))
                hard.append(key in sharp or any(not g.smooth for g in e.link_faces))
            tris.append((f.material_index, bool(f.smooth), f[reg], corners, hard))
        mats = [m for m in ob.data.materials] or [None]
        bm.free()
        ev.to_mesh_clear()
        yield ob.name, tris, mats


MESHES = list(meshes())
if not MESHES:
    FAILED.append(("the model", "the .blend has no mesh parts to export"))


# ---------------------------------------------------------------- textures: every map as PNG and JPG
def _unique_stem(img):
    src = img.filepath_raw or img.filepath
    base = os.path.splitext(os.path.basename(bpy.path.abspath(src)))[0] if src else ""
    base = re.sub(r"[^A-Za-z0-9_.\-]+", "_", base or img.name).strip("._") or "texture"
    taken = {t["stem"].lower() for t in TEXTURES.values()}          # the Mac's disk ignores upper/lower case
    stem, k = base, 2
    while stem.lower() in taken:
        stem, k = f"{base}_{k}", k + 1
    return stem


def _pil_of(img):
    """The picture as PIL, from its own file bytes (packed inside the .blend, or its file on disk), else from
    Blender's pixels. -> (PIL image, the original bytes if they are already a PNG file)"""
    raw = None
    if img.packed_file:
        raw = bytes(img.packed_file.data)
    else:
        src = bpy.path.abspath(img.filepath) if img.filepath else ""
        if src and os.path.exists(src):
            raw = open(src, "rb").read()
    if raw:
        try:
            im = Image.open(io.BytesIO(raw))
            im.load()
            return im, (raw if raw[:8] == b"\x89PNG\r\n\x1a\n" else None)
        except Exception:
            pass                                       # e.g. EXR/HDR: PIL can't read it - Blender's pixels below
    w, h = img.size
    if not w or not h:
        raise RuntimeError("the picture has no pixels (its file is missing and it is not packed)")
    a = np.array(img.pixels[:], dtype=np.float32).reshape(h, w, img.channels)[::-1]
    a = (np.clip(a, 0, 1) * 255 + 0.5).astype(np.uint8)
    mode = {1: "L", 2: "LA", 3: "RGB", 4: "RGBA"}[img.channels]
    return Image.fromarray(a if img.channels > 1 else a[..., 0], mode), None


def _to8(im):
    """16-bit and float pictures to 8-bit (JPG holds only 8-bit)."""
    if im.mode in ("I;16", "I;16B", "I;16L", "I", "F"):
        a = np.asarray(im).astype(np.float64)
        top = 65535.0 if a.max() > 255 else 255.0
        return Image.fromarray((np.clip(a / top, 0, 1) * 255 + 0.5).astype(np.uint8), "L")
    return im


def save_texture(img):
    """textures/<stem>.png (the picture's own PNG bytes when it is a PNG, else converted, lossless) and
    textures/<stem>.jpg (quality 92; any see-through part laid on neutral gray). -> its record"""
    if img.name in TEXTURES:
        return TEXTURES[img.name]
    stem = _unique_stem(img)
    im, png_bytes = _pil_of(img)
    if im.mode not in ("1", "L", "LA", "P", "RGB", "RGBA", "I", "I;16", "I;16B", "I;16L", "F"):
        im = im.convert("RGBA" if "A" in im.getbands() else "RGB")      # e.g. a CMYK JPEG: PNG can't hold CMYK
    png, jpg = os.path.join(TEX, stem + ".png"), os.path.join(TEX, stem + ".jpg")
    if png_bytes:
        _write_atomic(png, png_bytes)
    else:
        b = io.BytesIO()
        (_to8(im) if im.mode == "F" else im).save(b, "PNG")
        _write_atomic(png, b.getvalue())
    im8 = _to8(im)
    if im8.mode == "P":
        im8 = im8.convert("RGBA")
    alpha = im8.mode in ("RGBA", "LA") and im8.getchannel("A").getextrema()[0] < 255
    if im8.mode in ("RGBA", "LA"):
        rgba = im8.convert("RGBA")
        flat = Image.new("RGB", rgba.size, (128, 128, 128))
        flat.paste(rgba, mask=rgba.getchannel("A"))
    else:
        flat = im8.convert("RGB")
    b = io.BytesIO()
    flat.save(b, "JPEG", quality=92)
    _write_atomic(jpg, b.getvalue())
    TEXTURES[img.name] = {"stem": stem, "png": f"textures/{stem}.png", "jpg": f"textures/{stem}.jpg",
                          "alpha": bool(alpha), "image": img.name}
    return TEXTURES[img.name]


def save_all_textures():
    for img in bpy.data.images:
        if img.type not in ("IMAGE", "UV_TEST") or (not img.users and not img.packed_file):
            continue
        try:
            save_texture(img)
        except Exception as e:
            FAILED.append((f"texture {img.name}", str(e)))
            say(f"texture {img.name} FAILED: {e}")


# ---------------------------------------------------------------- what feeds each material input
def _source(sock, depth=0):
    """Walks back from a shader input to the picture feeding it. -> (image, channel or None) or (None, None).
    channel: 'R' / 'G' / 'B' when it passes a Separate Color node (one channel of a packed map)."""
    if depth > 12 or not sock.is_linked:
        return None, None
    lk = sock.links[0]
    n, out = lk.from_node, lk.from_socket
    if n.type == "TEX_IMAGE":
        return (n.image, "A" if out.name == "Alpha" else None) if n.image else (None, None)
    if n.type in ("SEPARATE_COLOR", "SEPRGB", "SEPARATE_RGB"):
        ch = {"Red": "R", "Green": "G", "Blue": "B", "R": "R", "G": "G", "B": "B"}.get(out.name)
        img, _ = _source(n.inputs[0], depth + 1)
        return img, ch
    if n.type == "NORMAL_MAP":
        return _source(n.inputs["Color"], depth + 1)
    for inp in n.inputs:                                  # a mix / curve / bump in between: follow what feeds it
        if inp.is_linked and inp.type in ("RGBA", "VALUE", "VECTOR"):
            img, ch = _source(inp, depth + 1)
            if img:
                return img, ch
    return None, None


def _bsdf(mat):
    if not mat or not mat.node_tree:
        return None
    for n in mat.node_tree.nodes:
        if n.type == "BSDF_PRINCIPLED":
            return n
    return None


def maps_of(mat):
    """{'base': (rec, None), 'rough': (rec, ch), 'metal': (rec, ch), 'normal': (rec, None)} - texture records."""
    b, out = _bsdf(mat), {}
    if not b:
        return out
    for key, inp in (("base", "Base Color"), ("rough", "Roughness"), ("metal", "Metallic"), ("normal", "Normal")):
        if inp in b.inputs:
            img, ch = _source(b.inputs[inp])
            if img and img.name in TEXTURES:
                out[key] = (TEXTURES[img.name], ch)
    return out


def base_color(mat):
    b = _bsdf(mat)
    return tuple(b.inputs["Base Color"].default_value[:3]) if b else (0.8, 0.8, 0.8)


def scalar(mat, inp, d):
    b = _bsdf(mat)
    try:
        return float(b.inputs[inp].default_value) if b else d
    except Exception:
        return d


# ---------------------------------------------------------------- .obj + .mtl (Blender's own writer)
def write_obj():
    obj, mtl = os.path.join(OUT, NAME + ".obj"), os.path.join(OUT, NAME + ".mtl")
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.wm.obj_export(filepath=obj, export_materials=True, path_mode="STRIP", export_uv=True,
                          export_normals=True, apply_modifiers=True, forward_axis="NEGATIVE_Z", up_axis="Y")
    if not os.path.exists(obj) or os.path.getmtime(obj) < STARTED - 2:
        raise RuntimeError("Blender's OBJ writer did not write the .obj")
    _wrote(obj)
    if not os.path.exists(mtl):
        raise RuntimeError("Blender's OBJ writer did not write the .mtl")
    # the material file's picture lines are written again from Blender's own material (the writer only knows a
    # picture plugged straight into a socket, and names packed pictures by their old file names)
    by_name = {}
    for m in bpy.data.materials:
        by_name[m.name] = m
        by_name.setdefault(m.name.replace(" ", "_"), m)
    out, cur = [], None
    for line in open(mtl).read().splitlines() + ["newmtl __end__"]:
        parts = line.split()
        if parts and parts[0] == "newmtl":
            if cur is not None:
                while out and not out[-1].strip():
                    out.pop()
                out += _mtl_maps(by_name.get(cur)) + [""]
            cur = line[len("newmtl"):].strip()
            if cur == "__end__":
                break
        if parts and parts[0].lower().startswith(("map_", "bump", "disp", "norm", "refl")):
            continue
        out.append(line)
    _write_atomic(mtl, "\n".join(out) + "\n", "w")


def _mtl_maps(mat):
    mp = maps_of(mat)
    lines = []
    if "base" in mp:
        lines.append(f"map_Kd {mp['base'][0]['png']}")
    for key, tag in (("rough", "map_Pr"), ("metal", "map_Pm")):
        if key in mp:
            rec, ch = mp[key]
            chan = {"R": "r", "G": "g", "B": "b", "A": "m"}.get(ch, "l")    # m = the alpha (matte) channel
            lines.append(f"{tag} -imfchan {chan} {rec['png']}")
    if "normal" in mp:
        lines.append(f"map_Bump -bm 1.000000 {mp['normal'][0]['png']}")
    return lines


# ---------------------------------------------------------------- .3ds (3D Studio binary, chunk format)
def _chunk(cid, data):
    return struct.pack("<HI", cid, 6 + len(data)) + data


def _cstr(s):
    return s.encode("ascii", "replace") + b"\0"


def _short_names(limit, names):
    """Unique short names (3D Studio cuts names short; two long names that start alike must not become one)."""
    out, taken = {}, set()
    for n in names:
        clean = re.sub(r"[^A-Za-z0-9_]", "_", n) or "x"
        s = clean[:limit]
        k = 1
        while s.lower() in taken:
            tail = f"{k:0{max(2, len(str(k)))}d}"
            s = clean[:limit - len(tail)] + tail
            k += 1
        taken.add(s.lower())
        out[n] = s
    return out


def write_3ds():
    tex_short = {}                                     # texture stem -> 8.3 file name
    taken = set()
    used = {}                                          # 3D Studio reads one color map per material: only those
    for _, _, mlist in MESHES:
        for mat in mlist:
            b = maps_of(mat).get("base")
            if b:
                used[b[0]["stem"]] = b[0]
    for rec in used.values():
        base = re.sub(r"[^A-Z0-9]", "", rec["stem"].upper())[:5] or "TEX"
        k = 1
        while f"{base}{k:03d}" in taken:
            k += 1
        short = f"{base}{k:03d}"
        taken.add(short)
        tex_short[rec["stem"]] = short + ".PNG"
        src = os.path.join(OUT, rec["png"])
        _write_atomic(os.path.join(TEX, "3ds", short + ".PNG"), open(src, "rb").read())
    lines = ["Short names used by the .3ds file (3D Studio only reads names of 8 letters + 3).",
             "Each short-named picture in textures/3ds/ is an exact copy of the full-named one in textures/.", ""]
    lines += [f"textures/3ds/{s}  =  textures/{stem}.png" for stem, s in sorted(tex_short.items(), key=lambda x: x[1])]
    if not tex_short:
        lines.append("(none - no part of this model has a color picture, so the .3ds needs no short names)")
    _write_atomic(os.path.join(TEX, "names.txt"), "\n".join(lines) + "\n", "w")

    mats_used, objs = {}, []
    for oname, tris, mlist in MESHES:
        groups = {}
        for t in tris:
            groups.setdefault(t[0], []).append(t)
        for mi, faces in groups.items():
            mat = mlist[mi] if mi < len(mlist) else None
            mats_used[mat.name if mat else "default"] = mat
            # 3DS keeps one UV per vertex and at most 65,535 of each: split into pieces as needed. Vertices are
            # split where smooth regions meet (sharp edges) and for flat faces, so those stay crisp.
            verts, index, out_faces, smooth = [], {}, [], []
            for _, sm, region, corners, _hard in faces:
                ids = []
                for k_, (co, uv, vid) in enumerate(corners):
                    key = (vid, round(uv[0], 6), round(uv[1], 6), region if sm else ("flat", len(out_faces)))
                    if key not in index:
                        index[key] = len(verts)
                        verts.append((co, uv))
                    ids.append(index[key])
                out_faces.append(ids)
                smooth.append(1 if sm else 0)
                if len(verts) > 65000 or len(out_faces) > 65000:
                    objs.append((oname, verts, out_faces, smooth, mat))
                    verts, index, out_faces, smooth = [], {}, [], []
            if out_faces:
                objs.append((oname, verts, out_faces, smooth, mat))
    mshort = _short_names(16, list(mats_used))                     # 3DS material names: 16 letters
    edit = _chunk(0x3D3E, struct.pack("<I", 3))
    for mname, mat in mats_used.items():
        mp = maps_of(mat)
        body = _chunk(0xA000, _cstr(mshort[mname]))
        body += _chunk(0xA020, _chunk(0x0011, bytes(int(max(0, min(1, c)) * 255 + 0.5) for c in base_color(mat))))
        if "base" in mp:
            body += _chunk(0xA200, _chunk(0x0030, struct.pack("<H", 100)) +
                           _chunk(0xA300, _cstr("textures/3ds/" + tex_short[mp["base"][0]["stem"]])))
        edit += _chunk(0xAFFF, body)
    names = _short_names(10, [f"{o[0]}~{i}" for i, o in enumerate(objs)])   # 3DS object names: 10 letters
    for i, (oname, verts, faces, smooth, mat) in enumerate(objs):
        mname = mshort[mat.name if mat else "default"]
        pts = struct.pack("<H", len(verts)) + b"".join(struct.pack("<3f", *co) for co, _ in verts)
        uvs = struct.pack("<H", len(verts)) + b"".join(struct.pack("<2f", *uv) for _, uv in verts)
        fc = struct.pack("<H", len(faces)) + b"".join(struct.pack("<4H", a, b, c, 7) for a, b, c in faces)
        grp = _chunk(0x4130, _cstr(mname) + struct.pack("<H", len(faces)) +
                     b"".join(struct.pack("<H", k) for k in range(len(faces))))
        smg = _chunk(0x4150, b"".join(struct.pack("<I", s) for s in smooth))   # smoothing group per face
        mesh = _chunk(0x4110, pts) + _chunk(0x4140, uvs) + _chunk(0x4120, fc + grp + smg)
        nm = names[f"{oname}~{i}"]
        edit += _chunk(0x4000, _cstr(nm) + _chunk(0x4100, mesh))
    data = _chunk(0x4D4D, _chunk(0x0002, struct.pack("<I", 3)) + _chunk(0x3D3D, edit))
    _write_atomic(os.path.join(OUT, NAME + ".3ds"), data)


# ---------------------------------------------------------------- .ma (Maya ASCII)
def _safe(s):
    s = "".join(c if c.isalnum() else "_" for c in s) or "part"
    return ("n_" + s) if s[0].isdigit() else s


def _ranges(ids):
    """[0,1,2,5,7,8] -> ['f[0:2]', 'f[5]', 'f[7:8]']"""
    out, start, prev = [], None, None
    for i in sorted(ids):
        if start is None:
            start = prev = i
        elif i == prev + 1:
            prev = i
        else:
            out.append(f'"f[{start}]"' if start == prev else f'"f[{start}:{prev}]"')
            start = prev = i
    if start is not None:
        out.append(f'"f[{start}]"' if start == prev else f'"f[{start}:{prev}]"')
    return out


def write_ma():
    L = ['//Maya ASCII 2020 scene', f'//Name: {NAME}.ma', 'requires maya "2020";',
         'currentUnit -l centimeter -a degree -t film;', 'fileInfo "application" "maya";']
    used_names, shading, connects = set(), {}, []

    def unique(n, suffixes=("",)):
        """A base name whose nodes (base + each suffix) are all still free in the scene; claims them."""
        k, base = 2, n
        while any(n + s in used_names for s in suffixes):
            n, k = f"{base}_{k}", k + 1
        used_names.update(n + s for s in suffixes)
        return n
    for oname, tris, mlist in MESHES:
        safe = unique(_safe(oname), ("", "Shape"))
        verts, vindex, uvs, uvindex, edges, eindex, hard_of, faces = [], {}, [], {}, [], {}, {}, []
        for mi, sm, region, corners, hard in tris:
            vids, uids = [], []
            for co, uv, vid in corners:
                if vid not in vindex:
                    vindex[vid] = len(verts)
                    verts.append(co)
                vids.append(vindex[vid])
                ku = (round(uv[0], 6), round(uv[1], 6))
                if ku not in uvindex:
                    uvindex[ku] = len(uvs)
                    uvs.append(ku)
                uids.append(uvindex[ku])
            es = []
            for k_, (a, b) in enumerate(((vids[0], vids[1]), (vids[1], vids[2]), (vids[2], vids[0]))):
                if (a, b) in eindex:
                    ei = eindex[(a, b)]
                    es.append(ei)
                elif (b, a) in eindex:
                    ei = eindex[(b, a)]
                    es.append(-ei - 1)                  # the edge, run backwards
                else:
                    ei = eindex[(a, b)] = len(edges)
                    edges.append((a, b))
                    es.append(ei)
                hard_of[ei] = hard_of.get(ei, False) or hard[k_]
            faces.append((mi, es, uids))
        if not faces:
            continue
        L.append(f'createNode transform -n "{safe}";')
        L.append(f'createNode mesh -n "{safe}Shape" -p "{safe}";')
        L.append('\tsetAttr -k off ".v";')
        L.append('\tsetAttr ".uvst[0].uvsn" -type "string" "map1";')
        L.append(f'\tsetAttr -s {len(uvs)} ".uvst[0].uvsp[0:{len(uvs) - 1}]" -type "float2" ' +
                 " ".join(f"{u:.6f} {v:.6f}" for u, v in uvs) + ";")
        L.append('\tsetAttr ".cuvs" -type "string" "map1";')
        # Blender is Z-up in meters; Maya here is Y-up in centimeters
        L.append(f'\tsetAttr -s {len(verts)} ".vt[0:{len(verts) - 1}]" ' +
                 " ".join(f"{x * 100:.5f} {z * 100:.5f} {-y * 100:.5f}" for x, y, z in verts) + ";")
        # third number per edge: 1 = soft (smooth shading across it), 0 = hard - from Blender's flat/sharp data
        L.append(f'\tsetAttr -s {len(edges)} ".ed[0:{len(edges) - 1}]" ' +
                 " ".join(f"{a} {b} {0 if hard_of.get(i) else 1}" for i, (a, b) in enumerate(edges)) + ";")
        L.append(f'\tsetAttr -s {len(faces)} ".fc[0:{len(faces) - 1}]" -type "polyFaces" ' +
                 " ".join(f"f 3 {e[0]} {e[1]} {e[2]} mu 0 3 {u[0]} {u[1]} {u[2]}" for _, e, u in faces) + ";")
        by_mat = {}
        for i, (mi, _, _) in enumerate(faces):
            by_mat.setdefault(mi, []).append(i)
        for mi, ids in by_mat.items():
            mat = mlist[mi] if mi < len(mlist) else None
            key = mat.name if mat else "default"
            if key not in shading:
                shading[key] = (unique(_safe(key), ("_mat", "_SG", "_info")), mat)
            connects.append((safe, shading[key][0], ids if len(by_mat) > 1 else None))
    files = {}                                          # (texture stem, color space) -> file node name

    def file_node(rec, raw):
        k = (rec["stem"], raw)
        if k in files:
            return files[k], []
        n = unique(_safe(rec["stem"]) + ("_raw" if raw else "") + "_file")
        p = unique(n + "_p2d")
        files[k] = n
        lines = [f'createNode file -n "{n}";', f'\tsetAttr ".fileTextureName" -type "string" "{rec["png"]}";',
                 f'\tsetAttr ".colorSpace" -type "string" "{"Raw" if raw else "sRGB"}";']
        if raw:
            lines.append('\tsetAttr ".ignoreColorSpaceFileRules" yes;')
        lines += [f'createNode place2dTexture -n "{p}";',
                  f'connectAttr "{p}.outUV" "{n}.uvCoord";', f'connectAttr "{p}.outUvFilterSize" "{n}.uvFilterSize";',
                  f'connectAttr "{n}.message" ":defaultTextureList1.textures" -na;',
                  f'connectAttr "{p}.message" ":defaultRenderUtilityList1.utilities" -na;']
        return n, lines
    body, links = [], []
    for key, (m, mat) in shading.items():
        col = base_color(mat)
        body.append(f'createNode standardSurface -n "{m}_mat";')
        body.append('\tsetAttr ".base" 1;')
        body.append(f'\tsetAttr ".baseColor" -type "float3" {col[0]:.4f} {col[1]:.4f} {col[2]:.4f};')
        body.append(f'\tsetAttr ".specularRoughness" {scalar(mat, "Roughness", 0.5):.4f};')
        body.append(f'\tsetAttr ".metalness" {scalar(mat, "Metallic", 0.0):.4f};')
        body.append(f'createNode shadingEngine -n "{m}_SG";')
        body.append('\tsetAttr ".ihi" 0;')
        body.append('\tsetAttr ".ro" yes;')
        body.append(f'createNode materialInfo -n "{m}_info";')
        links += [f'connectAttr "{m}_mat.outColor" "{m}_SG.surfaceShader";',
                  f'connectAttr "{m}_SG.message" "{m}_info.shadingGroup";',
                  f'connectAttr "{m}_mat.message" "{m}_info.material";',
                  f'connectAttr "{m}_SG.partition" ":renderPartition.sets" -na;',
                  f'connectAttr "{m}_mat.message" ":defaultShaderList1.shaders" -na;']
        mp = maps_of(mat)
        if "base" in mp:
            n, ls = file_node(mp["base"][0], False)
            body += ls
            links.append(f'connectAttr "{n}.outColor" "{m}_mat.baseColor";')
        for k2, attr in (("rough", "specularRoughness"), ("metal", "metalness")):
            if k2 in mp:
                rec, ch = mp[k2]
                n, ls = file_node(rec, True)
                body += ls
                plug = "outAlpha" if ch == "A" else "outColor" + (ch if ch in ("R", "G", "B") else "R")
                links.append(f'connectAttr "{n}.{plug}" "{m}_mat.{attr}";')
        if "normal" in mp:
            n, ls = file_node(mp["normal"][0], True)
            body += ls
            bump = unique(m + "_bump")
            body += [f'createNode bump2d -n "{bump}";', '\tsetAttr ".bumpInterp" 1;']
            links += [f'connectAttr "{n}.outAlpha" "{bump}.bumpValue";',
                      f'connectAttr "{bump}.outNormal" "{m}_mat.normalCamera";']
    L += body + links
    n_inst = {}
    for safe, m, ids in connects:
        if ids is not None:
            k = n_inst.get(safe, 0)
            n_inst[safe] = k + 1
            rng = _ranges(ids)
            L.append(f'select -ne "{safe}Shape";')
            L.append(f'\tsetAttr ".iog[0].og[{k}].gcl" -type "componentList" {len(rng)} {" ".join(rng)};')
            L.append(f'connectAttr "{safe}Shape.iog.og[{k}]" "{m}_SG.dagSetMembers" -na;')
        else:
            L.append(f'connectAttr "{safe}Shape.iog" "{m}_SG.dagSetMembers" -na;')
    L.append(f"// End of {NAME}.ma")
    _write_atomic(os.path.join(OUT, NAME + ".ma"), "\n".join(L) + "\n", "w")


save_all_textures()
for fn, label in ((write_obj, "obj + mtl"), (write_3ds, "3ds"), (write_ma, "ma")):
    if not MESHES:
        break
    try:
        fn()
        say(f"{label} written")
    except Exception as e:
        FAILED.append((label, str(e)))
        say(f"{label} FAILED: {e}")
ok = not FAILED
json.dump({"ok": ok, "name": NAME, "blend": os.path.abspath(BLEND), "started": STARTED, "finished": time.time(),
           "files": WROTE, "textures": {r["stem"]: r for r in TEXTURES.values()},
           "failed": [{"what": w, "why": y} for w, y in FAILED]},
          open(os.path.join(OUT, "exports.json"), "w"), indent=1)
if not ok:
    say("NOT everything was written: " + "; ".join(f"{w}: {y}" for w, y in FAILED))
    sys.exit(1)
say(f"every format written ({len(WROTE)} files, {len(TEXTURES)} texture maps as PNG + JPG)")
