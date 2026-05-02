# Motion Attribution

## Purpose

The motion attribution module verifies, at the repetition level, whether the limb that actually moved in each rep matches the limb that should have moved according to the declared exercise pattern.

This module addresses a class of errors that frame-level preprocessing cannot resolve. In monocular pose data, a moving limb may be occluded while a stationary limb is reported as moving, or labels may drift over a longer time scale than a single frame swap. These cases require comparing observed motion energy against the expected exercise pattern over a full rep.

Motion attribution does not modify coordinate values. It produces rep-level metadata about labeling consistency.

## Pipeline Role

Motion attribution runs after normalization and before feature extraction.

```text
Pose CSV
-> Validation
-> Annotation Mask Application
-> Exercise Definition Loading
-> Preprocessing
-> Normalization
-> Motion Attribution
-> Feature Extraction
```

The module requires:

```text
- rep boundaries (from annotation)
- exercise context (from annotation: exercise_type, pattern, starting_side)
- exercise definition (from exercise definition loading: laterality, primary_joints)
- normalized coordinates (from normalization)
```

Body-relative coordinates are used so that motion-energy comparisons are not biased by absolute body size or camera distance.

## Design Rule

Motion attribution decides labeling consistency, not movement quality.

```text
allowed:
- detect which side moved more during a rep
- compare detected active limb against the expected active limb
- mark rep-level inconsistency
- label-only correction when confidence is high enough
- attribution report generation

not allowed:
- judge whether a rep was "well executed"
- compute movement quality scores
- modify coordinate values
- modify rep boundaries
```

Exercise-specific quality assessment belongs to feature extraction, biomechanical proxy modeling, and scoring.

## When Does This Module Apply?

Motion attribution is exercise-aware and is gated by the loaded exercise definition's `classification.laterality` (cross-checked against `pattern` from annotation).

```text
laterality = bilateral_symmetric  -> module is skipped, no rep-level active limb concept
laterality = alternating          -> module runs and produces attribution metadata
laterality = unilateral_*         -> module runs with the declared side as expected
laterality unknown / generic      -> module is skipped (safe default)
```

For bilateral exercises (squat, pike push-up), there is no expected per-rep active side, so attribution is not meaningful at the rep level.

## Active Limb Detection

For each rep marked with `segment_type = rep` in annotation, motion energy is computed for left and right paired landmarks of interest.

```text
rep window [start, end]:

left_motion  = Σ |p_left_landmark(t+1)  - p_left_landmark(t)|     for t in window
right_motion = Σ |p_right_landmark(t+1) - p_right_landmark(t)|   for t in window

motion_share = max(left_motion, right_motion)
              / (left_motion + right_motion + ε)
```

The paired landmark used for attribution depends on the exercise's `landmarks.primary_joints` field (with optional per-exercise overrides via configuration).

```text
plank_shoulder_tap : left_wrist  vs right_wrist
lunge              : left_knee   vs right_knee
                     (forward leg has larger vertical excursion)
```

Multiple landmark pairs may be combined as a weighted sum of individual `motion_share` values to reduce sensitivity to a single noisy landmark.

## Detection Outcome

```text
if motion_share > τ_active (default: 0.7):
    detected_active = side with higher motion
    attribution_confidence = motion_share

elif τ_ambiguous < motion_share <= τ_active (default: 0.55 to 0.7):
    detected_active = "ambiguous"
    attribution_confidence = motion_share

else:
    detected_active = "bilateral"
    attribution_confidence = 1 - motion_share
```

## Expected Active Limb

The expected active limb per rep is derived from `pattern` and `starting_side` from annotation, cross-checked with the loaded definition's `laterality`.

```text
pattern = alternating, starting_side = right:
  rep 1 -> right
  rep 2 -> left
  rep 3 -> right
  rep 4 -> left
  ...

pattern = alternating, starting_side = left:
  rep 1 -> left
  rep 2 -> right
  rep 3 -> left
  rep 4 -> right
  ...
```

If `starting_side` is missing, the module assumes the detected active side of rep 1 as the starting side and propagates from there.

## Consistency Check and Action

For each rep, the detected active limb is compared against the expected active limb.

```text
case A: detected_active == expected_active
        attribution_consistent = True
        action = "accept"

case B: detected_active != expected_active
        AND attribution_confidence > τ_swap (default: 0.85)
        attribution_consistent = False
        action = "swap"     (label-only swap inside this rep window)
                or "flag"   (when running in conservative mode)

case C: detected_active != expected_active
        AND attribution_confidence <= τ_swap
        attribution_consistent = False
        action = "flag"

case D: detected_active in {"ambiguous", "bilateral"}
        attribution_consistent = None
        action = "flag"
```

By default, the module operates in conservative mode and uses `flag` rather than `swap`. Auto-correction may be enabled later when the simulation-based robustness study has characterized the false-correction rate.

## Output Columns

The module adds rep-level attribution columns. These columns are populated only on frames inside `rep` segments and remain null elsewhere.

```text
detected_active_limb       : 'left' | 'right' | 'bilateral' | 'ambiguous' | None
expected_active_limb       : 'left' | 'right' | None
attribution_consistent     : bool | None
attribution_confidence     : float (0 to 1) | None
attribution_action         : 'accept' | 'flag' | 'swap' | None
```

## Attribution Report

The motion attribution report should make the decision process auditable.

Recommended report fields:

```text
method
exercise_type
laterality
pattern
starting_side
num_reps
num_consistent
num_flagged
num_swapped
num_ambiguous
num_bilateral
thresholds:
  τ_active
  τ_ambiguous
  τ_swap
landmark_pairs_used
mode: 'conservative' | 'auto_correct'
```

## Configuration Draft

```yaml
motion_attribution:
  enabled: false
  thresholds:
    active: 0.70
    ambiguous: 0.55
    swap: 0.85
  mode: conservative           # 'conservative' | 'auto_correct'
  landmark_pairs:              # optional; falls back to landmarks.primary_joints
    plank_shoulder_tap:
      - [left_wrist, right_wrist]
    lunge:
      - [left_knee, right_knee]
      - [left_ankle, right_ankle]
```

When the loaded definition's `laterality` is `bilateral_symmetric`, the module is skipped regardless of `enabled`.

## Relationship to Preprocessing

Preprocessing operates frame by frame. It can correct local left-right swap events but cannot reliably detect a sustained mislabeling across an entire rep, especially when the moving limb is occluded.

Motion attribution operates rep by rep on the normalized data. It provides a higher-level consistency check that uses both rep boundaries and exercise context.

```text
preprocessing       -> frame-level reliability and label correctness
motion_attribution  -> rep-level active-limb verification
```

A rep that passes preprocessing without any swap correction can still be flagged by motion attribution if the active limb does not match the expected pattern.

## Relationship to Feature Extraction

Feature extraction reads attribution metadata to decide how to attribute rep-level features.

```text
attribution_consistent == True
  features for the rep are attributed to the expected active limb

attribution_consistent == False AND action == 'flag'
  features may be computed but downweighted, or excluded from
  per-side aggregations, depending on the feature definition

attribution_consistent == False AND action == 'swap'
  the rep's left and right labels are treated as swapped before
  feature computation
```

This keeps feature extraction free of label-correction logic.

## Initial Completion Criteria

The first motion attribution implementation is complete when:

```text
1. motion_attribution.py exists
2. the module skips bilateral exercises automatically (driven by definition laterality)
3. motion energy is computed per rep over annotated rep windows
4. detected active limb is produced with a confidence value
5. expected active limb is derived from pattern and starting_side
6. attribution columns are added to the dataframe
7. conservative mode flags inconsistencies without modifying labels
8. attribution report is returned
9. pipeline.py can run motion attribution when enabled
10. notebook/08_motion_attribution_test.ipynb verifies the behavior
```

## Future Extensions

Later versions may include:

- multi-landmark weighted motion-share with learned weights per exercise
- vertical-only or normal-axis motion energy for tap-style exercises
- HMM-based phase recognition that infers active limb without an explicit `starting_side`
- swap auto-correction enabled after simulation-based robustness validation
- motion-energy visualization per rep for manual review
- per-rep motion attribution under synthetic occlusion to support the robustness study
