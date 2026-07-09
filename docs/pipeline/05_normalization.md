# 05. 정규화 (Normalization)

**문서 버전:** 2.3.1
**최종 갱신:** 2026-07-09
**영문 동기화:** `docs_eng/pipeline/05_normalization.md`는 동일 버전의 영문 번역본이다.

파이프라인 단계 ⑤는 전처리 포즈 데이터를 정규화 포즈 데이터로 변환한다. 즉 전처리 포즈 데이터에
`norm`이라는 신체 기준 정규화 좌표 계열과 명시적인 depth-evidence metadata를 추가한다. 기본 작업은
평행이동과 척도 정규화만 수행한다. Pose backend는 MediaPipe처럼 x/y/z를 제공할 수도 있고,
YOLO pose처럼 x/y와 confidence만 제공할 수도 있다. 따라서 ① Validation은 2D backend를 위해
schema harmonization을 수행한다. 즉 raw z column이 없으면 `<landmark>_z`를 `NaN` placeholder로
추가해 이후 table shape를 xyz로 맞춘다. Placeholder z는 depth evidence가 아니며, provenance와
downstream gate를 통해 z 평가 여부와 분리해야 한다.

선택 analysis-space canonicalization은 이제 ⑤의 하위 단계로 취급한다. 모든 recording이
canonicalization을 통과해야 하는 것은 아니며, 통과하는 recording도 선택한 prior만 켤 수 있어야
하기 때문이다.

이 단계는 절대 힘, 절대 토크, calibrated 3D 위치, 절대 신체 치수를 추정하지 않는다. 이후
recording-view feature extraction과 선택 canonicalization filter가 사용할 안정적인 좌표 기반을
제공한다.

---

## 1. 파이프라인 위치 (Pipeline Position)

```text
Pose CSV
→ ① Validation
→ ② Annotation
→ ③ Exercise Definition
→ ④ Preprocessing
→ ⑤ Normalization          ← 본 단계
   └─ ⑤-1 Optional Canonicalization filters
→ ⑥ Segmentation
→ ⑦ Feature Extraction
→ ⑧ Biomechanical Proxy
→ ⑨ Biomarker Scoring
```

④ Preprocessing 이후에 실행된다. 신뢰도 낮은 hip/shoulder landmark가 척도 기준에 영향을 주기
전에 보정, 보간, 또는 표시되어야 하기 때문이다.

기존 독립 Canonicalization 단계는 ⑤의 선택 ⑤-1 branch로 편입한다. 병합 이후 후속 단계는
⑥ Segmentation, ⑦ Feature Extraction, ⑧ Biomechanical Proxy, ⑨ Biomarker Scoring으로
당겨 번호를 부여한다.

Stage-check notebook은 raw pose CSV를 직접 normalize하지 않고 전처리 포즈 데이터
(preprocessed pose data)를 normalize해야 한다. 또한 preprocessing provenance가 normalized output에도 보존되는지 확인해야 한다.
`preprocessing_valid`와 landmark별 usability/source column은 필수이고,
`preprocessing_confidence`는 ④에서 방출된 경우에 보존 여부를 확인한다.

Stage-check notebook은 앞 단계 노트북에서 쓰던 기존 양식을 따른다. 즉 `Data Setup`,
`Direct Normalization Test`, 번호가 붙은 check, `Pipeline Integration`, `Check Summary` 구조를
사용한다. Visualization은 normalized coordinate output을 직접 확인하는 경우 노트북에 둘 수 있다.

---

## 2. 기본 정규화 계약 (Base Normalization Contract)

안정적인 정규화 방식은 `hip_torso`다. Schema harmonization 이후 table shape는 xyz로 통일하지만,
z가 placeholder뿐인 경우 scale/evidence path는 여전히 recording-view xy일 수 있다.

```text
평행이동 기준 : 프레임별 골반 중심
척도 기준     : 시퀀스 단위 몸통 길이 중앙값
모델 depth gain: model_depth_scale, 기본 1.0 (finite model z가 있을 때만 적용)
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
torso_length_xy(t) = distance_xy(hip_center(t), shoulder_center(t))
torso_length_xyz(t)= distance_xyz(hip_center(t), shoulder_center(t))  # finite z evidence가 있을 때
s                  = median(valid torso_length_xy or torso_length_xyz)
p_norm_x_i(t)      = p_translated_x_i(t) / s
p_norm_y_i(t)      = p_translated_y_i(t) / s
p_norm_z_i(t)      = NaN                                             # z가 placeholder뿐일 때
p_norm_z_i(t)      = p_translated_z_i(t) * model_depth_scale / s     # finite model z가 있을 때
```

`model_depth_scale`은 단안 모델 depth에 대한 좌표 gain이며 camera calibration이 아니다. 기본값은
`1.0`이다. 검토 run에서는 model depth를 약화할 수 있지만, 반드시 report해야 하며 여전히
low-confidence evidence로 취급한다.

### 2.1 XYZ Schema Harmonization과 Z Evidence 계약

① Validation/schema harmonization은 preprocessing과 normalization 전에 좌표 table shape를
통일한다. YOLO-style 입력에 z가 없으면 누락된 `<landmark>_z` column을 `NaN`으로 추가한다.

```text
raw.shape_axes      = [x, y, z]
raw.observed_axes   = [x, y] 또는 [x, y, z]
raw.z_source        = absent | model_depth | partial_model_depth
raw.z_evaluable     = false | true
raw.z_fill_policy   = nan_placeholder | provided_by_backend
```

⑤ Normalization은 xyz schema를 유지하고 `*_norm_x/y/z`를 방출한다. Raw z가 `NaN` placeholder뿐이면
`*_norm_z`도 `NaN`으로 유지하고, `normalized_evidence_axes=[x,y]`, `z_evaluable=false`로 보고한다.
이때 z를 0으로 채우지 않는다. 0으로 채운 z는 실제 관측 depth처럼 downstream feature가 잘못 사용할
위험이 있기 때문이다.

```text
2D 입력  : <landmark>_x, <landmark>_y, <landmark>_confidence 또는 confidence
2D harmonized 입력 : <landmark>_x, <landmark>_y, <landmark>_z = NaN
2D 정규화 출력     : <landmark>_norm_x, <landmark>_norm_y, <landmark>_norm_z = NaN
3D 입력  : <landmark>_x, <landmark>_y, <landmark>_z, <landmark>_confidence
3D 출력  : <landmark>_norm_x, <landmark>_norm_y, <landmark>_norm_z
```

2D 입력에서도 hip/shoulder 기반 신체 상대 좌표와 torso-length ratio는 만들 수 있다. 다만
depth-sensitive feature는 `norm`만으로 scoring-ready가 될 수 없고, ⑤-1 Canonicalization에서
별도의 `canonical_depth_hypothesis` 또는 `canon` analysis evidence와 confidence, `quality_gravity` 요약이
생성된 경우에만 analysis evidence로 검토한다. Raw residual/burden 진단값은 canonicalization report
또는 audit export에 둔다.

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

Table state 용어는 다음처럼 일관되게 사용한다.

```text
전처리 포즈 데이터 = raw pose coordinates + observation confidence + preprocessing provenance
정규화 포즈 데이터 = 전처리 포즈 데이터 + body-relative norm coordinates + depth-evidence metadata
```

`preprocessed pose data`는 좌표 계열 이름이 아니라 ④ output table 상태다. ⑤는 그 table state
위에 `norm` 좌표 계열을 추가한다.

`canon` 및 corrected-3D-hypothesis analysis-space 좌표 계열은 ⑤-1의 선택 canonicalization output이며
`raw`나 `norm`을 대체하지 않는다.

---

## 3. 설정 계약 (Configuration Contract)

상세 기본값은 `configs/pipeline_default.yaml`에 둔다. 안정적인 ⑤ 계약은 다음과 같다.

```yaml
normalization:
  enabled: true
  method: hip_torso
  coordinate_axes: auto  # auto | xy | xyz; table shape가 아니라 z evidence 사용 여부를 선택
  keep_reference_columns: true
  model_depth_scale: 1.0
  canonicalization:
    enabled: false
    coordinate_mode: norm
    output_prefix: canon
    report_only: true
    downstream_coordinate_mode: norm
    support_plane_alignment:
      enabled: false
    movement_plane_alignment:
      enabled: false
    protocol_height_lateral_width_alignment:
      enabled: false
    xy_depth_lift:
      enabled: false
      method: recording_view_depth_hypothesis
    anthropometric_skeleton_prior:
      enabled: false
    corrected_3d_hypothesis:
      enabled: false
```

중첩된 `normalization.canonicalization` block을 표준 설정 표면으로 사용한다. 기존 root-level
`canonicalization` block은 기존 config와 notebook을 위한 하위 호환 alias로 유지한다.

`coordinate_axes: auto`는 finite z evidence가 scale과 z normalization에 참여할지 선택한다.
Table shape는 ① harmonization 이후 xyz로 유지된다. 명시적으로 `xy`를 지정하면 z column이 있어도
z를 non-evaluable로 유지한다. 명시적으로 `xyz`를 지정하면 finite z evidence가 필요하며, z가
placeholder뿐이면 실패해야 한다.

⑤ Normalization은 score-policy weight 또는 final-score contribution을 할당하지 않는다. 이후 단계가
사용할 좌표 척도와 model-depth gain만 노출한다. 선택 canonicalization은 evidence availability,
confidence, `quality_gravity`, norm-vs-analysis sensitivity를 노출할 수 있으며, raw correction
burden과 residual 진단값은 canonicalization report에 둔다.

후속 단계에는 하나의 "신뢰된" 좌표 stream이 아니라 정규화 포즈 데이터를 넘긴다. 실제 구성은
전처리 table을 보존하고, `norm` 좌표 계열을 추가하며, z가 finite backend model depth인지
placeholder뿐인지 depth-evidence metadata로 기록한 상태다. 이후 feature extraction과 scoring은
availability, confidence, `quality_gravity`, norm-vs-analysis sensitivity를 사용해 각 좌표
계열이 feature와 score에 얼마나 기여할지 결정한다. Raw burden/residual 값은 review/audit 맥락에서만
해석한다. 이는 ① structural validation을 사후에 바꾸는 의미가 아니라, downstream feature
availability와 score contribution을 gate하는 의미다.

---

## 4. 선택 Canonicalization 하위 단계 (Optional Canonicalization Substage)

Canonicalization은 ⑤ 아래의 opt-in branch다. `norm` 좌표를 입력으로 받아 `canon` 또는
corrected-3D-hypothesis analysis-space 좌표 계열을 추가할 수 있다. `norm_z`가 placeholder인 경우에도
⑤-1은 별도 `xy_depth_lift` prior를 통해 `canon_z`를 채울 수 있다. 이 z는 관측 depth가 아니라
canonical depth hypothesis다. 이렇게 YOLO-style data도 MediaPipe-style xyz data와 구조적으로
비교 가능해지지만, depth 평가는 이후 정책이 승격할 때까지 비활성으로 둔다.

```text
raw      원본 pose 좌표
norm     ⑤의 hip-torso 정규화 좌표
canon    ⑤-1의 선택 analysis-space 좌표
```

각 prior는 독립적으로 켜고 끌 수 있다. 어떤 recording은 canonicalization을 전혀 쓰지 않을 수
있고, 어떤 recording은 `support_plane_alignment`만, 또 다른 recording은
`protocol_height_lateral_width_alignment`만 또는 검토된 prior 조합만 사용할 수 있다.

```yaml
normalization:
  canonicalization:
    enabled: true
    support_plane_alignment:
      enabled: true
    movement_plane_alignment:
      enabled: false
    protocol_height_lateral_width_alignment:
      enabled: false
    xy_depth_lift:
      enabled: true
      method: recording_view_depth_hypothesis
    corrected_3d_hypothesis:
      enabled: false
```

`report_only: true`는 analysis-space column과 `canonicalization_report`를 만들 수 있지만, 후속 단계는
기본적으로 계속 `norm`을 사용한다는 뜻이다. `downstream_coordinate_mode: canon`으로 승격하려면
노트북 검토, robustness 근거, 명시적 문서 갱신이 선행되어야 한다.

세부 canonicalization reference는 역사적 문서인 [05_1_canonicalization.md](05_1_canonicalization.md)에
남긴다. 다만 더 이상 필수 독립 파이프라인 단계는 아니다.

## 5. 리포트 계약 (Report Contract)

`normalize_pose_by_hip_torso(df, landmarks)`는 정규화된 DataFrame과 report를 반환한다.

```python
{
    "method": str,
    "input_pose_data_state": "preprocessed_pose_data" | str,
    "output_pose_data_state": "normalized_pose_data",
    "input_coordinate_families": list[str],
    "output_coordinate_families": list[str],
    "input_coordinate_axes": dict[str, list[str]],
    "output_coordinate_axes": dict[str, list[str]],
    "added_coordinate_family": "norm",
    "normalized_axes": ["x", "y", "z"],
    "normalized_evidence_axes": ["x", "y"] | ["x", "y", "z"],
    "z_axis_policy": "nan_placeholder" | "preserved_model_depth",
    "z_source": "absent" | "model_depth" | "partial_model_depth",
    "z_evaluable": bool,
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
normalized_axes
normalized_evidence_axes
z_axis_policy
z_evaluable
```

기본 normalization report는 corrected-coordinate readiness, score-policy weight, final-score contribution
flag를 포함하지 않는다. ⑤-1가 활성화된 경우 pipeline report에 `report["canonicalization"]`이
추가되며, 여기에는 evidence availability, confidence, `quality_gravity`, active prior, skipped-prior
reason, report-local correction burden/residual 진단값이 들어간다.

---

## 6. 후속 단계 규칙 (Downstream Rules)

- ⑤-1 Canonicalization은 `norm` 좌표를 입력으로 받아 `canon` 또는 corrected-3D-hypothesis analysis evidence
  좌표 계열을 추가할 수 있다.
- placeholder `norm_z`를 가진 입력은 ⑥ 이후 recording-view feature에는 사용할 수 있다.
  Depth-sensitive feature는 finite z evidence와 `z_evaluable`을 확인해야 하며, ⑤-1 analysis evidence가
  명시적으로 승격되지 않으면 `not_assessed` 또는 withheld로 남긴다.
- ⑥ Segmentation, ⑦ Feature Extraction, ⑧ Biomechanical Proxy, ⑨ Biomarker Scoring은 기본적으로
  `norm` 좌표를 소비한다.
- 후속 feature가 ⑤-1의 analysis-space 좌표를 사용하려면 먼저 `recording_view_only`,
  `corrected_3d_hypothesis`, 또는 `dual_domain_compare` 평가 domain을 선언해야 한다.
- ⑤는 단안 depth 오류를 숨기지 않는다. 운동 시작 전 raw/model depth가 불안정하면 그 불안정성은
  `norm`에도 남는다. ⑤-1는 analysis evidence를 low confidence 또는 not available로 표시할 수 있다.
- ⑧ Biomechanical Proxy는 normalized coordinate로 상대 CoM, moment-arm, load-shift proxy를 계산한다.
  이 단계에서 절대 force, torque, calibrated physical distance를 추론해서는 안 된다.

---

## 7. 계획된 확장 (Planned Extensions)

- confidence-weighted scale estimation과 torso-length outlier 처리.
- 운동 prior를 ⑤로 옮기지 않는 범위에서 운동별 normalization parameter review.
- Depth-sensitive downstream policy에 nonzero score-policy weight를 부여하기 전 `model_depth_scale`
  sensitivity robustness 평가.
- YOLO/2D pose backend를 위한 xyz schema harmonization을 안정화하면서 `xy_depth_lift`와
  depth-evaluation gate를 정교화한다.
