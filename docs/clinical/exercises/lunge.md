# 런지 상세 해석 배경 (Lunge Clinical Rationale)

**문서 버전:** 1.1.0
**최종 갱신:** 2026-05-21
**영문 동기화:** `docs_eng/clinical/exercises/lunge.md`는 동일 버전의 영문 번역본이다.

본 문서는 본 연구에서 런지를 포함하는 이유와 alternating split-stance mechanics 해석 방식을
요약한다. 진단 기준도 아니고 코드 명세도 아니다.

관련 문서:

- 수행 프로토콜: [exercise_performance_protocol.md](../../practical_protocols/exercise_performance_protocol.md)
- 운동 YAML: [lunge.yaml](../../../data/definitions/exercises/lunge.yaml)
- 분석 프로파일: [lunge.yaml](../../../data/definitions/analysis_profiles/lunge.yaml)
- Feature meaning map: [per_exercise_mapping.md](../per_exercise_mapping.md)

---

## 1. 연구 내 역할 (Study Role)

런지는 active-side 및 role-based 해석을 위한 주요 하지 운동이다. 한쪽 다리는 forward/load-accepting
limb, 다른쪽은 balance를 돕는 trailing limb 역할을 한다. 본 연구는 이를 통해 side-sequence
provenance, motion attribution, anterior knee travel, trunk alignment, pelvic stability,
step consistency를 검증한다.

좌우 순서는 운동의 고유 속성이 아니라 protocol-specific 선택이다.

## 2. 실행 컨텍스트 (Execution Context)

| Item | Current setting | Interpretation intent |
|---|---|---|
| Classification | alternating split-stance closed-chain | forward/trailing limb role 보존 |
| Primary joints | hip, knee, ankle | 하지 ROM 및 alignment |
| Segmentation | hip-center vertical trajectory, descent/ascent | 반복 lunge cycle 분할 |
| Performance | 한 앞발 5 reps 후 반대 앞발 5 reps | 현재 same-side block; 향후 alternating-each-rep 가능 |
| Camera | Z3/Z7, H2 | knee travel, rear-limb ROM, trunk lean의 side-view 관찰 |
| Biomech focus | vertical + anterior-posterior CoM, hip/knee/ankle load regions | 상대 load-acceptance tendency |

실행 기준은 YAML이다.

## 3. 관찰 대상 (Observation Targets)

```text
forward-leg ROM          forward hip/knee/ankle load acceptance
rear-leg motion          rear hip extension and support strategy
step consistency         ankle/foot trajectory and base of support
trunk alignment          shoulder-hip line
pelvic stability         hip_center and pelvis line
side order               active side per rep
```

기대 수행은 취득 reference이다: 안정된 split stance, 일관된 step length, 통제된 trunk, side switch 중
camera-facing direction 변화 없음.

## 4. 후보 패턴 (Candidate Patterns)

| Pattern | Interpretation direction | Detectability | Status |
|---|---|---|---|
| knee valgus | load acceptance 중 forward-knee medial deviation | 중간; side view에서 frontal 정보 제한 | view warning 포함 구현 후보 |
| asymmetric knee/hip flexion | role-specific ROM difference | active-side metadata가 있으면 높음 | candidate / role-based feature |
| insufficient rear hip extension | rear-limb extension constraint 또는 짧은 step strategy | 중간; side view 필요 | candidate |
| excessive trunk flexion | forward trunk-lean strategy | side view에서 높음 | 구현 후보 |
| lateral trunk lean | side-bending strategy | 중간; frontal/oblique가 유리 | candidate 또는 limitation |
| pelvis drop/shift | pelvic-control proxy | 중간; view/visibility 의존 | candidate |
| heel lift | forward/trailing role context가 필요한 ankle/contact proxy | 중간 | 구현 후보 |
| camera side change | side switch 중 몸이 돌아감 | metadata/video review가 있으면 높음 | control/limitation factor |

## 5. Role 및 View 제한 (Role And View Limits)

단순 anatomical left/right comparison만으로는 부족하다. 각 rep는 다음을 보존해야 한다:

```text
forward_leg / trailing_leg
active_side / support_side
near_side / far_side
expected side sequence / observed side sequence
```

Side view는 anterior knee travel, sagittal ROM, rear-hip extension, trunk flexion,
step length를 지지한다. Frontal/oblique view는 step width, pelvis drop/shift,
lateral trunk lean, frontal knee alignment를 지지한다. 이는 confidence state이지 직접 penalty가 아니다.

한쪽 limb가 지속적으로 far-side이거나 visibility가 낮으면 side-to-side comparison을 unilateral
movement deficit로 해석하지 말고 unavailable 또는 low-confidence로 처리한다.

## 6. 개발 경계 (Development Boundary)

런지의 고가치 개발 작업은 side-sequence provenance를 보존해야 한다. 향후 alternating-each-rep
variant가 추가되면 exercise name만으로는 부족하고 protocol profile 또는 별도 YAML variant가
필요할 수 있다.
