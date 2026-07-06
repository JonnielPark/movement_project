# 파이크 푸쉬업 상세 해석 배경 (Pike Push-up Clinical Rationale)

**문서 버전:** 1.1.0
**최종 갱신:** 2026-05-21
**영문 동기화:** `docs_eng/clinical/exercises/pike_pushup.md`는 동일 버전의 영문 번역본이다.

본 문서는 본 연구에서 파이크 푸쉬업을 포함하는 이유와 inverted upper-body support mechanics
해석 방식을 요약한다. 진단 기준도 아니고 코드 명세도 아니다.

관련 문서:

- 수행 프로토콜: [exercise_performance_protocol.md](../../practical_protocols/exercise_performance_protocol.md)
- 운동 YAML: [pike_pushup.yaml](../../../data/definitions/exercises/pike_pushup.yaml)
- 분석 프로파일: [pike_pushup.yaml](../../../data/definitions/analysis_profiles/pike_pushup.yaml)
- Feature meaning map: [per_exercise_mapping.md](../per_exercise_mapping.md)

---

## 1. 연구 내 역할 (Study Role)

파이크 푸쉬업은 inverted upper-body closed-chain task이다. shoulder/elbow ROM과 symmetry,
head descent, inverted-V 유지, hip-height change, 어려운 bodyweight task에서의 support consistency를
관찰하는 데 사용한다.

self-occlusion과 partial completion이 흔하므로 visibility limit와 performance failure-point
기록을 테스트하는 데도 유용하다.

## 2. 실행 컨텍스트 (Execution Context)

| Item | Current setting | Interpretation intent |
|---|---|---|
| Classification | bilateral symmetric, inverted closed-chain | upper-body support task |
| Primary joints | shoulder, elbow, wrist, trunk | push mechanics and support consistency |
| Segmentation | nose/head vertical trajectory, descent/ascent | head descent as depth proxy |
| Performance | 10 reps 또는 clean maximum with failure provenance | partial completion이 예상되는 어려운 task |
| Camera | Z3/Z7, H1 | head descent와 hip position을 위한 low side view |
| Biomech focus | shoulder/elbow/wrist/trunk load regions | 상대 support tendency만 해석 |

실행 기준은 YAML이다.

## 3. 관찰 대상 (Observation Targets)

```text
head descent              nose 또는 head proxy
shoulder ROM              shoulder angle and side symmetry
elbow ROM                 push-phase control and flare tendency
hip height                hip_center and hip angle
support consistency         wrist/ankle/foot contact trajectories
upper-limb symmetry       left/right shoulder and elbow features
```

기대 수행은 취득 reference이다: hip은 inverted V로 높게 유지하고, head는 손 사이로 내려가며,
support point는 크게 이동하지 않는다.

## 4. 후보 패턴 (Candidate Patterns)

| Pattern | Interpretation direction | Detectability | Status |
|---|---|---|---|
| insufficient head descent | partial depth proxy | 높음-중간; nose가 불안정하면 head proxy 필요 | pending candidate |
| head forward shift | load-avoidance trajectory proxy | 중간; side view가 유리 | pending candidate |
| elbow flare | altered support strategy | 중간; view/elbow visibility 의존 | pending candidate |
| shoulder asymmetry | unequal upper-limb support proxy | 중간; self-occlusion 민감 | pending candidate |
| hip drop | regular push-up에 가까워지는 task change | side view에서 높음 | pending candidate |
| hip pike variation | hip-height strategy 변화 | 중간 | pending candidate |
| hand/foot repositioning | support-reference change | 낮음-중간 | control/limitation factor |
| tempo instability | task difficulty에 따른 timing drift | stable segmentation이 있으면 높음 | candidate |

현재 `COMPENSATION_RULES`에 구현된 pike push-up compensation feature는 없다. 후보는 규칙과
테스트가 생기기 전까지 연구 메모로 남긴다.

## 5. View 및 품질 제한 (View And Quality Limits)

기본 view는 low side (`Z3`/`Z7`, `H1`)이다. head descent, hip pike/drop, vertical upper-body
motion을 지지한다. Frontal/oblique view는 elbow flare와 shoulder asymmetry에는 도움 될 수 있지만
head depth에는 덜 직접적이다.

Far-side elbow 또는 wrist occlusion이 흔하다. 먼쪽 landmark가 불안정하면 upper-limb symmetry를
직접 감점하지 않는다. visible-side sagittal ROM, head descent, hip position, trunk/hip alignment를
우선한다.

낮은 repetition count는 그 자체로 점수가 아니다. actual count, failure point, failure reason과
함께 해석한다.

## 6. 개발 경계 (Development Boundary)

초기 고가치 규칙 후보:

```text
insufficient_head_descent
hip_drop
head_forward_shift
```

Shoulder asymmetry와 elbow flare는 view 및 self-occlusion 의존성이 있어 detectability check 이후에
다룬다.
