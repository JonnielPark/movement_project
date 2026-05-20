# 04. 전처리 (Preprocessing)

**문서 버전:** 1.1.2
**최종 갱신:** 2026-05-21
**영문 동기화:** `docs_eng/pipeline/04_preprocessing.md`는 동일 버전의 영문 번역본이다.

파이프라인 단계 ④. 정규화 이전에 단안 포즈 데이터의 품질 이슈를 보정한다.
보정된 데이터프레임 사본을 반환하며, 입력은 수정하지 않는다.

데이터 품질 이슈만 보정하며, 동작 품질 패턴(보상 움직임, 스쿼트 깊이 등)은 변경하지 않는다.

현재 구현은 reliability mask, 라벨만 교환하는 L/R swap 보정, 짧은 gap 보간, 선택적 smoothing,
그리고 측면 또는 측면에 가까운 촬영을 위한 선택적 visibility-aware far-side stabilization과
feature-availability hook을 포함한다.

---

## 1. 파이프라인 위치 (Pipeline Position)

```text
Pose CSV
→ ① Validation
→ ② Annotation
→ ③ Exercise Definition
→ ④ Preprocessing          ← 본 단계
→ ⑤ Normalization
→ ⑥ Segmentation
→ ⑦ Motion Attribution
→ ⑧ Feature Extraction
```

③ 이후에 실행되어, 운동별 점검 활성화에 필요한 `exercise_type`, `pattern`, 운동 정의 필드
(`laterality`, `quality_rules`)를 사용할 수 있도록 한다.

⑤ 정규화 이전에 실행된다. 척도 기준(몸통 길이 중앙값)은 엉덩이/어깨 랜드마크가
신뢰도 게이팅을 통과한 후 더 안정적이기 때문이다.

## 2. 설계 원칙 (Design Principle)

```text
허용:
    가시성(visibility) 기반 신뢰도 표시
    해부학적 제약 점검
    좌·우 라벨 스왑(swap) 보정 (라벨 교환만; 좌표는 변경하지 않음)
    신뢰도 마스크가 표시된 짧은 갭의 보간(interpolation)
    프레임 단위 작은 떨림에 대한 선택적 평활화(smoothing)
    전처리 리포트 출력

불허:
    비정상 동작 패턴을 정상처럼 보이도록 수정
    부족한 스쿼트 깊이 보정
    무릎 외반(knee valgus) 패턴 보정
    프레임을 조용히 삭제
    원본 프레임 번호 변경
    특정 기구학(kinematic) 모델에 맞추기 위한 좌표 조정
```

## 3. 입력 (Inputs)

필수:
```text
<landmark>_x / _y / _z     좌표 칼럼
```

선택 (있을 경우 사용):
```text
<landmark>_visibility      신뢰도 게이팅
exercise_type              운동별 로직 활성화
pattern                    좌·우 스왑 검출 범위
```

운동 정의에서 참조하는 필드:
```text
landmarks.primary_joints
landmarks.critical_landmarks
classification.laterality
quality_rules.minimum_visible_landmark_ratio
quality_rules.max_interpolation_gap_frames
camera_protocol.recommended_zones
view_metric_reliability
```

## 4. 출력 (Outputs)

```python
pre_df, pre_report = preprocess_pose_dataframe(df, landmarks, exercise_definition)
```

추가되는 출력 칼럼 (원본을 대체하지 않음):

```text
<landmark>_reliable    bool    랜드마크별·프레임별 신뢰도 마스크
preprocessing_valid    bool    프레임 단위 종합 신뢰도
preprocessing_note     str     비신뢰 사유
swap_corrected         bool    좌·우 라벨 스왑 보정 여부
```

Task B 리포트/메타데이터 출력(정책상 안정화된 경우를 제외하고 좌표를 대체하지 않음):

```text
<landmark>_camera_side       near_side | far_side | unknown
<landmark>_jitter_score      정규화된 landmark jitter score
<landmark>_confidence_note   landmark-level observation confidence note
preprocessing_confidence     후속 단계용 frame-level confidence note
feature_availability_summary feature scoring 가능 여부를 담는 report-level context
```

## 5. 신뢰도 검출 (Reliability Detection)

특정 프레임의 랜드마크가 다음 중 하나에 해당하면 `unreliable`로 표시된다:

### 5-1. 가시성 게이팅 (Visibility Gating)

```text
landmark.visibility < visibility_threshold (기본값: 0.5)
```

낮은 가시성 랜드마크는 표시만 되며 삭제되지 않는다.

### 5-2. 분절 길이 일관성 (Segment Length Consistency)

프레임별 분절 길이를 시퀀스 중앙값과 비교한다.

```text
deviation = |segment_length(t) - median_segment_length| / median_segment_length

if deviation > segment_length_tolerance (기본값: 0.25):
    프레임 t에서 분절 양 끝점 랜드마크를 unreliable로 표시
```

**예외**: 엉덩이-무릎(허벅지) 분절은 본 점검에서 제외된다.
단안 데이터에서는 깊이 원근(depth perspective)의 영향으로 스쿼트 시 허벅지가 40 % 이상
짧아지거나 길어 보일 수 있어, 정상 동작에서 거짓 양성(false positive)을 유발한다.

### 5-3. 관절각 생리학적 한계 (Joint Angle Physiological Bounds)

(근위, 정점, 원위) 랜드마크 트리플렛에서 계산된 끼인각(included angle)을 보수적인
해부학적 한계와 비교한다:

```text
관절          허용 끼인각 (도)
─────────────────────────────────────────────
knee           10 – 180
elbow          10 – 180
hip            20 – 180
```

점검 대상 관절: `left_knee`, `right_knee`, `left_elbow`, `right_elbow`,
`left_hip`, `right_hip`.

이 점검은 해부학적으로 불가능한 구성만 표시한다(보수적 임계값).
운동별 ROM 점검은 ⑧ 피처 추출의 책임이다.

### 5-4. 속도 이상값 (Velocity Outliers)

```text
v(t) = |p(t) - p(t-1)| / Δt

if v(t) > velocity_threshold:
    프레임 t에서 랜드마크를 unreliable로 표시
```

임계값은 torso-length-per-second 단위로 정의된다(신체 크기 불변).
`configs/pipeline_default.yaml`에서 설정:
```yaml
preprocessing:
  reliability:
    velocity_threshold_torso_per_sec: 5.0
```

## 6. 좌·우 스왑 검출 (L/R Swap Detection)

포즈 추정기는 가끔 좌·우 랜드마크 라벨을 뒤집는다(특히 가려짐, 회전, 엎드린 자세에서).
활성화는 `classification.laterality`에 따른다:

```text
bilateral_symmetric  → 스왑 검출 건너뜀
alternating          → 프레임별 스왑 검출 활성
unilateral_*         → 활성, 단측 우선
generic 폴백          → 건너뜀(안전 기본값)
```

### 검출 휴리스틱 (둘 모두 함께 사용)

시간 일관성:
```text
프레임 t에서 스왑 표시 조건:
    |p_L(t) - p_R(t-1)| < |p_L(t) - p_L(t-1)|
    AND
    |p_R(t) - p_L(t-1)| < |p_R(t) - p_R(t-1)|
```

운동 방향 사전(prior) (해당되는 경우):
```text
정면 운동에서:
    (left_hip.x - right_hip.x)의 기대 부호는 카메라 규약에 의해 고정.
    관찰 부호가 반복 프레임의 > orientation_disagree_ratio 비율에서 불일치하면,
    해당 반복을 시퀀스 단위 스왑 후보로 표시.
```

### 보정 정책 (Correction Policy)

높은 신뢰도 스왑 → 해당 프레임의 짝 랜드마크 라벨을 교환.
라벨만 교환되며, 좌표 값은 변경되지 않는다.
`swap_corrected = True`, 사유는 `preprocessing_note`에 기록.

낮은 신뢰도 → 표시만 하며 수정하지 않는다.
반복 단위 일관성은 ⑦ 모션 어트리뷰션에서 점검한다.

## 7. 짧은 갭 보간 (Short-Gap Interpolation)

신뢰도 마스크가 표시된 갭에만 적용된다(원시 결측값에는 적용되지 않음).

```text
max_interpolation_gap_frames  : quality_rules에서 참조 (기본값: 3)
방법                          : 선형 보간(linear)
```

```text
짧은 마스크 갭  → 선형 보간
긴 마스크 갭    → unreliable로 유지; 리포트에 미해결로 기록
```

## 8. 평활화 (Smoothing, 선택)

신뢰 가능한 랜드마크의 작은 프레임 단위 떨림을 줄인다.

```text
방법: rolling_median (권장), moving_average, none
기본값: smoothing.enabled = false
```

`rolling_median`이 잔여 이상값에 강건하므로 `moving_average`보다 권장된다.
윈도우 크기는 의미 있는 동작 동역학(보상 움직임 등)을 보존할 수 있을 만큼 작아야 한다.

설정:
```yaml
preprocessing:
  smoothing:
    enabled: false
    method: rolling_median
    window_size: 3
```

## 9. Task B 확장: Visibility-Aware Far-Side Stabilization

이 선택 구현은 촬영 view가 측면 또는 측면에 가깝고, 카메라에서 먼 쪽 landmark가 낮은
visibility, 높은 jitter, 높은 L/R swap 위험을 보이는 상황을 다룬다. 이는 canonicalization이
아니며, skeleton을 대칭으로 맞추려는 절차도 아니다.

### 9-1. Near-Side / Far-Side 추정

전처리 단계는 landmark 또는 body side 단위의 camera-side context를 추정한다.

```text
near_side    관찰 pose에서 카메라에 더 가까운 landmark/body side
far_side     관찰 pose에서 카메라에서 더 먼 landmark/body side
unknown      근거 부족; side-specific stabilization을 적용하지 않음
```

추정에는 다음 정보를 사용할 수 있다.

```text
annotation 또는 recording metadata의 camera_zone
hip_center 또는 body center 대비 좌/우 depth 좌표
paired landmark 사이의 visibility 차이
side assignment의 시간적 연속성
가능한 경우 exercise laterality와 active/support role
```

camera-side 추정이 불안정하면 결과는 `unknown`으로 남긴다. unknown은 confidence state이지,
movement-quality penalty가 아니다.

### 9-2. Far-Side Jitter Score

Jitter score는 reliability metric이지 생체역학 점수가 아니다. 특정 landmark가 불안정한
단안 추정값일 가능성을 요약한다.

```text
velocity_spike_ratio
acceleration_spike_ratio
visibility_drop_ratio
segment_length_inconsistency
left_right_swap_risk
```

가능하면 body scale로 정규화한다. 이 값은 landmark별 또는 paired side별로 보고하고,
후속 feature-availability gate에서 사용한다.

### 9-3. 안정화 정책

Far-side stabilization은 보수적으로 적용한다.

```text
허용:
    낮은 visibility + 높은 jitter landmark에 한한 강화 smoothing
    짧은 low-confidence gap 보간
    해결되지 않은 긴 gap에 대한 confidence/report metadata

불허:
    far-side landmark를 near-side landmark에 강제로 맞추기
    실제 knee valgus, pelvic shift, trunk lean, asymmetry 제거
    far-side 불안정성을 곧바로 나쁜 movement-quality score로 변환
```

분절 길이 plausibility는 guardrail로 사용할 수 있지만, 고정 template을 강제해서는 안 된다.
긴 gap 또는 불안정한 side assignment는 `low_confidence` 또는 `not_assessed`로 남긴다.

### 9-4. Feature-Availability Hook

④ 전처리는 후속 단계가 feature의 scoring 투입 가능 여부를 판단할 수 있도록 다음 context를 제공해야 한다.

```text
bilateral_landmark_coverage
near_far_side_context
far_side_jitter_score
left_right_swap_risk
segment_length_plausibility
운동 정의의 view_reliability
```

`spatial.symmetry.*`는 양측 landmark coverage, 분절 길이 plausibility, 낮은 swap risk,
허용 가능한 far-side jitter, 좌우 해석을 뒷받침하는 camera view를 모두 만족할 때만
`assessed`가 된다. 그렇지 않으면 `low_confidence` 또는 `not_assessed`가 될 수 있다.

설정 블록:

```yaml
preprocessing:
  far_side_stabilization:
    enabled: false
    camera_side_inference: true
    visibility_threshold: 0.6
    jitter_threshold_torso_per_sec: null
    acceleration_threshold_torso_per_sec2: null
    max_gap_frames: 3
    smoothing_method: rolling_median
    smoothing_window_size: 3
    mark_long_gaps_low_confidence: true
    depth_axis: z
    near_depth_sign: negative
    min_depth_offset_torso: 0.05
```

리포트 필드:

```python
{
    "far_side_stabilization_summary": {
        "enabled": bool,
        "camera_side_inference": dict,
        "num_near_side_landmark_frames": int,
        "num_far_side_landmark_frames": int,
        "num_unknown_side_landmark_frames": int,
        "num_high_jitter_far_side_landmark_frames": int,
        "num_far_side_gaps_interpolated": int,
        "num_far_side_gaps_unresolved": int,
        "num_far_side_values_smoothed": int,
    },
    "feature_availability_summary": {
        "symmetry_gate_ready": bool,
        "low_confidence_feature_families": list,
        "not_assessed_feature_families": list,
        "reasons": dict,
    },
}
```

## 10. Laterality 분기 요약 (Laterality Branch Summary)

```text
laterality               visibility  segment  ROM  velocity  L/R swap  far-side  smoothing
──────────────────────   ──────────  ───────  ───  ────────  ────────  ────────  ─────────
bilateral_symmetric      enabled     enabled  on   enabled   skip      view-gated optional
alternating              enabled     enabled  on   enabled   enabled   role-aware optional
unilateral_*             enabled     enabled  on   enabled   enabled   role-aware optional
generic 폴백              enabled     enabled  on   enabled   skip      skip      optional
```

## 11. 무효 프레임 표시 (Invalid Frame Marking)

프레임은 절대 조용히 삭제되지 않는다. 품질 메타데이터 칼럼이 추가된다:

```text
preprocessing_valid = True    본 단계 이후 사용 가능한 프레임
preprocessing_valid = False   미해결 품질 이슈가 남아 있음
swap_corrected = True         좌·우 라벨이 교환됨
```

피처 추출 단계에서의 정확한 프레임 제외는 어노테이션 규칙과 피처 단계 로직이 결정한다.

## 12. 전처리 리포트 (Preprocessing Report)

```python
{
    "method": str,
    "exercise_type": str,
    "pattern": str,
    "laterality": str,
    "num_frames": int,
    "num_coordinate_columns": int,
    "reliability_summary": {
        "visibility_threshold": float,
        "num_low_visibility_frames_per_landmark": dict,
        "num_segment_length_violations": int,
        "num_joint_angle_violations": int,
        "num_velocity_outliers": int,
        "num_unreliable_landmark_frames": int,
    },
    "swap_detection_summary": {
        "enabled": bool,
        "num_temporal_swap_corrected": int,
        "num_orientation_disagree_reps": int,
    },
    "interpolation_summary": {
        "enabled": bool,
        "max_interpolation_gap": int,
        "num_short_gaps_interpolated": int,
        "num_long_gaps_unresolved": int,
    },
    "smoothing_summary": {
        "enabled": bool,
        "method": str,
        "window_size": int,
        "applied_columns": list,
    },
    "far_side_stabilization_summary": dict | None,
    "feature_availability_summary": dict | None,
    "num_invalid_frames": int,
    "applied_columns": list,
}
```

## 13. 향후 확장 (Planned Extensions)

- 가시성 가중 보간(visibility-weighted interpolation)
- 신뢰도 가중 평활화
- Hampel 필터 (이상값 강건 평활화)
- One-Euro 필터 (저지연 jitter 인지 평활화)
- 운동별 속도 임계값 튜닝
- Task B far-side 정책을 넘어서는 landmark별 reliability rule
- 보정 전·후 시각화
