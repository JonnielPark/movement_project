# 05. 정규화 (Normalization)

**문서 버전:** 1.4.0
**최종 갱신:** 2026-05-21
**영문 동기화:** `docs_eng/pipeline/05_normalization.md`는 동일 버전의 영문 번역본이다.

파이프라인 단계 ⑤는 원시 pose 좌표를 신체 상대 좌표계로 변환한다. 명시적으로 켠 경우에는
단안 pose의 일관된 관찰 편향을 줄이는 검토용 canonical 좌표도 생성할 수 있다.

이 단계는 절대 힘, 절대 토크, calibrated 3D, 절대 신체 치수를 추정하지 않는다. ⑧ Feature
Extraction과 ⑨ Biomechanical Proxy의 좌표 기반을 제공한다.

---

## 1. 파이프라인 위치 (Pipeline Position)

```text
Pose CSV
→ ① Validation
→ ② Annotation
→ ③ Exercise Definition
→ ④ Preprocessing
→ ⑤ Normalization          ← 본 단계
   ├─ base normalization: hip-center translation + torso-length scale
   └─ optional canonicalization: review-only candidate coordinates
→ ⑥ Segmentation
→ ⑦ Motion Attribution
→ ⑧ Feature Extraction
```

④ Preprocessing 이후에 실행된다. 신뢰도 낮은 hip/shoulder landmark가 척도 기준에 영향을 주기
전에 보정, 보간, 또는 표시되어야 하기 때문이다.

---

## 2. 기본 정규화 계약 (Base Normalization Contract)

구현된 방식은 `hip_torso`다.

```text
평행이동 기준 : 프레임별 골반 중심
척도 기준     : 시퀀스 단위 몸통 길이 중앙값
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
p_norm_i(t)        = (p_i(t) - hip_center(t)) / s
```

원시 좌표는 절대 덮어쓰지 않는다.

```text
left_knee_x       원본 x
left_knee_norm_x  기본 정규화 x
left_knee_canon_x 선택 canonical 후보 x
```

좌표 계열의 의미는 고정한다.

```text
raw      원본 pose 좌표
norm     hip-torso 기본 정규화 좌표
canon    canonicalization 이후 선택 검토/후보 좌표
```

---

## 3. 설정 계약 (Configuration Contract)

상세 기본값은 `configs/pipeline_default.yaml`에 둔다. 안정적인 계약은 다음과 같다.

```yaml
normalization:
  enabled: true
  method: hip_torso
  keep_reference_columns: true
  canonicalization:
    enabled: false
    coordinate_mode: norm
    output_prefix: canon
    report_only: true
    downstream_coordinate_mode: norm
    data_confidence: ...
    support_plane_alignment: ...
    movement_plane_alignment: ...
    protocol_height_lateral_width_alignment: ...
    anthropometric_skeleton_prior: ...
```

`report_only: true`는 `canon` 좌표와 report를 만들 수 있지만 후속 단계가 계속 `norm` 좌표를
소비한다는 뜻이다. `downstream_coordinate_mode`를 `canon`으로 바꾸려면 노트북 검토, robustness
근거, 명시적 문서 갱신이 선행되어야 한다.

`floor_relative_correction`은 local 또는 legacy config에 남아 있을 수 있다. 이는
`support_plane_alignment`의 하위 호환 alias로 취급하며, 새 작업에서는 canonicalization key를
우선 사용한다.

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
}
```

canonicalization이 켜진 경우 `canonicalization_report`를 normalization report 안에 추가한다.

```python
{
    "enabled": bool,
    "status": "skipped" | "applied" | "partial" | "rejected",
    "coordinate_mode": "norm",
    "output_prefix": "canon",
    "report_only": bool,
    "downstream_coordinate_mode": "norm" | "canon",
    "active_priors": list[str],
    "applied_priors": list[str],
    "skipped_priors": dict[str, str],
    "max_correction_torso": float,
    "median_correction_torso": float,
    "residual_after_fit_torso": float | None,
    "data_confidence": {
        "level": "high" | "moderate" | "low",
        "reasons": list[str],
    },
    "prior_reports": {
        "support_plane_alignment": dict | None,
        "movement_plane_alignment": dict | None,
        "protocol_height_lateral_width_alignment": dict | None,
        "anthropometric_skeleton_prior": dict | None,
    },
}
```

`data_confidence.level`은 movement-quality score가 아니다. 낮은 confidence는 자동 감점이 아니라
주의, withheld, provenance로 표현한다.

---

## 5. Canonicalization 계약 (Canonicalization Contract)

Canonicalization은 선택 기능이며 기본 비활성화 상태다. 이는 calibrated 3D reconstruction도,
좋은 동작 template fitting도 아니다. 역할은 raw/norm 좌표를 보존한 채 일관된 관찰 편향을
완화하고, knee valgus, heel lift, trunk lean, pelvis rotation 같은 실제 보상 패턴을 남기는 것이다.

현재 활성 또는 계획 prior:

| Prior | 상태 | 목적 | 보호선 |
|---|---|---|---|
| `support_plane_alignment` | 구현됨, 기본 비활성 | 접지 landmark 기반 pose 내부 pseudo-floor/support-plane 검토. 기존 `floor_relative_correction` 로직을 감싼다. | 발을 바닥에 고정하지 않으며 camera calibration이 아니다. |
| `movement_plane_alignment` | prototype, 기본 비활성 | hip-knee-ankle 주 운동 방향을 이용한 수직축 기준 capped rigid rotation. | out-of-plane residual을 보존해 보상 움직임 검토에 남긴다. |
| `protocol_height_lateral_width_alignment` | prototype, 기본 비활성 | H1/H2/H3 body anchor 주변의 보수적 lateral-width attenuation 전에 camera-height metadata를 gate로 사용한다. | 렌즈 보정, reprojection, far-side 좌표 생성이 아니다. |
| `anthropometric_skeleton_prior` | 계획됨, 기본 비활성 | 느슨한 신체 분절 길이 plausibility range를 단안 depth 검토용 engineering envelope로 사용한다. | raw row-level 자료 전에는 경험적 P5/P95가 아니며 skeleton template fitting이 아니다. |

현재 prior 순서:

```text
1. support_plane_alignment
2. movement_plane_alignment
3. protocol_height_lateral_width_alignment
4. anthropometric_skeleton_prior
```

Body-axis alignment는 의도적으로 활성화하지 않는다. 골반/어깨 축 정렬은 너무 일찍 적용하면
실제 골반 회전, 체간 기울기, 횡단면 보상을 지울 수 있으므로, anthropometric skeleton prior가
구체화된 뒤에만 재검토한다.

---

## 6. 인체계측 스켈레톤 Prior 정책 (Anthropometric Skeleton Prior Policy)

### 6.1 목적 (Purpose)

Anthropometric skeleton prior는 단안 pose depth를 위한 **느슨한 해부학적 plausibility envelope**다.
정밀한 인체계측 통계 모델이 아니다.

허용 용도:

```text
- 정규화 이후 anatomically implausible한 segment length 표시
- bounded하고 작은 경우에만 review-only candidate depth residual correction 생성
- 영향받은 segment/frame/feature record의 data confidence downgrade
- depth-sensitive feature가 withheld 또는 low confidence가 된 이유 문서화
```

금지:

```text
- raw coordinates overwrite
- base norm coordinates overwrite
- normal skeleton template에 pose 강제 fitting
- monocular depth confidence를 high로 승격
- calibrated 3D reconstruction 또는 subject-specific body reconstruction 주장
- row-level raw 인체계측 자료 전 empirical P5/P95 range 주장
- 절대 물리 길이, 힘, 토크, 근력, 진단, 예후 추론
```

### 6.2 근거 수준 (Evidence Level)

현재 source scope:

```text
source                 Size Korea 8th Korean Anthropometric Survey
included data family   2020 3D full-body automatic measurements only
included item range    No.138-311
excluded families      direct measurement, 3D direct measurement,
                       3D foot/hand/head automatic measurements
current evidence       file design + aggregate statistics fallback
raw row-level data     not yet available
```

현재 통계표는 항목별 주변분포 aggregate 값을 제공한다. 같은 개인 안에서
`(hip height - knee height) / stature`처럼 짝지어진 비율을 직접 제공하지 않는다.
따라서 첫 구현 단계는 aggregate engineering envelope만 사용할 수 있다. 이 range를 경험적
percentile prior라고 부르면 안 된다.

Two-stage evidence model:

| Stage | Data level | Allowed claim | Use |
|---|---|---|---|
| Stage A | file design + aggregate statistics | aggregate ratio 주변의 conservative engineering range | plausibility flag, low-confidence marking, review-only candidate residual |
| Stage B | de-identified row-level 3D full-body automatic raw data | empirical row-level ratio distribution, P1/P99, P5/P95, stratified checks | narrower prior, height-bin validation, model comparison |

### 6.3 Aggregate-Only Segment Map

첫 prior는 aggregate statistics에서 파생한 dimensionless ratio를 사용한다. 아래 값은
개인별 ratio percentile이 아니다.

| Segment | Pose endpoints | Measurement proxy | Aggregate mean/stature | Status |
|---|---|---|---:|---|
| `shoulder_width` | left_shoulder ↔ right_shoulder | `m299` shoulder-outside breadth | 0.2220 | proxy close |
| `hip_width` | left_hip ↔ right_hip | `m265` hip breadth | 0.2114 | surface-width proxy |
| `torso` | shoulder_center ↔ hip_center | `m145 - m155` | 0.3211 | vertical proxy, not Euclidean torso |
| `upper_arm` | shoulder ↔ elbow | `m189` | 0.1921 | proxy close |
| `forearm` | elbow ↔ wrist | `m191 - m189` | 0.1423 | derived proxy |
| `thigh` | hip ↔ knee | `m155 - m159` | 0.2287 | vertical proxy |
| `shank` | knee ↔ ankle | `m159 - m161` | 0.2186 | vertical proxy to lateral malleolus |
| `foot` | ankle ↔ foot_index | not available | null | unavailable in current source scope |

`sitting_height`, `trunk_vertical`, `crotch_height`, `outside_leg_length`는 검토용 보조 proxy로
저장할 수 있지만 primary skeleton segment는 아니다.

`m195` thigh straight length는 primary hip-knee prior가 아니다. Aggregate stature ratio가
`m155 - m159`보다 훨씬 작으므로, 측정 정의가 검토되기 전까지 definition-check 또는 sensitivity
note로만 유지한다.

### 6.4 Range 정책 (Range Policy)

Stage A range policy:

```text
center value          aggregate mean(segment) / aggregate mean(stature)
range name            conservative_engineering_range
range source          aggregate center 주변의 연구자 정의 loose tolerance
range purpose         impossible skeleton behavior 탐지, population percentile 추정 아님
configuration         YAML/data artifact에 저장하고 Python에 hardcode하지 않음
```

Stage B upgrade policy:

```text
required input        de-identified row-level 3D full-body automatic raw table
ratio calculation     segment / stature, segment / torso proxy, relevant body-scale ratios
summary statistics    n, mean, SD, median, IQR, P1, P5, P95, P99
range names           recommended_plausible_range = P5-P95
                      conservative_range = P1-P99
stratification        sex, age_group, height_bin only after sample-size review
```

### 6.5 Height-Bin 정책 (Height-Bin Policy)

설문에서는 선택형 5 cm 키 범주를 수집할 수 있다:

```text
150cm 이하
151-155cm
156-160cm
161-165cm
166-170cm
171-175cm
176-180cm
181cm 이상
응답하지 않음
```

Stage A에서 height bin은 metadata/provenance 용도다. Aggregate table만으로는 height-bin-specific
segment ratio가 모델을 개선한다는 것을 증명할 수 없으므로 stratified prior 선택에는 사용하지 않는다.

Stage B에서 row-level data가 확보되면 bin 유용성을 검정할 수 있다:

```text
Model 0  overall mean ratio
Model 1  sex mean ratio
Model 2  sex + height_bin mean ratio
Model 3  sex + age_group + height_bin mean ratio
```

5 cm bin이 sparse하거나 불안정하면 내부 분석에서는 인접 bin을 병합할 수 있다. 설문 선택지는 향후
유연성을 위해 5 cm bin을 유지할 수 있다.

### 6.6 Correction 및 Confidence 정책

Prior는 다음 조건을 모두 만족할 때만 candidate `canon` 좌표를 만들 수 있다:

```text
1. 해당 segment가 prior에 존재
2. x/y evidence 자체가 plausible range를 이미 위반하지 않음
3. bounded depth residual로 segment를 loose range 안으로 가져올 수 있음
4. correction magnitude가 config cap 이하
5. landmark visibility와 swap-risk gate가 review를 허용
```

x/y projection 자체가 envelope 밖이면 depth를 invent해서 segment를 맞추지 않는다. 해당
segment/frame을 low confidence 또는 not assessed로 표시한다.

Report fields:

```text
source_scope
evidence_level
range_type
segments_checked
segments_unavailable
candidate_corrections
correction_magnitude_torso
rejection_reasons
confidence_downgrade_reasons
model_depth_reliability_after_correction = low
```

### 6.7 Articulation Plausibility

관절 각도와 reverse-bending constraint는 Size Korea segment length statistics와 분리한다.
이는 `articulation_plausibility` guard로 별도 문서화·구현하며, impossible configuration의
data confidence를 낮추는 역할만 한다. Movement-quality score를 직접 감점하지 않는다.

### 6.8 Data Artifact 정책 (Data Artifact Policy)

권장 repository 위치:

```text
data/reference/anthropometry/
    size_korea8_3d_auto_skeleton_prior.yaml
    size_korea8_3d_auto_aggregate_ratio_preview.csv
    size_korea8_3d_auto_unavailable_segments.csv

data/processed/anthropometry/
    row-level-derived summaries and validation reports when raw data become available
```

모든 파생 table에는 다음을 포함한다:

```text
source_scope = 3d_fullbody_auto_only
evidence_level = aggregate_engineering_preview | row_level_empirical
unit = dimensionless_ratio
```

---

## 7. 후속 단계 규칙 (Downstream Rules)

- ⑥ Segmentation, ⑧ Feature Extraction, ⑨ Biomechanical Proxy, ⑩ Biomarker Scoring은 기본적으로
  `norm` 좌표를 소비한다.
- `canon` 좌표는 승격 기준이 작성되고 테스트되기 전까지 검토용 후보 좌표다.
- Corrected-coordinate magnitude와 residual은 movement-quality 감점이 아니라
  data-confidence/provenance signal이다.
- ④ Preprocessing은 scale 계산 전에 reliability violation을 표시할 수 있지만, 신체 상대 척도화와
  canonical 후보 좌표 생성은 ⑤ Normalization의 책임이다.
- ⑨ Biomechanical Proxy는 정규화 좌표로 상대 CoM, moment-arm, load-shift proxy를 계산한다.
  이 단계로부터 절대 힘, 토크, calibrated physical distance를 추론하지 않는다.
- Anthropometric skeleton prior 출력은 명시적 승격 규칙이 notebook review와 robustness evaluation으로
  정의되기 전까지 후속 단계에서 사용하지 않는다.

---

## 8. 향후 확장 (Planned Extensions)

- Size Korea 8차 3D full-body automatic measurement source에서 Stage A aggregate-only engineering
  prior를 만든다.
- 비식별 row-level 3D full-body automatic measurements가 확보될 때만 row-level empirical prior를
  추가한다.
- visibility-weighted scale estimation과 torso-length outlier handling.
- exercise definition field 기반 운동별 canonicalization prior 선택.
- `canon` coordinate 승격 전 robustness evaluation.
- local config가 더 이상 의존하지 않으면 legacy `floor_relative_correction` key 점진 축소.
