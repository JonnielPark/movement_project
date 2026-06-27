# 05. Normalization

**Document Version:** 2.0.0
**Last Updated:** 2026-06-16
**Korean Sync:** `docs/pipeline/05_normalization.md` is the same-version Korean source.

Pipeline step ⑤ converts raw pose coordinates into a body-relative coordinate
family named `norm`. It performs translation and scale normalization only. It
does not create canonicalized, corrected-depth, or exercise-prior-constrained
candidate coordinates.

This step does not estimate absolute force, torque, calibrated 3D position, or
absolute body dimensions. It provides the stable coordinate base consumed by
⑥ Canonicalization and by later recording-view feature extraction.

---

## 1. Pipeline Position

```text
Pose CSV
→ ① Validation
→ ② Annotation
→ ③ Exercise Definition
→ ④ Preprocessing
→ ⑤ Normalization          ← this step
→ ⑥ Canonicalization
→ ⑦ Segmentation
→ ⑨ Feature Extraction
→ ⑩ Biomechanical Proxy
→ ⑪ Biomarker Scoring
```

Runs after ④ Preprocessing so unreliable hip/shoulder landmarks are corrected,
interpolated, or marked before they affect the scale reference.

The stage-check notebook should normalize the preprocessed dataframe, not the
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

The implemented method is `hip_torso`.

```text
Translation reference : frame-wise hip center
Scale reference       : sequence-wise median torso length
Model-depth gain      : model_depth_scale, default 1.0
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
torso_length(t)    = distance(hip_center(t), shoulder_center(t))
s                  = median(valid torso_length)
p_norm_x_i(t)      = p_translated_x_i(t) / s
p_norm_y_i(t)      = p_translated_y_i(t) / s
p_norm_z_i(t)      = p_translated_z_i(t) * model_depth_scale / s
```

`model_depth_scale` is a coordinate-gain parameter for monocular model depth,
not camera calibration. The default is `1.0`; review runs may attenuate model
depth, but this must be reported and remains low-confidence evidence.

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

`canon` and any corrected-3D-hypothesis candidate families are defined in
[06_canonicalization.md](06_canonicalization.md). They are additive outputs of
⑥, not replacements for `raw` or `norm`.

---

## 3. Configuration Contract

Detailed defaults live in `configs/pipeline_default.yaml`. The stable ⑤ contract
is:

```yaml
normalization:
  enabled: true
  method: hip_torso
  keep_reference_columns: true
  model_depth_scale: 1.0
```

⑤ Normalization does not assign score gravity. It exposes the coordinate scale
and model-depth gain needed by later stages. Any candidate confidence, correction
burden, residual, or norm-vs-candidate sensitivity belongs to
⑥ Canonicalization or later scoring policy.

Downstream stages receive the carried coordinate families and provenance rather
than a single "trusted" coordinate stream: raw coordinates, preprocessing
reliability/usability metadata, and `norm` coordinates are preserved. Later
feature extraction and scoring decide how much a coordinate family contributes
by using availability, confidence, correction burden, residuals, and
norm-vs-candidate sensitivity. This does not retroactively change ① structural
validation; it gates feature availability and score contribution downstream.

---

## 4. Report Contract

`normalize_pose_by_hip_torso(df, landmarks)` returns a normalized DataFrame and a
report.

```python
{
    "method": str,
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
```

No `canonicalization_report`, corrected-coordinate readiness, score gravity, or
final-score contribution flag is emitted by ⑤.

---

## 5. Downstream Rules

- ⑥ Canonicalization consumes `norm` coordinates and may add `canon` or
  corrected-3D-hypothesis candidate families.
- ⑦ Segmentation, ⑨ Feature Extraction, ⑩ Biomechanical Proxy, and
  ⑪ Biomarker Scoring consume `norm` coordinates by default.
- Downstream features must declare `recording_view_only`,
  `corrected_3d_hypothesis`, or `dual_domain_compare` before using candidate
  coordinates produced by ⑥.
- ⑤ must not hide monocular-depth errors. If raw/model depth is unstable before
  movement onset, that instability remains visible in `norm`; ⑥ may mark a
  candidate as low confidence or not available.
- ⑩ Biomechanical Proxy uses normalized coordinates to compute relative CoM,
  moment-arm, and load-shift proxies. It must not infer absolute force, torque,
  or calibrated physical distances from this step.

---

## 6. Planned Extensions

- Visibility-weighted scale estimation and torso-length outlier handling.
- Per-exercise normalization parameter review, without moving exercise priors
  into ⑤.
- Robustness evaluation of `model_depth_scale` sensitivity before any
  depth-sensitive downstream policy receives nonzero score gravity.
