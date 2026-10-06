"""THE PAGE IS THE MACHINE (Cody, 2026-10-05 09:09): every input comes from https://<project>.pages.dev - add an
item (words and/or a photo), a note on an item, Keep / Redo / Retry now, Restart, a job on or off, a photo pick,
a size - and lands in a Cloudflare KV box through the page's own Function (library/site_root/functions). This
module is the Mac's side: set the box up once, then every minute fetch what is waiting, apply it through the same
doors the phone path used (portal's inbox, approvals.json, restart.request, jobs-off.txt, picks.json), and tell
the page what happened (WORK/portal/replies.json, shown on the page). No Telegram anywhere in the workflow.

Setup (once, by the run itself; wrangler is already logged in for the publish):
    npx wrangler kv namespace create crushed_inbox      -> the KV id  (developers.cloudflare.com/kv/)
    npx wrangler kv key put _token <token> --namespace-id <id>
    ~/.hellbox/page-inbox.json = {"kv_id", "token", "project"};  the token also in ~/.hellbox/page-token.txt
Cody unlocks the page once with that token (it stays in his browser)."""
import base64
import json
import os
import re
import secrets
import subprocess
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
WORK = os.environ.get("CRUSHED_REMASTER_WORK") or os.path.expanduser("~/crushed-render/remaster")
HB = os.path.expanduser("~/.hellbox")
CONF = os.path.join(HB, "page-inbox.json")
TOKEN_FILE = os.path.join(HB, "page-token.txt")
PROJECT = "crushed-remaster"
ACTIONS = ("add", "note", "keep", "redo", "retry", "restart", "job_on", "job_off", "pick", "size")


def _load(p, d):
    try:
        return json.load(open(p))
    except Exception:
        return d


def _save(p, v):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    tmp = p + ".tmp"
    json.dump(v, open(tmp, "w"), indent=1)
    os.replace(tmp, p)


def conf():
    c = _load(CONF, {})
    return c if c.get("kv_id") and c.get("token") else None


def url(path):
    c = conf() or {}
    return f"https://{c.get('project', PROJECT)}.pages.dev{path}"


def _npx():
    for p in ("/opt/homebrew/bin/npx", "/usr/local/bin/npx", "npx"):
        if p == "npx" or os.path.exists(p):
            return p
    return None


def setup(log=print):
    """Make the KV box and the token once. -> the config, or None with the reason logged."""
    if conf():
        return conf()
    npx = _npx()
    if not npx:
        log("[page] inbox setup skipped: Node (npx) is not installed")
        return None
    r = subprocess.run([npx, "--yes", "wrangler@3", "kv", "namespace", "create", "crushed_inbox"],
                       capture_output=True, text=True, timeout=300)
    m = re.search(r'id\s*=\s*"([0-9a-f]{32})"', r.stdout + r.stderr)
    if not m:
        log("[page] inbox setup: could not make the KV box: " + (r.stderr or r.stdout)[-300:])
        return None
    kv_id = m.group(1)
    token = secrets.token_urlsafe(18)
    r2 = subprocess.run([npx, "--yes", "wrangler@3", "kv", "key", "put", "_token", token, "--namespace-id", kv_id],
                        capture_output=True, text=True, timeout=300)
    if r2.returncode != 0:
        log("[page] inbox setup: could not store the token: " + (r2.stderr or r2.stdout)[-300:])
        return None
    c = {"kv_id": kv_id, "token": token, "project": PROJECT, "made": time.time()}
    _save(CONF, c)
    open(TOKEN_FILE, "w").write(token + "\n")
    log(f"[page] the page's inbox is set up (KV {kv_id[:8]}...). Unlock the page once with the token in {TOKEN_FILE}")
    return c


def write_wrangler_toml(root):
    """The publish folder's wrangler.toml (binding the KV box) from the template; without a box, no file."""
    c = conf()
    p = os.path.join(root, "wrangler.toml")
    if not c:
        if os.path.exists(p):
            os.remove(p)
        return False
    t = open(os.path.join(HERE, "site_root", "wrangler.toml.template")).read()
    open(p, "w").write(t.replace("{project}", c.get("project", PROJECT)).replace("{kv_id}", c["kv_id"]))
    return True


def fetch(timeout=30):
    """What is waiting in the box. -> list of messages (each with its key)."""
    c = conf()
    if not c:
        return []
    with urllib.request.urlopen(url("/api/inbox?token=" + c["token"]), timeout=timeout) as r:
        return (json.load(r) or {}).get("messages") or []


def ack(keys, timeout=30):
    c = conf()
    if not c or not keys:
        return
    body = json.dumps({"token": c["token"], "keys": list(keys)}).encode()
    req = urllib.request.Request(url("/api/ack"), data=body, headers={"content-type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        r.read()


def reply(text, item=None):
    """What the machine says back, shown on the page (the last 30)."""
    p = os.path.join(WORK, "portal", "replies.json")
    rs = _load(p, [])
    rs.append({"at": time.time(), "item": item, "text": str(text)[:400]})
    _save(p, rs[-30:])


def _save_photo(data_url, name):
    m = re.match(r"^data:image/(png|jpe?g|webp);base64,(.+)$", str(data_url), re.S)
    if not m:
        return None
    ext = {"jpeg": "jpg", "jpg": "jpg", "png": "png", "webp": "webp"}[m.group(1)]
    p = os.path.join(WORK, "portal", "photos", f"{name}.{ext}")
    os.makedirs(os.path.dirname(p), exist_ok=True)
    open(p, "wb").write(base64.b64decode(m.group(2)))
    return p


def apply(messages, log=print):
    """Each message through its door. -> [(action, item)] handled. Never raises for one bad message."""
    import portal
    out = []
    for m in messages:
        act, item, text = m.get("action"), (m.get("item") or "").strip() or None, (m.get("text") or "").strip()
        try:
            if act in ("add", "note", "size"):
                # the same inbox portal.process reads: it understands the words, finds the size, puts it first
                photo = _save_photo(m.get("photo"), f"page_{int(m.get('at') or time.time())}") if m.get("photo") else None
                if act == "note" and item:
                    text = f"{item}: {text}"
                if act == "size" and item:
                    text = f"{item}: size {text}"
                inbox = portal._load(portal.INBOX, [])
                inbox.append({"id": m.get("key"), "text": text, "photo": photo, "from": "page", "at": m.get("at")})
                portal._save(portal.INBOX, inbox)
            elif act in ("keep", "redo") and item:
                ap = _load(os.path.join(HB, "approvals.json"), {})
                ap[item] = {"say": act, "at": time.time(), "from": "page"}
                _save(os.path.join(HB, "approvals.json"), ap)
                reply(f"{act.title()} noted for {item.replace('_', ' ')} - it is taken up at the next step.", item)
            elif act == "retry" and item:
                p = os.path.join(WORK, "library", "status.json")
                st = _load(p, {})
                if item in st:
                    st[item]["at"] = time.time() - 3600 - 60      # its retry is due now (the "kick")
                    _save(p, st)
                reply(f"{item.replace('_', ' ')}: retrying now.", item)
            elif act == "restart":
                open(os.path.join(WORK, "restart.request"), "w").write(f"page {time.time()}\n")
                reply("Restarting at the next safe step - the newest version is taken.")
            elif act in ("job_on", "job_off") and text:
                name = re.sub(r"[^a-z0-9_.-]", "", text.lower())
                p = os.path.join(HB, "jobs-off.txt")
                off = set(open(p).read().split()) if os.path.exists(p) else set()
                (off.discard if act == "job_on" else off.add)(name)
                open(p, "w").write("\n".join(sorted(off)) + ("\n" if off else ""))
                reply(f"{name}: {'on' if act == 'job_on' else 'off'}.")
            elif act == "pick" and item and text:
                picks = _load(os.path.join(HB, "picks.json"), {})
                picks[item] = {"pick": text, "at": time.time(), "from": "page"}
                _save(os.path.join(HB, "picks.json"), picks)
                reply(f"{item.replace('_', ' ')}: that photo is the pick.", item)
            else:
                reply(f"Could not use that ({act} {item or ''}).", item)
                log(f"[page] message not understood: {m}")
                continue
            out.append((act, item))
            log(f"[page] from the page: {act} {item or ''} {text[:60]}")
        except Exception as e:
            log(f"[page] message {m.get('key')} could not be handled: {e}")
            reply(f"That could not be handled ({str(e)[:80]}).", item)
    return out


def poll(log=print):
    """Once a minute from the run: fetch, apply, acknowledge. Quiet when nothing is set up or nothing waits."""
    if not conf():
        return []
    try:
        msgs = fetch()
    except Exception as e:
        log(f"[page] the inbox could not be reached: {str(e)[:120]}")
        return []
    if not msgs:
        return []
    done = apply(msgs, log=log)
    try:
        ack([m.get("key") for m in msgs if m.get("key")])
    except Exception as e:
        log(f"[page] could not acknowledge the inbox: {str(e)[:120]}")
    return done
