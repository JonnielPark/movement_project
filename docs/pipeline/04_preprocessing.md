# 04. 전처리 (Preprocessing)

**문서 버전:** 1.2.0
**최종 갱신:** 2026-05-21
**영문 동기화:** `docs_eng/pipeline/04_preprocessing.md`는 동일 버전의 영문 번역본이다.

파이프라인 단계 ④는 정규화 전에 단안 pose data의 data-quality 문제를 보정하거나 표시한다.
입력 객체를 직접 수정하지 않고 보정된 DataFrame 사본을 반환한다.

이 단계는 관측 신뢰도만 다룬다. Depth, knee valgus, trunk lean, compensatory asymmetry 같은
movement-quality pattern을 바꾸면 안 된다.

---

## 1. 파이프라인 위치 (Pipeline Position)

```text
③ Exercise Definition → ④ Preprocessing ← 본 단계 → ⑤ Normalization → ⑥ Canonicalization
```

③ 이후에 실행되므로 laterality, landmarks, camera protocol, quality rules를 사용할 수 있다.
⑤ 이전에 실행되어 신뢰도 낮은 hip/shoulder landmark가 torso-length scale을 오염시키지 않게 한다.

---

## 2. 입력과 출력 (Inputs And Outputs)

필수 입력 칼럼:

```text
<landmark>_x / _y / _z
```

선택 입력:

```text
<landmark>_visibility
exercise_id, execution_pattern
camera_zone, camera_height_level
```

소비하는 exercise-definition field:

```text
classification.laterality
landmarks.primary_joints
landmarks.critical_landmarks
quality_rules.*
camera_protocol
view_metric_reliability
```

추가되는 칼럼:

```text
<landmark>_observed_reliable 원본 관측값의 repair 전 reliability
<landmark>_usable            short-gap repair 이후 다음 계산 사용 가능 여부
<landmark>_preprocessing_source
                              observed | short_gap_interpolated | unusable
preprocessing_valid          frame-level validity
preprocessing_note           machine-readable reason text
swap_corrected               해당 frame에서 L/R label 교환 여부
<landmark>_camera_side       near_side | far_side | unknown
<landmark>_jitter_score      선택 observation-jitter score
<landmark>_confidence_note   선택 landmark confidence note
preprocessing_confidence     frame-level confidence note
```

---

## 3. Reliability Checks

Landmark는 다음 이유로 unreliable로 표시될 수 있다.

```text
visibility gating
    visibility가 threshold보다 낮음.

segment-length consistency
    segment length가 sequence median에서 tolerance 이상 벗어남.
    Thigh segment는 valid squat 중에도 monocular depth 때문에 크게 변할 수 있으므로 제외될 수 있다.

conservative joint-angle bounds
    해부학적으로 불가능한 configuration만 표시한다.
    운동별 ROM 평가는 ⑨ Feature Extraction의 책임이다.

velocity outliers
    body-scale-normalized frame-to-frame jump가 threshold를 초과.
```

신뢰도 낮은 데이터는 삭제하지 않고 표시한다. Repair된 값은 다음 계산에 사용할 수
있게 될 수 있지만, preprocessing source를 통해 낮은 관측 confidence를 계속 남긴다.

---

## 4. 보정 (Corrections)

### L/R Swap Correction

활성 여부는 `classification.laterality`에 따른다.

```text
bilateral_symmetric  기본 skip
alternating          enabled
unilateral_*         enabled
generic fallback     skip
```

High-confidence swap candidate는 해당 frame의 paired landmark label을 교환한다. Coordinate value는
바꾸지 않는다. Low-confidence case는 표시만 하고 ⑨ Feature Extraction role-context 처리 또는 manual review로 남긴다.

### Short-Gap Interpolation

Interpolation은 reliability-masked short gap에만 적용한다.

```text
short gap   linear interpolation
long gap    unreliable 상태로 남기고 report에 기록
```

한계는 `quality_rules.max_interpolation_gap_frames`가 제어한다.

Interpolation은 `<landmark>_usable`을 갱신하지만
`<landmark>_observed_reliable`은 바꾸지 않는다. 이는 두 질문을 분리하기 위해서다.

```text
observed_reliable  원본 landmark 관측값을 믿을 수 있었는가?
usable             repair 이후 다음 단계 계산에 사용할 수 있는가?
```

활성화된 경우 post-interpolation velocity sanity check는 interpolation으로 회복된
landmark-frame만 다시 평가한다. 보간 좌표가 여전히 velocity threshold를 넘는 frame-to-frame
jump를 만들면 `post_interpolation_velocity_failed`로 표시하고 unusable로 되돌린다.

Short-gap interpolation된 landmark는 사용할 수는 있지만, 이후 feature/scoring 단계에서
낮은 confidence evidence로 처리해야 한다.

### Optional Smoothing

Smoothing은 기본 비활성화이며 작은 window를 사용해야 한다. 이는 작은 observation jitter를 줄이는
용도이지 실제 movement pattern을 바꾸는 용도가 아니다.

---

## 5. Far-Side Stabilization

선택 far-side stabilization은 측면 또는 측면에 가까운 view에서 카메라에서 먼 쪽의 visibility가
낮거나 jitter/swap risk가 높은 경우를 다룬다. 이는 canonicalization이 아니며 skeleton을
대칭으로 맞추지 않는다.

Monocular pose 좌표는 원래 noise가 크기 때문에 far-side jitter detection은 의도적으로 보수적으로
둔다. 작은 coordinate wobble은 jitter로 보지 않는다. Jitter gate는 큰 motion spike와 낮은
visibility 또는 기존 reliability-mask 실패 같은 low-confidence context가 함께 있을 때만
동작해야 한다.

Report는 원본 관측과 preprocessing 이후 상태를 분리한다.

```text
observed_*             interpolation/far-side repair 전 원본 관측
post_preprocessing_*   preprocessing repair 시도 이후에도 남은 문제
```

Observed-only issue는 provenance이다. 이후 feature availability gate에는
post-preprocessing issue가 더 강한 근거가 된다.

따라서 far-side summary는 `num_observed_low_confidence_far_side_landmark_frames`,
`num_observed_high_jitter_far_side_landmark_frames`,
`num_post_preprocessing_low_confidence_far_side_landmark_frames`,
`num_post_preprocessing_high_jitter_far_side_landmark_frames`처럼 원본/처리 후 count를
분리해서 노출해야 한다.

허용:

```text
near/far/unknown side context 추론
far-side low-confidence landmark에만 선택 smoothing/interpolation 적용
짧은 low-confidence gap 보간
해결되지 않은 long gap을 low confidence로 report
⑨와 ⑩을 위한 feature-availability hook 방출
```

금지:

```text
far-side landmark를 near-side landmark에 강제로 맞춤
실제 knee valgus, pelvic shift, trunk lean, asymmetry 제거
far-side unreliability를 poor movement-quality score로 직접 변환
```

Feature-availability hook 예:

```text
bilateral_landmark_coverage
near_far_side_context
far_side_jitter_score
left_right_swap_risk
segment_length_plausibility
view_reliability
```

---

## 6. 리포트 계약 (Report Contract)

`preprocess_pose_dataframe(df, landmarks, exercise_definition)`는 DataFrame과 report를 반환한다.

```python
{
    "method": str,
    "exercise_id": str | None,
    "movement_template_id": str | None,
    "execution_pattern": str | None,
    "laterality": str,
    "num_frames": int,
    "reliability_summary": dict,
    "landmark_quality_summary": list[dict],
    "rule_contribution_summary": dict,
    "worst_landmarks_by_observed_unreliable": list[dict],
    "worst_landmarks_by_unusable": list[dict],
    "frames_with_many_unusable_landmarks": list[dict],
    "swap_detection_summary": dict,
    "interpolation_summary": dict,
    "smoothing_summary": dict,
    "far_side_stabilization_summary": dict | None,
    "feature_availability_summary": dict | None,
    "num_invalid_frames": int,
    "applied_columns": list,
}
```

`exercise_id`와 `movement_template_id`는 로드된 exercise definition에서 가져온다.
`execution_pattern`은 첫 프레임 값이 아니라 DataFrame의 non-null 대표값을 사용한다. 실제
recording에는 운동 시작 전 setup frame이 포함될 수 있기 때문이다.

landmark/rule/frame summary는 QC provenance이지 movement-quality score가 아니다.
어떤 landmark, rule, frame 때문에 preprocessing confidence가 낮아졌는지 보여주어,
이후 feature 단계가 해당 feature를 사용할지, 낮은 신뢰도로 다룰지, 건너뛸지 판단하게 한다.

Stage-check notebook은 이 report에서 compact QC ratio와 readiness label을 만들 수 있다.
예: `ready_for_next_stage`, `ready_with_low_confidence_notes`, `review_recommended`.
이 label은 실행/QC 해석 보조일 뿐 biomarker score가 아니며, feature-level availability 결정을
대체하지 않는다.

Stage-check notebook은 이런 QC ratio 옆에 활성 preprocessing configuration도 표시할 수 있다.
예: visibility threshold, segment-length tolerance, joint angle check, velocity threshold,
interpolation gap, post-interpolation velocity check, smoothing 설정, far-side jitter gate.
이 configuration summary는 재현성을 위한 provenance이지 scoring input이 아니다.

Stage-check notebook은 앞 단계 노트북에서 쓰던 기존 양식을 따른다. 즉 `Data Setup`,
`Direct Preprocessing Test`, 번호가 붙은 check, `Pipeline Integration`, `Check Summary` 구조를
사용한다. Synthetic diagnostic은 뒤쪽의 별도 번호 check로 둘 수 있지만, target recording의
movement quality가 아니라 diagnostic evidence임을 명확히 표시해야 한다.

Frame은 조용히 삭제하지 않는다. Feature-level exclusion은 이후 ⑨ Feature Extraction과 ⑪ Biomarker
Scoring에서 결정한다.

---

## 7. 설정 (Configuration)

상세 기본값은 `configs/pipeline_default.yaml`에 둔다.

```yaml
preprocessing:
  enabled: false
  reliability: ...
  swap_detection: ...
  interpolation: ...
    post_velocity_check: true
  smoothing: ...
  far_side_stabilization: ...
```

Kalman filtering은 현재 preprocessing scope에서 활성화하지 않는다.

---

## 8. 향후 확장 (Planned Extensions)

- Availability resolution을 위한 per-feature landmark coverage summary.
- 실제 sample review 이후 reliability-weighted interpolation/smoothing.
- Test로 정당화되는 경우 per-exercise velocity threshold.
- ⑪에서 before/after quality visualization.
