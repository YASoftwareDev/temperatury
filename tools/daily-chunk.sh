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
trap 'rm -f "$NEWLIST" "$PUSHERR"' EXIT
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

echo "== fetching missing cities (up to 20 min; stops when today's quota is spent) =="
# Two passes. First finish the popular pages: precipitation + daily max/min for
# the most-populous cities that are already rendered (unlocks their extra
# charts and the records widget). Then spend the rest of the budget widening
# mean coverage. Once the enrich backlog is empty, its pass costs seconds.
"$PY" tools/om_parallel.py --groups precip,extremes --top-pop 500 --shuffle --max-seconds 360
"$PY" tools/om_parallel.py --groups mean --shuffle --max-seconds 840

# The genuinely-new data files: untracked, ASCII-named .csv.gz files not already
# on origin/main. (A feature branch keeps already-pushed files untracked in the
# working tree, so filter those out to avoid re-sending them.) We deliberately do
# NOT commit these onto the checked-out branch - see build_data_commit below.
NEWFILES=()
while IFS= read -r f; do
  case "$f" in *.csv.gz) ;; *) continue ;; esac
  case "$f" in *[!\ -~]*) continue ;; esac              # skip non-ASCII names
  git cat-file -e "origin/main:$f" 2>/dev/null && continue   # already on main
  NEWFILES+=("$f")
done < <(git ls-files --others --exclude-standard -- data)

if [ "${#NEWFILES[@]}" -eq 0 ]; then
  echo "Nothing new to send - today's quota is already spent (resets 00:00 UTC)."
  exit 0
fi
NEW="${#NEWFILES[@]}"
printf '%s\n' "${NEWFILES[@]}" > "$NEWLIST"       # for the archive fallback
echo "$NEW city file(s) to contribute."

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

if [ "$push_rc" -eq 0 ]; then
  echo; echo "DONE: pushed $NEW city file(s) to $slug (data only). CI will rebuild + deploy."
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
       4. re-run:  bash tools/daily-chunk.sh

 Nothing is lost - your download stays on disk, so re-running is safe.
============================================================
EOF
exit 0
