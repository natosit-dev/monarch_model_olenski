from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Iterable

from .config import DEFAULT_RULES, FeatureRule


WORD_RE = re.compile(r"\b\w+(?:[-']\w+)*\b")
ACRONYM_RE = re.compile(r"\b[A-Z][A-Z0-9-]{1,7}\b")
INTRODUCED_ACRONYM_RE = re.compile(
    r"\b[A-Z][A-Za-z]+(?:\s+[A-Z]?[A-Za-z]+){0,6}\s*\(([A-Z][A-Z0-9-]{1,7})\)"
)


@dataclass(frozen=True)
class Match:
    text: str
    start: int
    end: int


@dataclass(frozen=True)
class FeatureResult:
    id: str
    label: str
    count: int
    rate_per_100_words: float
    half_saturation: float
    strength: float
    semantic_max: float
    semantic_contribution: float
    ai_max: float
    ai_contribution: float
    matches: tuple[Match, ...]


@dataclass(frozen=True)
class DiScOProfile:
    word_count: int
    character_count: int
    features: tuple[FeatureResult, ...]
    signal_score: float
    ai_signal_score: float

    def as_dict(self) -> dict:
        return asdict(self)


def _lexicon_matches(text: str, terms: Iterable[str], stems: bool = False) -> list[Match]:
    suffix = r"\w*" if stems else ""
    pattern = re.compile(
        r"\b(?:" + "|".join(re.escape(term) for term in terms) + r")" + suffix + r"\b",
        re.IGNORECASE,
    )
    return [Match(m.group(0), m.start(), m.end()) for m in pattern.finditer(text)]


def _regex_matches(text: str, pattern: str) -> list[Match]:
    compiled = re.compile(pattern, re.IGNORECASE)
    return [Match(m.group(0), m.start(), m.end()) for m in compiled.finditer(text)]


def _unintroduced_acronym_matches(text: str) -> list[Match]:
    introduced = {m.group(1) for m in INTRODUCED_ACRONYM_RE.finditer(text)}
    return [
        Match(m.group(0), m.start(), m.end())
        for m in ACRONYM_RE.finditer(text)
        if m.group(0) not in introduced
    ]


def _matches_for_rule(text: str, rule: FeatureRule) -> list[Match]:
    if rule.kind == "lexicon":
        return _lexicon_matches(text, rule.terms)
    if rule.kind == "lexicon_stem":
        return _lexicon_matches(text, rule.terms, stems=True)
    if rule.kind == "regex" and rule.pattern:
        return _regex_matches(text, rule.pattern)
    if rule.kind == "unintroduced_acronym":
        return _unintroduced_acronym_matches(text)
    raise ValueError(f"Unsupported DiScO feature kind: {rule.kind}")


def _bounded_strength(rate: float, half_saturation: float) -> float:
    """Map a non-negative rate to [0, 1) with an asymptotic curve."""

    if half_saturation <= 0:
        raise ValueError("DiScO half_saturation must be greater than zero.")
    if rate <= 0:
        return 0.0
    return rate / (rate + half_saturation)


def inspect_text(
    text: str,
    rules: tuple[FeatureRule, ...] = DEFAULT_RULES,
) -> DiScOProfile:
    """Create a deterministic feature inventory for one text blob.

    Raw feature counts and rates are canonical observations. Scoring is a
    bounded compression layer:

        strength = rate / (rate + half_saturation)
        contribution = strength * configured maximum

    Both final signals are capped at 1.0. Neither is a calibrated probability.
    """

    word_count = len(WORD_RE.findall(text))
    denominator = max(word_count, 1)
    features: list[FeatureResult] = []

    for rule in rules:
        if rule.semantic_max < 0 or rule.ai_max < 0:
            raise ValueError("DiScO maximum contributions must be non-negative.")

        matches = tuple(_matches_for_rule(text, rule))
        rate = (len(matches) / denominator) * 100.0
        strength = _bounded_strength(rate, rule.half_saturation)
        semantic_contribution = strength * rule.semantic_max
        ai_contribution = strength * rule.ai_max

        features.append(
            FeatureResult(
                id=rule.id,
                label=rule.label,
                count=len(matches),
                rate_per_100_words=rate,
                half_saturation=rule.half_saturation,
                strength=strength,
                semantic_max=rule.semantic_max,
                semantic_contribution=semantic_contribution,
                ai_max=rule.ai_max,
                ai_contribution=ai_contribution,
                matches=matches,
            )
        )

    semantic_score = min(sum(feature.semantic_contribution for feature in features), 1.0)
    ai_score = min(sum(feature.ai_contribution for feature in features), 1.0)

    return DiScOProfile(
        word_count=word_count,
        character_count=len(text),
        features=tuple(features),
        signal_score=semantic_score,
        ai_signal_score=ai_score,
    )
