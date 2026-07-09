# 00. Data Format

**Document Version:** 1.2.1
**Last Updated:** 2026-06-20
**Korean Sync:** `docs/pipeline/00_data_format.md` is the same-version Korean source.

Input specification for monocular 3D pose time-series CSV files.

---

## 1. Input Contract

The current pipeline expects a MediaPipe-style 33-landmark CSV:

```text
one row = one frame
required scalar columns = frame, timestamp
coordinate columns = <landmark>_x, <landmark>_y, <landmark>_z
optional confidence columns = <landmark>_confidence
landmark names = src/movement/core/config.py
```

Other engines are adapters until their export schemas are available. They should
be converted into this schema before entering the current pipeline.

Future pose engines such as YOLOv11 should enter through a pose-backend adapter,
not through exercise-specific special cases. The adapter may map native keypoints
to the pipeline landmark schema, translate native confidence into confidence or
confidence provenance, and record source metadata such as engine name, model
version, coordinate convention, and depth availability. If the engine has no
native depth output, the adapter must not synthesize depth as trusted evidence;
depth-dependent downstream records should instead carry unavailable or
low-confidence provenance until a later scoring policy explicitly supports that
source.

After MediaPipe-based analysis and scoring stabilize, the same exercise
definition can be used to compare MediaPipe and YOLOv11 outputs as an
engineering model-dependence study. The comparison should report how much the
exercise-definition and canonicalization evidence changes availability
availability, confidence, `quality_gravity`, report-local burden/residual
diagnostics, and feature sensitivity for each backend. It must not be framed as
clinical validation or as proof that one pose engine is biomechanically correct.

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
left_knee_confidence
```

confidence is recommended because monocular pose engines often return low-quality
landmarks rather than missing landmarks. ④ Preprocessing and later reliability
gates use confidence metadata when available.

## 4. CSV Example

```text
frame,timestamp,nose_x,nose_y,nose_z,nose_confidence,left_shoulder_x,...
0,0.000,0.51,0.23,-0.12,0.98,0.42,...
1,0.033,0.52,0.24,-0.13,0.97,0.43,...
```

Sample file:

```text
data/pose/sample/mediapipe_squat_synthetic.csv
```

## 5. Participant Profile YAML

Participant information is optional de-identified analysis metadata. It should
not contain direct identifiers such as name, birth date, contact information, or
raw video references.

Recommended location:

```text
data/participants/<scope>/<participant_id>.yaml
```

Minimal schema:

```yaml
participant_profile:
  schema_version: "0.1.0"
  participant_id: p01
  anthropometry:
    sex: male
    height_cm: 175
    height_bin: 171-175cm
  common_subject_skeleton:
    profile_id: male_175cm
    matrix_path: data/reference/anthropometry/common_subject_skeleton_matrix.yaml
    model_path: data/reference/anthropometry/common_subject_skeleton_male_175cm.yaml
  policy:
    deidentified: true
    used_for_scoring: false
```

At the current stage, participant YAML is provenance and review input only.
Height is not used to rescale pose coordinates into cm/m, and the common-subject
skeleton is not a subject-specific body reconstruction.

## 6. Coordinate And Unit Policy

Input coordinates remain in the pose engine's native coordinate convention until
⑤ Normalization. Downstream features and biomarkers use body-relative units:

```text
torso_length_ratio
degree
dimensionless / dimensionless_cv
second
```

Absolute force, torque, mass, or physical-length outputs are not used.

## 7. Data Locations

```text
data/pose/          joint-point CSV input
data/participants/  optional de-identified participant profile YAML
data/definitions/   exercise definitions and interpretation YAML
data/protocols/     performance and camera protocol YAML
data/reference/     reference statistics
data/processed/     pipeline outputs; gitignored
```

Raw videos are not analysis inputs for this repository. Shareable inputs are
de-identified joint-point CSVs.
