from __future__ import annotations

import streamlit as st

from monarch.glossary import GLOSSARY_SOURCE_LABEL, GLOSSARY_SOURCE_URL, MONARCH_GLOSSARY


st.set_page_config(page_title="Monarch Model — Glossary", layout="wide")
st.title("Monarch Model — Glossary")
st.caption("Core terms used throughout the Monarch Model prototype.")

for term, definition in MONARCH_GLOSSARY:
    st.markdown(f"### {term}")
    st.write(definition)

st.divider()
st.markdown(f"**Reference:** [{GLOSSARY_SOURCE_LABEL}]({GLOSSARY_SOURCE_URL})")
