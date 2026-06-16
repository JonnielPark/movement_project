# Camera Filming Protocol per Exercise

**Document Version:** 1.4.0
**Last Updated:** 2026-05-21
**Korean Sync:** [docs/practical_protocols/camera_protocol.md](../../docs/practical_protocols/camera_protocol.md) is the matching Korean document.

This document defines minimum filming conditions for reproducible monocular pose
analysis. It is an acquisition guide and provenance schema, not a camera
calibration or coordinate-correction algorithm. Recordings outside the
recommended zone are processed, but their filming condition is retained as
warning/provenance metadata.

---

## 1. Camera Zone Model

`reference_origin` is the subject or reference-mat center. Camera placement is
represented by azimuth zone, radial distance, and height level. The default
recommended distance is a 200-250 cm ring around `reference_origin`.

![Camera-zone protocol for exercise filming](assets/camera_zone_protocol.png)

| Zone | Direction | Main observation plane |
|---|---|---|
| Z1 | frontal, 0 degrees | frontal |
| Z2 | front-right oblique, +45 degrees | frontal + sagittal mixed |
| Z3 | right side, +90 degrees | sagittal |
| Z4 | rear-right oblique, +135 degrees | posterior + sagittal mixed |
| Z5 | rear, 180 degrees | posterior frontal |
| Z6 | rear-left oblique, -135 degrees | posterior + sagittal mixed |
| Z7 | left side, -90 degrees | sagittal |
| Z8 | front-left oblique, -45 degrees | frontal + sagittal mixed |

All zones use the same radial-distance recommendation and about +/-10 degrees
azimuth tolerance.

| Height | Range | Main use |
|---|---|---|
| H1 | 0-30 cm above floor | floor-based exercises |
| H2 | 80-110 cm above floor | lower-body exercises |
| H3 | 140-170 cm above floor | upper-body or full-body exercises |

Optional canonicalization priors may use height only to select a conservative
body anchor:

```text
H1 → support / ankle-level anchor
H2 → pelvis / hip-center anchor
H3 → shoulder-center / shoulder-line anchor
```

This is not lens correction, camera intrinsic/extrinsic estimation, or physical
reprojection.

## 2. Reference Mat

A reference mat is a human-facing placement aid, roughly 180 cm x 60 cm. It helps
the user estimate distance and direction without a calibration device.

Pipeline policy:

```text
mat corners detected automatically      no
mat size inferred from video            no
perspective transform estimated         no
camera calibration performed            no
metadata stored                         reference_mat_used, filming warnings
```

If no mat is available, the recording is still accepted and the condition is
recorded as metadata.

## 3. Recommended Settings

| Exercise | Recommended zone | Height | Main observation purpose |
|---|---|---|---|
| Squat | Z2 / Z8 | H2 | knee tracking + hip-flexion depth |
| Lunge | Z3 / Z7 | H2 | anterior knee travel + sagittal trunk/lower-limb alignment |
| Pike push-up | Z3 / Z7 | H1 | shoulder angle + inverted-V hip geometry |
| Plank shoulder tap | Z2 / Z8 | H1 | pelvic rotation + lateral sway during weight shift |

The recommended setting is a reliability prior, not an inclusion rule. The same
recording may support one metric family well and another poorly.

## 4. View Reliability

Feature interpretation separates three concepts:

```text
metric_computed        numeric feature can be calculated
view_reliability       camera view supports the intended interpretation
feature_availability   visibility, geometry, swap risk, and view reliability allow scoring
```

Reliability levels:

```text
high            eligible for scoring when landmark quality is sufficient
moderate        eligible with confidence/provenance note
low             report/review only unless stronger evidence supports it
not_assessed    do not score
```

View-family summary:

| View family | Typical zones | Stronger reads | Weaker reads |
|---|---|---|---|
| Frontal | Z1, Z5 | bilateral symmetry, frontal knee/pelvis/trunk alignment | sagittal ROM, depth, heel lift |
| Oblique | Z2, Z8, Z4, Z6 | mixed frontal-sagittal review | fine-grained pure-plane interpretation |
| Side | Z3, Z7 | sagittal ROM, anterior knee travel, trunk lean, step length | left/right symmetry, valgus/varus, lateral shift |

For unilateral or alternating tasks, interpretation should be role-based:

```text
forward_leg / trailing_leg
active_side / support_side
near_side / far_side
```

Side-to-side scoring is eligible only when active-side provenance and near/far
visibility reliability are recorded.

## 5. Session Protocol

```text
set recording                  one take when possible
default pilot acquisition      3 sets per exercise, 10 counts per set
multi-set storage              separate recording files allowed
session linkage                session_id + set_index
static calibration pose        not required
normalization scale            sequence median torso length + per-frame hip center
```

Ten continuous repetitions are used to observe within-set trends. This does not
diagnose fatigue.

## 6. Pipeline Use

Primary data locations:

```text
data/camera/camera_zones.yaml
data/protocols/camera/<exercise_id>.yaml
annotation columns: camera_zone, camera_height_level, reference_mat_used,
                    filming_protocol_status
```

Processing policy:

```text
recommended zone matched       process normally, record provenance
recommended zone mismatched    warn and process normally
filming zone missing           record unknown and process normally
reference mat absent           warn, no forced exclusion
coordinate reprojection        not applied
view_metric_reliability        confidence/provenance gate, not coordinate correction
```

⑥ Canonicalization may add pose-internal floor or height priors as candidate
evidence. These priors do not create a true frontal observation from a side view.
Bilateral symmetry features enter scoring only when the feature-availability gate
confirms sufficient visibility, plausible segment geometry, low swap risk, and a
supportive view.

Related documents:

- [exercise_performance_protocol.md](exercise_performance_protocol.md)
- [02_annotation.md](../pipeline/02_annotation.md)
- [03_exercise_definition.md](../pipeline/03_exercise_definition.md)
- [05_normalization.md](../pipeline/05_normalization.md)
- [06_canonicalization.md](../pipeline/06_canonicalization.md)
- [13_insilico_simulation.md](../pipeline/13_insilico_simulation.md)
