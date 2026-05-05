# Movement Project

**Document Version:** 1.0.0  
**Last Updated:** 2026-05-06  
**Versioning Rule:** Semantic Versioning 2.0.0 (`MAJOR.MINOR.PATCH`)  
**Korean Sync:** `README.md` is the same-version Korean source.

PhD dissertation research: an analysis framework that quantifies movement
quality from monocular mobile-camera 3D pose data in biomechanical terms and
expresses the result as interpretable digital biomarkers.

Repository: <https://github.com/JonnielPark/movement_project>

---

## Document Versioning

All documents start version notation at `1.0.0` as of 2026-05-06. The versioning
rule follows the Semantic Versioning 2.0.0 `MAJOR.MINOR.PATCH` format.

```text
MAJOR  incompatible changes to document structure, pipeline step definitions, or public API meaning
MINOR  new features, sections, or deliverables added while preserving existing meaning
PATCH  typos, translation, links, or wording clarifications with no meaning change
```

`docs/` is the Korean source documentation, and `docs_eng/` is the same-version
English translation with the same content. `README_eng.md` is only the English
translation of `README.md`; it must not diverge. `docs/code_revision_plan.md`
and `docs_eng/code_revision_plan.md` remain local execution-plan documents and
are excluded from git upload.

---

## Pipeline

```text
Pose CSV  +  annotation CSV  +  exercise definition YAML
            ↓
①  Validation           structural integrity check
②  Annotation           frame-level segment metadata
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

Stage activation is controlled by `enabled` flags in `configs/pipeline_default.yaml`.

---

## Implementation Status

Baseline date: 2026-05-06

| Area | Module / File | Status |
|---|---|---|
| Pose I/O and config | `io.py`, `config.py` | CSV loading, landmark/connection definitions |
| ① Validation | `validation.py` | Structural integrity report |
| ② Annotation | `annotation.py` | Frame-level metadata merge, `phase` column reserved |
| ③ Exercise Definition | `exercise_definition.py` | YAML loader, validator, generic fallback, `PhaseSegmentationSpec` |
| ④ Preprocessing | `preprocessing.py` | Visibility, segment consistency, angle bounds, velocity outliers, L/R swap, interpolation, smoothing |
| ⑤ Normalization | `normalization.py` | Hip-center translation and median torso-length scale |
| ⑥ Phase Segmentation | `segmentation.py` | SG-smoothed inflection detection, Descent / Ascent / Bottom_Hold |
| ⑦ Motion Attribution | `motion_attribution.py` | Per-rep active-limb consistency, conservative / auto-correct modes |
| ⑧ Feature Extraction | `features/` | ROM, symmetry, shape, tempo, variability, CoM stability, compensation rules |
| ⑨ Biomech Proxy | `biomech/` | CoM range/path, moment arms, load-shift OLS slope |
| ⑩ Biomarker Derivation | `biomarker/` | Z-score deduction, dynamic floor, composite domain score, YAML interpretation rules |
| Clinical mapping | `src/movement/clinical.py`, `data/clinical/` | Feature-meaning mapping, FMS-like traffic-light support labels |
| Pipeline runner | `pipeline.py` | Stages ①-⑩ connected |
| Unit tests | `tests/` | 46 tests passing |

Partial:

| Area | Module | Remaining Work |
|---|---|---|
| ⑪ Visualization | `visualization.py` | provenance-centric reporting charts, robustness sensitivity chart |
| ⑫ Simulation | `simulation/` | robustness experiment runner, viewpoint variation evaluation |

---

## Project Structure

```text
movement_project/
├── configs/
│   └── pipeline_default.yaml
├── data/
│   ├── exercise_definitions/
│   ├── clinical/
│   │   ├── feature_meanings.yaml
│   │   └── fms_mapping.yaml
│   ├── interpretation_rules/
│   ├── reference/
│   └── sample/
├── docs/
│   ├── _terminology.md
│   ├── 00_overview.md ~ 12_insilico_simulation.md
│   └── clinical/
├── docs_eng/
│   ├── _terminology.md
│   ├── 00_overview.md ~ 12_insilico_simulation.md
│   └── clinical/
├── notebook/
├── scripts/
├── tests/
└── src/movement/
    ├── annotation.py
    ├── biomech/
    ├── biomarker/
    ├── clinical.py
    ├── exercise_definition.py
    ├── features/
    ├── pipeline.py
    ├── segmentation.py
    └── visualization.py
```

---

## Installation

```bash
git clone https://github.com/JonnielPark/movement_project.git
cd movement_project
python -m pip install -e .
python -m pip install -e ".[dev]"
```

---

## Quick Start

```python
import pandas as pd

from movement.io import load_pose_csv
from movement.pipeline import load_pipeline_config, run_pipeline

config = load_pipeline_config("configs/pipeline_default.yaml")
df = load_pose_csv("data/sample/mediapipe_squat_synthetic.csv")
ann_df = pd.read_csv("data/sample/mediapipe_squat_synthetic_annotation.csv")

df, report = run_pipeline(df, config, ann_df=ann_df)
```

Interpretation rules and traffic-light support labels:

```python
from movement.biomarker.interpretation import derive_interpretations
from movement.clinical import traffic_light_for_score

for score in score_records:
    label = traffic_light_for_score(score)
    print(score.rep_id, label.label, label.meaning)

    for interp in derive_interpretations(score, biomech_records=biomech_records):
        print(interp.rule_id, interp.label)
```

---

## Tests

```bash
pytest -q
```

Current baseline:

```text
46 passed
```

---

## Documentation

| Version | File | Content | Korean Source |
|---|---|---|---|
| 1.0.0 | [docs_eng/_terminology.md](docs_eng/_terminology.md) | Terminology | [docs/_terminology.md](docs/_terminology.md) |
| 1.0.0 | [docs_eng/00_overview.md](docs_eng/00_overview.md) | Overall pipeline overview and document index | [docs/00_overview.md](docs/00_overview.md) |
| 1.0.0 | [docs_eng/01_data_format.md](docs_eng/01_data_format.md) | Input CSV data format | [docs/01_data_format.md](docs/01_data_format.md) |
| 1.0.0 | [docs_eng/02_validation.md](docs_eng/02_validation.md) | ① Validation | [docs/02_validation.md](docs/02_validation.md) |
| 1.0.0 | [docs_eng/03_annotation_and_segmentation.md](docs_eng/03_annotation_and_segmentation.md) | ② Annotation · ⑥ Phase Segmentation | [docs/03_annotation_and_segmentation.md](docs/03_annotation_and_segmentation.md) |
| 1.0.0 | [docs_eng/04_exercise_definition.md](docs_eng/04_exercise_definition.md) | ③ Exercise Definition YAML | [docs/04_exercise_definition.md](docs/04_exercise_definition.md) |
| 1.0.0 | [docs_eng/05_preprocessing.md](docs_eng/05_preprocessing.md) | ④ Preprocessing | [docs/05_preprocessing.md](docs/05_preprocessing.md) |
| 1.0.0 | [docs_eng/06_normalization.md](docs_eng/06_normalization.md) | ⑤ Normalization | [docs/06_normalization.md](docs/06_normalization.md) |
| 1.0.0 | [docs_eng/07_motion_attribution.md](docs_eng/07_motion_attribution.md) | ⑦ Motion Attribution | [docs/07_motion_attribution.md](docs/07_motion_attribution.md) |
| 1.0.0 | [docs_eng/08_feature_extraction.md](docs_eng/08_feature_extraction.md) | ⑧ Feature Extraction | [docs/08_feature_extraction.md](docs/08_feature_extraction.md) |
| 1.0.0 | [docs_eng/09_biomechanical_proxy.md](docs_eng/09_biomechanical_proxy.md) | ⑨ Biomech Proxy | [docs/09_biomechanical_proxy.md](docs/09_biomechanical_proxy.md) |
| 1.0.0 | [docs_eng/10_biomarker_scoring.md](docs_eng/10_biomarker_scoring.md) | ⑩ Biomarker Scoring | [docs/10_biomarker_scoring.md](docs/10_biomarker_scoring.md) |
| 1.0.0 | [docs_eng/11_visualization.md](docs_eng/11_visualization.md) | ⑪ Visualization | [docs/11_visualization.md](docs/11_visualization.md) |
| 1.0.0 | [docs_eng/12_insilico_simulation.md](docs_eng/12_insilico_simulation.md) | ⑫ In-silico Simulation | [docs/12_insilico_simulation.md](docs/12_insilico_simulation.md) |
| 1.0.0 | [docs_eng/clinical/per_exercise_mapping.md](docs_eng/clinical/per_exercise_mapping.md) | Per-exercise feature-meaning mapping | [docs/clinical/per_exercise_mapping.md](docs/clinical/per_exercise_mapping.md) |
| 1.0.0 | [docs_eng/clinical/fms_linkage.md](docs_eng/clinical/fms_linkage.md) | FMS-like traffic-light mapping | [docs/clinical/fms_linkage.md](docs/clinical/fms_linkage.md) |

---

## Data Policy

- Do not commit raw video, personal recordings, clinical data, or API keys.
- Only shareable synthetic/demo data belongs in `data/sample/`.
- Private and processed data belong in `data/raw/`, `data/private/`, and `data/processed/`.
- Paper figures and experiment outputs are stored in `outputs/` by default and excluded from git upload.

---

## Research Scope

This project targets engineering feasibility and robustness evaluation, not
clinical efficacy. All metrics are relative values (`torso_length_ratio`,
`degree`, `dimensionless_cv`). Absolute force units (`N`, `N·m`, `kg`) are not
computed.

---

## License

TBD.
