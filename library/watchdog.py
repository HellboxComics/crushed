"""WATCHDOG: the clock runs this every 5 minutes. It only acts on things it can prove:

  1. the drawing room (ComfyUI) doesn't answer its own health check two checks in a row while a run is going
     -> restart the drawing room, tell your phone
  2. the run's heartbeat (written every time it does anything, and every minute while it waits on a long job)
     hasn't moved in 45 minutes -> restart the run, tell your phone
  3. a newer version is waiting and the run is idle -> stop the run so the clock starts the newer version
     (not when that version was already found impossible to add - the run says that once on your page)

Whenever it stops the run, it also stops the heavy jobs the run started (Blender builders, the viewer's browser,
Hunyuan, your AI's test builds), so nothing is left running in the background eating memory. They are found by
being started by the run, or - if the run is already gone - by their exact script path in the asset maker's folder.
It never stops anything else: never Ollama, never the Telegram bot, never the drawing room's own process.

It never judges "stuck" from the status page (that can be old); only from the heartbeat and a live check.
"""
import json
import os
import signal
import subprocess
import time
import urllib.request

WORK = os.path.expanduser(os.environ.get("CRUSHED_REMASTER_WORK", "~/crushed-render/remaster"))
BEAT = os.path.join(WORK, "heartbeat.json")
STATE = os.path.join(WORK, "watchdog.json")
SYNC_STATE = os.path.join(WORK, "sync_state.json")
REPO = os.path.expanduser("~/crushed-render/repo")
ENG = os.path.join(WORK, "engineer")
WT = os.path.join(ENG, "wt")
ROOM = os.environ.get("DRAWING_ROOM", "http://127.0.0.1:8188")
RUN_MARK = "bin/python library/run.py"                 # how the clock and the watchdog start the run
NEVER = ("ollama", "/.hellbox/ai/", "comfyui", "telegram")   # never stopped, whoever started them
HEAVY = ("exports.py", "webglb.py", "cutaway.py", "preview.py", "viewshot.py", "hunyuan.py")


def running():
    return subprocess.run(["pgrep", "-f", RUN_MARK], capture_output=True).returncode == 0


def procs():
    """Every process on this Mac: (process id, parent's id, command line)."""
    r = subprocess.run(["ps", "-A", "-o", "pid=", "-o", "ppid=", "-o", "command="], capture_output=True, text=True,
                       timeout=30)
    out = []
    for line in r.stdout.splitlines():
        parts = line.strip().split(None, 2)
        if len(parts) >= 2 and parts[0].isdigit() and parts[1].isdigit():
            out.append((int(parts[0]), int(parts[1]), parts[2] if len(parts) > 2 else ""))
    return out


def never(cmd):
    low = cmd.lower()
    return any(n in low for n in NEVER)


def child_kind(cmd):
    """What a heavy job of the run is, by its exact script path (None when it is not one of them)."""
    if never(cmd):
        return None
    libs = {p + "/library/" for p in (REPO, WT, os.path.realpath(REPO), os.path.realpath(WT))}
    for lib in libs:
        if lib + "shapes/" in cmd:
            return "Blender builder"
        for s in HEAVY:
            if lib + s in cmd:
                return s
        if lib + "run.py" in cmd and ("--trial" in cmd or "--judge" in cmd):
            return "your AI's test build"
    if os.path.join(ENG, "probe.py") in cmd or os.path.join(os.path.realpath(ENG), "probe.py") in cmd:
        return "your AI's measuring"
    if any(p + "/.venv/" in cmd for p in (REPO, os.path.realpath(REPO))) and "playwright" in cmd.lower():
        return "the viewer's browser"
    return None


def plan_stop(table, me=None):
    """Which processes to stop when the run is restarted: the run, everything it started (its whole family tree,
    test builds and their Blender included), and heavy jobs left over from a run that is already gone (their parent
    is gone, so the system adopted them; matched by exact script path). {process id: what it is}."""
    me = me or os.getpid()
    kids, cmds = {}, {}
    for pid, ppid, cmd in table:
        kids.setdefault(ppid, []).append(pid)
        cmds[pid] = cmd
    roots = [pid for pid, _, cmd in table if RUN_MARK in cmd and pid != me]
    out, todo = {}, list(roots)
    while todo:
        p = todo.pop()
        if p in out or p == me or never(cmds.get(p, "")):
            continue
        out[p] = "the run" if p in roots else (child_kind(cmds.get(p, "")) or "started by the run")
        todo += kids.get(p, [])
    for pid, ppid, cmd in table:
        if pid in out or pid == me or ppid != 1:
            continue
        k = child_kind(cmd)
        if k:
            out[pid] = k + " (left over)"
    return out


def _alive(pid):
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    try:                                              # a finished process nobody collected yet is not running
        with open(f"/proc/{pid}/stat") as f:
            return f.read().rsplit(")", 1)[1].split()[0] != "Z"
    except OSError:
        pass
    r = subprocess.run(["ps", "-o", "stat=", "-p", str(pid)], capture_output=True, text=True)
    return bool(r.stdout.strip()) and not r.stdout.strip().startswith("Z")


def stop_run(why):
    """Stop the run and every heavy job it started: asked politely first, then made to."""
    plan = plan_stop(procs())
    if not plan:
        return {}
    for pid in plan:
        try:
            os.kill(pid, signal.SIGTERM)
        except (ProcessLookupError, PermissionError):
            pass
    t = time.time()
    while time.time() - t < 8 and any(_alive(p) for p in plan):
        time.sleep(0.3)
    for pid in plan:
        if _alive(pid):
            try:
                os.kill(pid, signal.SIGKILL)
            except (ProcessLookupError, PermissionError):
                pass
    print(f"[watchdog] {why}: stopped {len(plan)} process(es) - " + ", ".join(sorted(set(plan.values()))), flush=True)
    return plan


def tell(text):
    import sys
    p = os.path.expanduser("~/.hellbox/ai/hart")         # (at the END: its dossier.py must never shadow ours)
    if p not in sys.path:
        sys.path.append(p)
    try:
        import hart as H
        H.send(text)
    except (Exception, SystemExit):
        pass


def room_ok():
    try:
        urllib.request.urlopen(ROOM + "/system_stats", timeout=15).read()
        return True
    except Exception:
        return False


def _save(w):
    try:
        tmp = STATE + ".tmp"
        json.dump(w, open(tmp, "w"))
        os.replace(tmp, STATE)
    except Exception:
        pass


def main():
    try:
        w = json.load(open(STATE))
    except Exception:
        w = {}
    if not running():
        _save({})
        return
    req = os.path.join(WORK, "restart.request")                    # Claude asked for the newest version now
    if os.path.exists(req):
        os.replace(req, req + ".done")
        stop_run("restart asked for (the clock starts the newest version)")
        return
    # 1. the drawing room
    if room_ok():
        w["room_fails"] = 0
    else:
        w["room_fails"] = w.get("room_fails", 0) + 1
        if w["room_fails"] >= 2:
            subprocess.run(["launchctl", "kickstart", "-k", f"gui/{os.getuid()}/com.hellbox.ai.draw"])
            tell("Asset maker: the drawing room stopped answering, so I restarted it.")
            print("[watchdog] drawing room not answering twice: restarted it")
            w["room_fails"] = 0
    # 2. the run's heartbeat
    try:
        beat = json.load(open(BEAT))
    except Exception:
        beat = {"at": time.time(), "doing": "starting"}
    idle = time.time() - beat.get("at", 0)
    if idle > 45 * 60:
        stop_run(f"no heartbeat for {idle / 60:.0f} min")
        time.sleep(3)
        subprocess.Popen([os.path.join(REPO, ".venv", "bin", "python"), "library/run.py", "--loop", "--queue", "3"],
                         cwd=REPO, stdout=open(os.path.expanduser("~/crushed-render/library.log"), "a"),
                         stderr=subprocess.STDOUT, start_new_session=True)
        tell(f"Asset maker: no sign of life for {idle / 60:.0f} min while '{beat.get('doing')}'. I restarted it. "
             "If this repeats, send it to Claude.")
        print(f"[watchdog] heartbeat {idle / 60:.0f} min old ({beat.get('doing')}): restarted the run")
        _save(w)
        return
    # 3. a newer version is waiting and the run is idle (everything waiting on you, done or parked): restart it so
    #    the clock loads the new version (it never changes code under a running job) - unless that version was
    #    already found impossible to add (the run said so once; stopping it again would only repeat that)
    try:
        st = json.load(open(os.path.join(WORK, "library", "status.json")))
        busy = [v for v in st.values() if isinstance(v, dict) and not str(v.get("step", "")).startswith(
            ("waiting", "done", "stopped", "3 rounds", "in line", "no usable", "failed"))]
        newest = max((v.get("at", 0) for v in st.values() if isinstance(v, dict)), default=0)
        if not busy and time.time() - newest > 600:
            subprocess.run(["git", "fetch", "-q"], cwd=REPO, timeout=60)
            ahead = subprocess.run(["git", "rev-list", "--count", "HEAD..@{u}"], cwd=REPO, capture_output=True,
                                   text=True).stdout.strip()
            up = subprocess.run(["git", "rev-parse", "@{u}"], cwd=REPO, capture_output=True, text=True).stdout.strip()
            try:
                stuck = json.load(open(SYNC_STATE)).get("stuck_at")
            except Exception:
                stuck = None
            if ahead and ahead != "0" and up != stuck:
                stop_run(f"idle and {ahead} newer version(s) waiting (the clock loads them)")
    except Exception as e:
        print(f"[watchdog] version check skipped: {e}")
    _save(w)


if __name__ == "__main__":
    main()
