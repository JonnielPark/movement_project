# 08. 피처 추출 (Feature Extraction)

**문서 버전:** 1.4.0
**최종 갱신:** 2026-07-04
**영문 동기화:** `docs_eng/pipeline/08_feature_extraction.md`는 동일 버전의 영문 번역본이다.

파이프라인 단계 ⑧은 정규화된 pose 데이터에서 movement-quality feature를 계산한다. Pose 좌표는
수정하지 않는다. 모든 출력은 numeric value, unit, `source_fields`, availability/reliability
metadata를 가진 `FeatureRecord`이며, ⑩ Biomarker Derivation이 provenance를 추적할 수 있게 한다.

---

## 1. 파이프라인 위치 (Pipeline Position)

```text
⑤ Normalization → ⑥ Canonicalization → ⑦ Segmentation
→ ⑧ Feature Extraction     ← 본 단계
→ ⑨ Biomech Proxy → ⑩ Biomarker Derivation
```

필수 입력:

```text
<landmark>_norm_x/y/z       정규화 좌표
rep_id                      확정된 반복 label
phase                       ⑦에서 온 선택 phase label
exercise_definition         feature_domains, angle_definitions,
                            compensation_candidates, support context,
                            view_metric_reliability
recording provenance        camera_zone, camera_height_level이 있으면 사용
preprocessing context       visibility, swap risk, far-side jitter, availability hooks
role context settings       laterality, execution pattern, side sequence
```

---

## 2. 설계 계약 (Design Contract)

허용:

```text
YAML angle_definitions 기반 joint included angle
반복 단위 및 phase 단위 집계
Registry 기반 compensation candidate dispatch
Feature availability/reliability metadata
Closed-chain support-consistency axis path diagnostics
source_fields provenance
degree, second, dimensionless, dimensionless_cv, torso_length_ratio 단위
```

금지:

```text
feature code에서 exercise_id로 분기
source_fields 없는 FeatureRecord
절대 force/torque/length 출력
camera-view 한계를 movement-quality penalty로 직접 변환
closed-chain support-consistency axis 3D path length를 직접적인 foot/hand motion으로 취급
feature ID에서 kinematic phase label과 kinetic phase 명칭 혼합
bilateral symmetric 운동에 active-side role context 적용
```

---

## 3. Feature Context Resolution

Feature Extraction은 side-role context resolution을 소유한다. 이는 score가 아니며, 더 이상 standalone
pipeline stage로 존재하지 않는다. 이는 feature family가 side role, confidence, provenance를 어떻게
해석할지 알려주는 정보다.

⑧의 첫 context substep은 다음 형태다:

```text
resolve_feature_context(df, exercise_definition, role_context_report=None)
apply_feature_context(records, feature_context)
```

개념적 출력:

```text
feature_context:
  laterality
  role_mode                 bilateral_symmetry | active_side | unavailable
  role_context              active_side, support_side, forward_leg, trailing_leg 등
  role_confidence           assessed | low_confidence | not_assessed
  context_reasons           provenance 문자열
```

정책:

```text
bilateral_symmetric
    active-side role detection을 실행하지 않는다. 좌우 movement quality를 비교하는 feature family를
    위해 bilateral symmetry / side-bias context를 제공한다.

alternating / unilateral_left / unilateral_right
    ⑧ 내부에서 segmented dataframe, performance_protocol.side_sequence, annotation context를 이용해
    side-role context를 해석한다.

unilateral_unspecified / bilateral_asymmetric / unsupported
    강한 side role을 만들지 않는다. conditional 또는 not-yet-supported provenance를 방출하고,
    값의 assessed 여부는 feature availability가 결정하게 한다.
```

이 context-resolution substep은 좌표를 수정하거나, rep/phase를 다시 라벨링하거나, score를 만들거나,
`exercise_id`로 분기하면 안 된다.

통합 정책:

```text
⑧ owns feature-facing interpretation
    Feature Extraction 내부에서 side-role context를 해석하고, feature family가 유용하다고 선언한
    곳에만 role_context를 부착하며, confidence/provenance는 numeric feature value와 분리한다.

public notebook review
    Side-role context와 feature record를 `27_feature_extraction_test.ipynb`에서 함께 검증한다.
```

Context application은 의도적으로 좁게 적용한다:

```text
spatial.role_alignment.*
    role_mode == bilateral_symmetry이면 bilateral symmetry context를 부착한다.
    이는 좌우 비교 provenance를 명시할 뿐, numeric role-alignment value나 low-confidence depth gate를
    바꾸지 않는다.

alternating / unilateral active-side records
    side-role evidence가 있을 때만 active-side context를 부착한다.
    Ambiguous 또는 missing context는 강한 side role이 아니라 provenance로 남긴다.

그 외 records
    향후 feature family가 context requirement를 명시하기 전까지 기존 role_context를 보존한다.
```

---

## 4. 피처 계열 (Feature Families)

Domain은 `feature_id` prefix로 표시한다.

```text
spatial.*
    range of motion, movement path, support consistency, role alignment,
    alignment/depth proxy.

temporal.*
    rep duration, phase duration, tempo variability, rhythm/smoothness proxy.

control.*
    hip-center stability와 knee_valgus, knee_varus, lateral_pelvic_shift,
    excessive_trunk_flexion, heel_lift, pelvis_rotation 같은 compensation candidate.
```

`feature_domains.biomechanical_proxy`는 ⑧ extractor 누락이 아니라 ⑨ Biomech Proxy로 전달되는
항목이다.

Depth-sensitive feature는 extraction 단계에서 버리지 않는다. ⑧은 `depth_dependency`,
`availability`, reliability metadata를 붙여 방출하고, ⑩이 score gravity를 결정한다. 이렇게 하면
evidence는 보존하면서 recording-view-heavy scoring policy를 적용할 수 있다.

Feature identifier는 특정 반복이 아니라 측정한 metric을 설명한다. Per-rep feature에서
`rep_id`는 record field로 운반하며 `feature_id` 안에 넣지 않는다. 이렇게 해야 반복 수가 다른
recording도 같은 baseline metric과 안정적으로 매칭된다.

```text
temporal.tempo.rep_duration       한 반복의 duration in seconds
temporal.variability.tempo_cv     sequence-level coefficient of variation
```

`temporal.tempo.rep_3` 같은 rep-indexed metric id는 피한다. Rep 3을 rep 1과 다른 metric처럼
만들기 때문에 baseline에 앞쪽 반복 id만 있을 때 temporal score가 false 100점으로 보일 수 있다.

Phase-level temporal id는 ⑦ Segmentation이 방출한 운동정의 기반 phase label을 사용한다.
현재 phase-level duration row는 다른 phase-aware feature family와 같은 phase-suffix 방식을 유지해
예를 들어 `temporal.tempo.rep_duration.descent`처럼 기록하고, `phase`는 record metadata로 남긴다.
Rep-level phase-profile summary는 가능한 경우
`exercise_definition.phase_segmentation.phase_sequence`에서 label pair를 가져와야 하며, squat 전용
label을 하드코딩하지 않는다.

Temporal record도 spatial record와 같은 public/private 분리를 따른다. 다만 첫 계약은 의도적으로
작게 둔다:

```text
temporal public/common fields
    landmark_ids          향후 특정 landmark에 묶인 timing metric이 생기기 전까지 []
    support_role          unknown
    coordinate_reference  timestamp
    evaluation_domain     timing_only
    evidence_axes         time
    feature_family        tempo | variability | phase_profile
```

현재 temporal private family:

```text
tempo
    temporal.tempo.rep_duration
    timestamp와 rep boundary evidence에서 확정 반복 하나의 duration을 측정한다.
    `rep_id`는 record metadata이며 feature id에 넣지 않는다.

variability
    temporal.variability.tempo_cv
    rep duration 간 sequence-level coefficient of variation을 측정한다.
    현재 첫 rhythm/repeatability signal로 사용한다. Per-rep score audit에서는 같은 sequence-level
    값을 각 rep에 복사해 보여줄 수 있다. 이는 rep마다 별도의 CV가 있다는 뜻이 아니라, set-level
    rhythm penalty를 각 rep score에서 확인 가능하게 하기 위한 것이다.

phase_profile
    temporal.phase_profile.duration_ratio.<phase_a>_<phase_b>
    운동정의가 지정한 두 phase duration의 ratio를 측정한다. Descent/Ascent resistance 운동에서는
    `temporal.phase_profile.duration_ratio.descent_ascent`가 되고, lift/tap/return template에서는
    같은 규칙으로 `lift_return`을 만들 수 있다. `Hold` 하나만 있는 static-hold template은 duration
    ratio를 방출하지 않는다.
```

Temporal source field는 timing family와 계산에 사용한 upstream label을 구분해야 한다:

```text
temporal.tempo.rep_duration
    feature_domains.temporal.tempo
    segmentation.rep_id
    timestamp

temporal.variability.tempo_cv
    feature_domains.temporal.variability
    temporal.tempo.rep_duration

temporal.phase_profile.duration_ratio.<phase_a>_<phase_b>
    feature_domains.temporal.phase_profile
    phase_segmentation.phase_sequence
    temporal.tempo.rep_duration.<phase_a>
    temporal.tempo.rep_duration.<phase_b>
```

이렇게 하면 temporal record는 점수화에 사용할 수 있으면서도 좁은 absolute-speed 해석을 피할 수
있다. 기본 scoring intent는 다음과 같다.

```text
tempo          넓은 acceptable-duration band; 명백한 timing outlier만 표시
variability    rep 간 rhythm/repeatability evidence
phase_profile  운동정의 phase label에서 나온 phase-ratio evidence
```

향후 static 및 alternating template도 같은 구조를 재사용해야 한다.

```text
static_hold
    temporal.tempo.rep_duration 또는 hold duration이 주요 timing metric이다.
    drift/correction subphase가 명시적으로 정의되고 검토되기 전까지 duration-ratio
    phase profile은 방출하지 않는다.

alternating / unilateral sequence
    rep duration은 반복 단위로 유지한다. 향후 private family는 side-sequence timing CV나
    left/right phase-ratio summary를 추가할 수 있다. 이때 side/phase label은 bilateral squat
    phase를 가정하지 말고 운동정의 또는 annotation protocol에서 읽어야 한다.
```

공통 record context metadata는 `feature_id` 문자열에서 매번 다시 추론하지 않고 ⑧에서 한 번 부착한 뒤
downstream으로 전달해야 한다. 이 필드들은 feature value나 score gravity를 직접 바꾸지 않는다.
대신 ⑩과 notebook에서 좌표 기준, evidence 경로, scoring 맥락을 명시적으로 확인할 수 있게 한다.

안정적인 해부학 정보는 각 feature row가 아니라 joint/landmark metadata registry에 둔다.
Feature row는 `landmark_ids`로 관련 landmark를 가리키고, report가 body-region, side,
paired landmark, default joint-action label이 필요할 때 registry와 join한다.

```text
Joint/landmark metadata registry
landmark_id           canonical landmark id. hip_center, shoulder_center,
                      whole_body_com 같은 derived id도 포함한다.
body_region           안정적인 anatomical/body region
side                  left | right | midline | derived | unknown
landmark_type         joint_center | surface_landmark | derived_center |
                      proxy | unknown
paired_with           적용 가능한 contralateral partner
proximal_landmarks    segment/joint 해석에 쓰는 실제 존재 proximal landmark id list.
                      active landmark set에 더 proximal한 점이 없으면 비운다.
distal_landmarks      segment/joint 해석에 쓰는 실제 존재 distal landmark id list.
                      active landmark set에 더 distal한 점이 없으면 비운다.
derived_from_landmarks hip_center 같은 derived center/proxy를 만드는 데 사용한
                      실제 landmark id list
segment_proximal      적용 가능한 proximal adjacent segment id list
segment_distal        적용 가능한 distal adjacent segment id list
default_joint_actions landmark와 연결되는 안정적인 namespaced anatomical actions.
                      예: ankle.dorsiflexion_plantarflexion
joint_profile         private joint/profile key. 예: ankle
support_capable       구조적으로 support가 가능하다는 정보일 뿐이다.
                      실제 support role은 운동 맥락에 따라 runtime에서 결정한다.
default_evidence_axes feature-specific override 전의 일반 evidence axes
default_depth_sensitivity low | moderate | high | unknown
```

Joint/profile별 private metadata는 별도 profile registry에 둔다. Profile 내부 action 이름은
local name이므로 profile 이름을 반복하지 않는다. Global id로 노출할 때만 profile namespace를
붙인다.
Profile registry는 일반 해부학 catalogue가 아니다. 현재 방출되는 feature template과 명시적으로
계획된 해석 후보만 유지한다. 예를 들어 knee profile은 knee range of motion, knee movement path,
knee role alignment,
`knee_valgus`/`knee_varus` compensation record가 구현되었거나 scoring review 계획에 들어 있으므로
`flexion_extension`과 `varus_valgus_proxy`를 유지한다. Axial knee rotation은 view-supported feature와
reliability policy가 생기기 전까지 제외한다.

같은 최소 규칙을 모든 joint profile에 적용한다:

```text
hip                  hip flexion/extension, hip range of motion, hip movement path,
                     hip role alignment만 유지한다. View-supported feature가 생기기
                     전까지 hip rotation/abduction은 제외한다.
pelvis_reference     운동정의에서 control/review 개념으로 이미 쓰는 derived
                     control, lateral-tilt, AP-tilt, rotation, weight-shift
                     proxy를 유지한다. Depth-heavy pelvis rotation은
                     low-confidence evidence로 둔다.
trunk_reference      운동정의와 compensation review path에 등장하는 trunk
                     flexion/extension, lateral-flexion, rotation proxy를 유지한다.
shoulder             shoulder flexion/extension과 scapular stability proxy를 유지한다.
                     Feature와 reliability policy가 정의되기 전까지 일반 shoulder
                     rotation은 추가하지 않는다.
elbow                elbow flexion/extension과 계획된 elbow-tracking 후보만 유지하고,
                     pronation/supination은 제외한다.
wrist                endpoint/support movement path와 wrist flexion extension만 유지하고,
                     radial/ulnar deviation은 제외한다.
support_base         derived support-consistency control만 유지한다.
whole_body_com       CoM range/path proxy만 유지한다.
```

```text
joint_profiles.ankle.anatomical_actions.primary
    dorsiflexion_plantarflexion

global/action id
    ankle.dorsiflexion_plantarflexion
```

MediaPipe-style foot direction evidence에는 `foot_progression_proxy`가 아니라
`foot_heading_proxy`를 사용한다. 이 proxy는 사용 가능한 ankle, heel, foot-index landmark에서
관찰되는 foot/toe heading을 뜻하며, 완전한 gait progression-angle 측정이 아니다.

Record-level field는 dynamic 또는 feature-specific 맥락만 유지한다:

```text
landmark_ids          record가 대표하는 landmark id list. Pure timing 또는
                      sequence-level aggregate record에서는 비어 있을 수 있다.
support_role          support_consistency | moving_landmark |
                      pelvis_reference | trunk_reference | whole_body_proxy |
                      joint_proxy | unknown
coordinate_reference  norm | norm_recording_view_xy | norm_model_depth |
                      corrected_3d_hypothesis | timestamp | derived_proxy |
                      unknown
evaluation_domain     recording_view_only | corrected_3d_hypothesis |
                      dual_domain_compare | timing_only | unknown
evidence_axes         x | y | z | xy | xz | yz | xyz | time | scalar | unknown
feature_family        range_of_motion | movement_path | support_consistency |
                      role_alignment | phase_profile | tempo | variability |
                      stability | compensation | proxy | other
```

`phase_profile`은 spatial 전용 개념이 아니라 domain-local summary layer다. 현재 구현은
template-specific descent/ascent range-of-motion ratio를 위한 `spatial.phase_profile.*`와
운동정의 phase-duration ratio를 위한 `temporal.phase_profile.*`를 방출한다. 다른 phase sequence는
descent/ascent 비교에 억지로 맞추지 말고 별도 summary rule을 정의해야 한다. 향후 예약 영역은
다음과 같다:

```text
control.phase_profile.*    phase별 compensation 또는 control tendency summary
biomech.phase_profile.*    phase별 CoM, moment-arm, load-shift summary
```

이 확장은 별도 테스트와 scoring 검토 후 활성화해야 하며, ⑧이 spatial 또는 temporal profile에서
자동 추론하지 않는다.

이 분리는 같은 해부학 사실을 두 번 저장하지 않기 위한 것이다. Range of motion는 measurement
geometry를 조금 더 명시해야 하는 예외다. Knee range 값은 단순한 knee point measurement가 아니라
`angle_definitions`의 proximal, vertex, distal landmark를 사용하는 3점 included-angle
measurement다. 따라서 range-of-motion record는 전체 angle triplet을 `landmark_ids`에 담고, 안정적인
해부학 해석은 landmark/profile registry에서 가져온다.

`evaluation_domain`은 보수적으로 유지해야 한다. MediaPipe `z`/`xyz`를 사용하는 record가 자동으로
corrected-3D-hypothesis record가 되는 것은 아니다. 보통은 `evidence_axes = z` 또는 `xyz`,
높은 `depth_dependency`를 함께 가지며, 향후 corrected candidate evidence와 비교할 의도가 있을
때만 `evaluation_domain = dual_domain_compare`로 둔다. 순수 timing record는 `timing_only`를 쓴다.

Range of motion는 movement-path evidence policy와 동일하게 명시적인 evidence variant를 방출한다.

```text
spatial.range_of_motion.xy.<joint_angle>
    Normalized camera-plane x/y에서 계산한 recording-view included-angle range of motion.
    Movement-quality 질문을 recording view에서 답할 수 있고 camera protocol이 호환될 때
    우선 scoring 후보로 사용한다.

spatial.range_of_motion.xyz.<joint_angle>
    Normalized x/y와 model/candidate z를 함께 쓰는 mixed-axis included-angle range of motion.
    Depth-sensitive comparative evidence이며, review와 향후 corrected-3D-hypothesis 비교에
    유용하다. Validation이 승격하기 전까지 matching `spatial.range_of_motion.xy.*` record보다 낮은
    score gravity를 받아야 한다.
```

두 variant 모두 원천 `angle_definitions.<joint_angle>` entry와 `proximal`, `vertex`,
`distal` landmark를 `source_fields`에 남겨야 한다. 예:

```text
spatial.range_of_motion.xy.left_knee_angle
    landmark_ids = [left_hip, left_knee, left_ankle]
    evidence_axes = xy
    evaluation_domain = recording_view_only

spatial.range_of_motion.xyz.left_knee_angle
    landmark_ids = [left_hip, left_knee, left_ankle]
    evidence_axes = xyz
    evaluation_domain = dual_domain_compare
```

Closed-chain support anchor는 별도 취급이 필요하다. Support context가 고정된 floor/ground
contact를 선언한 운동에서 support landmark의 누적 path length는 실제 지지점 이동보다 pose
jitter, monocular-depth drift, canonicalization residual이 크게 섞일 수 있다. 따라서 ⑧은
축이 숨겨진 movement-path 이름을 쓰지 않고 명시적인 movement-path evidence variant를 방출한다. 각
variant가 점수에 얼마나 기여할지는 ⑩ Scoring 단계가 결정한다.

```text
spatial.movement_path.arc_length_xy.<landmark>
    Recording-view support-consistency axis path evidence. 고정 closed-chain support에서는
    보통 diagnostic 또는 낮은 gravity evidence이지, foot/hand가 실제로 움직였다는
    직접 증거가 아니다.

spatial.movement_path.arc_length_xyz.<landmark>
    Recording-view/depth가 섞인 support-consistency axis path evidence. Monocular pose에서는
    depth-sensitive provenance이며, validation이 승격하기 전까지 withheld하거나 낮은
    score gravity를 부여해야 한다.

spatial.support_consistency.axis_path_x.<landmark>
spatial.support_consistency.axis_path_y.<landmark>
spatial.support_consistency.axis_path_z.<landmark>
spatial.support_consistency.axis_path_xy.<landmark>
    Closed-chain support anchor의 report-only diagnostic이다. Apparent support
    motion의 축별 출처를 드러내며, 기본적으로 baseline scoring에 사용하지 않는다.
```

Support-landmark path diagnostic은 `exercise_id` 분기가 아니라 exercise definition의 support
context에서 유도해야 한다.

Support-consistency feature는 support-consistency axis path diagnostic과 분리한다. 이는 `maintain_foot_contact`
같은 fixed-support exercise constraint를 recording-view x/y 일관성 feature로 변환한다. 기본적으로
monocular depth를 사용하지 않으며, baseline을 재생성한 뒤 별도 `support_consistency` family budget으로
scoring할 수 있다. 이 family는 CoP/CoM류 생체역학적 안정성 proxy로 해석하지 않으며, 부하 중심 또는
질량 중심 해석은 ⑨ Biomechanical Proxy에서 다룬다.

```text
spatial.support_consistency.point_drift_xy.<landmark>
    반복 또는 phase 안에서 support ankle/wrist가 median support position으로부터 recording-view
    x/y에서 얼마나 벗어났는지의 최대값.

spatial.support_consistency.width_variation_xy
    좌우 support anchor 사이 recording-view x/y 거리의 coefficient of variation.

spatial.support_consistency.center_drift_xy
    좌우 support center가 median support-center position으로부터 recording-view x/y에서 얼마나
    벗어났는지의 최대값.

spatial.role_alignment.left_right.support_consistency_xy_drift.<left_anchor>_<right_anchor>
    Support-point x/y drift의 좌우 차이를 stance width로 정규화한 값이다. 이는
    recording-view support-consistency role-alignment feature이며, depth-sensitive range-of-motion role alignment feature가 아니다.
```

Bilateral-foot squat에서 이 feature들은 ankle range of motion가 아니라 base-of-support consistency를
나타낸다. 따라서 support-consistency proxy로 해석하며,
`spatial.range_of_motion.xy.*_ankle_angle` 및 `spatial.range_of_motion.xyz.*_ankle_angle`과 분리한다.
Role-alignment variant는 availability gate가 assessed로 남을 때만 `role_alignment` scoring
family에 기여할 수 있다. Depth-sensitive role-alignment variant는 더 강한 view/depth evidence가
있기 전까지 scoring에 조심스럽게 사용한다.

Support consistency도 joint-level feature와 같은 public/private metadata 분리를 따른다:

```text
Public FeatureRecord fields
    feature_id             support_consistency metric id. 예:
                           spatial.support_consistency.point_drift_xy.left_ankle
    landmark_ids           측정한 support landmark 또는 derived support_center
                           reference. Stance-width record는 양쪽 anchor를 사용한다.
    support_role           support_consistency
    coordinate_reference   norm_recording_view_xy
    evaluation_domain      recording_view_only
    evidence_axes          xy
    feature_family         support_consistency. 단, support-consistency role-alignment row는
                           role_alignment family에 남긴다.
    depth_dependency       none
    source_fields          support context field와
                           support_consistency.recording_view_xy

Private registry/profile fields
    ankle/wrist profile    좌우 support-consistency point-drift template
    support_base profile   support-center drift와 stance-width variation template
    reliability_priors     view-specific support_consistency_xy prior
    stable anatomy         side, paired_with, body_region, default action label은
                           landmark/profile registry에 둔다.
```

이 분리는 support participation을 ankle 또는 wrist의 영구 해부학 속성으로 취급하지 않기 위한 것이다.
Wrist는 어떤 운동에서는 moving endpoint이고, 다른 운동에서는 support landmark일 수 있다. Runtime
record가 `support_role = support_consistency`를 받는지는 운동정의의 support context가 결정한다.

움직이는 primary landmark도 같은 explicit evidence-variant 정책을 따른다. Coordinate-derived
movement-path target은 최소한 `xy`와 `xyz` variant를 방출할 수 있어야 한다. 이렇게 하면
recording-view evidence와 depth-sensitive evidence를 같은 audit trail에 남기면서, 점수 반영
강도는 ⑩ Scoring 단계에서 조절할 수 있다.

```text
spatial.movement_path.arc_length_xy.<landmark>
    Normalized camera-plane의 recording-view movement path다. Movement-quality 질문이 x/y
    evidence로 답해질 수 있고 recording view가 baseline과 호환될 때 우선 scoring 후보가 된다.

spatial.movement_path.arc_length_xyz.<landmark>
    Normalized x/y와 model/candidate z를 함께 쓰는 mixed-axis movement path다. 이는
    depth-sensitive evidence이며 review와 candidate-3D 비교에는 유용하지만, 현재 monocular
    pipeline에서는 보통 `xy` variant보다 낮은 score gravity를 가져야 한다.

spatial.movement_path.axis_path_x.<landmark>
spatial.movement_path.axis_path_y.<landmark>
spatial.movement_path.axis_path_z.<landmark>
    Non-support primary landmark의 report-only movement-path-axis diagnostic이다.
    어떤 축이 movement-path value에 기여했는지 드러내며, 추후 validation study가 특정 축을
    승격하기 전까지 provenance로 남긴다.
```

Scoring 승격 규칙:

```text
diagnosis/reporting
    Path-length anomaly의 원인이 보이도록 xy, xyz, x, y, z evidence를 방출한다.

composite scoring
    운동정의와 camera view가 recording-view 해석을 뒷받침하면 `xy` movement path를 우선 사용한다.
    `xyz`는 낮은 gravity의 depth-sensitive evidence 또는 corrected-3D-hypothesis provenance로
    둔다. 같은 path를 중복 감점하지 않도록 `xy`, `z`, `xyz`를 동시에 full strength로
    scoring하지 않는다.
```

Pelvis와 hip-center proxy에는 명시적인 coordinate-reference guard가 필요하다.
운동정의가 hip flexion/extension을 선언하면 `left_hip`과 `right_hip`은 primary hip landmark로
남는다. 하지만 파생된 `pelvis` 또는 `hip_center` reference는 feature가 이를 primary task metric으로
명시하지 않는 한 secondary/control proxy다.

⑤ Normalization에서 좌표 원점으로 사용한 같은 reference point를 다시 측정하는 feature는
scoring-ready로 표시하지 않는다. Hip-centered `norm` 좌표계에서는 다음 feature가 자기 기준점
측정이 되어 값이 0에 가까워질 수 있으므로, 독립 reference에서 재정의되기 전까지 report-only로
둔다:

```text
control.stability.hip_center_x_std
control.stability.hip_center_z_std
control.compensation.lateral_pelvic_shift.xy
```

Closed-chain lower-body exercise에서는 support-relative pelvis proxy를 우선 대체안으로 사용한다.
이는 hip/pelvis center를 자기 자신이 아니라 운동정의의 support center와 recording-view x/y에서
비교해야 한다:

```text
control.stability.hip_center_support_center_xy_drift
    Hip_center가 bilateral support center에 대해 recording-view x/y에서 얼마나 이동했는지 나타낸다.
    이는 absolute camera-space translation이 아니라 base-of-support 위의 pelvis control proxy다.
```

Recording view와 운동정의가 뒷받침할 때는 추가 pelvis alignment proxy를 방출할 수 있다:

```text
control.compensation.pelvis_line_tilt
    Frontal-plane 해석이 가능한 recording-view plane에서 left-right hip height/line tilt를 보는 proxy.

control.compensation.pelvis_rotation.xyz
    Transverse-plane pelvis rotation proxy. Monocular depth와 near/far-side ordering이 이 신호를
    지배할 수 있으므로 view/candidate-evidence policy가 승격하기 전까지 low-gravity 또는
    report-only로 둔다.
```

운동정의와 emitted feature id에서는 `pelvis_rotation`을 일관되게 사용한다.
feature id는 안정적인 scoring key이므로 같은 의미의 형용사형 표기를 혼용하지 않는다.

Control record도 spatial/temporal record와 같은 public/private metadata 분리를 따른다.

```text
Public record fields
    feature_id, value, unit, availability, depth_dependency, focus_tier,
    landmark_ids, support_role, coordinate_reference, evaluation_domain,
    evidence_axes, feature_family

Private registry/profile fields
    knee profile      valgus/varus compensation link와 frontal-plane proxy
    ankle profile     heel-lift/support-contact compensation link
    pelvis_reference  derived pelvis-control과 rotation proxy 범위
    trunk_reference   trunk-flexion compensation proxy 범위
```

`control.compensation.heel_lift.xy.<side>`는 closed-chain support-contact proxy다.
현재 monocular pipeline에서는 model-depth `z`가 아니라 recording-view vertical axis를 사용해야 한다.
MediaPipe monocular depth만으로 heel이 지지면에서 들렸는지 판단하기에는 신뢰도가 충분하지 않기
때문이다. 향후 depth-sensitive heel-lift diagnostic이 필요하면 support-contact score를 조용히
재사용하지 말고, 별도 feature id와 낮은 gravity로 방출해야 한다.

좌표에서 파생되는 control record도 명시적인 evidence variant를 가진다. Recording-view candidate는
feature id에 `xy` 토큰을 사용하고, depth가 섞인 candidate는 `xyz` 토큰을 사용한다. `xyz`
candidate는 monocular model-depth reliability가 낮으면 낮은 gravity로 점수화하거나 withheld해야 한다.
좌표 기반 compensation에서 variant 없는 control feature id를 방출하면 recording-view evidence인지
model-depth evidence인지 숨기게 되므로 사용하지 않는다.

현재 control variant 계약:

```text
control.compensation.knee_valgus.xy.<side>
control.compensation.knee_varus.xy.<side>
    Recording-view hip-knee-ankle deviation proxy. 현재 squat/lunge knee tracking의 scoring
    candidate다. raw monocular depth에 기대지 않고 corrected/body-frontal plane에서 medial/lateral
    direction을 정의할 수 있기 전까지 `knee_valgus.xyz` 또는 `knee_varus.xyz` variant는 방출하지
    않는다.

control.compensation.excessive_trunk_flexion.xy
    Image vertical 기준 shoulder-center to hip-center trunk-line angle이다. Camera view가 sagittal
    해석을 뒷받침할 때 선호하는 public scoring candidate다.

control.compensation.excessive_trunk_flexion.xyz
    같은 recording-view vertical axis를 쓰지만 3D vector norm에 depth가 섞인 trunk-line angle이다.
    현재 monocular pipeline에서는 comparative evidence로만 쓰며 reduced gravity를 가져야 한다.

control.compensation.heel_lift.xy.<side>
    Support baseline 위 recording-view heel elevation이다. `xy` plane의 vertical component만 쓰므로
    `evidence_axes`는 `y`일 수 있다.

control.compensation.pelvis_rotation.xyz
    Left-right hip model-depth asymmetry에 기반한 depth-sensitive proxy다. View/candidate evidence가
    transverse-plane 해석을 뒷받침하기 전까지 low-confidence/report-only로 유지한다.
```

---

## 5. Availability And View Reliability

Feature extraction은 camera view 또는 pose model이 scoring을 뒷받침하지 않는 값도 계산할 수
있다. 따라서 `FeatureRecord.availability`가 ⑩ scoring gate다.

```text
assessed
    baseline이 있으면 composite scoring에 들어갈 수 있다.

low_confidence
    numeric value는 report할 수 있지만 기본적으로 composite scoring에서 withheld된다.

not_assessed
    scoring에 사용하지 않고 unavailable/provenance로만 보고한다.
```

Resolver가 결합하는 정보:

```text
view_reliability             exercise_definition.view_metric_reliability
landmark_quality             visibility / coverage / preprocessing context
depth_dependency             none | low | moderate | high | unknown
model_depth_reliability      high | moderate | low | unknown
swap or far-side risk         ④ Preprocessing과 ⑧ side-role context에서 제공
camera_zone                  annotation 또는 recording metadata
role_context                 active/support/near/far side가 있으면 사용
```

측면 또는 측면에 가까운 squat recording에서는 sagittal 및 centerline feature가 gate를 통과하면
assessed로 남을 수 있다. Rotated monocular skeleton에서 나온 depth-sensitive role-alignment evidence는
frontal/front-oblique evidence가 없으면 `low_confidence` 또는 `not_assessed`로 둔다.

편측 또는 교대 운동에서는 단순 anatomical left/right보다 `forward_leg`, `trailing_leg`,
`active_side`, `support_side` 같은 role label을 사용한다.

---

## 6. Phase-Aware Features

⑦이 `phase` column을 제공하면 다음 계열은 rep-level과 phase-level record를 모두 방출할 수 있다.

```text
spatial.range_of_motion
spatial.movement_path
temporal.tempo
control.stability
```

규칙:

```text
Rep-level record      phase = None
Phase-level record    phase = "Descent" 등; feature_id에 lower-snake-case suffix 추가
source_fields         phase_segmentation provenance 포함
control.compensation  별도 phase-specific rule이 없으면 rep-level only
```

`summarize_phase_to_rep()`는 해당 label을 명시적으로 사용하는 phase sequence에 대해
descent/ascent range-of-motion ratio 같은 파생 rep-level summary를 추가할 수 있다.
입력 record는 수정하지 않는다.
⑧ pipeline report는 이 파생 summary record를 직접 계산된 feature record 옆에 함께 포함한다.
따라서 저장 산출물과 downstream check가 같은 feature set을 사용한다.

---

## 7. 출력 계약 (Output Contract)

```python
@dataclass
class FeatureRecord:
    feature_id: str
    exercise_id: str
    rep_id: int | None
    value: float
    unit: str
    source_fields: list[str]
    note: str | None = None
    phase: str | None = None
    view_reliability: str = "unknown"
    availability: str = "assessed"
    availability_reasons: list[str] = field(default_factory=list)
    camera_zone: str | None = None
    role_context: dict[str, str] | None = None
    depth_dependency: str = "unknown"
    model_depth_reliability: str = "unknown"
    landmark_quality: str = "unknown"
    focus_tier: str = "primary"
    landmark_ids: list[str] = field(default_factory=list)
    support_role: str | None = None
    coordinate_reference: str = "unknown"
    evaluation_domain: str = "unknown"
    evidence_axes: str | None = None
    feature_family: str | None = None
```

`features_to_dataframe()`은 record 목록을 tabular output으로 펼치며 phase, availability,
camera-zone, provenance field를 보존한다.

저장되는 stage-check 산출물은 feature table과 diagnostic context를 분리해 둔다:

```text
data/processed/features/<recording_id>_features.csv
    `features_to_dataframe()` tabular output. 필수 column은 feature_id,
    exercise_id, rep_id, phase, value, unit, source_fields, availability,
    availability_reasons, view_reliability, depth_dependency,
    model_depth_reliability, landmark_quality, focus_tier, landmark_ids,
    support_role, coordinate_reference, evaluation_domain, evidence_axes,
    feature_family, camera_zone, role_context다.

data/processed/features/<recording_id>_feature_context.json
    ⑧의 feature-context 및 role-context report. Side-role context가 왜 적용,
    생략, withheld 되었는지를 기록하며 feature value를 바꾸거나 score를 만들지 않는다.

data/processed/features/<recording_id>_feature_qc.json
    Follow-along check용 compact count. row count, availability count,
    feature-family count, phase count, missing source_fields 등을 담는다.
```

CSV round-trip은 row count와 필수 column을 보존해야 한다. `source_fields`,
`availability_reasons`, `landmark_ids`, `role_context` 같은 구조화 field는 CSV 저장을 위해
직렬화할 수 있지만, 이후 code path의 canonical object contract는 in-memory record다.

---

## 8. 감사 리포트 (Audits)

⑧은 feature record 옆에 diagnostic audit를 방출할 수 있다.

```text
Feature registry coverage
    YAML feature_domain entry와 compensation candidate가 implemented, routed to another
    step, unsupported, declared but deferred 중 어디에 해당하는지 보고한다.

Analysis-disrupting pattern detectability
    performance_protocol.analysis_disrupting_patterns를
    pose_detectable_scoring_candidate, acquisition_control_factor,
    interpretation_limitation_factor, unknown으로 분류한다.
```

Audit는 provenance/reporting 출력이다. 좌표를 바꾸거나 반복을 제외하거나 점수를 만들지 않는다.

---

## 9. 진입점 (Entry Point)

```python
from movement.features import (
    extract_rep_features,
    features_to_dataframe,
    summarize_phase_to_rep,
)

records = extract_rep_features(df, exercise_definition)
records += summarize_phase_to_rep(records)
feat_df = features_to_dataframe(records)
```

---

## 10. 다른 단계와의 관계 (Relationship To Other Steps)

- ⑦ Segmentation은 `rep_id`와 선택 `phase`를 제공한다. Phase label이 없으면 rep-level feature만
  산출한다.
- Side-role context는 ⑧ 내부에서 해석된 뒤 role-aware feature record에만 부착된다.
  Public stage-check 경로에서는 이 context를 `27_feature_extraction_test.ipynb`에서 검토한다.
- ⑨ Biomech Proxy는 같은 정규화 좌표를 사용하지만 `FeatureRecord`가 아니라 `BiomechRecord`를
  방출한다.
- ⑩ Biomarker Derivation은 모든 feature를 pass-through biomarker로 감싸고,
  `availability == assessed`인 feature만 composite scoring에 사용한다.
- ⑫ Simulation은 pose-detectable audit entry를 perturbation candidate로 사용할 수 있다.

---

## 11. 코드 매핑 (Code Mapping)

```text
src/movement/features/__init__.py        FeatureRecord, extract_rep_features,
                                         FeatureContext, resolve_feature_context,
                                         apply_feature_context,
                                         audits, summarize_phase_to_rep,
                                         features_to_dataframe
src/movement/features/spatial.py         range of motion, movement path,
                                         support consistency, role alignment
src/movement/features/temporal.py        tempo, variability
src/movement/features/control.py         stability, compensation
src/movement/features/compensation.py    COMPENSATION_RULES registry
src/movement/record_metadata.py          record context와 landmark-id helper
data/reference/landmarks/common_landmark_metadata.yaml
                                         안정적인 joint/landmark metadata registry
data/reference/landmarks/joint_profiles.yaml
                                         joint/profile별 private metadata
tests/test_feature_view_reliability.py   availability metadata
tests/test_feature_registry_coverage.py  feature/compensation coverage audit
tests/test_analysis_disrupting_patterns.py detectability audit
tests/test_features_phase_grouping.py    phase-level feature behavior
tests/test_feature_context_resolution.py feature-context resolution/application
```

---

## 12. 향후 확장 (Planned Extensions)

- Alternating/unilateral sample을 검토한 뒤 side-role context를 bilateral provenance에서
  active/support-side feature family로 확장한다.
- source fields, visibility policy, test가 준비된 compensation rule 추가.
- coarse preprocessing summary 대신 per-feature landmark coverage 사용.
- lunge와 plank shoulder tap을 위한 role-aware feature family.
- scored feature와 computed-but-withheld feature를 함께 보여주는 reporting view.
