# Movement Project

A biomechanical analysis framework that quantifies movement quality from monocular 3D pose data
and produces interpretable digital biomarkers.

Repository: <https://github.com/JonnielPark/movement_project>

---

## Pipeline

```text
Pose CSV + optional annotation file + exercise definition YAML

→ ① Validation           structural integrity check
→ ② Annotation           frame-level segment metadata
→ ③ Exercise Definition  biomechanical property object loading
→ ④ Preprocessing        monocular data quality correction
→ ⑤ Normalization        body-relative coordinate normalization
→ ⑥ Motion Attribution   per-rep active-side consistency
→ ⑦ Feature Extraction   spatial / temporal / control features
→ ⑧ Biomech Proxy        CoM, moment arms, anthropometry
→ ⑨ Biomarker Derivation interpretable digital biomarkers with provenance
→ ⑩ Visualization        per-step visualization and reporting
```

Step activation is controlled by `enabled` flags in `configs/pipeline_default.yaml`.

---

## Implementation Status (2026-05)

**Implemented**

- Pose CSV loading and landmark config (`io.py`, `config.py`)
- Data validation — structural integrity checks (`validation.py`)
- 3D pose animation — Plotly, raw / normalized (`visualization.py`)
- Coordinate normalization — hip center translation + sequence median torso scale (`normalization.py`)
- Annotation — frame-level metadata merge (`annotation.py`)
- Exercise definition — YAML schema, loader, validator, generic fallback (`exercise_definition.py`)
- Preprocessing — visibility gating, segment length consistency, joint angle bounds,
  velocity outlier detection, L/R swap detection and correction, short-gap interpolation,
  optional smoothing (`preprocessing.py`)
- Pipeline runner — steps ①–⑤ (`pipeline.py`)
- Motion attribution — per-rep active-side consistency, conservative / auto-correct modes
  (`motion_attribution.py`)
- Module scaffolding for steps ⑦–⑨ and simulation (`features/`, `biomech/`, `biomarker/`,
  `simulation/`)

**Planned**

- Feature extraction: spatial (ROM, symmetry, shape), temporal (tempo, variability),
  control (stability, compensation)
- Biomechanical proxy modeling: CoM estimation, moment arms, Winter (1990) anthropometry
- Biomarker derivation with full `source_fields` provenance
- Visualization: reliability overlay, joint angle time series, rep timeline, attribution
  chart, biomarker radar
- Robustness simulation: ROM restriction, Gaussian noise, occlusion, velocity spikes

---

## Project Structure

```
movement_project/
├── configs/
│   └── pipeline_default.yaml       # pipeline configuration
├── data/
│   ├── exercise_definitions/       # exercise YAML files (squat, lunge, pike_pushup,
│   │                               #   plank_shoulder_tap, generic)
│   ├── sample/                     # shareable synthetic data
│   └── raw/, processed/, private/  # .gitignored
├── docs/                           # module-level documentation (00–08)
├── notebook/                       # exploratory notebooks (00–09)
└── src/movement/
    ├── annotation.py
    ├── biomech/
    ├── biomarker/
    ├── config.py
    ├── exercise_definition.py
    ├── features/
    ├── io.py
    ├── motion_attribution.py
    ├── normalization.py
    ├── pipeline.py
    ├── preprocessing.py
    ├── simulation/
    ├── utils.py
    ├── validation.py
    └── visualization.py
```

---

## Installation

```bash
git clone https://github.com/JonnielPark/movement_project.git
cd movement_project
python -m pip install -e .
```

---

## Quick Start

```python
from movement.io import load_pose_csv
from movement.config import (
    LANDMARKS, CONNECTIONS,
    make_required_columns, make_coordinate_columns, make_visibility_columns,
)
from movement.validation import run_basic_validation
from movement.visualization import create_pose_animation

df = load_pose_csv("data/sample/mediapipe_squat_synthetic.csv")

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

Run the full pipeline:

```python
from movement.pipeline import load_pipeline_config, run_pipeline

config = load_pipeline_config("configs/pipeline_default.yaml")
result = run_pipeline(config)
```

---

## Data Format

Input CSV — required columns:

```text
frame           integer frame index (monotonically increasing)
timestamp       seconds since start
<landmark>_x    float
<landmark>_y    float
<landmark>_z    float
<landmark>_visibility   float 0–1 (recommended)
```

See [docs/01_data_format.md](docs/01_data_format.md) for the full column spec.

---

## Documentation

- [Terminology](docs/_terminology.md)
- [00. Overview](docs/00_overview.md)
- [01. Data Format](docs/01_data_format.md)
- [02. Validation](docs/02_validation.md)
- [03. Annotation & Segmentation](docs/03_annotation_and_segmentation.md)
- [04. Exercise Definition](docs/04_exercise_definition.md)
- [05. Preprocessing](docs/05_preprocessing.md)
- [06. Normalization](docs/06_normalization.md)
- [07. Motion Attribution](docs/07_motion_attribution.md)
- [08. Visualization](docs/08_visualization.md)

---

## Data Policy

- Never commit raw footage, private recordings, clinical data, or API keys.
- Shareable synthetic / demo data only under `data/sample/`.
- Private and processed data in `data/raw/`, `data/private/`, `data/processed/` (`.gitignored`).

---

## License

TBD.
