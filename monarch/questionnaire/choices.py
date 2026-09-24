from __future__ import annotations

from typing import Iterable


MONARCH_ANSWER_SYSTEM = "https://medilacra.dev/fhir/CodeSystem/monarch-answer"


def coded_options(values: Iterable[tuple[str, str]], *, system: str = MONARCH_ANSWER_SYSTEM) -> list[dict]:
    return [
        {"valueCoding": {"system": system, "code": code, "display": display}}
        for code, display in values
    ]


YES_NO_UNSURE_OPTIONS = coded_options(
    (
        ("yes", "Yes"),
        ("no", "No"),
        ("unsure", "Unsure"),
    )
)
