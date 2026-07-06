# 운동 작성 노트북 (Exercise Authoring Notebook)

**문서 버전:** 0.2.25
**최종 갱신:** 2026-06-20
**영문 동기화:** [docs_eng/practical_protocols/exercise_authoring_notebook.md](../../docs_eng/practical_protocols/exercise_authoring_notebook.md)는 동일 내용의 영문 번역본이다.

본 문서는 새 운동 추가를 위한 임시 notebook-first workflow를 정의한다.
수행 지침이나 촬영 지침이 아니다. Notebook은 작은 `exercise_authoring_spec`을 만들고,
생성 YAML artifact를 preview한 뒤, canonical file 갱신 전에 연구자 검토용 draft를 작성한다.

---

## 1. 현재 결정 (Current Decision)

별도 web app보다 notebook UI를 먼저 사용한다.

```text
reason 1   현재 검증 흐름이 notebook 중심
reason 2   YAML preview와 연구자 검토를 한 화면에서 수행 가능
reason 3   운동 확장 전에 split-YAML schema를 검증 가능
reason 4   향후 web UI도 같은 spec과 generator를 재사용 가능
```

첫 버전에는 새 UI dependency가 필요하지 않다. Notebook은 widget이 있을 때 선택 가능한
드롭다운 기반 selection cell을 제공하되, widget UI 없이도 실행되도록 plain-variable fallback을
유지한다. 새 dependency 추가는 package 추가 전에 별도로 결정한다.

Authoring UI는 연구자에게 movement archetype을 직접 고르게 하지 않고, 원자적인 movement
descriptor를 먼저 수집해야 한다. Primary/secondary joint actions를 먼저 선택하고,
support pattern, laterality, posture, body geometry, primary body regions와 함께
해석한다. Export되는 `movement_template_id`는 이 joint-action-plus-context 조합에서
산출한다. Legacy `movement_pattern` key는 별도 registry migration을 계획하기 전까지 내부
호환 alias로 남을 수 있다.
이 제한은 선택 가능한 template label에 적용된다. `exercise_id`와 `display_name`은 작성 중인
구체적 운동 이름을 사용할 수 있다.

## 2. 작성 흐름 (Authoring Flow)

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
UI input은 작고 연구자 친화적이어야 함
동일 input은 동일 YAML을 생성
draft bundle은 data/processed/authoring_drafts/<exercise_id>/ 아래 작성
git에 올릴 예시는 data/examples/exercise_authoring/<exercise_id>/ 아래 보관
canonical YAML은 명시 승인 없이 덮어쓰지 않음
generated fields와 review-required fields를 분리
생성 text는 임상 진단, 임상 효과 주장, 절대 힘/토크 표현을 피함
```

Notebook은 세 가지 authoring mode를 구분한다:

| Mode | 목적 | File 정책 | Metadata 정책 |
|---|---|---|---|
| `draft_bundle` | Preview와 연구자 검토를 위한 local generated draft. | `data/processed/authoring_drafts/<exercise_id>/` | Top-level `status: draft`, `generated_by`, `requires_review`를 유지한다. |
| `canonical_loader_view` | 기존 hand-authored 운동 정의가 없었다고 가정하고 pipeline 실행을 시험할 수 있도록 draft bundle을 intended canonical exercise처럼 읽는 loader-time view. | Draft bundle을 재사용하며 duplicate candidate file은 작성하지 않는다. | Draft top-level metadata를 runtime `authoring_provenance`로 이동한다. |
| `canonical_install` | 향후 검토 완료 후 runtime `data/definitions/`와 `data/protocols/`로 승격. | Main runtime directories. | 명시적인 연구자 승인이 필요하며 notebook의 기본 동작이 아니다. |

현재 prototype은 `draft_bundle`과 `canonical_loader_view`를 구현한다.
`canonical_install`은 equivalence check와 review gate가 안정화될 때까지 수동 승격 단계로 둔다.

## 3. Authoring Spec

예시:

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

이 spec은 draft input이며 pipeline이 직접 소비하는 실행 기준 문서가 아니다.
현재 notebook UI에서 `movement_pattern: squat`은 직접 선택하지 않는다. Standing, bilateral,
two-foot support context 안에서 lower-body flexion/extension joint actions를 해석해 산출된다.
`movement_template_id`가 후속 분석에서 우선 쓰는 analysis-template identifier이고,
`movement_pattern`은 draft biomechanical default를 시작하기 위한 legacy registry family로 남긴다.

`posture_type`은 넓은 시작 신체 방향을 설명하고, `body_geometry`는 그 posture 안에서의
shape 정보를 추가한다. 예를 들어 floor-supported prone posture와 neutral body-line geometry는
plank 계열을, 같은 posture와 high-hip inverted-V geometry는 pike-like upper-body press 계열을
설명한다.

현재 posture 선택지는 넓은 custom option 뒤에 숨기지 않고 명시적으로 제공한다:

| Posture | 의미 | 대표 예시 |
|---|---|---|
| `standing` | 몸통이 세워져 있고 발 또는 한쪽 발이 주요 지지 기반이 되는 자세. | squat, lunge, hip hinge, step-up, balance reach |
| `floor_supported_prone` | 몸이 바닥을 향하고 손, 발, 전완, 무릎 등이 지지면과 연결되는 자세. 세부 shape는 `body_geometry`에서 보완한다. | plank, plank shoulder tap, mountain climber, pike push-up |
| `kneeling` | 한쪽 또는 양쪽 무릎이 주요 지지 접점이 되는 자세. | tall-kneeling reach, half-kneeling press, kneeling push-up |
| `seated` | 골반이 의자나 바닥에 지지되고, seated base에서 몸통/사지 움직임을 분석하는 자세. | seated march, seated trunk rotation, seated shoulder raise |
| `supine` | 얼굴과 몸통 앞면이 위를 향한 바로 누운 자세. | dead bug, glute bridge, supine heel slide, hollow hold |
| `side_lying` | 몸이 한쪽으로 누워 있거나 측면 지지 상태인 자세. | side plank, side-lying hip abduction, clamshell |
| `hanging` | 위쪽 지지물에 매달린 자세. | dead hang, pull-up, hanging knee raise |
| `external_object_supported` | 벤치, 벽, 의자, 바, 머신 등이 신체를 의미 있게 지지하는 자세. | wall squat, bench-supported row, chair sit-to-stand, incline push-up |

Notebook은 `posture_type`에 따라 `body_geometry` 선택지를 필터링한다:

| Posture | 허용 body geometry |
|---|---|
| `standing` | `neutral_upright`, `forward_lean_hinge` |
| `floor_supported_prone` | `neutral_prone_line`, `high_hip_inverted_v`, `quadruped` |
| `kneeling` | `neutral_upright`, `tall_kneeling_upright`, `half_kneeling_upright`, `quadruped` |
| `seated` | `neutral_upright`, `seated_flexed_trunk`, `long_sitting`, `cross_legged_sitting` |
| `supine` | `supine_hooklying`, `supine_tabletop`, `supine_straight_leg`, `supine_hollow` |
| `side_lying` | `side_supported`, `side_plank_line`, `side_lying_relaxed` |
| `hanging` | `neutral_upright`, `hanging_tuck`, `hanging_pike` |
| `external_object_supported` | `neutral_upright`, `neutral_prone_line`, `side_supported`, `supported_incline_line`, `machine_supported_fixed_trunk`, `custom` |

일부 body-geometry 선택지는 구현보다 먼저 등록해둔다. 이들은 authoring descriptor로는 선택할
수 있지만, 대응 registry template이 추가되기 전까지는 현재 movement-template family로 자동
매핑하지 않는다.

Dead bug 계열 운동은 `posture_type: supine`에서 시작하는 것으로 본다. 다만 supine core-control
registry family가 추가되기 전까지는 현재 movement-template family로 자동 매핑하지 않는다.

`laterality`는 의도한 움직임의 좌우 수행 방식을 설명한다. 예를 들어 양측 대칭, 양측 비대칭,
좌우 교대, 한쪽 수행을 구분한다. 대부분의 posture는 bilateral, alternating, unilateral 변형을
가질 수 있으므로 posture로 laterality를 강하게 필터링하지 않는다. 대신 laterality는 counting,
active-side attribution, side-sequence review, 생성 draft의 추가 검토 필요성에 영향을 준다.

`support_template`은 지지면과 실제로 하중을 주고받는 접촉 방식을 설명하므로 `posture_type`에
따라 필터링한다. 이렇게 해야 supine movement와 two-foot standing support처럼 물리적으로 맞지
않는 authoring 상태를 막을 수 있다. 일부 support template은 전체 analysis-template 구현보다
먼저 등록한다. 이들은 descriptor로는 유효하지만, 대응 movement-template 또는 analysis template이
추가되기 전까지는 draft YAML 생성 단계에서 추가 구현이 필요할 수 있다.

Notebook은 `posture_type`에 따라 `support_template` 선택지를 필터링한다:

| Posture | 허용 support template |
|---|---|
| `standing` | `bilateral_feet`, `split_stance`, `single_foot` |
| `floor_supported_prone` | `hands_and_feet`, `forearms_and_feet`, `hands_and_knees`, `hands_and_feet_with_trunk` |
| `kneeling` | `knees_floor`, `one_knee_one_foot`, `hands_and_knees` |
| `seated` | `seated_base` |
| `supine` | `supine_body_floor` |
| `side_lying` | `side_body_floor` |
| `hanging` | `overhead_hang` |
| `external_object_supported` | `external_object`, `bilateral_feet`, `split_stance`, `hands_and_feet` |

`primary_body_regions`는 별도의 movement 설명 축이 아니다. 선택된 primary/secondary joint
actions에서 분석 초점 부위 목록을 추천한 뒤, checkbox로 보여주는 항목이다. 연구자는 추천값을
그대로 쓰거나, 실제 분석 초점이 관절 동작 목록과 다를 때 수정할 수 있다. 이렇게 하면 UI에서
같은 정보를 두 번 묻지 않으면서도 reporting, visualization, 향후 feature grouping에 사용할
명시적인 region list를 유지할 수 있다.

`primary_plane`은 카메라 시야가 아니라 몸 기준의 주 해부학적 움직임 평면이다. UI에서는
`sagittal`, `frontal`, `transverse`, `static` 중 하나를 고르는 toggle button으로 보여준다.
`secondary_planes`는 추가로 관찰할 보상 또는 제어 평면이므로 선택된 primary anatomical plane은
secondary 목록에서 제외한다. `multiplanar`는 이 notebook에서 사용자가 직접 고르는 값이 아니라,
primary와 secondary anatomical plane의 unique plane이 2개 이상일 때 나중에 파생할 수 있는
상태로 둔다. `static`은 hold/control 운동을 위한 primary descriptor로 유지한다.

`phase_template`은 한 번의 반복을 어떻게 찾고, 그 반복 안을 어떤 phase로 나눌지를 설명한다.
운동 이름이 아니라 segmentation descriptor이다. 구현된 phase template은 일반 draft input으로
사용할 수 있다. planned template은 새 운동군을 설명하기 위해 구현 전에 registry에 미리 등록할
수 있지만, 선택 시 notebook에서 warning을 표시해야 한다. Planned template은 canonical pipeline
input이 되기 전에 segmentation review가 필요하다.

Phase template은 boundary detection에 사용할 coordinate family를 선언할 수 있다. 예를 들어
squat 계열 template은 descent/ascent detection에 recording-view raw `hip_center` `image_y`를
사용하면서도, 후속 feature와 scoring 단계는 여전히 normalized coordinate를 소비하게 할 수 있다.
Report contract는 `docs/pipeline/07_segmentation.md`를 따른다.

Notebook은 `phase_template`을 hard-filter하지 않고 앞선 authoring axis로 추천하고 정렬한다.
추천에는 `posture_type`, `body_geometry`, `support_template`, 선택된 joint actions,
`primary_plane`을 사용할 수 있다. 추천 template은 먼저 보여주고, 예외 운동 작성을 위해 다른
template도 선택 가능하게 유지한다. 강한 추천이 없으면 그 상태를 표시하고 전체 template을
사용 가능하게 둔다.

`counting_template`은 repeated repetition, same-side block, left-right pair처럼 count를 어떻게
해석할지 정의한다. 현재 recording unit은 single set이므로 basic authoring UI는
`target_count_per_set`을 주요 처방값으로 수집한다. `target_sets`와 `rest_between_sets_s`는
set-level recording의 필수 분석 입력이 아니라 optional protocol metadata이다. 생성되는 authoring
draft는 이 값들이 명시적으로 제공된 경우에만 포함해야 한다.

Notebook은 `counting_template`을 `laterality`와 `phase_template`에 따라 추천하고 정렬한다.
Bilateral 및 고정 side movement는 보통 `repeated_repetition`을 추천한다. Alternating movement는
pair 또는 side-sequence template을 추천한다. Static hold phase는 planned hold-seconds template을
추천한다. Phase template과 마찬가지로 edge case를 위해 추천되지 않은 counting template도 계속
선택 가능하지만, 현재 laterality/phase context와 맞지 않는 counting template을 선택하면 note 또는
warning을 표시해야 한다.

`camera_view_family`와 `camera_height_level`은 하나의 긴 H/Z dropdown이나 운동 이름별 camera
preset이 아니라 별도 control로 선택한다. `camera_view_family`는 `front_oblique`(`Z2`/`Z8`),
`side`(`Z3`/`Z7`), `rear_oblique`(`Z4`/`Z6`)처럼 좌우 mirror-equivalent인 수평 방향을 묶는다.
`H`는 camera height이다. Notebook은 연구자가 YAML을 먼저 열지 않아도 각 코드를 이해할 수
있도록 `data/camera/camera_zones.yaml`의 짧은 label을 각 control 옆에 보여줘야 한다.

Camera 추천도 phase/counting 추천과 같은 advisory 성격이다. Notebook은 앞선 authoring axis,
즉 posture, support, laterality, 선택된 joint actions, primary plane을 이용해 view-family/H 조합을
추천하고 정렬한다. 추천 조합은 먼저 보여주되, 추천되지 않은 조합도 계속 선택 가능해야 한다.
특이한 촬영 조건도 review나 향후 방법 비교에 쓸 수 있으므로 hard block이 아니라 warning으로
처리한다.

생성되는 camera draft YAML은 선택된 view-family/H 위치와 추천 문맥을 함께 보존해야 한다:

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

선택된 view-family/H 상태는 이후 feature availability와 view-metric reliability 점검을 위한
provenance이다.
이는 camera calibration 결과가 아니며 좌표를 보정하지 않는다.

`Z2`와 `Z8`, 또는 `Z3`와 `Z7`처럼 좌우가 대칭인 zone은 pose와 annotation context에서 좌우 역할을
추론할 수 있는 경우 운동 정의의 추천 로직에서 equivalent pair로 취급한다. 운동을 정의하는
단계에서는 향후 recording이 어느 mirror side에서 촬영될지 고정할 수 없으므로 구체 `Z` 코드를
필수로 요구하지 않는다. Concrete recording metadata는 관측된 `Z`를 알고 있을 때만 저장하고,
그렇지 않으면 view family만으로 충분하다.

`analysis_template`은 운동별 template이 아니라 analysis-profile family이다. 생성되는 analysis
profile의 기본 landmark set, biomechanical focus, compensation candidates, feature domains,
quality-rule 시작점을 정한다. 현재 key는 lower-body closed-chain, split-stance lower-body loading,
closed-chain upper-body press, anti-rotation control처럼 넓은 분석 family를 설명할 수는 있지만,
구체 운동 이름을 담아서는 안 된다.

Notebook은 `analysis_template`도 고정 운동 preset 목록에서 직접 고르게 하지 않고 앞선 authoring
axis로 추천하고 정렬해야 한다. 추천에는 posture, body geometry, support template, laterality,
선택된 body regions, 선택된 joint actions를 사용할 수 있다. 추천 analysis family는 먼저 보여주고,
추천되지 않은 family도 warning과 함께 선택 가능하게 둔다. 이렇게 해야 새 운동이 추가될 때
일회성 운동 preset을 계속 늘리는 대신 기존 analysis family를 재사용하거나 필요한 경우 새 family를
추가하는 구조로 확장할 수 있다.

Analysis family가 선택된 뒤 generator는 같은 authoring axis에서 보수적 context inference를 적용할 수
있다. 이 추론으로 추가되는 항목은 좁고 설명 가능해야 하며 review label을 유지해야 한다. 예를 들어
standing, bilateral-feet, bilateral lower-body bend이고 primary motion이 sagittal이며 보조 plane이
frontal/transverse이면 pelvis tilt/rotation proxy action, foot external-rotation compensation,
joint-tracking error, compensation load-shift proxy availability를 유추할 수 있다. Generator는 운동
이름만으로 이런 항목을 유추하면 안 되며, posture, support, laterality, joint action, plane 조건이
받쳐주지 않는 운동에는 추가하면 안 된다.

## 4. 생성 산출물 (Generated Artifacts)

하나의 spec은 네 artifact family를 생성한다:

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

Interpretation rules와 feature-meaning text는 별도 display layer로 유지한다.
Loader는 split YAML artifact와 legacy combined exercise YAML을 모두 지원한다.

Authoring notebook은 기본적으로 `draft_bundle`을
`data/processed/authoring_drafts/<exercise_id>/`에 작성한다. 이 위치는 local review
artifact용이다. Git에 포함할 예시는 다음 위치에 둔다:

```text
data/examples/exercise_authoring/<exercise_id>/
```

Example directory는 runtime repository layout과 같은 nested split-YAML 구조를 유지한다:

```text
data/examples/exercise_authoring/draft_squat/
    data/definitions/exercises/draft_squat.yaml
    data/definitions/analysis_profiles/draft_squat.yaml
    data/protocols/performance/draft_squat.yaml
    data/protocols/camera/draft_squat.yaml
```

이 구조를 유지하면 별도 bundle 전용 API 없이도 기존 loader가 authoring bundle을 사용할 수
있다. Pipeline에서 authoring bundle을 실행하려면 다음처럼 설정한다:

```yaml
exercise_definition:
  exercise_id: draft_squat
  definitions_dir: data/examples/exercise_authoring/draft_squat/data/definitions/exercises
```

이 `definitions_dir`를 기준으로 loader는 같은 bundle root 안의
`data/definitions/analysis_profiles`, `data/protocols/performance`,
`data/protocols/camera`에 있는 sibling split artifact를 찾는다. Draft bundle은
`status: draft`, `requires_review` metadata를 유지하므로, 연구자 검토를 거쳐 main
`data/definitions`와 `data/protocols`로 승격하기 전까지 canonical definition으로 취급하지 않는다.

`canonical_loader_view`는 두 번째 candidate bundle을 작성하지 않는다. 같은 draft file을
재사용하고, loader에게 intended canonical `exercise_id`로 노출하라고 요청한다. 예를 들어
`draft_squat` bundle은 네 개 YAML file을 복사하지 않고 runtime `squat`처럼 평가할 수 있다:

```python
context = load_exercise_context(
    exercise_id="draft_squat",
    definitions_dir="data/processed/authoring_drafts/draft_squat/data/definitions/exercises",
    authoring_mode="canonical_view",
    canonical_exercise_id="squat",
    canonical_display_name="Bodyweight Squat",
)
```

Loader는 draft source path를 그대로 기록하지만, 반환되는 `ExerciseContext.exercise_id`와 parsed
`ExerciseDefinition.exercise_id`는 canonical view id를 사용한다. Top-level draft metadata는
in-memory view의 `authoring_provenance`로 이동한다. 이 방식은 기존 canonical `squat` file이
없었다고 가정하고 pipeline을 보여주되, 중복 YAML artifact를 만들지 않기 위한 것이다. 단, 이는
아직 검토 완료된 canonical install이 아니다.

## 5. 검토 경계 (Review Boundary)

자동 생성 가능:

```text
exercise identity and classification
support template
draft phase model
landmark set and draft angle triplets
rep/phase segmentation templates
performance count template
draft view-family/H camera recommendation
```

연구자 검토 필요:

```text
compensation candidates and implementation feasibility
view-metric reliability
quality thresholds and scoring eligibility
clinical meaning text
exercise-specific exception rules
naming and stage consistency with existing exercises
```

Draft artifact는 다음 metadata를 포함한다:

```yaml
status: draft
generated_by: exercise_authoring_notebook
requires_review:
  - compensation_candidates
  - view_metric_reliability
  - quality_rules
  - clinical_meaning
```

Canonical loader-view artifact는 이 세 field를 in-memory artifact top level에 유지하지
않는다. 같은 review boundary를 provenance로 보존한다:

```yaml
authoring_provenance:
  authoring_mode: canonical_view
  generated_by: exercise_authoring_notebook
  source_authoring_exercise_id: draft_squat
  canonical_exercise_id: squat
  requires_review:
    - compensation_candidates
    - view_metric_reliability
```

## 6. Notebook 목표 (Notebook Target)

Target notebook:

```text
notebook/10_manual_preparation/10_exercise_authoring_test.ipynb
```

Required cell flow:

```text
1. autoreload
2. registry loading
3. authoring spec input/selection (widget이 있으면 dropdown, 없으면 plain fallback)
4. exercise identity preview
5. analysis profile preview
6. performance protocol preview
7. camera protocol preview
8. review checklist
9. draft bundle write
10. canonical loader-view preview
```

Notebook cell은 YAML assembly를 다시 구현하지 말고
`src/movement/definitions/exercise_authoring.py`를 호출해야 한다.

## 7. 코드 매핑 (Code Mapping)

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

향후 web UI는 같은 spec과 generator를 호출해야 한다. canonical YAML을 직접 조립하지 않는다.
