from __future__ import annotations

from typing import Any, Mapping, Sequence

from monarch.questionnaire.definitions import question_item


QUESTIONNAIRE_ID = "caregiver-health-baseline"
QUESTIONNAIRE_VERSION = "0.2"
QUESTIONNAIRE_URL = "https://medilacra.dev/fhir/Questionnaire/caregiver-health-baseline"
MEDILACRA_CODE_SYSTEM = "https://medilacra.dev/fhir/CodeSystem/caregiver-health"
LOINC_SYSTEM = "http://loinc.org"
UCUM_SYSTEM = "http://unitsofmeasure.org"
RXNORM_SYSTEM = "http://www.nlm.nih.gov/research/umls/rxnorm"
DATA_ABSENT_REASON_URL = "http://hl7.org/fhir/StructureDefinition/data-absent-reason"

PAIN_LOINC = "72514-3"
PHQ2_QUESTION_1 = "44250-9"
PHQ2_QUESTION_2 = "44255-8"
PHQ2_TOTAL = "55757-9"
HEART_RATE_LOINC = "8867-4"

PHQ_CHOICES = (
    ("LA6568-5", "Not at all", 0),
    ("LA6569-3", "Several days", 1),
    ("LA6570-1", "More than half the days", 2),
    ("LA6571-9", "Nearly every day", 3),
)
PHQ_SCORE_BY_CODE = {code: score for code, _display, score in PHQ_CHOICES}
PHQ_DISPLAY_BY_CODE = {code: display for code, display, _score in PHQ_CHOICES}


def loinc_coding(code: str, display: str) -> dict[str, str]:
    return {"system": LOINC_SYSTEM, "code": code, "display": display}


def local_coding(code: str, display: str) -> dict[str, str]:
    return {"system": MEDILACRA_CODE_SYSTEM, "code": code, "display": display}


def data_absent_reason(reason: str) -> dict[str, str]:
    return {"url": DATA_ABSENT_REASON_URL, "valueCode": reason}


def _question_item(
    link_id: str,
    text: str,
    item_type: str,
    *,
    coding: Mapping[str, Any] | None = None,
    answer_options: Sequence[Mapping[str, Any]] | None = None,
    repeats: bool = False,
) -> dict[str, Any]:
    return question_item(
        link_id,
        text,
        item_type,
        coding=coding,
        answer_options=answer_options,
        repeats=repeats,
    )


def build_questionnaire() -> dict[str, Any]:
    phq_options = [
        {
            "valueCoding": {
                "system": LOINC_SYSTEM,
                "code": code,
                "display": display,
            }
        }
        for code, display, _score in PHQ_CHOICES
    ]
    pain_options = [{"valueInteger": value} for value in range(0, 11)]

    medication_group = question_item(
        "medications",
        "Medication",
        "group",
        repeats=True,
        enable_when=[
            {
                "question": "medication-status",
                "operator": "=",
                "answerBoolean": True,
            }
        ],
        children=[
            question_item("medication-name", "Medication name", "string"),
            question_item("medication-dose-value", "Dose", "decimal"),
            question_item("medication-dose-unit", "Dose unit", "string"),
            question_item("medication-route", "Route", "string"),
            question_item("medication-frequency", "Frequency", "string"),
        ],
    )

    return {
        "resourceType": "Questionnaire",
        "id": QUESTIONNAIRE_ID,
        "url": QUESTIONNAIRE_URL,
        "version": QUESTIONNAIRE_VERSION,
        "name": "CaregiverHealthBaseline",
        "title": "MediLacra Caregiver Health Baseline",
        "status": "active",
        "experimental": True,
        "date": "2026-09-09",
        "publisher": "MediLacra",
        "description": (
            "Baseline caregiver-health questionnaire for Gravity/SDC materialization, "
            "semantic-preservation testing, and optional free-text lived-experience capture."
        ),
        "subjectType": ["Patient"],
        "item": [
            question_item(
                "sleep-hours",
                "About how many hours did you sleep in the past 24 hours?",
                "quantity",
                coding=local_coding("sleep-hours-24h", "Hours slept in past 24 hours"),
                placeholder="e.g. 6.5",
                quantity_unit_coding={"system": UCUM_SYSTEM, "code": "h", "display": "hours"},
                section="Sleep",
            ),
            question_item(
                "pain-score",
                "On a scale from 0 to 10, where 0 means no pain and 10 means the worst pain imaginable, how would you rate your pain right now?",
                "integer",
                coding=loinc_coding(PAIN_LOINC, "Pain severity - 0-10 verbal numeric rating [Score] - Reported"),
                answer_options=pain_options,
                section="Pain",
            ),
            question_item(
                "phq2",
                "Over the last 2 weeks, how often have you been bothered by the following problems?",
                "group",
                coding=loinc_coding(PHQ2_TOTAL, "PHQ-2 total score"),
                section="PHQ-2",
                children=[
                    question_item(
                        "phq2-interest",
                        "Little interest or pleasure in doing things",
                        "choice",
                        coding=loinc_coding(PHQ2_QUESTION_1, "Little interest or pleasure in doing things"),
                        answer_options=phq_options,
                    ),
                    question_item(
                        "phq2-depressed",
                        "Feeling down, depressed, or hopeless",
                        "choice",
                        coding=loinc_coding(PHQ2_QUESTION_2, "Feeling down, depressed, or hopeless"),
                        answer_options=phq_options,
                    ),
                ],
            ),
            question_item(
                "heart-rate",
                "What is your current heart rate?",
                "quantity",
                coding=loinc_coding(HEART_RATE_LOINC, "Heart rate"),
                placeholder="e.g. 82",
                quantity_unit_coding={"system": UCUM_SYSTEM, "code": "/min", "display": "beats/minute"},
                section="Heart rate",
            ),
            question_item(
                "medication-status",
                "Are you currently taking any medications?",
                "boolean",
                section="Medication reconciliation",
            ),
            medication_group,
            question_item(
                "feeling-today",
                "How are you feeling today?",
                "text",
                coding=local_coding("feeling-today", "How are you feeling today?"),
                placeholder="Write as much or as little as you want.",
                section="How are you feeling today?",
            ),
            question_item(
                "life-today",
                "What's going on in your life today?",
                "text",
                coding=local_coding("life-today", "What's going on in your life today?"),
                placeholder="Anything that feels relevant today.",
                section="What's going on in your life today?",
            ),
        ],
    }
