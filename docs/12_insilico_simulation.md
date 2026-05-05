# 12. In-silico Simulation

Pipeline step ⑫. Called independently outside the ①–⑩ runner. An engineering
robustness harness that injects controlled distortions into normal synthetic
pose data and replays the pipeline to characterize how the framework behaves
under realistic monocular-data degradations.

This step is **engineering verification**, not clinical validation. It does
not produce patient-level outputs, and its results must not be reported as
diagnostic accuracy. Corresponds to dissertation §8.

---

## 1. Pipeline Position

```text
Pose CSV
→ ① ~ ⑪ analysis pipeline (normal flow)
                                       ↑
                                       │
   ⑫ Simulation  ──── inject distortion ┘
                  (called outside the ①–⑩ runner)
```

Simulation is **not** invoked by `run_pipeline()`. It is a separate runner
that loops the pipeline over distorted data and aggregates the resulting
`BiomarkerScoreRecord` and `BiomechRecord` outputs.

Required inputs:
```text
normal synthetic pose data         data/sample/mediapipe_squat_synthetic.csv
                                   (or pipeline-internal generators)
exercise YAML                      sets the joint triplets used by ROM restriction
distortion configuration           configs/pipeline_default.yaml :: simulation
```

## 2. Design Principle

```text
Allowed:
    Distortion injection on a copy of the input dataframe
    Per-distortion log dict recording exactly what was applied
    Engineering-robustness metrics (monotonicity, responsiveness, specificity)
    Synthetic abnormal labeling for downstream evaluation
    A/B comparison with visibility-weighted vs unweighted biomech proxy

Not allowed:
    Modifying the original input dataframe in place
    Introducing absolute units (the harness is dimensionless throughout)
    Using "normal / abnormal" labels as clinical diagnoses
    Using simulation outputs as patient-data substitutes
    Suppressing pipeline warnings (the harness must reveal failure modes)
```

## 3. Distortion Functions

`simulation/synthetic.py` provides four distortion injectors. Each returns a
`(modified_df, log_dict)` tuple; the original dataframe is not mutated.

### 3-1. Gaussian Noise

Coordinate jitter modeling pose-estimator measurement noise.

```python
add_gaussian_noise(
    df,
    sigma_torso_ratio=0.01,    # 1 % of torso length
    landmarks=None,            # None → all landmarks
    seed=42,
)
```

### 3-2. Occlusion

Sets landmark coordinates to NaN and visibility to 0 over a frame range.
Verifies ④ preprocessing reliability gating and ⑨ visibility weighting.

```python
add_occlusion(
    df,
    target_landmarks=["left_knee"],
    frame_range=(120, 180),
    zero_visibility=True,
)
```

### 3-3. Velocity Spike

Inserts position jumps at specified frames; verifies the velocity outlier
detector inside ④ preprocessing.

```python
add_velocity_spike(
    df,
    target_landmarks=["right_ankle"],
    spike_frames=[150],
    spike_magnitude_torso_ratio=0.5,
    seed=42,
)
```

### 3-4. ROM Restriction

Adjusts the distal landmark of a joint triplet so the included angle does
not exceed `restriction_deg`. Models stiffness or pain-avoidance limited
flexion patterns.

```python
restrict_rom(
    df,
    joint="left_knee",
    restriction_deg=90.0,
    landmarks_triplet=("left_hip", "left_knee", "left_ankle"),
    rep_frames=[(85, 160), (170, 245)],
)
```

## 4. Experimental Condition Matrix

Mirror of `configs/pipeline_default.yaml :: simulation`:

| Condition                | Levels                                  | Intent                                            |
|--------------------------|-----------------------------------------|---------------------------------------------------|
| Viewpoint variation      | ±15°, ±30° from frontal                 | Robustness to monocular viewpoint shifts          |
| ROM restriction (knee)   | 30°, 60°, 90° limit                     | Responsiveness to compensation patterns           |
| Gaussian noise σ         | 0.005, 0.01, 0.02 (`torso_length_ratio`)| Robustness to coordinate noise                    |
| Occlusion duration       | 5, 15, 30 frames                        | Robustness to occlusion                           |
| Velocity spike magnitude | 0.2, 0.5, 1.0 (`torso_length_ratio`)    | Robustness to estimation instability              |

The matrix is mirrored 1:1 in the YAML so that operators do not edit Python
code to add a level.

## 5. Robustness Metrics

Computed at both rep-level and phase-level (Descent / Ascent separately) so
that phase-resolved monotonicity can be reported for dissertation §4.5.

```text
monotonicity           Does the metric move in a consistent direction as
                       distortion strength increases?
                       Output: Spearman ρ between distortion level and metric.

responsiveness         Does the metric react when the simulated compensation
                       matches the candidate it tracks?
                       Output: deduction magnitude per distortion level.

specificity            Do unrelated metrics stay flat under that distortion
                       (false-positive control)?
                       Output: drift of off-target metrics per distortion level.

false_correction_rate  How often does ⑦ Motion Attribution auto_correct fire
                       incorrectly under the distortion?
                       Output: fraction of reps with action='swap'
                                where attribution_consistent should be True.
```

A metric is judged "robust" when monotonicity is high under matched
distortion **and** specificity drift is low under unmatched distortion.

## 6. Robustness Experiment Runner (planned)

```python
# scripts/run_robustness_experiment.py
def main():
    cfg          = load_pipeline_config(...)
    base_samples = load_normal_synthetic_samples(...)
    grid         = build_experiment_grid(cfg.simulation)

    results = []
    for sample in base_samples:
        for condition_name, level in grid:
            distorted = apply_distortion(sample, condition_name, level)
            report    = run_pipeline(distorted, cfg)
            results.append(summarize(report, condition_name, level))

    write_results_csv(results, "outputs/robustness_<timestamp>.csv")
    write_summary_report(results, "outputs/robustness_<timestamp>.md")
```

Each result row is keyed by `condition × level × metric × phase` and stored
in long-format CSV so that ⑪ visualization's `plot_robustness_sensitivity()`
can consume it directly.

## 7. Done Criteria

```text
1. simulation/synthetic.py implements all five distortion functions
   (the four §3 distortions + the planned viewpoint variation).
2. scripts/run_robustness_experiment.py iterates the full grid and writes
   long-format CSV plus a summary md.
3. monotonicity / responsiveness / specificity scores are computed at
   rep-level and phase-level.
4. tests/test_simulation.py verifies basic monotonic behavior of each
   distortion function.
5. The simulation section of configs/pipeline_default.yaml maps 1:1 to
   this runner.
```

## 8. Code Mapping

```text
src/movement/simulation/__init__.py    re-exports of distortion functions
src/movement/simulation/synthetic.py   add_gaussian_noise, add_occlusion,
                                       add_velocity_spike, restrict_rom,
                                       generate_squat_csv
scripts/run_robustness_experiment.py   planned: condition-grid runner
configs/pipeline_default.yaml          simulation: section mirrors §4 matrix
notebook/14_simulation_robustness_test.ipynb   planned demo
```

## 9. Relationship to Other Steps

- **④ Preprocessing** — robustness target; `restrict_rom` and
  `add_velocity_spike` exercise the velocity outlier detector and visibility
  gating logic. Verifies that ④ does **not** correct genuine compensation
  patterns into normal-looking data.
- **⑦ Motion Attribution** — `false_correction_rate` is the gating metric
  for promoting `auto_correct` mode from off-by-default to on-by-default.
- **⑨ Biomech Proxy** — visibility-weighted A/B comparison surfaces the
  contribution of low-confidence-frame exclusion to overall stability.
- **⑩ Biomarker Derivation** — the synthetic-normal baseline is generated
  by running the pipeline on **non-distorted** synthetic data, then
  simulation evaluates Z-score deductions of distorted data against that
  baseline.
- **⑪ Visualization** — `plot_robustness_sensitivity()` consumes the
  long-format CSV produced by the runner.

## 10. Planned Extensions

- **Viewpoint variation injector** — synthesize ±15° / ±30° camera offset
  by 3D rotation about the body vertical axis prior to pose estimation;
  required to close the matrix in §4
- **Combined distortion modes** — co-occurring noise + occlusion to model
  realistic adverse recording conditions
- **Compensation-pattern synthesis** — programmatic injection of named
  compensation patterns (knee valgus, lateral pelvic shift, etc.) using
  exercise-definition-driven trajectory deformations rather than purely
  geometric ROM restriction
- **Per-exercise grid pruning** — skip non-applicable conditions per exercise
  (e.g., knee ROM restriction is meaningless for `pike_pushup`)
- **Failure-mode catalogue** — auto-generated md report listing every
  (condition, level) where pipeline raised an exception
- **Bootstrap-CI per metric** — repeat the grid with multiple seeds and
  attach 95 % CI bands to monotonicity / responsiveness scores
- **Real-data swap test** — load a small corpus of real recordings and
  inject the same distortions; verify behavior parity with the synthetic
  case (distinct from clinical validation)
