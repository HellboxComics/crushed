# Audit report 3 - the engineer loop, acceptance, retries/queue, watchdog, portal, keeps, prompts
Severity 3 = the engineer cannot succeed on its own, or work is lost / a check can be weakened. (Lines as of commit 3040def.)

## 1 Safety of the lane [e]
- 3 run_fingerprint freezes only lines mentioning CHECKS/inspect/verdict/measure/judge: `failed = ... + j["failed"] + looked_failed`
  (run.py:439) can drop j["failed"]; dos_now (416), version_marks (394-402), route_of_card can be gutted - NOT CAUGHT -> freeze check_model, version_marks, route_of_card.
- 3 majority of three: F1,F2 from the engineer's code outvote Fp (engineer.py:1708-1709) -> Fp is a veto; majority only between F1/F2.
- 3 kept.py unlocked but holds the verdict cache; test builds write passes into the shared WORK/kept -> lock kept.py; isolated kept store per trial.
- 2 cards.py, kits.py, layout.py unlocked yet feed the judge/checks (CHECKS prompt text, typical, color_check) -> lock cards.py; split color_check into review.py.
- 2 deliver.py/exports.py unlocked (file into the owner's library) -> lock deliver.py.
- 2 _root_watch misses WORK/kept, kits/learned.json, hunt/<item> -> watch them.
- 1-2 LOCKED_NAMES lacks `hart`; _shadows only checks find_spec now -> reserve suite names.
- 1 brainjobs.py:204 exec of model output -> sandbox/ast-only.
- Nothing deletes owner files (moves only).

## 2 What stops the engineer [a]
- 3 time budget: reserve = min(90 min, 3.5*longest+300); rebuild needs left >= reserve+longest -> with 20-min builds, test builds only in the first 85 min; 40-min: one build per session; MAX_REBUILDS unreachable; playbook rule 3 impossible.
- 3 cannot test one step; only a full production rebuild incl. finish_files/exports/preview/viewshot/judge -> a test_step tool (one function or one Blender builder on a spec).
- 3 brain choice by name only; exam is 3 text questions (no tool calls/vision); fastest coder wins; a brain without tool support dies on turn 1 and the attempt is spent -> exam tool calling; refund.
- 3 `clear` not in _diff_hash; "Same code as before" caches machine failures -> clear in the key; never cache machine failures.
- 2 cannot read the dossier/card; first message lacks verdict["measure"]/["sides"] numbers -> readable; numbers shown.
- 2 crashed rebuild: cur not updated, 40-line tail, a rebuild spent -> show the crash build.
- 2 compare_colors unaligned 20x10 on render vs photo; ask_eyes one picture only; no UV/texture-region view -> two-picture ask_eyes; per-part UV view.
- 2 blind coder: 150-word descriptions; can_see True on error; playbook says "you have eyes"; no zoom.
- 3 STEP_FILES points at locked files (dossier.py, labelparts.py); playbook contradicts locks (family library); review.py/kitmaker.py locked.
- 2 ROUTE_FILES wrong/missing (mosaic, unwrap, kits, looks, parts for round) -> neighbours miss regressions.
- 2 risky() refuses setattr/sys.path/os.environ/".git"(matches .github)/"lessons"/"playbook" strings - builders already use these.
- 2 proven fix cannot be got back (sure=true reverts the whole file; proven diff unsaved) -> `restore_proven` tool.
- 2 never told its budget (time, rebuilds, turns).
- 2 context: 64k; 16k tool results; old results cut to 600 chars -> re-reading; read_file 400-line cap on 2600-line run.py; nudged never resets; think can eat the whole num_predict.
- 2 clear keys coarse ("parts" deletes parts.json not parts_plan.json); words key no code; label_kept keyed on two files only.

## 3 Acceptance (_accept/_keep) [b][c]
- 3 proven fix lost when time runs out after a later edit (engineer.py:1788-1789 tests the CURRENT diff) -> restore proven code at the end.
- 3 neighbours use _fails not _fails_of: "not_judged" counts as a NEW failure; one look decides; compared with stale status verdicts.
- 3 reserve too small for confirm + own check + 2 neighbours -> "out of time" blamed on the fix and cached.
- 2 a neighbour with no pick is blamed on the fix.
- 3 "same code same answer" and the confirmation are not independent: the kept-pass cache replays trial 1's passes; parts.plan/label rounds re-ask the brain so "same code" is not the same model.
- 2 own check uses the real dossier/card over the test build's (clear "dossier" lost; card keys dropped; owner note missing in trials).

## 4 Silent failures, stalls, lost work [b]
- 3 portal: every handled path `continue`s past _save(DONE) -> replies repeat, notes rewritten (re-queue, attempts reset, repick wipes the pick) -> save per message.
- 2-3 engineer OFF unless settings.json has engineer:true (run.py:2003) with no log -> default on.
- 2 kept fix dropped by the next sync (rebase fails -> engineer-kept-* branch + reset --hard); status still says "fixed".
- 2 lessons lost when a fix stays on a branch (appended before the "code moved" return).
- 2 watchdog heartbeat beats whenever ComfyUI answers -> stalls never caught; without ComfyUI a 40-min _chat is killed.
- 2 machine failures spend the 3 daily attempts (step-aside, brain failure, worktree error).
- 2 one judge error ("could not inspect") blocks the engineer from real exact failures for 6 h.
- 2 killed session: stale "fixing" status (not parked), edits in scratch unreadable, watchdog idle check fooled.
- 2 step-aside on the last item: no sync until quiet-quit; stuck sync -> 6 h wait.
- 2 kept items not re-checked when checks get stricter: pipeline files any item with a "keep" approval straight away.
- 1-2 PAUSE ignored mid-item; --only ignores RESTART; clock's git pull (unverified) bypasses the rebase logic.
- 2 portal errors swallowed (no reply).

## 5 Stale / inconsistent [c]
- 2 engineer attempts keyed by commit time; retries by sha; rebases restamp.
- 2 check_version counts checks only.
- 2 lessons.md cut to 6000 chars; rejected global, last 3000.
- 2 two writers of lessons.md/playbook (engineer local commits vs upstream) -> rebase conflicts drop kept fixes.
- 1-2 picks.json/approvals.json/cards written without locks by several programs.
- 1 self-test kit study instant after first; exam key lacks content.
- 1 material values disagree (playbook sRGB vs lessons linear; steel ranges).

## 6 Efficiency [d]
- 2 each test build is a full production build (exports, copies, kit gate, parts plan); confirm rebuilds everything; own check re-renders.
- 2 after a kept fix the item is rebuilt again + full self-test.
- 2 every failed item retried at once after any push (wait=0) -> 3-h sessions for unrelated changes.
- 2 model reloads: engineer num_ctx 65536 vs judge 32768; _release before each test build.
- 1-2 neighbour tests too often, sequential; describe one picture at a time.
- 1 real builds always run the judge (no fail fast).
- 1 disk grows (trials, scratch).
- 1 think=True retried without on every turn for brains that can't think.

## 7 Prompt/playbook [f]
- 2 rules vs permissions contradict (hand layouts offered; family library advice vs locks; "all must come out the same" outdated).
- 2 playbook assumes eyes and one change per rebuild the budget can't give; nothing on working through ask_eyes.
- 2 failure names inspect/sides/not_judged unexplained.
- 2 lesson format weak (no route/file:line/numbers/sha); dead-end lessons committed with kept fixes; rejected entries lack the hypothesis.
- 1 Duracell-specific examples in the playbook; "Start by looking" vs "start at the first failed step".
