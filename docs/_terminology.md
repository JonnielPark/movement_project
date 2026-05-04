# Terminology

Canonical term definitions for this project. All code, documentation, and notebooks
use the same terms with the same meanings. Add new terms here before using them elsewhere.

---

## 1. Core Concepts

| Term | Definition |
|---|---|
| Monocular vision data | 3D pose time series extracted from a single mobile camera. No depth sensor or multi-camera rig. |
| Movement quality | Biomechanical properties of a movement — joint alignment, CoM stability, left/right symmetry, inter-joint coordination, compensatory movements — evaluated independently of task completion. |
| Digital biomarker | Interpretable quantitative index derived from digitally measured physiological/behavioral signals. In this project: dimensionless movement quality metrics with traceable provenance. |
| Interpretability | Property that every output metric can be traced back to the specific exercise definition fields that drove its computation (`source_fields` provenance). |
| Analysis framework | The ordered pipeline steps (①–⑨) that transform a pose CSV into digital biomarkers under consistent rules. Referred to by step name, not by code module. |

---

## 2. Validation Exercises

Four representative exercises used to verify the pipeline across different exercise property combinations.
The analysis unit is the **exercise definition object**, not the exercise name.

| Exercise | exercise_id | Property sample |
|---|---|---|
| Squat | `squat` | bilateral symmetric, sagittal ROM, closed chain, vertical CoM |
| Lunge | `lunge` | alternating, sagittal, bilateral asymmetric compensation |
| Pike push-up | `pike_pushup` | bilateral symmetric, inverted closed chain, upper-body coordination |
| Plank shoulder tap | `plank_shoulder_tap` | alternating, frontal, static posture + dynamic task, CoM stability |

---

## 3. Feature Domains

Three fixed domains for movement quality characterization:

| Domain | English term | Sub-items (examples) |
|---|---|---|
| Spatial | Spatial features | ROM, left/right symmetry, trajectory shape |
| Temporal | Temporal features | tempo, inter-rep variability, phase duration |
| Control | Control features | CoM stability, compensatory movements, balance control |

The "control" domain is not abbreviated to "stability" alone.

---

## 4. Biomechanical Key Concepts

| Term | Definition |
|---|---|
| Joint alignment | Degree to which adjacent joints/segments form a biomechanically consistent axis. Misalignment is treated as a primary signal of compensation. |
| CoM stability (Center of Mass) | Degree to which the estimated whole-body center of mass follows a predictable trajectory with low unpredicted variance during a movement phase. |
| Left/right symmetry | Similarity of bilateral segment/joint metrics across time and space. Evaluated directly only for `bilateral_symmetric` exercises. |
| Inter-joint coordination | Degree to which adjacent joints' phase and velocity match biomechanical expectations during multi-joint movement. |
| Compensatory movement | Non-primary movement produced by segments other than the main working joints, substituting for limited ROM, insufficient strength, or balance loss. |
| Center of mass (CoM) | Whole-body center of mass estimated using a statistical anthropometric model (segment mass ratios). Must be estimable in both upright and prone postures. |
| Moment arm | Perpendicular distance between a joint's rotation axis and the line of action. Used as a simplified estimate of relative load distribution tendency, not absolute torque. |
| Anthropometric model | Statistical body proportion model for estimating segment length, mass, and joint center position. Used for relative normalized metrics, not individual absolute values. |

All outputs are relative load distribution tendencies. Absolute force units (N·m, kg)
are not used — if an absolute unit appears in an output, it is a bug.

---

## 5. Exercise Definition Terms

| Term | Definition |
|---|---|
| Exercise definition | YAML object encoding the biomechanical properties of one exercise: primary joints, base of support, phase model, compensation candidates, quality rules, etc. The analysis unit is the exercise definition object, not the exercise name. |
| Phase | Meaningful sub-interval within one rep. E.g., eccentric/isometric/concentric for resistance exercises; setup/shift/tap/return for task exercises. |
| Compensation candidate | Compensation movement type to monitor for a specific exercise. Only candidates listed in the definition are produced as biomarkers. |
| Quality rules | Thresholds that determine analysis eligibility: visibility ratio, max gap frames, etc. |

---

## 6. Processing Step Terms

| Term | Definition |
|---|---|
| Validation | Checks structural and formal integrity of input pose data. Does not modify data. |
| Robustness evaluation | Evaluates whether the pipeline consistently responds to noise, occlusion, and alignment variation using synthetic abnormal data. Distinct from validation. |
| Annotation | Marks analysis segments (set, rep) and exercise context metadata. Adds columns only; does not delete frames. |
| Preprocessing | Corrects data quality issues in monocular pose data: low visibility, segment length inconsistency, abnormal joint angles, velocity outliers, L/R label swaps. Does NOT correct movement quality patterns (compensation movements, etc.). |
| Normalization | Converts coordinates to a body-relative system (hip center translation + sequence median torso scale). Removes body size and camera position effects. |
| Motion attribution | Checks whether the observed active limb per rep matches the exercise-expected side. Adds metadata only; does not modify coordinates. |
| Feature extraction | Computes spatial, temporal, and control domain quantitative metrics from normalized coordinates and exercise definition. |
| Biomechanical proxy modeling | Estimates relative joint load distribution tendencies using statistical anthropometry, CoM, and moment arm approximations. |
| Biomarker derivation | Integrates feature and proxy metrics into interpretable digital biomarkers with `source_fields` provenance. |
| Robustness simulation | Applies ROM restriction, Gaussian noise, occlusion, or velocity spikes to normal movement data to generate synthetic abnormal data for pipeline evaluation. |

---

## 7. Data and Coordinate Conventions

| Item | Convention |
|---|---|
| Pose coordinate array | `(T, J, 3)` = (frame, joint_index, xyz) |
| Single frame coordinates | `(J, 3)` |
| Angle unit | degree. Variable names use `_deg` suffix or docstring annotation. |
| Time unit | second. Frame index is separate. |
| Normalized length unit | `torso_length_ratio` (dimensionless; divided by sequence median torso length) |
| Left/right prefix | `left_*`, `right_*` (lowercase + underscore) |

---

## 8. Terms Not to Use

Expressions that overstate scope or create misleading impressions.

| Avoid | Reason / Use instead |
|---|---|
| "clinically significant" | This project is engineering robustness verification, not clinical efficacy. → "consistently identifies deviation from the biomechanical reference" |
| "diagnoses / predicts disease" | Not a diagnostic tool. → "may serve as a reference index for future clinical data studies" (explicitly scoped) |
| Absolute torque / load (N·m) | Not estimable from monocular vision. → "relative load distribution tendency between joints" |
| "normal / abnormal" (binary) | Synthetic abnormal data is a simulation label, not a clinical diagnosis. → "reference movement / synthetic variant" |
| "patient data" | Input is synthetic + normal movement data. Use only when explicitly referring to clinical data. |
| "automatic detection" (unqualified) | Primary analysis is annotation-based. Automatic segmentation is a future extension. |
