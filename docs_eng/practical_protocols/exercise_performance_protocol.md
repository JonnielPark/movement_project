# Exercise Performance Protocol per Exercise

**Document Version:** 1.1.5
**Last Updated:** 2026-07-14
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
single-block example        squat, 1 set, 10 repetitions
multi-block example         Korean National Gymnastics draft; section/count protocol pending authoring
recording structure         one take per set when possible
rest                        exercise-session rest is one uniform value between blocks for now
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

| Exercise | Status | Image | Camera | Count target | Participant cue | Analysis-disrupting patterns |
|---|---|---|---|---|---|---|
| Squat | Illustrative single-block repeated-exercise example | `assets/exercise_squat.png` | Z2/Z8, H2 | 1 set × 10 reps | Feet about shoulder-width; hands fixed; sit hips back, descend near thigh-parallel, stand up. | arm swing assist; heel lift or foot repositioning; knees moving inward/outward; inconsistent depth; excessive trunk folding |
| Korean National Gymnastics | Illustrative draft multi-block sequence example; section performance protocol pending | pending | Z1, H2 | repeat-pass acquisition/analysis session; section/count unit TBD | Follow the acquired/analyzed repeat-pass order; detailed section cues pending review | Record sequence/event notes only until reviewed; do not turn unreviewed patterns into penalties |
| Lunge | Retained prior example artifact | `assets/exercise_lunge.png` | Z3/Z7, H2 | retained YAML protocol | Step one foot forward; hands on pelvis/waist; descend vertically near 90-degree knees; switch front foot without turning around. | changing step length; arm swing or trunk extension assist; excessive trunk flexion; body turn during side switch; unstable foot contact |
| Pike push-up | Retained prior example artifact | `assets/exercise_pike_pushup.png` | Z3/Z7, H1 | retained YAML protocol | Hips high in inverted V; lower crown of head toward floor between hands; press back up with shoulders. | hips dropping toward regular push-up; head moving forward beyond hands; excessive elbow flare; shallow/inconsistent depth; hand/foot repositioning |
| Plank shoulder tap | Retained prior example artifact | `assets/exercise_plank_shoulder_tap.png` | Z2/Z8, H1 | retained YAML protocol | High plank; brace trunk/hips; tap opposite shoulder; one left + one right tap = one protocol cycle. | excessive pelvic rotation/shift; hips too high/low; hand/foot repositioning; wrong side order; hand lift without tap |

Detailed rationale:

```text
squat                         ../clinical/exercises/squat.md
Korean National Gymnastics    ../clinical/exercises/korean_national_gymnastics.md
lunge                         ../clinical/exercises/lunge.md
pike_pushup                   ../clinical/exercises/pike_pushup.md
plank_shoulder_tap            ../clinical/exercises/plank_shoulder_tap.md
```

## 4. Pipeline Use

Performance protocol fields are represented in split YAML:

```text
data/protocols/performance/<exercise_id>.yaml
```

This file describes performance instructions inside one exercise definition. When
several exercise definitions are composed into one session, planned rest between
blocks is represented separately:

```text
data/definitions/exercise_sessions/<exercise_session_id>.yaml
rest_policy.rest_between_blocks_s
```

For now that rest value is session-wide and uniform. Per-block rest overrides are
not supported.

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
