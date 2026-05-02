# Notebooks

These notebooks are ordered as step-by-step checks for a new user after cloning and installing the package.

They are not ordered by development history. They are ordered by expected user verification flow.

## Order

```text
00_environment_check.ipynb
01_data_loading_test.ipynb
02_validation_test.ipynb
03_raw_visualization_test.ipynb
04_normalization_test.ipynb
05_annotation_mask_test.ipynb
06_exercise_definition_test.ipynb
07_preprocessing_test.ipynb
08_motion_attribution_test.ipynb
09_feature_extraction_test.ipynb
10_biomechanical_proxy_test.ipynb
11_scoring_test.ipynb
12_pipeline_end_to_end_test.ipynb
13_simulation_robustness_test.ipynb
```

## Implementation Status

| Notebook | Module | Status |
|----------|--------|--------|
| 00 | environment | implemented |
| 01 | io | implemented |
| 02 | validation | implemented |
| 03 | visualization | implemented |
| 04 | normalization | implemented |
| 05 | annotation | implemented |
| 06 | exercise_definition | implemented |
| 07 | preprocessing | not yet implemented |
| 08 | motion_attribution | not yet implemented |
| 09 | features | not yet implemented |
| 10 | biomech | not yet implemented |
| 11 | scoring | not yet implemented |
| 12 | pipeline end-to-end | partial (implemented steps only) |
| 13 | simulation robustness | not yet implemented |

Notebooks `06` and `07` include design documentation and `NotImplementedError` tests
so that the expected behaviour is verifiable even before the modules are built.
