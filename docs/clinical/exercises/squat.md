# 스쿼트 상세 해석 배경 (Squat Clinical Rationale)

**문서 버전:** 1.0.4
**최종 갱신:** 2026-05-12
**영문 동기화:** `docs_eng/clinical/exercises/squat.md`는 동일 버전의 영문 번역본이다.

본 문서는 스쿼트가 본 연구에서 어떤 생체역학적 의미를 갖는지, 어떤 움직임 패턴을 관찰하고,
어떤 패턴을 점수화 후보 또는 통제 요인으로 다룰 수 있는지를 정리한다. 이 문서는 임상 진단
기준이나 코드 구현 명세가 아니다.

관련 문서:

- 수행 프로토콜: [exercise_performance_protocol.md §2-1](../../practical_protocols/exercise_performance_protocol.md#2-1-스쿼트-squat)
- 운동 정의 YAML: [squat.yaml](../../../data/definitions/exercises/squat.yaml)
- 피처 의미 매핑: [per_exercise_mapping.md §Squat](../per_exercise_mapping.md#squat-스쿼트)

---

## 분석 파라미터 요약 (Analysis Parameter Summary)

아래 요약은 운동 정의 YAML의 핵심 설정을 해석 관점에서 풀어쓴 것이다. 실행 기준은
[squat.yaml](../../../data/definitions/exercises/squat.yaml)이다.

| YAML 블록 | 현재 설정 | 설정 의도 |
|---|---|---|
| `classification` | `bilateral_symmetric`, standing closed-chain, primary plane `sagittal` | 양측 하지가 동시에 체중을 지지하는 기준 운동으로 정의하고, 시상면 ROM과 관상면 정렬을 함께 관찰한다. |
| `landmarks` / `angle_definitions` | hip, knee, ankle 중심; shoulder/pelvis line 보조 | 하지 삼중 굴곡, 체간 기울기, 골반 정렬을 같은 반복 단위에서 추적한다. |
| `rep_segmentation` / `phase_segmentation` | `hip_center` vertical trajectory; top boundary, bottom split; `Descent` / `Ascent` | 골반 중심의 상하 이동으로 반복 경계와 하강/상승 phase를 안정적으로 나눈다. |
| `performance_protocol` | 10 repetitions, side sequence `none`, hands fixed cue | 좌우 교대가 없는 양측 운동으로 두고, 팔 반동이 하지/체간 지표에 섞이지 않게 한다. |
| `camera_protocol` | `Z2` / `Z8`, `H2`, 200-250 cm | 전방 대각 view에서 무릎 정렬과 하강 깊이를 동시에 관찰한다. |
| `feature_domains` | ROM, symmetry, shape, depth, alignment, tempo, stability, compensation | 기본 공간/시간/제어 feature를 넓게 켜서 reference exercise 역할을 하게 한다. |
| `biomechanical_focus` | vertical CoM motion, hip/knee/ankle load regions, moment-arm/load-shift proxy | 절대 부하가 아니라 하지 관절 간 상대 부하 분포 경향을 본다. |
| `compensation_candidates` | knee valgus/varus, asymmetric depth, trunk flexion, pelvic shift, heel lift 등 | 단안 pose에서 반복적으로 관찰 가능한 대표 하지 보상 후보를 우선 검토한다. |
| `quality_rules` | visible ratio `0.8`, critical ratio `0.9`, max interpolation gap 3 frames | 핵심 하지 landmark가 충분히 보이는 반복만 신뢰 가능한 지표로 사용한다. |

---

## 1. 본 연구에서의 역할

스쿼트는 양측 하지가 동시에 체중을 지지하는 대표적인 closed-chain 하체 운동이다. 본 연구에서는
스쿼트를 통해 양측 고관절, 무릎, 발목의 협응, 하강 깊이, 체간 정렬, 골반 중심 안정성, 좌우
대칭성을 관찰한다.

스쿼트는 비교적 반복 구조가 명확하고, 좌우가 동시에 움직이므로 단일 비전 기반 포즈 데이터에서
기본적인 공간/시간/제어 지표를 검증하기 좋은 기준 운동이다. 또한 무릎 외반/내반, 발뒤꿈치
들림, 과도한 체간 굴곡, 골반 측방 이동 같은 보상 움직임 후보가 관찰되기 쉬워 compensation
feature의 방향성을 확인하는 데 적합하다.

---

## 2. 기대되는 움직임

표준 수행에서 기대되는 움직임은 다음과 같다.

- 양발은 지면에 안정적으로 접촉한다.
- 고관절, 무릎, 발목이 함께 굴곡되며 골반 중심이 아래로 이동한다.
- 하강과 상승 동안 무릎은 발 진행 방향과 크게 어긋나지 않는다.
- 체간은 약간 전방으로 기울 수 있으나, 고관절 굴곡과 체간 굴곡이 완전히 섞일 정도로 접히지 않는다.
- 좌우 고관절과 무릎 ROM은 큰 차이 없이 반복된다.
- 반복 간 하강 깊이와 템포가 크게 흔들리지 않는다.

이 기대 움직임은 임상적 정상 기준이 아니라, 단안 비전 포즈 분석에서 일관된 동작 품질 지표를
산출하기 위한 관찰 기준이다.

---

## 3. 주요 관찰 구조

| 관찰 요소 | 관련 관절/분절 | 해석 방향 |
|---|---|---|
| 하강 깊이 | hip_center, hip/knee/ankle angle | ROM, depth proxy, 반복 간 일관성 |
| 무릎 정렬 | hip-knee-ankle line | knee valgus/varus, frontal-plane tracking |
| 발뒤꿈치 접지 | heel, ankle, foot index | ankle dorsiflexion 제한 또는 forefoot loading 보상 |
| 체간 기울기 | shoulder-hip line | hip strategy, trunk compensation |
| 골반 측방 이동 | hip_center x trajectory | weight-shift compensation |
| 좌우 대칭성 | left/right hip, knee, ankle ROM | unilateral mobility or load-avoidance tendency |

---

## 4. 보상 및 분석 방해 패턴

| 패턴 | 생체역학적 의미 | pose 식별 가능성 | 점수화/통제 방향 | 관련 후보 |
|---|---|---|---|---|
| knee valgus | 무릎이 hip-ankle line 대비 내측으로 이동하는 패턴. 부하 중 hip abductor control 부족 또는 발/고관절 전략 변화와 관련될 수 있다. | 높음. 전방 대각 또는 정면에 가까운 view에서 유리하다. | 점수화 후보 | `knee_valgus` |
| knee varus | 무릎이 외측으로 벗어나는 패턴. 넓은 스탠스, 구조적 정렬, 보상적 bracing과 혼동될 수 있다. | 중간. view와 foot direction 추정에 민감하다. | 점수화 후보, 해석 제한 동반 | `knee_varus` |
| asymmetric depth | 좌우 또는 반복 간 하강 깊이가 달라지는 패턴. 한쪽 가동성 제한, 통증 회피, 균형 전략을 반영할 수 있다. | 중간. rep segmentation과 hip_center 안정성이 필요하다. | 점수화 후보 | `asymmetric_depth` |
| excessive trunk flexion | 체간이 과도하게 앞으로 접히는 패턴. 무릎 부하를 줄이고 hip/lumbar strategy로 전환하는 보상일 수 있다. | 높음. 측면 또는 전방 대각 view에서 관찰 가능하다. | 점수화 후보 | `excessive_trunk_flexion` |
| lateral pelvic shift | 골반 중심이 좌우로 치우치는 패턴. 단측 하지 가동성 제한 또는 weight-shift 보상일 수 있다. | 중간. 정면/전방 대각 view에서 유리하다. | 점수화 후보 | `lateral_pelvic_shift` |
| heel lift | 하강 중 발뒤꿈치가 들리는 패턴. ankle dorsiflexion 제한 또는 forefoot loading 전략일 수 있다. | 중간. heel landmark visibility와 camera height에 민감하다. | 점수화 후보 또는 해석 제한 | `heel_lift` |
| arm swing | 팔 반동으로 상승을 돕는 패턴. 하지/체간 지표를 오염시킨다. | 중간. 팔 landmark는 보이나 동작 보조 의도는 pose만으로 단정하기 어렵다. | 주로 통제 요인 | `analysis_disrupting_patterns.arm_swing` |
| unstable foot contact | 발 위치가 반복마다 바뀌거나 지지면이 흔들리는 패턴. 관절 궤적 기준점을 불안정하게 만든다. | 낮음-중간. foot landmark와 실제 접촉 여부가 다를 수 있다. | 통제 또는 해석 제한 요인 | `unstable_foot_contact` |

---

## 5. 데이터 품질과 해석 제한

스쿼트는 front-oblique view에서 무릎 정렬과 하강 깊이를 함께 볼 수 있지만, 발 진행 방향과 실제
발 접촉 상태를 pose만으로 완전히 알기는 어렵다. 따라서 knee valgus/varus는 foot direction
추정에 민감하고, heel lift는 heel landmark visibility에 민감하다.

의복이 무릎이나 골반 landmark를 가리면 alignment와 pelvis shift 해석이 흔들릴 수 있다.
카메라가 지나치게 측면에 가까우면 관상면 무릎 편차가 줄어 보일 수 있고, 지나치게 정면이면
고관절/무릎의 시상면 ROM 해석이 약해질 수 있다.

측면 또는 측면에 가까운 스쿼트 촬영에서는 양측 대칭성을 view-dependent 지표로 다룬다. 측면
시점에서는 시상면 움직임이 안정적이고 눈에 띄는 보상이 거의 없어 보이지만, 단안 3D skeleton을
정면으로 돌려본 렌더링에서 좌우 균형이 크게 무너져 보일 수 있다. 이 정면 렌더링은 실제 정면
촬영이 아니라 depth 추정 결과를 회전한 것이므로, 실제 비대칭의 직접 증거로 해석하지 않는다.
실제 정면 또는 전방 대각 촬영이 같은 패턴을 확인하기 전까지는 단안 depth inference limitation으로
처리하는 것이 타당하다.

이 경우 스쿼트 해석은 하강 깊이, hip/knee/ankle ROM, 체간 기울기, heel lift, hip-center 궤적
안정성, tempo, smoothness 같은 시상면 및 중심선 피처를 우선한다. 좌우 ROM symmetry, hip depth
기반 pelvic rotation, 기타 depth-sensitive bilateral comparison은 나쁜 movement-quality score로
변환하지 않고 `low_confidence` 또는 `not_assessed`로 남긴다.

---

## 6. 권장 view 해석

스쿼트의 기본 권장 view는 전방 대각(`Z2` 또는 `Z8`)이다. 이 view는 정면 관상면 정보와 측면
시상면 정보를 동시에 일부 확보하기 위한 절충이다. 정면에 가까울수록 knee valgus/varus,
pelvic shift, 좌우 무릎 정렬을 보기 좋고, 측면에 가까울수록 하강 깊이, 체간 기울기, 고관절/
무릎 굴곡 ROM, 발뒤꿈치 들림을 보기 좋다.

본 연구의 기본 취득에서는 순수 정면 또는 순수 측면 중 하나를 추가로 요구하지 않는다. 대신
전방 대각 view에서 관찰 가능한 지표를 우선 사용하고, 특정 feature가 view에 민감한 경우에는
해석 제한 또는 confidence note를 남긴다. 예를 들어 관상면 무릎 편차는 카메라가 너무 측면에
가까우면 과소평가될 수 있고, 시상면 ROM은 카메라가 너무 정면에 가까우면 불안정해질 수 있다.

정밀 연구나 보조 촬영이 가능하다면 정면 view는 좌우 정렬과 관상면 보상 패턴을, 측면 view는
깊이와 체간/하지 시상면 움직임을 추가로 확인하는 데 유용할 수 있다. 그러나 이는 기본 프로토콜
요구사항이 아니라 후속 검토 또는 보조 자료로 둔다.

---

## 7. 개발 참고 가능성

이 문서의 패턴 설명은 개발 요구사항이 아니다. 다만 점수화 후보로 승격할 경우 다음 순서가
적절하다.

1. `docs_eng/pipeline/`과 `docs/pipeline/`에 feature 정의와 provenance 규칙을 문서화한다.
2. 운동 YAML의 `compensation_candidates` 또는 `analysis_disrupting_patterns`와 연결한다.
3. 합성 또는 최소 annotation fixture로 반복 가능한 식별 가능성을 테스트한다.
