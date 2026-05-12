# Camera Filming Protocol per Exercise

**Document Version:** 1.3.0
**Last Updated:** 2026-05-12
**Korean Sync:** [docs/practical_protocols/camera_protocol.md](../../docs/practical_protocols/camera_protocol.md) is the matching Korean document.

This document defines the data-acquisition guide used to reduce distortion in a
monocular vision setup and to keep analysis conditions reproducible. It minimizes
artificial control for in-the-wild use while defining the minimum filming conditions
needed to observe exercise-specific compensation patterns.

This protocol is not a coordinate-correction algorithm. Data filmed outside the
recommended zone is not rejected by the pipeline; filming conditions are retained
as provenance and warning metadata.

---

## 1. Camera Zone Matrix

The subject or reference-mat center is defined as `reference_origin`, not as a
filming zone. Camera placement is modeled as a circular filming ring around this
origin, with the default recommended distance set to 200-250 cm. A filming setup is
expressed by combining azimuth zone, distance on this ring, and height level.

Zones describe viewing direction, not different distance rules. Each zone uses the
same recommended radial distance and an azimuth tolerance of about ±10 degrees.
In the top-down diagram, `Z1` is drawn at the top and positive azimuth increases
clockwise; therefore `Z4` appears on the lower-right side of the ring and `Z6`
on the lower-left side.

![Camera-zone protocol for exercise filming](assets/camera_zone_protocol.png)

*Figure 1. Camera zones are defined as azimuth sectors on the same 200-250 cm
filming ring around `reference_origin`; height levels are recorded separately.*

| Zone | Azimuth / Position | Main Observation Plane | Ring Position |
|---|---|---|---|
| Z1 | Frontal, 0 degrees | Frontal | 200-250 cm radius, ±10 degrees |
| Z2 | Front-right oblique, +45 degrees | Frontal + sagittal mixed | 200-250 cm radius, ±10 degrees |
| Z3 | Right side, +90 degrees | Sagittal | 200-250 cm radius, ±10 degrees |
| Z4 | Rear-right oblique, +135 degrees | Posterior + sagittal mixed | 200-250 cm radius, ±10 degrees |
| Z5 | Rear, 180 degrees | Posterior frontal | 200-250 cm radius, ±10 degrees |
| Z6 | Rear-left oblique, -135 degrees | Posterior + sagittal mixed | 200-250 cm radius, ±10 degrees |
| Z7 | Left side, -90 degrees | Sagittal | 200-250 cm radius, ±10 degrees |
| Z8 | Front-left oblique, -45 degrees | Frontal + sagittal mixed | 200-250 cm radius, ±10 degrees |

Height is recorded using three levels.

| Height | Range | Use |
|---|---|---|
| H1 | 0-30 cm above the floor | Floor-based exercises such as plank or pike push-up |
| H2 | 80-110 cm above the floor | Lower-body exercises such as squat or lunge |
| H3 | 140-170 cm above the floor | Full-body or upper-body-focused exercises |

When height metadata is used by an optional canonicalization prior, the height
level selects a body-reference anchor rather than a calibrated camera model.

| Height | Canonicalization anchor when protocol height matches | Rationale |
|---|---|---|
| H1 | support/ankle-level anchor | Low camera placement is closest to support contacts in floor-based or low-position tasks. |
| H2 | pelvis / hip-center anchor | Squat and lunge recordings are intended to place the camera near lower-body center height, making the pelvis the most conservative lateral-width reference. |
| H3 | shoulder-center / shoulder-line anchor | Upper-body or full-body recordings are intended to keep shoulder-line geometry near the least distorted central observation height. |

This anchor selection is not used when the observed height is unknown or mismatched
unless the researcher explicitly overrides the metadata during review.

---

## 2. Reference-Mat Physical Anchor

A reference mat is used as a physical anchor so the user can estimate distance and
direction without a separate calibration device. A standard reference mat is treated
as approximately 180 cm × 60 cm.

The mat is not a calibration target that is automatically detected in the video.
The pipeline does not detect mat corners, infer mat size, estimate perspective
transforms, or use the mat for camera calibration. Reference-mat information is
used only as human-facing placement guidance and operational metadata for
`reference_mat_used` and filming-condition warnings.

| Item | Zones | Guidance |
|---|---|---|
| Distance | All zones | Step back about three steps, or 200-250 cm, until the full reference mat is visible on the smartphone screen. |
| Frontal filming | `Z1` | Place the camera on the front centerline of the reference mat and aim at `reference_origin`. The left and right sides of the mat should appear approximately symmetric in the frame. This option is kept for current or future exercises where frontal-plane tracking is the primary observation target. |
| Rear filming | `Z5` | Place the camera on the rear centerline of the reference mat and aim at `reference_origin`. This preserves the same origin while allowing posterior-view exercises or posterior compensation patterns to be filmed later. |
| Front-oblique filming | `Z2` / `Z8` | Place the camera about 45 degrees from the front side and aim toward the nearest front corner of the reference mat or the `reference_origin`. This supports mixed frontal-sagittal observation. |
| Rear-oblique filming | `Z4` / `Z6` | Place the camera about 45 degrees from the rear side and aim toward the nearest rear corner of the reference mat or the `reference_origin`. This is reserved for posterior-sagittal mixed observation when future exercises require it. |
| Side filming | `Z3` / `Z7` | Align the long edge of the reference mat with the screen center axis and aim at `reference_origin`. This supports sagittal-plane observation. |

Data is still accepted when no reference mat is available or when the recommended
distance cannot be met. The condition is recorded in filming metadata and reported
as a warning.

---

## 3. Per-Exercise Recommended Settings

| Exercise | Recommended Zone | Recommended Height | Observation Purpose |
|---|---|---|---|
| Squat | Z2 / Z8 | H2 | Observe knee valgus and hip-flexion depth from front-oblique views |
| Lunge | Z3 / Z7 | H2 | Observe anterior knee travel and sagittal trunk/lower-limb alignment |
| Pike push-up | Z3 / Z7 | H1 | Observe shoulder angle and hip-hinge geometry |
| Plank shoulder tap | Z2 / Z8 | H1 | Observe pelvic rotation and lateral sway during weight shift |

The recommended zone describes the best observation condition. The pipeline still
processes data outside the recommendation, but interpretation should display possible
confidence degradation caused by the filming condition.

---

## 4. View-Dependent Metric Reliability

The recommended camera zone is not a binary accept/reject rule. It is a reliability
prior for each metric family. The same recording may support one metric well while
making another metric low-confidence. The system should therefore separate:

```text
metric_computed        whether the numeric feature can be calculated
view_reliability       whether the filming view supports that interpretation
feature_availability   whether visibility, geometry, swap risk, and view reliability
                       allow the feature to enter scoring
```

Reliability levels are interpreted as:

| Level | Meaning | Default scoring use |
|---|---|---|
| high | The view directly supports the metric family. | Eligible for scoring if landmark quality is sufficient. |
| moderate | The view supports the metric but with known tradeoffs. | Eligible with confidence/provenance note. |
| low | The metric may be computable but is strongly view-limited. | Report/review only unless confirmed by stronger evidence. |
| not_assessed | The view does not support a meaningful read. | Do not score. |

### 4.1 Bilateral Symmetric Exercises

For bilateral symmetric exercises such as squat, left/right symmetry and frontal
alignment depend strongly on whether the camera directly observes the frontal
plane. Sagittal ROM and depth depend strongly on whether the camera observes the
side/sagittal plane. Front-oblique views are recommended when both families must
be reviewed from one recording.

| Zone family | Typical zones | Higher-reliability metric families | Lower-reliability metric families |
|---|---|---|---|
| Frontal | Z1, Z5 | bilateral symmetry, frontal knee tracking, lateral pelvic shift, shoulder/pelvis line tilt | sagittal ROM, depth, trunk flexion, heel lift |
| Front-oblique | Z2, Z8 | mixed symmetry + depth review, knee tracking, hip-center stability | fine-grained pure sagittal or pure frontal interpretation |
| Side | Z3, Z7 | depth, sagittal hip/knee/ankle ROM, trunk lean, heel lift, tempo/smoothness | bilateral symmetry, knee valgus/varus, lateral pelvic shift |
| Rear-oblique | Z4, Z6 | posterior-frontal alignment plus partial sagittal context when needed | anterior knee tracking and front-facing landmark interpretation |

Squat is therefore recommended from Z2/Z8 rather than because Z2/Z8 is perfect,
but because it gives the most balanced single-view reliability for knee tracking,
descent depth, and general bilateral coordination. If a squat is filmed from Z3/Z7,
sagittal features may remain high-confidence while symmetry is low-confidence or
not assessed. If it is filmed from Z1, frontal alignment may be high-confidence
while depth, sagittal ROM, trunk flexion, and heel lift become lower-confidence.

### 4.2 Unilateral Or Alternating Exercises

For unilateral or alternating exercises, the system must avoid treating anatomical
left/right as the only comparison axis. The preferred interpretation is role-based:

```text
forward_leg / trailing_leg       lunge and split-stance tasks
active_side / support_side       alternating or unilateral tasks
near_side / far_side             camera-facing reliability context
```

For side-view unilateral tasks such as lunge, the view often supports sagittal
role-specific mechanics better than frontal-plane compensation. However, when the
participant switches sides, the forward or active limb may also switch between
near-side and far-side visibility. Side-to-side comparison is therefore eligible
for scoring only when active-side provenance and near/far-side reliability are
recorded.

| Zone family | Typical zones | Higher-reliability metric families | Lower-reliability metric families |
|---|---|---|---|
| Frontal | Z1, Z5 | side order, step width, lateral trunk lean, pelvis drop/shift, frontal knee alignment | anterior knee travel, rear-hip extension, sagittal trunk lean, depth |
| Front-oblique | Z2, Z8 | mixed active-side attribution, partial frontal alignment, partial sagittal ROM | precise rear-limb sagittal ROM or pure frontal compensation |
| Side | Z3, Z7 | anterior knee travel, forward/rear limb sagittal ROM, rear-hip extension, trunk lean, step length | knee valgus/varus, pelvis drop, lateral trunk lean, left/right symmetry |
| Rear-oblique | Z4, Z6 | posterior support alignment and partial sagittal context | anterior knee tracking and active-limb frontal details |

Thus, a side-view lunge can be high-confidence for forward-leg knee travel and
trunk alignment while low-confidence for frontal-plane knee valgus. A frontal
lunge can be high-confidence for step width and pelvis drop while low-confidence
for rear-hip extension or anterior knee travel. These are view-dependent confidence
states, not automatic movement-quality penalties.

---

## 5. One-Take Session Protocol

1. Each set is filmed as 10 continuous repetitions without a separate static waiting
   period after recording starts.
2. When multiple sets are filmed, each set may be stored as a separate file, while
   `session_id` and `set_index` preserve that the files belong to one time-series
   session.
3. No artificial T-pose calibration is required. Normalization keeps the existing
   rule: use the sequence-level median torso length and the per-frame hip center.

Ten continuous repetitions are an acquisition strategy for observing later-repetition
changes that may appear with fatigue. This does not claim to diagnose fatigue; the
pipeline uses it to quantify trends across repetitions.

---

## 6. Pipeline Usage

The filming protocol is used as metadata in the following locations.

```text
data/camera/camera_zones.yaml
    shared polar-ring definitions for Z1-Z8 zones, reference_origin, H1-H3 height levels, anchor, and out_of_zone policy

data/definitions/exercises/<exercise_id>.yaml
    exercise-specific recommended zone, height, observation purpose, and planned
    view_metric_reliability map

Annotation or recording metadata
    optional columns such as session_id, recording_id, set_index, camera_zone,
    camera_height_level, reference_mat_used, filming_protocol_status
```

Processing policy:

```text
recommended zone matched       record as provenance and process normally
recommended zone mismatched    warn and process normally
filming zone missing           record as unknown and process normally
reference mat not used         warn, but do not force exclusion
reference-mat detection        not applied
mat-based calibration          not applied
calibrated camera-angle correction not applied
coordinate reprojection        not applied
pose-internal floor correction optional in ⑤; not interpreted as calibration
height-aware lateral-width canonicalization optional in ⑤; not interpreted as lens correction
side-view depth-derived symmetry      not scored unless feature availability gate passes
view-metric reliability map           used as confidence/provenance, not coordinate correction
```

The floor-relative filter inside ⑤ Normalization is not camera-angle correction in this filming protocol.
It does not estimate camera intrinsic/extrinsic parameters or reproject coordinates
into physical space. It is an optional artifact-mitigation step that estimates a
pseudo-floor reference inside the normalized pose coordinate system from
support-contact landmarks. It assumes a level-camera target by default
(`camera_pitch_deg=0.0`, `camera_roll_deg=0.0`), but those parameters may be
adjusted to preserve a known pose-coordinate pseudo-floor slope. The current
review transform is `rigid_rotation`, which rotates the pose coordinate set
together rather than changing only support-contact height. This remains a
pose-internal prior, not camera calibration. For detailed policy, see
[05_normalization.md](../pipeline/05_normalization.md).

The optional protocol-height lateral-width prior inside ⑤ Normalization may use
`camera_height_level` and the exercise's `recommended_height` as a gate. If the
height matches, it can choose an H1/H2/H3 body anchor and conservatively attenuate
depth-dependent lateral-width bias in review-only `canon` coordinates. For the
current squat protocol, H2 maps to the pelvis / hip-center anchor. This prior does
not model lens distortion, estimate camera intrinsics, or expand low-confidence
far-side landmarks into a claimed true location.

For side-view or near-side-view recordings, rotating the monocular 3D pose into a
frontal view does not create a true frontal observation. Large apparent left-right
imbalance in that rendering should be treated as a depth-inference confidence issue
unless an actual frontal or front-oblique recording supports the same finding.
Therefore bilateral symmetry features are only eligible for scoring when the
feature-availability gate confirms sufficient visibility, plausible segment
geometry, low swap risk, and a view that supports left-right interpretation.

The effect of viewpoint variation on metrics is evaluated as a robustness condition
in ⑫ Simulation. ⑪ Visualization may display filming-condition warnings next to
the interpretation output.

Related documents:

- [exercise_performance_protocol.md](exercise_performance_protocol.md)
- [02_annotation.md](../pipeline/02_annotation.md)
- [03_exercise_definition.md](../pipeline/03_exercise_definition.md)
- [12_insilico_simulation.md](../pipeline/12_insilico_simulation.md)
