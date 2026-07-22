#!/usr/bin/env python3
"""Generate assets/country_outlines.json - compact SVG silhouette paths per country.

One-off dev tool (NOT run by the build - the build only reads the committed JSON).

Source: Natural Earth 1:110m admin-0 countries (public domain), e.g.
  https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_110m_admin_0_countries.geojson

For each country it emits {cc: {"d": "<svg path>", "w": <viewBox w>, "h": <viewBox h>}}
where ``cc`` is the lowercase ISO 3166-1 alpha-2 code (matching the site's ranking
``cc`` field). Coordinates are equirectangular, aspect-corrected by cos(mean lat),
y-flipped for screen, normalised so the larger dimension spans 100 units.

Overseas territories and far-flung islands are dropped (area + distance filter) so
the silhouette stays the recognisable mainland; the antimeridian is handled so
Pacific-spanning countries (Russia, Fiji) do not smear across the whole globe.

Usage:
  curl -sL <ne url> -o /tmp/ne_110m.geojson
  .venv/bin/python tools/gen_country_outlines.py /tmp/ne_110m.geojson assets/country_outlines.json
"""
import json
import math
import sys
from shapely.geometry import shape, Polygon
from shapely.geometry.base import BaseGeometry


def _polys(geom: BaseGeometry):
    if geom.geom_type == "Polygon":
        return [geom]
    if geom.geom_type == "MultiPolygon":
        return list(geom.geoms)
    return []


def _shift_poly(poly):
    """Shift a polygon's negative longitudes by +360 (antimeridian fix)."""
    def sh(ring):
        return [((x + 360 if x < 0 else x), y) for x, y in ring.coords]
    return Polygon(sh(poly.exterior), [sh(h) for h in poly.interiors])


def build_path(geom: BaseGeometry, tol: float = 0.12):
    geom = geom.simplify(tol, preserve_topology=True)
    parts = _polys(geom)
    if not parts:
        return None
    lons = [x for p in parts for x, _ in p.exterior.coords]
    if lons and (max(lons) - min(lons)) > 180:
        parts = [_shift_poly(p) for p in parts]
    # Keep the largest part, then only parts both reasonably large and near it -
    # drops overseas territories (French Guiana, Alaska, Hawaii).
    parts.sort(key=lambda p: p.area, reverse=True)
    main = parts[0]
    max_area = main.area
    mcx, mcy = main.centroid.x, main.centroid.y
    kept = []
    for p in parts:
        if p.area < max_area * 0.03:
            continue
        cx, cy = p.centroid.x, p.centroid.y
        if math.hypot(cx - mcx, cy - mcy) > 30:
            continue
        kept.append(p)
    if not kept:
        kept = [main]
    # Projection: equirectangular with cos(mean lat) x-correction.
    all_lat = [y for p in kept for _, y in p.exterior.coords]
    lat0 = sum(all_lat) / len(all_lat)
    kx = math.cos(math.radians(lat0)) or 1.0

    rings = []
    for p in kept:
        rings.append(list(p.exterior.coords))
        for hole in p.interiors:
            rings.append(list(hole.coords))

    xs, ys, proj = [], [], []
    for ring in rings:
        pr = [(x * kx, -y) for x, y in ring]  # y-flip for screen coords
        proj.append(pr)
        xs.extend(px for px, _ in pr)
        ys.extend(py for _, py in pr)
    minx, miny, maxx, maxy = min(xs), min(ys), max(xs), max(ys)
    span = max(maxx - minx, maxy - miny) or 1.0
    scale = 100.0 / span
    w = round((maxx - minx) * scale, 1)
    h = round((maxy - miny) * scale, 1)

    segs = []
    for pr in proj:
        pts = [((px - minx) * scale, (py - miny) * scale) for px, py in pr]
        out = []
        for x, y in pts:
            xr, yr = round(x, 1), round(y, 1)
            if out and out[-1] == (xr, yr):
                continue
            out.append((xr, yr))
        if len(out) < 3:
            continue
        segs.append("M" + " ".join(f"{x},{y}" for x, y in out) + "Z")
    if not segs:
        return None
    return {"d": "".join(segs), "w": w, "h": h}


def main():
    src, dst = sys.argv[1], sys.argv[2]
    data = json.load(open(src, encoding="utf-8"))
    out, skipped = {}, []
    for feat in data["features"]:
        props = feat.get("properties", {})
        cc = props.get("ISO_A2") or ""
        if cc in ("", "-99"):
            cc = props.get("ISO_A2_EH") or ""
        cc = cc.strip().lower()
        if len(cc) != 2 or not cc.isalpha():
            skipped.append(props.get("NAME"))
            continue
        try:
            path = build_path(shape(feat["geometry"]))
        except Exception as e:  # noqa: BLE001
            skipped.append(f"{cc}:{e}")
            continue
        if path:
            out[cc] = path
    json.dump(out, open(dst, "w", encoding="utf-8"),
              ensure_ascii=True, separators=(",", ":"))
    print(f"wrote {len(out)} countries to {dst} "
          f"({len(json.dumps(out))/1024:.1f} KB)")
    if skipped:
        print("skipped:", ", ".join(str(s) for s in skipped[:12]))


if __name__ == "__main__":
    main()
