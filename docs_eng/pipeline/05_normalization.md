# 05. Normalization

**Document Version:** 1.0.0  
**Last Updated:** 2026-05-06  
**Korean Sync:** `docs/pipeline/05_normalization.md` is the same-version Korean source.

Pipeline step ⑤. Converts raw pose coordinates to a body-relative coordinate system,
removing the effects of camera position, subject position, and body size.

Does not estimate absolute forces or absolute body dimensions.
Provides a stable coordinate base for ⑧ feature extraction and ⑨ biomechanical proxy modeling.

---

## 1. Pipeline Position

```text
Pose CSV
→ ① Validation
→ ② Annotation
→ ③ Exercise Definition
→ ④ Preprocessing
→ ⑤ Normalization          ← this step
→ ⑥ Segmentation
→ ⑦ Motion Attribution
→ ⑧ Feature Extraction
```

Runs after ④ preprocessing because the scale reference (median torso length) is more
stable once hip/shoulder landmarks have passed reliability checks.

Does not branch per exercise type — the same normalization applies to all exercises.

## 2. Method: hip_torso

```text
Translation reference : frame-wise hip center
Scale reference       : sequence-wise median torso length
```

Using the sequence-wise median (rather than per-frame scale) avoids artificial skeleton
jitter caused by per-frame torso length noise in monocular depth estimation.

## 3. Step 1 — Translation

Hip center as the body-reference origin:

```text
hip_center(t) = (left_hip(t) + right_hip(t)) / 2
```

Each landmark is translated:

```text
p_translated_i(t) = p_i(t) - hip_center(t)
```

After this step, all landmarks are expressed relative to the pelvis origin.

## 4. Step 2 — Scale

Torso length as the body scale unit:

```text
shoulder_center(t) = (left_shoulder(t) + right_shoulder(t)) / 2
torso_length(t)    = distance(hip_center(t), shoulder_center(t))
```

Sequence-wise median is used as the representative scale:

```text
s = median(torso_length over all valid frames)
```

Each translated landmark is divided by `s`:

```text
p_norm_i(t) = (p_i(t) - hip_center(t)) / s
```

The resulting unit is `torso_length_ratio` (dimensionless).

## 5. Output Columns

Raw coordinates are preserved. Normalized coordinates are added as new columns:

```text
left_knee_x      → original x      left_knee_norm_x → normalized x
left_knee_y      → original y      left_knee_norm_y → normalized y
left_knee_z      → original z      left_knee_norm_z → normalized z
```

Reference columns (when `keep_reference_columns: true` in YAML):

```text
hip_center_x, hip_center_y, hip_center_z
shoulder_center_x, shoulder_center_y, shoulder_center_z
torso_length
```

## 6. Configuration

```yaml
normalization:
  enabled: true
  method: hip_torso
  keep_reference_columns: true
```

## 7. Normalization Report

```python
norm_df, norm_report = normalize_pose_by_hip_torso(df, landmarks)
```

Report fields:

```python
{
    "method": str,
    "num_frames": int,
    "scale_method": str,
    "scale_value": float,          # median torso length (raw units)
    "min_torso_length": float,
    "max_torso_length": float,
    "median_torso_length": float,
    "num_invalid_torso_frames": int,
    "num_normalized_landmarks": int,
}
```

## 8. Relationship to Other Steps

- **④ Preprocessing**: unreliable landmarks (low visibility, swap-corrected) should be
  resolved or marked before normalization to prevent scale contamination.
- **⑦ Motion Attribution**: uses normalized coordinates; body-size and camera-distance
  effects are already removed, making per-rep motion energy comparison more consistent.
- **⑨ Biomech Proxy**: uses normalized coordinates as input for CoM and moment arm estimation.
  This step provides the coordinate system; ⑨ adds the biomechanical computation.

## 9. Planned Extensions

- Visibility-weighted scale estimation
- Torso length outlier removal before median computation
- Rotation normalization (body-relative yaw alignment)
- Per-exercise normalization rules driven by exercise definition fields
