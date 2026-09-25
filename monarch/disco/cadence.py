from __future__ import annotations

import math
import re
from dataclasses import dataclass


WORD_RE = re.compile(r"\b\w+(?:[-']\w+)*\b")
_PROTECTED_PERIOD = "\uE000"
_COMMON_ABBREVIATION_RE = re.compile(
    r"\b(?:Mr|Mrs|Ms|Dr|Prof|Sr|Jr|St|vs|etc|No|Fig|e\.g|i\.e)\.",
    re.IGNORECASE,
)
_INITIALISM_RE = re.compile(r"\b(?:[A-Za-z]\.){2,}")
_SINGLE_INITIAL_RE = re.compile(r"\b[A-Z]\.(?=\s+[A-Z][A-Za-z'-]+)")
_DECIMAL_RE = re.compile(r"(?<=\d)\.(?=\d)")
_SENTENCE_RE = re.compile(r"[^.!?]+(?:[.!?]+(?:[\"”’')\]]+)?)?|[.!?]+", re.MULTILINE)


@dataclass(frozen=True)
class SentenceCadenceObservation:
    """Unscored sentence-length observations for cadence analysis."""

    sentence_count: int
    sentence_lengths: tuple[int, ...]
    mean_words: float
    std_dev_words: float
    coefficient_of_variation: float
    min_words: int
    max_words: int
    range_words: int


def _protect_periods(text: str) -> str:
    """Protect periods that are unlikely to mark sentence boundaries."""

    protected = _DECIMAL_RE.sub(_PROTECTED_PERIOD, text)

    def protect_match(match: re.Match[str]) -> str:
        return match.group(0).replace(".", _PROTECTED_PERIOD)

    protected = _COMMON_ABBREVIATION_RE.sub(protect_match, protected)
    protected = _INITIALISM_RE.sub(protect_match, protected)
    protected = _SINGLE_INITIAL_RE.sub(protect_match, protected)
    return protected


def sentence_word_lengths(text: str) -> tuple[int, ...]:
    """Return deterministic word counts for sentence-like spans.

    This intentionally avoids external NLP dependencies. It protects a small
    set of common abbreviations, initials, initialisms, and decimal points,
    then treats '.', '?', and '!' as sentence terminators. The raw sequence is
    the canonical cadence observation; the derived summaries can be replaced
    later without rescoring semantic or AI signals.
    """

    protected = _protect_periods(text)
    lengths: list[int] = []
    for match in _SENTENCE_RE.finditer(protected):
        span = match.group(0).replace(_PROTECTED_PERIOD, ".").strip()
        count = len(WORD_RE.findall(span))
        if count:
            lengths.append(count)
    return tuple(lengths)


def inspect_sentence_cadence(text: str) -> SentenceCadenceObservation:
    """Calculate unscored cadence uniformity/range observations."""

    lengths = sentence_word_lengths(text)
    count = len(lengths)
    if not count:
        return SentenceCadenceObservation(
            sentence_count=0,
            sentence_lengths=(),
            mean_words=0.0,
            std_dev_words=0.0,
            coefficient_of_variation=0.0,
            min_words=0,
            max_words=0,
            range_words=0,
        )

    mean_words = sum(lengths) / count
    variance = sum((length - mean_words) ** 2 for length in lengths) / count
    std_dev_words = math.sqrt(variance)
    coefficient_of_variation = std_dev_words / mean_words if mean_words else 0.0
    min_words = min(lengths)
    max_words = max(lengths)

    return SentenceCadenceObservation(
        sentence_count=count,
        sentence_lengths=lengths,
        mean_words=mean_words,
        std_dev_words=std_dev_words,
        coefficient_of_variation=coefficient_of_variation,
        min_words=min_words,
        max_words=max_words,
        range_words=max_words - min_words,
    )
