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
