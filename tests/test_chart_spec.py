"""charts_spec.json: shared constant chart fields, stripped per city and
merged back client-side. Strip must be equality-gated and exactly invertible."""
import json
from pathlib import Path

import chartspec


SPEC = {"yearly-trend": {"kind": "trend", "tk": "abs", "xlabel": "Year",
                         "raw": {"color": "#94a3b8", "style": "point"}}}


def test_strip_removes_only_spec_equal_fields():
    city = {"yearly-trend": {"kind": "trend", "tk": "abs", "xlabel": "Year",
                             "raw": {"color": "#94a3b8", "style": "point",
                                     "data": [1, 2, 3]},
                             "ylabel": "city-specific"}}
    stripped = chartspec.strip(city, SPEC)
    yt = stripped["yearly-trend"]
    assert "kind" not in yt and "tk" not in yt and "xlabel" not in yt
    assert yt["ylabel"] == "city-specific"
    assert yt["raw"] == {"data": [1, 2, 3]}


def test_strip_keeps_divergent_values():
    city = {"yearly-trend": {"kind": "trend", "xlabel": "Rok"}}
    assert chartspec.strip(city, SPEC)["yearly-trend"]["xlabel"] == "Rok"


def test_merge_inverts_strip():
    city = {"yearly-trend": {"kind": "trend", "tk": "abs", "xlabel": "Year",
                             "raw": {"color": "#94a3b8", "style": "point",
                                     "data": [1.5, 2.5]},
                             "trend": {"perDecade": 0.3}},
            "_years": [1940, 1941]}
    round_tripped = chartspec.merge(
        json.loads(json.dumps(chartspec.strip(city, SPEC))), SPEC)
    assert round_tripped == city


def test_underscore_keys_never_stripped():
    city = {"_years": [1940], "_labels": [["a", []]]}
    assert chartspec.strip(city, SPEC) == city


def test_bool_int_aliasing_not_stripped():
    # JSON True == 1 in Python; a type mismatch must not count as spec-equal.
    spec = {"c": {"diverging": True}}
    city = {"c": {"diverging": 1}}
    assert chartspec.strip(city, spec) == city


def test_committed_spec_is_valid():
    spec = json.loads(Path(__file__).resolve().parent.parent
                      .joinpath("charts_spec.json").read_text(encoding="utf-8"))
    assert spec, "spec must not be empty"

    def no_lists(node):
        assert not isinstance(node, list)
        if isinstance(node, dict):
            for v in node.values():
                no_lists(v)
    for chart_id, fields in spec.items():
        assert not chart_id.startswith("_")
        no_lists(fields)
