# Exercise Authoring Notebook

**Document Version:** 0.1.1
**Last Updated:** 2026-05-16
**Korean Sync:** [docs/practical_protocols/exercise_authoring_notebook.md](../../docs/practical_protocols/exercise_authoring_notebook.md) is the matching Korean document.

This document defines the temporary UI-development path for adding new exercises.
At the current stage, a Jupyter notebook authoring UI comes before a separate web
app. The purpose is to create an exercise draft from dropdown-like choices,
checkbox-like choices, and short text inputs, then generate multiple YAML artifacts
from that draft.

This document is not an exercise performance guide or a filming guide. Performance
instructions follow [exercise_performance_protocol.md](exercise_performance_protocol.md),
and filming instructions follow [camera_protocol.md](camera_protocol.md).

---

## 1. Current Decision

Use a notebook UI first in the current development stage.

Reasons:

1. The existing validation workflow is notebook-centered, so no new web framework is required.
2. User selections and generated YAML previews can be reviewed in the same place.
3. The authoring schema can be tested before splitting the current four target exercise YAML files.
4. A future web UI can reuse the same authoring spec and generator.

The first version should start without a new dependency: cell variables, tabular
previews, and YAML text previews are enough. If widgets such as `ipywidgets` become
necessary, the dependency should be decided separately before adding a package.
Streamlit, Dash, or React-based dashboards are not part of the current priority scope.

Current implementation files:

```text
src/movement/definitions/exercise_authoring.py
    ExerciseAuthoringSpec, registry loader, deterministic artifact generator,
    draft writer, overwrite protection

data/registries/
    exercise_authoring_schema.yaml
    movement_patterns.yaml
    support_templates.yaml
    phase_templates.yaml
    landmark_sets.yaml
    analysis_templates.yaml
    performance_templates.yaml
    camera_templates.yaml

notebook/16_exercise_authoring_test.ipynb
    notebook prototype for previewing generated draft YAML
```

---

## 2. Design Principle

The notebook is not the place for hand-editing final data structures. The user
creates one small `exercise_authoring_spec`, and a generator produces the required
YAML artifacts.

```text
Notebook selections
→ exercise_authoring_spec
→ deterministic generator
→ draft YAML preview
→ researcher review
→ canonical YAML files
```

Core principles:

- UI-facing input contains only exercise identity and high-level analysis choices.
- The generator produces the same YAML for the same input.
- Drafts are written first under `data/processed/authoring_drafts/<exercise_id>/`.
- Existing canonical YAML files are not overwritten without explicit approval.
- Automatically generated fields and researcher-review fields are displayed separately.
- Generated text must not claim clinical diagnosis, clinical effect, absolute torque, or absolute force.

---

## 3. Authoring Spec

The first input produced by the notebook UI stays small.

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

This file is a researcher-readable draft. It is not the execution source consumed
directly by the pipeline.

---

## 4. Generated Artifacts

The generator creates the following artifacts from one authoring spec.

```text
data/definitions/exercises/<exercise_id>.yaml
    exercise definition containing only exercise identity

data/definitions/analysis_profiles/<exercise_id>.yaml
    segmentation, landmarks, angle_definitions, feature_domains, quality overrides,
    and compensation-candidate draft

data/protocols/performance/<exercise_id>.yaml
    target sets/reps, count unit, side sequence, participant cues,
    and analysis-disrupting performance patterns

data/protocols/camera/<exercise_id>.yaml
    recommended zones, height, observation purpose, and view-metric reliability
```

Existing `data/definitions/interpretation_rules/<exercise_id>.yaml` and
`data/definitions/clinical/feature_meanings.yaml` remain separate interpretation
and display layers.

The current loader can read both split YAML artifacts and legacy combined exercise
YAML. For split artifacts, the pipeline loads an `ExerciseContext` by
`exercise_id`, composed from the files above, and exposes a backward-compatible
`ExerciseDefinition` to existing stages.

---

## 5. Generated Versus Review Fields

Can be generated automatically:

- `exercise_id`, `display_name`, and basic `classification`
- `support` and draft contact points
- basic `phase_model`
- landmark set and draft angle triplets
- basic `rep_segmentation` / `phase_segmentation` templates
- basic performance count template
- draft camera zone / height recommendation

Requires researcher review:

- compensation candidates and implementation feasibility
- view-metric reliability
- quality thresholds and scoring eligibility
- clinical meaning text
- exercise-specific exception rules
- naming and stage consistency with the current four target exercises

Before review, generated artifacts include this metadata.

```yaml
status: draft
generated_by: exercise_authoring_notebook
requires_review:
  - compensation_candidates
  - view_metric_reliability
  - quality_rules
  - clinical_meaning
```

---

## 6. Notebook Target

The first notebook should be `notebook/16_exercise_authoring_test.ipynb`.

Required cell flow:

1. Standard autoreload cell
2. Registry loading
3. Authoring spec input or selection
4. Exercise identity preview
5. Analysis profile preview
6. Performance protocol preview
7. Camera protocol preview
8. Review checklist display
9. Draft YAML write

The notebook is a UI prototype for validating the generator. The core generation
logic already lives in `src/movement/definitions/exercise_authoring.py`; notebook
cells should call that module rather than reimplementing YAML assembly.

---

## 7. Future Web UI Link

When a web UI is added later, it should not assemble YAML files directly. It should
call the same `exercise_authoring_spec` schema and generator validated in the notebook.

```text
Web UI dropdowns
→ same exercise_authoring_spec
→ same generator
→ same YAML review workflow
```

Therefore, the main output of this stage is not a polished UI. The main outputs are:

1. A small, clear authoring spec
2. A reusable generator
3. YAML previews and a review checklist that a researcher can inspect
