"""
⑩ Biomarker Scoring — Movement Quality Composite Score

Z-score deduction model anchored to a synthetic-normal baseline stored in
data/reference/baseline_zscore.json. Scores are relative to the baseline
and do not represent clinical thresholds.

Domain weights:
    spatial  40 %  — form completeness (ROM, symmetry, shape)
    temporal 30 %  — pacing and consistency
    control  20 %  — stability and compensation (intentionally low weight
                       to avoid penalising compensation too harshly and
                       preserve user adherence)
    biomech  10 %  — relative load-distribution tendency

Dynamic floor (per domain):
    floor_dynamic = 50 × clamp(mandatory_ROM_ratio, 0.0, 1.0)
    No domain score may fall below this floor due to compensation deductions.
    Example: achieving 80 % of expected ROM → floor = 40 pts.

Score formula (per domain d):
    Score_d = max(floor_dynamic, 100 − Σ_i w_i · |Z_i|)

    where w_i = 1 / n_features_in_domain (equal within-domain weight),
    Z_i = (value_i − μ_i) / σ_i against the synthetic-normal baseline.

Composite:
    Score_final = Σ_d W_d · Score_d,
    W = { spatial: 0.4, temporal: 0.3, control: 0.2, biomech: 0.1 }
"""
from __future__ import annotations

import json
import warnings
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

import numpy as np

if TYPE_CHECKING:
    from movement.biomech import BiomechRecord
    from movement.exercise_definition import ExerciseDefinition
    from movement.features import FeatureRecord


# Project root: src/movement/biomarker/scoring.py → 4 levels up
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent

DOMAIN_WEIGHTS: dict[str, float] = {
    "spatial":  0.40,
    "temporal": 0.30,
    "control":  0.20,
    "biomech":  0.10,
}

# Minimum σ applied at Z-score computation time (not stored in baseline):
#   σ_eff = max(σ_baseline, STD_FLOOR_RATIO × |μ|, STD_ABS_FLOOR)
# STD_ABS_FLOOR = 0.01 gives a meaningful floor for near-zero features
# (e.g. lateral_pelvic_shift ≈ 0 in symmetric synthetic data → σ_eff = 0.01 TLR,
# so a 1 % torso-length deviation yields Z ≈ 1 rather than Z → ∞).
_STD_FLOOR_RATIO: float = 0.10
_STD_ABS_FLOOR: float = 0.01


# ── Output dataclass ──────────────────────────────────────────────────────────

@dataclass
class BiomarkerScoreRecord:
    """Composite movement quality score for one rep (or full sequence).

    Parameters
    ----------
    score_id           : always 'rep_quality_score'
    exercise_id        : exercise identifier
    definition_version : exercise YAML version this record references (provenance)
    rep_id             : rep number (None = sequence-level)
    domain_scores      : { 'spatial': 87.3, 'temporal': 92.1, ... }
    floor_applied      : { 'spatial': False, 'control': True, ... }
    deductions         : per-feature audit list
                         [{'feature_id', 'domain', 'value', 'baseline_mean',
                           'baseline_std', 'z', 'w', 'deduction'}, ...]
    final_score        : weighted composite, 0–100
    source_fields      : exercise definition fields that drove the score
    """
    score_id: str
    exercise_id: str
    definition_version: str
    rep_id: int | None
    domain_scores: dict[str, float]
    floor_applied: dict[str, bool]
    deductions: list[dict[str, Any]]
    final_score: float
    source_fields: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "score_id":           self.score_id,
            "exercise_id":        self.exercise_id,
            "definition_version": self.definition_version,
            "rep_id":             self.rep_id,
            "domain_scores":      self.domain_scores,
            "floor_applied":      self.floor_applied,
            "final_score":        self.final_score,
            "deductions":         self.deductions,
            "source_fields":      self.source_fields,
        }


# ── Internal helpers ──────────────────────────────────────────────────────────

def _record_id(r: Any) -> str:
    return getattr(r, "feature_id", None) or getattr(r, "metric_id", "") or ""


def _classify_domain(record_id: str) -> str:
    for prefix, domain in (
        ("spatial.",  "spatial"),
        ("temporal.", "temporal"),
        ("control.",  "control"),
        ("biomech.",  "biomech"),
    ):
        if record_id.startswith(prefix):
            return domain
    return "other"


# ── Baseline I/O ──────────────────────────────────────────────────────────────

def load_baseline(
    path: Path | str,
    exercise_id: str,
) -> dict[str, dict[str, float]]:
    """Load per-metric (mean, std) entries for one exercise from the baseline JSON.

    Returns an empty dict if the file is absent, malformed, or the exercise
    key is not present — so callers can always check `if not baseline`.
    """
    path = Path(path)
    if not path.exists():
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}
    return data.get(exercise_id, {})


def save_baseline(
    baseline_all: dict[str, dict[str, dict[str, float]]],
    path: Path | str,
) -> None:
    """Write the full baseline dict (all exercises) to JSON.

    baseline_all structure:
        { exercise_id: { feature_id: { "mean": float, "std": float } } }
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(baseline_all, f, indent=2, ensure_ascii=False)


def build_baseline_from_records(
    feat_records: list["FeatureRecord"],
    biomech_records: list["BiomechRecord"],
) -> dict[str, dict[str, float]]:
    """Compute per-metric (mean, std) statistics from a set of normal-condition records.

    Intended to generate data/reference/baseline_zscore.json from the
    synthetic normal pipeline run. The returned dict is keyed by feature_id /
    metric_id and can be inserted under an exercise_id key before saving.

    σ is floored at max(σ_raw, _STD_FLOOR_RATIO × |μ|, _STD_ABS_FLOOR) to
    prevent near-zero division in the Z-score formula.
    """
    from collections import defaultdict

    values: dict[str, list[float]] = defaultdict(list)

    for r in feat_records:
        rid = _record_id(r)
        if rid and r.value is not None and not np.isnan(float(r.value)):
            values[rid].append(float(r.value))
    for r in biomech_records:
        rid = _record_id(r)
        if rid and r.value is not None and not np.isnan(float(r.value)):
            values[rid].append(float(r.value))

    baseline: dict[str, dict[str, float]] = {}
    for rid, vals in values.items():
        mu = float(np.mean(vals))
        sigma = float(np.std(vals, ddof=0 if len(vals) == 1 else 1))
        sigma = max(sigma, abs(mu) * _STD_FLOOR_RATIO, _STD_ABS_FLOOR)
        baseline[rid] = {"mean": round(mu, 6), "std": round(sigma, 6)}

    return baseline


# ── Scoring engine ────────────────────────────────────────────────────────────

def _mandatory_rom_ratio(
    feat_records: list["FeatureRecord"],
    exercise_definition: "ExerciseDefinition",
    baseline: dict[str, dict[str, float]],
) -> float:
    """Compute the fraction of expected primary-joint ROM achieved.

    Uses ROM features whose feature_id contains the name of any landmark in
    exercise_definition.landmarks.primary_joints. Returns 1.0 when no ROM
    baseline data is available (no floor penalty applied).
    """
    primary_joints = set(exercise_definition.landmarks.primary_joints or [])
    ratios: list[float] = []

    for r in feat_records:
        rid = _record_id(r)
        if not rid.startswith("spatial.rom."):
            continue
        if not any(j in rid for j in primary_joints):
            continue
        if rid not in baseline:
            continue
        expected = baseline[rid]["mean"]
        if expected < 1e-6:
            continue
        ratios.append(min(float(r.value) / expected, 1.0))

    return float(np.mean(ratios)) if ratios else 1.0


def _derive_domain_score(
    records: list[Any],
    baseline: dict[str, dict[str, float]],
    floor_dynamic: float,
) -> tuple[float, bool, list[dict[str, Any]]]:
    """Compute one domain score via the Z-score deduction formula.

    Score = max(floor_dynamic, 100 − Σ_i w_i · |Z_i|)
    Equal within-domain weights: w_i = 1 / n.

    Returns
    -------
    (score, floor_was_applied, deduction_details)
    """
    valid = [r for r in records if _record_id(r) in baseline]
    if not valid:
        return 100.0, False, []

    n = len(valid)
    w_i = 1.0 / n
    deductions: list[dict[str, Any]] = []
    total_deduction = 0.0

    for r in valid:
        rid = _record_id(r)
        mu = baseline[rid]["mean"]
        sigma = max(
            baseline[rid]["std"],
            abs(mu) * _STD_FLOOR_RATIO,
            _STD_ABS_FLOOR,
        )
        z = (float(r.value) - mu) / sigma
        d = w_i * abs(z)
        total_deduction += d
        deductions.append({
            "feature_id":     rid,
            "value":          round(float(r.value), 4),
            "baseline_mean":  round(mu, 4),
            "baseline_std":   round(sigma, 4),
            "z":              round(z, 3),
            "w":              round(w_i, 4),
            "deduction":      round(d, 4),
        })

    raw_score = max(0.0, 100.0 - total_deduction)
    final_score = max(floor_dynamic, raw_score)
    floor_applied = raw_score < floor_dynamic

    return round(final_score, 2), floor_applied, deductions


def _score_one_rep(
    feat_rep: list["FeatureRecord"],
    biomech_rep: list["BiomechRecord"],
    exercise_definition: "ExerciseDefinition",
    definition_version: str,
    rep_id: int | None,
    baseline: dict[str, dict[str, float]],
) -> BiomarkerScoreRecord:
    """Compute BiomarkerScoreRecord for one rep (or the full sequence)."""
    domain_records: dict[str, list] = {d: [] for d in DOMAIN_WEIGHTS}

    for r in feat_rep:
        d = _classify_domain(_record_id(r))
        if d in domain_records:
            domain_records[d].append(r)
    for r in biomech_rep:
        d = _classify_domain(_record_id(r))
        if d in domain_records:
            domain_records[d].append(r)

    rom_ratio = _mandatory_rom_ratio(feat_rep, exercise_definition, baseline)
    floor_dynamic = 50.0 * max(0.0, min(1.0, rom_ratio))

    domain_scores: dict[str, float] = {}
    floor_applied: dict[str, bool] = {}
    all_deductions: list[dict[str, Any]] = []

    for domain in DOMAIN_WEIGHTS:
        score_d, floor_d, ded_d = _derive_domain_score(
            domain_records[domain], baseline, floor_dynamic,
        )
        domain_scores[domain] = score_d
        floor_applied[domain] = floor_d
        for item in ded_d:
            item["domain"] = domain
        all_deductions.extend(ded_d)

    final_score = sum(DOMAIN_WEIGHTS[d] * domain_scores[d] for d in DOMAIN_WEIGHTS)

    return BiomarkerScoreRecord(
        score_id="rep_quality_score",
        exercise_id=exercise_definition.exercise_id,
        definition_version=definition_version,
        rep_id=rep_id,
        domain_scores=domain_scores,
        floor_applied=floor_applied,
        deductions=all_deductions,
        final_score=round(final_score, 2),
        source_fields=["feature_domains", "biomechanical_focus", "quality_rules"],
    )


# ── Public entry point ────────────────────────────────────────────────────────

def derive_biomarkers(
    feat_records: list["FeatureRecord"],
    biomech_records: list["BiomechRecord"],
    exercise_definition: "ExerciseDefinition",
    definition_version: str,
    *,
    baseline_path: Path | str | None = None,
) -> tuple[list[Any], list[BiomarkerScoreRecord]]:
    """Main entry point for ⑩ Biomarker Derivation.

    Converts FeatureRecord and BiomechRecord into:
    1. BiomarkerRecord list — individual metrics with provenance (pass-through).
    2. BiomarkerScoreRecord list — per-rep composite movement quality scores.

    Scoring (step 2) requires the synthetic-normal baseline file. If the file
    is absent, step 2 is skipped with a UserWarning. Generate the baseline with
    scripts/compute_baseline.py.

    Parameters
    ----------
    feat_records       : output of features.extract_rep_features()
    biomech_records    : output of biomech.extract_rep_biomech()
    exercise_definition: loaded ExerciseDefinition
    definition_version : exercise YAML version (exercise_def.version)
    baseline_path      : path to baseline JSON.
                         None → data/reference/baseline_zscore.json

    Returns
    -------
    (biomarker_records, score_records)
    """
    from movement.biomarker import from_biomech_record, from_feature_record

    # ── 1. Pass-through BiomarkerRecord ──────────────────────────────────────
    biomarker_records: list[Any] = []
    for r in feat_records:
        try:
            biomarker_records.append(from_feature_record(r, definition_version))
        except ValueError:
            pass
    for r in biomech_records:
        try:
            biomarker_records.append(from_biomech_record(r, definition_version))
        except ValueError:
            pass

    # ── 2. Composite score computation ───────────────────────────────────────
    if baseline_path is None:
        baseline_path = _PROJECT_ROOT / "data" / "reference" / "baseline_zscore.json"

    baseline = load_baseline(baseline_path, exercise_definition.exercise_id)

    if not baseline:
        warnings.warn(
            f"[biomarker] Baseline not found at '{baseline_path}'. "
            "BiomarkerScoreRecord computation skipped. "
            "Run scripts/compute_baseline.py to generate the baseline file.",
            UserWarning,
            stacklevel=2,
        )
        return biomarker_records, []

    rep_ids: set[int] = set()
    for r in feat_records:
        if r.rep_id is not None:
            rep_ids.add(int(r.rep_id))
    for r in biomech_records:
        if r.rep_id is not None:
            rep_ids.add(int(r.rep_id))

    score_records: list[BiomarkerScoreRecord] = []

    if rep_ids:
        for rep_id in sorted(rep_ids):
            feat_rep    = [r for r in feat_records    if r.rep_id == rep_id]
            biomech_rep = [r for r in biomech_records if r.rep_id == rep_id]
            score_records.append(_score_one_rep(
                feat_rep, biomech_rep, exercise_definition,
                definition_version, rep_id, baseline,
            ))
    else:
        score_records.append(_score_one_rep(
            feat_records, biomech_records, exercise_definition,
            definition_version, None, baseline,
        ))

    return biomarker_records, score_records


__all__ = [
    "BiomarkerScoreRecord",
    "DOMAIN_WEIGHTS",
    "build_baseline_from_records",
    "save_baseline",
    "load_baseline",
    "derive_biomarkers",
]
