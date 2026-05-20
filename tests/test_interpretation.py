"""
tests/test_interpretation.py

Unit tests for biomarker.interpretation:
    - Rule loader (load_rules)
    - derive_interpretations() — three core scenarios + edge cases
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from movement.biomarker.interpretation import (
    derive_interpretations,
    load_rules,
)

# ── Path helpers ──────────────────────────────────────────────────────────────

_RULES_DIR = (
    Path(__file__).resolve().parent.parent
    / "data"
    / "definitions"
    / "interpretation_rules"
)


# ── Minimal BiomarkerScoreRecord stub ─────────────────────────────────────────

@dataclass
class _Score:
    """Minimal stub matching the fields consumed by derive_interpretations."""
    score_id: str = "rep_quality_score"
    exercise_id: str = "squat"
    rep_id: int | None = 1
    domain_scores: dict = field(default_factory=lambda: {
        "spatial": 90.0, "temporal": 85.0, "control": 80.0, "biomech": 90.0
    })
    floor_applied: dict = field(default_factory=lambda: {
        "spatial": False, "temporal": False, "control": False, "biomech": False
    })
    deductions: list = field(default_factory=list)
    final_score: float = 86.25
    source_fields: list = field(default_factory=lambda: ["feature_domains"])


def _score(**kwargs) -> _Score:
    """Build a _Score with specific overrides."""
    s = _Score()
    for k, v in kwargs.items():
        object.__setattr__(s, k, v)
    return s


# ── Minimal BiomechRecord stub ────────────────────────────────────────────────

@dataclass
class _BiomechRec:
    metric_id: str
    exercise_id: str
    rep_id: int | None
    value: float
    unit: str = "torso_length_ratio_per_rep"
    source_fields: list = field(default_factory=list)


# ── 1. Rule loader ─────────────────────────────────────────────────────────────

class TestLoadRules:
    def test_squat_rules_loaded(self):
        rules = load_rules("squat", _RULES_DIR)
        assert len(rules) >= 3

    def test_lunge_rules_loaded(self):
        rules = load_rules("lunge", _RULES_DIR)
        assert len(rules) >= 3

    def test_pike_pushup_rules_loaded(self):
        rules = load_rules("pike_pushup", _RULES_DIR)
        assert len(rules) >= 3

    def test_plank_shoulder_tap_rules_loaded(self):
        rules = load_rules("plank_shoulder_tap", _RULES_DIR)
        assert len(rules) >= 3

    def test_each_rule_has_required_keys(self):
        for ex in ("squat", "lunge", "pike_pushup", "plank_shoulder_tap"):
            for rule in load_rules(ex, _RULES_DIR):
                assert "id"    in rule, f"{ex}: rule missing 'id'"
                assert "when"  in rule, f"{ex}: rule '{rule.get('id')}' missing 'when'"
                assert "label" in rule, f"{ex}: rule '{rule.get('id')}' missing 'label'"

    def test_missing_exercise_returns_empty(self):
        rules = load_rules("nonexistent_exercise", _RULES_DIR)
        assert rules == []


# ── 2. Scenario: spatial floor applied ────────────────────────────────────────

class TestScenarioFloorHitSpatial:
    """Scenario 1 — floor_applied.spatial = True → floor_hit_spatial fires."""

    def test_floor_hit_spatial_fires(self):
        score = _score(floor_applied={
            "spatial": True, "temporal": False,
            "control": False, "biomech": False,
        })
        results = derive_interpretations(score, rules_dir=_RULES_DIR)
        rule_ids = [r.rule_id for r in results]
        assert "floor_hit_spatial" in rule_ids

    def test_floor_hit_spatial_does_not_fire_when_false(self):
        score = _score()  # all floors False
        results = derive_interpretations(score, rules_dir=_RULES_DIR)
        rule_ids = [r.rule_id for r in results]
        assert "floor_hit_spatial" not in rule_ids

    def test_interpretation_record_fields(self):
        score = _score(floor_applied={
            "spatial": True, "temporal": False,
            "control": False, "biomech": False,
        })
        results = derive_interpretations(score, rules_dir=_RULES_DIR)
        rec = next(r for r in results if r.rule_id == "floor_hit_spatial")
        assert rec.score_id == score.score_id
        assert rec.exercise_id == score.exercise_id
        assert rec.rep_id == score.rep_id
        assert rec.label and len(rec.label) > 0
        assert "floor_applied.spatial" in rec.triggered_by
        assert any("squat.yaml" in sf for sf in rec.source_fields)


# ── 3. Scenario: dominant control, no floor ───────────────────────────────────

class TestScenarioDominantControl:
    """Scenario 2 — control dominates deductions + spatial floor not applied."""

    def _score_with_control_deductions(self) -> _Score:
        deductions = [
            {"feature_id": "control.compensation.knee_valgus.left",
             "domain": "control", "value": 0.05, "deduction": 5.0},
            {"feature_id": "control.stability.hip_center_x_std",
             "domain": "control", "value": 0.03, "deduction": 3.0},
            {"feature_id": "spatial.rom.left_knee_angle",
             "domain": "spatial", "value": 60.0, "deduction": 1.0},
        ]
        return _score(
            deductions=deductions,
            floor_applied={
                "spatial": False, "temporal": False,
                "control": False, "biomech": False,
            },
            domain_scores={
                "spatial": 92.0, "temporal": 88.0,
                "control": 78.0, "biomech": 90.0,
            },
        )

    def test_dominant_control_floor_free_fires(self):
        score = self._score_with_control_deductions()
        results = derive_interpretations(score, rules_dir=_RULES_DIR)
        rule_ids = [r.rule_id for r in results]
        assert "dominant_control_floor_free" in rule_ids

    def test_dominant_control_does_not_fire_when_spatial_floor_hit(self):
        score = self._score_with_control_deductions()
        score.floor_applied["spatial"] = True
        results = derive_interpretations(score, rules_dir=_RULES_DIR)
        rule_ids = [r.rule_id for r in results]
        assert "dominant_control_floor_free" not in rule_ids

    def test_triggered_by_lists_all_conditions(self):
        score = self._score_with_control_deductions()
        results = derive_interpretations(score, rules_dir=_RULES_DIR)
        rec = next(r for r in results if r.rule_id == "dominant_control_floor_free")
        assert "dominant_deduction_domain" in rec.triggered_by
        assert "floor_applied.spatial" in rec.triggered_by


# ── 4. Scenario: load shift (knee-to-hip) ─────────────────────────────────────

class TestScenarioLoadShift:
    """Scenario 3 — knee slope < -0.01 AND hip slope > 0.01."""

    def _biomech_load_shift(self) -> list:
        return [
            _BiomechRec(
                metric_id="biomech.load_shift.knee.left.slope",
                exercise_id="squat", rep_id=None, value=-0.025,
            ),
            _BiomechRec(
                metric_id="biomech.load_shift.hip.left.slope",
                exercise_id="squat", rep_id=None, value=0.018,
            ),
        ]

    def test_knee_to_hip_load_shift_fires(self):
        score = _score()
        results = derive_interpretations(
            score, biomech_records=self._biomech_load_shift(), rules_dir=_RULES_DIR
        )
        rule_ids = [r.rule_id for r in results]
        assert "knee_to_hip_load_shift" in rule_ids

    def test_load_shift_does_not_fire_without_biomech_records(self):
        score = _score()
        results = derive_interpretations(score, biomech_records=None, rules_dir=_RULES_DIR)
        rule_ids = [r.rule_id for r in results]
        assert "knee_to_hip_load_shift" not in rule_ids

    def test_load_shift_does_not_fire_when_knee_slope_positive(self):
        recs = [
            _BiomechRec(
                metric_id="biomech.load_shift.knee.left.slope",
                exercise_id="squat", rep_id=None, value=+0.015,  # positive → no fire
            ),
            _BiomechRec(
                metric_id="biomech.load_shift.hip.left.slope",
                exercise_id="squat", rep_id=None, value=0.018,
            ),
        ]
        score = _score()
        results = derive_interpretations(score, biomech_records=recs, rules_dir=_RULES_DIR)
        rule_ids = [r.rule_id for r in results]
        assert "knee_to_hip_load_shift" not in rule_ids


# ── 5. Edge cases ─────────────────────────────────────────────────────────────

class TestEdgeCases:
    def test_no_conditions_match_returns_empty(self):
        # Perfect score, no floors, no load shift → most rules should not fire
        score = _score(
            domain_scores={"spatial": 99.0, "temporal": 99.0,
                           "control": 99.0, "biomech": 99.0},
            floor_applied={"spatial": False, "temporal": False,
                           "control": False, "biomech": False},
            deductions=[{"feature_id": "spatial.rom.left_knee_angle",
                         "domain": "spatial", "value": 88.0, "deduction": 0.1}],
            final_score=99.0,
        )
        results = derive_interpretations(score, rules_dir=_RULES_DIR)
        # None of the threshold rules should fire on a perfect score
        rule_ids = {r.rule_id for r in results}
        assert "floor_hit_spatial"          not in rule_ids
        assert "floor_hit_control"          not in rule_ids
        assert "high_control_deduction"     not in rule_ids
        assert "low_overall_score"          not in rule_ids

    def test_unknown_exercise_returns_empty(self):
        score = _score(exercise_id="unknown_exercise")
        results = derive_interpretations(score, rules_dir=_RULES_DIR)
        assert results == []

    def test_returns_list_never_raises(self):
        # Even with a completely broken score stub, should return [] not raise
        class _BrokenScore:
            exercise_id = "squat"
            score_id = "rep_quality_score"
            rep_id = None
            domain_scores = {}
            floor_applied = {}
            deductions = []
            final_score = 0.0
            source_fields = []
        results = derive_interpretations(_BrokenScore(), rules_dir=_RULES_DIR)
        assert isinstance(results, list)

    def test_source_fields_contain_yaml_provenance(self):
        score = _score(floor_applied={
            "spatial": True, "temporal": False,
            "control": False, "biomech": False,
        })
        results = derive_interpretations(score, rules_dir=_RULES_DIR)
        rec = next(r for r in results if r.rule_id == "floor_hit_spatial")
        assert any("interpretation_rules" in sf for sf in rec.source_fields)
        assert any("floor_hit_spatial" in sf for sf in rec.source_fields)

    def test_all_four_exercises_produce_at_least_one_rule_on_low_score(self):
        for ex in ("squat", "lunge", "pike_pushup", "plank_shoulder_tap"):
            score = _score(
                exercise_id=ex,
                domain_scores={"spatial": 70.0, "temporal": 70.0,
                               "control": 70.0, "biomech": 70.0},
                floor_applied={"spatial": True, "temporal": False,
                               "control": False, "biomech": False},
                final_score=70.0,
            )
            results = derive_interpretations(score, rules_dir=_RULES_DIR)
            assert len(results) >= 1, f"{ex}: expected ≥ 1 rule to fire on low score"
