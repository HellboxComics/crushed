"""KEEP WHAT PASSED (Cody, 2026-10-04: "IT MUST KEEP WHAT IS GOOD AND REDO WHAT IS BAD").

A step's answer is kept, keyed by EVERYTHING that goes into it (the bytes of its input pictures, the words, the
brain, the version of the question). When a later build feeds a step the very same inputs, the kept answer is used
and the step is not run again. A step is never skipped on a guess: a different photo, a different word list or a
changed question is a different key. Only GOOD answers are kept where the answer is a verdict (a pass stays a pass;
a fail is always looked at again, because the item changed and the judge is a brain).

    key = kept.key("judge-side", [png, lit_png, ref_png], must, QUESTION_VERSION)
    v = kept.get("judge-side", key)          # None when nothing is kept
    kept.put("judge-side", key, verdict)

Files: ~/crushed-render/remaster/kept/<kind>/<key>.json
"""
import hashlib
import json
import os
import time

WORK = os.path.expanduser(os.environ.get("CRUSHED_REMASTER_WORK", "~/crushed-render/remaster"))
DIR = os.path.join(WORK, "kept")
# a test build (the engineer's) READS the shared store but WRITES only to its own (CRUSHED_KEPT_WRITE): code in a
# test build can never plant a pass that a real build or the asset maker's own check would then reuse
WRITE_DIR = os.path.expanduser(os.environ.get("CRUSHED_KEPT_WRITE") or DIR)


def file_sha(path):
    """The bytes of a file, hashed (None when there is no such file)."""
    try:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h.update(chunk)
        return h.hexdigest()
    except Exception:
        return None


def key(kind, files=(), *parts):
    """One key from the input files' BYTES and the other inputs (words, names, versions) - never from file names
    or times, so a rewritten-but-identical picture still matches and a changed one never does."""
    h = hashlib.sha256(kind.encode())
    for f in files or []:
        s = file_sha(f) if f else None
        h.update(b"|" + (s or "missing").encode())
    for p in parts:
        h.update(b"|" + json.dumps(p, sort_keys=True, default=str).encode())
    return h.hexdigest()[:40]


def _path(kind, k, base=None):
    return os.path.join(base or DIR, kind, k + ".json")


def _read(kind, k):
    """The record: the writer's own store first (a test build sees what it kept), then the shared store."""
    for base in dict.fromkeys([WRITE_DIR, DIR]):
        try:
            with open(_path(kind, k, base)) as f:
                return json.load(f)
        except Exception:
            continue
    return None


# a test build may ask for steps to be redone from scratch (clear=[...]): those kinds are not read from the store
_CLEAR_KINDS = {"parts": ("parts-plan", "board-parts"), "texture": ("labelparts", "look-unrolled"),
                "skin": ("look-faces",), "dossier": ("look-faces", "look-unrolled", "labelparts"),
                "all": ("parts-plan", "board-parts", "labelparts", "look-unrolled", "look-faces", "words",
                        "judge-side", "inspect")}
CLEARED = {kk for c in os.environ.get("CRUSHED_CLEAR", "").split(",") if c for kk in _CLEAR_KINDS.get(c.strip(), ())}


def get(kind, k):
    if kind in CLEARED:
        return None
    rec = _read(kind, k)
    return rec.get("value") if rec else None


def put(kind, k, value, note=""):
    p = _path(kind, k, WRITE_DIR)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    tmp = p + ".tmp"
    with open(tmp, "w") as f:
        json.dump({"value": value, "at": time.time(), "note": note}, f, indent=1, default=str)
    os.replace(tmp, p)
    return value


def forget(cid):
    """A Redo: every kept answer noted for this item is set aside (moved under kept/_stale/, never deleted), so
    nothing of a build the owner rejected is reused. -> how many."""
    import shutil
    n = 0
    for base in dict.fromkeys([WRITE_DIR, DIR]):
        for kind in ("judge-side", "inspect", "words", "labelparts"):
            folder = os.path.join(base, kind)
            if not os.path.isdir(folder):
                continue
            for f in os.listdir(folder):
                if not f.endswith(".json"):
                    continue
                p = os.path.join(folder, f)
                try:
                    note = str(json.load(open(p)).get("note") or "")
                except Exception:
                    continue
                if note == cid or note.startswith(cid + " "):
                    stale = os.path.join(base, "_stale", kind)
                    os.makedirs(stale, exist_ok=True)
                    shutil.move(p, os.path.join(stale, f"{int(time.time())}-{f}"))
                    n += 1
    return n


# ------------------------------------------------------------------ rendered pictures: the same within render noise
def pic_sig(path, n=512):
    """A picture's signature for matching: 512 x 512 gray. Two renders of the same model differ by sampling noise
    (a level or so per pixel); a changed word, line or color differs by a lot in some block. Compared, not hashed."""
    try:
        import numpy as np
        from PIL import Image
        im = Image.open(path).convert("L").resize((n, n), Image.BILINEAR)
        return np.asarray(im, dtype=np.uint8)
    except Exception:
        return None


def pics_match(a, b, block=4, block_tol=3.0, mean_tol=1.0, pixel_tol=24):
    """True when two signatures are the same picture up to render noise (measured: sampling noise moves a pixel of
    the 512 signature by 2 levels at most, a 4x4 block by under 1): no pixel differs by more than pixel_tol (one
    changed letter in a small word moves one pixel by 40+), no 4x4 block's mean by more than block_tol, and the whole
    by less than mean_tol."""
    import numpy as np
    if a is None or b is None or a.shape != b.shape:
        return False
    d = np.abs(a.astype(np.int16) - b.astype(np.int16))
    n = a.shape[0] // block
    blocks = d[:n * block, :n * block].reshape(n, block, n, block).mean(axis=(1, 3))
    return float(d.mean()) <= mean_tol and float(blocks.max()) <= block_tol and int(d.max()) <= pixel_tol


def get_pictures(kind, k, files):
    """A kept answer for these rendered pictures: the record under key k (made from the non-picture inputs) whose
    stored picture signatures match these files within render noise. None otherwise."""
    import numpy as np
    if kind in CLEARED:
        return None
    rec = _read(kind, k)
    if not rec:
        return None
    sigs = rec.get("sigs") or []
    files = [f for f in files if f]
    if len(sigs) != len(files):
        return None
    for s, f in zip(sigs, files):
        a = np.frombuffer(bytes.fromhex(s["hex"]), dtype=np.uint8).reshape(s["shape"]) if s else None
        if not pics_match(a, pic_sig(f)):
            return None
    return rec.get("value")


def put_pictures(kind, k, files, value, note=""):
    sigs = []
    for f in files:
        if not f:
            continue
        a = pic_sig(f)
        sigs.append({"hex": a.tobytes().hex(), "shape": list(a.shape)} if a is not None else None)
    p = _path(kind, k, WRITE_DIR)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    tmp = p + ".tmp"
    with open(tmp, "w") as f:
        json.dump({"value": value, "sigs": sigs, "at": time.time(), "note": note}, f, default=str)
    os.replace(tmp, p)
    return value
