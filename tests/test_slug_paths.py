"""Every slug is used verbatim as a filename and a URL path segment.

A slug containing a path separator does not fail loudly: the fetch succeeds and
spends quota, the write raises deep inside a per-city handler that swallows it,
and the city is silently re-queued on every future round - permanently absent
from the site while costing quota forever. Two Basque cities did exactly that
("Donostia / San Sebastián", "Gasteiz / Vitoria") and had never once been
gathered.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import codec
import config
import data


def test_no_slug_contains_a_path_separator():
    bad = {l.slug: l.name for l in config.LOCATIONS.values()
           if "/" in l.slug or "\\" in l.slug}
    assert not bad, f"slugs that would become directories: {bad}"


def test_every_cache_path_stays_directly_under_the_data_dir():
    """The real consequence, checked on the real path builder."""
    for loc in config.LOCATIONS.values():
        p = data._cache_path(loc, 1940, 2025)
        assert p.parent == config.DATA_DIR, f"{loc.name} escapes data/: {p}"
        assert p.name.endswith(codec.SUFFIX)


def test_no_two_roster_names_collapse_to_the_same_slug():
    """Checked on the RAW source rows, not on LOCATIONS.

    config builds LOCATIONS with setdefault, so a collision has already silently
    dropped one city by the time it is a dict - inspecting LOCATIONS can never
    see it. Slugify folds accents, punctuation and now "/", so distinct names
    can converge; at a 32k roster that is a real way to lose a city without
    any error. Pin it at the source.
    """
    import collections

    names = [n for _, n, _, _, _ in config._CITIES]
    tsv = config.ROOT / "cities750k.tsv"
    if tsv.exists():
        names += [r.split("\t")[1]
                  for r in tsv.read_text(encoding="utf-8").splitlines() if r.strip()]
    counts = collections.Counter(config.slugify(n) for n in names)
    collisions = {s: [n for n in names if config.slugify(n) == s]
                  for s, c in counts.items() if c > 1}
    assert not collisions, f"names collapsing to one slug: {collisions}"


def test_every_alias_resolves_to_a_location():
    """config drops an alias whose primary is not in LOCATIONS, so a slug change
    that misses city_aliases.tsv silently loses searchable places."""
    rows = [r.split("\t") for r in
            (config.ROOT / "city_aliases.tsv").read_text(encoding="utf-8").splitlines()
            if r.strip()]
    orphans = {r[0] for r in rows if r[0] not in config.LOCATIONS}
    assert not orphans, f"alias rows pointing at unknown primaries: {sorted(orphans)[:10]}"


@pytest.mark.parametrize("name,expected", [
    ("Donostia / San Sebastián", "donostia-san-sebastian"),
    ("Gasteiz / Vitoria", "gasteiz-vitoria"),
    ("Warszawa", "warszawa"),
    ("N'Djamena", "n'djamena"),
])
def test_slugify_examples(name, expected):
    """Pins the two repaired names without disturbing the existing forms other
    slugs (apostrophes, plain names) already rely on."""
    assert config.slugify(name) == expected
