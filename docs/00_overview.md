# 00. Overview

This document describes the overall design of the analysis pipeline.
For terminology definitions see [`docs/_terminology.md`](_terminology.md).

---

## 1. Core Design: Exercise Definitions as YAML Objects

Instead of writing per-exercise analysis code, each exercise is described as a YAML object
(`data/exercise_definitions/<exercise_id>.yaml`). All pipeline steps consume the same
`ExerciseDefinition` object; exercise-specific behavior comes from the YAML fields, not from
code branches.

```
Before : separate analysis code per exercise (squat, lunge, …)
After  : one YAML file per exercise, same pipeline steps for all exercises
```

Fields defined in the exercise YAML:

```text
classification        laterality, primary_plane, movement_chain, posture_type
landmarks             primary_joints, critical_landmarks, bilateral_pairs, base_of_support
phases                phase model (e.g., eccentric / concentric)
compensation_candidates  movement patterns to monitor
feature_domains       which spatial / temporal / control features to activate
biomechanical_focus   which proxy metrics to compute
quality_rules         visibility threshold, max interpolation gap, …
```

A generic fallback definition (`generic.yaml`) is loaded when no exercise-specific YAML
is found.

---

## 2. Pipeline Steps

```text
Input
    Pose CSV           monocular 3D pose time series
    Annotation file    (optional) segment and rep labels
    Exercise YAML      exercise definition

Steps
    ① Validation           structural integrity check — does not modify data
    ② Annotation           merge segment / rep metadata from annotation file
    ③ Exercise Definition  load ExerciseDefinition object (generic fallback if not found)
    ④ Preprocessing        reliability detection, swap correction, interpolation, smoothing
    ⑤ Normalization        hip-center translation + median torso-length scale
    ⑥ Motion Attribution   per-rep active-side consistency check
    ⑦ Feature Extraction   spatial / temporal / control features
    ⑧ Biomech Proxy        CoM, moment arms, anthropometry (Winter 1990)
    ⑨ Biomarker Derivation BiomarkerRecord with source_fields provenance
    ⑩ Visualization        called outside the ①–⑨ runner; diagnostic and result charts

Output
    Per-step dataframes (columns accumulate)
    Per-step report dicts
    Feature table (with provenance)
    Biomechanical proxy metric table
    Biomarker summary
    Visualization figures
```

② runs before ③ because the `exercise_type` column in the annotation file identifies
which exercise YAML to load. All steps from ③ onward reference the same definition object.

---

## 3. Stage Responsibility Table

| Step | Does | Does NOT |
|---|---|---|
| ① Validation | integrity diagnostics | modify data |
| ② Annotation | add frame-level metadata columns | modify coordinates |
| ③ Exercise Definition | load ExerciseDefinition object | modify annotation or coordinates |
| ④ Preprocessing | correct data quality issues | alter movement quality patterns |
| ⑤ Normalization | translate + scale to body-relative coords | branch per exercise type |
| ⑥ Motion Attribution | flag per-rep active-side consistency | modify coordinates or scores |
| ⑦ Feature Extraction | compute spatial / temporal / control features | correct labels |
| ⑧ Biomech Proxy | compute CoM, moment arms, relative load distribution | compute absolute torques |
| ⑨ Biomarker Derivation | produce BiomarkerRecord with provenance | emit records without source_fields |
| ⑩ Visualization | produce diagnostic and result figures | modify data |

---

## 4. Feature Domains

```text
Spatial
    ROM (range of motion)
    Left/right symmetry
    Trajectory shape

Temporal
    Tempo (execution speed)
    Inter-rep variability

Control
    CoM stability
    Compensation movements
```

Which domains are active for a given exercise is controlled by the `feature_domains` field
in the exercise YAML.

---

## 5. Annotation Strategy

Automatic segmentation is not in scope. Rep boundaries are provided via a pre-prepared
annotation CSV. If no annotation file is supplied, the full sequence is treated as a single
analysis segment.

Key annotation columns that drive downstream steps:

```text
exercise_type      identifies which exercise YAML to load (③)
pattern            bilateral | alternating
starting_side      first active side in alternating exercises (⑥)
```

See [03_annotation_and_segmentation.md](03_annotation_and_segmentation.md).

---

## 6. Normalization Strategy

```text
Translation reference : frame-wise hip center
Scale reference       : sequence-wise median torso length
```

Using the sequence-wise median (rather than per-frame scale) avoids artificial skeleton
jitter caused by per-frame torso length noise in monocular data.

All downstream features and biomarkers are expressed in `torso_length_ratio` units
(dimensionless) or degrees. Absolute force/length units are not used.

See [06_normalization.md](06_normalization.md).

---

## 7. Development Roadmap

```text
2026.03 – 2026.05  Environment setup and pipeline design
  [done]  Pose CSV loading, validation, 3D visualization
  [done]  Coordinate normalization, annotation
  [done]  Exercise definition schema, YAML loader, generic fallback
  [done]  Pipeline runner + preprocessing
  [done]  Motion attribution module (⑥)
  [done]  Module scaffolding for features / biomech / biomarker / simulation

2026.06 – 2026.09  Feature extraction (⑦)
  Spatial: ROM, symmetry, shape
  Temporal: tempo, variability
  Control: stability, compensation
  Visualization: reliability overlay, joint angle time series, step result charts

2026.10 – 2027.01  Biomechanical proxy modeling and biomarker derivation (⑧–⑨)
  CoM and moment arm estimation
  Relative load distribution / compensation metrics
  Digital biomarker derivation with provenance
  Synthetic data generation for robustness simulation

2027.02 – 2027.05  Robustness simulation and evaluation
  Abnormal motion simulation (ROM restriction, noise, occlusion)
  Monotonicity and consistency analysis of biomarker outputs
```
