import warnings

import pandas as pd

from services.semantic_column_classifier import SemanticColumnClassifier


def test_datetime_parser_supports_iso_and_italian_formats_without_guessing_warning():
    classifier = SemanticColumnClassifier()
    values = pd.Series([
        "2026-07-29",
        "29/07/2026",
        "29/07/2026 14:35",
        "2026-07-29T14:35:00",
        "not-a-date",
    ])

    with warnings.catch_warnings(record=True) as captured:
        warnings.simplefilter("always")
        parsed = classifier._parse_datetime_candidate(values)

    assert parsed.notna().tolist() == [True, True, True, True, False]
    assert not [item for item in captured if "Could not infer format" in str(item.message)]


def test_datetime_parser_does_not_silently_swap_italian_day_and_month():
    parsed = SemanticColumnClassifier()._parse_datetime_candidate(pd.Series(["03/07/2026"]))

    assert parsed.iloc[0] == pd.Timestamp("2026-07-03")
