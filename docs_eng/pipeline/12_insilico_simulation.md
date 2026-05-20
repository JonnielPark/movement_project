# 12. In-Silico Simulation

**Document Version:** 1.1.0
**Last Updated:** 2026-05-21
**Korean Sync:** `docs/pipeline/12_insilico_simulation.md` is the same-version Korean source.

Pipeline step ⑫ is an external robustness harness. It injects controlled
distortions into synthetic or reference pose data, reruns the analysis pipeline,
and summarizes how metrics respond.

This is engineering verification, not clinical validation or diagnostic accuracy.

---

## 1. Pipeline Position

```text
Base pose sample → distortion copy → ①-⑩ pipeline replay → robustness summary
```

Simulation is not invoked by `run_pipeline()`.

Inputs:

```text
base synthetic/reference pose data
exercise YAML
simulation settings from configs/pipeline_default.yaml
```

---

## 2. Design Contract

Allowed:

```text
distortion injection on a copy of the DataFrame
log of applied condition and level
metric responsiveness / monotonicity / specificity checks
long-format outputs for ⑪ visualization
```

Not allowed:

```text
in-place mutation of source data
absolute physical units
using synthetic labels as clinical diagnosis
suppressing pipeline warnings or failure modes
```

---

## 3. Implemented Distortions

`src/movement/simulation/synthetic.py` provides:

```text
add_gaussian_noise       coordinate jitter
add_occlusion            NaN coordinates and optional zero visibility
add_velocity_spike       abrupt coordinate jumps
restrict_rom             bounded joint-angle restriction
generate_squat_csv       synthetic squat sample generator
```

Each distortion returns `(modified_df, log_dict)` and leaves the input unchanged.

---

## 4. Planned Experiment Matrix

```text
Gaussian noise           coordinate-noise robustness
Occlusion                missing/low-visibility robustness
Velocity spike           preprocessing outlier behavior
ROM restriction          responsiveness to limited movement
Viewpoint variation      planned; camera-zone/view sensitivity
Compensation injection   planned; named compensation-pattern robustness
```

The grid should be mirrored in config so condition levels are not hardcoded in
notebooks.

---

## 5. Robustness Metrics

```text
monotonicity
    Does a target metric change consistently as distortion strength increases?

responsiveness
    Does the intended metric react to the matched distortion?

specificity
    Do unrelated metrics stay relatively stable under unmatched distortion?

false_correction_rate
    Does motion attribution introduce wrong side corrections under distortion?
```

Metrics should be summarized at rep level and, when available, phase level.

---

## 6. Planned Runner

```text
scripts/run_robustness_experiment.py
    load config and base samples
    build condition grid
    apply each distortion
    run ①-⑩ pipeline
    collect FeatureRecord, BiomechRecord, BiomarkerScoreRecord summaries
    write long-format CSV and markdown summary
```

Long-format output should use:

```text
condition × level × exercise × rep × phase × metric
```

so `plot_robustness_sensitivity()` can consume it directly.

---

## 7. Code Mapping

```text
src/movement/simulation/synthetic.py   distortion functions and sample generator
src/movement/simulation/__init__.py    public re-exports
configs/pipeline_default.yaml          simulation section
scripts/run_robustness_experiment.py   planned runner
tests/test_simulation.py               planned behavior tests
```

---

## 8. Planned Extensions

- Viewpoint variation injector.
- Named compensation-pattern injection.
- Combined noise + occlusion conditions.
- Per-exercise grid pruning.
- Failure-mode catalog in markdown summary.
- Bootstrap confidence bands across random seeds.
