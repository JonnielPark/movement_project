# Movement Analysis Framework Overview

## Goal

This project aims to develop an interpretable movement quality analysis framework using monocular 3D pose landmark data.

The framework is designed to quantify movement quality using spatial, temporal, control-related, and biomechanical proxy features.

Movement quality is not assessed against a fixed list of exercises. Each exercise is described as a **biomechanical property object** (an exercise definition), and the framework derives interpretable biomarkers from those properties. This shifts the unit of analysis from "the exercise" to "the property profile of the exercise," and is what makes biomarker output traceable.

## Validation Exercises

The following exercises form the initial validation set used during framework development:

- Squat
- Lunge
- Pike push-up
- Plank shoulder tap

These movements were selected to cover lower-limb support, left-right compensation, upper-body strength, and core stability. They are not the unit of analysis. Each is defined as a property object under [Exercise Definition](04_exercise_definition.md), and the framework treats them as four sample points in the schema's property space.

## Pipeline

```text
Pose CSV
+ optional annotation file
+ exercise definition (YAML)
-> Validation
-> Annotation Mask Application
-> Exercise Definition Loading
-> Preprocessing
-> Normalization
-> Motion Attribution
-> Feature Extraction
-> Biomechanical Proxy Modeling
-> Scoring
-> Visualization / Report
```

Annotation runs early so that exercise context (`exercise_type`, expected movement pattern, starting side) and rep boundaries are available to all downstream modules.

The exercise definition is loaded immediately after annotation, using `exercise_type` to select the YAML file. The loaded definition object is passed to every downstream module so that they can apply exercise-specific rules without re-reading annotation metadata.

Preprocessing and normalization can then apply exercise-aware logic without re-loading annotation metadata.

## Current Scope

Current development focuses on:

- pose data loading
- data validation
- 3D skeleton visualization
- coordinate normalization
- annotation-based frame selection design
- exercise definition schema and field dictionary

The following components are planned but not yet implemented:

- preprocessing options
- annotation mask application
- exercise definition loader and validator
- definition authoring notebook (dropdown-based) and annotation interpretation export
- motion attribution
- feature extraction
- biomechanical proxy modeling
- scoring
- simulation-based robustness evaluation

## Design Principle

Each module should have a clearly separated responsibility.

```text
validation         -> diagnose data quality
annotation         -> mark frames, reps, and declare exercise context
exercise_definition -> declare semantic and biomechanical structure as data
preprocessing      -> handle low-reliability landmarks and frame-level noise
normalization      -> convert coordinates into comparable body-relative space
motion attribution -> verify exercise-level active-limb labeling per rep
features           -> compute measurable movement indicators
biomechanics       -> estimate interpretable biomechanical proxies
scoring            -> convert indicators into movement quality scores
visualization      -> inspect pose data and analysis results
```

A second cross-cutting principle is that exercise-specific information must live in YAML, not in code. This is what allows the biomarker set to be derived from declared properties and to remain interpretable per exercise.

## Annotation Strategy

Automatic segmentation is not treated as the primary contribution in the initial implementation.

Instead, manually prepared annotation files can be used to mark frames or repetitions for analysis. If no annotation is provided, the pipeline uses the full sequence by default.

The annotation file also declares exercise-level context such as `exercise_type`, expected movement pattern, and starting side. The exercise definition layer reads `exercise_type` to load the corresponding property object, which is then consumed by preprocessing, motion attribution, and feature extraction.

Details are described in [Annotation and Segmentation](03_annotation_and_segmentation.md) and [Exercise Definition](04_exercise_definition.md).

## Coordinate Strategy

The initial coordinate normalization method uses:

```text
translation reference: frame-wise hip center
scale reference:       sequence-wise median torso length
```

This reduces global position offsets and scale differences while avoiding frame-wise scale jitter.

The normalization step is not intended to estimate physical force or absolute body dimensions. Later biomechanical modules may use segment-length estimation and anthropometric assumptions for COM and moment-arm-based proxy indicators.

## Planned Feature Domains

The final framework is expected to quantify movement quality using multiple feature domains.

```text
spatial:
- ROM
- shape
- symmetry

temporal:
- tempo
- variability

control:
- stability
- compensation
```

Which feature domains are activated for a given recording is determined by the loaded exercise definition (`feature_domains` field). See [Exercise Definition](04_exercise_definition.md) for the property → biomarker mapping.

## Simulation-Based Validation Plan

The later validation stage will evaluate engineering robustness using simulated abnormal or noisy conditions.

Planned simulation scenarios include:

- artificial ROM restriction
- visual noise injection
- landmark occlusion or dropout
- pose estimation instability

This stage is planned for later development and is not implemented yet.

## Expected Output

The pipeline should eventually return:

```text
processed dataframe
validation report
annotation report
exercise definition load report
preprocessing report
normalization report
motion attribution report
feature table (with biomarker provenance: source definition fields)
biomechanical proxy table
scoring summary
visualization artifacts
```

## Development Roadmap

```text
completed:
- package structure
- CSV loading
- validation
- 3D visualization
- basic coordinate normalization
- annotation mask application
- exercise definition schema and field dictionary

next:
- exercise definition YAML loader and validator
- generic-fallback definition for missing exercise_type
- preprocessing with reliability filtering
- exercise-aware frame-level swap detection
- pipeline runner with reordered step sequence
- short-gap interpolation tied to reliability mask
- motion attribution (rep-level active limb verification)
- definition authoring notebook (dropdown-based) and annotation interpretation export

later:
- feature extraction (driven by feature_domains in the definition)
- biomechanical proxy modeling (driven by biomechanical_focus)
- compensation biomarkers (driven by compensation_candidates)
- biomarker provenance carried into scoring and visualization
- scoring
- synthetic abnormal movement generation
- ROM restriction simulation
- visual noise / occlusion simulation
- robustness evaluation
```
