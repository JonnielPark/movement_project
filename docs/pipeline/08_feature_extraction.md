# 08. 피처 추출 (Feature Extraction)

**문서 버전:** 1.0.9
**최종 갱신:** 2026-05-12
**영문 동기화:** `docs_eng/pipeline/08_feature_extraction.md`는 동일 버전의 영문 번역본이다.

파이프라인 단계 ⑧. 정규화된 포즈 데이터로부터 동작 품질 피처를 계산한다.
각 피처는 `(value, unit, source_fields)`를 가진 `FeatureRecord`로 반환되어,
후속 바이오마커 도출(⑩)이 산출 근거(provenance)를 추적할 수 있게 한다.

원시 관절각을 넘어, 본 설계는 모든 지표가 임상적 추론 범주에 명확히 매핑되도록
**공간(spatial) / 시간(temporal) / 제어(control)** 의 3 도메인 분해를 엄격하게 강제한다.
학위논문 §5에 해당.

---

## 1. 파이프라인 위치 (Pipeline Position)

```text
Pose CSV
→ ① Validation
→ ② Annotation
→ ③ Exercise Definition
→ ④ Preprocessing
→ ⑤ Normalization
→ ⑥ Segmentation
→ ⑦ Motion Attribution
→ ⑧ Feature Extraction         ← 본 단계
→ ⑨ Biomech Proxy
→ ⑩ Biomarker Derivation
```

필수 입력:
```text
정규화 좌표                ⑤에서 온 <landmark>_norm_x/y/z 칼럼
반복 경계                  ②에서 온 segment_type == 'rep' + rep_id
phase 칼럼 (선택)          ⑥에서 온 값; 구간 단위 피처 방출 활성화
운동 정의                  angle_definitions, feature_domains, compensation_candidates
```

좌표를 수정하지 않는다. `FeatureRecord` 행만 추가한다; 포즈 데이터프레임은 그대로 보존된다.

## 2. 설계 원칙 (Design Principle)

```text
허용:
    angle_definitions 트리플렛에서의 관절별 끼인각
    반복별 집계 (min, max, range, std, arc length)
    ⑥의 phase 칼럼이 채워진 경우 (rep × phase) 단위 집계
    COMPENSATION_RULES 레지스트리로부터의 보상 후보 계산
    source_fields에 산출 근거 기록

불허:
    피처 코드 내 exercise_id에 따른 분기 (모든 동작은 YAML에서 구동)
    source_fields가 비어 있는 피처 산출 (ValueError 발생)
    feature_id 접미사에서 운동학적·기구학적 phase 라벨 혼용
    절대 단위 출력 (N, kg, m) — torso_length_ratio / degree만 허용
```

## 3. 3 피처 도메인 (Three Feature Domains)

운동 YAML의 `feature_domains`를 통해 운동별로 활성화되는 3 고정 도메인.
도메인 소속은 `feature_id` 접두어로 인코딩된다(`spatial.*`, `temporal.*`, `control.*`).

### 3-1. 공간(Spatial) 피처

가동성 제한과 근골격계 비대칭을 반영.

```text
spatial.rom.<joint>             반복별 끼인각 max − min                  (degree)
spatial.symmetry.<joint>        | ROM_left − ROM_right | / mean         (dimensionless_cv)
spatial.shape.arc_length.<lm>   주요 관절 궤적 길이                       (torso_length_ratio)
```

#### 시점 의존 대칭성 산출 가능성 (View-Dependent Symmetry Availability)

`spatial.symmetry.*`는 좌우 ROM 차이를 계산할 수 있다는 이유만으로 항상 유효한 동작 품질
감점 근거로 해석하지 않는다. 단안 촬영에서는 양측 대칭성 피처가 먼저 availability gate를
통과해야 한다. 이는 특히 측면에 가까운 스쿼트 촬영에서 중요하다. 단안 3D skeleton을 정면으로
돌려본 화면은 실제 정면 관찰이 아니라 depth 추정 결과를 회전한 것이므로, 좌우 불균형처럼
보이는 패턴이 카메라가 직접 관찰한 움직임이 아닐 수 있다.

의도하는 availability 상태는 다음과 같다.

```text
assessed
    양측 landmark visibility/coverage가 충분하고, 분절 길이가 말이 되며,
    좌우 swap 위험이 낮고, 촬영 view가 해당 좌우 해석을 뒷받침한다.

low_confidence
    값은 계산할 수 있지만 visibility, far-side jitter, depth-dependent
    canonicalization correction, viewpoint mismatch 때문에 해석 note로만 적합하다.

not_assessed
    계산값이 해석 가능한 움직임 비대칭보다 관측 artifact를 주로 반영할 가능성이 크다.
    movement-quality score에 넣지 않는다.
```

측면 또는 측면에 가까운 스쿼트에서는 주 점수화 대상을 하강 깊이, hip/knee/ankle ROM,
체간 기울기, heel lift, hip-center 궤적 안정성, tempo, smoothness 같은 시상면 및 중심선
피처로 둔다. 좌우 symmetry는 양측이 availability gate를 통과할 때만 방출한다. 측면 애니메이션은
안정적으로 보이는데 3D skeleton을 정면으로 돌렸을 때 좌우 균형이 크게 무너져 보인다면, 실제
정면 또는 전방 대각 view가 그 비대칭을 확인하기 전까지 depth inference limitation으로 처리한다.

동일한 원칙은 운동 정의의 `view_metric_reliability`로 일반화한다. Feature extraction은 피처를
계산하되, view reliability를 별도로 보고할 수 있다.

```text
computed_value      source field가 있을 때 산출된 FeatureRecord 수치
view_reliability   high | moderate | low | not_assessed
availability       assessed | low_confidence | not_assessed
```

양측 대칭 운동에서는 reliability map을 주로 관상면 가시성과 시상면 가시성의 tradeoff로 정리한다.
편측 또는 교대 운동에서는 `forward_leg`, `trailing_leg`, `active_side`, `support_side` 같은 역할
기준으로 정리한다. 따라서 측면 런지는 forward-leg 시상면 ROM과 rear-limb extension에는
high-confidence일 수 있지만 knee valgus나 pelvis drop에는 low-confidence일 수 있다. 정면 런지는
step width와 pelvis drop을 잘 보여주지만 무릎 전방 이동과 rear-hip extension은 low-confidence가
될 수 있다.

### 3-2. 시간(Temporal) 피처

통증 회피로 인한 주저함과 타이밍 제어 결손을 포착.

```text
temporal.tempo.rep_<n>          반복 지속 시간                          (second)
temporal.variability.tempo_cv   반복 간 템포 CV                          (dimensionless_cv)
```

### 3-3. 제어(Control) 피처

자세 안정성과 인접 관절에 의한 대체(substitution)를 정량화.

```text
control.stability.hip_center_x_std   골반 측방 동요                     (torso_length_ratio)
control.stability.hip_center_z_std   골반 수직 동요                     (torso_length_ratio)
control.compensation.<candidate>     규칙 레지스트리 기반 보상 지표      (torso_length_ratio | degree)
```

`control` 도메인은 의도적으로 "stability"로 줄이지 않는다
([`terminology.md`](../terminology.md) §3 참조).

## 4. 보상 규칙 레지스트리 (Compensation Rule Registry)

운동 YAML의 `compensation_candidates`는 `features/compensation.py`의
`COMPENSATION_RULES` 레지스트리로 디스패치된다. 등록되지 않은 후보는 `UserWarning`을 발생시키고
건너뛴다(YAML이 미래 후보를 미리 나열해도 파이프라인이 중단되지 않도록 함).

등록된 규칙:

| 후보 | 평면 / 축 | 출력 |
|---|---|---|
| `knee_valgus`            | 관상면(x-z), 측별  | hip-ankle 라인 대비 무릎 내측 편차 피크 |
| `knee_varus`             | 관상면(x-z), 측별  | 무릎 외측 편차 피크 |
| `lateral_pelvic_shift`   | x축               | 반복 평균 대비 골반 중심 측방 변위 피크 |
| `excessive_trunk_flexion`| z축               | 수직 대비 체간 기울기 피크 (degree) |
| `heel_lift`              | z축, 측별          | 반복 최저점 대비 발뒤꿈치 들림 피크 |
| `pelvis_rotation`        | y축 (깊이)        | 좌·우 엉덩이 깊이 비대칭 피크 (transverse 프록시) |

각 규칙은 `feature_id` 패턴 `control.compensation.<candidate>[.<side>]`을 가진
하나 이상의 `FeatureRecord`를 반환한다.

## 5. Phase-Aware 피처 패밀리 (Phase-Aware Feature Families)

⑥ Segmentation이 `phase` 칼럼을 채우면, `PHASE_AWARE_FEATURE_FAMILIES`에 속한
피처는 반복 단위(`phase=None`)와 구간 단위(`phase='Descent'` 등) 모두에서 방출된다.

```text
PHASE_AWARE_FEATURE_FAMILIES = {
    "spatial.rom",
    "spatial.shape",
    "temporal.tempo",
    "control.stability",
}
```

규칙:
```text
- 구간 단위 feature_id에는 소문자 phase 접미사가 붙는다
  예: spatial.rom.left_knee  →  spatial.rom.left_knee.descent

- 구간 단위 FeatureRecord.source_fields에 'segmentation.*' 항목이 포함된다
  (reference_landmark, reference_axis, split_logic)

- control.compensation은 반복 단위 전용 — 후보가 구간 경계를 가로지르므로
  분할하면 의미를 잃는다

- 기구학적(kinematic) phase 라벨 (Descent / Ascent / Turnaround_Hold / Lift / Tap / Return)은
  운동학적(kinetic) 라벨 (eccentric / isometric / concentric)과 혼용해서는 안 된다
```

A2 검증 요구:

```text
phase label이 있는 rep에서 방출되는 모든 phase-level FeatureRecord는 다음을 포함해야 한다:
    phase                         non-null 기구학적 phase label
    feature_id suffix             소문자 phase label
    source_fields                 원래 feature provenance +
                                  phase_segmentation.reference_landmark,
                                  phase_segmentation.reference_axis,
                                  phase_segmentation.split_logic
```

## 6. 계층 요약 (Hierarchical Summary)

`summarize_phase_to_rep()`은 구간 단위 레코드로부터 반복 단위 요약 지표를 도출한다(학위논문 §5.5).

```text
spatial.phase_rom_ratio.descent_ascent
    반복별 평균 Descent ROM 대 평균 Ascent ROM 비율.
    값 > 1 → 하강 가동범위가 상승보다 큼 (예: 통제되지 않은 하강).
```

요약기는 순수 가산적이다: 입력 레코드는 수정되지 않으며, 반환 목록에는 새 요약
`FeatureRecord` 항목만 포함된다.

## 7. 출력: FeatureRecord (Output)

```python
@dataclass
class FeatureRecord:
    feature_id:    str            # 예: 'spatial.rom.left_knee.descent'
    exercise_id:   str
    rep_id:        int | None     # None = 시퀀스 단위
    value:         float
    unit:          str            # 'degree' | 'torso_length_ratio'
                                  # | 'second' | 'dimensionless_cv' | 'dimensionless'
    source_fields: list[str]      # 필수; 비어 있으면 ValueError
    note:          str | None
    phase:         str | None     # None = 반복 단위; 'Descent' 등 = 구간 단위
```

운동별로 산출되는 피처 매핑:

```text
feature_domains.spatial   = [rom, symmetry, shape, ...]   → spatial.* 피처
feature_domains.temporal  = [tempo, variability, ...]     → temporal.* 피처
feature_domains.control   = [stability, compensation, ...] → control.* 피처
compensation_candidates   = [knee_valgus, ...]            → control.compensation.* 피처
```

## 8. 진입점 (Entry Point)

```python
from movement.features import (
    extract_rep_features,
    summarize_phase_to_rep,
    features_to_dataframe,
)

records = extract_rep_features(df, exercise_definition)
records += summarize_phase_to_rep(records)
feat_df = features_to_dataframe(records)
```

`features_to_dataframe()`는 표 교환을 위해 `source_fields`를 파이프(|)로 결합한 문자열로
펼치고 `phase` 칼럼을 보존한다.

## 9. 설정 (Configuration)

활성화는 YAML로만 구동된다; 운동별 Python 코드 분기 없음:

```yaml
feature_domains:
  spatial: [rom, symmetry, shape, depth_proxy, alignment]
  temporal: [tempo, rep_duration, eccentric_duration, isometric_duration, concentric_duration, timing_ratio]
  control: [stability, compensation, com_stability, pelvis_stability, lateral_shift]
  biomechanical_proxy: [com_displacement, moment_arm_proxy, relative_joint_load_proxy]

compensation_candidates:
  - knee_valgus
  - excessive_trunk_flexion
  - lateral_pelvic_shift
```

`biomechanical_proxy` 항목은 ⑧이 아닌 ⑨ Biomech Proxy에서 소비된다.

## 10. 피처 레지스트리 커버리지 감사 (Feature Registry Coverage Audit)

A3에서는 YAML이 향후 확장 후보를 포함하더라도, 모든 항목이 이미 점수화된 것처럼
조용히 오해되지 않도록 명시적인 coverage report를 추가한다.

```python
@dataclass
class FeatureRegistryCoverageReport:
    exercise_id: str
    connected_feature_domain_entries: dict[str, list[str]]
    unsupported_feature_domain_entries: list[dict]
    external_step_feature_domain_entries: list[dict]
    implemented_compensation_candidates: list[str]
    unimplemented_compensation_candidates: list[dict]
    compensation_candidate_availability: list[dict]
```

커버리지 규칙:

```text
feature_domains.spatial / temporal / control
    YAML 항목이 구현된 extractor 또는 문서화된 alias와 연결되면 connected로 보고한다.
    extractor가 없으면 unsupported로 보고한다.

feature_domains.biomechanical_proxy
    ⑧ extractor 누락으로 취급하지 않는다. 이 항목은 ⑨ Biomech Proxy로 라우팅하며
    external_step_feature_domain_entries에 기록한다.

compensation_candidates
    COMPENSATION_RULES에 있는 후보는 implemented로 보고한다. 선언됐지만 등록되지 않은
    후보는 declared_unimplemented 또는 no_rule_registered 사유와 함께 unimplemented로 보고한다.
```

이 report는 진단/provenance 출력이다. Unsupported 항목은 feature extraction을 중단시키지 않고,
자동으로 scoring factor로 승격하지 않는다.

운동별 compensation-candidate availability matrix는 candidate 구현 상태에 대한 현재 기준표이며,
그 자체로 새 metric을 만들지는 않는다.

```text
candidate                    YAML candidate 이름
availability_status          implemented_rule |
                             declared_unimplemented |
                             deferred_feature_design |
                             no_rule_registered
emits_feature                COMPENSATION_RULES dispatch rule이 있으면 true
report_reason                implemented_rule | declared_unimplemented |
                             deferred_feature_design | no_rule_registered
source_fields                provenance fields 예:
                             compensation_candidates.<candidate>
                             feature_domains.control.compensation
next_action                  구현 또는 문서화 다음 행동 요약
```

상태 의미:

```text
implemented_rule
    COMPENSATION_RULES에 rule이 있고, 필요한 landmark가 있으면
    control.compensation.* record를 방출할 수 있다.

declared_unimplemented
    YAML vocabulary로 수용되어 `_UNIMPLEMENTED`에 의도적으로 추적되지만,
    아직 active feature rule은 없다.

deferred_feature_design
    운동 해석상 의미 있는 후보지만 score factor가 되려면 별도 feature 정의,
    visibility policy, role-based side logic, validation fixture가 먼저 필요하다.

no_rule_registered
    YAML에는 선언됐지만 아직 위의 명시적 상태 중 하나로 배정되지 않은 후보.
    report에서 계속 보이게 유지한다.
```

이 matrix는 스쿼트와 파이크 푸쉬업처럼 아직 점수화 규칙으로 승격되지 않은 후보도 report에
보이게 유지하기 위해 사용한다.

## 11. 분석 방해 패턴 탐지 가능성 감사 (Analysis-Disrupting Pattern Detectability Audit)

`performance_protocol.analysis_disrupting_patterns`에 대한 두 번째 diagnostic report를
추가한다. 이 감사는 pose-detectable scoring candidate와 protocol-control 또는
interpretation-limit factor를 분리하여, 분석 방해 패턴이 조용히 자동 제외나 자동 점수로
승격되지 않도록 한다.

```python
@dataclass
class AnalysisDisruptingPatternDetectabilityReport:
    exercise_id: str
    pose_detectable_scoring_candidates: list[dict]
    acquisition_control_factors: list[dict]
    interpretation_limitation_factors: list[dict]
    unknown_patterns: list[dict]
    all_patterns: list[dict]
```

`all_patterns`의 각 항목은 다음을 보고한다.

```text
pattern                       YAML pattern 이름
classification                pose_detectable_scoring_candidate |
                              acquisition_control_factor |
                              interpretation_limitation_factor |
                              unknown
required_landmarks            pose 기반 판독에 필요한 landmarks
view_sensitivity              low | medium | high
visibility_dependency         low | medium | high
annotation_fallback           필요한 annotation 또는 metadata fallback
linked_compensation_candidates 이 pattern이 연결될 수 있는 compensation candidates
linked_feature_domain_entries 이 pattern이 연결될 수 있는 feature-domain entries
source_fields                 classification의 provenance fields
basis                         분류 근거 요약
```

규칙:

```text
pose_detectable_scoring_candidate
    구현된 feature rule과 provenance test가 존재할 때 향후 FeatureRecord/BiomarkerRecord
    출력으로 연결할 수 있다. 감사 자체가 점수화하지는 않는다.

acquisition_control_factor
    recording/protocol warning으로 남긴다. report와 figure caption에는 표시할 수 있지만
    movement-quality score를 직접 바꾸지 않는다.

interpretation_limitation_factor
    pose data만으로 underlying event를 증명하기 어려운 경우 confidence 또는
    interpretation note로 남긴다.

unknown
    명시적으로 분류되기 전까지 warning/provenance로만 남긴다.
```

이 report는 ⑧ 실행 시 `feature_registry_coverage`와 함께 방출될 수 있다. downstream reporting과
⑫ simulation planning에는 사용할 수 있지만, pose coordinate를 수정하지 않고 반복을 제외하지도
않는다.

## 12. 다른 단계와의 관계 (Relationship to Other Steps)

- **⑥ Segmentation** — `phase` 칼럼을 채워 구간 단위 피처 방출을 활성화한다.
  칼럼이 없거나 비어 있으면 반복 단위 레코드만 산출된다(graceful no-op).
- **⑦ Motion Attribution** — 반복별 `attribution_consistent`와 `attribution_action`을 공급.
  비일관 반복의 가중치 하향/제외는 본 단계에서 피처를 변형하지 않고 바이오마커 계층에서 처리한다.
- **⑨ Biomech Proxy** — 동일한 정규화 좌표와 `feature_domains.biomechanical_proxy` /
  `biomechanical_focus` 필드를 소비하지만 `BiomechRecord` (CoM, 모멘트 암)을 산출한다.
  FeatureRecord 출력을 **참조하지 않는다**.
- **⑩ Biomarker Derivation** — FeatureRecord를 BiomarkerRecord 패스스루로 변환하고,
  반복별 종합 점수(composite score)에 공급한다.
- **⑫ In-Silico Simulation** — 향후 pose-detectable analysis-disrupting pattern을 named
  perturbation 후보로 사용할 수 있다. control 또는 interpretation-limit factor는 별도 injector가
  설계되기 전까지 reporting note로 남긴다.

## 13. 코드 매핑 (Code Mapping)

```text
src/movement/features/__init__.py        FeatureRecord, extract_rep_features,
                                         FeatureRegistryCoverageReport,
                                         audit_feature_registry,
                                         AnalysisDisruptingPatternDetectabilityReport,
                                         audit_analysis_disrupting_patterns,
                                         summarize_phase_to_rep,
                                         features_to_dataframe,
                                         PHASE_AWARE_FEATURE_FAMILIES
src/movement/features/spatial.py         compute_rom, compute_symmetry, compute_shape
src/movement/features/temporal.py        compute_tempo, compute_variability
src/movement/features/control.py         compute_stability, compute_compensation
src/movement/features/compensation.py    COMPENSATION_RULES 레지스트리, 디스패치
tests/test_features_phase_grouping.py    phase-level feature 방출과 provenance
tests/test_feature_registry_coverage.py  YAML feature-domain, compensation coverage,
                                         candidate availability
tests/test_analysis_disrupting_patterns.py
                                         analysis-disrupting pattern detectability coverage
tests/test_feature_provenance.py          missing source_fields policy
```

## 14. 임상적 의미 참조 (Clinical Meaning Reference)

운동별 피처 × 임상적 의미 매핑:

```text
docs/clinical/per_exercise_mapping.md   마크다운 표 (§5.5/§5.6)
data/definitions/clinical/feature_meanings.yaml     대시보드 툴팁용 YAML 미러
```

YAML은 `exercise_id → feature_id → {domain, unit, level, phase_suffix, clinical_meaning}` 키 구조다.
계획된 CDSS 대시보드(Task F)에서 호버 툴팁 provenance 공개를 위해 소비된다.

## 15. 향후 확장 (Planned Extensions)

- 가시성 가중 ROM / 대칭성 (max/min 이전 저-가시성 프레임 제거)
- 보상 규칙: `asymmetric_depth`, `foot_external_rotation_proxy`,
  `tempo_instability` (현재 `_UNIMPLEMENTED`)
- 측별 시간 변동성 (좌·우 교대 운동을 위한 좌·우 템포 비대칭)
- 속도 프로파일 피처 (peak velocity, jerk / SPARC을 통한 속도 평활도)
- 구간 단위 변동성 (반복 간 phase 내 템포 CV)
- 관절 협응 피처 (예: hip-knee 위상 결합의 교차 상관(cross-correlation))
- ROM-by-phase 집계를 `summarize_phase_to_rep`에 직접 통합
- 단위 테스트 스캐폴딩: `tests/test_features_phase_grouping.py`, `tests/test_compensation.py`
