#!/bin/bash
# Paste-once. Renders all 888 blocks at 1024px into ~/crushed-render/out, one PNG each, then the homepage
# turntable (72 frames of serial 0044) and the pre-reveal "sealed" image.
# - runs in a subshell under nohup + caffeinate, so closing the window or sleeping the Mac does not stop it
# - skips any block that already has a finished PNG, so pasting it again simply resumes
# - logs to ~/crushed-render/out/render.log, with a count line after every block
# Watch it:  tail -f ~/crushed-render/out/render.log     Count done:  ls ~/crushed-render/out/0*.png | wc -l
(
  curl -fsSL https://raw.githubusercontent.com/HellboxComics/crushed/claude/epic-galileo-iubypk/scripts/_setup.sh \
      -o "${TMPDIR:-/tmp}/crushed_setup.sh" || { echo "Could not download the setup script."; exit 1; }
  source "${TMPDIR:-/tmp}/crushed_setup.sh"
  OUT="$WORK/out"; mkdir -p "$OUT"
  cat > "$WORK/run_all.sh" <<'RUN'
cd "$(dirname "$0")/repo"
OUT="$(dirname "$0")/out"
.venv/bin/python blender/generate.py --range 1 888 --res 1024 --samples 96 --device auto --skip-existing --out "$OUT" \
  | while IFS= read -r line; do echo "$line"; echo "progress: $(ls "$OUT"/0*.png 2>/dev/null | wc -l | tr -d ' ')/888 blocks"; done
[ -d "$OUT/0044_frames" ] || .venv/bin/python blender/generate.py --token 44 --turntable 72 --res 1024 --samples 96 --device auto --out "$OUT"
[ -f "$OUT/sealed.png" ] || .venv/bin/python blender/generate.py --sealed --res 1024 --samples 96 --device auto --out "$OUT"
echo "ALL DONE: $(ls "$OUT"/0*.png | wc -l | tr -d ' ') blocks, turntable and sealed image in $OUT"
RUN
  nohup caffeinate -i bash "$WORK/run_all.sh" >> "$OUT/render.log" 2>&1 &
  echo "Started. Follow along with:  tail -f $OUT/render.log"
)
