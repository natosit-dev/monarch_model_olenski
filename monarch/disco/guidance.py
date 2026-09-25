from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FeatureGuidance:
    """Plain-language interpretation guidance for one DiScO observation.

    Guidance is intentionally separate from detector configuration. Rules decide
    what is observed and how much it can contribute; Virgil explains what the
    observation means, why it may matter, and where it can misfire.
    """

    summary: str
    why_it_matters: str
    caveat: str
    orwell_quote: str | None = None
    orwell_source: str | None = None


VIRGIL_OVERVIEW = (
    "DiScO does not decide whether writing is good, true, human, or AI-generated. "
    "It records observable features and then compresses some of them into two bounded signals."
)

METRIC_GUIDANCE: dict[str, str] = {
    "Semantic signal": (
        "How much the active rules currently associate this wording with extra reconstruction cost, "
        "blurred mechanism, hidden agency, or other damage to meaning. It is not a truth score."
    ),
    "AI signal": (
        "How much the active rules currently associate this text with AI-oriented style/provenance patterns. "
        "It is not an authorship probability."
    ),
    "Count": "How many times this detector matched the submitted text.",
    "Rate / 100": "The match count normalized to 100 words so texts of different lengths are easier to compare.",
    "Strength": (
        "A bounded version of the raw rate. It shows how much of this feature's configured evidence budget "
        "has been activated."
    ),
    "Contribution": "What this feature actually added to the final semantic or AI signal for this judgement.",
}

CADENCE_GUIDANCE = FeatureGuidance(
    summary=(
        "Records the word count of every sentence, then summarizes how similar or different those lengths are. "
        "Uniformity asks whether sentences stay about the same size; range asks how far the shortest and longest are apart."
    ),
    why_it_matters=(
        "Cadence may eventually help distinguish highly regular generated prose from writing that mixes short, medium, "
        "and sprawling sentences. DiScO currently records the observation without scoring it."
    ),
    caveat=(
        "Genre, formatting, quotations, dialogue, and sentence splitting all affect cadence. The raw sentence-length "
        "sequence is therefore preserved so later interpretations can change without losing the observation."
    ),
)

FEATURE_GUIDANCE: dict[str, FeatureGuidance] = {
    "metaphor_vocabulary": FeatureGuidance(
        summary="Counts a small vocabulary of abstract spatial or material metaphors such as substrate, landscape, lens, and architecture.",
        why_it_matters="These words can compress complicated relationships, but they can also make an explanation feel concrete without specifying the actual relationship.",
        caveat="The words are not inherently vague. A literal or well-defined use can be completely precise.",
    ),
    "mechanism_placeholders": FeatureGuidance(
        summary="Looks for verbs such as shape, align, transform, facilitate, and optimize that can stand in for an unstated mechanism.",
        why_it_matters="A sentence may tell you that something changed without telling you what acted on what, through which process, or under which conditions.",
        caveat="These verbs can also describe real mechanisms. The detector only identifies places worth inspecting.",
    ),
    "anthropomorphic_mechanism": FeatureGuidance(
        summary="Looks for human-like mental-state claims about models or systems, such as 'the model learned' or 'the AI thinks'.",
        why_it_matters="Human-like language can quietly substitute a familiar story for an unspecified technical mechanism or provenance path.",
        caveat="Some forms can be technically appropriate in context, especially when 'learned' refers explicitly to training. The problem is unsupported mechanism substitution, not personification by itself.",
    ),
    "nominalizations": FeatureGuidance(
        summary="Counts noun-like forms such as implementation, coordination, complexity, and resilience.",
        why_it_matters="Turning actions and qualities into nouns can make prose denser and can hide who did what to whom.",
        caveat="Technical writing legitimately contains many nominalizations, and this detector is a suffix-based approximation rather than a grammatical parser.",
    ),
    "unintroduced_acronyms": FeatureGuidance(
        summary="Looks for capitalized abbreviations that appear without an earlier long-form introduction in the same text.",
        why_it_matters="Readers may need outside knowledge to reconstruct what an unexplained acronym means.",
        caveat="All-caps headings, time-zone abbreviations, labels, and other capitalized text can be mistaken for acronyms. Treat the match list as evidence to inspect, not a verdict.",
    ),
    "ready_made_phrases": FeatureGuidance(
        summary="Counts prefabricated phrases such as 'at the end of the day', 'it is worth noting', and 'moving forward'.",
        why_it_matters="Stock phrases can arrive already assembled, letting prose advance without adding much new information.",
        caveat="A familiar phrase can still be the clearest wording. Repetition and context matter more than the phrase's mere existence.",
    ),
    "verbal_false_limbs": FeatureGuidance(
        summary="Looks for padded verb constructions such as 'make use of', 'give rise to', and 'take into consideration'.",
        why_it_matters="These constructions can make a simple action harder to see by wrapping it in extra grammatical machinery.",
        caveat="Some multi-word constructions carry a real distinction. The detector is looking for avoidable padding, not banning phrases.",
        orwell_quote="If it is possible to cut a word out, always cut it out.",
        orwell_source="George Orwell, Politics and the English Language (1946)",
    ),
    "dead_metaphors": FeatureGuidance(
        summary="Looks for familiar metaphors such as 'move the needle', 'tip of the iceberg', 'deep dive', and 'north star'.",
        why_it_matters="A worn metaphor can be processed as a stock unit instead of forcing the writer to specify the relationship being described.",
        caveat="A conventional metaphor can still communicate efficiently. The concern is automatic use that blurs or replaces the actual claim.",
        orwell_quote="Never use a metaphor, simile or other figure of speech which you are used to seeing in print.",
        orwell_source="George Orwell, Politics and the English Language (1946)",
    ),
    "prestige_diction": FeatureGuidance(
        summary="Counts high-status or intimidating vocabulary such as paradigm, epistemic, robust, nuanced, multidimensional, and operationalize.",
        why_it_matters="Prestige vocabulary can be useful shorthand, but it can also raise the apparent sophistication of a claim without adding mechanism or evidence.",
        caveat="Specialized words are often exactly the right words in specialized work. DiScO should not punish necessary terminology.",
        orwell_quote="Never use a long word where a short one will do.",
        orwell_source="George Orwell, Politics and the English Language (1946)",
    ),
    "semantically_sparse_words": FeatureGuidance(
        summary="Counts broad evaluative words such as meaningful, strategic, authentic, impact, quality, resilience, and success.",
        why_it_matters="These words often tell the reader how to value something without specifying the observable conditions that would make the evaluation true.",
        caveat="Sparse does not mean meaningless. A document may define these terms elsewhere or use them as established domain shorthand.",
    ),
    "concealment_euphemisms": FeatureGuidance(
        summary="Looks for phrases that can soften, depersonalize, or obscure a material action, such as 'workforce reduction' or 'collateral damage'.",
        why_it_matters="Euphemistic wording can suppress agency, affected people, or the physical event that occurred.",
        caveat="Some phrases are legitimate legal, operational, or domain terms. The question is whether the wording clarifies the event or hides it.",
        orwell_quote="language as an instrument for expressing and not for concealing or preventing thought",
        orwell_source="George Orwell, Politics and the English Language (1946)",
    ),
    "em_dash_style": FeatureGuidance(
        summary="Counts em dashes as a lightweight style observation.",
        why_it_matters="Repeated em-dash use is being tested as one small signal associated with some generated prose styles.",
        caveat="Humans use em dashes constantly. This is intentionally a weak AI-oriented vote and says nothing about semantic quality by itself.",
    ),
    "markdown_scaffolding": FeatureGuidance(
        summary="Counts visible Markdown structure such as headings, bullets, block quotes, bold text, code spans, and horizontal rules.",
        why_it_matters="Highly scaffolded formatting is common in assistant-generated answers and can provide a small style/provenance signal.",
        caveat="Markdown is also ordinary human formatting, especially in technical communities. It is not evidence of bad meaning or AI authorship on its own.",
    ),
    "contrastive_reframing": FeatureGuidance(
        summary="Looks for compact contrast templates such as 'not just X, but Y' and 'this isn't X, it's Y'.",
        why_it_matters="These structures are common in polished generated explanations and can create a synthetic sense of clarification or escalation.",
        caveat="Contrast is basic human rhetoric. This is only a low-weight style signal.",
    ),
    "formulaic_signposting": FeatureGuidance(
        summary="Looks for guide-rail phrases such as 'in other words', 'the key point is', and 'what matters is'.",
        why_it_matters="Repeated signposting can indicate prose that is continually packaging its own interpretation for the reader.",
        caveat="Good human explanations use signposting too. The observation matters only in combination with other evidence.",
    ),
    "pseudo_conversational_setup": FeatureGuidance(
        summary="Looks for canned conversational openings such as 'here's the thing', 'here's why', and 'think of it this way'.",
        why_it_matters="These phrases can simulate conversational intimacy while introducing a preassembled explanatory move.",
        caveat="They are also ordinary speech. This is intentionally a small style/provenance signal.",
    ),
    "punchy_synthetic_conclusion": FeatureGuidance(
        summary="Looks for short synthetic wrap-up lines such as 'That distinction matters.' or 'That's the point.'",
        why_it_matters="Generated prose often compresses an argument into a polished final slogan after the explanation.",
        caveat="Humans also write punchy conclusions. The detector only records a narrow recurring structure.",
    ),
    "label_colon_scaffolding": FeatureGuidance(
        summary="Looks for short line-leading labels followed by a colon, such as 'Problem:' or 'Key point:'.",
        why_it_matters="Repeated label-colon blocks are one common way generated text turns prose into modular explanatory scaffolding.",
        caveat="This structure is normal in notes, forms, technical documentation, and presentations. It is a weak style signal only.",
    ),
}


def get_feature_guidance(feature_id: str) -> FeatureGuidance:
    """Return guidance for a known feature, or a safe generic fallback."""

    return FEATURE_GUIDANCE.get(
        feature_id,
        FeatureGuidance(
            summary="This detector records an observable text pattern configured in the active DiScO rule set.",
            why_it_matters="Its meaning depends on the detector definition and the scoring priors active for this judgement.",
            caveat="No dedicated Virgil explanation has been written for this rule yet.",
        ),
    )
