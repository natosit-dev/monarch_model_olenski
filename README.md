# monarch_model_olenski
Designs inspired by Erica Olenski's Monarch Model. "A framework for operationalizing lived experience as the driver of human agency in healthcare innovation."

Full description at https://www.monarchfutures.com/themonarchmodeltextonly 

I am building some prototypes to see how the ideas translate into healthcare data.

## Imported MediLacra baseline

This repository starts from a deliberately small working slice of **MediLacra** plus the **Gravity Caregiver Health** module developed for HL7 Connectathon 43.

**Import provenance**

- Source repository: `natosit-dev/medilacra`
- Source branch: `feature/gravity-caregiver-baseline-v0.1`
- Source commit: `284d6e6fa382218f06e427854684fcbfee117a0d`
- Imported: 2026-09-24

The baseline includes the MediLacra synthetic Patient generator required by the caregiver workflow, HL7 helpers, DuckDB persistence helpers, generic FHIR control/preflight helpers, the Gravity caregiver questionnaire/materialization/storage/quality/HL7 v2 modules, the Streamlit caregiver page, tests, and the original Gravity build documentation.

It intentionally does **not** import unrelated Connectathon experiments, DiScO, PIQI tooling, IRIS integration, notebooks, or large terminology datasets.

### Run the caregiver baseline

```bash
pip install -r requirements.txt
streamlit run pages/10_Gravity_Caregiver_Health.py
```

### Test

```bash
pytest -q tests/test_gravity_caregiver.py tests/test_gravity_hl7v2.py tests/test_gravity_caregiver_streamlit.py
```

The imported code is a baseline, not the Monarch implementation itself. The next layer can operationalize **Understand → Decide → Act** while keeping lived experience, agency, healthcare-system state, and data representation distinct.

## License note

The imported MediLacra source is AGPL-3.0. This repository therefore preserves that license for the derivative baseline rather than relabeling the copied code under the MIT license that was selected when the repository was initialized.
