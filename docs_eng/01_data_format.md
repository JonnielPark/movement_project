# 01. Data Format

**Document Version:** 1.0.0  
**Last Updated:** 2026-05-06  
**Versioning Rule:** Semantic Versioning 2.0.0 (`MAJOR.MINOR.PATCH`)  
**Korean Sync:** `docs/01_data_format.md` is the same-version Korean source.

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

Landmark names are defined in [src/movement/config.py](../src/movement/config.py).
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

Sample file: `data/sample/mediapipe_squat_synthetic.csv`

## 6. Assumptions

```text
1. One row = one frame.
2. Each landmark has x, y, z columns.
3. frame values are sortable.
4. timestamp values are monotonically increasing.
5. Landmark names match the definitions in src/movement/config.py.
```

Violations are reported by ① validation (see [02_validation.md](02_validation.md)).

## 7. Coordinate Convention

- Input coordinates are in the native units of the pose estimation engine
  (e.g., MediaPipe normalized image coordinates).
- ⑤ normalization converts to a body-relative coordinate system
  (see [06_normalization.md](06_normalization.md)).
- All downstream features and biomarkers use dimensionless `torso_length_ratio` units or degrees.
  Absolute force/length units are not used.

## 8. Data Management

Never commit to the repository:

```text
data/raw/       raw video footage
data/private/   private recordings
data/clinical/  clinical / identifiable data
data/videos/    any video files
```

Only shareable synthetic / demo data is stored in `data/sample/`.
