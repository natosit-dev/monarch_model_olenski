from __future__ import annotations

from connectathon.gravity_questionnaire import QUESTIONNAIRE_VERSION, build_questionnaire
from connectathon.gravity_response import answer_absent_reason, build_questionnaire_response, find_response_items, first_answer
from monarch.questionnaire.scope import scope_allows


PATIENT_ID = "PAT-MONARCH-001"
BASELINE_INPUT = {
    "sleep-hours": "6.5",
    "pain-score": 4,
    "phq2-interest": "LA6569-3",
    "phq2-depressed": "LA6568-5",
    "heart-rate": "82",
    "medication-status": True,
    "medications": [{"name": "lisinopril", "dose_value": "10", "dose_unit": "mg", "route": "oral", "frequency": "daily"}],
    "feeling-today": "Tired, but pretty steady today.",
    "life-today": "My mom has an appointment and work is busy.",
}


def _top(questionnaire):
    return {item["linkId"]: item for item in questionnaire["item"]}


def test_modular_adapter_preserves_baseline_answer_semantics():
    response = build_questionnaire_response(PATIENT_ID, BASELINE_INPUT, response_id="monarch-refactor-test", authored="2026-09-24T20:00:00+00:00")
    assert first_answer(response, "sleep-hours")["valueQuantity"]["value"] == 6.5
    assert first_answer(response, "pain-score") == {"valueInteger": 4}
    assert first_answer(response, "phq2-interest")["valueCoding"]["code"] == "LA6569-3"
    assert first_answer(response, "heart-rate")["valueQuantity"]["value"] == 82.0
    assert first_answer(response, "medication-status") == {"valueBoolean": True}
    assert first_answer(response, "feeling-today") == {"valueString": BASELINE_INPUT["feeling-today"]}
    assert first_answer(response, "life-today") == {"valueString": BASELINE_INPUT["life-today"]}


def test_monarch_questionnaire_has_scope_and_new_capacity_sections():
    questionnaire = build_questionnaire()
    items = _top(questionnaire)
    assert QUESTIONNAIRE_VERSION == "0.3"
    for link_id in (
        "assessment-scope",
        "financial-unexpected-100",
        "financial-current-savings",
        "care-hours-per-day",
        "safe-absence-mode",
        "safe-absence-hours",
        "home-safety",
        "interaction-unsafe",
        "context-artifact-text",
    ):
        assert link_id in items
    assert items["home-safety"]["repeats"] is True


def test_scope_filters_questions_in_questionnaire_response():
    raw = dict(BASELINE_INPUT)
    raw["assessment-scope"] = "basics"
    raw["financial-unexpected-100"] = "no"
    response = build_questionnaire_response(PATIENT_ID, raw)
    assert first_answer(response, "sleep-hours") is not None
    assert find_response_items(response, "financial-unexpected-100") == []
    assert find_response_items(response, "heart-rate") == []


def test_scope_metadata_orders_high_level_after_basics():
    items = _top(build_questionnaire())
    assert scope_allows(items["sleep-hours"], "basics") is True
    assert scope_allows(items["financial-unexpected-100"], "basics") is False
    assert scope_allows(items["financial-unexpected-100"], "high_level") is True
    assert scope_allows(items["financial-current-savings"], "high_level") is False
    assert scope_allows(items["financial-current-savings"], "full") is True


def test_unsure_multiselect_and_varies_remain_explicit_coded_answers():
    raw = dict(BASELINE_INPUT)
    raw.update(
        {
            "assessment-scope": "high_level",
            "financial-unexpected-100": "unsure",
            "safe-absence-mode": "varies",
            "home-safety": ["medication-support", "emergency-alert"],
        }
    )
    response = build_questionnaire_response(PATIENT_ID, raw)
    assert first_answer(response, "financial-unexpected-100")["valueCoding"]["code"] == "unsure"
    assert first_answer(response, "safe-absence-mode")["valueCoding"]["code"] == "varies"
    assert find_response_items(response, "safe-absence-hours") == []
    safety = find_response_items(response, "home-safety")[0]["answer"]
    assert [answer["valueCoding"]["code"] for answer in safety] == ["medication-support", "emergency-alert"]


def test_safe_absence_hours_are_quantity_only_when_hours_selected():
    raw = dict(BASELINE_INPUT)
    raw.update({"assessment-scope": "high_level", "safe-absence-mode": "hours", "safe-absence-hours": "2.5"})
    response = build_questionnaire_response(PATIENT_ID, raw)
    answer = first_answer(response, "safe-absence-hours")
    assert answer["valueQuantity"]["value"] == 2.5
    assert answer["valueQuantity"]["code"] == "h"


def test_exact_financial_amounts_are_optional_full_scope_decimals_and_decline_is_distinct():
    raw = dict(BASELINE_INPUT)
    raw.update({"assessment-scope": "full", "financial-current-savings": "2500", "financial-current-debt": ""})
    response = build_questionnaire_response(PATIENT_ID, raw, declined={"financial-current-debt"})
    assert first_answer(response, "financial-current-savings") == {"valueDecimal": 2500.0}
    assert answer_absent_reason(first_answer(response, "financial-current-debt")) == "asked-declined"


def test_raw_context_is_preserved_without_interpretation():
    raw = dict(BASELINE_INPUT)
    raw.update({"assessment-scope": "high_level", "context-artifact-text": "I am exhausted and juggling three appointments."})
    response = build_questionnaire_response(PATIENT_ID, raw)
    assert first_answer(response, "context-artifact-text") == {"valueString": raw["context-artifact-text"]}
