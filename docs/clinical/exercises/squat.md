# 스쿼트 상세 해석 배경 (Squat Clinical Rationale)

**문서 버전:** 1.1.0
**최종 갱신:** 2026-05-21
**영문 동기화:** `docs_eng/clinical/exercises/squat.md`는 동일 버전의 영문 번역본이다.

본 문서는 본 연구에서 스쿼트를 포함하는 이유와 동작 패턴 해석 방식을 요약한다.
진단 기준도 아니고 코드 명세도 아니다.

관련 문서:

- 수행 프로토콜: [exercise_performance_protocol.md](../../practical_protocols/exercise_performance_protocol.md)
- 운동 YAML: [squat.yaml](../../../data/definitions/exercises/squat.yaml)
- 분석 프로파일: [squat.yaml](../../../data/definitions/analysis_profiles/squat.yaml)
- Feature meaning map: [per_exercise_mapping.md](../per_exercise_mapping.md)

---

## 1. 연구 내 역할 (Study Role)

스쿼트는 양측 하지 reference task이다. 단안 포즈 데이터에서 hip-knee-ankle coordination,
descent depth, trunk alignment, hip-center stability, 좌우 symmetry를 관찰하는 데 사용한다.

본 프로젝트에서의 가치는 방법론적이다. 반복 구조가 명확하고 흔한 보상 후보가 관찰되기 쉽다.
임상적 정상 기준을 정의하지 않는다.

## 2. 실행 컨텍스트 (Execution Context)

| Item | Current setting | Interpretation intent |
|---|---|---|
| Classification | bilateral symmetric, standing closed-chain | 양측 하지 coordination reference task |
| Primary joints | hip, knee, ankle | triple flexion/extension 및 하지 alignment |
| Segmentation | hip-center vertical trajectory, descent/ascent | 반복 cycle 검증이 쉬운 구조 |
| Camera | Z2/Z8, H2 | knee tracking과 depth를 함께 보는 절충 view |
| Main feature families | ROM, symmetry, arc length, tempo, stability, compensation | spatial/temporal/control 전반 검증 |
| Biomech focus | vertical CoM, hip/knee/ankle load regions | 상대 load-distribution proxy만 해석 |

실행 기준은 이 해석 문장이 아니라 YAML이다.

## 3. 관찰 대상 (Observation Targets)

```text
descent depth              hip_center 및 hip/knee/ankle ROM
knee tracking              hip-knee-ankle line
heel contact               heel/ankle/foot landmarks
trunk lean                 shoulder-hip line
lateral pelvic shift       hip_center x trajectory
bilateral symmetry         left/right hip, knee, ankle features
```

기대 수행은 데이터 취득 reference이다: 안정된 foot contact, 협응된 hip/knee/ankle flexion,
일관된 depth/tempo, 과도하지 않은 trunk folding.

## 4. 후보 패턴 (Candidate Patterns)

| Pattern | Interpretation direction | Detectability | Status |
|---|---|---|---|
| knee valgus | 부하 중 medial knee-deviation proxy | frontal/front-oblique에서 높음 | 구현 후보 |
| knee varus | lateral knee-deviation proxy; stance/view 민감 | 중간 | 제한 포함 구현 후보 |
| excessive trunk flexion | forward trunk-lean strategy | side/front-oblique에서 높음 | 구현 후보 |
| lateral pelvic shift | weight-shift proxy | 중간; view 의존 | 구현 후보 |
| heel lift | ankle/forefoot-loading proxy | 중간; heel visibility 의존 | 구현 후보 |
| pelvic rotation | hip-depth asymmetry proxy | 낮음-중간; depth 민감 | 주의 포함 구현 후보 |
| arm swing | 상지 momentum이 하지 trajectory를 오염 | 중간 | control factor |
| unstable foot contact | support 변화로 비교 가능성 저하 | 낮음-중간 | control/limitation factor |

위 용어는 movement-quality proxy이지 진단이 아니다.

## 5. View 및 품질 제한 (View And Quality Limits)

Front-oblique view가 기본 절충안이다. 더 frontal한 view는 frontal knee/pelvis alignment를,
더 side에 가까운 view는 depth, sagittal ROM, trunk lean, heel-lift review를 강화한다.

Side-view 또는 near-side-view recording에서는 bilateral symmetry가 view-dependent이다.
회전시킨 단안 3D rendering은 직접 정면 근거를 만들지 않는다. far-side visibility, depth
plausibility, swap risk가 충분하지 않으면 symmetry feature는 `low_confidence` 또는
`not_assessed`로 처리한다.

View support가 약하면 다음 sagittal/centerline feature를 우선한다:

```text
descent depth
hip/knee/ankle ROM
trunk lean
heel lift
hip-center trajectory stability
tempo and smoothness
```

## 6. 개발 경계 (Development Boundary)

해석 항목이 scoring feature가 될 때:

```text
1. pipeline docs에 feature/unit/provenance를 정의한다.
2. YAML candidate 또는 interpretation rule에 연결한다.
3. 재현 가능한 detectability에 대한 최소 테스트를 추가한다.
4. 구현 후에만 per-exercise mapping을 갱신한다.
```
