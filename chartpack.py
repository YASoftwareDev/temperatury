"""Pack chart-payload numeric lists into base64 scaled-int blobs.

A JSON list of numbers/nulls costs ~6 characters per value ("20.46,"); the
packed form costs 2 bytes (int16) or 4 (int32) plus base64 overhead - the
single biggest lever on per-city chart JSON (measured 23.3 KB of numeric
characters in a 34 KB minified payload). The GitHub Pages cap counts
UNCOMPRESSED bytes, so this on-disk encoding matters where gzip would not.

Packed form: {"_p": <base64 little-endian ints>, "d": <decimals>, "w": 2|4}.
null is the sentinel (int16 -32768 / int32 -2147483648). Packing is verified
per array - unpack(pack(a)) must equal a exactly, else the plain list is kept.
Never lossy, same philosophy as codec.py. Client mirror: __unpackCharts in
assets/charts.js.
"""
from __future__ import annotations

import base64
import json
import struct

PACK_KEY = "_p"
MIN_LEN = 8                      # below this, packing saves nothing
_SENT = {2: -(2 ** 15), 4: -(2 ** 31)}
_FMT = {2: "h", 4: "i"}
_INF = (float("inf"), float("-inf"))


def _decimals(vals: list) -> int | None:
    """Smallest d in 0..4 such that every value survives round(v, d)."""
    for d in range(5):
        if all(v is None or round(v, d) == v for v in vals):
            return d
    return None


def _pack_list(vals: list) -> dict | None:
    """One list -> packed dict, or None when it cannot be packed exactly."""
    if len(vals) < MIN_LEN:
        return None
    if not all(v is None or (isinstance(v, (int, float))
                             and not isinstance(v, bool)) for v in vals):
        return None
    if any(v is not None and (v != v or v in _INF) for v in vals):
        return None
    d = _decimals(vals)
    if d is None:
        return None
    scale = 10 ** d
    ints = [None if v is None else int(round(v * scale)) for v in vals]
    lim16 = 2 ** 15
    width = 2 if all(i is None or (-lim16 < i < lim16) for i in ints) else 4
    sent = _SENT[width]
    if any(i == sent for i in ints):
        return None                      # a real value collides with null
    if width == 4 and any(i is not None and not (-(2 ** 31) < i < 2 ** 31)
                          for i in ints):
        return None
    raw = struct.pack(f"<{len(ints)}{_FMT[width]}",
                      *(sent if i is None else i for i in ints))
    return {PACK_KEY: base64.b64encode(raw).decode("ascii"),
            "d": d, "w": width}


def _unpack_dict(p: dict) -> list:
    raw = base64.b64decode(p[PACK_KEY])
    width, d = p["w"], p["d"]
    ints = struct.unpack(f"<{len(raw) // width}{_FMT[width]}", raw)
    sent, scale = _SENT[width], 10 ** d
    return [None if i == sent else (i if d == 0 else i / scale) for i in ints]


def pack_tree(obj):
    """Deep-copy ``obj`` with every packable numeric list packed (verified)."""
    if isinstance(obj, list):
        packed = _pack_list(obj)
        if packed is not None and _unpack_dict(packed) == obj:
            return packed
        return [pack_tree(v) for v in obj]
    if isinstance(obj, dict):
        return {k: pack_tree(v) for k, v in obj.items()}
    return obj


def unpack_tree(obj):
    """Inverse of :func:`pack_tree` (tests and tooling; browsers use JS)."""
    if isinstance(obj, dict):
        if isinstance(obj.get(PACK_KEY), str):
            return _unpack_dict(obj)
        return {k: unpack_tree(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [unpack_tree(v) for v in obj]
    return obj


# --- columnar row packing ----------------------------------------------------
# A list of flat, mostly-same-keyed dicts (the _global.json ranking: one row
# per city) stores each key ONCE as a column; numeric columns and fixed-stride
# per-row number lists (the st sparkline) ride the same verified base64 int
# codec. Missing keys survive as null slots that unpack_rows drops again.
# Like pack_tree, packing is verified per call: if unpack_rows(pack_rows(rows))
# is not exactly the input, the caller gets the plain rows back untouched.

_ABSENT = object()


def _pack_col(vals: list):
    """One column -> its packed/plain form. ``_ABSENT`` slots become null."""
    plain = [None if v is _ABSENT else v for v in vals]
    if all(v is None or (isinstance(v, (int, float))
                         and not isinstance(v, bool)) for v in plain):
        packed = _pack_list(plain)
        if packed is not None and _unpack_dict(packed) == plain:
            return packed
        return plain
    lens = {len(v) for v in plain if isinstance(v, list)}
    if len(lens) == 1 and all(v is None or isinstance(v, list) for v in plain):
        stride = lens.pop()
        flat = [x for v in plain for x in (v if v is not None
                                           else [None] * stride)]
        packed = _pack_list(flat)
        if packed is not None and _unpack_dict(packed) == flat:
            # A fully-absent row is indistinguishable from a row of nulls
            # after flattening; record which rows were absent.
            gaps = [i for i, v in enumerate(plain) if v is None]
            out = {**packed, "stride": stride}
            if gaps:
                out["gaps"] = gaps
            return out
    return plain


def pack_rows(rows: list[dict]):
    """Columnar layout for ``rows``; the plain input when not exactly inverse."""
    keys: list[str] = []
    for row in rows:
        for k in row:
            if k not in keys:
                keys.append(k)
    cols = {k: _pack_col([row.get(k, _ABSENT) for row in rows]) for k in keys}
    packed = {"_cols": cols, "n": len(rows)}
    # No try/except blindfold: unpacking what was just packed must not throw,
    # and hiding a throw here once masked a NameError as a silent fallback.
    return packed if unpack_rows(json.loads(json.dumps(packed))) == rows \
        else rows


def unpack_rows(packed):
    """Inverse of :func:`pack_rows` (also the JS __inflateRows contract)."""
    if isinstance(packed, list):
        return packed                      # pack_rows fell back to plain
    n = packed["n"]
    rows = [{} for _ in range(n)]
    for k, col in packed["_cols"].items():
        if isinstance(col, dict) and "stride" in col:
            stride = col["stride"]
            gaps = set(col.get("gaps", ()))
            flat = _unpack_dict(col)
            for i in range(n):
                if i not in gaps:
                    rows[i][k] = flat[i * stride:(i + 1) * stride]
        else:
            vals = _unpack_dict(col) if isinstance(col, dict) else col
            for i in range(n):
                if vals[i] is not None:
                    rows[i][k] = vals[i]
    return rows
