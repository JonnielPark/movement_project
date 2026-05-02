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
06_preprocessing_test.ipynb
07_motion_attribution_test.ipynb
08_feature_extraction_test.ipynb
09_biomechanical_proxy_test.ipynb
10_scoring_test.ipynb
11_pipeline_end_to_end_test.ipynb
12_simulation_robustness_test.ipynb
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
| 06 | preprocessing | not yet implemented |
| 07 | motion_attribution | not yet implemented |
| 08 | features | not yet implemented |
| 09 | biomech | not yet implemented |
| 10 | scoring | not yet implemented |
| 11 | pipeline end-to-end | partial (implemented steps only) |
| 12 | simulation robustness | not yet implemented |

Notebooks `06` and `07` include design documentation and `NotImplementedError` tests
so that the expected behaviour is verifiable even before the modules are built.
