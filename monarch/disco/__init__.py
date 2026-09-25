"""DiScO — Deterministic Inspection of Semantic Coupling in Outputs.

Text-only evaluator imported from the MediLacra Connect DiScO branch.
Disco Inferno mutation machinery, feedback history, document provenance, and
mutable calibration tools are intentionally excluded.
"""

from .cadence import SentenceCadenceObservation, inspect_sentence_cadence, sentence_word_lengths
from .config import DEFAULT_RULES, FeatureRule, load_rules
from .engine import DiScOProfile, FeatureResult, Match, inspect_text

DESCRIPTION = "Deterministic Inspection of Semantic Coupling in Outputs"

__all__ = [
    "DESCRIPTION",
    "DEFAULT_RULES",
    "DiScOProfile",
    "FeatureResult",
    "FeatureRule",
    "Match",
    "SentenceCadenceObservation",
    "inspect_sentence_cadence",
    "inspect_text",
    "load_rules",
    "sentence_word_lengths",
]
