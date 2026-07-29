#!/bin/bash
# Daily backfill for a DEDICATED gathering clone: refresh data/ from main first,
# then run the normal daily chunk. Point a second machine at this instead of
# tools/daily-chunk.sh directly.
#
# Why the sync matters: daily-chunk.sh only fetches refs, never updating the
# working tree, so each machine's "is this city cached?" check sees only what it
# downloaded itself. Two machines that cannot see each other's files re-download
# roughly N^2/500 of the same cities a day (N = cities one machine manages) even
# with the priority-window shuffle. Refreshing data/ from main first removes
# almost all of that overlap.
#
# WHY THIS IS A SEPARATE SCRIPT, not a flag on daily-chunk.sh: that script is
# data-only by construction because it may run while a feature branch is checked
# out, so it must never touch the checked-out branch. Fast-forwarding the branch
# is exactly that, and is only safe on a clone that does nothing but gather. So
# the sync here is guarded, and every guard failure SKIPS the sync and still
# gathers - a stale data/ only wastes quota, while a surprised branch loses work.
set -u
REPO="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO" || exit 1

export GIT_TERMINAL_PROMPT=0   # a credential prompt would hang an unattended run

skip() { echo "sync skipped: $* - gathering with data/ as-is"; exec bash tools/daily-chunk.sh; }

echo "== refreshing data/ from main =="

branch="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "")"
[ "$branch" = "main" ] || skip "on branch '${branch:-detached}', not main"

# Any tracked-file edit means this is not a pure gathering clone; a fast-forward
# could silently take it somewhere the operator did not intend.
git diff --quiet && git diff --cached --quiet || skip "tracked files are modified"

git fetch -q origin main || skip "git fetch failed"

# Fast-forward only. If main and HEAD have diverged, this clone has local commits
# and is not a plain gatherer.
if ! git merge-base --is-ancestor HEAD origin/main; then
  skip "HEAD is not an ancestor of origin/main (diverged)"
fi

# Drop untracked data files whose content is ALREADY on main, byte for byte.
# Those are downloads another machine has since published: keeping them only
# makes the fast-forward abort with "untracked working tree files would be
# overwritten". Anything not yet on main - this clone's un-pushed work - is left
# alone, so it still goes out on the send below. Compared by hash, never by
# name, so a file that merely shares a name is never discarded.
dropped=0
while IFS= read -r f; do
  [ -f "$f" ] || continue
  upstream="$(git rev-parse "origin/main:$f" 2>/dev/null)" || continue
  [ "$upstream" = "$(git hash-object "$f")" ] || continue
  rm -f "$f" && dropped=$((dropped + 1))
done < <(git ls-files --others --exclude-standard -- data)
[ "$dropped" -gt 0 ] && echo "  dropped $dropped redundant file(s) already on main"

git merge -q --ff-only origin/main || skip "fast-forward failed"
echo "  data/ now at $(git rev-parse --short HEAD)"

exec bash tools/daily-chunk.sh
