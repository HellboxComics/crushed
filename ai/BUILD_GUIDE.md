# How to build an object for CRUSHED IT (for the local AI)

You are adding props to a Blender object library. No Blender window is involved: Blender is a Python module
(`bpy`) and everything is code. One object = one function. Build it, render it, look at it, fix it, repeat.

## Setup (once)

    cd ~/crushed-render/repo            # the project (bash scripts/mac_time_one.sh sets this up)
    .venv/bin/python -c "import bpy; print(bpy.app.version_string)"      # prints 5.0.1

Use `.venv/bin/python` for every command below.

## The loop

1. Write the function in `blender/crushed/objects/modern.py` (2009-2026 things), `era.py` (older eras),
   `degen.py` (the adult/gambling shelf), `filler.py` (debris), or `gifts.py` (one-of-one props).
2. Render it on the stage, uncrushed:

        .venv/bin/python blender/catalog.py --names my_object --out /tmp/my_object.png --res 800 --samples 24

3. Open `/tmp/my_object.png` and look. Does it read as the thing from across a room? Is the print readable?
   Fix and render again until it does.
4. Render it crushed inside a block to see it survive the press (pick any token):

        .venv/bin/python blender/generate.py --token 44 --out /tmp/t --res 640 --samples 32

5. Add the display name to `NAMES` and three one-line inventory notes to `NOTES` in `blender/crushed/lore.py`.
6. Run `.venv/bin/python blender/selftest.py` (must pass) and hand it in.

## Anatomy of an object

```python
@obj("lava_lamp", eras=(1, 2), mass=0.6, weight=0.8, hero=(0, -1, 0))
def lava_lamp(b, rng, pal):
    # a lathe is a 2D profile (radius, height) spun into a solid; this one is the glass bottle
    b.lathe([(0.0, 0.0), (0.03, 0.0), (0.045, 0.06), (0.025, 0.2), (0.02, 0.24), (0.0, 0.24)],
            loc=(0, 0, -0.14), mat="glass", seg=28)
    b.lathe([(0.0, 0.0), (0.05, 0.0), (0.03, 0.09), (0.0, 0.09)], loc=(0, 0, -0.23), mat="base", seg=28)
    b.cyl(0.02, 0.03, loc=(0, 0, 0.115), mat="base", seg=20)                     # the cap
    for z in (-0.08, -0.02, 0.05):                                               # blobs of wax
        b.sphere(0.018, loc=(0, 0, z), scale=(1, 1, 1.4), mat="wax", seg=14)
    return {"glass": ("glass", {"color": (0.9, 0.5, 0.8), "trans": 1.0, "rough": 0.02}),
            "base": ("metal", {"color": (0.8, 0.72, 0.4), "rough": 0.3}),
            "wax": ("plastic", {"color": (1.0, 0.3, 0.1), "rough": 0.3, "glow": 1.5})}
```

- `@obj(name, eras, mass, weight, hero, group, big, tags)` registers it. `eras` are indexes into
  `["1985-1990", "1991-1996", "1997-2002", "2003-2008", "2009-2026"]`. `mass` is kilograms (the block's weight
  adds them up). `weight` is how often it is dealt. `hero` is the face that should point at the camera
  (`(0,0,1)` = top, `(0,-1,0)` = front). `big=True` for things that take a whole face. `group="filler"` for
  debris that fills gaps, `"special"` for one-of-one props (never dealt into the regular 888).
- Everything is in meters. A 12-inch cube is 0.3048 m; a hero object is scaled to about 0.17 m on its
  longest side, so build at real size and let the stage scale it.
- `b` is the Builder. Parts: `box(size, loc, rot, mat, bevel)`, `cyl(r, depth, ...)`, `sphere(r, ...)`,
  `plane(w, h, ...)` (a flat print; UV 0..1), `lathe(profile, ...)`, `tube(points, r, ...)`,
  `extrude(outline, depth, ...)`, `torus(R, r, ...)`, `loft(rings, ...)`. `b.frame = Matrix` sets a local
  frame for the parts that follow; reset to `Matrix.Identity(4)` after.
- `rng` is a seeded numpy Generator. Use it for every random choice so the collection is reproducible.
  Never use `random`. `pal` is the era palette: `pal.body()` for a plausible housing color, `pal.loud()`.
- The returned dict maps each material key you used to a spec `(kind, params)`. Kinds: `plastic`,
  `translucent`, `rubber`, `metal`, `chrome`, `gold`, `glass`, `printed` (`{"image": tex.something(rng, "key")}`),
  `paper`, `cardboard`, `foam`, `fabric`, `tape`, `clay`, `wood`, `wax`, `screen`, `gem`, `copper`. Params:
  `color` (0..1 RGB as you would see it), `rough`, `coat`, `glow` (emission strength), `keep=True` (do not let
  a one-of-one's whole-block finish repaint this part).
- Prints: `tex.py` has a numpy `Canvas` with `rect`, `circle`, `line`, `poly`, `text`, `text_fit`, `gradient`,
  `noise`, and a 5x7 pixel font. A new print is a function `def my_print(rng, name): ... return c.image(name)`.
  Add it to `SLOT_NAMES` at the bottom of `tex.py` and it becomes a drop-in slot automatically (a PNG in
  `assets/slots/` overrides it).

## Rules

- Original, generic shapes only. Era comes from shape, color, material and invented print, never from a real
  logo, wordmark, mascot or a copy of a real product's trade dress. Invented brand names are encouraged.
- American spelling in every string that can be seen.
- No deleting files. No `random`. No network. No paths under `~/Desktop` typed by hand.
- Determinism: the same token must build the same block every time. `blender/generate.py --verify` proves it.
- When a bug is found in one object (a scrambled print, a wrong scale), fix every object that shares it.

## OPEN: objects wanted

Build these next, in this order. Each is a gift block's prop or a regular-deal object.

LOW RES (the Pixelord gift, purple and acid green): `lava_lamp`, `skull_candle`, `black_cat_figurine`,
`potted_plant`, `mini_arcade`, `mushroom_cluster`, `server_rack_slice`, `pixel_heart`.
Regular deal, 2009-2026: `gaming_mouse`, `rgb_fan`, `energy_shot`, `air_pods_single`, `phone_grip`,
`sticker_sheet`, `ring_box_empty`, `hot_sauce_bottle`.
Regular deal, 1985-2002: `view_finder`, `trapper_binder`, `scrunchie`, `pogs_tube`, `lite_brite_peg_sheet`,
`cereal_box_flat`, `trading_card`, `jelly_shoe`.
Degen shelf: `lighter_tray`, `ash_tray`, `dollar_wad`, `lottery_pencil`, `club_wristband`, `beer_koozie`.
