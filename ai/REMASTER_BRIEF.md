# BRIEF: CRUSHED.BUZZ REMASTER -- rebuild every object as a real Blender model, hands off

Written 2026-10-01 from Harrow's words: "go back through everything ... make all assets look even more realistic
... using actual blendr instead of code." The project is ~/crushed-render/repo. The collection stays ON HOLD
(collection/HOLD) the whole time: the crusher renders nothing until Harrow says the remaster is done.

## The loop (the clock runs `crushed remaster` for you; this is what it does and what you check)
    cd ~/crushed-render/repo && .venv/bin/python ai/remaster.py --limit 3
Each object: the drawing room paints a 2x2 reference sheet (front, back, left, right) from
ai/remaster/prompts/<name>.txt, the sculptor makes the shape, Blender fits it to the real size and paints the
sheet on. Result: assets/models_pending/<name>/ with model.glb, reference.png and review.png
(top row = the remaster from four sides, bottom row = the code version it replaces).

## Your job each cycle
1. PROMPTS FIRST. Before an object is made, open its prompt and rewrite it into an exact physical description of
   the real object: overall shape and proportions, materials (glossy ABS, rubber, brushed aluminum, cardboard),
   exact colors, every recognizable detail (button layout, vents, ports, seams, screws, labels' placement and
   colors), wear. One paragraph. The image model draws exactly what the text says, nothing more.
   Then the INSIDE: write ai/remaster/prompts/<name>.inside.txt, what you would see if it split open. A game
   cartridge: green circuit board, black chips, gold contacts. A chocolate bar: the filling (nougat, caramel,
   wafer layers). A sneaker: foam midsole and fabric lining. A plush: white polyester stuffing and plastic
   pellets. A console: motherboard, heat sink, ribbon cables. A soda can: bare aluminum, a little syrup.
   The crusher tears holes in the shell and this is what shows through, so make it true to the object.
   Writing the .inside.txt is what marks the object ready: the loop only makes objects that have one.
2. LOOK at every review.png. A remaster passes only if, from the four sides, it is (a) obviously that object,
   (b) more real than the code version under it, (c) whole: no holes, no melted blobs, no extra limbs, no
   background baked into the texture, no wrong colors. Then write one line to
   ai/remaster/verdicts.txt:  `<name> PASS` or `<name> REDO <why>`.
3. A REDO: improve the prompt (say what went wrong in plain terms: "single object, no stand", "flat front view"),
   then `.venv/bin/python ai/remaster.py --only <name> --redo`. Three tries, then `<name> KEEP CODE` and move on:
   the code version stays, nothing is lost.
4. You never approve. Harrow approves from the review sheet:
   `.venv/bin/python ai/remaster.py --sheet` puts it on his Desktop. He runs `--approve`.
5. `note` progress once a day in plain words: how many passed, how many kept code, what is next.

## Rules (his, standing)
- American spelling. Never delete a file (redos move the old one to ~/Desktop/_to delete/remaster/).
- Never spend money. Nothing leaves this machine.
- Slop is a bug: nothing gets a PASS you would not show him.
- If the drawing room or the sculptor is off, `note` it in plain words and stop that cycle; do not open them yourself.
- The sculptor's license (Hunyuan3D-2) asks that AI-made work be labeled as AI-made when published.
