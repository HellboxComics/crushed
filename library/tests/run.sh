#!/bin/bash
cd /home/claude/crushed
for t in test_labelparts test_round_label test_review test_compose test_ownmods test_prompts test_layout test_kits test_brains test_units test_render test_dossier test_build test_swap test_routes test_pipeline; do
  timeout 900 python3 "/tmp/claude-0/-home-claude-crushed/db81eea7-ef8c-55dd-b827-ea6e2d91f37e/scratchpad/maintests/$t.py" > "/tmp/claude-0/-home-claude-crushed/db81eea7-ef8c-55dd-b827-ea6e2d91f37e/scratchpad/maintests/$t.log" 2>&1
  echo "$t exit=$? : $(tail -1 "/tmp/claude-0/-home-claude-crushed/db81eea7-ef8c-55dd-b827-ea6e2d91f37e/scratchpad/maintests/$t.log")"
done
cd /tmp/claude-0/-home-claude-crushed/db81eea7-ef8c-55dd-b827-ea6e2d91f37e/scratchpad/maintests/eng
for t in test_engineer test_run test_watchdog; do
  timeout 1200 python3 $t.py > $t.log 2>&1
  echo "$t exit=$? : $(tail -1 $t.log)"
done
