from __future__ import annotations

import re

import streamlit as st

from monarch.disco import (
    RUNTIME_RULES_PATH,
    FeatureRule,
    load_rules,
    reset_rules,
    save_rules,
)


st.title("🕺 Disco Fever")
st.caption("DiScO calibration console")
st.markdown(
    "Adjust bounded scoring priors and detector dictionaries without changing the detector engine. "
    "Changes are stored locally and applied to future judgements."
)
st.info(
    "Each feature has a maximum semantic contribution, a maximum AI contribution, and a half-saturation rate. "
    "Historical profiles keep the exact rule snapshot used when they were scored."
)

rules = load_rules()

st.markdown("## Active rules")
with st.form("disco_fever_rules"):
    edited_rules: list[FeatureRule] = []

    for rule in rules:
        with st.expander(f"{rule.label} · `{rule.id}`", expanded=True):
            st.caption(f"Detector type: `{rule.kind}`")
            semantic_col, ai_col, saturation_col = st.columns(3)
            with semantic_col:
                semantic_max = st.number_input(
                    "Semantic max",
                    min_value=0.0,
                    max_value=1.0,
                    value=float(rule.semantic_max),
                    step=0.01,
                    format="%.3f",
                    key=f"semantic-max-{rule.id}",
                    help="Maximum amount this feature can add to the 0–1 semantic signal.",
                )
            with ai_col:
                ai_max = st.number_input(
                    "AI max",
                    min_value=0.0,
                    max_value=1.0,
                    value=float(rule.ai_max),
                    step=0.01,
                    format="%.3f",
                    key=f"ai-max-{rule.id}",
                    help="Maximum amount this feature can add to the 0–1 AI-oriented signal.",
                )
            with saturation_col:
                half_saturation = st.number_input(
                    "Half-saturation / 100 words",
                    min_value=0.01,
                    value=float(rule.half_saturation),
                    step=0.25,
                    format="%.3f",
                    key=f"half-saturation-{rule.id}",
                    help="Feature rate where this rule reaches half of either configured maximum.",
                )

            terms = rule.terms
            pattern = rule.pattern

            if rule.kind in {"lexicon", "lexicon_stem"}:
                terms_text = st.text_area(
                    "Term dictionary — one term per line",
                    value="\n".join(rule.terms),
                    height=160,
                    key=f"terms-{rule.id}",
                )
                terms = tuple(
                    line.strip()
                    for line in terms_text.splitlines()
                    if line.strip()
                )
            elif rule.kind == "regex":
                pattern = st.text_area(
                    "Regex pattern",
                    value=rule.pattern or "",
                    height=120,
                    key=f"pattern-{rule.id}",
                ).strip()
            else:
                st.caption(
                    "This is currently a structural detector. Its scoring priors are configurable; "
                    "its underlying parser remains fixed in code."
                )

            edited_rules.append(
                FeatureRule(
                    id=rule.id,
                    label=rule.label,
                    kind=rule.kind,
                    semantic_max=float(semantic_max),
                    ai_max=float(ai_max),
                    half_saturation=float(half_saturation),
                    terms=terms,
                    pattern=pattern,
                )
            )

    save = st.form_submit_button(
        "🔥 SAVE FEVER SETTINGS",
        type="primary",
        use_container_width=True,
    )

if save:
    errors: list[str] = []
    for rule in edited_rules:
        if rule.half_saturation <= 0:
            errors.append(f"{rule.label}: half-saturation must be greater than zero.")
        if not 0 <= rule.semantic_max <= 1:
            errors.append(f"{rule.label}: semantic max must be between 0 and 1.")
        if not 0 <= rule.ai_max <= 1:
            errors.append(f"{rule.label}: AI max must be between 0 and 1.")
        if rule.kind == "regex":
            if not rule.pattern:
                errors.append(f"{rule.label}: regex pattern cannot be empty.")
                continue
            try:
                re.compile(rule.pattern, re.IGNORECASE)
            except re.error as exc:
                errors.append(f"{rule.label}: {exc}")
        if rule.kind in {"lexicon", "lexicon_stem"} and not rule.terms:
            errors.append(f"{rule.label}: term dictionary cannot be empty.")

    if errors:
        st.error("Configuration was not saved.")
        for error in errors:
            st.code(error, language="text")
    else:
        path = save_rules(tuple(edited_rules))
        st.success(f"Saved active DiScO configuration to `{path}`.")
        st.rerun()

reset_col, path_col = st.columns([1, 3])
with reset_col:
    if st.button("Reset to defaults", use_container_width=True):
        reset_rules()
        st.rerun()
with path_col:
    st.caption(f"Local overrides: `{RUNTIME_RULES_PATH}`")

st.caption("Use Discotorium to review stored judgements and corpus-level statistics.")
