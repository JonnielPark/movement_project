# 05-1. Canonicalization

**문서 버전:** 2.3.1
**최종 갱신:** 2026-07-09
**영문 동기화:** `docs_eng/pipeline/05_1_canonicalization.md`는 동일 버전의 영문 번역본이다.

Canonicalization은 더 이상 필수 독립 파이프라인 단계가 아니다.
[05_normalization.md](05_normalization.md)의 선택 ⑤-1 하위 단계이며, ⑤ Normalization에서 생성한
`norm` 좌표를 입력으로 받아 `canon` 또는 `corrected_3d_hypothesis` 같은 analysis-space 좌표
계열을 추가할 수 있다. 이 문서는 선택 filter와 provenance 계약을 보존하는 상세 reference로
유지한다.

이 단계는 절대 힘, 절대 토크, calibrated 3D, 절대 신체 치수를 추정하지 않는다. 좋은 동작
template에 pose를 맞추지도 않는다. 후속 feature/scoring policy가 명시적으로 선언하기 전까지
기본 downstream coordinate mode는 `norm`으로 유지한다.

**현재 상태:** ⑤ Normalization 아래의 선택 ⑤-1 canonicalization filter로 병합했다. root-level YAML
key `canonicalization`은 하위 호환 alias로만 유지하며, 새 config는
`normalization.canonicalization`을 사용한다.

---

## 1. 파이프라인 위치 (Pipeline Position)

```text
Pose CSV
→ ① Validation
→ ② Annotation
→ ③ Exercise Definition
→ ④ Preprocessing
→ ⑤ Normalization
   └─ ⑤-1 Optional Canonicalization filters       ← 이 reference
→ ⑥ Segmentation
→ ⑦ Feature Extraction
→ ⑧ Biomechanical Proxy
→ ⑨ Biomarker Scoring
```

⑤ Normalization 이후에 실행된다. 모든 prior는 이미 생성된 신체 상대 좌표 계열 위에서 작동한다.
`raw`와 `norm` column은 보존하고 analysis-space column만 추가해야 한다.

---

## 2. 입력 및 좌표 계열 계약 (Input And Coordinate-Family Contract)

필수 입력은 정규화 포즈 데이터다. 즉 전처리 포즈 데이터에 ⑤의 신체 기준 `norm` 좌표 계열과
depth-evidence metadata가 추가된 상태를 입력으로 받는다. ① schema harmonization과 ⑤
Normalization 이후 `norm`은 xyz column shape를 갖는 것을 목표로 한다. 중요한 구분은
`norm_z`가 finite depth evidence를 담는지, 아니면 `NaN` placeholder뿐인지다.

원시 좌표는 절대 덮어쓰지 않는다.

```text
left_knee_x       원본 x
left_knee_norm_x  ⑤의 기본 정규화 x
left_knee_canon_x ⑤-1의 선택 canonical analysis evidence x
left_knee_canon_z ⑤-1의 선택 canonical depth hypothesis z
```

좌표 계열의 의미는 고정한다.

```text
raw      원본 pose 좌표
norm     ⑤의 hip-torso 정규화 좌표
canon    ⑤-1의 선택 analysis-space 좌표
```

Canonicalization output은 다음처럼 canonicalized pose data로 설명한다.

```text
Canonicalized pose data = 정규화 포즈 데이터 + analysis-space 좌표 + analysis-evidence report
```

`norm_z`가 placeholder인 경우 ⑤-1은 `xy_depth_lift` 같은 prior가 명시적으로 켜져 있을 때만
`canon_z` analysis evidence를 채울 수 있다. 이때 `canon_z`는 관측 depth가 아니라 canonical depth hypothesis다.
향후 corrected-3D-hypothesis 좌표 계열도 같은 additive rule을 따른다. 예를 들어
`<landmark>_<output_family>_<axis>` 형식을 사용할 수 있다. analysis-space column은 `norm`을 대체해서는
안 된다.

---

## 3. 설정 계약 (Configuration Contract)

상세 기본값은 `configs/pipeline_default.yaml`에 둔다. 안정적인 ⑤-1 설정 계약은
`normalization` 아래에 중첩한다.

```yaml
normalization:
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
    xy_depth_lift:
      enabled: false
      method: recording_view_depth_hypothesis
    anthropometric_skeleton_prior: ...
    corrected_3d_hypothesis:
      enabled: false
      output_family: corrected_3d_hypothesis
      downstream_coordinate_mode: norm
      emit_sensitivity_report: true
      support_pair: [left_ankle, right_ankle]
      report_burden_before_feature_use: true
      require_feature_domain_declaration: true
```

`report_only: true`는 `canon` 좌표와 report를 만들 수 있지만 후속 단계가 계속 `norm` 좌표를
소비한다는 뜻이다. `downstream_coordinate_mode`를 `canon`으로 바꾸려면 노트북 검토, robustness
근거, 명시적 문서 갱신이 선행되어야 한다.

`floor_relative_correction`은 local 또는 legacy config에 남아 있을 수 있다. 이는
`support_plane_alignment`의 하위 호환 alias로 취급하며, 새 작업에서는 canonicalization key를
우선 사용한다.

⑤-1 Canonicalization은 score-policy weight 또는 final-score contribution을 할당하지 않는다.
Corrected-depth 및 canonicalization analysis evidence는 availability, confidence, `quality_gravity`,
norm-vs-analysis sensitivity 같은 evidence 요약만 노출한다. Raw residual과 correction burden은
report-local 진단값으로 둔다. 현재 개발 정책은 ⑨에서 corrected-depth score contribution을 0으로
유지하지만, 이를 ⑤-1 output field로 encode하지 않는다.

---

## 4. 리포트 계약 (Report Contract)

`apply_canonicalization(df, landmarks, config)`는 additive analysis-space column이 포함된 DataFrame과
`canonicalization_report`를 반환한다.

```python
{
    "enabled": bool,
    "evidence_available": bool,
    "evidence_confidence": "not_available" | "high" | "moderate" | "low",
    "quality_gravity": float,
    "burden_level": "none" | "low" | "moderate" | "high",
    "input_pose_data_state": "normalized_pose_data" | str,
    "output_pose_data_state": "canonicalized_pose_data" | str,
    "input_coordinate_families": list[str],
    "output_coordinate_families": list[str],
    "input_coordinate_axes": dict[str, list[str]],
    "output_coordinate_axes": dict[str, list[str]],
    "added_coordinate_family": "canon" | str | None,
    "coordinate_mode": "norm",
    "output_prefix": "canon",
    "report_only": bool,
    "downstream_coordinate_mode": "norm" | "canon",
    "status": "disabled" | "skipped" | "applied" | "partial" | "rejected",
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
        "xy_depth_lift": dict | None,
        "anthropometric_skeleton_prior": dict | None,
    },
}
```

Public canonicalization summary는 `evidence_available`, `evidence_confidence`,
`quality_gravity`를 우선 사용한다. `burden_level`은 review를 위한 report-local diagnostic summary이며
필수 downstream payload field가 아니다. Legacy `status`와 prior-level status는 이전 report 해석과
debugging/provenance를 위해 남기지만, prototype review 이후의 primary readiness surface로 쓰지 않는다.
Score-policy weight와 final-score contribution flag는 ⑤-1 Canonicalization report에서 의도적으로 제외한다.

일상적인 노트북 review에서는 prior count보다 prior evidence table을 보여준다. 이 table은
`canonicalization_report.prior_reports`와 active `CanonicalizationConfig`에서 만든다:

```text
prior_id
configured_on
evidence_available
reason
key_metric
```

`evidence_confidence`, `quality_gravity`, `burden_level`은 prior별 row가 아니라 전체 canonicalization
evidence summary에 속한다. Prior evidence table에서는 이를 제외해 prior별 confidence나 burden
score가 따로 계산된 것처럼 보이지 않게 한다.

`configured_on`은 각 prior config의 `enabled` flag에서 가져온다. `evidence_available`은 prior report
status가 `applied` 또는 `warning`이면 true다. `reason`은 짧은 사람이 읽을 수 있는 status 또는
confidence-note summary다. `key_metric`은 support anchor frame, movement rotation/residual, protocol
camera height match처럼 prior별 가장 중요한 diagnostic을 노출한다. Prior count는 full provenance에서
계산할 수 있지만 primary review surface로 쓰지 않는다.

`data_confidence.level`은 movement-quality score가 아니다. 낮은 confidence는 자동 감점이 아니라
주의, withheld, provenance로 표현한다.

Stage-check notebook은 앞 단계 노트북에서 쓰던 기존 양식을 따른다. 즉 `Data Setup`,
`Direct Canonicalization Test`, 번호가 붙은 check, `Pipeline Integration`, `Check Summary`
구조를 사용한다. setup은 ⑤ Normalization에서 사용한 previous-stage input chain과 동일하게
validation, annotation, exercise definition loading, preprocessing, normalization을 준비해야 한다.
Canonicalization은 raw pose를 단독으로 normalization한 DataFrame이 아니라, preprocessing
validity/usability provenance가 보존된 normalized preprocessed pose data 위에서 검증해야 한다.

Stage-check notebook의 시각화는 compact하게 유지한다. Pose 확인에는 normalized vs canonical
비교 하나면 충분하며, residual, correction magnitude, prior-specific evidence를 직접 보여주는 경우에만
별도 diagnostic plot을 둔다.

---

## 5. Canonicalization 계약 (Canonicalization Contract)

Canonicalization은 선택 기능이며 기본 비활성화 상태다. 이는 calibrated 3D reconstruction도,
좋은 동작 template fitting도 아니다. 역할은 raw/norm 좌표를 보존한 채 일관된 관찰 편향을
완화하고, knee valgus, heel lift, trunk lean, pelvis rotation 같은 실제 보상 패턴을 남기는 것이다.

현재 활성 또는 계획 prior:

| Prior | 상태 | 목적 | 보호선 |
|---|---|---|---|
| `xy_depth_lift` | 계획됨, 기본 비활성 | YOLO 등 2D pose backend처럼 `norm_z`가 placeholder뿐인 경우 `norm_x/y`에서 `canon_z` analysis evidence를 채우는 recording-view constrained depth hypothesis. | 3D 복원, measured depth, subject-specific skeleton fitting이 아니며 score-policy weight를 만들지 않는다. |
| `support_plane_alignment` | 구현됨, 기본 비활성 | 접지 landmark 기반 pose 내부 pseudo-floor/support-plane 검토. 기존 `floor_relative_correction` 로직을 감싼다. | 발을 바닥에 고정하지 않으며 camera calibration이 아니다. |
| `movement_plane_alignment` | prototype, 기본 비활성 | hip-knee-ankle 주 운동 방향을 이용한 수직축 기준 capped rigid rotation. | out-of-plane residual을 보존해 보상 움직임 검토에 남긴다. |
| `protocol_height_lateral_width_alignment` | prototype, 기본 비활성 | H1/H2/H3 body anchor 주변의 보수적 lateral-width attenuation 전에 camera-height metadata를 gate로 사용한다. | 기본 score contribution이 0인 analysis evidence이며 렌즈 보정, reprojection, far-side 좌표 생성이 아니다. |
| `anthropometric_skeleton_prior` | 계획됨, 기본 비활성 | 느슨한 신체 분절 길이 plausibility range를 단안 depth 검토용 engineering envelope로 사용한다. | raw row-level 자료 전에는 경험적 P5/P95가 아니며 skeleton template fitting이 아니다. |

현재 prior 순서:

```text
1. xy_depth_lift
2. support_plane_alignment
3. movement_plane_alignment
4. protocol_height_lateral_width_alignment
5. anthropometric_skeleton_prior
```

`xy_depth_lift`는 finite `norm_z` evidence가 없을 때만 필수 analysis prior가 될 수 있다. MediaPipe-style
입력처럼 finite model-depth `norm_z`가 있는 경우에는 기본 비활성으로 두거나 sensitivity 비교에만
사용할 수 있다.

### 5.1 XY Depth Lift evidence contract

`xy_depth_lift`의 기본 method는 `recording_view_depth_hypothesis`다. 목적은 2D recording-view
좌표를 calibrated 3D로 복원하는 것이 아니라, 후속 depth-sensitive feature가 왜 withheld 또는
low confidence인지 설명할 수 있는 분석용 analysis z evidence와 provenance를 만드는 것이다.

필수 입력:

```text
norm_pose_df
  <landmark>_norm_x/y/z column을 가진 DataFrame. backend가 z를 제공하지 않은 경우
  <landmark>_norm_z는 NaN placeholder일 수 있다.

landmarks
  pipeline run에서 사용한 ordered landmark name.

exercise_context
  운동 id, kinetic chain, support landmarks, support pair, movement plane, camera protocol.

depth_prior_config
  segment prior source, correction cap, temporal smoothness, confidence gate,
  near/far side sign policy, rejection rule.
```

기본 생성 규칙:

```text
1. canon_x/y는 norm_x/y를 복사한다.
2. 분절별 recording-view 길이 d_xy를 계산한다.
3. 느슨한 분절 길이 target 또는 envelope가 있고 d_xy가 envelope 안에 있으면
   dz_abs analysis evidence를 sqrt(max(target_length^2 - d_xy^2, 0))로 계산할 수 있다.
4. z 부호는 임의로 정하지 않는다. Near/far side evidence, support contact, 이전/이후
   stable-frame memory처럼 문서화된 sign prior가 있을 때만 부호를 배정한다.
5. d_xy가 이미 target/envelope보다 크면 z를 발명해서 맞추지 않고
   `projected_length_exceeds_prior`로 reject한다.
6. temporal continuity와 correction cap을 통과하지 못한 frame/segment는 evidence unavailable로 둔다.
```

필수 output:

```text
<landmark>_canon_x/y/z
canonical_depth_hypothesis_available
canonical_depth_hypothesis_confidence
canonical_depth_hypothesis_quality_gravity
canonical_depth_hypothesis_rejection_reason
```

Report-local burden/residual 진단값은 최소 다음 항목을 포함한다:

```text
frame
landmark_or_segment
source_axes = xy
target_axes = xyz
d_xy_torso_ratio
target_length_torso_ratio
analysis_dz_torso_ratio
cap_torso_ratio
cap_fraction
residual_before_torso
residual_after_torso
accepted
rejection_reason
confidence
used_for_features_or_scores = false
```

`xy_depth_lift` output은 analysis evidence다. ⑥ 이후 feature가 이 analysis z evidence를 사용하려면
`evaluation_domain = canonical_depth_hypothesis` 또는 `dual_domain_compare`를 선언해야 하며,
⑨ Scoring에서 별도 score-policy weight가 승격되기 전까지 기본 composite score에는 기여하지 않는다.

### 5.2 승격된 corrected-3D-hypothesis analysis evidence 정책

p01 squat correction review는 ⑤-1 Canonicalization의 첫 formal corrected-3D-hypothesis review
policy를 확립했다. 여기서 승격은 coordinate family, quality summary, burden ledger, residual
진단값, readiness gate가 formal canonicalization artifact 요구사항이라는 뜻이다. 보정 좌표가
calibrated 3D, ground truth, 좋은 동작 template, 또는 scoring input이라는 뜻은 아니다.

현재 승격 stack:

```text
1. aggregate anthropometry 기반 common-subject skeleton envelope
2. reference-worthy frame 기반 within-session stable segment-memory table
3. squat closed-chain support context
4. recording-view-constrained skeleton placement: rv_skeleton_fit
5. bounded recording-view residual variant: rv_skeleton_fit_bounded_xy
6. visible-support mirrored anchor prior
7. bounded pre/post standing support-landmark blend
8. whole-video planted support temporal memory
9. scoring-readiness 및 bend-flip provenance gate
```

마지막으로 검토된 p01 coordinate family는
`rv_skeleton_fit_bounded_xy_endpoint_blend_support_memory`였다. Public evaluation notebook은 아직
이 solver를 실행하지 않는다. Solver가 tested contract와 함께 `src/movement/`로 이관되기 전까지
후속 coordinate mode는 `norm`으로 유지한다.
검토 당시의 parameter value는 historical snapshot으로
`docs/pipeline/05_1_canonicalization_p01_squat_review_snapshot.md`에 보존한다.

retired tuning branch는 더 이상 active code/config branch로 남기지 않는다:

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

### 5.3 Corrected-3D-Hypothesis Solver 승격 Contract

이전 p01 correction solver를 `src/movement/`로 옮기기 전, 다음 최소 contract를 만족하는
report-first analysis-evidence generator로 구현해야 한다. 이는 solver contract이지 scoring contract가 아니다.

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
  exercise id, kinetic chain, base of support, support surface, support landmark
  landmark, primary support pair, rep/phase/ready-window label.

solver_config
  source family, output family, correction cap, strength, confidence gate,
  support-width no-worsen guard, bend-side guard, report setting. p01 review 값은
  `05_1_canonicalization_p01_squat_review_snapshot.md`에 보존한다.
```

필수 output:

```text
analysis_coordinate_df
  norm_pose_df와 같은 frame index 및 row order.
  analysis-space column은 additive only다. <landmark>_<output_family>_<axis> 같은
  family-specific convention은 result report가 정확한 coordinate-column map을 함께 제공할 때만 허용한다.

burden_ledger
  frame/stage/landmark 또는 segment 단위 correction burden table.

residual_report
  analysis-evidence 생성 전후 segment-length, support-width, support-surface, bend-side,
  confidence residual.

norm_vs_corrected_sensitivity_report
  corrected-3D-hypothesis 사용을 검토하는 feature별 comparison table.

readiness_provenance
  evidence availability, confidence, status, rejection reason.
```

Burden ledger는 최소 다음 field를 포함해야 한다:

```text
frame
rep_id 또는 phase label when available
coordinate_family
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
confidence_min
confidence
used_for_features_or_scores = false
```

Sensitivity report는 최소 다음 field를 포함해야 한다:

```text
feature_id
evaluation_domain
source_evidence
norm_value
corrected_value
delta
delta_abs
correction_burden
residual
availability
confidence
quality_gravity
```

승격 gate:

```text
1. raw, norm, 기존 canon column은 절대 overwrite하지 않는다.
2. burden 및 residual report 없이 analysis evidence를 만들지 않는다.
3. feature가 analysis evidence를 소비하려면 evaluation_domain이 corrected_3d_hypothesis 또는
   dual_domain_compare로 선언되어야 한다.
4. Canonicalization은 score-policy weight 또는 final-score contribution을 결정하지 않는다.
   이후 scoring policy가 사용할 analysis evidence만 emit한다.
5. support width, bend-side consistency, support-surface plausibility 같은 configured hard residual
   gate를 악화시키는 correction step은 reject하거나 not_assessed로 둔다.
6. Trusted depth가 없을 때 impossible cap은 availability gate일 뿐이며 hidden correction target이 아니다.
7. Readiness는 feature별, recording별 판단이다. p01 review 성공이 다른 운동, camera view, participant의
   readiness를 뜻하지 않는다.
```

첫 module extraction의 최소 구현 목표:

```text
module path      src/movement/stages/corrected_3d_hypothesis.py
primary function build_corrected_3d_hypothesis_evidence(...)
return object    Corrected3DHypothesisResult
default mode     analysis evidence only, downstream_coordinate_mode = norm
first feature    analysis.support_width_stability sensitivity only
```

### 5.4 첫 Sensitivity Target: `analysis.support_width_stability`

첫 code-backed sensitivity target은 support width stability의 analysis-evidence comparison이다. 이는
corrected coordinate를 생성하지 않는다. 기존 analysis-space coordinate family와 base `norm` family를 비교만
한다.

정의:

```text
support_pair          기본 left_ankle, right_ankle
norm_width(t)         norm axes [x, y]에서 support_pair 사이 거리
analysis_width(t)    coordinate axes [x, y, z]에서 support_pair 사이 거리
stability_value       P95(width) - P05(width), torso-length ratio
delta                 analysis_stability_value - norm_stability_value
```

`norm` 값은 의도적으로 recording-plane axis만 사용한다. Analysis-space 값은 model-depth 또는
corrected-depth axis를 포함할 수 있지만, 여전히 low-confidence corrected-3D-hypothesis evidence다.
Analysis-space coordinate column이 없으면 feature는 `not_assessed`다. 이 함수 자체가 analysis evidence를 만들면
안 된다.

필수 output row:

```text
feature_id = analysis.support_width_stability
evaluation_domain = corrected_3d_hypothesis
source_evidence = norm support-pair width versus existing coordinate family
norm_value
corrected_value
delta
delta_abs
correction_burden
residual
availability
confidence
quality_gravity
```

`quality_gravity`는 row의 downstream trust summary다. `correction_burden`과 residual 세부값은 가능하면
제공된 burden ledger와 비교 residual에서 가져오는 report-local diagnostic이다. Analysis-space column이 있어도
ledger가 없으면 row는 `low_confidence`다. Burden이 높거나 값이 finite하지 않으면 low-confidence
analysis evidence로 유지하고, availability를 `low_confidence` 또는 `not_assessed`로 낮출 수 있다.

### 5.5 Pipeline Review Surface

`canonicalization.corrected_3d_hypothesis.enabled = true`이고 `emit_sensitivity_report = true`이면
`run_pipeline`은 top-level report block을 emit한다:

```python
{
    "corrected_3d_hypothesis_review": {
        "num_analysis_rows": int,
        "num_burden_rows": int,
        "residual_report": dict,
        "norm_vs_corrected_sensitivity_report": list[dict],
        "num_sensitivity_rows": int,
        "readiness_provenance": {
            "status": "analysis_evidence",
            "used_for_features_or_scores": False,
            "downstream_coordinate_mode": "norm",
        },
    }
}
```

이 block은 analysis-evidence surface다. `df`, downstream coordinate mode, feature extraction,
biomechanical proxy, biomarker record, 최종 score를 바꾸면 안 된다. 설정된 coordinate family column이
없으면 sensitivity row는 `not_assessed`로 emit하여 report에서 이유가 보이게 한다. Score-policy weight는
이후 scoring policy로 의도적으로 미룬다.

### 5.6 Multi-Recording / Multi-Exercise Sensitivity Surface

Multi-recording review는 이미 생성된 pipeline report를 모으는 것에서 시작한다. Aggregation helper는
`corrected_3d_hypothesis_review` block을 읽고 grouped analysis-evidence row를 반환한다.
필수 grouping field:

```text
feature_id
exercise_id
n_recordings
n_rows
n_assessed
n_low_confidence
n_not_assessed
median_norm_value
median_corrected_value
median_delta_abs
max_correction_burden
median_quality_gravity
```

Summary는 feature가 최종 score에 영향을 주어야 하는지 결정하지 않는다. 충분한 recording이 있어
stability, availability, `quality_gravity`, report-local burden 진단값, norm-vs-analysis sensitivity를
검토할 수 있는지만 보여준다. Nonzero score-policy weight 할당은 여러 recording과 여러 운동에서
이 summary를 검토한 뒤의 scoring-policy 작업으로 보류한다.

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
- bounded하고 작은 경우에만 analysis depth residual evidence 생성
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
| Stage A | file design + aggregate statistics | aggregate ratio 주변의 conservative engineering range | plausibility flag, low-confidence marking, analysis residual evidence |
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

Prior는 다음 조건을 모두 만족할 때만 `canon` analysis-space 좌표를 만들 수 있다:

```text
1. 해당 segment가 prior에 존재
2. x/y evidence 자체가 plausible range를 이미 위반하지 않음
3. bounded depth residual로 segment를 loose range 안으로 가져올 수 있음
4. correction magnitude가 config cap 이하
5. landmark confidence와 swap-risk gate가 review를 허용
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
analysis_corrections
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

- ⑥ Segmentation, ⑦ Feature Extraction, ⑧ Biomechanical Proxy, ⑨ Biomarker Scoring은 기본적으로
  `norm` 좌표를 소비한다.
- 후속 feature는 보정 좌표를 사용하기 전에 `recording_view_only`,
  `corrected_3d_hypothesis`, 또는 `dual_domain_compare`를 선언해야 한다.
- Corrected-3D-hypothesis 좌표는 ⑤-1 안에서 analysis evidence로 남긴다. 이후 scoring policy가
  score-policy weight를 결정하며, 현재 개발 계획은 그 단계에서 corrected-depth contribution을 0으로 유지한다.
- Corrected-coordinate magnitude와 residual은 movement-quality 감점이 아니라
  data-confidence/provenance signal이다.
- ④ Preprocessing은 scale 계산 전에 reliability violation을 표시할 수 있지만, 신체 상대 척도화는
  ⑤ Normalization의 책임이고 canonical analysis-space 좌표 생성은 ⑤-1 Canonicalization의 책임이다.
- ⑧ Biomechanical Proxy는 정규화 좌표로 상대 CoM, moment-arm, load-shift proxy를 계산한다.
  이 단계로부터 절대 힘, 토크, calibrated physical distance를 추론하지 않는다.
- Corrected analysis-space 출력은 feature별 `quality_gravity`, report-local burden/residual 진단값,
  norm-vs-corrected sensitivity gate가 문서화되기 전까지 후속 단계에서 사용하지 않는다.

---

## 8. 향후 확장 (Planned Extensions)

- Size Korea 8차 3D full-body automatic measurement source에서 Stage A aggregate-only engineering
  prior를 만든다.
- 비식별 row-level 3D full-body automatic measurements가 확보될 때만 row-level empirical prior를
  추가한다.
- confidence-weighted scale estimation과 torso-length outlier handling.
- exercise definition field 기반 운동별 canonicalization prior 선택.
- corrected coordinate가 이후 scoring policy에서 nonzero score-policy weight를 받기 전 robustness evaluation.
- local config가 더 이상 의존하지 않으면 legacy `floor_relative_correction` key 점진 축소.

