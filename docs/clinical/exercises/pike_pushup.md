# 파이크 푸쉬업 상세 해석 배경 (Pike Push-up Clinical Rationale)

**문서 버전:** 1.0.0  
**최종 갱신:** 2026-05-09  
**영문 동기화:** `docs_eng/clinical/exercises/pike_pushup.md`는 동일 버전의 영문 번역본이다.

본 문서는 파이크 푸쉬업이 본 연구에서 어떤 생체역학적 의미를 갖는지, 상체 지지와 역V자 자세를
어떻게 해석할 수 있는지, 어떤 패턴을 점수화 후보 또는 통제 요인으로 다룰 수 있는지를 정리한다.
이 문서는 임상 진단 기준이나 코드 구현 명세가 아니다.

관련 문서:

- 수행 프로토콜: [exercise_performance_protocol.md §2-3](../../practical_protocols/exercise_performance_protocol.md#2-3-파이크-푸쉬업-pike-push-up)
- 운동 정의 YAML: `data/definitions/exercises/pike_pushup.yaml`
- 피처 의미 매핑: [per_exercise_mapping.md §Pike Push-up](../per_exercise_mapping.md#pike-push-up-파이크-푸쉬업)

---

## 1. 본 연구에서의 역할

파이크 푸쉬업은 inverted closed-chain 자세에서 상체가 체중을 지지하는 운동이다. 본 연구에서는
파이크 푸쉬업을 통해 어깨와 팔꿈치의 대칭적 굴곡/신전, 머리 하강 궤적, 역V자 자세 유지,
엉덩이 높이 변화, 상체 지지 안정성을 관찰한다.

이 운동은 하체 운동과 달리 상지 landmark self-occlusion과 지면 근접 자세가 자주 발생한다.
따라서 파이크 푸쉬업은 단일 비전 환경에서 상체 지지 과제의 가시성 한계와 수행 실패 지점 기록
전략을 검토하기 좋은 운동이다.

---

## 2. 기대되는 움직임

- 엉덩이를 높게 유지해 역V자 자세를 만든다.
- 머리는 양손 사이를 향해 내려간다.
- 어깨와 팔꿈치는 좌우가 비교적 대칭적으로 굴곡/신전된다.
- 엉덩이가 내려가 일반 푸쉬업 자세로 바뀌지 않는다.
- 손과 발 위치는 반복 중 크게 이동하지 않는다.
- 10회를 채우기 어렵다면 수행 실패 지점과 실제 반복 수를 기록한다.

---

## 3. 주요 관찰 구조

| 관찰 요소 | 관련 관절/분절 | 해석 방향 |
|---|---|---|
| 머리 하강 | nose 또는 head proxy | depth proxy, partial completion |
| 어깨 ROM | shoulder angle | 상체 지지, 좌우 대칭성 |
| 팔꿈치 ROM | elbow angle | push phase control, elbow flare |
| 엉덩이 높이 | hip_center, hip angle | inverted-V 유지, hip drop |
| 손/발 위치 | wrist, ankle, foot | base of support stability |
| 좌우 상지 대칭성 | left/right shoulder/elbow | unilateral loading or compensation |

---

## 4. 보상 및 분석 방해 패턴

| 패턴 | 생체역학적 의미 | pose 식별 가능성 | 점수화/통제 방향 | 관련 후보 |
|---|---|---|---|---|
| insufficient head descent | 머리가 충분히 내려가지 않는 패턴. ROM 제한, 피로, 난도 조절 또는 partial completion을 반영할 수 있다. | 높음-중간. nose visibility가 필요하며, shoulder_center fallback이 필요할 수 있다. | 점수화 후보, failure provenance 동반 | `insufficient_head_descent` |
| head forward shift | 머리가 양손 사이가 아니라 앞쪽으로 빠지는 패턴. 어깨 부하 회피 또는 자세 붕괴를 반영할 수 있다. | 중간. 측면 view에서 유리하다. | 점수화 후보 | `head_forward_shift` |
| elbow flare | 팔꿈치가 과도하게 벌어지는 패턴. 어깨 안정성 저하 또는 지지 전략 변화를 반영할 수 있다. | 중간. camera view와 elbow visibility에 민감하다. | 점수화 후보 | `elbow_flare` |
| shoulder asymmetry | 좌우 어깨 ROM이나 궤적이 달라지는 패턴. 단측 지지 회피 또는 shoulder control 차이를 시사할 수 있다. | 중간. self-occlusion 영향이 크다. | 점수화 후보 또는 해석 제한 | `shoulder_asymmetry` |
| hip drop | 엉덩이가 내려가 일반 푸쉬업에 가까워지는 패턴. 과제 자체가 바뀌므로 상체 지표 해석을 크게 바꾼다. | 높음. 측면 view에서 유리하다. | 점수화 후보, 심하면 통제/해석 제한 | `hip_drop` |
| hip pike variation | 엉덩이가 지나치게 높거나 반복마다 크게 변하는 패턴. 어깨 부하량과 머리 하강 기준을 바꾼다. | 중간. hip and shoulder visibility 필요. | 점수화 후보 | `hip_pike` |
| hand/foot repositioning | 손 또는 발 위치가 반복 중 바뀌는 패턴. base of support와 ROM 기준을 바꾼다. | 낮음-중간. 실제 접촉 위치와 landmark가 다를 수 있다. | 통제 또는 해석 제한 요인 | `hand_foot_repositioning` |
| tempo instability | 반복 속도가 급격히 변하는 패턴. 난도, 피로, 부분 수행과 관련될 수 있다. | 높음. rep segmentation 안정성이 필요하다. | 점수화 후보 | `tempo_instability` |

---

## 5. 데이터 품질과 해석 제한

파이크 푸쉬업은 측면 low-angle view에서 머리와 엉덩이 높이 변화를 보기 쉽지만, 하강 지점에서
팔꿈치와 손목이 몸통 또는 머리에 가려질 수 있다. nose landmark가 불안정하면 head descent는
shoulder_center 또는 head proxy로 보조해야 할 수 있다.

이 운동은 난도가 높기 때문에 목표 반복 수 미달 자체가 흔할 수 있다. 따라서 낮은 반복 수를
곧바로 나쁜 점수로 해석하기보다, 실제 반복 수, 수행 실패 지점, 실패 사유를 함께 기록해야 한다.

---

## 6. 개발 참고 가능성

파이크 푸쉬업에서 개발 참고 가치가 큰 항목은 partial completion과 failure point provenance이다.
insufficient head descent, hip drop, head forward shift처럼 관절 포인트로 비교적 관찰 가능한 항목은
점수화 후보가 될 수 있지만, shoulder asymmetry나 elbow flare는 self-occlusion과 view dependency가
크므로 식별 가능성 평가가 먼저 필요하다.

