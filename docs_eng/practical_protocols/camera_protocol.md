# Camera Filming Protocol per Exercise

**Document Version:** 1.2.3
**Last Updated:** 2026-05-08
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

---

## 2. Reference-Mat Physical Anchor

A reference mat is used as a physical anchor so the user can estimate distance and
direction without a separate calibration device. A standard reference mat is treated
as approximately 180 cm × 60 cm.

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

## 4. One-Take Session Protocol

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

## 5. Pipeline Usage

The filming protocol is used as metadata in the following locations.

```text
data/camera/camera_zones.yaml
    shared polar-ring definitions for Z1-Z8 zones, reference_origin, H1-H3 height levels, anchor, and out_of_zone policy

data/definitions/exercises/<exercise_id>.yaml
    exercise-specific recommended zone, height, and observation purpose in camera_protocol

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
camera-angle correction        not applied
coordinate reprojection        not applied
```

The effect of viewpoint variation on metrics is evaluated as a robustness condition
in ⑫ Simulation. ⑪ Visualization may display filming-condition warnings next to
the interpretation output.

Related documents:

- [exercise_performance_protocol.md](exercise_performance_protocol.md)
- [02_annotation.md](../pipeline/02_annotation.md)
- [03_exercise_definition.md](../pipeline/03_exercise_definition.md)
- [12_insilico_simulation.md](../pipeline/12_insilico_simulation.md)
