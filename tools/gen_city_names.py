#!/usr/bin/env python
"""Build data/city_names.json = {slug: {lang: localized name}} from GeoNames.

Match each of our cities to the nearest GeoNames city (by coordinates), then pull
its preferred name in each of the site's languages from the alternate-names dump.
Only names that actually differ from the default are stored, so the table is
sparse (mostly the major cities that have real exonyms, e.g. Munich -> Monachium).

Usage:
    python tools/gen_city_names.py <cities15000.txt> <alternateNamesV2.txt>
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config  # noqa: E402
import i18n  # noqa: E402

LANGS = set(i18n.LANGUAGES)
NEAR = 0.25   # deg: search radius for a NAME-SIMILAR GeoNames match
SAME = 0.02   # deg (~2 km): close enough to be the same town regardless of name


def _lev(a: str, b: str) -> int:
    """Plain Levenshtein distance (names are short, quadratic is fine)."""
    if len(a) < len(b):
        a, b = b, a
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[-1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def _name_like(ours: str, theirs: str) -> bool:
    """Do the two names plausibly denote the same city? Catches exonym pairs
    (Warszawa/Warsaw) while rejecting distinct neighbours (Rabka-Zdrój matched
    to Nowy Targ 15 km away, before this guard existed)."""
    a, b = config.slugify(ours), config.slugify(theirs)
    if not a or not b:
        return False
    if a == b or a in b or b in a:
        return True
    return _lev(a, b) <= max(2, min(len(a), len(b)) // 4)


def main() -> None:
    if len(sys.argv) < 3:
        raise SystemExit("usage: gen_city_names.py <cities15000.txt> <alternateNamesV2.txt>")
    c15, altf = Path(sys.argv[1]), Path(sys.argv[2])

    # 1. GeoNames candidates: (geonameid, name, lat, lon, population).
    geo = []
    for line in c15.read_text(encoding="utf-8").splitlines():
        f = line.split("\t")
        if len(f) < 15:
            continue
        try:
            geo.append((int(f[0]), f[1], float(f[4]), float(f[5]), int(f[14] or 0)))
        except ValueError:
            continue

    # 2. Match each of our cities to the nearest (and, on ties, most populous)
    #    GeoNames city within NEAR degrees. Bucket by whole degree for speed.
    buckets: dict[tuple, list] = {}
    for g in geo:
        buckets.setdefault((round(g[2]), round(g[3])), []).append(g)

    slug_gid: dict[str, tuple[int, float]] = {}   # slug -> (geonameid, dist)
    import math
    for slug, loc in config.LOCATIONS.items():
        la, lo = loc.latitude, loc.longitude
        k = math.cos(math.radians(la))   # true km, not raw degrees
        # Two tiers. A NAME-SIMILAR record anywhere in the radius always wins
        # (the exonym case: Warszawa/Warsaw). Only when none exists may a
        # name-dissimilar record within SAME (~2 km) stand in for the same
        # town (a renamed GeoNames entry). One combined pass let a central
        # district hijack its city (Berlin matched the "Mitte" record) and a
        # 15 km neighbour adopt a small town (Rabka-Zdrój became Nowy Targ).
        named = close = None   # (distance, -population, geonameid)
        for dla in (-1, 0, 1):
            for dlo in (-1, 0, 1):
                for g in buckets.get((round(la) + dla, round(lo) + dlo), []):
                    d = abs(g[2] - la) + abs(g[3] - lo) * k
                    if d >= NEAR:
                        continue
                    key = (d, -g[4], g[0])
                    if _name_like(loc.name, g[1]):
                        if named is None or key < named:
                            named = key
                    elif d < SAME:
                        if close is None or key < close:
                            close = key
        pick = named or close
        if pick:
            slug_gid[slug] = (pick[2], pick[0])
    # Two slugs can share a nearest GeoNames record; the closer one owns it
    # (the inversion used to keep an arbitrary dict-order winner).
    gid_slug: dict[int, str] = {}
    gid_d: dict[int, float] = {}
    for slug, (gid, d) in slug_gid.items():
        if gid not in gid_slug or d < gid_d[gid]:
            gid_slug[gid], gid_d[gid] = slug, d
    print(f"matched {len(slug_gid)}/{len(config.LOCATIONS)} cities to GeoNames ids")

    # 3. Stream the alternate-names dump, keeping only our ids x our languages.
    #    Cols: altId, geonameid, isolang, altname, isPreferred, isShort, isColloquial, isHistoric.
    want = set(gid_slug)
    cand: dict[int, dict[str, list]] = {}
    for line in altf.open(encoding="utf-8"):
        f = line.rstrip("\n").split("\t")
        if len(f) < 4:
            continue
        try:
            gid = int(f[1])
        except ValueError:
            continue
        if gid not in want:
            continue
        lang = f[2]
        if lang not in LANGS:
            continue
        if len(f) > 7 and (f[6] == "1" or f[7] == "1"):   # colloquial / historic
            continue
        pref = len(f) > 4 and f[4] == "1"
        short = len(f) > 5 and f[5] == "1"
        cand.setdefault(gid, {}).setdefault(lang, []).append((f[3], pref, short))

    # 4. Pick one name per (city, lang): preferred > short > shortest string.
    #    Keep only names that differ from the default (case-insensitive).
    out: dict[str, dict[str, str]] = {}
    for gid, langs in cand.items():
        slug = gid_slug[gid]
        default = config.LOCATIONS[slug].name
        dnorm = default.casefold()
        for lang, names in langs.items():
            names.sort(key=lambda n: (not n[1], not n[2], len(n[0])))
            pick = names[0][0]
            if pick and pick.casefold() != dnorm:
                out.setdefault(slug, {})[lang] = pick

    dest = Path(__file__).resolve().parent.parent / "data" / "city_names.json"
    dest.write_text(json.dumps(out, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    n_names = sum(len(v) for v in out.values())
    print(f"wrote {dest}: {len(out)} cities with {n_names} localized names")
    for s in ("munich", "warszawa", "vienna", "moscow", "cologne", "koln"):
        if s in out:
            print(f"  {s}: {out[s]}")


if __name__ == "__main__":
    main()
