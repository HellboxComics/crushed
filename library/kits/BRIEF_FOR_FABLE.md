# BRIEF FOR THE NEXT ENGINE (Fable) - the asset maker, as of 2026-10-03 17:00 Central

Read this, then kits/DESIGN.md (the redesign and its Status), then playbook/playbook.md (what Cody's AI is told).

## Who and what
- Cody (persona Harrow; firefighter; NOT a developer). Project: crushed.buzz. Every catalog item (2,668, list in
  assets/plan/items.json, order in library/queue.txt) must become a production-quality, real-size 3D master asset,
  made by HIS LOCAL AI on his Mac (M4 Max, 128 GB; Ollama brains; ComfyUI "drawing room"; Blender; Hunyuan3D).
- Your job is SETUP and WORKFLOW only. "YOU DON'T FUCKING TOUCH MY ASSETS. YOU GIVE MY AI THE LOGIC AND REASONING."
  Never hand-make or hand-fix an asset, never feed Cody's own photos in ("giving you that image would nullify my
  efforts" - he shows photos only as evidence of what's missing).
- His end goal (today): "take any item prompt or image, and turn it into a perfect 3d object without your input or
  mine, while being self aware enough to see its own output, realize what is wrong, and correct it on its own."
  So every bug you fix by hand must ALSO become an automatic step check + a playbook lesson (see Self-review).

## Standing rules (from Cody; breaking them makes him furious)
- Talk to him at a 6th-grade level: short words, no jargon (if you must name a thing, say what it is in the same
  sentence). American spelling. Brief. He's often on his phone.
- Don't ask him engineering choices - decide the best, most efficient setup and do it. Ask only product rules,
  money, or things only he knows (batch questions).
- Redesign, don't patch; fix the whole CLASS of a bug in one pass; data first (read the real log/artifact) before any
  theory; never blame his AI or Mac before auditing your setup; LOOK at results (stage the pictures) before saying
  anything about how a build looks.
- Never delete his files (move to ~/Desktop/_to delete with a note). No money spent, no accounts made, no CAPTCHAs.
  His real name/location never on public surfaces. Local AI first.
- Git: commit in /home/claude/crushed, push `git push origin HEAD:claude/epic-galileo-iubypk`; commit messages end
  with the two attribution lines (Co-Authored-By / Claude-Session) given in the session's system reminder.

## How the machine works (reaching it)
- Repo on the Mac: ~/crushed-render/repo (library/ is the asset maker). Work dir: ~/crushed-render/remaster
  (library/<item>/ = each build: texture/, check/, measure/, model/, review.json; hunt/<item>/ = photos;
  dossier/<item>.json). Log: ~/crushed-render/library.log. Status: remaster/library/status.json.
- From this cloud container you reach the Mac through the device tools (a Linux VM with the folders mounted at
  $HOME/mnt/{crushed-render,.hellbox,Desktop,...}); you can't run Mac programs. You steer by files and git:
  - push code -> the Mac pulls it; the run restarts on new code BETWEEN items ("[update] restarting between items")
  - restart now: write remaster/restart.request (the watchdog kills the run; the clock restarts it within 5 min,
    self-test first ~4 min). Stop: a PAUSE file in remaster/.
  - the clock (~/.hellbox/ai/crushed_library.sh, every 5 min): watchdog -> git pull -> run.py --loop --queue 3.
- Stage files to look at them: device_stage_files -> /mnt/user-data/uploads/... then Read the PNG/JPG.
- Tests: copies in library/tests/ (run.sh runs them all; they expect the fixture work dir mine_work/ that lives in
  this session's scratchpad - if the scratchpad is gone, point CRUSHED_REMASTER_WORK at a fresh copy of real Mac
  data). Every change today ran the full suite green. Always run it before pushing.
- The brain server (Ollama) is SHARED with Cody's other tools (~/.hellbox/ai); they ask long questions and load big
  brains. His "testlock" rule: while one of his brain tests runs, nothing else may use the brain server.

## What happened today (26 commits, 937ac8d..HEAD - read the messages)
- Kits redesign (kits.py, family_library.json): trusted variants (name or catalog size), AA/AAA/C/D cell templates
  from the measured AA master, 12 oz can size + CMI lid, carton zones with what each side carries; lathe faces
  oriented by the outline (an AAA threw 100 mm spikes before).
- ownmods.py: the asset maker's own files always win - Cody's suite has its own facts.py/dossier.py and tools that
  push their folder to the front of Python's search list; every dossier was failing. Self-test piece guards it.
- Brain exam (brainjobs.py): judge = qwen3.8:27b-q8_0, sort = qwen3.5:122b-a10b (from the photo exam).
- Round labels, end to end for the first time (run.round_label): close-ups placed by scale at the end they show
  (mosaic.placed); words read twice off strips AND the photos themselves; cut-off words made whole; the dossier's
  printed lines allowed; the writer gets the comparison's fixes; numbers kept in range; words fit their panel;
  plain ink over metal is not metal; the colors MEASURED against the real label (layout.color_check - the look said
  "match 9" for a label drawn all black).
- Self-review (review.py): every round-label step and the box sides write their work + their own checks to
  review.json; the engineer gets the sheet and starts at the first step that went wrong.
- labelparts.py: the label checks itself against what every label of its kind carries (kit zone "expect") and
  hunts the missing parts in more photos (own photos first, then targeted searches), read twice, with receipts.
- Retries: a stopped/failed item is retried as soon as newer code arrives. Self-test no longer fails because the
  shared brain server is busy.

## Where it stands right now
- Duracell (the proof item; Cody picked a real 90s PowerCheck photo p2db7abb9ae2a): build 6 running (~22:00 UTC).
  Build 4 got every exact check but lost its copper top (caught by the final judge; now measured). Build 6 found
  SIZE AA, ALKALINE 1.5 Volts, MN1500, LR6 in other photos; still missing: the caution line and "Made in U.S.A.".
  LOOK at check/viewer_around.jpg + viewer_close.jpg + texture/round*.png + review.json when it finishes.
- Next in queue: Pop-Tarts (Cody's note: build the BLUE box design; no good blue 90s box photo found yet - it may
  need his pick on the phone), Canada Dry 12 oz can (kit size + lid; pull tab missing), Furby (old one-photo
  Hunyuan route, looks bad - the plush-toy redesign plan is in DESIGN.md "Soft and molded things").

## Next work, in order (hardest/most valuable first)
1. Finish the Duracell to PERFECT, entirely by Cody's AI. Known gaps:
   a. labelparts: the "same_line" filter is too loose (a Mallory mercury battery photo was read). Require the
      product line/version (e.g. PowerCheck AA) - use the dossier's careful look (match exact/sister) or a name match.
   b. Era marks as expectations: the era version (cards.era_version "marks": "PowerCheck tester strip", "white test
      dots", "PRESS DOTS TO TEST") should join the kit's expect list for that item, so the label insists on them.
   c. Caution / Made in still missing: better targeted queries (e.g. "<brand> <line> battery wrapper", "battery label
      text"), and read flat/peeled labels found in the hunt first.
   d. Strongest redesign idea for label art: build the BASE layout by MEASUREMENT (color bands along/around from
      real.png + real_seen.png - copper end, black body, panels), then let the AI only place words and small marks.
      That removes the "drew it all black / copper at the wrong end" class entirely. The color check stays as the gate.
2. Prove the box kit on Pop-Tarts and the can kit on the Canada Dry can (end to end, review sheet green, LOOK).
   Can pull tab: measured by the AI from a top photo relative to the 54.1 mm lid, built as its own part.
3. Self-review for every route (pcb, assembly, organic) + an exact "render looks like its layout" check.
4. Plush/figure redesign (DESIGN.md): erase tags/hands (drawing room) with a nothing-else-changed check;
   multi-view shape; parts (eyes, beak, feet) as solids; fur as a material with the photo's light taken out.
5. Media kits (sizes researched with sources in kits/media_dimensions.md): CD + jewel case, VHS, cassette,
   cartridges (90 / 75 / 69 / 58 catalog items).
6. Later (only after assets are perfect and kept): the marketplace lane and the BuiltInside brand (DESIGN.md).

## Scheduled check-ins already set in this session
- "Check Duracell 5th build" fires 22:06 UTC (it's really build 6 now). Handle it: read the log + review.json, LOOK,
  fix setup bugs, tell Cody plainly.
