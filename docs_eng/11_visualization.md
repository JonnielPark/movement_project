# 11. Visualization

**Document Version:** 1.0.0  
**Last Updated:** 2026-05-06  
**Versioning Rule:** Semantic Versioning 2.0.0 (`MAJOR.MINOR.PATCH`)  
**Korean Sync:** `docs/11_visualization.md` is the same-version Korean source.

Pipeline step ⑪. Called independently outside the ①–⑩ runner. A collection of
functions that render pose data and analysis results for diagnostic inspection
and clinician-facing reporting.

The framing is **provenance-centric**: a reviewer should be able to read a
single figure and trace each deduction back to the contributing feature, the
rep, the phase, the source landmarks, and the biomechanical reasoning. From
the CDSS (Clinical Decision Support System) perspective, interpretability and
intuitiveness take priority over visual density.

All functions accept a dataframe / record list and return a figure object;
they do not modify input data. Corresponds to dissertation §7.5.

---

## 1. Role

```text
Diagnostic use     inspect raw data, preprocessing, and normalization effects
                   during development and debugging

Result reporting   present biomarker scores, feature distributions, and
                   movement-quality metrics in a reviewable layout
                   suitable for clinician review and dissertation figures
```

## 2. Correspondence to Pipeline Steps

```text
After ① Validation              → frame coverage / missing-value heatmap
After ② Annotation              → rep boundary + segment-label timeline
After ③ Exercise Definition     → (no coordinate output; no visualization)
After ④ Preprocessing           → reliability mask overlay, before / after
After ⑤ Normalization           → raw vs. normalized skeleton comparison
After ⑥ Phase Segmentation      → smoothed reference trajectory + phase bands
After ⑦ Motion Attribution      → per-rep active-side assignment chart
After ⑧ Feature Extraction      → joint angle time-series, ROM bar, symmetry
After ⑨ Biomech Proxy           → CoM trajectory, moment-arm overlay
After ⑩ Biomarker Derivation    → biomarker radar, attribution heatmap
After ⑫ Simulation              → robustness sensitivity curves
```

## 3. Provenance Disclosure Convention

Every visualization function consumes the input record's `source_fields` and
surfaces it through hover tooltips (interactive Plotly) or captions (static
matplotlib).

`plot_attribution_heatmap()` exposes the following per cell:

```text
feature_id    : control.compensation.knee_valgus.left
rep_id        : 2
phase         : Descent
value         : 0.13 (torso_length_ratio)
z_score       : 1.8
deduction     : 5.4 pts
source_fields : compensation_candidates.knee_valgus,
                landmarks.primary_joints
reasoning     : "Frontal-plane knee deviation; possible hip abductor weakness."
```

This enables the user to retrace the chain `score → deduction → feature →
landmark → YAML field` without leaving the figure.

## 4. Implemented Functions

### 4-1. create_pose_animation

Plotly interactive 3D pose animation with Play/Pause buttons and frame slider.

```python
from movement.visualization import create_pose_animation
from movement.config import LANDMARKS, CONNECTIONS

fig = create_pose_animation(
    df,
    landmarks=LANDMARKS,
    connections=CONNECTIONS,
    coord_mode="raw",        # "raw" or "norm"
    frame_duration=100,      # ms per frame
    height=750,
    width=1000,
    show_text=True,
)
fig.show()
```

`coord_mode`:
```text
"raw"   <landmark>_x/y/z columns
"norm"  <landmark>_norm_x/y/z columns (requires ⑤ normalization)
```

### 4-2. create_pose_comparison_animation

Overlays two coordinate modes in one animation (blue = raw, red = normalized).
Used to debug ⑤ normalization.

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

## 5. Planned Functions

These functions exist as stubs (raise `NotImplementedError`); they are the
remaining deliverables for dissertation Task B (see local `code_revision_plan.md`).

### 5-1. plot_reliability_overlay

Overlays the ④ preprocessing reliability mask on a 3D pose animation.
Unreliable landmarks are rendered in a distinct color and size.

```python
plot_reliability_overlay(
    df, landmarks, connections, reliability_col, coord_mode,
)
```

### 5-2. plot_joint_angle_timeseries

Joint angle time-series per frame (unit: degree). Rep ranges shown as
background shading; comparable directly with ⑧ ROM features.

```python
plot_joint_angle_timeseries(
    df, joint_triplets, joint_labels, rep_ranges, coord_mode,
)
```

### 5-3. plot_rep_timeline

② annotation segment labels rendered as a frame-level horizontal bar timeline.
Analysis segments (`use_for_analysis=True`) are highlighted.

```python
plot_rep_timeline(df, segment_col, rep_col, set_col)
```

### 5-4. plot_attribution_chart

⑦ motion attribution results per frame. Shows detected vs. expected active
side and attribution confidence.

```python
plot_attribution_chart(
    df, attribution_col, confidence_col, expected_col,
)
```

### 5-5. plot_phase_segmentation

Smoothed reference-landmark trajectory with the inflection frame marker and
phase-color bands (Descent, Ascent, Bottom_Hold, etc.). Verifies ⑥ phase
segmentation visually.

```python
plot_phase_segmentation(
    df, reference_landmark, reference_axis, phase_col,
)
```

### 5-6. plot_biomech_overlay

3D skeleton overlaid with the CoM point and moment-arm lines (still or
animated). Surfaces ⑨ biomech-proxy outputs in their geometric context.

```python
plot_biomech_overlay(
    df, com_xyz, moment_arm_lines, coord_mode,
)
```

### 5-7. plot_biomarker_radar

Domain-score radar chart (spatial / temporal / control / biomech). Optional
overlay of a reference (synthetic-normal baseline) for visual comparison.

```python
plot_biomarker_radar(
    score_records, reference_records=None,
)
```

Useful for at-a-glance identification of the user's weakest movement-quality
domain.

### 5-8. plot_biomech_load_shift

Within-set load-shift trend: rep number on the X axis, relative moment-arm
proxy on the Y axis. Visualizes the `biomech.load_shift.*.slope`
metric (see [09_biomechanical_proxy.md](09_biomechanical_proxy.md) §7).

```python
plot_biomech_load_shift(
    biomech_records, joints=("knee", "hip"),
)
```

### 5-9. plot_attribution_heatmap

Provenance-traceback heatmap for ⑩ biomarker scoring deductions.

```text
X axis    time (frame or phase boundary)
Y axis    feature_id grouped by domain (spatial / temporal / control / biomech)
Cell      deduction magnitude (color), with hover-disclosed source_fields
Overlay   phase boundaries from ⑥ phase segmentation
```

```python
plot_attribution_heatmap(
    score_records, feat_records, biomech_records,
)
```

### 5-10. plot_robustness_sensitivity

Consumes the long-format CSV produced by `scripts/run_robustness_experiment.py`
(see [12_insilico_simulation.md](12_insilico_simulation.md)) and plots per-metric
stability curves across simulation condition levels.

```python
plot_robustness_sensitivity(
    robustness_csv_path, conditions=None, metrics=None,
)
```

## 6. Implementation Notes

```text
3D pose animation         Plotly (interactive in JupyterLab)
Diagnostic charts         matplotlib + seaborn
Publication output        svg / pdf via save_figure(fig, path, fmt='svg')
```

Both Plotly and matplotlib backends should be supported for every chart in
§5; Plotly for notebook-driven exploration, matplotlib for paper-ready
exports. No function may mutate its input dataframe.

## 7. Related Notebooks

```text
notebook/03_raw_visualization_test.ipynb       3D pose animation (raw)
notebook/04_normalization_test.ipynb           raw vs. normalized comparison
notebook/07_preprocessing_test.ipynb           reliability mask, pipeline integration
notebook/09_motion_attribution_test.ipynb      per-rep motion energy
notebook/10_feature_extraction_test.ipynb      feature-level visualization
notebook/15_visualization_demo.ipynb           planned — all five Task B charts
```

## 8. Code Mapping

```text
src/movement/visualization.py        create_pose_animation,
                                     create_pose_comparison_animation,
                                     plot_reliability_overlay (stub),
                                     plot_joint_angle_timeseries (stub),
                                     plot_rep_timeline (stub),
                                     plot_attribution_chart (stub),
                                     plot_biomarker_radar (stub),
                                     ... (planned 5-5 ~ 5-10)
src/movement/utils.py                get_frame_data, compute_plot_ranges,
                                     validate_landmark_columns
```

## 9. Planned Extensions

- `save_figure(fig, path, fmt='svg')` helper for paper-ready vector exports
- Per-rep small-multiples layout (one row per rep, one column per metric) for
  visual rep-by-rep comparison within a set
- Side-by-side baseline-vs-current radar overlay with confidence shading
- Animated phase-band overlay on `create_pose_animation()` output
- Per-domain deduction stacked-bar chart for clinician-facing 1-page summary
- Tablet-friendly responsive layout for clinical demonstration
- Internationalization of axis labels (Korean / English) driven by a runtime flag
