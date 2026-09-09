# FMS Linkage Mapping

**Document Version:** 1.0.1
**Last Updated:** 2026-09-09
**Korean Sync:** `docs/clinical/fms_linkage.md` is the same-version Korean source.

This document does not reproduce FMS scoring text. It is a retained/deferred
crosswalk describing how `movement_project` feature/domain deductions may
parallel FMS-like movement-observation categories. It is not an endpoint for the
current dissertation-facing verification and not a participant-feedback screen.

## Principles

- Green / Yellow / Red labels are optional support labels derived from `BiomarkerScoreRecord.final_score`; they are not FMS scores.
- The current dissertation verification prioritizes feasibility, output availability, robustness, and interpretability summaries; FMS-like traffic-light output is not required.
- The YAML stores feature links and citation-only references, not protected scoring text.
- Medical conclusion or classification claims are intentionally avoided.
- `data/definitions/clinical/fms_mapping.yaml` is the single source of truth.

## Exercise Crosswalk

| Exercise | FMS-like Reference Pattern | Primary Linked Features |
|---|---|---|
| Squat | deep squat-like pattern | knee valgus, trunk flexion, heel lift, knee ROM symmetry |
| Lunge | inline lunge-like pattern | hip-center stability, knee valgus, trunk flexion, heel lift |
| Pike push-up | trunk stability push-up-like pattern | shoulder symmetry, elbow symmetry, hip-center stability, shoulder ROM |
| Plank shoulder tap | rotary stability-like pattern | pelvic rotation, lateral pelvic shift, shoulder symmetry, tempo CV |

## Implementation Surface

```text
data/definitions/clinical/fms_mapping.yaml
src/movement/definitions/clinical.py
tests/test_fms_mapping.py
```

`traffic_light_for_score()` accepts either a numeric score or a record with
`final_score` and `exercise_id`, then returns a `TrafficLightLabel` with YAML
provenance for reporting and dashboard views.
