"""
⑩ Biomarker Interpretation Rules Layer

Dissertation §7.3: rule-table-driven layer that consumes BiomarkerScoreRecord
and emits InterpretationRecord strings.

Rules are stored in data/definitions/interpretation_rules/<exercise_id>.yaml.
No clinical assertions are made; labels describe observed movement patterns
and suggest possible biomechanical causes.

Condition types supported in rule `when` blocks:
    floor_applied.<domain>          : bool   — whether the dynamic floor was applied
    dominant_deduction_domain       : str    — domain with highest total deduction
    domain_score.<domain>           : { lt | gt | lte | gte: float }
    final_score                     : { lt | gt | lte | gte: float }
    load_shift_slope.<joint>        : { lt | gt | lte | gte: float }
      (any side of that joint satisfying the threshold counts as True)

Rule firing: ALL conditions in `when` must be True. Unmatched rules are silently
skipped. No exception may propagate out of derive_interpretations().
"""

from __future__ import annotations

import re
import warnings
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

# Project root derived from this file's location
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_DEFAULT_RULES_DIR = _PROJECT_ROOT / "data" / "definitions" / "interpretation_rules"

_LOAD_SHIFT_RE = re.compile(
    r"^biomech\.load_shift\.(?P<joint>\w+)\.(?P<side>\w+)\.slope$"
)


# ── Output dataclass ──────────────────────────────────────────────────────────


@dataclass
class InterpretationRecord:
    """Interpretation of one BiomarkerScoreRecord firing one rule.

    Parameters
    ----------
    score_id      : matches the BiomarkerScoreRecord.score_id that triggered this
    exercise_id   : exercise identifier
    rep_id        : rep number (None = sequence-level, matching the source score)
    rule_id       : identifier of the fired rule (from YAML `id` field)
    label         : human-readable biomechanical interpretation string
    triggered_by  : condition keys in `when` that caused the rule to fire
    source_fields : YAML rule provenance + score source_fields
    """

    score_id: str
    exercise_id: str
    rep_id: int | None
    rule_id: str
    label: str
    triggered_by: list[str] = field(default_factory=list)
    source_fields: list[str] = field(default_factory=list)


# ── Rule loader ───────────────────────────────────────────────────────────────


def load_rules(exercise_id: str, rules_dir: Path | str | None = None) -> list[dict]:
    """Load interpretation rules for one exercise from YAML.

    Returns an empty list when the file is absent or malformed, so callers
    can always iterate without checking for None.
    """
    rules_dir = Path(rules_dir) if rules_dir else _DEFAULT_RULES_DIR
    path = rules_dir / f"{exercise_id}.yaml"
    if not path.exists():
        return []
    try:
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return data.get("rules", []) if isinstance(data, dict) else []
    except Exception as exc:
        warnings.warn(
            f"[interpretation] Failed to load rules from '{path}': {exc}",
            UserWarning,
            stacklevel=2,
        )
        return []


# ── Condition helpers ─────────────────────────────────────────────────────────


def _threshold_check(value: float, spec: Any) -> bool:
    """Check a numeric value against a threshold spec.

    Spec can be a plain number (equality) or a dict of operators:
        { lt: 80.0, gt: 50.0 }  → value < 80 AND value > 50
    """
    if isinstance(spec, dict):
        for op, threshold in spec.items():
            threshold = float(threshold)
            if op == "lt" and not (value < threshold):
                return False
            if op == "gt" and not (value > threshold):
                return False
            if op == "lte" and not (value <= threshold):
                return False
            if op == "gte" and not (value >= threshold):
                return False
        return True
    return float(value) == float(spec)


def _dominant_domain(deductions: list[dict]) -> str:
    """Return the domain with the highest cumulative deduction sum."""
    sums: dict[str, float] = {}
    for d in deductions:
        domain = d.get("domain", "other")
        sums[domain] = sums.get(domain, 0.0) + float(d.get("deduction", 0.0))
    return max(sums, key=lambda k: sums[k]) if sums else "none"


def _build_load_shift_map(biomech_records: list) -> dict[str, float]:
    """Extract { '<joint>.<side>': slope } from load-shift BiomechRecords."""
    result: dict[str, float] = {}
    for rec in biomech_records:
        m = _LOAD_SHIFT_RE.match(getattr(rec, "metric_id", ""))
        if m:
            key = f"{m.group('joint')}.{m.group('side')}"
            result[key] = float(rec.value)
    return result


def _evaluate_condition(
    key: str,
    spec: Any,
    score: Any,
    dominant: str,
    load_shift: dict[str, float],
) -> bool:
    """Evaluate one `when` condition. Returns True if the condition is met."""

    # floor_applied.<domain>
    if key.startswith("floor_applied."):
        domain = key[len("floor_applied.") :]
        actual = score.floor_applied.get(domain, False)
        return actual == bool(spec)

    # dominant_deduction_domain
    if key == "dominant_deduction_domain":
        return dominant == str(spec)

    # load_shift_slope.<joint> or <joint>.<side>
    if key.startswith("load_shift_slope."):
        suffix = key[len("load_shift_slope.") :]
        matching = {k: v for k, v in load_shift.items() if k.startswith(suffix)}
        if not matching:
            return False
        return any(_threshold_check(v, spec) for v in matching.values())

    # domain_score.<domain>
    if key.startswith("domain_score."):
        domain = key[len("domain_score.") :]
        actual = score.domain_scores.get(domain)
        if actual is None:
            return False
        return _threshold_check(actual, spec)

    # final_score
    if key == "final_score":
        return _threshold_check(score.final_score, spec)

    # Unknown condition key — warn and treat as unmet
    warnings.warn(
        f"[interpretation] Unknown condition key '{key}' — treated as False.",
        UserWarning,
        stacklevel=4,
    )
    return False


# ── Public entry point ────────────────────────────────────────────────────────


def derive_interpretations(
    score: Any,
    biomech_records: list | None = None,
    rules_dir: Path | str | None = None,
) -> list[InterpretationRecord]:
    """Apply YAML interpretation rules to a BiomarkerScoreRecord.

    Rules are loaded from data/definitions/interpretation_rules/<exercise_id>.yaml.
    Each rule whose `when` conditions all evaluate to True produces one
    InterpretationRecord. Unmatched rules produce no output and no exception.

    Parameters
    ----------
    score : BiomarkerScoreRecord
        The per-rep (or sequence-level) composite quality score.
    biomech_records : list[BiomechRecord] | None
        Optional — needed to evaluate load_shift_slope conditions.
        Set-level records (rep_id=None) are used regardless of score.rep_id.
    rules_dir : Path | str | None
        Override the default data/definitions/interpretation_rules/ directory (e.g. for tests).

    Returns
    -------
    list[InterpretationRecord]
        One record per fired rule. Empty list when no rules fire or rules file
        is absent. Never raises an exception.
    """
    try:
        return _derive_interpretations_inner(score, biomech_records, rules_dir)
    except Exception as exc:
        warnings.warn(
            f"[interpretation] Unexpected error in derive_interpretations: {exc}",
            UserWarning,
            stacklevel=2,
        )
        return []


def _derive_interpretations_inner(
    score: Any,
    biomech_records: list | None,
    rules_dir: Path | str | None,
) -> list[InterpretationRecord]:
    rules = load_rules(score.exercise_id, rules_dir)
    if not rules:
        return []

    dominant = _dominant_domain(score.deductions)
    load_shift = _build_load_shift_map(biomech_records or [])

    results: list[InterpretationRecord] = []

    for rule in rules:
        rule_id = rule.get("id", "")
        label = rule.get("label", "")
        when = rule.get("when") or {}

        if not rule_id or not label or not when:
            continue

        fired = True
        fired_keys: list[str] = []

        for cond_key, cond_spec in when.items():
            try:
                met = _evaluate_condition(
                    cond_key, cond_spec, score, dominant, load_shift
                )
            except Exception:
                met = False
            if not met:
                fired = False
                break
            fired_keys.append(cond_key)

        if not fired:
            continue

        yaml_provenance = (
            f"interpretation_rules/{score.exercise_id}.yaml#rules[{rule_id}]"
        )
        sf = [yaml_provenance] + list(getattr(score, "source_fields", []))

        results.append(
            InterpretationRecord(
                score_id=score.score_id,
                exercise_id=score.exercise_id,
                rep_id=score.rep_id,
                rule_id=rule_id,
                label=label,
                triggered_by=fired_keys,
                source_fields=sf,
            )
        )

    return results


__all__ = ["InterpretationRecord", "derive_interpretations", "load_rules"]
