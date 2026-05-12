# 09. Biomechanical Proxy

**Document Version:** 1.0.1
**Last Updated:** 2026-05-06  
**Korean Sync:** `docs/pipeline/09_biomechanical_proxy.md` is the same-version Korean source.

Pipeline step ⑨. Computes simplified biomechanical proxy metrics — center of
mass (CoM) trajectory and moment arms — from normalized pose data.

The single mobile camera setup cannot resolve absolute depth nor estimate joint
forces in newtons. Instead of measuring **absolute** torque or load, this step
quantifies **relative** load-distribution tendencies that explain *which*
joints carry more of the work as the rep progresses. Corresponds to
dissertation §6.

All outputs are in `torso_length_ratio` (dimensionless) or `degree`. Absolute
units (`N`, `N·m`, `kg`, `m`) are forbidden — they are treated as a bug.

---

## 1. Pipeline Position

```text
Pose CSV
→ ① Validation
→ ② Annotation
→ ③ Exercise Definition
→ ④ Preprocessing
→ ⑤ Normalization
→ ⑥ Segmentation
→ ⑦ Motion Attribution
→ ⑧ Feature Extraction
→ ⑨ Biomech Proxy              ← this step
→ ⑩ Biomarker Derivation
```

Required inputs:
```text
normalized coordinates                  <landmark>_norm_x/y/z columns from ⑤
visibility columns (optional)           <landmark>_visibility for confidence weighting
rep boundaries                          segment_type == 'rep' + rep_id from ②
exercise definition fields              landmarks.primary_joints,
                                        biomechanical_focus.main_load_regions,
                                        biomechanical_focus.expected_com_motion,
                                        quality_rules.minimum_visible_landmark_ratio
```

Does not modify the pose dataframe; produces `BiomechRecord` rows.

## 2. Design Principle

```text
Allowed:
    Statistical anthropometric segment masses (Winter 1990)
    Whole-body CoM as segment-mass-weighted average
    2D projection moment arm proxies (sagittal / frontal)
    Visibility-weighted frame exclusion for monocular noise robustness
    Relative load-distribution tendencies between joints

Not allowed:
    Absolute force / torque outputs (N, N·m)
    Per-subject anthropometry (everything is dimensionless ratios)
    Patient-specific mass / length values
    Single-frame instantaneous forces (output is per-rep aggregate)
```

## 3. Anthropometric Modeling

`biomech/anthropometry.py` encodes Winter (1990) Table 4.1 segment ratios.
All ratios are dimensionless: whole-body mass = 1.0, segment length = 1.0.

```text
SEGMENT_MASS_RATIO   head 0.081  trunk 0.497  thigh 0.100  shank 0.0465  foot 0.0145
                     upper_arm 0.028  forearm 0.016  hand 0.006
SEGMENT_COM_RATIO    fraction of segment length from the proximal end
                     (e.g., thigh CoM at 43.3 % from the hip end)
SEGMENT_ENDPOINTS    landmark pair defining each segment (proximal, distal)
```

The trunk is approximated by the `(left_hip → left_shoulder)` line; this
is a center-line proxy adequate for proxy ratios but not for absolute
trunk mass localization.

## 4. Center of Mass (CoM) Estimation

`biomech/com.py — estimate_com()` returns `(T, 3)` per-frame CoM positions:

```text
seg_com(t)        = p_proximal(t) + com_ratio · ( p_distal(t) - p_proximal(t) )
whole_body_CoM(t) = Σ_seg ( mass_ratio · seg_com(t) ) / Σ_seg mass_ratio
```

Per-rep summary metrics (`compute_com_metrics`):

```text
biomech.com.range_x      lateral CoM excursion              (torso_length_ratio)
biomech.com.range_z      vertical CoM excursion             (torso_length_ratio)
biomech.com.path_length  total CoM trajectory arc length    (torso_length_ratio)
```

Interpretation: large `range_x` during a sagittal-plane exercise (e.g. squat)
suggests medial-lateral instability or weight-shift compensation; large
`path_length` relative to `range_z` suggests an inefficient CoM trajectory.

## 5. 2D Moment Arm Proxy

`biomech/moment_arm.py — compute_moment_arms()` projects to a 2D plane and
takes the perpendicular distance from the CoM to each load-bearing joint axis.

```text
plane          axis line                            metric_id
─────────      ─────────────                        ───────────────────────────
xz (sagittal)  ankle ↔ knee  (knee axis)            biomech.moment_arm.knee.<side>.median
xz (sagittal)  knee  ↔ hip   (hip axis)             biomech.moment_arm.hip.<side>.median
```

The **median** across frames of the per-frame distance is reported (more
robust to monocular outliers than mean). Joints to evaluate are read from
`biomechanical_focus.main_load_regions`:

```text
main_load_regions: [hip, knee, ankle]
    → emit hip + knee moment arms (ankle proxy not yet implemented)
```

## 6. Visibility-Weighted Confidence

Monocular pose engines occasionally produce momentary depth-estimation
collapses. `compute_visibility_weights()` excludes those frames from the
proxy computation rather than smoothing them, preserving monotonicity:

```text
mean_vis(t) = mean( <primary_joint>_visibility(t) for primary_joints )

if mean_vis(t) < quality_rules.minimum_visible_landmark_ratio:
    weight(t) = 0       (frame excluded)
else:
    weight(t) = mean_vis(t)
```

Effect on output records:
```text
visibility_weight_applied        True / False
n_frames_used                    frames included after the threshold
n_frames_excluded_low_visibility frames dropped
```

A/B comparison is supported by passing `use_visibility_weight=False` to
`extract_rep_biomech()`; useful for ablation experiments in ⑫ simulation.

## 7. Within-Set Load-Shift Tendency

`biomech/load_shift.py — compute_load_shift()` regresses per-rep moment-arm
medians against `rep_id` within a set to expose how load redistributes as the
user fatigues. Requires at least **3 reps**; returns an empty list otherwise.

```text
slope = np.polyfit( rep_ids,  moment_arm_medians,  1 )[0]

metric_id:  biomech.load_shift.<joint>.<side>.slope
unit:       torso_length_ratio_per_rep
rep_id:     None  (set-level — not per-rep)
```

Interpretation:
```text
negative slope_knee  ∧ positive slope_hip  → knee → hip load migration
                                             (fatigue-related hip-dominant
                                             compensation signature)
```

`extract_rep_biomech()` calls `compute_load_shift()` automatically when
`len(rep_ids) ≥ 3`. Results are appended to the returned `BiomechRecord` list
and flow into ⑩ biomarker scoring via the `biomech.*` domain.

## 8. Output: BiomechRecord

```python
@dataclass
class BiomechRecord:
    metric_id:                            str   # e.g. 'biomech.com.range_z'
    exercise_id:                          str
    rep_id:                               int | None
    value:                                float
    unit:                                 str   # torso_length_ratio | torso_length_ratio_per_rep
                                              # | degree | dimensionless
    source_fields:                        list[str]   # required (ValueError if empty)
    note:                                 str | None
    visibility_weight_applied:            bool
    n_frames_used:                        int
    n_frames_excluded_low_visibility:     int
```

Unit validation is enforced at construction time: any other unit raises
`ValueError`. This prevents accidental absolute-unit leakage from spreading
into ⑩ biomarker derivation.

## 9. Entry Point

```python
from movement.biomech import extract_rep_biomech

biomech_records = extract_rep_biomech(
    df,
    exercise_definition,
    use_visibility_weight=True,    # default
)
```

Behavior:
```text
- Iterates over rep_ids when annotation columns are present
- Falls back to sequence-level computation when annotation is absent
- Reads minimum_visible_landmark_ratio from quality_rules
- Returns one record per (rep_id × metric)
```

## 10. Provenance

Every BiomechRecord references the YAML fields that drove the computation:

```text
biomech.com.*           biomechanical_focus.expected_com_motion,
                        biomechanical_focus.stability_requirement
biomech.moment_arm.*    biomechanical_focus.main_load_regions,
                        biomechanical_focus.expected_com_motion
```

⑩ Biomarker Derivation passes these through to BiomarkerRecord without
modification, preserving the full provenance chain to the visualization layer.

## 11. Code Mapping

```text
src/movement/biomech/__init__.py         BiomechRecord, extract_rep_biomech,
                                         compute_load_shift
src/movement/biomech/anthropometry.py    Winter (1990) ratios, segment endpoints
src/movement/biomech/com.py              estimate_com, compute_com_metrics,
                                         compute_visibility_weights
src/movement/biomech/moment_arm.py       compute_moment_arms, _point_to_line_dist_2d
src/movement/biomech/load_shift.py       compute_load_shift; OLS slope per
                                         (joint × side); §7 within-set trend
tests/test_biomech_l
