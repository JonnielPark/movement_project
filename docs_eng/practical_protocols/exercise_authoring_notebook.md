# Exercise Authoring Notebook

**Document Version:** 0.2.25
**Last Updated:** 2026-06-20
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

No new UI dependency is required for the first version. The notebook provides an
optional dropdown-backed selection cell when widgets are available, while keeping
a plain-variable fallback so the workflow remains executable without widget UI.
Any new dependency must be decided separately before adding a package.

The authoring UI should collect atomic movement descriptors rather than ask the
researcher to choose a movement archetype directly. Primary and secondary joint
actions are selected first, then interpreted with support pattern,
laterality, posture, body geometry, and primary body regions. The exported
`movement_template_id` is derived from that joint-action-plus-context
combination. The legacy `movement_pattern` key may still appear as an internal
compatibility alias until a separate registry migration is planned.

This restriction applies to selectable template labels. `exercise_id` and
`display_name` may use the concrete exercise name being authored.

## 2. Authoring Flow

```text
Notebook atomic selections
→ joint_action + context derivation
→ movement_template_id / legacy movement_pattern anchor
→ exercise_authoring_spec
→ deterministic generator
→ draft YAML preview
→ draft bundle export
→ canonical loader-view preview
→ researcher review
→ canonical YAML install
```

Core rules:

```text
UI input is small and researcher-facing
same input produces the same YAML
draft bundles are written under data/processed/authoring_drafts/<exercise_id>/
git-tracked examples are copied under data/examples/exercise_authoring/<exercise_id>/
canonical YAML is not overwritten without explicit approval
generated fields and review-required fields are separated
generated text must avoid clinical diagnosis, clinical-effect claims, absolute force, and absolute torque
```

The notebook supports three authoring modes:

| Mode | Purpose | File policy | Metadata policy |
|---|---|---|---|
| `draft_bundle` | Local generated draft for preview and researcher review. | `data/processed/authoring_drafts/<exercise_id>/` | Keeps top-level `status: draft`, `generated_by`, and `requires_review`. |
| `canonical_loader_view` | Loader-time view of the draft bundle as the intended canonical exercise, so the pipeline can be tested as if the exercise had no prior hand-authored definition. | Reuses the draft bundle; no duplicate draft files are written. | Moves draft top-level metadata into runtime `authoring_provenance`. |
| `canonical_install` | Future reviewed promotion into the runtime `data/definitions/` and `data/protocols/` directories. | Main runtime directories. | Requires explicit researcher approval and is not the default notebook action. |

The current prototype implements `draft_bundle` and `canonical_loader_view`.
`canonical_install` remains a manual promotion step until equivalence checks and
review gates are stable.

## 3. Authoring Spec

Example:

```yaml
exercise_id: squat
display_name: Bodyweight Squat
movement_template_id: bilateral_lower_body_closed_chain
movement_pattern: squat
movement_pattern_source: derived_from_joint_actions_and_context
posture_type: standing
body_geometry: neutral_upright
laterality: bilateral_symmetric
support_template: bilateral_feet
primary_body_regions: [hip, knee, ankle]
primary_joint_actions:
  - hip_flexion_extension
  - knee_flexion_extension
  - ankle_dorsiflexion_plantarflexion
secondary_joint_actions:
  - trunk_flexion_extension
primary_plane: sagittal
secondary_planes: [frontal, transverse]
phase_template: descent_ascent
counting_template: repeated_repetition
target_count_per_set: 10
camera_view_family: front_oblique
camera_height_level: H2
analysis_template: bilateral_lower_body_closed_chain
```

The spec is a draft input, not the execution source consumed by the pipeline.
In the current notebook UI, `movement_pattern: squat` is not selected directly.
It is derived from lower-body flexion/extension joint actions in a standing,
bilateral, two-foot support context. `movement_template_id` is the preferred
downstream analysis-template identifier; `movement_pattern` remains a legacy
registry family used to seed draft biomechanical defaults.

`posture_type` describes the broad starting body orientation, while
`body_geometry` adds shape information inside that posture. For example,
floor-supported prone posture with neutral body-line geometry describes a plank
family, while the same posture with high-hip inverted-V geometry describes a
pike-like upper-body press family.

Current posture choices are explicit rather than hidden behind a broad custom
option:

| Posture | Meaning | Representative examples |
|---|---|---|
| `standing` | Upright body orientation with feet or one foot acting as the main support base. | squat, lunge, hip hinge, step-up, balance reach |
| `floor_supported_prone` | Body faces the floor and is supported by hands, feet, forearms, or knees. Body shape is refined by `body_geometry`. | plank, plank shoulder tap, mountain climber, pike push-up |
| `kneeling` | One or both knees are primary support landmarks. | tall-kneeling reach, half-kneeling press, kneeling push-up |
| `seated` | Pelvis is supported by a seat or floor, with trunk and limb motion analyzed from a seated base. | seated march, seated trunk rotation, seated shoulder raise |
| `supine` | Body lies face-up. | dead bug, glute bridge, supine heel slide, hollow hold |
| `side_lying` | Body lies on one side or is side-supported. | side plank, side-lying hip abduction, clamshell |
| `hanging` | Body is suspended from an overhead support. | dead hang, pull-up, hanging knee raise |
| `external_object_supported` | A bench, wall, chair, bar, or machine meaningfully supports the body. | wall squat, bench-supported row, chair sit-to-stand, incline push-up |

The notebook filters `body_geometry` choices from `posture_type`:

| Posture | Allowed body geometry |
|---|---|
| `standing` | `neutral_upright`, `forward_lean_hinge` |
| `floor_supported_prone` | `neutral_prone_line`, `high_hip_inverted_v`, `quadruped` |
| `kneeling` | `neutral_upright`, `tall_kneeling_upright`, `half_kneeling_upright`, `quadruped` |
| `seated` | `neutral_upright`, `seated_flexed_trunk`, `long_sitting`, `cross_legged_sitting` |
| `supine` | `supine_hooklying`, `supine_tabletop`, `supine_straight_leg`, `supine_hollow` |
| `side_lying` | `side_supported`, `side_plank_line`, `side_lying_relaxed` |
| `hanging` | `neutral_upright`, `hanging_tuck`, `hanging_pike` |
| `external_object_supported` | `neutral_upright`, `neutral_prone_line`, `side_supported`, `supported_incline_line`, `machine_supported_fixed_trunk`, `custom` |

Some body-geometry choices are registered ahead of implementation. They are
selectable authoring descriptors, but they do not automatically map to a current
movement-template family until the corresponding registry template is added.

Dead bug-like exercises should start from `posture_type: supine`. They are not
mapped to a current movement-template family until a supine core-control
registry family is added.

`laterality` describes the side pattern of the intended movement: bilateral
symmetric, bilateral asymmetric, alternating, or unilateral. It is not strongly
filtered by posture because most postures can have bilateral, alternating, or
single-side variants. Instead, laterality informs counting, active-side
attribution, side-sequence review, and whether a generated draft needs additional
researcher review.

`support_template` describes load-bearing contact with the support surface, so it
is filtered by `posture_type`. This prevents physically mismatched authoring
states such as supine movement with two-foot standing support. Some support
templates are registered before full analysis-template support exists; those
choices are valid descriptors but may still require a future movement-template
or analysis template before draft YAML can be generated.

The notebook filters `support_template` choices from `posture_type`:

| Posture | Allowed support template |
|---|---|
| `standing` | `bilateral_feet`, `split_stance`, `single_foot` |
| `floor_supported_prone` | `hands_and_feet`, `forearms_and_feet`, `hands_and_knees`, `hands_and_feet_with_trunk` |
| `kneeling` | `knees_floor`, `one_knee_one_foot`, `hands_and_knees` |
| `seated` | `seated_base` |
| `supine` | `supine_body_floor` |
| `side_lying` | `side_body_floor` |
| `hanging` | `overhead_hang` |
| `external_object_supported` | `external_object`, `bilateral_feet`, `split_stance`, `hands_and_feet` |

`primary_body_regions` is not a separate movement description. It is an analysis
focus list derived from the selected primary and secondary joint actions, then
shown as editable checkboxes. The researcher may keep the suggested regions or
override them when the analysis focus differs from the literal joint-action
list. This keeps the UI from asking for the same information twice while still
preserving an explicit region list for reporting, visualization, and future
feature grouping.

`primary_plane` is the main body-relative anatomical plane of the movement, not
the camera view. It should be shown as a single-choice toggle button with
`sagittal`, `frontal`, `transverse`, and `static`. The `secondary_planes` field
represents additional compensation or control planes, so it should exclude the
selected primary anatomical plane. `multiplanar` is not a direct user selection
in this notebook; it can be derived later when the primary and secondary
anatomical planes include two or more unique planes. `static` remains a primary
descriptor for hold/control exercises.

`phase_template` describes how one repetition is detected and how the inside of
that repetition is divided into phases. It is a segmentation descriptor, not an
exercise name. Implemented phase templates may be used as normal draft inputs.
Planned templates may be registered ahead of implementation so new exercise
families can be described, but the notebook must show a warning when one is
selected. Planned templates require segmentation review before becoming canonical
pipeline inputs.

Phase templates may declare the coordinate family used for boundary detection.
For example, a squat-like template may use recording-view raw `hip_center`
`image_y` for descent/ascent detection while downstream feature and scoring
stages still consume normalized coordinates. See
`docs_eng/pipeline/06_segmentation.md` for the report contract.

The notebook should recommend and order phase templates from the earlier
authoring axes rather than hard-filter them. The recommendation may use
`posture_type`, `body_geometry`, `support_template`, selected joint actions, and
`primary_plane`. Recommended templates are shown first, while other templates
remain selectable for unusual exercises. If no strong recommendation exists, the
notebook should show that state and keep all templates available.

`counting_template` defines how counts are interpreted, such as repeated
repetitions, same-side blocks, or left-right pairs. The current recording unit is
a single set, so the basic authoring UI collects `target_count_per_set` as the
main prescription value. `target_sets` and `rest_between_sets_s` are optional
protocol metadata, not required analysis inputs for a set-level recording.
Generated authoring drafts should omit them unless they are explicitly provided.

The notebook should recommend and order counting templates from `laterality` and
`phase_template`. Bilateral and fixed-side movements usually recommend
`repeated_repetition`. Alternating movements recommend pair or side-sequence
templates. Static hold phases recommend a planned hold-seconds template. As with
phase templates, non-recommended counting templates remain selectable for edge
cases, but the notebook should show a warning or note when the selected counting
template does not match the current laterality/phase context.

`camera_view_family` and `camera_height_level` are selected as separate
controls rather than a single long H/Z dropdown or an exercise-name camera
preset. `camera_view_family` groups mirror-equivalent horizontal directions such
as `front_oblique` (`Z2`/`Z8`), `side` (`Z3`/`Z7`), and `rear_oblique`
(`Z4`/`Z6`). `H` describes the camera height. The notebook should show short
labels from `data/camera/camera_zones.yaml` beside each control so the
researcher can understand each code without reading the YAML first.

Camera recommendations are advisory, like phase and counting recommendations.
The notebook should recommend and order view-family/H combinations from the
earlier authoring axes, including posture, support, laterality, selected joint
actions, and primary plane. Recommended combinations are shown first.
Non-recommended combinations remain selectable and should produce a warning, not
a hard block, because unusual camera placement may still be useful for review or
future method comparison.

Generated camera draft YAML should retain both the selected view-family/H
position and the recommendation context:

```yaml
camera_protocol:
  selected_view:
    view_family: front_oblique
    member_zones: [Z2, Z8]
    height: H2
    recommendation_status: recommended
  recommended_view_positions:
    - {view_family: front_oblique, member_zones: [Z2, Z8], height: H2}
  non_recommended_view_positions:
    - {view_family: side, member_zones: [Z3, Z7], height: H2}
  recommended_zones: [Z2, Z8]
  recommended_height: H2
  coordinate_correction: none
```

The selected view-family/H status is provenance for later feature-availability and
view-metric reliability checks. It is not a camera calibration result and does
not correct coordinates.

Mirror-equivalent zones such as `Z2` and `Z8`, or `Z3` and `Z7`, should be
treated as equivalent in the exercise-definition recommendation logic. The exact
selected `Z` code should not be required while authoring an exercise because a
future recording may be captured from either mirror side. Concrete recording
metadata may still store an observed `Z` code when it is known; otherwise the
view family is sufficient for exercise definition.

`analysis_template` is an analysis-profile family, not an exercise-specific
template. It determines the default landmark set, biomechanical focus,
compensation patterns, feature domains, and quality-rule starting point for
the generated analysis profile. The current keys may still describe broad
families such as lower-body closed-chain, split-stance lower-body loading,
closed-chain upper-body press, or anti-rotation control. They should not encode
the concrete exercise name.

The notebook should recommend and order analysis templates from the earlier
authoring axes rather than ask the researcher to choose from fixed exercise
presets. Recommendation may use posture, body geometry, support template,
laterality, selected body regions, and selected joint actions. Recommended
analysis families are shown first, while non-recommended families remain
selectable with a warning. This keeps the authoring flow extensible: adding a
new exercise should usually mean reusing or adding an analysis family, not
adding another one-off exercise preset.

After the analysis family is selected, the generator may apply conservative
context inference from the same authoring axes. These inferred additions should
be narrow, explainable, and review-labeled. For example, a standing,
bilateral-feet, bilateral lower-body bend with sagittal primary motion and
frontal/transverse secondary planes may infer pelvis tilt/rotation proxy actions,
foot external-rotation compensation, joint-tracking error, and compensation
load-shift proxy availability. The generator must not infer these items from the
exercise name alone, and must not add them for exercises whose posture, support,
laterality, joint actions, or planes do not support the inference.

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
    selected view-family/H position, recommended and non-recommended positions,
    observation purpose, view-metric reliability
```

Interpretation rules and feature-meaning text remain separate display layers.
The loader supports both split YAML artifacts and legacy combined exercise YAML.

Authoring writes a `draft_bundle` to
`data/processed/authoring_drafts/<exercise_id>/` by default because generated
drafts are local review artifacts. Files that should be committed as examples
must be placed under:

```text
data/examples/exercise_authoring/<exercise_id>/
```

The example directory keeps the same nested split-YAML layout as the runtime
repository layout:

```text
data/examples/exercise_authoring/draft_squat/
    data/definitions/exercises/draft_squat.yaml
    data/definitions/analysis_profiles/draft_squat.yaml
    data/protocols/performance/draft_squat.yaml
    data/protocols/camera/draft_squat.yaml
```

This layout lets the existing loader use an authoring bundle without a new
bundle-specific API. To run the pipeline against an authoring bundle, set:

```yaml
exercise_definition:
  exercise_id: draft_squat
  definitions_dir: data/examples/exercise_authoring/draft_squat/data/definitions/exercises
```

From that `definitions_dir`, the loader resolves sibling split artifacts at
`data/definitions/analysis_profiles`, `data/protocols/performance`, and
`data/protocols/camera` inside the same bundle root. A draft bundle remains
review-labeled (`status: draft`, `requires_review`) and should not be treated as
canonical until researcher review promotes it into the main `data/definitions`
and `data/protocols` directories.

A `canonical_loader_view` does not write a second draft bundle. It reuses
the same draft files and asks the loader to expose them as the intended
canonical `exercise_id`. For example, a `draft_squat` bundle can be evaluated as
runtime `squat` without copying four YAML files:

```python
context = load_exercise_context(
    exercise_id="draft_squat",
    definitions_dir="data/processed/authoring_drafts/draft_squat/data/definitions/exercises",
    authoring_mode="canonical_view",
    canonical_exercise_id="squat",
    canonical_display_name="Bodyweight Squat",
)
```

The loader still records the draft source paths, but the returned
`ExerciseContext.exercise_id` and parsed `ExerciseDefinition.exercise_id` use the
canonical view id. Top-level draft metadata is moved into
`authoring_provenance` in the in-memory view. This is useful when demonstrating
the pipeline from the assumption that no canonical `squat` file existed
beforehand, while avoiding duplicated YAML artifacts. It is still not a reviewed
canonical install.

## 5. Review Boundary

Generated automatically:

```text
exercise identity and classification
support template
draft phase model
landmark set and draft angle triplets
rep/phase segmentation templates
performance count template
draft view-family/H camera recommendation
```

Requires researcher review:

```text
compensation patterns and implementation feasibility
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
  - compensation_patterns
  - view_metric_reliability
  - quality_rules
  - clinical_meaning
```

Canonical loader-view artifacts do not keep those three fields at the in-memory
artifact top level. They preserve the same review boundary as provenance:

```yaml
authoring_provenance:
  authoring_mode: canonical_view
  generated_by: exercise_authoring_notebook
  source_authoring_exercise_id: draft_squat
  canonical_exercise_id: squat
  requires_review:
    - compensation_patterns
    - view_metric_reliability
```

## 6. Notebook Target

Target notebook:

```text
notebook/10_manual_preparation/10_exercise_authoring_test.ipynb
```

Required cell flow:

```text
1. autoreload
2. registry loading
3. authoring spec input/selection (dropdown widgets when available; plain fallback)
4. exercise identity preview
5. analysis profile preview
6. performance protocol preview
7. camera protocol preview
8. review checklist
9. draft bundle write
10. canonical loader-view preview
```

Notebook cells must call `src/movement/definitions/exercise_authoring.py` rather
than reimplement YAML assembly.

## 7. Code Mapping

```text
src/movement/definitions/exercise_authoring.py
    ExerciseAuthoringSpec
    load_authoring_registries()
    derive_movement_pattern_from_authoring_axes()
    suggest_body_regions_from_joint_actions()
    recommend_phase_templates_for_authoring_axes()
    recommend_counting_templates_for_authoring_axes()
    recommend_camera_positions_for_authoring_axes()
    recommend_analysis_templates_for_authoring_axes()
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

data/camera/
    camera_zones.yaml
```

A future web UI should call the same spec and generator. It should not assemble
canonical YAML directly.
