# 05 Normalization — p01 Squat Review Parameter Snapshot

**Version:** 0.1.0  
**Last Updated:** 2026-06-10  
**Status:** historical review snapshot, not an executable pipeline profile.

This file preserves the key parameters from the retired
`notebook_16_closed_chain_stance_corridor_review` profile. The original YAML was
used to review the p01 squat corrected-3D-hypothesis candidate surface. It is no
longer kept under `configs/pipeline_runs/` because retired review settings must
not look like active or dormant pipeline branches.

The snapshot is for reproducibility of research reasoning only. It does not make
corrected coordinates a ground truth, a good-movement template, calibrated 3D, or
a scoring input.

## 1. Review Boundary

```yaml
profile:
  name: notebook_16_closed_chain_stance_corridor_review
  mode: notebook_review
  description: p01 squat normalization review for the promoted corrected-3D-hypothesis candidate stack

recording_context:
  observed_camera_zone: Z8
  observed_camera_height_level: H2
  reference_mat_used: false
  filming_protocol_status: no_anchor

participant:
  sex: male
  height_cm: 175
  height_bin: 171-175cm
  common_subject_skeleton_profile_id: male_175cm
```

Input pose/video paths are intentionally omitted from this snapshot. The review
parameters below are the part that should survive after the notebook 16 review
surface is removed from the public path.

## 2. Pipeline Overrides

```yaml
preprocessing:
  enabled: true
  interpolation:
    enabled: true
  smoothing:
    enabled: true
    method: rolling_median
    window_size: 3
  far_side_stabilization:
    enabled: true
    jitter_threshold_torso_per_sec: 1.0
    acceleration_threshold_torso_per_sec2: 30.0

normalization:
  model_depth_scale: 0.5
  corrected_3d_hypothesis:
    enabled: true
    output_family: rv_skeleton_fit_bounded_xy_endpoint_blend_support_memory
    downstream_coordinate_mode: norm
    feature_depth_gravity: 0.0
    report_burden_before_feature_use: true
    require_feature_domain_declaration: true
```

## 3. Active Review Stack

```yaml
active_review_stack:
  - rv_skeleton_fit
  - rv_skeleton_fit_bounded_xy
  - within_session_segment_memory
  - closed_chain_support_context
  - support_width_guard
  - soft_bend_side_guard
  - support_surface_height_guard
  - visible_support_mirrored_anchor_prior
  - bounded_pre_post_standing_anchor_blend
  - planted_support_temporal_memory
  - score_readiness_review
  - bend_flip_provenance_review

reporting:
  used_for_features_or_scores: false
  confidence_when_applied: very_low
```

## 4. Recording-View-Constrained Skeleton Fit

```yaml
recording_view_constrained_skeleton_fit:
  family: rv_skeleton_fit
  source_family: norm
  review_rep_id: 1
  include_ready_window: true
  preserve_recording_axes: [x, y]
  correction_axes: [z]
  chains:
    - id: left_leg
      proximal: left_hip
      joint: left_knee
      distal: left_ankle
      proximal_segment: thigh
      distal_segment: shank
    - id: right_leg
      proximal: right_hip
      joint: right_knee
      distal: right_ankle
      proximal_segment: thigh
      distal_segment: shank
  width_segments:
    - id: hip_width
      left: left_hip
      right: right_hip
      segment: hip_width
  solver:
    strength: 0.85
    tolerance_ratio: 0.015
    max_joint_z_shift_ratio: 0.45
    max_width_z_shift_ratio: 0.25
    bend_side_guard:
      enabled: true
      mode: soft_reject_candidate_shift
      source_family: norm
      planes: [yz_height_depth, xz_recording_depth]
      near_neutral_tolerance_ratio: 0.010
      soft_flip_tolerance_ratio: 0.012
      allow_source_reverse_bend: true
      report_only: false
```

## 5. Segment Memory And Closed-Chain Context

```yaml
within_session_segment_memory:
  source_family: norm
  review_rep_id: 1
  include_ready_window: true
  include_review_rep: true
  min_endpoint_visibility: 0.55
  min_stable_frames: 12
  trim_quantile: 0.10
  max_p95_p05_ratio: 0.30
  max_frame_to_frame_jump_ratio: 0.16
  max_memory_deviation_from_anthropometric_ratio: 0.25
  blend_with_anthropometric:
    enabled: true
    memory_weight: 0.65
  accepted_segments:
    - left_shank
    - right_shank
  rejected_when_unstable:
    - left_thigh
    - right_thigh
    - hip_width

closed_chain_support_context:
  source_family: norm
  reference_source: ready_window_median
  apply_to_review_rep: true
  include_ready_window: true
  center_landmark_suffixes: [ankle, heel, foot_index]
  movable_landmark_suffixes: [ankle, heel, foot_index]
  sides: [left, right]
  side_strength:
    left: 0.15
    right: 0.70
  strength:
    x: 0.00
    y: 0.00
    z: 0.80
  max_shift_ratio:
    x: 0.00
    y: 0.00
    z: 0.18
  support_width_guard:
    enabled: true
    pair: [left_ankle, right_ankle]
    target_source: ready_window_median
    trim_quantile: 0.10
    tolerance_ratio: 0.005
    reject_shift_when_residual_worsens: true
```

## 6. Bounded Recording-View Residual Variant

```yaml
bounded_recording_view_residual:
  family: rv_skeleton_fit_bounded_xy
  source_family: norm
  baseline_family: rv_skeleton_fit
  review_rep_id: 1
  include_ready_window: true
  correction_axes: [x, y, z]
  solver:
    strength: 0.70
    tolerance_ratio: 0.015
    max_joint_xy_shift_ratio: 0.025
    max_joint_z_shift_ratio: 0.45
    max_width_xy_shift_ratio: 0.015
    max_width_z_shift_ratio: 0.25
    bend_side_guard:
      enabled: true
      mode: soft_reject_candidate_shift
      source_family: norm
      planes: [yz_height_depth, xz_recording_depth]
      near_neutral_tolerance_ratio: 0.010
      soft_flip_tolerance_ratio: 0.012
      allow_source_reverse_bend: true
      report_only: false
```

## 7. Support Surface And Visible-Support Priors

```yaml
support_surface_height_guard:
  enabled: true
  exercise_definition_gate: true
  required_kinetic_chain: closed_chain
  required_base_of_support: bilateral_feet
  required_support_surface: floor
  source_family: norm
  reference_source: ready_window_median
  axis: y
  sides: [left, right]
  landmark_suffixes: [ankle, heel, foot_index]
  primary_suffixes: [ankle]
  strength: 0.55
  side_strength:
    left: 0.30
    right: 0.65
  max_shift_ratio: 0.040
  residual_tolerance_ratio: 0.012
  trim_quantile: 0.10
  reject_shift_when_residual_worsens: true
  report_only: false

visible_support_mirrored_anchor_prior:
  enabled: true
  mode: ready_window_mirrored_support_anchor
  exercise_definition_gate: true
  required_kinetic_chain: closed_chain
  required_base_of_support: bilateral_feet
  required_support_surface: floor
  source_family: norm
  trusted_side_source: visibility_stability
  fallback_trusted_side: left
  target_side: auto_opposite
  candidate_sides: [left, right]
  body_frame_source: ready_window_median
  body_center_landmarks: [left_hip, right_hip]
  support_landmark_suffixes: [ankle, heel, foot_index]
  primary_suffixes: [ankle]
  reference_source: ready_window_median
  axes: [z]
  tolerance_ratio: 0.005
  strength: 1.00
  max_z_shift_ratio: 0.060
  trim_quantile: 0.10
  min_reference_frames: 8
  support_width_no_worsen:
    enabled: true
    target_source: ready_window_median
    trim_quantile: 0.10
    tolerance_ratio: 0.005
  report_only: false
```

## 8. Endpoint Blend And Whole-Video Support Memory

```yaml
bounded_pre_post_standing_anchor_blend:
  mode: start_endpoint_to_end_support_anchor_z_blend
  review_rep_id: 1
  source_family: rv_skeleton_fit_bounded_xy
  family: rv_skeleton_fit_bounded_xy_endpoint_blend
  playback_norm_family: norm
  start_window_before_frames: 2
  start_window_after_frames: 0
  end_window_before_frames: 2
  ramp_after_start_frames: 1
  target_anchor_source: end_window_median
  sides: [left, right]
  support_landmark_suffixes: [ankle, heel, foot_index]
  primary_suffixes: [ankle]
  body_center_landmarks: [left_hip, right_hip]
  axes: [z]
  strength: 0.50
  max_z_shift_ratio: 0.050
  support_width_no_worsen:
    enabled: true
    target_source: end_window_median
    tolerance_ratio: 0.005
  report_only: false

planted_support_temporal_memory:
  mode: whole_video_support_anchor_memory_z_only
  scope: whole_video
  review_only_candidate: false
  source_family: rv_skeleton_fit_bounded_xy_endpoint_blend
  family: rv_skeleton_fit_bounded_xy_endpoint_blend_support_memory
  playback_norm_family: norm
  sides: [left, right]
  support_landmark_suffixes: [ankle, heel, foot_index]
  primary_suffixes: [ankle]
  support_pair: [left_ankle, right_ankle]
  axes: [z]
  strength: 0.15
  max_z_shift_ratio: 0.020
  reference:
    source: whole_video_stable_trimmed_median
    trim_quantile: 0.10
    min_visibility: 0.55
    max_frame_to_frame_jump_ratio: 0.030
    min_reference_frames: 12
  support_width_no_worsen:
    enabled: true
    target_source: whole_video_trimmed_median
    tolerance_ratio: 0.005
  bend_side_no_worsen:
    enabled: true
    reference_family: norm
    planes: [xz_recording_depth, yz_height_depth, xy_recording_plane]
    epsilon: 0.010
```

## 9. Score-Readiness And Bend-Flip Provenance Gates

```yaml
score_readiness_review:
  mode: report_only
  rep_id_start: 1
  rep_id_end: 10
  reference_family: norm
  candidate_family: final_review_output
  bend_epsilon: 0.020
  critical_landmarks_by_side:
    left: [left_hip, left_knee, left_ankle]
    right: [right_hip, right_knee, right_ankle]
  thresholds:
    min_visibility_p10: 0.50
    min_visibility_median: 0.65
    max_bend_flip_frames: 0
    max_knee_flexion_median_abs_delta_deg: 3.0
    max_knee_flexion_p95_abs_delta_deg: 8.0
    max_shank_angle_median_abs_delta_deg: 3.0
    max_shank_angle_p95_abs_delta_deg: 8.0
    max_segment_length_cv: 0.080
    max_joint_step_p95_ratio: 0.120
  reporting:
    used_for_features_or_scores: false
    confidence_when_applied: review_gate_only

bend_flip_provenance_review:
  mode: report_only
  rep_id_start: 1
  rep_id_end: 10
  reference_family: norm
  family_sequence:
    - label: norm
      family: norm
    - label: rv_skeleton_fit
      family: rv_skeleton_fit
    - label: rv_skeleton_fit_bounded_xy
      family: rv_skeleton_fit_bounded_xy
    - label: endpoint_blend
      family: rv_skeleton_fit_bounded_xy_endpoint_blend
    - label: support_memory_final
      family: final_review_output
  planes: [xz_recording_depth, yz_height_depth, xy_recording_plane]
  epsilon: 0.020
  reporting:
    used_for_features_or_scores: false
    confidence_when_applied: review_gate_only
```

## 10. Visualization Parameters Worth Preserving

```yaml
playback:
  speed: 1.0
  stride: 2

review_display:
  visual_focus: support_surface_height
  show_legacy_visualizations: false
  show_support_surface_playback: true
  show_final_playback: true
  show_audit_plots: false
  playback_anchor:
    enabled: true
    mode: bilateral_ankle_midpoint
    family: bounded_candidate
    landmarks: [left_ankle, right_ankle]
    include_height: true

scene_camera:
  projection_type: orthographic
  eye: {x: 1.45, y: -2.25, z: 1.05}
  up: {x: 0.0, y: 0.0, z: 1.0}
  top_down_eye: {x: 0.0, y: 0.0, z: 2.6}
  top_down_up: {x: 0.0, y: 1.0, z: 0.0}
```

