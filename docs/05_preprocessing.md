# 05. 전처리 (Preprocessing)

본 단계는 **단일 비전 포즈 추정 결과의 데이터 품질 문제**(낮은 가시도, 분절 길이 비일관성, 비정상 관절각, 속도 이상치, 좌우 라벨 스왑)를 해결한다. 정규화·특징 추출 전에 안정적인 포즈 시퀀스를 준비하면서, **원본 동작 패턴은 보존**한다.

> 용어는 [`_terminology.md`](_terminology.md)의 단일 정의를 따른다.

---

## 1. 단일 비전 환경에서 전처리가 필요한 이유

단일 모바일 카메라 기반 포즈 추정(MediaPipe Pose 등)은 모든 프레임의 모든 랜드마크에 대해 좌표를 산출한다. 가려졌거나 신뢰도가 낮은 경우에도 좌표 자체는 빈 값이 아니다. 따라서 본 단계가 다루는 1차 문제는 “결측 좌표”가 아니라 다음과 같은 “신뢰성 낮은 좌표”이다.

- 해부학적으로 비현실적 위치
- 낮은 가시도(visibility)
- 프레임 간 비정상적 점프

전처리는 이 현실에 맞게 설계된다.

## 2. 분석 단계에서의 위치

```text
Pose CSV
→ ① 데이터 검증
→ ② Annotation 적용
→ ③ 운동 정의 로딩
→ ④ 전처리                 ← 본 단계
→ ⑤ 정규화
→ ⑥ 귀속
→ ⑦ 특징 추출
```

② Annotation이 먼저 적용되어 `exercise_type`과 `pattern`이 사용 가능해진 후, ③ 운동 정의 로딩이 운동별 속성 객체(`landmarks`, `laterality`, `quality_rules` 등)를 적재한다. ④ 전처리는 이 객체를 참조해 운동별 점검을 활성화/비활성화한다.

⑤ 정규화는 ④ 전처리 후에 수행된다. 그 이유는 정규화의 배율 기준(중간값 몸통 길이)이 hip·shoulder 랜드마크의 신뢰도를 거친 후에 더 안정적이기 때문이다.

## 3. 설계 원칙

본 단계는 **데이터 품질 문제만 보정**한다. 동작의 질적 패턴(보상 움직임, 스쿼트 깊이 등)은 보정하지 않는다.

```text
허용:
- 가시도 기반 신뢰도 마킹
- 해부학적 제약 점검
- 좌우 라벨 스왑 보정 (라벨만 변경, 좌표는 그대로)
- 신뢰도 마스크된 단기 결손에 대한 보간
- 작은 프레임 단위 잡음의 평활화
- 전처리 보고서 산출

금지:
- 비정상 동작을 정상으로 만드는 변경
- 부족한 스쿼트 깊이를 보정
- knee valgus 패턴을 보정
- 프레임을 조용히 삭제
- 원본 frame 번호를 변경
- 특정 운동학 모델에 맞추기 위한 좌표 변경
```

본 단계는 생체역학적·동작 품질적으로 의미 있는 패턴을 가려서는 안 된다.

## 4. 입력

본 단계의 입력은 ① 데이터 검증, ② Annotation, ③ 운동 정의를 거친 포즈 데이터프레임이다.

필수 좌표 컬럼:

```text
<landmark>_x
<landmark>_y
<landmark>_z
```

가시도 컬럼이 있을 경우 신뢰도 검출에 사용된다.

```text
<landmark>_visibility
```

annotation 맥락 컬럼은 운동별 로직 활성화에 사용된다.

```text
exercise_type
pattern
```

운동 정의에서 본 단계가 읽는 필드:

```text
landmarks.primary_joints
landmarks.critical_landmarks
classification.laterality
quality_rules.minimum_visible_landmark_ratio
quality_rules.max_interpolation_gap_frames
```

generic fallback일 경우 보수적 기본값을 사용한다.

## 5. 출력

본 단계는 데이터프레임과 보고서를 함께 반환한다.

```python
pre_df, pre_report = preprocess_pose_dataframe(df, landmarks, exercise_definition)
```

출력 데이터프레임이 보존하는 컬럼:

```text
frame
timestamp
원본 좌표 컬럼
가시도 컬럼(있는 경우)
annotation 컬럼
```

본 단계가 추가하는 신뢰도 관련 컬럼:

```text
<landmark>_reliable        bool, 랜드마크 단위 프레임 단위 신뢰도 마스크
preprocessing_valid        bool, 프레임 단위 종합 신뢰도
preprocessing_note         str, 신뢰 불가 사유
swap_corrected             bool, 좌우 라벨 스왑 발생 여부
```

초기 구현은 좌표 컬럼을 직접 갱신하거나, 별도의 전처리 좌표 컬럼을 추가하는 두 방식 중 하나를 택한다. 직접 갱신을 택할 경우 보고서가 어떤 처리가 적용되었는지를 명확히 기록한다.

후속 버전이 별도 컬럼을 추가할 경우의 명명 예:

```text
left_knee_pre_x
left_knee_pre_y
left_knee_pre_z
```

## 6. 신뢰도 검출

랜드마크 단위 프레임 단위 신뢰도 마스크가 산출된다. 다음 조건 중 하나라도 만족하면 unreliable로 표시된다.

### 6-1. 가시도 게이팅

```text
landmark.visibility < visibility_threshold (default: 0.5)
```

낮은 가시도 랜드마크는 표시만 하고 삭제하지 않는다.

### 6-2. 분절 길이 일관성

각 분절(skeleton segment)의 프레임별 길이를 시퀀스 중간값과 비교한다. **단, hip-knee(thigh) 분절은 본 점검에서 제외한다.** 단일 비전에서 thigh 분절은 squat 등에서 깊이 변화에 따라 외관 길이가 40% 이상 변동할 수 있어 정상 동작에서도 위반이 자주 발생하기 때문이다.

```text
deviation = |segment_length(t) - median_segment_length| / median_segment_length

if deviation > segment_length_tolerance (default: 0.25):
    frame t에서 양 끝점 랜드마크를 unreliable로 표시
```

좌우 분절(예: left_thigh vs right_thigh) 간 비교도 보조 점검으로 사용할 수 있다.

### 6-3. 관절각 생리학적 한계

(proximal, vertex, distal) triplet에서 산출한 included angle을 보수적 해부학 한계와 비교한다.

```text
관절          허용 included angle (도)
─────────────────────────────────────
무릎(knee)    10 – 180
팔꿈치(elbow) 10 – 180
고관절(hip)   20 – 180
```

점검 관절: `left_knee`, `right_knee`, `left_elbow`, `right_elbow`, `left_hip`, `right_hip`. 본 점검은 “해부학적으로 불가능한 형태”만을 표시하기 위한 보수적 임계이며, 운동별 정상 범위 점검은 ⑦ 특징 추출의 책임이다.

### 6-4. 속도 이상치

프레임 간 변위가 임계값을 넘는 경우를 표시한다.

```text
v(t) = |p(t) - p(t-1)| / Δt

if v(t) > velocity_threshold:
    frame t의 해당 랜드마크를 unreliable로 표시
```

임계값은 시퀀스 단위 몸통 길이/초 단위로 정의해 신체 크기에 무관하게 만든다.

## 7. 좌우 라벨 스왑 검출 (운동-인지)

포즈 추정기는 paired 랜드마크의 좌우 라벨을 가끔 뒤집는다(특히 가려짐, 회전, prone 자세에서). 본 점검은 운동 정의의 `classification.laterality`를 기준으로 활성화 여부를 결정한다 (annotation의 `pattern`과 교차 검증).

```text
laterality = bilateral_symmetric  → frame 단위 스왑 검출 비활성
laterality = alternating          → frame 단위 스왑 검출 활성
laterality = unilateral_*         → 활성, 단측 우선 적용
```

### 7-1. 검출 휴리스틱 (둘을 함께 사용)

시간 일관성 점검:

```text
frame t에 스왑 의심:
  |p_L(t) - p_R(t-1)|  <  |p_L(t) - p_L(t-1)|
  AND
  |p_R(t) - p_L(t-1)|  <  |p_R(t) - p_R(t-1)|
```

운동별 방향 점검(적용 가능한 경우):

```text
정면 동작:
  (left_hip.x - right_hip.x) 의 기대 부호가 카메라 규약에 의해 고정된다.

관측 부호가 반복(rep)의 orientation_disagree_ratio 이상에서 어긋나면,
해당 반복은 시퀀스 단위 스왑 가능성으로 표시한다.
```

### 7-2. 보정 정책

스왑이 높은 확신으로 검출되면, 해당 프레임의 paired 랜드마크 좌우 라벨을 교체한다. **라벨만 교체이며 좌표값은 변경하지 않는다.**

```text
swap_corrected = True 로 마킹
preprocessing_note 에 트리거된 휴리스틱 기록
```

확신이 낮으면 좌표·라벨을 변경하지 않고 표시만 한다. 반복 단위 일관성은 ⑥ 귀속 단계에서 추가로 점검한다.

## 8. 결손 마스크에 대한 단기 보간

원본 결측이 아니라 **신뢰도 마스크된 결손**에 대해서만 단기 보간을 적용한다.

```text
입력 : 위 단계들이 산출한 신뢰도 마스크
출력 : 짧은 마스크 결손은 보간으로 채워지고, 긴 결손은 미해결 상태로 유지된다.
```

정책 (운동 정의의 `quality_rules.max_interpolation_gap_frames`에서 읽는다, 기본 3):

```text
max_interpolation_gap = 3 frames
method                = linear
```

```text
짧은 마스크 결손  → 선형 보간
긴 마스크 결손    → unreliable로 유지, 보고서에 미해결로 기록
```

긴 unreliable 구간이 인공적으로 재구성되는 것을 방지한다.

## 9. 평활화 (Smoothing)

신뢰성 있는 랜드마크의 작은 프레임 단위 잡음을 줄이기 위한 단계.

초기 구현은 단순하고 해석 가능한 방법을 사용한다.

```text
moving_average
rolling_median
none
```

포즈 데이터에는 잔여 이상치에 견고한 `rolling_median`이 권장된다. 기본값은 보수적이다.

```text
smoothing.enabled = false
```

평활화 활성화 시 보고서에 다음을 기록한다.

```text
method
window_size
applied_columns
```

평활화 윈도우는 의미 있는 동작 동특성(보상 움직임 등)을 제거하지 않을 만큼 짧아야 한다.

## 10. Kalman 필터 정책

Kalman 필터링은 연구계획서에서 프레임 단위 좌표 잡음·시계열 불연속성 보정을 위한 최종 방법으로 언급된다. 초기 구현은 다음의 단순한 방법으로 검증 가능한 베이스라인을 먼저 확립한다.

```text
가시도 게이팅
해부학적 제약 점검
속도 이상치 검출
마스크 결손에 대한 선형 보간
rolling median
```

단순 방법이 충분히 특성화되고 프레임 간 상태 추정 필요성이 명확해진 시점에 Kalman 필터링을 도입한다. YAML 옵션은 미리 두되 비활성 상태로 둔다.

```yaml
preprocessing:
  enabled: false
  kalman_filter:
    enabled: false
```

이 단계적 접근은 초기 분석 체계의 해석 가능성을 유지하면서 향후 업그레이드 경로를 보존한다.

## 11. 운동별 분기 요약

본 단계가 운동 정의의 `classification.laterality`(annotation의 `pattern`과 교차 점검)에 따라 적용하는 분기:

```text
laterality                       visibility   segment   ROM   velocity   L/R swap   smoothing
─────────────────────────────    ──────────   ───────   ───   ────────   ────────   ─────────
bilateral_symmetric              enabled      enabled   enabled  enabled  skip       optional
alternating                      enabled      enabled   enabled  enabled  enabled    optional
unilateral_*                     enabled      enabled   enabled  enabled  enabled    optional
generic fallback                 enabled      enabled   enabled  enabled  skip       optional
```

generic fallback은 bilateral 분기로 폴백한다. 이는 잘못된 스왑 보정을 만들 위험이 없는 안전한 기본값이기 때문이다.

## 12. 무효 프레임 표시

본 단계는 프레임을 조용히 삭제하지 않는다. 대신 품질 메타데이터 컬럼을 추가한다.

```text
preprocessing_valid
preprocessing_note
swap_corrected
```

의미:

```text
preprocessing_valid = True   → 본 단계 후 사용 가능한 프레임
preprocessing_valid = False  → 미해결 품질 문제가 남은 프레임
swap_corrected      = True   → 좌우 라벨이 교체된 프레임
```

⑦ 특징 추출 시점의 정확한 프레임 제외는 annotation·특징 단계 규칙이 결정한다.

## 13. 전처리 보고서

```text
method
exercise_type
pattern
laterality
num_frames
num_coordinate_columns

reliability_summary:
  visibility_threshold
  num_low_visibility_frames_per_landmark
  num_segment_length_violations
  num_joint_angle_violations
  num_velocity_outliers
  num_unreliable_landmark_frames

swap_detection_summary:
  enabled
  num_temporal_swap_corrected
  num_orientation_disagree_reps

interpolation_summary:
  enabled
  max_interpolation_gap
  num_short_gaps_interpolated
  num_long_gaps_unresolved

smoothing_summary:
  enabled
  method
  window_size
  applied_columns

num_invalid_frames
applied_columns
```

본 보고서는 본 단계를 재현 가능·감사 가능하게 만든다.

## 14. 향후 확장

- 가시도 가중 보간
- 신뢰도 가중 평활화
- Hampel 필터(이상치 견고 평활화)
- One-Euro Filter(저지연 jitter-aware 평활화)
- Kalman 필터링 도입
- 운동별 속도 임계값 튜닝
- 랜드마크별 신뢰도 규칙(예: 가려진 반복의 발 랜드마크)
- 보정 전·후 시각화
