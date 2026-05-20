# 05. Normalization

**Document Version:** 1.3.0
**Last Updated:** 2026-05-21
**Korean Sync:** `docs/pipeline/05_normalization.md` is the same-version Korean source.

Pipeline step ⑤ converts raw pose coordinates to a body-relative coordinate
system. When explicitly enabled, it may also create review-only canonical
coordinates that reduce consistent monocular-observation bias.

This step does not estimate absolute forces, absolute torque, calibrated 3D, or
absolute body dimensions. It provides the coordinate base for ⑧ Feature
Extraction and ⑨ Biomechanical Proxy.

---

## 1. Pipeline Position

```text
Pose CSV
→ ① Validation
→ ② Annotation
→ ③ Exercise Definition
→ ④ Preprocessing
→ ⑤ Normalization          ← this step
   ├─ base normalization: hip-center translation + torso-length scale
   └─ optional canonicalization: review-only candidate coordinates
→ ⑥ Segmentation
→ ⑦ Motion Attribution
→ ⑧ Feature Extraction
```

Runs after ④ Preprocessing so unreliable hip/shoulder landmarks are corrected,
interpolated, or marked before they affect the scale reference.

---

## 2. Base Normalization Contract

The implemented method is `hip_torso`.

```text
Translation reference : frame-wise hip center
Scale reference       : sequence-wise median torso length
Output unit           : torso_length_ratio (dimensionless)
```

The hip center is the body-relative origin.

```text
hip_center(t) = (left_hip(t) + right_hip(t)) / 2
p_translated_i(t) = p_i(t) - hip_center(t)
```

The sequence-level median torso length is the body scale. Using a sequence median
instead of per-frame scale avoids artificial skeleton jitter from monocular
torso-length noise.

```text
shoulder_center(t) = (left_shoulder(t) + right_shoulder(t)) / 2
torso_length(t)    = distance(hip_center(t), shoulder_center(t))
s                  = median(valid torso_length)
p_norm_i(t)        = (p_i(t) - hip_center(t)) / s
```

Raw coordinates are never overwritten.

```text
left_knee_x       original x
left_knee_norm_x  base normalized x
left_knee_canon_x optional canonicalized candidate x
```

Coordinate families have fixed meanings.

```text
raw      original pose coordinates
norm     base hip-torso normalized coordinates
canon    optional review/candidate coordinates after canonicalization
```

---

## 3. Configuration Contract

Detailed defaults live in `configs/pipeline_default.yaml`. The stable contract is:

```yaml
normalization:
  enabled: true
  method: hip_torso
  keep_reference_columns: true
  canonicalization:
    enabled: false
    coordinate_mode: norm
    output_prefix: canon
    report_only: true
    downstream_coordinate_mode: norm
    data_confidence: ...
    support_plane_alignment: ...
    movement_plane_alignment: ...
    protocol_height_lateral_width_alignment: ...
```

`report_only: true` means `canon` coordinates and reports may be created, but
downstream stages continue to consume `norm` coordinates. Changing
`downstream_coordinate_mode` to `canon` requires notebook review, robustness
evidence, and an explicit docs update before code promotion.

`floor_relative_correction` may still appear in local or legacy config files. It
is treated as a backward-compatible alias for `support_plane_alignment`; new work
should prefer the canonicalization key.

---

## 4. Report Contract

`normalize_pose_by_hip_torso(df, landmarks)` returns a normalized DataFrame and a
report.

```python
{
    "method": str,
    "num_frames": int,
    "scale_method": str,
    "scale_value": float,
    "min_torso_length": float,
    "max_torso_length": float,
    "median_torso_length": float,
    "num_invalid_torso_frames": int,
    "num_normalized_landmarks": int,
}
```

When canonicalization is enabled, `canonicalization_report` is added inside the
normalization report.

```python
{
    "enabled": bool,
    "status": "skipped" | "applied" | "partial" | "rejected",
    "coordinate_mode": "norm",
    "output_prefix": "canon",
    "report_only": bool,
    "downstream_coordinate_mode": "norm" | "canon",
    "active_priors": list[str],
    "applied_priors": list[str],
    "skipped_priors": dict[str, str],
    "max_correction_torso": float,
    "median_correction_torso": float,
    "residual_after_fit_torso": float | None,
    "data_confidence": {
        "level": "high" | "moderate" | "low",
        "reasons": list[str],
    },
    "prior_reports": {
        "support_plane_alignment": dict | None,
        "movement_plane_alignment": dict | None,
        "protocol_height_lateral_width_alignment": dict | None,
    },
}
```

`data_confidence.level` is not a movement-quality score. Low confidence should
surface as caution, withholding, or provenance rather than automatic score
deduction.

---

## 5. Canonicalization Contract

Canonicalization is optional and disabled by default. It is not calibrated 3D
reconstruction and does not fit the pose to a good-movement template. Its role is
to attenuate consistent observation bias while preserving raw/norm coordinates
and true compensation patterns such as knee valgus, heel lift, trunk lean, or
pelvis rotation.

Current active priors:

| Prior | Status | Purpose | Guardrail |
|---|---|---|---|
| `support_plane_alignment` | implemented, disabled by default | Pose-internal pseudo-floor/support-plane review from support-contact landmarks. Wraps the older `floor_relative_correction` logic. | Does not lock feet to the floor; not camera calibration. |
| `movement_plane_alignment` | prototype, disabled by default | Capped rigid rotation around the vertical axis using the dominant hip-knee-ankle movement direction. | Preserves out-of-plane residuals for compensation review. |
| `protocol_height_lateral_width_alignment` | prototype, disabled by default | Uses camera-height metadata as a gate before conservative lateral-width attenuation around H1/H2/H3 body anchors. | Not lens correction, reprojection, or far-side coordinate invention. |

Current prior order:

```text
1. support_plane_alignment
2. movement_plane_alignment
3. protocol_height_lateral_width_alignment
```

Body-axis alignment is intentionally not active. It may be reconsidered only
after the anthropometric skeleton prior is specified, because pelvis/shoulder
axis alignment could suppress true pelvis rotation, trunk lean, or transverse
compensation if applied too early.

---

## 6. Downstream Rules

- ⑥ Segmentation, ⑧ Feature Extraction, ⑨ Biomechanical Proxy, and ⑩ Biomarker
  Scoring consume `norm` coordinates by default.
- `canon` coordinates are review candidates until promotion criteria are written
  and tested.
- Corrected-coordinate magnitude and residuals are data-confidence/provenance
  signals, not movement-quality penalties.
- ④ Preprocessing may mark reliability violations before scale computation, but
  ⑤ Normalization owns body-relative scaling and canonical candidate coordinates.
- ⑨ Biomechanical Proxy uses normalized coordinates to compute relative CoM,
  moment-arm, and load-shift proxies. It must not infer absolute force, torque,
  or calibrated physical distances from this step.

---

## 7. Planned Extensions

- Anthropometric skeleton prior for segment-length/depth plausibility after the
  Size Korea-derived ratio source is documented.
- Visibility-weighted scale estimation and torso-length outlier handling.
- Per-exercise canonicalization prior selection from exercise definition fields.
- Robustness evaluation before any `canon` coordinate promotion.
- Gradual de-emphasis of the legacy `floor_relative_correction` key once local
  configs no longer depend on it.
