# Exercise Performance Protocol per Exercise

**Document Version:** 1.0.2
**Last Updated:** 2026-05-08
**Korean Sync:** [docs/practical_protocols/exercise_performance_protocol.md](../../docs/practical_protocols/exercise_performance_protocol.md) is the matching Korean document.

This document defines standard performance instructions, participant-facing cues,
and analysis-disrupting performance patterns for the four target exercises. Here,
"standard performance" means a reproducible acquisition target for monocular pose
analysis, not a clinical correction standard.

Shared camera position and height definitions follow [camera_protocol.md](camera_protocol.md).

---

## 1. Common Principles

1. Each set should be filmed in one take when possible, without a separate static
   waiting period after recording starts.
2. For pilot pipeline-validation data, the default acquisition unit is one exercise
   per day, 3 sets per exercise, and 10 repetitions per set. Store each set as a
   separate recording when possible.
3. Rest for about 2-3 minutes between sets, or until breathing has returned close
   to baseline. If two or more exercise types must be filmed on the same day, rest
   for at least 15-20 minutes between exercise types.
4. Wear exercise clothing that allows the main joints to be detected. Very loose
   shirts or wide pants should be avoided because they can hide knee, hip, shoulder,
   or trunk landmarks.
5. Film in an independent space without mirror reflections or other people entering
   the frame, so the pose detector does not confuse the target participant with
   another body or reflected body.
6. If the posture deteriorates near the end of a set, do not artificially perform
   cleaner-looking repetitions for the camera. Continue naturally only within a
   pain-free range, and stop immediately if pain or injury risk appears.
7. The target is 10 repetitions. If the participant cannot complete 10 repetitions,
   record the maximum clean repetitions before the posture fully breaks down, and
   store the actual count in annotation or recording metadata.
8. When arm motion is not the target of analysis, the hands should be fixed so arm
   swing does not contaminate the intended joint trajectory.
9. The "analysis-disrupting performance patterns" below are not automatic exclusion
   rules. They are candidates for data-quality warnings, annotation notes,
   synthetic distortion design, or future YAML-based quality rules.

---

## 2. Per-Exercise Protocols

### 2-1. Squat

**Camera Setup**

```text
Zone: Z2 / Z8
Height: H2
```

Place the camera at a front-oblique position, either `Z2` or `Z8`, relative to
the reference mat. Set the lens around pelvis or navel height, approximately
80-110 cm.

**Measurement Rationale**

This setup supports simultaneous observation of frontal-plane knee tracking and
hip-flexion depth.

**Participant Cue**

1. Stand with feet about shoulder-width apart. Cross both hands over the chest or
   hold them lightly in front of the body so arm swing is not used.
2. Sit the hips back as if sitting into a chair, descend until the thighs are nearly
   parallel to the floor, and stand back up.
3. Perform 10 continuous repetitions without resting.

**Analysis-Disrupting Patterns**

- Large arm swing that assists the ascent
- Repeated heel lift or large foot-position changes across repetitions
- Knees moving excessively inward or outward relative to the foot direction
- Depth varying so much that ROM landmarks become unstable
- Excessive trunk folding that makes hip flexion and trunk flexion hard to separate

**Development Use**

This protocol can map to `knee_valgus`, `knee_varus`, `asymmetric_depth`,
`excessive_trunk_flexion`, `heel_lift`, and `tempo_instability` in
`compensation_candidates`.

### 2-2. Lunge

**Camera Setup**

```text
Zone: Z3 / Z7
Height: H2
```

Place the camera at a side-view position, either `Z3` or `Z7`, relative to the
reference mat. Set the lens around pelvis height, approximately 80-110 cm.

**Measurement Rationale**

This setup supports observation of anterior knee travel, sagittal trunk alignment,
and the relative motion of the front and rear limbs.

**Participant Cue**

1. Stand with feet about pelvis-width apart, then step one foot comfortably forward.
   Place both hands on the pelvis or waist so arm swing is not used.
2. Keep the trunk upright, descend vertically until both knees approach about
   90 degrees, and return to the starting height.
3. Perform 5 continuous repetitions with the same front foot. Then switch feet
   without turning around and perform 5 continuous repetitions with the opposite
   front foot, for 10 total repetitions.

**Analysis-Disrupting Patterns**

- Step length changing substantially across repetitions
- Arm swing or large trunk extension used to assist the ascent
- Excessive trunk flexion that makes anterior knee travel and trunk alignment hard
  to separate
- Turning the body or changing the camera-facing side during the side switch
- Repeatedly unstable front-foot or rear-foot contact

**Development Use**

The practical lunge protocol uses a 5-rep block on one side followed by a 5-rep
block on the other side. The current simple `pattern = alternating` representation
may not fully encode this structure, so future metadata such as `rep_side_sequence`
or `side_block_size` may be needed.

### 2-3. Pike Push-up

**Camera Setup**

```text
Zone: Z3 / Z7
Height: H1
```

Place the camera at a side-view position, either `Z3` or `Z7`, relative to the
reference mat. Keep the camera low, approximately 0-30 cm above the floor.

**Measurement Rationale**

This setup supports observation of the inverted-V posture and the sagittal-plane
trajectory of the head, shoulder, and elbow.

**Participant Cue**

1. Lift the hips high so the body forms an inverted V.
2. Lower the crown of the head toward the floor between the hands, then press back
   up using the shoulders.
3. The target is 10 repetitions. If 10 repetitions are too difficult, do not force
   the movement; perform only the maximum clean repetitions before the posture fully
   breaks down, and keep the same 3-set acquisition structure when possible.

**Analysis-Disrupting Patterns**

- Hips dropping so the movement becomes closer to a regular push-up
- Head moving forward beyond the hands rather than descending between them
- Excessive elbow flare that destabilizes the shoulder and elbow trajectory
- Descent depth that is too shallow or highly inconsistent
- Large hand or foot repositioning during the set

**Development Use**

This protocol can map to `insufficient_head_descent`, `head_forward_shift`,
`elbow_flare`, `shoulder_asymmetry`, `hip_drop`, `hip_pike`, and
`tempo_instability`. If fewer than 10 repetitions are completed, metadata such as
`actual_rep_count` is needed.

### 2-4. Plank Shoulder Tap

**Camera Setup**

```text
Zone: Z2 / Z8
Height: H1
```

Place the camera at a front-oblique position, either `Z2` or `Z8`, relative to
the reference mat. Keep the camera low, approximately 0-30 cm above the floor.

**Measurement Rationale**

This setup supports observation of pelvic rotation, weight shift, and lateral sway
while one hand taps the opposite shoulder.

**Participant Cue**

1. Start in a high plank or push-up-ready position, with the core and hips braced.
2. Resist trunk and pelvis motion while lifting one hand to lightly tap the opposite
   shoulder.
3. Count one left tap plus one right tap as one protocol cycle. Perform 10 total
   protocol cycles.

**Analysis-Disrupting Patterns**

- Excessive pelvic rotation or lateral shift during the tap
- Hips repeatedly lifting too high or dropping too low
- Hand or foot repositioning that changes the base of support during the set
- Missing the left-right order or repeating only one side
- Lifting the hand without actually tapping the opposite shoulder

**Development Use**

The practical protocol counts one left-right pair as one cycle, but segmentation may
treat each tap as an atomic repetition. Future annotation may need explicit
`tap_count`, `protocol_cycle_id`, or `rep_unit` fields.

---

## 3. Code Integration Boundary

The practical protocol is represented in exercise YAML as `performance_protocol`
and parsed by ③ Exercise Definition. Current implementation treats it as structured
metadata. It does not yet change segmentation or motion-attribution behavior.

```text
performance_protocol metadata
    target_count, count_unit, segmentation_reps_per_count, recommended_sets

side sequence metadata
    side_sequence.mode, block_size_counts, first_side_source

performance quality metadata
    performance_protocol_status, actual_rep_count, performance_note

analysis-disrupting pattern tags
    arm_swing, unstable_foot_contact, excessive_pelvic_rotation, incomplete_depth, ...
```

Fields that describe what actually happened during recording, such as
`actual_rep_count` or `performance_protocol_status`, belong to annotation or
recording metadata rather than the exercise definition.

Related implementation plans are recorded in `docs/code_revision_plan.md` and
`docs_eng/code_revision_plan.md`.
