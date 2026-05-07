# Camera Filming Protocol per Exercise

**Document Version:** 1.0.0
**Last Updated:** 2026-05-08
**Korean Sync:** [docs/camera_protocol.md](../docs/camera_protocol.md) is the matching Korean document.

This document defines the data-acquisition guide used to reduce distortion in a
monocular vision setup and to keep analysis conditions reproducible. It minimizes
artificial control for in-the-wild use while defining the minimum filming conditions
needed to observe exercise-specific compensation patterns.

This protocol is not a coordinate-correction algorithm. Data filmed outside the
recommended zone is not rejected by the pipeline; filming conditions are retained
as provenance and warning metadata.

---

## 1. Camera Zone Matrix

The subject position is defined as `Z5`, and the default recommended camera distance
is 200-250 cm from the subject. A filming setup is expressed by combining camera
azimuth zones and height levels.

| Zone | Azimuth / Position | Main Observation Plane | Physical Range |
|---|---|---|---|
| Z1 | Front-left oblique, about 45 degrees | Frontal + sagittal mixed | 140-175 cm left and 140-175 cm anterior to the subject |
| Z2 | Frontal, 0 degrees | Frontal | 200-250 cm in front of the subject, within ±30 cm lateral offset |
| Z3 | Front-right oblique, about 45 degrees | Frontal + sagittal mixed | 140-175 cm right and 140-175 cm anterior to the subject |
| Z4 | Left side, about 90 degrees | Sagittal | 200-250 cm left of the subject, within ±30 cm anterior-posterior offset |
| Z6 | Right side, about 90 degrees | Sagittal | 200-250 cm right of the subject, within ±30 cm anterior-posterior offset |

Height is recorded using three levels.

| Height | Range | Use |
|---|---|---|
| H1 | 0-30 cm above the floor | Floor-based exercises such as plank or pike push-up |
| H2 | 80-110 cm above the floor | Lower-body exercises such as squat or lunge |
| H3 | 140-170 cm above the floor | Full-body or upper-body-focused exercises |

---

## 2. Yoga-Mat Physical Anchor

A yoga mat is used as a physical anchor so the user can estimate distance and
direction without a separate calibration device. A standard yoga mat is treated as
approximately 180 cm × 60 cm.

| Item | Guidance |
|---|---|
| Distance | Step back about three steps, or 200-250 cm, until the full mat is visible on the smartphone screen. |
| Oblique filming | For `Z1` or `Z3`, align the camera toward the front corner of the mat. |
| Side filming | For `Z4` or `Z6`, align the long edge of the mat with the screen center axis. |

Data is still accepted when no yoga mat is available or when the recommended distance
cannot be met. The condition is recorded in filming metadata and reported as a warning.

---

## 3. Per-Exercise Recommended Settings

| Exercise | Recommended Zone | Recommended Height | Observation Purpose |
|---|---|---|---|
| Squat | Z1 / Z3 | H2 | Observe knee valgus and hip-flexion depth together |
| Lunge | Z4 / Z6 | H2 | Observe anterior knee travel and sagittal trunk/lower-limb alignment |
| Pike push-up | Z4 / Z6 | H1 | Observe shoulder angle and hip-hinge geometry |
| Plank shoulder tap | Z1 / Z3 | H1 | Observe pelvic rotation and lateral sway during weight shift |

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
    shared definitions for Z1-Z6 zones, H1-H3 height levels, anchor, and out_of_zone policy

data/definitions/exercises/<exercise_id>.yaml
    exercise-specific recommended zone, height, and observation purpose in camera_protocol

Annotation or recording metadata
    optional columns such as session_id, recording_id, set_index, camera_zone,
    camera_height_level, mat_anchor_used, filming_protocol_status
```

Processing policy:

```text
recommended zone matched       record as provenance and process normally
recommended zone mismatched    warn and process normally
filming zone missing           record as unknown and process normally
yoga mat not used              warn, but do not force exclusion
camera-angle correction        not applied
coordinate reprojection        not applied
```

The effect of viewpoint variation on metrics is evaluated as a robustness condition
in ⑫ Simulation. ⑪ Visualization may display filming-condition warnings next to
the interpretation output.

Related documents:

- [02_annotation.md](pipeline/02_annotation.md)
- [03_exercise_definition.md](pipeline/03_exercise_definition.md)
- [12_insilico_simulation.md](pipeline/12_insilico_simulation.md)
