#!/bin/bash
# Autonomous, resumable backfill of the Open-Meteo daily max/min ("extremes")
# and precipitation caches for every location, respecting the free-tier rate
# limit. Idempotent: re-running skips already-cached cities and fetches only
# what's missing, so it safely resumes after an interruption / VM restart.
#
# Usage (from anywhere):  bash tools/backfill.sh
# Runs until both datasets cover all cities, then exits. It commits + pushes
# each batch to main; CI then rebuilds the site offline from the cache.
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

  # Fetch order matters under the rate limit: mean first (a city only renders
  # once its mean is cached), then the *cheap* precip (1 var, 15/call), then the
  # *expensive* extremes (2 vars, 7/call) last. Doing extremes before precip
  # starved precip — it drained the per-round quota first.
  # Fetch order matters under the rate limit: mean first (a city only renders
  # once its mean is cached), then the *cheap* precip (1 var, 15/call), then the
  # *expensive* extremes (2 vars, 7/call). Apparent temperature (heat index) is
  # the lowest-priority chart, so it is fetched last.
  "$PY" -c "
import config, data
locs = list(config.LOCATIONS.values())
mean = data.load_temperatures_bulk(locs, 1940, 2025)
pre = data.load_precip_bulk(locs, 1940, 2025)
ext = data.load_extremes_bulk(locs, 1940, 2025)
app = data.load_apparent_bulk(locs, 1940, 2025)
mm = sum(1 for l in locs if l.slug not in mean)
me = sum(1 for l in locs if l.slug not in ext)
mp = sum(1 for l in locs if l.slug not in pre)
ma = sum(1 for l in locs if l.slug not in app)
print('MEAN missing', mm, '| PRECIP missing', mp,
      '| EXTREMES missing', me, '| APPARENT missing', ma)
open('/tmp/backfill_remaining.txt','w').write(str(mm+me+mp+ma))
"
  remaining=$(cat /tmp/backfill_remaining.txt 2>/dev/null || echo 99)

  for f in data/*.csv.gz; do
    [ -e "$f" ] || continue
    case "$f" in *[!\ -~]*) : ;; *) git add "$f" ;; esac
  done
  if ! git diff --cached --quiet; then
    git commit -q -m "Backfill extremes/precip cache (round $round)" \
      && git push -q origin main \
      && echo "round $round: pushed; $remaining dataset-cities still missing"
  else
    echo "round $round: no new data"
  fi

  if [ "$remaining" = "0" ]; then
    echo "ALL extremes + precip cached - backfill complete."
    break
  fi
  sleep 1800
done
