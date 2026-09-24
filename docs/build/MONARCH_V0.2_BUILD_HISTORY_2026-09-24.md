# Monarch Model v0.2 Build History

**Date:** 2026-09-24  
**Status:** BUILD COMPLETE / CI GREEN  
**Design:** `docs/design/MONARCH_MODEL_V0.2_DESIGN.md`  
**Build plan:** `docs/design/MONARCH_MODEL_V0.2_BUILD_PLAN.md`  
**Frozen control:** `baseline/monarch-v0.1`

---

## 1. Build goal

The v0.2 build followed one rule:

> **Refactor first without changing meaning. Then expand meaning without rewriting infrastructure.**

The frozen Gravity caregiver implementation was treated as the control condition.

Stage 1 extracted reusable questionnaire rendering and response-generation machinery while preserving the existing caregiver FHIR / HL7 behavior.

Stage 2 used that machinery to add the first Monarch-specific assessment shell and capacity/context questions.

---

## 2. Starting point

The build began from commit:

`1db80719dff7f23439e6e6121e87f31f0f7bdcf9`

At that point the repository contained:

- the frozen imported MediLacra + Gravity caregiver baseline;
- baseline build/results documentation;
- the v0.2 Monarch design;
- the v0.2 build plan.

The known-good frozen baseline remains available at:

`baseline/monarch-v0.1`

---

## 3. Stage 1 — modular refactor

### Commit

`29f0f81c3a5453d33051c2d17c94c1b4b583c676`

**Message:** `Refactor caregiver questionnaire into modular renderer and response adapter`

### Added reusable questionnaire package

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

### Responsibilities

#### definitions.py

Introduced reusable Questionnaire item construction plus lightweight UI metadata extensions for:

- minimum assessment scope;
- UI section;
- placeholder;
- quantity unit;
- future help / What's This? content.

FHIR Questionnaire remains the canonical question-definition artifact.

#### renderer.py

Introduced generic Streamlit rendering for ordinary question types:

- `string`
- `text`
- `integer`
- `decimal`
- `quantity`
- `boolean`
- `choice`
- repeating `choice` → multiselect
- `group`

The renderer returns raw answers + decline state.

It does not perform clinical materialization.

Medication reconciliation remains an explicit custom renderer.

#### response_adapter.py

Introduced generic conversion from question definitions + raw state into FHIR QuestionnaireResponse items.

It supports:

- FHIR `value[x]` answer construction;
- quantity values with units;
- coded choices;
- repeating coded choices;
- nested groups;
- FHIR DataAbsentReason for declined answers;
- `enableWhen`;
- assessment-scope filtering;
- custom builders for special components.

#### choices.py

Introduced shared coded-choice vocabulary infrastructure.

#### scope.py

Introduced:

```text
urgent_only
basics
high_level
full
```

with display labels and scope comparison logic.

### Reproducibility cleanup

The imported repository had relied on CI installing dependencies separately from `requirements.txt`.

The build added:

- `PyYAML>=6.0`
- `pytest>=8.0`

to `requirements.txt`.

The GitHub Actions workflow was also corrected to run on pushes to `main` rather than the old MediLacra feature branch.

---

## 4. Stage 1 failure — circular import

The first CI run did not pass.

### Failure

The new `monarch.questionnaire.__init__` imported the response adapter.

The response adapter imported `DATA_ABSENT_REASON_URL` from `connectathon.gravity_questionnaire`.

But `gravity_questionnaire` was itself importing the new Monarch definitions.

Result:

```text
gravity_questionnaire
    ↓
monarch.questionnaire
    ↓
response_adapter
    ↓
gravity_questionnaire
```

Python correctly rejected the partially initialized module.

### Fix

Commit:

`0e0f3c26b93af32c1ec33e5a1e89e89d7e3fb85a`

**Message:** `Break questionnaire import cycle`

The package `__init__` was made intentionally inert.

Then:

`0a1a7046b2beeb2506d4f4eee8c3570f69dcf793`

**Message:** `Keep generic response adapter independent of Gravity`

The generic adapter stopped importing the FHIR DataAbsentReason URL from the Gravity implementation.

This established the intended dependency direction:

```text
Gravity implementation
        ↓
reusable Monarch questionnaire machinery
```

rather than the reusable layer depending back on Gravity.

### Stage 1 result

GitHub Actions run:

`36074407040`

completed successfully.

The mechanical refactor was therefore accepted before Stage 2 semantics were added.

---

# 5. Stage 2 — Monarch assessment shell

A temporary implementation branch was created:

`feature/monarch-v0.2-build`

### Core Stage 2 commit

`a8fac456e4a9ca4d1c50759a0f77b934577eee3b`

**Message:** `Build Monarch v0.2 assessment shell and capacity questions`

The commit was then fast-forwarded onto `main`.

The FHIR Questionnaire version was advanced from **0.2 → 0.3**.

---

# 6. New assessment-scope behavior

The top-level interaction now asks:

> **How much do you feel like you can handle right now?**

Options:

- Only urgent questions
- Just the basics
- High-level check-in
- Full evaluation

Internal codes:

```text
urgent_only
basics
high_level
full
```

The selected scope controls which questions are rendered.

The default UI selection is:

`basics`

The scope selection is also preserved in the QuestionnaireResponse rather than existing only as UI state.

---

# 7. Trauma-informed / interaction-preference questions

The following were added and remain available even at the smallest assessment scope:

1. Is there anything that would make this interaction feel unsafe?
2. Are there kinds of questions you would prefer not to answer?
3. Would you like someone with you for this discussion?
4. Are there ways we should communicate with you differently?
5. Are there procedures, environments, or situations you want us to know may be difficult?
6. Would you like to stop or come back later?

The build preserves these as self-report / interaction-preference data.

It does not derive a trauma diagnosis.

Full behavioral adaptation and resumable assessments remain roadmap work.

---

# 8. Existing caregiver baseline preserved

The existing caregiver questions remain available with scope metadata:

- sleep;
- pain;
- PHQ-2;
- heart rate;
- medication reconciliation;
- “How are you feeling today?”;
- “What’s going on in your life today?”

The existing materialization code and HL7 v2 ORU projection were deliberately **not generalized** to invent representations for every new Monarch question.

The existing known clinical/materialized fields continue to project as before.

New Monarch context remains faithfully available in the QuestionnaireResponse until downstream representation semantics are explicitly designed.

---

# 9. Financial capacity

Added:

- Can you handle an unexpected $100 expense?
- Can you handle an unexpected $500 expense?
- Could you miss one week of work?
- Are you having difficulty paying current healthcare costs?
- Is debt currently affecting healthcare choices?

Shared responses:

```text
Yes
No
Unsure
Prefer not to answer
```

Semantics:

- Yes / No / Unsure are explicit answers.
- Prefer not to answer is stored as FHIR DataAbsentReason `asked-declined`.
- Blank remains unanswered.

At full scope, optional exact values are also available for:

- current savings;
- current debt.

Exact values are not required to answer the coarse financial-capacity questions.

---

# 10. Caregiver capacity

Added:

### Care labor

> About how many hours per day do you spend administering care?

Stored as a quantity.

### Safe absence

> How long do you feel you can safely leave the home?

Supported states:

```text
Enter hours
Unsure
Varies
Prefer not to answer
```

When `Enter hours` is selected, a quantity in hours is enabled.

`Unsure` and `Varies` remain coded semantic states rather than fabricated numeric values.

### Home safety

> What safety precautions are in place at home?

Implemented as a repeating coded choice / Streamlit multiselect.

Initial options:

- someone else can provide supervision;
- medication organization/reminders;
- mobility/fall precautions;
- emergency contact or alert system;
- medical/safety equipment;
- environmental/home modifications;
- other;
- none currently;
- unsure.

Selecting `Other` can expose free-text context.

---

# 11. Context blob

Added:

> Anything else you want to add about what's going on right now?

The value is preserved as raw text.

The build intentionally performs **no semantic analysis** of that text.

Future file/audio adapters may produce additional preserved text or transcription, but analysis remains downstream.

---

# 12. Stage 2 initial CI failure — UI wiring

The first Stage 2 CI run compiled successfully and most tests passed, but two UI tests failed.

### Failure 1

The page still rendered the old title:

`Gravity — Caregiver Health Baseline`

### Failure 2

The generic renderer was rendering the `assessment-scope` Questionnaire item itself.

That meant the field had no default and duplicated the intended top-of-assessment scope control.

### Cause

The Stage 2 Questionnaire/data-definition changes had landed, but the intended Streamlit page wiring patch did not apply to the page body.

The data model was correct; the page was still calling the renderer with:

```text
selected_scope="full"
```

and did not exclude the scope item.

### Fix

Commit:

`0c0e76300ce84d99a7e6377513e538784c77d4ac`

**Message:** `Wire Monarch scope selector into caregiver UI`

The page now:

- uses the title `Monarch Model — Caregiver Assessment`;
- labels the synthetic person as `Caregiver`;
- renders one explicit scope selector at the top;
- defaults to `basics`;
- passes the selected scope into the generic renderer;
- excludes the scope item from being rendered twice;
- seeds `assessment-scope` into raw response state.

Test expectations were updated in:

`e588faf8c642a6bd2450b693f1faa7ae3c3f5287`

**Message:** `Update Streamlit expectations for Monarch caregiver UI`

---

# 13. Final test result

Final tested code commit:

`e588faf8c642a6bd2450b693f1faa7ae3c3f5287`

GitHub Actions run:

`36074750994`

Result:

```text
32 passed, 1 warning in 2.71s
```

The tested suites were:

- `tests/test_gravity_caregiver.py`
- `tests/test_gravity_hl7v2.py`
- `tests/test_gravity_caregiver_streamlit.py`
- `tests/test_monarch_questionnaire.py`

Compilation also passed for the new questionnaire modules and application page.

The remaining warning is an existing Python DeprecationWarning in:

`hl7_demo/utils.py:142`

for an invalid escape sequence in a string/docstring.

It is not a v0.2 test failure.

---

# 14. What the final tests establish

The green build establishes:

- existing caregiver baseline semantics still work through the modular adapter;
- existing FHIR materialization remains functional;
- existing HL7 v2 ORU generation remains functional;
- existing quality checks remain functional;
- scope metadata filters QuestionnaireResponse content;
- the UI defaults to `basics`;
- higher scope reveals higher-detail questions;
- `Unsure` remains an explicit coded answer;
- `Varies` remains an explicit coded answer;
- repeating choice / multiselect produces multiple QuestionnaireResponse answers;
- safe-absence hours are represented as a quantity only when hours are selected;
- optional exact financial amounts can be captured;
- decline remains distinct from unanswered / unsure;
- raw context text is preserved without interpretation.

---

# 15. Explicitly not built yet

The following remain roadmap items:

- partial completion / save / resume;
- full “What’s this?” presentation;
- human-readable glossary;
- Structured Sparsity reaction-time module;
- air-quality integration into this assessment;
- document/audio upload and transcription;
- DiScO educational-material evaluation;
- UnderstandingEvidence;
- Decision log;
- Act workflows;
- provider/caregiver notifications;
- pharmacy requests;
- decision-driven ORM generation;
- Outcome model;
- separate caregiver vs care-recipient identity model;
- automated interpretation of narrative;
- composite agency or cognitive-load scores.

---

# 16. Architectural result

The build changed the application from:

```text
question semantics
    scattered through
question definition + UI + response builder
```

to:

```text
FHIR Questionnaire definition
        ↓
generic renderer
        ↓
raw values + explicit response state
        ↓
generic response adapter
        ↓
FHIR QuestionnaireResponse
        ↓
existing downstream projections
```

That means most new ordinary assessment questions can now be added as data definitions rather than duplicated imperative UI/response code.

The UI remains intentionally simple.

Specialized modules remain specialized.

---

# 17. Next verification step

The automated build is green.

The next useful verification is a local human run through each assessment scope and generation of a new v0.3 artifact ZIP.

That will let the project compare:

```text
frozen v0.1 artifact
        vs.
Monarch v0.3 questionnaire / response artifact
```

while confirming that the old downstream FHIR and HL7 projections still preserve the original baseline facts.
