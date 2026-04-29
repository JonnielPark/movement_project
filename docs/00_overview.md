# Movement Analysis Framework Overview

## Goal

This project aims to develop an interpretable movement quality analysis framework using monocular 3D pose landmark data.

The framework is designed to quantify movement quality using spatial, temporal, control-related, and biomechanical proxy features.

## Target Exercises

The initial target exercises are:

- Squat
- Lunge
- Pike push-up
- Plank shoulder tap

These movements were selected to cover lower-limb support, left-right compensation, upper-body strength, and core stability.

## Pipeline

```text
Pose CSV
+ optional annotation file
-> Validation
-> Preprocessing
-> Normalization
-> Annotation Mask Application
-> Feature Extraction
-> Biomechanical Proxy Modeling
-> Scoring
-> Visualization / Report
```

## Current Scope

Current development focuses on:

- pose data loading
- data validation
- 3D skeleton visualization
- coordinate normalization
- annotation-based frame selection design

The following components are planned but not yet implemented:

- preprocessing options
- annotation mask application
- feature extraction
- biomechanical proxy modeling
- scoring
- simulation-based robustness evaluation

## Design Principle

Each module should have a clearly separated responsibility.

```text
validation      -> diagnose data quality
preprocessing   -> correct noise and missing values
normalization   -> convert coordinates into comparable body-relative space
annotation      -> mark frames or repetitions for analysis
features        -> compute measurable movement indicators
biomechanics    -> estimate interpretable biomechanical proxies
scoring         -> convert indicators into movement quality scores
visualization   -> inspect pose data and analysis results
```

## Annotation Strategy

Automatic segmentation is not treated as the primary contribution in the initial implementation.

Instead, manually prepared annotation files can be used to mark frames or repetitions for analysis. If no annotation is provided, the pipeline uses the full sequence by default.

Details are described in [Annotation and Segmentation](04_annotation_and_segmentation.md).

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

These features are planned but not fully implemented yet.

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
normalization report
annotation report
feature table
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

next:
- annotation mask application
- pipeline runner with on/off module config
- preprocessing options
- feature extraction

later:
- biomechanical proxy modeling
- scoring
- synthetic abnormal movement generation
- ROM restriction simulation
- visual noise / occlusion simulation
- robustness evaluation
```
