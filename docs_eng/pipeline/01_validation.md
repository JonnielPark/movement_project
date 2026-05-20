# 01. Validation

**Document Version:** 1.1.0
**Last Updated:** 2026-05-21
**Korean Sync:** `docs/pipeline/01_validation.md` is the same-version Korean source.

Pipeline step ① checks structural integrity of input pose data. It does not
modify data and is distinct from ⑫ robustness evaluation.

---

## 1. Pipeline Position

```text
Pose CSV
→ ① Validation             ← this step
→ ② Annotation
→ downstream steps
```

Downstream steps rely on integrity assumptions confirmed here.

## 2. Checks

| Check | Purpose |
|---|---|
| Required columns | `frame`, `timestamp`, coordinate columns |
| Frame continuity | frame-index gaps |
| Frame duplicates | repeated frame values |
| Timestamp monotonicity | non-positive time differences |
| Estimated FPS | median timestamp delta |
| Missing value ratio | per coordinate column |
| Visibility quality | low-visibility ratio when visibility columns exist |

## 3. Entry Point

```python
report = run_basic_validation(
    df=df,
    required_columns=make_required_columns(),
    coordinate_columns=make_coordinate_columns(),
    visibility_columns=make_visibility_columns(),
)
```

Report top-level keys:

```text
passed
required_columns
frame_continuity
timestamp
missing_values
visibility     # only when visibility columns are provided
```

## 4. Policy

Validation reports issues; it does not correct them.

```text
short gaps          handled later by ④ interpolation
noisy trajectories  handled later by ④ smoothing
low visibility      handled later by reliability gates
failed validation   manual-review signal, not automatic discard
```

## 5. Thresholds

Configured in `configs/pipeline_default.yaml`:

```yaml
validation:
  missing_value_threshold: 0.05
  visibility_threshold: 0.5
```

## 6. Code Mapping

```text
src/movement/stages/validation.py
src/movement/core/config.py
```
