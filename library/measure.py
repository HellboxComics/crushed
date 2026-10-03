"""THE EXACT CHECKS: everything about a finished model that can be MEASURED is measured - never left to a vision
model's yes/no. Each check fails closed: a missing tool or an error is a failure with a plain reason, never a pass.

  size          the model's real size against the dossier's (within 3% on every side)
  sides         a flat-lit, straight-on picture of every side of the MODEL (measure_blender.py), so what is checked
                is what is really on it - UV map and all; no side may be missing, no printed side may be blank
  barcode       every barcode the plan puts on a side must SCAN (zxing-cpp) and equal the dossier's verified UPC
  text          every printed element the plan lists must be READ off the model's own side (the Mac's built-in
                text reader, ocrmac; else tesseract; else your AI reading twice, keeping only what both reads agree on)
  materials     each part's base color / metallic / roughness inside the real-world range of its material
                (materials.json)
  mesh          no spikes, no inside-out parts, no heaps of broken faces
  inside_fit    thousands of looks at the model from every side: no inside part may show through the outside
  web_copy      the phone page's light copy exists and is under 24 MB (the host refuses bigger files)
  viewer        the phone-viewer pictures are not blank

    m = measure.run(cid, build_dir, glb, dossier, route, fam=family_entry, shots=[...], web_glb=..., use=model)
    m -> {"pass", "checks": {name: {"pass", "why", ...}}, "renders": {side: png}, "failed": [...], "problems": [...]}
"""
import difflib
import json
import os
import re
import subprocess
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
PY = sys.executable
_M = json.load(open(os.path.join(HERE, "materials.json")))
RANGES = _M["kinds"]
SLOTS = {name: kind for kind, names in _M.get("_slots", {}).items() if kind != "_about" for name in names}


def _text_of(t):
    """A printed element's words: a list (or a list written as text) becomes its lines joined."""
    if isinstance(t, list):
        return " ".join(str(x) for x in t)
    t = str(t or "")
    if t.strip().startswith("["):
        try:
            v = json.loads(t)
            if isinstance(v, list):
                return " ".join(str(x) for x in v)
        except Exception:
            pass
    return t
PX_PER_MM = 12
SIZE_TOL = 0.03
SHOW_THROUGH = 0.002          # an inside part seen on more than 0.2% of looks shows through


def _c(ok, why, **kw):
    return dict({"pass": bool(ok), "why": why}, **kw)


# ------------------------------------------------------------------ readers
def read_barcodes(png):
    """Every barcode in a picture: [(format, text)]. Raises when no barcode reader is installed."""
    import zxingcpp
    from PIL import Image
    im = Image.open(png).convert("RGB")
    out = []
    for turn in (0, 90):
        for b in zxingcpp.read_barcodes(im.rotate(turn, expand=True) if turn else im):
            out.append((str(b.format), b.text))
        if out:
            break
    return out


def norm_upc(t):
    t = re.sub(r"\D", "", str(t))
    return t[1:] if len(t) == 13 and t.startswith("0") else t


def reader():
    """Which text reader this Mac has: 'ocrmac' (Apple's own, built into macOS), 'tesseract', or None."""
    try:
        import ocrmac  # noqa: F401
        return "ocrmac"
    except Exception:
        pass
    try:
        import pytesseract
        pytesseract.get_tesseract_version()
        return "tesseract"
    except Exception:
        return None


def read_lines(png, turns=(0, 180, 90, 270), least=0.5):
    """The printed lines on a picture, each exactly as the text reader (Apple's own, else tesseract) reads it -
    for writing artwork with the exact words (a language model is never trusted to spell). [] without a reader."""
    kind = reader()
    if kind not in ("ocrmac", "tesseract"):
        return []
    from PIL import Image
    im = Image.open(png).convert("RGB")
    if max(im.size) < 2400:
        k = 2400 / max(im.size)
        im = im.resize((int(im.width * k), int(im.height * k)), Image.LANCZOS)
    best = []
    for turn in turns:                                    # the turn that reads the most words wins
        t = im.rotate(turn, expand=True) if turn else im
        if kind == "ocrmac":
            from ocrmac import ocrmac
            got = [x.strip() for x, conf, box in ocrmac.OCR(t).recognize() if conf >= least and x.strip()]
        else:
            import pytesseract
            got = [ln.strip() for ln in pytesseract.image_to_string(t, config="--psm 11").splitlines() if ln.strip()]
        got = [g for g in got if len(re.sub(r"[^A-Za-z0-9]", "", g)) >= 2]
        if sum(len(g) for g in got) > sum(len(b) for b in best):
            best = got
    return list(dict.fromkeys(best))


def read_text(png, use=None, log=print):
    """All the words on a picture, as one string - read upright and turned both ways, since print on a side often
    runs sideways (a battery's label, a carton's side panel)."""
    kind = reader()
    if kind in ("ocrmac", "tesseract"):
        from PIL import Image
        im = Image.open(png).convert("RGB")
        a = np.asarray(im).copy()
        bg = (a[..., 0] > 230) & (a[..., 1] < 30) & (a[..., 2] > 230)
        a[bg] = 255                                          # the magenta background reads as plain white
        ys, xs = np.where(~bg)
        if len(xs):                                          # just the side itself, read bigger
            a = a[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
        im = Image.fromarray(a)
        if max(im.size) < 2400:
            k = 2400 / max(im.size)
            im = im.resize((int(im.width * k), int(im.height * k)), Image.LANCZOS)
        texts = []
        for turn in (0, 90, 180, 270):
            t = im.rotate(turn, expand=True) if turn else im
            if kind == "ocrmac":
                from ocrmac import ocrmac
                texts.append(" ".join(x for x, conf, box in ocrmac.OCR(t).recognize() if conf >= 0.3))
            else:
                import pytesseract
                texts.append(pytesseract.image_to_string(t, config="--psm 11"))   # sparse text, any layout
        return " ".join(texts)
    if not use:
        raise RuntimeError("no text reader on this Mac (ocrmac or tesseract) and no AI to read")
    import vet as V                                   # your AI reads it twice; only words both reads saw count
    q = 'Read every word printed in this picture, exactly as printed, in reading order. Answer ONLY JSON: {"text": "..."}'
    a = str((V.ask(use, q, [png], think=False, side=1600) or {}).get("text", ""))
    b = str((V.ask(use, q + " Read slowly and carefully.", [png], think=False, side=1600) or {}).get("text", ""))
    wb = set(_words(b))
    return " ".join(w for w in _words(a) if w in wb)


def _words(t):
    return re.findall(r"[A-Z0-9]+", str(t).upper())


def text_found(want, got):
    """Is the printed element `want` in the read text `got`? Short lines: a close match somewhere (small misreads
    allowed); long text (ingredients): at least 85% of its words found, in any order."""
    w, g = _words(want), _words(got)
    if not w:
        return True, 1.0
    if len(w) > 12:
        have = set(g)
        score = sum(1 for x in w if x in have) / len(w)
        return score >= 0.85, round(score, 2)
    ws, gs = "".join(w), "".join(g)                          # spacing never matters ("MN1500" = "MN 1500")
    if ws in gs:
        return True, 1.0
    n, best = len(ws), 0.0
    for i in range(0, max(1, len(gs) - n + 1)):
        r = difflib.SequenceMatcher(None, ws, gs[i:i + n]).ratio()
        if r > best:
            best = r
            if best >= 0.97:
                break
    return best >= 0.85, round(best, 2)


# ------------------------------------------------------------------ the checks
def side_names(route, face):
    """The model pictures that show one side of the plan."""
    if route == "round" and face == "label":
        return ["label_0", "label_90", "label_180", "label_270"]
    return [face]


def blank(png):
    """(fraction of the picture the object fills, how much its print varies 0..255)."""
    from PIL import Image
    a = np.asarray(Image.open(png).convert("RGB")).astype(np.int16)
    bg = (a[..., 0] > 200) & (a[..., 1] < 80) & (a[..., 2] > 200)       # the magenta background (and its fringe)
    obj = ~bg
    frac = float(obj.mean())
    from PIL import ImageFilter
    core = np.asarray(Image.fromarray((obj * 255).astype(np.uint8)).filter(ImageFilter.MinFilter(9))) > 0
    if core.sum() < 50:                                  # the edges of a side are never counted as its print
        return frac, 0.0
    px = a[core]
    return frac, float(px.std(0).mean())


def run(cid, d, glb, dos, route, fam=None, shots=None, web_glb=None, use=None, log=print):
    started = time.time()
    out = os.path.join(d, "measure")
    os.makedirs(out, exist_ok=True)
    fam = fam or {}
    checks, renders = {}, {}
    render_route = {"round": "round", "flat": "flat", "pcb": "pcb"}.get(route, "box")
    mbj = os.path.join(out, "measure_blender.json")
    try:
        r = subprocess.run([PY, os.path.join(HERE, "measure_blender.py"), "--", glb, out, render_route,
                            str(PX_PER_MM)], capture_output=True, text=True, timeout=1200)
        if r.returncode != 0 or not os.path.exists(mbj) or os.path.getmtime(mbj) < started:
            raise RuntimeError((r.stderr or r.stdout)[-400:])
        mb = json.load(open(mbj))
    except Exception as e:
        checks["model_measured"] = _c(False, f"the model could not be measured in Blender: {e}")
        return _finish(checks, renders)
    renders = {k: v["file"] for k, v in mb["renders"].items()}

    # size
    want = [x for x in (dos.get("size_m") or [])[:3] if x]
    got = mb["overall"]["size_m"]
    if len(want) == 3:
        ws, gs = sorted(want), sorted(got)
        if route in ("pcb", "flat"):                    # a board / sheet: its thickness depends on what stands on it
            ws, gs = ws[1:], gs[1:]
        off = [abs(g - w) / w for g, w in zip(gs, ws)]
        checks["size"] = _c(max(off) <= SIZE_TOL, "real size matches" if max(off) <= SIZE_TOL else
                            f"the model is {', '.join(f'{g * 1000:.1f}' for g in got)} mm but the real item is "
                            f"{', '.join(f'{w * 1000:.1f}' for w in want)} mm (off by up to {max(off) * 100:.1f}%)",
                            got_mm=[round(g * 1000, 1) for g in got], want_mm=[round(w * 1000, 1) for w in want])
    else:
        checks["size"] = _c(False, "the dossier has no real size to check against")

    # sides: none missing, printed ones not blank
    faces = dos.get("faces") or {}
    printed = {f for f, e in faces.items() if e.get("source") in ("exact_photo", "template_photo", "rebuilt")
               and e.get("must_show")}
    bad = []
    for name, png in renders.items():
        frac, var = blank(png)
        face = "label" if name.startswith("label_") else name
        if frac < 0.02:
            bad.append(f"{name}: the model shows nothing from this side")
        elif face in printed and var < 6:
            bad.append(f"{name}: this side should be printed but is one flat color")
    checks["sides"] = _c(not bad, "every side is there and every printed side carries its print" if not bad
                         else "; ".join(bad))

    # barcode
    upc = ((dos.get("facts") or {}).get("upc") or {})
    bar_faces = [f for f, e in faces.items() if any(m.get("kind") == "barcode" for m in e.get("must_show", []))]
    if bar_faces or "barcode" in fam.get("checks", []):
        if not upc.get("value") or upc.get("status") not in ("verified", "single_source"):
            # no verified UPC: a gap in the dossier, not a fault of the model - as long as the model prints NO barcode
            # (any barcode it shows would be made up)
            try:
                printed = [t for n, png in renders.items() for _, t in read_barcodes(png)]
                checks["barcode"] = _c(not printed, "no verified UPC was found, and the model prints no barcode (a gap "
                                       "in the dossier, listed in its gaps)" if not printed else
                                       f"the model prints a barcode ({', '.join(printed)}) but no real UPC was "
                                       "verified - a made-up barcode", scanned=printed)
            except ImportError:
                checks["barcode"] = _c(False, "the barcode reader (zxing-cpp) is not installed on this Mac")
        else:
            try:
                seen = {}
                for f in bar_faces or list(faces):
                    for n in side_names(route, f):
                        if n in renders:
                            seen[n] = read_barcodes(renders[n])
                codes = [norm_upc(t) for v in seen.values() for _, t in v]
                ok = norm_upc(upc["value"]) in codes
                checks["barcode"] = _c(ok, f"the barcode scans as {upc['value']}, the real UPC" if ok else
                                       (f"the barcode on the model scans as {', '.join(codes)} but the real UPC is "
                                        f"{upc['value']}" if codes else "no barcode on the model scans"),
                                       scanned=codes, want=upc["value"])
            except ImportError:
                checks["barcode"] = _c(False, "the barcode reader (zxing-cpp) is not installed on this Mac")
            except Exception as e:
                checks["barcode"] = _c(False, f"the barcode could not be read: {e}")

    # text: every printed element the plan lists, read off the model's own sides
    want_text = [(f, m) for f, e in faces.items() for m in e.get("must_show", [])
                 if m.get("kind") in ("text", "panel") and len(_text_of(m.get("text", "")).strip()) >= 3]
    read = {}                                               # every side read once, shared by the word checks
    if want_text:
        try:
            ref_read, skipped = {}, []
            missing = []
            for f, m in want_text:
                e = faces.get(f) or {}
                ref = e.get("photo")
                if e.get("source") in ("exact_photo", "template_photo") and ref and os.path.exists(ref):
                    # a side taken from a real photo: only words the reader can read on the REAL photo count
                    # (a stylized logo it can't read on the real box either proves nothing about the model)
                    if ref not in ref_read:
                        ref_read[ref] = read_text(ref, use=use, log=log)
                    on_photo = m.get("sister_text") if e.get("source") == "template_photo" and m.get("sister_text") \
                        else m["text"]                      # a sister's side shows ITS words where ours now are
                    if not text_found(_text_of(on_photo), ref_read[ref])[0]:
                        skipped.append(f"{f}: {m.get('what', '')}")
                        continue
                names = [n for n in side_names(route, f) if n in renders]
                for n in names:
                    if n not in read:
                        read[n] = read_text(renders[n], use=use, log=log)
                got_t = " ".join(read[n] for n in names)
                ok, score = text_found(_text_of(m["text"]), got_t)
                if not ok:
                    missing.append(f"{f}: \"{_text_of(m['text'])[:60]}\" ({m.get('what', '')}; best match {score})")
            n = len(want_text) - len(skipped)
            checks["text"] = _c(not missing, f"all {n} readable printed elements read off the model" if not missing
                                else f"{len(missing)} of {n} printed elements missing or misspelled: "
                                + "; ".join(missing[:8]), reader=reader() or "your AI (read twice)",
                                not_readable_on_the_real_photo=skipped)
        except Exception as e:
            checks["text"] = _c(False, f"the printed words could not be read: {e}")

    # words that can only come from a PHOTO - a watermark, someone's name and email, a photo or auction site's name -
    # must never be on the model (they would be sold printed on it)
    try:
        import facts as FX
        found = []
        for n, png in renders.items():
            if n not in read:
                read[n] = read_text(png, use=use, log=log)
            for m in FX.NOT_PRINTED.finditer(read[n] or ""):
                found.append(f"{n}: \"{m.group(0).strip()[:40]}\"")
        checks["no_photo_marks"] = _c(not found, "no watermark, email, photographer or photo-site name on the model"
                                      if not found else "words that belong to a photo, not the item, are printed "
                                      "on the model: " + "; ".join(found[:6]), found=found)
    except Exception as e:
        checks["no_photo_marks"] = _c(False, f"the model's sides could not be read for watermarks: {e}")

    # materials
    bad = []
    for part, info in mb["parts"].items():
        for m in info.get("materials", []):
            if m["name"].endswith("_print"):
                continue
            slot_kind = next((k for n, k in SLOTS.items() if n in m["name"].lower()), None)
            rng = RANGES.get(slot_kind or info.get("material_kind", ""))
            if not rng:
                continue
            base = float(np.mean(m.get("base", [0.5, 0.5, 0.5])))
            for key, val in (("metallic", m.get("metallic")), ("roughness", m.get("roughness")), ("base", base)):
                if val is None:
                    continue
                lo, hi = rng[key]
                if not (lo - 1e-3 <= val <= hi + 1e-3):
                    bad.append(f"{part} ({(slot_kind or info['material_kind']).replace('_', ' ')}): {key} {val:.2f}, real is "
                               f"{lo:.2f}-{hi:.2f}")
    checks["materials"] = _c(not bad, "every material is in its real-world range" if not bad else "; ".join(bad[:10]))

    # mesh
    bad = []
    for part, info in mb["parts"].items():
        if info.get("spikes"):
            bad.append(f"{part}: {info['spikes']} spike points")
        v = info.get("signed_volume_mm3")
        if v is not None and v < 0:
            bad.append(f"{part}: inside-out (its faces point inward)")
        if info["faces"] and info.get("degenerate_faces", 0) > max(20, 0.01 * info["faces"]):
            bad.append(f"{part}: {info['degenerate_faces']} broken (zero-size) faces")
    checks["mesh"] = _c(not bad, "no spikes, no inside-out parts, no broken faces" if not bad else "; ".join(bad))

    # inside fit
    st = mb.get("inside_fit") or {}
    show = {k: v for k, v in (st.get("showing_through") or {}).items() if v > SHOW_THROUGH}
    checks["inside_fit"] = _c(not show, "no inside part shows through the outside" if not show else
                              "; ".join(f"the inside part '{k}' shows through the outside ({v * 100:.1f}% of looks)"
                                        for k, v in show.items()),
                              inside_parts=st.get("inside_parts", []))

    # web copy
    if web_glb is not None:
        ok = os.path.exists(web_glb) and os.path.getsize(web_glb) < 24 * 2 ** 20 and os.path.getmtime(web_glb) >= started - 7200
        checks["web_copy"] = _c(ok, "the phone page's copy is there and small enough" if ok else
                                "the phone page's copy is missing, old, or over 24 MB (the host would show nothing)")

    # viewer
    if shots:
        bad = []
        from PIL import Image
        for s in shots:
            if not s or not os.path.exists(s):
                bad.append(f"{os.path.basename(str(s))}: missing")
                continue
            a = np.asarray(Image.open(s).convert("L")).astype(float)
            if a.std() < 4:
                bad.append(f"{os.path.basename(s)}: blank")
        checks["viewer"] = _c(not bad, "the phone viewer shows the model" if not bad else "; ".join(bad))
    return _finish(checks, renders, mb)


def _finish(checks, renders, mb=None):
    failed = [k for k, v in checks.items() if not v["pass"]]
    return {"pass": not failed, "checks": checks, "renders": renders, "failed": failed,
            "problems": [f"{k}: {checks[k]['why']}" for k in failed], "parts": (mb or {}).get("parts", {})}


if __name__ == "__main__":
    # by hand: python measure.py model.glb out_dir route [dossier.json]
    dos = json.load(open(sys.argv[4])) if len(sys.argv) > 4 else {}
    print(json.dumps(run("by-hand", sys.argv[2], sys.argv[1], dos, sys.argv[3]), indent=1)[:6000])
