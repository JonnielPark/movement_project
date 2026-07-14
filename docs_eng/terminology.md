# Terminology

**Document Version:** 1.8.5
**Last Updated:** 2026-07-14
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
| Digital biomarker | A dimensionless or relatively normalized movement-quality metric with explicit operational metadata for scoring and review. It is not a diagnostic label or clinical-efficacy endpoint. |
| Biomechanical proxy | A biomechanical surrogate that can be computed from monocular pose data. It does not directly estimate actual force, mass, or absolute torque. |
| Relative load distribution tendency | A relative tendency showing how load shifts across joints or body segments. Outputs do not use absolute units such as `N`, `N·m`, or `kg`. |
| Moment-arm proxy | A normalized distance between a joint center and a reference line of action. It is used to interpret relative load distribution, not to compute absolute torque. |
| Muscle-specific activation / target-muscle recruitment | Electrical activation, force contribution, or selective recruitment of an individual muscle. This study does not infer it directly from monocular pose. Outputs may describe joint-/segment-level tendencies, active side, or compensatory movement, but they are not direct evidence of a specific muscle's activation. |
| Synthetic-normal baseline | Per-metric reference statistics from a normal-condition synthetic pipeline run. This is a reference distribution for Z-score computation, not a clinical normal/abnormal label. |
| Movement quality score | A per-rep composite score (0–100) computed through Z-score deductions against the synthetic-normal baseline. It is not a clinical diagnostic score and must be interpreted separately from data confidence. |
| Data confidence | A separate summary describing observation and coordinate-standardization reliability, such as landmark confidence, left/right swap risk, correction-summary confidence, and quality gravity. It is not the movement-quality score itself and should not be used as a direct score penalty by default. |
| Quality gravity (`quality_gravity`) | The canonical downstream quality-weight summary for how much trust a coordinate family, feature, or comparison should carry. It may be derived from confidence, availability gates, correction caps, residual diagnostics, burden diagnostics, and sensitivity checks, but raw residual and burden values should remain in stage reports or audit exports unless explicitly needed for review. Downstream scoring should consume `quality_gravity` instead of reinterpreting raw residual/burden fields. |
| Landmark confidence | The canonical observation-quality field for a landmark. It answers whether the landmark observation is reliable enough for downstream computation. Backend-specific fields such as MediaPipe `visibility` or YOLO keypoint confidence must be mapped to `<landmark>_confidence` during ① Validation/schema harmonization. After that point, pipeline payloads, configs, reports, and notebooks should use confidence terminology only. |
| Raw pose data | The frame-level pose table first saved from the video or pose estimator. It has at least `<landmark>_x/y`, optional backend-provided `<landmark>_z`, and a canonical `<landmark>_confidence` field after ① schema harmonization. Backend-specific `visibility` is accepted only as a raw import alias and should not remain in downstream pipeline payloads. Missing z may appear as a `NaN` placeholder while still representing absent depth evidence. |
| Preprocessed pose data | The pose table after ④ Preprocessing. Raw coordinate columns are preserved, while operational quality/status columns such as `<landmark>_observed_reliable`, `<landmark>_usable`, and `preprocessing_valid` may be added. Detailed processing history belongs in the preprocessing report, not in the downstream payload. Use this term instead of "preprocessed raw data." |
| Normalized pose data | The pose table after ⑤ Normalization: preprocessed pose data plus the body-relative coordinate family `<landmark>_norm_x/y/z` and depth-evidence metadata such as `normalized_evidence_axes`, `z_axis_policy`, and `z_evaluable`. If z was absent in the backend, `norm_z` remains a `NaN` placeholder until optional canonicalization produces a analysis z. |
| Canonicalized pose data | The optional ⑤-1 canonicalization output: normalized pose data plus analysis-space coordinate families such as `canon` or `corrected_3d_hypothesis`, together with payload summaries such as confidence, availability, and `quality_gravity`. Raw residual and burden details belong in the canonicalization report or audit export. It is not the default downstream/scoring input unless a later scoring policy explicitly promotes it. |
| Coordinate-axis contract | The explicit distinction between coordinate shape and coordinate evidence. The working table may be harmonized to `axes=[x,y,z]`, but `observed_axes`, `z_source`, `z_fill_policy`, and `z_evaluable` must say whether z is backend model-depth evidence, a canonical hypothesis, or only a `NaN` placeholder. A missing z axis must never be filled with zero to imitate 3D. |
| 2D pose data | Pose-backend output such as YOLO pose that provides recording-view x/y and confidence but no model-depth z. It may be schema-harmonized to xyz with `NaN` z placeholders, while depth-sensitive features and score contribution remain restricted unless separate analysis evidence is produced. |

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
| Exercise definition | The exercise-identity YAML object, not the exercise name itself. The target schema should describe what the movement is: classification, support, primary body regions, phase model, joint actions, and biomechanical identity. During migration, legacy combined YAML may still contain analysis and protocol fields for loader compatibility. |
| Exercise session definition | An ordered composition of one or more existing exercise definitions. It specifies block order, block repeat count, and one uniform rest policy between blocks. It is distinct from recording metadata `session_id` and does not create a separate general/mixed exercise category. |
| Exercise authoring spec | A small draft object created by a notebook or future UI from researcher selections. It is used to generate exercise definition, analysis profile, performance protocol, and camera protocol YAML artifacts; it is not directly consumed as the execution source by the pipeline. |
| Analysis profile | The exercise-specific analysis configuration separated from exercise identity, such as segmentation settings, landmark sets, angle definitions, active feature domains, quality-rule overrides, and compensation-pattern drafts. |
| Exercise runtime context (`ExerciseContext`) | The runtime object assembled from the exercise definition plus related analysis, performance, and camera YAML artifacts for one `exercise_id`. It is the target replacement for passing one oversized exercise-definition YAML object through the pipeline. |
| Movement template ID | An exercise-definition classification key describing the analysis template derived from joint actions plus context, such as `bilateral_lower_body_closed_chain`. It is not the frame-level annotation side/sequence pattern and should not depend on the display exercise name alone. |
| Movement pattern | Deprecated compatibility name for `movement_template_id` during migration. New docs and code should use `movement_template_id` when referring to the exercise-definition analysis template. |
| Execution pattern | A frame- or segment-level value describing the observed execution side/sequence pattern in the recording, such as `bilateral` or `alternating`. It is distinct from `movement_template_id` and should not be used as the exercise's biomechanical identity. |
| Performance failure point | The first rep/frame or recording endpoint at which the participant can no longer maintain the exercise's baseline posture, ROM, rhythm, base of support, or left-right sequence consistently, even if no pain is reported. It is an acquisition/annotation marker for actual repetition count and stop reason, not a clinical diagnosis of strength or fatigue, and is distinct from a segmentation failure point. |
| Compensatory movement | A non-primary movement that substitutes for or distorts the main task. Only patterns declared in YAML `compensation_patterns` and registered in the compensation-rule code are emitted as biomarkers. |
| Validation | Structural and formal integrity checking of the input pose data. It is distinct from robustness evaluation. It may include schema harmonization, such as adding `NaN` z placeholders for 2D pose backends, but it must not invent measurement evidence or overwrite backend-provided coordinates. |
| Robustness evaluation | Evaluation of metric responsiveness and consistency under synthetic conditions such as noise, occlusion, ROM restriction, or velocity spikes. It is not input-integrity validation. |
| Landmark-confidence weighting | A biomechanical-proxy weighting scheme that uses key-landmark confidence as frame weights. Low-confidence frames have reduced influence or are excluded from metric computation. |
| View-metric reliability | An exercise-definition prior describing how well a camera zone supports a metric family. It is separate from coordinate correction and landmark quality; values such as `high`, `moderate`, `low`, and `not_assessed` guide reporting and scoring eligibility. |
| Feature-context resolution | A ⑦ Feature Extraction preparation step that converts exercise definition, segmentation, side-role evidence, bilateral-symmetry context, and observation reliability into `role_context`, availability reasons, and `source_fields`. It does not modify coordinates, relabel reps/phases, or create scores. |
| Feature availability | A per-feature decision on whether a computable value may enter scoring after checking landmark coverage, geometry plausibility, swap risk, and view-metric reliability. It is distinct from merely being able to calculate a numeric value. |
| Range of motion | The spatial feature family for joint-angle range evidence, emitted as explicit `xy` and `xyz` variants such as `spatial.range_of_motion.xy.<joint_angle>` and `spatial.range_of_motion.xyz.<joint_angle>`. It replaces the older internal `rom` family name. |
| Movement path | The spatial feature family for landmark path-length evidence, emitted as `spatial.movement_path.arc_length_xy.<landmark>` or `spatial.movement_path.arc_length_xyz.<landmark>`, with single-axis `axis_path_*` diagnostics kept report-only unless explicitly promoted. It replaces the older internal `trajectory` or `shape` family names. |
| Support consistency | The spatial feature family for recording-view fixed-support consistency evidence, such as support-point drift, support-width variation, and support-center drift. It is not a CoP/CoM-like biomechanical stability proxy; those load- or mass-center interpretations belong to ⑧ Biomechanical Proxy. |
| Role alignment | The spatial feature family for comparing expected roles such as left/right, front/rear, support/moving, or active/passive sides. In bilateral squat it currently emits left/right range-of-motion or support-consistency comparisons, but the term is not limited to bilateral symmetry. |
| Phase profile | A domain-local summary layer for rep-level summaries of feature behavior across kinematic phases, such as `spatial.phase_profile.range_of_motion_ratio.descent_ascent`. The same pattern may later exist under `temporal.phase_profile.*`, `control.phase_profile.*`, and `biomech.phase_profile.*`; it is not a separate segmentation step. |
| Analysis evidence | A computed coordinate family, feature, or comparison that carries operational metadata such as availability, confidence, `quality_gravity`, and sensitivity. It is produced before scoring and does not define final-score contribution by itself. Raw residual/burden values are stage-local diagnostics unless promoted to an explicit review export. |
| Stage report / audit metadata | A sidecar report emitted by a pipeline stage for debugging, reproducibility, and review. It records applied rules, source/config references, warnings, and algorithm choices. It is not a direct downstream payload and should not be required for scoring. |
| Audit references (`source_fields`) | Optional trace references used in reports or debug exports to explain which YAML fields, algorithms, or source columns informed a record. They are not required record payload, and scoring must use explicit operational fields such as availability, evidence axes, depth dependency, focus tier, and feature family instead. |
| Near-side / far-side | A camera-relative observation-confidence context. `Near-side` means the landmark or body side closer to the camera; `far-side` means the side farther from the camera. It is used for confidence interpretation, not as an anatomical quality label. |
| Far-side jitter | Instability of landmarks on the camera-far side, summarized from confidence drops, velocity/acceleration spikes, segment-length inconsistency, or swap risk. It is a data-confidence signal, not a compensatory-movement metric. |

---

## 4. Coordinate-Correction Terms

| Term | Fixed Meaning in This Study |
|---|---|
| Analysis-space canonicalization | Optional ⑤-1 substage under Normalization, which consumes ⑤ `norm` coordinates and may add analysis-space coordinate families to reduce consistent monocular-observation bias for movement-pattern evaluation. It is not template fitting to a good movement and not absolute 3D reconstruction. |
| Canonical analysis space | An analysis coordinate representation defined from hip center, torso scale, exercise-specific movement-plane priors, support-plane priors, and related constraints. It is not an anatomical absolute coordinate system or calibrated world coordinate; it supports comparison of relative joint trajectories and temporal change. |
| Canonical depth hypothesis | An analysis z estimate that ⑤-1 Canonicalization may generate from 2D or low-confidence monocular-depth input. It is constrained by x/y projection, segment-length plausibility, support context, and temporal continuity; it is not measured depth, calibrated 3D, or ground truth. It must remain analysis evidence with confidence and `quality_gravity` summaries, while raw burden/residual diagnostics stay in the ⑤-1 report. |
| Pseudo-floor reference | An apparent floor reference estimated from exercise-defined support landmarks inside the monocular pose coordinate system. It is not the physical location of the real floor, camera calibration, or absolute 3D reconstruction. |
| Floor-relative correction | A support-plane prior for static support-consistency contexts that attenuates apparent floor artifacts using the pseudo-floor reference. It is currently treated as the `support_plane_alignment` sub-filter of analysis-space canonicalization. Raw/norm coordinates are preserved, analysis-space coordinates may be added, and raw residuals remain report-local diagnostics unless exported for review. |
| Support landmark | A landmark expected by the exercise definition to participate in floor or support-surface contact, such as feet in a squat or hands/feet in plank. Because true compensatory movement must not be erased, it is not always a fixed anchor; it is used for pseudo-floor estimation only when confidence and stability criteria are met. |
| Protocol-height lateral-width alignment | A analysis-evidence canonicalization prior that first checks whether the observed camera height matches the exercise protocol, then uses the protocol height level to choose a body anchor for attenuating depth-dependent lateral-width bias. H1 uses a support/ankle-level anchor, H2 uses a pelvis/hip-center anchor, and H3 uses a shoulder-line anchor. It is not lens calibration, perspective reprojection, or template fitting. |
| Anthropometric skeleton prior | A loose body-segment length plausibility envelope used to review monocular-depth behavior. In Stage A it may use aggregate Size Korea ratios only as an engineering envelope; it is not an empirical percentile prior, calibrated 3D reconstruction, or subject-specific skeleton fitting. |
| Conservative engineering range | A researcher-defined wide tolerance around aggregate anthropometric ratios. It is used to catch impossible skeleton behavior and data-confidence problems, not to estimate population P5/P95. |
| Row-level empirical anthropometric prior | A future upgrade that requires de-identified individual-level anthropometric rows so segment/stature ratios can be computed within each person before summarizing P1/P99 or P5/P95. |
| Depth residual correction | A bounded analysis-evidence adjustment of the depth axis that may be attempted only when x/y evidence, segment-length plausibility, confidence, and correction caps allow it. It never overwrites raw or base normalized coordinates. Its raw residual/burden diagnostics stay inside ⑤-1 reports or audit exports; downstream payloads use `quality_gravity` when this evidence is promoted. |
| Articulation plausibility | A separate guard for impossible joint-angle or reverse-bending configurations. It downgrades data confidence or marks features unavailable; it is not a direct movement-quality penalty. |

---

## 5. Clinical Language Use

This study does not avoid clinical interpretation. However, because it does not
perform a clinical trial, patient-cohort validation, or diagnostic-performance
evaluation, clinical wording must stay within the scope of **clinical interpretability**
and **decision-support information for clinicians**.

| Expression Type | Usage Principle |
|---|---|
| clinical interpretation / clinical meaning | Allowed, as long as the wording does not imply disease diagnosis or treatment-effect proof. |
| clinically significant | Use only when actual clinical data and statistical/clinical significance testing support it. At this stage, use "clinically interpretable" or "may support clinician judgment." |
| diagnoses / predicts disease | Do not use. Use "exploratory metric for future clinical studies" or "quantitative information that may support clinician assessment." |
| sensitivity / specificity / diagnostic accuracy | Use only with clinical labels and a diagnostic-performance evaluation design. In this study, use robustness, responsiveness, and consistency. |
| normal / abnormal | Do not use as a clinical binary without clinical criteria. Use "reference movement", "synthetic variant", or "deviation from reference." |
| patient data | Use only for actual patient-cohort data. Current inputs are synthetic data and normal movement data; prefer "participant", "subject", or "sample." |
| absolute torque / load | Do not use. Monocular-pose outputs are relative metrics, expressed as "relative load distribution tendency between joints." |
| automatic detection | Do not use without qualification. Rep/phase segmentation is semi-automatic and includes failure-point recording plus manual intervention; use "semi-automatic segmentation" or "confirmed after manual review." |

Suggested wording:

```text
This metric is not designed to diagnose a specific disease. It provides quantitative
information that clinicians may use when interpreting movement quality biomechanically.

The observed compensatory movement should be interpreted as a observed movement pattern
strategy for further clinical assessment, not as direct evidence of a specific pathology.

The biomechanical outputs of this pipeline are monocular-pose-based relative metrics;
they do not directly represent absolute strength, joint torque, or clinical prognosis.

The result does not replace clinician assessment. It structures rep-level movement
patterns and compensatory strategies to support clinical reasoning.

Clinical meaning should be further reviewed by medical advisors and validated in
future clinical-data studies.
```
