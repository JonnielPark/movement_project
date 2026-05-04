# 08. Visualization

Pipeline step ⑩. Called independently outside the ①–⑨ runner.
A collection of functions that render analysis results for diagnostic or reporting purposes.

All functions accept a dataframe and return a figure object. They do not modify input data.

---

## 1. Role

```text
Diagnostic use:    inspect raw data, preprocessing results, normalization effects
                   during development and debugging

Result reporting:  present biomarker results, feature distributions, and movement
                   quality metrics in a reviewable format
```

## 2. Correspondence to Pipeline Steps

```text
After ① Validation           → frame coverage / missing value heatmap
After ② Annotation           → rep boundary and segment label timeline
After ③ Exercise Definition  → (no coordinate output; no visualization)
After ④ Preprocessing        → reliability mask overlay, before/after comparison
After ⑤ Normalization        → raw vs. normalized skeleton comparison
After ⑥ Motion Attribution   → per-rep active side assignment chart
After ⑦ Feature Extraction   → joint angle time series, ROM bar, symmetry chart
After ⑧ Biomech Proxy        → CoM trajectory, segment load distribution
After ⑨ Biomarker Derivation → biomarker radar chart / summary chart
```

## 3. Implemented Functions

### create_pose_animation

```python
from movement.visualization import create_pose_animation
from movement.config import LANDMARKS, CONNECTIONS

fig = create_pose_animation(
    df,
    landmarks=LANDMARKS,
    connections=CONNECTIONS,
    coord_mode="raw",       # "raw" or "norm"
    frame_duration=100,     # ms per frame
    height=750,
    width=1000,
    show_text=True,
)
fig.show()
```

Plotly interactive 3D pose animation with Play/Pause buttons and frame slider.

`coord_mode`:
```text
"raw"  : <landmark>_x/y/z columns
"norm" : <landmark>_norm_x/y/z columns (requires ⑤ normalization)
```

### create_pose_comparison_animation

```python
from movement.visualization import create_pose_comparison_animation

fig = create_pose_comparison_animation(
    df,
    landmarks=LANDMARKS,
    connections=CONNECTIONS,
    coord_modes=("raw", "norm"),
    names=("Raw", "Normalized"),
)
fig.show()
```

Overlays two coordinate modes in one animation (blue = raw, red = normalized).
Useful for debugging ⑤ normalization.

## 4. Planned Functions

These functions exist as stubs (raise `NotImplementedError`):

### plot_reliability_overlay

Overlays ④ preprocessing reliability mask on a 3D pose animation.
Unreliable landmarks rendered in a distinct color/size.

```python
plot_reliability_overlay(df, landmarks, connections, reliability_col, coord_mode)
```

### plot_joint_angle_timeseries

Joint angle time series per frame (unit: degree).
Rep ranges shown as background shading.

```python
plot_joint_angle_timeseries(df, joint_triplets, joint_labels, rep_ranges, coord_mode)
```

### plot_rep_timeline

② annotation segment labels as a frame-level horizontal bar timeline.
Analysis segments (`use_for_analysis=True`) highlighted.

```python
plot_rep_timeline(df, segment_col, rep_col, set_col)
```

### plot_attribution_chart

⑥ motion attribution results per frame.
Shows detected vs. expected active side and confidence.

```python
plot_attribution_chart(df, attribution_col, confidence_col, expected_col)
```

### plot_biomarker_radar

⑨ biomarker derivation results as a radar chart.
Optional reference overlay for comparison.

```python
plot_biomarker_radar(biomarker_records, reference_records=None)
```

## 5. Implementation Notes

```text
3D pose animation          : Plotly (interactive in JupyterLab)
Diagnostic / result charts : matplotlib + seaborn
Publication output format  : svg / pdf
```

## 6. Related Notebooks

```text
notebook/03_raw_visualization_test.ipynb     → 3D pose animation (raw)
notebook/04_normalization_test.ipynb         → raw vs. normalized comparison
notebook/07_preprocessing_test.ipynb         → reliability mask, pipeline integration
notebook/08_motion_attribution_test.ipynb    → per-rep motion energy
notebook/09_feature_extraction_test.ipynb    → feature visualization (planned)
```
