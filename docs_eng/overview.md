# Overview

**Document Version:** 1.4.8
**Last Updated:** 2026-05-10
**Korean Sync:** [docs/overview.md](../docs/overview.md) is the matching Korean document.

This document describes the overall design of the analysis pipeline.
For terminology definitions see [`terminology.md`](terminology.md).

---

## Document Index

| Version | File | Content |
|---|---|---|
| 1.4.3 | [terminology.md](terminology.md) | Study-specific terms and clinical language principles |
| 1.4.7 | [overview.md](overview.md) | Overall pipeline overview |
| 1.2.3 | [practical_protocols/camera_protocol.md](practical_protocols/camera_protocol.md) | Camera filming protocol per exercise |
| 1.0.8 | [practical_protocols/exercise_performance_protocol.md](practical_protocols/exercise_performance_protocol.md) | Exercise performance protocol per exercise |
| 1.0.1 | [clinical/exercises/README.md](clinical/exercises/README.md) | Per-exercise clinical rationale documents |
| 1.0.1 | [00_data_format.md](pipeline/00_data_format.md) | Input CSV data format |
| 1.0.0 | [01_validation.md](pipeline/01_validation.md) | ① Validation |
| 1.1.3 | [02_annotation.md](pipeline/02_annotation.md) | ② Annotation |
| 1.4.8 | [03_exercise_definition.md](pipeline/03_exercise_definition.md) | ③ Exercise Definition YAML |
| 1.0.0 | [04_preprocessing.md](pipeline/04_preprocessing.md) | ④ Preprocessing |
| 1.0.0 | [05_normalization.md](pipeline/05_normalization.md) | ⑤ Normalization |
| 1.2.0 | [06_segmentation.md](pipeline/06_segmentation.md) | ⑥ Segmentation |
| 1.0.1 | [07_motion_attribution.md](pipeline/07_motion_attribution.md) | ⑦ Motion Attribution |
| 1.0.1 | [08_feature_extraction.md](pipeline/08_feature_extraction.md) | ⑧ Feature Extraction |
| 1.0.0 | [09_biomechanical_proxy.md](pipeline/09_biomechanical_proxy.md) | ⑨ Biomech Proxy |
| 1.0.0 | [10_biomarker_scoring.md](pipeline/10_biomarker_scoring.md) | ⑩ Biomarker Scoring |
| 1.0.1 | [11_visualization.md](pipeline/11_visualization.md) | ⑪ Visualization |
| 1.0.0 | [12_insilico_simulation.md](pipeline/12_insilico_simulation.md) | ⑫ In-silico Simulation |

---

## 1. Core Design: Exercise Definitions as YAML Objects

Each exercise is described as a YAML object in
`data/definitions/exercises/<exercise_id>.yaml`. All pipeline steps consume the same
`ExerciseDefinition` object, and exercise-specific behavior is determined by YAML fields.

Fields defined in the exercise YAML:

```text
classification        laterality, primary_plane, movement_chain, posture_type
landmarks             primary_joints, critical_landmarks, bilateral_pairs, base_of_support
phases                phase model (e.g., eccentric / concentric)
rep_segmentation      repetition-boundary detection settings
phase_segmentation    intra-rep phase detection settings
performance_protocol  participant-facing count and side-sequence rules
camera_protocol       recommended filming zone/height and warning policy
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
    Recording metadata (optional) session_id, set_index, camera zone/height
    Exercise YAML      exercise definition

Steps
    ①  Validation           structural integrity check — does not modify data
    ②  Annotation           merge segment / rep metadata from annotation file
    ③  Exercise Definition  load ExerciseDefinition object (generic fallback if not found)
    ④  Preprocessing        reliability detection, swap correction, interpolation, smoothing
    ⑤  Normalization        hip-center translation + median torso-length scale
    ⑥  Segmentation        semi-automatic rep/phase splitting from joint-motion tracking
    ⑦  Motion Attribution   per-rep active-side consistency check
    ⑧  Feature Extraction   spatial / temporal / control features (rep-level + phase-level)
    ⑨  Biomech Proxy        CoM, moment arms, anthropometry (Winter 1990)
    ⑩  Biomarker Derivation BiomarkerRecord (individual metrics) + BiomarkerScoreRecord (per-rep composite)
    ⑪  Visualization        called outside the ①–⑩ runner; diagnostic and result charts
    ⑫  Simulation           robustness simulation, called outside the runner

Output
    Per-step dataframes (columns accumulate)
    Per-step report dicts
    rep_id              — semi-automatically or manually confirmed repetition ID
    phase column        — 'Descent' | 'Ascent' | 'Turnaround_Hold' | 'Lift' | 'Tap' | 'Return' | NA
    Feature table       — FeatureRecord list, rep-level (phase=None) + phase-level (phase=str)
    Phase summary       — summarize_phase_to_rep() hierarchical aggregates (e.g., Descent/Ascent ROM ratio)
    Biomechanical proxy table — BiomechRecord list, rep-level, visibility-weighted
    Biomarker record list — BiomarkerRecord (individual metric pass-through)
    Biomarker score list — BiomarkerScoreRecord (per-rep Z-score composite, 0–100)
    Interpretation record list — InterpretationRecord (YAML-rule narrative labels per rep)
    Segmentation report — SegmentationReport list, one per rep
    Segmentation failure point records — SegmentationFailurePoint list for frames/ranges needing manual intervention
    Visualization figures
```

---

## 3. Stage Processing and Outputs

| Step | Input / Reference Information | Main Processing | Output |
|---|---|---|---|
| ① Validation | Pose CSV | Checks required columns, frame order, timestamps, landmark coordinate structure, and missing-value patterns. | Validation report |
| ② Annotation | Pose DataFrame, Annotation CSV, optional recording metadata | Merges manual annotation information at frame level and constructs `exercise_type`, `pattern`, `starting_side`, the initial `phase`, and filming provenance columns. | Annotated DataFrame |
| ③ Exercise Definition | `exercise_type`, exercise YAML | Loads the exercise-specific YAML to create an `ExerciseDefinition` object; applies `generic.yaml` when no specific definition is available. `camera_protocol` is retained as definition metadata for filming recommendations and warning policy. | ExerciseDefinition, camera protocol metadata |
| ④ Preprocessing | Pose DataFrame, `quality_rules` | Checks confidence columns and corrects left/right swap candidates, missing values, short gaps, and abrupt coordinate changes; applies smoothing when needed. | Preprocessed DataFrame, preprocessing report |
| ⑤ Normalization | Preprocessed DataFrame | Translates coordinates relative to the hip center and scales them by the sequence-level median torso length. | Normalized DataFrame |
| ⑥ Segmentation | Normalized DataFrame, `rep_segmentation`, `phase_segmentation` | Derives repetition boundaries from joint motion and labels phases inside each repetition. Uncertain ranges are recorded as failure points, and manual intervention results are incorporated. | `rep_id`, `phase`, SegmentationReport, SegmentationFailurePoint |
| ⑦ Motion Attribution | Segmented DataFrame, laterality/pattern settings | Estimates the active side per repetition and checks left/right order and primary-side consistency for alternating exercises. | active-side flag, attribution report |
| ⑧ Feature Extraction | Segmented DataFrame, `feature_domains` | Computes rep-level and phase-level ROM, symmetry, trajectory, tempo, variability, and compensation features. | FeatureRecord list, feature DataFrame |
| ⑨ Biomech Proxy | Normalized/featured DataFrame, `biomechanical_focus` | Computes relative biomechanical indicators such as CoM trajectory, moment-arm proxies, and load shift. | BiomechRecord list |
| ⑩ Biomarker Derivation | FeatureRecord, BiomechRecord, baseline | Converts individual metrics into BiomarkerRecord entries and derives Z-score-based domain scores and composite scores. | BiomarkerRecord, BiomarkerScoreRecord, InterpretationRecord |
| ⑪ Visualization | Per-step DataFrames, records, reports | Visualizes confidence, joint angles, phases, features, and biomarker results as diagnostic and result charts. | figures |
| ⑫ Simulation | Normal or reference sequence, injector settings | Injects conditions such as noise, occlusion, ROM restriction, and velocity spikes, then evaluates metric responsiveness. | synthetic dataset, robustness report |

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
    CoM stability (hip-center displacement std)
    Compensation movements — rule-based registry:
        knee_valgus / knee_varus     frontal-plane knee deviation from hip-ankle line
        lateral_pelvic_shift         pelvis center lateral displacement
        excessive_trunk_flexion      trunk lean angle from vertical
        heel_lift                    heel elevation from rep minimum
        pelvis_rotation              left-right hip depth asymmetry (transverse proxy)
```

Which domains are active for a given exercise is controlled by the `feature_domains` field
in the exercise YAML.

---

## 5. Annotation Strategy

② Annotation merges a user-prepared manual annotation CSV into the pose dataframe.
If no annotation file is supplied, the full sequence is treated as a single analysis segment.

Key annotation columns that drive downstream steps:

```text
exercise_type      identifies which exercise YAML to load (③)
pattern            bilateral | alternating
starting_side      first active side in alternating exercises (⑦)
rep_side_sequence  observed side order for protocol/provenance comparison
protocol_cycle_id  groups atomic reps into participant-facing protocol cycles
```

See [02_annotation.md](pipeline/02_annotation.md).

---

## 6. Segmentation Strategy

⑥ Segmentation has two sub-procedures. The new `rep_segmentation` tracks joint motion
to confirm repetition boundaries semi-automatically, and the existing
`phase_segmentation` splits phases such as descent, hold, and ascent inside confirmed
reps. When automatic recognition is unclear, the user intervenes to force rep boundaries
or phase labels.

Segmentation failures are recorded as `SegmentationFailurePoint` entries. Failure levels
are handled as follows.

```text
rep_boundary failure      exclude the affected rep/range from rep-level and phase-level analysis until manual correction
phase_boundary failure    keep rep-level metrics, but do not emit phase-level metrics for that rep
optional_phase failure    skip optional phases such as Turnaround_Hold and continue with coarse phases
```

After manual intervention confirms a boundary, `rep_segmentation_source` or
`phase_segmentation_source` is marked as `manual_override`, and downstream steps use
only confirmed labels. Failure points are never silently interpolated or treated as
successful segmentation.

See [06_segmentation.md](pipeline/06_segmentation.md).

---

## 7. Normalization Strategy

```text
Translation reference : frame-wise hip center
Scale reference       : sequence-wise median torso length
```

Using the sequence-wise median (rather than per-frame scale) avoids artificial skeleton
jitter caused by per-frame torso length noise in monocular data.

All downstream features and biomarkers are expressed in `torso_length_ratio` units
(dimensionless) or degrees. Absolute force/length units are not used.

See [05_normalization.md](pipeline/05_normalization.md).

---

## 8. Development Roadmap

```text
2026.03 – 2026.05  Environment setup and pipeline design
  [done]  Pose CSV loading, validation, 3D visualization
  [done]  Coordinate normalization, annotation
  [done]  Exercise definition schema, YAML loader, generic fallback
  [done]  Pipeline runner + preprocessing
  [done]  Motion attribution module (⑦)
  [done]  Module scaffolding for features / biomech / biomarker / simulation

2026.06 – 2026.09  Feature extraction (⑧)
  [done]  compute_rom() connected to YAML angle_definitions (points + vertex index format)
  [done]  compute_symmetry() — left/right ROM symmetry index per rep
  [done]  compute_shape() — primary joint arc length per rep
  [done]  extract_rep_features() — per-rep spatial / temporal / control feature extraction
  [done]  features_to_dataframe() — FeatureRecord list → DataFrame export
  [done]  pipeline ⑧ connected — extract_rep_features() wired into run_pipeline()
  [done]  Compensation rule engine — COMPENSATION_RULES registry (knee_valgus, knee_varus, lateral_pelvic_shift, excessive_trunk_flexion, heel_lift, pelvis_rotation)
  Visualization: reliability overlay, joint angle time series, step result charts

2026.10 – 2027.01  Biomechanical proxy modeling and biomarker derivation (⑨–⑩)
  [done]  CoM trajectory metrics — rep-level (range_x, range_z, path_length) + visibility weighting
  [done]  Moment arm proxy — knee / hip sagittal plane, rep-level + visibility weighting
  [done]  extract_rep_biomech() orchestrator wired into pipeline ⑨
  [done]  Biomarker record conversion (FeatureRecord / BiomechRecord → BiomarkerRecord)
  [done]  BiomarkerScoreRecord — Z-score deduction, dynamic floor, composite domain score (0–100)
  [done]  derive_biomarkers() entry point wired into pipeline ⑩
  [done]  Synthetic-normal baseline (data/reference/baseline_zscore.json, scripts/compute_baseline.py)
  [in progress]  Segmentation (⑥) — `rep_segmentation` repetition-boundary detection + existing `phase_segmentation` phase splitting; manual intervention on failure
  [planned]  Exercise YAML `phases` definitions connected to semi-automatic phase labels and phase-level features
  [done]  FeatureRecord.phase field; extract_rep_features() emits rep-level + phase-level records
  [done]  summarize_phase_to_rep() hierarchical aggregator (Descent/Ascent ROM ratio)
  [done]  Load-shift OLS — compute_load_shift() in biomech/load_shift.py; metric biomech.load_shift.<joint>.<side>.slope (torso_length_ratio_per_rep); requires ≥ 3 reps; test_biomech_load_shift.py (17 tests)
  [done] 
