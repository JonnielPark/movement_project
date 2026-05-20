# Exercise Authoring Notebook

**Document Version:** 0.2.0
**Last Updated:** 2026-05-21
**Korean Sync:** [docs/practical_protocols/exercise_authoring_notebook.md](../../docs/practical_protocols/exercise_authoring_notebook.md) is the matching Korean document.

This document defines the temporary notebook-first workflow for adding new
exercises. It is not a performance guide or filming guide. The notebook creates
a small `exercise_authoring_spec`, previews generated YAML artifacts, and writes
drafts for researcher review before canonical files are updated.

---

## 1. Current Decision

Use a notebook UI before building a separate web app.

```text
reason 1   current validation workflow is notebook-centered
reason 2   YAML previews and researcher review can happen in one place
reason 3   the split-YAML schema can be tested before broad exercise expansion
reason 4   a future web UI can reuse the same spec and generator
```

No new UI dependency is required for the first version. Cell variables, tables,
and YAML text previews are enough. Any widget or web framework dependency must
be decided separately before adding a package.

## 2. Authoring Flow

```text
Notebook selections
→ exercise_authoring_spec
→ deterministic generator
→ draft YAML preview
→ researcher review
→ canonical YAML files
```

Core rules:

```text
UI input is small and researcher-facing
same input produces the same YAML
drafts are written under data/processed/authoring_drafts/<exercise_id>/
canonical YAML is not overwritten without explicit approval
generated fields and review-required fields are separated
generated text must avoid clinical diagnosis, clinical-effect claims, absolute force, and absolute torque
```

## 3. Authoring Spec

Example:

```yaml
exercise_id: squat
display_name: Bodyweight Squat
movement_pattern: squat
posture_type: standing
laterality: bilateral_symmetric
support_template: bilateral_feet
primary_body_regions: [hip, knee, ankle]
primary_plane: sagittal
secondary_planes: [frontal, transverse]
phase_template: descent_ascent
counting_template: repeated_repetition
camera_template: front_oblique_lower_body
analysis_template: bilateral_lower_body_closed_chain
```

The spec is a draft input, not the execution source consumed by the pipeline.

## 4. Generated Artifacts

One spec generates four artifact families:

```text
data/definitions/exercises/<exercise_id>.yaml
    exercise identity

data/definitions/analysis_profiles/<exercise_id>.yaml
    segmentation, landmarks, angle definitions, feature domains, quality overrides

data/protocols/performance/<exercise_id>.yaml
    target sets/reps, count unit, side sequence, participant cues,
    analysis-disrupting performance patterns

data/protocols/camera/<exercise_id>.yaml
    recommended zones, height, observation purpose, view-metric reliability
```

Interpretation rules and feature-meaning text remain separate display layers.
The loader supports both split YAML artifacts and legacy combined exercise YAML.

## 5. Review Boundary

Generated automatically:

```text
exercise identity and classification
support/contact template
draft phase model
landmark set and draft angle triplets
rep/phase segmentation templates
performance count template
draft camera recommendation
```

Requires researcher review:

```text
compensation candidates and implementation feasibility
view-metric reliability
quality thresholds and scoring eligibility
clinical meaning text
exercise-specific exception rules
naming and stage consistency with existing exercises
```

Draft artifacts include:

```yaml
status: draft
generated_by: exercise_authoring_notebook
requires_review:
  - compensation_candidates
  - view_metric_reliability
  - quality_rules
  - clinical_meaning
```

## 6. Notebook Target

Target notebook:

```text
notebook/16_exercise_authoring_test.ipynb
```

Required cell flow:

```text
1. autoreload
2. registry loading
3. authoring spec input/selection
4. exercise identity preview
5. analysis profile preview
6. performance protocol preview
7. camera protocol preview
8. review checklist
9. draft YAML write
```

Notebook cells must call `src/movement/definitions/exercise_authoring.py` rather
than reimplement YAML assembly.

## 7. Code Mapping

```text
src/movement/definitions/exercise_authoring.py
    ExerciseAuthoringSpec
    load_authoring_registries()
    validate_authoring_spec()
    generate_authoring_artifacts()
    artifact_to_yaml()
    draft_artifact_paths()
    write_authoring_draft_artifacts()

data/registries/
    exercise_authoring_schema.yaml
    movement_patterns.yaml
    support_templates.yaml
    phase_templates.yaml
    landmark_sets.yaml
    analysis_templates.yaml
    performance_templates.yaml
    camera_templates.yaml
```

A future web UI should call the same spec and generator. It should not assemble
canonical YAML directly.
