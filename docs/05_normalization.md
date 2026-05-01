# Coordinate Normalization

## Purpose

Raw pose coordinates are affected by camera position, subject location, body size, and pose estimation scale.

Normalization converts raw landmark coordinates into a body-relative coordinate system so that movement patterns can be compared across frames and subjects.

This step is not intended to estimate absolute force or physical body dimensions. Its purpose is to provide a stable coordinate basis for downstream analysis such as ROM, symmetry, stability, trajectory shape, and biomechanical proxy modeling.

## Pipeline Role

Normalization runs after preprocessing and before motion attribution.

```text
Pose CSV
-> Validation
-> Annotation Mask Application
-> Preprocessing
-> Normalization
-> Motion Attribution
-> Feature Extraction
```

This order was selected because reference landmarks (hip and shoulder) should first be cleaned by reliability-based preprocessing so that torso-length scale estimation is not contaminated by a few unreliable frames.

## Design Summary

The first implementation uses:

```text
translation reference: frame-wise hip center
scale reference:       sequence-wise median torso length
```

This design was selected to reduce frame-to-frame scale jitter caused by monocular pose estimation noise.

## Step 1. Translation Normalization

The hip center is used as the body reference point.

```text
hip_center(t) = (left_hip(t) + right_hip(t)) / 2
```

Each landmark is translated by subtracting the hip center.

```text
p_translated_i(t) = p_i(t) - h(t)
```

Where:

```text
p_i(t) = landmark i at frame t
h(t)   = hip center at frame t
```

After this step, each landmark is represented relative to the pelvis rather than the original camera or image coordinate system.

## Step 2. Scale Normalization

The torso length is used as the initial body scale.

```text
shoulder_center(t) = (left_shoulder(t) + right_shoulder(t)) / 2
torso_length(t)    = distance(hip_center(t), shoulder_center(t))
```

Instead of using the torso length of each frame, the sequence-level median torso length is used as the representative scale.

```text
s = median(torso_length over all valid frames)
```

Each translated landmark is divided by this scale.

```text
p_norm_i(t) = (p_i(t) - h(t)) / s
```

Where:

```text
s = sequence-level median torso length
```

## Why Sequence-wise Median Scale?

A frame-wise scale can be unstable in monocular pose data because the estimated torso length may fluctuate due to landmark noise, occlusion, or depth estimation instability.

Using a sequence-wise median scale provides a more stable body-relative coordinate system.

```text
frame-wise scale:
- reacts to every frame
- sensitive to pose estimation noise
- may cause artificial skeleton jitter

sequence-wise median scale:
- stable across the sequence
- robust to short-term noise
- suitable for feature extraction
```

Therefore, the default normalization method is:

```text
p_norm_i(t) = (p_i(t) - hip_center(t)) / median_torso_length
```

## Relationship to Preprocessing

Preprocessing should run before normalization.

If preprocessing has already filtered or interpolated unreliable hip and shoulder landmarks, the median torso length is computed from cleaner data, and the normalization scale is more stable.

```text
preprocessed raw coordinates
-> hip-centered translation
-> torso-scale normalization
```

## Relationship to Biomechanical Proxy Modeling

This normalization step is an initial coordinate transformation.

It should not be confused with the later biomechanical proxy model.

```text
normalization.py
-> creates stable body-relative coordinates

biomechanics.py
-> estimates COM, segment-level relationships, moment arms, and relative load tendency
```

Later biomechanical modules may use segment-length estimation and anthropometric assumptions to calculate COM and moment-arm-based proxy indicators.

The current normalization only prepares the coordinate system for those later steps.

## Relationship to Motion Attribution

Motion attribution runs on the normalized dataframe.

Working in body-relative coordinates makes motion-energy comparison across reps and subjects more consistent, because absolute body size and camera distance are already factored out.

## Output Columns

Raw coordinates are preserved.

Normalized coordinates are added as new columns.

```text
left_knee_x      -> raw x coordinate
left_knee_norm_x -> normalized x coordinate

left_knee_y      -> raw y coordinate
left_knee_norm_y -> normalized y coordinate

left_knee_z      -> raw z coordinate
left_knee_norm_z -> normalized z coordinate
```

Additional helper columns may also be added:

```text
hip_center_x
hip_center_y
hip_center_z

shoulder_center_x
shoulder_center_y
shoulder_center_z

torso_length
```

## Normalization Report

The normalization function should return both the normalized dataframe and a report.

```python
norm_df, norm_report = normalize_pose_by_hip_torso(df, landmarks)
```

The report should include:

```text
method
num_frames
scale_method
scale_value
min_torso_length
max_torso_length
median_torso_length
num_invalid_torso_frames
num_normalized_landmarks
```

This allows abnormal scale estimation or landmark problems to be inspected later.

## Initial Completion Criteria

The first implementation is complete when:

```text
1. raw coordinates are preserved
2. normalized coordinates are added
3. hip center is approximately zero after normalization
4. median normalized torso length is approximately 1.0
5. normalization report is returned
6. raw and normalized skeletons can be visualized
```

## Future Extensions

Later versions may include:

- visibility-based scale filtering
- torso length outlier removal
- rotation normalization using a body-centered coordinate system
- exercise-specific normalization rules
- segment-length-based anthropometric modeling
