# Monarch Model Baseline Freeze v0.1

**Date:** 2026-09-24  
**Status:** FROZEN BASELINE  
**Repository:** `natosit-dev/monarch_model_olenski`

## Purpose

This checkpoint freezes the known-good starting point before Monarch-specific implementation begins.

The baseline is intentionally the imported MediLacra + Gravity Caregiver Health slice, not yet a full Monarch implementation. It exists so future work on **Understand → Decide → Act**, determinants of agency, lived experience, and action workflows can be compared against a stable starting state.

## Source provenance

The working code was copied from:

- Source repository: `natosit-dev/medilacra`
- Source branch: `feature/gravity-caregiver-baseline-v0.1`
- Source commit: `284d6e6fa382218f06e427854684fcbfee117a0d`
- Import commit in this repository: `d7e47e9d3bce6e61981bd15441a6e4b920600de2`

The import preserved the Gravity caregiver-health implementation, its supporting synthetic Patient generation and storage dependencies, FHIR control/preflight helpers, HL7 v2 output, tests, and the original Gravity design/build documentation.

The following original build-history documents remain preserved under `docs/gravity/`:

- `CAREGIVER_HEALTH_BASELINE_PHASE_1_PLAN_v0.1_2026-09-08.md`
- `CAREGIVER_HEALTH_BASELINE_PHASE_1_BUILD_HISTORY_v0.1_2026-09-08.md`
- `CAREGIVER_HEALTH_BASELINE_PHASE_1_BUILD_ANALYSIS_v0.1_2026-09-08.md`
- `CAREGIVER_HEALTH_BASELINE_INITIAL_USER_TESTING_v0.1_2026-09-09.md`

## Monarch repository build history

### 2026-09-24 — repository initialized

A new public repository, `monarch_model_olenski`, was created to explore how Erica Olenski's Monarch Model can be operationalized in healthcare data and workflow.

The repo was initialized separately rather than modifying MediLacra in place so Monarch-specific semantics and workflow can evolve without making the original synthetic-data project carry the new conceptual load.

### 2026-09-24 — dependency boundary identified

The Gravity caregiver page depends on more than the visible Streamlit file. The minimum working slice was identified as:

- Gravity questionnaire, response, materialization, quality, storage, and HL7 v2 modules
- generic FHIR control/preflight helpers
- MediLacra Patient dataclass/generator support used by the UI
- shared HL7 formatting helpers
- DuckDB persistence helpers
- ZIP/address reference data
- tests and original Gravity documentation

Unrelated Connectathon experiments, DiScO, PIQI tooling, IRIS integration, notebooks, and large terminology datasets were deliberately excluded.

### 2026-09-24 — baseline imported

The working slice was imported to `main` in commit:

`d7e47e9d3bce6e61981bd15441a6e4b920600de2`

The derivative repository license was aligned with MediLacra's AGPL-3.0 license rather than leaving the copied code under the MIT license selected during initial repo creation.

### 2026-09-24 — clean local checkout tested

The repository was pulled into a fresh folder and run in its own Python 3.11 environment.

The imported `requirements.txt` did not include two packages that the old CI installed separately:

- `pytest`
- `PyYAML`

Those were installed explicitly for the clean-room local run. This is a reproducibility issue to clean up after the freeze; it does not alter the tested runtime behavior.

### 2026-09-24 — caregiver artifact run succeeded

The caregiver-health baseline successfully materialized a complete artifact package from one response.

The run demonstrated the intended baseline flow:

```text
caregiver input
      ↓
QuestionnaireResponse
      ↓
materialization
   ↙       ↘
FHIR       HL7 v2
Bundle     ORU^R01
   ↓          ↓
quality / semantic-preservation checks
```

## Results

### FHIR output

The generated FHIR collection contained **10 resources**:

| Resource type | Count |
|---|---:|
| Patient | 1 |
| Questionnaire | 1 |
| QuestionnaireResponse | 1 |
| Observation | 6 |
| MedicationStatement | 1 |

Structural validation reported **PASS** for all 8 checks:

- Bundle resourceType
- Bundle type = `collection`
- 10 entries present
- every entry contains a resource with resourceType and id
- every entry has a `fullUrl`
- all 10 `fullUrl` values are unique
- no MessageHeader in the PIQI collection boundary
- all internal references resolve by `fullUrl`

### Semantic / plausibility quality gate

The quality report returned overall status **PASS**.

All 16 checks passed:

- bundle preflight
- Patient existence
- Questionnaire existence
- QuestionnaireResponse existence
- authored timestamp
- subject reference
- response parse integrity
- sleep plausibility
- pain plausibility
- heart-rate plausibility
- PHQ-2 answer integrity
- PHQ-2 total calculation
- heart-rate materialization
- pain materialization
- medication cardinality
- medication dose materialization

### HL7 v2 output

The same caregiver response successfully produced an HL7 v2.5 `ORU^R01`.

The ORU preserved structured caregiver-health values and free-text lived-experience responses as OBX segments, demonstrating that the imported baseline can project the same source response into both FHIR and HL7 v2 representations.

### Known limitation

The quality report explicitly states:

> Self-contained FHIR collection shape; external PIQI ingest not yet exercised.

Therefore this freeze establishes **local structural coherence, semantic-preservation checks, and dual-representation generation**. It does **not** claim successful ingest by an external PIQI endpoint or other external receiver.

## Artifact manifest

The tested local artifact archive was:

`caregiver_health_phase1_artifacts (4).zip`

SHA-256:

`872b3959923a938c5a837f128b19afc9b329debb59c125a1d358b849987b095e`

Contained artifacts:

| File | Bytes | SHA-256 |
|---|---:|---|
| `caregiver_health_baseline_questionnaire_v0.2.json` | 6813 | `5499a3153aa250b6858f071f4dc53b3ec8bc5c65cadaabd3292cdc88c85941c2` |
| `caregiver_health_questionnaire_response.json` | 3581 | `bc48188cc432c5e1f22c0f3d616456985b74aa4ef83694f6c9abaefbe16d691b` |
| `caregiver_health_phase1_bundle.json` | 20978 | `b93cc2e7550a8214a16df14e2a93a900ef06e87115aea97f99b8fcabc991ecdd` |
| `caregiver_health_oru_r01.hl7` | 1806 | `38ee1fa08846c04a0372d43b04afb6daf4cdf1a2abf3d0dfe308ebff58303b20` |
| `caregiver_health_quality_report.json` | 3632 | `226ab9a4dcb69e1246226083b65cea291533fc781ece83909317ef35111b0d09` |
| `caregiver_health_bundle_cleanup.json` | 314 | `41d0a8619e7cf2c7b9d10cb7f74cd1f187a5eae51b2a0531650a83772c8024b5` |

The raw archive is **not committed to this public repository** because the run contains entered caregiver-response content. The hashes preserve exact-run provenance without publishing that content.

## Freeze boundary

This baseline intentionally freezes the pre-Monarch behavior:

- caregiver-health input
- FHIR Questionnaire / QuestionnaireResponse
- Observation and MedicationStatement materialization
- local structural and semantic quality checks
- HL7 v2 ORU generation
- DuckDB-backed storage support

It does **not** yet implement:

- Understand semantics or demonstrated-understanding evidence
- decision objects or a decision log
- explicit choices and consequence representation
- Act workflows
- provider/caregiver notifications
- pharmacy requests
- generated ORM actions as a consequence of a decision
- Monarch determinants-of-agency semantics
- friction modeling
- agency-state modeling

Those belong after this checkpoint.

## Baseline rule

Future Monarch work should be compared against this checkpoint rather than retroactively editing it into the desired future architecture.

**Baseline first. Transformation second.**
