# Movement Project

English | [한국어](README.md)

PhD dissertation research: an analysis framework that quantifies movement quality
from monocular mobile-camera 3D pose data in biomechanical terms and expresses
the result as interpretable digital biomarkers.

Repository: <https://github.com/JonnielPark/movement_project>

---

## Pipeline

```text
Pose CSV  +  annotation CSV  +  exercise definition YAML
            ↓
①  Validation           structural integrity check
②  Annotation           frame-level segment metadata (`phase` column reserved)
③  Exercise Definition  biomechanical property object loading
④  Preprocessing        monocular data quality correction
⑤  Normalization        body-relative coordinate normalization
⑥  Phase Segmentation   semi-automatic intra-rep kinematic phase splitting
⑦  Motion Attribution   per-rep active-side consistency
⑧  Feature Extraction   spatial / temporal / control features, rep and phase level
⑨  Biomech Proxy        CoM, moment arms, load-shift trend
⑩  Biomarker Derivation interpretable digital biomarkers and interpretation rules
⑪  Visualization        per-step visualization and reporting      [partial]
⑫  Simulation           robustness condition injection            [partial]
```

Stage activation is controlled by the `enabled` flags in
`configs/pipeline_default.yaml`.

---

## Implementation Status (2026-05-05)

### Complete

| Area | Module / File | Notes |
|---|---|---|
| Pose I/O and config | `io.py`, `config.py` | CSV loading, landmark / connection definitions |
| ① Validation | `validation.py` | Structural integrity report |
| ② Annotation | `annotation.py` | Frame-level metadata merge; `phase` column reserved |
| ③ Exercise Definition | `exercise_definition.py` | YAML loader + validator + generic fallback; `PhaseSegmentationSpec` |
| ④ Preprocessing | `preprocessing.py` | Visibility gating, segment consistency, angle bounds, velocity outliers, left-right swap, interpolation, smoothing |
| ⑤ Normalization | `normalization.py` | Hip-center translation + median torso-length scale |
| ⑥ Phase Segmentation | `segmentation.py` | SG-smoothed inflection detection; Descent / Ascent / Bottom_Hold; multi-inflection policy; all four exercise YAMLs v0.2.0 |
| ⑦ Motion Attribution | `motion_attribution.py` | Per-rep active-limb consistency; conservative / auto-correct modes |
| ⑧ Feature Extraction | `features/` | ROM, symmetry, shape, tempo, variability, CoM stability, compensation rules (`knee_valgus`, `lateral_pelvic_shift`, `excessive_trunk_flexion`, `heel_lift`, `pelvic_rotation`); rep-level + **phase-level** emission; `summarize_phase_to_rep()` |
| ⑨ Biomech Proxy | `biomech/` | CoM range/path, knee/hip moment arms with visibility weighting, **load-shift OLS slope** (`biomech/load_shift.py`, §6.5) |
| ⑩ Biomarker Derivation | `biomarker/` | Z-score deduction, dynamic floor, composite domain score, **YAML-based interpretation rules** (`biomarker/interpretation.py`, §7.3) |
| Clinical mapping | clinical mapping docs, `data/definitions/clinical/` | §5.5/§5.6 per-exercise feature × biomechanical meaning table + YAML mirror for dashboard tooltips |
| Interpretation rules | `data/definitions/interpretation_rules/` | §7.3 rule engine; four exercises × 5-7 rules; forbidden-vocabulary validation complete |
| Pipeline runner | `pipeline.py` | Stages ①-⑩ connected |
| Unit tests | `tests/` | `test_biomech_load_shift.py` (17 cases), `test_interpretation.py` (20 cases) |

### Partial

| Area | Module | Remaining Work |
|---|---|---|
| ⑪ Visualization | `visualization.py` | Biomech overlay, attribution heatmap, radar chart, robustness sensitivity chart (→ Task B) |
| ⑫ Simulation | `simulation/` | Experiment runner + viewpoint variation distortion (→ Task A) |

### Plan (Before Defense)

| Task | Deliverable | Dissertation § |
|---|---|---|
| E — FMS linkage | FMS linkage document + `data/definitions/clinical/fms_mapping.yaml` | §7.4 |
| A — Robustness runner | `scripts/run_robustness_experiment.py` | §8 |
| B — Visualization charts | Six provenance-centric chart functions | §11 |
| F — CDSS dashboard | `dashboard/app.py` (Streamlit + phantom 3D) | §7.5 |

---

## Project Structure

```text
movement_project/
├── configs/
│   └── pipeline_default.yaml        # stage toggles + all runtime parameters
├── data/
│   ├── pose/                        # joint-point time-series CSVs
│   │   ├── sample/                  # synthetic/demo CSVs
│   │   └── mediapipe/               # MediaPipe-extracted CSVs
│   ├── definitions/                 # YAML-based analysis definitions
│   │   ├── exercises/               # squat · lunge · pike_pushup · plank_shoulder_tap · generic
│   │   ├── clinical/                # feature_meanings.yaml, fms_mapping.yaml
│   │   └── interpretation_rules/    # squat/lunge/pike_pushup/plank_shoulder_tap .yaml
│   ├── reference/                   # baseline_zscore.json (synthetic-normal baseline)
│   └── processed/                   # intermediate/final pipeline outputs by stage (.gitignore)
├── docs/
│   ├── terminology.md               # single source of truth for domain terms
│   ├── overview.md                  # framework overview
│   ├── pipeline/                    # pipeline stage documents ① ~ ⑫
│   │   └── 01_data_format.md ~ 12_insilico_simulation.md
│   ├── clinical/
│   │   └── per_exercise_mapping.md  # §5.5/§5.6 feature × clinical meaning
│   └── code_revision_plan.md        # implementation plan before defense (.gitignore)
├── notebook/                        # exploratory notebooks (00-13; 14-18 planned)
├── scripts/                         # one-off utilities such as baseline computation
├── tests/
│   ├── test_biomech_load_shift.py   # ⑨ load-shift slope sign + guards (17 cases)
│   └── test_interpretation.py       # ⑩ rule loader + 3 scenarios (20 cases)
└── src/movement/
    ├── annotation.py
    ├── biomech/
    │   ├── __init__.py              # BiomechRecord · extract_rep_biomech()
    │   ├── anthropometry.py
    │   ├── com.py
    │   ├── load_shift.py            # §6.5 within-set load transfer OLS
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

Python 3.10 or newer is required. Python 3.11 or 3.12 is recommended for local
research and development.

```bash
git clone https://github.com/JonnielPark/movement_project.git
cd movement_project
python -m pip install -e .
# Development dependency group (pytest)
python -m pip install -e ".[dev]"
```

---

## Quick Start

```python
from movement.io import load_pose_csv
from movement.pipeline import load_pipeline_config, run_pipeline
import pandas as pd

config = load_pipeline_config("configs/pipeline_default.yaml")
df     = load_pose_csv("data/pose/sample/mediapipe_squat_synthetic.csv")
ann_df = pd.read_csv("data/pose/sample/mediapipe_squat_synthetic_annotation.csv")

df, report = run_pipeline(df, config, ann_df=ann_df)
```

Getting interpretation labels after running the pipeline:

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
frame          integer frame index (monotonic increasing)
timestamp      seconds elapsed from start
<landmark>_x   float
<landmark>_y   float
<landmark>_z   float
<landmark>_visibility  float 0-1  (recommended)
```

The full column specification and detailed document index are tracked in
[docs_eng/overview.md](docs_eng/overview.md).

---

## Documentation

README tracks only the top-level documents. The list and versions of documents
inside `pipeline/` and `clinical/` are tracked in the document index in
[docs_eng/overview.md](docs_eng/overview.md).

| Version | File | Content | Korean Sync |
|---|---|---|---|
| 1.0.0 | [docs_eng/terminology.md](docs_eng/terminology.md) | Single source of truth for all domain terms | [docs/terminology.md](docs/terminology.md) |
| 1.1.0 | [docs_eng/overview.md](docs_eng/overview.md) | Framework overview and detailed document index | [docs/overview.md](docs/overview.md) |

Korean documents are synchronized under the same structure in `docs/`.

---

## Data Policy

This project does not analyze videos directly. It analyzes only **joint-point
time series (CSV)** extracted from videos.

**Can be committed.**

- `data/pose/sample/` — synthetic/demo joint-point CSVs generated by code
- `data/pose/mediapipe/` — joint-point CSVs extracted with MediaPipe
- `data/definitions/` — exercise definitions, interpretation rules, clinical mapping YAML
- `data/reference/` — reference statistics such as the synthetic-normal baseline

**Do not commit (`.gitignore`).**

- Pipeline outputs — `data/processed/`

**Caution.** If a committable CSV contains direct identifiers such as subject
name or birth date, replace them with anonymous IDs before committing. Store the
anonymous ID ↔ real-name mapping only after documenting the sidecar path and
matching `.gitignore` rule.

---

## Research Scope

This project does **not** aim to perform **absolute quantification of joint
load** that requires high-cost biomechanical equipment (absolute quantification;
e.g., `N`, `N·m`, `kg`).

Instead, it focuses on quantifying **relative load shift between body segments**
and **kinetic-chain breakdown patterns** that can be tracked broadly in
monocular-vision remote monitoring settings, in order to verify the system's
**engineering feasibility and robustness**.

Therefore, all biomechanical proxy metrics in this pipeline are designed and
produced as body-scale-normalized relative values or angle-based metrics, not
absolute force, mass, or length units (e.g., `torso_length_ratio`, `degree`,
`dimensionless_cv`, `dimensionless`).

This prioritizes a reliable XAI structure that can consistently support
clinical reasoning under the physical limitations of monocular-camera data,
before any direct demonstration of clinical efficacy.

---

## License

TBD.
