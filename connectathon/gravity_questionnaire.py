from __future__ import annotations

from typing import Any, Mapping, Sequence

from monarch.questionnaire.choices import (
    HOME_SAFETY_OPTIONS,
    SAFE_ABSENCE_OPTIONS,
    STOP_RETURN_OPTIONS,
    YES_NO_UNSURE_OPTIONS,
    MONARCH_ANSWER_SYSTEM,
)
from monarch.questionnaire.definitions import question_item
from monarch.questionnaire.scope import SCOPE_OPTIONS


QUESTIONNAIRE_ID = "caregiver-health-baseline"
QUESTIONNAIRE_VERSION = "0.3"
QUESTIONNAIRE_URL = "https://medilacra.dev/fhir/Questionnaire/caregiver-health-baseline"
MEDILACRA_CODE_SYSTEM = "https://medilacra.dev/fhir/CodeSystem/caregiver-health"
LOINC_SYSTEM = "http://loinc.org"
UCUM_SYSTEM = "http://unitsofmeasure.org"
ISO_4217_SYSTEM = "urn:iso:std:iso:4217"
DEFAULT_CURRENCY = "USD"
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
    return question_item(link_id, text, item_type, coding=coding, answer_options=answer_options, repeats=repeats)


def build_questionnaire() -> dict[str, Any]:
    phq_options = [
        {"valueCoding": {"system": LOINC_SYSTEM, "code": code, "display": display}}
        for code, display, _score in PHQ_CHOICES
    ]
    pain_options = [{"valueInteger": value} for value in range(0, 11)]

    medication_group = question_item(
        "medications",
        "Medication",
        "group",
        repeats=True,
        min_scope="high_level",
        enable_when=[{"question": "medication-status", "operator": "=", "answerBoolean": True}],
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
        "name": "MonarchCaregiverAssessment",
        "title": "Monarch Model Caregiver Assessment",
        "status": "active",
        "experimental": True,
        "date": "2026-09-24",
        "publisher": "MediLacra / Monarch Model prototype",
        "description": (
            "Caregiver assessment prototype inspired by the Monarch Model. "
            "Preserves lived experience and capacity context before downstream interpretation."
        ),
        "subjectType": ["Patient"],
        "item": [
            question_item(
                "assessment-scope",
                "How much do you feel like you can handle right now?",
                "choice",
                answer_options=SCOPE_OPTIONS,
                required=True,
                section="Evaluation depth",
            ),
            question_item(
                "interaction-unsafe",
                "Is there anything that would make this interaction feel unsafe?",
                "text",
                min_scope="urgent_only",
                section="Interaction and safety preferences",
                placeholder="Anything you want the system or care team to know.",
            ),
            question_item(
                "question-boundaries",
                "Are there kinds of questions you would prefer not to answer?",
                "text",
                min_scope="urgent_only",
                section="Interaction and safety preferences",
            ),
            question_item(
                "support-person",
                "Would you like someone with you for this discussion?",
                "choice",
                answer_options=YES_NO_UNSURE_OPTIONS,
                min_scope="urgent_only",
                section="Interaction and safety preferences",
            ),
            question_item(
                "communication-preferences",
                "Are there ways we should communicate with you differently?",
                "text",
                min_scope="urgent_only",
                section="Interaction and safety preferences",
            ),
            question_item(
                "difficult-situations",
                "Are there procedures, environments, or situations you want us to know may be difficult?",
                "text",
                min_scope="urgent_only",
                section="Interaction and safety preferences",
            ),
            question_item(
                "stop-return-preference",
                "Would you like to stop or come back later?",
                "choice",
                answer_options=STOP_RETURN_OPTIONS,
                min_scope="urgent_only",
                section="Interaction and safety preferences",
            ),
            question_item(
                "sleep-hours",
                "About how many hours did you sleep in the past 24 hours?",
                "quantity",
                coding=local_coding("sleep-hours-24h", "Hours slept in past 24 hours"),
                placeholder="e.g. 6.5",
                quantity_unit_coding={"system": UCUM_SYSTEM, "code": "h", "display": "hours"},
                min_scope="basics",
                section="Current capacity",
            ),
            question_item(
                "pain-score",
                "On a scale from 0 to 10, where 0 means no pain and 10 means the worst pain imaginable, how would you rate your pain right now?",
                "integer",
                coding=loinc_coding(PAIN_LOINC, "Pain severity - 0-10 verbal numeric rating [Score] - Reported"),
                answer_options=pain_options,
                min_scope="basics",
                section="Current capacity",
            ),
            question_item(
                "feeling-today",
                "How are you feeling today?",
                "text",
                coding=local_coding("feeling-today", "How are you feeling today?"),
                placeholder="Write as much or as little as you want.",
                min_scope="basics",
                section="Current context",
            ),
            question_item(
                "life-today",
                "What's going on in your life today?",
                "text",
                coding=local_coding("life-today", "What's going on in your life today?"),
                placeholder="Anything that feels relevant today.",
                min_scope="basics",
                section="Current context",
            ),
            question_item(
                "phq2",
                "Over the last 2 weeks, how often have you been bothered by the following problems?",
                "group",
                coding=loinc_coding(PHQ2_TOTAL, "PHQ-2 total score"),
                min_scope="high_level",
                section="Current capacity",
                children=[
                    question_item("phq2-interest", "Little interest or pleasure in doing things", "choice", coding=loinc_coding(PHQ2_QUESTION_1, "Little interest or pleasure in doing things"), answer_options=phq_options),
                    question_item("phq2-depressed", "Feeling down, depressed, or hopeless", "choice", coding=loinc_coding(PHQ2_QUESTION_2, "Feeling down, depressed, or hopeless"), answer_options=phq_options),
                ],
            ),
            question_item(
                "heart-rate",
                "What is your current heart rate?",
                "quantity",
                coding=loinc_coding(HEART_RATE_LOINC, "Heart rate"),
                placeholder="e.g. 82",
                quantity_unit_coding={"system": UCUM_SYSTEM, "code": "/min", "display": "beats/minute"},
                min_scope="high_level",
                section="Current capacity",
            ),
            question_item(
                "medication-status",
                "Are you currently taking any medications?",
                "boolean",
                min_scope="high_level",
                section="Medication reconciliation",
            ),
            medication_group,
            question_item("financial-unexpected-100", "Can you handle an unexpected $100 expense?", "choice", answer_options=YES_NO_UNSURE_OPTIONS, min_scope="high_level", section="Financial capacity"),
            question_item("financial-unexpected-500", "Can you handle an unexpected $500 expense?", "choice", answer_options=YES_NO_UNSURE_OPTIONS, min_scope="high_level", section="Financial capacity"),
            question_item("financial-miss-week-work", "Could you miss one week of work?", "choice", answer_options=YES_NO_UNSURE_OPTIONS, min_scope="high_level", section="Financial capacity"),
            question_item("financial-healthcare-cost-difficulty", "Are you having difficulty paying current healthcare costs?", "choice", answer_options=YES_NO_UNSURE_OPTIONS, min_scope="high_level", section="Financial capacity"),
            question_item("financial-debt-affects-care", "Is debt currently affecting healthcare choices?", "choice", answer_options=YES_NO_UNSURE_OPTIONS, min_scope="high_level", section="Financial capacity"),
            question_item("financial-current-savings", "Current savings (optional exact amount; USD)", "quantity", min_scope="full", section="Financial capacity", placeholder="Optional amount, e.g. 2500", quantity_unit_coding={"system": ISO_4217_SYSTEM, "code": DEFAULT_CURRENCY, "display": DEFAULT_CURRENCY}),
            question_item("financial-current-debt", "Current debt (optional exact amount; USD)", "quantity", min_scope="full", section="Financial capacity", placeholder="Optional amount, e.g. 6000", quantity_unit_coding={"system": ISO_4217_SYSTEM, "code": DEFAULT_CURRENCY, "display": DEFAULT_CURRENCY}),
            question_item(
                "care-hours-per-day",
                "About how many hours per day do you spend administering care?",
                "quantity",
                min_scope="high_level",
                section="Caregiver capacity",
                quantity_unit_coding={"system": UCUM_SYSTEM, "code": "h/d", "display": "hours/day"},
                placeholder="e.g. 6",
            ),
            question_item("safe-absence-mode", "How long do you feel you can safely leave the home?", "choice", answer_options=SAFE_ABSENCE_OPTIONS, min_scope="high_level", section="Caregiver capacity"),
            question_item(
                "safe-absence-hours",
                "Safe time away from home (hours)",
                "quantity",
                min_scope="high_level",
                section="Caregiver capacity",
                quantity_unit_coding={"system": UCUM_SYSTEM, "code": "h", "display": "hours"},
                enable_when=[{"question": "safe-absence-mode", "operator": "=", "answerCoding": {"system": MONARCH_ANSWER_SYSTEM, "code": "hours"}}],
            ),
            question_item("home-safety", "What safety precautions are in place at home?", "choice", answer_options=HOME_SAFETY_OPTIONS, repeats=True, min_scope="high_level", section="Caregiver capacity"),
            question_item(
                "home-safety-other",
                "Other home safety precautions",
                "text",
                min_scope="high_level",
                section="Caregiver capacity",
                enable_when=[{"question": "home-safety", "operator": "=", "answerCoding": {"system": MONARCH_ANSWER_SYSTEM, "code": "other"}}],
            ),
            question_item(
                "context-artifact-text",
                "Anything else you want to add about what's going on right now?",
                "text",
                min_scope="high_level",
                section="Additional context",
                placeholder="Raw context only for now. Analysis can happen later.",
            ),
        ],
    }
