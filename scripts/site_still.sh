#!/bin/bash
# Paste-once. Puts the real 1024px renders of the 8 teaser cubes on crushed.buzz (no 3D, no GPU work) and publishes.
(
set -e
cd ~/crushed-render/repo && git pull -q
SRC=~/crushed-render/out/$(cut -c3-12 collection/provenance.txt)
mkdir -p site/cube
for id in 529 8 282 324 344 527 552 718; do
  n=$(printf "%04d" $id)
  [ -f "$SRC/$n.png" ] || { echo "STOP: cube $n isn't rendered yet in $SRC"; exit 0; }
  .venv/bin/python -c "from PIL import Image; Image.open('$SRC/$n.png').convert('RGB').save('site/cube/$n.webp', quality=92, method=6)"
done
mkdir -p "$HOME/Desktop/_to delete/crushed-buzz-3d-cubes"
mv site/cube/*.glb "$HOME/Desktop/_to delete/crushed-buzz-3d-cubes/" 2>/dev/null || true
echo "the 3D cube files from the site, parked while the 3D gets fixed" > "$HOME/Desktop/_to delete/crushed-buzz-3d-cubes/WHAT THIS IS.txt"
npx --yes wrangler@3 pages deploy site --project-name crushed-buzz --branch main --commit-dirty=true
)
