# DiScO Suite Import

**Date:** 2026-09-24  
**Target:** `natosit-dev/monarch_model_olenski`

## DiScO source

- Repository: `natosit-dev/medilacra_connect`
- Branch: `DiScO`
- Source commit: `020704f8b8d1ac12182b39ac2889d826451cf703`

## Document provenance source

- Repository: `natosit-dev/doc_history`
- Branch: `main`
- Source commit: `a8fbd9602dcea6376c5004f1cbacae6cdcc90e73`
- License: MIT; notice preserved at `doc_history/LICENSE`

## Included

The Monarch prototype carries the DiScO suite while remaining separate from Disco Inferno:

- deterministic text scoring;
- pasted-text input;
- DOCX/PDF upload and deterministic text extraction;
- document provenance / metadata inspection;
- AI-generated feedback label;
- local judgement history;
- exact rule snapshot and hashes per judgement;
- unscored sentence cadence;
- Virgil feature guidance;
- Disco Fever calibration console;
- mutable local rule overrides;
- Discotorium corpus/history review;
- JSON/JSONL downloads.

Local state is stored below `data/disco/` and ignored by Git.

## Excluded

The following remain excluded:

- Disco Inferno entropy/corruption experiments;
- HL7/FHIR mutation machinery;
- experiment worker/process-control code;
- PIQI integration;
- MediLacra synthetic-reality experiment orchestration.

```text
DiScO suite
  ├─ inspect text/documents
  ├─ preserve provenance
  ├─ store labelled judgements
  ├─ calibrate rules
  └─ review corpus

NOT

Disco Inferno
  └─ mutate healthcare representations / run entropy experiments
```
