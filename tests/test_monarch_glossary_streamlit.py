from __future__ import annotations

from pathlib import Path

from monarch.glossary import GLOSSARY_SOURCE_URL, MONARCH_GLOSSARY


def _page_path() -> Path:
    return Path(__file__).resolve().parents[1] / "pages" / "20_Monarch_Glossary.py"


def test_glossary_data_contains_expected_terms_and_reference():
    terms = [term for term, _definition in MONARCH_GLOSSARY]
    assert terms == [
        "Lived Experience",
        "Human Agency",
        "Determinants of Agency",
        "Human Nervous System",
        "Physical Capital",
        "Social Capital",
        "Intellectual Capital",
        "Friction",
        "Intentional Listening",
        "Governance",
    ]
    assert GLOSSARY_SOURCE_URL == "https://www.monarchfutures.com/themonarchmodeltextonly"


def test_glossary_page_renders_all_terms():
    from streamlit.testing.v1 import AppTest

    app = AppTest.from_file(str(_page_path()), default_timeout=10).run()

    assert not app.exception
    assert app.title[0].value == "Monarch Model — Glossary"

    rendered_markdown = [element.value for element in app.markdown]
    for term, _definition in MONARCH_GLOSSARY:
        assert any(term in value for value in rendered_markdown)
