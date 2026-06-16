# 05. 정규화 (Normalization)

**문서 버전:** 2.0.0
**최종 갱신:** 2026-06-16
**영문 동기화:** `docs_eng/pipeline/05_normalization.md`는 동일 버전의 영문 번역본이다.

파이프라인 단계 ⑤는 원시 pose 좌표를 `norm`이라는 신체 상대 좌표 계열로 변환한다. 이 단계는
평행이동과 척도 정규화만 수행한다. Canonicalized 좌표, corrected-depth 좌표, 운동 prior로 제약된
후보 좌표는 만들지 않는다.

이 단계는 절대 힘, 절대 토크, calibrated 3D 위치, 절대 신체 치수를 추정하지 않는다. ⑥
Canonicalization과 이후 recording-view feature extraction이 사용할 안정적인 좌표 기반을 제공한다.

---

## 1. 파이프라인 위치 (Pipeline Position)

```text
Pose CSV
→ ① Validation
→ ② Annotation
→ ③ Exercise Definition
→ ④ Preprocessing
→ ⑤ Normalization          ← 본 단계
→ ⑥ Canonicalization
→ ⑦ Segmentation
→ ⑧ Motion Attribution
→ ⑨ Feature Extraction
→ ⑩ Biomechanical Proxy
→ ⑪ Biomarker Scoring
```

④ Preprocessing 이후에 실행된다. 신뢰도 낮은 hip/shoulder landmark가 척도 기준에 영향을 주기
전에 보정, 보간, 또는 표시되어야 하기 때문이다.

---

## 2. 기본 정규화 계약 (Base Normalization Contract)

구현된 방식은 `hip_torso`다.

```text
평행이동 기준 : 프레임별 골반 중심
척도 기준     : 시퀀스 단위 몸통 길이 중앙값
모델 depth gain: model_depth_scale, 기본 1.0
출력 단위     : torso_length_ratio (무차원)
```

골반 중심을 신체 상대 원점으로 사용한다.

```text
hip_center(t) = (left_hip(t) + right_hip(t)) / 2
p_translated_i(t) = p_i(t) - hip_center(t)
```

시퀀스 단위 몸통 길이 중앙값을 신체 척도로 사용한다. 프레임별 척도 대신 시퀀스 중앙값을
사용하면 단안 torso-length noise로 인한 인위적 skeleton jitter를 줄일 수 있다.

```text
shoulder_center(t) = (left_shoulder(t) + right_shoulder(t)) / 2
torso_length(t)    = distance(hip_center(t), shoulder_center(t))
s                  = median(valid torso_length)
p_norm_x_i(t)      = p_translated_x_i(t) / s
p_norm_y_i(t)      = p_translated_y_i(t) / s
p_norm_z_i(t)      = p_translated_z_i(t) * model_depth_scale / s
```

`model_depth_scale`은 단안 모델 depth에 대한 좌표 gain이며 camera calibration이 아니다. 기본값은
`1.0`이다. 검토 run에서는 model depth를 약화할 수 있지만, 반드시 report해야 하며 여전히
low-confidence evidence로 취급한다.

원시 좌표는 절대 덮어쓰지 않는다.

```text
left_knee_x       원본 x
left_knee_norm_x  기본 정규화 x
```

좌표 계열의 의미는 고정한다.

```text
raw   원본 pose 좌표
norm  ⑤에서 생성한 hip-torso 정규화 좌표
```

`canon` 및 corrected-3D-hypothesis 후보 좌표 계열은
[06_canonicalization.md](06_canonicalization.md)에 정의한다. 이들은 ⑥의 additive output이며
`raw`나 `norm`을 대체하지 않는다.

---

## 3. 설정 계약 (Configuration Contract)

상세 기본값은 `configs/pipeline_default.yaml`에 둔다. 안정적인 ⑤ 계약은 다음과 같다.

```yaml
normalization:
  enabled: true
  method: hip_torso
  keep_reference_columns: true
  model_depth_scale: 1.0
```

⑤ Normalization은 score gravity를 할당하지 않는다. 이후 단계가 사용할 좌표 척도와 model-depth
gain만 노출한다. 후보 confidence, correction burden, residual, norm-vs-candidate sensitivity는
⑥ Canonicalization 또는 이후 scoring policy의 책임이다.

---

## 4. 리포트 계약 (Report Contract)

`normalize_pose_by_hip_torso(df, landmarks)`는 정규화된 DataFrame과 report를 반환한다.

```python
{
    "method": str,
    "num_frames": int,
    "scale_method": str,
    "scale_value": float,
    "min_torso_length": float,
    "max_torso_length": float,
    "median_torso_length": float,
    "num_invalid_torso_frames": int,
    "num_normalized_landmarks": int,
    "model_depth_scale": float,
}
```

공개 ⑤ review surface는 다음 항목에 집중한다.

```text
scale_value
num_invalid_torso_frames
model_depth_scale
<landmark>_norm_x/y/z column 존재 여부
```

⑤는 `canonicalization_report`, corrected-coordinate readiness, score gravity, final-score
contribution flag를 방출하지 않는다.

---

## 5. 후속 단계 규칙 (Downstream Rules)

- ⑥ Canonicalization은 `norm` 좌표를 입력으로 받아 `canon` 또는 corrected-3D-hypothesis 후보
  좌표 계열을 추가할 수 있다.
- ⑦ Segmentation, ⑨ Feature Extraction, ⑩ Biomechanical Proxy, ⑪ Biomarker Scoring은 기본적으로
  `norm` 좌표를 소비한다.
- 후속 feature가 ⑥의 후보 좌표를 사용하려면 먼저 `recording_view_only`,
  `corrected_3d_hypothesis`, 또는 `dual_domain_compare` 평가 domain을 선언해야 한다.
- ⑤는 단안 depth 오류를 숨기지 않는다. 운동 시작 전 raw/model depth가 불안정하면 그 불안정성은
  `norm`에도 남는다. ⑥은 후보를 low confidence 또는 not available로 표시할 수 있다.
- ⑩ Biomechanical Proxy는 normalized coordinate로 상대 CoM, moment-arm, load-shift proxy를 계산한다.
  이 단계에서 절대 force, torque, calibrated physical distance를 추론해서는 안 된다.

---

## 6. 계획된 확장 (Planned Extensions)

- Visibility-weighted scale estimation과 torso-length outlier 처리.
- 운동 prior를 ⑤로 옮기지 않는 범위에서 운동별 normalization parameter review.
- Depth-sensitive downstream policy에 nonzero score gravity를 부여하기 전 `model_depth_scale`
  sensitivity robustness 평가.
