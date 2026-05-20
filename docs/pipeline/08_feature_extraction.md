# 08. 피처 추출 (Feature Extraction)

**문서 버전:** 1.2.0
**최종 갱신:** 2026-05-21
**영문 동기화:** `docs_eng/pipeline/08_feature_extraction.md`는 동일 버전의 영문 번역본이다.

파이프라인 단계 ⑧은 정규화된 pose 데이터에서 movement-quality feature를 계산한다. Pose 좌표는
수정하지 않는다. 모든 출력은 numeric value, unit, `source_fields`, availability/reliability
metadata를 가진 `FeatureRecord`이며, ⑩ Biomarker Derivation이 provenance를 추적할 수 있게 한다.

---

## 1. 파이프라인 위치 (Pipeline Position)

```text
⑤ Normalization → ⑥ Segmentation → ⑦ Motion Attribution
→ ⑧ Feature Extraction     ← 본 단계
→ ⑨ Biomech Proxy → ⑩ Biomarker Derivation
```

필수 입력:

```text
<landmark>_norm_x/y/z       정규화 좌표
rep_id                      확정된 반복 label
phase                       ⑥에서 온 선택 phase label
exercise_definition         feature_domains, angle_definitions,
                            compensation_candidates, view_metric_reliability
recording provenance        camera_zone, camera_height_level이 있으면 사용
preprocessing context       visibility, swap risk, far-side jitter, availability hooks
```

---

## 2. 설계 계약 (Design Contract)

허용:

```text
YAML angle_definitions 기반 joint included angle
반복 단위 및 phase 단위 집계
Registry 기반 compensation candidate dispatch
Feature availability/reliability metadata
source_fields provenance
degree, second, dimensionless, dimensionless_cv, torso_length_ratio 단위
```

금지:

```text
feature code에서 exercise_id로 분기
source_fields 없는 FeatureRecord
절대 force/torque/length 출력
camera-view 한계를 movement-quality penalty로 직접 변환
feature ID에서 kinematic phase label과 kinetic phase 명칭 혼합
```

---

## 3. 피처 계열 (Feature Families)

Domain은 `feature_id` prefix로 표시한다.

```text
spatial.*
    ROM, 좌우 대칭, trajectory shape, alignment/depth proxy.

temporal.*
    rep duration, phase duration, tempo variability, rhythm/smoothness proxy.

control.*
    hip-center stability와 knee_valgus, knee_varus, lateral_pelvic_shift,
    excessive_trunk_flexion, heel_lift, pelvis_rotation 같은 compensation candidate.
```

`feature_domains.biomechanical_proxy`는 ⑧ extractor 누락이 아니라 ⑨ Biomech Proxy로 전달되는
항목이다.

---

## 4. Availability And View Reliability

Feature extraction은 camera view 또는 pose model이 scoring을 뒷받침하지 않는 값도 계산할 수
있다. 따라서 `FeatureRecord.availability`가 ⑩ scoring gate다.

```text
assessed
    baseline이 있으면 composite scoring에 들어갈 수 있다.

low_confidence
    numeric value는 report할 수 있지만 기본적으로 composite scoring에서 withheld된다.

not_assessed
    scoring에 사용하지 않고 unavailable/provenance로만 보고한다.
```

Resolver가 결합하는 정보:

```text
view_reliability             exercise_definition.view_metric_reliability
landmark_quality             visibility / coverage / preprocessing context
depth_dependency             none | low | moderate | high | unknown
model_depth_reliability      high | moderate | low | unknown
swap or far-side risk         ④ Preprocessing과 ⑦ Motion Attribution에서 제공
camera_zone                  annotation 또는 recording metadata
role_context                 active/support/near/far side가 있으면 사용
```

측면 또는 측면에 가까운 squat recording에서는 sagittal 및 centerline feature가 gate를 통과하면
assessed로 남을 수 있다. Rotated monocular skeleton에서 나온 depth-sensitive bilateral symmetry는
frontal/front-oblique evidence가 없으면 `low_confidence` 또는 `not_assessed`로 둔다.

편측 또는 교대 운동에서는 단순 anatomical left/right보다 `forward_leg`, `trailing_leg`,
`active_side`, `support_side` 같은 role label을 사용한다.

---

## 5. Phase-Aware Features

⑥이 `phase` column을 제공하면 다음 계열은 rep-level과 phase-level record를 모두 방출할 수 있다.

```text
spatial.rom
spatial.shape
temporal.tempo
control.stability
```

규칙:

```text
Rep-level record      phase = None
Phase-level record    phase = "Descent" 등; feature_id에 lower-case suffix 추가
source_fields         phase_segmentation provenance 포함
control.compensation  별도 phase-specific rule이 없으면 rep-level only
```

`summarize_phase_to_rep()`는 descent/ascent ROM ratio 같은 파생 rep-level summary를 추가할 수 있다.
입력 record는 수정하지 않는다.

---

## 6. 출력 계약 (Output Contract)

```python
@dataclass
class FeatureRecord:
    feature_id: str
    exercise_id: str
    rep_id: int | None
    value: float
    unit: str
    source_fields: list[str]
    note: str | None = None
    phase: str | None = None
    view_reliability: str = "unknown"
    availability: str = "assessed"
    availability_reasons: list[str] = field(default_factory=list)
    camera_zone: str | None = None
    role_context: dict[str, str] | None = None
    depth_dependency: str = "unknown"
    model_depth_reliability: str = "unknown"
    landmark_quality: str = "unknown"
```

`features_to_dataframe()`은 record 목록을 tabular output으로 펼치며 phase, availability,
camera-zone, provenance field를 보존한다.

---

## 7. 감사 리포트 (Audits)

⑧은 feature record 옆에 diagnostic audit를 방출할 수 있다.

```text
Feature registry coverage
    YAML feature_domain entry와 compensation candidate가 implemented, routed to another
    step, unsupported, declared but deferred 중 어디에 해당하는지 보고한다.

Analysis-disrupting pattern detectability
    performance_protocol.analysis_disrupting_patterns를
    pose_detectable_scoring_candidate, acquisition_control_factor,
    interpretation_limitation_factor, unknown으로 분류한다.
```

Audit는 provenance/reporting 출력이다. 좌표를 바꾸거나 반복을 제외하거나 점수를 만들지 않는다.

---

## 8. 진입점 (Entry Point)

```python
from movement.features import (
    extract_rep_features,
    features_to_dataframe,
    summarize_phase_to_rep,
)

records = extract_rep_features(df, exercise_definition)
records += summarize_phase_to_rep(records)
feat_df = features_to_dataframe(records)
```

---

## 9. 다른 단계와의 관계 (Relationship To Other Steps)

- ⑥ Segmentation은 `rep_id`와 선택 `phase`를 제공한다. Phase label이 없으면 rep-level feature만
  산출한다.
- ⑦ Motion Attribution은 role-aware feature를 위한 side/consistency context를 제공한다.
- ⑨ Biomech Proxy는 같은 정규화 좌표를 사용하지만 `FeatureRecord`가 아니라 `BiomechRecord`를
  방출한다.
- ⑩ Biomarker Derivation은 모든 feature를 pass-through biomarker로 감싸고,
  `availability == assessed`인 feature만 composite scoring에 사용한다.
- ⑫ Simulation은 pose-detectable audit entry를 perturbation candidate로 사용할 수 있다.

---

## 10. 코드 매핑 (Code Mapping)

```text
src/movement/features/__init__.py        FeatureRecord, extract_rep_features,
                                         audits, summarize_phase_to_rep,
                                         features_to_dataframe
src/movement/features/spatial.py         ROM, symmetry, shape
src/movement/features/temporal.py        tempo, variability
src/movement/features/control.py         stability, compensation
src/movement/features/compensation.py    COMPENSATION_RULES registry
tests/test_feature_view_reliability.py   availability metadata
tests/test_feature_registry_coverage.py  feature/compensation coverage audit
tests/test_analysis_disrupting_patterns.py detectability audit
tests/test_features_phase_grouping.py    phase-level feature behavior
```

---

## 11. 향후 확장 (Planned Extensions)

- source fields, visibility policy, test가 준비된 compensation rule 추가.
- coarse preprocessing summary 대신 per-feature landmark coverage 사용.
- lunge와 plank shoulder tap을 위한 role-aware feature family.
- scored feature와 computed-but-withheld feature를 함께 보여주는 reporting view.
