# 플랭크 숄더탭 상세 해석 배경 (Plank Shoulder Tap Clinical Rationale)

**문서 버전:** 1.1.0
**최종 갱신:** 2026-05-21
**영문 동기화:** `docs_eng/clinical/exercises/plank_shoulder_tap.md`는 동일 버전의 영문 번역본이다.

본 문서는 본 연구에서 플랭크 숄더탭을 포함하는 이유와 anti-rotation mechanics 해석 방식을
요약한다. 진단 기준도 아니고 코드 명세도 아니다.

관련 문서:

- 수행 프로토콜: [exercise_performance_protocol.md](../../practical_protocols/exercise_performance_protocol.md)
- 운동 YAML: [plank_shoulder_tap.yaml](../../../data/definitions/exercises/plank_shoulder_tap.yaml)
- 분석 프로파일: [plank_shoulder_tap.yaml](../../../data/definitions/analysis_profiles/plank_shoulder_tap.yaml)
- Feature meaning map: [per_exercise_mapping.md](../per_exercise_mapping.md)

---

## 1. 연구 내 역할 (Study Role)

플랭크 숄더탭은 stability-under-perturbation을 보는 주요 task이다. 한 손이 바닥에서 떨어지고
반대 팔과 양발이 몸을 지지한다. 본 연구는 pelvic rotation, lateral weight shift,
base-of-support change, trunk/pelvis stability, left-right tap order를 관찰한다.

피험자 count와 segmentation unit은 다르다. left tap + right tap은 하나의 protocol cycle이지만,
각 tap은 atomic segmented rep가 될 수 있다.

## 2. 실행 컨텍스트 (Execution Context)

| Item | Current setting | Interpretation intent |
|---|---|---|
| Classification | alternating plank closed-chain | one-hand support 중 anti-rotation |
| Primary joints | wrist, shoulder, hip, pelvis/trunk support | active hand, support arm, pelvis/trunk control |
| Segmentation | active-wrist trajectory, Lift/Tap/Return | atomic tap segmentation |
| Performance | 10 left-right protocol cycles; count당 2 atomic reps | user count와 segmentation reps 분리 |
| Camera | Z2/Z8, H1 | rotation + lateral shift를 위한 low front-oblique view |
| Biomech focus | medial-lateral CoM, shoulder/trunk/core/pelvis regions | 상대 one-hand-support tendency |

실행 기준은 YAML이다.

## 3. 관찰 대상 (Observation Targets)

```text
pelvic rotation          left/right hip depth
lateral weight shift     hip_center x and shoulder/hip trajectory
hip-height change        hip_center z and hip angle
active hand trajectory   wrist and shoulder
base of support          support wrist/ankle/foot
side order               active side per tap
```

기대 수행은 취득 reference이다: high plank, 통제된 trunk/pelvis rotation, side order 유지,
최소 support repositioning.

## 4. 후보 패턴 (Candidate Patterns)

| Pattern | Interpretation direction | Detectability | Status |
|---|---|---|---|
| pelvic rotation | hip-depth asymmetry 기반 anti-rotation control proxy | front-oblique에서 높음-중간 | 구현 후보 |
| lateral pelvic shift | support arm 쪽 weight shift | 높음-중간; hip-center/view 의존 | 구현 후보 |
| hip drop / height drift | trunk/core stability 또는 posture deterioration proxy | 중간 | pending candidate |
| shoulder collapse/asymmetry | support-arm stability proxy | 중간; shoulder visibility 의존 | pending candidate |
| side order error | protocol-adherence 및 attribution issue | active-hand detection이 있으면 높음 | candidate/protocol warning |
| missed shoulder tap | true contact uncertainty | 낮음-중간 | control/limitation factor |
| base-of-support shift | support reference 변화 | 낮음-중간 | control/limitation factor |

현재 구현된 compensation feature는 pelvic rotation과 lateral pelvic shift뿐이다.

## 5. View 및 품질 제한 (View And Quality Limits)

Low front-oblique view (`Z2`/`Z8`, `H1`)가 기본 절충안이다. pelvic rotation, lateral shift,
shoulder/pelvis sway, active-hand trajectory를 함께 지지한다.

Pure frontal view는 lateral shift와 side order를 강화할 수 있지만 depth rotation을 약화한다.
Pure side view는 hip-height review를 강화할 수 있지만 active wrist overlap이 tap segmentation과
side-order interpretation을 약화할 수 있다.

Missed tap은 true contact가 필요하며 pose만으로 robust하게 증명하기 어렵다. 검증 전에는
annotation note, protocol warning, interpretation limitation으로 다룬다.

## 6. 개발 경계 (Development Boundary)

초기 고가치 규칙:

```text
pelvis_rotation
lateral_pelvic_shift
hip_drop
side_order_error
```

`protocol_cycle_id`, `rep_unit`, `tap_count`, `rep_side_sequence`를 유지해 user-facing count와
atomic tap segmentation이 하나의 모호한 label로 합쳐지지 않게 한다.
