# Audit report 2 - build routes, exact checks, judge, inspect, review prompts, keeps, time, deliverable
Tags: [a] guessed where measurable, [b] uncaught failure, [c] stale keep, [d] item-specific, [e] time, [f] prompt, [g] deliverable.
Severity 3 = a wrong asset is made or passed silently. (Lines as of commit 3040def.)

## Root causes
1. [b] 3 THE STEP CHECKS GATE NOTHING: every review.Sheet.step check is informational; verdict = check_model only (run.py:439).
   -> every review check with ok False goes into verdict["failed"].
2. [b] 3 SIZE IS COMPARED TO THE NUMBER THE BUILDER WAS GIVEN: cards.py:116 default 0.1 m; dossier.py:908 copies it; measure.py:229
   checks against it. Nothing measures size from photos outside the round route. -> catalog size vs photo proportions + kit standard.
3. [b] 3 "NOTHING INVENTED" NOT ENFORCED: text check only looks for must_show; extra words, logos on unseen sides, sprinkles, solder
   traces, default bracket never flagged. -> OCR every side; fail untraceable tokens.
4. [c] 3 KEEPS SURVIVE REDO: start_over moves only model/ and skin/; label_kept.json, judge-side and inspect passes stay.
   -> Redo marks the item's keeps stale.

## 5a build() shared
- [b] 3 run.py:418 assembly/Hunyuan measured as six box sides by world axes -> render the dossier's named faces by measured view boxes.
- [b] 3 no orientation check: renders assume front=-Y up=+Z; OCR reads 4 rotations so a 180° label passes -> OCR at 0° only; orientation score per side.
- [b] 2 run.py:513-521 recipe failure -> hollow round item, inside_fit passes trivially -> fail when kit/recipe says insides exist.
- [a][d] 2 run.py:464 hand-made families.json AA master -> kits.spec_for only.
- [a] 2 run.py:531-535 labels/<cid>.json hand layout path bypasses label checks -> remove.
- [a] 2 run.py:600-603 surface guessed from material keywords -> per-part kit material.
- [b] 2 run.py:676 preview check=True kills build silently; viewshot failure -> close=None skips close checks.
- [b] 2 run.py:471-473/501 card rewritten each build; construction overwritten by spec.

## 5b round label
- [a] 3 whole artwork is brain vector art: 3 fonts (labelart.py:29-37), rect/ellipse/bar only; positions/heights/colors from a brain JSON
  -> word boxes/heights from OCR boxes on real.png; colors sampled under them; logos/graphics cut from real pixels as image layers.
- [b] 3 layout.py:327 color_check exception -> share 1.0 "100% right" -> share 0, fail.
- [b] 3 review.py:160 only_words tests tokens as substrings of the joined allowed string ("CELL","A","1" pass) -> whole normalized tokens vs set.
- [b] 2 whole_words swaps real standalone words -> only edge-touching words.
- [b] 2 two reads = same brain; like>=0.8 lets misspellings through -> OCR agreement; exact match.
- [d] 2 MARKS "+/-" battery; "™M" strip; top="plus".
- [a] 2 skin.py:200 second photo rolled exactly 180°, no registration (mosaic.register dead) -> register by print.
- [d] 2 skin.py:196 other_side 0.10 tuned on one Duracell.
- [a] 2 mosaic.py:38 re-exposes every photo to 0.9 -> measured colors drift -> white balance on neutral / raw for sampling.
- [b] 2 delighting only smooth shading; glare/hard shadows stay.
- [d] 2 layout prompts: "metal ends, plus button", copper #b87333 default, base_bands assumes bands.
- [b] 2 color_check families lump copper/gold/tan/orange/brown; 20x10; >90 -> finer families/hue.
- [b] 2 labelart.py:143-145 whole bbox resized to letter height distorts; load_default tiny font fallback.
- [a] 1 fixed roughness 0.45/0.3; no height/normal for raised print.
- [b] 2 run.py:1055 passes with no tries; 1016/1021 can never fail; None counts as not-False in label_passed.
- [b] 2 final 4096 px render never re-checked.

## 5c box/flat
- [b] 3 skin.py:450/473 fixed fallback crops used as "the real logo/picture" on unseen sides -> find by matching; else plain.
- [b] 3 panels.brand_panel / eraprint.panel_notes invent layout, 2.2 mm type, placement on unseen sides -> measured paper color + receipted facts in a sister's layout, else blank and flagged.
- [b] 2 skin.py:585-588 pick shape off >20% "used anyway" -> flag catalog size.
- [a] 2 quad->side by heuristics; rotated photos -> rotated panels; OCR hides it.
- [b] 2 Real-ESRGAN invents letter shapes; text check fuzzy 0.85.
- [a][d] 2 box.py:80-84 tuck-lid flap on every card box; open geometry skips volume.
- [b] 3 box.py:139 no extras, no material_kind, no physics.json; names end _print so measure skips -> box route zero material checks.
- [b] 2 finish.box_atlas bakes invented "cracked ink" and seam lines; carton.py:110-113 same.
- [g][b] 2 atlas black fill, no padding; bevel across UV seams -> dark streaks.
- [b] 2 eraprint UPC single_source accepted then verified against itself; UPC-A only.
- [d] 1 US FDA layouts + fixed footnote text.
- [d] 2 magenta mask erases magenta/pink print (measure.py:197/129).

## 5d carton
- [d] 3 carton.py:263-288 Pop-Tarts pouch/pastry/sprinkles hard-coded; KeyError for any other contents -> contents as generic parts from the dossier, colors measured.
- [a] 2 board thickness/flaps/inside colors handbook constants.
- [b] 2 layered flaps leave open edges unchecked.
- [b] 1 lid art rotate 180 by assumption.

## 5e pcb
- [a] 3 PARTS_Q asks heights from a straight-down photo; KIND table defaults -> side photos / kit package heights; flag unknown.
- [b] 3 board_parts exception -> []; 0 parts never fails; parts not kept -> keep; gate.
- [d] 3 pcb.py:197-217 bracket always -> only when photos show one.
- [b] 3 invented solder traces when no photo -> plain measured mask color + flag.
- [a] 2 fixed thickness/colors; electrolytics as bare aluminum (false materials failure).
- [b] 2 board top texture = raw photo with parts' sides/shadows baked.
- [b] 1 overlapping parts / past outline unchecked.

## 5f assembly
- [a] 3 all geometry from one brain answer (parts.py:228) -> boxes/outlines from segmentation masks scaled by measured size.
- [f] 3 ASK invites internals no photo shows; biased examples.
- [b] 3 assembly.py:410-412 "could not be built" flagged only.
- [b] 2 parts.clean silent defaults (shape, material, color 0.5, metallic rounding, size 0.1).
- [a] 2 measure_colors no white balance; brain color kept within 0.08.
- [b] 2 print = raw crop stretched; cylinder side_uv sliver.
- [b] 2 lathe placement inconsistent (clean clamps to object H; assembly offsets again).
- [b] 2 tubes open ends, no UVs.
- [b] 2 realmat.fit clamps into the same ranges measure checks -> cannot fail.
- [a] 1 looks.py procedural.

## 5g Hunyuan
- [c] 3 run.py:1796 textured.glb kept with no key -> key on reference sha + hunyuan.py sha.

## 6a exact checks
- [b] 3 holes never checked (open/non-manifold computed, never read; volume skipped when open) -> fail outside parts with open edges.
- [b] 3 UVs never checked (presence, overlap, flip, stretch, range) -> per-part UV check.
- [b] 2 inside-out = one signed volume per part -> per-island normals.
- [b] 2 parts interpenetrating unchecked; label vs shell.
- [b] 2 text_found: no-letters passes; 4-rotation soup; fuzzy 0.85; long text 85% any order.
- [b] 2 unreadable reference elements skipped (logos never checked).
- [b] 2 barcode: none when dossier lists no face.
- [b] 2 materials: brightness only vs wide ranges; unknown kinds skipped; channel wiring ignored; img_mean over unused atlas; sRGB vs linear; first BSDF only.
- [b] 2 unprinted faces only "not empty".
- [b] 1 inside_fit only flagged parts; fixed seed.
- thresholds: SIZE_TOL 0.03 (pcb/flat drop thinnest side); SHOW_THROUGH 0.002; blank 0.02; var 6; fuzzy 0.85; degenerate max(20,1%); spikes p99x1.6; viewer std<4.

## 6b judge
- [b] 3 judge.py:126-127 faces without a render skipped silently; renders without a face never judged -> fail unjudged.
- [b] 2 191 trusts v["pass"]; inventory counts ignored -> pass computed in code.
- [f] 3 TIEBREAK burden on the fail; overrides -> another full look; 2 of 3 passes required.
- [f] 2 Q never asks color/size/proportion; "missing them is never a fault" loophole; nothing-listed faces have nothing to fail.
- [b] 2 PRIMARY_FACE lacks "assembly"; must cut to 60 chars.
- [b] 1 reference crop from a brain box.

## 6c inspect
- [b] 2 all 8 checks from one 1024 px call; [f] 2 "slight wear" invites invention; materials/layers item examples; [c] 2 check_version counts checks only.

## 6d review prompts
- [f] 2 LOOK_Q battery words; FACES_Q six sides used for pcb; [b] 2 None never fails; [b] 2 not_on_item prefix/suffix drops real words.

## 7 keeps
- [c] 3 kept.pic_sig gray square-squashed: color-only or aspect change reads same -> RGB at native aspect.
- [c] 2 QUESTION_VERSION hand-bumped; passes never expire.
- [c] 3 label_kept key misses model, w/h, typical, marks, cover, product, review.py, fonts; survives Redo.
- [c] 2 words key misses prompts/OCR engine; labelparts key misses models/photos/kits.
- [c] 2 file_away not tied to the verdict that passed.
- [c] 1 skin.face keep unkeyed (dead).

## 8 time
- [e] 2 look_unrolled, look_faces, logo_box, photo_box every build, informational -> key on bytes+model.
- [e] 2 parts.plan and board_parts re-asked every build -> keep on (photos, size, prompt, model).
- [e] 2 same_design without dossier up to 8 calls -> key.
- [e] 2 measure.read_text re-OCRs references every build -> keep by sha.
- [e] 2 label redone when only non-label checks failed -> keep when its own checks passed.
- [e] 1 renders repeat (lit+unlit, preview+viewshot); exports in TRIAL; make_room swaps.

## 9 deliverable (by route)
Round: label UV ok, other parts planar top-down (stretched), inside parts none. Box/flat: one mesh, atlas, no physics. Carton: ok + physics.
PCB: parts default overlapping UVs; no mr maps. Assembly: box parts overlapping 0..1 per side; color-only materials; looks only. Hunyuan: baked light, no PBR.
- [g] 3 box/flat no physics.
- [g] 2 not reskinnable: inside parts no UVs; overlapping UVs; color-only materials; uv/ skips parts silently.
- [g] 2 material model differs by route; no AO/height; glass opaque.
- [g] 2 tiling scale lost in .mtl/.ma/.3ds; map_Bump non-standard; no DirectX normal.
- [g] 2 deliver.verify never re-imports (bbox/scale/UVs/materials).
- [g] 2 texture names inconsistent -> <asset>_<part>_<map>.
- [g] 2 no clean unbranded set, no LODs/collision.
- [g] 1 half the atlas wasted.
