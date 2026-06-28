# 10. Biomarker Scoring

**Document Version:** 1.2.0
**Last Updated:** 2026-05-21
**Korean Sync:** `docs/pipeline/10_biomarker_scoring.md` is the same-version Korean source.

Pipeline step ⑩ wraps ⑧ `FeatureRecord` and ⑨ `BiomechRecord` outputs into
interpretable biomarker records and, when a baseline exists, derives a per-rep
movement-quality score. Observation reliability, feature availability, and
coordinate-correction magnitude remain separate confidence/provenance signals.

Scores are engineering summaries, not clinical thresholds or diagnostic outputs.

---

## 1. Pipeline Position

```text
⑧ Feature Extraction   FeatureRecord list
⑨ Biomech Proxy        BiomechRecord list
→ ⑩ Biomarker Scoring  ← this step
```

Required inputs:

```text
feat_records           FeatureRecord list, including availability metadata
biomech_records        BiomechRecord list
exercise_definition    feature_domains, biomechanical_focus, quality rules
definition_version     exercise YAML version
baseline JSON          data/reference/baseline_zscore.json when scoring is enabled
```

---

## 2. Output Contract

Two record types are emitted.

```text
BiomarkerRecord
    Pass-through individual metric with value, unit, rep_id, source_fields,
    availability, view/depth reliability, and note metadata.

BiomarkerScoreRecord
    Per-rep composite score with domain scores, final score, floor flags,
    deduction audit, withheld-feature audit, score bounds, and domain weights.
```

`BiomarkerRecord.source_fields` is required. Records without provenance should not
be produced.

---

## 3. Scoring Contract

Composite scoring uses Z-score deductions against a synthetic-normal baseline.
Default score bounds are 0-100 and default domain weights are equal relative
weights.

```text
spatial   form completeness and symmetry/shape features
temporal  pacing and timing consistency
control   stability and compensation features
biomech   relative load-distribution proxy features
```

The default configuration lives in `configs/pipeline_default.yaml`.

```yaml
biomarker:
  score_bounds:
    min: 0.0
    max: 100.0
  domain_weights:
    spatial: 1.0
    temporal: 1.0
    control: 1.0
    biomech: 1.0
```

Domain assignment is by record ID prefix.

```text
spatial.*   → spatial
temporal.*  → temporal
control.*   → control
biomech.*   → biomech
other       → pass-through only
```

---

## 4. Feature Eligibility

⑧ may emit numeric features that are not reliable enough for scoring. ⑩ uses
`availability` as the composite-score gate.

```text
assessed
    Eligible for Z-score deduction if baseline statistics exist.

low_confidence
    Excluded from composite score by default. Preserved in BiomarkerRecord and
    recorded in BiomarkerScoreRecord.withheld_features.

not_assessed
    Excluded from composite score. Report as provenance/unavailable.

missing availability
    Backward-compatible: treated as assessed only for legacy records.
```

`view_reliability` is not a separate score multiplier. It should already be
reflected in `availability`, which avoids false precision from camera artifacts.

Large canonicalization correction magnitude also does not directly reduce the
movement-quality score. It belongs in data-confidence/provenance unless a later
validated scoring policy says otherwise.

---

## 5. Z-Score Deduction And Dynamic Floor

For each assessed feature in a domain:

```text
σ_eff  = max(σ_baseline, STD_FLOOR_RATIO * |μ_baseline|, STD_ABS_FLOOR)
Z      = (value - μ_baseline) / σ_eff
w_i    = 1 / number_of_assessed_features_in_domain
deduct = scaled_abs_z_deduction(Z, w_i, score_bounds)
```

The σ floor prevents near-zero baseline variance from producing unstable
deductions.

The dynamic floor is anchored to mandatory ROM achievement:

```text
mandatory_ROM_ratio = mean(min(ROM_i / ROM_baseline_i, 1.0))
floor_dynamic       = score_min + 0.50 * score_span * clamp(mandatory_ROM_ratio)
domain_score        = max(floor_dynamic, raw_domain_score)
```

This keeps a completed movement from collapsing to the minimum score solely
because several compensation or control deductions are present. `floor_applied`
records where the floor affected the domain.

---

## 6. Baseline

```text
File       data/reference/baseline_zscore.json
Generator  scripts/compute_baseline.py
Schema     { exercise_id: { metric_id: {"mean": float, "std": float} } }
```

The baseline is a synthetic engineering reference, not a population norm. Missing
baseline data should skip composite score records with a warning while still
returning pass-through biomarker records.

---

## 7. Audit Fields

`deductions` explains why scored features affected a domain score.

```python
{
    "domain": "spatial",
    "feature_id": "spatial.rom.left_knee",
    "value": 85.4,
    "baseline_mean": 92.1,
    "baseline_std": 3.5,
    "z": -1.91,
    "weight": 0.143,
    "deduction": 0.273,
}
```

`withheld_features` explains why computed metrics did not affect the score.

```python
{
    "feature_id": "spatial.symmetry.knee",
    "value": 0.31,
    "availability": "low_confidence",
    "view_reliability": "low",
    "camera_zone": "Z3",
    "depth_dependency": "high",
    "model_depth_reliability": "low",
    "reasons": ["view_metric_low"],
}
```

Reporting and visualization should show both lists: one answers "why points were
deducted"; the other answers "why a computed metric was withheld."

---

## 8. Entry Point

```python
from movement.biomarker import derive_biomarkers

biomarker_records, score_records = derive_biomarkers(
    feat_records,
    biomech_records,
    exercise_definition,
    definition_version=exercise_definition.version,
    baseline_path=None,
    domain_weights=None,
    score_bounds=None,
)
```

Behavior:

```text
Always returns pass-through BiomarkerRecord entries.
Returns empty score_records if the baseline file is missing.
Scores each rep_id independently; falls back to sequence-level when needed.
```

---

## 9. Provenance And Clinical Boundary

```text
BiomarkerRecord.source_fields       inherited from FeatureRecord/BiomechRecord
BiomarkerScoreRecord.source_fields  feature_domains, biomechanical_focus,
                                    quality_rules, baseline file, score config
```

The composite score may mirror the structure of functional movement assessments,
but it is not directly comparable to FMS/OAB scores and must not be described as a
clinical diagnosis, patient classification, or clinical significance claim.

---

## 11. Code Mapping

```text
src/movement/biomarker/__init__.py        BiomarkerRecord, derive_biomarkers
src/movement/biomarker/scoring.py         BiomarkerScoreRecord, baseline IO,
                                          scoring, score bounds, weights
src/movement/biomarker/interpretation.py  YAML rule loader and InterpretationRecord
data/definitions/interpretation_rules/    per-exercise interpretation rules
scripts/compute_baseline.py               baseline generator
tests/test_biomarker_scoring_weights.py   weights and bounds
tests/test_biomarker_scoring_availability.py assessed-only scoring and withheld audit
tests/test_interpretation.py              rule engine behavior
```

---

## 12. Planned Extensions

- Phase-specific sub-scores after phase-aware feature evidence stabilizes.
- Exercise-specific domain-weight profiles after sensitivity analysis.
- Real cohort baseline support while preserving the synthetic fallback.
- Set-level trend records for within-set fatigue or consistency analysis.
