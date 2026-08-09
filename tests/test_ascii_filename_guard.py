"""daily-chunk's non-ASCII filename guard must not depend on the shell's locale.

The send step drops files whose names are not pure ASCII (the archive fallback
and some contributors' filesystems cannot carry them). It spells that as a glob
bracket range::

    case "$f" in *[!\\ -~]*) continue ;; esac

Bracket ranges are compared in COLLATION order outside the C locale, not ASCII
order, so under a UTF-8 locale ``[ -~]`` need not contain every printable ASCII
character. bash >= 5.0 masks this by defaulting ``globasciiranges`` on; bash 4.3
defaults it off, and there that made the guard reject *every* ordinary
filename: a gatherer downloaded 28 cities, discarded all 28 as "non-ASCII", and
printed only "Nothing new to send" - a silent total data loss that looked like a
successful run.

These tests pin both halves of the contract under the hostile setting
(``globasciiranges`` explicitly off), which is what bash 4.3 does natively:
ordinary names survive, genuinely non-ASCII names are still rejected.
"""
import shutil
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parent.parent / "tools" / "daily-chunk.sh"

# Real filenames from the run that exposed the bug, plus the punctuation the
# older curated slugs rely on (apostrophes, parentheses) which must also pass.
ASCII_NAMES = [
    "data/central-coast_1940-2025_extremes.csv.gz",
    "data/las-vegas_1940-2025_extremes.csv.gz",
    "data/chula-vista_1940-2025_extremes.csv.gz",
    "data/n'djamena_1940-2025.csv.gz",
    "data/barcelona-(ve)_1940-2025_precip.csv.gz",
    "data/6th-of-october-city_1940-2025.csv.gz",
]

NON_ASCII_NAMES = [
    "data/bến-cát_1940-2025.csv.gz",
    "data/ōsaki_1940-2025_extremes.csv.gz",
    "data/жуковский_1940-2025.csv.gz",
]

# `globasciiranges` off reproduces bash 4.3's native behaviour on bash 5.x too,
# so this test is meaningful on a modern developer machine and on CI alike.
_GUARD = r"""
shopt -u globasciiranges
{fix}
case "$1" in *[!\ -~]*) echo NONASCII ;; *) echo ASCII ;; esac
"""


def _classify(name: str, *, with_fix: bool) -> str:
    fix = "shopt -s globasciiranges 2>/dev/null || true" if with_fix else ""
    out = subprocess.run(
        ["bash", "-c", _GUARD.format(fix=fix), "_", name],
        capture_output=True, text=True, check=True,
    )
    return out.stdout.strip()


@pytest.mark.parametrize("name", ASCII_NAMES)
def test_ascii_names_survive_the_guard(name):
    """The regression itself: these must never be mistaken for non-ASCII."""
    assert _classify(name, with_fix=True) == "ASCII"


@pytest.mark.parametrize("name", NON_ASCII_NAMES)
def test_non_ascii_names_are_still_rejected(name):
    """The fix must not disarm the guard it repairs."""
    assert _classify(name, with_fix=True) == "NONASCII"


def test_without_the_fix_the_guard_really_does_misfire():
    """Guards the guard: if this stops failing, the test proves nothing.

    Should bash ever change so that a bare range is ASCII-ordered regardless of
    `globasciiranges`, this test fails and tells us the parametrised ones above
    have quietly become vacuous.
    """
    assert _classify(ASCII_NAMES[0], with_fix=False) == "NONASCII"


def test_daily_chunk_sets_globasciiranges_before_using_a_range():
    """The shopt must precede the guard, or it fixes nothing."""
    text = SCRIPT.read_text()
    assert "shopt -s globasciiranges" in text, "the locale-proofing shopt is gone"
    assert text.index("shopt -s globasciiranges") < text.index(r"*[!\ -~]*"), \
        "shopt must come before the first bracket-range pattern"


def test_script_is_bash_not_sh():
    """`shopt` is a bash builtin; a /bin/sh shebang would silently skip it."""
    assert shutil.which("bash"), "bash is required to run the gatherer"
    assert SCRIPT.read_text().splitlines()[0] == "#!/bin/bash"
