# 런지 상세 해석 배경 (Lunge Clinical Rationale)

**문서 버전:** 1.0.3
**최종 갱신:** 2026-05-12
**영문 동기화:** `docs_eng/clinical/exercises/lunge.md`는 동일 버전의 영문 번역본이다.

본 문서는 런지가 본 연구에서 어떤 생체역학적 의미를 갖는지, 편측성/교대성 수행을 어떻게
해석할 수 있는지, 어떤 패턴을 점수화 후보 또는 통제 요인으로 다룰 수 있는지를 정리한다.
이 문서는 임상 진단 기준이나 코드 구현 명세가 아니다.

관련 문서:

- 수행 프로토콜: [exercise_performance_protocol.md §2-2](../../practical_protocols/exercise_performance_protocol.md#2-2-런지-lunge)
- 운동 정의 YAML: [lunge.yaml](../../../data/definitions/exercises/lunge.yaml)
- 피처 의미 매핑: [per_exercise_mapping.md §Lunge](../per_exercise_mapping.md#lunge-런지)

---

## 분석 파라미터 요약 (Analysis Parameter Summary)

아래 요약은 운동 정의 YAML의 핵심 설정을 해석 관점에서 풀어쓴 것이다. 실행 기준은
[lunge.yaml](../../../data/definitions/exercises/lunge.yaml)이다.

| YAML 블록 | 현재 설정 | 설정 의도 |
|---|---|---|
| `classification` | `alternating`, split-stance closed-chain, primary plane `sagittal` | 앞다리와 뒷다리 역할이 다른 편측성 하체 과제로 정의한다. |
| `landmarks` / `angle_definitions` | bilateral hip/knee/ankle 중심; shoulder/pelvis line 보조 | forward leg, trailing leg, 체간 정렬, 골반 안정성을 같은 반복 안에서 비교한다. |
| `rep_segmentation` / `phase_segmentation` | `hip_center` vertical trajectory; top boundary, bottom split; `Descent` / `Ascent` | split-stance에서 골반 중심 하강/상승으로 반복과 phase를 나눈다. |
| `performance_protocol` | 10 repetitions; 기본 `same_side_block_then_switch`, block size 5; `alternating_each_rep`도 허용 | 현재 취득은 5회 한쪽 후 5회 반대쪽이지만, 향후 매회 교대 런지도 같은 운동군 안에서 지원한다. |
| `camera_protocol` | `Z3` / `Z7`, `H2`, 200-250 cm | 측면 view에서 앞무릎 전방 이동, 뒷다리 ROM, 체간 정렬을 우선 관찰한다. |
| `feature_domains` | ROM, symmetry, alignment, support width, left/right timing variability, balance control | 좌우 수행 순서와 앞/뒤 다리 역할 차이를 feature 수준에서 보존한다. |
| `biomechanical_focus` | vertical + anterior-posterior CoM motion, hip/knee/ankle load regions | 앞다리 부하 수용과 뒷다리 보조 역할의 상대적 움직임을 본다. |
| `compensation_candidates` | knee valgus, asymmetric knee/hip flexion, rear hip extension, trunk lean, pelvis drop/shift 등 | 편측 부하와 균형 전략에서 반복적으로 나타날 수 있는 보상 후보를 검토한다. |
| `quality_rules` | visible ratio `0.8`, critical ratio `0.9`, max interpolation gap 3 frames | 양측 하지 landmark와 active-side provenance가 충분할 때 좌우 비교를 해석한다. |

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

런지에서는 metric reliability를 역할 기반으로 해석해야 한다. 단순 anatomical left/right 비교만으로는
충분하지 않다. 같은 해부학적 측이 한 블록에서는 forward leg이고 다른 블록에서는 trailing leg일 수
있기 때문이다. 피처 해석은 `forward_leg`, `trailing_leg`, `active_side`, `support_side`, 그리고
카메라 기준 near/far-side 맥락을 함께 보존해야 한다. 측면 촬영 블록에서 한쪽이 지속적으로
카메라에서 멀거나 visibility가 낮다면, side-to-side 비교는 단측 결손으로 처리하지 않고
low-confidence로 표시한다.

---

## 6. 권장 view 해석

런지의 기본 권장 view는 측면(`Z3` 또는 `Z7`)이다. 런지는 앞다리와 뒷다리의 역할이 다르고,
하강 중 앞무릎 전방 이동, 앞다리/뒷다리의 시상면 ROM, 체간 전방 기울기, 보폭 일관성을 보는
것이 핵심이므로 측면 view가 가장 직접적이다.

이 선택은 관상면 보상 패턴을 무시한다는 뜻이 아니다. knee valgus, pelvis drop, lateral trunk
lean은 정면 또는 전방 대각에서 더 잘 보일 수 있다. 다만 단일 카메라 기본 취득에서 두 view를
요구하면 수행 부담이 커지고, 같은 반복을 동일 조건으로 비교하기도 어려워진다. 따라서 본
프로토콜에서는 측면 view를 기본으로 두고, 관상면 패턴은 관찰 가능할 때 점수화 후보로 다루며,
view상 불리하면 confidence note 또는 해석 제한 요인으로 남긴다.

실제 촬영에서 far-side 관절이 잘 추출된다면 양측 또는 trailing-leg feature를 사용할 수 있다.
반대로 가려짐이 반복되면 해당 feature를 나쁜 점수로 처리하지 않고 unavailable 또는
low-confidence로 남기는 것이 적절하다. 이 방어 로직은 기본 요구사항이 아니라 파일럿 촬영 후
필요성이 확인될 때 적용할 optional 확장으로 둔다.

따라서 계획된 `view_metric_reliability` map은 zone에 따라 서로 다른 metric family에 high reliability를
부여해야 한다. 측면 view는 무릎 전방 이동, 앞/뒤 다리 시상면 ROM, rear-hip extension,
체간 굴곡, 보폭을 잘 뒷받침한다. 정면 view는 step width, 좌우 순서, pelvis drop/shift,
lateral trunk lean, 관상면 무릎 정렬을 더 잘 뒷받침한다. 대각 view는 혼합 정보를 주지만
순수 시상면 또는 순수 관상면 판독보다는 덜 정밀할 수 있다. 이 confidence 상태는 feature 옆에
표시되어야 하며 movement-quality penalty로 바로 변환하지 않는다.

---

## 7. 개발 참고 가능성

런지에서 가장 중요한 개발 참고점은 side sequence와 active side provenance이다. 현재 연구
프로토콜은 5회 한쪽 블록 뒤 5회 반대쪽 블록이지만, 향후 alternate-each-rep 런지를 추가할 수
있다. 이 경우 같은 `lunge`라는 운동명만으로는 충분하지 않고, protocol profile 또는 별도 YAML
variant가 필요할 수 있다.

점수화 후보를 만들 때는 각 반복의 forward leg, trailing leg, expected side sequence, observed
side sequence를 함께 보존해야 한다.
