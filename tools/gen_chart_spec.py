"""Regenerate charts_spec.json from a BUILT output/charts/ directory.

Run after a full offline build:
    rm -rf output && TEMPERATURY_OFFLINE=1 python main.py --all
    python tools/gen_chart_spec.py

For every chart id, a scalar field path enters the spec when (a) it is present
in EVERY city that has the chart - the client merge fills MISSING keys, so a
spec'd path absent from some city's payload would get injected there, silently
changing that payload - and (b) one single value covers >= 99% of those cities
(majority, not unanimity: strip is equality-gated, so an outlier city simply
keeps its own copy). List values are never speced. _-prefixed top-level keys
and packed-array dicts (chartpack's {"_p": ...}) are never speced.
"""
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import chartpack  # noqa: E402

CHARTS = Path(__file__).resolve().parent.parent / "output" / "charts"
OUT = Path(__file__).resolve().parent.parent / "charts_spec.json"
QUORUM = 0.99


def scalar_paths(node, prefix=()):
    """Yield (path, value) for every non-list scalar field under ``node``."""
    for k, v in node.items():
        if isinstance(v, dict):
            if chartpack.PACK_KEY not in v:         # packed arrays are data
                yield from scalar_paths(v, prefix + (k,))
        elif not isinstance(v, list):
            yield prefix + (k,), v


def main() -> None:
    counts: dict[str, dict[tuple, Counter]] = defaultdict(
        lambda: defaultdict(Counter))
    seen: Counter = Counter()
    files = [p for p in CHARTS.glob("*.json") if not p.name.startswith("_")]
    if not files:
        raise SystemExit("no built city charts found - run a build first")
    for p in files:
        city = json.loads(p.read_text(encoding="utf-8"))
        for chart_id, payload in city.items():
            if chart_id.startswith("_") or not isinstance(payload, dict):
                continue
            seen[chart_id] += 1
            for path, v in scalar_paths(payload):
                counts[chart_id][path][json.dumps(v, ensure_ascii=False)] += 1
    spec: dict = {}
    for chart_id, paths in counts.items():
        for path, ctr in paths.items():
            if sum(ctr.values()) != seen[chart_id]:
                continue                 # absent somewhere: merge would inject
            val, n = ctr.most_common(1)[0]
            if n / seen[chart_id] < QUORUM:
                continue
            node = spec.setdefault(chart_id, {})
            for part in path[:-1]:
                node = node.setdefault(part, {})
            node[path[-1]] = json.loads(val)
    OUT.write_text(json.dumps(spec, ensure_ascii=False, indent=1,
                              sort_keys=True) + "\n", encoding="utf-8")
    print(f"{OUT.name}: {len(spec)} charts, "
          f"{OUT.stat().st_size / 1024:.1f} KB, from {len(files)} cities")


if __name__ == "__main__":
    main()
