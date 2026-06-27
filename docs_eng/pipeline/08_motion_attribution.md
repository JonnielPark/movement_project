# 08. Motion Attribution

**Document Version:** 1.1.3
**Last Updated:** 2026-06-27
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

The public stage-check path folds this step into
`27_motion_context_feature_extraction_test.ipynb`. The code-backed
`attribute_motion()` helper remains separate because alternating/unilateral
exercises still need an active-side QC path. The combined stage-check must not
be limited to the current real sample's laterality:

```text
Data Setup
    Prepares the real sample through ⑦ Segmentation.

Motion Context Contract
    Runs attribute_motion on the selected real sample and verifies the expected
    policy outcome, output columns, and non-mutation contract.

Pipeline Integration
    Runs the same motion-context path through run_pipeline and verifies report
    provenance before feature extraction consumes `FeatureContext`.
```

The stage-check notebook may use one default real sample, but motion-context
checks should remain definition-driven rather than hard-coded to a single
exercise. Fields that exist in the exercise definition but are not yet
implemented should be carried forward as provenance, not silently ignored.

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
For later side-specific review, a side-specific definition should be downgraded
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

## 9. Stage-Check Merge Boundary With ⑨

The current implementation keeps ⑧ as a separate code-backed pipeline helper
because it is useful for QC, provenance, and extension testing. The public
stage-check path folds ⑧ checks into ⑨ Feature Extraction so the user reviews
motion context and feature context in one place.

The planned integration direction is to let ⑨ Feature Extraction own a
`feature_context` preparation substep before computing feature values:

```text
⑨ Feature Extraction
    1. Resolve feature context
       - bilateral_symmetric      → bilateral symmetry / side-bias context
       - alternating/unilateral   → active-side attribution context
       - conditional/unsupported  → provenance warning, no strong side role
    2. Compute spatial / temporal / control features
    3. Attach availability, reliability, burden/provenance, and role_context
```

Under this direction, `attribute_motion()` remains a code-backed helper for
alternating/unilateral exercises, while the public pipeline may later present
the operation as part of feature extraction. This merge must not change the
coordinate policy, must not turn attribution into a score, and must not apply
active-side logic to bilateral symmetric exercises such as squat.

The combined stage-check must keep these guards:

```text
1. Confirm bilateral_symmetric exercises skip active-side attribution.
2. Confirm attribution columns, when added, do not mutate coordinates, rep_id,
   or phase.
3. Confirm ⑨ attaches role_context/source_fields only to context-consuming
   FeatureRecord families.
4. Do not remove the `attribute_motion()` helper until alternating/unilateral
   exercise samples have been reviewed.
```

## 10. Code Mapping

```text
src/movement/stages/motion_attribution.py
    AttributionThresholds
    AttributionReport
    attribute_motion()

tests/test_motion_attribution_protocol_sequence.py
```
