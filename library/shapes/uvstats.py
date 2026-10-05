"""UV HEALTH OF ONE PART (shared by shapes/contract.py and measure_blender.py).

    stats(o) -> {"has_uv", "overlap", "collapsed", "out_of_range", "faces"}
      overlap      share of the part's UV area that lies under another face (0 = every island has its own room)
      collapsed    share of the part's real surface (by area) whose UV area is nothing (a side mapped to a line)
      (a UV triangle that appears twice - a solidified shell's inner copy - is not counted as an overlap)
      out_of_range share of UV corners outside 0..1 (a tiling layout; fine only for repeating materials)
"""
import bmesh
import numpy as np

GRID = 1024


def coverage(o, grid=GRID):
    """Where this part's UV islands cover the map: a grid x grid array of True/False (v up, as a picture), or None
    when the part has no UV map. The measure averages a part's maps over this - never over the empty background
    the bake leaves black (2026-10-05: a bare-steel can measured 'metallic 0.71' because 29 % of its map was
    uncovered background)."""
    me = o.data
    if not me.uv_layers or not me.polygons:
        return None
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.triangulate(bm, faces=bm.faces[:])
    uv = bm.loops.layers.uv.active
    from PIL import Image, ImageDraw
    im = Image.new("L", (grid, grid), 0)
    dr = ImageDraw.Draw(im)
    for f in bm.faces:
        pts = [tuple(l[uv].uv) for l in f.loops]
        dr.polygon([(u * grid, (1 - v) * grid) for u, v in pts], fill=255)
    bm.free()
    return np.asarray(im) > 0


def stats(o):
    me = o.data
    if not me.uv_layers or not me.polygons:
        return {"has_uv": False, "overlap": 1.0, "collapsed": 1.0, "out_of_range": 0.0, "faces": len(me.polygons)}
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.transform(o.matrix_world)
    bmesh.ops.triangulate(bm, faces=bm.faces[:])
    uv = bm.loops.layers.uv.active
    tris, real_area = [], 0.0
    outside = total_c = 0
    seen = set()
    for f in bm.faces:
        a3 = f.calc_area()
        pts = [tuple(l[uv].uv) for l in f.loops]
        total_c += len(pts)
        outside += sum(1 for u, v in pts if not (-1e-4 <= u <= 1 + 1e-4 and -1e-4 <= v <= 1 + 1e-4))
        key = tuple(sorted((round(u, 5), round(v, 5)) for u, v in pts))
        dup = key in seen                      # the same UV triangle again (a shell's inner copy): not an overlap
        seen.add(key)
        tris.append((pts, a3, dup))
    bm.free()
    from PIL import Image, ImageDraw
    im = Image.new("L", (GRID, GRID), 0)
    dr = ImageDraw.Draw(im)
    sum_area = 0.0
    collapsed = 0.0
    for pts, a3, dup in tris:
        (u0, v0), (u1, v1), (u2, v2) = pts
        a = abs((u1 - u0) * (v2 - v0) - (u2 - u0) * (v1 - v0)) / 2
        if a3 > 1e-12:
            real_area += a3
            if a < 1e-9:
                collapsed += a3                # weighted by real area: a thin rim counts for what it is
        if a < 1e-9 or dup:
            continue
        sum_area += a
        dr.polygon([(u0 * GRID, (1 - v0) * GRID), (u1 * GRID, (1 - v1) * GRID), (u2 * GRID, (1 - v2) * GRID)], fill=255)
    union = float((np.asarray(im) > 0).mean())
    # tiny triangles that never cover a pixel's centre make sum_area > union even with no overlap: a 1.5 % floor
    overlap = max(0.0, (sum_area - union) / sum_area) if sum_area > 0 else 1.0
    overlap = 0.0 if overlap < 0.015 else overlap
    return {"has_uv": True, "overlap": round(overlap, 4), "collapsed": round(collapsed / max(real_area, 1e-12), 4),
            "out_of_range": round(outside / max(total_c, 1), 4), "faces": len(me.polygons)}
