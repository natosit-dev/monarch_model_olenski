from __future__ import annotations

import math
from typing import Any, Callable, Mapping, Sequence

from connectathon.gravity_questionnaire import DATA_ABSENT_REASON_URL
from .definitions import enable_when_satisfied, quantity_unit
from .scope import scope_allows


CustomBuilder = Callable[[Mapping[str, Any], Mapping[str, Any], set[str]], Any]


def absent_answer(reason: str) -> dict[str, Any]:
    return {
        "extension": [
            {"url": DATA_ABSENT_REASON_URL, "valueCode": reason}
        ]
    }


def _parse_float(raw: Any) -> tuple[float | None, str | None]:
    if raw is None or str(raw).strip() == "":
        return None, None
    try:
        value = float(str(raw).strip())
    except (TypeError, ValueError):
        return None, "error"
    if math.isnan(value):
        return None, "not-a-number"
    if math.isinf(value):
        return None, "positive-infinity" if value > 0 else "negative-infinity"
    return value, None


def _parse_int(raw: Any) -> tuple[int | None, str | None]:
    if raw is None or str(raw).strip() == "":
        return None, None
    try:
        value = int(str(raw).strip())
    except (TypeError, ValueError):
        return None, "error"
    return value, None


def _option_value(option: Mapping[str, Any]) -> tuple[Any, dict[str, Any]] | None:
    for key in ("valueCoding", "valueString", "valueInteger", "valueDecimal"):
        if key not in option:
            continue
        value = option[key]
        if key == "valueCoding" and isinstance(value, Mapping):
            return value.get("code"), {key: dict(value)}
        return value, {key: value}
    return None


def _choice_answer(item: Mapping[str, Any], raw: Any) -> dict[str, Any] | None:
    for option in item.get("answerOption", []) or []:
        if not isinstance(option, Mapping):
            continue
        parsed = _option_value(option)
        if not parsed:
            continue
        option_value, answer = parsed
        if raw == option_value:
            return answer
    if raw in (None, ""):
        return None
    return absent_answer("error")


def answer_for_item(item: Mapping[str, Any], raw: Any, *, declined: bool = False) -> list[dict[str, Any]]:
    if declined:
        return [absent_answer("asked-declined")]

    item_type = str(item.get("type") or "")
    if item_type in {"string", "text"}:
        if raw is None or not str(raw).strip():
            return []
        return [{"valueString": str(raw)}]

    if item_type == "boolean":
        if raw is None or raw == "":
            return []
        if isinstance(raw, bool):
            return [{"valueBoolean": raw}]
        text = str(raw).strip().lower()
        if text in {"yes", "y", "true", "1"}:
            return [{"valueBoolean": True}]
        if text in {"no", "n", "false", "0"}:
            return [{"valueBoolean": False}]
        return [absent_answer("error")]

    if item_type == "integer":
        value, error = _parse_int(raw)
        if error:
            return [absent_answer(error)]
        return [] if value is None else [{"valueInteger": value}]

    if item_type == "decimal":
        value, error = _parse_float(raw)
        if error:
            return [absent_answer(error)]
        return [] if value is None else [{"valueDecimal": value}]

    if item_type == "quantity":
        value, error = _parse_float(raw)
        if error:
            return [absent_answer(error)]
        if value is None:
            return []
        unit = quantity_unit(item) or {}
        quantity: dict[str, Any] = {"value": value}
        for key in ("display", "system", "code"):
            if unit.get(key):
                quantity["unit" if key == "display" else key] = unit[key]
        return [{"valueQuantity": quantity}]

    if item_type == "choice":
        if item.get("repeats"):
            values = list(raw or []) if isinstance(raw, (list, tuple, set)) else ([] if raw in (None, "") else [raw])
            answers = []
            for value in values:
                answer = _choice_answer(item, value)
                if answer is not None:
                    answers.append(answer)
            return answers
        answer = _choice_answer(item, raw)
        return [] if answer is None else [answer]

    return []


def build_response_items(
    questionnaire_items: Sequence[Mapping[str, Any]],
    raw_input: Mapping[str, Any],
    *,
    declined: set[str] | None = None,
    selected_scope: str = "full",
    custom_builders: Mapping[str, CustomBuilder] | None = None,
) -> list[dict[str, Any]]:
    declined = declined or set()
    custom_builders = custom_builders or {}
    output: list[dict[str, Any]] = []

    for item in questionnaire_items:
        link_id = str(item.get("linkId") or "")
        if not link_id or not scope_allows(item, selected_scope):
            continue
        if not enable_when_satisfied(item, raw_input):
            continue

        custom = custom_builders.get(link_id)
        if custom:
            built = custom(item, raw_input, declined)
            if built is None:
                continue
            if isinstance(built, list):
                output.extend(built)
            else:
                output.append(built)
            continue

        response_item: dict[str, Any] = {
            "linkId": link_id,
            "text": str(item.get("text") or ""),
        }

        if item.get("type") == "group":
            children = build_response_items(
                list(item.get("item") or []),
                raw_input,
                declined=declined,
                selected_scope=selected_scope,
                custom_builders=custom_builders,
            )
            if children:
                response_item["item"] = children
            output.append(response_item)
            continue

        answers = answer_for_item(item, raw_input.get(link_id), declined=link_id in declined)
        if answers:
            response_item["answer"] = answers
        output.append(response_item)

    return output
