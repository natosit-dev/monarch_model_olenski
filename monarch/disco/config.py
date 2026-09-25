from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


RULES_DIR = Path(__file__).resolve().parent / "rules"
DEFAULT_RULES_PATH = RULES_DIR / "defaults.json"
AI_STYLE_RULES_PATH = RULES_DIR / "ai_style_structures.json"


@dataclass(frozen=True)
class FeatureRule:
    """Configuration for one deterministic DiScO text feature."""

    id: str
    label: str
    kind: str
    semantic_max: float = 0.0
    ai_max: float = 0.0
    half_saturation: float = 1.0
    terms: tuple[str, ...] = ()
    pattern: str | None = None


def _rule_from_dict(raw: dict) -> FeatureRule:
    return FeatureRule(
        id=str(raw["id"]),
        label=str(raw["label"]),
        kind=str(raw["kind"]),
        semantic_max=float(raw.get("semantic_max", 0.0)),
        ai_max=float(raw.get("ai_max", 0.0)),
        half_saturation=float(raw.get("half_saturation", 1.0)),
        terms=tuple(str(term) for term in raw.get("terms", ())),
        pattern=raw.get("pattern"),
    )


def _load_rule_file(path: Path) -> tuple[FeatureRule, ...]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    return tuple(_rule_from_dict(item) for item in raw)


DEFAULT_RULES = _load_rule_file(DEFAULT_RULES_PATH) + _load_rule_file(AI_STYLE_RULES_PATH)


def load_rules() -> tuple[FeatureRule, ...]:
    """Return the checked-in DiScO rules.

    Monarch intentionally imports the text evaluator only. Mutable local
    calibration/override state belongs to Disco Fever and is not loaded here.
    """

    return DEFAULT_RULES
