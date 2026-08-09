#!/usr/bin/env python
"""Build data/city_pop.json = {slug: population} from GeoNames cities15000.

Match each of our cities to the nearest (and, on ties, most populous) GeoNames
city within a small coordinate window, then record its population. Same matching
approach as tools/gen_city_names.py.

Usage:
    python tools/gen_city_pop.py <cities15000.txt>
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config  # noqa: E402

NEAR = 0.25  # deg: max coord distance to accept a GeoNames match


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit("usage: gen_city_pop.py <cities15000.txt>")
    c15 = Path(sys.argv[1])

    geo = []  # (name, lat, lon, population)
    for line in c15.read_text(encoding="utf-8").splitlines():
        f = line.split("\t")
        if len(f) < 15:
            continue
        try:
            geo.append((f[1], float(f[4]), float(f[5]), int(f[14] or 0)))
        except ValueError:
            continue

    buckets: dict[tuple, list] = {}
    for g in geo:
        buckets.setdefault((round(g[1]), round(g[2])), []).append(g)

    out: dict[str, int] = {}
    n_city = 0
    for slug, loc in config.LOCATIONS.items():
        if getattr(loc, "kind", "city") != "city":
            continue
        n_city += 1
        la, lo = loc.latitude, loc.longitude
        # Our set is all major cities, so within the window pick the MOST POPULOUS
        # GeoNames match (nearest would grab a small ward/suburb, e.g. Tokyo).
        best_pop = -1
        for dla in (-1, 0, 1):
            for dlo in (-1, 0, 1):
                for g in buckets.get((round(la) + dla, round(lo) + dlo), []):
                    d = abs(g[1] - la) + abs(g[2] - lo)
                    if d < NEAR and g[3] > best_pop:
                        best_pop = g[3]
        if best_pop > 0:
            out[slug] = best_pop

    dest = Path(__file__).resolve().parent.parent / "data" / "city_pop.json"
    dest.write_text(json.dumps(out, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    print(f"wrote {dest}: {len(out)}/{n_city} cities with population")
    for s in ("warszawa", "tokyo", "delhi", "london"):
        if s in out:
            print(f"  {s}: {out[s]:,}")


if __name__ == "__main__":
    main()
