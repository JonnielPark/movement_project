# Movement Analysis Framework Overview

## Goal

This project aims to develop an interpretable movement quality analysis framework using monocular 3D pose landmark data.

The framework is designed to quantify movement quality using spatial, temporal, control-related, and biomechanical proxy features.

## Pipeline

```text
Pose CSV
-> Validation
-> Normalization
-> Preprocessing
-> Segmentation
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

## Design Principle

Each module should have a clearly separated responsibility.

```text
validation      -> diagnose data quality
normalization   -> convert coordinates into comparable body-relative space
preprocessing   -> correct noise and missing values
segmentation    -> divide movement into meaningful phases
features        -> compute measurable movement indicators
biomechanics    -> estimate interpretable biomechanical proxies
scoring         -> convert indicators into movement quality scores
```
