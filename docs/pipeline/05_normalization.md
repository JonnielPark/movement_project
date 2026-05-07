# 05. 정규화 (Normalization)

**문서 버전:** 1.0.0  
**최종 갱신:** 2026-05-06  
**영문 동기화:** `docs_eng/pipeline/05_normalization.md`는 동일 버전의 영문 번역본이다.

파이프라인 단계 ⑤. 원시 포즈 좌표를 신체 상대(body-relative) 좌표계로 변환하여,
카메라 위치, 피험자 위치, 신체 크기의 영향을 제거한다.

절대 힘이나 절대 신체 치수를 추정하지 않는다.
⑧ 피처 추출과 ⑨ 생체역학 프록시 모델링에 안정적인 좌표 기반을 제공한다.

---

## 1. 파이프라인 위치 (Pipeline Position)

```text
Pose CSV
→ ① Validation
→ ② Annotation
→ ③ Exercise Definition
→ ④ Preprocessing
→ ⑤ Normalization          ← 본 단계
→ ⑥ Segmentation
→ ⑦ Motion Attribution
→ ⑧ Feature Extraction
```

④ 전처리 이후에 실행된다. 척도 기준(몸통 길이 중앙값)은 엉덩이/어깨 랜드마크가
신뢰도 점검을 통과한 후 더 안정적이기 때문이다.

운동 종류별 분기를 하지 않는다 — 모든 운동에 동일한 정규화가 적용된다.

## 2. 방식: hip_torso (Method)

```text
평행이동 기준 : 프레임별 골반 중심 (hip center)
척도 기준     : 시퀀스 단위 몸통 길이 중앙값 (median torso length)
```

(프레임별 척도가 아닌) 시퀀스 단위 중앙값을 사용하면, 단안 깊이 추정의 프레임별 몸통 길이
노이즈로 인한 인위적 골격 떨림이 방지된다.

## 3. 1단계 — 평행이동 (Translation)

골반 중심을 신체 기준 원점으로 사용:

```text
hip_center(t) = (left_hip(t) + right_hip(t)) / 2
```

각 랜드마크가 평행이동된다:

```text
p_translated_i(t) = p_i(t) - hip_center(t)
```

본 단계 이후, 모든 랜드마크는 골반 원점에 대해 표현된다.

## 4. 2단계 — 척도화 (Scale)

몸통 길이를 신체 척도 단위로 사용:

```text
shoulder_center(t) = (left_shoulder(t) + right_shoulder(t)) / 2
torso_length(t)    = distance(hip_center(t), shoulder_center(t))
```

대표 척도로 시퀀스 단위 중앙값을 사용:

```text
s = median(모든 유효 프레임의 torso_length)
```

평행이동된 각 랜드마크를 `s`로 나눈다:

```text
p_norm_i(t) = (p_i(t) - hip_center(t)) / s
```

결과 단위는 `torso_length_ratio` (무차원)이다.

## 5. 출력 칼럼 (Output Columns)

원본 좌표는 보존된다. 정규화된 좌표는 새 칼럼으로 추가된다:

```text
left_knee_x      → 원본 x      left_knee_norm_x → 정규화된 x
left_knee_y      → 원본 y      left_knee_norm_y → 정규화된 y
left_knee_z      → 원본 z      left_knee_norm_z → 정규화된 z
```

참조 칼럼 (YAML에서 `keep_reference_columns: true`인 경우):

```text
hip_center_x, hip_center_y, hip_center_z
shoulder_center_x, shoulder_center_y, shoulder_center_z
torso_length
```

## 6. 설정 (Configuration)

```yaml
normalization:
  enabled: true
  method: hip_torso
  keep_reference_columns: true
```

## 7. 정규화 리포트 (Normalization Report)

```python
norm_df, norm_report = normalize_pose_by_hip_torso(df, landmarks)
```

리포트 필드:

```python
{
    "method": str,
    "num_frames": int,
    "scale_method": str,
    "scale_value": float,          # 몸통 길이 중앙값 (원시 단위)
    "min_torso_length": float,
    "max_torso_length": float,
    "median_torso_length": float,
    "num_invalid_torso_frames": int,
    "num_normalized_landmarks": int,
}
```

## 8. 다른 단계와의 관계 (Relationship to Other Steps)

- **④ 전처리**: 척도 오염을 막기 위해, 정규화 이전에 비신뢰 랜드마크
  (낮은 가시성, 스왑 보정 대상)를 해결하거나 표시해 두어야 한다.
- **⑦ 모션 어트리뷰션**: 정규화 좌표를 사용한다. 신체 크기와 카메라 거리 효과가 이미 제거되어
  반복별 동작 에너지(motion energy) 비교가 더 일관된다.
- **⑨ 생체역학 프록시**: CoM과 모멘트 암 추정의 입력으로 정규화 좌표를 사용한다.
  본 단계는 좌표계를 제공하고, ⑨가 생체역학 계산을 추가한다.

## 9. 향후 확장 (Planned Extensions)

- 가시성 가중 척도 추정
- 중앙값 계산 이전의 몸통 길이 이상값 제거
- 회전 정규화 (신체 상대 yaw 정렬)
- 운동 정의 필드로 구동되는 운동별 정규화 규칙
