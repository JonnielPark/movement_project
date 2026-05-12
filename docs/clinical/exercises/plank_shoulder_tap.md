# 플랭크 숄더탭 상세 해석 배경 (Plank Shoulder Tap Clinical Rationale)

**문서 버전:** 1.0.3
**최종 갱신:** 2026-05-12
**영문 동기화:** `docs_eng/clinical/exercises/plank_shoulder_tap.md`는 동일 버전의 영문 번역본이다.

본 문서는 플랭크 숄더탭이 본 연구에서 어떤 생체역학적 의미를 갖는지, anti-rotation 과제를
어떻게 해석할 수 있는지, 어떤 패턴을 점수화 후보 또는 통제 요인으로 다룰 수 있는지를 정리한다.
이 문서는 임상 진단 기준이나 코드 구현 명세가 아니다.

관련 문서:

- 수행 프로토콜: [exercise_performance_protocol.md §2-4](../../practical_protocols/exercise_performance_protocol.md#2-4-플랭크-숄더탭-plank-shoulder-tap)
- 운동 정의 YAML: [plank_shoulder_tap.yaml](../../../data/definitions/exercises/plank_shoulder_tap.yaml)
- 피처 의미 매핑: [per_exercise_mapping.md §Plank Shoulder Tap](../per_exercise_mapping.md#plank-shoulder-tap-플랭크-숄더탭)

---

## 분석 파라미터 요약 (Analysis Parameter Summary)

아래 요약은 운동 정의 YAML의 핵심 설정을 해석 관점에서 풀어쓴 것이다. 실행 기준은
[plank_shoulder_tap.yaml](../../../data/definitions/exercises/plank_shoulder_tap.yaml)이다.

| YAML 블록 | 현재 설정 | 설정 의도 |
|---|---|---|
| `classification` | `alternating`, plank closed-chain alternating, primary plane `frontal`, secondary `transverse` | 한 손 지지 perturbation 동안 몸통과 골반 안정성을 보는 anti-rotation 과제로 정의한다. |
| `landmarks` / `angle_definitions` | wrist/shoulder 중심; hip, ankle, pelvis 보조 | active hand trajectory, 어깨 지지, 골반 회전과 측방 이동을 함께 추적한다. |
| `rep_segmentation` / `phase_segmentation` | active wrist vertical trajectory; `Lift` / `Tap` / `Return`; starting side로 wrist 결정 | 각 tap을 원자 반복으로 나누고, 손이 들리고 닿고 돌아오는 phase를 분리한다. |
| `performance_protocol` | 10 left-right pairs; `segmentation_reps_per_count: 2`; `alternating_each_rep` | 피험자 카운트 1회와 segmentation atomic tap 2개를 분리해 저장한다. |
| `camera_protocol` | `Z2` / `Z8`, `H1`, 200-250 cm | 낮은 전방 대각 view에서 골반 회전, 측방 sway, active hand 궤적을 함께 관찰한다. |
| `feature_domains` | alignment, symmetry, reach, support width, rhythm, rotation/lateral-shift control | 안정성, 좌우 순서, anti-rotation control을 feature로 남긴다. |
| `biomechanical_focus` | medial-lateral CoM motion, shoulder/trunk/core/pelvis load regions, load-distribution proxy | 한 손 지지 중 측방 체중 이동과 회전 제어 경향을 본다. |
| `compensation_candidates` | pelvis/trunk rotation, lateral pelvic shift, hip drop, shoulder collapse, side-order error 등 | anti-rotation 과제의 핵심 보상과 protocol adherence 문제를 함께 검토한다. |
| `quality_rules` | visible ratio `0.75`, critical ratio `0.85`, max interpolation gap 3 frames | active wrist와 shoulder/hip landmark가 불안정하면 side-order와 안정성 해석을 제한한다. |

---

## 1. 본 연구에서의 역할

플랭크 숄더탭은 한 손이 지면에서 떨어지는 동안 반대쪽 상지와 양발로 체중을 지지해야 하는
anti-rotation 과제이다. 본 연구에서는 이 운동을 통해 골반 회전, 측방 체중 이동, 지지 기저면
변화, trunk/pelvis stability, 좌우 tap 순서를 관찰한다.

피험자 안내 기준으로는 왼손 tap과 오른손 tap 한 쌍을 1회 protocol cycle로 세지만, segmentation
관점에서는 각 tap이 원자적 움직임 단위가 될 수 있다. 따라서 protocol count와 segmented atomic
rep를 분리해서 기록해야 한다.

---

## 2. 기대되는 움직임

- 기본 플랭크 자세에서 손과 발의 지지 기저면을 유지한다.
- 한 손을 들어 반대쪽 어깨를 터치한 뒤 다시 지면으로 돌아온다.
- 손을 들 때 골반과 몸통의 회전이 과도하지 않다.
- 좌우 tap 순서가 유지된다.
- 엉덩이가 반복적으로 처지거나 높이 들리지 않는다.
- 손 또는 발 위치가 반복 중 크게 이동하지 않는다.

---

## 3. 주요 관찰 구조

| 관찰 요소 | 관련 관절/분절 | 해석 방향 |
|---|---|---|
| 골반 회전 | left/right hip depth | anti-rotation control |
| 측방 체중 이동 | hip_center x, shoulder/hip trajectory | support-arm loading strategy |
| 엉덩이 높이 변화 | hip_center z, hip angle | trunk stability, hip drop/lift |
| active hand trajectory | wrist, shoulder | tap segmentation, missed tap |
| 지지 기저면 | support wrist/ankle/foot | base-of-support shift |
| 좌우 순서 | active side per tap | protocol adherence, motion attribution |

---

## 4. 보상 및 분석 방해 패턴

| 패턴 | 생체역학적 의미 | pose 식별 가능성 | 점수화/통제 방향 | 관련 후보 |
|---|---|---|---|---|
| excessive pelvic rotation | 손을 들 때 골반이 회전하는 패턴. anti-rotation control 부족을 가장 직접적으로 반영한다. | 높음-중간. front-oblique view에서 유리하다. | 점수화 후보 | `pelvis_rotation`, `trunk_rotation` |
| lateral pelvic shift | 체중이 지지 팔 쪽으로 크게 이동하는 패턴. 한 손 지지 상태의 균형 전략을 반영한다. | 높음-중간. hip_center와 camera view에 민감하다. | 점수화 후보 | `lateral_pelvic_shift`, `excessive_com_lateral_shift` |
| hip drop | 엉덩이가 아래로 처지는 패턴. trunk/core stability 저하 또는 피로와 관련될 수 있다. | 중간. 측면 성분과 hip visibility 필요. | 점수화 후보 | `hip_drop` |
| hip height drift | 반복 중 엉덩이가 계속 높아지거나 낮아지는 패턴. 과제 난도 회피 또는 자세 붕괴를 반영한다. | 중간. long set trend 해석이 필요하다. | 점수화 후보 | `hip_height_drift` |
| shoulder collapse/asymmetry | 지지 어깨가 내려앉거나 좌우 어깨 궤적이 달라지는 패턴. 상지 지지 안정성 차이를 시사한다. | 중간. shoulder visibility와 occlusion에 민감하다. | 점수화 후보 또는 해석 제한 | `shoulder_collapse`, `shoulder_asymmetry` |
| side order error | 좌우 tap 순서가 누락되거나 한쪽만 반복되는 패턴. protocol adherence와 attribution에 직접 영향을 준다. | 높음. active hand detection이 필요하다. | 점수화 후보 또는 protocol warning | `side_order_error` |
| missed shoulder tap | 손을 들지만 실제로 반대 어깨를 터치하지 않는 패턴. 과제 수행 여부를 흐리게 한다. | 낮음-중간. 실제 접촉은 pose만으로 확정하기 어렵다. | 주로 통제/해석 제한 요인 | `missed_shoulder_tap` |
| base-of-support shift | 손 또는 발 위치가 반복 중 이동하는 패턴. 안정성 지표의 기준 자체를 바꾼다. | 낮음-중간. 접촉 위치와 landmark 안정성 필요. | 통제 또는 해석 제한 요인 | `base_of_support_shift` |

---

## 5. 데이터 품질과 해석 제한

플랭크 숄더탭은 front-oblique low-angle view에서 골반 회전과 측방 이동을 함께 볼 수 있다. 그러나
active wrist가 몸통 또는 반대쪽 어깨와 겹치면 tap 접촉 여부를 pose만으로 확정하기 어렵다.
따라서 missed shoulder tap은 점수화 후보라기보다 annotation note 또는 해석 제한 요인으로 두는
것이 보수적이다.

손/발 위치 이동은 실제 지면 접촉 변화와 landmark jitter를 구분하기 어렵다. 이 패턴은 automatic
exclusion보다 recording note, base-of-support warning, interpretation confidence note로 남기는
방향이 적절하다.

플랭크 숄더탭은 교대 과제이므로 reliability는 단순 anatomical left/right가 아니라 각 tap의
active/support 역할을 따라가야 한다. active wrist나 support shoulder에서 피처를 계산할 수 있더라도,
active hand가 몸통과 겹치거나 support arm이 가려지거나 camera zone이 rotation과 lateral-shift
해석 중 한쪽을 약하게 만들면 view reliability는 낮게 표시해야 한다. 이 경우 metric은 나쁜
movement-quality score로 바로 바꾸지 않고 low-confidence 또는 not assessed로 보고한다.

---

## 6. 권장 view 해석

플랭크 숄더탭의 기본 권장 view는 낮은 전방 대각(`Z2` 또는 `Z8`, `H1`)이다. 이 view는 한 손이
떨어질 때 나타나는 골반 회전, 측방 체중 이동, 어깨/골반 라인의 흔들림, active hand trajectory를
동시에 관찰하기 위한 절충이다.

순수 정면 view는 좌우 측방 이동과 tap 순서를 보기 좋지만, 골반 회전의 깊이 성분과 손-어깨 접촉
여부를 구분하기 어려울 수 있다. 순수 측면 view는 엉덩이 높이 변화나 hip drop을 보기 좋지만,
active wrist가 몸통과 겹치기 쉬워 tap segmentation과 좌우 순서 해석이 약해질 수 있다. 따라서
본 연구에서는 전방 대각 low-angle view를 기본으로 두고, 측방 이동과 회전 제어를 함께 보는
방향을 택한다.

missed shoulder tap처럼 실제 접촉 여부가 중요한 항목은 pose만으로 확정하기 어렵다. 이 경우
점수화보다 annotation note, protocol warning, 해석 제한 요인으로 남기는 것이 보수적이다.

따라서 계획된 `view_metric_reliability` map은 낮은 전방 대각 view를 핵심 절충안으로 다룬다.
이 view는 pelvic rotation, lateral pelvic shift, active-hand trajectory, side order에는 더 높은
reliability를 줄 수 있지만, 실제 손-어깨 접촉이나 wrist/trunk overlap에 가려지는 피처는 낮게
본다. 순수 정면 view는 lateral shift와 side order confidence를 높이지만 depth rotation을 약화하고,
순수 측면 view는 hip-height confidence를 높일 수 있으나 active-hand segmentation을 약화할 수 있다.

---

## 7. 개발 참고 가능성

플랭크 숄더탭에서 개발 참고 가치가 큰 항목은 protocol cycle과 atomic tap의 분리이다. 한 쌍의
좌우 tap은 피험자 안내 기준 1회이지만, active-hand trajectory에서는 각 tap이 개별 segment가 될
수 있다. 따라서 `protocol_cycle_id`, `rep_unit`, `tap_count`, `rep_side_sequence` 같은 metadata가
필요할 수 있다.

점수화 후보는 pelvic rotation, lateral pelvic shift, hip drop, side-order error처럼 pose
시계열에서 비교적 반복 가능하게 관찰되는 항목부터 검토하는 것이 적절하다.
