#!/usr/bin/env bash
# Run a command and report how close the machine came to running out of memory.
#
#   tools/mem-watch.sh [--] <command> [args...]
#
# The CI build outgrew the 16 GB runner once (2026-09-26 to 10-02) and nothing
# said so: an OOM kill reads as "the hosted runner lost communication", and the
# log of the killed step is cut off. This samples MemTotal - MemAvailable (memory
# the kernel cannot reclaim) so the margin is visible in every run, and prints
# a line at intervals so a run that dies still shows the climb before it.
#
# Exit status is the command's. Tunables (environment):
#   MEM_WATCH_WARN_PCT  peak used % of MemTotal that raises a warning (75)
#   MEM_WATCH_INTERVAL  seconds between samples (2)
#   MEM_WATCH_REPORT    seconds between progress lines (300)
set -uo pipefail

[ "${1:-}" = "--" ] && shift
if [ $# -eq 0 ]; then
  echo "usage: $0 [--] <command> [args...]" >&2
  exit 2
fi

warn_pct=${MEM_WATCH_WARN_PCT:-75}
interval=${MEM_WATCH_INTERVAL:-2}
report=${MEM_WATCH_REPORT:-300}

# Prints "<used MiB> <total MiB> <swap used MiB>".
sample() {
  awk '/^MemTotal:/{t=$2} /^MemAvailable:/{a=$2}
       /^SwapTotal:/{st=$2} /^SwapFree:/{sf=$2}
       END{printf "%d %d %d\n", (t-a)/1024, t/1024, (st-sf)/1024}' /proc/meminfo
}

read -r base total _ < <(sample)
peak=$base; swap_peak=0
start=$SECONDS; next_report=$report

"$@" &
pid=$!
# A cancelled job signals this script; pass it on rather than orphan the command.
trap 'kill -TERM "$pid" 2>/dev/null' INT TERM

while kill -0 "$pid" 2>/dev/null; do
  read -r used _ swap < <(sample)
  [ "$used" -gt "$peak" ] && peak=$used
  [ "$swap" -gt "$swap_peak" ] && swap_peak=$swap
  if [ $((SECONDS - start)) -ge "$next_report" ]; then
    echo "mem-watch: $((SECONDS - start))s used ${used}/${total} MiB" \
         "(peak ${peak}, swap ${swap})"
    next_report=$((next_report + report))
  fi
  sleep "$interval"
done
wait "$pid"
rc=$?

pct=$((peak * 100 / total))
line="peak used ${peak}/${total} MiB (${pct}%), ${base} MiB before start, peak swap ${swap_peak} MiB, $((SECONDS - start))s, exit ${rc}"
echo "mem-watch: $line"
if [ -n "${GITHUB_STEP_SUMMARY:-}" ]; then
  printf '**Build memory:** %s\n' "$line" >> "$GITHUB_STEP_SUMMARY"
fi
if [ "$pct" -ge "$warn_pct" ]; then
  # A workflow-command annotation: shown on the run page, not only in the log.
  echo "::warning title=Build memory::${pct}% of RAM used at peak (warn at ${warn_pct}%): ${line}"
fi
exit "$rc"
