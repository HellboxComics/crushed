#!/bin/bash
# Paste-once. Builds the homepage's 3D cube on this Mac's GPU (skipped if it is already current), then
# publishes the site to Cloudflare (crushed-buzz). Prints the live link.
(
set -e
cd ~/crushed-render/repo && git pull -q
FREEZE=$(cut -c3-12 collection/provenance.txt)
STAMP="site/cube/.freeze"
if [ "$(cat "$STAMP" 2>/dev/null)" != "$FREEZE" ]; then
  echo "building the 3D cube (a few minutes on the GPU)..."
  .venv/bin/python blender/export_glb.py --token 44 --out site/cube --size 4096 --samples 16 --device auto | grep "\[glb\]"
  .venv/bin/python blender/generate.py --token 44 --res 1024 --samples 64 --device auto --out /tmp/crushed_poster >/dev/null 2>&1
  .venv/bin/python -c "from PIL import Image; Image.open('/tmp/crushed_poster/0044.png').convert('RGB').save('site/cube/0044.webp', quality=88)"
  echo "$FREEZE" > "$STAMP"
else
  echo "3D cube already current, skipping"
fi
command -v npx >/dev/null || { echo "STOP: install Node from https://nodejs.org (LTS button), then paste again."; exit 2; }
npx --yes wrangler@3 pages deploy site --project-name crushed-buzz --branch main --commit-dirty=true
)
