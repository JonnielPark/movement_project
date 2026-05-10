# 파이크 푸쉬업 상세 해석 배경 (Pike Push-up Clinical Rationale)

**문서 버전:** 1.0.2
**최종 갱신:** 2026-05-10  
**영문 동기화:** `docs_eng/clinical/exercises/pike_pushup.md`는 동일 버전의 영문 번역본이다.

본 문서는 파이크 푸쉬업이 본 연구에서 어떤 생체역학적 의미를 갖는지, 상체 지지와 역V자 자세를
어떻게 해석할 수 있는지, 어떤 패턴을 점수화 후보 또는 통제 요인으로 다룰 수 있는지를 정리한다.
이 문서는 임상 진단 기준이나 코드 구현 명세가 아니다.

관련 문서:

- 수행 프로토콜: [exercise_performance_protocol.md §2-3](../../practical_protocols/exercise_performance_protocol.md#2-3-파이크-푸쉬업-pike-push-up)
- 운동 정의 YAML: [pike_pushup.yaml](../../../data/definitions/exercises/pike_pushup.yaml)
- 피처 의미 매핑: [per_exercise_mapping.md §Pike Push-up](../per_exercise_mapping.md#pike-push-up-파이크-푸쉬업)

---

## 분석 파라미터 요약 (Analysis Parameter Summary)

아래 요약은 운동 정의 YAML의 핵심 설정을 해석 관점에서 풀어쓴 것이다. 실행 기준은
[pike_pushup.yaml](../../../data/definitions/exercises/pike_pushup.yaml)이다.

| YAML 블록 | 현재 설정 | 설정 의도 |
|---|---|---|
| `classification` | `bilateral_symmetric`, inverted closed-chain, primary plane `sagittal` | 역V자 자세에서 양측 상지가 체중을 지지하는 상체 push 과제로 정의한다. |
| `landmarks` / `angle_definitions` | shoulder, elbow, wrist 중심; hip/head 보조 | 상지 ROM, 머리 하강, hip pike 유지 여부를 함께 추적한다. |
| `rep_segmentation` / `phase_segmentation` | `nose` vertical trajectory; top boundary, bottom split; `Descent` / `Ascent` | 머리 하강/상승을 기준으로 반복과 phase를 나누며, nose 불안정 시 head proxy 보조가 필요할 수 있다. |
| `performance_protocol` | 10 repetitions, side sequence `none`, partial completion 허용 | 난도가 높은 운동이므로 목표 반복 미달을 failure provenance와 함께 기록한다. |
| `camera_protocol` | `Z3` / `Z7`, `H1`, 200-250 cm | 낮은 측면 view에서 머리 하강, hip drop, inverted-V 유지 여부를 우선 관찰한다. |
| `feature_domains` | ROM, symmetry, shape, depth, reach, tempo, trunk/com stability | 상체 지지 ROM과 자세 유지, 반복 간 난도/피로 관련 변화를 함께 본다. |
| `biomechanical_focus` | shoulder/elbow/wrist/trunk load regions, support moment/load-shift proxy | 절대 상지 근력 대신 지지 구조와 상대 부하 경향을 해석한다. |
| `compensation_candidates` | elbow flare, shoulder asymmetry/collapse, insufficient head descent, head forward shift, hip drop/pike 등 | 상체 지지 과제에서 pose로 관찰 가능한 자세 붕괴와 부분 수행 후보를 우선 검토한다. |
| `quality_rules` | visible ratio `0.75`, critical ratio `0.9`, max interpolation gap 3 frames | self-occlusion 가능성을 고려하되 핵심 상지/골반 landmark는 높은 신뢰도를 요구한다. |

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

## 6. 권장 view 해석

파이크 푸쉬업의 기본 권장 view는 낮은 측면(`Z3` 또는 `Z7`, `H1`)이다. 이 view는 머리가 양손
사이로 내려가는지, 엉덩이가 역V자 자세를 유지하는지, 일반 푸쉬업 형태로 hip drop이 발생하는지,
상체가 어느 정도 수직 방향으로 이동하는지를 보기 좋다.

정면 또는 전방 대각 view는 elbow flare, shoulder asymmetry, 좌우 손 지지 차이를 보는 데 도움이
될 수 있지만, 머리 하강 깊이와 hip pike/hip drop 같은 핵심 구조를 해석하기에는 측면보다 불리할
수 있다. 따라서 본 연구에서는 측면 view를 기본으로 두고, 좌우 상지 대칭성은 양측 어깨/팔꿈치
landmark visibility가 충분할 때만 보조적으로 해석한다.

측면 촬영에서는 카메라에서 먼 쪽 팔꿈치나 손목이 가려질 수 있다. 이 경우 반대편 상지 ROM이나
대칭성을 나쁜 점수로 바로 반영하지 않고, visible-side sagittal ROM, head descent, hip position,
trunk/hip alignment 같은 더 안정적인 지표를 우선한다.

---

## 7. 개발 참고 가능성

파이크 푸쉬업에서 개발 참고 가치가 큰 항목은 partial completion과 failure point provenance이다.
insufficient head descent, hip drop, head forward shift처럼 관절 포인트로 비교적 관찰 가능한 항목은
점수화 후보가 될 수 있지만, shoulder asymmetry나 elbow flare는 self-occlusion과 view dependency가
크므로 식별 가능성 평가가 먼저 필요하다.
