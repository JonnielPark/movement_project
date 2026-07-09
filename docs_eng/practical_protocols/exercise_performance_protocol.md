# Exercise Performance Protocol per Exercise

**Document Version:** 1.1.0
**Last Updated:** 2026-05-21
**Korean Sync:** [docs/practical_protocols/exercise_performance_protocol.md](../../docs/practical_protocols/exercise_performance_protocol.md) is the matching Korean document.

This document defines standard performance instructions for data acquisition.
"Standard performance" means a reproducible monocular-pose acquisition target,
not a clinical correction standard. The same failure-point and provenance rules
apply to future exercises.

Camera placement follows [camera_protocol.md](camera_protocol.md). Detailed
biomechanical rationale and score-eligible feature/control-factor distinctions live in
`docs_eng/clinical/exercises/`.

---

## 1. Common Rules

```text
default pilot unit          1 exercise/day, 3 sets/exercise, 10 counts/set
recording structure         one take per set when possible
rest                        2-3 minutes between sets; 15-20 minutes between exercise types
clothing                    joints visible; avoid loose clothes hiding landmarks
environment                 no mirror reflections or other people in frame
arm motion                  fix hands when arm swing is not the target
participant safety          stop with pain or injury risk
metadata                    record actual count and performance notes
```

Do not perform artificially cleaner repetitions for the camera. If posture breaks
down, continue only within a pain-free range and record what happened.

## 2. Failure-Point Policy

Every exercise supports performance failure-point recording. A performance failure
point is the first rep/frame, or the recording endpoint, where the participant can
no longer maintain the core task requirement consistently:

```text
baseline posture
range of motion
rhythm
base of support
left-right sequence
```

This marker is acquisition/annotation provenance. It does not diagnose strength,
fatigue, or disease, and it is not an automatic score penalty.

Analysis-disrupting patterns are recorded in notes. Patterns reproducibly visible
in joint-point time series may become score-eligible features; patterns that cannot be
separated reliably from pose data remain acquisition-control or interpretation
limitation factors.

## 3. Per-Exercise Protocols

| Exercise | Image | Camera | Count target | Participant cue | Analysis-disrupting patterns |
|---|---|---|---|---|---|
| Squat | `assets/exercise_squat.png` | Z2/Z8, H2 | 10 reps | Feet about shoulder-width; hands fixed; sit hips back, descend near thigh-parallel, stand up. | arm swing assist; heel lift or foot repositioning; knees moving inward/outward; inconsistent depth; excessive trunk folding |
| Lunge | `assets/exercise_lunge.png` | Z3/Z7, H2 | 5 reps each front foot | Step one foot forward; hands on pelvis/waist; descend vertically near 90-degree knees; switch front foot without turning around. | changing step length; arm swing or trunk extension assist; excessive trunk flexion; body turn during side switch; unstable foot contact |
| Pike push-up | `assets/exercise_pike_pushup.png` | Z3/Z7, H1 | 10 reps or clean maximum | Hips high in inverted V; lower crown of head toward floor between hands; press back up with shoulders. | hips dropping toward regular push-up; head moving forward beyond hands; excessive elbow flare; shallow/inconsistent depth; hand/foot repositioning |
| Plank shoulder tap | `assets/exercise_plank_shoulder_tap.png` | Z2/Z8, H1 | 10 protocol cycles | High plank; brace trunk/hips; tap opposite shoulder; one left + one right tap = one protocol cycle. | excessive pelvic rotation/shift; hips too high/low; hand/foot repositioning; wrong side order; hand lift without tap |

Detailed rationale:

```text
squat                ../clinical/exercises/squat.md
lunge                ../clinical/exercises/lunge.md
pike_pushup          ../clinical/exercises/pike_pushup.md
plank_shoulder_tap   ../clinical/exercises/plank_shoulder_tap.md
```

## 4. Pipeline Use

Performance protocol fields are represented in split YAML:

```text
data/protocols/performance/<exercise_id>.yaml
```

Annotation may record:

```text
performance_protocol_status
actual_rep_count
failure_point_frame
failure_rep_id
failure_reason
performance_note
rep_side_sequence
side_block_size
rep_unit
protocol_cycle_id
```

These fields are provenance for reports, ⑦ Feature Extraction role context, feature
availability, and interpretation-confidence notes. They are not automatic
movement-quality penalties by themselves.
