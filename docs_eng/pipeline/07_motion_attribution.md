# 07. Motion Attribution

**Document Version:** 1.0.1  
**Last Updated:** 2026-05-10  
**Korean Sync:** `docs/pipeline/07_motion_attribution.md` is the same-version Korean source.

Pipeline step ⑦. Checks whether the limb that moved most in each rep matches the
expected active side. The expected side is derived from
`performance_protocol.side_sequence` when available, then falls back to annotation
`pattern` / `starting_side`.

Does not modify coordinates. Adds per-rep metadata columns only.

---

## 1. Pipeline Position

```text
Pose CSV
→ ① Validation
→ ② Annotation
→ ③ Exercise Definition
→ ④ Preprocessing
→ ⑤ Normalization
→ ⑥ Segmentation
→ ⑦ Motion Attribution     ← this step
→ ⑧ Feature Extraction
```

Required inputs:
```text
rep boundaries            from annotation (segment_type = rep)
exercise context          exercise_type, pattern, starting_side from annotation
exercise definition       laterality, primary_joints, performance_protocol.side_sequence
normalized coordinates    from ⑤ normalization
```

Uses normalized coordinates so that motion energy comparison is independent of
absolute body size and camera distance.

## 2. Activation Condition

```text
laterality = bilateral_symmetric  → step is skipped (no active-side concept per rep)
laterality = alternating          → runs per-rep attribution
laterality = unilateral_*         → runs; declared side is the expected active side
laterality unknown / generic      → skipped (safe default)
```

## 3. Active Side Detection

Motion energy is computed for left and right paired landmarks within the rep window
(`segment_type = rep`):

```text
left_motion  = Σ |p_left_landmark(t+1)  - p_left_landmark(t)|
right_motion = Σ |p_right_landmark(t+1) - p_right_landmark(t)|

motion_share = max(left_motion, right_motion) / (left_motion + right_motion + ε)
```

Landmark pairs are derived from `landmarks.primary_joints` in the exercise definition.
Custom pairs can be specified per exercise in the YAML config.

Examples:
```text
plank_shoulder_tap : left_wrist  vs right_wrist
lunge              : left_knee   vs right_knee
```

Multiple paired landmarks can be combined (weighted average) to reduce sensitivity to
a single noisy landmark.

## 4. Detection Thresholds

```text
if motion_share > τ_active (default: 0.70):
    detected_active = side with greater motion
    confidence = motion_share

elif τ_ambiguous < motion_share ≤ τ_active (default: 0.55 – 0.70):
    detected_active = "ambiguous"
    confidence = motion_share

else:
    detected_active = "bilateral"
    confidence = 1 - motion_share
```

## 5. Expected Active Side

Derived first from `performance_protocol.side_sequence`, then from `pattern` and
`starting_side` in annotation, cross-checked against `laterality` in the exercise
definition.

```text
pattern = alternating, starting_side = right:
    rep 1 → right
    rep 2 → left
    rep 3 → right
    ...

pattern = alternating, starting_side = left:
    rep 1 → left
    rep 2 → right
    ...

performance_protocol.side_sequence.mode = same_side_block_then_switch,
block_size_counts = 5, starting_side = right:
    rep 1-5  → right
    rep 6-10 → left

performance_protocol.side_sequence.mode = alternating_each_rep,
starting_side = left:
    rep 1 → left
    rep 2 → right
    ...
```

If `starting_side` is absent, the detected active side of rep 1 is assumed as the
start, and alternation is applied from rep 2.

## 6. Consistency Check and Action

```text
case A: detected == expected
        attribution_consistent = True
        action = "accept"

case B: detected != expected AND confidence > τ_swap (default: 0.85)
        attribution_consistent = False
        action = "swap"   (in auto_correct mode)
             or "flag"   (in conservative mode)

case C: detected != expected AND confidence ≤ τ_swap
        attribution_consistent = False
        action = "flag"

case D: detected in {"ambiguous", "bilateral"}
        attribution_consistent = None
        action = "flag"
```

Default mode is `conservative` (flag only; no label modification).
`auto_correct` (swap) mode is enabled only after false-correction rate is verified
in robustness simulation.

## 7. Output Columns

Added per-frame; non-null only within `rep` segments.

```text
detected_active_limb     'left' | 'right' | 'bilateral' | 'ambiguous' | None
expected_active_limb     'left' | 'right' | None
attribution_consistent   bool | None
attribution_confidence   float 0–1 | None
attribution_action       'accept' | 'flag' | 'swap' | None
```

## 8. Attribution Report

```python
attr_df, attr_report = attribute_motion(df, exercise_definition, thresholds, mode)
```

Report fields:
```python
{
    "method": str,
    "exercise_type": str,
    "laterality": str,
    "pattern": str,
    "starting_side": str,
    "num_reps": int,
    "num_consistent": int,
    "num_flagged": int,
    "num_swapped": int,
    "num_ambiguous": int,
    "num_bilateral": int,
    "thresholds": {"active": float, "ambiguous": float, "swap": float},
    "landmark_pairs_used": list,
    "mode": str,      # "conservative" | "auto_correct"
    "skipped": bool,
    "skip_reason": str | None,
}
```

## 9. Configuration

```yaml
motion_attribution:
  enabled: false
  thresholds:
    active: 0.70
    ambiguous: 0.55
    swap: 0.85
  mode: conservative        # conservative | auto_correct
```

`bilateral_symmetric` laterality always skips this step regardless of the `enabled` flag.

## 10. Relationship to ④ Preprocessing

④ preprocessing operates frame-by-frame and can correct short L/R swap events.
It cannot reliably detect rep-level label mismatches (e.g., active limb occluded for
the entire rep, causing the stationary side to appear as the mover).

⑦ motion attribution operates on rep windows using rep boundaries and exercise context,
catching higher-level consistency issues that ④ misses.

## 11. Relationship to ⑧ Feature Extraction

⑧ uses the attribution metadata to assign features to the correct side:

```text
attribution_consistent == True
    → features attributed to the expected active side

attribution_consistent == False AND action == "flag"
    → features computed but down-weighted or excluded in per-side aggregation

attribution_consistent == False AND action == "swap"
    → L/R labels exchanged; features computed on the corrected assignment
```

## 12. Planned Extensions

- Multi-landmark motion-share with exercise-specific learned weights
- Vertical-axis / normal-axis motion energy for tap-style exercises
- HMM-based phase recognition to infer starting_side without annotation
- Activation of auto_correct after robustness simulation verification
- Per-rep motion energy visualization for manual review
