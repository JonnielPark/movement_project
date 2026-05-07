# Terminology

**Document Version:** 1.1.0
**Last Updated:** 2026-05-07
**Versioning Rule:** Semantic Versioning 2.0.0 (`MAJOR.MINOR.PATCH`)  
**Korean Sync:** `docs/terminology.md` is the same-version Korean source.  
**Filename Policy:** Keep `terminology.md` as the standard filename according to `AGENTS.md`.

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
| Analysis framework | The ordered pipeline steps (①–⑩, with ⑥–⑩ being the core analysis stages) that transform a pose CSV into digital biomarkers under consistent rules. Referred to by step name, not by code module. |

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
| Compensatory movement | Non-primary movement produced by segments other than the main working joints, substituting for limited ROM, insufficient strength, or balance loss. Detected via the compensation rule registry (COMPENSATION_RULES) which maps candidate names to geometric compute functions. |
| Synthetic-normal baseline | Per-metric (μ, σ) reference statistics computed from a normal-condition synthetic pipeline run and stored in `data/reference/baseline_zscore.json`. Z-scores for the movement quality score are computed relative to this baseline, not against absolute clinical thresholds. |
| Movement quality score | Per-rep composite score (0–100) computed as a weighted average of domain scores (spatial 40 %, temporal 30 %, control 20 %, biomech 10 %). Each domain score uses Z-score deduction against the synthetic-normal baseline, bounded from below by the dynamic floor derived from the mandatory-ROM ratio. |
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
| Phase | Meaningful sub-interval within one rep. Two distinct labeling schemes coexist: (1) **kinetic phase** labels (eccentric / isometric / concentric) stored in `phase_model.expected_ratio` for duration-ratio reference; (2) **kinematic phase** labels (Descent / Ascent / Bottom_Hold etc.) written to the `phase` column by ⑥ Phase Segmentation. These are deliberately decoupled. |
| Kinematic phase | A trajectory-based sub-interval of one rep defined by the movement direction of a reference landmark (e.g., hip-center descent vs. ascent). Labels: `Descent`, `Ascent`, `Bottom_Hold` (resistance exercises); `Lift`, `Tap`, `Return` (task exercises). Written to the `phase` column by ⑥ Phase Segmentation; never mixed with kinetic terms (eccentric, concentric). |
| Inflection frame | The frame at which the reference landmark reverses direction, detected as a local minimum or maximum of the smoothed trajectory. Divides one rep into its constituent kinematic phases. Identified by SG-filtered `find_peaks` and collapsed to a single candidate by the `multi_inflection_policy`. |
| Segmentation failure point | A frame or frame interval where ⑥ Phase Segmentation cannot reliably decide a rep boundary or phase boundary. Causes may include poor pose quality, insufficient ROM, multiple candidates, reference-landmark occlusion, or the need for manual correction. Failure points are recorded in the report rather than hidden; phase-level metrics are not emitted for the affected range until it is resolved. |
| Bottom_Hold | Optional kinematic phase label for the ±N frames surrounding the inflection frame, used when the exercise has a controlled isometric hold at the bottom of the range (e.g., squat bottom). Enabled by `bottom_hold.enabled: true` in the `phase_segmentation` block. |
| Phase segmentation block | The `phase_segmentation:` YAML block in an exercise definition that declares the reference landmark, reference axis, phase sequence, smoothing parameters, and inflection-detection logic for ⑥ Phase Segmentation. Absent in `generic.yaml`; when absent the ⑥ step no-ops. |
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
| Phase segmentation | Tracks joint motion to semi-automatically decide rep boundaries and intra-rep kinematic phase labels (Descent / Ascent / Bottom_Hold etc.), then writes them to the `phase` column. When automatic results are unclear, the step records segmentation failure points and uses manual intervention to confirm boundaries. Corresponds to dissertation §4.5. |
| Feature extraction | Computes spatial, temporal, and control domain quantitative metrics from normalized coordinates and exercise definition. When ⑥ Phase Segmentation has populated the `phase` column, features in PHASE_AWARE_FEATURE_FAMILIES are also emitted at (rep_id, phase) granularity alongside rep-level records. |
| Biomechanical proxy modeling | Estimates relative joint load distribution tendencies using statistical anthropometry, CoM, and moment arm approximations. |
| Biomarker derivation | Integrates feature and proxy metrics into (1) individual `BiomarkerRecord` entries with `source_fields` provenance and (2) per-rep `BiomarkerScoreRecord` composite scores (0–100) computed against a synthetic-normal baseline. |
| Visibility-based confidence weighting | Per-frame weight scheme for ⑨ biomech proxy modeling. Frame weight = mean visibility of primary-joint landmarks; frames below `minimum_visible_landmark_ratio` receive weight = 0 and are excluded from metric computation. Reduces the influence of depth-estimation noise inherent in monocular vision. |
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
| "automatic detection" (unqualified) | Rep/phase segmentation is a semi-automatic procedure with failure-point recording and manual intervention. → "semi-automatic segmentation", "confirmed after manual review" |
