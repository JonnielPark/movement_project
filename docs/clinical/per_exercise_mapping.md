# 운동별 피처 x 임상적 의미 매핑 (Per-Exercise Feature x Clinical Meaning Mapping)

**문서 버전:** 1.1.0
**최종 갱신:** 2026-05-21
**영문 동기화:** `docs_eng/clinical/per_exercise_mapping.md`는 동일 버전의 영문 번역본이다.

본 문서는 4개 검증 운동의 구현된 feature family와 해석 경계를 요약한다.
자세한 tooltip 문장은 [`data/definitions/clinical/feature_meanings.yaml`](../../data/definitions/clinical/feature_meanings.yaml)에
유지한다.

이 매핑은 설명용이다. 진단, 치료 효과, 환자 분류, 보호된 scoring text를 정의하지 않는다.

---

## 1. Record Levels

```text
rep            repetition당 1개 record
rep / phase    repetition 및 phase당 1개 record
set            세트 전체를 포괄하는 1개 record
rep_*          rep별로 확장되는 template id, 예: temporal.tempo.rep_1
```

Phase-level variant는 `spatial.rom`, `spatial.shape`, `control.stability`에서만 방출된다.
Compensation feature는 full rep trajectory 위에서 동작하므로 rep-level이다.

`spatial.symmetry.*`는 [08_feature_extraction.md](../pipeline/08_feature_extraction.md)의
feature-availability gate를 통과한 뒤에만 해석한다. 측면 단안 rendering은 직접 정면 관찰 근거가
아니다. 지지되지 않는 symmetry feature는 `low_confidence` 또는 `not_assessed`로 보고해야 한다.

## 2. 운동별 Feature Family (Feature Families By Exercise)

| Exercise | ROM | Symmetry | Shape | Temporal | Stability | Implemented compensation |
|---|---|---|---|---|---|---|
| Squat | hip/knee/ankle | hip/knee/ankle | hip/knee/ankle arc length; descent/ascent ratio | rep tempo, tempo CV | hip_center x/z | knee valgus/varus, trunk flexion, pelvic shift, heel lift, pelvic rotation |
| Lunge | hip/knee/ankle | hip/knee/ankle | hip/knee/ankle arc length; descent/ascent ratio | rep tempo, tempo CV | hip_center x/z | knee valgus, trunk flexion, pelvic shift, heel lift |
| Pike push-up | shoulder/elbow/hip | shoulder/elbow/hip | shoulder/elbow/wrist arc length; descent/ascent ratio | rep tempo, tempo CV | hip_center x/z | 아직 구현 없음 |
| Plank shoulder tap | shoulder/elbow/hip | shoulder/elbow/hip | wrist/shoulder arc length | rep tempo, tempo CV | hip_center x/z | pelvic rotation, lateral pelvic shift |

Common units:

```text
degree                  joint-angle ROM 및 trunk-angle feature
torso_length_ratio      정규화 distance/trajectory feature
torso_length_ratio_per_rep ⑧ load-shift trend
second                  rep duration
dimensionless_cv        coefficient of variation / symmetry index
dimensionless           ratio
```

## 3. 구현된 Compensation Features

| Exercise | Feature ids | 해석 경계 |
|---|---|---|
| Squat | `control.compensation.knee_valgus.left/right` | 관상면 knee deviation proxy; view support와 foot/hip/ankle landmark reliability 필요. |
| Squat | `control.compensation.knee_varus.left/right` | lateral knee deviation proxy; stance width와 view에 민감. |
| Squat | `control.compensation.excessive_trunk_flexion` | trunk-lean proxy; 상대 load strategy 해석이며 spine diagnosis가 아님. |
| Squat | `control.compensation.lateral_pelvic_shift` | pelvis displacement 기반 weight-shift proxy. |
| Squat | `control.compensation.heel_lift.left/right` | heel-elevation proxy; contact와 landmark visibility가 confidence를 제한할 수 있음. |
| Squat | `control.compensation.pelvic_rotation` | hip-depth asymmetry proxy; 단안 depth에 민감. |
| Lunge | `control.compensation.knee_valgus.left/right` | forward-leg 또는 side-specific knee deviation; active/forward-leg context 보존 필요. |
| Lunge | `control.compensation.excessive_trunk_flexion` | split stance에서의 forward trunk-lean proxy. |
| Lunge | `control.compensation.lateral_pelvic_shift` | pelvic-control proxy; view와 hip visibility 의존. |
| Lunge | `control.compensation.heel_lift.left/right` | forward/trailing-leg role과 함께 해석 필요. |
| Plank shoulder tap | `control.compensation.pelvic_rotation` | hip-depth asymmetry 기반 anti-rotation proxy. |
| Plank shoulder tap | `control.compensation.lateral_pelvic_shift` | one-hand support 중 lateral weight-shift proxy. |

Pike push-up compensation candidate는 현재 YAML 후보일 뿐이다. `COMPENSATION_RULES`에 대응 규칙이
추가되기 전에는 구현 feature로 나열하지 않는다.

## 4. Pending Candidate 처리 (Pending Candidate Handling)

Exercise YAML에는 구현되지 않은 candidate가 있을 수 있다. Runtime behavior:

```text
matching rule in COMPENSATION_RULES        feature 방출 가능
no matching rule                           UserWarning; 이 mapping에서는 생략
```

Pending candidate는 연구 메모이며 숨은 score component가 아니다.

## 5. 코드와 데이터 매핑 (Code And Data Mapping)

```text
src/movement/features/
data/definitions/clinical/feature_meanings.yaml
docs_eng/pipeline/08_feature_extraction.md
docs_eng/pipeline/10_biomarker_scoring.md
```

Feature family, unit, interpretation boundary가 바뀌면 `docs_eng/`를 먼저 수정하고,
`docs/`를 동기화한 뒤 YAML/code를 수정한다.
