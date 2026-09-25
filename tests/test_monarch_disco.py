from __future__ import annotations

from io import BytesIO
from pathlib import Path
import zipfile

from monarch.disco import (
    FeatureRule,
    extract_document_text,
    inspect_document_artifact,
    inspect_sentence_cadence,
    inspect_text,
    load_judgements,
    load_rules,
    record_judgement,
    reset_rules,
    save_rules,
)


def _page(name: str) -> Path:
    return Path(__file__).resolve().parents[1] / "pages" / name


def _minimal_docx() -> bytes:
    core = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties"
 xmlns:dc="http://purl.org/dc/elements/1.1/"
 xmlns:dcterms="http://purl.org/dc/terms/"
 xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <dc:creator>Casey Caregiver</dc:creator>
  <cp:lastModifiedBy>Editor Example</cp:lastModifiedBy>
  <dcterms:created xsi:type="dcterms:W3CDTF">2026-09-24T12:00:00Z</dcterms:created>
  <dcterms:modified xsi:type="dcterms:W3CDTF">2026-09-24T13:00:00Z</dcterms:modified>
</cp:coreProperties>"""
    app = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties">
  <Application>Microsoft Office Word</Application>
  <TotalTime>12</TotalTime>
  <Words>8</Words>
</Properties>"""
    document = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body><w:p><w:r><w:t>This is a provenance test document.</w:t></w:r></w:p></w:body>
</w:document>"""
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("docProps/core.xml", core)
        archive.writestr("docProps/app.xml", app)
        archive.writestr("word/document.xml", document)
    return buffer.getvalue()


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


def test_judgement_history_preserves_feedback_label_and_rule_snapshot(tmp_path):
    rules = load_rules()
    text = "The key point is that this robust framework matters."
    profile = inspect_text(text, rules=rules)
    path = tmp_path / "judgements.jsonl"

    record = record_judgement(
        text=text,
        profile=profile,
        ai_generated=True,
        rules=rules,
        path=path,
    )
    loaded = load_judgements(path)

    assert len(loaded) == 1
    assert loaded[0]["judgement_id"] == record["judgement_id"]
    assert loaded[0]["ai_generated"] is True
    assert loaded[0]["text"] == text
    assert loaded[0]["rules_sha256"]
    assert loaded[0]["rules"]
    assert loaded[0]["sentence_cadence"]["sentence_count"] >= 1


def test_disco_fever_rule_override_round_trip(tmp_path):
    path = tmp_path / "rules.json"
    baseline = load_rules(path=path)
    original = baseline[0]
    changed = FeatureRule(
        id=original.id,
        label=original.label,
        kind=original.kind,
        semantic_max=min(original.semantic_max + 0.01, 1.0),
        ai_max=original.ai_max,
        half_saturation=original.half_saturation,
        terms=original.terms,
        pattern=original.pattern,
    )
    configured = (changed, *baseline[1:])

    save_rules(configured, path=path)
    loaded = load_rules(path=path)
    assert loaded[0].semantic_max == changed.semantic_max

    reset_rules(path=path)
    assert not path.exists()
    assert load_rules(path=path)[0] == original


def test_docx_upload_text_and_provenance_work_without_external_checkout():
    data = _minimal_docx()
    text = extract_document_text(data, "example.docx")
    artifact = inspect_document_artifact(data, "example.docx")

    assert "provenance test document" in text
    assert artifact["filename"] == "example.docx"
    assert artifact["doc_history"]["type"] == "docx"
    core = artifact["doc_history"]["embedded_metadata"]["core"]
    assert core["creator"] == "Casey Caregiver"
    assert core["last_modified_by"] == "Editor Example"
    assert any("Embedded creator" in clue for clue in artifact["provenance_clues"])
    assert len(artifact["timeline_events"]) >= 2


def test_disco_page_renders_full_suite_entry_point():
    from streamlit.testing.v1 import AppTest

    app = AppTest.from_file(str(_page("30_DiScO_Text_Evaluator.py")), default_timeout=10).run()
    assert not app.exception
    assert app.title[0].value == "🪩 DiScO"
    assert any(radio.label == "Input source" for radio in app.radio)
    assert any(area.label == "Free text" for area in app.text_area)
    assert any(box.label == "AI generated" for box in app.checkbox)
    assert any(button.label == "⚖️ JUDGEMENT" for button in app.button)


def test_disco_fever_page_renders():
    from streamlit.testing.v1 import AppTest

    app = AppTest.from_file(str(_page("31_Disco_Fever.py")), default_timeout=10).run()
    assert not app.exception
    assert app.title[0].value == "🕺 Disco Fever"
    assert any(button.label == "🔥 SAVE FEVER SETTINGS" for button in app.button)


def test_discotorium_page_renders_empty_corpus_state():
    from streamlit.testing.v1 import AppTest

    app = AppTest.from_file(str(_page("32_Discotorium.py")), default_timeout=10).run()
    assert not app.exception
    assert app.title[0].value == "🏛️ Discotorium"
