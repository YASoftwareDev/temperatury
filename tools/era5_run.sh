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

# THREE workers, split by year-third. CDS caps *queued* requests per dataset per
# user, but the sustainable depth is ≥3 (measured: 3 jobs accepted, 0 rejected —
# the earlier rejection storm was a 170-request flood, not modest concurrency).
# cdsapi.retrieve() blocks per request, so each worker keeps exactly ONE request
# in flight → 3 workers = 3 in flight = at the safe depth. Each does its year
# range mean→precip→extremes (mean first), so all mean-years finish ~3× sooner.
# NWORKERS can be raised only if CDS proves it runs >3 in parallel.
launch() {  # name  start  end
  local name="$1" s="$2" e="$3"
  setsid nohup "$PY" tools/era5_extract.py --extract-only --staging "$STAGE" \
    --groups mean,precip,extremes --start "$s" --end "$e" \
    > "$STAGE/logs/$name.log" 2>&1 &
  echo "launched $name (pid $!): ${s}-${e}"
}
launch w_early 1940 1968
launch w_mid   1969 1997
launch w_late  1998 2025
echo "pickles so far: $(ls "$STAGE"/extract/*.pkl 2>/dev/null | wc -l)/344"
