from __future__ import annotations

from typing import Iterable


MONARCH_ANSWER_SYSTEM = "https://medilacra.dev/fhir/CodeSystem/monarch-answer"


def coded_options(values: Iterable[tuple[str, str]], *, system: str = MONARCH_ANSWER_SYSTEM) -> list[dict]:
    return [
        {"valueCoding": {"system": system, "code": code, "display": display}}
        for code, display in values
    ]


YES_NO_UNSURE_OPTIONS = coded_options((("yes", "Yes"), ("no", "No"), ("unsure", "Unsure")))
SAFE_ABSENCE_OPTIONS = coded_options((("hours", "Enter hours"), ("unsure", "Unsure"), ("varies", "Varies")))
HOME_SAFETY_OPTIONS = coded_options(
    (
        ("backup-supervision", "Someone else can provide supervision"),
        ("medication-support", "Medication organization or reminders"),
        ("fall-precautions", "Mobility or fall precautions"),
        ("emergency-alert", "Emergency contact or alert system"),
        ("medical-equipment", "Medical or safety equipment"),
        ("home-modifications", "Environmental or home modifications"),
        ("other", "Other"),
        ("none", "None currently"),
        ("unsure", "Unsure"),
    )
)
STOP_RETURN_OPTIONS = coded_options(
    (
        ("continue", "Continue now"),
        ("pause", "Stop for now and come back later"),
        ("stop", "Stop this evaluation"),
        ("unsure", "Unsure"),
    )
)
