"""Shared test setup: a throwaway git repo with a copy of the code, a copy of the Duracell work data, a fake HOME."""
import json
import os
import shutil
import subprocess
import sys

SCR = "/tmp/claude-0/-home-claude-crushed/db81eea7-ef8c-55dd-b827-ea6e2d91f37e/scratchpad"
SRC = "/home/claude/crushed"
DATA = os.path.join(SCR, "eng", "work")
CID = "duracell_coppertop_aa_1998"
NB = "energizer_fake_aa_1999"            # a made-up second round item (the neighbor)


def sh(*a, cwd=None, check=True):
    r = subprocess.run(list(a), cwd=cwd, capture_output=True, text=True)
    if check and r.returncode:
        raise RuntimeError(f"{a}: {r.stderr}")
    return r


def make(name, with_data=True):
    T = os.path.join(SCR, "t", name)
    if os.path.exists(T):                                    # a test fixture (the session's scratch, not the owner's
        shutil.rmtree(T, ignore_errors=True)                 # files): remade fresh each run - 16 GB of old copies
        #                                                      filled the disk on 2026-10-04
    home, repo, work = (os.path.join(T, n) for n in ("home", "repo", "work"))
    os.makedirs(home)
    os.makedirs(repo)
    shutil.copytree(os.path.join(SRC, "library"), os.path.join(repo, "library"),
                    ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copy(os.path.join(SRC, ".gitignore"), os.path.join(repo, ".gitignore"))
    sh("git", "init", "-q", "-b", "main", cwd=repo)
    sh("git", "-c", "user.name=t", "-c", "user.email=t@t", "add", "-A", cwd=repo)
    sh("git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "base", cwd=repo)
    os.makedirs(work)
    if with_data:
        shutil.copytree(os.path.join(DATA, "cards"), os.path.join(work, "cards"))
        lib = os.path.join(work, "library")
        shutil.copytree(os.path.join(DATA, "library", CID), os.path.join(lib, CID))
        shutil.copytree(os.path.join(DATA, "library", CID), os.path.join(lib, NB))
        card = json.load(open(os.path.join(work, "cards", CID + ".json")))
        card.update(id=NB, product="Energizer AA (made up for the test)")
        json.dump(card, open(os.path.join(work, "cards", NB + ".json"), "w"), indent=1)
        json.dump({CID: {"step": "failed the realism check", "verdict": {"pass": False, "failed": ["details"]}},
                   NB: {"step": "done", "verdict": {"pass": False, "failed": ["print"]}}},
                  open(os.path.join(lib, "status.json"), "w"), indent=1)
        os.makedirs(os.path.join(home, ".hellbox"))
        json.dump({CID: {"pick": "1"}, NB: {"pick": "1"}}, open(os.path.join(home, ".hellbox", "picks.json"), "w"))
    return T, home, repo, work


def env_for(home, work):
    return dict(os.environ, HOME=home, CRUSHED_REMASTER_WORK=work)


def alive(pid):
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    try:
        return open(f"/proc/{pid}/stat").read().rsplit(")", 1)[1].split()[0] != "Z"
    except OSError:
        return False


class Check:
    def __init__(self):
        self.ok, self.bad = 0, []

    def __call__(self, cond, what):
        if cond:
            self.ok += 1
            print("  PASS", what, flush=True)
        else:
            self.bad.append(what)
            print("  FAIL", what, flush=True)

    def done(self):
        print(f"\n{self.ok} passed, {len(self.bad)} failed", flush=True)
        for b in self.bad:
            print("   failed:", b)
        sys.exit(1 if self.bad else 0)
