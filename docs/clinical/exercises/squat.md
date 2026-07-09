# 스쿼트 상세 해석 배경 (Squat Clinical Rationale)

**문서 버전:** 1.2.0
**최종 갱신:** 2026-06-10
**영문 동기화:** `docs_eng/clinical/exercises/squat.md`는 동일 버전의 영문 번역본이다.

본 문서는 본 연구에서 스쿼트를 포함하는 이유와 동작 패턴 해석 방식을 요약한다.
진단 기준도 아니고 코드 명세도 아니다.

관련 문서:

- 수행 프로토콜: [exercise_performance_protocol.md](../../practical_protocols/exercise_performance_protocol.md)
- 운동 YAML: [squat.yaml](../../../data/definitions/exercises/squat.yaml)
- 분석 프로파일: [squat.yaml](../../../data/definitions/analysis_profiles/squat.yaml)
- Feature meaning map: [per_exercise_mapping.md](../per_exercise_mapping.md)

---

## 1. 연구 내 역할 (Study Role)

스쿼트는 양측 하지 reference task이다. 단안 포즈 데이터에서 hip-knee-ankle coordination,
descent depth, trunk alignment, hip-center stability, 좌우 symmetry를 관찰하는 데 사용한다.

본 프로젝트에서의 가치는 방법론적이다. 반복 구조가 명확하고 흔한 보상 패턴이 관찰되기 쉽다.
임상적 정상 기준을 정의하지 않는다.

## 2. 실행 컨텍스트 (Execution Context)

| Item | Current setting | Interpretation intent |
|---|---|---|
| Classification | bilateral symmetric, standing closed-chain | 양측 하지 coordination reference task |
| Primary joints | hip, knee, ankle | triple flexion/extension 및 하지 alignment |
| Segmentation | hip-center vertical trajectory, descent/ascent | 반복 cycle 검증이 쉬운 구조 |
| Camera | Z2/Z8, H2 | knee tracking과 depth를 함께 보는 절충 view |
| Main feature families | ROM, symmetry, arc length, tempo, stability, compensation | spatial/temporal/control 전반 검증 |
| Biomech focus | vertical CoM, hip/knee/ankle load regions | 상대 load-distribution proxy만 해석 |

실행 기준은 이 해석 문장이 아니라 YAML이다.

## 3. 관찰 대상 (Observation Targets)

```text
descent depth              hip_center 및 hip/knee/ankle ROM
knee tracking              hip-knee-ankle line
heel contact               heel/ankle/foot landmarks
trunk lean                 shoulder-hip line
lateral pelvic shift       hip_center x trajectory
bilateral symmetry         left/right hip, knee, ankle features
```

기대 수행은 데이터 취득 reference이다: 안정된 foot contact, 협응된 hip/knee/ankle flexion,
일관된 depth/tempo, 과도하지 않은 trunk folding.

## 4. 보상 패턴 (Compensation Patterns)

| Pattern | Interpretation direction | Detectability | Status |
|---|---|---|---|
| knee valgus | 부하 중 medial knee-deviation proxy | frontal/front-oblique에서 높음 | 구현 패턴 |
| knee varus | lateral knee-deviation proxy; stance/view 민감 | 중간 | 제한 포함 구현 패턴 |
| excessive trunk flexion | forward trunk-lean strategy | side/front-oblique에서 높음 | 구현 패턴 |
| lateral pelvic shift | weight-shift proxy | 중간; view 의존 | 구현 패턴 |
| heel lift | ankle/forefoot-loading proxy | 중간; heel confidence 의존 | 구현 패턴 |
| pelvic rotation | hip-depth asymmetry proxy | 낮음-중간; depth 민감 | 주의 포함 구현 패턴 |
| arm swing | 상지 momentum이 하지 trajectory를 오염 | 중간 | control factor |
| unstable foot contact | support 변화로 비교 가능성 저하 | 낮음-중간 | control/limitation factor |

위 용어는 movement-quality proxy이지 진단이 아니다.

## 5. View 및 품질 제한 (View And Quality Limits)

Front-oblique view가 기본 절충안이다. 더 frontal한 view는 frontal knee/pelvis alignment를,
더 side에 가까운 view는 depth, sagittal ROM, trunk lean, heel-lift review를 강화한다.

Side-view 또는 near-side-view recording에서는 bilateral symmetry가 view-dependent이다.
회전시킨 단안 3D rendering은 직접 정면 근거를 만들지 않는다. far-side confidence, depth
plausibility, swap risk가 충분하지 않으면 symmetry feature는 `low_confidence` 또는
`not_assessed`로 처리한다.

View support가 약하면 다음 sagittal/centerline feature를 우선한다:

```text
descent depth
hip/knee/ankle ROM
trunk lean
heel lift
hip-center trajectory stability
tempo and smoothness
```

## 6. p01 Squat Feature-Domain Table

이 표는 corrected coordinate를 feature extraction, biomechanical proxy, scoring에 사용하기 전의
현재 p01 squat gate다. `corrected_3d_hypothesis` row는 analysis evidence일 뿐이며, scoring weight는
이후 scoring policy로 defer한다.

| feature_id | evaluation_domain | source_evidence | active_constraints | cap_strength | expected_output | confidence/burden rule |
|---|---|---|---|---|---|---|
| `spatial.range_of_motion.xy.left_hip_angle`, `spatial.range_of_motion.xy.right_hip_angle` | `recording_view_only` | `norm` camera-plane hip/shoulder/knee trajectory; phase label이 있으면 함께 사용 | hip/knee/shoulder confidence, valid rep/phase segmentation, sagittal motion을 지지하는 view | 없음 | rep/phase별 degree ROM | Source landmark가 보이고 swap/far-side warning이 지배적이지 않을 때만 점수화 가능 feature로 사용한다. |
| `spatial.range_of_motion.xy.left_knee_angle`, `spatial.range_of_motion.xy.right_knee_angle` | `recording_view_only` | `norm` camera-plane hip-knee-ankle trajectory | hip/knee/ankle confidence, valid rep/phase segmentation, bend-flip provenance flag 없음 | 없음 | rep/phase별 degree ROM | Knee bend-side 또는 far-side evidence가 불안정하면 provenance 또는 `low_confidence`로 둔다. |
| `spatial.range_of_motion.xy.left_ankle_angle`, `spatial.range_of_motion.xy.right_ankle_angle` | `recording_view_only` | `norm` camera-plane knee-ankle-foot movement path | knee/ankle/foot confidence, heel/foot confidence, valid rep/phase segmentation | 없음 | rep/phase별 degree range of motion | Foot landmark가 불안정하거나 support-consistency evidence가 약하면 withhold 또는 confidence downgrade한다. |
| `spatial.role_alignment.left_right.range_of_motion_xy.hip`, `spatial.role_alignment.left_right.range_of_motion_xy.knee`, `spatial.role_alignment.left_right.range_of_motion_xy.ankle` | `dual_domain_compare` | 좌우 recording-view ROM; 이후 optional corrected-coordinate comparison | bilateral squat context, 양측 confidence 충분, high correction burden 없음 | corrected comparison은 report-only delta | dimensionless role-alignment index | 양측이 view-supported일 때만 recording-view left/right alignment를 점수화 가능 feature로 사용한다. Corrected 사용 전 norm-vs-corrected delta를 보고한다. |
| `spatial.movement_path.arc_length_xy.left_hip`, `spatial.movement_path.arc_length_xy.right_hip` | `recording_view_only` | `norm` camera-plane hip trajectory | valid rep/phase segmentation, hip confidence, baseline-compatible view | 없음 | torso-length ratio recording-view trajectory arc length | Pelvis confidence, segmentation, camera-view compatibility가 불안정하면 confidence를 낮춘다. |
| `spatial.movement_path.arc_length_xy.left_knee`, `spatial.movement_path.arc_length_xy.right_knee` | `recording_view_only` | `norm` camera-plane knee trajectory | knee confidence, valid rep/phase segmentation, knee tracking을 지지하는 view | 없음 | torso-length ratio recording-view trajectory arc length | Far-side knee arc는 occlusion/swap risk가 높으면 `low_confidence`로 둔다. |
| `spatial.movement_path.arc_length_xyz.*` trajectory variant | `dual_domain_compare` | recording-view/depth가 섞인 trajectory; 이후 optional corrected-coordinate comparison | source landmark confidence, depth provenance, 사용 전 correction-burden report | low-weight/analysis evidence | torso-length ratio mixed-axis trajectory arc length | 대응되는 `xy` variant와 동시에 full strength로 scoring하지 않는다. Validation 전까지 depth-sensitive provenance로 둔다. |
| `spatial.movement_path.arc_length_xy.left_ankle`, `spatial.movement_path.arc_length_xy.right_ankle` | `recording_view_only` | recording-view ankle support-landmark movement path | closed-chain support context, ankle/foot confidence, planted-support provenance | low-weight/support-consistency context | torso-length ratio apparent support-landmark path | Squat에서는 support consistency에 `spatial.support_consistency.*`를 우선 사용한다. Ankle movement path는 ankle range of motion가 아니다. |
| `spatial.phase_profile.range_of_motion_ratio.descent_ascent` | `recording_view_only` | 확정된 descent/ascent label의 phase-level ROM record | valid phase segmentation, 양 phase의 충분한 ROM record | 없음 | descent/ascent ratio | Phase segmentation이 failed, manually uncertain, 또는 너무 짧으면 withhold한다. |
| `temporal.tempo.rep_*`, `temporal.variability.tempo_cv` | `recording_view_only` | timestamp와 rep boundary | valid annotation 또는 accepted rep segmentation | 없음 | seconds; dimensionless CV | Depth와 무관하다. Availability는 rep boundary reliability에 의존한다. |
| `control.stability.hip_center_x_std` | `recording_view_only` | `norm` camera-plane hip-center lateral trajectory | 양측 hip confidence, valid rep/phase segmentation | 없음 | torso-length ratio | Pelvis x trajectory가 보이고 swap/interpolation에 지배되지 않을 때 점수화 가능 feature로 사용한다. |
| `control.stability.hip_center_z_std` | `dual_domain_compare` | 현재 model-depth axis와 향후 corrected-coordinate comparison | depth evidence는 low-confidence; scoring 전 norm-vs-corrected sensitivity 필요 | analysis evidence only | torso-length ratio | 현재 public path에서는 corrected depth가 score에 영향 주지 않는다. Sensitivity와 availability만 보고한다. |
| `control.compensation.knee_valgus.xy.left`, `control.compensation.knee_valgus.xy.right` | `recording_view_only` | hip-ankle line 대비 camera-plane knee deviation | frontal/front-oblique view support, hip/knee/ankle confidence | 없음 | torso-length ratio peak medial deviation | Frontal knee tracking을 지지하는 view에서만 점수화 가능 feature로 사용한다. Side-view 결과는 provenance 또는 `not_assessed`다. |
| `control.compensation.knee_varus.xy.left`, `control.compensation.knee_varus.xy.right` | `recording_view_only` | hip-ankle line 대비 camera-plane knee deviation | knee valgus와 동일; stance width는 context로 검토 | 없음 | torso-length ratio peak lateral deviation | Support stance가 view-sensitive하거나 far-side landmark가 불안정하면 confidence를 낮춘다. |
| `control.compensation.excessive_trunk_flexion.xy` | `recording_view_only` | camera-plane shoulder-hip trunk line | shoulder/hip confidence, sagittal trunk lean을 지지하는 view | 없음 | peak trunk angle in degrees | Shoulder/hip landmark가 안정적이면 sagittal/centerline feature로 점수화 가능 feature가 된다. |
| `control.compensation.excessive_trunk_flexion.xyz` | `dual_domain_compare` | depth-mixed shoulder-hip trunk line | shoulder/hip confidence, depth-sensitive comparison only | 없음 | peak trunk angle in degrees | corrected-3D 또는 multi-view validation이 승격하기 전까지 low-weight로 둔다. |
| `control.compensation.lateral_pelvic_shift.xy` | `recording_view_only` | `norm` camera-plane hip-center lateral displacement | bilateral hip confidence, valid rep segmentation | 없음 | torso-length ratio peak lateral displacement | Landmark 품질 때문에 pelvis center가 불안정하면 confidence를 낮춘다. |
| `control.compensation.heel_lift.xy.left`, `control.compensation.heel_lift.xy.right` | `recording_view_only` | recording-view heel/ankle/foot height | closed-chain support context, heel confidence, foot support provenance | analysis-evidence soft support-consistency cap | torso-length ratio peak heel elevation | Heel이 보이면 recording-view 값은 점수화 가능 feature가 될 수 있다. Corrected support-surface comparison은 burden provenance다. |
| `control.compensation.pelvis_rotation.xyz` | `corrected_3d_hypothesis` | left/right hip model-depth asymmetry와 향후 corrected-coordinate evidence | depth-sensitive; `quality_gravity`와 report-local correction diagnostics, sensitivity report 필요 | analysis evidence only | torso-length ratio hip-depth asymmetry | 현재 public path에서는 score하지 않는다. Low-confidence corrected-3D evidence로만 사용한다. |
| `biomech.com.range_x`, `biomech.com.path_length` | `recording_view_only` | segment ratio 기반 normalized camera-plane CoM proxy | confidence weighting, valid rep segmentation | 없음 | torso-length ratio | 상대 proxy로만 점수화 가능 feature가 된다. 절대 force/torque 해석 금지. |
| `biomech.com.range_z` | `dual_domain_compare` | model-depth CoM proxy와 향후 corrected-coordinate comparison | depth-sensitive; corrected 사용 전 burden report 필요 | analysis evidence only | torso-length ratio | Multi-video sensitivity 근거 전까지 provenance 또는 low-confidence로 둔다. |
| `biomech.moment_arm.knee.<side>.median`, `biomech.moment_arm.hip.<side>.median` | `recording_view_only` | 2D recording-view CoM-to-joint proxy | view-supported joint/CoM projection, confidence weighting | 없음 | torso-length ratio | 상대 load-distribution proxy일 뿐이며 absolute torque를 추론하지 않는다. |
| `analysis.support_width_stability` | `corrected_3d_hypothesis` | recording-view ankle width와 비교한 corrected support anchor | closed-chain support context, support-width residual, planted-support memory | soft cap + high burden이면 hard not-assessed | review metric, score 아님 | 첫 depth-sensitive review analysis evidence. Feature 승격 전 norm/corrected delta와 burden을 보고한다. |
| `analysis.segment_length_stability.shank`, `analysis.segment_length_stability.thigh` | `corrected_3d_hypothesis` | skeleton envelope/session memory 대비 corrected-coordinate evidence segment length | anthropometric skeleton envelope, segment memory, confidence, residual | soft envelope; hard invalid/not-assessed boundary | review metric, score 아님 | Movement quality가 아니라 corrected-coordinate evidence의 availability/confidence 판단에 사용한다. |

## 7. 개발 경계 (Development Boundary)

해석 항목이 scoring feature가 될 때:

```text
1. pipeline docs에 feature/unit/provenance를 정의한다.
2. YAML pattern 또는 interpretation rule에 연결한다.
3. 재현 가능한 detectability에 대한 최소 테스트를 추가한다.
4. 구현 후에만 per-exercise mapping을 갱신한다.
```
