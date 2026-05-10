# Movement Project

English | [한국어](README.md)

PhD dissertation research: an analysis framework that quantifies movement quality
from monocular mobile-camera 3D pose data in biomechanical terms and expresses
the result as interpretable digital biomarkers.

Repository: <https://github.com/JonnielPark/movement_project>

![Interpretable digital biomarker framework overview](docs/assets/framework_overview.png)

*Figure. Conceptual overview of the monocular-vision movement-quality analysis
framework. The six macro-stages summarize the detailed 12-stage pipeline below;
scores and labels on the right are illustrative examples, not validation results.*

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
⑥  Segmentation        semi-automatic rep/phase splitting from joint-motion tracking
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

## Implementation Status (2026-05-10)

### Complete

| Area | Module / File | Notes |
|---|---|---|
| Pose I/O and config | `io.py`, `config.py` | CSV loading, landmark / connection definitions |
| ① Validation | `validation.py` | Structural integrity report |
| ② Annotation | `annotation.py` | Frame-level metadata merge; filming/performance provenance and observed protocol metadata preserved |
| ③ Exercise Definition | `exercise_definition.py` | YAML loader + validator + generic fallback; `rep_segmentation`, `phase_segmentation`, `performance_protocol`, `CameraProtocolSpec`, `allowed_side_sequence_modes` |
| ④ Preprocessing | `preprocessing.py` | Visibility gating, segment consistency, angle bounds, velocity outliers, left-right swap, interpolation, smoothing |
| ⑤ Normalization | `normalization.py` | Hip-center translation + median torso-length scale |
| ⑥ Segmentation | `segmentation.py` | `rep_segmentation` repetition-boundary detection + existing `phase_segmentation` phase labels; failure-point report |
| ⑦ Motion Attribution | `motion_attribution.py` | Per-rep active-limb consistency; reads `performance_protocol.side_sequence`; conservative / auto-correct modes |
| ⑧ Feature Extraction | `features/` | ROM, symmetry, shape, tempo, variability, CoM stability, compensation rules (`knee_valgus`, `lateral_pelvic_shift`, `excessive_trunk_flexion`, `heel_lift`, `pelvic_rotation`); rep-level + **phase-level** emission; `summarize_phase_to_rep()` |
| ⑨ Biomech Proxy | `biomech/` | CoM range/path, knee/hip moment arms with visibility weighting, **load-shift OLS slope** (`biomech/load_shift.py`, §6.5) |
| ⑩ Biomarker Derivation | `biomarker/` | Z-score deduction, dynamic floor, composite domain score, **YAML-based interpretation rules** (`biomarker/interpretation.py`, §7.3) |
| Clinical mapping | clinical mapping docs, `data/definitions/clinical/`, `clinical.py` | §5.5/§5.6 per-exercise feature × biomechanical meaning table + basic FMS-like traffic-light mapping |
| Interpretation rules | `data/definitions/interpretation_rules/` | §7.3 rule engine; four exercises × 5-7 rules; forbidden-vocabulary validation complete |
| Pipeline runner | `pipeline.py` | Stages ①-⑩ connected |
| Protocol metadata schema | `exercise_definition.py`, `annotation.py`, `motion_attribution.py`, `pipeline.py`, exercise YAML | CameraProtocol parser/validation, camera-zone warning provenance, protocol count/side-sequence metadata, MediaPipe-style input clarification |
| Unit tests | `tests/` | Protocol-metadata schema targeted tests pass 17 cases; latest full run passes 70/71 with one known active Task A/P1 segmentation-policy failure |

### Partial

| Area | Module | Remaining Work |
|---|---|---|
| Existing pipeline verification | `segmentation.py`, `features/`, reporting records | Phase segmentation tests, feature registry coverage, declared-but-unimplemented reports, provenance/source-field policy (→ Task A) |
| Motion attribution / robustness evidence | `motion_attribution.py`, `simulation/` | Structured correction log, false-correction metrics, viewpoint variation, compensation injection, experiment runner, robustness summaries (→ Task B) |
| ⑪ Visualization | `visualization.py` | Dissertation-grade static figures: phase segmentation, load shift, robustness sensitivity, attribution heatmap, radar, score breakdown (→ Task C) |

### Plan (Before Defense)

| Task | Deliverable | Dissertation § |
|---|---|---|
| A — Existing pipeline verification | Phase segmentation tests, feature registry coverage, compensation candidate reports, provenance/source-field policy | Method verification |
| B — Motion attribution and robustness backbone | Structured correction log, false-correction metrics, viewpoint/compensation simulation injectors, `scripts/run_robustness_experiment.py`, robustness summaries | §8 |
| C — Dissertation-grade reporting visualization | Six static figure functions, `save_figure()`, source-field/caption provenance, `outputs/figures/` exports | §11 |
| D — Clinical mapping integration | FMS-like mapping coverage check, feature availability linkage, optional traffic-light/severity integration into reporting | §7.4 |
| E — Maintenance and repository hygiene | Focused test runs, full `pytest` before handoff, cache/build cleanup, stable README development commands | Development hygiene |
| F — Optional visibility-aware scoring fallback | Feature availability policy and confidence notes if pilot filming shows repeated occlusion, left/right swap, or landmark jitter | Conditional after Task A/C |

Task letters follow the current priority order in
`docs_eng/code_revision_plan.md`. Dashboard / Phantom 3D work is deferred behind
the Task D gate and is not an active implementation task unless selected as a
dissertation output.

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
│   ├── camera/                      # camera_zones.yaml filming-zone definitions
│   ├── reference/                   # baseline_zscore.json (synthetic-normal baseline)
│   └── processed/                   # intermediate/final pipeline outputs by stage (.gitignore)
├── docs/
│   ├── assets/                       # Shared figures for README and documents
│   ├── terminology.md               # study-specific terms and clinical language principles
│   ├── overview.md                  # framework overview
│   ├── practical_protocols/         # practical filming and performance protocols
│   │   ├── camera_protocol.md
│   │   └── exercise_performance_protocol.md
│   ├── pipeline/                    # pipeline stage documents ① ~ ⑫
│   │   └── 00_data_format.md ~ 12_insilico_simulation.md
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
inside `practical_protocols/`, `pipeline/`, and `clinical/` are tracked in the document index in
[docs_eng/overview.md](docs_eng/overview.md).

| Version | File | Content |
|---|---|---|
| 1.4.4 | [docs_eng/terminology.md](docs_eng/terminology.md) | Study-specific terms and clinical language principles |
| 1.4.10 | [docs_eng/overview.md](docs_eng/overview.md) | Framework overview and detailed document index |
| 1.2.3 | [docs_eng/practical_protocols/camera_protocol.md](docs_eng/practical_protocols/camera_protocol.md) | Camera filming protocol per exercise |
| 1.0.8 | [docs_eng/practical_protocols/exercise_performance_protocol.md](docs_eng/practical_protocols/exercise_performance_protocol.md) | Exercise performance protocol per exercise |
| 1.0.1 | [docs_eng/clinical/exercises/README.md](docs_eng/clinical/exercises/README.md) | Per-exercise clinical rationale documents |

---

## Data Policy

This project does not analyze videos directly. It analyzes only **joint-point
time series (CSV)** extracted from videos.

**Can be committed.**

- `data/pose/sample/` — synthetic/demo joint-point CSVs generated by code
- `data/pose/mediapipe/` — joint-point CSVs extracted with MediaPipe
- `data/definitions/` — exercise definitions, interpretation rules, clinical mapping YAML
- `data/camera/` — shared YAML for filming zones and height levels
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

It also does **not** directly determine muscle-specific activation or
target-muscle recruitment. Because small changes in joint angle, stance, load,
speed, and anatomy can change muscle recruitment, this pipeline interprets active
side, relative load shift, moment-arm proxy, and compensatory movement as
joint-/segment-level tendencies rather than direct evidence of activation in a
specific muscle.

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
