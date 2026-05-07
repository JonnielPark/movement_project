# 00. Data Format

**Document Version:** 1.0.0  
**Last Updated:** 2026-05-06  
**Korean Sync:** `docs/pipeline/00_data_format.md` is the same-version Korean source.

Input format specification for monocular 3D pose time series data.

---

## 1. Input

CSV file exported from a pose estimation engine (e.g., MediaPipe Pose 33, iPIXEL EXERCITE).
One row per frame.

## 2. Required Columns

```text
frame        integer frame index (sortable, monotonically increasing)
timestamp    seconds since recording start (float)
```

- `frame` — used for continuity and duplicate checks in ① validation.
- `timestamp` — used to estimate sampling interval and FPS.

## 3. Landmark Coordinate Columns

Each landmark has three coordinate columns:

```text
<landmark>_x
<landmark>_y
<landmark>_z
```

Example:

```text
left_knee_x
left_knee_y
left_knee_z
```

Landmark names are defined in [src/movement/config.py](../../src/movement/config.py).
Naming convention: `left_*` / `right_*` prefixes for bilateral landmarks.

## 4. Visibility Columns (optional, recommended)

```text
<landmark>_visibility    float 0.0–1.0
```

Used by ④ preprocessing for reliability gating. In monocular data, landmarks are rarely
fully absent — they are more commonly reported with low visibility. Including visibility
columns improves the reliability classification.

## 5. CSV Example

```text
frame,timestamp,nose_x,nose_y,nose_z,nose_visibility,left_shoulder_x,...
0,0.000,0.51,0.23,-0.12,0.98,0.42,...
1,0.033,0.52,0.24,-0.13,0.97,0.43,...
```

Sample file: `data/pose/sample/mediapipe_squat_synthetic.csv`

## 6. Assumptions

```text
1. One row = one frame.
2. Each landmark has x, y, z columns.
3. frame values are sortable.
4. timestamp values are monotonically increasing.
5. Landmark names match the definitions in src/movement/config.py.
```

Violations are reported by ① validation (see [01_validation.md](01_validation.md)).

## 7. Coordinate Convention

- Input coordinates are in the native units of the pose estimation engine
  (e.g., MediaPipe normalized image coordinates).
- ⑤ normalization converts to a body-relative coordinate system
  (see [05_normalization.md](05_normalization.md)).
- All downstream features and biomarkers use dimensionless `torso_length_ratio` units or degrees.
  Absolute force/length units are not used.

## 8. Data Management

`data/` separates analysis-input CSVs from analysis definition files:

```text
data/pose/         joint-point time-series CSVs
data/definitions/  exercise definitions, interpretation rules, clinical mapping YAML
data/reference/    reference statistics such as the synthetic-normal baseline
data/processed/    pipeline outputs (.gitignore)
```

Raw videos are not analysis inputs for this repository. Shareable joint-point
CSVs are stored under `data/pose/` after direct identifiers have been removed.
