"""WATCHDOG: the clock runs this every 5 minutes. If the asset maker is running but hasn't moved in 10 minutes
(and isn't waiting on you), it restarts the drawing room once; if it still hasn't moved 10 minutes later, it
stops the run, restarts it, and tells your phone what was stuck. A run never sits frozen without anyone knowing.
"""
import json
import os
import subprocess
import time

WORK = os.path.expanduser(os.environ.get("CRUSHED_REMASTER_WORK", "~/crushed-render/remaster"))
STATUS = os.path.join(WORK, "library", "status.json")
STATE = os.path.join(WORK, "watchdog.json")
REPO = os.path.expanduser("~/crushed-render/repo")


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


def main():
    if not running():
        return
    try:
        st = json.load(open(STATUS))
    except Exception:
        return
    busy = {k: v for k, v in st.items() if not str(v.get("step", "")).startswith(("waiting", "done", "stopped", "3 rounds"))}
    if not busy:
        return
    cid, v = max(busy.items(), key=lambda kv: kv[1].get("at", 0))
    idle = time.time() - v.get("at", 0)
    try:
        w = json.load(open(STATE))
    except Exception:
        w = {}
    if idle < 600:
        if w:
            json.dump({}, open(STATE, "w"))
        return
    if w.get("cid") != cid or w.get("at") != v.get("at"):        # first time stuck on this step
        subprocess.run(["launchctl", "kickstart", "-k", f"gui/{os.getuid()}/com.hellbox.ai.draw"])
        json.dump({"cid": cid, "at": v.get("at"), "kicked": time.time()}, open(STATE, "w"))
        print(f"[watchdog] {cid} stuck {idle / 60:.0f} min on '{v.get('step')}': restarted the drawing room")
        return
    if time.time() - w.get("kicked", 0) >= 600:                  # still stuck: restart the run itself
        subprocess.run(["pkill", "-f", "bin/python library/run.py"])
        time.sleep(3)
        subprocess.Popen(["nohup", os.path.join(REPO, ".venv", "bin", "python"), "library/run.py", "--loop", "--queue", "3"],
                         cwd=REPO, stdout=open(os.path.expanduser("~/crushed-render/library.log"), "a"),
                         stderr=subprocess.STDOUT, start_new_session=True)
        json.dump({}, open(STATE, "w"))
        tell(f"Asset maker was stuck on {cid} ({v.get('step')}) for {idle / 60:.0f} min. "
             "I restarted the drawing room, then the run. If this repeats, send it to Claude.")
        print(f"[watchdog] {cid}: restarted the run")


if __name__ == "__main__":
    main()
