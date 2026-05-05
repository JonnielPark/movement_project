# 00. Overview

**Document Version:** 1.0.0  
**Last Updated:** 2026-05-06  
**Versioning Rule:** Semantic Versioning 2.0.0 (`MAJOR.MINOR.PATCH`)  
**Korean Sync:** `docs/00_overview.md` is the same-version Korean source.

This document describes the overall design of the analysis pipeline.
For terminology definitions see [`_terminology.md`](_terminology.md).

---

## 0. Document Versioning

All documents start version notation at `1.0.0` as of 2026-05-06. The versioning
rule follows the Semantic Versioning 2.0.0 `MAJOR.MINOR.PATCH` format.

```text
MAJOR  incompatible changes to document structure, pipeline step definitions, or public API meaning
MINOR  new features, sections, or deliverables added while preserving existing meaning
PATCH  typos, translation, links, or wording clarifications with no meaning change
```

Operating rules:

```text
[Required]
- `docs/` is the Korean source documentation.
- `docs_eng/` is the same-version English translation with the same content.
- `README_eng.md` is only the English translation of `README.md`; it must not diverge.
- `code_revision_plan.md` remains a local execution plan and is excluded from git upload.
- `_terminology.md` will receive the final document-number prefix after development is complete.
```

Document index for this folder:

| Version | File | Content | Korean Source |
|---|---|---|---|
| 1.0.0 | [_terminology.md](_terminology.md) | Terminology | [docs/_terminology.md](../docs/_terminology.md) |
| 1.0.0 | [00_overview.md](00_overview.md) | Overall pipeline overview | [docs/00_overview.md](../docs/00_overview.md) |
| 1.0.0 | [01_data_format.md](01_data_format.md) | Input CSV data format | [docs/01_data_format.md](../docs/01_data_format.md) |
| 1.0.0 | [02_validation.md](02_validation.md) | ① Validation | [docs/02_validation.md](../docs/02_validation.md) |
| 1.0.0 | [03_annotation_and_segmentation.md](03_annotation_and_segmentation.md) | ② Annotation · ⑥ Phase Segmentation | [docs/03_annotation_and_segmentation.md](../docs/03_annotation_and_segmentation.md) |
| 1.0.0 | [04_exercise_definition.md](04_exercise_definition.md) | ③ Exercise Definition YAML | [docs/04_exercise_definition.md](../docs/04_exercise_definition.md) |
| 1.0.0 | [05_preprocessing.md](05_preprocessing.md) | ④ Preprocessing | [docs/05_preprocessing.md](../docs/05_preprocessing.md) |
| 1.0.0 | [06_normalization.md](06_normalization.md) | ⑤ Normalization | [docs/06_normalization.md](../docs/06_normalization.md) |
| 1.0.0 | [07_motion_attribution.md](07_motion_attribution.md) | ⑦ Motion Attribution | [docs/07_motion_attribution.md](../docs/07_motion_attribution.md) |
| 1.0.0 | [08_feature_extraction.md](08_feature_extraction.md) | ⑧ Feature Extraction | [docs/08_feature_extraction.md](../docs/08_feature_extraction.md) |
| 1.0.0 | [09_biomechanical_proxy.md](09_biomechanical_proxy.md) | ⑨ Biomech Proxy | [docs/09_biomechanical_proxy.md](../docs/09_biomechanical_proxy.md) |
| 1.0.0 | [10_biomarker_scoring.md](10_biomarker_scoring.md) | ⑩ Biomarker Scoring | [docs/10_biomarker_scoring.md](../docs/10_biomarker_scoring.md) |
| 1.0.0 | [11_visualization.md](11_visualization.md) | ⑪ Visualization | [docs/11_visualization.md](../docs/11_visualization.md) |
| 1.0.0 | [12_insilico_simulation.md](12_insilico_simulation.md) | ⑫ In-silico Simulation | [docs/12_insilico_simulation.md](../docs/12_insilico_simulation.md) |

`code_revision_plan.md` is version-managed locally but excluded from git upload.

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
    ①  Validation           structural integrity check — does not modify data
    ②  Annotation           merge segment / rep metadata from annotation file
    ③  Exercise Definition  load ExerciseDefinition object (generic fallback if not found)
    ④  Preprocessing        reliability detection, swap correction, interpolation, smoothing
    ⑤  Normalization        hip-center translation + median torso-length scale
    ⑥  Phase Segmentation  semi-automatic intra-rep kinematic phase splitting (Descent/Ascent/…)
    ⑦  Motion Attribution   per-rep active-side consistency check
    ⑧  Feature Extraction   spatial / temporal / control features (rep-level + phase-level)
    ⑨  Biomech Proxy        CoM, moment arms, anthropometry (Winter 1990)
    ⑩  Biomarker Derivation BiomarkerRecord (individual metrics) + BiomarkerScoreRecord (per-rep composite)
    ⑪  Visualization        called outside the ①–⑩ runner; diagnostic and result charts
    ⑫  Simulation           robustness simulation, called outside the runner

Output
    Per-step dataframes (columns accumulate)
    Per-step report dicts
    phase column        — 'Descent' | 'Ascent' | 'Bottom_Hold' | 'Lift' | 'Tap' | 'Return' | NA
    Feature table       — FeatureRecord list, rep-level (phase=None) + phase-level (phase=str)
    Phase summary       — summarize_phase_to_rep() hierarchical aggregates (e.g., Descent/Ascent ROM ratio)
    Biomechanical proxy table — BiomechRecord list, rep-level, visibility-weighted
    Biomarker record list — BiomarkerRecord (individual metric pass-through)
    Biomarker score list — BiomarkerScoreRecord (per-rep Z-score composite, 0–100)
    Interpretation record list — InterpretationRecord (YAML-rule narrative labels per rep)
    Phase segmentation report — PhaseSegmentationReport list, one per rep
    Visualization figures
```

② runs before ③ because the `exercise_type` column in the annotation file identifies
which exercise YAML to load. All steps from ③ onward reference the same definition object.

---

## 3. Stage Responsibility Table

| Step | Does | Does NOT |
|---|---|---|
| ① Validation | integrity diagnostics | modify data |
| ② Annotation | add frame-level metadata columns; pre-fills `phase` as NA | modify coordinates |
| ③ Exercise Definition | load ExerciseDefinition object | modify annotation or coordinates |
| ④ Preprocessing | correct data quality issues | alter movement quality patterns |
| ⑤ Normalization | translate + scale to body-relative coords | branch per exercise type |
| ⑥ Phase Segmentation | populate `phase` column for rep frames (kinematic labels) | overwrite existing non-NA phase values; modify coordinates |
| ⑦ Motion Attribution | flag per-rep active-side consistency | modify coordinates or scores |
| ⑧ Feature Extraction | compute rep-level and phase-level spatial / temporal / control features | correct labels |
| ⑨ Biomech Proxy | compute CoM, moment arms, relative load distribution | compute absolute torques |
| ⑩ Biomarker Derivation | produce BiomarkerRecord + BiomarkerScoreRecord with provenance | emit records without source_fields |
| ⑪ Visualization | produce diagnostic and result figures | modify data |

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

Automatic segmentation is not in scope. Rep boundaries are provided via a pre-prepared
annotation CSV. If no annotation file is supplied, the full sequence is treated as a single
analysis segment.

Key annotation columns that drive downstream steps:

```text
exercise_type      identifies which exercise YAML to load (③)
pattern            bilateral | alternating
starting_side      first active side in alternating exercises (⑦)
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
  [done]  Phase segmentation (⑥) — segment_phases() with SG smoothing + find_peaks, wired into pipeline
  [done]  Exercise YAMLs updated with phase_segmentation blocks (v0.2.0); PhaseSegmentationSpec parsed
  [done]  FeatureRecord.phase field; extract_rep_features() emits rep-level + phase-level records
  [done]  summarize_phase_to_rep() hierarchical aggregator (Descent/Ascent ROM ratio)
  [done]  Load-shift OLS — compute_load_shift() in biomech/load_shift.py; metric biomech.load_shift.<joint>.<side>.slope (torso_length_ratio_per_rep); requires ≥ 3 reps; test_biomech_load_shift.py (17 tests)
  [done] 
