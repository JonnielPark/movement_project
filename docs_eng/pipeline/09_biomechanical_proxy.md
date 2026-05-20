# 09. Biomechanical Proxy

**Document Version:** 1.1.0
**Last Updated:** 2026-05-21
**Korean Sync:** `docs/pipeline/09_biomechanical_proxy.md` is the same-version Korean source.

Pipeline step ⑨ computes simplified biomechanical proxy metrics from normalized
pose data: center-of-mass (CoM) trajectory, 2D moment-arm proxies, and within-set
load-shift tendencies. The single-camera setup cannot estimate absolute force,
torque, or subject mass. Outputs describe relative load-distribution tendencies
only.

Allowed output units are `torso_length_ratio`, `torso_length_ratio_per_rep`,
`degree`, and `dimensionless`. Absolute units such as `N`, `N·m`, `kg`, and `m`
are treated as bugs.

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
→ ⑩ Biomarker Scoring
```

Required inputs:

```text
normalized coordinates          <landmark>_norm_x/y/z from ⑤
visibility columns (optional)   <landmark>_visibility
rep boundaries                  segment_type == rep, rep_id
exercise definition fields      landmarks.primary_joints
                                biomechanical_focus.main_load_regions
                                biomechanical_focus.expected_com_motion
                                quality_rules.minimum_visible_landmark_ratio
```

The pose dataframe is not modified. This step emits `BiomechRecord` rows.

## 2. Design Boundaries

Allowed:

```text
- Population-level segment mass and CoM ratios
- Whole-body CoM as a segment-mass-weighted proxy
- 2D moment-arm distances in projected planes
- Visibility-based frame exclusion for monocular robustness
- Relative joint-to-joint load-distribution tendencies
```

Not allowed in the current implementation:

```text
- Absolute force or torque
- Subject mass, external load, or kg-based scaling
- Meter/mm outputs
- Single-frame instantaneous joint-force claims
- Clinical diagnosis or disease classification
```

Future height-bin or anthropometric-survey priors must be documented as
dimensionless relative skeleton constraints before code implementation.

## 3. Anthropometric Model

`biomech/anthropometry.py` encodes Winter-style segment ratios:

```text
SEGMENT_MASS_RATIO   head, trunk, thigh, shank, foot, upper_arm, forearm, hand
SEGMENT_COM_RATIO    fraction of segment length from the proximal endpoint
SEGMENT_ENDPOINTS    landmark pair defining each segment
```

All ratios are dimensionless. The current trunk proxy uses a hip-to-shoulder
line. This is sufficient for relative proxy trends but not for absolute trunk
mass localization.

## 4. Computed Metrics

CoM metrics:

```text
biomech.com.range_x      lateral CoM excursion
biomech.com.range_z      vertical CoM excursion
biomech.com.path_length  total CoM trajectory length
unit                     torso_length_ratio
```

2D moment-arm proxies:

```text
biomech.moment_arm.knee.<side>.median
biomech.moment_arm.hip.<side>.median
unit = torso_length_ratio
```

The value is the median per-frame perpendicular distance from CoM to the
load-bearing joint-axis proxy. Joints are selected from
`biomechanical_focus.main_load_regions`. The current implementation emits hip
and knee proxies; ankle proxy support is not implemented yet.

Within-set load shift:

```text
biomech.load_shift.<joint>.<side>.slope
unit = torso_length_ratio_per_rep
rep_id = None
```

This is an ordinary least-squares slope of rep-level moment-arm medians against
`rep_id`. It requires at least 3 reps; otherwise no load-shift record is emitted.
The metric is a relative trend, not a fatigue diagnosis.

## 5. Visibility Handling

For each frame, visibility is averaged across primary joints:

```text
mean_vis(t) < quality_rules.minimum_visible_landmark_ratio → frame excluded
otherwise                                                  → frame included
```

Record metadata:

```text
visibility_weight_applied
n_frames_used
n_frames_excluded_low_visibility
```

`extract_rep_biomech(..., use_visibility_weight=False)` disables this exclusion
for ablation experiments in ⑫ simulation.

## 6. Output Contract

```python
@dataclass
class BiomechRecord:
    metric_id: str
    exercise_id: str
    rep_id: int | None
    value: float
    unit: str
    source_fields: list[str]
    note: str | None
    visibility_weight_applied: bool
    n_frames_used: int
    n_frames_excluded_low_visibility: int
```

Validation rules:

```text
unit must be torso_length_ratio | torso_length_ratio_per_rep | degree | dimensionless
source_fields must not be empty
```

## 7. Entry Point

```python
from movement.biomech import extract_rep_biomech

biomech_records = extract_rep_biomech(
    df,
    exercise_definition,
    use_visibility_weight=True,
)
```

Behavior:

```text
- Computes per-rep records when rep annotation exists
- Falls back to sequence-level records when annotation is absent
- Reads visibility threshold from quality_rules
- Appends load-shift records when at least 3 reps provide moment-arm metrics
```

## 8. Provenance

Every record references the exercise-definition fields that controlled the
calculation:

```text
biomech.com.*           biomechanical_focus.expected_com_motion
                        biomechanical_focus.stability_requirement
biomech.moment_arm.*    biomechanical_focus.main_load_regions
                        biomechanical_focus.expected_com_motion
biomech.load_shift.*    derived from biomech.moment_arm.* records
```

⑩ Biomarker Scoring preserves these fields when converting to biomarker records.

## 9. Code Mapping

```text
src/movement/biomech/__init__.py         BiomechRecord, extract_rep_biomech
src/movement/biomech/anthropometry.py    segment ratios and endpoints
src/movement/biomech/com.py              estimate_com, compute_com_metrics,
                                         compute_visibility_weights
src/movement/biomech/moment_arm.py       compute_moment_arms
src/movement/biomech/load_shift.py       compute_load_shift

tests/test_biomech_load_shift.py
```
