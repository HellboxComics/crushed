"""WATCHDOG: the clock runs this every 5 minutes. It only acts on things it can prove:

  1. the drawing room (ComfyUI) doesn't answer its own health check two checks in a row while a run is going
     -> restart the drawing room, tell your phone
  2. the run's heartbeat (written every time it does anything, and every minute while it waits on a long job)
     hasn't moved in 45 minutes -> restart the run, tell your phone

It never judges "stuck" from the status page (that can be old); only from the heartbeat and a live check.
"""
import json
import os
import subprocess
import time
import urllib.request

WORK = os.path.expanduser(os.environ.get("CRUSHED_REMASTER_WORK", "~/crushed-render/remaster"))
BEAT = os.path.join(WORK, "heartbeat.json")
STATE = os.path.join(WORK, "watchdog.json")
REPO = os.path.expanduser("~/crushed-render/repo")
ROOM = os.environ.get("DRAWING_ROOM", "http://127.0.0.1:8188")


def running():
    return subprocess.run(["pgrep", "-f", "bin/python library/run.py"], capture_output=True).returncode == 0


def tell(text):
    import sys
    sys.path.insert(0, os.path.expanduser("~/.hellbox/ai/hart"))
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


def main():
    try:
        w = json.load(open(STATE))
    except Exception:
        w = {}
    if not running():
        json.dump({}, open(STATE, "w"))
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
        subprocess.run(["pkill", "-f", "bin/python library/run.py"])
        time.sleep(3)
        subprocess.Popen([os.path.join(REPO, ".venv", "bin", "python"), "library/run.py", "--loop", "--queue", "3"],
                         cwd=REPO, stdout=open(os.path.expanduser("~/crushed-render/library.log"), "a"),
                         stderr=subprocess.STDOUT, start_new_session=True)
        tell(f"Asset maker: no sign of life for {idle / 60:.0f} min while '{beat.get('doing')}'. I restarted it. "
             "If this repeats, send it to Claude.")
        print(f"[watchdog] heartbeat {idle / 60:.0f} min old ({beat.get('doing')}): restarted the run")
    json.dump(w, open(STATE, "w"))


if __name__ == "__main__":
    main()
