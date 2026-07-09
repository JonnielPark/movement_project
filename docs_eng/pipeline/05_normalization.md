# 05. Normalization

**Document Version:** 2.3.1
**Last Updated:** 2026-07-09
**Korean Sync:** `docs/pipeline/05_normalization.md` is the same-version Korean source.

Pipeline step ⑤ converts preprocessed pose data into normalized pose data:
preprocessed pose data plus a body-relative coordinate family named `norm` and
explicit depth-evidence metadata. The base operation performs translation and
scale normalization only. A pose backend may provide x/y/z, as MediaPipe-style
outputs do, or x/y plus confidence only, as YOLO pose commonly does. Therefore
① Validation performs schema harmonization for 2D backends: missing raw z
columns are added as `NaN` placeholders so later tables share an xyz column
shape. Placeholder z is not depth evidence and must be separated from z
evaluation by provenance and downstream gates.

Optional analysis-space canonicalization is now treated as a ⑤ substage because
not every recording should pass through canonicalization, and recordings that do
pass through it may activate only selected priors.

This step does not estimate absolute force, torque, calibrated 3D position, or
absolute body dimensions. It provides the stable coordinate base consumed by
later recording-view feature extraction and by optional canonicalization filters.

---

## 1. Pipeline Position

```text
Pose CSV
→ ① Validation
→ ② Annotation
→ ③ Exercise Definition
→ ④ Preprocessing
→ ⑤ Normalization          ← this step
   └─ ⑤-1 Optional Canonicalization filters
→ ⑥ Segmentation
→ ⑦ Feature Extraction
→ ⑧ Biomechanical Proxy
→ ⑨ Biomarker Scoring
```

Runs after ④ Preprocessing so unreliable hip/shoulder landmarks are corrected,
interpolated, or marked before they affect the scale reference.

The former standalone Canonicalization stage is folded into ⑤ as the optional
⑤-1 branch. Downstream stages are renumbered after the merge: ⑥ Segmentation,
⑦ Feature Extraction, ⑧ Biomechanical Proxy, and ⑨ Biomarker Scoring.

The stage-check notebook should normalize the preprocessed pose data, not the
raw pose CSV directly. It should also confirm that preprocessing provenance
columns are preserved in the normalized output: `preprocessing_valid` and
per-landmark usability/source columns are required, while
`preprocessing_confidence` is checked when it is emitted by ④.

The stage-check notebook should follow the established notebook style used by
the earlier stage checks: `Data Setup`, `Direct Normalization Test`, numbered
checks, `Pipeline Integration`, and `Check Summary`. Visualization may remain in
the notebook when it directly confirms the normalized coordinate output.

---

## 2. Base Normalization Contract

The stable normalization method is `hip_torso`. After schema harmonization, the
table shape is xyz, but the scale/evidence path may still be recording-view xy
when z is only a placeholder.

```text
Translation reference : frame-wise hip center
Scale reference       : sequence-wise median torso length
Model-depth gain      : model_depth_scale, default 1.0 (only when finite model z exists)
Output unit           : torso_length_ratio (dimensionless)
```

The hip center is the body-relative origin.

```text
hip_center(t) = (left_hip(t) + right_hip(t)) / 2
p_translated_i(t) = p_i(t) - hip_center(t)
```

The sequence-level median torso length is the body scale. Using a sequence
median instead of a per-frame scale avoids artificial skeleton jitter from
monocular torso-length noise.

```text
shoulder_center(t) = (left_shoulder(t) + right_shoulder(t)) / 2
torso_length_xy(t) = distance_xy(hip_center(t), shoulder_center(t))
torso_length_xyz(t)= distance_xyz(hip_center(t), shoulder_center(t))  # when finite z evidence exists
s                  = median(valid torso_length_xy or torso_length_xyz)
p_norm_x_i(t)      = p_translated_x_i(t) / s
p_norm_y_i(t)      = p_translated_y_i(t) / s
p_norm_z_i(t)      = NaN                                             # when z is placeholder only
p_norm_z_i(t)      = p_translated_z_i(t) * model_depth_scale / s     # when finite model z exists
```

`model_depth_scale` is a coordinate-gain parameter for monocular model depth,
not camera calibration. The default is `1.0`; review runs may attenuate model
depth, but this must be reported and remains low-confidence evidence.

### 2.1 XYZ Schema Harmonization And Z Evidence Contract

① Validation/schema harmonization makes the coordinate table shape consistent
before preprocessing and normalization. If YOLO-style input lacks z, the missing
`<landmark>_z` columns are added with `NaN` values.

```text
raw.shape_axes      = [x, y, z]
raw.observed_axes   = [x, y] or [x, y, z]
raw.z_source        = absent | model_depth | partial_model_depth
raw.z_evaluable     = false | true
raw.z_fill_policy   = nan_placeholder | provided_by_backend
```

⑤ Normalization preserves the xyz schema and emits `*_norm_x/y/z`. If raw z was
only a `NaN` placeholder, `*_norm_z` remains `NaN`, `normalized_evidence_axes`
is `[x,y]`, and `z_evaluable` remains `false`. It must not fill z with zero,
because a zero-filled z axis can be misused by downstream features as observed
depth.

```text
2D input  : <landmark>_x, <landmark>_y, <landmark>_confidence or confidence
2D harmonized input : <landmark>_x, <landmark>_y, <landmark>_z = NaN
2D normalized output: <landmark>_norm_x, <landmark>_norm_y, <landmark>_norm_z = NaN
3D input  : <landmark>_x, <landmark>_y, <landmark>_z, <landmark>_confidence
3D output : <landmark>_norm_x, <landmark>_norm_y, <landmark>_norm_z
```

Even 2D input can support hip/shoulder-based body-relative coordinates and a
torso-length ratio. However, depth-sensitive features cannot become
scoring-ready from `norm` alone. They may be reviewed only as analysis evidence
when ⑤-1 Canonicalization emits a separate `canonical_depth_hypothesis` or
`canon` analysis evidence with confidence and `quality_gravity` summaries. Raw
residual/burden diagnostics stay in the canonicalization report or audit export.

Raw coordinates are never overwritten.

```text
left_knee_x       original x
left_knee_norm_x  base normalized x
```

Coordinate families have fixed meanings.

```text
raw   original pose coordinates
norm  hip-torso normalized coordinates from ⑤
```

Use the table-state terms consistently:

```text
Preprocessed pose data = raw pose coordinates + observation confidence + preprocessing provenance
Normalized pose data   = preprocessed pose data + body-relative norm coordinates + depth-evidence metadata
```

`Preprocessed pose data` is not a coordinate-family name. ⑤ adds the `norm`
coordinate family on top of that table state.

`canon` and any corrected-3D-hypothesis coordinate families are optional
canonicalization outputs of ⑤-1, not replacements for `raw` or `norm`.

---

## 3. Configuration Contract

Detailed defaults live in `configs/pipeline_default.yaml`. The stable ⑤ contract
is:

```yaml
normalization:
  enabled: true
  method: hip_torso
  coordinate_axes: auto  # auto | xy | xyz; selects z evidence use, not table shape
  keep_reference_columns: true
  model_depth_scale: 1.0
  canonicalization:
    enabled: false
    coordinate_mode: norm
    output_prefix: canon
    report_only: true
    downstream_coordinate_mode: norm
    support_plane_alignment:
      enabled: false
    movement_plane_alignment:
      enabled: false
    protocol_height_lateral_width_alignment:
      enabled: false
    xy_depth_lift:
      enabled: false
      method: recording_view_depth_hypothesis
    anthropometric_skeleton_prior:
      enabled: false
    corrected_3d_hypothesis:
      enabled: false
```

The nested `normalization.canonicalization` block is the preferred configuration
surface. The older root-level `canonicalization` block remains a
backward-compatible alias for existing configs and notebooks.

`coordinate_axes: auto` selects whether finite z evidence participates in scale
and z normalization. The table shape stays xyz after ① harmonization. Explicit
`xy` keeps z as non-evaluable even if z columns are present. Explicit `xyz`
requires finite z evidence and must fail when z is only a placeholder.

⑤ Normalization does not assign score-policy weights or final-score contribution.
It exposes the coordinate scale and model-depth gain needed by later stages.
Optional canonicalization can expose evidence availability, confidence,
`quality_gravity`, and norm-vs-analysis sensitivity. Raw correction burden and
residual diagnostics stay in the canonicalization report.

Downstream stages receive normalized pose data rather than a single "trusted"
coordinate stream. In practice, that means the preprocessed table is preserved,
the `norm` family is added, and depth-evidence metadata records whether z is
finite backend model depth or only a placeholder. Later feature extraction and
scoring decide how much a coordinate family contributes by using availability,
confidence, `quality_gravity`, and norm-vs-analysis sensitivity. Raw burden and
residual values are interpreted only in review/audit contexts.
This does not retroactively change ① structural validation; it gates feature
availability and score contribution downstream.

---

## 4. Optional Canonicalization Substage

Canonicalization is an opt-in branch under ⑤. It consumes `norm` coordinates and
may add `canon` or corrected-3D-hypothesis analysis-space coordinate families. When
`norm_z` is a placeholder, ⑤-1 may fill `canon_z` through an explicit
`xy_depth_lift` prior. That z axis is a canonical depth hypothesis, not observed
depth. This makes YOLO-style data structurally comparable to MediaPipe-style
xyz data while leaving depth evaluation disabled until later policy promotes it.

```text
raw      original pose coordinates
norm     hip-torso normalized coordinates from ⑤
canon    optional analysis-space coordinates from ⑤-1
```

Each prior is independently switchable. A recording may use no canonicalization,
only `support_plane_alignment`, only `protocol_height_lateral_width_alignment`,
or a reviewed combination of priors.

```yaml
normalization:
  canonicalization:
    enabled: true
    support_plane_alignment:
      enabled: true
    movement_plane_alignment:
      enabled: false
    protocol_height_lateral_width_alignment:
      enabled: false
    xy_depth_lift:
      enabled: true
      method: recording_view_depth_hypothesis
    corrected_3d_hypothesis:
      enabled: false
```

`report_only: true` means analysis-space columns and a `canonicalization_report` may
be emitted, while downstream stages still consume `norm` by default. Promoting
`downstream_coordinate_mode: canon` requires notebook review, robustness
evidence, and an explicit docs update.

The historical detailed canonicalization reference remains in
[05_1_canonicalization.md](05_1_canonicalization.md), but it is no longer a required
standalone pipeline stage.

## 5. Report Contract

`normalize_pose_by_hip_torso(df, landmarks)` returns a normalized DataFrame and a
report.

```python
{
    "method": str,
    "input_pose_data_state": "preprocessed_pose_data" | str,
    "output_pose_data_state": "normalized_pose_data",
    "input_coordinate_families": list[str],
    "output_coordinate_families": list[str],
    "input_coordinate_axes": dict[str, list[str]],
    "output_coordinate_axes": dict[str, list[str]],
    "added_coordinate_family": "norm",
    "normalized_axes": ["x", "y", "z"],
    "normalized_evidence_axes": ["x", "y"] | ["x", "y", "z"],
    "z_axis_policy": "nan_placeholder" | "preserved_model_depth",
    "z_source": "absent" | "model_depth" | "partial_model_depth",
    "z_evaluable": bool,
    "num_frames": int,
    "scale_method": str,
    "scale_value": float,
    "min_torso_length": float,
    "max_torso_length": float,
    "median_torso_length": float,
    "num_invalid_torso_frames": int,
    "num_normalized_landmarks": int,
    "model_depth_scale": float,
}
```

The public ⑤ review surface should focus on:

```text
scale_value
num_invalid_torso_frames
model_depth_scale
presence of <landmark>_norm_x/y/z columns
normalized_axes
normalized_evidence_axes
z_axis_policy
z_evaluable
```

The base normalization report does not include corrected-coordinate readiness,
score-policy weights, or final-score contribution flags. When ⑤-1 is enabled, the
pipeline report additionally includes `report["canonicalization"]` with
evidence availability, confidence, `quality_gravity`, active priors,
skipped-prior reasons, and report-local correction burden/residual diagnostics.

---

## 6. Downstream Rules

- ⑤-1 Canonicalization consumes `norm` coordinates and may add `canon` or
  corrected-3D-hypothesis coordinate families.
- Inputs with placeholder `norm_z` can proceed to recording-view features after
  ⑥. Depth-sensitive features must check finite z evidence and `z_evaluable`;
  they remain `not_assessed` or withheld unless ⑤-1 analysis evidence is
  explicitly promoted.
- ⑥ Segmentation, ⑦ Feature Extraction, ⑧ Biomechanical Proxy, and
  ⑨ Biomarker Scoring consume `norm` coordinates by default.
- Downstream features must declare `recording_view_only`,
  `corrected_3d_hypothesis`, or `dual_domain_compare` before using analysis-space evidence
  coordinates produced by ⑤-1.
- ⑤ must not hide monocular-depth errors. If raw/model depth is unstable before
  movement onset, that instability remains visible in `norm`; ⑤-1 may mark a
  analysis evidence as low confidence or not available.
- ⑧ Biomechanical Proxy uses normalized coordinates to compute relative CoM,
  moment-arm, and load-shift proxies. It must not infer absolute force, torque,
  or calibrated physical distances from this step.

---

## 7. Planned Extensions

- confidence-weighted scale estimation and torso-length outlier handling.
- Per-exercise normalization parameter review, without moving exercise priors
  into ⑤.
- Robustness evaluation of `model_depth_scale` sensitivity before any
  depth-sensitive downstream policy receives nonzero score-policy weight.
- Keep xyz schema harmonization stable for YOLO/2D pose backends while refining
  `xy_depth_lift` and depth-evaluation gates.
