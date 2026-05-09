# 플랭크 숄더탭 상세 해석 배경 (Plank Shoulder Tap Clinical Rationale)

**문서 버전:** 1.0.0  
**최종 갱신:** 2026-05-09  
**영문 동기화:** `docs_eng/clinical/exercises/plank_shoulder_tap.md`는 동일 버전의 영문 번역본이다.

본 문서는 플랭크 숄더탭이 본 연구에서 어떤 생체역학적 의미를 갖는지, anti-rotation 과제를
어떻게 해석할 수 있는지, 어떤 패턴을 점수화 후보 또는 통제 요인으로 다룰 수 있는지를 정리한다.
이 문서는 임상 진단 기준이나 코드 구현 명세가 아니다.

관련 문서:

- 수행 프로토콜: [exercise_performance_protocol.md §2-4](../../practical_protocols/exercise_performance_protocol.md#2-4-플랭크-숄더탭-plank-shoulder-tap)
- 운동 정의 YAML: `data/definitions/exercises/plank_shoulder_tap.yaml`
- 피처 의미 매핑: [per_exercise_mapping.md §Plank Shoulder Tap](../per_exercise_mapping.md#plank-shoulder-tap-플랭크-숄더탭)

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

---

## 6. 개발 참고 가능성

플랭크 숄더탭에서 개발 참고 가치가 큰 항목은 protocol cycle과 atomic tap의 분리이다. 한 쌍의
좌우 tap은 피험자 안내 기준 1회이지만, active-hand trajectory에서는 각 tap이 개별 segment가 될
수 있다. 따라서 `protocol_cycle_id`, `rep_unit`, `tap_count`, `rep_side_sequence` 같은 metadata가
필요할 수 있다.

점수화 후보는 pelvic rotation, lateral pelvic shift, hip drop, side-order error처럼 pose
시계열에서 비교적 반복 가능하게 관찰되는 항목부터 검토하는 것이 적절하다.

