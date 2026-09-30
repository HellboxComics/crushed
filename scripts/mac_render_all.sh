#!/bin/bash
# Paste-once. Renders all 888 blocks at 1024px into ~/crushed-render/out, one PNG each.
# - runs in a subshell under nohup + caffeinate, so closing the window or sleeping the Mac does not stop it
# - skips any block that already has a finished PNG, so pasting it again simply resumes
# - logs to ~/crushed-render/out/render.log
# Watch it:  tail -f ~/crushed-render/out/render.log     Count done:  ls ~/crushed-render/out/*.png | wc -l
(
  source <(curl -fsSL https://raw.githubusercontent.com/HellboxComics/crushed/claude/epic-galileo-iubypk/scripts/_setup.sh)
  OUT="$WORK/out"; mkdir -p "$OUT"
  nohup caffeinate -i .venv/bin/python blender/generate.py --range 1 888 --res 1024 --samples 96 --device auto \
      --skip-existing --out "$OUT" >> "$OUT/render.log" 2>&1 &
  echo "Started. Follow along with:  tail -f $OUT/render.log"
)
