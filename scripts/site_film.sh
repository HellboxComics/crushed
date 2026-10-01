#!/bin/bash
# Paste-once. Puts the opening film on crushed.buzz: shrinks the finished film (wide for computers, square for
# phones) to web size, adds the 8 cube pictures, and publishes the site.
(
set -e
cd ~/crushed-render/repo && git pull -q
W=~/Desktop/crushed_buzz_hero.mp4; Q=~/Desktop/crushed_buzz_hero_square.mp4
[ -f "$W" ] && [ -f "$Q" ] || { echo "STOP: the film isn't finished yet (paste the film render first)."; exit 0; }
FF=$(.venv/bin/python -c "import imageio_ffmpeg; print(imageio_ffmpeg.get_ffmpeg_exe())")
mkdir -p site/film
"$FF" -y -loglevel error -i "$W" -vf scale=1920:-2 -c:v libx264 -preset slow -crf 22 -profile:v high -pix_fmt yuv420p \
  -c:a aac -b:a 160k -movflags +faststart site/film/hero_wide.mp4
"$FF" -y -loglevel error -i "$Q" -vf scale=1080:1080 -c:v libx264 -preset slow -crf 23 -profile:v high -pix_fmt yuv420p \
  -c:a aac -b:a 160k -movflags +faststart site/film/hero_square.mp4
ls -lh site/film/*.mp4 | awk '{print "  " $9 "  " $5}'
SRC=~/crushed-render/out/$(cut -c3-12 collection/provenance.txt)-$(cat blender/ART_VERSION)
for id in 529 8 282 324 344 527 552 718; do
  n=$(printf "%04d" $id)
  [ -f site/cube/$n.webp ] && [ site/cube/$n.webp -nt "$SRC/$n.png" ] && continue
  .venv/bin/python -c "from PIL import Image; Image.open('$SRC/$n.png').convert('RGB').save('site/cube/$n.webp', quality=92, method=6)"
done
mkdir -p "$HOME/Desktop/_to delete/crushed-buzz-3d-cubes"
mv site/cube/*.glb "$HOME/Desktop/_to delete/crushed-buzz-3d-cubes/" 2>/dev/null || true
npx --yes wrangler@3 pages deploy site --project-name crushed-buzz --branch main --commit-dirty=true
)
