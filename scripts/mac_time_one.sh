#!/bin/bash
# Paste-once. Renders ONE block (#0044) on this Mac, says which device it used and how many seconds it took.
# Nothing else is rendered. Safe to run as many times as you like.
(
  curl -fsSL https://raw.githubusercontent.com/HellboxComics/crushed/claude/epic-galileo-iubypk/scripts/_setup.sh \
      -o "${TMPDIR:-/tmp}/crushed_setup.sh" || { echo "Could not download the setup script."; exit 1; }
  source "${TMPDIR:-/tmp}/crushed_setup.sh"
  S=$(date +%s)
  .venv/bin/python blender/generate.py --token 44 --res 1024 --samples 96 --device auto --out "$WORK/test" 2>&1 | grep -E "crushed\]|Error|Traceback"
  echo "Seconds for one 1024px block: $(( $(date +%s) - S ))  (includes scene build)"
  open "$WORK/test/0044.png" 2>/dev/null || true
)
