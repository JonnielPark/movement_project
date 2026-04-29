# Validation

## Purpose

The validation module checks whether pose landmark data is structurally valid and suitable for downstream analysis.

Validation does not modify the input data.

## Current Checks

- Required column existence
- Frame continuity
- Duplicated frames
- Timestamp monotonicity
- Estimated FPS
- Missing coordinate values
- Visibility quality

## Design Rule

Validation should only report potential problems.

```text
validation.py    -> detect and report issues
preprocessing.py -> correct or smooth data
features.py      -> compute indicators from corrected data
```

## Output

The validation module returns a dictionary-based report.

```python
report = run_basic_validation(...)
print(report["passed"])
```

## Interpretation

A failed validation result does not always mean the data is unusable.

It means that the issue should be reviewed before downstream processing.
For example, missing values may later be handled by interpolation, and noisy trajectories may later be handled by smoothing or Kalman filtering.
