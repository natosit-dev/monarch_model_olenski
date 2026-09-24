# Monarch Model v0.2 Design

**Version:** 0.2  
**Date:** 2026-09-24  
**Status:** DESIGN BASELINE — POST-READING, PRE-IMPLEMENTATION  
**Repository:** `natosit-dev/monarch_model_olenski`  
**Predecessor baseline:** `baseline/monarch-v0.1`

---

## 1. Purpose

This document defines the first post-baseline design for implementing concepts inspired by Erica Olenski's Monarch Model in a working healthcare data and workflow prototype.

The current repository already contains a frozen, known-good caregiver-health baseline imported from MediLacra. That baseline can:

- collect caregiver-health responses;
- preserve them in a FHIR QuestionnaireResponse;
- materialize selected values into FHIR resources;
- generate an HL7 v2 ORU^R01 from the same source response;
- run local structural and semantic-preservation checks.

The next phase is not simply "add more questions."

The purpose of v0.2 is to begin representing and operationalizing the conditions under which a patient or caregiver can:

1. **Understand**
2. **Decide**
3. **Act**

The design also captures the lived-experience, cognitive, environmental, financial, caregiving, and trauma-informed context that may expand or constrain those abilities.

This is an implementation design, not a claim that every item below is itself part of the formal Monarch Model. The source for this design is Nat's post-reading interpretation and implementation notes, combined with the existing caregiver-health baseline.

---

# 2. Raw Post-Reading Notes

The notes below are preserved as the original design input before formalization.

> Top of the evaluation- how much do you feel like you can handle right now? We can do high level, a full eval, just the basics, or only urgent questions.
>
> Have cognition tests at the top as optional to measure reaction and comprehension. Just pull the reaction test from structured sparsity.
>
> Cognitive Load- What's going on in your life? Record basic reaction time.
>
> Air quality- use existing API for medilacra
>
> Length and detail of medical history
>
> Current savings Vs. current debt
>
> For caregivers- how long do you feel you can safely leave the home?
>
> What safety precautions are in place at home?
>
> Add DiScO module. It'll be a POC for evaluating educational material.
>
> Family caregivers are an externality of value based care. Their labor should be measured. Add question- hours spent administering care per day.
>
> Add trauma informed questions for caregivers
>
> Add section to drop audio file into eval with basic transcription.
> Could also be doc, txt, raw text- anything the caregiver feels is relevant to what's going on. We'll parse it later but for now a text blob is fine.

Additional design decisions made immediately after reviewing those notes:

### Financial-capacity questions

Add:

- Can you handle an unexpected $100 expense?
- Can you handle an unexpected $500 expense?
- Could you miss one week of work?
- Are you having difficulty paying current healthcare costs?
- Is debt currently affecting healthcare choices?

Also allow optional exact amounts:

- current savings — optional exact amount;
- current debt — optional exact amount.

The coarse questions are the primary signal. Exact amounts are optional additional context, not required for participation.

### Trauma-informed questions

Use:

- Is there anything that would make this interaction feel unsafe?
- Are there kinds of questions you would prefer not to answer?
- Would you like someone with you for this discussion?
- Are there ways we should communicate with you differently?
- Are there procedures, environments, or situations you want us to know may be difficult?
- Would you like to stop or come back later?

### Context-artifact decision

The text/blob path is intentionally simple in v0.2.

Files or audio may be accepted and reduced to a preserved text representation or transcription. Analysis, classification, coding, extraction, and inference can happen later.

The first requirement is preservation, not interpretation.

---

# 3. Core Architecture

The working conceptual flow is:

```text
LIVED EXPERIENCE
      ↓
CONTEXT / CAPACITY / FRICTION
      ↓
UNDERSTAND
      ↓
DECIDE
      ↓
ACT
      ↓
OUTCOME
```

The system should not assume that failure at Understand, Decide, or Act belongs to the person.

A person may fail to understand because:

- educational material is poor;
- terminology is opaque;
- cognitive load is high;
- the information is too long;
- environmental conditions are bad;
- pain, sleep loss, caregiving burden, or financial strain are consuming available capacity;
- the information was delivered in the wrong format;
- the system asked too much at once.

A person may understand and still be unable to decide.

A person may understand and decide and still be unable to act.

Those are different states and should remain distinguishable.

---

# 4. Design Principles

## 4.1 Agency begins before the questionnaire

The evaluation itself must not contradict the model it is trying to implement.

At the top of the interaction, the person chooses how much they can handle.

Proposed scope selector:

```text
How much do you feel like you can handle right now?

[ ] Only urgent questions
[ ] Just the basics
[ ] High-level check-in
[ ] Full evaluation
```

This is not merely a UI preference.

It should be represented as an explicit assessment-scope decision that controls which questions are shown and which modules run.

A person should also be able to reduce scope or stop later.

---

## 4.2 Do not spend human capacity collecting machine-observable facts

When the system can obtain a fact from an existing source, it should generally avoid forcing a human to manually report it.

Example:

```text
location/context
      ↓
existing MediLacra AirNow integration
      ↓
air-quality observation
```

The human should not need to know the AQI or type it into a form.

This principle should be used carefully: machine-observable context can supplement lived experience, not override it.

---

## 4.3 Preserve source material before interpreting it

Original supplied content must survive.

For narrative material:

```text
original artifact
      ↓
transcription / text extraction
      ↓
preserved text blob
      ↓
optional later analysis
```

Do not immediately convert a narrative into a set of structured clinical facts.

Example:

A caregiver says:

```text
"I've barely slept and I can't keep all of the medication changes straight."
```

The first stored truth is:

```text
The caregiver said:
"I've barely slept and I can't keep all of the medication changes straight."
```

A later process may derive:

```text
possible cognitive-load signal
possible medication-management burden
possible sleep-related capacity constraint
```

Those are interpretations and must remain distinguishable from the original statement.

---

## 4.4 Preserve epistemic status

At minimum, the architecture should be able to distinguish:

- machine-observed fact;
- entered numeric/value response;
- person-reported statement;
- uploaded source artifact;
- transcription;
- derived calculation;
- model or rules-based interpretation;
- later clinician or reviewer interpretation.

The system should not silently promote an inference into "reality."

---

## 4.5 Optional means optional

Optional fields should not become effectively mandatory through UI pressure, validation rules, or downstream assumptions.

This is especially important for:

- cognition testing;
- exact financial amounts;
- trauma-related context;
- narrative uploads;
- free-text explanations;
- decision rationale.

---

# 5. Evaluation Entry Point

## 5.1 AssessmentScope

Proposed conceptual object:

```text
AssessmentScope
- scope_id
- respondent_id
- timestamp
- selected_scope
    - urgent_only
    - basics
    - high_level
    - full
- cognition_test_opt_in
- may_continue
- may_pause
- may_stop
```

The selected scope controls the rest of the evaluation.

### Urgent only

Collect only information required to identify immediate needs, safety concerns, or time-sensitive actions.

### Basics

Collect the smallest useful caregiver/patient state.

### High-level

Collect broad capacity and context without detailed history.

### Full

Enable the complete evaluation.

No scope should eliminate the ability to surface urgent information.

---

# 6. Optional Cognition / Reaction Testing

## 6.1 Reuse before generating

Do not build a new reaction test.

Reuse the reaction-time component already developed in the Structured Sparsity experiment.

The first implementation should preserve its basic behavior and extract it into a reusable module.

## 6.2 Purpose

The test is not intended to diagnose neurological or psychiatric conditions.

It is a lightweight contextual measurement of response timing and, later, basic comprehension performance.

Possible outputs:

```text
reaction_time_ms
trial_count
median_reaction_time_ms
completion_status
timestamp
```

Later versions may add comprehension tasks.

## 6.3 Longitudinal interpretation

A single reaction time has limited meaning.

The more useful comparison is within-person:

```text
usual/baseline reaction time
vs.
today's reaction time
```

paired with context such as:

- sleep;
- pain;
- acute stress;
- caregiving load;
- financial disruption;
- complexity of the current decision.

No diagnostic conclusion should be generated from reaction time alone.

---

# 7. Cognitive Load and Available Capacity

## 7.1 Core prompt

Retain the existing/open-ended approach:

> What's going on in your life?

This is intentionally broad.

It allows context to be supplied without forcing the respondent into categories invented by the system.

## 7.2 Supporting signals

Potential capacity signals include:

- hours slept;
- pain;
- PHQ-2 baseline items;
- heart rate;
- reaction time;
- medication burden;
- medical-history complexity;
- caregiving labor;
- financial strain;
- environmental burden;
- free-text or uploaded context.

## 7.3 Medical-history complexity

Capture the length and detail of medical history as a possible system burden.

The first implementation should avoid pretending that "complexity" has already been solved as one score.

Possible direct measures later include:

- number of active conditions;
- number of active medications;
- number of treating clinicians;
- number of recent encounters;
- number of recent medication changes;
- length of available longitudinal history.

For v0.2, preserve the concept and available counts without building a composite complexity score.

---

# 8. Environmental Context

## 8.1 Air quality

Reuse the existing MediLacra air-quality integration.

Proposed conceptual representation:

```text
EnvironmentalContext
- observed_at
- location_context
- aq_source
- aqi
- pollutant details if available
- observation provenance
```

The environmental observation is machine-sourced context.

It should not be represented as a self-report unless the person actually reports an environmental experience.

---

# 9. Financial Capacity

The purpose is to understand financial room to absorb healthcare disruption without forcing exact financial disclosure.

## 9.1 Primary questions

- Can you handle an unexpected $100 expense?
- Can you handle an unexpected $500 expense?
- Could you miss one week of work?
- Are you having difficulty paying current healthcare costs?
- Is debt currently affecting healthcare choices?

Each should support, at minimum:

```text
Yes
No
Unsure
Prefer not to answer
```

Where useful, brief free-text context can be optional.

## 9.2 Optional exact amounts

Also support:

- Current savings — optional exact amount.
- Current debt — optional exact amount.

These fields are supplementary.

The system must not require exact amounts in order to calculate or display the coarse financial-capacity signals.

## 9.3 Proposed conceptual object

```text
FinancialCapacity
- unexpected_100_capacity
- unexpected_500_capacity
- could_miss_week_of_work
- healthcare_cost_difficulty
- debt_affecting_healthcare_choices
- current_savings_exact_optional
- current_debt_exact_optional
- respondent_notes_optional
- timestamp
```

The exact values should retain clear provenance as self-reported values.

No creditworthiness, socioeconomic rank, or eligibility inference should be generated in v0.2.

---

# 10. Caregiver Capacity

The existing caregiver-health baseline becomes one component of a larger caregiver-capacity model.

## 10.1 Existing useful signals

Continue to collect:

- sleep;
- pain;
- PHQ-2 baseline;
- heart rate;
- medication reconciliation;
- current lived-experience journal responses.

## 10.2 New caregiver-capacity questions

### Safe absence

> How long do you feel you can safely leave the home?

The answer should support both:

- structured duration where possible;
- optional explanation.

Do not infer that a caregiver *should* be able to leave for a particular duration.

### Home safety

> What safety precautions are in place at home?

This should allow multiple selections and free text.

Do not initially force the response into a complete home-safety ontology.

### Caregiving labor

> About how many hours per day do you spend administering care?

The purpose is to measure labor that is often invisible in healthcare workflows and value-based-care accounting.

At v0.2, measure time before attempting monetization.

Possible later expansion:

- medication administration;
- transportation;
- scheduling;
- clinical communication;
- physical assistance;
- monitoring/supervision;
- documentation;
- insurance/administrative work.

Do not require task-level breakdown in the first implementation.

## 10.3 Conceptual object

```text
CaregiverCapacity
- caregiver_id
- person_supported_id
- care_hours_per_day
- safe_absence_duration
- home_safety_precautions
- backup_support_available
- sleep
- pain
- medication_burden
- notes
- timestamp
```

"Family caregivers are an externality of value-based care" is preserved here as a motivating design hypothesis: caregiver labor should be measured rather than assumed to be free or infinitely available.

The prototype should measure the labor first. Economic valuation can be a later analysis.

---

# 11. Trauma-Informed Interaction

The trauma-informed section should not become a trauma-history extraction form.

The goal is to let the person define interaction boundaries and support needs.

Use:

1. Is there anything that would make this interaction feel unsafe?
2. Are there kinds of questions you would prefer not to answer?
3. Would you like someone with you for this discussion?
4. Are there ways we should communicate with you differently?
5. Are there procedures, environments, or situations you want us to know may be difficult?
6. Would you like to stop or come back later?

## 11.1 Design behavior

These responses should be able to change the interaction.

Examples:

- hide or skip marked question categories;
- reduce evaluation scope;
- display preferred communication guidance;
- record support-person preference;
- pause the assessment;
- stop without treating the assessment as failed.

## 11.2 Conceptual object

```text
TraumaInformedPreferences
- respondent_id
- unsafe_conditions
- question_boundaries
- support_person_preference
- communication_preferences
- difficult_procedures_or_environments
- pause_or_return_preference
- timestamp
```

These are interaction preferences and self-reported constraints.

Do not automatically infer a trauma diagnosis.

---

# 12. Context Artifacts

## 12.1 Goal

Provide a low-friction way for a patient or caregiver to add context the structured questionnaire did not capture.

Accepted inputs may include:

- audio;
- `.txt`;
- document files;
- pasted raw text;
- other simple text-extractable material.

## 12.2 v0.2 behavior

Keep this deliberately simple.

### Audio

```text
audio file
   ↓
basic transcription
   ↓
preserved text blob
```

### Documents

```text
document / txt
   ↓
basic text extraction where supported
   ↓
preserved text blob
```

### Raw text

```text
pasted text
   ↓
preserved text blob
```

No semantic parsing is required for the initial implementation.

## 12.3 ContextArtifact

```text
ContextArtifact
- artifact_id
- respondent_id
- created_at
- media_type
- original_filename_optional
- original_content_reference_optional
- extracted_or_transcribed_text
- respondent_description_optional
- processing_status
- provenance
```

If the original binary is retained, the text is a derived representation of that artifact.

If only text is retained, that limitation should be explicit.

## 12.4 Non-goal

Do not automatically create diagnoses, Observations, conditions, or other structured clinical facts from uploaded narrative in v0.2.

Analysis can be performed later against the preserved artifact.

---

# 13. Understand

"Understand" is an operational capability, not a checkbox that information was displayed.

## 13.1 "What's this?" everywhere

Every major section should include a visible **What's this?** affordance explaining:

- what is being asked;
- why it is being asked;
- how the answer may be used;
- who may see it;
- whether it can be skipped.

This information should be adjacent to the interaction, not buried in a general privacy notice.

## 13.2 Human-readable glossary

Maintain a glossary for healthcare and system terminology.

The target style is:

- technically accurate;
- plainspoken;
- short;
- concrete;
- willing to use examples;
- not written like a payer policy or standards specification.

Internal shorthand: **"Nat Style, but for normal humans."**

A glossary entry should be able to contain:

```text
term
plain-language meaning
why it matters here
example
optional technical definition
source/provenance
```

## 13.3 Examples and context

When a concept is abstract, provide concrete examples.

Examples are educational material, not defaults that should bias the person toward one answer.

## 13.4 Demonstrated understanding

The system should eventually be able to record evidence that understanding occurred.

Potential evidence:

- teach-back;
- selecting the correct interpretation of a statement;
- identifying a likely consequence;
- answering a comprehension question;
- correctly explaining the next step;
- asking a question demonstrating recognition of the relevant issue.

Do not treat:

- clicking "I understand";
- scrolling;
- opening the glossary;
- spending a particular amount of time on a page

as proof of understanding.

Those may be interaction signals but not comprehension evidence.

## 13.5 UnderstandingEvidence

```text
UnderstandingEvidence
- evidence_id
- person_id
- subject/concept
- evidence_type
- prompt
- response
- result
- timestamp
- provenance
```

---

# 14. Educational Material and DiScO

DiScO will be reused as a proof of concept for evaluating educational material.

The use case is not "score the patient."

It is:

```text
educational material
      ↓
DiScO analysis
      ↓
human comprehension attempt
      ↓
UnderstandingEvidence
```

This makes it possible to distinguish:

```text
The person did not demonstrate understanding.
```

from:

```text
The material may have been difficult, semantically sparse,
jargon-heavy, or poorly scaffolded.
```

The prototype should preserve both sides of the interaction.

## 14.1 EducationalMaterial

```text
EducationalMaterial
- material_id
- title
- source
- version
- raw_text
- target_concept
- disco_analysis_optional
- timestamp
```

## 14.2 DiScO boundary

DiScO output is an analysis of the material.

It is not itself proof that a human will or will not understand that material.

The human-side evidence remains separate.

---

# 15. Decide

A decision is not simply a final selected value.

The prototype should preserve:

- what decision was being made;
- what options were presented;
- potential effects of each option;
- uncertainty;
- the selected choice if one was made;
- optional rationale;
- whether the person deferred or declined to decide.

There may be no singular "correct" choice.

## 15.1 Decision log

Proposed conceptual object:

```text
Decision
- decision_id
- person_id
- question
- context
- available_options[]
- option_effects[]
- uncertainty
- selected_option_optional
- rationale_optional
- decision_status
    - decided
    - deferred
    - declined
    - unresolved
- timestamp
- provenance
```

The decision log should preserve change over time rather than overwriting an earlier decision.

---

# 16. Act

The system should be capable of turning an understood and recorded decision into an action.

Initial action targets include:

- update providers;
- update caregivers;
- send pharmacy requests;
- link to relevant materials;
- create ORM messages where appropriate.

## 16.1 Action object

```text
Action
- action_id
- originating_decision_id_optional
- actor
- recipient
- action_type
- requested_state_change
- representation
    - UI event
    - FHIR
    - HL7 v2
    - document/link
    - other
- status
    - proposed
    - queued
    - sent
    - acknowledged
    - completed
    - failed
    - declined
- timestamps
- provenance
```

An action should not be considered complete merely because a message was generated.

Generation, transmission, receipt, and resulting state change are different events.

---

# 17. Outcome

Outcomes should remain downstream from actions.

Possible later questions:

- Did the requested change happen?
- Did the person gain or lose practical capacity?
- Was the information useful?
- Did the decision need to be revisited?
- Did the action introduce new burden?
- Did caregiver labor change?

No comprehensive outcome model is required for v0.2.

The object is included now so Understand → Decide → Act does not terminate at message generation.

---

# 18. Conceptual Object Inventory

The v0.2 design introduces the following conceptual objects:

```text
AssessmentScope
Person
Patient
Caregiver
ContextArtifact
CapacityState
EnvironmentalContext
FinancialCapacity
CaregiverCapacity
TraumaInformedPreferences
EducationalMaterial
UnderstandingEvidence
Decision
Action
Outcome
```

These are conceptual objects, not an instruction to immediately create one Python class or one FHIR resource for each.

Implementation should reuse existing structures where they already preserve the needed semantics.

---

# 19. CapacityState

A useful aggregate concept is `CapacityState`, but it should not become a single magic score.

```text
CapacityState
- person_id
- observed_at
- sleep
- pain
- mood_baseline
- heart_rate
- reaction_time
- medical_history_context
- financial_capacity_reference
- caregiver_capacity_reference
- environmental_context_reference
- narrative_context_reference
```

The initial prototype should expose constituent factors.

Do not collapse them into "agency score = 72" or equivalent.

The model is intended to make constraints visible, not manufacture false precision.

---

# 20. Relationship to the Frozen Baseline

The frozen v0.1 baseline remains the control condition.

It already supports:

```text
caregiver input
      ↓
QuestionnaireResponse
      ↓
FHIR materialization
      +
HL7 v2 ORU generation
```

v0.2 extends the model around that working machinery.

The existing caregiver questionnaire is not discarded.

It becomes one instrument feeding the larger model.

Proposed relationship:

```text
AssessmentScope
      ↓
context + caregiver/patient capacity
      ↓
existing caregiver-health questions
      ↓
UNDERSTAND
      ↓
DECIDE
      ↓
ACT
      ↓
OUTCOME

      ↘ representations ↙
       FHIR / HL7 v2
```

Representation remains downstream from the human/system interaction.

---

# 21. Representation Boundary

The system should distinguish:

```text
what happened
what a person said
what the system observed
what the model inferred
what was represented
what was transmitted
what another system received
```

FHIR and HL7 v2 are representations of portions of this reality.

They are not the reality itself.

A v0.2 implementation should therefore preserve enough provenance to ask later:

> What survived the transformation?

This is especially important for:

- lived-experience narrative;
- financial strain;
- caregiver labor;
- trauma-informed preferences;
- demonstrated understanding;
- decision uncertainty;
- rationale;
- action state.

---

# 22. Proposed Implementation Sequence

The design does not require implementing every module at once.

## Phase A — assessment shell

Build:

- AssessmentScope;
- urgent/basic/high-level/full routing;
- visible pause/stop behavior;
- "What's this?" framework;
- glossary data structure.

Keep the existing caregiver baseline working.

## Phase B — capacity/context expansion

Add:

- financial-capacity questions;
- optional exact savings/debt;
- caregiver care-hours question;
- safe-absence question;
- home-safety question;
- trauma-informed preferences;
- medical-history context;
- AirNow context reuse.

## Phase C — cognition reuse

Extract/reuse the Structured Sparsity reaction-time test.

Make it optional.

Store raw/basic results without diagnostic interpretation.

## Phase D — ContextArtifact

Add:

- raw-text entry;
- txt/document upload;
- audio upload;
- basic transcription;
- preserved text blob.

No semantic extraction required.

## Phase E — Understand

Add:

- glossary UI;
- examples/context;
- educational material object;
- simple demonstrated-understanding tasks;
- UnderstandingEvidence.

## Phase F — DiScO

Reuse the existing DiScO module to evaluate educational material.

Keep DiScO analysis separate from human comprehension evidence.

## Phase G — Decide

Add the decision log with:

- options;
- effects;
- uncertainty;
- selected/deferred/declined states;
- optional rationale.

## Phase H — Act

Implement proof-of-concept actions:

- provider update;
- caregiver update;
- pharmacy request;
- link/material delivery;
- ORM generation.

Track action status rather than equating generation with completion.

---

# 23. v0.2 Non-Goals

Do not attempt to solve all of the following in the first implementation:

- diagnostic cognition testing;
- a single agency score;
- a single cognitive-load score;
- full financial modeling;
- creditworthiness or eligibility prediction;
- monetization of caregiver labor;
- automated trauma diagnosis;
- automated conversion of narrative into clinical truth;
- a complete home-safety ontology;
- a complete medical-complexity score;
- a comprehensive outcome model;
- automatic causal inference;
- universal FHIR mapping for every Monarch concept;
- external PIQI validation for every new object;
- replacing the existing caregiver baseline.

---

# 24. Minimum Acceptance Criteria for the First v0.2 Build

A first implementation should be considered materially different from the frozen caregiver baseline when it can demonstrate all of the following:

1. The respondent can choose urgent/basic/high-level/full scope.
2. The scope choice actually changes which questions are presented.
3. The respondent can pause or stop.
4. At least one section has a functional "What's this?" explanation.
5. The financial-capacity questions are collected.
6. Exact savings and debt are optional.
7. Caregiving hours/day are collected.
8. Safe-absence duration can be recorded.
9. Home-safety context can be recorded.
10. The trauma-informed preference questions are available and skippable.
11. At least raw text can be preserved as a ContextArtifact.
12. Existing caregiver FHIR output still works.
13. Existing caregiver HL7 v2 output still works.
14. New self-report/context information retains explicit provenance.
15. No narrative-analysis inference is silently promoted into a source fact.

The reaction-time test, DiScO integration, demonstrated-understanding tasks, decision log, and Act workflows can follow incrementally.

---

# 25. Design Decisions Worth Preserving

Several decisions in this version should be treated as intentional unless later evidence justifies changing them.

### The assessment can shrink itself

The person's available capacity controls the depth of evaluation.

### Context is not garnish

Sleep, pain, money, caregiving burden, environment, and narrative context can materially affect a person's ability to understand, decide, and act.

### Caregiver labor is measured

Caregiver labor is not assumed to be free or infinitely available.

### Trauma-informed means changing interaction behavior

The system should not merely collect trauma context and then behave exactly the same way.

### Narrative is preserved before analysis

The blob is intentionally dumb.

### DiScO evaluates material, not the human

The system should be able to ask whether educational material failed the person.

### Understanding requires evidence

"I clicked the button" is not the same as "I understood."

### Decisions preserve ambiguity

Not every healthcare decision has one correct answer.

### Actions are state transitions

Generating a message is not the same as completing an action.

### Representation is downstream

FHIR and HL7 v2 represent selected portions of the interaction. They should not be allowed to erase provenance or silently redefine what happened.

---

# 26. Version History

## v0.1 — 2026-09-24

Frozen imported MediLacra + Gravity Caregiver Health baseline.

See:

`docs/baseline/MONARCH_BASELINE_v0.1_2026-09-24.md`

## v0.2 — 2026-09-24

First full post-reading Monarch implementation design.

Adds:

- assessment-scope control;
- optional cognition/reaction measurement;
- cognitive-load/context framing;
- environmental context;
- financial capacity;
- caregiver labor/capacity;
- trauma-informed interaction preferences;
- ContextArtifact;
- Understand design;
- glossary / "What's this?";
- demonstrated-understanding evidence;
- DiScO educational-material evaluation;
- Decision log;
- Act workflow;
- explicit outcome boundary;
- provenance and representation rules.
