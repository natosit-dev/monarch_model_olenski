from __future__ import annotations

from connectathon.gravity_materialize import build_submission_bundle, bundle_resources
from connectathon.gravity_quality import caregiver_quality_gate
from connectathon.gravity_questionnaire import DEFAULT_CURRENCY, ISO_4217_SYSTEM, QUESTIONNAIRE_VERSION, UCUM_SYSTEM, build_questionnaire
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


def test_exact_financial_amounts_default_to_usd_and_decline_is_distinct():
    raw = dict(BASELINE_INPUT)
    raw.update({"assessment-scope": "full", "financial-current-savings": "2500", "financial-current-debt": ""})
    response = build_questionnaire_response(PATIENT_ID, raw, declined={"financial-current-debt"})
    assert first_answer(response, "financial-current-savings") == {
        "valueQuantity": {
            "value": 2500.0,
            "unit": DEFAULT_CURRENCY,
            "system": ISO_4217_SYSTEM,
            "code": DEFAULT_CURRENCY,
        }
    }
    assert answer_absent_reason(first_answer(response, "financial-current-debt")) == "asked-declined"


def test_raw_context_is_preserved_without_interpretation():
    raw = dict(BASELINE_INPUT)
    raw.update({"assessment-scope": "high_level", "context-artifact-text": "I am exhausted and juggling three appointments."})
    response = build_questionnaire_response(PATIENT_ID, raw)
    assert first_answer(response, "context-artifact-text") == {"valueString": raw["context-artifact-text"]}


PATIENT = {
    "patient_id": PATIENT_ID,
    "patient_name": "CAREGIVER, CASEY",
    "date_of_birth": "1982-03-14",
    "sex": "F",
    "phone": "555-0100",
    "address": "1 Test Way",
    "city": "Lowell",
    "state": "MA",
    "zip": "01852",
}


def _full_monarch_input():
    raw = dict(BASELINE_INPUT)
    raw.update(
        {
            "assessment-scope": "full",
            "interaction-unsafe": "",
            "question-boundaries": "",
            "support-person": "unsure",
            "communication-preferences": "",
            "difficult-situations": "",
            "stop-return-preference": "continue",
            "financial-unexpected-100": "yes",
            "financial-unexpected-500": "yes",
            "financial-miss-week-work": "yes",
            "financial-healthcare-cost-difficulty": "no",
            "financial-debt-affects-care": "unsure",
            "financial-current-savings": "16000",
            "financial-current-debt": "6000",
            "care-hours-per-day": "2",
            "safe-absence-mode": "hours",
            "safe-absence-hours": "12",
            "home-safety": ["other"],
            "home-safety-other": "Door jam",
            "context-artifact-text": "I feel overstimulated, like my brain is on fire.",
        }
    )
    return raw


def _quality_bundle(raw):
    response = build_questionnaire_response(
        PATIENT_ID,
        raw,
        response_id="monarch-quality-test",
        authored="2026-09-24T23:30:00+00:00",
    )
    bundle, _cleanup = build_submission_bundle(PATIENT, response)
    return response, bundle


def test_care_hours_uses_ucum_hours_per_day():
    response = build_questionnaire_response(PATIENT_ID, _full_monarch_input())
    answer = first_answer(response, "care-hours-per-day")
    assert answer["valueQuantity"] == {
        "value": 2.0,
        "unit": "hours/day",
        "system": UCUM_SYSTEM,
        "code": "h/d",
    }


def test_quality_gate_validates_full_monarch_capture():
    _response, bundle = _quality_bundle(_full_monarch_input())
    report = caregiver_quality_gate(bundle)
    assert report["status"] == "PASS"
    assert report["scope"] == "MONARCH_CAPTURE_AND_CAREGIVER_BASELINE"
    checks = {check["check"]: check for check in report["checks"]}
    for name in (
        "questionnaire_response.definition_conformance",
        "scope.selection",
        "scope.content",
        "enable_when.consistency",
        "financial.choice_semantics",
        "financial.currency",
        "care_hours.unit_plausibility",
        "safe_absence.consistency",
        "home_safety.semantics",
        "interaction.preference_semantics",
        "context.capture",
    ):
        assert checks[name]["status"] == "PASS"


def test_quality_gate_rejects_wrong_currency_and_care_hours_unit():
    _response, bundle = _quality_bundle(_full_monarch_input())
    qr = bundle_resources(bundle, "QuestionnaireResponse")[0]
    first_answer(qr, "financial-current-savings")["valueQuantity"]["code"] = "EUR"
    first_answer(qr, "care-hours-per-day")["valueQuantity"]["code"] = "h"

    report = caregiver_quality_gate(bundle)
    checks = {check["check"]: check for check in report["checks"]}
    assert report["status"] == "FAIL"
    assert checks["financial.currency"]["status"] == "FAIL"
    assert checks["care_hours.unit_plausibility"]["status"] == "FAIL"
    assert checks["questionnaire_response.definition_conformance"]["status"] == "FAIL"


def test_quality_gate_rejects_out_of_scope_capture():
    raw = _full_monarch_input()
    response, bundle = _quality_bundle(raw)
    qr = bundle_resources(bundle, "QuestionnaireResponse")[0]
    first_answer(qr, "assessment-scope")["valueCoding"]["code"] = "basics"

    report = caregiver_quality_gate(bundle)
    checks = {check["check"]: check for check in report["checks"]}
    assert report["status"] == "FAIL"
    assert checks["scope.content"]["status"] == "FAIL"


def test_quality_gate_rejects_safe_absence_and_home_safety_contradictions():
    raw = _full_monarch_input()
    raw["safe-absence-mode"] = "varies"
    raw["home-safety"] = ["none", "emergency-alert"]
    _response, bundle = _quality_bundle(raw)

    qr = bundle_resources(bundle, "QuestionnaireResponse")[0]
    safe_item = find_response_items(qr, "safe-absence-mode")[0]
    safe_index = qr["item"].index(safe_item)
    qr["item"].insert(
        safe_index + 1,
        {
            "linkId": "safe-absence-hours",
            "text": "Safe time away from home (hours)",
            "answer": [
                {
                    "valueQuantity": {
                        "value": 4.0,
                        "unit": "hours",
                        "system": UCUM_SYSTEM,
                        "code": "h",
                    }
                }
            ],
        },
    )

    report = caregiver_quality_gate(bundle)
    checks = {check["check"]: check for check in report["checks"]}
    assert report["status"] == "FAIL"
    assert checks["safe_absence.consistency"]["status"] == "FAIL"
    assert checks["home_safety.semantics"]["status"] == "FAIL"
    assert checks["enable_when.consistency"]["status"] == "FAIL"


def test_programmatic_response_defaults_missing_scope_to_explicit_full():
    response = build_questionnaire_response(PATIENT_ID, BASELINE_INPUT)
    assert first_answer(response, "assessment-scope")["valueCoding"]["code"] == "full"
