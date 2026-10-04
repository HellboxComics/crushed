#!/bin/bash
# Every test of the asset maker, from this folder (the fixture work dir is CRUSHED_TEST_WORK, default: the session
# scratchpad's mine_work copy of real Mac data).
HERE="$(cd "$(dirname "$0")" && pwd)"
cd "$HERE/../.."
for t in test_kitmaker test_portal test_labelparts test_round_label test_parts test_review test_compose test_ownmods test_prompts test_layout test_kits test_brains test_units test_render test_dossier test_build test_swap test_routes test_pipeline; do
  timeout 900 python3 "$HERE/$t.py" > "$HERE/$t.log" 2>&1
  echo "$t exit=$? : $(tail -1 "$HERE/$t.log")"
done
cd "$HERE/eng"
for t in test_engineer test_run test_watchdog; do
  timeout 1200 python3 $t.py > $t.log 2>&1
  echo "$t exit=$? : $(tail -1 $t.log)"
done
