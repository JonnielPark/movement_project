# Movement Project

Monocular pose-based movement analysis framework for interpretable movement quality assessment.

Each exercise is described as a structured biomechanical property object (an "exercise definition"). Downstream modules read the definition to decide which features and biomarkers to compute, so the framework can be extended to new exercises by authoring a YAML file rather than by adding code branches.

## Status

Implemented:

- Pose CSV loading
- Landmark configuration
- 3D skeleton visualization
- Basic data validation
- Coordinate normalization
- Annotation mask application
- Exercise definition schema and field dictionary
- Exercise definition YAML loader and validator (with generic fallback)
- Pipeline runner with full step sequence: validation → annotation → exercise_definition → preprocessing → normalization → motion_attribution → features → biomech → scoring

Planned:

- Definition authoring notebook (dropdown-based) and annotation interpretation export
- Preprocessing (reliability filtering, exercise-aware swap detection, short-gap interpolation)
- Motion attribution (rep-level active-limb verification)
- Feature extraction (spatial, temporal, control), driven by `feature_domains`
- Biomechanical proxy modeling, driven by `biomechanical_focus`
- Compensation biomarkers, driven by `compensation_candidates`
- Movement quality scoring with biomarker provenance
- Simulation-based robustness evaluation

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

Annotation runs early so that exercise context (`exercise_type`, `pattern`, `starting_side`) and rep boundaries are available to all downstream modules. The exercise definition is loaded immediately after annotation, using `exercise_type` to select the YAML file. Downstream modules query the loaded definition for exercise-specific rules.

## Installation

```bash
git clone https://github.com/JonnielPark/movement_project.git
cd movement_project
python -m pip install -e .
```

## Quick Start

```python
from movement.io import load_pose_csv
from movement.config import (
    LANDMARKS,
    CONNECTIONS,
    make_required_columns,
    make_coordinate_columns,
    make_visibility_columns,
)
from movement.validation import run_basic_validation
from movement.visualization import create_pose_animation

df = load_pose_csv("data/sample/mediapipe_forward_bend_sample.csv")

report = run_basic_validation(
    df=df,
    required_columns=make_required_columns(),
    coordinate_columns=make_coordinate_columns(),
    visibility_columns=make_visibility_columns(),
)

print(report["passed"])

fig = create_pose_animation(df, LANDMARKS, CONNECTIONS)
fig.show()
```

## Documentation

Concept notes are maintained in `docs/`.

- [Overview](docs/00_overview.md)
- [Data Format](docs/01_data_format.md)
- [Validation](docs/02_validation.md)
- [Annotation and Segmentation](docs/03_annotation_and_segmentation.md)
- [Exercise Definition](docs/04_exercise_definition.md)
- [Preprocessing](docs/05_preprocessing.md)
- [Normalization](docs/06_normalization.md)
- [Motion Attribution](docs/07_motion_attribution.md)

## Data Format

Current modules assume a MediaPipe-style CSV format:

```text
frame
timestamp
<landmark>_x
<landmark>_y
<landmark>_z
<landmark>_visibility
```

Visibility columns are optional but recommended. Preprocessing uses visibility values for reliability gating when present.

## Notes

- Validation only reports data integrity issues. It does not modify the input data.
- Preprocessing may modify coordinates, but only to mask, interpolate, or smooth low-reliability landmark detections. It does not modify movement patterns.
- Motion attribution does not modify coordinates. It produces rep-level metadata about active-limb labeling consistency.
- The exercise definition layer does not modify coordinates or annotation. It declares the semantic and biomechanical structure that downstream modules consult.
- Each emitted biomarker should carry a `source_fields` provenance record citing the definition fields that justified its computation.
- Do not commit raw videos, private recordings, clinical data, or API keys.
- Sample data may be included only if it is safe to share.

## License

To be determined.
