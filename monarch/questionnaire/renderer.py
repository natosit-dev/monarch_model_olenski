from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Mapping

import streamlit as st

from .definitions import (
    PLACEHOLDER_EXTENSION_URL,
    SECTION_EXTENSION_URL,
    enable_when_satisfied,
    extension_value,
    quantity_unit,
)
from .scope import scope_allows


@dataclass
class RenderResult:
    raw_input: dict[str, Any] = field(default_factory=dict)
    declined: set[str] = field(default_factory=set)

    def merge(self, other: "RenderResult") -> None:
        self.raw_input.update(other.raw_input)
        self.declined.update(other.declined)


CustomRenderer = Callable[[Mapping[str, Any], str], RenderResult]


def _decline_control(link_id: str, key_prefix: str) -> bool:
    state_key = f"{key_prefix}_declined_{link_id}"
    st.session_state.setdefault(state_key, False)
    button_label = "Answer instead" if st.session_state[state_key] else "Prefer not to answer"
    if st.button(button_label, key=f"{key_prefix}_decline_button_{link_id}", use_container_width=True):
        st.session_state[state_key] = not st.session_state[state_key]
        st.rerun()
    if st.session_state[state_key]:
        st.caption("Declined — stored as FHIR DataAbsentReason `asked-declined`.")
    return bool(st.session_state[state_key])


def _option_pairs(item: Mapping[str, Any]) -> list[tuple[Any, str]]:
    pairs: list[tuple[Any, str]] = []
    for option in item.get("answerOption", []) or []:
        if not isinstance(option, Mapping):
            continue
        if isinstance(option.get("valueCoding"), Mapping):
            coding = option["valueCoding"]
            pairs.append((coding.get("code"), str(coding.get("display") or coding.get("code") or "")))
        elif "valueString" in option:
            pairs.append((option["valueString"], str(option["valueString"])))
        elif "valueInteger" in option:
            pairs.append((option["valueInteger"], str(option["valueInteger"])))
        elif "valueDecimal" in option:
            pairs.append((option["valueDecimal"], str(option["valueDecimal"])))
    return pairs


def _render_leaf(item: Mapping[str, Any], key_prefix: str) -> RenderResult:
    link_id = str(item["linkId"])
    label = str(item.get("text") or link_id)
    item_type = str(item.get("type") or "")
    placeholder = extension_value(item, PLACEHOLDER_EXTENSION_URL)

    columns = st.columns([4, 1])
    with columns[1]:
        declined = _decline_control(link_id, key_prefix)
    with columns[0]:
        key = f"{key_prefix}_{link_id}"
        if item_type == "text":
            value = st.text_area(label, value="", placeholder=placeholder, disabled=declined, key=key)
        elif item_type == "string":
            value = st.text_input(label, value="", placeholder=placeholder, disabled=declined, key=key)
        elif item_type == "boolean":
            value = st.selectbox(
                label,
                options=[None, True, False],
                format_func=lambda v: "Choose an answer" if v is None else ("Yes" if v else "No"),
                disabled=declined,
                key=key,
            )
        elif item_type == "choice":
            pairs = _option_pairs(item)
            labels = {value: display for value, display in pairs}
            values = [value for value, _display in pairs]
            if item.get("repeats"):
                value = st.multiselect(
                    label,
                    options=values,
                    format_func=lambda v: labels.get(v, str(v)),
                    disabled=declined,
                    key=key,
                )
            else:
                value = st.selectbox(
                    label,
                    options=[None, *values],
                    format_func=lambda v: "Choose an answer" if v is None else labels.get(v, str(v)),
                    disabled=declined,
                    key=key,
                )
        elif item_type == "integer" and item.get("answerOption"):
            pairs = _option_pairs(item)
            labels = {value: display for value, display in pairs}
            values = [value for value, _display in pairs]
            value = st.selectbox(
                label,
                options=[None, *values],
                format_func=lambda v: "Choose an answer" if v is None else labels.get(v, str(v)),
                disabled=declined,
                key=key,
            )
        elif item_type in {"integer", "decimal", "quantity"}:
            value = st.text_input(label, value="", placeholder=placeholder or "", disabled=declined, key=key)
            if item_type == "quantity":
                unit = quantity_unit(item) or {}
                if unit.get("display"):
                    st.caption(f"Unit: {unit['display']}")
        else:
            value = st.text_input(label, value="", placeholder=placeholder or "", disabled=declined, key=key)

    result = RenderResult(raw_input={link_id: value})
    if declined:
        result.declined.add(link_id)
    return result


def render_questionnaire(
    questionnaire: Mapping[str, Any],
    *,
    selected_scope: str = "full",
    key_prefix: str = "monarch",
    exclude: set[str] | None = None,
    initial_raw: Mapping[str, Any] | None = None,
    custom_renderers: Mapping[str, CustomRenderer] | None = None,
) -> RenderResult:
    exclude = exclude or set()
    custom_renderers = custom_renderers or {}
    result = RenderResult(raw_input=dict(initial_raw or {}))
    last_section: str | None = None

    def render_items(items: list[Mapping[str, Any]]) -> None:
        nonlocal last_section
        for item in items:
            link_id = str(item.get("linkId") or "")
            if not link_id or link_id in exclude or not scope_allows(item, selected_scope):
                continue
            if not enable_when_satisfied(item, result.raw_input):
                continue

            section = extension_value(item, SECTION_EXTENSION_URL)
            if section and section != last_section:
                st.markdown(f"#### {section}")
                last_section = str(section)

            custom = custom_renderers.get(link_id)
            if custom:
                result.merge(custom(item, key_prefix))
                continue

            if item.get("type") == "group":
                st.caption(str(item.get("text") or ""))
                render_items(list(item.get("item") or []))
                continue

            result.merge(_render_leaf(item, key_prefix))

    render_items(list(questionnaire.get("item") or []))
    return result
