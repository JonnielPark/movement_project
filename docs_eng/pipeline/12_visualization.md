# 12. Visualization

**Document Version:** 1.1.0
**Last Updated:** 2026-05-21
**Korean Sync:** `docs/pipeline/12_visualization.md` is the same-version Korean source.

Pipeline step ⑫ is called outside the ①-⑪ runner. It renders pose data,
intermediate reports, features, biomech proxies, and biomarker outputs for
diagnostic review and dissertation figures.

Visualization functions return figure objects and must not mutate input data.

---

## 1. Role

```text
Diagnostic review
    Inspect raw data, preprocessing, normalization/canonicalization candidates,
    segmentation boundaries, and feature availability.

Result reporting
    Present feature, biomech, biomarker, and robustness outputs with enough
    provenance for a reviewer to trace the result back to source fields.
```

The visualization layer should show confidence/provenance beside scored results,
especially computed-but-withheld features and low-confidence depth-dependent
metrics.

---

## 2. Step Coverage

```text
④ Preprocessing       reliability overlay and before/after quality views
⑤ Normalization       raw/norm comparison
⑥ Canonicalization    norm/canon/candidate comparison
⑦ Segmentation        rep/phase boundaries and failure points
⑧ Motion Attribution  active-side and correction logs
⑨ Feature Extraction  joint angles, ROM, feature availability
⑩ Biomech Proxy       CoM and moment-arm/load-shift proxies
⑪ Biomarker Scoring   domain scores, deductions, withheld features
⑬ Simulation          robustness sensitivity curves
```

---

## 3. Provenance Convention

Figures should surface:

```text
record id / rep id / phase
feature_id or metric_id
value and unit
availability and confidence reasons
source_fields
deduction or withheld-feature reason when relevant
```

Interactive figures may use hover text; static dissertation figures should use
captions, legends, or side summaries.

---

## 4. Implemented Functions

```text
create_pose_animation
    Plotly 3D pose animation for raw, norm, or available candidate coordinate
    modes.

create_pose_comparison_animation
    Overlay two coordinate modes, such as raw vs norm or norm vs canon, for
    visual QC.
```

The optional `floor`/candidate coordinate modes are review tools and do not imply
downstream promotion.

---

## 5. Planned Reporting Functions

Visualization stubs are intentionally retained until implementation starts.

```text
plot_reliability_overlay
plot_joint_angle_timeseries
plot_rep_timeline
plot_attribution_chart
plot_phase_segmentation
plot_biomech_overlay
plot_biomarker_radar
plot_biomech_load_shift
plot_attribution_heatmap
plot_robustness_sensitivity
plot_biomarker_score_breakdown
save_figure(fig, path, fmt='svg')
```

All planned functions should consume stable pipeline records/reports rather than
recomputing metrics internally.

---

## 6. Implementation Rules

```text
Notebook exploration       Plotly is acceptable.
Publication figures        matplotlib/seaborn + svg/pdf/png export.
Input mutation             forbidden.
source_fields              preserve in hover/caption/side summary.
Low confidence             visible beside the plotted value.
Language                   Korean/English labels should be runtime-selectable later.
```

---

## 7. Code Mapping

```text
src/movement/reporting/visualization.py  implemented animations + planned stubs
src/movement/core/utils.py               frame extraction, plot ranges,
                                         landmark-column validation
notebook/00_setup/setup_02_raw_visualization_test.ipynb          raw pose animation
notebook/20_stage_checks/04_preprocessing_test.ipynb             reliability review
notebook/20_stage_checks/05_normalization_test.ipynb             raw/norm review
notebook/20_stage_checks/06_canonicalization_test.ipynb          norm/canon candidate review
notebook/20_stage_checks/09_feature_extraction_test.ipynb        feature review
```

---

## 8. Planned Extensions

- Dissertation-ready figure export helper.
- Deduction and withheld-feature side-by-side summary.
- Robustness sensitivity figure once the simulation runner exists.
- Per-rep small multiples for set-level consistency review.
