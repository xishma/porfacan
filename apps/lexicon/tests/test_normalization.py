from apps.lexicon.normalization import normalize_persian


def test_normalize_persian_meymoon_no_false_zwnj():
    assert normalize_persian("میمون") == "میمون"
    assert normalize_persian("می مون") == "میمون"
    assert normalize_persian("می\u00a0مون") == "میمون"


def test_normalize_persian_verbs_keep_mi_zwnj():
    assert "\u200c" in normalize_persian("میروم")
    assert "\u200c" in normalize_persian("می روم")
    assert "\u200c" in normalize_persian("نمیدانم")


def test_normalize_persian_does_not_glue_mi_inside_words():
    out = normalize_persian("قدیمی فارسی.")
    assert "فارسی" in out
    assert "قدیمیفارسی" not in out
