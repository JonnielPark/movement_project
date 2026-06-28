# Overview

**Document Version:** 1.4.38
**Last Updated:** 2026-06-27
**Korean Sync:** [docs/overview.md](../docs/overview.md) is the matching Korean document.

This document describes the overall design of the analysis pipeline.
For terminology definitions see [`terminology.md`](terminology.md).

---

## Document Index

| Version | File | Content |
|---|---|---|
| 1.6.2 | [terminology.md](terminology.md) | Study-specific terms and clinical language principles |
| 1.4.38 | [overview.md](overview.md) | Overall pipeline overview |
| 1.4.0 | [practical_protocols/camera_protocol.md](practical_protocols/camera_protocol.md) | Camera filming protocol per exercise |
| 1.1.0 | [practical_protocols/exercise_performance_protocol.md](practical_protocols/exercise_performance_protocol.md) | Exercise performance protocol per exercise |
| 0.2.22 | [practical_protocols/exercise_authoring_notebook.md](practical_protocols/exercise_authoring_notebook.md) | Notebook-first exercise authoring and YAML generation plan |
| 1.1.0 | [clinical/exercises/README.md](clinical/exercises/README.md) | Per-exercise clinical rationale documents |
| 1.1.0 | [00_data_format.md](pipeline/00_data_format.md) | Input CSV data format |
| 1.1.0 | [01_validation.md](pipeline/01_validation.md) | ① Validation |
| 1.2.0 | [02_annotation.md](pipeline/02_annotation.md) | ② Annotation |
| 1.6.1 | [03_exercise_definition.md](pipeline/03_exercise_definition.md) | ③ Exercise Definition YAML |
| 1.2.0 | [04_preprocessing.md](pipeline/04_preprocessing.md) | ④ Preprocessing |
| 2.0.0 | [05_normalization.md](pipeline/05_normalization.md) | ⑤ Normalization |
| 2.0.0 | [06_canonicalization.md](pipeline/06_canonicalization.md) | ⑥ Canonicalization |
| 1.3.0 | [07_segmentation.md](pipeline/07_segmentation.md) | ⑦ Segmentation |
| 1.2.4 | [08_feature_extraction.md](pipeline/08_feature_extraction.md) | ⑧ Feature Extraction |
| 1.2.0 | [09_biomechanical_proxy.md](pipeline/09_biomechanical_proxy.md) | ⑨ Biomech Proxy |
| 1.2.0 | [10_biomarker_scoring.md](pipeline/10_biomarker_scoring.md) | ⑩ Biomarker Scoring |
| 1.1.0 | [11_visualization.md](pipeline/11_visualization.md) | ⑪ Visualization |
| 1.1.0 | [12_insilico_simulation.md](pipeline/12_insilico_simulation.md) | ⑫ In-silico Simulation |

---

## Analytical Scope and Interpretation Principle

This study takes monocular 3D pose time series as input and tracks joint-center and
body-segment motion over time. The input consists of pose CSV files, optional
annotation, recording metadata, and exercise-definition YAML; these data are shared
through the same `ExerciseDefinition` object and per-stage reports across the
pipeline.

The analytical principle is not to reconstruct absolute force or absolute torque,
but to derive body-scale-normalized joint angles, segment trajectories, left/right
symmetry, CoM stability, moment-arm proxies, relative load-shift tendencies, and
compensatory movement candidates at the rep and phase levels. This converts
movements observable in a monocular-camera setting into biomechanically interpretable
features and digital biomarkers.

The outputs therefore include rep-level and phase-level feature tables,
biomechanical-proxy tables, biomarker scores, interpretation-rule narrative labels,
and provenance-aware reports and figures. These outputs provide structured
quantitative information for reviewing movement quality, left/right consistency,
relative load distribution, and compensatory strategies.

Muscle-recruitment interpretation is kept within this joint-/segment-level
principle. Joint angle, stance, external load, movement speed, and individual anatomy
can change muscle moment arms and recruitment strategies; therefore, active side,
relative load shift, moment-arm proxy, and compensatory movement are treated as
interpretable tendencies derived from observable motion, not direct evidence of
activation in a specific muscle.

The current priority scope is structured in-place bodyweight exercise. Squat, lunge,
pike push-up, and plank shoulder tap are suitable for comparing rep-level
joint-/segment-level motion from monocular 3D pose without equipment tracking or
large spatial travel. In contrast, equipment-based exercises with dumbbells, bands,
or barbells would require additional records for equipment position, external load
metadata, hand-equipment contact, and resistance direction. Highly dynamic or
spatially traveling tasks such as jumping, running, or change-of-direction movements
would require ground-contact events, flight phases, global travel paths, tracking
continuity, more complex event segmentation, and expanded camera protocols. The
current results should therefore be interpreted as engineering feasibility and
robustness evidence within this scope.

---

## 1. Core Design: Exercise Definitions as YAML Objects

Each exercise is loaded from an `ExerciseContext` assembled by `exercise_id`. The
current target exercises use split YAML artifacts: the exercise definition keeps
movement identity, while analysis, performance, and camera settings live in
separate files. The loader still supports legacy combined exercise YAML for
backward compatibility and returns the same `ExerciseDefinition` object to
downstream pipeline stages. See
[exercise_authoring_notebook.md](practical_protocols/exercise_authoring_notebook.md).

Fields defined across the split YAML artifacts:

```text
data/definitions/exercises/<exercise_id>.yaml
classification        laterality, primary_plane, movement_chain, posture_type
phases                phase model (e.g., eccentric / concentric)

data/definitions/analysis_profiles/<exercise_id>.yaml
landmarks             primary_joints, critical_landmarks, bilateral_pairs
rep_segmentation      repetition-boundary detection settings
phase_segmentation    intra-rep phase detection settings
compensation_candidates  movement patterns to monitor
feature_domains       which spatial / temporal / control features to activate
biomechanical_focus   which proxy metrics to compute
quality_rules         visibility threshold, max interpolation gap, …

data/protocols/performance/<exercise_id>.yaml
performance_protocol  participant-facing count and side-sequence rules

data/protocols/camera/<exercise_id>.yaml
camera_protocol       recommended filming zone/height and warning policy
view_metric_reliability  per-zone metric-family reliability prior
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
    ⑥  Canonicalization     optional analysis-space candidate coordinates (raw/norm preserved)
    ⑦  Segmentation         semi-automatic rep/phase splitting from joint-motion tracking
    ⑧  Feature Extraction   side-role context resolution + spatial / temporal / control features + audit reports
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
    Feature audit reports — feature-registry coverage + compensation availability + analysis-disrupting pattern detectability
    Phase summary       — summarize_phase_to_rep() hierarchical aggregates (e.g., Descent/Ascent ROM ratio)
    Biomechanical proxy table — BiomechRecord list, rep-level, visibility-weighted
    Biomarker record list — BiomarkerRecord (individual metric pass-through)
    Biomarker score list — BiomarkerScoreRecord (per-rep Z-score composite, default 0–100 configurable scale)
    Interpretation record list — InterpretationRecord (YAML-rule narrative labels per rep)
    Performance provenance report — actual_rep_count / failure-point metadata for confidence notes
    Canonicalization report — optional coordinate-alignment priors, correction magnitude, confidence notes
    Segmentation report — SegmentationReport list, one per rep
    Segmentation failure point records — SegmentationFailurePoint list for frames/ranges needing manual intervention
    Visualization figures
```

---

## 3. Stage Processing and Outputs

| Step | Input / Reference Information | Main Processing | Output |
|---|---|---|---|
| ① Validation | Pose CSV | Checks required columns, frame order, timestamps, landmark coordinate structure, and missing-value patterns. | Validation report |
| ② Annotation | Pose DataFrame, Annotation CSV, optional recording metadata | Merges manual annotation information at frame level and constructs `exercise_id`, `execution_pattern`, `starting_side`, the initial `phase`, filming provenance columns, and performance/failure provenance summaries. | Annotated DataFrame, annotation report |
| ③ Exercise Definition | `exercise_id`, split YAML artifacts or legacy combined YAML | Loads an `ExerciseContext` and returns a backward-compatible `ExerciseDefinition`; applies `generic.yaml` when no specific definition is available. `camera_protocol` is retained as metadata for filming recommendations and warning policy. | ExerciseContext, ExerciseDefinition, camera protocol metadata |
| ④ Preprocessing | Pose DataFrame, `quality_rules` | Checks confidence columns and corrects left/right swap candidates, missing values, short gaps, and abrupt coordinate changes; applies smoothing when needed. | Preprocessed DataFrame, preprocessing report |
| ⑤ Normalization | Preprocessed DataFrame | Translates coordinates relative to the hip center and scales them by the sequence-level median torso length. | Normalized DataFrame |
| ⑥ Canonicalization | Normalized DataFrame, exercise/camera/support priors | Optionally emits analysis-space candidate coordinate families using support-plane, movement-plane, protocol-height, or anthropometric priors. Raw/norm/candidate coordinate families remain separate and every candidate is reported with confidence, burden, residual, and sensitivity provenance. | Optional candidate coordinate columns, canonicalization report, correction diagnostics |
| ⑦ Segmentation | Normalized DataFrame, `rep_segmentation`, `phase_segmentation` | Derives repetition boundaries from joint motion and labels phases inside each repetition. Uncertain ranges are recorded as failure points, and manual intervention results are incorporated. | `rep_id`, `phase`, SegmentationReport, SegmentationFailurePoint |
| ⑧ Feature Extraction | Segmented DataFrame, `feature_domains`, `performance_protocol.analysis_disrupting_patterns`, side-role settings | Resolves side-role context inside feature extraction, then computes rep-level and phase-level ROM, symmetry, trajectory, tempo, variability, and compensation features; reports feature-registry coverage, compensation-candidate availability, and analysis-disrupting pattern detectability. | FeatureRecord list, feature DataFrame, feature-role-context report, audit reports |
| ⑨ Biomech Proxy | Normalized/featured DataFrame, `biomechanical_focus` | Computes relative biomechanical indicators such as CoM trajectory, moment-arm proxies, and load shift. | BiomechRecord list |
| ⑩ Biomarker Derivation | FeatureRecord, BiomechRecord, baseline | Converts individual metrics into BiomarkerRecord entries and derives Z-score-based domain scores and composite scores. Coordinate-correction magnitude and observation quality are interpreted separately from the movement-quality score as data-confidence/provenance information. | BiomarkerRecord, BiomarkerScoreRecord, InterpretationRecord |
| ⑪ Visualization | Per-step DataFrames, records, reports | Visualizes confidence, joint angles, phases, features, and biomarker results as diagnostic and result charts. | figures |
| ⑫ Simulation | Normal or reference sequence, injector settings | Injects conditions such as noise, occlusion, ROM restriction, and velocity spikes, then evaluates metric responsiveness. | synthetic dataset, robustness report |

---

## 4. Active Feature Families

Detailed formulas live in the step documents. At the overview level, the active
families are:

```text
Spatial            ROM, left/right symmetry, trajectory shape, compensation candidates
Temporal           tempo and inter-rep variability
Control            CoM stability, path consistency, smoothness, provenance gates
Biomech proxy      CoM trajectory, moment-arm proxies, relative load-shift tendency
Biomarker output   per-metric records, Z-score domain/composite scores, rule labels
```

Feature availability and observation reliability are kept separate from movement
quality. A low-confidence view, low visibility, or model-depth limitation should
surface as provenance or withholding logic rather than an automatic movement-quality
penalty.

---

## 5. Core Operating Rules

- Annotation provides `exercise_id`, execution pattern, side sequence, protocol
  grouping, and recording provenance. See
  [02_annotation.md](pipeline/02_annotation.md).
- Segmentation emits confirmed `rep_id` and `phase` labels. Failure points require
  manual confirmation before affected ranges drive rep-level or phase-level metrics.
  See [07_segmentation.md](pipeline/07_segmentation.md).
- Normalization uses frame-wise hip-center translation and sequence-wise median
  torso-length scaling. Downstream values remain dimensionless
  `torso_length_ratio` units or degrees; absolute force/length units are not used.
  See [05_normalization.md](pipeline/05_normalization.md).
- Optional canonicalization preserves raw/norm coordinates and emits separate
  candidate coordinates plus confidence/correction reports. It must not fit the
  pose to a good-movement template or erase true compensation patterns.
  See [06_canonicalization.md](pipeline/06_canonicalization.md).

---

## 6. Current Development Status

```text
Implemented
    ①-⑩ pipeline runner, split exercise YAML loading, annotation, preprocessing,
    normalization, canonicalization candidate reports, segmentation, feature-side-role context, features, biomech proxies,
    biomarker scoring, interpretation rules, and synthetic-normal baseline.

Review-only / disabled by default
    canonicalization priors, including support-plane, movement-plane, and
    protocol-height lateral-width review. Downstream stages still use norm
    coordinates unless later notebook and robustness evidence justify promotion.

Partial
    far-side landmark stabilization, simulation injectors, and visualization
    scaffolding. Visualization stubs are intentionally retained until ⑪ begins.

Next design gate
    Stage A anthropometric skeleton prior for depth plausibility using Size Korea
    8th 3D full-body automatic aggregate ratios as a loose engineering envelope.
    It must remain confidence/provenance support, not calibrated 3D
    reconstruction or empirical P5/P95 prior.

Out of current scope
    calibrated camera reprojection, Kalman filtering, full dashboard, Phantom 3D,
    absolute torque/force estimation, and real patient-group validation.
```

Detailed task ordering lives in
[`code_revision_plan.md`](code_revision_plan.md), which is a local execution-plan
document and not a publication-facing overview.
