# Shared by the Mac scripts: get the repo, a Python 3.11 environment, and the bpy wheel. Safe to run again.
set -e
WORK="$HOME/crushed-render"
mkdir -p "$WORK" && cd "$WORK"
command -v git >/dev/null || { echo "git is missing. Run: xcode-select --install   then paste this again."; exit 1; }
if [ -d repo/.git ]; then
  git -C repo pull -q
else
  git clone -q --depth 1 -b claude/epic-galileo-iubypk https://github.com/HellboxComics/crushed repo
fi
cd repo
export PATH="$HOME/.local/bin:$PATH"
if [ ! -x .venv/bin/python ]; then
  if command -v python3.11 >/dev/null; then
    python3.11 -m venv .venv
  else
    command -v uv >/dev/null || curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
    uv venv --python 3.11 .venv
  fi
fi
if [ ! -f .venv/.ready ]; then
  if .venv/bin/python -m pip --version >/dev/null 2>&1; then
    .venv/bin/python -m pip install -q "bpy==5.0.1" "numpy==1.26.4" pillow
  else
    uv pip install -q --python .venv/bin/python "bpy==5.0.1" "numpy==1.26.4" pillow
  fi
  touch .venv/.ready
fi
.venv/bin/python blender/generate.py --verify 2>&1 | grep -E "verify" || { echo "The recipe on this Mac does not match the frozen collection. Stop and tell Claude."; exit 2; }
