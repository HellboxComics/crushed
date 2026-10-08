"""A stopped run's drawing is taken out of the drawing room (ComfyUI's /queue clear and /interrupt), so the next
self-test is not stuck behind it (2026-10-08 00:20)."""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import watchdog as W  # noqa: E402

sent = []


class R:
    def read(self):
        return b"{}"


W.urllib.request.urlopen = lambda req, timeout=10: (sent.append((req.full_url, req.data)) or R())
W.clear_room()
assert [u.rsplit("/", 1)[1] for u, _ in sent] == ["queue", "interrupt"], sent
assert b'"clear": true' in sent[0][1]
src = open(W.__file__).read()
assert "    clear_room()\n" in src.split("def stop_run")[1].split("def clear_room")[0]
print("ALL 3 PASS")
