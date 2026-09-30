# Art slots

Every printed surface in the collection (magazine covers, centerfolds, labels, cans, packaging, posters, screens)
is a slot. To replace one with your own art, drop a PNG into `assets/slots/`:

- `<slot>.png` replaces that surface everywhere it appears.
- `<slot>_<anything>.png` adds variants; one is dealt per object, deterministically.

`python3 blender/slots.py` writes a template for every slot into `assets/slots/_templates/` at the right size and
shape. Nothing else changes: the recipe, the crushing, the lighting and the metadata stay as they are.

Everything in `assets/slots/` (not the templates) is hashed into `collection/manifest.json`, so the published
provenance covers the art you dropped in. Change a slot after the freeze and the hash no longer matches.
