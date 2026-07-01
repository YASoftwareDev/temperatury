#!/usr/bin/env python
"""Regenerate cities750k.tsv — every city with population > 750,000.

Source: GeoNames ``cities15000.txt`` (download + unzip from
https://download.geonames.org/export/dump/cities15000.zip). Each qualifying
city is mapped to a region and de-duplicated against the curated list in
config.py by proximity (~20 km), so e.g. GeoNames "Warsaw" doesn't duplicate the
curated "Warszawa". Output columns: region, name, lat, lon, IANA timezone.

Usage:  python tools/gen_cities.py /path/to/cities15000.txt
"""
from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config  # noqa: E402

MIN_POP = 750_000
NEAR_DEG = 0.2  # ~22 km: treat as the same city as an existing one

# ISO-3166 alpha-2 -> region. Georgia/Armenia/Azerbaijan grouped with Asia and
# Turkey with the Middle East, matching the curated config.
REGION = {
    **dict.fromkeys("PL RU UA IT DE ES GB FR HU SE NO DK NL BE AT CZ RO RS BG BY IE".split(), "Europe"),
    **dict.fromkeys("CN IN ID JP KR PK PH VN BD TW MY HK KZ MM KH TH LA MN NP SG UZ TM KG KP AF GE AM AZ LK".split(), "Asia"),
    **dict.fromkeys("TR IQ IR SA AE YE SY LB JO IL OM QA BH KW".split(), "Middle East"),
    **dict.fromkeys("NG ZA CD MA EG TZ SN SD MZ KE CI AO MW LY GN GH CM CG BF ZW ZM UG TG TD SO SL RW NE MR ML MG LR ET GA CF BI DZ".split(), "Africa"),
    **dict.fromkeys("US MX CA HN DO CU GT HT JM NI".split(), "North America"),
    **dict.fromkeys("BR CO VE PE BO AR EC PY UY CL".split(), "South America"),
    **dict.fromkeys("AU NZ".split(), "Oceania"),
}


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit("usage: python tools/gen_cities.py <cities15000.txt>")
    src = Path(sys.argv[1])
    # De-dupe against the CURATED list only (config._CITIES), never against the
    # generated TSV itself — otherwise a second run dedupes against its own
    # output and produces nothing.
    coords = [(la, lo) for _, _, la, lo, _ in config._CITIES]
    slugs = {config.slugify(name) for _, name, _, _, _ in config._CITIES}
    rows: list[tuple] = []
    skipped = 0

    def near(la: float, lo: float) -> bool:
        return any(abs(la - a) < NEAR_DEG and abs(lo - o) < NEAR_DEG for a, o in coords)

    for line in src.read_text(encoding="utf-8").splitlines():
        f = line.split("\t")
        if len(f) < 18:
            continue
        try:
            pop = int(f[14])
        except ValueError:
            continue
        if pop <= MIN_POP:
            continue
        name, la, lo, cc, tz = f[1], float(f[4]), float(f[5]), f[8], f[17]
        region = REGION.get(cc)
        if not region or near(la, lo):
            skipped += 1
            continue
        slug = config.slugify(name)
        if slug in slugs:
            slug = f"{slug}-{cc.lower()}"
            if slug in slugs:
                skipped += 1
                continue
            name = f"{name} ({cc})"
        slugs.add(slug)
        coords.append((la, lo))
        rows.append((region, name, f"{la:.4f}", f"{lo:.4f}", tz))

    rows.sort(key=lambda r: (r[0], r[1]))
    out = Path(__file__).resolve().parent.parent / "cities750k.tsv"
    out.write_text("".join("\t".join(r) + "\n" for r in rows), encoding="utf-8")
    print(f"wrote {len(rows)} cities to {out} (skipped {skipped})")
    print("by region:", dict(Counter(r[0] for r in rows)))


if __name__ == "__main__":
    main()
