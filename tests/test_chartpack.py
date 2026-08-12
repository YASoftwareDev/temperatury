"""chartpack: chart-payload numeric lists <-> base64 scaled-int blobs.

The packed form must be verified-lossless (bit-exact round trip after JSON),
deterministic, and must refuse rather than degrade: any list it cannot
represent exactly stays a plain JSON list.
"""
import json
import math

import chartpack


def rt(obj):
    """Pack -> JSON -> parse -> unpack, i.e. the full production path."""
    packed = chartpack.pack_tree(obj)
    return chartpack.unpack_tree(json.loads(json.dumps(packed)))


def test_round_trip_two_decimal_temps():
    a = [19.83, -0.5, None, 20.46, 0.0, -12.34, 5.5, 7.25, 8.0]
    assert rt({"raw": {"data": a}}) == {"raw": {"data": a}}


def test_round_trip_int_years():
    a = list(range(1940, 2026))
    packed = chartpack.pack_tree({"x": a})
    assert isinstance(packed["x"], dict) and "_p" in packed["x"]
    assert packed["x"]["d"] == 0
    assert rt({"x": a}) == {"x": a}


def test_nested_lists_pack_rows():
    rows = [[1.5, None, 2.25, 3.0, -4.5, 5.0, 6.5, 7.0, 8.5, 9.0]] * 3
    out = rt({"cells": rows})
    assert out == {"cells": rows}


def test_short_lists_left_alone():
    a = [1.0, 2.0, 3.0]
    assert chartpack.pack_tree({"spark": a}) == {"spark": a}


def test_mixed_type_lists_left_alone():
    a = ["_years", 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0]
    assert chartpack.pack_tree({"x": a}) == {"x": a}


def test_large_values_take_int32():
    # degree-days can be thousands; x100 overflows int16
    a = [4321.25, 3999.5, None, 1234.75, 0.25, 999.0, 4500.0, 4000.0]
    packed = chartpack.pack_tree({"data": a})
    assert packed["data"]["w"] == 4
    assert rt({"data": a}) == {"data": a}


def test_unrepresentable_precision_left_alone():
    # 5 decimals exceeds the d<=4 budget: must stay a plain list, not round.
    a = [0.12345, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0]
    assert chartpack.pack_tree({"data": a}) == {"data": a}


def test_deterministic_bytes():
    a = [1.25, 2.5, None, -3.75, 4.0, 5.0, 6.25, 7.5]
    p1 = json.dumps(chartpack.pack_tree({"d": a}), sort_keys=True)
    p2 = json.dumps(chartpack.pack_tree({"d": list(a)}), sort_keys=True)
    assert p1 == p2


def test_sentinel_value_collision_left_alone():
    # A real value that would encode to the int16 sentinel must not become null.
    a = [-327.68, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0]
    out = rt({"data": a})
    assert out == {"data": a}          # either unpacked exactly or left alone


def test_strings_and_scalars_untouched():
    obj = {"kind": "trend", "vmin": -3.5, "label": "x", "n": 7,
           "arr": [None] * 10}
    assert rt(obj) == obj


def test_infinity_and_nan_left_alone():
    a = [math.inf, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0]
    assert chartpack.pack_tree({"data": a}) == {"data": a}


# --- columnar row packing (the _global.json ranking) -----------------------

ROWS = [
    {"n": "Nuuk", "s": "nuuk", "cc": "gl", "r": "North America",
     "pop": 14798, "t": 0.56, "dt": 4.8,
     "st": [-1.08, -0.67, -0.46, -0.01, 0.36, 0.52, 2.11, 2.49, 4.17]},
    {"n": "Kraków", "s": "krakow", "cc": "pl", "r": "Europe",
     "pop": 766683, "t": 0.31, "dt": 2.6,
     "st": [-0.5, -0.4, -0.3, -0.2, 0.0, 0.2, 0.4, 0.6, 0.8]},
] * 8


def test_rows_round_trip():
    packed = chartpack.pack_rows(ROWS)
    assert isinstance(packed, dict) and "_cols" in packed
    assert chartpack.unpack_rows(json.loads(json.dumps(packed))) == ROWS


def test_rows_with_a_missing_key_round_trip():
    rows = [dict(r) for r in ROWS]
    del rows[3]["st"]
    del rows[5]["pop"]
    assert chartpack.unpack_rows(
        json.loads(json.dumps(chartpack.pack_rows(rows)))) == rows


def test_rows_numeric_columns_are_packed():
    packed = chartpack.pack_rows(ROWS)
    assert "_p" in packed["_cols"]["t"], "numeric column should pack"
    assert "_p" in packed["_cols"]["st"], "fixed-stride lists should pack flat"
    assert isinstance(packed["_cols"]["n"], list), "strings stay plain"


def test_rows_unpackable_shape_falls_back_to_plain():
    # A None-valued key and a ragged nested list are both representable -
    # verified round trip - but a row value the codec cannot express exactly
    # (5-decimal float) must keep its column plain rather than round.
    rows = [dict(r) for r in ROWS]
    rows[0]["t"] = 0.12345
    packed = chartpack.pack_rows(rows)
    assert chartpack.unpack_rows(json.loads(json.dumps(packed))) == rows


def test_rows_smaller_than_plain():
    plain = len(json.dumps(ROWS, separators=(",", ":")))
    packed = len(json.dumps(chartpack.pack_rows(ROWS), separators=(",", ":")))
    assert packed < plain * 0.8
