#!/bin/bash
# Resumable backfill of the CURRENT (in-progress) year's daily mean + max/min
# for every render-eligible city, so the interactive monthly-range and
# monthly-records widgets can offer the current year (e.g. 2026) as a
# selectable year. Mirrors tools/backfill.sh but targets year-01-01..today and
# caches under the distinct '{slug}_{year}_current[_extremes].csv.gz' key.
#
# Run this AFTER tools/backfill.sh has finished (or while it sleeps) — running
# both at once competes for the Open-Meteo rate limit. It only fetches current-
# year data for cities that already have historical mean data (so the year is
# immediately visible on a page that exists), and skips ones already cached, so
# it is safe to re-run / resume after an interruption.
#
# Usage:  bash tools/backfill-current.sh
set -u
REPO="$(cd "$(dirname "$0")/.." && pwd)"
PY="$REPO/.venv/bin/python"
PROBE='https://archive-api.open-meteo.com/v1/archive?latitude=52&longitude=21&start_date=2024-07-01&end_date=2024-07-02&daily=temperature_2m_max&timezone=auto'
cd "$REPO" || exit 1

for round in $(seq 1 96); do
  code=$(curl -s -o /dev/null -w '%{http_code}' -m 20 "$PROBE")
  if [ "$code" != "200" ]; then
    echo "round $round: quota not ready (HTTP $code); sleeping"
    sleep 1800
    continue
  fi

  "$PY" -c "
import os, config, data
# Only cities that already have historical mean data (page is built for them).
locs = [l for l in config.LOCATIONS.values()
        if os.path.exists(f'data/{l.slug}_1940-2025.csv.gz')]
cur = data.load_current_bulk(locs)
ext = data.load_current_extremes_bulk(locs)
mc = sum(1 for l in locs if l.slug not in cur)
ec = sum(1 for l in locs if l.slug not in ext)
print('CURRENT mean missing', mc, '| CURRENT extremes missing', ec, 'of', len(locs))
open('/tmp/backfill_current_remaining.txt','w').write(str(mc+ec))
"
  remaining=$(cat /tmp/backfill_current_remaining.txt 2>/dev/null || echo 99)

  for f in data/*_current*.csv.gz; do
    [ -e "$f" ] || continue
    case "$f" in *[!\ -~]*) : ;; *) git add "$f" ;; esac
  done
  if ! git diff --cached --quiet; then
    git commit -q -m "Backfill current-year cache (round $round)" \
      && git push -q origin main \
      && echo "round $round: pushed; $remaining current-year datasets still missing"
  else
    echo "round $round: no new current-year data"
  fi

  if [ "$remaining" = "0" ]; then
    echo "ALL current-year mean + extremes cached - done."
    break
  fi
  sleep 1800
done
