"""HOW FAST YOUR AI CAN THINK, MEASURED ON THIS MAC - and set up so it thinks as fast as this Mac allows.

Your AI spends most of each item asking the brain (Ollama) one question at a time: a careful look at a photo takes
about 3 minutes of thinking. Ollama answers ONE question at a time unless it is told otherwise (its own setting,
OLLAMA_NUM_PARALLEL, default 1 - docs.ollama.com/faq). Answering 2 at once makes nearly twice the words a minute on
a Mac with plenty of memory, because each step of the brain's work is shared by both answers. So:

  1. the brain server is set to answer 2 questions at once (macOS: `launchctl setenv OLLAMA_NUM_PARALLEL 2`, then
     Ollama restarted so it takes the setting - the way Ollama's own FAQ says to). The setting is lost when the Mac
     restarts, so this check runs every time the asset maker starts and puts it back.
  2. the speed is MEASURED: the same short answer asked 1 at a time and 2 at a time, words per second compared.
     Your AI then asks that many at once (vet.workers()) - only if it really is faster on this Mac.

Memory: Ollama keeps room for each answer at once (2 x 32,768 words of room); the 27B brain plus that fits easily
in 128 GB. The results are in ~/crushed-render/remaster/speed.json and the log.
"""
import json
import os
import shutil
import subprocess
import sys
import threading
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
WORK = os.path.expanduser(os.environ.get("CRUSHED_REMASTER_WORK", "~/crushed-render/remaster"))
OUT = os.path.join(WORK, "speed.json")
WANT = 2                      # answers at once (memory stays comfortable with the label drawer and Hunyuan too)
VERSION = 1


def _sh(cmd, timeout=60):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except Exception as e:
        return subprocess.CompletedProcess(cmd, 1, "", str(e))


def _up():
    import vet as V
    try:
        urllib.request.urlopen(V.OLLAMA + "/api/tags", timeout=5).read()
        return True
    except Exception:
        return False


def _wait(up, seconds):
    t = time.time()
    while time.time() - t < seconds:
        if _up() == up:
            return True
        time.sleep(1)
    return False


def restart_ollama(log=print):
    """Restart the brain server the way it was started, so it reads the new setting. -> what was done"""
    ps = _sh(["pgrep", "-fl", "ollama"]).stdout
    labels = [ln.split()[-1] for ln in _sh(["launchctl", "list"]).stdout.splitlines() if "ollama" in ln.lower()]
    if "Ollama.app" in ps or (not ps.strip() and os.path.exists("/Applications/Ollama.app")):
        _sh(["osascript", "-e", 'quit app "Ollama"'])     # the Ollama app (what its FAQ describes)
        if not _wait(False, 20):
            _sh(["pkill", "-f", "Ollama.app"])
            _wait(False, 10)
        _sh(["open", "-a", "Ollama"])
        how = "the Ollama app was quit and opened again"
    elif labels:                                          # a background service (Homebrew or the suite's own)
        _sh(["launchctl", "kickstart", "-k", f"gui/{os.getuid()}/{labels[0]}"])
        how = f"its background service ({labels[0]}) was restarted"
    else:                                                 # started by hand: started again the same way
        _sh(["pkill", "-f", "ollama serve"])
        _wait(False, 10)
        exe = shutil.which("ollama") or "/opt/homebrew/bin/ollama"
        env = dict(os.environ, OLLAMA_NUM_PARALLEL=str(WANT))
        subprocess.Popen([exe, "serve"], env=env, stdout=open(os.path.join(WORK, "ollama_serve.log"), "a"),
                         stderr=subprocess.STDOUT, start_new_session=True)
        how = "it was started again with the setting"
    ok = _wait(True, 120)
    log(f"[speed] brain server restarted to take the setting: {how}" + ("" if ok else " - BUT it did not come back up"))
    return ok


def _rate(model, k):
    """Words (tokens) per second when k questions are asked at the same time."""
    import vet as V
    body = {"model": model, "stream": False, "think": False,
            "options": {"temperature": 0, "num_predict": 256, "seed": 1},
            "messages": [{"role": "user", "content": "Count from 1 to 400 in words, separated by commas. Nothing else."}]}
    got = [0] * k
    errs = []

    def one(i):
        try:
            got[i] = int(V._call("/api/chat", body, timeout=600).get("eval_count") or 0)
        except Exception as e:
            errs.append(str(e))
    t = time.time()
    th = [threading.Thread(target=one, args=(i,)) for i in range(k)]
    for x in th:
        x.start()
    for x in th:
        x.join()
    wall = time.time() - t
    if errs:
        raise RuntimeError(errs[0])
    return sum(got) / max(wall, 0.01)


def setup(log=print, force=False):
    """Make sure the brain server answers WANT at once, measure it, write how many at once to use. -> workers"""
    import vet as V
    model = V.model()
    if not model:
        return 1
    cur = _sh(["launchctl", "getenv", "OLLAMA_NUM_PARALLEL"]).stdout.strip()
    try:
        old = json.load(open(OUT))
    except Exception:
        old = {}
    fresh = old.get("version") == VERSION and old.get("model") == model and old.get("setting") == cur == str(WANT) \
        and time.time() - float(old.get("at") or 0) < 7 * 86400
    if fresh and not force:
        return int(old.get("workers") or 1)
    if cur != str(WANT):
        _sh(["launchctl", "setenv", "OLLAMA_NUM_PARALLEL", str(WANT)])
        log(f"[speed] the brain server was set to answer {cur or 1} question(s) at a time - now {WANT} "
            "(launchctl setenv OLLAMA_NUM_PARALLEL, Ollama's own way on a Mac)")
        if not restart_ollama(log):
            json.dump({"version": VERSION, "workers": 1, "model": model, "setting": cur, "at": time.time(),
                       "note": "the brain server did not come back after the restart"}, open(OUT, "w"), indent=1)
            return 1
    try:
        _rate(model, 1)                                 # loads the brain (not counted)
        rates = {1: _rate(model, 1)}
        rates[2] = _rate(model, 2)
    except Exception as e:
        log(f"[speed] could not measure ({e}) - asking one at a time")
        rates = {1: 0}
    best = 2 if rates.get(2, 0) >= 1.25 * rates.get(1, 1e9) else 1
    json.dump({"version": VERSION, "workers": best, "model": model, "setting": str(WANT), "at": time.time(),
               "words_per_second": {str(k): round(v, 1) for k, v in rates.items()}}, open(OUT, "w"), indent=1)
    log(f"[speed] measured: 1 at a time {rates.get(1, 0):.1f} words/s, 2 at a time {rates.get(2, 0):.1f} words/s "
        f"in total - your AI asks {best} at a time" + ("" if best > 1 else " (2 at once was not faster here)"))
    return best


if __name__ == "__main__":
    print(setup(force="--force" in sys.argv))
