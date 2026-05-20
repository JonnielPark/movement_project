# 10. 바이오마커 점수화 (Biomarker Scoring)

**문서 버전:** 1.2.0
**최종 갱신:** 2026-05-21
**영문 동기화:** `docs_eng/pipeline/10_biomarker_scoring.md`는 동일 버전의 영문 번역본이다.

파이프라인 단계 ⑩은 ⑧ `FeatureRecord`와 ⑨ `BiomechRecord`를 해석 가능한 biomarker record로
감싸고, baseline이 있을 때 반복별 movement-quality score를 산출한다. 관측 신뢰도, feature
availability, coordinate-correction magnitude는 별도 confidence/provenance signal로 유지한다.

점수는 공학적 요약이며 clinical threshold 또는 diagnostic output이 아니다.

---

## 1. 파이프라인 위치 (Pipeline Position)

```text
⑧ Feature Extraction   FeatureRecord list
⑨ Biomech Proxy        BiomechRecord list
→ ⑩ Biomarker Scoring  ← 본 단계
```

필수 입력:

```text
feat_records           availability metadata를 포함한 FeatureRecord list
biomech_records        BiomechRecord list
exercise_definition    feature_domains, biomechanical_focus, quality rules
definition_version     exercise YAML version
baseline JSON          scoring을 켤 때 data/reference/baseline_zscore.json
```

---

## 2. 출력 계약 (Output Contract)

두 record type을 방출한다.

```text
BiomarkerRecord
    value, unit, rep_id, source_fields, availability, view/depth reliability,
    note metadata를 가진 개별 metric pass-through record.

BiomarkerScoreRecord
    domain score, final score, floor flag, deduction audit, withheld-feature audit,
    score bounds, domain weights를 가진 반복별 composite score.
```

`BiomarkerRecord.source_fields`는 필수다. Provenance 없는 record는 산출하지 않는다.

---

## 3. 점수화 계약 (Scoring Contract)

Composite scoring은 synthetic-normal baseline 대비 Z-score deduction을 사용한다. 기본 score bounds는
0-100이고, 기본 domain weight는 동일한 상대 가중치다.

```text
spatial   form completeness와 symmetry/shape feature
temporal  pacing과 timing consistency
control   stability와 compensation feature
biomech   relative load-distribution proxy feature
```

기본 설정은 `configs/pipeline_default.yaml`에 둔다.

```yaml
biomarker:
  score_bounds:
    min: 0.0
    max: 100.0
  domain_weights:
    spatial: 1.0
    temporal: 1.0
    control: 1.0
    biomech: 1.0
```

Domain은 record ID prefix로 배정한다.

```text
spatial.*   → spatial
temporal.*  → temporal
control.*   → control
biomech.*   → biomech
other       → pass-through only
```

---

## 4. Feature Eligibility

⑧은 scoring에 충분히 신뢰할 수 없는 numeric feature도 방출할 수 있다. ⑩은 `availability`를
composite-score gate로 사용한다.

```text
assessed
    baseline statistics가 있으면 Z-score deduction 대상.

low_confidence
    기본적으로 composite score에서 제외한다. BiomarkerRecord에는 보존하고
    BiomarkerScoreRecord.withheld_features에 기록한다.

not_assessed
    composite score에서 제외한다. provenance/unavailable로만 보고한다.

availability 누락
    하위 호환: legacy record에 한해 assessed로 취급한다.
```

`view_reliability`는 별도 score multiplier가 아니다. 이는 이미 `availability`에 반영되어야 하며,
camera artifact에서 나온 가짜 정밀도를 피하기 위함이다.

큰 canonicalization correction magnitude도 movement-quality score를 직접 낮추지 않는다. 검증된
별도 점수 정책이 생기기 전까지는 data-confidence/provenance에 둔다.

---

## 5. Z-Score Deduction And Dynamic Floor

각 assessed feature에 대해:

```text
σ_eff  = max(σ_baseline, STD_FLOOR_RATIO * |μ_baseline|, STD_ABS_FLOOR)
Z      = (value - μ_baseline) / σ_eff
w_i    = 1 / domain 안의 assessed feature 수
deduct = scaled_abs_z_deduction(Z, w_i, score_bounds)
```

σ floor는 baseline variance가 0에 가까울 때 deduction이 불안정해지는 것을 막는다.

Dynamic floor는 mandatory ROM achievement에 묶는다.

```text
mandatory_ROM_ratio = mean(min(ROM_i / ROM_baseline_i, 1.0))
floor_dynamic       = score_min + 0.50 * score_span * clamp(mandatory_ROM_ratio)
domain_score        = max(floor_dynamic, raw_domain_score)
```

이 규칙은 동작을 수행한 반복이 여러 compensation/control deduction 때문에 최저점으로 바로
떨어지는 것을 막는다. `floor_applied`는 floor가 domain에 영향을 준 경우를 기록한다.

---

## 6. Baseline

```text
File       data/reference/baseline_zscore.json
Generator  scripts/compute_baseline.py
Schema     { exercise_id: { metric_id: {"mean": float, "std": float} } }
```

Baseline은 synthetic engineering reference이며 population norm이 아니다. Baseline data가 없으면
warning과 함께 composite score record만 건너뛰고, pass-through biomarker record는 반환한다.

---

## 7. Audit Fields

`deductions`는 scoring에 사용된 feature가 domain score에 어떤 영향을 줬는지 설명한다.

```python
{
    "domain": "spatial",
    "feature_id": "spatial.rom.left_knee",
    "value": 85.4,
    "baseline_mean": 92.1,
    "baseline_std": 3.5,
    "z": -1.91,
    "weight": 0.143,
    "deduction": 0.273,
}
```

`withheld_features`는 계산됐지만 score에는 들어가지 않은 metric의 이유를 설명한다.

```python
{
    "feature_id": "spatial.symmetry.knee",
    "value": 0.31,
    "availability": "low_confidence",
    "view_reliability": "low",
    "camera_zone": "Z3",
    "depth_dependency": "high",
    "model_depth_reliability": "low",
    "reasons": ["view_metric_low"],
}
```

Reporting과 visualization은 두 목록을 모두 보여줘야 한다. 하나는 "왜 감점됐는가"를, 다른
하나는 "왜 계산된 metric이 점수에 들어가지 않았는가"를 설명한다.

---

## 8. 진입점 (Entry Point)

```python
from movement.biomarker import derive_biomarkers

biomarker_records, score_records = derive_biomarkers(
    feat_records,
    biomech_records,
    exercise_definition,
    definition_version=exercise_definition.version,
    baseline_path=None,
    domain_weights=None,
    score_bounds=None,
)
```

동작:

```text
항상 pass-through BiomarkerRecord를 반환한다.
baseline file이 없으면 score_records는 빈 목록이다.
rep_id별로 독립 산출하고, 필요하면 sequence-level score로 fallback한다.
```

---

## 9. Provenance And Clinical Boundary

```text
BiomarkerRecord.source_fields       FeatureRecord/BiomechRecord에서 상속
BiomarkerScoreRecord.source_fields  feature_domains, biomechanical_focus,
                                    quality_rules, baseline file, score config
```

Composite score는 functional movement assessment 구조를 참고할 수 있지만 FMS/OAB 점수와 직접
비교할 수 없다. Clinical diagnosis, patient classification, clinical significance claim으로
표현하지 않는다.

---

## 10. 코드 매핑 (Code Mapping)

```text
src/movement/biomarker/__init__.py        BiomarkerRecord, derive_biomarkers
src/movement/biomarker/scoring.py         BiomarkerScoreRecord, baseline IO,
                                          scoring, score bounds, weights
src/movement/biomarker/interpretation.py  YAML rule loader and InterpretationRecord
data/definitions/interpretation_rules/    per-exercise interpretation rules
scripts/compute_baseline.py               baseline generator
tests/test_biomarker_scoring_weights.py   weights and bounds
tests/test_biomarker_scoring_availability.py assessed-only scoring and withheld audit
tests/test_interpretation.py              rule engine behavior
```

---

## 11. 향후 확장 (Planned Extensions)

- Phase-aware feature 근거가 안정화된 뒤 phase-specific sub-score 추가.
- Sensitivity analysis 이후 exercise-specific domain-weight profile 추가.
- Synthetic fallback을 보존하면서 real cohort baseline 지원.
- Set-level trend record로 within-set fatigue 또는 consistency 분석.
