# 08. Feature Extraction

**Document Version:** 1.4.0
**Last Updated:** 2026-07-04
**Korean Sync:** `docs/pipeline/08_feature_extraction.md` is the same-version Korean source.

Pipeline step ⑧ computes movement-quality features from normalized pose data. It
does not modify pose coordinates. Every output is a `FeatureRecord` with numeric
value, unit, `source_fields`, and availability/reliability metadata for ⑩
Biomarker Derivation.

---

## 1. Pipeline Position

```text
⑤ Normalization → ⑥ Canonicalization → ⑦ Segmentation
→ ⑧ Feature Extraction     ← this step
→ ⑨ Biomech Proxy → ⑩ Biomarker Derivation
```

Required inputs:

```text
<landmark>_norm_x/y/z       normalized coordinates
rep_id                      confirmed repetition labels
phase                       optional phase labels from ⑦
exercise_definition         feature_domains, angle_definitions,
                            compensation_candidates, support context,
                            view_metric_reliability
recording provenance        camera_zone, camera_height_level when available
preprocessing context       visibility, swap risk, far-side jitter, availability hooks
role context settings       laterality, execution pattern, side sequence
```

---

## 2. Design Contract

Allowed:

```text
Per-joint included angles from YAML angle_definitions
Per-rep and per-phase aggregation
Compensation candidates dispatched from a registry
Feature availability/reliability metadata
Closed-chain support-consistency axis path diagnostics
Provenance through source_fields
Units limited to degree, second, dimensionless, dimensionless_cv, torso_length_ratio
```

Not allowed:

```text
Branching on exercise_id in feature code
FeatureRecord without source_fields
Absolute force/torque/length output
Turning camera-view limitations directly into movement-quality penalties
Treating closed-chain support-consistency axis 3D path length as direct foot/hand motion
Mixing kinematic phase labels with kinetic phase names in feature IDs
Using active-side role context for bilateral symmetric exercises
```

---

## 3. Feature Context Resolution

Feature Extraction owns side-role context resolution. This is not a score by
itself and no longer exists as a standalone pipeline stage. It only tells feature
families how to interpret side roles, confidence, and provenance.

The first context substep of ⑧ is:

```text
resolve_feature_context(df, exercise_definition, role_context_report=None)
apply_feature_context(records, feature_context)
```

Conceptual output:

```text
feature_context:
  laterality
  role_mode                 bilateral_symmetry | active_side | unavailable
  role_context              active_side, support_side, forward_leg, trailing_leg, etc.
  role_confidence           assessed | low_confidence | not_assessed
  context_reasons           provenance strings
```

Policy:

```text
bilateral_symmetric
    Do not run active-side role detection. Provide bilateral symmetry / side-bias
    context for feature families that compare left and right movement quality.

alternating / unilateral_left / unilateral_right
    Resolve side-role context inside ⑧ from the segmented dataframe,
    performance_protocol.side_sequence, and annotation context.

unilateral_unspecified / bilateral_asymmetric / unsupported
    Do not create strong side roles. Emit conditional or not-yet-supported
    provenance and let feature availability decide whether values are assessed.
```

This context-resolution substep must not modify coordinates, relabel reps or
phases, create scores, or branch on `exercise_id`.

Integration policy:

```text
⑧ owns feature-facing interpretation
    Resolve side-role context inside Feature Extraction, attach role_context only
    where a feature family declares it useful, and keep confidence/provenance
    separate from numeric feature values.

public notebook review
    Verify side-role context and feature records together in
    `27_feature_extraction_test.ipynb`.
```

Context application is intentionally narrow:

```text
spatial.role_alignment.*
    Attach bilateral symmetry context when role_mode == bilateral_symmetry.
    This makes left/right comparison provenance explicit but does not change
    the numeric role-alignment value or its low-confidence depth gate.

alternating / unilateral active-side records
    Attach active-side context only when side-role evidence is available.
    Ambiguous or missing context remains provenance, not a strong side role.

all other records
    Preserve the original role_context unless a future feature family declares
    a context requirement.
```

---

## 4. Feature Families

Domain membership is encoded in the `feature_id` prefix.

```text
spatial.*
    range of motion, movement path, support consistency, role alignment,
    alignment/depth proxies.

temporal.*
    Rep duration, phase duration, tempo variability, rhythm/smoothness proxies.

control.*
    Hip-center stability and compensation candidates such as knee_valgus,
    knee_varus, lateral_pelvic_shift, excessive_trunk_flexion, heel_lift,
    pelvis_rotation.
```

`feature_domains.biomechanical_proxy` is routed to ⑨ Biomech Proxy, not consumed
as a missing ⑧ extractor.

Depth-sensitive features are not discarded at extraction time. ⑧ should emit
them with `depth_dependency`, `availability`, and reliability metadata, then ⑩
decides their score gravity. This keeps the evidence visible while allowing
recording-view-heavy scoring policies.

Feature identifiers describe the measured metric, not the specific repetition.
For any per-rep feature, `rep_id` is carried in the record field and must not be
embedded in `feature_id`. This keeps baseline matching stable across recordings
with different repetition counts.

```text
temporal.tempo.rep_duration       one repetition duration in seconds
temporal.variability.tempo_cv     sequence-level coefficient of variation
```

Avoid rep-indexed metric ids such as `temporal.tempo.rep_3`; they make rep 3
look like a different metric from rep 1 and can produce false 100-point temporal
scores when the baseline only contains earlier repetition ids.

Phase-level temporal ids use the exercise-defined phase labels emitted by
⑦ Segmentation. The current phase-level duration rows keep the common
phase-suffix mechanism, for example `temporal.tempo.rep_duration.descent`, while
`phase` remains record metadata. Rep-level phase-profile summaries must derive
their label pair from `exercise_definition.phase_segmentation.phase_sequence`
when available, rather than hard-coding squat-only labels.

Temporal records follow the same public/private separation as spatial records,
but the first contract is intentionally smaller:

```text
temporal public/common fields
    landmark_ids          [] unless a future timing metric is tied to a landmark
    support_role          unknown
    coordinate_reference  timestamp
    evaluation_domain     timing_only
    evidence_axes         time
    feature_family        tempo | variability | phase_profile
```

Current temporal private families:

```text
tempo
    temporal.tempo.rep_duration
    Measures one confirmed repetition duration from timestamp and rep boundary
    evidence. `rep_id` is record metadata and must not be embedded in the
    feature id.

variability
    temporal.variability.tempo_cv
    Measures sequence-level coefficient of variation across rep durations.
    This is the preferred first rhythm/repeatability signal. It may be copied
    into each per-rep score audit with the same value so that the set-level
    rhythm penalty is visible without inventing rep-specific CV values.

phase_profile
    temporal.phase_profile.duration_ratio.<phase_a>_<phase_b>
    Measures the ratio of two exercise-defined phase durations. For
    descent/ascent resistance exercises this becomes
    `temporal.phase_profile.duration_ratio.descent_ascent`. For a
    lift/tap/return template the same rule can emit `lift_return`. Static-hold
    templates with a single `Hold` phase do not emit a duration ratio.
```

Temporal source fields should distinguish the timing family and the upstream
labels used to compute it:

```text
temporal.tempo.rep_duration
    feature_domains.temporal.tempo
    segmentation.rep_id
    timestamp

temporal.variability.tempo_cv
    feature_domains.temporal.variability
    temporal.tempo.rep_duration

temporal.phase_profile.duration_ratio.<phase_a>_<phase_b>
    feature_domains.temporal.phase_profile
    phase_segmentation.phase_sequence
    temporal.tempo.rep_duration.<phase_a>
    temporal.tempo.rep_duration.<phase_b>
```

This keeps temporal records available for scoring while avoiding a narrow
absolute-speed interpretation. The default scoring intent is:

```text
tempo          broad acceptable-duration band; flags only obvious timing outliers
variability    rhythm/repeatability evidence across reps
phase_profile  phase-ratio evidence from exercise-defined labels
```

Future static and alternating templates should reuse this structure:

```text
static_hold
    temporal.tempo.rep_duration or hold duration is the main timing metric.
    No duration-ratio phase profile is emitted unless a drift/correction
    subphase is explicitly defined and reviewed.

alternating / unilateral sequence
    rep duration remains per repetition, while future private families may add
    side-sequence timing CV or left/right phase-ratio summaries. Those metrics
    must read side/phase labels from the exercise definition or annotation
    protocol instead of assuming bilateral squat phases.
```

Common record context metadata should be attached once in ⑧ and carried
downstream instead of being re-inferred repeatedly from `feature_id` strings.
These fields do not change feature values or score gravity by themselves; they
make coordinate, evidence, and scoring context explicit for ⑩ and notebooks.

Stable anatomical facts belong in the joint/landmark metadata registry, not in
each feature row. A feature row should point to the involved landmarks through
`landmark_ids`; reports may join those ids to the registry when they need
body-region, side, paired-landmark, or default joint-action labels.

```text
Joint/landmark metadata registry
landmark_id           canonical landmark id, including derived ids such as
                      hip_center, shoulder_center, or whole_body_com
body_region           stable anatomical/body region
side                  left | right | midline | derived | unknown
landmark_type         joint_center | surface_landmark | derived_center |
                      proxy | unknown
paired_with           contralateral partner when applicable
proximal_landmarks    existing proximal landmark ids for segment/joint
                      interpretation; empty when none exist in the active
                      landmark set
distal_landmarks      existing distal landmark ids for segment/joint
                      interpretation; empty when none exist in the active
                      landmark set
derived_from_landmarks existing landmark ids used to construct a derived
                      center/proxy such as hip_center
segment_proximal      adjacent proximal segment ids when applicable
segment_distal        adjacent distal segment ids when applicable
default_joint_actions stable namespaced anatomical actions associated with
                      the landmark, e.g. ankle.dorsiflexion_plantarflexion
joint_profile         private joint/profile key, e.g. ankle
support_capable       structural support capability only; actual
                      support role is decided at runtime by exercise context
default_evidence_axes usual evidence axes before feature-specific overrides
default_depth_sensitivity low | moderate | high | unknown
```

Joint/profile-specific private metadata belongs in a separate profile registry.
Inside a profile, action names are local and should not repeat the profile name;
when surfaced as a global id, the profile namespace is added.
The profile registry is not a general anatomy catalogue. It should keep only
currently emitted feature templates and explicitly planned interpretation
candidates. For example, the knee profile keeps `flexion_extension` and
`varus_valgus_proxy` because knee range of motion, knee movement path, knee role
balance, and
`knee_valgus`/`knee_varus` compensation records are implemented or planned for
scoring review. Axial knee rotation remains omitted until a view-supported
feature and reliability policy exist.

Apply the same minimal rule to all joint profiles:

```text
hip                  keep hip flexion/extension, hip range of motion, hip movement
                     path, and hip role alignment; leave hip rotation/abduction out until
                     a view-supported feature exists.
pelvis_reference     keep derived control, lateral-tilt, AP-tilt, rotation, and
                     weight-shift proxies because exercise definitions already
                     use these as control/review concepts. Treat depth-heavy
                     pelvis rotation as low-confidence evidence.
trunk_reference      keep trunk flexion/extension, lateral-flexion, and
                     rotation proxies because these appear in exercise
                     definitions and compensation review paths.
shoulder             keep shoulder flexion/extension and scapular stability
                     proxy; do not add general shoulder rotation unless a
                     feature and reliability policy are defined.
elbow                keep elbow flexion/extension and planned elbow-tracking
                     candidates; omit pronation/supination.
wrist                keep endpoint/support movement path and wrist flexion
                     extension only; omit radial/ulnar deviation.
support_base         keep derived support-consistency control only.
whole_body_com       keep CoM range/path proxies only.
```

```text
joint_profiles.ankle.anatomical_actions.primary
    dorsiflexion_plantarflexion

global/action id
    ankle.dorsiflexion_plantarflexion
```

Use `foot_heading_proxy`, not `foot_progression_proxy`, for MediaPipe-style
foot direction evidence. The proxy describes the observed foot/toe heading from
available ankle, heel, and foot-index landmarks; it is not a full gait
progression-angle measurement.

Record-level fields remain dynamic or feature-specific:

```text
landmark_ids          list of landmark ids represented by the record; may be
                      empty for pure timing or sequence-level aggregate records
support_role          support_consistency | moving_landmark |
                      pelvis_reference | trunk_reference | whole_body_proxy |
                      joint_proxy | unknown
coordinate_reference  norm | norm_recording_view_xy | norm_model_depth |
                      corrected_3d_hypothesis | timestamp | derived_proxy |
                      unknown
evaluation_domain     recording_view_only | corrected_3d_hypothesis |
                      dual_domain_compare | timing_only | unknown
evidence_axes         x | y | z | xy | xz | yz | xyz | time | scalar | unknown
feature_family        range_of_motion | movement_path | support_consistency |
                      role_alignment | phase_profile | tempo | variability |
                      stability | compensation | proxy | other
```

`phase_profile` is a domain-local summary layer, not a spatial-only concept.
Current implementation emits `spatial.phase_profile.*` for template-specific
descent/ascent range-of-motion ratios and `temporal.phase_profile.*` for
exercise-defined phase-duration ratios. Other phase sequences must define their
own summary rule instead of being forced into a descent/ascent comparison.
Reserved future domains include:

```text
control.phase_profile.*    phase-specific compensation or control-tendency summaries
biomech.phase_profile.*    phase-specific CoM, moment-arm, or load-shift summaries
```

Those additions require separate tests and scoring review before they are
enabled; ⑧ does not infer them from the spatial or temporal profile.

This split avoids storing the same anatomical facts twice. Range of motion is the
exception that must expose its measurement geometry more explicitly: a knee
range value is
not just a knee-point measurement, but a three-point included-angle measurement
using proximal, vertex, and distal landmarks from `angle_definitions`. Therefore
range-of-motion records carry the full angle triplet in `landmark_ids`, while stable
anatomical interpretation still comes from the landmark/profile registries.

`evaluation_domain` must remain conservative. A record that uses MediaPipe
`z`/`xyz` is not automatically a corrected-3D-hypothesis record. It should
normally carry `evidence_axes = z` or `xyz`, elevated `depth_dependency`, and
`evaluation_domain = dual_domain_compare` only when the feature is intended to
be compared with corrected-candidate evidence later. Pure timing records use
`timing_only`.

Range of motion emits explicit evidence variants, matching the movement-path evidence policy:

```text
spatial.range_of_motion.xy.<joint_angle>
    Recording-view included-angle range of motion computed from normalized camera-plane x/y.
    Use this as the preferred scoring candidate when the movement-quality
    question can be answered from the recording view and the camera protocol is
    compatible.

spatial.range_of_motion.xyz.<joint_angle>
    Mixed-axis included-angle range of motion using normalized x/y and model/candidate z.
    This remains depth-sensitive comparative evidence. It is useful for review
    and future corrected-3D-hypothesis comparison, but should receive lower
    score gravity than the matching `spatial.range_of_motion.xy.*` record until
    validation promotes it.
```

Both variants must include `source_fields` that identify the originating
`angle_definitions.<joint_angle>` entry and its `proximal`, `vertex`, and
`distal` landmarks. For example:

```text
spatial.range_of_motion.xy.left_knee_angle
    landmark_ids = [left_hip, left_knee, left_ankle]
    evidence_axes = xy
    evaluation_domain = recording_view_only

spatial.range_of_motion.xyz.left_knee_angle
    landmark_ids = [left_hip, left_knee, left_ankle]
    evidence_axes = xyz
    evaluation_domain = dual_domain_compare
```

Closed-chain support landmarks need special handling. For exercises whose support
context declares fixed floor/ground contact, cumulative path length of a support
landmark can be dominated by pose jitter, monocular-depth drift, or
canonicalization residual rather than true support movement. Stage 8 must
therefore emit explicit movement-path evidence variants instead of an implicit
mixed-axis movement-path name. The scorer decides how much each variant contributes.

```text
spatial.movement_path.arc_length_xy.<landmark>
    Recording-view support-consistency axis path evidence. Under fixed closed-chain
    support it is usually diagnostic or low-gravity evidence, not direct proof
    that the foot/hand moved.

spatial.movement_path.arc_length_xyz.<landmark>
    Mixed recording-view/depth support-consistency axis path evidence. Under monocular
    pose it is depth-sensitive provenance and should be withheld or assigned low
    score gravity unless validation promotes it.

spatial.support_consistency.axis_path_x.<landmark>
spatial.support_consistency.axis_path_y.<landmark>
spatial.support_consistency.axis_path_z.<landmark>
spatial.support_consistency.axis_path_xy.<landmark>
    Report-only diagnostics for closed-chain support landmarks. They expose the
    axis source of apparent support motion and are not baseline-scored by
    default.
```

Support-landmark path diagnostics must be derived from the exercise definition's
support context, not from an `exercise_id` branch.

Support-consistency features are separate from support-consistency axis path diagnostics. They
translate fixed-support exercise constraints such as `maintain_foot_contact`
into recording-view x/y consistency features. These features do not use monocular
depth by default and may be scored with a dedicated `support_consistency` family
budget once a baseline is regenerated. They should not be interpreted as
CoP/CoM-like biomechanical stability proxies; those belong to ⑨ Biomechanical
Proxy.

```text
spatial.support_consistency.point_drift_xy.<landmark>
    Maximum recording-view x/y displacement of a support ankle/wrist from its
    median support position within the rep or phase.

spatial.support_consistency.width_variation_xy
    Coefficient of variation of bilateral support-anchor distance in the
    recording-view x/y plane.

spatial.support_consistency.center_drift_xy
    Maximum recording-view x/y displacement of the bilateral support center
    from its median support-center position.

spatial.role_alignment.left_right.support_consistency_xy_drift.<left_anchor>_<right_anchor>
    Stance-width-normalized left/right difference in support-point x/y drift.
    This is a recording-view support-consistency role-alignment feature, not a
    depth-sensitive range-of-motion role alignment feature.
```

For bilateral-foot squat these features represent base-of-support consistency,
not ankle range of motion. They should be interpreted as support-consistency
proxies and remain separate from `spatial.range_of_motion.xy.*_ankle_angle` and
`spatial.range_of_motion.xyz.*_ankle_angle`. The role-alignment
variant may contribute to the `role_alignment` scoring family only when its
availability gate remains assessed; depth-sensitive role-alignment variants still
requires stronger view/depth evidence before scoring.

Support consistency uses the same public/private metadata split as joint-level
features:

```text
Public FeatureRecord fields
    feature_id             support_consistency metric id, e.g.
                           spatial.support_consistency.point_drift_xy.left_ankle
    landmark_ids           measured support landmark(s) or derived support_center
                           reference; stance-width records use both anchors
    support_role           support_consistency
    coordinate_reference   norm_recording_view_xy
    evaluation_domain      recording_view_only
    evidence_axes          xy
    feature_family         support_consistency; left/right support-drift rows use
                           role_alignment
    depth_dependency       none
    source_fields          support context fields plus
                           support_consistency.recording_view_xy

Private registry/profile fields
    ankle/wrist profile    support-consistency point-drift templates for each side
    support_base profile   support-center drift and stance-width variation
                           templates
    reliability_priors     view-specific support_consistency_xy priors
    stable anatomy         side, paired_with, body_region, and default action
                           labels live in landmark/profile registries
```

This avoids treating support participation as a permanent anatomical property of
the ankle or wrist. A wrist can be a moving endpoint in one exercise and a support
landmark in another. The exercise definition's support context decides whether
the runtime record receives `support_role = support_consistency`.

Moving primary landmarks follow the same explicit evidence-variant policy.
Every coordinate-derived movement-path target should be able to emit at least an
`xy` and an `xyz` variant. This keeps recording-view evidence and
depth-sensitive evidence in the same audit trail while leaving score gravity to
Stage 10.

```text
spatial.movement_path.arc_length_xy.<landmark>
    Recording-view movement path in the normalized camera plane. This is the
    preferred scoring candidate when the movement-quality question can be
    answered from x/y evidence and the recording view is compatible with the
    baseline.

spatial.movement_path.arc_length_xyz.<landmark>
    Mixed-axis movement path using normalized x/y and model/candidate z. This
    is depth-sensitive evidence. It remains useful for review and candidate-3D
    comparison, but its score gravity should normally be lower than the `xy`
    variant under the current monocular pipeline.

spatial.movement_path.axis_path_x.<landmark>
spatial.movement_path.axis_path_y.<landmark>
spatial.movement_path.axis_path_z.<landmark>
    Report-only movement-path-axis diagnostics for non-support primary landmarks.
    They expose which axis contributed to the movement-path value and remain
    provenance unless a later validation study promotes a specific axis.
```

Scoring promotion rule:

```text
diagnosis/reporting
    Emit xy, xyz, x, y, and z evidence so the cause of a path-length anomaly is
    visible.

composite scoring
    Prefer `xy` movement path when the exercise definition and camera view support
    a recording-view interpretation. Keep `xyz` available with depth-sensitive
    gravity or corrected-3D-hypothesis provenance. Do not score `xy`, `z`, and
    `xyz` at full strength at the same time, because that double-counts the
    same path through overlapping evidence.
```

Pelvis and hip-center proxies need an explicit coordinate-reference guard.
`left_hip` and `right_hip` remain primary hip landmarks when the exercise
definition declares hip flexion/extension. The derived `pelvis` or
`hip_center` reference is a secondary/control proxy unless a feature explicitly
uses it as a primary task metric.

Do not mark a feature as scoring-ready when it measures the same reference
point that ⑤ Normalization used as the coordinate origin. In a hip-centered
`norm` coordinate frame, the following features can become self-measurements
whose values collapse toward zero and should be report-only until they are
redefined from an independent reference:

```text
control.stability.hip_center_x_std
control.stability.hip_center_z_std
control.compensation.lateral_pelvic_shift.xy
```

The preferred replacement for closed-chain lower-body exercises is a
support-relative pelvis proxy. It should compare the hip/pelvis center with the
exercise-defined support center in recording-view x/y, not with itself:

```text
control.stability.hip_center_support_center_xy_drift
    Recording-view x/y displacement of hip_center relative to the bilateral
    support center. This represents pelvis-over-base-of-support control, not
    absolute camera-space translation.
```

Additional pelvis alignment proxies may be emitted when supported by the
recording view and exercise definition:

```text
control.compensation.pelvis_line_tilt
    Left-right hip height/line tilt proxy in a recording-view plane that can
    support frontal-plane interpretation.

control.compensation.pelvis_rotation.xyz
    Transverse-plane pelvis rotation proxy. Because monocular depth and
    near/far-side ordering can dominate this signal, it should remain
    low-gravity or report-only unless a view/candidate-evidence policy promotes
    it.
```

Use `pelvis_rotation` consistently in exercise definitions and emitted feature
ids. Avoid alternate adjective-based spellings, because the pipeline treats
feature ids as stable scoring keys.

Control records follow the same public/private metadata split as spatial and
temporal records.

```text
Public record fields
    feature_id, value, unit, availability, depth_dependency, focus_tier,
    landmark_ids, support_role, coordinate_reference, evaluation_domain,
    evidence_axes, feature_family

Private registry/profile fields
    knee profile      valgus/varus compensation links and frontal-plane proxy
    ankle profile     heel-lift/support-contact compensation link
    pelvis_reference  derived pelvis-control and rotation proxy scope
    trunk_reference   trunk-flexion compensation proxy scope
```

`control.compensation.heel_lift.xy.<side>` is a closed-chain support-contact proxy.
Under the current monocular pipeline it should use the recording-view vertical
axis, not model-depth `z`, because MediaPipe monocular depth is not reliable
enough to decide whether the heel left the support surface. A future
depth-sensitive heel-lift diagnostic must use an explicit feature id and reduced
gravity instead of silently reusing the support-contact score.

Coordinate-derived control records also carry explicit evidence variants. The
recording-view candidate uses an `xy` feature-id token; any depth-mixed candidate
uses an `xyz` token and must be scored with reduced gravity or withheld when
monocular model-depth reliability is low. Do not emit a variantless control
feature id for coordinate-derived compensation, because it hides whether the
value came from recording-view evidence or model-depth evidence.

Current control variant contract:

```text
control.compensation.knee_valgus.xy.<side>
control.compensation.knee_varus.xy.<side>
    Recording-view hip-knee-ankle deviation proxy. This is the current scoring
    candidate for squat/lunge knee tracking. A `knee_valgus.xyz` or
    `knee_varus.xyz` variant is not emitted until a corrected/body-frontal
    plane can define medial/lateral direction without relying on raw monocular
    depth.

control.compensation.excessive_trunk_flexion.xy
    Recording-view shoulder-center to hip-center trunk-line angle from the
    image vertical. This is the preferred public scoring candidate when the
    camera view supports sagittal interpretation.

control.compensation.excessive_trunk_flexion.xyz
    Depth-mixed trunk-line angle using the same recording-view vertical axis
    but a 3D vector norm. It is comparative evidence only and should carry
    reduced gravity under the current monocular pipeline.

control.compensation.heel_lift.xy.<side>
    Recording-view heel elevation above the support baseline. Evidence axes may
    be `y` because the feature uses the vertical component of the `xy` plane.

control.compensation.pelvis_rotation.xyz
    Depth-sensitive left-right hip model-depth asymmetry. It remains
    low-confidence/report-only unless view/candidate evidence supports a
    transverse-plane interpretation.
```

---

## 5. Availability And View Reliability

Feature extraction may compute a numeric value even when the camera view or pose
model does not support scoring that value. Therefore `FeatureRecord.availability`
is the scoring gate for ⑩.

```text
assessed
    Eligible for composite scoring if a baseline exists.

low_confidence
    Numeric value can be reported, but is withheld from composite scoring by
    default.

not_assessed
    Do not use for scoring; report only as unavailable/provenance.
```

The resolver combines:

```text
view_reliability             exercise_definition.view_metric_reliability
landmark_quality             visibility / coverage / preprocessing context
depth_dependency             none | low | moderate | high | unknown
model_depth_reliability      high | moderate | low | unknown
swap or far-side risk         from ④ Preprocessing and ⑧ side-role context
camera_zone                  from annotation or recording metadata
role_context                 active/support/near/far side when available
```

For side-view or near-side-view squat recordings, sagittal and centerline
features may remain assessed when their gates pass. Depth-sensitive bilateral
role-alignment evidence from a rotated monocular skeleton should be `low_confidence` or
`not_assessed` unless frontal/front-oblique evidence supports the interpretation.

For unilateral or alternating exercises, reliability should use role labels such
as `forward_leg`, `trailing_leg`, `active_side`, and `support_side` rather than
raw anatomical left/right alone.

---

## 6. Phase-Aware Features

When ⑦ provides a `phase` column, these families may emit both rep-level and
phase-level records:

```text
spatial.range_of_motion
spatial.movement_path
temporal.tempo
control.stability
```

Rules:

```text
Rep-level record      phase = None
Phase-level record    phase = "Descent" etc.; feature_id gets a lower-snake-case suffix
source_fields         include phase_segmentation provenance
control.compensation  rep-level only unless a separate phase-specific rule is defined
```

`summarize_phase_to_rep()` may add derived rep-level summaries, such as
descent/ascent range-of-motion ratios for phase sequences that explicitly use
those labels. It is additive and must not mutate input records.
The ⑧ pipeline report includes these derived summary records beside the direct
feature records so saved outputs and downstream checks use the same feature set.

---

## 7. Output Contract

```python
@dataclass
class FeatureRecord:
    feature_id: str
    exercise_id: str
    rep_id: int | None
    value: float
    unit: str
    source_fields: list[str]
    note: str | None = None
    phase: str | None = None
    view_reliability: str = "unknown"
    availability: str = "assessed"
    availability_reasons: list[str] = field(default_factory=list)
    camera_zone: str | None = None
    role_context: dict[str, str] | None = None
    depth_dependency: str = "unknown"
    model_depth_reliability: str = "unknown"
    landmark_quality: str = "unknown"
    focus_tier: str = "primary"
    landmark_ids: list[str] = field(default_factory=list)
    support_role: str | None = None
    coordinate_reference: str = "unknown"
    evaluation_domain: str = "unknown"
    evidence_axes: str | None = None
    feature_family: str | None = None
```

`features_to_dataframe()` flattens record lists for tabular output while
preserving phase, availability, camera-zone, and provenance fields.

Saved stage-check outputs should keep the feature table and diagnostic context
separate:

```text
data/processed/features/<recording_id>_features.csv
    Tabular `features_to_dataframe()` output. Required columns include
    feature_id, exercise_id, rep_id, phase, value, unit, source_fields,
    availability, availability_reasons, view_reliability, depth_dependency,
    model_depth_reliability, landmark_quality, focus_tier, landmark_ids,
    support_role, coordinate_reference, evaluation_domain, evidence_axes,
    feature_family, camera_zone, and role_context.

data/processed/features/<recording_id>_feature_context.json
    Feature-context and role-context report for ⑧. This file records why
    side-role context was applied, skipped, or withheld, without changing
    feature values or creating scores.

data/processed/features/<recording_id>_feature_qc.json
    Compact counts for follow-along checks, such as row counts, availability
    counts, feature-family counts, phase counts, and missing source_fields.
```

CSV round-trips must preserve the row count and required columns. Structured
fields such as `source_fields`, `availability_reasons`, `landmark_ids`, and
`role_context` may be serialized for the CSV file, but the in-memory records
remain the canonical object contract for later code paths.

---

## 8. Audits

⑧ may emit diagnostic audits beside the feature records.

```text
Feature registry coverage
    Reports which YAML feature_domain entries and compensation candidates are
    implemented, routed to another step, unsupported, or declared but deferred.

Analysis-disrupting pattern detectability
    Classifies performance_protocol.analysis_disrupting_patterns as
    pose_detectable_scoring_candidate, acquisition_control_factor,
    interpretation_limitation_factor, or unknown.
```

Audits are provenance/reporting outputs. They do not mutate coordinates, exclude
repetitions, or create scores by themselves.

---

## 9. Entry Point

```python
from movement.features import (
    extract_rep_features,
    features_to_dataframe,
    summarize_phase_to_rep,
)

records = extract_rep_features(df, exercise_definition)
records += summarize_phase_to_rep(records)
feat_df = features_to_dataframe(records)
```

---

## 10. Relationship To Other Steps

- ⑦ Segmentation provides `rep_id` and optional `phase`; missing phase labels
  produce rep-level features only.
- Side-role context is resolved inside ⑧, then attached only to role-aware
  feature records. The public stage-check path reviews this context in
  `27_feature_extraction_test.ipynb`.
- ⑨ Biomech Proxy consumes the same normalized coordinates but emits
  `BiomechRecord`, not `FeatureRecord`.
- ⑩ Biomarker Derivation wraps all features as pass-through biomarkers and uses
  only `availability == assessed` features for composite scoring.
- ⑫ Simulation may later use pose-detectable audit entries as perturbation
  candidates.

---

## 11. Code Mapping

```text
src/movement/features/__init__.py        FeatureRecord, extract_rep_features,
                                         FeatureContext, resolve_feature_context,
                                         apply_feature_context,
                                         audits, summarize_phase_to_rep,
                                         features_to_dataframe
src/movement/features/spatial.py         range of motion, movement path,
                                         support consistency, role alignment
src/movement/features/temporal.py        tempo, variability
src/movement/features/control.py         stability, compensation
src/movement/features/compensation.py    COMPENSATION_RULES registry
src/movement/record_metadata.py          record context and landmark-id helpers
data/reference/landmarks/common_landmark_metadata.yaml
                                         stable joint/landmark metadata registry
data/reference/landmarks/joint_profiles.yaml
                                         joint/profile-specific private metadata
tests/test_feature_view_reliability.py   availability metadata
tests/test_feature_registry_coverage.py  feature/compensation coverage audit
tests/test_analysis_disrupting_patterns.py detectability audit
tests/test_features_phase_grouping.py    phase-level feature behavior
tests/test_feature_context_resolution.py feature-context resolution/application
```

---

## 12. Planned Extensions

- Review alternating/unilateral samples before expanding side-role context from
  bilateral provenance to active/support-side feature families.
- More compensation rules after source fields, visibility policy, and tests exist.
- Per-feature landmark coverage instead of coarse preprocessing summaries.
- Role-aware feature families for lunge and plank shoulder tap.
- Reporting views that show computed-but-withheld features beside scored features.
