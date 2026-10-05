"""No undefined name anywhere in the asset maker (2026-10-05, 1:15 AM: the Duracell's build failed its text check
with "name 'text_found' is not defined" - an edit the day before had deleted the function next to the one it
rewrote; a second one waited in the keep step. The suite ran green because neither line runs in a unit test. So
every module is now read whole by pyflakes, and one undefined name fails the suite - and the self-test."""
import os
import subprocess
import sys

LIB = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ok = 0


def check(cond, what):
    global ok
    print(("PASS " if cond else "FAIL ") + what)
    assert cond, what
    ok += 1


def undefined_names(lib=LIB):
    """Every 'undefined name' pyflakes finds in the library's own modules (tests left out). [] when clean; None
    when pyflakes is not installed here (then nothing is claimed)."""
    files = []
    for root, dirs, names in os.walk(lib):
        dirs[:] = [d for d in dirs if d not in ("tests", "__pycache__", ".venv", "node_modules") and not d.startswith(".")]
        files += [os.path.join(root, n) for n in names if n.endswith(".py")]
    try:
        r = subprocess.run([sys.executable, "-m", "pyflakes", *files], capture_output=True, text=True, timeout=300)
    except Exception:
        return None
    if "No module named pyflakes" in (r.stderr or ""):
        return None
    return [l for l in (r.stdout or "").splitlines() if "undefined name" in l or "undefined local" in l]


if __name__ == "__main__":
    bad = undefined_names()
    check(bad is not None, "pyflakes is here to read the modules")
    check(bad == [], "no undefined name in any module: " + ("; ".join(bad) if bad else "clean"))
    print(f"ALL {ok} PASS")
