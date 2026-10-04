# Audit report 1 - card, era version, hunt, rank/pick, family, kits/kitmaker, dossier, facts, label parts, label words
Format: [tag] severity - file:line - problem -> fix. Tags: [a] guessed where measurable, [b] uncaught failure, [c] stale cache,
[d] item-specific, [e] time, [f] prompt quality. Severity 3 = produces a wrong asset silently. (Lines as of commit 3040def.)

## Cross-cutting
- X1 [b] 3 - run.py build()/review.py: the review sheet gets steps only from build(); nothing from card, era, hunt, rank, pick, family, identity, facts or dossier gaps. dos["gaps"] read only by catalog.py and deliver.py. An upstream mistake is self-consistent and passes. -> a sheet step per upstream stage with checks; every dossier gap a check.
- X2 [b] 3 - dossier.py:524 `match = "exact"  # your pick is the item, by definition`: the pick is never checked; an auto-pick becomes ground truth. -> the careful look records its own match for the pick; disagreement flagged.
- X3 [b] 3 - run.py:1128/1146 auto-pick lead with one candidate = whole score; a lone photo with seen>=3 auto-picks. -> need 2+ candidates; marks by name.
- X4 [a][b] 3 - cards.py:116 size default [0.1,0.1,0.1] flows into every stage and passes measure_size against itself. -> stop with "no catalog size".
- X5 [b] 2 - cards.py:105-111 `except Exception: pass` around portal.catalog_entry -> log and stop.

## Stage 0 card (cards.py)
- C1 [c] 3 - 128-129 card keyed on cid only (catalog/ASK/model changes never remake it) -> hash (catalog entry, ASK, model) on the card.
- C2 [a] 3 - 35 "label_reads" around/along is a memory guess deciding label orientation (run.py:525-541) -> measure from the pick's OCR at 0/90 or take from the kit.
- C3 [a] 2 - 34 "standing" guessed -> measure from the mask's long axis.
- C4 [b] 2 - 138-141 only "route" validated; "standing"/"label_reads" unvalidated -> validate.
- C5 [a][b] 2 - 121-123/140 year from a regex on the product name ("2000 Flushes") -> catalog field; flag no year.
- C6 [b] 2 - 136-137 no-JSON crash; missing keys silently empty -> require keys, stop with reason.
- C7 [b] 2 - 77-79 construction failure returns {} unrecorded; num_predict 1200 invites truncation -> on the sheet; bigger budget.
- C8 [b] 2 - 81-82 unknown material coerced to molded_plastic -> re-ask or flag.
- C9 [c] 1 - 65-66 construction reused forever -> key it.
- C10 [d][f] 1 - 42-45 battery-first examples in BUILD/DETAILS prompts -> neutral.
- C11 [f] 2 - 36-37 recognize/avoid from memory, no evidence -> ask for the source; unverified until an era photo shows them.

## Stage 0b era version
- E1 [a] 3 - cards.py:226-228/vet.py:210-211 names from memory injected into every photo judgement -> keep a name only with web/evidence support.
- E2 [a][b] 3 - run.py:1198 era_evidence takes match>=4 (other versions count) and ERA_Q calls it "better than memory": circular -> match>=7 and kind photo.
- E3 [c] 2 - cards.py:204-206 never re-asked once evidence exists; key lacks product/model/prompt -> compare evidence, product, model, prompt version.
- E4 [f] 2 - 155-156 asks memory for exact printed names without citing a snippet -> cite.
- E5 [b] 1 - 170-172/187 no web -> pure memory unflagged -> record "no web evidence".
- E6 [d] 1 - 176-177 "vintage {toks[0]} {toks[2:]}" assumes Duracell-shaped names -> brand from identity.

## Stage 1 hunt
- H1 [b][c] 3 - google_images.py:98-101/140-141 captcha -> (None,None) -> 0 photos recorded as a done search; dossier marked done -> raise on captcha; don't record.
- H2 [c] 2 - run.py:235 found.json reused without checking the searches that made it -> store the searches; hunt the missing.
- H3 [e] 1 - hunt.py:204-207/222-231 no search cache; failed downloads retried every run -> cache per (query, date); negative cache.
- H4 [b] 1 - hunt.py:226-231 silent drops -> log counts.
- H5 [d] 1 - hunt.py:176-187 brand = first word (dead path) -> remove.
- H6/H7 [b] 1 - substring heuristics in words_ok / source by URL substring.

## Stage 2 rank (vet.vet, run.rank)
- R1 [c] 3 - run.py:242-261 vetted.json reused per path; not keyed on recognize/avoid, model, ASK, product, year -> key each vet on (photo sha, model, ASK hash, marks hash).
- R2 [b][c] 2 - vet.py:218-219 error -> {"match":0} saved as a real vet; the photo is sunk forever -> don't save failures.
- R3 [a] 3 - vet.py:149-150 "seen" is an unverifiable count driving rank and auto-pick -> list marks by name; count only names in recognize.
- R4 [a] 2 - vet.py:143-145 made_year "subtract shelf life" invites guessing -> printed years only; flag estimates.
- R5 [a] 2 - run.py:275-279 quick-model scores on the same scale as careful ones; never re-looked -> provisional; re-look before showing.
- R6 [b] 1 - magic caps [:60], careful=6, [:24] -> on the sheet.
- R7 [f] 2 - vet.py:140-141 one 0-10 "match" mixes identity/version/era -> separate booleans + evidence.
- R8 [e] 2 - every photo looked at twice (vet ASK, then QUICK_Q/LABEL_Q) -> share looks keyed on (sha, model, prompt).

## Stage 3 pick
- P1 [a][b] 2 - run.py:1184-1189 size_fits ±35% against ANY pair of dims; failure overridden by brain count -> tighten; per-view dims; no override.
- P2 [b] 1 - thresholds 800 px, "*16 bytes" -> record on the sheet.
- P3 [b] 1 - run.py:1624 shown[int(pick)-1] unchecked -> validate.

## Stage 4 family
- F1 [b] 3 - families.py:108-114 low confidence promoted to 6 because a kit got written -> keep the confidence.
- F2 [a] 2 - self-reported confidence, threshold 6 -> ask twice / second model; agreement as confidence.
- F3 [c] 2 - 91-93 cache key misses notes, model, menu, product, ASK -> hash them.
- F4 [f] 2 - 36 kind_name "as exact as the photo allows" splits kits per product -> generic kind noun matched against existing kits first.
- F5 [f] 2 - menu unbounded -> cap/group.
- F6 [a] 2 - is_package vs identity.kind never compared -> flag disagreement.
- F7 [b] 1 - unknown family -> general silently -> log.
- F8 [b] 2 - family_library.json judge_notes/facts/checks/_checks_all read by nothing -> wire or delete.
- F9 [d] 2 - cylindrical_cell typical "a PowerCheck strip with test dots" (brand-specific); size pattern misses C/D; voltage pattern matches "9V" from a neighbour -> fix patterns; drop brand typicals.
- F10 [d] 2 - only cylindrical_cell has expect lists; others show a pass that never ran -> None when no list.
- F11 [d] 1 - "no bare steel ring" note untrue of every cell (unused).

## Stage 5 kits
- K1 [a] 3 - kitmaker.py:141-153 web sizes kept without the numbers appearing in the snippet; they override the catalog size -> keep only with numbers in the source text.
- K2 [a][b] 2 - 51/117-121 expect regexes from memory, only compiled -> test on the item's confirmed words before keeping.
- K3 [b] 2 - 172-176 bad material silently substituted -> re-ask or reject.
- K4 [b] 2 - 85-97 _route heuristic on free text -> ask route as enum; check vs zones.
- K5 [c] 2 - 196-202 kit keyed on kind+VERSION only -> add model, prompt, materials hashes.
- K6 [e] 2 - failed study not cached; tries=2 at temperature 0 repeats -> cache failures; retry on exception only.
- K7 [b] 2 - run.py ensure_kit: product-name fallback makes a kit per product; family changed without updating route/recipe/dossier -> rerun classify bookkeeping or invalidate.
- K8 [b] 2 - kits.py:27-38 `except: pass` drops every learned kit silently -> log and stop.
- K9 [b] 2 - kits.py:46-56 single-letter variants "C"/"D" match "Vitamin C" -> require size context.
- K10 [b] 1 - variant_default alphabetical -> none.
- K11 [d] 2 - GENERIC_ELEMENTS (nutrition left, UPC bottom) applied to every package -> per kit.
- K12 [a] 1 - C/D button height = AA's -> flag estimate.

## Stage 6 dossier
- D1 [b] 3 - 978-990 ensure() turns any exception into an empty dossier; build continues -> stop or failing check.
- D2 [b][c] 3 - 970 done = bool(use) even when identity/hunt/looks failed; reused forever -> done only when complete.
- D3 [c] 2 - 196-206 inputs miss models, prompts, family_lib, owner note, pick bytes, new photos -> add.
- D4 [c] 2 - 881-896 version bumps re-look only round items by hand rules -> prompt version per look.
- D5 [b][c] 2 - 424-437 quick-look exception stored as "none" forever; not keyed -> don't store; key.
- D6 [a] 2 - careful looks gated by one fast brain's same_line -> second opinion for high useful.
- D7 [b] 1 - MOST_LOOKS 12 < 13 for a box -> cap = len(FACES)*LOOK+1.
- D8 [b] 2 - 238-239 box scale guess (>1.5 -> /1000) -> use image size when >1000.
- D9 [a] 2 - 514-516 turn/straight_on/edge_on from the brain -> measure turn by OCR at 4 rotations.
- D10 [b][d] 2-3 - 540-541/650-651 NOT_PRINTED lines become overlays with box None, covering every face; modern packages print emails -> keep printed lines unless the look called them overlays; use the box.
- D11 [b] 2 - 580-581 unmeasurable shape passes template check -> fail for copying.
- D12 [a] 3 - 689-691 same_artwork sister accepted on the brain's word -> measure artwork similarity (phash/features of the label region).
- D13 [b][d] 2-3 - 590-594/614-622 KIND_OF "count" matches net weight; food words -> own kind; neutral words.
- D14 [d] 2 - 57-66 box hunt words "nutrition facts"/"barcode" for every box item -> per family.
- D15 [d][f] 1-2 - Pop-Tarts examples in ID_Q/QUICK_Q -> neutral.
- D16 [a] 2 - 296 food = one brain answer -> cross-check kit.
- D17 [b] 1-2 - parse_years takes only the first decade -> all decades.
- D18 [b] 1 - text[:60] silent truncation -> log.
- D19 [d] 1 - narrow-side twin logic carton-specific -> kit elements.
- D20 [b] 2 - 1024-1029 cut-out failure only logged -> sheet.
- D21 [e] 2 - run.py:200/475 DS.ensure called twice -> pass through.

## Stage 7 facts
- FA1 [b][c] 2 - 285-290 panel exception stored {} forever; not keyed -> don't store; key.
- FA2 [b] 2 - 219-225 zxing missing -> [] silently -> sheet.
- FA3 [a] 2 - upcitemdb/barcodespider/buycott mirrors counted independent -> one source.
- FA4 [b] 2 - 476 "size_on_pages_matches_photo" compares nothing -> compare.
- FA5 [a] 1 - identity read counts as a photo source -> mark single.
- FA6 [d] 2 - 71-72 count regex knows pastries/batteries only -> generic with identity.unit.
- FA7 [d] 2 - 693 "per pouch" query -> "per pack".
- FA8 [d][a] 2 - 729 folding_carton packing fallback for any packaged item -> own family only.
- FA9 [a][d] 2 - 762-768 magic contents numbers -> on the sheet.
- FA10 [b] 1 - GS1 prefix 6 digits only -> 6-10.
- FA11 [f] 1 - PANEL_Q US/Pop-Tarts examples -> neutral.

## Stage 8 label parts and label words
- L1 [a][b] 3 - labelparts.py:58-61 sister counts as "ours"; its lines added to the label -> exact or measured same-artwork only; check model/size words vs kit variant.
- L2 [b] 3 - 50 era ±6 years window -> era span.
- L3 [a][b] 3 - 150/run.py:1009 read() on the whole photo (neighbour items' text) -> item cutout only; 2 photos.
- L4 [c] 2 - run.py:1001 labelparts key misses photos, expect, models, hunt outcome -> add; don't keep failed hunts.
- L5 [b][d] 2-3 - 1015-1018/labelparts.py:136-139 missing parts never fail; no-expect kinds show a pass -> None without list; False when missing.
- L6 [b] 1 - DATE pattern matches any year -> context.
- L7 [b] 3 - run.py:885-889 fuzzy 0.8 confirms "MN1504" by "MN1500" -> exact for digit tokens.
- L8 [a] 2 - two reads = same brain; OCR silently [] -> OCR agreement for numbers; flag no OCR.
- L9 [a][b] 3 - 990-996 must_show texts bypass the two-read rule -> confirm them too.
- L10 [c][b] 2 - words key misses prompts/OCR engine; stores reduced sets on partial failure -> add; keep only complete.
- L11 [b] 2 - whole_words swaps real standalone words; TM-letter strip -> only edge-touching words; drop strip.
- L12 [c] 2 - label_kept key misses model, marks, typical, w/h, judge version -> add.
- L13 [b] 1 - overlay check hard-coded True -> real or removed.
- L14 [e] 1 - same_design/look_faces/look_unrolled not cached -> key on shas.
- L15 [d] 1 - top="plus" for cylindrical_cell; families.json AA master hard-wired -> kit declares.

## Notes
- Most common silent failure: a failure cached as an answer (R2, D5, FA1, H1, L10, L4).
- Most common stale cache: key missing model and prompt version (C1, R1, F3, K5, D3, FA1, L10, L12).
- Biggest guesses: label_reads (C2), "seen" count (R3), era names (E1), kit sizes (K1), same_artwork pixels (D12), label parts from sisters/whole photos (L1, L3), fuzzy digit confirmation (L7).
