"""The long-record note: one element, with text in it.

"Why is there no data before 1940?" is answered once, in the Q&A tab. What stays
on a city page is only the per-city fact that this place holds one of the world's
long instrumental records - and only for the few cities that do.

The trap this pins: ``deephist_record`` USED to carry its own ``<p>``, wrapped in
a second one. Nested ``<p>`` is invalid, so the parser closed the outer element -
leaving an empty note, the text as a sibling, and a stray empty paragraph - while
the CSS still only matched the retired ``details.deephist`` ancestor, so the line
rendered unstyled. Nothing threw, no chart broke, and 178 other tests stayed
green through it, which is why this asserts the PARENT-CHILD relationship, the
rendered text, and the COMPUTED STYLE rather than the markup.
"""
import pytest
from playwright.sync_api import sync_playwright

import deephist
import i18n
import i18ndict
import report
from tests.conftest import build

RECORD_CITY = "london"      # deephist.RECORDS: Central England (HadCET), 1659
PLAIN_CITY = "krakow"       # no long instrumental record


def _note(uri, switch_to=None):
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(locale="en-GB")
        pg.route("**/*", lambda r: r.abort()
                 if r.request.url.startswith(("http://", "https://"))
                 else r.continue_())
        pg.goto(uri, wait_until="domcontentloaded")
        pg.wait_for_timeout(200)
        if switch_to:
            pg.evaluate(f"window.__setLang({switch_to!r})")
            pg.wait_for_function(
                f"document.documentElement.lang === {switch_to!r}", timeout=4000)
            pg.wait_for_timeout(150)
        data = pg.evaluate("""() => {
          const notes = [...document.querySelectorAll('.deephist-note')];
          const inner = document.querySelector('.deephist-note .dh-here');
          const cs = inner ? getComputedStyle(inner) : null;
          return {
            count: notes.length,
            text: notes.map(n => n.textContent.trim().replace(/\\s+/g, ' ')),
            // the regression made .dh-here a SIBLING of an empty note
            nested: !!inner,
            strays: [...document.querySelectorAll('p')]
                      .filter(p => !p.textContent.trim() && !p.children.length).length,
            // the CSS only ever matched `details.deephist .dh-here`; once the
            // <details> went away the note shipped unstyled - body size, full
            // ink, no accent rule - which is what visitors actually saw.
            border: cs ? cs.borderInlineStartWidth : null,
            fontPx: cs ? parseFloat(cs.fontSize) : null,
            bodyFontPx: parseFloat(getComputedStyle(document.body).fontSize)
          };
        }""")
        b.close()
        return data


def test_the_pre_1940_explanation_lives_only_in_the_qa_tab():
    """The move's whole point. The explainer text must be in _ABOUT_QA and must no
    longer be a string the city page can render."""
    answers = " ".join(a for _q, a in report._ABOUT_QA)
    assert "1940" in answers and "ERA5" in answers, "the Q&A lost the explanation"
    # EVERY language, not just English: the curated table in deephist.py covers 21
    # languages and extra_i18n.fill backfills the other 111 from
    # i18n_data/_dashboard_mt.json. Deleting the keys from the curated table alone
    # left 111 languages still shipping the moved explainer in their dictionary,
    # and an English-only check passed straight through it.
    leaked = {lang: sorted(k for k in ("deephist_title", "deephist_body")
                           if k in i18ndict.merged_table(lang))
              for lang in i18n.LANGUAGES}
    leaked = {k: v for k, v in leaked.items() if v}
    assert not leaked, \
        f"the moved explainer is still shipped to {len(leaked)} languages: " \
        f"{dict(list(leaked.items())[:5])}"
    # Asserted against the SOURCE table, not merged_table: overlay() backfills
    # English into every language, so "the key is present after merging" is true
    # by construction and would pass even if a language lost its translation.
    fellback = [lang for lang in i18n.LANGUAGES
                if "deephist_record" not in deephist._TEXT.get(lang, {})]
    assert not fellback, f"{len(fellback)} languages fall back to English: {fellback[:10]}"


def test_no_translation_carries_the_notes_markup():
    """Structure belongs to the template, words to the dictionary.

    While `<p class="dh-here">` was part of the translated value, the machine
    translator relocated it in 39 of 132 languages - closing the tag mid-sentence
    or opening it after a leading word - so part of the note rendered outside the
    styled block. Plain values make that impossible, and the {label}/{year}
    placeholders must survive for the line to say anything.
    """
    offenders, no_label, no_year = [], [], []
    for lang in i18n.LANGUAGES:
        s = deephist.overlay({}, lang)["deephist_record"]
        if "<" in s or ">" in s:
            offenders.append(lang)
        if "{label}" not in s:
            no_label.append(lang)
        if "{year}" not in s:      # the translator does drop numerals elsewhere
            no_year.append(lang)
    assert not offenders, \
        f"{len(offenders)} translations carry markup: {offenders[:10]}"
    assert not no_label, f"{len(no_label)} translations lost {{label}}: {no_label[:10]}"
    assert not no_year, f"{len(no_year)} translations lost {{year}}: {no_year[:10]}"


@pytest.mark.slow
def test_long_record_note_renders_as_one_element_with_text():
    out = build(RECORD_CITY, "en", client_i18n=True)
    rec = deephist.record_for(RECORD_CITY)
    assert rec, f"{RECORD_CITY} has no record entry"
    label = rec[0]
    n = _note((out / "en" / f"{RECORD_CITY}.html").as_uri())
    assert n["count"] == 1, f"expected exactly one note, got {n['count']}"
    assert n["nested"], \
        "the record line is not inside the note (invalid nesting split them apart)"
    assert label.split()[0] in n["text"][0], \
        f"note does not name the record: {n['text']}"
    assert n["strays"] == 0, "an empty paragraph was left in the page"
    assert n["border"] == "3px", \
        f"the accent rule in page.src.css is not applying (border={n['border']})"
    assert n["fontPx"] < n["bodyFontPx"], \
        f"note renders at body size ({n['fontPx']}px), so its rule is not applying"


@pytest.mark.slow
def test_a_city_without_a_record_shows_no_note():
    out = build(PLAIN_CITY, "en", client_i18n=True)
    n = _note((out / "en" / f"{PLAIN_CITY}.html").as_uri())
    assert n["count"] == 0, "a city with no long record must show nothing here"


@pytest.mark.slow
def test_the_note_follows_a_language_switch():
    """The client-i18n carrier. With an empty carrier the runtime had nothing to
    replace, so the note either stayed English or the translation landed in a node
    the visitor could not see."""
    out = build(RECORD_CITY, "en,pl", client_i18n=True)
    uri = (out / "en" / f"{RECORD_CITY}.html").as_uri()
    before = _note(uri)
    after = _note(uri, switch_to="pl")
    assert after["count"] == 1 and after["nested"], \
        "the note lost its structure on a language switch"
    assert after["text"][0], "the note went empty on a language switch"
    assert after["text"][0] != before["text"][0], \
        f"the note did not localise: {before['text']} -> {after['text']}"
    # Compared in FULL. Substring-matching a prefix of the template was vacuous:
    # the Polish string starts with "{label}", so the prefix was the empty string
    # and the assertion held for any text at all.
    rec = deephist.record_for(RECORD_CITY)
    assert rec, f"{RECORD_CITY} lost its record entry"
    pl_expected = deephist.overlay({}, "pl")["deephist_record"].format(
        label=rec[0], year=rec[1])
    assert after["text"][0] == pl_expected, (
        f"switched text is not the Polish record line:\n"
        f"  got  {after['text'][0]!r}\n  want {pl_expected!r}")
