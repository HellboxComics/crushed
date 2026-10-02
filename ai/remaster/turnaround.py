"""THE TURNAROUND -- the real product from six sides in one picture, the way a 3D artist's reference sheet looks:
top row FRONT, LEFT SIDE, BACK; bottom row RIGHT SIDE, TOP, BOTTOM. One object, same size, same colors, same label
in every view, so the sculptor gets ONE object and the painter gets every face.

Two steps, both on this Mac, both free:
  1. describe(): your local language model (Ollama, through ~/Desktop/AI/ask.py) writes the exact real product:
     brand, year, model, colors, materials, proportions and what is printed on every side. Saved as
     ai/remaster/prompts/<name>.turn.txt (edit it and redo the object to steer it).
  2. draw(): Qwen-Image 2512 in the drawing room (ComfyUI) paints the 3x2 turnaround from that description.
     Apache 2.0, made for readable product lettering.
split() cuts it into the six views; sheet2x2() lays front/back/left/right out the way the sculptor reads them.
"""
import json
import os
import random
import sys
import time
import urllib.parse
import urllib.request
import uuid

HERE = os.path.dirname(os.path.abspath(__file__))
PROMPTS = os.path.join(HERE, "prompts")
ROOM = os.environ.get("DRAWING_ROOM", "http://127.0.0.1:8188")
WRITER = os.environ.get("CRUSHED_WRITER", "gpt-oss:120b")
ASK_DIR = os.path.expanduser(os.environ.get("CRUSHED_ASK", "~/Desktop/AI"))
ORDER = ["front", "left", "back", "right", "top", "bottom"]          # cells, left to right, top row first
W, H = 1584, 1056                                                    # Qwen-Image's 3:2 size: six 528 px cells

LAYOUT = ("A professional 3D modeling reference sheet: a 3 by 2 grid of six orthographic studio product photos of "
          "the SAME single object on a plain light grey background, evenly lit, true colors, sharp focus. Top row, "
          "left to right: the FRONT view, the LEFT SIDE view, the BACK view. Bottom row, left to right: the RIGHT "
          "SIDE view, the TOP view looking straight down, the BOTTOM view looking straight up. The object is exactly "
          "the same size, centered in each cell, upright the same way in the four side views, with the same "
          "colors, wear and printing in every view; each view shows what really is on that side. No captions, no "
          "labels, no text outside the object, no hands, no props, no other objects. The object: ")

BRIEF = """You write reference descriptions for a 3D artist rebuilding real nostalgic products exactly as they were.
Object: {display}
Era: {years}
What it is (from the collection notes): {notes}
Starting description: {seed}

Write ONE paragraph, under 170 words, describing the REAL product exactly as it was sold in that era: the real brand,
model and year; overall shape and proportions; materials and finish (glossy ABS, brushed steel, matte cardboard,
foil, fabric); exact colors; and then what is printed or molded on each side: front, left side, back, right side,
top, bottom, with the real logo and the real words on it. Mild wear from use. No people, no faces of real people.
Only the paragraph, no heading, no list."""


def _ask():
    sys.path.insert(0, ASK_DIR)
    import ask
    return ask


def describe(name, display, years, notes, seed, redo=False):
    out = os.path.join(PROMPTS, name + ".turn.txt")
    if os.path.exists(out) and not redo:
        return open(out).read().strip()
    text = _ask().ask(WRITER, BRIEF.format(display=display, years=years, notes=notes or "-", seed=seed or "-"),
                      kind="write")
    release()                       # hand its memory back before the drawing room loads a 20B image model
    text = " ".join(str(text or "").split())
    if len(text) < 80:
        raise RuntimeError(f"the writer gave back almost nothing for {name}")
    open(out, "w").write(text + "\n")
    return text


def release():
    """Ollama's own way to unload a model now: ask for nothing with keep_alive 0."""
    host = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434")
    host = host if host.startswith("http") else "http://" + host + ":11434"
    try:
        body = json.dumps({"model": WRITER, "keep_alive": 0}).encode()
        urllib.request.urlopen(urllib.request.Request(host + "/api/generate", data=body,
                                                      headers={"content-type": "application/json"}), timeout=30)
    except Exception:
        pass


def draw(description, out, seed=None, steps=30, timeout=1800):
    """One 1584x1056 turnaround from Qwen-Image 2512 (bf16), its own text encoder and VAE."""
    seed = seed if seed is not None else random.randint(1, 2 ** 31)
    wf = {
        "1": {"class_type": "UNETLoader", "inputs": {"unet_name": "qwen_image_2512_bf16.safetensors", "weight_dtype": "default"}},
        "2": {"class_type": "CLIPLoader", "inputs": {"clip_name": "qwen_2.5_vl_7b.safetensors", "type": "qwen_image"}},
        "3": {"class_type": "VAELoader", "inputs": {"vae_name": "qwen_image_vae.safetensors"}},
        "4": {"class_type": "ModelSamplingAuraFlow", "inputs": {"model": ["1", 0], "shift": 3.1}},
        "5": {"class_type": "CLIPTextEncode", "inputs": {"text": LAYOUT + description, "clip": ["2", 0]}},
        "6": {"class_type": "CLIPTextEncode", "inputs": {"text": "blurry, deformed, different objects, inconsistent, "
                                                                 "captions, watermark, hands, people", "clip": ["2", 0]}},
        "7": {"class_type": "EmptySD3LatentImage", "inputs": {"width": W, "height": H, "batch_size": 1}},
        "8": {"class_type": "KSampler", "inputs": {"model": ["4", 0], "positive": ["5", 0], "negative": ["6", 0],
                                                  "latent_image": ["7", 0], "seed": seed, "steps": steps, "cfg": 4.0,
                                                  "sampler_name": "euler", "scheduler": "simple", "denoise": 1.0}},
        "9": {"class_type": "VAEDecode", "inputs": {"samples": ["8", 0], "vae": ["3", 0]}},
        "10": {"class_type": "SaveImage", "inputs": {"images": ["9", 0], "filename_prefix": "crushed_turn"}},
    }
    body = json.dumps({"prompt": wf, "client_id": uuid.uuid4().hex}).encode()
    req = urllib.request.Request(ROOM + "/prompt", data=body, headers={"content-type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        pid = json.load(r)["prompt_id"]
    t0 = time.time()
    while time.time() - t0 < timeout:
        time.sleep(5)
        with urllib.request.urlopen(ROOM + "/history/" + pid, timeout=20) as r:
            h = json.load(r)
        if pid in h:
            st = h[pid].get("status", {})
            if st.get("status_str") == "error":
                raise RuntimeError("the drawing room could not draw it: " + json.dumps(st)[:400])
            for node in h[pid].get("outputs", {}).values():
                for im in node.get("images", []):
                    q = urllib.parse.urlencode({"filename": im["filename"], "subfolder": im.get("subfolder", ""),
                                                "type": im.get("type", "output")})
                    with urllib.request.urlopen(ROOM + "/view?" + q, timeout=60) as r2:
                        open(out, "wb").write(r2.read())
                    return out
    raise RuntimeError("the drawing room took too long")


def to_white(im):
    """The grey studio background to pure white, so every later step sees only the object."""
    import numpy as np
    from PIL import Image
    a = np.asarray(im.convert("RGB")).astype(int)
    bg = np.median(np.concatenate([a[:6].reshape(-1, 3), a[-6:].reshape(-1, 3), a[:, :6].reshape(-1, 3),
                                   a[:, -6:].reshape(-1, 3)]), axis=0)
    close = np.abs(a - bg).sum(-1) < 36
    a[close] = 255
    return Image.fromarray(a.astype("uint8"))


def split(turn_png):
    from PIL import Image
    im = Image.open(turn_png).convert("RGB")
    w, h = im.width // 3, im.height // 2
    return {k: im.crop(((i % 3) * w, (i // 3) * h, (i % 3 + 1) * w, (i // 3 + 1) * h)) for i, k in enumerate(ORDER)}


def sheet2x2(cells, out):
    """Front, back, left, right on white, 1024x1024, the sculptor's layout."""
    from PIL import Image
    S = 512
    sheet = Image.new("RGB", (1024, 1024), (255, 255, 255))
    for k, (x, y) in {"front": (0, 0), "back": (S, 0), "left": (0, S), "right": (S, S)}.items():
        c = to_white(cells[k])
        c.thumbnail((S, S))
        sheet.paste(c, (x + (S - c.width) // 2, y + (S - c.height) // 2))
    sheet.save(out)
    return out


def atlas(turn_png, out):
    """The whole turnaround on white: the texture the model is painted from."""
    from PIL import Image
    to_white(Image.open(turn_png)).save(out)
    return out
