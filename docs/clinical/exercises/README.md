# 운동별 상세 해석 문서 (Per-Exercise Clinical Rationale)

**문서 버전:** 1.1.0
**최종 갱신:** 2026-05-21
**영문 동기화:** `docs_eng/clinical/exercises/README.md`는 동일 버전의 영문 번역본이다.

이 폴더는 현재 4개 검증 운동의 생체역학적 해석 배경을 보관한다.
여기서 "임상적"은 전문가의 동작 관찰 맥락을 뜻하며, 질환 진단, 치료 효과 입증,
환자 분류를 의미하지 않는다.

이 문서는 실행 명세가 아니다. 실행 기준은 YAML과 코드이다. 해석 문장은 pipeline 문서를
먼저 갱신한 뒤에만 `compensation_patterns`, `analysis_disrupting_patterns`, feature registry,
scoring rule로 승격할 수 있다.

---

## 1. 문서 목록 (Document List)

| Exercise | Rationale | Exercise YAML | Performance protocol |
|---|---|---|---|
| Squat | [squat.md](squat.md) | [squat.yaml](../../../data/definitions/exercises/squat.yaml) | [exercise_performance_protocol.md](../../practical_protocols/exercise_performance_protocol.md) |
| Lunge | [lunge.md](lunge.md) | [lunge.yaml](../../../data/definitions/exercises/lunge.yaml) | [exercise_performance_protocol.md](../../practical_protocols/exercise_performance_protocol.md) |
| Pike Push-up | [pike_pushup.md](pike_pushup.md) | [pike_pushup.yaml](../../../data/definitions/exercises/pike_pushup.yaml) | [exercise_performance_protocol.md](../../practical_protocols/exercise_performance_protocol.md) |
| Plank Shoulder Tap | [plank_shoulder_tap.md](plank_shoulder_tap.md) | [plank_shoulder_tap.yaml](../../../data/definitions/exercises/plank_shoulder_tap.yaml) | [exercise_performance_protocol.md](../../practical_protocols/exercise_performance_protocol.md) |

## 2. 승격 규칙 (Promotion Rule)

해석 항목이 계산 규칙이 될 때:

```text
1. docs_eng/pipeline/ 및 docs/pipeline/에 feature, unit, confidence/provenance policy를 정의한다.
2. analysis profile, performance protocol, camera protocol, interpretation rule YAML을 추가/수정한다.
3. 테스트와 함께 코드를 구현한다.
4. 구현된 동작만 per-exercise mapping에 반영한다.
```

해석 문장이 숨은 scoring rule이 되지 않게 한다.

## 3. 공통 라벨 (Shared Labels)

| Label | 의미 |
|---|---|
| Score-eligible feature | 관절 포인트 시계열에서 식별 가능해 향후 feature/biomarker로 연결할 수 있는 패턴 |
| Control factor | 취득 행동 또는 pose uncertainty와 분리하기 어려운 패턴 |
| Interpretation-limitation factor | 직접 penalty가 아니라 confidence limitation으로 표시해야 하는 패턴 |
| High detectability | 현재 landmark와 권장 view에서 비교적 명확함 |
| Medium detectability | 적절한 view, confidence, annotation support가 필요함 |
| Low detectability | pose 시계열만으로 어렵거나 외부 정보가 필요함 |

## 4. 측면 촬영 규칙 (Side-View Rule)

편측 운동과 측면 촬영에서는 먼쪽 관절이 안정적일 수도 있고, occlusion과 left/right overlap 때문에
불안정할 수도 있다. 먼쪽 confidence나 jitter가 나쁘면 해당 feature를 나쁜 movement quality가
아니라 unavailable 또는 low-confidence로 처리한다.

Bilateral symmetry feature는 양측 coverage와 view support가 충분할 때만 해석한다. 그렇지 않으면
`hip_center`, `shoulder_center`, trunk angle, vertical motion, visible-side sagittal ROM 같은
centerline 또는 visible-side feature를 우선한다.

## 5. Asset 정책 (Asset Policy)

대표 수행 사진은 다음에 둔다:

```text
docs/practical_protocols/assets/
docs_eng/practical_protocols/assets/
```

운동 해석 그림은 다음에 둔다:

```text
docs/clinical/exercises/assets/<exercise_id>/
docs_eng/clinical/exercises/assets/<exercise_id>/
```

그림 안에 텍스트가 없으면 양 언어에서 같은 파일명을 사용한다. 언어별 label이 있으면
`*_ko.png`, `*_eng.png`를 사용한다.
