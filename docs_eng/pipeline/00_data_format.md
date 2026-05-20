# 00. Data Format

**Document Version:** 1.1.0
**Last Updated:** 2026-05-21
**Korean Sync:** `docs/pipeline/00_data_format.md` is the same-version Korean source.

Input specification for monocular 3D pose time-series CSV files.

---

## 1. Input Contract

The current pipeline expects a MediaPipe-style 33-landmark CSV:

```text
one row = one frame
required scalar columns = frame, timestamp
coordinate columns = <landmark>_x, <landmark>_y, <landmark>_z
optional visibility columns = <landmark>_visibility
landmark names = src/movement/core/config.py
```

Other engines are adapters until their export schemas are available. They should
be converted into this schema before entering the current pipeline.

## 2. Required Columns

```text
frame        integer frame index; sortable and monotonically increasing
timestamp    seconds since recording start; float
```

① Validation uses these columns for duplicate/gap checks and FPS estimation.

## 3. Landmark Columns

Example:

```text
left_knee_x
left_knee_y
left_knee_z
left_knee_visibility
```

Visibility is recommended because monocular pose engines often return low-quality
landmarks rather than missing landmarks. ④ Preprocessing and later reliability
gates use visibility metadata when available.

## 4. CSV Example

```text
frame,timestamp,nose_x,nose_y,nose_z,nose_visibility,left_shoulder_x,...
0,0.000,0.51,0.23,-0.12,0.98,0.42,...
1,0.033,0.52,0.24,-0.13,0.97,0.43,...
```

Sample file:

```text
data/pose/sample/mediapipe_squat_synthetic.csv
```

## 5. Coordinate And Unit Policy

Input coordinates remain in the pose engine's native coordinate convention until
⑤ Normalization. Downstream features and biomarkers use body-relative units:

```text
torso_length_ratio
degree
dimensionless / dimensionless_cv
second
```

Absolute force, torque, mass, or physical-length outputs are not used.

## 6. Data Locations

```text
data/pose/          joint-point CSV input
data/definitions/   exercise definitions and interpretation YAML
data/protocols/     performance and camera protocol YAML
data/reference/     reference statistics
data/processed/     pipeline outputs; gitignored
```

Raw videos are not analysis inputs for this repository. Shareable inputs are
de-identified joint-point CSVs.
