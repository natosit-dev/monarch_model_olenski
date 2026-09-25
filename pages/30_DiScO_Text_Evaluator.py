from __future__ import annotations

import pandas as pd
import streamlit as st

from monarch.disco import DESCRIPTION, inspect_sentence_cadence, inspect_text, load_rules


st.set_page_config(page_title="DiScO — Text Evaluator", layout="wide")
st.title("🪩 DiScO — Text Evaluator")
st.caption(DESCRIPTION)
st.write(
    "Deterministic text inspection only. This page does not load Disco Inferno, "
    "document provenance, judgement history, or calibration tools."
)
st.caption(
    "DiScO inventories observable text features associated with semantic reconstruction "
    "cost and experimental style/authorship signals. The scores are bounded signals, not probabilities."
)

with st.form("disco_text_evaluator"):
    text = st.text_area(
        "Text to inspect",
        height=320,
        placeholder="Paste educational material or other text here...",
    )
    evaluate = st.form_submit_button("⚖️ JUDGEMENT", type="primary", use_container_width=True)

if evaluate:
    if not text.strip():
        st.warning("Paste some text first.")
    else:
        rules = load_rules()
        profile = inspect_text(text, rules=rules)
        cadence = inspect_sentence_cadence(text)

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Words", f"{profile.word_count:,}")
        m2.metric("Characters", f"{profile.character_count:,}")
        m3.metric("Semantic signal", f"{profile.signal_score:.3f}")
        m4.metric("AI signal", f"{profile.ai_signal_score:.3f}")

        st.markdown("### Feature inventory")
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
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

        st.markdown("### Matches")
        matched = [feature for feature in profile.features if feature.matches]
        if not matched:
            st.caption("No configured features matched this text.")
        else:
            for feature in matched:
                with st.expander(f"{feature.label} · {feature.count} match{'es' if feature.count != 1 else ''}"):
                    st.caption(
                        f"rate={feature.rate_per_100_words:.3f}/100 · "
                        f"strength={feature.strength:.3f} · "
                        f"semantic contribution={feature.semantic_contribution:.3f} · "
                        f"AI contribution={feature.ai_contribution:.3f}"
                    )
                    st.code("\n".join(match.text for match in feature.matches), language="text")

        st.markdown("### Sentence cadence · unscored")
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Sentences", f"{cadence.sentence_count:,}")
        c2.metric("Mean words", f"{cadence.mean_words:.1f}")
        c3.metric("Std. dev.", f"{cadence.std_dev_words:.2f}")
        c4.metric("Variation / mean", f"{cadence.coefficient_of_variation:.2f}")
        c5.metric("Range", f"{cadence.range_words:,} words")
        st.caption("Cadence is recorded as a deterministic observation only; it contributes to neither score.")

        with st.expander("Raw profile JSON"):
            st.json(profile.as_dict())
