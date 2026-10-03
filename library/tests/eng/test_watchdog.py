"""Watchdog: when it restarts the run, the run's heavy children go too - and nothing else."""
import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C  # noqa: E402

T, HOME, _, WORK = C.make("watchdog", with_data=False)
os.environ.update(HOME=HOME, CRUSHED_REMASTER_WORK=WORK)
sys.path.insert(0, os.path.join(C.SRC, "library"))
import watchdog as W  # noqa: E402

check = C.Check()
R, WT = W.REPO, W.WT
print("\n1. which processes it would stop (a made-up process list)")
table = [
    (100, 50, ".venv/bin/python library/run.py --loop --queue 3"),
    (101, 100, f"{R}/.venv/bin/python {R}/library/shapes/lathe.py -- spec.json out"),
    (102, 100, f"{R}/.venv/bin/python {WT}/library/run.py --trial duracell /x/trial"),
    (103, 102, f"{R}/.venv/bin/python {WT}/library/shapes/lathe.py -- spec.json out"),
    (104, 100, "/Applications/Ollama.app/Contents/Resources/ollama runner --model x"),
    (105, 100, f"{R}/.venv/lib/python3.12/site-packages/playwright/driver/node cli.js run-driver"),
    (106, 105, "/Users/x/Library/Caches/ms-playwright/chromium-1/chrome --headless"),
    (200, 1, f"/Users/x/.hellbox/hunyuan3d-mlx/.venv/bin/python {R}/library/hunyuan.py ref.png out"),
    (201, 1, "/usr/bin/python3 /Users/x/other_app.py"),
    (202, 1, "/Users/x/.hellbox/ai/hart/.venv/bin/python /Users/x/.hellbox/ai/hart/bot.py"),
    (203, 1, f"{R}/.venv/bin/python {R}/library/lab.py duracell"),
    (204, 60, f"{R}/.venv/bin/python {R}/library/shapes/box.py -- 1 1 1 out"),
    (205, 1, f"{R}/.venv/bin/python {R}/library/exports.py -- a.blend out cid"),
    (206, 1, "/opt/homebrew/bin/ollama serve"),
    (207, 1, f"/Applications/ComfyUI/python main.py --listen {R}/library/shapes/x"),
]
plan = W.plan_stop(table, me=999)
check(set(plan) == {100, 101, 102, 103, 105, 106, 200, 205}, f"stops: {sorted(plan)}")
check(104 not in plan and 206 not in plan, "never Ollama (even when the run started it)")
check(202 not in plan and 201 not in plan, "never the Telegram bot or other apps")
check(203 not in plan and 204 not in plan, "not a Blender job someone else (lab.py) started, not lab.py itself")
check(207 not in plan, "never the drawing room")

print("\n2. a live run with children, a test build in its own process group and its grandchild")
os.makedirs(os.path.join(R, ".venv", "bin"))
os.makedirs(os.path.join(R, "library", "shapes"))
os.makedirs(os.path.join(WT, "library", "shapes"))
os.symlink(sys.executable, os.path.join(R, ".venv", "bin", "python"))
sleeper = "import time\ntime.sleep(300)\n"
for p in (os.path.join(R, "library", "shapes", "lathe.py"), os.path.join(WT, "library", "shapes", "lathe.py")):
    open(p, "w").write(sleeper)
open(os.path.join(WT, "library", "run.py"), "w").write(
    "import subprocess, sys, time\n"
    f"subprocess.Popen([sys.executable, {os.path.join(WT, 'library', 'shapes', 'lathe.py')!r}, '--'])\n"
    "time.sleep(300)\n")
pids = os.path.join(T, "pids.txt")
open(os.path.join(R, "library", "run.py"), "w").write(
    "import subprocess, sys, time\n"
    f"a = subprocess.Popen([sys.executable, {os.path.join(R, 'library', 'shapes', 'lathe.py')!r}, '--'])\n"
    f"b = subprocess.Popen([sys.executable, {os.path.join(WT, 'library', 'run.py')!r}, '--trial', 'x', '/tmp/x'],"
    " start_new_session=True)\n"
    f"open({pids!r}, 'w').write(f'{{a.pid}} {{b.pid}}')\n"
    "time.sleep(300)\n")
other = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(300)"])
run = subprocess.Popen([".venv/bin/python", "library/run.py", "--loop"], cwd=R, start_new_session=True)
for _ in range(50):
    if os.path.exists(pids):
        break
    time.sleep(0.1)
time.sleep(1.0)
a, b = map(int, open(pids).read().split())
grand = [pid for pid, ppid, _ in W.procs() if ppid == b]
check(W.running(), "the run is seen as running")
stopped = W.stop_run("test")
time.sleep(0.5)
run.poll()
check(not C.alive(run.pid) and not C.alive(a) and not C.alive(b) and grand and not any(C.alive(g) for g in grand),
      f"the run, its Blender job, its test build and the test build's Blender are all gone ({sorted(stopped)})")
check(C.alive(other.pid), "an unrelated program is still running")
other.kill()
check.done()
