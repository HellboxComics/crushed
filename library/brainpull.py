"""GET A BRAIN ONTO THIS MAC (free download from Ollama's library), then PROVE it works before anything uses it:
it loads, it answers, it calls a tool correctly, and it can see a picture. The result goes to
~/crushed-render/remaster/brains/<name>.json and ~/crushed-render/brains.log. Nothing switches to it by itself.

    .venv/bin/python library/brainpull.py qwen3.8-flash-next:125b-mlx

The test waits until no asset run is going (it takes the same one-run lock), so a 100 GB brain never loads
while Blender or the judge is working.
"""
import base64
import fcntl
import io
import json
import os
import re
import sys
import time
import urllib.request

OLLAMA = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434")
OLLAMA = OLLAMA if OLLAMA.startswith("http") else "http://" + OLLAMA + ":11434"
WORK = os.path.expanduser(os.environ.get("CRUSHED_REMASTER_WORK", "~/crushed-render/remaster"))


def say(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


def call(path, body=None, timeout=1800):
    req = urllib.request.Request(OLLAMA + path, data=json.dumps(body).encode() if body is not None else None,
                                 headers={"content-type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def pull(name):
    req = urllib.request.Request(OLLAMA + "/api/pull", data=json.dumps({"model": name, "stream": True}).encode(),
                                 headers={"content-type": "application/json"})
    last = -10
    with urllib.request.urlopen(req, timeout=24 * 3600) as r:
        for line in r:
            try:
                m = json.loads(line)
            except Exception:
                continue
            if m.get("error"):
                raise RuntimeError(m["error"])
            if m.get("total") and m.get("completed"):
                pct = 100 * m["completed"] / m["total"]
                if pct - last >= 5:
                    last = pct
                    say(f"[brains] {name}: {pct:.0f}% of {m['total'] / 1e9:.0f} GB")
            elif m.get("status") and "pulling" not in m["status"]:
                say(f"[brains] {name}: {m['status']}")


def free_all():
    try:
        for m in call("/api/ps", timeout=10).get("models", []):
            call("/api/generate", {"model": m["name"], "prompt": "", "keep_alive": 0}, timeout=120)
    except Exception:
        pass


def test(name):
    from PIL import Image
    out = {"model": name, "at": time.time()}
    try:
        out["ollama"] = call("/api/version", timeout=10).get("version")
    except Exception:
        pass
    free_all()
    t0 = time.time()
    try:
        r = call("/api/chat", {"model": name, "stream": False, "think": False, "keep_alive": "5m",
                               "messages": [{"role": "user", "content": "Answer with exactly the word: ready"}]})
        out["loads"] = True
        out["load_and_answer_s"] = round(time.time() - t0)
        out["answer"] = r.get("message", {}).get("content", "")[:80]
        if r.get("eval_duration"):
            out["words_per_s"] = round(r["eval_count"] / (r["eval_duration"] / 1e9), 1)
    except Exception as e:
        out["loads"] = False
        out["error"] = str(getattr(e, "read", lambda: b"")() or e)[:500]
        return out
    try:                                                   # a tool call, the way the engineer works
        tools = [{"type": "function", "function": {"name": "mesh_info", "description": "Measure the 3D model.",
                                                   "parameters": {"type": "object", "properties": {}, "required": []}}}]
        r = call("/api/chat", {"model": name, "stream": False, "think": False, "tools": tools, "messages": [
            {"role": "user", "content": "Measure the 3D model. Use your tool."}]})
        out["tool_call"] = bool(r.get("message", {}).get("tool_calls"))
    except Exception as e:
        out["tool_call"] = f"failed: {e}"
    try:                                                   # can it see? a red square on white
        im = Image.new("RGB", (256, 256), "white")
        im.paste((220, 30, 30), (64, 64, 192, 192))
        b = io.BytesIO()
        im.save(b, "PNG")
        r = call("/api/chat", {"model": name, "stream": False, "think": False, "messages": [
            {"role": "user", "content": "What color is the square? One word.",
             "images": [base64.b64encode(b.getvalue()).decode()]}]})
        out["sees"] = "red" in r.get("message", {}).get("content", "").lower()
    except Exception as e:
        out["sees"] = f"failed: {e}"
    call("/api/generate", {"model": name, "prompt": "", "keep_alive": 0}, timeout=120)
    return out


if __name__ == "__main__":
    os.makedirs(os.path.join(WORK, "brains"), exist_ok=True)
    for name in sys.argv[1:]:
        res = {"model": name}
        try:
            say(f"[brains] {name}: downloading")
            pull(name)
            say(f"[brains] {name}: downloaded - waiting for the asset run to be idle to test it")
            lock = open(os.path.join(WORK, "run.lock"), "w")
            while True:
                try:
                    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    break
                except OSError:
                    time.sleep(60)
            try:
                res = test(name)
            finally:
                lock.close()
        except Exception as e:
            res["error"] = str(e)[:500]
        say(f"[brains] {name}: " + json.dumps(res))
        json.dump(res, open(os.path.join(WORK, "brains", re.sub(r"[^a-z0-9.]+", "_", name.lower()) + ".json"), "w"),
                  indent=1)
