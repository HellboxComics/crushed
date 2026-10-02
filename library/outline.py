"""Round things without a hand-made shape file: the exact profile traced from your photo's outline, at the
catalog's real size. A can, a bottle, a tub, a yo-yo or a crayon all come out of the same few steps:

  1. the single item from your photo (cut out), stood with its axis up
  2. its width measured on every row of pixels = its radius all the way up
  3. scaled to the catalog's real height and width, smoothed, and made symmetric
  4. written as a lathe spec: bottom cap, the printed side (the label, which gets the AI's flat artwork) and top
     cap, with cap colors taken from the photo

    spec = from_photo(picked_photo, size_m=[w, d, h], standing="upright")
"""
import numpy as np
from PIL import Image


def from_photo(f, size_m, standing="upright", cid="item", rows=72):
    import skin
    im, m = skin.one_item(f, upright=True)
    m = (m > 0.5)
    a = np.asarray(im).astype(float) / 255
    if standing == "lying" and m.shape[1] > m.shape[0]:      # lying on its side in the photo: stand it up
        m, a = np.rot90(m), np.rot90(a)
    ys = np.where(m.any(1))[0]
    y0, y1 = ys.min(), ys.max() + 1
    widths = np.array([(np.where(r)[0].max() - np.where(r)[0].min() + 1) if r.any() else 0 for r in m[y0:y1]], float)
    # smooth out the cut-out's fuzz, but keep real steps (a cap, a shoulder)
    from scipy.ndimage import median_filter
    widths = median_filter(widths, size=max(3, len(widths) // 60 | 1))
    W_mm = 1000 * min(size_m[0], size_m[1]) if standing != "lying" else 1000 * sorted(size_m)[1]
    H_mm = 1000 * size_m[2] if standing != "lying" else 1000 * max(size_m)
    r_mm = widths / widths.max() * W_mm / 2
    z_mm = (len(widths) - 1 - np.arange(len(widths))) / max(len(widths) - 1, 1) * H_mm   # photo top = z max
    idx = np.unique(np.linspace(0, len(widths) - 1, rows).astype(int))[::-1]            # bottom to top
    side = [[round(float(r_mm[i]), 3), round(float(z_mm[i]), 3)] for i in idx]
    side[0][1], side[-1][1] = 0.0, round(H_mm, 3)
    side = [p for p in side if p[0] > 0.05] or [[W_mm / 2, 0.0], [W_mm / 2, H_mm]]

    def color(rows_):
        sel = m[rows_]
        px = a[rows_][sel]
        return [round(float(x), 3) for x in (np.median(px, 0) if len(px) else [0.5, 0.5, 0.5])]

    band = max(2, (y1 - y0) // 40)
    spec = {"id": cid, "name": cid, "units": "mm", "segments": 128, "source": "traced from your photo, real size from the catalog",
            "materials": {"label": {"color": [0.5, 0.5, 0.5], "roughness": 0.4, "texture": True},
                          "bottom": {"color": color(slice(y1 - band, y1)), "roughness": 0.5},
                          "top": {"color": color(slice(y0, y0 + band)), "roughness": 0.5}},
            "profile": [{"part": "bottom", "pts": [[0, 0], [side[0][0], 0.0]]},
                        {"part": "label", "pts": side},
                        {"part": "top", "pts": [[side[-1][0], side[-1][1]], [0, side[-1][1]]]}]}
    return spec


METAL = {"bare_steel": ([0.5, 0.5, 0.49], 0.36), "aluminum": ([0.8, 0.8, 0.8], 0.32), "chrome": ([0.85, 0.85, 0.85], 0.08),
         "copper": ([0.95, 0.64, 0.54], 0.3), "brass": ([0.9, 0.75, 0.45], 0.3), "gold_plate": ([1.0, 0.77, 0.34], 0.25),
         "painted_metal": (None, 0.4)}


def apply_construction(spec, card):
    """The item's 'how it's made' (cards.construction) turned into the real build: the printed part gets the right
    surface (a glossy plastic sleeve, or a matte paper label), the overlap seam where its ends meet and its edge
    rolled over the shoulders; metal ends become real metal with pressed rings; plastic ends get a molded finish."""
    import cards
    c = card.get("construction") or {}
    layers = c.get("layers", [])
    det = cards.details(card)
    mats = [L.get("material") for L in layers]
    label_mat = next((m for m in mats if m in ("printed_plastic_sleeve", "printed_paper_label")), None)
    end_mat = next((m for m in mats if m in METAL), None) or next((m for m in mats if m in ("molded_plastic", "glass",
                                                                                         "clear_plastic")), None)
    M = spec["materials"]
    lab = next(p for p in spec["profile"] if p["part"] == "label")
    if label_mat == "printed_paper_label":
        M["label"].update(finish="card", roughness=0.55)
    else:
        M["label"].update(finish="wrap", roughness=0.4)
    if label_mat or "sleeve_seam" in det:                     # every wrapped label has a seam where its ends meet
        lab["seam"] = {"overlap_deg": 6 if label_mat != "printed_paper_label" else 10,
                       "thickness_mm": 0.07 if label_mat != "printed_paper_label" else 0.12, "ramp_deg": 2}
    for part in ("top", "bottom"):
        if part not in M:
            continue
        if end_mat in METAL:
            col, rough = METAL[end_mat]
            M[part].update(metallic=1.0, roughness=rough, finish="spun", **({"color": col} if col else {}))
        elif end_mat in ("molded_plastic",):
            M[part].update(finish="plastic")
    if "pressed_rings" in det or "can_rim" in det:            # a stamped end: a groove and a raised ring
        for p in spec["profile"]:
            if p["part"] == "top" and len(p["pts"]) == 2:
                (r0, z0), (r1, z1) = p["pts"]
                p["pts"] = [[r0, z0], [r0 * 0.85, z0 - 0.15], [r0 * 0.7, z0], [r0 * 0.45, z0 + 0.12], [r0 * 0.3, z0], [0, z0]]
    spec["construction"] = c
    return spec
