from __future__ import annotations

import json
from dataclasses import asdict

import streamlit as st

from connectathon.gravity_caregiver import build_artifact_files, build_artifact_zip
from connectathon.gravity_hl7v2 import build_caregiver_oru
from connectathon.gravity_materialize import build_submission_bundle
from connectathon.gravity_quality import caregiver_quality_gate
from connectathon.gravity_questionnaire import QUESTIONNAIRE_VERSION, build_questionnaire
from connectathon.gravity_response import build_questionnaire_response
from connectathon.gravity_storage import init_questionnaire_storage, load_questionnaire_responses, save_questionnaire_response
from hl7_demo.generators import gen_patient
from monarch.questionnaire.renderer import RenderResult, render_questionnaire
from storage_duckdb_entities import DEFAULT_DB_PATH, init_db, upsert_patient
from utils.db import reader


st.set_page_config(page_title="MediLacra — Gravity Caregiver Health", layout="wide")
st.title("Gravity — Caregiver Health Baseline")
st.caption("Same caregiver semantics, now rendered from the Questionnaire definition instead of hard-coded twice.")


def _load_patients(db_path: str, limit: int = 100) -> list[dict]:
    with reader(db_path=db_path) as connection:
        rows = connection.execute(
            """
            SELECT patient_id, mrn, patient_name, date_of_birth, sex, race,
                   ssn, phone, address, city, state, zip
            FROM patients
            ORDER BY created_ts DESC
            LIMIT ?
            """,
            [int(limit)],
        ).fetchall()
    columns = ["patient_id", "mrn", "patient_name", "date_of_birth", "sex", "race", "ssn", "phone", "address", "city", "state", "zip"]
    return [dict(zip(columns, row)) for row in rows]


def _reset_assessment_state() -> None:
    preserve = {"cg_db_path", "cg_patient", "cg_reset_assessment"}
    for key in list(st.session_state.keys()):
        if key.startswith("cg_") and key not in preserve:
            del st.session_state[key]


def _json_download(label: str, filename: str, value: dict, key: str) -> None:
    st.download_button(
        label,
        data=json.dumps(value, indent=2, sort_keys=True, default=str),
        file_name=filename,
        mime="application/fhir+json",
        key=key,
    )


def _render_medications(_item: dict, key_prefix: str) -> RenderResult:
    st.session_state.setdefault(f"{key_prefix}_medication_count", 1)
    count_columns = st.columns([1, 1, 4])
    with count_columns[0]:
        if st.button("+ Add medication", key=f"{key_prefix}_add_medication", use_container_width=True):
            st.session_state[f"{key_prefix}_medication_count"] += 1
            st.rerun()
    with count_columns[1]:
        if st.button(
            "− Remove last",
            key=f"{key_prefix}_remove_medication",
            disabled=st.session_state[f"{key_prefix}_medication_count"] <= 1,
            use_container_width=True,
        ):
            st.session_state[f"{key_prefix}_medication_count"] -= 1
            st.rerun()

    medications: list[dict] = []
    for index in range(int(st.session_state[f"{key_prefix}_medication_count"])):
        st.markdown(f"**Medication {index + 1}**")
        row1 = st.columns([4, 1, 1])
        with row1[0]:
            name = st.text_input("Medication", placeholder="e.g. lisinopril", key=f"{key_prefix}_med_name_{index}")
        with row1[1]:
            dose_value = st.text_input("Dose", key=f"{key_prefix}_med_dose_{index}")
        with row1[2]:
            dose_unit = st.text_input("Unit", placeholder="Example: mg", key=f"{key_prefix}_med_unit_{index}")
        row2 = st.columns(2)
        with row2[0]:
            route = st.selectbox("Route", options=["", "oral", "inhaled", "injection", "topical", "other"], key=f"{key_prefix}_med_route_{index}")
        with row2[1]:
            frequency = st.text_input("Frequency", placeholder="e.g. daily", key=f"{key_prefix}_med_frequency_{index}")
        medications.append({"name": name, "dose_value": dose_value, "dose_unit": dose_unit, "route": route, "frequency": frequency})
    return RenderResult(raw_input={"medications": medications})


reset_columns = st.columns([1, 4])
with reset_columns[0]:
    st.button("Reset assessment", key="cg_reset_assessment", on_click=_reset_assessment_state, use_container_width=True)

with st.sidebar:
    st.header("Baseline settings")
    db_path = st.text_input("DuckDB path", DEFAULT_DB_PATH, key="cg_db_path")
    st.write(f"Questionnaire version: **{QUESTIONNAIRE_VERSION}**")
    st.write("IRIS round trip: **Phase 2**")

init_db(db_path)
init_questionnaire_storage(db_path)
patients = _load_patients(db_path)

st.subheader("1. Synthetic caregiver")
patient_columns = st.columns([4, 1])
with patient_columns[1]:
    if st.button("Generate patient", type="secondary", use_container_width=True):
        generated_patient = gen_patient()
        upsert_patient(asdict(generated_patient), db_path=db_path)
        st.rerun()

if not patients:
    st.info("No synthetic patients are persisted yet. Generate one to start the questionnaire.")
    st.stop()

patient_lookup = {str(patient["patient_id"]): patient for patient in patients}
selected_patient_id = st.selectbox(
    "Patient",
    options=list(patient_lookup),
    format_func=lambda patient_id: f"{patient_id} — {patient_lookup[patient_id].get('patient_name') or 'Unnamed synthetic patient'}",
    key="cg_patient",
)
patient = patient_lookup[selected_patient_id]

st.divider()
st.subheader("2. Caregiver Health Baseline")
questionnaire = build_questionnaire()
rendered = render_questionnaire(
    questionnaire,
    selected_scope="full",
    key_prefix="cg",
    custom_renderers={"medications": _render_medications},
)

st.divider()
submit = st.button("Submit assessment", type="primary", use_container_width=True)

if submit:
    questionnaire_response = build_questionnaire_response(selected_patient_id, rendered.raw_input, declined=rendered.declined)
    bundle, cleanup = build_submission_bundle(patient, questionnaire_response)
    hl7v2 = build_caregiver_oru(patient, questionnaire_response)
    quality = caregiver_quality_gate(bundle)
    save_questionnaire_response(questionnaire_response, rendered.raw_input, bundle=bundle, db_path=db_path)
    st.session_state.cg_last_result = {
        "questionnaire": questionnaire,
        "questionnaire_response": questionnaire_response,
        "bundle": bundle,
        "hl7v2": hl7v2,
        "cleanup": cleanup,
        "quality": quality,
    }
    if quality["status"] == "PASS":
        st.success("Baseline materialized. Local plausibility/conformance checks passed.")
    else:
        st.warning("Assessment was preserved, but one or more plausibility/conformance checks failed.")

result = st.session_state.get("cg_last_result")
if result:
    st.divider()
    st.subheader("3. Materialized artifacts")
    artifact_files = build_artifact_files(result)
    st.download_button(
        "Download all artifacts (.zip)",
        data=build_artifact_zip(result),
        file_name="caregiver_health_phase1_artifacts.zip",
        mime="application/zip",
        key="cg_download_all_artifacts",
        use_container_width=True,
    )
    st.caption("ZIP contains the same individually downloadable Questionnaire, QuestionnaireResponse, FHIR Bundle, HL7 v2 ORU^R01, quality report, and Bundle-cleanup receipt shown below.")

    tab_questionnaire, tab_response, tab_bundle, tab_hl7v2, tab_quality = st.tabs(["Questionnaire", "QuestionnaireResponse", "FHIR Bundle", "HL7 v2", "PIQITT-style checks"])
    with tab_questionnaire:
        st.json(result["questionnaire"])
        _json_download("Download Questionnaire", f"caregiver_health_baseline_questionnaire_v{QUESTIONNAIRE_VERSION}.json", result["questionnaire"], "cg_download_questionnaire")
    with tab_response:
        st.json(result["questionnaire_response"])
        _json_download("Download QuestionnaireResponse", "caregiver_health_questionnaire_response.json", result["questionnaire_response"], "cg_download_response")
    with tab_bundle:
        st.caption(f"Existing Connectathon bundle cleanup: {result['cleanup']}")
        st.json(result["bundle"])
        _json_download("Download Bundle", "caregiver_health_phase1_bundle.json", result["bundle"], "cg_download_bundle")
        _json_download("Download Bundle cleanup receipt", "caregiver_health_bundle_cleanup.json", result["cleanup"], "cg_download_cleanup")
    with tab_hl7v2:
        st.caption("HL7 v2.5 ORU^R01 projection of the same QuestionnaireResponse. No encounter, order, or medication-administration event is invented.")
        st.code(result["hl7v2"].replace("\r", "\n"), language="text")
        st.download_button("Download HL7 v2 ORU^R01", data=result["hl7v2"], file_name="caregiver_health_oru_r01.hl7", mime="text/plain", key="cg_download_hl7v2")
    with tab_quality:
        st.write(f"**Result:** {result['quality']['status']}")
        st.write(result["quality"]["claim"])
        st.dataframe(result["quality"]["checks"], use_container_width=True, hide_index=True)
        _json_download("Download quality report", "caregiver_health_quality_report.json", result["quality"], "cg_download_quality")

with st.expander("Recent persisted QuestionnaireResponses"):
    try:
        recent = load_questionnaire_responses(limit=20, db_path=db_path)
        if recent:
            st.dataframe(
                [{"response_id": row["response_id"], "patient_id": row["patient_id"], "authored": row["authored"], "status": row["status"], "created_ts": row["created_ts"]} for row in recent],
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.info("No caregiver questionnaire responses persisted yet.")
    except Exception as exc:
        st.error(f"Unable to load recent responses: {exc}")
