from __future__ import annotations

from pathlib import Path


def _home_path() -> Path:
    return Path(__file__).resolve().parents[1] / "Home.py"


def test_home_page_renders():
    from streamlit.testing.v1 import AppTest

    app = AppTest.from_file(str(_home_path()), default_timeout=10).run()

    assert not app.exception
    assert app.title[0].value == "🦋 Monarch Model Prototype"

    text = "\n".join(
        [element.value for element in app.markdown]
        + [element.value for element in app.caption]
        + [element.value for element in app.info]
    )
    for expected in (
        "Monarch Assessment",
        "Monarch Glossary",
        "DiScO",
        "Disco Fever",
        "Discotorium",
    ):
        assert expected in text
