# 05. 정규화 (Normalization)

**문서 버전:** 1.13.0
**최종 갱신:** 2026-06-10
**영문 동기화:** `docs_eng/pipeline/05_normalization.md`는 동일 버전의 영문 번역본이다.

파이프라인 단계 ⑤는 원시 pose 좌표를 신체 상대 좌표계로 변환한다. 명시적으로 켠 경우에는
단안 pose의 일관된 관찰 편향을 줄이는 corrected-3D-hypothesis 후보 좌표와 burden report도
생성할 수 있다.

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
p_translated_i(t)  = p_i(t) - hip_center(t)
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
  model_depth_scale: 1.0
  corrected_3d_hypothesis:
    enabled: false
    output_family: corrected_3d_hypothesis
    downstream_coordinate_mode: norm
    feature_depth_gravity: 0.0
    report_burden_before_feature_use: true
    require_feature_domain_declaration: true
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

`corrected_3d_hypothesis.feature_depth_gravity`는 depth-derived 후보 evidence의 명시적 scoring
gate다. 기본값 `0.0`은 후보 좌표 계열을 review용으로 생성하더라도 corrected depth가 feature scoring에서
제외된다는 뜻이다. 이후 여러 recording과 여러 운동에서 sensitivity review가 feature별 burden threshold를
정의한 뒤에만 이 값을 높일 수 있다.

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
    "corrected_3d_hypothesis": {
        "enabled": bool,
        "output_family": str,
        "downstream_coordinate_mode": "norm" | "corrected_3d_hypothesis",
        "feature_depth_gravity": float,
        "used_for_features_or_scores": bool,
        "require_feature_domain_declaration": bool,
        "report_burden_before_feature_use": bool,
        "depth_evidence_policy": str,
    },
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

### 5.1 승격된 corrected-3D-hypothesis 후보 정책

p01 squat correction review는 ⑤ Normalization의 첫 formal corrected-3D-hypothesis candidate
policy를 확립했다. 여기서 승격은 candidate family, burden ledger, residual, readiness gate가
formal normalization artifact 요구사항이라는 뜻이다. 보정 좌표가 calibrated 3D, ground truth,
좋은 동작 template, 또는 scoring input이라는 뜻은 아니다.

현재 승격 stack:

```text
1. aggregate anthropometry 기반 common-subject skeleton envelope
2. reference-worthy frame 기반 within-session stable segment-memory table
3. squat closed-chain support context
4. recording-view-constrained skeleton placement: rv_skeleton_fit
5. bounded recording-view residual variant: rv_skeleton_fit_bounded_xy
6. visible-support mirrored anchor prior
7. bounded pre/post standing support-anchor blend
8. whole-video planted support temporal memory
9. scoring-readiness 및 bend-flip provenance gate
```

마지막으로 검토된 p01 candidate family는
`rv_skeleton_fit_bounded_xy_endpoint_blend_support_memory`였다. Public evaluation notebook은 아직
이 solver를 실행하지 않는다. Solver가 tested contract와 함께 `src/movement/`로 이관되기 전까지
후속 coordinate mode는 `norm`으로 유지한다.
검토 당시의 parameter value는 historical snapshot으로
`docs/pipeline/05_normalization_p01_squat_review_snapshot.md`에 보존한다.

Retired review-only 후보는 더 이상 active code/config branch로 남기지 않는다:

```text
paired target unification
strong segment projection
support-body corridor pull
support-locked 또는 knee-led support projection
support-width projection variants
lower-body knee-heading 및 knee-lane priors
foot-heading / toe-fixed adjustment templates
standalone support-height leveling
visual 또는 ideal symmetry templates
knee-over-foot 및 knee-bend templates
phase-specific norm blend
far-side decompression
post-correction smoothing
```

이들은 `docs_eng/`에서 연구 필요성을 정의하고, `docs/`를 동기화하고, config/report field를 추가하고,
여러 recording 또는 여러 운동에서 ON/OFF behavior를 비교한 뒤에만 다시 도입할 수 있다.

### 5.2 Corrected-3D-Hypothesis Solver 승격 Contract

이전 p01 correction solver를 `src/movement/`로 옮기기 전, 다음 최소 contract를 만족하는
report-first candidate generator로 구현해야 한다. 이는 solver contract이지 scoring contract가 아니다.

필수 input:

```text
norm_pose_df
  frame별 1행과 기존 <landmark>_norm_x/y/z column을 가진 DataFrame.
  raw와 base norm column은 read-only다.

landmarks
  pipeline run에서 사용한 ordered landmark name.

common_subject_skeleton_profile
  선택된 profile id, source matrix path, sex/bin provenance, segment target
  ratio. Height는 readable nominal length에만 사용할 수 있으며, 좌표를 cm 또는 m로 rescale하지 않는다.

exercise_support_context
  exercise id, kinetic chain, base of support, support surface, support-contact
  landmark, primary support pair, rep/phase/ready-window label.

solver_config
  source family, output family, correction cap, strength, visibility gate,
  support-width no-worsen guard, bend-side guard, report setting. p01 review 값은
  `05_normalization_p01_squat_review_snapshot.md`에 보존한다.
```

필수 output:

```text
corrected_candidate_df
  norm_pose_df와 같은 frame index 및 row order.
  candidate column은 additive only다. <landmark>_<output_family>_<axis> 같은
  family-specific convention은 result report가 정확한 coordinate-column map을 함께 제공할 때만 허용한다.

burden_ledger
  frame/stage/landmark 또는 segment 단위 correction burden table.

residual_report
  candidate 생성 전후 segment-length, support-width, support-surface, bend-side,
  visibility residual.

norm_vs_corrected_sensitivity_report
  corrected-3D-hypothesis 사용을 검토하는 feature별 comparison table.

readiness_provenance
  score-exclusion, availability, confidence, status, rejection reason.
```

Burden ledger는 최소 다음 field를 포함해야 한다:

```text
frame
rep_id 또는 phase label when available
candidate_family
stage
landmark_or_segment
axis
delta_torso_ratio
cap_torso_ratio
cap_fraction
residual_before_torso
residual_after_torso
accepted
rejection_reason
visibility_min
confidence
used_for_features_or_scores = false
```

Sensitivity report는 최소 다음 field를 포함해야 한다:

```text
feature_id
evaluation_domain
source_evidence
norm_value
corrected_candidate_value
delta
delta_abs
correction_burden
residual
availability
confidence
used_for_score = false
```

승격 gate:

```text
1. raw, norm, 기존 canon column은 절대 overwrite하지 않는다.
2. burden 및 residual report 없이 candidate를 만들지 않는다.
3. feature가 candidate를 소비하려면 evaluation_domain이 corrected_3d_hypothesis 또는
   dual_domain_compare로 선언되어야 한다.
4. feature_depth_gravity = 0.0인 동안 sensitivity report가 있어도 모든 corrected candidate는
   score-excluded다.
5. support width, bend-side consistency, support-surface plausibility 같은 configured hard residual
   gate를 악화시키는 correction step은 reject하거나 not_assessed로 둔다.
6. Trusted depth가 없을 때 impossible cap은 availability gate일 뿐이며 hidden correction target이 아니다.
7. Readiness는 feature별, recording별 판단이다. p01 review 성공이 다른 운동, camera view, participant의
   readiness를 뜻하지 않는다.
```

첫 module extraction의 최소 구현 목표:

```text
module path      src/movement/stages/corrected_3d_hypothesis.py
primary function build_corrected_3d_hypothesis_candidates(...)
return object    Corrected3DHypothesisResult
default mode     report_only, downstream_coordinate_mode = norm
first feature    candidate.support_width_stability sensitivity only
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
- 후속 feature는 보정 좌표를 사용하기 전에 `recording_view_only`,
  `corrected_3d_hypothesis`, 또는 `dual_domain_compare`를 선언해야 한다.
- `feature_depth_gravity = 0.0`인 동안 corrected-3D-hypothesis 좌표는 score에서 제외된다.
- Corrected-coordinate magnitude와 residual은 movement-quality 감점이 아니라
  data-confidence/provenance signal이다.
- ④ Preprocessing은 scale 계산 전에 reliability violation을 표시할 수 있지만, 신체 상대 척도화와
  canonical 후보 좌표 생성은 ⑤ Normalization의 책임이다.
- ⑨ Biomechanical Proxy는 정규화 좌표로 상대 CoM, moment-arm, load-shift proxy를 계산한다.
  이 단계로부터 절대 힘, 토크, calibrated physical distance를 추론하지 않는다.
- Corrected candidate 출력은 feature별 burden, residual, norm-vs-corrected sensitivity gate가
  문서화되기 전까지 후속 단계에서 사용하지 않는다.

---

## 8. 향후 확장 (Planned Extensions)

- Size Korea 8차 3D full-body automatic measurement source에서 Stage A aggregate-only engineering
  prior를 만든다.
- 비식별 row-level 3D full-body automatic measurements가 확보될 때만 row-level empirical prior를
  추가한다.
- visibility-weighted scale estimation과 torso-length outlier handling.
- exercise definition field 기반 운동별 canonicalization prior 선택.
- corrected coordinate를 scoring에 사용하거나 `feature_depth_gravity`를 `0.0`보다 높이기 전
  robustness evaluation.
- local config가 더 이상 의존하지 않으면 legacy `floor_relative_correction` key 점진 축소.
