# 스쿼트 상세 해석 배경 (Squat Clinical Rationale)

**문서 버전:** 1.0.0  
**최종 갱신:** 2026-05-09  
**영문 동기화:** `docs_eng/clinical/exercises/squat.md`는 동일 버전의 영문 번역본이다.

본 문서는 스쿼트가 본 연구에서 어떤 생체역학적 의미를 갖는지, 어떤 움직임 패턴을 관찰하고,
어떤 패턴을 점수화 후보 또는 통제 요인으로 다룰 수 있는지를 정리한다. 이 문서는 임상 진단
기준이나 코드 구현 명세가 아니다.

관련 문서:

- 수행 프로토콜: [exercise_performance_protocol.md §2-1](../../practical_protocols/exercise_performance_protocol.md#2-1-스쿼트-squat)
- 운동 정의 YAML: `data/definitions/exercises/squat.yaml`
- 피처 의미 매핑: [per_exercise_mapping.md §Squat](../per_exercise_mapping.md#squat-스쿼트)

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

---

## 6. 개발 참고 가능성

이 문서의 패턴 설명은 개발 요구사항이 아니다. 다만 점수화 후보로 승격할 경우 다음 순서가
적절하다.

1. `docs/code_revision_plan.md`에 후보와 식별 가능성 근거를 기록한다.
2. 운동 YAML의 `compensation_candidates` 또는 `analysis_disrupting_patterns`와 연결한다.
3. `docs_eng/pipeline/`과 `docs/pipeline/`에 feature 정의와 provenance 규칙을 문서화한다.
4. 합성 또는 최소 annotation fixture로 반복 가능한 식별 가능성을 테스트한다.

