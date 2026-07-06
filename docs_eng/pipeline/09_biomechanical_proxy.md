# 09. Biomechanical Proxy

**Document Version:** 1.3.1
**Last Updated:** 2026-06-29
**Korean Sync:** `docs/pipeline/09_biomechanical_proxy.md` is the same-version Korean source.

Pipeline step ⑨ computes simplified biomechanical proxy metrics from normalized
pose data: center-of-mass (CoM) trajectory proxies, 2D moment-arm proxies, and
within-set load-shift tendencies. The single-camera setup cannot estimate
absolute force, torque, calibrated vertical displacement, or subject mass.
Outputs describe relative load-distribution tendencies only.

Because current MediaPipe-style monocular `z` is model-depth evidence, not a
calibrated depth or gravity axis, ⑨ outputs are emitted as low-confidence
biomechanical proxy evidence by default. They may be reported and inspected, but
should not become strong composite-score evidence unless a later scoring policy
explicitly upgrades their weight from availability/provenance metadata.

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
→ ⑥ Canonicalization
→ ⑦ Segmentation
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
- 2D moment-arm distances in projected planes as proxy evidence
- Visibility-based frame exclusion for monocular robustness
- Relative joint-to-joint load-distribution tendencies
```

Not allowed in the current implementation:

```text
- Absolute force or torque
- Subject mass, external load, or kg-based scaling
- Meter/mm outputs
- Treating model-depth values as calibrated gravity/depth evidence
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

This Winter-style model is separate from the Size Korea-derived
`anthropometric_skeleton_prior` described in
[06_canonicalization.md](06_canonicalization.md). Winter ratios are used for CoM and
segment-mass proxy computation inside ⑨. The Size Korea prior is a loose
segment-length plausibility envelope for monocular-depth confidence and candidate
evidence inside ⑥. The two priors must not be merged into
one subject-specific skeleton model.

Current policy:

```text
Winter anthropometry         CoM / segment-mass proxy in ⑨
Size Korea aggregate prior   segment-length plausibility envelope in ⑥
row-level Size Korea prior   future empirical upgrade only if raw data exist
foot segment conflict        Size Korea full-body auto source marks foot unavailable;
                             Winter foot mass ratio may still remain in CoM proxy
```

## 4. Computed Metrics

CoM metrics:

```text
biomech.com.range_x      lateral CoM excursion
biomech.com.range_z      normalized z-axis CoM excursion
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
load-bearing joint-axis proxy in the current normalized projection. Joints are selected from
`biomechanical_focus.main_load_regions`. The current implementation emits hip
and knee proxies; ankle proxy support is not implemented yet.

Within-set load shift:

```text
biomech.load_shift.<joint>.<side>.slope
unit = torso_length_ratio_per_rep
rep_id = None
```

This is an ordinary least-squares slope of rep-level moment-arm medians against
`rep_id`. Non-finite moment-arm medians are excluded before fitting. It requires
at least 3 finite reps with distinct `rep_id` values; otherwise no load-shift
record is emitted. The metric is a relative trend, not a fatigue diagnosis.

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
    availability: str = "low_confidence"
    availability_reasons: list[str] = field(default_factory=list)
    depth_dependency: str = "high"
    model_depth_reliability: str = "low"
    landmark_quality: str = "unknown"
```

Validation rules:

```text
unit must be torso_length_ratio | torso_length_ratio_per_rep | degree | dimensionless
source_fields must not be empty
availability must be assessed | low_confidence | not_assessed
depth_dependency must be none | low | moderate | high | unknown
model_depth_reliability must be high | moderate | low | unknown
```

Default availability policy:

```text
CoM trajectory proxies       low_confidence; model-depth and segment-ratio proxy
moment-arm proxies           low_confidence; projected 2D proxy with model-depth input
load-shift slopes            low_confidence; derived from low-confidence moment-arm records
```

This policy keeps ⑨ available for reporting and later comparison while preventing
uncalibrated monocular-depth proxy values from silently becoming strong scores.

Saved stage-check outputs:

```text
data/processed/biomech/<recording_id>_biomech.csv
    Tabular BiomechRecord output. Required columns include metric_id,
    exercise_id, rep_id, value, unit, source_fields, note,
    visibility_weight_applied, n_frames_used,
    n_frames_excluded_low_visibility, availability, availability_reasons,
    depth_dependency, model_depth_reliability, and landmark_quality.

data/processed/biomech/<recording_id>_biomech_qc.json
    Compact counts for follow-along checks, such as row counts, unit counts,
    availability counts, metric-family counts, and missing source_fields.
```

CSV round-trips must preserve the row count and required columns. Structured
fields such as `source_fields` and `availability_reasons` may be serialized for
CSV compatibility.

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
- Appends load-shift records when at least 3 finite reps provide moment-arm metrics
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
Composite scoring should treat `availability != assessed` as withheld or
minimal-gravity evidence unless a later scoring policy explicitly says otherwise.

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
