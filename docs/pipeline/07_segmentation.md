# 07. 세그멘테이션 (Segmentation)

**문서 버전:** 1.3.4
**최종 갱신:** 2026-07-04
**영문 동기화:** `docs_eng/pipeline/07_segmentation.md`는 동일 버전의 영문 번역본이다.

파이프라인 단계 ⑦은 반복 경계와 반복 내부 phase label을 확정한다. Rep와 phase를 모두 다루므로
단계명은 `Segmentation`이다. 기존 `phase_segmentation` YAML/code key는 phase splitting 전용으로
유지하고, `rep_segmentation`이 반복 경계를 담당한다.

이 단계는 좌표를 수정하거나 frame을 삭제하지 않는다.

---

## 1. 파이프라인 위치 (Pipeline Position)

```text
⑤ Normalization → ⑥ Canonicalization → ⑦ Segmentation ← 본 단계 → ⑧ Feature Extraction
```

입력:

```text
normalized dataframe       ⑤ 산출물
annotation metadata        set_id, rep_id, phase, use_for_analysis가 있으면 사용
exercise definition        rep_segmentation과 phase_segmentation 설정
```

출력:

```text
rep_id
rep_segmentation_status        not_run | success | failed | manual_override | skipped
rep_segmentation_source        annotation | semi_auto | manual_override | fallback
rep_segmentation_failure_id
phase
phase_segmentation_status      not_run | success | failed | manual_override | skipped
phase_segmentation_source      annotation | semi_auto | manual_override | fallback
phase_segmentation_failure_id
```

② Annotation에서 온 manual label은 후보 또는 확정 label로 취급하며 조용히 덮어쓰지 않는다.

Stage-check notebook 26은 공통 stage-check pattern을 따른다:

```text
Data Setup
    prepare_previous_stage_inputs(prepare_until="normalization")로 validation,
    annotation, exercise definition, preprocessing, normalization 산출물을 준비한다.

Direct Segmentation Test
    rep label handoff를 짧게 확인한 뒤, 준비된 normalized dataframe에 phase
    segmentation 함수를 직접 호출한다.

Pipeline Integration
    run_pipeline으로 같은 stage를 실행하고 report 존재 여부와 frame-level label을 비교한다.
```

Stage-check notebook은 annotation rep range를 자세히 재검증하지 않고,
recording-specific phase-split guide를 ground truth로 승격하지 않는다. Annotation의 rep label이
handoff evidence로 보존되는지와 현재 exercise definition이 usable phase label과 provenance를
만들 수 있는지만 확인한다.

Canonicalization은 전체 파이프라인의 선행 단계로 유지되지만, 현재 segmentation boundary detection은
canonical candidate coordinate를 필요로 하지 않는다. Normalized/preprocessed dataframe과
exercise-defined reference signal을 입력으로 사용한다.

---

## 2. 전략 (Strategy)

```text
rep_segmentation
    반복 시작/종료 경계를 추정하고 rep_id를 확정한다.

phase_segmentation
    확정된 반복 내부의 phase boundary를 추정하고 phase label을 채운다.
```

두 block은 exercise-defined reference landmark, coordinate family, axis, expected phase order,
minimum-length 설정을 사용한다. Visibility, ROM, boundary candidate 수, boundary order,
manual-label consistency가 불명확하면 automatic segmentation은 거부한다.

`reference_coordinate_family`는 boundary detection에 쓰는 신호와 feature/scoring 계산에 쓰는
좌표를 분리한다:

```text
norm
    기본값. ⑤ Normalization의 <landmark>_norm_x/y/z를 읽는다.

recording_view_raw
    <landmark>_x/y/z 같은 raw recording-plane column을 읽는다. Reference landmark가
    normalization anchor라서 normalized trajectory가 제거되는 경우에 유용하다.
```

예를 들어 squat phase splitting은 `recording_view_raw`의 `hip_center`와 `image_y`를 사용해
눈에 보이는 recording-plane hip trajectory를 따라 descent/ascent를 나눌 수 있다. 이는
normalized coordinate를 바꾸거나 raw coordinate를 scoring feature로 승격하는 것이 아니다.

### 2.1 Phase Label Vocabulary

Phase label은 exercise-defined kinematic/task label이다. `Descent`와 `Ascent` 한 쌍으로
하드코딩하지 않는다. Exercise definition은 registry template 또는 authoring bundle에서
`phase_sequence`를 선택하고, segmentation은 reference signal이 이를 뒷받침할 때 해당 순서를
채운다.

대표 label group:

```text
vertical/resistance cycle
    Start_Hold, Descent, Turnaround_Hold, Ascent, Top_Hold, Reset

flexion-extension cycle
    Flexion, Flexion_Hold, Extension, Extension_Hold, Return

push/pull cycle
    Lowering, Bottom_Hold, Press, Pull, Top_Hold, Lockout, Return

reach/return cycle
    Reach, Reach_Hold, Return, Recenter

support/alternating cycle
    Support, Weight_Shift, Unweight, Lift, Tap, Replant, Return

directional reach/step cycle
    Step_Out, Step_In, Forward_Reach, Backward_Return, Lateral_Reach,
    Medial_Return

rotation/control cycle
    Rotate_Left, Rotate_Right, Rotate, Rotation_Hold, AntiRotation_Hold, Return

static/control cycle
    Hold, Drift, Correction, Failure_Point
```

사람이 읽는 phase label은 `phase` column에 그대로 보존한다. Phase-specific suffix가 필요한
feature ID에서는 같은 label을 lower snake case로 바꿔 사용한다. 예:
`Turnaround_Hold` → `turnaround_hold`.

`eccentric`, `isometric`, `concentric` 같은 kinetic term은 `phase_model`의 기대 비율이나 해석
note에는 등장할 수 있지만, exercise definition이 명시적으로 task label로 승격하지 않는 한
primary phase label로 쓰지 않는다. 단일 카메라 pose만으로 force나 muscle-action ground truth를
암시하지 않기 위해서다.

`Turnaround_Hold`, `Top_Hold`, `Reach_Hold` 같은 optional label은 해당 option이 켜져 있고
accepted 된 경우에만 출력한다. Optional phase가 불명확하면 coarse phase sequence로 계속
진행하고 `optional_phase` failure point를 기록한다.

현재 구현 상태:

```text
implemented
    Segmentation은 구현된 template에 대해 exercise-defined phase_sequence를 읽을 수 있고,
    phase-level feature record는 관측된 phase label을 보존한다.

limited
    현재 rep-level spatial.phase_profile aggregate는 아직 Descent/Ascent ROM ratio에 특화되어
    있다. Generic phase-profile aggregate는 scoring에 쓰기 전에 명시적으로 설계해야 한다.
```

---

## 3. 상태와 실패 정책 (Status And Failure Policy)

```text
success
    accepted interval이 minimum_reps와 minimum_rep_length_frames를 만족한다.

failed
    필요한 landmark/axis가 없거나, candidate boundary가 없거나, interval이 너무 짧거나,
    candidate order가 잘못됐거나, accepted interval이 minimum_reps보다 적다.

skipped
    필요한 segmentation config가 없거나 stage가 비활성화됐다.

manual_override
    연구자 확인 label이 failure를 해결하거나 automatic candidate를 대체한다.
```

Failure level:

```text
rep_boundary
    반복을 확정할 수 없다. 수동 해결 전까지 해당 구간은 rep-level 및 phase-level output에서 제외.

phase_boundary
    반복은 확정됐지만 phase boundary가 불명확하다. Rep-level metric은 유지하고
    해당 반복의 phase-level record는 withheld한다.

optional_phase
    Turnaround_Hold 같은 선택 phase가 불명확하다. Coarse phase로 계속 진행하고 skipped optional
    phase를 기록한다.
```

---

## 4. Failure Point 계약

```text
failure_id
failure_level          rep_boundary | phase_boundary | optional_phase
set_id, rep_id
start_frame, end_frame
candidate_frame
reason                 low_visibility | insufficient_rom | missing_candidate |
                       multiple_candidates | order_mismatch | manual_required
confidence
pipeline_action        exclude_range | rep_level_only | coarse_phase_continue |
                       wait_for_manual_override
resolved
resolution_note
```

Failure point는 provenance이며, 보간해서 success로 만들지 않는다.

---

## 5. Manual Intervention

Manual intervention은 failure point의 label을 확정하며 coordinate value는 바꾸지 않는다.

```text
rep_segmentation_status / phase_segmentation_status = manual_override
rep_segmentation_source / phase_segmentation_source = manual_override
```

후속 단계는 확정 label만 사용하고 correction reason과 reviewer note를 보존한다.

---

## 6. Recording-Plane Phase Split Artifact

실제 one-take MediaPipe recording에서는 confirmed annotation으로 승격하기 전에 annotation 파일
옆에 recording-plane phase split을 만들 수 있다. MediaPipe `z`가 height가 아니라 depth proxy일
때 raw image/recording-plane signal이 visual QC에 더 안전할 수 있기 때문이다.

승격 전의 `<recording_id>_phase_split.csv`는 해당 recording을 점검하기 위한 가이드일 뿐이다.
이를 ground-truth phase annotation이나 scoring 입력으로 취급하지 않는다.

```text
source annotation    <recording_id>_annotation.csv
candidate output     <recording_id>_phase_split.csv
confirmed output     <recording_id>_phase_annotation.csv
reference signal     raw image/recording coordinates의 hip_center_y
```

Stable helper:

```text
generate_recording_plane_phase_split
validate_phase_split_for_promotion
promote_phase_split_to_annotation
```

Promotion에는 정확한 rep coverage, phase gap/overlap 없음, 올바른 phase order, filming provenance
보존, visual QC가 필요하다. 추가 real sample과 robustness 근거가 생기기 전까지 이는 generic
pipeline default가 아니라 annotation-adjacent QC workflow로 유지한다.

---

## 7. 후속 단계 규칙 (Downstream Rules)

```text
⑧ Feature Extraction   확정된 rep_id를 사용하고 side-role context를 해석하며,
                       confirmed rep에는 rep-level feature를, successful/manual phase에는
                       phase-level feature를 방출.
⑨ Biomech Proxy        unresolved rep-boundary failure는 제외.
⑩ Biomarker Scoring    failure/exclusion provenance를 보존.
⑪ Visualization        failure point와 manual boundary를 표시.
```

---

## 8. 검증 대상 (Verification Targets)

```text
tests/test_phase_segmentation.py
    nominal phase split, rejected short reps, multi-inflection policy, annotation
    override behavior.

tests/test_features_phase_grouping.py
    phase-level FeatureRecord provenance.

tests/test_recording_phase_split.py
    recording-plane artifact generation and promotion validation.
```
