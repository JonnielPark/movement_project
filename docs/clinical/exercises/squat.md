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

본 프로젝트에서의 가치는 방법론적이다. 반복 구조가 명확하고 흔한 보상 후보가 관찰되기 쉽다.
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

## 4. 후보 패턴 (Candidate Patterns)

| Pattern | Interpretation direction | Detectability | Status |
|---|---|---|---|
| knee valgus | 부하 중 medial knee-deviation proxy | frontal/front-oblique에서 높음 | 구현 후보 |
| knee varus | lateral knee-deviation proxy; stance/view 민감 | 중간 | 제한 포함 구현 후보 |
| excessive trunk flexion | forward trunk-lean strategy | side/front-oblique에서 높음 | 구현 후보 |
| lateral pelvic shift | weight-shift proxy | 중간; view 의존 | 구현 후보 |
| heel lift | ankle/forefoot-loading proxy | 중간; heel visibility 의존 | 구현 후보 |
| pelvic rotation | hip-depth asymmetry proxy | 낮음-중간; depth 민감 | 주의 포함 구현 후보 |
| arm swing | 상지 momentum이 하지 trajectory를 오염 | 중간 | control factor |
| unstable foot contact | support 변화로 비교 가능성 저하 | 낮음-중간 | control/limitation factor |

위 용어는 movement-quality proxy이지 진단이 아니다.

## 5. View 및 품질 제한 (View And Quality Limits)

Front-oblique view가 기본 절충안이다. 더 frontal한 view는 frontal knee/pelvis alignment를,
더 side에 가까운 view는 depth, sagittal ROM, trunk lean, heel-lift review를 강화한다.

Side-view 또는 near-side-view recording에서는 bilateral symmetry가 view-dependent이다.
회전시킨 단안 3D rendering은 직접 정면 근거를 만들지 않는다. far-side visibility, depth
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
현재 p01 squat gate다. `corrected_3d_hypothesis` row는 candidate evidence일 뿐이며, score gravity는
이후 scoring policy로 defer한다.

| feature_id | evaluation_domain | source_evidence | active_constraints | cap_strength | expected_output | confidence/burden rule |
|---|---|---|---|---|---|---|
| `spatial.rom.left_hip_angle`, `spatial.rom.right_hip_angle` | `recording_view_only` | `norm` camera-plane hip/shoulder/knee trajectory; phase label이 있으면 함께 사용 | hip/knee/shoulder visibility, valid rep/phase segmentation, sagittal motion을 지지하는 view | 없음 | rep/phase별 degree ROM | Source landmark가 보이고 swap/far-side warning이 지배적이지 않을 때만 scoring 후보로 사용한다. |
| `spatial.rom.left_knee_angle`, `spatial.rom.right_knee_angle` | `recording_view_only` | `norm` camera-plane hip-knee-ankle trajectory | hip/knee/ankle visibility, valid rep/phase segmentation, bend-flip provenance flag 없음 | 없음 | rep/phase별 degree ROM | Knee bend-side 또는 far-side evidence가 불안정하면 provenance 또는 `low_confidence`로 둔다. |
| `spatial.rom.left_ankle_angle`, `spatial.rom.right_ankle_angle` | `recording_view_only` | `norm` camera-plane knee-ankle-foot trajectory | knee/ankle/foot visibility, heel/foot visibility, valid rep/phase segmentation | 없음 | rep/phase별 degree ROM | Foot landmark가 불안정하거나 support-contact evidence가 약하면 withhold 또는 confidence downgrade한다. |
| `spatial.symmetry.hip`, `spatial.symmetry.knee`, `spatial.symmetry.ankle` | `dual_domain_compare` | 좌우 recording-view ROM; 이후 optional corrected candidate comparison | bilateral squat context, 양측 visibility 충분, high correction burden 없음 | corrected comparison은 report-only delta | dimensionless symmetry index | 양측이 view-supported일 때만 recording-view symmetry를 score 후보로 사용한다. Corrected 사용 전 norm-vs-corrected delta를 보고한다. |
| `spatial.shape.arc_length.left_hip`, `spatial.shape.arc_length.right_hip` | `recording_view_only` | `norm` camera-plane hip trajectory | valid rep/phase segmentation, hip visibility | 없음 | torso-length ratio trajectory arc length | Pelvis visibility 또는 segmentation이 불안정하면 confidence를 낮춘다. |
| `spatial.shape.arc_length.left_knee`, `spatial.shape.arc_length.right_knee` | `recording_view_only` | `norm` camera-plane knee trajectory | knee visibility, valid rep/phase segmentation, knee tracking을 지지하는 view | 없음 | torso-length ratio trajectory arc length | Far-side knee arc는 occlusion/swap risk가 높으면 `low_confidence`로 둔다. |
| `spatial.shape.arc_length.left_ankle`, `spatial.shape.arc_length.right_ankle` | `dual_domain_compare` | recording-view ankle trajectory; optional support-memory candidate comparison | closed-chain support context, ankle/foot visibility, planted-support provenance | corrected delta는 report-only | torso-length ratio trajectory arc length | Support landmark가 안정적일 때만 recording-view score 후보로 사용한다. Corrected support-memory comparison은 burden provenance다. |
| `spatial.phase_rom_ratio.descent_ascent` | `recording_view_only` | 확정된 descent/ascent label의 phase-level ROM record | valid phase segmentation, 양 phase의 충분한 ROM record | 없음 | descent/ascent ratio | Phase segmentation이 failed, manually uncertain, 또는 너무 짧으면 withhold한다. |
| `temporal.tempo.rep_*`, `temporal.variability.tempo_cv` | `recording_view_only` | timestamp와 rep boundary | valid annotation 또는 accepted rep segmentation | 없음 | seconds; dimensionless CV | Depth와 무관하다. Availability는 rep boundary reliability에 의존한다. |
| `control.stability.hip_center_x_std` | `recording_view_only` | `norm` camera-plane hip-center lateral trajectory | 양측 hip visibility, valid rep/phase segmentation | 없음 | torso-length ratio | Pelvis x trajectory가 보이고 swap/interpolation에 지배되지 않을 때 scoring 후보로 사용한다. |
| `control.stability.hip_center_z_std` | `dual_domain_compare` | 현재 model-depth axis와 향후 corrected candidate comparison | depth evidence는 low-confidence; scoring 전 norm-vs-corrected sensitivity 필요 | candidate evidence only | torso-length ratio | 현재 public path에서는 corrected depth가 score에 영향 주지 않는다. Sensitivity와 availability만 보고한다. |
| `control.compensation.knee_valgus.left`, `control.compensation.knee_valgus.right` | `recording_view_only` | hip-ankle line 대비 camera-plane knee deviation | frontal/front-oblique view support, hip/knee/ankle visibility | 없음 | torso-length ratio peak medial deviation | Frontal knee tracking을 지지하는 view에서만 score 후보로 사용한다. Side-view 결과는 provenance 또는 `not_assessed`다. |
| `control.compensation.knee_varus.left`, `control.compensation.knee_varus.right` | `recording_view_only` | hip-ankle line 대비 camera-plane knee deviation | knee valgus와 동일; stance width는 context로 검토 | 없음 | torso-length ratio peak lateral deviation | Support stance가 view-sensitive하거나 far-side landmark가 불안정하면 confidence를 낮춘다. |
| `control.compensation.excessive_trunk_flexion` | `recording_view_only` | camera-plane shoulder-hip trunk line | shoulder/hip visibility, sagittal trunk lean을 지지하는 view | 없음 | peak trunk angle in degrees | Shoulder/hip landmark가 안정적이면 sagittal/centerline feature로 scoring 후보가 된다. |
| `control.compensation.lateral_pelvic_shift` | `recording_view_only` | `norm` camera-plane hip-center lateral displacement | bilateral hip visibility, valid rep segmentation | 없음 | torso-length ratio peak lateral displacement | Landmark 품질 때문에 pelvis center가 불안정하면 confidence를 낮춘다. |
| `control.compensation.heel_lift.left`, `control.compensation.heel_lift.right` | `dual_domain_compare` | recording-view heel/ankle/foot height; optional support-surface candidate comparison | closed-chain support context, heel visibility, foot support provenance | review-only soft support-contact cap | torso-length ratio peak heel elevation | Heel이 보이면 recording-view 값은 score 후보가 될 수 있다. Corrected support-surface comparison은 burden provenance다. |
| `control.compensation.pelvic_rotation` | `corrected_3d_hypothesis` | left/right hip model-depth asymmetry와 향후 corrected candidate | depth-sensitive; correction burden, residual, sensitivity report 필요 | candidate evidence only | torso-length ratio hip-depth asymmetry | 현재 public path에서는 score하지 않는다. Low-confidence corrected-3D evidence로만 사용한다. |
| `biomech.com.range_x`, `biomech.com.path_length` | `recording_view_only` | segment ratio 기반 normalized camera-plane CoM proxy | visibility weighting, valid rep segmentation | 없음 | torso-length ratio | 상대 proxy로만 score 후보가 된다. 절대 force/torque 해석 금지. |
| `biomech.com.range_z` | `dual_domain_compare` | model-depth CoM proxy와 향후 corrected candidate comparison | depth-sensitive; corrected 사용 전 burden report 필요 | candidate evidence only | torso-length ratio | Multi-video sensitivity 근거 전까지 provenance 또는 low-confidence로 둔다. |
| `biomech.moment_arm.knee.<side>.median`, `biomech.moment_arm.hip.<side>.median` | `recording_view_only` | 2D recording-view CoM-to-joint proxy | view-supported joint/CoM projection, visibility weighting | 없음 | torso-length ratio | 상대 load-distribution proxy일 뿐이며 absolute torque를 추론하지 않는다. |
| `candidate.support_width_stability` | `corrected_3d_hypothesis` | recording-view ankle width와 비교한 corrected support anchor | closed-chain support context, support-width residual, planted-support memory | soft cap + high burden이면 hard not-assessed | review metric, score 아님 | 첫 depth-sensitive review 후보. Feature 승격 전 norm/corrected delta와 burden을 보고한다. |
| `candidate.segment_length_stability.shank`, `candidate.segment_length_stability.thigh` | `corrected_3d_hypothesis` | skeleton envelope/session memory 대비 corrected candidate segment length | anthropometric skeleton envelope, segment memory, visibility, residual | soft envelope; hard invalid/not-assessed boundary | review metric, score 아님 | Movement quality가 아니라 corrected candidate의 availability/confidence 판단에 사용한다. |

## 7. 개발 경계 (Development Boundary)

해석 항목이 scoring feature가 될 때:

```text
1. pipeline docs에 feature/unit/provenance를 정의한다.
2. YAML candidate 또는 interpretation rule에 연결한다.
3. 재현 가능한 detectability에 대한 최소 테스트를 추가한다.
4. 구현 후에만 per-exercise mapping을 갱신한다.
```
