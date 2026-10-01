#!/bin/bash
# Paste-once. Builds the homepage's 3D cube on this Mac's GPU (skipped if it is already current), then
# publishes the site to Cloudflare (crushed-buzz). Prints the live link.
(
set -e
cd ~/crushed-render/repo && git pull -q
FREEZE=$(cut -c3-12 collection/provenance.txt)
STAMP="site/cube/.freeze"
if [ "$(cat "$STAMP" 2>/dev/null)" != "$FREEZE" ]; then
  # the eight cubes on the teaser: 529 is the default, the rest are one tap away
  for id in 529 8 282 324 344 527 552 718; do
    n=$(printf "%04d" $id)
    echo "building cube $n in 3D (about 2 minutes each on the GPU)..."
    .venv/bin/python blender/export_glb.py --token $id --out site/cube --size 4096 --samples 16 --device auto | grep "\[glb\]"
    .venv/bin/python blender/generate.py --token $id --res 768 --samples 64 --device auto --out /tmp/crushed_poster >/dev/null 2>&1
    .venv/bin/python -c "from PIL import Image; Image.open('/tmp/crushed_poster/$n.png').convert('RGB').save('site/cube/$n.webp', quality=86)"
  done
  echo "$FREEZE" > "$STAMP"
else
  echo "3D cubes already current, skipping"
fi
command -v npx >/dev/null || { echo "STOP: install Node from https://nodejs.org (LTS button), then paste again."; exit 2; }
npx --yes wrangler@3 pages deploy site --project-name crushed-buzz --branch main --commit-dirty=true
)
