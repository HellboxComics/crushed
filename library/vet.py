"""The local vision model looks at every hunted photo and says, as JSON: is it this exact product, is it from the
right era, which side shows, is it straight-on, sharp and the whole object. Only good photos go on.
Uses Qwen 3.8 (27B, the newest local vision model, chosen 2026-10-02), all on the Mac through Ollama."""
import base64
import json
import os
import re
import sys
import urllib.request

OLLAMA = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434")
OLLAMA = OLLAMA if OLLAMA.startswith("http") else "http://" + OLLAMA
PREFER = ["qwen3.8:27b-q8_0", "qwen3.8:27b", "qwen3.5:122b", "qwen2.5vl:7b"]   # newest first
QUICK = "qwen3.6:35b"                     # fast first look


def _call(path, body, timeout=900):
    req = urllib.request.Request(OLLAMA + path, data=json.dumps(body).encode(), headers={"content-type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def has(name):
    try:
        have = [m["name"] for m in json.loads(urllib.request.urlopen(OLLAMA + "/api/tags", timeout=20).read()).get("models", [])]
    except Exception:
        return False
    return name in have or name + ":latest" in have


def model():
    try:
        have = \
            [m["name"] for m in json.loads(urllib.request.urlopen(OLLAMA + "/api/tags", timeout=20).read()).get("models", [])]
    except Exception:
        return None
    for m in PREFER:
        if m in have or m + ":latest" in have:
            return m
    return None


ASK = """Product: {display}
Era: {era}
Look at this photo and answer ONLY with JSON, no other words:
{{"match": 0-10 how surely this shows exactly this product (right brand, model and design version),
  "era_ok": true if the design fits that era (packaging from within about 3 years counts), false if clearly newer/older,
  "count": how many of the product are visible,
  "view": which side of the product faces the camera most: "front", "back", "left", "right", "top", "bottom" or "mixed",
  "straight_on": true if the camera looks squarely at that side (not steeply from above or at a sharp angle),
  "sharp": true if the printing on it is in focus and readable,
  "whole": true if the whole product is in the picture (not cut off, not mostly hidden by hands or packaging),
  "problems": "short note of anything wrong, or empty"}}"""


def vet(path, display, era, use=None):
    use = use or model()
    if not use:
        return None
    body = {"model": use, "stream": False, "format": "json", "think": False, "options": {"temperature": 0},
            "messages": [{"role": "user", "content": ASK.format(display=display, era=era),
                          "images": [base64.b64encode(open(path, "rb").read()).decode()]}]}
    try:
        txt = _call("/api/chat", body).get("message", {}).get("content", "{}")
        v = json.loads(re.search(r"\{.*\}", txt, re.S).group(0))
    except Exception as e:
        return {"match": 0, "problems": f"could not judge: {e}"}
    v["model"] = use
    return v


def good(v, need=7):
    return (v and v.get("match", 0) >= need and v.get("era_ok", True) is not False and v.get("sharp", True)
            and v.get("whole", True) and v.get("straight_on", True))


if __name__ == "__main__":
    print(json.dumps(vet(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else ""), indent=1))
