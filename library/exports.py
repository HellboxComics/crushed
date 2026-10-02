"""EVERY FORMAT, ONE FOLDER PER ASSET: from the finished .blend, writes the files other 3D programs open.

    python exports.py -- <asset>.blend <out_dir> <name>      (the Python that has Blender's bpy)

  <name>.blend  .fbx  .glb  .usdc   (written by the builder)
  <name>.obj + <name>.mtl          (Wavefront: opens in everything; .mtl = its materials)
  <name>.3ds                       (3D Studio: opens in 3ds Max, Cinema 4D, Maya and most others)
  <name>.ma                        (Maya ASCII)
  textures/*.png                   (every texture map, lossless)
  previews/*.jpg                   (written by the asset maker: the check pictures)
  physics.json                     (how each part behaves when crushed)

Not here, and why: .max can only be written by 3ds Max itself; .c4d needs Maxon's Cineware library.
Both programs open the .fbx natively.
"""
import os
import struct
import sys

import bpy

argv = sys.argv[sys.argv.index("--") + 1:]
BLEND, OUT, NAME = argv[0], argv[1], argv[2]
bpy.ops.wm.open_mainfile(filepath=os.path.abspath(BLEND))
os.makedirs(os.path.join(OUT, "textures"), exist_ok=True)


def meshes():
    """Every mesh part, evaluated (modifiers applied), in world space, triangulated, with its UVs and material."""
    import bmesh
    dg = bpy.context.evaluated_depsgraph_get()
    for ob in bpy.context.scene.objects:
        if ob.type != "MESH" or ob.hide_render:
            continue
        ev = ob.evaluated_get(dg)
        me = ev.to_mesh()
        bm = bmesh.new()
        bm.from_mesh(me)
        bmesh.ops.triangulate(bm, faces=bm.faces)
        bm.transform(ob.matrix_world)
        uvl = bm.loops.layers.uv.active
        tris = []
        for f in bm.faces:
            tris.append((f.material_index, [(tuple(l.vert.co), tuple(l[uvl].uv) if uvl else (0.0, 0.0)) for l in f.loops]))
        mats = [m for m in ob.data.materials] or [None]
        bm.free()
        ev.to_mesh_clear()
        yield ob.name, tris, mats


def _save_image(img):
    """An image the asset uses, saved as textures/<its name>.png (from its own file on disk). -> file name"""
    from PIL import Image
    src = bpy.path.abspath(img.filepath) if img.filepath else ""
    fn = os.path.splitext(os.path.basename(src) or bpy.path.clean_name(img.name))[0] + ".png"
    p = os.path.join(OUT, "textures", fn)
    if not os.path.exists(p):
        if src and os.path.exists(src):
            Image.open(src).save(p)
        elif img.size[0]:
            img.save_render(p)
        else:
            return None
    return fn


def tex_of(mat):
    """The base-color image of a material, as its textures/ file name (or None)."""
    if not mat or not mat.use_nodes:
        return None
    for n in mat.node_tree.nodes:
        if n.type == "TEX_IMAGE" and n.image and n.outputs["Color"].is_linked:
            if any(l.to_socket.name == "Base Color" for l in n.outputs["Color"].links):
                return _save_image(n.image)
    return None


def base_color(mat):
    if mat and mat.use_nodes:
        b = mat.node_tree.nodes.get("Principled BSDF")
        if b:
            return tuple(b.inputs["Base Color"].default_value[:3])
    return (0.8, 0.8, 0.8)


def save_all_textures():
    for img in bpy.data.images:
        try:
            _save_image(img)
        except Exception as e:
            print(f"[exports] texture {img.name}: {e}")


# ---------------------------------------------------------------- .obj + .mtl (Blender's own writer)
def write_obj():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.wm.obj_export(filepath=os.path.join(OUT, NAME + ".obj"), export_materials=True, path_mode="STRIP",
                          export_uv=True, export_normals=True, apply_modifiers=True, forward_axis="NEGATIVE_Z",
                          up_axis="Y")
    mtl = os.path.join(OUT, NAME + ".mtl")             # the material file points into textures/ (all PNG)
    if os.path.exists(mtl):
        out = []
        for line in open(mtl):
            parts = line.split()
            if parts and parts[0].startswith(("map_", "bump", "disp", "norm")):
                f = os.path.splitext(parts[-1])[0] + ".png"
                line = " ".join(parts[:-1] + ["textures/" + f]) + "\n"
            out.append(line)
        open(mtl, "w").writelines(out)


# ---------------------------------------------------------------- .3ds (3D Studio binary, chunk format)
def _chunk(cid, data):
    return struct.pack("<HI", cid, 6 + len(data)) + data


def _cstr(s, n):
    return s.encode("ascii", "replace")[:n] + b"\0"


def write_3ds():
    mats, objs = {}, []
    for oname, tris, mlist in meshes():
        groups = {}
        for mi, corners in tris:
            groups.setdefault(mi, []).append(corners)
        for mi, faces in groups.items():
            mat = mlist[mi] if mi < len(mlist) else None
            mname = (mat.name if mat else "default")[:16]
            mats[mname] = (base_color(mat), tex_of(mat))
            # 3DS keeps one UV per vertex and at most 65,535 of each: split into pieces as needed
            verts, index, out_faces = [], {}, []
            for corners in faces:
                ids = []
                for co, uv in corners:
                    key = (round(co[0], 6), round(co[1], 6), round(co[2], 6), round(uv[0], 5), round(uv[1], 5))
                    if key not in index:
                        index[key] = len(verts)
                        verts.append((co, uv))
                    ids.append(index[key])
                out_faces.append(ids)
                if len(verts) > 65000 or len(out_faces) > 65000:
                    objs.append((f"{oname[:7]}{len(objs):02d}", verts, out_faces, mname))
                    verts, index, out_faces = [], {}, []
            if out_faces:
                objs.append((f"{oname[:7]}{len(objs):02d}", verts, out_faces, mname))
    edit = _chunk(0x3D3E, struct.pack("<I", 3))
    for mname, (col, tex) in mats.items():
        body = _chunk(0xA000, _cstr(mname, 16))
        rgb = _chunk(0x0011, bytes(int(max(0, min(1, c)) * 255) for c in col))
        body += _chunk(0xA020, rgb)
        if tex:
            short = (os.path.splitext(tex)[0][:8] + ".png").upper()          # 3DS file names are 8.3
            src = os.path.join(OUT, "textures", tex)
            dst = os.path.join(OUT, "textures", short)
            if os.path.exists(src) and not os.path.exists(dst):
                import shutil
                shutil.copy(src, dst)
            body += _chunk(0xA200, _chunk(0x0030, struct.pack("<H", 100)) + _chunk(0xA300, _cstr("textures/" + short, 30)))
        edit += _chunk(0xAFFF, body)
    for oname, verts, faces, mname in objs:
        pts = struct.pack("<H", len(verts)) + b"".join(struct.pack("<3f", *co) for co, _ in verts)
        uvs = struct.pack("<H", len(verts)) + b"".join(struct.pack("<2f", *uv) for _, uv in verts)
        fc = struct.pack("<H", len(faces)) + b"".join(struct.pack("<4H", a, b, c, 7) for a, b, c in faces)
        grp = _chunk(0x4130, _cstr(mname, 16) + struct.pack("<H", len(faces)) +
                     b"".join(struct.pack("<H", i) for i in range(len(faces))))
        mesh = _chunk(0x4110, pts) + _chunk(0x4140, uvs) + _chunk(0x4120, fc + grp)
        edit += _chunk(0x4000, _cstr(oname, 10) + _chunk(0x4100, mesh))
    data = _chunk(0x4D4D, _chunk(0x0002, struct.pack("<I", 3)) + _chunk(0x3D3D, edit))
    open(os.path.join(OUT, NAME + ".3ds"), "wb").write(data)


# ---------------------------------------------------------------- .ma (Maya ASCII)
def write_ma():
    L = ['//Maya ASCII 2018 scene', f'//Name: {NAME}.ma', 'requires maya "2018";', 'currentUnit -l centimeter -a degree -t film;',
         'fileInfo "application" "maya";']
    sg_of = {}
    connects = []
    for oname, tris, mlist in meshes():
        safe = "".join(c if c.isalnum() else "_" for c in oname) or "part"
        verts, vindex, uvs, uvindex, edges, eindex, faces = [], {}, [], {}, [], {}, []
        for mi, corners in tris:
            vids, uids = [], []
            for co, uv in corners:
                k = (round(co[0], 6), round(co[1], 6), round(co[2], 6))
                if k not in vindex:
                    vindex[k] = len(verts)
                    verts.append(k)
                vids.append(vindex[k])
                ku = (round(uv[0], 6), round(uv[1], 6))
                if ku not in uvindex:
                    uvindex[ku] = len(uvs)
                    uvs.append(ku)
                uids.append(uvindex[ku])
            es = []
            for a, b in ((vids[0], vids[1]), (vids[1], vids[2]), (vids[2], vids[0])):
                if (a, b) in eindex:
                    es.append(eindex[(a, b)])
                elif (b, a) in eindex:
                    es.append(-eindex[(b, a)] - 1)                  # the edge, run backwards
                else:
                    eindex[(a, b)] = len(edges)
                    edges.append((a, b))
                    es.append(eindex[(a, b)])
            faces.append((mi, es, uids))
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
        L.append(f'\tsetAttr -s {len(edges)} ".ed[0:{len(edges) - 1}]" ' + " ".join(f"{a} {b} 1" for a, b in edges) + ";")
        L.append(f'\tsetAttr -s {len(faces)} ".fc[0:{len(faces) - 1}]" -type "polyFaces" ' +
                 " ".join(f"f 3 {e[0]} {e[1]} {e[2]} mu 0 3 {u[0]} {u[1]} {u[2]}" for _, e, u in faces) + ";")
        by_mat = {}
        for i, (mi, _, _) in enumerate(faces):
            by_mat.setdefault(mi, []).append(i)
        for mi, ids in by_mat.items():
            mat = mlist[mi] if mi < len(mlist) else None
            mname = "".join(c if c.isalnum() else "_" for c in (mat.name if mat else "default"))
            if mname not in sg_of:
                col, tex = base_color(mat), tex_of(mat)
                sg_of[mname] = (col, tex)
            rng = " ".join(f'"f[{i}]"' for i in ids) if len(by_mat) > 1 else '"f[*]"'
            connects.append((safe, mname, rng, len(by_mat) > 1, mi))
    for mname, (col, tex) in sg_of.items():
        L.append(f'createNode lambert -n "{mname}_mat";')
        L.append(f'\tsetAttr ".c" -type "float3" {col[0]:.4f} {col[1]:.4f} {col[2]:.4f};')
        L.append(f'createNode shadingEngine -n "{mname}_SG";')
        L.append('\tsetAttr ".ihi" 0;\n\tsetAttr ".ro" yes;')
        L.append(f'createNode materialInfo -n "{mname}_info";')
        if tex:
            L.append(f'createNode file -n "{mname}_tex";')
            L.append(f'\tsetAttr ".ftn" -type "string" "textures/{tex}";')
            L.append(f'createNode place2dTexture -n "{mname}_p2d";')
    for mname, (col, tex) in sg_of.items():
        L.append(f'connectAttr "{mname}_mat.oc" "{mname}_SG.ss";')
        L.append(f'connectAttr "{mname}_SG.msg" "{mname}_info.sg";')
        L.append(f'connectAttr "{mname}_mat.msg" "{mname}_info.m";')
        L.append(f'connectAttr "{mname}_SG.pa" ":renderPartition.st" -na;')
        L.append(f'connectAttr "{mname}_mat.msg" ":defaultShaderList1.s" -na;')
        if tex:
            L.append(f'connectAttr "{mname}_tex.oc" "{mname}_mat.c";')
            L.append(f'connectAttr "{mname}_p2d.o" "{mname}_tex.uv";')
            L.append(f'connectAttr "{mname}_p2d.ofs" "{mname}_tex.fs";')
            L.append(f'connectAttr "{mname}_tex.msg" ":defaultTextureList1.tx" -na;')
            L.append(f'connectAttr "{mname}_p2d.msg" ":defaultRenderUtilityList1.u" -na;')
    n_inst = {}
    for safe, mname, rng, partial, mi in connects:
        if partial:
            k = n_inst.get(safe, 0)
            n_inst[safe] = k + 1
            L.append(f'select -ne "{safe}Shape";')
            L.append(f'\tsetAttr ".iog[0].og[{k}].gcl" -type "componentList" 1 {rng};')
            L.append(f'connectAttr "{safe}Shape.iog.og[{k}]" "{mname}_SG.dsm" -na;')
        else:
            L.append(f'connectAttr "{safe}Shape.iog" "{mname}_SG.dsm" -na;')
    L.append(f"// End of {NAME}.ma")
    open(os.path.join(OUT, NAME + ".ma"), "w").write("\n".join(L) + "\n")


save_all_textures()
for fn, label in ((write_obj, "obj + mtl"), (write_3ds, "3ds"), (write_ma, "ma")):
    try:
        fn()
        print(f"[exports] {label} written")
    except Exception as e:
        print(f"[exports] {label} FAILED: {e}")
