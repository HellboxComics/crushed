#!/bin/bash
# Hands-off: waits for the crusher to finish all 888 (so the two don't fight over the GPU), renders the hero film,
# makes the wide and square cuts with sound, then puts the film on crushed.buzz. Runs in the background, Mac kept awake.
# Watch it: tail -f ~/crushed-render/film.log
(
source ~/crushed-render/repo/scripts/_setup.sh
.venv/bin/python -c "import imageio_ffmpeg" 2>/dev/null || .venv/bin/python -m pip install -q imageio-ffmpeg 2>/dev/null \
  || uv pip install -q --python .venv/bin/python imageio-ffmpeg
FREEZE=$(cut -c3-12 collection/provenance.txt)-$(cat blender/ART_VERSION)   # the freeze plus the art version: new art, new folder
OUT="renders/film_$FREEZE"
nohup caffeinate -i bash -c "
  while [ \$(ls ~/crushed-render/out/$FREEZE/0[0-9][0-9][0-9].png 2>/dev/null | wc -l) -lt 888 ]; do
    echo \"\$(date +%H:%M) waiting for the crusher: \$(ls ~/crushed-render/out/$FREEZE/0[0-9][0-9][0-9].png | wc -l)/888\"; sleep 300
  done
  .venv/bin/python film/render.py --out '$OUT' --samples \${SAMPLES:-64} --device auto 2>&1 | grep --line-buffered '\[film\]' &&
  .venv/bin/python film/sound.py &&
  .venv/bin/python film/cut.py --src '$OUT' --out ~/Desktop/crushed_buzz_hero.mp4 --stills ~/Desktop/crushed_buzz_hero_frames &&
  .venv/bin/python film/cut.py --src '$OUT' --out ~/Desktop/crushed_buzz_hero_square.mp4 --square &&
  bash scripts/site_film.sh &&
  echo \"\$(date +%H:%M) ALL DONE: film on your Desktop and live on crushed.buzz\"
" > ~/crushed-render/film.log 2>&1 &
echo "queued. It starts the film once all 888 are rendered. Watch: tail -f ~/crushed-render/film.log"
)
