# Movement Project

Monocular pose-based movement analysis framework for interpretable movement quality assessment.

## Status

Implemented:

- Pose CSV loading
- Landmark configuration
- 3D skeleton visualization
- Basic data validation

Planned:

- Coordinate normalization
- Preprocessing
- Movement segmentation
- Feature extraction
- Biomechanical proxy modeling
- Movement quality scoring

## Installation

```bash
git clone <repository-url>
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
- [Validation](docs/02_validation.md)
- [Normalization](docs/03_normalization.md)

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

Visibility columns are optional but recommended.

## Notes

- Validation only reports data quality issues. It does not modify the input data.
- Do not commit raw videos, private recordings, clinical data, or API keys.
- Sample data may be included only if it is safe to share.

## License

To be determined.