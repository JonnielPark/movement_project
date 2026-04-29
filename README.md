# Movement Project

Monocular pose-based movement analysis framework.

This project is being developed for interpretable movement quality analysis using 3D pose landmark data from a single camera.

## Current Status

Implemented:

- Pose CSV loading
- Basic landmark configuration
- 3D skeleton visualization
- Basic data validation
  - required columns
  - frame continuity
  - timestamp / FPS check
  - missing values
  - visibility quality

Planned:

- preprocessing
- coordinate normalization
- movement segmentation
- feature extraction
- biomechanical proxy modeling
- movement quality scoring

## Project Structure

```text
movement_project/
├─ pyproject.toml
├─ data/
│  └─ sample/
├─ notebook/
├─ scripts/
└─ src/
   └─ movement/
      ├─ config.py
      ├─ io.py
      ├─ utils.py
      ├─ validation.py
      └─ visualization.py
```

## Installation

```bash
git clone <repository-url>
cd movement_project
python -m pip install -e .
```

## Basic Usage

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

fig = create_pose_animation(
    df=df,
    landmarks=LANDMARKS,
    connections=CONNECTIONS,
)

fig.show()
```

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
- Raw videos, private recordings, clinical data, and API keys should not be committed.
- Sample data may be included only if it is safe to share.

## Roadmap

```text
validation
→ preprocessing
→ normalization
→ segmentation
→ feature extraction
→ biomechanical proxy
→ scoring
```

## License

To be determined.
