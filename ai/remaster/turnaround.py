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
          "left to right: the FRONT view, the LEFT SIDE view (the object turned so the side that was on the viewer's "
          "left now faces the camera), the BACK view. Bottom row, left to right: the RIGHT SIDE view (the side that "
          "was on the viewer's right), the TOP view (camera directly overhead, perfectly flat, only the top surface "
          "visible, no perspective), the BOTTOM view (camera directly underneath, perfectly flat, only the underside). The object is exactly "
          "the same size, centered in each cell, upright the same way in the four side views, with the same "
          "colors, wear and printing in every view; each view shows what really is on that side. No captions, no "
          "labels, no text outside the object, no measurements, no hands, no props, no other objects. Every view is "
          "a flat, straight-on orthographic photo like a technical drawing: no perspective, no tilt, no corners of "
          "the neighboring sides showing. The object: ")

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


def _era(t):
    from refs import era
    return era(t)


def describe(name, display, years, notes, seed, redo=False):
    out = os.path.join(PROMPTS, name + ".turn.txt")
    if os.path.exists(out) and not redo:
        return open(out).read().strip()
    text = _ask().ask(WRITER, BRIEF.format(display=_era(display), years=_era(str(years)), notes=notes or "-", seed=seed or "-"),
                      kind="write", timeout=600)
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


def free_room():
    """Tell the drawing room (ComfyUI) to let go of the 40 GB drawing model, so the sculptor gets the memory.
    ComfyUI's own POST /free; the model loads again by itself on the next drawing."""
    try:
        body = json.dumps({"unload_models": True, "free_memory": True}).encode()
        urllib.request.urlopen(urllib.request.Request(ROOM + "/free", data=body,
                                                      headers={"content-type": "application/json"}), timeout=30)
    except Exception:
        pass


LIGHTNING = "Qwen-Image-2512-Lightning-8steps-V1.0-bf16.safetensors"     # the official 8-step speed-up (Apache 2.0)
LORA_DIR = os.path.expanduser("~/.hellbox/drawing-room/ComfyUI/models/loras")


def _upload(png_bytes, name):
    boundary = uuid.uuid4().hex
    body = (f"--{boundary}\r\nContent-Disposition: form-data; name=\"image\"; filename=\"{name}\"\r\n"
            f"Content-Type: image/png\r\n\r\n").encode() + png_bytes + f"\r\n--{boundary}--\r\n".encode()
    req = urllib.request.Request(ROOM + "/upload/image", data=body,
                                 headers={"content-type": f"multipart/form-data; boundary={boundary}"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r).get("name", name)


def _run_all(wf, timeout=900):
    """Send a workflow, wait, return {save node id: picture bytes}."""
    body = json.dumps({"prompt": wf, "client_id": uuid.uuid4().hex}).encode()
    req = urllib.request.Request(ROOM + "/prompt", data=body, headers={"content-type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        pid = json.load(r)["prompt_id"]
    t0 = time.time()
    while time.time() - t0 < timeout:
        time.sleep(3)
        with urllib.request.urlopen(ROOM + "/history/" + pid, timeout=20) as r:
            h = json.load(r)
        if pid in h:
            st = h[pid].get("status", {})
            if st.get("status_str") == "error":
                raise RuntimeError("the drawing room failed: " + json.dumps(st)[:400])
            got = {}
            for nid, node in h[pid].get("outputs", {}).items():
                for im in node.get("images", []):
                    q = urllib.parse.urlencode({"filename": im["filename"], "subfolder": im.get("subfolder", ""),
                                                "type": im.get("type", "output")})
                    with urllib.request.urlopen(ROOM + "/view?" + q, timeout=60) as r2:
                        got[nid] = r2.read()
            if got:
                return got
    raise RuntimeError("the drawing room took too long")


CUTOUT = "birefnet.safetensors"          # BiRefNet (MIT), ComfyUI's own repackaging (Comfy-Org/BiRefNet)


def photo_mask(png):
    """The cut-out model (BiRefNet, in the drawing room) on one whole photo -> <photo>_mask.png, white = object.
    Kept once made."""
    import io
    from PIL import Image
    out = png.rsplit(".", 1)[0] + "_mask.png"
    if os.path.exists(out) and os.path.getmtime(out) >= os.path.getmtime(png):
        return out
    im = Image.open(png).convert("RGB")
    b = io.BytesIO()
    im.save(b, "PNG")
    name = _upload(b.getvalue(), f"crushed_photo_{uuid.uuid4().hex[:8]}.png")
    wf = {"0": {"class_type": "LoadBackgroundRemovalModel", "inputs": {"bg_removal_name": CUTOUT}},
          "1": {"class_type": "LoadImage", "inputs": {"image": name}},
          "2": {"class_type": "RemoveBackground", "inputs": {"bg_removal_model": ["0", 0], "image": ["1", 0]}},
          "3": {"class_type": "MaskToImage", "inputs": {"mask": ["2", 0]}},
          "4": {"class_type": "SaveImage", "inputs": {"images": ["3", 0], "filename_prefix": "crushed_pmask"}}}
    got = _run_all(wf)
    Image.open(io.BytesIO(got["4"])).convert("L").resize(im.size).save(out)
    return out


def masks(turn_png):
    """Exactly what is object and what is background, in each of the six views, from a real cut-out model (BiRefNet)
    instead of guessing by color: a grey Furby on a grey studio backdrop came apart under color guessing. Saved
    next to the drawing as <name>_mask.png (white = object). Skipped when already made for this drawing."""
    import io
    from PIL import Image
    out = turn_png[:-4] + "_mask.png"
    if os.path.exists(out) and os.path.getmtime(out) >= os.path.getmtime(turn_png):
        return out
    im = Image.open(turn_png).convert("RGB")
    w, h = im.width // 3, im.height // 2
    wf = {"0": {"class_type": "LoadBackgroundRemovalModel", "inputs": {"bg_removal_name": CUTOUT}}}
    for i in range(6):
        cell = im.crop(((i % 3) * w, (i // 3) * h, (i % 3 + 1) * w, (i // 3 + 1) * h))
        b = io.BytesIO()
        cell.save(b, "PNG")
        name = _upload(b.getvalue(), f"crushed_cell_{uuid.uuid4().hex[:8]}_{i}.png")
        a = 10 * (i + 1)
        wf[str(a)] = {"class_type": "LoadImage", "inputs": {"image": name}}
        wf[str(a + 1)] = {"class_type": "RemoveBackground", "inputs": {"bg_removal_model": ["0", 0], "image": [str(a), 0]}}
        wf[str(a + 2)] = {"class_type": "MaskToImage", "inputs": {"mask": [str(a + 1), 0]}}
        wf[str(a + 3)] = {"class_type": "SaveImage", "inputs": {"images": [str(a + 2), 0], "filename_prefix": "crushed_mask"}}
    got = _run_all(wf)
    sheet = Image.new("L", im.size, 0)
    for i in range(6):
        m = Image.open(io.BytesIO(got[str(10 * (i + 1) + 3)])).convert("L").resize((w, h))
        sheet.paste(m, ((i % 3) * w, (i // 3) * h))
    sheet.save(out)
    return out


def _run(wf, out, timeout=3600):
    """Send a workflow to the drawing room (ComfyUI), wait, save its first picture to out."""
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


UPSCALER = "RealESRGAN_x4plus.pth"      # Real-ESRGAN (BSD-3), from its own GitHub release


LABEL = ("A flat, straight-on scan of the complete printed wrap-around label of the object below, unrolled into one "
         "rectangle exactly as it is printed: everything printed all the way around the side, from its top edge to its "
         "bottom edge, filling the whole image edge to edge. No background, no shadows, no curvature, no perspective, "
         "no object shape, no captions. The left and right edges continue into each other seamlessly. The object: ")


EDIT_UNET = "qwen_image_edit_2511_bf16.safetensors"     # Qwen-Image-Edit-2511 (Apache 2.0), ComfyUI's own repackaging
EDIT_LORA = "Qwen-Image-Edit-2511-Lightning-8steps-V1.0-bf16.safetensors"   # its official 8-step speed-up
COMFY_MODELS = os.path.expanduser("~/.hellbox/drawing-room/ComfyUI/models")
FROM_PHOTO = ("Picture 1 is a real photograph of a real product. Make a professional 3D modeling reference sheet of "
              "EXACTLY this object, copied faithfully from the photograph: the same shape and proportions, the same "
              "colors, materials and wear, the same logos, printed words and markings in the same places. "
              "Copy the surface texture at the same scale and softness as the photograph (short soft plush stays "
              "short and soft, smooth plastic stays smooth); never make it spikier, shaggier or more cartoonish. "
              "Sides the photograph does not show continue the same material plainly: do not invent panels, "
              "stickers, barcodes or writing there, and only show words that are in the photograph or named in the "
              "description, on the side where they really are. The TOP view looks straight down onto the highest "
              "part of the object as it stands in the photograph (for a creature or figure, the top of its head), "
              "and nothing that belongs underneath appears in it. ")


def can_edit():
    return os.path.exists(os.path.join(COMFY_MODELS, "diffusion_models", EDIT_UNET))


def draw_from_photos(description, photos, out, width=None, height=None, prefix=None, seed=None, timeout=3600):
    """The drawing made FROM real photos (Qwen-Image-Edit-2511, the photo-editing version of the drawing model):
    the photos say what the product really looks like, the words only fill in the sides no photo shows. Follows
    ComfyUI's own Qwen-Image-Edit-2511 template (reference method index_timestep_zero, CFGNorm, shift 3.1)."""
    import io
    from PIL import Image
    seed = seed if seed is not None else random.randint(1, 2 ** 31)
    fast = os.path.exists(os.path.join(LORA_DIR, EDIT_LORA))
    wf = {
        "1": {"class_type": "UNETLoader", "inputs": {"unet_name": EDIT_UNET, "weight_dtype": "default"}},
        "2": {"class_type": "CLIPLoader", "inputs": {"clip_name": "qwen_2.5_vl_7b.safetensors", "type": "qwen_image"}},
        "3": {"class_type": "VAELoader", "inputs": {"vae_name": "qwen_image_vae.safetensors"}},
        "4": {"class_type": "ModelSamplingAuraFlow", "inputs": {"model": ["11", 0] if fast else ["1", 0], "shift": 3.1}},
        "12": {"class_type": "CFGNorm", "inputs": {"model": ["4", 0], "strength": 1.0}},
        "7": {"class_type": "EmptySD3LatentImage", "inputs": {"width": width or W, "height": height or H, "batch_size": 1}},
        "9": {"class_type": "VAEDecode", "inputs": {"samples": ["8", 0], "vae": ["3", 0]}},
        "10": {"class_type": "SaveImage", "inputs": {"images": ["9", 0], "filename_prefix": "crushed_photo_turn"}},
    }
    if fast:
        wf["11"] = {"class_type": "LoraLoaderModelOnly", "inputs": {"model": ["1", 0], "lora_name": EDIT_LORA,
                                                                   "strength_model": 1.0}}
    imgs = {}
    for i, p in enumerate(photos[:3]):
        im = Image.open(p).convert("RGB")
        b = io.BytesIO()
        im.save(b, "PNG")
        name = _upload(b.getvalue(), f"crushed_ref_{uuid.uuid4().hex[:8]}_{i}.png")
        wf[str(20 + i)] = {"class_type": "LoadImage", "inputs": {"image": name}}
        imgs[f"image{i + 1}"] = [str(20 + i), 0]
    text = (prefix or (FROM_PHOTO + LAYOUT)) + for_drawing(description)
    wf["5"] = {"class_type": "TextEncodeQwenImageEditPlus", "inputs": {"clip": ["2", 0], "prompt": text, "vae": ["3", 0], **imgs}}
    wf["6"] = {"class_type": "TextEncodeQwenImageEditPlus", "inputs": {"clip": ["2", 0], "prompt": "", "vae": ["3", 0], **imgs}}
    wf["15"] = {"class_type": "FluxKontextMultiReferenceLatentMethod",
                "inputs": {"conditioning": ["5", 0], "reference_latents_method": "index_timestep_zero"}}
    wf["16"] = {"class_type": "FluxKontextMultiReferenceLatentMethod",
                "inputs": {"conditioning": ["6", 0], "reference_latents_method": "index_timestep_zero"}}
    wf["8"] = {"class_type": "KSampler", "inputs": {"model": ["12", 0], "positive": ["15", 0], "negative": ["16", 0],
                                                    "latent_image": ["7", 0], "seed": seed, "steps": 8 if fast else 40,
                                                    "cfg": 1.0 if fast else 3.0, "sampler_name": "euler",
                                                    "scheduler": "simple", "denoise": 1.0}}
    return _run(wf, out, timeout)


SIDES = ("A professional 3D modeling reference sheet: a 2 by 2 grid of four orthographic studio product photos of "
         "the SAME single object standing upright exactly as in the photograph, on a plain light grey background, "
         "evenly lit, true colors, sharp focus, the camera level with the middle of the object. Top row, left to "
         "right: the FRONT view, the LEFT SIDE view (the object turned so the side that was on the viewer's left now "
         "faces the camera). Bottom row, left to right: the BACK view, the RIGHT SIDE view (the side that was on the "
         "viewer's right). Exactly the same size and upright the same way in all four; each view shows what really "
         "is on that side, and anything that is on the underside or the very top is not seen in these four views. "
         "No captions, no labels, no text outside the object, no measurements, no hands, no props, no other "
         "objects, no perspective, no tilt. The object: ")

ENDS = ("Picture 1 shows this exact object from the front, the left, the back and the right. Picture 2 is a real "
        "photograph of it. Make two orthographic studio product photos side by side on the same plain light grey "
        "background, evenly lit, the same size scale as Picture 1. LEFT half: the TOP view, the camera straight "
        "above looking down at the top of the object as it stands upright (for a creature or figure, the top of its "
        "head, with its ears, hair or tuft seen from above), the front of the object toward the bottom edge of the "
        "picture. RIGHT half: the BOTTOM view, the camera straight below looking up at the surface it stands on "
        "(its feet or base, and any battery door, label or markings that are underneath), the front toward the top "
        "edge of the picture. Same colors, materials and surface texture as Picture 1 and the photograph. Nothing "
        "that is underneath appears in the top view; nothing that is on top appears in the bottom view. No "
        "captions, no text outside the object, no perspective, no other objects. The object: ")


def sides_only(description):
    """The words for the four side views: anything said to be underneath or on the bottom is left out, because
    the drawing model puts every detail it is told about somewhere it can see (the Furby's battery door landed on
    its back)."""
    import re
    parts = re.split(r"(?<=[,.;])\s+", description)
    keep = [p for p in parts if not re.search(r"underneath|underside|bottom|\bbase\b|beneath", p, re.I)]
    text = " ".join(keep).strip()
    return text if len(text) > 40 else description


def _silhouette(im):
    """Rough object mask of one cell: what differs from the plain background in its corners."""
    import numpy as np
    a = np.asarray(im.convert("RGB").resize((256, 256))).astype(int)
    bg = np.median(np.concatenate([a[:8, :8], a[:8, -8:], a[-8:, :8], a[-8:, -8:]]).reshape(-1, 3), 0)
    return np.abs(a - bg).sum(-1) > 45


def _iou(a, b):
    return (a & b).sum() / max(1, (a | b).sum())


def photo_front(path, C):
    """The real photo itself as the front view (no redraw can beat the real thing): centered on the plain sheet
    background, the object filling the cell the way the drawn views do."""
    from PIL import Image
    import numpy as np
    im = Image.open(path).convert("RGB")
    im.thumbnail((int(C * 0.92), int(C * 0.92)), Image.LANCZOS)
    a = np.asarray(im)
    bg = tuple(int(v) for v in np.median(np.concatenate([a[:6, :6], a[:6, -6:], a[-6:, :6], a[-6:, -6:]]).reshape(-1, 3), 0))
    cell = Image.new("RGB", (C, C), bg)            # the photo's own background color around it, no hard frame
    cell.paste(im, ((C - im.width) // 2, (C - im.height) // 2))
    return cell


def draw_from_photos_six(description, photos, out, seed=None, front_is_photo=False):
    """Six views in two drawings, because one drawing of six cells kept putting the underside's battery door on
    the top and the back: first the four side views from the photo (told nothing about the underside), then the
    top and the bottom drawn while looking at those four sides and the photo. When the real photo is a straight
    front view it IS the front view. The two side views are checked to face opposite ways (the model sometimes
    draws both facing the same way); a same-facing right view is mirrored. Put together into the 3 by 2 sheet."""
    from PIL import Image
    tmp_a, tmp_b = out[:-4] + "_sides.png", out[:-4] + "_ends.png"
    draw_from_photos(sides_only(description), photos, tmp_a, width=1328, height=1328,
                     prefix=FROM_PHOTO + SIDES, seed=seed)
    draw_from_photos(description, [tmp_a] + list(photos[:2]), tmp_b, width=1600, height=800, prefix=ENDS, seed=seed)
    a, b = Image.open(tmp_a).convert("RGB"), Image.open(tmp_b).convert("RGB")
    C = H // 2
    ha, wa, hb, wb = a.height // 2, a.width // 2, b.height, b.width // 2
    cells = {"front": a.crop((0, 0, wa, ha)), "left": a.crop((wa, 0, 2 * wa, ha)),
             "back": a.crop((0, ha, wa, 2 * ha)), "right": a.crop((wa, ha, 2 * wa, 2 * ha)),
             "top": b.crop((0, 0, wb, hb)), "bottom": b.crop((wb, 0, 2 * wb, hb))}
    cells = {k: v.resize((C, C), Image.LANCZOS) for k, v in cells.items()}
    L, R = _silhouette(cells["left"]), _silhouette(cells["right"])
    same, mirrored = _iou(L, R), _iou(L, R[:, ::-1])
    if same > mirrored + 0.05:
        print(f"  the two side views faced the same way ({same:.2f} vs {mirrored:.2f}): right view mirrored", flush=True)
        cells["right"] = cells["right"].transpose(Image.FLIP_LEFT_RIGHT)
    if front_is_photo:
        cells["front"] = photo_front(photos[0], C)
    sheet = Image.new("RGB", (3 * C, 2 * C), (235, 235, 235))
    for i, k in enumerate(ORDER):
        sheet.paste(cells[k], ((i % 3) * C, (i // 3) * C))
    sheet.save(out)
    return out

def label_size(circumference, height):
    """A drawing size with the label's real proportions (about 1.6 megapixels, multiples of 16)."""
    a = max(0.4, min(3.0, circumference / max(height, 1e-6)))
    px = 1_670_000
    w = int(round((px * a) ** 0.5 / 16)) * 16
    h = int(round((px / a) ** 0.5 / 16)) * 16
    return w, h


def draw_label(description, out, circumference, height, photos=None):
    """The whole printed wrap of a round object (a can, a battery) as one flat picture: painted on as one piece,
    it has no seams and no logo twice, which four separate views of a cylinder can't promise. From the real photos
    when there are any."""
    w, h = label_size(circumference, height)
    if photos and can_edit():
        return draw_from_photos(description, photos, out, width=w, height=h,
                                prefix=("Picture 1 is a real photograph of a real product. Do NOT draw the product itself: no "
                                        "can, no battery, no bottle, no ends, no shadow. Peel its printed label off in "
                                        "your mind and show only that, laid perfectly flat. " + LABEL))
    return draw(description, out, width=w, height=h, prefix=LABEL)


def flat_label_ok(png):
    """True when a drawn label really is a flat print filling the picture. False when the model drew the product
    standing on a background instead (light, plain, grey-white margins around it), which wrapped onto a can or a
    battery shows as a picture of the product inside a white tube."""
    import numpy as np
    from PIL import Image
    a = np.asarray(Image.open(png).convert("RGB").resize((400, 400))).astype(int)
    e = 14
    border = np.concatenate([a[:e].reshape(-1, 3), a[-e:].reshape(-1, 3), a[:, :e].reshape(-1, 3), a[:, -e:].reshape(-1, 3)])
    plain = (border.min(1) > 175) & (border.max(1) - border.min(1) < 20)
    return plain.mean() < 0.25


def upscale(png, timeout=900, force=False):
    """The finished turnaround made twice as sharp (Real-ESRGAN 4x, then down to 2x): letters and edges crisp
    instead of soft when the model is seen up close. Done in place; a picture already this size is left alone."""
    from PIL import Image
    with Image.open(png) as im:
        if im.width >= 2 * W and not force:
            return png
    name = f"crushed_up_{uuid.uuid4().hex[:8]}.png"
    boundary = uuid.uuid4().hex
    data = open(png, "rb").read()
    body = (f"--{boundary}\r\nContent-Disposition: form-data; name=\"image\"; filename=\"{name}\"\r\n"
            f"Content-Type: image/png\r\n\r\n").encode() + data + f"\r\n--{boundary}--\r\n".encode()
    req = urllib.request.Request(ROOM + "/upload/image", data=body,
                                 headers={"content-type": f"multipart/form-data; boundary={boundary}"})
    with urllib.request.urlopen(req, timeout=60) as r:
        up = json.load(r)
    wf = {
        "1": {"class_type": "LoadImage", "inputs": {"image": up.get("name", name)}},
        "2": {"class_type": "UpscaleModelLoader", "inputs": {"model_name": UPSCALER}},
        "3": {"class_type": "ImageUpscaleWithModel", "inputs": {"upscale_model": ["2", 0], "image": ["1", 0]}},
        "4": {"class_type": "ImageScaleBy", "inputs": {"image": ["3", 0], "upscale_method": "lanczos", "scale_by": 0.5}},
        "5": {"class_type": "SaveImage", "inputs": {"images": ["4", 0], "filename_prefix": "crushed_up"}},
    }
    tmp = png + ".up.png"
    _run(wf, tmp, timeout)
    os.replace(tmp, png)
    return png


def for_drawing(description):
    """The words the drawing model gets: measurements taken out (it printed '14.0 x 5.0 x 20.0 cm' right onto the
    Pop-Tarts box). The size still sets the model's real size; it just isn't drawn."""
    import re
    from refs import era
    parts = re.split(r"(?<=[,.;])\s+", era(description))
    keep = [p for p in parts if not re.search(r"\d\s*(cm|mm|in\b|inch)|real size", p, re.I)]
    text = " ".join(keep).strip()
    return text if len(text) > 40 else description


def draw(description, out, seed=None, steps=None, timeout=3600, width=None, height=None, prefix=None):
    """One 1584x1056 turnaround from Qwen-Image 2512 (bf16), its own text encoder and VAE. With the Lightning
    LoRA installed it takes 8 steps at guidance 1 (one pass per step) instead of 30 at guidance 4: ~7x faster."""
    seed = seed if seed is not None else random.randint(1, 2 ** 31)
    fast = os.path.exists(os.path.join(LORA_DIR, LIGHTNING))
    steps = steps or (8 if fast else 30)
    cfg = 1.0 if fast else 4.0
    wf = {
        "1": {"class_type": "UNETLoader", "inputs": {"unet_name": "qwen_image_2512_bf16.safetensors", "weight_dtype": "default"}},
        "2": {"class_type": "CLIPLoader", "inputs": {"clip_name": "qwen_2.5_vl_7b.safetensors", "type": "qwen_image"}},
        "3": {"class_type": "VAELoader", "inputs": {"vae_name": "qwen_image_vae.safetensors"}},
        "4": {"class_type": "ModelSamplingAuraFlow", "inputs": {"model": ["11", 0] if fast else ["1", 0], "shift": 3.1}},
        "5": {"class_type": "CLIPTextEncode", "inputs": {"text": (prefix or LAYOUT) + for_drawing(description), "clip": ["2", 0]}},
        "6": {"class_type": "CLIPTextEncode", "inputs": {"text": "blurry, deformed, different objects, inconsistent, "
                                                                 "captions, watermark, hands, people", "clip": ["2", 0]}},
        "7": {"class_type": "EmptySD3LatentImage", "inputs": {"width": width or W, "height": height or H, "batch_size": 1}},
        "8": {"class_type": "KSampler", "inputs": {"model": ["4", 0], "positive": ["5", 0], "negative": ["6", 0],
                                                  "latent_image": ["7", 0], "seed": seed, "steps": steps, "cfg": cfg,
                                                  "sampler_name": "euler", "scheduler": "simple", "denoise": 1.0}},
        "9": {"class_type": "VAEDecode", "inputs": {"samples": ["8", 0], "vae": ["3", 0]}},
        "10": {"class_type": "SaveImage", "inputs": {"images": ["9", 0], "filename_prefix": "crushed_turn"}},
    }
    if fast:
        wf["11"] = {"class_type": "LoraLoaderModelOnly", "inputs": {"model": ["1", 0], "lora_name": LIGHTNING,
                                                                   "strength_model": 1.0}}
    return _run(wf, out, timeout)


def to_white(im):
    """The studio background (grey, often a gradient with a soft shadow) to pure white, so every later step sees
    only the object. Flood-fills from the edges through light, low-color pixels, stepping neighbor to neighbor, so a
    gradient is followed but the object (darker or colored) stops it."""
    import numpy as np
    from collections import deque
    from PIL import Image
    if max(im.size) > 640:                  # a big (sharpened) picture: find the background small, apply it full size
        big = np.asarray(im.convert("RGB")).copy()
        s = 640 / max(im.size)
        small = to_white(im.convert("RGB").resize((round(im.width * s), round(im.height * s)), Image.BILINEAR))
        bgm = (np.asarray(small) == 255).all(-1)
        bgm = np.asarray(Image.fromarray(bgm.astype(np.uint8) * 255).resize(im.size, Image.NEAREST)) > 127
        lum = big.astype(np.int16).mean(-1)
        sat = big.max(-1).astype(np.int16) - big.min(-1)
        bgm &= (lum > 60) & (sat < 22)        # never whiten a real object pixel along the edge
        big[bgm] = 255
        return Image.fromarray(_no_dividers(big))
    a = np.asarray(im.convert("RGB")).astype(np.int16)
    h, w = a.shape[:2]
    lum = a.mean(-1)
    sat = a.max(-1) - a.min(-1)
    bgish = (lum > 60) & (sat < 22)            # light grey studio background and its soft grey shadows
    seen = np.zeros((h, w), bool)
    q = deque()
    for x in range(w):
        for y in (0, h - 1):
            if bgish[y, x] and not seen[y, x]:
                seen[y, x] = True
                q.append((y, x))
    for y in range(h):
        for x in (0, w - 1):
            if bgish[y, x] and not seen[y, x]:
                seen[y, x] = True
                q.append((y, x))
    while q:
        y, x = q.popleft()
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            ny, nx = y + dy, x + dx
            if 0 <= ny < h and 0 <= nx < w and not seen[ny, nx] and bgish[ny, nx] \
                    and abs(int(lum[ny, nx]) - int(lum[y, x])) < 12:
                seen[ny, nx] = True
                q.append((ny, nx))
    a[seen] = 255
    return Image.fromarray(_no_dividers(a).astype("uint8"))


def _no_dividers(a):
    """Thin divider lines along the cell edges (the drawing model draws some): erased."""
    h, w = a.shape[:2]
    ink = (a.min(-1) < 200)
    e = max(4, int(min(h, w) * 0.08))
    for x in list(range(e)) + list(range(w - e, w)):
        if ink[:, x].mean() > 0.6:
            a[:, x] = 255
    for y in list(range(e)) + list(range(h - e, h)):
        if ink[y, :].mean() > 0.6:
            a[y, :] = 255
    return a


def split(turn_png):
    from PIL import Image
    im = Image.open(turn_png).convert("RGB")
    w, h = im.width // 3, im.height // 2
    m = int(min(w, h) * 0.02)               # skip the thin divider lines the model sometimes draws between views
    return {k: im.crop(((i % 3) * w + m, (i // 3) * h + m, (i % 3 + 1) * w - m, (i // 3 + 1) * h - m))
            for i, k in enumerate(ORDER)}


def cutouts(turn_png):
    """{view: (picture on pure white, object mask or None)}. Uses the cut-out model's masks when they exist
    (<name>_mask.png), and the color guess only as a fallback."""
    import numpy as np
    from PIL import Image
    mp = turn_png[:-4] + "_mask.png"
    cells = split(turn_png)
    if not os.path.exists(mp):
        return {k: (to_white(c), None) for k, c in cells.items()}
    mm = Image.open(mp).convert("L")
    if mm.size != Image.open(turn_png).size:
        mm = mm.resize(Image.open(turn_png).size)
    tmp = turn_png[:-4] + "_masktmp.png"
    mm.convert("RGB").save(tmp)
    mcells = split(tmp)
    os.remove(tmp)
    out = {}
    for k, c in cells.items():
        m = np.asarray(mcells[k].convert("L")) > 127
        a = np.asarray(c.convert("RGB")).copy()
        a[~m] = 255
        out[k] = (Image.fromarray(a), m)
    return out


def sheet2x2(cells, out):
    """Front, back, left, right on white, 1024x1024, the sculptor's layout. cells: {view: picture} (cleaned here)
    or {view: (cleaned picture, mask)} from cutouts()."""
    from PIL import Image
    S = 512
    sheet = Image.new("RGB", (1024, 1024), (255, 255, 255))
    for k, (x, y) in {"front": (0, 0), "back": (S, 0), "left": (0, S), "right": (S, S)}.items():
        c = cells[k][0] if isinstance(cells[k], tuple) else to_white(cells[k])
        if isinstance(cells[k], tuple) and cells[k][1] is not None and cells[k][1].any():
            import numpy as np
            ys, xs = np.nonzero(cells[k][1])
            c = c.crop((xs.min(), ys.min(), xs.max() + 1, ys.max() + 1))
        c.thumbnail((S, S))
        sheet.paste(c, (x + (S - c.width) // 2, y + (S - c.height) // 2))
    sheet.save(out)
    return out


def atlas(turn_png, out):
    """The whole turnaround on white: the texture the model is painted from."""
    from PIL import Image
    im = Image.open(turn_png).convert("RGB")
    sheet = Image.new("RGB", im.size, (255, 255, 255))
    w, h = im.width // 3, im.height // 2
    for i, (k, c) in enumerate(split(turn_png).items()):        # each view cleaned on its own, dividers dropped
        c = to_white(c)
        sheet.paste(c, ((i % 3) * w + (w - c.width) // 2, (i // 3) * h + (h - c.height) // 2))
    sheet.save(out)
    return out
