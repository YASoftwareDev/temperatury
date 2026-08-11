"""Strip/merge chart-payload fields against the committed charts_spec.json.

Fields identical across cities (axis labels, colors, chart kinds - measured
~10.8 KB of strings/structure per 34 KB payload) live ONCE in charts_spec.json;
each city's JSON keeps only what differs. The client (assets/charts.js
__mergeChartSpec) fills missing keys back in before rendering. Strip is
equality-gated: a field is removed only when deep-equal to the spec value, so
merge (which only fills MISSING keys) is exactly inverse and a divergent city
keeps its own value. Reserved _-keys (_years, _range, _records, _labels) are
never touched. Spec values contain no lists by construction (gen_chart_spec).
"""
from __future__ import annotations


class _Missing:
    pass


_MISSING = _Missing()


def strip(city: dict, spec: dict) -> dict:
    """Return a copy of ``city`` minus fields equal to their spec values."""
    out = {}
    for chart_id, payload in city.items():
        s = spec.get(chart_id)
        if (chart_id.startswith("_") or s is None
                or not isinstance(payload, dict)):
            out[chart_id] = payload
            continue
        out[chart_id] = _strip_node(payload, s)
    return out


def _strip_node(node: dict, spec_node: dict) -> dict:
    kept = {}
    for k, v in node.items():
        sv = spec_node.get(k, _MISSING)
        if sv is _MISSING:
            kept[k] = v
        elif isinstance(v, dict) and isinstance(sv, dict):
            sub = _strip_node(v, sv)
            if sub:
                kept[k] = sub
        elif v == sv and type(v) is type(sv):
            continue                      # spec carries it
        else:
            kept[k] = v
    return kept


def merge(city: dict, spec: dict) -> dict:
    """Fill spec fields back into ``city`` in place (missing keys only)."""
    for chart_id, s in spec.items():
        payload = city.get(chart_id)
        if isinstance(payload, dict):
            _merge_node(payload, s)
    return city


def _merge_node(node: dict, spec_node: dict) -> None:
    for k, sv in spec_node.items():
        if k not in node:
            node[k] = sv
        elif isinstance(node[k], dict) and isinstance(sv, dict):
            _merge_node(node[k], sv)
