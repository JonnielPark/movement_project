# 런지 상세 해석 배경 (Lunge Clinical Rationale)

**문서 버전:** 1.0.0  
**최종 갱신:** 2026-05-09  
**영문 동기화:** `docs_eng/clinical/exercises/lunge.md`는 동일 버전의 영문 번역본이다.

본 문서는 런지가 본 연구에서 어떤 생체역학적 의미를 갖는지, 편측성/교대성 수행을 어떻게
해석할 수 있는지, 어떤 패턴을 점수화 후보 또는 통제 요인으로 다룰 수 있는지를 정리한다.
이 문서는 임상 진단 기준이나 코드 구현 명세가 아니다.

관련 문서:

- 수행 프로토콜: [exercise_performance_protocol.md §2-2](../../practical_protocols/exercise_performance_protocol.md#2-2-런지-lunge)
- 운동 정의 YAML: `data/definitions/exercises/lunge.yaml`
- 피처 의미 매핑: [per_exercise_mapping.md §Lunge](../per_exercise_mapping.md#lunge-런지)

---

## 1. 본 연구에서의 역할

런지는 split-stance에서 한쪽 다리가 주된 부하를 받고, 반대쪽 다리가 지지와 균형을 보조하는
편측성 하체 운동이다. 본 연구에서는 런지를 통해 교대 또는 블록 기반 좌우 수행에서 active side
attribution, 앞다리와 뒷다리의 역할 차이, 보폭 일관성, 체간 정렬, 무릎 전방 이동, 골반 안정성을
관찰한다.

현재 수행 프로토콜은 같은 앞발로 5회 수행한 뒤 반대 앞발로 5회 수행하는 방식이다. 그러나 런지
자체는 매회 좌우를 번갈아 수행할 수도 있다. 따라서 런지의 좌우 순서는 운동 고유 속성이 아니라
취득 프로토콜의 선택값으로 다루어야 한다.

---

## 2. 기대되는 움직임

- 앞발과 뒷발은 split stance를 유지한다.
- 하강 중 앞다리 고관절, 무릎, 발목이 부하를 받으며 굴곡된다.
- 뒷다리는 엉덩이 신전과 무릎 굴곡을 동반하며 균형을 보조한다.
- 체간은 과도하게 앞으로 접히거나 뒤로 젖혀지지 않는다.
- 앞발 보폭은 반복 간 크게 변하지 않는다.
- 좌우 전환 시 몸 전체가 카메라를 향해 돌아서지 않고, 동일한 촬영 기준을 유지한다.

---

## 3. 주요 관찰 구조

| 관찰 요소 | 관련 관절/분절 | 해석 방향 |
|---|---|---|
| 앞다리 ROM | forward hip/knee/ankle | 부하 수용, 하강 깊이, 좌우 차이 |
| 뒷다리 확장 | rear hip/knee | hip flexor extensibility, trailing-leg control |
| 보폭 일관성 | ankle/foot trajectory | 반복 간 비교 가능성, segmentation 안정성 |
| 체간 정렬 | shoulder-hip line | anterior trunk lean, ascent compensation |
| 골반 안정성 | hip_center, pelvis line | lateral shift, pelvis drop/rotation |
| 좌우 순서 | active side per rep | protocol adherence, motion attribution |

---

## 4. 보상 및 분석 방해 패턴

| 패턴 | 생체역학적 의미 | pose 식별 가능성 | 점수화/통제 방향 | 관련 후보 |
|---|---|---|---|---|
| knee valgus | 앞다리 무릎이 내측으로 붕괴되는 패턴. 하강 phase에서 부하 수용 전략과 관련될 수 있다. | 중간. 측면 view에서는 관상면 편차가 약해질 수 있다. | 점수화 후보, view warning 필요 | `knee_valgus` |
| asymmetric knee/hip flexion | 좌우 또는 앞다리/뒷다리 ROM 차이. 사지 간 부하 전략 차이를 반영할 수 있다. | 높음. active side annotation이 필요하다. | 점수화 후보 | `asymmetric_knee_flexion`, `asymmetric_hip_flexion` |
| insufficient rear hip extension | 뒷다리 고관절이 충분히 신전되지 않는 패턴. hip flexor extensibility 제한 또는 보폭 부족과 관련될 수 있다. | 중간. 측면 view와 뒷다리 landmark visibility가 필요하다. | 점수화 후보 | `insufficient_rear_hip_extension` |
| excessive trunk flexion | 앞쪽으로 과도하게 숙이는 패턴. 앞다리 발목 제한, 균형 전략, 상승 보조와 관련될 수 있다. | 높음. 측면 view에서 유리하다. | 점수화 후보 | `excessive_trunk_flexion` |
| lateral trunk lean | 체간이 좌우로 기울어지는 패턴. 골반 안정성 저하 또는 단측 부하 회피 전략일 수 있다. | 중간. frontal/front-oblique view에서 더 유리하다. | 점수화 후보 또는 해석 제한 | `lateral_trunk_lean` |
| pelvis drop/shift | 골반이 한쪽으로 떨어지거나 이동하는 패턴. hip abductor control 또는 균형 전략과 관련될 수 있다. | 중간. view와 hip landmark 가시성에 민감하다. | 점수화 후보 | `pelvis_drop`, `lateral_pelvic_shift` |
| unstable step width | 보폭 또는 발 위치가 반복마다 바뀌는 패턴. 반복 간 비교와 active-side 해석을 어렵게 한다. | 낮음-중간. 실제 발 접촉과 foot landmark 안정성이 필요하다. | 주로 통제 요인 | `unstable_step_width`, `inconsistent_step_length` |
| camera side change | 좌우 전환 시 몸 또는 카메라 기준이 바뀌는 패턴. 같은 지표의 좌우 비교를 어렵게 한다. | 높음. recording metadata와 영상 확인이 유리하다. | 통제 또는 해석 제한 요인 | `camera_side_change` |
| arm swing/trunk extension assist | 팔이나 몸통 반동으로 상승을 돕는 패턴. 하지 부하 해석을 오염시킨다. | 중간. pose로 움직임은 보이나 보조 의도는 단정하기 어렵다. | 통제 요인 | `arm_swing` |

---

## 5. 데이터 품질과 해석 제한

런지는 앞다리와 뒷다리의 역할이 다르기 때문에, 단순히 좌우 관절값을 비교하면 해석이 흐려질 수
있다. 같은 left/right라도 해당 반복에서 forward leg인지 trailing leg인지 annotation 또는 motion
attribution으로 구분해야 한다.

측면 view는 무릎 전방 이동과 체간 정렬 관찰에 유리하지만, 관상면 knee valgus나 pelvis drop은
약하게 보일 수 있다. 반대로 정면 또는 전방 대각 view는 좌우 정렬에 유리하지만, 시상면 ROM과
뒷다리 움직임 해석이 약해질 수 있다.

---

## 6. 개발 참고 가능성

런지에서 가장 중요한 개발 참고점은 side sequence와 active side provenance이다. 현재 연구
프로토콜은 5회 한쪽 블록 뒤 5회 반대쪽 블록이지만, 향후 alternate-each-rep 런지를 추가할 수
있다. 이 경우 같은 `lunge`라는 운동명만으로는 충분하지 않고, protocol profile 또는 별도 YAML
variant가 필요할 수 있다.

점수화 후보를 만들 때는 각 반복의 forward leg, trailing leg, expected side sequence, observed
side sequence를 함께 보존해야 한다.

