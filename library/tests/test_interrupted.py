"""A build stopped only because the run was restarted (a newer version, a restart asked for) goes on at once - it
did not fail (2026-10-07 12:27: after a restart the battery sat parked for an hour, 'stopped: the run was
interrupted'). A real error still waits an hour; at most 3 tries a day either way."""
import os
import sys
import tempfile
import time

os.environ["CRUSHED_REMASTER_WORK"] = tempfile.mkdtemp()
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import run  # noqa: E402

ok = 0


def check(cond, what):
    global ok
    print(("PASS " if cond else "FAIL ") + what)
    assert cond, what
    ok += 1


now = time.time()
sha = run.code_sha()
v = {"step": 'stopped: the run was interrupted while "4/7 your AI gets to know the item"', "at": now - 60, "code": sha}
check(run.retry_due("x", v, {"x": [[now - 600, sha]]}, now) is True, "interrupted by a restart: tried again at once")
e = {"step": "stopped: KeyError 'faces'", "at": now - 60, "code": sha}
check(run.retry_due("x", e, {"x": [[now - 600, sha]]}, now) is False, "a real error still waits its hour")
check(run.retry_due("x", v, {"x": [[now - 600, sha]] * 3}, now) is False, "and never more than 3 tries a day")
print(f"ALL {ok} PASS")
