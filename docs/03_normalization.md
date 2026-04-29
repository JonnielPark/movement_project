# Coordinate Normalization

## Purpose

Raw pose coordinates are affected by camera position, subject location, body size, and pose estimation scale.

Normalization converts raw landmark coordinates into a body-relative coordinate system so that movement patterns can be compared across frames and subjects.

## Step 1. Translation Normalization

The hip center is used as the body reference point.

```text
hip_center = (left_hip + right_hip) / 2
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

## Step 2. Scale Normalization

The torso length is used as the body scale.

```text
shoulder_center = (left_shoulder + right_shoulder) / 2
torso_length    = distance(hip_center, shoulder_center)
```

For stability, the sequence-level median torso length is used.

```text
s = median(torso_length over all frames)
```

Each translated landmark is divided by the scale.

```text
p_norm_i(t) = (p_i(t) - h(t)) / s
```

## Initial Design Choice

The first implementation uses:

```text
reference point: frame-wise hip center
scale value:     sequence-wise median torso length
```

This provides stable translation and scale normalization while avoiding frame-wise scale jitter.

## Output Columns

Normalized coordinates are stored as new columns.

```text
left_knee_x      -> raw x coordinate
left_knee_norm_x -> normalized x coordinate
```

Raw coordinates are preserved.

## Future Extension

Later versions may include:

- visibility-based scale filtering
- rotation normalization using a body-centered coordinate system
- exercise-specific normalization rules
