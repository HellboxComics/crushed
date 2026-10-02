"""The drawing room (ComfyUI + FLUX schnell on this Mac), guided by a picture: the real photos are laid into the
four views of the sheet and FLUX repaints it as a clean product sheet. denoise ~0.7 keeps the real colors, shape and
logo placement and redraws everything else. Same models and settings as ~/Desktop/AI/draw.py, plus an input image."""
import io
import json
import os
import random
import time
import urllib.parse
import urllib.request
import uuid

ROOM = os.environ.get("DRAWING_ROOM", "http://127.0.0.1:8188")


def _upload(path):
    bnd = uuid.uuid4().hex
    name = f"crushed_{uuid.uuid4().hex[:10]}.png"
    data = open(path, "rb").read()
    body = (f"--{bnd}\r\nContent-Disposition: form-data; name=\"image\"; filename=\"{name}\"\r\n"
            f"Content-Type: image/png\r\n\r\n").encode() + data + \
        f"\r\n--{bnd}\r\nContent-Disposition: form-data; name=\"overwrite\"\r\n\r\ntrue\r\n--{bnd}--\r\n".encode()
    req = urllib.request.Request(ROOM + "/upload/image", data=body,
                                 headers={"content-type": f"multipart/form-data; boundary={bnd}"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)["name"]


def sheet_from_photos(photos, out):
    """A 1024x1024 starting sheet: FRONT and BACK from the photos, LEFT and RIGHT squeezed from them."""
    from PIL import Image, ImageOps
    S = 512
    canvas = Image.new("RGB", (1024, 1024), (255, 255, 255))
    ims = [Image.open(p).convert("RGB") for p in photos[:2]]
    front = ims[0]
    back = ims[1] if len(ims) > 1 else ImageOps.mirror(front)

    def put(im, x, y, squeeze=1.0):
        im = im.copy()
        im = im.resize((max(1, int(im.width * squeeze)), im.height))
        im.thumbnail((S - 40, S - 40))
        canvas.paste(im, (x + (S - im.width) // 2, y + (S - im.height) // 2))
    put(front, 0, 0)
    put(back, S, 0)
    put(front, 0, S, 0.45)
    put(ImageOps.mirror(front), S, S, 0.45)
    canvas.save(out)
    return out


def draw_guided(prompt, init_png, out, denoise=0.72, seed=None, timeout=900):
    seed = seed if seed is not None else random.randint(1, 2 ** 31)
    img = _upload(init_png)
    wf = {
        "1": {"class_type": "UNETLoader", "inputs": {"unet_name": "flux1-schnell.safetensors", "weight_dtype": "default"}},
        "2": {"class_type": "DualCLIPLoader", "inputs": {"clip_name1": "t5xxl_fp16.safetensors", "clip_name2": "clip_l.safetensors", "type": "flux"}},
        "3": {"class_type": "VAELoader", "inputs": {"vae_name": "ae.safetensors"}},
        "4": {"class_type": "CLIPTextEncode", "inputs": {"text": prompt, "clip": ["2", 0]}},
        "7": {"class_type": "CLIPTextEncode", "inputs": {"text": "", "clip": ["2", 0]}},
        "10": {"class_type": "LoadImage", "inputs": {"image": img}},
        "11": {"class_type": "VAEEncode", "inputs": {"pixels": ["10", 0], "vae": ["3", 0]}},
        "6": {"class_type": "KSampler", "inputs": {"model": ["1", 0], "positive": ["4", 0], "negative": ["7", 0],
                                                  "latent_image": ["11", 0], "seed": seed, "steps": 4, "cfg": 1.0,
                                                  "sampler_name": "euler", "scheduler": "simple", "denoise": denoise}},
        "8": {"class_type": "VAEDecode", "inputs": {"samples": ["6", 0], "vae": ["3", 0]}},
        "9": {"class_type": "SaveImage", "inputs": {"images": ["8", 0], "filename_prefix": "crushed_ref"}},
    }
    body = json.dumps({"prompt": wf, "client_id": uuid.uuid4().hex}).encode()
    req = urllib.request.Request(ROOM + "/prompt", data=body, headers={"content-type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        pid = json.load(r)["prompt_id"]
    t0 = time.time()
    while time.time() - t0 < timeout:
        time.sleep(3)
        with urllib.request.urlopen(ROOM + "/history/" + pid, timeout=15) as r:
            h = json.load(r)
        if pid in h:
            if h[pid].get("status", {}).get("status_str") == "error":
                return False
            for node in h[pid].get("outputs", {}).values():
                for im in node.get("images", []):
                    q = urllib.parse.urlencode({"filename": im["filename"], "subfolder": im.get("subfolder", ""),
                                                "type": im.get("type", "output")})
                    with urllib.request.urlopen(ROOM + "/view?" + q, timeout=30) as r2:
                        open(out, "wb").write(r2.read())
                    return True
    return False
