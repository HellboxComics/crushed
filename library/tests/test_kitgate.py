"""THE KIT GATE: nothing is built from a family without a finished kit; your AI studies the kind first; no kit, no build."""
import os
import sys

os.environ["CRUSHED_REMASTER_WORK"] = "/tmp/claude-0/-home-claude-crushed/db81eea7-ef8c-55dd-b827-ea6e2d91f37e/scratchpad/mine_work"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import run  # noqa: E402
import kitmaker  # noqa: E402
import families  # noqa: E402

ok = 0


def check(cond, what):
    global ok
    print(("PASS " if cond else "FAIL ") + what)
    assert cond, what
    ok += 1


run.say = lambda *a, **k: None
card = {"product": "Furby 1998 gray with pink ears", "size": [0.12, 0.12, 0.15]}
# 1. a finished hand-written kit: through at once
c = run.ensure_kit("t", card, {"family": "cylindrical_cell"}, None, "brain")
check(c[0][1] is True and "hand-written" in c[0][2], f"a finished kit passes the gate: {c[0][2]}")

# 2. a family with no kit: the kind your AI named is studied and used
studied = []
good = {"what": "an electronic plush toy", "parts": [{"part": "body"}, {"part": "eyeballs"}, {"part": "light sensor"}],
        "zones": [{"name": "body", "kind": "fabric"}], "faces": ["body"], "builder": "assembly", "builder_status": "partial",
        "route": "free", "learned": {"version": 1}}


def fake_ensure(kind, card_, photo, use, log=print):
    studied.append(kind)
    if kind == "electronic plush toy":
        families.library()["families"]["electronic_plush_toy"] = good
        return "electronic_plush_toy", good
    return None, None


real_ensure = kitmaker.ensure
kitmaker.ensure = fake_ensure
try:
    fl = {"family": "organic_toy", "kind_name": "electronic plush toy"}
    c = run.ensure_kit("t", card, fl, None, "brain")
    check(c[0][1] is True and fl["family"] == "electronic_plush_toy" and card["family_lib"]["family"] == "electronic_plush_toy",
          f"a family with no kit: the named kind is studied and becomes the item's family ({c[0][2][:60]})")
    check(studied == ["electronic plush toy"], "studied once, as the kind the AI named")
    # 3. no kit can be written: no build
    studied.clear()
    kitmaker.ensure = lambda kind, card_, photo, use, log=print: (studied.append(kind), (None, None))[1]
    try:
        run.ensure_kit("t", {"product": "Mystery widget, circa 1990", "size": [0.1, 0.1, 0.1]},
                       {"family": "organic_toy", "kind_name": "mystery widget"}, None, "brain")
        check(False, "no kit must stop the build")
    except RuntimeError as e:
        check("no kit" in str(e) and "never" not in "" and "mystery widget" in str(e), f"no kit -> the build stops and says why: {str(e)[:80]}")
    check(studied.count("mystery widget") == 2 and studied.count("organic_toy") == 2 and len(studied) == 4,
          f"every distinct name was tried twice (the product's first words equal the kind here): {studied}")
finally:
    kitmaker.ensure = real_ensure
    families.library()["families"].pop("electronic_plush_toy", None)
print(f"\n{ok} checks passed")
