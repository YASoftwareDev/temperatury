"""Every language's client-i18n dictionary must cover every key English defines.

A missing key would render an empty element in the browser, so this guards the
core invariant of the R1-hybrid design. Pure Python, fast (no build).
"""
import i18n
import i18ndict  # created in Phase 1; this import fails until then


def test_every_lang_dict_covers_ui_keys():
    en = i18ndict.merged_table("en")
    assert en, "English dictionary is empty"
    for lang in i18n.LANGUAGES:
        d = i18ndict.merged_table(lang)
        missing = [k for k in en if k not in d]
        assert not missing, f"{lang} dict missing keys: {missing[:10]}"


def test_dict_values_are_strings():
    for lang in i18n.LANGUAGES:
        d = i18ndict.merged_table(lang)
        bad = [k for k, v in d.items() if not isinstance(v, str)]
        assert not bad, f"{lang} has non-string values: {bad[:10]}"
