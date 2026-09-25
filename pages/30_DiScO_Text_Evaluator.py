from __future__ import annotations

import hashlib
import json

import pandas as pd
import streamlit as st

from monarch.disco import (
    CADENCE_GUIDANCE,
    DESCRIPTION,
    METRIC_GUIDANCE,
    VIRGIL_OVERVIEW,
    DocHistoryUnavailable,
    extract_document_text,
    get_feature_guidance,
    inspect_document_artifact,
    inspect_text,
    load_rules,
    record_judgement,
)


def _render_feature_guidance(feature_id: str) -> None:
    guidance = get_feature_guidance(feature_id)
    st.write(guidance.summary)
    st.markdown("**Why it matters**")
    st.write(guidance.why_it_matters)
    st.caption(f"Caveat: {guidance.caveat}")
    if guidance.orwell_quote:
        st.markdown(f"> “{guidance.orwell_quote}”")
        if guidance.orwell_source:
            st.caption(guidance.orwell_source)


st.title("🪩 DiScO")
st.caption(DESCRIPTION)
st.markdown(
    "DiScO inventories cheap, observable text features "
    "associated with semantic reconstruction cost. Same text + same configuration produces the same profile. Disco Inferno is not loaded here."
)

with st.expander("🕯️ Virgil — What am I looking at?", expanded=False):
    st.write(VIRGIL_OVERVIEW)
    st.markdown("**Semantic signal**")
    st.write(METRIC_GUIDANCE["Semantic signal"])
    st.markdown("**AI signal**")
    st.write(METRIC_GUIDANCE["AI signal"])
    st.markdown("**Count / rate / strength / contribution**")
    st.write(
        f"{METRIC_GUIDANCE['Count']} {METRIC_GUIDANCE['Rate / 100']} "
        f"{METRIC_GUIDANCE['Strength']} {METRIC_GUIDANCE['Contribution']}"
    )
    st.markdown("**Sentence cadence**")
    st.write(CADENCE_GUIDANCE.summary)
    st.caption("Cadence is currently recorded as an observation only. It contributes to neither score.")

input_mode = st.radio(
    "Input source",
    options=("Paste text", "Upload document"),
    horizontal=True,
)

with st.form("disco_judgement"):
    text = ""
    uploaded_file = None
    if input_mode == "Paste text":
        text = st.text_area("Free text", height=300, placeholder="Paste free text here...")
    else:
        uploaded_file = st.file_uploader("DOCX or PDF", type=("docx", "pdf"))
        st.caption(
            "Uploaded files are always scored from extracted text. If doc_history is available, "
            "DiScO also records the richer document provenance dataset."
        )

    ai_generated = st.checkbox(
        "AI generated",
        value=False,
        help="Feedback metadata only. The label is stored for later analysis and does not affect scoring.",
    )
    judge = st.form_submit_button("⚖️ JUDGEMENT", type="primary", use_container_width=True)

if judge:
    artifact = None

    if input_mode == "Upload document":
        if uploaded_file is None:
            st.warning("Upload a DOCX or PDF first.")
            st.stop()

        file_bytes = uploaded_file.getvalue()

        # Text extraction is the required path for a DiScO judgement. Document
        # provenance is optional enrichment and must never block text scoring.
        try:
            text = extract_document_text(file_bytes, uploaded_file.name)
        except Exception as exc:
            st.error(f"Could not extract text from uploaded document: {type(exc).__name__}: {exc}")
            st.stop()

        artifact = {
            "source_type": "file",
            "filename": uploaded_file.name,
            "file_sha256": hashlib.sha256(file_bytes).hexdigest(),
            "doc_history": None,
            "timeline_events": [],
            "provenance_clues": [],
        }

        try:
            artifact = inspect_document_artifact(file_bytes, uploaded_file.name)
        except DocHistoryUnavailable as exc:
            artifact["doc_history_unavailable"] = str(exc)
            st.warning(
                "Document provenance enrichment is unavailable because doc_history could not be imported. "
                "DiScO will continue with normal text scoring."
            )
        except Exception as exc:
            artifact["doc_history_error"] = f"{type(exc).__name__}: {exc}"
            st.warning(
                "doc_history could not inspect this document. DiScO will continue with normal text scoring."
            )

    if not text.strip():
        st.warning("No inspectable text was found.")
    else:
        rules = load_rules()
        profile = inspect_text(text, rules=rules)
        record = record_judgement(
            text=text,
            profile=profile,
            ai_generated=ai_generated,
            rules=rules,
            artifact=artifact,
        )

        source_note = f" • file = `{artifact['filename']}`" if artifact is not None else ""
        st.caption(
            f"Judgement saved locally: `{record['judgement_id']}` • "
            f"AI generated = `{record['ai_generated']}`{source_note}. The label did not affect scoring."
        )
        judgement_id = str(record.get("judgement_id", "judgement"))
        st.download_button(
            "Download this judgement (JSON)",
            data=json.dumps(record, ensure_ascii=False, indent=2),
            file_name=f"disco_judgement_{judgement_id}.json",
            mime="application/json",
            key=f"download_judgement_{judgement_id}",
            use_container_width=True,
        )

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Words", f"{profile.word_count:,}")
        m2.metric("Characters", f"{profile.character_count:,}")
        m3.metric("Semantic signal", f"{profile.signal_score:.3f}")
        m4.metric("AI signal", f"{profile.ai_signal_score:.3f}")

        rows = [
            {
                "Feature": feature.label,
                "Count": feature.count,
                "Rate / 100": round(feature.rate_per_100_words, 3),
                "Strength": round(feature.strength, 3),
                "Semantic contribution": round(feature.semantic_contribution, 3),
                "AI contribution": round(feature.ai_contribution, 3),
            }
            for feature in profile.features
        ]
        st.markdown("### DiScO profile")
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

        st.markdown("#### ❓ Virgil's feature guide")
        st.caption("Open any feature for a plain-language explanation, caveat, and Orwell only where he actually helps.")
        for feature in profile.features:
            with st.expander(f"❓ {feature.label} · {feature.count} match{'es' if feature.count != 1 else ''}"):
                _render_feature_guidance(feature.id)
                st.caption(
                    f"rate={feature.rate_per_100_words:.3f}/100 · "
                    f"half-saturation={feature.half_saturation:.3f} · "
                    f"strength={feature.strength:.3f} · "
                    f"semantic max={feature.semantic_max:.3f} · "
                    f"AI max={feature.ai_max:.3f}"
                )
                if feature.matches:
                    st.markdown("**Matches in this judgement**")
                    st.code("\n".join(match.text for match in feature.matches), language="text")
                else:
                    st.caption("No matches in this judgement.")

        cadence = record.get("sentence_cadence", {}) or {}
        if cadence:
            st.markdown("### Sentence cadence · unscored")
            c1, c2, c3, c4, c5 = st.columns(5)
            c1.metric("Sentences", f"{int(cadence.get('sentence_count', 0) or 0):,}")
            c2.metric("Mean words", f"{float(cadence.get('mean_words', 0.0) or 0.0):.1f}")
            c3.metric("Std. dev.", f"{float(cadence.get('std_dev_words', 0.0) or 0.0):.2f}")
            c4.metric("Variation / mean", f"{float(cadence.get('coefficient_of_variation', 0.0) or 0.0):.2f}")
            c5.metric("Range", f"{int(cadence.get('range_words', 0) or 0):,} words")
            with st.expander("❓ What do these cadence numbers mean?"):
                st.write(CADENCE_GUIDANCE.summary)
                st.markdown("**Why it might matter later**")
                st.write(CADENCE_GUIDANCE.why_it_matters)
                st.caption(f"Caveat: {CADENCE_GUIDANCE.caveat}")
                st.markdown("**Raw sentence lengths**")
                st.code(
                    ", ".join(str(value) for value in cadence.get("sentence_lengths", []) or []),
                    language="text",
                )

        if artifact is not None:
            doc_history = artifact.get("doc_history") or {}
            provenance_problem = artifact.get("doc_history_unavailable") or artifact.get("doc_history_error")

            st.markdown("### Document artifact inventory")

            if provenance_problem:
                st.caption(
                    "The uploaded file was scored successfully. Rich provenance inspection was unavailable for this judgement."
                )
                a1, a2 = st.columns(2)
                a1.metric("File", str(artifact.get("filename", "—")))
                sha = str(artifact.get("file_sha256", ""))
                a2.metric("File SHA-256", sha[:16] if sha else "—")
                st.warning(str(provenance_problem))
            else:
                embedded = doc_history.get("embedded_metadata", {}) or {}
                core = embedded.get("core", {}) or {}
                application = embedded.get("application", {}) or {}

                st.caption(
                    "Pulled by doc_history and stored with the judgement. These observations do not currently alter DiScO scoring."
                )
                a1, a2, a3, a4 = st.columns(4)
                a1.metric("File type", str(doc_history.get("type", "—")).upper())
                a2.metric("Size", f"{int(doc_history.get('size_bytes', 0) or 0):,} bytes")
                a3.metric("Embedded creator", str(core.get("creator", "—")))
                a4.metric("Word TotalTime", str(application.get("TotalTime", "—")))

                clues = artifact.get("provenance_clues", []) or []
                if clues:
                    with st.expander("doc_history provenance clues", expanded=True):
                        for clue in clues:
                            st.write(f"• {clue}")

                timeline = artifact.get("timeline_events", []) or []
                if timeline:
                    with st.expander("doc_history timeline events"):
                        st.dataframe(pd.DataFrame(timeline), use_container_width=True, hide_index=True)

                with st.expander("Raw doc_history dataset"):
                    st.json(doc_history)

            with st.expander("Extracted document text"):
                st.text_area("Text sent to DiScO", value=text, height=320, disabled=True)

        with st.expander("Raw profile JSON"):
            st.json(profile.as_dict())
