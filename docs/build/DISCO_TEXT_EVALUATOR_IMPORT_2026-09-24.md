# DiScO Text Evaluator Import

**Date:** 2026-09-24  
**Target:** `natosit-dev/monarch_model_olenski`  
**Source repository:** `natosit-dev/medilacra_connect`  
**Source branch:** `DiScO`  
**Source commit:** `020704f8b8d1ac12182b39ac2889d826451cf703`

## Purpose

Reuse DiScO as a standalone deterministic text evaluator for later Monarch educational-material experiments.

This import intentionally preserves the text-scoring boundary and does **not** import Disco Inferno.

## Imported behavior

The Monarch copy preserves:

- deterministic token/feature matching;
- checked-in DiScO default rule dictionaries;
- checked-in supplemental AI-style rules;
- bounded semantic signal;
- bounded AI-oriented signal;
- raw match text and character offsets;
- rates per 100 words;
- bounded feature strengths and contributions;
- deterministic sentence-cadence observations.

The scoring equation remains:

```text
strength = rate / (rate + half_saturation)
contribution = max_contribution × strength
```

Signals remain capped at `1.0`.

They are **not calibrated probabilities**.

## Deliberately excluded

The following source components are not imported:

- Disco Inferno mutation/corruption machinery;
- HL7/FHIR entropy experiments;
- Disco Fever;
- mutable runtime rule overrides;
- Discotorium;
- judgement history / JSONL corpus;
- AI-generated feedback labels;
- document upload/extraction;
- `doc_history` provenance;
- local judgement persistence;
- Virgil guidance layer.

The imported page is intentionally:

```text
pasted text
    ↓
checked-in rules
    ↓
deterministic feature inventory
    ↓
bounded semantic / AI signals
    +
unscored sentence cadence
```

## Target files

```text
monarch/disco/
    __init__.py
    config.py
    engine.py
    cadence.py
    rules/
        defaults.json
        ai_style_structures.json

pages/30_DiScO_Text_Evaluator.py
tests/test_monarch_disco.py
```

The page is a thin UI over the imported evaluator.
