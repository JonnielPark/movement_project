# Terminology

**Document Version:** 1.4.1
**Last Updated:** 2026-05-08
**Korean Sync:** `docs/terminology.md` is the same-version Korean source.

This document is not a general glossary. Pipeline documents and code docstrings cover
ordinary stage names, coordinate shapes, unit notation, and exercise lists. This file
keeps only terms whose meaning is intentionally narrowed in this study or whose misuse
could change the research scope.

---

## 1. Scope and Output Meaning

| Term | Fixed Meaning in This Study |
|---|---|
| Movement quality | Biomechanically interpretable movement properties such as joint alignment, left/right symmetry, CoM stability, and compensatory movement. It is independent of task success alone. |
| Digital biomarker | A dimensionless or relatively normalized movement-quality metric with traceable `source_fields` provenance. It is not a diagnostic label or clinical-efficacy endpoint. |
| Biomechanical proxy | A biomechanical surrogate that can be computed from monocular pose data. It does not directly estimate actual force, mass, or absolute torque. |
| Relative load distribution tendency | A relative tendency showing how load shifts across joints or body segments. Outputs do not use absolute units such as `N`, `N·m`, or `kg`. |
| Moment-arm proxy | A normalized distance between a joint center and a reference line of action. It is used to interpret relative load distribution, not to compute absolute torque. |
| Synthetic-normal baseline | Per-metric reference statistics from a normal-condition synthetic pipeline run. This is a reference distribution for Z-score computation, not a clinical normal/abnormal label. |
| Movement quality score | A per-rep composite score (0–100) computed through Z-score deductions against the synthetic-normal baseline. It is not a clinical diagnostic score. |

All biomechanical outputs are relative metrics. If absolute force, mass, or torque units
appear in an output, treat it as a documentation or code error.

---

## 2. Phase and Segmentation

| Term | Fixed Meaning in This Study |
|---|---|
| Phase | A sub-interval within one rep. This study separates two schemes: kinetic labels in `phase_model.expected_ratio`, and kinematic labels written to the `phase` column by ⑥ Segmentation. |
| Kinematic phase | A phase defined by the movement direction of a reference landmark. Examples: `Descent`, `Ascent`, `Turnaround_Hold`, `Lift`, `Tap`, `Return`. Never mix these with kinetic labels such as `eccentric` or `concentric`. |
| Rep segmentation | The semi-automatic procedure that uses `rep_segmentation` settings to confirm repetition start/end boundaries and create `rep_id`. |
| Phase segmentation | The intra-rep phase-splitting procedure that keeps the existing `phase_segmentation` code identifier and YAML key. |
| Segmentation failure point | A frame or interval where rep or phase boundaries cannot be decided reliably. Failure points are recorded rather than hidden, and related metrics are not emitted for the affected range until manual intervention resolves them. |
| Turnaround hold (Turnaround_Hold) | An optional kinematic phase label around the inflection frame. It means the reference landmark briefly holds after moving in one direction before reversing into the opposite direction. It is governed by `phase_segmentation.turnaround_hold`. |

---

## 3. Analysis Unit and Evaluation Terms

| Term | Fixed Meaning in This Study |
|---|---|
| Exercise definition | The YAML object, not the exercise name itself. It contains exercise-specific landmarks, phase settings, compensation candidates, feature domains, and quality rules used by downstream stages. |
| Compensatory movement | A non-primary movement that substitutes for or distorts the main task. Only candidates declared in YAML `compensation_candidates` and registered in the compensation-rule code are emitted as biomarkers. |
| Validation | Structural and formal integrity checking of the input pose data. It is distinct from robustness evaluation and does not modify data. |
| Robustness evaluation | Evaluation of metric responsiveness and consistency under synthetic conditions such as noise, occlusion, ROM restriction, or velocity spikes. It is not input-integrity validation. |
| Visibility-based confidence weighting | A biomechanical-proxy weighting scheme that uses key-landmark visibility as frame weights. Low-visibility frames have reduced influence or are excluded from metric computation. |

---

## 4. Terms Not to Use

Expressions that overstate scope or create misleading impressions.

| Avoid | Reason / Use instead |
|---|---|
| "clinically significant" | This project is engineering robustness verification, not clinical efficacy testing. → "consistently identifies deviation from the biomechanical reference" |
| "diagnoses / predicts disease" | Not a diagnostic tool. → "may serve as a reference index for future clinical data studies" with explicit scope. |
| Absolute torque / load (`N·m`, `kg`) | Not estimated from monocular vision. → "relative load distribution tendency between joints" |
| "normal / abnormal" as a binary | Synthetic abnormal data is a simulation label, not a clinical diagnosis. → "reference movement / synthetic variant" |
| "patient data" | Inputs are synthetic data and normal movement data. Use only when explicitly referring to clinical data. |
| "automatic detection" without qualification | Rep/phase segmentation is semi-automatic and includes failure-point recording plus manual intervention. → "semi-automatic segmentation", "confirmed after manual review" |
