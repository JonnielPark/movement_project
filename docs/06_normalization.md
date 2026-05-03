# 06. 정규화 (Normalization)

본 단계는 원본 포즈 좌표를 **신체 기준 좌표계**로 변환해, 카메라 위치·피험자 위치·신체 크기·포즈 추정 배율의 영향을 줄인다. 이로써 후속 단계가 동작 패턴을 프레임·피험자 간 비교 가능한 형태로 다룰 수 있다.

본 단계는 절대값 힘이나 절대 신체 치수를 추정하지 않는다. 본 단계의 목적은 ⑦ 특징 추출 / ⑧ 생체역학적 근사 모델링이 사용할 안정적인 좌표 기반을 마련하는 것이다.

> 용어는 [`_terminology.md`](_terminology.md)의 단일 정의를 따른다.

---

## 1. 분석 단계에서의 위치

```text
Pose CSV
→ ① 데이터 검증
→ ② Annotation 적용
→ ③ 운동 정의 로딩
→ ④ 전처리
→ ⑤ 정규화                ← 본 단계
→ ⑥ 귀속
→ ⑦ 특징 추출
```

본 단계가 ④ 전처리 후에 수행되는 이유는, 배율 추정에 사용되는 hip·shoulder 랜드마크가 신뢰도 점검을 거친 후에야 안정적이기 때문이다.

## 2. 설계 요약

초기 구현이 채택하는 정규화 방법:

```text
이동 기준 (translation reference) : 프레임별 엉덩이 중심 (frame-wise hip center)
배율 기준 (scale reference)        : 시퀀스 중간값 몸통 길이 (sequence-wise median torso length)
```

단일 비전 환경의 잡음에 의한 프레임별 배율 진동을 피하기 위한 설계이다.

## 3. Step 1. Translation Normalization

엉덩이 중심을 신체 기준점으로 사용한다.

```text
hip_center(t) = (left_hip(t) + right_hip(t)) / 2
```

각 랜드마크에서 엉덩이 중심을 빼서 이동시킨다.

```text
p_translated_i(t) = p_i(t) - h(t)
```

이 단계 후, 각 랜드마크는 카메라 / 영상 좌표계가 아니라 **골반(pelvis)을 원점으로 하는 좌표계**에서 표현된다.

## 4. Step 2. Scale Normalization

몸통 길이(torso length)를 신체 배율 단위로 사용한다.

```text
shoulder_center(t) = (left_shoulder(t) + right_shoulder(t)) / 2
torso_length(t)    = distance(hip_center(t), shoulder_center(t))
```

프레임별 몸통 길이가 아니라 **시퀀스 중간값**을 대표 배율로 사용한다.

```text
s = median(torso_length over all valid frames)
```

각 이동된 랜드마크를 이 배율로 나눈다.

```text
p_norm_i(t) = (p_i(t) - h(t)) / s
```

여기서 `s`는 시퀀스 중간값 몸통 길이이다.

## 5. 왜 시퀀스 중간값 배율인가

단일 비전 포즈 데이터에서는 잡음·가려짐·심도 추정 불안정성으로 인해 프레임별 몸통 길이 추정이 불안정할 수 있다.

```text
프레임별 배율:
- 매 프레임 반응한다.
- 포즈 추정 잡음에 민감하다.
- 인공적 skeleton 흔들림을 야기할 수 있다.

시퀀스 중간값 배율:
- 시퀀스 전체에서 안정적이다.
- 단기 잡음에 견고하다.
- 특징 추출에 적합하다.
```

따라서 본 프레임워크의 기본 정규화 식:

```text
p_norm_i(t) = (p_i(t) - hip_center(t)) / median_torso_length
```

## 6. ④ 전처리와의 관계

④ 전처리가 신뢰도 마스크와 보간을 거친 후에 본 단계가 수행되어야 hip·shoulder 랜드마크의 노이즈에 의한 배율 왜곡이 줄어든다.

```text
전처리된 좌표
→ 엉덩이 중심 이동
→ 몸통 배율 정규화
```

## 7. ③ 운동 정의와의 관계

본 단계 자체는 운동에 따라 분기하지 않는다. 즉, 모든 운동에 동일한 정규화가 적용된다.

다만 본 단계의 출력 좌표계는 ③ 운동 정의를 참조하는 모든 후속 단계(⑥ 귀속, ⑦ 특징 추출, ⑧ 생체역학적 근사 모델링)의 입력으로 사용된다. 신체 기준 좌표에서 작업하는 것이 정의 기반 바이오마커를 피험자 간 비교 가능하게 만든다.

## 8. ⑧ 생체역학적 근사 모델링과의 관계

본 단계는 좌표계의 1차 변환이며, 후속 ⑧ 생체역학적 근사 모델링과 혼동되어서는 안 된다.

```text
정규화 (본 단계)
→ 안정적인 신체 기준 좌표 산출

생체역학적 근사 모델링 (⑧)
→ CoM, 분절 단위 관계, 모멘트 암, 상대 부하 분포 추정
   (운동 정의의 biomechanical_focus 가 구동)
```

⑧ 단계는 분절 길이 추정과 통계적 인체 계측 가정을 사용해 CoM과 모멘트 암 기반 근사 지표를 산출한다. 본 단계는 단지 그 단계를 위한 좌표계를 마련한다.

## 9. ⑥ 귀속과의 관계

⑥ 귀속(motion attribution)은 정규화된 데이터프레임 위에서 작동한다. 신체 기준 좌표에서 작업하면 절대 신체 크기와 카메라 거리가 이미 제거되어, 반복·피험자 간 motion energy 비교가 더 일관된다.

## 10. 출력 컬럼

원본 좌표는 보존한다. 정규화 좌표는 새 컬럼으로 추가한다.

```text
left_knee_x      → 원본 x
left_knee_norm_x → 정규화 x

left_knee_y      → 원본 y
left_knee_norm_y → 정규화 y

left_knee_z      → 원본 z
left_knee_norm_z → 정규화 z
```

보조 참조 컬럼:

```text
hip_center_x
hip_center_y
hip_center_z

shoulder_center_x
shoulder_center_y
shoulder_center_z

torso_length
```

## 11. 정규화 보고서

본 단계는 정규화 데이터프레임과 함께 보고서를 반환한다.

```python
norm_df, norm_report = normalize_pose_by_hip_torso(df, landmarks)
```

보고서에 포함될 항목:

```text
method
num_frames
scale_method
scale_value
min_torso_length
max_torso_length
median_torso_length
num_invalid_torso_frames
num_normalized_landmarks
```

이 보고는 비정상 배율 추정이나 랜드마크 문제를 사후 점검할 수 있도록 한다.

## 12. 향후 확장

- 가시도 기반 배율 필터링
- torso length 이상치 제거
- 신체 중심 좌표계 기반 회전 정규화
- 운동 정의 필드 기반 운동별 정규화 규칙
- 분절 길이 기반 통계적 인체 계측 모델링
