import os
import re
import sys

os.environ["CRUSHED_REMASTER_WORK"] = "/tmp/claude-0/-home-claude-crushed/db81eea7-ef8c-55dd-b827-ea6e2d91f37e/scratchpad/mine_work"
sys.path.insert(0, "/home/claude/crushed/library")
import eraprint
import facts
import websearch

ok = 0


def check(cond, what):
    global ok
    print(("PASS " if cond else "FAIL ") + what)
    assert cond, what
    ok += 1


# --- UPC check digit
check(facts.upc_check("038000317101")["ok"], "038000317101 is a valid UPC-A")
check(facts.upc_check("0038000317101")["upc"] == "038000317101", "EAN-13 with a leading 0 reads as the same UPC-A")
check(eraprint.check_digit("03800031710") == 1, "check digit of 03800031710 is 1")
bad = "03800031810"                       # the old prompt's example digits
made = eraprint.upc12(bad)
check(made == "038000318108" and made != "038000317101", f"03800031810 + its computed digit = {made}, not the real code")
check(not facts.upc_check("038000317102")["ok"], "a wrong check digit is refused")
try:
    eraprint.upc12("0380003171")          # 10 digits: never padded
    check(False, "10 digits refused")
except ValueError as e:
    check(True, f"10 digits refused ({e})")
check(facts.prefix("038000317101") == "038000", "maker prefix 038000")

# --- nutrition math
n_ok = {"calories": 200, "rows": [["Total Fat", "5g", "8%", 0], ["Total Carbohydrate", "37g", "12%", 0],
                                  ["Protein", "2g", "", 0]]}
r = facts.calories_check(n_ok)
check(r["ok"] is True and abs(r["from_grams"] - 201) < 0.01, f"200 kcal vs 4x37 + 4x2 + 9x5 = 201 -> ok ({r})")
n_bad = dict(n_ok, calories=320)
check(facts.calories_check(n_bad)["ok"] is False, "320 kcal with the same grams is off by more than 15%")
check(facts.calories_check({"calories": 200, "rows": []})["ok"] is None, "too few numbers -> no verdict")

# --- format by year
for y, f in ((1990, "pre_nlea"), (1993, "pre_nlea"), (1994, "1994_nlea"), (1997, "1994_nlea"), (2005, "1994_nlea"),
             (2006, "2006_trans"), (2019, "2006_trans"), (2020, "2020_new"), (2024, "2020_new")):
    check(facts.nutrition_format(y) == f, f"{y} -> {f}")

# --- sizes / counts
check(facts.sizes("NET WT. 14.7 OZ. (416g)") == {"oz": {14.7}, "g": {416}}, "sizes read from the box line")
check(facts.count_set("8 TOASTER PASTRIES") == {8} and facts.count_set("8") == {8}, "counts")
idn = {"brand": "Kellogg's", "line": "Pop-Tarts", "variant": "Frosted Strawberry", "count": "8 TOASTER PASTRIES",
       "size_text": "NET WT. 14.7 OZ. (416g)"}
check(facts._matches_item("Pop-Tarts - Frosted Strawberry Toaster Pastries 14.70 oz", idn), "title with 14.70 oz matches")
check(not facts._matches_item("Pop-Tarts Frosted Strawberry Pastries - 8ct/13.5oz", idn),
      "a 13.5 oz box is NOT our 14.7 oz item even with the same count")
check(not facts._matches_item("Pop Tarts Strawberry Milkshake - 8ct/13.54oz", idn), "another flavor is not ours")

# --- the web: a real read of upcitemdb
t = websearch.read("https://www.upcitemdb.com/upc/38000317101")
m = re.search(r"UPC-A:\s*([\d ]{14,16})", t)
title = re.search(r"is associated with ([^\n]+)", t)
print("  upcitemdb says:", m and m.group(1), "|", title and title.group(1))
check(m and re.sub(r"\D", "", m.group(1)) == "038000317101", "upcitemdb page read: UPC-A 0 38000 31710 1")
check(title and "Frosted Strawberry" in title.group(1) and "14.7" in title.group(1), "upcitemdb title names the item")


# --- retries: 3 a day, and a fresh count when newer code arrives
import run as R  # noqa: E402
R._CODE_TIME[:] = [1000.0]
now = 10000.0
v = {"step": "failed the realism check (x)", "at": 500.0}
check(R.retry_due("x", v, {"x": [600.0, 700.0, 800.0]}, now) is True,
      "three tries on OLD code do not count: an item failed on old code is due again now")
check(R.retry_due("x", v, {"x": [1100.0, 1200.0, 1300.0]}, now) is False, "three tries on THIS code: it waits")
v2 = {"step": "failed the realism check (x)", "at": 2000.0}
check(R.retry_due("x", v2, {}, now) is False, "failed on this code: waits its 6 hours")
check(R.retry_due("x", v2, {}, 2000.0 + 6 * 3600) is True, "and is due after them")
check(R.retry_due("x", {"step": "done", "at": 2000.0}, {}, now) is None, "a done item is not retried")
R._CODE_TIME[:] = []


# --- every brain question has a word budget; an answer that was all thinking is asked again plainly
import json as _json  # noqa: E402
import urllib.request as _ur  # noqa: E402
import vet  # noqa: E402
_seen = []


class _R:
    def __init__(self, n):
        self.n = n

    def __enter__(self):
        return self

    def __exit__(self, *a):
        pass

    def read(self):
        return _json.dumps({"message": {"content": "(thinking, cut off)" if self.n == 1 else '{"ok": 1}'}}).encode()


def _fake(req, timeout=0):
    _seen.append(_json.loads(req.data))
    return _R(len(_seen))


_real_open, _real_test = _ur.urlopen, vet._test_running
_ur.urlopen, vet._test_running = _fake, lambda: False
try:
    r = vet.ask("m", "q", [], think=True)
finally:
    _ur.urlopen, vet._test_running = _real_open, _real_test
check(r == {"ok": 1} and len(_seen) == 2, "an answer with no JSON (budget spent thinking) is asked again without thinking")
check(_seen[0]["options"]["num_predict"] == vet.THINK_WORDS and _seen[1]["options"]["num_predict"] == vet.PLAIN_WORDS
      and _seen[1]["think"] is False, "both questions carry a word budget")
_seen.clear()
_ur.urlopen, vet._test_running = _fake, lambda: False
try:
    vet._call("/api/chat", {"model": "m", "think": True, "messages": [{"role": "user", "content": "x"}]})
finally:
    _ur.urlopen, vet._test_running = _real_open, _real_test
check(_seen[0]["options"]["num_predict"] == vet.THINK_WORDS, "a call made elsewhere without a budget gets one")
print(f"\n{ok} checks passed")
