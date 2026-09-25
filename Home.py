from __future__ import annotations

import streamlit as st


st.set_page_config(
    page_title="Monarch Model Prototype",
    page_icon="🦋",
    layout="wide",
)

st.title("🦋 Monarch Model Prototype")
st.caption(
    "Prototypes inspired by Erica Olenski's Monarch Model, exploring how lived experience, "
    "human agency, context, and semantic quality can be represented in healthcare data."
)

st.markdown(
    """
Use the standard Streamlit sidebar to move between modules.

### Monarch Assessment
Capture lived experience, current capacity, caregiver context, financial capacity,
interaction preferences, and the existing clinical baseline at a level of detail the
person chooses.

### Monarch Glossary
Reference the shared vocabulary used by the prototype, including lived experience,
human agency, determinants of agency, capital, friction, intentional listening, and governance.

### DiScO — Text Evaluator
Run deterministic text inspection against educational or other written material.
DiScO inventories observable text features and reports bounded semantic and AI-oriented
signals plus unscored sentence cadence.

### Disco Fever
Inspect and calibrate DiScO rule dictionaries and scoring priors.

### Discotorium
Review stored DiScO judgements, feature inventories, provenance, and corpus-level summaries.
"""
)

st.divider()
st.markdown(
    "**Reference:** [The Monarch Model™ — Monarch Futures]"
    "(https://www.monarchfutures.com/themonarchmodeltextonly)"
)

st.info(
    "This is a prototype environment. Modules preserve source data and explicit distinctions "
    "before downstream interpretation wherever possible."
)
