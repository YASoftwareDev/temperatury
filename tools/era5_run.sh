#!/usr/bin/env bash
# Launch (or RESUME) the 4 parallel ERA5 extract workers.
#
# Idempotent: each worker skips (variable, year) pickles already on disk, so
# re-running after a VM reboot or crash resumes exactly where it left off. The
# staging dir lives on /home (persistent disk), so finished pickles survive a
# restart — only in-flight CDS jobs are re-requested.
#
# After all 344 pickles land, assemble the per-city CSVs (fill-only):
#   .venv/bin/python tools/era5_extract.py --assemble-only --staging "$STAGE"
#   .venv/bin/python tools/era5_crossval.py --staging "$STAGE"   # full-scale check
#
# Progress:  ls "$STAGE"/extract/*.pkl | wc -l     (target 344)
#            tail "$STAGE"/logs/w*.log
set -euo pipefail
cd "$(dirname "$0")/.."
STAGE="${ERA5_STAGE:-/home/devuser/era5_staging}"
PY=.venv/bin/python
mkdir -p "$STAGE/logs"

# Match the actual python worker process, not a shell wrapper whose command
# line merely mentions the script (which caused false "already running" hits).
_GUARD='python[^ ]* tools/era5_extract\.py --extract-only'
if pgrep -f "$_GUARD" >/dev/null 2>&1; then
  echo "ERA5 workers already running — refusing to double-launch:"
  pgrep -af "$_GUARD"
  echo "(kill them first if you want a clean restart)"
  exit 0
fi

launch() {  # name  extra-args...
  local name="$1"; shift
  setsid nohup "$PY" tools/era5_extract.py --extract-only --staging "$STAGE" "$@" \
    > "$STAGE/logs/$name.log" 2>&1 &
  echo "launched $name (pid $!): $*"
}

launch w1_mean      --groups mean     --start 1940 --end 2025
launch w2_precip    --groups precip   --start 1940 --end 2025
launch w3_ext_early --groups extremes --start 1940 --end 1982
launch w4_ext_late  --groups extremes --start 1983 --end 2025

echo "pickles so far: $(ls "$STAGE"/extract/*.pkl 2>/dev/null | wc -l)/344"
