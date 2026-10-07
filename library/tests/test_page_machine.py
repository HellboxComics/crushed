"""THE PAGE IS THE MACHINE (Cody, 2026-10-05): the page's Function takes every input into a KV box, the Mac fetches,
applies and acknowledges; the page shows controls and what the machine said. The Function is run here under node
with a fake KV; the Mac side with a fake fetch."""
import json
import os
import subprocess
import sys
import tempfile

W = tempfile.mkdtemp()
HOME = tempfile.mkdtemp()
os.environ["CRUSHED_REMASTER_WORK"] = W
os.environ["HOME"] = HOME
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

ok = 0


def check(cond, what):
    global ok
    print(("PASS " if cond else "FAIL ") + what)
    assert cond, what
    ok += 1


# 1. the Function, under node with a fake KV
fn = os.path.join(HERE, "site_root", "functions", "api", "[[route]].js")
harness = os.path.join(W, "h.mjs")
open(harness, "w").write(f"""
import {{ onRequest }} from {json.dumps("file://" + fn)};
const store = new Map();
const KV = {{ get: async k => store.has(k) ? store.get(k) : null, put: async (k, v) => store.set(k, v),
             delete: async k => store.delete(k), list: async ({{prefix}}) => ({{ keys: [...store.keys()].filter(k => k.startsWith(prefix)).map(name => ({{name}})) }}) }};
store.set("_token", "secret1");
const env = {{ INBOX: KV }};
const call = async (route, method, body, q = "") => {{
  const req = new Request("https://x.pages.dev/api/" + route + q, {{ method, body: body ? JSON.stringify(body) : undefined,
    headers: {{ "content-type": "application/json" }} }});
  const r = await onRequest({{ request: req, env, params: {{ route: route.split("/") }} }});
  return [r.status, await r.json()];
}};
const out = {{}};
out.ping0 = await call("ping", "GET");
out.badtok = await call("act", "POST", {{ token: "nope", action: "keep", item: "x" }});
out.badact = await call("act", "POST", {{ token: "secret1", action: "explode", item: "x" }});
out.keep = await call("act", "POST", {{ token: "secret1", action: "keep", item: "duracell" }});
out.add = await call("act", "POST", {{ token: "secret1", action: "add", text: "Energizer AA 1999" }});
out.inbox_bad = await call("inbox", "GET", null, "?token=nope");
out.inbox = await call("inbox", "GET", null, "?token=secret1");
out.ack = await call("ack", "POST", {{ token: "secret1", keys: out.inbox[1].messages.map(m => m.key) }});
out.inbox2 = await call("inbox", "GET", null, "?token=secret1");
out.ping1 = await call("ping", "GET");
out.nodoor = await call("nothing", "GET");
console.log(JSON.stringify(out));
""")
r = subprocess.run(["node", harness], capture_output=True, text=True, timeout=60)
assert r.returncode == 0, r.stderr[-800:]
o = json.loads(r.stdout.strip().splitlines()[-1])
check(o["ping0"][0] == 200 and o["ping0"][1]["bound"] is True and o["ping0"][1]["waiting"] == 0, "ping: bound, nothing waiting")
check(o["badtok"][0] == 403 and o["badact"][0] == 400, "a wrong token is refused (403); an unknown action too (400)")
check(o["keep"][1]["ok"] and o["add"][1]["ok"], "Keep and Add are taken")
check(o["inbox_bad"][0] == 403, "the Mac's fetch needs the token too")
msgs = o["inbox"][1]["messages"]
check(len(msgs) == 2 and msgs[0]["action"] == "keep" and msgs[0]["item"] == "duracell" and msgs[1]["text"] == "Energizer AA 1999",
      "the inbox lists both, oldest first, with what was sent")
check(o["ack"][1]["removed"] == 2 and o["inbox2"][1]["messages"] == [] and o["ping1"][1]["waiting"] == 0, "acknowledged messages are gone")
check(o["nodoor"][0] == 404, "no other door")

# 2. the Mac side: fetch -> apply -> ack, through the same doors the phone used
import inbox  # noqa: E402
import portal  # noqa: E402
os.makedirs(inbox.HB, exist_ok=True)
json.dump({"kv_id": "a" * 32, "token": "secret1", "project": "crushed-remaster"}, open(inbox.CONF, "w"))
json.dump({"duracell_aa": {"product": "Duracell", "step": "stopped: x", "at": 1000.0}}, open(os.path.join(W, "library", "status.json") if os.path.isdir(os.path.join(W, "library")) else (os.makedirs(os.path.join(W, "library")) or os.path.join(W, "library", "status.json")), "w"))
import base64  # noqa: E402
tiny = base64.b64encode(b"\x89PNG\r\n\x1a\n" + b"0" * 20).decode()
sent = {}
inbox.fetch = lambda timeout=30: [
    {"key": "in:1", "at": 1, "action": "keep", "item": "duracell_aa"},
    {"key": "in:2", "at": 2, "action": "redo", "item": "other_item"},
    {"key": "in:3", "at": 3, "action": "add", "text": "Energizer AA 1999", "photo": "data:image/png;base64," + tiny},
    {"key": "in:4", "at": 4, "action": "note", "item": "duracell_aa", "text": "the 1999 label"},
    {"key": "in:5", "at": 5, "action": "retry", "item": "duracell_aa"},
    {"key": "in:6", "at": 6, "action": "restart"},
    {"key": "in:7", "at": 7, "action": "job_off", "text": "hart"},
    {"key": "in:8", "at": 8, "action": "pick", "item": "duracell_aa", "text": "/x/p1.jpg"},
    {"key": "in:9", "at": 9, "action": "size", "item": "duracell_aa", "text": "14.5 x 14.5 x 50.5 mm"},
    {"key": "in:10", "at": 10, "action": "explode"},
]
inbox.ack = lambda keys, timeout=30: sent.setdefault("acked", list(keys))
done = inbox.poll(log=lambda *a: None)
ap = json.load(open(os.path.join(inbox.HB, "approvals.json")))
check(ap["duracell_aa"]["say"] == "keep" and ap["other_item"]["say"] == "redo", "Keep / Redo land in approvals.json like before")
pin = json.load(open(portal.INBOX))
check(len(pin) == 3 and pin[0]["text"] == "Energizer AA 1999" and pin[0]["photo"] and os.path.exists(pin[0]["photo"]),
      "Add (with its photo saved), Note and Size land in the portal's inbox for portal.process")
check(pin[1]["text"] == "duracell_aa: the 1999 label" and pin[2]["text"].startswith("duracell_aa: size 14.5"), "a note and a size are written the way the portal reads them")
st = json.load(open(os.path.join(W, "library", "status.json")))
import time  # noqa: E402
check(time.time() - 3700 < st["duracell_aa"]["at"] <= time.time() - 3600, "Retry now sets the item's clock to an hour ago so its retry is due now")
check(os.path.exists(os.path.join(W, "restart.request")), "Restart writes restart.request (taken at the next safe step)")
check("hart" in open(os.path.join(inbox.HB, "jobs-off.txt")).read().split(), "a job switched off lands in jobs-off.txt")
check(json.load(open(os.path.join(inbox.HB, "picks.json")))["duracell_aa"]["pick"] == "/x/p1.jpg", "a pick lands in picks.json")
check(sorted(sent["acked"]) == sorted(f"in:{i}" for i in range(1, 11)), "every message is acknowledged, the bad one too")
rs = json.load(open(os.path.join(W, "portal", "replies.json")))
check(any("Keep noted" in r["text"] for r in rs) and any("Could not use" in r["text"] for r in rs), "the machine says back what it did, on the page")
check(len(done) == 9, f"{len(done)} of 10 handled (the unknown one refused, said)")

# 3. the page carries the controls, the machine bar and what was said
import run  # noqa: E402
import remaster as RM  # noqa: E402
RM.publish = lambda force=True: None
run.say = lambda *a, **k: None
run.page(force=False)
html = open(os.path.join(W, "index.html")).read()
check('data-act=keep data-item="duracell_aa"' in html and 'data-act=retry' in html and 'data-act=note' in html, "each card has Keep / Retry now / Note")
check('id=addf' in html and 'data-act=restart' in html and 'data-text="hart"' in html and 'hart: off' in html, "the machine bar: add an item, restart, jobs with their state")
check("the machine said" in html and "Could not use" in html and "/api/act" in html and "crushed_page_token" in html, "what the machine said is shown; the page posts to its own Function with a saved token")
check("telegram" not in html.lower(), "no Telegram anywhere on the page")

# 4. the publish folder gets wrangler.toml with the KV box
root = os.path.join(W, "site_root"); os.makedirs(root, exist_ok=True)
check(inbox.write_wrangler_toml(root) and ("a" * 32) in open(os.path.join(root, "wrangler.toml")).read()
      and 'binding = "INBOX"' in open(os.path.join(root, "wrangler.toml")).read(), "wrangler.toml binds this Mac's KV box as INBOX")
import inbox as IB
src_ib = open(IB.__file__).read()
check(src_ib.count('"User-Agent": UA') >= 2, "the inbox poll and ack name their client (Cloudflare's 1010 bans Python's default signature)")
print(f"ALL {ok} PASS")
