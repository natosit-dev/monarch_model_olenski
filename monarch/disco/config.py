from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path


DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "disco"
RUNTIME_RULES_PATH = DATA_DIR / "rules.json"
RULES_DIR = Path(__file__).resolve().parent / "rules"
DEFAULT_RULES_PATH = RULES_DIR / "defaults.json"
AI_STYLE_RULES_PATH = RULES_DIR / "ai_style_structures.json"


@dataclass(frozen=True)
class FeatureRule:
    """Configuration for one deterministic text feature."""

    id: str
    label: str
    kind: str
    semantic_max: float = 0.0
    ai_max: float = 0.0
    half_saturation: float = 1.0
    terms: tuple[str, ...] = ()
    pattern: str | None = None


def _rule_from_dict(
    raw: dict,
    scoring_defaults: dict[str, FeatureRule] | None = None,
) -> FeatureRule:
    """Build a rule from JSON, with safe migration for legacy local overrides.

    Older runtime rule files used ``weight`` and ``ai_weight`` as density
    multipliers. When a legacy local override matches a checked-in rule ID,
    preserve its detector dictionary/pattern while adopting the new bounded
    scoring priors from the checked-in defaults.
    """

    rule_id = str(raw["id"])
    default = (scoring_defaults or {}).get(rule_id)

    if "semantic_max" in raw:
        semantic_max = float(raw["semantic_max"])
    elif default is not None:
        semantic_max = default.semantic_max
    else:
        semantic_max = float(raw.get("weight", 0.0))

    if "ai_max" in raw:
        ai_max = float(raw["ai_max"])
    elif default is not None:
        ai_max = default.ai_max
    else:
        ai_max = float(raw.get("ai_weight", 0.0))

    if "half_saturation" in raw:
        half_saturation = float(raw["half_saturation"])
    elif default is not None:
        half_saturation = default.half_saturation
    else:
        half_saturation = 1.0

    return FeatureRule(
        id=rule_id,
        label=str(raw["label"]),
        kind=str(raw["kind"]),
        semantic_max=semantic_max,
        ai_max=ai_max,
        half_saturation=half_saturation,
        terms=tuple(str(term) for term in raw.get("terms", ())),
        pattern=raw.get("pattern"),
    )


def _load_rule_file(
    path: Path,
    scoring_defaults: dict[str, FeatureRule] | None = None,
) -> tuple[FeatureRule, ...]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    return tuple(_rule_from_dict(item, scoring_defaults=scoring_defaults) for item in raw)


DEFAULT_RULES = _load_rule_file(DEFAULT_RULES_PATH) + _load_rule_file(AI_STYLE_RULES_PATH)


def load_rules(path: Path = RUNTIME_RULES_PATH) -> tuple[FeatureRule, ...]:
    """Load mutable local rules, falling back to checked-in JSON defaults.

    Local detector edits are overlaid on the current checked-in rule set:
    - legacy scoring fields inherit the new bounded priors for known rule IDs
    - newly added checked-in rules appear even if an older local override exists
    - extra local custom rules are retained after the checked-in defaults
    """

    if not path.exists():
        return DEFAULT_RULES

    defaults_by_id = {rule.id: rule for rule in DEFAULT_RULES}
    local_rules = _load_rule_file(path, scoring_defaults=defaults_by_id)
    local_by_id = {rule.id: rule for rule in local_rules}

    merged = [local_by_id.get(default.id, default) for default in DEFAULT_RULES]
    merged.extend(rule for rule in local_rules if rule.id not in defaults_by_id)
    return tuple(merged)


def save_rules(
    rules: tuple[FeatureRule, ...],
    path: Path = RUNTIME_RULES_PATH,
) -> Path:
    """Persist the active local rule configuration."""

    path.parent.mkdir(parents=True, exist_ok=True)
    payload = [asdict(rule) for rule in rules]
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def reset_rules(path: Path = RUNTIME_RULES_PATH) -> None:
    """Remove local overrides so checked-in defaults become active again."""

    if path.exists():
        path.unlink()
