#!/bin/bash
# Collaborative daily backfill: fetch the latest data, download a chunk of the
# cities still missing (as much as today's free Open-Meteo quota allows), then
# send it back - direct push, else a fork Pull Request, else a packaged archive
# with manual instructions. See CONTRIBUTING.md. Safe to run once a day.
#
# DATA-ONLY BY CONSTRUCTION: this may run unattended while a feature branch is
# checked out here. It never commits to, rebases, or pushes the checked-out
# branch. The send builds a commit from origin/main's tree plus the new data
# files ONLY (isolated index; see build_data_commit) and refuses to push if that
# commit touches any non-data path - so un-merged feature work can never reach
# main through this script.
set -u
# Bracket ranges like [ -~] are compared in COLLATION order outside the C
# locale, not ASCII order, so under a UTF-8 locale a plain-ASCII name can fall
# outside [ -~] and be judged non-ASCII. bash >= 5.0 hides this by defaulting
# `globasciiranges` on; bash 4.3 defaults it off, where the
# non-ASCII guard below silently discarded EVERY downloaded file - a gatherer
# fetched 28 cities and sent none, reporting only "Nothing new to send".
# Must be set before the first use of such a pattern.
shopt -s globasciiranges 2>/dev/null || true
REPO="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO" || exit 1

# A credential prompt would hang an unattended run, and answering it with a
# GitHub password cannot work (removed in 2021). Fail fast instead, so a
# contributor without write access falls through to the PR / archive tiers.
export GIT_TERMINAL_PROMPT=0
export GIT_SSH_COMMAND="${GIT_SSH_COMMAND:-ssh} -o BatchMode=yes"
export GH_PROMPT_DISABLED=1

mktmp() { mktemp "${TMPDIR:-/tmp}/temps.XXXXXX"; }
NEWLIST="$(mktmp)"; PUSHERR="$(mktmp)"
# store_failed is honoured HERE, once, rather than at each exit site: this
# script has six ways to finish, and patching them one at a time is how the
# 'already on main' path was missed. It only ever upgrades a SUCCESS to a
# failure, so an interrupt still reports 130 and real errors keep their code.
trap 'rc=$?; rm -f "$NEWLIST" "$PUSHERR"; [ "$rc" -eq 0 ] && [ "${store_failed:-0}" -eq 1 ] && exit 1' EXIT
trap 'echo; echo "Interrupted. Nothing is lost - just run this again." >&2; exit 130' INT TERM

command -v git >/dev/null 2>&1 || {
  echo "This helper needs Git:"
  echo "  Windows: https://git-scm.com/download/win  (then use the 'Git Bash' app)"
  echo "  macOS:   xcode-select --install"
  echo "  Linux:   sudo apt install git"
  exit 1
}

# --- Python environment (created on first run; venv layout differs by OS) ---
venv_python() {
  if   [ -x "$REPO/.venv/bin/python" ];         then echo "$REPO/.venv/bin/python"
  elif [ -x "$REPO/.venv/Scripts/python.exe" ]; then echo "$REPO/.venv/Scripts/python.exe"
  fi
}
PY="$(venv_python)"
if [ -z "$PY" ]; then
  boot=""
  for c in python3 python; do command -v "$c" >/dev/null 2>&1 && { boot="$c"; break; }; done
  [ -z "$boot" ] && command -v py >/dev/null 2>&1 && boot="py -3"
  [ -z "$boot" ] && { echo "This helper needs Python 3: https://www.python.org/downloads/ (on Windows tick 'Add Python to PATH')."; exit 1; }
  echo "== first run: setting up (only once, ~1-2 min) =="
  $boot -m venv .venv || { echo "Could not create the Python environment." >&2; exit 1; }
  PY="$(venv_python)"
  [ -z "$PY" ] && { echo "Environment created but no Python found under .venv." >&2; exit 1; }
  "$PY" -m pip install --upgrade pip >/dev/null
  "$PY" -m pip install -r requirements.txt \
    || { echo "Could not install required packages - check your internet, then re-run." >&2; exit 1; }
fi

echo "== syncing latest data from GitHub =="
# Fetch only - never `pull --rebase` the checked-out branch. This script may run
# unattended while a feature branch is checked out here; rebasing or committing
# onto that branch (and then pushing it) is exactly how a data round could drag
# un-merged feature work onto main. We only need origin/main up to date; the send
# below builds its commit from origin/main's tree, not from HEAD.
git fetch -q origin main \
  || { echo "git fetch failed - resolve the above, then re-run." >&2; exit 1; }

echo "== fetching missing cities (stops as soon as the hourly quota is spent) =="
# The free tier meters by the HOUR, not by the day, and one chunk (15 cities x
# 86 years) is heavy: a run lands roughly 75 cities before every further call
# comes back "Hourly API request limit exceeded". So a run does not get a budget
# it can divide between groups - it gets ONE group's worth, and whichever group
# runs first takes all of it.
#
# That is why a fixed order silently froze two thirds of the dataset: `precip`
# always led, so `extremes` gained nothing between 2026-07-29 and 2026-08-05 and
# `mean` (the only group that adds NEW cities) stalled at 2494 from 2026-08-03.
# Rotating the leader by UTC day gives each group every third run, so all three
# keep moving. --shuffle still spreads concurrent fetchers within the priority
# window; it cannot help when the budget itself is the binding constraint.
case $(( 10#$(date -u +%j) % 3 )) in
  0) ORDER="mean precip extremes" ;;
  1) ORDER="precip extremes mean" ;;
  *) ORDER="extremes mean precip" ;;
esac
# TEMPERATURY_GROUP_ORDER overrides the rotation for THIS machine only. Use it
# on a gatherer whose shard lags in one dataset (its leading group takes the
# whole budget, so a machine that gets one scrap of a shared-IP quota per day
# should spend that scrap where its bucket is behind). The fleet-wide rotation
# above stays the default; a typo'd group name aborts the run via the rc=2
# check below rather than gathering nothing silently.
if [ -n "${TEMPERATURY_GROUP_ORDER:-}" ]; then
  ORDER="$TEMPERATURY_GROUP_ORDER"
  echo "group order overridden: $ORDER"
else
  echo "today's group order: $ORDER"
fi

# Fleet sharding: a machine that owns shard I of N (a `.gather-shard` file
# containing e.g. "2/4", or $TEMPERATURY_SHARD) fetches its own hash-bucket of
# cities before anyone else's, so concurrently running fleet machines never
# collide while each still has owned work - a guarantee, where staggered cron
# times were only a probability. Machines without a shard (volunteers) keep the
# plain shuffled queue. The file is per-machine state, never sent anywhere.
if [ -z "${TEMPERATURY_SHARD:-}" ] && [ -f "$REPO/.gather-shard" ]; then
  TEMPERATURY_SHARD="$(tr -d '[:space:]' < "$REPO/.gather-shard")"
fi
if [ -n "${TEMPERATURY_SHARD:-}" ]; then
  export TEMPERATURY_SHARD
  echo "fleet shard: $TEMPERATURY_SHARD"
fi
store_failed=0
for group in $ORDER; do
  # Only the enrich groups are restricted to already-rendered cities; `mean` is
  # what widens the roster, so it must see every city.
  case "$group" in
    mean) "$PY" tools/om_parallel.py --groups mean --shuffle --max-seconds 400 ;;
    *)    "$PY" tools/om_parallel.py --groups "$group" --rendered-only --shuffle --max-seconds 400 ;;
  esac
  # Exit 2 is argparse rejecting the invocation - a bad .gather-shard /
  # TEMPERATURY_SHARD value, most likely. Without this check every group's
  # pass fails the same way and the run ends in "Nothing new to send" with
  # exit 0: a fleet machine silently gathering nothing, indefinitely.
  rc=$?
  if [ "$rc" -eq 2 ]; then
    echo "ERROR: the fetcher rejected its arguments - check .gather-shard / TEMPERATURY_SHARD / TEMPERATURY_GROUP_ORDER. Aborting." >&2
    exit 1
  elif [ "$rc" -ne 0 ]; then
    # The fetcher stored nothing it fetched. Do NOT abort: files from an
    # earlier group may be waiting, and skipping the send would strand them.
    # Carry the failure to the exit code instead, so cron surfaces it.
    echo "ERROR: '$group' fetched cities but stored none (rc=$rc)." >&2
    store_failed=1
  fi
done

# The genuinely-new data files: untracked, ASCII-named cache files not already
# on origin/main. (A feature branch keeps already-pushed files untracked in the
# working tree, so filter those out to avoid re-sending them.) We deliberately do
# NOT commit these onto the checked-out branch - see build_data_commit below.
NEWFILES=()
while IFS= read -r f; do
  # Both encodings count: a machine that gathered before the format migration
  # still holds unsent .csv.gz files, and skipping them would lose real work.
  case "$f" in *.tpy|*.csv.gz) ;; *) continue ;; esac
  case "$f" in *[!\ -~]*) continue ;; esac              # skip non-ASCII names
  git cat-file -e "origin/main:$f" 2>/dev/null && continue   # already on main
  NEWFILES+=("$f")
done < <(git ls-files --others --exclude-standard -- data)

if [ "${#NEWFILES[@]}" -eq 0 ]; then
  # THIS is the path a total store failure takes, so the flag has to be read
  # here too: "nothing new" after a spent quota is a normal quiet day, but
  # "nothing new" after fetching cities we could not store is a broken machine.
  if [ "$store_failed" -eq 1 ]; then
    echo "ERROR: nothing to send because nothing could be STORED, not because" >&2
    echo "       the quota ran out. This machine will gather nothing until fixed." >&2
    exit 1
  fi
  echo "Nothing new to send - today's quota is already spent (resets 00:00 UTC)."
  exit 0
fi
NEW="${#NEWFILES[@]}"
printf '%s\n' "${NEWFILES[@]}" > "$NEWLIST"       # for the archive fallback
echo "$NEW city file(s) to contribute."

# Building the data commit needs a git identity, and a fresh machine often has
# none. The failure is badly placed: `git commit-tree` dies with "empty ident
# name", build_data_commit returns non-zero, and the send falls all the way to
# the archive tier - whose advice talks about GitHub auth, which is NOT the
# problem. A gatherer lost a full round to that. Supply a repo-local identity
# instead of failing: it only labels the data commit, and `git config` without
# --global cannot disturb the machine's own settings.
#
# The identity is deliberately GENERIC, not derived from $USER or $(hostname).
# This repository is public and its history is permanent, so a machine-derived
# address would publish a volunteer's login name and the name of a machine on
# their network - forever, and invisibly, since the address travels inside the
# commit rather than in any text a contributor could review. Nobody signs up for
# that by running a data-gathering helper. `.invalid` is reserved by RFC 2606 and
# can never be routed. Contributors who DO want the credit simply set their own
# git identity; this only fills the gap when there is none.
if ! git var GIT_AUTHOR_IDENT >/dev/null 2>&1; then
  git config user.name  "temperatury gatherer"
  git config user.email "gatherer@temperatury.invalid"
  echo "  note: this machine had no git identity; using a neutral one for the commit."
  echo "        (set user.name/user.email yourself if you want the commit in your name)"
fi

url="$(git remote get-url origin)"
slug="$(echo "$url" | sed -E 's#.*github\.com[:/]+##; s#\.git$##; s#/$##')"
owner="${slug%%/*}"; repo="${slug##*/}"

# Build a commit that is origin/main's tree PLUS the new data files only, parented
# on origin/main - never on HEAD. An isolated index (GIT_INDEX_FILE) keeps the
# working tree and the checked-out branch completely untouched, so an unattended
# run on a feature branch can never carry un-merged work to main. A safety check
# refuses to proceed if the commit ever touches a non-data path. Echoes the sha;
# returns 3 when nothing actually differs from main, non-zero on any failure.
build_data_commit() {
  git fetch -q origin main || return 1
  local idx tree commit f nondata
  idx="$(mktmp)"
  GIT_INDEX_FILE="$idx" git read-tree origin/main || { rm -f "$idx"; return 1; }
  for f in "${NEWFILES[@]}"; do
    [ -f "$f" ] || continue
    GIT_INDEX_FILE="$idx" git update-index --add -- "$f" || { rm -f "$idx"; return 1; }
  done
  tree="$(GIT_INDEX_FILE="$idx" git write-tree)"; rm -f "$idx"
  [ -n "$tree" ] || return 1
  commit="$(git commit-tree "$tree" -p origin/main \
              -m "Backfill data cache (Open-Meteo round)")" || return 1
  # Safety: the commit must touch ONLY data/. Test grep's OUTPUT, not its exit
  # code - this box's grep is ugrep, whose `-qv` exit status differs from GNU
  # grep's (and CI uses GNU grep), so the output is the portable signal.
  nondata="$(git diff --name-only origin/main "$commit" | grep -vE '^data/' || true)"
  if [ -n "$nondata" ]; then
    echo "SAFETY: backfill commit touches non-data paths; refusing to send:" >&2
    printf '%s\n' "$nondata" | head >&2
    return 1
  fi
  git diff --quiet origin/main "$commit" && return 3   # nothing new vs main
  echo "$commit"
}

echo "== sending data back =="
# (1) direct push of the data-only commit. A non-fast-forward means someone
# pushed first -> rebuild on the new origin/main and retry; any other failure
# means no write access or a protected branch -> fall through to a PR.
COMMIT=""; push_rc=1; tries=0
while [ "$tries" -lt 5 ]; do
  tries=$((tries + 1))
  COMMIT="$(build_data_commit)"; brc=$?
  if [ "$brc" -eq 3 ]; then
    echo "All fetched files are already on main - nothing to push."; exit 0
  fi
  { [ "$brc" -eq 0 ] && [ -n "$COMMIT" ]; } || { push_rc=2; break; }
  if git push origin "$COMMIT:main" 2>"$PUSHERR"; then push_rc=0; break; fi
  if grep -qiE "non-fast-forward|fetch first|behind" "$PUSHERR"; then
    echo "  someone else pushed first; rebuilding on the new main..."
    continue
  fi
  push_rc=2; break
done

# The push above went out through an ISOLATED index, so these files are on main
# yet still untracked here - and stay that way, which makes the next `git pull`
# abort ("untracked working tree files would be overwritten"). Reconcile: drop
# the local copies that are byte-identical to what we just pushed, then
# fast-forward, which brings the very same bytes back as tracked files.
#
# Deliberately narrow, because this is the one step that touches the checked-out
# branch: only on main, only with a clean index, only files git confirms are
# untracked AND identical to the pushed blob. Anything else is left alone - an
# unreconciled tree is untidy, losing someone's work is not.
reconcile_local_copies() {
  local on_main=0 f blob removed=0
  [ "$(git symbolic-ref --quiet --short HEAD 2>/dev/null)" = "main" ] && on_main=1
  # A clean tree only matters when main is checked out, because only then do we
  # move the branch the worktree is sitting on.
  if [ "$on_main" -eq 1 ]; then
    git diff --quiet && git diff --cached --quiet || return 0
  fi
  # Removing an untracked file whose bytes are already in the commit we just
  # PUSHED loses nothing: the content is durable on origin/main. Off main it
  # also restores the honest state - a feature branch never had these files, so
  # a worktree without them is what the branch actually describes.
  for f in "${NEWFILES[@]}"; do
    [ -f "$f" ] || continue
    git ls-files --error-unmatch -- "$f" >/dev/null 2>&1 && continue   # already tracked
    blob="$(git rev-parse --quiet --verify "$COMMIT:$f" 2>/dev/null)" || continue
    [ "$blob" = "$(git hash-object -- "$f")" ] || continue             # not identical
    rm -f -- "$f" && removed=$((removed + 1))
  done
  [ "$removed" -gt 0 ] || return 0

  if [ "$on_main" -eq 1 ]; then
    if git merge --ff-only "$COMMIT" >/dev/null 2>&1; then
      echo "  reconciled $removed file(s) into main (now tracked)."
    else
      git checkout -- data/ 2>/dev/null || true   # restore rather than leave gaps
      echo "  note: kept $removed file(s) (main would not fast-forward)." >&2
    fi
    return 0
  fi
  # Off main: advance the local main REF without checking it out, so a later
  # `git checkout main` materialises exactly these files instead of aborting on
  # them. Never touches the checked-out branch.
  if git fetch -q origin main:main 2>/dev/null; then
    echo "  reconciled $removed file(s); local main advanced (checkout main to get them)."
  else
    echo "  reconciled $removed file(s); run 'git fetch origin main:main' when convenient." >&2
  fi
}

if [ "$push_rc" -eq 0 ]; then
  echo; echo "DONE: pushed $NEW city file(s) to $slug (data only). CI will rebuild + deploy."
  reconcile_local_copies
  "$PY" tools/coverage.py 2>/dev/null | grep 'mean (historical)' || true
  exit 0
fi
if [ "$push_rc" -eq 1 ]; then
  echo "Could not finish pushing (repeated conflicts). The files stay on disk and go out on the next run." >&2
  exit 0
fi

# (2) Pull Request from your fork - still the data-only commit, never HEAD.
[ -n "$COMMIT" ] || COMMIT="$(build_data_commit)" || COMMIT=""
if [ -n "$COMMIT" ] && command -v gh >/dev/null 2>&1 && gh auth status >/dev/null 2>&1; then
  me="$(gh api user -q .login 2>/dev/null)"
  if [ -n "$me" ]; then
    echo "No direct write access - opening a Pull Request from your fork..."
    branch="data-$(date -u +%Y%m%d-%H%M%S)"
    gh repo fork "$owner/$repo" --clone=false >/dev/null 2>&1 || true
    git remote remove fork 2>/dev/null || true
    git remote add fork "https://github.com/$me/$repo.git"
    pushed=1
    for _ in 1 2; do
      git push -q fork "$COMMIT:refs/heads/$branch" 2>"$PUSHERR" && { pushed=0; break; }
      sleep 5   # a brand-new fork may take a moment to accept pushes
    done
    if [ "$pushed" -eq 0 ]; then
      if pr="$(gh pr create --repo "$owner/$repo" --base main --head "$me:$branch" \
            --title "Backfill data cache (Open-Meteo round)" \
            --body "Adds $NEW city file(s) fetched from Open-Meteo, via tools/daily-chunk.sh." 2>&1)"; then
        echo; echo "DONE: opened a Pull Request with $NEW file(s):"; echo "  $pr"
        echo "The project owner just needs to merge it."
        exit 0
      fi
      echo "Opening the Pull Request failed:" >&2; echo "$pr" >&2
    else
      echo "Could not push to your fork:" >&2; cat "$PUSHERR" >&2
    fi
  fi
fi

# (3) manual fallback.
mkdir -p outbox
archive="outbox/temps-data-$(date -u +%Y%m%d-%H%M%S).tar.gz"
tar -czf "$archive" -C "$REPO" -T "$NEWLIST"
cat <<EOF

============================================================
 Could not send automatically. Your $NEW new file(s) are packaged here:

     $archive

 To contribute them, do ONE of these:
   * Email that file to the project owner (they unpack it into data/).
   * Or set up automatic Pull Requests, then re-run this script:
       1. free account at https://github.com
       2. install GitHub CLI:  https://cli.github.com
       3. run:  gh auth login
       4. run this helper again, the same way you ran it this time

 Nothing is lost - your download stays on disk, so re-running is safe.
============================================================
EOF
exit 0
