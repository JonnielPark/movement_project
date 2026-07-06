# 10. 바이오마커 점수화 (Biomarker Scoring)

**문서 버전:** 1.6.2
**최종 갱신:** 2026-07-07
**영문 동기화:** `docs_eng/pipeline/10_biomarker_scoring.md`는 동일 버전의 영문 번역본이다.

파이프라인 단계 ⑩은 ⑧ `FeatureRecord`와 ⑨ `BiomechRecord`를 해석 가능한 biomarker record로
감싸고, baseline이 있을 때 반복별 movement-quality score를 산출한다. 관측 신뢰도, feature
availability, coordinate-correction magnitude는 별도 confidence/provenance signal로 유지한다.

점수는 공학적 요약이며 clinical threshold 또는 diagnostic output이 아니다.

---

## 1. 파이프라인 위치 (Pipeline Position)

```text
⑧ Feature Extraction   FeatureRecord list
⑨ Biomech Proxy        BiomechRecord list
→ ⑩ Biomarker Scoring  ← 본 단계
```

필수 입력:

```text
feat_records           availability metadata를 포함한 FeatureRecord list
biomech_records        BiomechRecord list
exercise_definition    feature_domains, biomechanical_focus, quality rules
definition_version     exercise YAML version
baseline JSON          scoring을 켤 때 data/reference/baseline_zscore.json
```

Baseline matching은 metric id 기준으로 수행한다. 따라서 per-rep metric은
`temporal.tempo.rep_duration`처럼 rep-invariant id를 사용해야 하며, 반복 번호는 `feature_id`가
아니라 `rep_id`에 둔다. Feature id에 반복 번호가 들어가면 후반 rep가 baseline entry를 찾지
못해 감점 없이 남을 수 있다.

---

## 2. 출력 계약 (Output Contract)

두 record type을 방출한다.

```text
BiomarkerRecord
    value, unit, rep_id, source_fields, availability, view/depth reliability,
    focus tier, 공통 record context metadata, landmark reference, note
    metadata를 가진 개별 metric pass-through record.

BiomarkerScoreRecord
    domain score, final score, floor flag, deduction audit, withheld-feature audit,
    score bounds, domain weights를 가진 반복별 composite score.

BiomarkerScoreItem
    BiomarkerScoreRecord.deductions에서 파생한 feature별 score audit table.
    별도 점수 알고리즘이 아니라 reporting view다.
```

`BiomarkerRecord.source_fields`는 필수다. Provenance 없는 record는 산출하지 않는다.

단계별 점검용 저장 산출물은 pass-through biomarker record와 composite score record를 분리한다.

```text
data/processed/biomarker/<recording_id>_biomarkers.csv
    BiomarkerRecord 1개당 1행. availability, source_fields, view/depth
    reliability, focus tier, record context metadata, landmark reference,
    unit metadata를 보존한다.

data/processed/biomarker/<recording_id>_biomarker_scores.csv
    baseline이 있을 때 BiomarkerScoreRecord 1개당 1행. CSV 호환성을 위해
    domain_scores, floor_applied, deductions, withheld_features, domain_weights,
    domain-feature-family weights, low-confidence/depth/focus/feature gravity policy,
    score_bounds는 JSON 문자열로 직렬화한다.

data/processed/biomarker/<recording_id>_biomarker_score_items.csv
    Scored feature item당 한 row. 각 score record의 deduction audit을 rep_id, domain,
    feature_id, item_score, deduction, value, baseline, confidence gravity,
    depth/focus gravity, feature-family weight, record context field로 펼친다.
    item_score는 score_max - effective deduction을 configured score bounds로 clipping해
    계산하므로 독립적인 임상 등급이 아니라 해당 feature의 effective contribution audit으로 읽는다.

data/processed/biomarker/<recording_id>_biomarker_qc.json
    row count, score availability, final-score range, withheld-feature count,
    output file provenance를 담은 compact QC 파일.
```

선택된 운동의 baseline이 없으면 biomarker CSV와 QC JSON은 저장하고, score CSV와 score-item
CSV는 현재 schema를 유지한 0행 파일로 저장한다. 새 authoring 운동에서 baseline을 만들기
전까지는 이것이 정상 상태다.

---

## 3. 점수화 계약 (Scoring Contract)

Composite scoring은 synthetic-normal baseline 대비 Z-score deduction을 사용한다. 기본 score bounds는
0-100이고, 기본 domain weight는 동일한 상대 가중치다.

```text
spatial   range of motion, movement path, support consistency, role alignment
temporal  pacing과 timing consistency
control   stability와 compensation feature
biomech   relative load-distribution proxy feature
```

기본 설정은 `configs/pipeline_default.yaml`에 둔다.

```yaml
biomarker:
  score_bounds:
    min: 0.0
    max: 100.0
  domain_weights:
    spatial: 1.0
    temporal: 1.0
    control: 1.0
    biomech: 1.0
  domain_feature_family_weights:
    spatial:
      range_of_motion: 0.60
      movement_path: 0.15
      support_consistency: 0.05
      role_alignment: 0.15
      phase_profile: 0.05
    temporal:
      tempo: 0.25
      variability: 0.50
      phase_profile: 0.25
  scoring_focus_weights:
    primary: 1.0
    secondary: 0.45
    context_constraint: 0.6
    compensation: 0.5
    diagnostic: 0.0
  low_confidence_score_weights:
    spatial: 0.0
    temporal: 0.0
    control: 0.0
    biomech: 0.1
  depth_dependency_score_weights:
    none: 1.0
    low: 1.0
    moderate: 0.5
    high: 0.1
    unknown: 0.3
  feature_score_weight_overrides:
    spatial.movement_path.arc_length_xy.left_ankle.*: 0.0
    spatial.movement_path.arc_length_xy.right_ankle.*: 0.0
    spatial.movement_path.arc_length_xyz.left_ankle.*: 0.0
    spatial.movement_path.arc_length_xyz.right_ankle.*: 0.0
    spatial.movement_path.arc_length_xyz.left_knee.*: 0.0
    spatial.movement_path.arc_length_xyz.right_knee.*: 0.0
    spatial.range_of_motion.xyz.*: 0.25
    control.compensation.knee_valgus.xy.*: 0.25
    control.compensation.knee_varus.xy.*: 0.25
    control.compensation.excessive_trunk_flexion.xy: 0.5
    control.compensation.excessive_trunk_flexion.xyz: 0.25
    spatial.range_of_motion.xy.left_hip_angle.turnaround_hold: 0.0
    spatial.range_of_motion.xy.right_hip_angle.turnaround_hold: 0.0
    spatial.range_of_motion.xy.left_knee_angle.turnaround_hold: 0.0
    spatial.range_of_motion.xy.right_knee_angle.turnaround_hold: 0.0
    spatial.range_of_motion.xy.left_ankle_angle.turnaround_hold: 0.0
    spatial.range_of_motion.xy.right_ankle_angle.turnaround_hold: 0.0
    spatial.range_of_motion.xyz.left_hip_angle.turnaround_hold: 0.0
    spatial.range_of_motion.xyz.right_hip_angle.turnaround_hold: 0.0
    spatial.range_of_motion.xyz.left_knee_angle.turnaround_hold: 0.0
    spatial.range_of_motion.xyz.right_knee_angle.turnaround_hold: 0.0
    spatial.range_of_motion.xyz.left_ankle_angle.turnaround_hold: 0.0
    spatial.range_of_motion.xyz.right_ankle_angle.turnaround_hold: 0.0
  feature_score_direction_overrides:
    spatial.support_consistency.*: upper_bound_only
    spatial.role_alignment.left_right.support_consistency_xy_drift.*: upper_bound_only
    spatial.movement_path.arc_length_xy.left_hip.turnaround_hold: upper_bound_only
    spatial.movement_path.arc_length_xy.right_hip.turnaround_hold: upper_bound_only
    spatial.movement_path.arc_length_xy.left_knee.turnaround_hold: upper_bound_only
    spatial.movement_path.arc_length_xy.right_knee.turnaround_hold: upper_bound_only
  baseline_generation:
    enabled: true
    generate_when_missing: true
    source_mode: current_run
    baseline_status: provisional
    source_type: current_recording
    pose_backend: mediapipe
    coordinate_mode: norm
    output_dir: data/reference/baselines
    active_metrics_path: data/reference/baseline_zscore.json
    qc_output_dir: data/reference/baseline_qc
    mirror_active_metrics: false
    use_generated_for_current_scoring: true
```

Domain은 record ID prefix로 배정한다.

```text
spatial.*   → spatial
temporal.*  → temporal
control.*   → control
biomech.*   → biomech
other       → pass-through only
```

---

## 4. Feature Eligibility

⑧은 scoring에 충분히 신뢰할 수 없는 numeric feature도 방출할 수 있다. ⑩은 `availability`를
composite-score gate로 사용하고, evidence gravity로 점수 반영 강도를 조절한다.

```text
assessed
    baseline statistics가 있으면 Z-score deduction 대상.

low_confidence
    scoring 설정에서 해당 domain의 low-confidence score weight가 0보다 클 때만
    작은 gravity로 반영한다. 기본값은 spatial/temporal/control low-confidence
    record는 제외하고, biomech low-confidence record만 낮은 영향으로 반영한다.

not_assessed
    composite score에서 제외한다. provenance/unavailable로만 보고한다.

availability 누락
    하위 호환: legacy record에 한해 assessed로 취급한다.
```

### 현재 점수화 항목 catalog

현재 score는 항목화된 scoring prototype이지 최종 normative movement-quality 판정이 아니다.
Score gravity가 낮거나 0인 항목도 biomarker audit에는 남긴다.

```text
spatial.range_of_motion.xy.*
    상태: primary scoring candidate.
    의미: recording-view 관절 range of motion.
    현재 주의: 가능한 경우 운동정의의 acceptable band를 사용한다. 통제된 깊은 squat를
    synthetic 평균보다 크다는 이유만으로 나쁘게 해석하지 않는다.

spatial.range_of_motion.xyz.*
    상태: depth-mixed comparative evidence.
    의미: 같은 joint-angle family에 model/candidate depth를 포함한 값.
    현재 주의: corrected-3D 또는 multi-view validation이 뒷받침되기 전까지 낮은 gravity를 둔다.

spatial.movement_path.arc_length_xy.*
    상태: score-tunable recording-view path evidence.
    의미: camera-plane landmark path length.
    현재 주의: fixed-support ankle path는 squat에서 기본적으로 withheld한다. Apparent support
    motion은 실제 foot travel보다 pose noise일 수 있기 때문이다.

spatial.support_consistency.*
    상태: support-context scoring candidate with one-sided scoring.
    의미: fixed support anchor의 recording-view 일관성.
    현재 주의: CoP/CoM stability 주장이 아니며, biomechanical center proxy는 ⑨에서 다룬다.

spatial.role_alignment.*
    상태: secondary/context scoring candidate.
    의미: 운동에 필요한 landmark의 bilateral 또는 role-based agreement.
    현재 주의: view-sensitive symmetry는 camera compatibility와 landmark quality를 함께 봐야 한다.

temporal.tempo.* / temporal.variability.* / temporal.phase_profile.*
    상태: 넓은 tolerance band를 가진 scoring candidate.
    의미: rep duration, rhythm/repeatability, 운동정의 기반 phase timing balance.
    현재 주의: 본 연구는 absolute speed를 primary quality target으로 보지 않는다. 좁은 synthetic
    duration과 일치하는 것보다 안정적인 rhythm이 더 중요하다.

control.compensation.knee_valgus.xy.* / control.compensation.knee_varus.xy.*
    상태: attenuated control scoring candidate.
    의미: recording-view hip-knee-ankle tracking proxy.
    현재 주의: lower-body stance task에서 의미가 있지만 view와 visibility에 민감하다.
    Low-confidence control record는 기본적으로 withheld한다.

control.compensation.excessive_trunk_flexion.xy
    상태: provisional control scoring candidate.
    의미: image vertical 기준 recording-view trunk-line angle.
    현재 주의: 정상적인 trunk strategy는 운동 맥락에 따라 다르다. Hinge, squat, plank,
    push-up은 하나의 좁은 trunk-flexion baseline을 공유하면 안 된다.
    기본 gravity: trunk-orientation tolerance band가 provisional인 동안 0.5.

control.compensation.excessive_trunk_flexion.xyz
    상태: low-gravity comparative evidence.
    의미: model/candidate depth가 섞인 trunk-line angle.
    현재 주의: monocular depth-mixed evidence이므로 corrected-3D validation 전까지 visible but weak로 둔다.

control.compensation.heel_lift.xy.*
    상태: recording-view support-contact proxy.
    의미: rep support baseline 위 apparent heel elevation.
    현재 주의: landmark visibility가 좋아야 하며, 현재 prototype에서는 depth-based heel lift를 승격하지 않는다.

control.compensation.pelvis_rotation.xyz
    상태: low-confidence/report-heavy evidence.
    의미: left-right hip model-depth asymmetry 기반 pelvic rotation proxy.
    현재 주의: monocular pose에서는 depth-sensitive하다.

biomech.*
    상태: low-confidence gravity를 가진 biomechanical proxy evidence.
    의미: 상대적 CoM/moment-arm/load-shift tendency이며 absolute force/torque가 아니다.
    현재 주의: 해석과 향후 비교에는 유용하지만 clinical 또는 kinetic ground-truth measurement는 아니다.
```

현재 p01 squat run에서 control subscore가 낮게 나오는 것은 주로 control-family baseline과
tolerance rule이 여러 recording으로 검토되어야 함을 의미한다. 따라서 score audit은 항목별로
읽어야 한다. Control candidate와 evidence path는 사용할 수 있지만, 최종 score calibration은
후속 작업으로 남긴다.

### 운동 전반에 적용되는 control scoring 문법

Control feature는 고정된 universal checklist가 아니다. 운동정의가 어떤 control family가 적용되는지
결정하고, scoring은 다른 domain과 같은 evidence/availability 문법을 적용한다.

```text
exercise context
    운동정의의 posture, support, laterality, primary/secondary joint, movement phase,
    camera-view family.

control family
    stability | compensation | support_contact | alignment_control |
    phase_control | diagnostic

evidence path
    recording-view candidate evidence는 xy, depth-sensitive comparative evidence는 xyz/z,
    control 질문이 phase timing에 관한 경우 timing, ⑨ biomechanical proxy에서 온 경우 proxy.

confidence gate
    landmark visibility/coverage, view compatibility, support-context compatibility,
    depth dependency, correction/canonicalization provenance.

scoring status
    scoring_candidate | attenuated_candidate | low_gravity_compare |
    report_only | not_applicable
```

현재 cross-exercise control matrix는 다음과 같다.

```text
knee_tracking
    Feature ids:
        control.compensation.knee_valgus.xy.<side>
        control.compensation.knee_varus.xy.<side>
    Exercise context:
        hip-knee-ankle tracking이 의미 있는 lower-body stance task
        (squat, lunge, step-up 계열). 운동정의가 lower-limb control 질문을 명시적으로
        승격하지 않는 한 upper-body 또는 supine/core task에는 적용하지 않는다.
    Evidence path:
        현재 pipeline에서는 recording-view xy만 사용한다. Body-frontal/corrected reference
        plane이 생기기 전까지 knee valgus/varus xyz variant는 방출하지 않는다.
    Confidence gate:
        hip, knee, ankle landmark quality, camera-view compatibility, unilateral 또는
        alternating task의 laterality/role context.
    Scoring status:
        attenuated candidate. Low-confidence row는 기본적으로 withheld한다.

trunk_orientation_control
    Feature ids:
        control.compensation.excessive_trunk_flexion.xy
        control.compensation.excessive_trunk_flexion.xyz
    Exercise context:
        운동별로 다르다. Trunk lean은 squat에서는 compensation일 수 있고, hinge에서는
        예상되는 strategy일 수 있으며, plank 또는 push-up에서는 다른 control 문제다.
        운동정의가 acceptable direction 또는 target band를 제공해야 강한 점수화가 가능하다.
    Evidence path:
        xy는 recording-view public candidate이고, xyz는 depth-mixed comparative evidence다.
    Confidence gate:
        shoulder/hip landmark quality, view family, 해당 posture에서 image-vertical trunk angle이
        의미 있는지 여부.
    Scoring status:
        xy는 provisional candidate, xyz는 low-gravity comparison.

support_contact_control
    Feature ids:
        control.compensation.heel_lift.xy.<side>
        향후 plank 또는 push-up 계열에서 정의되는 hand/wrist support-contact proxy.
    Exercise context:
        closed-chain support task. Foot-supported lower-body exercise에서는 heel lift가 의미
        있을 수 있고, hand-supported exercise에서는 별도 wrist/hand support-contact proxy가
        필요하다.
    Evidence path:
        기본은 recording-view support-axis evidence다. Depth 기반 contact inference는 검증 전까지
        low-confidence/report-only로 둔다.
    Confidence gate:
        support landmark visibility, 선언된 support anchor, 운동정의의 support surface assumption.
    Scoring status:
        support context와 visibility가 충분할 때만 candidate.

pelvis_control
    Feature ids:
        control.stability.hip_center_support_center_xy_drift
        control.compensation.lateral_pelvic_shift.xy
        control.compensation.pelvis_rotation.xyz
    Exercise context:
        support-relative pelvis control은 lower-body stance와 plank/shoulder-tap 계열의
        anti-rotation task에서 의미가 있을 수 있다. Hip-centered self-measurement는 독립적인
        support-relative reference로 재정의되기 전까지 diagnostic/not_assessed다.
    Evidence path:
        support-relative xy를 scoring 후보로 우선한다. z/xyz 기반 pelvis rotation은
        depth-sensitive comparative evidence다.
    Confidence gate:
        support anchor availability, hip landmark quality, laterality/role context,
        rotation에 대한 depth reliability.
    Scoring status:
        support-relative xy는 candidate가 될 수 있고, depth-heavy rotation은 low-gravity 또는
        report-only로 둔다.

phase_control
    Feature ids:
        control.phase_profile.* (future)
    Exercise context:
        bottom-position hold stability 또는 ascent-specific compensation처럼 phase label이 control
        질문을 실제로 의미 있게 만들 때만 사용한다.
    Evidence path:
        phase-aware feature에서 파생된 domain-local summary이며 hidden coordinate correction이 아니다.
    Confidence gate:
        phase segmentation quality와 source feature 자체의 confidence를 함께 따른다.
    Scoring status:
        planned extension이며, 테스트 전까지 report-only다.
```

이 문법은 control을 squat 전용 rule로 하드코딩하지 않고 확장 가능하게 유지한다. 새 운동은 관련
context를 선언하고, 같은 availability, depth-dependency, focus-tier, feature-family, feature-id
gravity gate를 통해 점수 기여도를 결정한다.

`view_reliability`는 별도 score multiplier가 아니다. 이는 이미 `availability`에 반영되어야 하며,
camera artifact에서 나온 가짜 정밀도를 피하기 위함이다.

Coordinate-reference self-measurement는 composite scoring에 들어가면 안 된다. ⑤ Normalization이
좌표 원점으로 사용한 파생 reference point를 같은 feature가 다시 측정하면, 원본 recording view에서
신체 분절이 움직였더라도 numeric value가 0에 가까워질 수 있다. 이런 record는 ⑧에서 독립 reference
기준으로 재정의되기 전까지 `not_assessed` 또는 `diagnostic`으로 둔다.

Hip-centered `norm` 좌표에서는 이 guard가 다음 hip/pelvis-center stability proxy에 적용된다:

```text
control.stability.hip_center_x_std
control.stability.hip_center_z_std
control.compensation.lateral_pelvic_shift.xy
```

Closed-chain squat-style pelvis control은 운동정의의 support center에 대한 hip-center drift처럼
support-relative recording-view evidence로 대체하고, 이후 일반 availability, depth-dependency,
focus-tier, feature-family gravity를 통해 점수 반영 강도를 조절한다.

Closed-chain heel-lift scoring도 현재 pipeline에서는 recording-view support-contact proxy다.
`control.compensation.heel_lift.xy.<side>`는 recording-view vertical evidence에서 계산될 때만 점수화할 수
있다. Model-depth `z`를 이용한 heel-lift diagnostic은 향후 corrected-3D validation이 승격하기
전까지 low-confidence 또는 report-only로 남아야 한다.

⑧과 ⑨에서 온 공통 record context metadata는 보존하지만, 그 자체가 추가 score gravity를 만들지는
않는다. 특히 `landmark_ids`, `support_role`, `coordinate_reference`, `evaluation_domain`,
`evidence_axes`, `feature_family`는 어떤 landmark를 어떤 좌표/evidence 경로로 측정했는지
설명한다. Body region, side, default joint action 같은 안정적인 해부학 label은 report에서
필요할 때 joint/landmark metadata registry와 join해서 얻으며, 모든 score record에 중복 저장하지
않는다. 실제 점수 반영 강도는 계속 availability, depth dependency, focus tier,
feature-family budget, feature-specific override에서 결정한다.

`low_confidence_score_weights`는 scoring 단계의 gravity이지 normalization 또는 canonicalization
산출물이 아니다. Depth-sensitive biomech proxy evidence를 composite score에서 완전히 숨기지
않되, monocular depth가 full-strength evidence처럼 작동하지 않도록 제한한다. Effective score
weight가 0인 record는 `withheld_features`에 기록하고, 0보다 큰 low-confidence record는
`deductions`에 availability와 confidence weight를 함께 기록한다.

`depth_dependency_score_weights`는 두 번째 scoring-stage gravity다. Feature를 제거하거나
biomarker value를 바꾸지 않는다. Baseline과 매칭된 deduction이 composite score에 얼마나 강하게
들어가는지만 조절한다.

```text
none       recording-view 또는 timing evidence; 기본 full gravity
low        낮은 depth sensitivity; 현재 기본 full gravity
moderate   recording-view/depth evidence가 섞인 항목; 기본 attenuated
high       monocular-depth 또는 corrected-3D-hypothesis evidence; 작은 gravity
unknown    evidence path가 분류되기 전까지 보고하되 약하게 반영
```

Effective deduction gravity:

```text
g_effective =
    availability_gravity
  * depth_dependency_gravity
  * focus_gravity
  * feature_gravity
```

이 구조는 recording-view evidence와 depth-sensitive evidence를 같은 audit trail에 유지하면서도,
각 evidence family가 final score에 미치는 영향을 조정할 수 있게 한다. 향후 scoring 연구에서
기본값은 바뀔 수 있지만, 모든 변경은 score record에 남아야 한다.

### Movement-path evidence variant gravity

Movement-path scoring은 `xy`와 `xyz` 중 하나를 전역으로 선택하지 않는다. ⑧ Feature Extraction은
coordinate-derived movement-path target에 대해 두 variant를 모두 방출하고, ⑩ Scoring은 feature id,
focus tier, depth dependency, view compatibility에 따라 각 variant의 기여도를 조정한다.

```text
xy
    Recording-view evidence다. Movement-quality 질문이 camera-plane x/y로 답해질 수 있고
    baseline view와 호환될 때 우선 사용한다.

xyz
    Depth-sensitive evidence다. Review와 corrected-3D comparison을 위해 visible하게 남기되,
    monocular MediaPipe depth에서는 해당 feature가 검증되기 전까지 낮은 gravity를 부여한다.

z
    Single-axis diagnostic/provenance다. 기본적으로 scoring하지 않는다.
```

따라서 calibration 목표는 프로젝트 전체에 하나의 `xy:xyz` 비율을 정하는 것이 아니다. 여러 recording,
camera view, exercise를 보면서 feature별 gravity 정책을 정하는 것이다. 예를 들어 squat knee
movement path는 `xy` 중심으로 유지할 수 있고, 고정 ankle support movement path는 `support_consistency`를
우선 사용하며, 향후 corrected-3D hip/trunk feature는 correction burden과 residual evidence가
허용될 때만 `xyz` gravity를 올릴 수 있다.

### Range-of-motion evidence variant gravity

Range of motion도 같은 explicit-evidence 정책을 따른다. ⑧은 같은 `angle_definitions` triplet에서
`spatial.range_of_motion.xy.<joint_angle>`와 `spatial.range_of_motion.xyz.<joint_angle>`를 모두 방출한다. ⑩은 camera
view가 호환될 때 `xy` variant를 우선 recording-view scoring 후보로 보고, `xyz` variant는 낮은
기본 gravity를 가진 depth-sensitive comparative evidence로 다룬다.

이는 2D projected angle이 항상 옳다는 뜻이 아니다. Monocular 연구 환경에서 x/y evidence는
recording view 안에서 더 안정적인 반면, xyz evidence는 review와 향후 corrected-3D comparison에
필요하다. Score는 단일 implicit range-of-motion 값 안에 선택을 숨기지 않고, 두 variant와 각 gravity를
드러내야 한다.

### 운동정의 focus 정책

운동정의는 scoring intent 문서이기도 하다. 따라서 authoring에서 선택한 primary/secondary
joint action은 점수 반영 강도에 영향을 주어야 한다. 다만 운동정의를 hard whitelist로 만들지는
않는다. ⑧은 각 feature 또는 proxy record에 `focus_tier`를 붙이고, ⑩은
`scoring_focus_weights`의 값을 deduction gravity에 곱한다.

```text
primary
    운동정의의 primary joint action, primary body region, primary joint,
    main load region에 의해 뒷받침되는 주 task signal.

secondary
    secondary joint action 또는 secondary movement plane에 의해 뒷받침되는
    보조 task signal. 기본적으로 낮은 gravity로 score-visible하게 둔다.

context_constraint
    closed-chain support consistency, base-of-support consistency, role alignment처럼
    운동 setup이 요구하지만 단순한 primary joint action으로 환원되지 않는
    운동 맥락 signal.

compensation
    보상 움직임 또는 안전성 관련 후보 pattern. 점수에 반영될 수 있지만
    primary/secondary task signal보다 과도하게 지배하지 않도록 한다.

diagnostic
    axis diagnostic, support-consistency axis path diagnostic, retired/deferred feature
    후보처럼 report-only 또는 직접 해석력이 약한 evidence.
```

기본 focus weight는 primary feature를 full strength로 유지하고, secondary/context signal은
낮게 반영하며, diagnostic은 composite scoring에서 제외한다. Focus weight는 여러 gravity 중
하나일 뿐이다. Primary feature라도 low-confidence, high depth dependency, baseline 부재,
feature-id override가 있으면 점수 반영은 작아질 수 있다. 반대로 support-consistency와 compensation
evidence는 운동정의가 요구하는 경우 score-visible하게 유지될 수 있다.

Domain 내부에서는 해당 domain에 `domain_feature_family_weights`가 설정되어 있으면 feature-family
weight를 사용한다. 이렇게 하면 어떤 feature family가 withheld되었다는 이유만으로 남은 feature의
상대 비중이 커지지 않는다. 특정 family가 없거나 unavailable이거나 명시적으로 0이면 그 family
budget은 다른 family로 재분배하지 않는다.

```text
spatial.range_of_motion.xy.*                  → range_of_motion
spatial.range_of_motion.xyz.*                 → range_of_motion
spatial.movement_path.arc_length_*.*      → movement_path
spatial.role_alignment.*                    → role_alignment
spatial.support_consistency.*               → support_consistency
temporal.tempo.*                            → tempo
temporal.variability.*                      → variability
<domain>.phase_profile.*                    → phase_profile
그 외 spatial record              → other
```

현재는 `spatial.phase_profile.*`와 `temporal.phase_profile.*`가 domain-local phase-summary family로
방출될 수 있다. `control.phase_profile.*`, `biomech.phase_profile.*`는 여전히 예약 영역이며, 별도
scoring 검토 후 활성화한다.

Temporal family budget은 spatial과 의도적으로 다르다. Absolute duration(`tempo`)은 낮은 비중을
갖는다. 본 연구는 하나의 고정 운동 속도를 더 좋은 수행으로 점수화하지 않기 때문이다.
Rhythm/repeatability(`variability`)가 가장 큰 temporal budget을 받고, 운동정의 기반 phase
ratio(`phase_profile`)는 temporal domain을 과도하게 지배하지 않는 선에서 score-visible하게 둔다.

현재 spatial 정책에서 `support_consistency`는 recording-view fixed-support consistency를 위한 좁은
constraint/QC 성격의 budget만 받는다. Fixed support는 normalization/canonicalization에서 일부
강제될 수 있고 pose jitter도 섞일 수 있으므로, primary movement-quality score처럼 작동하면 안
된다. 따라서 spatial budget은 range of motion와 assessed role alignment를 더 우선하고,
support-consistency row는 낮은 강도의 fixed-support compliance evidence로 남긴다. 첫
scoring-ready support-consistency role-alignment
record는 `spatial.role_alignment.left_right.support_consistency_xy_drift.*`이다. 이 feature는 monocular depth가 아니라
fixed-support x/y drift에서 유도된다. Depth-sensitive range-of-motion role alignment는 계속 방출될 수 있지만,
view/depth availability gate의 지배를 받으며 low-confidence로 표시되면 withheld된다.
Axis-path `support_consistency` diagnostic은 diagnostic으로 남기며, recording-view point/width/center
stability row만 좁은 support-consistency family budget을 받을 수 있다.

Support-consistency scoring은 기본적으로 `upper_bound_only` direction을 사용한다. Provisional
baseline보다 support drift가 작은 것은 fault가 아니며, baseline보다 큰 drift만 deduction을 만들 수
있다. Corrected coordinate를 사용할 때는 correction burden/residual과 함께 해석해야 하며, 숨은
fixed-support correction을 단순히 좋은 점수로 보상하지 않아야 한다.

### Range-of-motion target-band 정책

Range-of-motion scoring이 항상 "synthetic baseline 평균에 가까울수록 좋다"는 뜻이어서는 안 된다.
운동정의가 `spatial.range_of_motion.xy.*` target을 제공하면 ⑩은 generic absolute z-score penalty 대신 기능적
acceptable-band penalty를 사용한다.

```yaml
quality_rules:
  range_of_motion_targets:
    spatial.range_of_motion.xy.left_knee_angle:
      scoring_mode: minimum_sufficient_band
      minimum_sufficient_deg: 90.0
      excessive_threshold_deg: 160.0
      soft_tolerance_deg: 10.0
      excessive_penalty_scale: 0.5
      apply_to_phase_suffixes: [full_rep, descent, ascent]
```

현재 rule의 의미는 다음과 같다.

- `minimum_sufficient_deg`보다 작으면 `soft_tolerance_deg` 기준으로 부족분을 감점한다.
- `minimum_sufficient_deg`와 `excessive_threshold_deg` 사이에서는 충분한 task range of motion를 달성한
  것으로 보고 range-of-motion 감점을 만들지 않는다.
- `excessive_threshold_deg`를 넘으면 운동정의가 upper bound를 제공한 경우에만 더 약한 excess
  penalty를 적용한다.
- Squat의 `turnaround_hold` range of motion는 기본적으로 match하지 않는다. Hold 중 움직임이 작은 것은
  range-of-motion 실패가 아니기 때문이다. 현재 기본 squat 정책은 lower-body
  `spatial.range_of_motion.xy.*.turnaround_hold`와 `spatial.range_of_motion.xyz.*.turnaround_hold`를
  `feature_score_weight_overrides`로 composite scoring에서 withheld한다.

이 정책은 range of motion를 movement-quality signal로 유지하되, 더 깊거나 큰 controlled squat range of motion가
provisional baseline 평균과 다르다는 이유만으로 나쁘게 해석되는 것을 피하기 위한 것이다.

### Temporal tolerance-band 정책

현재 연구는 운동 속도 자체를 주요 movement-quality target으로 보지 않는다. Temporal scoring은
주로 rhythm과 repeatability를 보존해야 한다. 반복이 provisional synthetic baseline보다 느리거나
빠르더라도, 운동정의가 제공한 timing band 안에 있으면 허용 가능한 수행으로 본다.

운동정의가 `temporal.tempo.rep_duration*` target을 제공하면 ⑩은 generic baseline z-score를
바로 적용하기 전에 acceptable-duration band를 먼저 사용한다.

```yaml
quality_rules:
  temporal_tolerance_bands:
    temporal.tempo.rep_duration:
      scoring_mode: acceptable_duration_band
      minimum_duration_s: 1.2
      maximum_duration_s: 3.5
      soft_tolerance_s: 0.3
    temporal.tempo.rep_duration.descent:
      scoring_mode: acceptable_duration_band
      minimum_duration_s: 0.4
      maximum_duration_s: 1.5
      soft_tolerance_s: 0.15
    temporal.tempo.rep_duration.turnaround_hold:
      scoring_mode: acceptable_duration_band
      minimum_duration_s: 0.0
      maximum_duration_s: 0.5
      soft_tolerance_s: 0.1
    temporal.tempo.rep_duration.ascent:
      scoring_mode: acceptable_duration_band
      minimum_duration_s: 0.4
      maximum_duration_s: 1.5
      soft_tolerance_s: 0.15
```

현재 rule의 의미는 다음과 같다.

- `[minimum_duration_s, maximum_duration_s]` 안에 있으면 absolute-duration 감점을 만들지 않는다.
- `minimum_duration_s`보다 짧으면 `soft_tolerance_s` 기준으로 부족분만 감점한다.
- `maximum_duration_s`보다 길면 `soft_tolerance_s` 기준으로 초과분만 감점한다.
- Timing consistency는 `temporal.variability.tempo_cv`와 `temporal.phase_profile.*`
  feature로 계속 노출한다. 이들이 모든 피험자를 좁은 절대 속도에 맞추는 것보다 rhythm과
  repeatability를 보기 적합하다.

이 정책은 temporal scoring을 논문 범위와 맞춘다. 명백한 timing outlier는 표시하되, 하나의
고정된 squat 속도가 임상적 또는 생체역학적으로 최적이라고 주장하지 않는다.

`temporal.variability.tempo_cv`는 sequence-level evidence다. Per-rep score record가 있을 때는
같은 sequence-level variability record를 각 rep의 temporal audit에 포함할 수 있다. 이는 rep마다
별도의 CV가 있다는 뜻이 아니라, rhythm consistency가 composite score에 기여하는 방식을 각 rep
score에서 확인할 수 있게 하기 위한 것이다.

`quality_rules.temporal_variability_bands`와 match되는 feature id는 maximum-variability ceiling을
사용한다.

```yaml
quality_rules:
  temporal_variability_bands:
    temporal.variability.tempo_cv:
      scoring_mode: maximum_sufficient_ceiling
      maximum_cv: 0.05
      soft_tolerance_cv: 0.05
```

`maximum_cv` 이하 값은 rhythm deduction을 만들지 않는다. 초과 값은 `soft_tolerance_cv` 기준으로
초과분만 감점한다.

`quality_rules.temporal_phase_profile_bands`와 match되는 feature id는 acceptable phase-ratio band를
사용한다.

```yaml
quality_rules:
  temporal_phase_profile_bands:
    temporal.phase_profile.duration_ratio.descent_ascent:
      scoring_mode: acceptable_ratio_band
      minimum_ratio: 0.5
      maximum_ratio: 2.0
      soft_tolerance_ratio: 0.25
```

Ratio band 안의 값은 감점을 만들지 않는다. Band 밖의 값은 가장 가까운 bound에서 벗어난 정도를
`soft_tolerance_ratio`로 나누어 감점한다. 이렇게 하면 squat rhythm review에서 phase-profile
scoring을 visible하게 유지하면서도, 특정 descent/ascent timing ratio 하나가 생체역학적으로
최적이라는 좁은 주장을 피할 수 있다.

`feature_score_weight_overrides`는 정확한 feature id 또는 `prefix.*` feature family에 적용하는
선택적 세 번째 gravity layer다. 현재 monocular pipeline에서 numeric value는 review에 유용하지만
movement-quality penalty로 직접 강하게 쓰기 약한 evidence variant에 사용한다. Feature extraction은
recording-view path evidence인 `spatial.movement_path.arc_length_xy.<landmark>`와 recording-view/depth가
섞인 evidence인 `spatial.movement_path.arc_length_xyz.<landmark>`를 명시적으로 방출한다. Range of motion도
recording-view included-angle range of motion인 `spatial.range_of_motion.xy.<joint_angle>`와
recording-view/depth가 섞인 range of motion인 `spatial.range_of_motion.xyz.<joint_angle>`를 명시적으로 방출하고,
scoring이 gravity 결정을 소유한다.

고정 bilateral-foot squat에서 support-consistency axis `xyz` movement-path evidence는 visible/baseline-matchable
evidence로 유지하지만, 기본 feature gravity를 `0.0`으로 두어 composite scoring에서는 withheld한다.
향후 `maintain_foot_contact` 점수 기여는 별도의 recording-view support-consistency feature family가
담당해야 한다.

현재 validation 정책은 recording-view knee movement path length를 승격하고 knee `xyz` path는
composite scoring에서 withheld한다. Knee motion은 squat 중 실제로 움직이는 관절 신호지만, p01
review에서 `xyz` path가 monocular MediaPipe depth의 z축에 강하게 지배될 수 있음이 확인됐다.
따라서 `spatial.movement_path.arc_length_xy.*_knee*`를 active movement-path scoring evidence로 사용하고,
`spatial.movement_path.arc_length_xyz.*_knee*`는 같은 움직임을 depth-dominated evidence로 중복 감점하지
않도록 feature gravity `0.0`으로 visible provenance에 남긴다.

Lower-body movement path의 `turnaround_hold` 구간에서는 baseline보다 작은 path length를 실패로 보지
않는다. 하단 전환부가 조용한 것은 움직임 실패가 아니라 bottom-position control이 안정적이라는
신호일 수 있기 때문이다. 따라서 기본 정책은 승격된 hip/knee recording-view movement path에
`upper_bound_only` scoring을 적용한다. Path가 baseline보다 과도하게 클 때만 감점하고, 더 작은
path length는 감점하지 않는다.

Recording-view movement-path feature도 camera-view dependent하다. `z` 또는 `xyz` path length보다
monocular depth noise에는 덜 노출되지만, view invariant한 feature는 아니다. 향후 multi-camera-zone
baseline에서는 이러한 feature를 호환 가능한 camera-zone family 안에서만 비교하거나, active recording
view가 baseline view와 맞지 않으면 scoring gravity를 낮춰야 한다.

Frontal knee-tracking compensation(`control.compensation.knee_valgus.xy.*`,
`control.compensation.knee_varus.xy.*`)도 기본 개발 정책에서는 attenuate한다. Knee tracking은 squat에서
생체역학적으로 의미 있는 신호이므로 scoring 후보로 유지하지만, 현재 monocular proxy는 view-sensitive하고
provisional baseline에서는 작은 hip-knee-ankle line deviation도 매우 큰 z-score를 만들 수 있다.
Camera-view gating과 multi-recording baseline이 생기기 전까지 기본 feature gravity는 `0.25`로 둔다.
반복적으로 나타나는 frontal knee deviation은 보이게 하되, 이 항목 하나가 control domain을 지배하지
않도록 하기 위한 설정이다. `control.compensation.excessive_trunk_flexion.xyz` 같은 depth-mixed
control variant는 corrected-3D 또는 multi-view validation이 더 강한 사용을 뒷받침하기 전까지
visible but low-gravity evidence로 둔다.
Recording-view trunk orientation(`control.compensation.excessive_trunk_flexion.xy`)은 임시 feature
gravity `0.5`를 사용한다. 현재 synthetic baseline은 squat, hinge, plank, push-up 계열 전반의
최종 trunk-control rule로 쓰기에는 너무 좁기 때문이다. 이 설정은 trunk compensation을 visible하게
유지하되, provisional baseline이 control subscore 전체를 지배하지 않게 한다.

Single-axis movement-path diagnostic은 특정 future validation study가 없는 한 기본적으로 report-only다.
`spatial.movement_path.axis_path_z.<landmark>`는 기본적으로 scoring하지 않으며, 검증된 depth-sensitive
score path가 승격하기 전까지 depth-noise/corrected-3D-hypothesis provenance로 둔다. `xy`와 `xyz`
record가 score-tunable movement-path variant이며, 기여도는 availability, focus tier, depth-dependency
gravity, feature-specific gravity가 함께 결정한다.

큰 canonicalization correction magnitude도 movement-quality score를 직접 낮추지 않는다. 검증된
별도 점수 정책이 생기기 전까지는 data-confidence/provenance에 둔다.

---

## 5. Z-Score Deduction And Dynamic Floor

각 assessed feature에 대해:

```text
σ_eff  = max(σ_baseline, STD_FLOOR_RATIO * |μ_baseline|, STD_ABS_FLOOR)
Z      = (value - μ_baseline) / σ_eff
w_i    = feature_family_weight / family 안의 scoring candidate feature 수
g_a    = assessed는 1.0, low_confidence는 domain별 low-confidence score weight
g_d    = depth_dependency_score_weights[record.depth_dependency]
g_f    = feature_score_weight_overrides.get(feature_id, 1.0)
g_i    = g_a * g_d * g_f
Z_eff  = score_direction_transform(Z, feature_score_direction_overrides)
deduct = scaled_abs_z_deduction(Z_eff, w_i, score_bounds) * g_i
```

`feature_score_direction_overrides`는 특정 feature가 기본 two-sided baseline deviation을 쓸지,
one-sided 해석을 쓸지 조절한다.

```text
two_sided         |Z|를 감점한다. 대부분의 baseline-matched feature 기본값
upper_bound_only  max(Z, 0)만 감점한다. baseline보다 작은 값은 실패로 보지 않는다
lower_bound_only  min(Z, 0)만 감점한다. baseline보다 큰 값은 실패로 보지 않는다
```

`quality_rules.range_of_motion_targets`와 match되는 feature id에서는 `Z` 대신 signed target-band deviation을
사용한다.

```text
Z_band = 0                                           if value is inside band
Z_band = (value - minimum_sufficient) / tolerance    if range of motion is insufficient
Z_band = excess_scale * (value - excessive) / tolerance
                                                    if range of motion is excessive
```

Deduction audit에는 `scoring_mode: minimum_sufficient_band`와 target bound를 기록한다.

`quality_rules.temporal_tolerance_bands`와 match되는 feature id에서는 `Z` 대신 signed
acceptable-duration-band deviation을 사용한다.

```text
Z_band = 0                                           if duration is inside band
Z_band = (duration - minimum_duration_s) / tolerance if duration is too short
Z_band = (duration - maximum_duration_s) / tolerance if duration is too long
```

Deduction audit에는 `scoring_mode: acceptable_duration_band`와 target timing bound를 기록한다.

`quality_rules.temporal_variability_bands`와 match되는 feature id에서는 `Z` 대신 signed
maximum-variability deviation을 사용한다.

```text
Z_band = 0                              if CV <= maximum_cv
Z_band = (CV - maximum_cv) / tolerance  if CV is too high
```

Deduction audit에는 `scoring_mode: maximum_sufficient_ceiling`와 target CV bound를 기록한다.

`quality_rules.temporal_phase_profile_bands`와 match되는 feature id에서는 `Z` 대신 signed
acceptable-ratio-band deviation을 사용한다.

```text
Z_band = 0                                if ratio is inside band
Z_band = (ratio - minimum_ratio) / tol    if ratio is too low
Z_band = (ratio - maximum_ratio) / tol    if ratio is too high
```

Deduction audit에는 `scoring_mode: acceptable_ratio_band`와 target ratio bound를 기록한다.

Domain에 feature-family weight가 없으면 legacy equal-within-domain weight로 fallback한다.
Domain에 family weight가 있는데 record가 zero-weight 또는 unlisted family에 속하면 해당 record는
`feature_family_weight_zero` reason과 함께 `withheld_features`에 기록하고, 그 budget은 다른 family로
넘기지 않는다.

σ floor는 baseline variance가 0에 가까울 때 deduction이 불안정해지는 것을 막는다.

Dynamic floor는 mandatory range-of-motion achievement에 묶는다.

```text
mandatory_range_of_motion_ratio = mean(min(range_of_motion_i / range_of_motion_baseline_i, 1.0))
floor_dynamic       = score_min + 0.50 * score_span * clamp(mandatory_range_of_motion_ratio)
domain_score        = max(floor_dynamic, raw_domain_score)
```

이 규칙은 동작을 수행한 반복이 여러 compensation/control deduction 때문에 최저점으로 바로
떨어지는 것을 막는다. `floor_applied`는 floor가 domain에 영향을 준 경우를 기록한다.

---

## 6. Baseline

```text
File       data/reference/baseline_zscore.json
Generator  scripts/generate_baseline.py
Schema     { exercise_id: { metric_id: {"mean": float, "std": float} } }
```

Baseline은 synthetic engineering reference이며 population norm이 아니다. Baseline 파일이 없거나
선택한 운동의 baseline entry가 없으면 warning과 함께 composite score record만 건너뛰고,
pass-through biomarker record는 반환한다.

Baseline statistics는 그것을 생성한 exercise definition 및 feature schema에 묶인다. Authoring
운동이 승격되거나 feature set이 바뀌면 기존 baseline entry는 재생성하거나 명시적으로 version
guard를 두기 전까지 invalid다.

Baseline generation은 별도 번호가 붙은 pipeline stage가 아니라 ⑩ scoring의 하위 정책이다.
Baseline 생성과 baseline 채택은 별도 동작이다. `biomarker.baseline_generation.enabled`와
`generate_when_missing`이 true이면 ⑩은 선택한 운동의 active baseline entry가 없을 때
provisional baseline을 생성할 수 있다. 이는 scoring path를 smoke-test하기 위한 것이며,
생성된 baseline을 active research baseline으로 조용히 승격해서는 안 된다. 생성된 baseline은
active baseline으로 사용하기 전에 QC/provenance metadata로 검토해야 한다.

Baseline-view compatibility도 pose-derived inference가 아니라 metadata contract로 다룬다.
Movement path 및 frontal-plane compensation처럼 view-sensitive한 recording-view feature에서는 baseline과
target recording을 먼저 선언된 recording/protocol metadata로 맞춰야 한다.

```text
exercise_id
definition_version
pose_backend
coordinate_mode
feature_schema_version
camera_view_family
camera_height_level
framing_scope
scoring_policy_version
```

Pose-derived body direction은 primary view-match key가 아니다. Body direction은 pose noise, 운동 중
몸통 회전, 피험자 회전과 구분하기 어렵기 때문에 보조 QC signal로만 사용한다.

```text
metadata compatible + pose QC plausible       → normal scoring eligibility
metadata compatible + pose QC contradictory   → warning / possible low_confidence
metadata missing                              → view-sensitive feature는 provisional로 해석
metadata incompatible                         → view-sensitive feature family는 withheld하거나 compatible baseline으로 재평가
```

이렇게 해야 연구 범위가 명확해진다. 본 프레임워크는 camera-invariant 절대 3D truth를 주장하지 않고,
선언된 recording-view contract 안에서 protocol-conditioned movement-quality proxy를 산출한다.
프로토콜 안의 작은 view variation은 universal view-sensitivity multiplier로 일괄 감쇠하기보다 reviewed
baseline, tolerance rule, feature-family budget, directional scoring rule로 흡수해야 한다.

---

## 7. Exercise Priors And Baseline Tiers

Exercise definition은 scoring policy의 seed를 줄 수 있지만, 그 자체만으로 신뢰할 수 있는 score
baseline을 만들 수는 없다.

Exercise definition이 제공하는 prior:

```text
feature selection         어떤 spatial/temporal/control/biomech metric을 볼지
eligibility policy        어떤 evidence를 assessed 또는 withheld로 볼지
expected movement pattern phase model, support context, primary plane
QC and warning defaults   impossible/implausible range, camera-view reliability
```

Exercise definition이 직접 제공하지 않는 score statistics:

```text
baseline mean/std         reference execution에서 관측된 값
natural variability       reviewed rep/recording/subject에서 추정한 자연 변동
model error distribution  실제 pose backend와 pipeline에서 관측되는 오류 분포
```

따라서 reference 구축은 별도의 연구 작업이다. 사용자는 대상 운동에서 무엇을 "기대되는" 움직임으로
볼지 정하는 reference material을 직접 구축하거나 선택해야 한다.

```text
synthetic reference       통제된 synthetic 또는 demonstration sequence
reviewed-good examples   provisional/reviewed engineering reference로 적합하다고
                         연구자가 검토한 실행
custom expected values    pilot experiment, 지도/자문 검토, 연구 설계에서 정한
                         운동별 값 또는 tolerance band
```

운동 YAML과 default scoring config는 feature selection, eligibility, 기본 gravity를 제공할 수
있다. 하지만 normative mean/std를 스스로 발견하지는 못한다. 사용자가 운동별 또는 개인 맞춤
scoring을 원한다면, 점수를 smoke-test 이상으로 해석하기 전에 reference recording,
reviewed-good example, 또는 custom tolerance 값을 직접 수집하고 문서화해야 한다.

따라서 baseline 생성은 tier로 구분한다.

```text
exercise_prior
    Definition, 문헌, 전문가 지식 기반 expected range. Feature selection,
    warning, availability, QC에 사용한다. Composite-score baseline은 아니다.

provisional_baseline
    Synthetic data 또는 소수 reviewed sample로 만든 임시 기준. Scoring
    pipeline을 열어 deduction/withheld evidence와 sensitivity를 점검하는 데 쓴다.
    이 tier에서 나온 score는 provisional로 표시해야 한다.

reviewed_baseline
    같은 exercise definition, pose backend, feature schema, pipeline policy로
    생성한 여러 reviewed good-quality recording/rep 기반 기준. 연구 점수화에
    사용할 수 있는 첫 tier다.

locked_baseline
    논문/결과 snapshot을 위해 provenance와 함께 고정한 reviewed baseline.
    Exercise definition, feature schema, preprocessing, scoring policy가 바뀌면
    새 baseline version이 필요하다.
```

현재 `baseline_zscore.json` schema는 metric statistics만 저장하며 backward-compatible active
metrics store로 유지한다. 새로운 생성 흐름은 numeric metric statistics와 사람이 검토할
metadata를 분리한 generated baseline bundle을 먼저 저장해야 한다.

```text
data/reference/baselines/<baseline_id>/
    baseline.yaml      검토 가능한 metadata, status, path
    metrics.json       { metric_id: {"mean": float, "std": float} }
    qc.json            included/withheld metric audit 및 source provenance
```

`baseline.yaml`에는 다음 정보를 기록한다.

```text
exercise_id
definition_version
baseline_status          provisional | reviewed | locked
source_type              synthetic | reviewed_recordings | mixed
source_mode              current_run | single_file | manifest
pose_backend             mediapipe | yolo | other
coordinate_mode          기본값 norm
camera_view_family       front | front_oblique | side | rear_oblique | unknown
camera_height_level      H1 | H2 | H3 | unknown
framing_scope            full_body | lower_body | upper_body | unknown
view_match_source        body-direction inference가 아닌 protocol_metadata
recording_count
rep_count
included_metric_count
withheld_metric_count
created_from_manifest
created_at
pipeline_version_or_commit
metrics_path
qc_path
active_for_scoring       생성 baseline은 승격 전까지 false
used_for_current_scoring current-run provisional bootstrap일 때만 true
```

새 authoring 운동의 권장 흐름:

```text
운동 정의 작성
→ stage check 및 feature/biomech extraction 실행
→ synthetic 또는 reviewed-good example로 provisional baseline 생성
→ score sensitivity, deduction, withheld evidence 점검
→ 대표성 있는 실행 데이터가 충분해진 뒤 reviewed baseline으로 승격
```

---

## 8. Baseline Generation Procedure

Baseline generation은 hidden exercise-specific branch가 아니라 exercise definition과 reviewed
recording manifest를 기준으로 동작해야 한다.

현재 구현에서는 이 절차를 `scripts/generate_baseline.py`로 명시적으로 실행하거나,
`biomarker.baseline_generation.enabled`가 true일 때 ⑩ 내부에서 자동 실행할 수 있다. 자동 생성은
현재 `source_mode = current_run`을 지원한다. 이 모드는 scoring path를 열기 위한 provisional
bootstrap이지 reviewed reference baseline이 아니다. Reviewed baseline은 여전히 사용자가 제공한
reference recording 또는 manifest가 필요하다.

필수 절차:

```text
1. Canonical exercise definition 및 protocol 파일을 로드한다.
2. Baseline source recording/rep manifest를 읽는다.
3. Evaluation과 같은 ①-⑨ pipeline을 실행한다.
4. FeatureRecord와 BiomechRecord row를 수집한다.
5. Effective scoring gravity가 0이 아닌 record만 포함한다. 즉 `availability == assessed`
   record도 depth-dependency gravity 정책을 통과하며, low_confidence record는 low-confidence와
   depth-dependency gravity가 모두 0보다 클 때만 포함한다.
6. 모든 low_confidence/not_assessed row는 baseline QC로 보존한다. Provisional statistics에
   포함된 low-confidence row도 해당 상태를 숨기지 않고 계속 표시해야 한다.
7. Scoring σ floor를 적용해 metric별 mean/std를 계산한다.
8. Generated baseline bundle(`baseline.yaml`, `metrics.json`, `qc.json`)을 저장한다.
9. 명시적 승격 또는 개발용 호환 단계가 있을 때만 generated metrics를 backward-compatible active
   `baseline_zscore.json`에 mirror한다.
10. Held-out example에서 ⑩을 다시 실행해 score scale과 deduction을 점검한다.
```

`source_mode = current_run`은 현재 pipeline에서 이미 계산된 FeatureRecord와 BiomechRecord row를
임시 reference로 사용한다. 이 모드는 default metadata를 채워 완전한 baseline bundle을 만들 수
있지만 self-reference다. 따라서 `provisional`로 표시하고 inspection에 사용해야 하며, 연구 점수화
전에는 synthetic/reference/reviewed-good material로 대체해야 한다.

`scripts/generate_baseline.py`를 baseline-generation entry point로 사용한다. 이 이름은
"compute"보다 연구 workflow를 더 정확히 드러낸다. 즉 script는 active 기준값을 조용히
확정하는 것이 아니라, 검토할 provisional 또는 reviewed baseline bundle을 생성한다.

---

## 9. Audit Fields

`deductions`는 scoring에 사용된 feature가 domain score에 어떤 영향을 줬는지 설명한다.
노트북과 UI review를 위해 같은 항목은 `_biomarker_score_items.csv`에도 scored feature당
한 row로 펼쳐 저장한다.

```python
{
    "domain": "spatial",
    "feature_id": "spatial.range_of_motion.xy.left_knee_angle",
    "item_score": 99.73,
    "landmark_ids": ["left_hip", "left_knee", "left_ankle"],
    "evaluation_domain": "recording_view_only",
    "evidence_axes": "xy",
    "value": 85.4,
    "baseline_mean": 92.1,
    "baseline_std": 3.5,
    "z": -1.91,
    "weight": 0.143,
    "feature_family": "range_of_motion",
    "feature_family_weight": 0.65,
    "deduction": 0.273,
}
```

`withheld_features`는 계산됐지만 score에는 들어가지 않은 metric의 이유를 설명한다.
`reasons` field는 feature availability reason을 보존하며, feature family가 명시적 score gravity로
withheld된 경우 `feature_score_weight_zero` 같은 scoring policy reason을 추가할 수 있다.

```python
{
    "feature_id": "spatial.role_alignment.left_right.range_of_motion_xy.knee",
    "value": 0.31,
    "availability": "low_confidence",
    "view_reliability": "low",
    "camera_zone": "Z3",
    "depth_dependency": "high",
    "model_depth_reliability": "low",
    "landmark_ids": ["left_knee", "right_knee"],
    "evaluation_domain": "dual_domain_compare",
    "evidence_axes": "xyz",
    "reasons": ["view_metric_low"],
}
```

Reporting과 visualization은 두 목록을 모두 보여줘야 한다. 하나는 "왜 감점됐는가"를, 다른
하나는 "왜 계산된 metric이 점수에 들어가지 않았는가"를 설명한다.

---

## 10. 진입점 (Entry Point)

```python
from movement.biomarker import derive_biomarkers

biomarker_records, score_records = derive_biomarkers(
    feat_records,
    biomech_records,
    exercise_definition,
    definition_version=exercise_definition.version,
    baseline_path=None,
    domain_weights=None,
    score_bounds=None,
)
```

동작:

```text
항상 pass-through BiomarkerRecord를 반환한다.
baseline file 또는 exercise entry가 없으면 score_records는 빈 목록이다.
rep_id별로 독립 산출하고, 필요하면 sequence-level score로 fallback한다.
```

---

## 11. Provenance And Clinical Boundary

```text
BiomarkerRecord.source_fields       FeatureRecord/BiomechRecord에서 상속
BiomarkerScoreRecord.source_fields  feature_domains, biomechanical_focus,
                                    quality_rules, baseline file, score config
```

Composite score는 functional movement assessment 구조를 참고할 수 있지만 FMS/OAB 점수와 직접
비교할 수 없다. Clinical diagnosis, patient classification, clinical significance claim으로
표현하지 않는다.

---

## 12. 코드 매핑 (Code Mapping)

```text
src/movement/biomarker/__init__.py        BiomarkerRecord, derive_biomarkers,
                                          save_biomarker_outputs
src/movement/biomarker/scoring.py         BiomarkerScoreRecord, baseline IO,
                                          scoring, score bounds, weights
src/movement/record_metadata.py           공유 record context metadata field
src/movement/biomarker/interpretation.py  YAML rule loader and InterpretationRecord
data/definitions/interpretation_rules/    per-exercise interpretation rules
scripts/generate_baseline.py              baseline generator
data/reference/baseline_zscore.json       현재 metric-statistics 저장소
tests/test_biomarker_scoring_weights.py   weights and bounds
tests/test_biomarker_scoring_availability.py availability gravity and withheld audit
tests/test_interpretation.py              rule engine behavior
```

---

## 13. 향후 확장 (Planned Extensions)

- Baseline manifest input 및 baseline QC metadata output.
- Baseline tier label: `provisional`, `reviewed`, `locked`.
- Exercise definition과 feature schema 기반 baseline version guard.
- Phase-aware feature 근거가 안정화된 뒤 phase-specific sub-score 추가.
- Sensitivity analysis 이후 exercise-specific domain-weight profile 추가.
- Synthetic fallback을 보존하면서 real cohort baseline 지원.
- Set-level trend record로 within-set fatigue 또는 consistency 분석.
