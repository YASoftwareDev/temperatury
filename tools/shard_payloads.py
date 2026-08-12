"""Distribute built per-city payloads into per-origin shard directories.

Usage: python tools/shard_payloads.py <payload_dir> <n_shards>

Moves every ``<payload_dir>/<slug>[_w].json`` into
``<payload_dir>/shard-<i>/`` where ``i = report.payload_shard(slug, n)`` -
the same function the browser resolver (window.__payloadBase) uses to pick
the fetch origin, so a file always lives exactly where the client looks.
Idempotent: files already inside a shard dir are re-homed if their shard
assignment changed (n_shards grew), so re-sharding is one CI-config change.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from report import payload_shard  # noqa: E402


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit("usage: shard_payloads.py <payload_dir> <n_shards>")
    root = Path(sys.argv[1])
    n = int(sys.argv[2])
    for i in range(n):
        (root / f"shard-{i}").mkdir(parents=True, exist_ok=True)
    moved = 0
    candidates = list(root.glob("*.json"))
    for i in range(n):
        candidates += (root / f"shard-{i}").glob("*.json")
    for p in candidates:
        slug = p.name[:-7] if p.name.endswith("_w.json") else p.stem
        want = root / f"shard-{payload_shard(slug, n)}" / p.name
        if p != want:
            want.parent.mkdir(parents=True, exist_ok=True)
            p.replace(want)
            moved += 1
    counts = {i: sum(1 for _ in (root / f"shard-{i}").glob("*.json"))
              for i in range(n)}
    print(f"sharded into {n}: {counts} ({moved} moved)")


if __name__ == "__main__":
    main()
