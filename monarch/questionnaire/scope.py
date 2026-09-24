from __future__ import annotations

from typing import Any, Mapping

from .choices import coded_options
from .definitions import SCOPE_EXTENSION_URL, extension_value


SCOPE_ORDER = ("urgent_only", "basics", "high_level", "full")
SCOPE_LABELS = {
    "urgent_only": "Only urgent questions",
    "basics": "Just the basics",
    "high_level": "High-level check-in",
    "full": "Full evaluation",
}
ASSESSMENT_SCOPE_PROMPT = "How much do you feel like you can handle right now?"
SCOPE_OPTIONS = coded_options(tuple((code, SCOPE_LABELS[code]) for code in SCOPE_ORDER))


def scope_allows(item: Mapping[str, Any], selected_scope: str) -> bool:
    minimum = extension_value(item, SCOPE_EXTENSION_URL)
    if not minimum:
        return True
    try:
        return SCOPE_ORDER.index(selected_scope) >= SCOPE_ORDER.index(str(minimum))
    except ValueError:
        return True
