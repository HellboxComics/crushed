"""The asset maker's own files always win: with your suite's same-named files (facts.py in ~/.hellbox/ai, dossier.py
in its phone bot's folder) and its tools that put their folder at the front of the search list (testlock.py,
askfirst.py), every "import facts" / "import dossier" still loads the asset maker's own - as on the Mac."""
import os
import subprocess
import sys
import tempfile

ok = 0


def check(cond, what):
    global ok
    print(("PASS " if cond else "FAIL ") + what)
    assert cond, what
    ok += 1


home = tempfile.mkdtemp()
suite = os.path.join(home, ".hellbox", "ai")
hart = os.path.join(suite, "hart")
os.makedirs(hart)
open(os.path.join(suite, "facts.py"), "w").write("WHO = 'the suite'\n")
open(os.path.join(suite, "progress.py"), "w").write("WHO = 'the suite'\n")
open(os.path.join(suite, "testlock.py"), "w").write(
    "import os, sys\nHERE = os.path.dirname(os.path.abspath(__file__))\nsys.path.insert(0, HERE)\n"
    "def testing():\n    import progress\n    return progress.WHO == 'the suite' and False\n"
    "def mine():\n    return False\n")
open(os.path.join(suite, "askfirst.py"), "w").write(
    "import os, sys\nsys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'hart'))\n"
    "def ask_pick(*a):\n    import hart\n    return hart.WHO\n")
open(os.path.join(hart, "hart.py"), "w").write("WHO = 'the phone bot'\n")
open(os.path.join(hart, "dossier.py"), "w").write("WHO = 'the phone bot'\n")
prog = r'''
import os, sys
sys.path.insert(0, "/home/claude/crushed/library")
import run                                   # sets the search list exactly as on the Mac
import vet
print("testlock ok:", vet._test_running() is False)
import askfirst
print("askfirst ok:", askfirst.ask_pick() == "the phone bot")
for n in ("facts", "dossier"):
    sys.modules.pop(n, None)
import facts, dossier
print("facts:", facts.__file__, hasattr(facts, "not_printed"))
print("dossier:", dossier.__file__, hasattr(dossier, "replan"))
import ownmods
print("wrong:", ownmods.wrong())
'''
env = dict(os.environ, HOME=home, CRUSHED_REMASTER_WORK=os.path.join(home, "work"))
r = subprocess.run([sys.executable, "-c", prog], capture_output=True, text=True, env=env, timeout=300)
out = r.stdout + r.stderr
print(out[-1500:])
check("testlock ok: True" in out, "the suite's testlock loads and answers (and its folder is not left in front)")
check("askfirst ok: True" in out, "askfirst and the phone bot still load")
check("facts: /home/claude/crushed/library/facts.py True" in out, "import facts -> the asset maker's facts.py")
check("dossier: /home/claude/crushed/library/dossier.py True" in out, "import dossier -> the asset maker's dossier.py")
check("wrong: []" in out, "nothing loaded under the asset maker's names from elsewhere")
print(f"\n{ok} checks passed")
