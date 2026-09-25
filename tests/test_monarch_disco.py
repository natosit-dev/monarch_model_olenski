from __future__ import annotations

from pathlib import Path

from monarch.disco import inspect_sentence_cadence, inspect_text, load_rules


def _page_path() -> Path:
    return Path(__file__).resolve().parents[1] / "pages" / "30_DiScO_Text_Evaluator.py"


def test_disco_text_profile_is_deterministic():
    text = (
        "It is important to note that this robust strategic framework can leverage "
        "an integrated architecture and move the needle."
    )
    rules = load_rules()
    first = inspect_text(text, rules=rules)
    second = inspect_text(text, rules=rules)

    assert first.as_dict() == second.as_dict()
    assert first.word_count > 0
    assert 0 <= first.signal_score <= 1
    assert 0 <= first.ai_signal_score <= 1

    by_id = {feature.id: feature for feature in first.features}
    assert by_id["ready_made_phrases"].count >= 1
    assert by_id["prestige_diction"].count >= 1
    assert by_id["mechanism_placeholders"].count >= 1
    assert by_id["dead_metaphors"].count >= 1


def test_disco_includes_supplemental_ai_style_rules():
    profile = inspect_text("Here's the thing: this is not just useful, but important. The key point is clarity.")
    by_id = {feature.id: feature for feature in profile.features}

    assert by_id["pseudo_conversational_setup"].count >= 1
    assert by_id["contrastive_reframing"].count >= 1
    assert by_id["formulaic_signposting"].count >= 1


def test_sentence_cadence_is_separate_and_unscored():
    cadence = inspect_sentence_cadence("Short sentence. This sentence is somewhat longer than the first one.")
    assert cadence.sentence_count == 2
    assert cadence.sentence_lengths[0] < cadence.sentence_lengths[1]
    assert cadence.range_words > 0


def test_disco_page_renders_without_disco_inferno_dependencies():
    from streamlit.testing.v1 import AppTest

    app = AppTest.from_file(str(_page_path()), default_timeout=10).run()
    assert not app.exception
    assert app.title[0].value == "🪩 DiScO — Text Evaluator"
    assert any(area.label == "Text to inspect" for area in app.text_area)
    assert any(button.label == "⚖️ JUDGEMENT" for button in app.button)
