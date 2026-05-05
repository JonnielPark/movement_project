# Movement Project

박사학위 논문 연구 — 단일 비전(모바일 카메라) 3D 포즈 데이터로부터 신체 동작의 질을
생체역학적으로 정량화하여 해석 가능한 디지털 바이오마커로 표현하는 분석 프레임워크.

Repository: <https://github.com/JonnielPark/movement_project>

---

## Pipeline

```text
Pose CSV  +  annotation CSV  +  exercise definition YAML
            ↓
①  Validation          structural integrity check
②  Annotation          frame-level segment metadata (phase column reserved)
③  Exercise Definition biomechanical property object loading
④  Preprocessing       monocular data quality correction
⑤  Normalization       body-relative coordinate normalization
⑥  Phase Segmentation  semi-automatic intra-rep kinematic phase splitting
⑦  Motion Attribution  per-rep active-side consistency
⑧  Feature Extraction  spatial / temporal / control features (rep + phase level)
⑨  Biomech Proxy       CoM · moment arms · load-shift trend
⑩  Biomarker Derivation interpretable digital biomarkers + interpretation rules
⑪  Visualization       per-step visualization and reporting  [partial]
⑫  Simulation          robustness condition injection         [partial]
```

Stage activation is controlled by `enabled` flags in `configs/pipeline_default.yaml`.

---

## Implementation Status (2026-05-05)

### Done

| Area | Module / File | Notes |
|---|---|---|
| Pose I/O & config | `io.py`, `config.py` | CSV loading, landmark/connection definitions |
| ① Validation | `validation.py` | Structural integrity report |
| ② Annotation | `annotation.py` | Frame-level metadata merge; `phase` column reserved |
| ③ Exercise Definition | `exercise_definition.py` | YAML loader + validator + generic fallback; `PhaseSegmentationSpec` |
| ④ Preprocessing | `preprocessing.py` | Visibility gating, segment consistency, angle bounds, velocity outlier, L/R swap, interpolation, smoothing |
| ⑤ Normalization | `normalization.py` | Hip-center translation + median torso scale |
| ⑥ Phase Segmentation | `segmentation.py` | SG-smoothed inflection detection; Descent / Ascent / Bottom\_Hold; multi-inflection policy; all 4 exercise YAMLs v0.2.0 |
| ⑦ Motion Attribution | `motion_attribution.py` | Per-rep active-limb consistency; conservative / auto-correct modes |
| ⑧ Feature Extraction | `features/` | ROM · symmetry · shape · tempo · variability · CoM stability · compensation rules (`knee_valgus`, `lateral_pelvic_shift`, `excessive_trunk_flexion`, `heel_lift`, `pelvic_rotation`); rep-level + **phase-level** emission; `summarize_phase_to_rep()` |
| ⑨ Biomech Proxy | `biomech/` | CoM range/path · knee/hip moment arms (visibility-weighted) · **load-shift OLS slope** (`biomech/load_shift.py`, §6.5) |
| ⑩ Biomarker Derivation | `biomarker/` | Z-score deduction · dynamic floor · composite domain score · **YAML-driven interpretation rules** (`biomarker/interpretation.py`, §7.3) |
| Clinical mapping | `docs/clinical/`, `data/clinical/` | §5.5/§5.6 per-exercise feature × biomechanical meaning table + YAML mirror for dashboard tooltips |
| Interpretation rules | `data/interpretation_rules/` | §7.3 rule engine; 4 exercises × 5–7 rules; forbidden-vocabulary verified |
| Pipeline runner | `pipeline.py` | Stages ①–⑩ connected |
| Unit tests | `tests/` | `test_biomech_load_shift.py` (17 tests), `test_interpretation.py` (20 tests) |

### Partial

| Area | Module | Missing |
|---|---|---|
| ⑪ Visualization | `visualization.py` | Biomech overlay · attribution heatmap · radar · robustness sensitivity chart (→ Task B) |
| ⑫ Simulation | `simulation/` | Experiment runner + viewpoint-variation distortion (→ Task A) |

### Planned (pre-defense)

| Task | Deliverable | Thesis § |
|---|---|---|
| E — FMS Linkage | `docs/clinical/fms_linkage.md` + `data/clinical/fms_mapping.yaml` | §7.4 |
| A — Robustness Runner | `scripts/run_robustness_experiment.py` | §8 |
| B — Visualization Charts | 6 provenance-centric chart functions | §11 |
| F — CDSS Dashboard | `dashboard/app.py` (Streamlit + phantom 3D) | §7.5 |

---

## Project Structure

```
movement_project/
├── configs/
│   └── pipeline_default.yaml        # stage toggles + all runtime parameters
├── data/
│   ├── exercise_definitions/        # squat · lunge · pike_pushup · plank_shoulder_tap · generic
│   ├── clinical/                    # feature_meanings.yaml (dashboard tooltips)
│   │                                # fms_mapping.yaml (Task E, planned)
│   ├── interpretation_rules/        # squat/lunge/pike_pushup/plank_shoulder_tap .yaml
│   ├── reference/                   # baseline_zscore.json (synthetic-normal baseline)
│   ├── sample/                      # shareable synthetic data
│   └── raw/, processed/, private/   # .gitignored
├── docs/
│   ├── _terminology.md              # single source of truth for all domain terms
│   ├── 00_overview.md ~ 12_insilico_simulation.md
│   ├── clinical/
│   │   └── per_exercise_mapping.md  # §5.5/§5.6 feature × clinical meaning
│   └── code_revision_plan.md        # pre-defense implementation plan
├── notebook/                        # exploratory notebooks (00–13; 14–18 planned)
├── scripts/                         # one-shot utilities (baseline computation, …)
├── tests/
│   ├── test_biomech_load_shift.py   # ⑨ load-shift slope sign + guard (17 tests)
│   └── test_interpretation.py       # ⑩ rule loader + 3 scenarios (20 tests)
└── src/movement/
    ├── annotation.py
    ├── biomech/
    │   ├── __init__.py              # BiomechRecord · extract_rep_biomech()
    │   ├── anthropometry.py
    │   ├── com.py
    │   ├── load_shift.py            # §6.5 within-set load-migration OLS
    │   └── moment_arm.py
    ├── biomarker/
    │   ├── __init__.py
    │   ├── interpretation.py        # §7.3 YAML rule engine → InterpretationRecord
    │   └── scoring.py               # BiomarkerScoreRecord · Z-score · dynamic floor
    ├── config.py
    ├── exercise_definition.py
    ├── features/
    │   ├── __init__.py              # extract_rep_features() · FeatureRecord
    │   ├── compensation.py          # COMPENSATION_RULES registry
    │   ├── control.py
    │   ├── spatial.py
    │   └── temporal.py
    ├── io.py
    ├── motion_attribution.py
    ├── normalization.py
    ├── pipeline.py
    ├── preprocessing.py
    ├── segmentation.py
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
# dev dependencies (pytest)
python -m pip install -e ".[dev]"
```

---

## Quick Start

```python
from movement.io import load_pose_csv
from movement.pipeline import load_pipeline_config, run_pipeline
import pandas as pd

config = load_pipeline_config("configs/pipeline_default.yaml")
df     = load_pose_csv("data/sample/mediapipe_squat_synthetic.csv")
ann_df = pd.read_csv("data/sample/mediapipe_squat_synthetic_annotation.csv")

df, report = run_pipeline(df, config, ann_df=ann_df)
```

After running the pipeline, retrieve interpretation labels:

```python
from movement.biomarker.interpretation import derive_interpretations

# score_records: list[BiomarkerScoreRecord] returned by run_pipeline / derive_biomarkers
for score in score_records:
    for interp in derive_interpretations(score, biomech_records=biomech_records):
        print(f"[rep {score.rep_id}] {interp.rule_id}: {interp.label}")
```

---

## Tests

```bash
pytest -q
```

---

## Data Format

Input CSV — required columns:

```text
frame          integer frame index (monotonically increasing)
timestamp      seconds since start
<landmark>_x   float
<landmark>_y   float
<landmark>_z   float
<landmark>_visibility  float 0–1  (recommended)
```

See [docs/01_data_format.md](docs/01_data_format.md) for the full column spec.

---

## Documentation

| File | Content |
|---|---|
| [docs/\_terminology.md](docs/_terminology.md) | Single source of truth for all domain terms |
| [docs/00\_overview.md](docs/00_overview.md) | Framework overview |
| [docs/01\_data\_format.md](docs/01_data_format.md) | CSV column spec |
| [docs/02\_validation.md](docs/02_validation.md) | ① Validation |
| [docs/03\_annotation\_and\_segmentation.md](docs/03_annotation_and_segmentation.md) | ② Annotation · ⑥ Phase Segmentation |
| [docs/04\_exercise\_definition.md](docs/04_exercise_definition.md) | ③ Exercise Definition YAML schema |
| [docs/05\_preprocessing.md](docs/05_preprocessing.md) | ④ Preprocessing |
| [docs/06\_normalization.md](docs/06_normalization.md) | ⑤ Normalization |
| [docs/07\_motion\_attribution.md](docs/07_motion_attribution.md) | ⑦ Motion Attribution |
| [docs/08\_feature\_extraction.md](docs/08_feature_extraction.md) | ⑧ Feature Extraction |
| [docs/09\_biomechanical\_proxy.md](docs/09_biomechanical_proxy.md) | ⑨ Biomech Proxy |
| [docs/10\_biomarker\_scoring.md](docs/10_biomarker_scoring.md) | ⑩ Biomarker Derivation |
| [docs/11\_visualization.md](docs/11_visualization.md) | ⑪ Visualization |
| [docs/12\_insilico\_simulation.md](docs/12_insilico_simulation.md) | ⑫ Robustness Simulation |
| [docs/clinical/per\_exercise\_mapping.md](docs/clinical/per_exercise_mapping.md) | §5.5/§5.6 Feature × clinical meaning |
| [docs/code\_revision\_plan.md](docs/code_revision_plan.md) | Pre-defense implementation plan |

---

## Data Policy

- Never commit raw footage, private recordings, clinical data, or API keys.
- Shareable synthetic / demo data only under `data/sample/`.
- Private and processed data in `data/raw/`, `data/private/`, `data/processed/` (`.gitignored`).

---

## Scope

This project targets **engineering feasibility and robustness validation**, not clinical efficacy.
All metrics are relative (torso\_length\_ratio, degree, dimensionless\_cv).
Absolute force units (N, N·m, kg) are not computed and must not appear in source code.

---

## License

TBD.
