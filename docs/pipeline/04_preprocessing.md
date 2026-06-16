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
exercise_type, pattern
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
<landmark>_reliable          landmark별 reliability mask
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

신뢰도 낮은 데이터는 삭제하지 않고 표시한다.

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
바꾸지 않는다. Low-confidence case는 표시만 하고 ⑧ Motion Attribution 또는 manual review로 남긴다.

### Short-Gap Interpolation

Interpolation은 reliability-masked short gap에만 적용한다.

```text
short gap   linear interpolation
long gap    unreliable 상태로 남기고 report에 기록
```

한계는 `quality_rules.max_interpolation_gap_frames`가 제어한다.

### Optional Smoothing

Smoothing은 기본 비활성화이며 작은 window를 사용해야 한다. 이는 작은 observation jitter를 줄이는
용도이지 실제 movement pattern을 바꾸는 용도가 아니다.

---

## 5. Far-Side Stabilization

선택 far-side stabilization은 측면 또는 측면에 가까운 view에서 카메라에서 먼 쪽의 visibility가
낮거나 jitter/swap risk가 높은 경우를 다룬다. 이는 canonicalization이 아니며 skeleton을
대칭으로 맞추지 않는다.

허용:

```text
near/far/unknown side context 추론
low-visibility + high-jitter landmark에만 더 강한 smoothing 적용
짧은 low-confidence gap 보간
해결되지 않은 long gap을 low confidence로 report
⑧과 ⑩을 위한 feature-availability hook 방출
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
    "exercise_type": str,
    "pattern": str,
    "laterality": str,
    "num_frames": int,
    "reliability_summary": dict,
    "swap_detection_summary": dict,
    "interpolation_summary": dict,
    "smoothing_summary": dict,
    "far_side_stabilization_summary": dict | None,
    "feature_availability_summary": dict | None,
    "num_invalid_frames": int,
    "applied_columns": list,
}
```

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
