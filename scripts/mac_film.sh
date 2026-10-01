#!/bin/bash
# Renders the crushed.buzz hero film (3440 x 1440, 24 fps, 24 s) on this Mac's GPU, then edits it into
# ~/Desktop/crushed_buzz_hero.mp4 (plus one still per second in ~/Desktop/crushed_buzz_hero_frames).
# Runs in the background with the Mac kept awake; pasting again resumes where it stopped.
# Watch it: tail -f ~/crushed-render/film.log
(
source ~/crushed-render/repo/scripts/_setup.sh
.venv/bin/python -c "import imageio_ffmpeg" 2>/dev/null || .venv/bin/python -m pip install -q imageio-ffmpeg 2>/dev/null \
  || uv pip install -q --python .venv/bin/python imageio-ffmpeg
OUT="renders/film_$(cut -c3-12 collection/provenance.txt)"
nohup caffeinate -i bash -c "
  .venv/bin/python film/render.py --out '$OUT' --samples ${SAMPLES:-64} --device auto 2>&1 | grep --line-buffered '\[film\]' &&
  .venv/bin/python film/sound.py &&
  .venv/bin/python film/cut.py --src '$OUT' --out ~/Desktop/crushed_buzz_hero.mp4 --stills ~/Desktop/crushed_buzz_hero_frames &&
  .venv/bin/python film/cut.py --src '$OUT' --out ~/Desktop/crushed_buzz_hero_square.mp4 --square &&
  open ~/Desktop/crushed_buzz_hero.mp4
" > ~/crushed-render/film.log 2>&1 &
echo "film is rendering in the background. Watch: tail -f ~/crushed-render/film.log"
)
