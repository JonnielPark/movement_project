# 02. Validation

**Document Version:** 1.0.0  
**Last Updated:** 2026-05-06  
**Versioning Rule:** Semantic Versioning 2.0.0 (`MAJOR.MINOR.PATCH`)  
**Korean Sync:** `docs/pipeline/02_validation.md` is the same-version Korean source.

Pipeline step ①. Checks structural and formal integrity of input pose data.
Does not modify the data. Returns a diagnostic report dict.

Note: "validation" here means data integrity checking only.
      Robustness evaluation (simulation-based testing with synthetic data) is a separate concept.

---

## 1. Pipeline Position

```text
Pose CSV
→ ① Validation             ← this step
→ ② Annotation
→ ③ Exercise Definition
→ ④ Preprocessing
→ ⑤ Normalization
→ ⑥ Motion Attribution
→ ⑦ Feature Extraction
```

Runs before all other steps. Downstream steps can rely on the integrity assumptions
confirmed by the validation report.

## 2. Checks

| Check | Description |
|---|---|
| Required columns | `frame`, `timestamp`, landmark coordinate columns |
| Frame continuity | gaps in frame index |
| Frame duplicates | repeated frame values |
| Timestamp monotonicity | non-positive time diffs |
| Estimated FPS | derived from median timestamp delta |
| Missing value ratio | per coordinate column |
| Visibility quality | distribution / ratio below threshold (if visibility columns present) |

## 3. Output

```python
report = run_basic_validation(
    df=df,
    required_columns=make_required_columns(),
    coordinate_columns=make_coordinate_columns(),
    visibility_columns=make_visibility_columns(),
)
print(report["passed"])   # bool
```

Report structure:

```python
{
    "passed": bool,
    "required_columns": {
        "passed": bool,
        "missing_columns": list[str],
        "num_missing_columns": int,
    },
    "frame_continuity": {
        "passed": bool,
        "start_frame": int,
        "end_frame": int,
        "num_frames": int,
        "num_missing_frames": int,
        "missing_frames": list[int],
        "num_duplicated_frames": int,
        "duplicated_frames": list[int],
    },
    "timestamp": {
        "passed": bool,
        "num_timestamps": int,
        "median_dt": float,
        "estimated_fps": float | None,
        "min_dt": float,
        "max_dt": float,
        "num_non_positive_diffs": int,
    },
    "missing_values": {
        "passed": bool,
        "num_columns": int,
        "total_missing_values": int,
        "missing_ratio_by_column": dict[str, float],
    },
    "visibility": { ... },   # only if visibility_columns provided
}
```

## 4. Design Principle

This step only reports potential issues. It does not correct them.

- Short gaps → handled by ④ preprocessing interpolation.
- Noisy trajectories → handled by ④ preprocessing smoothing.
- Low visibility → handled by ④ preprocessing reliability gating.

A failed validation is a signal for manual review, not automatic discard.

## 5. Thresholds

Configured in `configs/pipeline_default.yaml`:

```yaml
validation:
  missing_value_threshold: 0.05   # column missing ratio > 5% → warn
  visibility_threshold: 0.5       # landmark visibility quality threshold
```

## 6. Planned Extensions

- Missing value heatmap visualization (⑩ step)
- Coordinate unit auto-detection (pixel vs. normalized)
- Enhanced temporal gap distribution statistics
