"""Stands in for `run.py --trial` (and, with --judge, `run.py --judge`): writes a scripted verdict.
The script (FAKE_SCRIPT, JSON) says, per item, what each successive call returns."""
import json
import os
import shutil
import subprocess
import sys
import time

judge = sys.argv[1] == "--judge"
args = sys.argv[2:] if judge else sys.argv[1:]
cid, tdir = args[0], args[1]
S = os.environ["FAKE_SCRIPT"]
script = json.load(open(S))
kind = "judge" if judge else "trials"
cf = f"{S}.{kind}.{cid}.n"
n = int(open(cf).read()) if os.path.exists(cf) else 0
open(cf, "w").write(str(n + 1))
plan = script.get(kind, {}).get(cid, [])
step = plan[min(n, len(plan) - 1)] if plan else {"failed": []}
print(f"fake {kind} {cid} call {n}: {step}", flush=True)
if step.get("hang"):
    p = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(600)"])
    open(script["hang_pid_file"], "w").write(str(p.pid))
    time.sleep(600)
if step.get("tamper_wt"):
    open(os.path.join(os.environ["FAKE_WT"], "library", "vet.py"), "a").write("\n# changed by a test build\n")
if step.get("tamper_root"):
    open(os.path.join(os.environ["FAKE_ROOT"], "library", "vet.py"), "a").write("\n# changed by a test build\n")
if step.get("tamper_card"):
    p = os.path.join(os.environ["CRUSHED_REMASTER_WORK"], "cards", cid + ".json")
    card = json.load(open(p))
    card["construction"] = {"layers": [], "closeups": []}
    json.dump(card, open(p, "w"))
if step.get("crash"):
    sys.exit(3)
failed = step.get("failed", [])
v = {"pass": not failed, "failed": failed, "problems": [f"{f} looks off" for f in failed]}
if judge:
    json.dump({"verdict": v}, open(os.path.join(tdir, "judged.json"), "w"))
else:
    os.makedirs(os.path.join(tdir, "check"), exist_ok=True)
    src = script["shots_dir"]
    for f in ("viewer_around.jpg", "viewer_close.jpg"):
        shutil.copy(os.path.join(src, f), os.path.join(tdir, "check", f))
    json.dump({"verdict": v, "shots": os.path.join(tdir, "check", "viewer_around.jpg"),
               "close": os.path.join(tdir, "check", "viewer_close.jpg")}, open(os.path.join(tdir, "trial.json"), "w"))
