#!/usr/bin/env python
"""Cross-validate ERA5 (Copernicus) against Open-Meteo for overlapping cities.

Both sources derive from ERA5 reanalysis but via independent processing chains
(grid interpolation, local-day vs UTC-day aggregation, any Open-Meteo
post-processing). Strong agreement confirms our unit conversions (K→°C, m→mm),
nearest-gridpoint extraction and day-boundary choice are sound; a systematic gap
would flag a bug *before* we trust 757 cities of ERA5 data.

Read-only. ERA5 comes from the extractor's staging pickles ({key}_{year}.pkl,
date×slug) — which contain **every** city, including the ~287 that also have an
Open-Meteo cache — so we compare wherever the two overlap at zero CDS cost.
Open-Meteo comes from the committed data/{slug}_1940-2025[...].csv.gz caches.

For each city/variable we align on common dates and report bias (ERA5−OM), MAE,
RMSE, Pearson r and the annual-mean difference, then summarise the distribution
across all compared cities.

Usage
-----
    python tools/era5_crossval.py                      # all groups, all overlap
    python tools/era5_crossval.py --group mean --sample 15
    python tools/era5_crossval.py --staging /home/devuser/era5_staging
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE.parent))
sys.path.insert(0, str(_HERE))
import config  # noqa: E402
import era5_extract as ex  # noqa: E402  (GROUPS + unit conversions + staging)

DATA_DIR = config.DATA_DIR


def _load_era5(ex_dir: Path, group: str):
    """Return {stat_col: date×slug DataFrame} in site units, for years on disk."""
    out = {}
    for key, _api, _stat, col, conv in ex.GROUPS[group]["stats"]:
        parts = [pd.read_pickle(p) for p in sorted(ex_dir.glob(f"{key}_*.pkl"))]
        if not parts:
            out[col] = None
            continue
        out[col] = conv(pd.concat(parts).sort_index())
    return out


def _stats(era: pd.Series, om: pd.Series):
    """Agreement metrics for one aligned (ERA5, Open-Meteo) daily series."""
    joined = pd.concat([era.rename("e"), om.rename("o")], axis=1, sort=False).dropna()
    if len(joined) < 30:
        return None
    e, o = joined["e"].to_numpy(float), joined["o"].to_numpy(float)
    diff = e - o
    r = float(np.corrcoef(e, o)[0, 1]) if e.std() and o.std() else float("nan")
    ann_e = joined["e"].groupby(joined.index.year).mean()
    ann_o = joined["o"].groupby(joined.index.year).mean()
    return {
        "n": len(joined),
        "bias": float(diff.mean()),
        "mae": float(np.abs(diff).mean()),
        "rmse": float(np.sqrt((diff ** 2).mean())),
        "r": r,
        "ann_bias": float((ann_e - ann_o).mean()),
    }


def _om_path(slug: str, suffix: str) -> Path:
    return DATA_DIR / f"{slug}_1940-2025{suffix}.csv.gz"


def run(args):
    ex_dir = Path(args.staging) / "extract"
    if not ex_dir.exists():
        raise SystemExit(f"no staging pickles at {ex_dir}")
    slugs = [l.slug for l in config.LOCATIONS.values()]

    for group in args.groups:
        spec = ex.GROUPS[group]
        suffix = spec["suffix"]
        era = _load_era5(ex_dir, group)
        cols = [col for _k, _a, _s, col, _c in spec["stats"]]
        if any(era[c] is None for c in cols):
            print(f"\n[{group}] no ERA5 pickles yet — skipping")
            continue
        years = sorted({d.year for d in next(iter(era.values())).index})
        print(f"\n=== {group}  (ERA5 years on disk: {years[0]}–{years[-1]}, "
              f"{len(years)} yr) ===")

        rows = []
        for slug in slugs:
            om_path = _om_path(slug, suffix)
            if not om_path.exists():
                continue
            om = pd.read_csv(om_path, parse_dates=["date"]).set_index("date")
            for col in cols:
                if col not in om.columns or slug not in era[col].columns:
                    continue
                s = _stats(era[col][slug], om[col])
                if s:
                    rows.append({"slug": slug, "var": col, **s})

        if not rows:
            print("  no overlapping cities with Open-Meteo cache yet")
            continue
        df = pd.DataFrame(rows)

        for col in cols:
            sub = df[df["var"] == col]
            if sub.empty:
                continue
            print(f"\n  {col}  —  {len(sub)} cities, "
                  f"{int(sub['n'].sum()):,} day-pairs")
            print(f"    bias (ERA5-OM)  median {sub.bias.median():+.2f}   "
                  f"mean {sub.bias.mean():+.2f}   "
                  f"[{sub.bias.min():+.2f}, {sub.bias.max():+.2f}]")
            print(f"    RMSE            median {sub.rmse.median():.2f}    "
                  f"p95 {sub.rmse.quantile(.95):.2f}")
            print(f"    MAE             median {sub.mae.median():.2f}")
            print(f"    Pearson r       median {sub.r.median():.3f}    "
                  f"min {sub.r.min():.3f}")
            print(f"    annual-mean bias median {sub.ann_bias.median():+.2f}   "
                  f"|max| {sub.ann_bias.abs().max():.2f}")
            worst = sub.reindex(sub.rmse.sort_values(ascending=False).index).head(
                args.sample)
            print(f"    worst {len(worst)} by RMSE:")
            for _, w in worst.iterrows():
                print(f"      {w.slug:22s} rmse {w.rmse:5.2f}  bias {w.bias:+5.2f}"
                      f"  r {w.r:.3f}  ann {w.ann_bias:+.2f}")


def parse_args(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--staging", default=str(ex.DEFAULT_STAGING))
    ap.add_argument("--groups", default="mean,extremes,precip")
    ap.add_argument("--sample", type=int, default=10,
                    help="how many worst-RMSE cities to list per variable")
    args = ap.parse_args(argv)
    args.groups = [g.strip() for g in args.groups.split(",") if g.strip() in ex.GROUPS]
    return args


if __name__ == "__main__":
    run(parse_args())
