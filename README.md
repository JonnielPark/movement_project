# Movement Project

Monocular pose-based movement analysis framework for interpretable movement quality assessment.

## Status

Implemented:

- Pose CSV loading
- Landmark configuration
- 3D skeleton visualization
- Basic data validation
- Coordinate normalization
- Annotation mask application

Planned:

- Preprocessing (reliability filtering, exercise-aware swap detection, short-gap interpolation)
- Motion attribution (rep-level active-limb verification)
- Pipeline runner reordered to: validation → annotation → preprocessing → normalization → motion attribution → features
- Feature extraction (spatial, temporal, control)
- Biomechanical proxy modeling
- Movement quality scoring
- Simulation-based robustness evaluation

## Pipeline

```text
Pose CSV
+ optional annotation file
-> Validation
-> Annotation Mask Application
-> Preprocessing
-> Normalization
-> Motion Attribution
-> Feature Extraction
-> Biomechanical Proxy Modeling
-> Scoring
-> Visualization / Report
```

Annotation runs early so that exercise context (`exercise_type`, `pattern`, `starting_side`) and rep boundaries are available to all downstream modules. Preprocessing and motion attribution use this context to enable or skip exercise-specific logic.

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
- [Preprocessing](docs/04_preprocessing.md)
- [Normalization](docs/05_normalization.md)
- [Motion Attribution](docs/06_motion_attribution.md)

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
- Do not commit raw videos, private recordings, clinical data, or API keys.
- Sample data may be included only if it is safe to share.

## License

To be determined.
