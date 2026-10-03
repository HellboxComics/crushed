"""THE ASSET MAKER'S OWN FILES ALWAYS WIN.

The asset maker shares the Mac with your other AI tools (~/.hellbox/ai, its phone bot in ~/.hellbox/ai/hart), and some
of their files have the same names as the asset maker's: facts.py, dossier.py. Some of those tools also put their own
folder at the FRONT of Python's search list when they are loaded (testlock.py, askfirst.py). After that, a plain
"import facts" anywhere in the asset maker got your suite's facts.py instead of its own - found 2026-10-03: every
dossier stopped with "module 'facts' has no attribute 'not_printed'" and every item was built without one.

install() fixes the whole kind of problem: for any name that is one of the asset maker's own files (library/<name>.py),
Python is sent straight to that file, wherever anything else has put its folders. Other tools' modules with other
names (askfirst, hart, testlock, turnaround) are still found as before.

    import ownmods; ownmods.install()      # first thing in every program the asset maker starts
    ownmods.wrong()                        # [(name, file)] own names that were loaded from somewhere else
"""
import importlib.abc
import importlib.util
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


class OwnFiles(importlib.abc.MetaPathFinder):
    def find_spec(self, name, path=None, target=None):
        if "." in name:
            return None
        f = os.path.join(HERE, name + ".py")
        return importlib.util.spec_from_file_location(name, f) if os.path.isfile(f) else None


def install():
    """Send every import of one of the asset maker's own names to its own file (safe to call more than once)."""
    if not any(type(f).__name__ == "OwnFiles" for f in sys.meta_path):
        sys.meta_path.insert(0, OwnFiles())
    if HERE not in sys.path:
        sys.path.insert(0, HERE)
    for n, f in wrong():                     # loaded from elsewhere before install(): loaded again from our file
        sys.modules.pop(n, None)


def add_path(p):
    """Another tool's folder, put at the END of the search list (never in front of the asset maker's own files)."""
    p = os.path.expanduser(p)
    if p not in sys.path:
        sys.path.append(p)


def outside(path, name=None):
    """A module from another tool, loaded from its file without touching the search list (testlock, ...)."""
    path = os.path.expanduser(path)
    name = name or "outside_" + os.path.splitext(os.path.basename(path))[0]
    if name in sys.modules:
        return sys.modules[name]
    if not os.path.isfile(path):
        return None
    keep = list(sys.path)
    try:
        spec = importlib.util.spec_from_file_location(name, path)
        mod = importlib.util.module_from_spec(spec)
        sys.modules[name] = mod
        spec.loader.exec_module(mod)
        return mod
    except Exception:
        sys.modules.pop(name, None)
        return None
    finally:
        sys.path[:] = keep                           # anything it put in front of the search list: taken back out
        add_path(os.path.dirname(path))              # (at the end: its own later imports of its neighbours still work)


def wrong():
    """[(name, file)]: modules loaded under one of the asset maker's own names but from another file."""
    out = []
    for n, m in list(sys.modules.items()):
        if "." in n or not os.path.isfile(os.path.join(HERE, n + ".py")):
            continue
        f = getattr(m, "__file__", None) or ""
        if not f or os.path.dirname(os.path.abspath(f)) != HERE:
            out.append((n, f))
    return out
