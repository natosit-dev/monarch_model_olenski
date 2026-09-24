from __future__ import annotations

from connectathon.gravity_questionnaire import build_questionnaire
from connectathon.gravity_response import build_questionnaire_response, first_answer


PATIENT_ID = "PAT-MONARCH-001"
BASELINE_INPUT = {
    "sleep-hours": "6.5",
    "pain-score": 4,
    "phq2-interest": "LA6569-3",
    "phq2-depressed": "LA6568-5",
    "heart-rate": "82",
    "medication-status": True,
    "medications": [
        {
            "name": "lisinopril",
            "dose_value": "10",
            "dose_unit": "mg",
            "route": "oral",
            "frequency": "daily",
        }
    ],
    "feeling-today": "Tired, but pretty steady today.",
    "life-today": "My mom has an appointment and work is busy.",
}


def test_modular_adapter_preserves_baseline_answer_semantics():
    response = build_questionnaire_response(
        PATIENT_ID,
        BASELINE_INPUT,
        response_id="monarch-refactor-test",
        authored="2026-09-24T20:00:00+00:00",
    )

    assert first_answer(response, "sleep-hours") == {
        "valueQuantity": {
            "value": 6.5,
            "unit": "hours",
            "system": "http://unitsofmeasure.org",
            "code": "h",
        }
    }
    assert first_answer(response, "pain-score") == {"valueInteger": 4}
    assert first_answer(response, "phq2-interest")["valueCoding"]["code"] == "LA6569-3"
    assert first_answer(response, "heart-rate") == {
        "valueQuantity": {
            "value": 82.0,
            "unit": "beats/minute",
            "system": "http://unitsofmeasure.org",
            "code": "/min",
        }
    }
    assert first_answer(response, "medication-status") == {"valueBoolean": True}
    assert first_answer(response, "feeling-today") == {"valueString": BASELINE_INPUT["feeling-today"]}
    assert first_answer(response, "life-today") == {"valueString": BASELINE_INPUT["life-today"]}


def test_questionnaire_definition_is_now_renderer_driven_without_changing_baseline_ids():
    questionnaire = build_questionnaire()
    ids = {item["linkId"] for item in questionnaire["item"]}
    assert ids == {
        "sleep-hours",
        "pain-score",
        "phq2",
        "heart-rate",
        "medication-status",
        "medications",
        "feeling-today",
        "life-today",
    }
