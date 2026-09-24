from __future__ import annotations

from typing import Any, Mapping, Sequence


EXTENSION_BASE = "https://medilacra.dev/fhir/StructureDefinition/monarch"
SCOPE_EXTENSION_URL = f"{EXTENSION_BASE}-minimum-scope"
SECTION_EXTENSION_URL = f"{EXTENSION_BASE}-ui-section"
PLACEHOLDER_EXTENSION_URL = f"{EXTENSION_BASE}-ui-placeholder"
QUANTITY_UNIT_EXTENSION_URL = f"{EXTENSION_BASE}-quantity-unit"
HELP_EXTENSION_URL = f"{EXTENSION_BASE}-help-text"


def _extension(url: str, value_key: str, value: Any) -> dict[str, Any]:
    return {"url": url, value_key: value}


def extension(item: Mapping[str, Any], url: str) -> Mapping[str, Any] | None:
    for candidate in item.get("extension", []) or []:
        if isinstance(candidate, Mapping) and candidate.get("url") == url:
            return candidate
    return None


def extension_value(item: Mapping[str, Any], url: str) -> Any:
    found = extension(item, url)
    if not found:
        return None
    for key, value in found.items():
        if key.startswith("value"):
            return value
    return None


def quantity_unit(item: Mapping[str, Any]) -> Mapping[str, Any] | None:
    value = extension_value(item, QUANTITY_UNIT_EXTENSION_URL)
    return value if isinstance(value, Mapping) else None


def question_item(
    link_id: str,
    text: str,
    item_type: str,
    *,
    coding: Mapping[str, Any] | None = None,
    answer_options: Sequence[Mapping[str, Any]] | None = None,
    repeats: bool = False,
    required: bool = False,
    min_scope: str | None = None,
    section: str | None = None,
    placeholder: str | None = None,
    quantity_unit_coding: Mapping[str, Any] | None = None,
    help_text: str | None = None,
    enable_when: Sequence[Mapping[str, Any]] | None = None,
    children: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    item: dict[str, Any] = {
        "linkId": link_id,
        "text": text,
        "type": item_type,
        "required": required,
        "repeats": repeats,
    }
    if coding:
        item["code"] = [dict(coding)]
    if answer_options:
        item["answerOption"] = [dict(option) for option in answer_options]
    if enable_when:
        item["enableWhen"] = [dict(condition) for condition in enable_when]
    if children:
        item["item"] = [dict(child) for child in children]

    extensions: list[dict[str, Any]] = []
    if min_scope:
        extensions.append(_extension(SCOPE_EXTENSION_URL, "valueCode", min_scope))
    if section:
        extensions.append(_extension(SECTION_EXTENSION_URL, "valueString", section))
    if placeholder:
        extensions.append(_extension(PLACEHOLDER_EXTENSION_URL, "valueString", placeholder))
    if quantity_unit_coding:
        extensions.append(_extension(QUANTITY_UNIT_EXTENSION_URL, "valueCoding", dict(quantity_unit_coding)))
    if help_text:
        extensions.append(_extension(HELP_EXTENSION_URL, "valueString", help_text))
    if extensions:
        item["extension"] = extensions
    return item


def _expected_enable_value(condition: Mapping[str, Any]) -> Any:
    for key in (
        "answerBoolean",
        "answerCoding",
        "answerString",
        "answerInteger",
        "answerDecimal",
    ):
        if key in condition:
            value = condition[key]
            if key == "answerCoding" and isinstance(value, Mapping):
                return value.get("code")
            return value
    return None


def _matches(actual: Any, expected: Any) -> bool:
    if isinstance(actual, (list, tuple, set)):
        return expected in actual
    return actual == expected


def enable_when_satisfied(item: Mapping[str, Any], raw_input: Mapping[str, Any]) -> bool:
    conditions = list(item.get("enableWhen") or [])
    if not conditions:
        return True

    results: list[bool] = []
    for condition in conditions:
        if not isinstance(condition, Mapping):
            continue
        actual = raw_input.get(str(condition.get("question") or ""))
        expected = _expected_enable_value(condition)
        operator = condition.get("operator", "=")
        matched = _matches(actual, expected)
        results.append(not matched if operator == "!=" else matched)

    if not results:
        return True
    behavior = str(item.get("enableBehavior") or "all").lower()
    return any(results) if behavior == "any" else all(results)
