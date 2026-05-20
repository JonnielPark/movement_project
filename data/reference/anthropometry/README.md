# Size Korea 8th Anthropometric Skeleton Prior

This folder stores compact, derived reference artifacts for the anthropometric skeleton prior used by the movement analysis project.

## Current Data Level

The current artifacts are **Stage A aggregate fallback** materials. They use the Size Korea 8th 2020 3D full-body automatic measurement schema and aggregate statistical summaries, but they do not include individual-level raw rows.

Because row-level paired measurements are not included here, these files must not be interpreted as empirical P5/P95 ratio distributions. They are intended only as conservative plausibility priors for segment-length/depth-residual checks while monocular depth confidence remains low.

## Files

- `size_korea8_3d_auto_skeleton_prior.yaml`: loadable skeleton-prior draft for segment plausibility and confidence adjustment.
- `size_korea8_3d_auto_segment_map.csv`: mapping between pose-model segments and Size Korea 3D full-body automatic measurement proxies.
- `size_korea8_3d_auto_aggregate_ratio_preview.csv`: overall and sex-total aggregate ratio preview. Ratio percentiles are intentionally unavailable at this stage.
- `size_korea8_3d_auto_unavailable_segments.csv`: pose segments that should remain unavailable under the 3D full-body-auto-only source scope.
- `source_manifest.yaml`: source-document provenance and commit policy.

## Commit Policy

Public binary source documents such as PDFs/XLSX workbooks are not committed here. Keep them locally or in a private/raw data area, and commit only compact derived artifacts and provenance metadata. Individual-level anthropometric rows, if obtained later, should remain outside Git; only anonymized aggregate outputs should be committed.
