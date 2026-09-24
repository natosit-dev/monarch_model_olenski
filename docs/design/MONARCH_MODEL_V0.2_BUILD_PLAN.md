# Monarch Model v0.2 Build Plan

**Version:** 0.2  
**Date:** 2026-09-24  
**Status:** READY FOR IMPLEMENTATION  
**Design reference:** `docs/design/MONARCH_MODEL_V0.2_DESIGN.md`  
**Frozen baseline:** `baseline/monarch-v0.1`

---

## 1. Objective

Refactor the existing Gravity caregiver questionnaire into a modular Monarch assessment framework without changing the meaning or behavior of the frozen baseline, then add the first Monarch-specific assessment features.

The build is intentionally split into two stages:

```text
STAGE 1
Refactor without changing meaning.

STAGE 2
Expand meaning without rewriting infrastructure.
```

This sequence is the primary risk-control mechanism for the build.

---

## 2. Working Assumptions

### 2.1 Synthetic Patient = evaluated caregiver

For v0.2, the existing synthetic `Patient` represents the caregiver/person being evaluated.

The prototype does not yet model a separate caregiver and care recipient.

This is an intentional simplification for the current proof of concept.

A later version may introduce:

```text
Caregiver / respondent
        ↓ cares for
Care recipient / patient
```

but that relationship is out of scope for the first v0.2 build.

### 2.2 Existing caregiver baseline remains the control condition

The frozen baseline must remain reproducible.

No refactor is considered complete until the current caregiver questionnaire can run through the new framework and produce a semantically equivalent QuestionnaireResponse.

### 2.3 FHIR Questionnaire remains the question-definition source

Do not create a parallel proprietary form schema unless FHIR Questionnaire becomes materially obstructive.

Reuse the existing question-format code and extend it only where needed.

### 2.4 The UI should remain simple

The Streamlit UI should consume definitions and renderer output rather than contain duplicated question semantics.

The UI is not the semantic model.

---

# 3. Target Architecture

Current baseline:

```text
hard-coded question definition
        ↓
hand-written Streamlit widget
        ↓
hand-written raw_input key
        ↓
hand-written decline mapping
        ↓
hand-written QuestionnaireResponse builder
```

Target:

```text
FHIR Questionnaire definitions
        ↓
generic renderer
        ↓
raw answers + response state
        ↓
generic response adapter
        ↓
FHIR QuestionnaireResponse
        ↓
existing materialization / HL7 / storage
```

Special-purpose modules remain explicit:

```text
Medication reconciliation ─┐
Reaction-time test         │
ContextArtifact upload     ├── custom components / modules
DiScO                      │
Decision                   │
Action                     ┘
```

Do not force specialized workflows through the generic renderer when doing so makes the code harder to understand.

---

# 4. Proposed Module Structure

Create a reusable questionnaire package:

```text
monarch/
    questionnaire/
        __init__.py
        definitions.py
        renderer.py
        response_adapter.py
        choices.py
        scope.py
```

The exact filenames may change during implementation if a simpler structure emerges, but the separation of responsibilities should remain.

## 4.1 definitions.py

Responsibilities:

- reusable question-definition helpers;
- FHIR Questionnaire item construction;
- renderer metadata;
- scope metadata;
- display/help metadata hooks;
- common option lists.

The existing `_question_item()` helper is the starting point.

## 4.2 renderer.py

Responsibilities:

- render ordinary Questionnaire items into Streamlit controls;
- preserve raw values;
- preserve declined state;
- avoid clinical/materialization logic.

Initial generic mappings:

| Questionnaire type | Streamlit behavior |
|---|---|
| `string` | text input |
| `text` | text area |
| `integer` | numeric/select input |
| `decimal` | numeric input |
| `quantity` | numeric value with known unit |
| `boolean` | yes/no selection |
| `choice` | selectbox |
| `choice + repeats` | multiselect |
| `group` | section / nested rendering |
| `display` | explanatory text/help content |

The renderer should return values and interaction state, not build FHIR resources.

## 4.3 response_adapter.py

Responsibilities:

- convert renderer state into QuestionnaireResponse items;
- map values to the correct FHIR answer type;
- preserve declined answers as DataAbsentReason;
- preserve unanswered values as unanswered;
- preserve coded states such as `Unsure` or `Varies`;
- recurse through groups;
- support repeating choices.

The adapter should eliminate the need to manually add every ordinary new question to `build_questionnaire_response()`.

## 4.4 choices.py

Centralize shared option vocabularies such as:

```text
Yes
No
Unsure
Prefer not to answer
```

Important semantic handling:

```text
Yes                   → coded/boolean answer
No                    → coded/boolean answer
Unsure                → explicit coded answer
Varies                → explicit coded answer where supported
Prefer not to answer  → DataAbsentReason asked-declined
Blank                 → unanswered
```

`Unsure` must not be collapsed into decline or blank.

## 4.5 scope.py

Responsibilities:

- assessment scope definitions;
- scope ordering;
- helper functions for deciding whether a section/question is visible.

Initial scopes:

```text
urgent_only
basics
high_level
full
```

---

# 5. Stage 1 — Refactor Without Changing Meaning

Stage 1 is successful only if the frozen caregiver workflow behaves materially the same after the refactor.

## 5.1 Extract reusable question helpers

Move or wrap the reusable parts of `connectathon/gravity_questionnaire.py`.

Do not remove the old module until the new abstraction is proven.

Prefer:

```text
gravity_questionnaire.py
        ↓ imports / delegates
monarch/questionnaire/*
```

over a destructive rewrite.

## 5.2 Build generic renderer

Implement ordinary item rendering for the question types already present in the caregiver baseline.

Initial baseline support must include:

- quantity;
- integer;
- choice;
- boolean;
- text;
- group;
- repeating medication group remains custom.

## 5.3 Build generic response adapter

Implement equivalent QuestionnaireResponse generation for the existing caregiver baseline.

It must preserve:

- linkId;
- text;
- answer type;
- PHQ coded answers;
- quantities and UCUM units;
- declined responses;
- medication repeating groups;
- free text.

## 5.4 Preserve existing custom medication UI

Do not generalize medication reconciliation unless the new renderer makes it trivially obvious.

The current medication UI already works.

Keep it as a custom component for this build.

## 5.5 Semantic-equivalence test

Create a regression test using the same baseline input through:

1. the frozen/legacy response path;
2. the new renderer/adapter path.

Normalize IDs/timestamps if necessary.

Compare semantic content rather than byte-for-byte serialization.

The test should establish:

```text
old caregiver input
      ↓
old response builder
      ↓
QuestionnaireResponse A

same caregiver input
      ↓
new response adapter
      ↓
QuestionnaireResponse B

A ≈ B semantically
```

This is the acceptance gate for Stage 1.

---

# 6. Stage 2 — Expand Meaning

Only begin Stage 2 after Stage 1 equivalence passes.

---

## 6.1 Assessment scope

Add the first Monarch-specific interaction at the top:

> How much do you feel like you can handle right now?

Options:

- Only urgent questions
- Just the basics
- High-level check-in
- Full evaluation

The selected scope must actually affect which sections/questions render.

Do not add a decorative scope selector that leaves the rest of the assessment unchanged.

### Initial routing proposal

| Section | Minimum scope |
|---|---|
| urgent/safety interaction controls | all |
| basic caregiver state | basics |
| sleep/pain/life context | basics |
| heart rate / medication reconciliation | high-level |
| financial-capacity questions | high-level |
| optional exact savings/debt | full |
| broader detailed context | full |

The exact routing can be tuned after the first working pass.

---

# 7. New Question Types / Behaviors

## 7.1 Multiselect

Add generic support for:

```text
type = choice
repeats = true
```

Render as a Streamlit multiselect.

Primary initial use:

> What safety precautions are in place at home?

Suggested broad options:

- Someone else can provide supervision
- Medication organization/reminders
- Mobility/fall precautions
- Emergency contact or alert system
- Medical equipment/safety equipment
- Environmental/home modifications
- Other
- None currently
- Unsure

Allow optional free text for additional context.

Do not block implementation on a perfect home-safety terminology system.

---

## 7.2 Unsure

Add `Unsure` as a normal coded response where applicable.

It must remain distinguishable from:

- blank/unanswered;
- declined;
- invalid input.

---

## 7.3 Varies

Add `Varies` where the quantity cannot reasonably be represented by a single stable value.

Initial use:

> How many hours do you feel you can safely leave the home?

Supported states:

```text
numeric hours
Unsure
Varies
Prefer not to answer
```

For v0.2, use **hours only**.

Do not introduce minutes/days/unit selectors yet.

---

# 8. Financial Capacity

Add:

1. Can you handle an unexpected $100 expense?
2. Can you handle an unexpected $500 expense?
3. Could you miss one week of work?
4. Are you having difficulty paying current healthcare costs?
5. Is debt currently affecting healthcare choices?

Primary response set:

```text
Yes
No
Unsure
Prefer not to answer
```

Add optional exact fields:

- Current savings
- Current debt

Exact amounts are supplementary and must not be required to use the coarse financial-capacity questions.

Do not calculate creditworthiness, eligibility, socioeconomic rank, or a composite financial score.

---

# 9. Caregiver Capacity

Add:

## 9.1 Care hours

> About how many hours per day do you spend administering care?

Use a numeric hours/day field plus decline handling.

Do not require a detailed task breakdown in this build.

## 9.2 Safe absence

> How many hours do you feel you can safely leave the home?

Support:

- numeric hours;
- Unsure;
- Varies;
- decline.

## 9.3 Home safety

> What safety precautions are in place at home?

Use multiselect plus optional free text.

---

# 10. Trauma-Informed Questions

Add the following questions as optional/skippable:

1. Is there anything that would make this interaction feel unsafe?
2. Are there kinds of questions you would prefer not to answer?
3. Would you like someone with you for this discussion?
4. Are there ways we should communicate with you differently?
5. Are there procedures, environments, or situations you want us to know may be difficult?
6. Would you like to stop or come back later?

For this build, preserving these answers is sufficient.

The system does not yet need to dynamically implement every preference.

Do not infer a trauma diagnosis from these responses.

---

# 11. Context Input

## 11.1 First implementation

Start with raw text.

Reuse the existing free-text preservation behavior.

The core requirement is:

```text
user-supplied context
      ↓
preserved text blob
```

Do not analyze or structure the narrative in the initial implementation.

## 11.2 Later adapters

Roadmap:

```text
audio → transcription → preserved text
doc/txt → extraction → preserved text
raw text → preserved text
```

The preserved source/transcription remains distinct from later interpretations.

---

# 12. "What's this?" — Roadmap

Add to the v0.2 roadmap but do not block the first modular build.

Extend question metadata to eventually support:

- what is being asked;
- why it is being asked;
- how the answer may be used;
- who may see it;
- whether it can be skipped;
- example/context;
- glossary reference.

The generic renderer should be designed so this metadata can later be displayed consistently.

Do not bury this information in a general privacy page.

---

# 13. Partial Completion — Roadmap

Add explicit support later for:

```text
QuestionnaireResponse.status = in-progress
```

and:

- save;
- stop;
- resume;
- return later.

Current baseline behavior always produces a completed response.

Do not silently treat a stopped assessment as a failed or completed assessment.

---

# 14. Reaction / Cognition Testing — Roadmap

Reuse the existing Structured Sparsity reaction-time component.

Do not build a new reaction test.

Future integration should:

- be optional;
- preserve raw/basic timing results;
- support longitudinal comparison;
- avoid diagnostic claims.

This remains a separate module rather than a generic questionnaire widget.

---

# 15. DiScO — Roadmap

DiScO will be added later as a separate module for educational-material evaluation.

Target relationship:

```text
EducationalMaterial
      ↓
DiScO
      ↓
material analysis

separate from

human comprehension
      ↓
UnderstandingEvidence
```

Do not couple DiScO to the questionnaire renderer.

---

# 16. Understand / Decide / Act — Later Build Layers

The modular questionnaire refactor is groundwork.

It should make later implementation easier without prematurely forcing those objects into QuestionnaireResponse.

Future modules:

```text
UnderstandingEvidence
Decision
Action
Outcome
```

Questionnaire answers may feed those modules, but they should not be treated as interchangeable.

---

# 17. Test Plan

## 17.1 Existing tests must continue to pass

Retain:

- caregiver questionnaire tests;
- caregiver HL7 v2 tests;
- caregiver Streamlit smoke tests;
- FHIR materialization/quality behavior.

## 17.2 Add renderer tests

Test each generic question type:

- text;
- integer;
- decimal;
- quantity;
- boolean;
- choice;
- repeating choice/multiselect;
- group.

## 17.3 Add response-adapter tests

Verify:

- correct FHIR value[x] mapping;
- declined → DataAbsentReason `asked-declined`;
- Unsure remains explicit;
- Varies remains explicit;
- blank remains unanswered;
- multiselect produces multiple answers;
- nested groups recurse correctly.

## 17.4 Add scope tests

For each scope, verify that expected questions appear and excluded questions do not.

At minimum:

```text
urgent_only < basics < high_level < full
```

## 17.5 Regression test

Prove semantic equivalence between legacy and refactored caregiver baseline outputs.

This is the most important test in the build.

---

# 18. Acceptance Criteria

## Stage 1 acceptance

All of the following must be true:

1. Existing caregiver baseline still launches.
2. Existing tests pass.
3. Existing caregiver inputs can be rendered through the new modular system.
4. The new response adapter produces a semantically equivalent QuestionnaireResponse.
5. Existing FHIR materialization still works.
6. Existing HL7 v2 ORU generation still works.
7. Existing quality checks still pass.
8. Medication reconciliation still works.

Only then is the refactor considered complete.

## Stage 2 acceptance

The v0.2 assessment must then demonstrate:

1. Scope selector is present.
2. Scope actually controls rendered content.
3. Financial-capacity questions are collected.
4. Optional savings/debt amounts are supported.
5. Unsure is represented explicitly.
6. Multiselect works.
7. Care hours/day can be recorded.
8. Safe-absence hours / Unsure / Varies can be recorded distinctly.
9. Home-safety precautions can be recorded.
10. Trauma-informed questions are available and skippable.
11. Raw context text is preserved without automatic interpretation.
12. Existing FHIR/HL7 baseline outputs remain functional.
13. Self-report and derived values retain distinguishable provenance.

---

# 19. Explicit Non-Goals for This Build

Do not allow the first build to expand into:

- separate caregiver/care-recipient identity model;
- full partial-completion/resume system;
- full What's This?/glossary implementation;
- DiScO integration;
- reaction-time integration;
- automatic narrative analysis;
- automated trauma inference;
- decision log;
- action workflow;
- ORM generation from decisions;
- complete outcome model;
- universal FHIR mapping for all Monarch concepts;
- agency/cognitive-load scoring.

These remain roadmap items unless implementation reveals that one is genuinely required to make the modular architecture work.

---

# 20. Build Order

Recommended execution order:

```text
1. Create reusable questionnaire package
2. Extract definition helpers
3. Implement generic renderer
4. Implement response adapter
5. Prove old/new semantic equivalence
6. Run existing FHIR/HL7/quality tests
────────────────────────────────────
7. Add scope
8. Add shared choices: Unsure / decline semantics
9. Add multiselect
10. Add financial-capacity questions
11. Add caregiver capacity questions
12. Add trauma-informed questions
13. Add raw context text
14. Expand tests
15. Generate v0.2 artifact bundle
16. Compare v0.2 artifacts against frozen baseline
```

---

# 21. Build Rule

The guiding rule for this implementation is:

> **Refactor first without changing meaning. Then expand meaning without rewriting infrastructure.**

The frozen v0.1 branch remains the reference point if the build starts to drift.
