# 08. Motion Attribution

**Document Version:** 1.1.1
**Last Updated:** 2026-06-25
**Korean Sync:** `docs/pipeline/08_motion_attribution.md` is the same-version Korean source.

Pipeline step ⑧ checks whether the observed moving limb in each rep matches the
expected active side. The expected side is derived from
`performance_protocol.side_sequence` when available, then from annotation
`execution_pattern` / `starting_side`. This step does not modify coordinates; it adds
rep-level metadata columns for downstream feature attribution.

---

## 1. Pipeline Position

```text
Pose CSV
→ ① Validation
→ ② Annotation
→ ③ Exercise Definition
→ ④ Preprocessing
→ ⑤ Normalization
→ ⑥ Canonicalization
→ ⑦ Segmentation
→ ⑧ Motion Attribution     ← this step
→ ⑨ Feature Extraction
```

Required inputs:

```text
rep boundaries            segment_type == rep, rep_id
exercise context          exercise_id, execution_pattern, starting_side
exercise definition       laterality, primary_joints, performance_protocol.side_sequence
definition readiness      primary_body_regions, joint_actions.primary
normalized coordinates    <landmark>_norm_x/y/z
```

Normalized coordinates keep motion-energy comparisons independent of body size
and camera distance.

Stage-check notebook 27 follows the shared stage-check pattern, but it must not
be limited to the current real sample's laterality:

```text
Data Setup
    Prepares the real sample through ⑦ Segmentation.

Definition Policy Matrix
    Reads available exercise definitions and classifies motion-attribution
    policy as skip, run, conditional, or not-yet-implemented from definition
    fields such as laterality, performance side sequence, and pairable primary
    joints.

Definition Field Coverage
    Shows whether selected definition fields are used by this stage, carried as
    provenance/context, reserved for downstream stages, or not yet supported.

Direct Real-Sample Test
    Runs attribute_motion on the selected real sample and verifies the expected
    policy outcome.

Synthetic Applicability Smoke Test
    Uses a minimal generated dataframe for one runnable definition, when
    available, to confirm the active-side attribution path without requiring a
    new recording.

Pipeline Integration
    Runs the same stage through run_pipeline and verifies report provenance and
    frame-level output contract.
```

The stage-check notebook may use one default real sample, but the policy matrix,
field coverage table, and synthetic smoke test must be definition-driven rather
than hard-coded to a single exercise. Fields that exist in the exercise
definition but are not yet implemented should be represented as
`not_yet_implemented`, `conditional`, or carried-forward context, not silently
ignored.

For side-specific definitions, the stage-check policy treats `primary_body_regions`
and `joint_actions.primary` as readiness gates. They do not change the
motion-energy formula, but they prevent a definition from being reported as
fully runnable when the authoring context needed to interpret the active-side
evidence is missing.

## 2. Activation Rules

```text
bilateral_symmetric       skipped; no per-rep active-side concept
bilateral_asymmetric      not_yet_implemented; route to side-bias/symmetry
                          feature policy until active-side semantics are defined
alternating               run per rep
unilateral_left/right     run; declared side is expected
unilateral_unspecified    run when side can be inferred from context/evidence
unknown / generic         skipped
```

`bilateral_symmetric` skips this step even if the config flag is enabled.
For the stage-check readiness preview, a side-specific definition is downgraded
to `conditional` when pairable primary landmarks, primary body regions, or
primary joint actions are missing.

## 3. Detection Method

For each rep window, left/right motion energy is computed from paired landmarks:

```text
left_motion  = Σ ||p_left(t+1)  - p_left(t)||
right_motion = Σ ||p_right(t+1) - p_right(t)||
motion_share = max(left_motion, right_motion) / (left_motion + right_motion + ε)
```

Pairs are selected from `landmarks.primary_joints` when possible; otherwise the
default shoulder/elbow/wrist/hip/knee/ankle pairs are used. Exercise YAML may
provide custom pairs for tasks such as taps or asymmetric lower-limb movements.

Decision thresholds:

```text
motion_share > τ_active          → detected_active = left/right, confidence = motion_share
τ_ambiguous < share ≤ τ_active   → detected_active = ambiguous
share ≤ τ_ambiguous              → detected_active = bilateral
```

Default thresholds: `τ_active = 0.70`, `τ_ambiguous = 0.55`, `τ_swap = 0.85`.

## 4. Expected Side

Priority:

```text
1. laterality = unilateral_left/right
2. performance_protocol.side_sequence
3. execution pattern + starting_side
4. first-rep detected side when starting_side is missing and evidence is usable
```

Supported side-sequence modes:

```text
alternating_each_rep             rep 1 right, rep 2 left, ...
same_side_block_then_switch      first block on starting_side, next block on the other side
```

When the expected side cannot be determined, the rep is flagged rather than
silently accepted.

## 5. Action Policy

```text
detected == expected
    attribution_consistent = True
    action = accept

detected != expected and confidence > τ_swap
    attribution_consistent = False
    action = swap in auto_correct mode, otherwise flag

detected != expected and confidence ≤ τ_swap
    attribution_consistent = False
    action = flag

detected in {ambiguous, bilateral}
    attribution_consistent = None
    action = flag
```

Default mode is `conservative`: labels are not changed. `auto_correct` is a
future/experimental mode and should remain disabled until robustness simulation
shows a sufficiently low false-correction rate.

## 6. Output Contract

Columns added per frame; values are non-null only inside `rep` segments:

```text
detected_active_limb     left | right | bilateral | ambiguous | None
expected_active_limb     left | right | None
attribution_consistent   bool | None
attribution_confidence   float 0-1 | None
attribution_action       accept | flag | swap | None
```

Report fields:

```text
method
exercise_id
laterality
execution_pattern
starting_side
num_reps / num_consistent / num_flagged / num_swapped
num_ambiguous / num_bilateral
thresholds = {τ_active, τ_ambiguous, τ_swap}
landmark_pairs_used
performance_side_sequence
expected_side_source
side_sequence_warnings
mode
skipped / skip_reason
```

These provenance fields are emitted even when the stage is skipped. A skipped
bilateral exercise should still report `exercise_id`, `laterality`,
`execution_pattern` when present, `performance_side_sequence`, thresholds, and
the skip reason.

## 7. Configuration

```yaml
motion_attribution:
  enabled: false
  thresholds:
    active: 0.70
    ambiguous: 0.55
    swap: 0.85
  mode: conservative        # conservative | auto_correct
```

## 8. Downstream Use

⑨ Feature Extraction uses attribution metadata to assign or qualify side-specific
features:

```text
consistent true       → assign features to expected active side
flagged mismatch      → compute features but mark side attribution as low confidence
auto-corrected swap   → compute features on corrected side assignment
ambiguous/bilateral   → avoid strong side-specific interpretation
```

⑧ complements ④ Preprocessing: ④ handles short frame-level L/R swaps, while ⑧
checks rep-level side consistency using segmentation and exercise context.

## 9. Code Mapping

```text
src/movement/stages/motion_attribution.py
    AttributionThresholds
    AttributionReport
    attribute_motion()

tests/test_motion_attribution_protocol_sequence.py
```
