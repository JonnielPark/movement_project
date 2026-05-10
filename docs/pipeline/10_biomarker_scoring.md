# 10. 바이오마커 점수화 (Biomarker Scoring)

**문서 버전:** 1.0.2
**최종 갱신:** 2026-05-10
**영문 동기화:** `docs_eng/pipeline/10_biomarker_scoring.md`는 동일 버전의 영문 번역본이다.

파이프라인 단계 ⑩. ⑧ 피처 추출과 ⑨ 생체역학 프록시의 출력을 해석 가능한 디지털
바이오마커와 반복별 종합 동작 품질 점수(composite movement quality score)로 통합한다.

두 종류의 레코드가 산출된다:
1. **`BiomarkerRecord`** — `source_fields` provenance를 갖춘 패스스루 개별 지표.
   표 형식 보고에 적합.
2. **`BiomarkerScoreRecord`** — 도메인별 서브 스코어, 동적 하한(dynamic floor),
   피처별 감점 감사(audit)를 포함한 반복별 종합 점수(기본 0–100).

학위논문 §7에 해당. 점수는 합성 정상 베이스라인(synthetic-normal baseline)에 고정되며,
임상 임계값이 **아니므로** 진단 결과로 보고되어서는 안 된다.

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
→ ⑧ Feature Extraction          (FeatureRecord 목록)
→ ⑨ Biomech Proxy               (BiomechRecord  목록)
→ ⑩ Biomarker Derivation         ← 본 단계
```

필수 입력:
```text
feat_records          list[FeatureRecord]   ⑧에서
biomech_records       list[BiomechRecord]   ⑨에서
exercise_definition   feature_domains, biomechanical_focus, quality_rules 포함
definition_version    운동 YAML 버전 문자열 (provenance)
baseline JSON         data/reference/baseline_zscore.json
                      scripts/compute_baseline.py로 생성
```

## 2. 설계 원칙 (Design Principle)

```text
허용:
    합성 정상 베이스라인 대비 Z-score 감점으로부터의 도메인별 서브 스코어
    문서화된 도메인 가중치를 가진 종합 점수
    의무 ROM 달성에 비례하는 동적 하한
    z, weight, deduction을 포함한 피처별 감점 감사 목록
    FeatureRecord / BiomechRecord로부터의 provenance 패스스루

불허:
    "정상" vs "비정상"의 임상 임계값
    환자 분류 라벨
    하드코딩된 mean / std (반드시 베이스라인 파일에서)
    질병 예측 출력
    도메인별 투명성 없는 단일 숫자 요약
```

## 3. 2단계 출력 (Two-Stage Output)

### 3-1. BiomarkerRecord (패스스루)

각 FeatureRecord와 BiomechRecord가 동일한 value, unit, provenance를 가진 BiomarkerRecord 1개로 변환된다.
YAML 버전(`definition_version`)으로 감싸는 것 외에 어떠한 변환도 없다.

```python
@dataclass
class BiomarkerRecord:
    biomarker_id:       str
    exercise_id:        str
    definition_version: str
    source_fields:      list[str]   # 필수; 비면 ValueError
    rep_id:             int | None
    value:              float
    unit:               str         # torso_length_ratio | degree
                                    # | dimensionless_cv | second
    note:               str | None
```

### 3-2. BiomarkerScoreRecord (종합)

합성 정상 베이스라인 대비 계산된 반복별 동작 품질 요약. `rep_id`당 1개 레코드;
반복이 어노테이트되지 않은 경우 시퀀스 단위로 폴백한다.

```python
@dataclass
class BiomarkerScoreRecord:
    score_id:           str               # 항상 'rep_quality_score'
    exercise_id:        str
    definition_version: str
    rep_id:             int | None
    domain_scores:      dict[str, float]  # 도메인별 설정 점수 척도
    floor_applied:      dict[str, bool]
    deductions:         list[dict]        # 피처별 감사
    final_score:        float             # 가중 종합
    source_fields:      list[str]
    domain_weights:     dict[str, float]  # final_score에 사용된 정규화 가중치
    score_bounds:       dict[str, float]  # 기본값 {'min': 0.0, 'max': 100.0}
```

## 4. 도메인 가중치와 점수 범위 (Domain Weights and Score Bounds)

현재 검증 정책은 score domain 사이에 **동일 상대 가중치**를 사용한다. 가중치는 상대 단위로
입력하고 런타임에서 합이 1이 되도록 정규화한다:

```text
spatial   1.0 → 25 %     폼 완성도 (ROM, 대칭, 형태)
temporal  1.0 → 25 %     속도 조절과 일관성
control   1.0 → 25 %     안정성과 보상
biomech   1.0 → 25 %     상대적 부하 분포 경향
```

종합 공식:

```text
final_score = Σ_d  W_d · domain_score_d
```

기본 상대 단위는 `configs/pipeline_default.yaml`에 둔다:

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

현재 연구 단계에서는 임상적 우선순위 가정을 임의로 추가하지 않기 위해 동일 가중을 사용한다.
향후 민감도 분석에서는 운동별 또는 보고 목적별로 값을 조정할 수 있다. 특정 domain을 `0.0`으로
두면 최종 종합 점수에서는 제외되지만, 해당 domain score와 감점 감사는 계속 보고할 수 있다.

점수 척도 역시 `score_bounds`로 파라미터화한다. 기본값 `min: 0.0`, `max: 100.0`은 현재의
0–100 보고 규칙을 그대로 유지한다. 향후 다른 표시 척도나 검증 척도가 필요해지면, 점수화
방법을 바꾸는 것이 아니라 같은 Z-score 감점 로직을 설정된 범위에 선형 스케일링한다.

도메인 할당은 `feature_id` / `metric_id` 접두어로 결정된다:

```text
spatial.*    → spatial      temporal.*   → temporal
control.*    → control      biomech.*    → biomech
기타          → 무시
```

## 5. Z-Score 감점 공식 (Z-Score Deduction Formula)

도메인 `d`의 각 피처 `i`에 대해:

```text
σ_eff_i  = max( σ_baseline_i,  STD_FLOOR_RATIO · |μ_baseline_i|,  STD_ABS_FLOOR )
           STD_FLOOR_RATIO = 0.10
           STD_ABS_FLOOR   = 0.01

Z_i      = ( value_i − μ_i ) / σ_eff_i
score_span = score_max − score_min
w_i        = 1 / n_features_in_domain          (도메인 내 균등 가중)
deduct_i   = (score_span / 100) · w_i · | Z_i |

raw_score_d   = max( score_min, score_max − Σ_i deduct_i )
domain_d      = max( floor_dynamic, raw_score_d )
```

σ 하한은 합성 정상 베이스라인에서 사실상 0인 피처(예: 깔끔한 스쿼트의 측방 골반 이동)에서
거의 0인 σ가 Z-score를 폭발시키는 것을 방지한다. 1 % 몸통 길이 편차는
`Z → ∞` 대신 `Z ≈ 1`을 산출한다.

## 6. 동적 하한 — 의무 ROM 기준 (Dynamic Floor)

```text
mandatory_ROM_ratio = mean(  min( ROM_i / ROM_baseline_i,  1.0 )  )
                      반복 내 주요 관절 ROM 피처에 대해

floor_dynamic = score_min + 0.50 · score_span · clamp( mandatory_ROM_ratio,  0.0,  1.0 )
```

근거: 요구되는 ROM을 달성한 반복은 단지 보상 움직임 때문에 하한까지 처벌받아서는 안 된다.
하한은 많은 control 감점이 적용되더라도 동작을 완수한 것에 대한 절반 점수를 보존한다.

기본 0–100 척도:

```text
ROM 달성률         하한       최대 감점
────────────       ─────      ─────────────────
 100 %              50 pts    50 pts
  80 %              40 pts    60 pts
  50 %              25 pts    75 pts
   0 %               0 pts   100 pts
```

`floor_applied[domain] = True`는 해당 반복에서 하한에 도달한 모든 도메인을 기록하여,
가동성과 제어 사이의 반복 간 결합(coupling)을 표면화한다.

## 7. 합성 정상 베이스라인 (Synthetic-Normal Baseline)

```text
파일         data/reference/baseline_zscore.json
생성기       scripts/compute_baseline.py  (합성 정상 데이터에 파이프라인을 실행하고
                                          μ, σ를 집계)

스키마       { exercise_id: {
                 feature_id: { "mean": float, "std": float },
                 ...
               }, ... }
```

`load_baseline()`이 로드한다; 파일이 없으면 `BiomarkerScoreRecord` 계산은 예외를 발생시키는 대신
**`UserWarning`과 함께 건너뛰어**, ⑧ + ⑨ 패스스루 레코드는 여전히 반환된다.

베이스라인은 합성 공학 참조이며 인구 규준(population norm)이 아니다.
이 베이스라인 대비 Z-score를 환자 분류로 보고하지 **말 것**.

## 8. 감점 감사 (Deduction Audit)

모든 BiomarkerScoreRecord는 피처별 감사 목록을 포함한다:

```python
deductions = [
    {
        "domain":         "spatial",
        "feature_id":     "spatial.rom.left_knee",
        "value":          85.4,
        "baseline_mean":  92.1,
        "baseline_std":   3.5,
        "z":              -1.91,
        "w":              0.143,
        "deduction":      0.273,
    },
    ...
]
```

이 목록은 ⑪ 시각화의 `plot_attribution_heatmap()`에서 직접 소비되어, "이 반복이 왜 점수를 잃었는가"를
개별 피처 수준에서 표면화한다.

## 9. 진입점 (Entry Point)

```python
from movement.biomarker import derive_biomarkers

biomarker_records, score_records = derive_biomarkers(
    feat_records,
    biomech_records,
    exercise_definition,
    definition_version=exercise_definition.version,
    baseline_path=None,    # 기본값: data/reference/baseline_zscore.json
    domain_weights=None,   # 기본값: 동일 상대 가중
    score_bounds=None,     # 기본값: {'min': 0.0, 'max': 100.0}
)
```

동작:
```text
- 항상 biomarker_records를 반환 (⑧/⑨ 패스스루)
- 베이스라인 파일이 없으면 빈 score_records 목록 반환
- 입력 레코드의 distinct rep_id를 순회
- rep_id가 어디에도 설정되어 있지 않으면 단일 시퀀스 단위 점수로 폴백
```

## 10. 기존 임상 평가 척도와의 연계 (Linkage to Existing Clinical Scales)

종합 점수는 확립된 기능적 동작 평가(예: FMS 형식의 0–3 감점, OAB 형식의 이진 체크리스트)
구조를 **반영(mirror)** 하도록 설계되었으나, 그것들과 직접 비교 가능한 것은 아니다.
연계는 감사 목록 수준에서 명시적이다:

```text
spatial 감점     → "form" 하위 기준         (FMS 채점 루브릭)
temporal 감점    → "control" 하위 기준      (FMS / SFMA 내)
control 감점     → 보상 감점                (FMS 동작 스크린)
biomech 감점     → 부하 분포 경향           (FMS에 직접 등가물 없음)
```

⑪ 시각화는 감사 목록을 임상의가 읽기 쉬운 레이아웃으로 표면화하는 책임을 진다;
본 단계는 데이터만 제공한다.

## 11. Provenance

```text
BiomarkerRecord.source_fields         FeatureRecord / BiomechRecord에서 상속
BiomarkerScoreRecord.source_fields    ['feature_domains', 'biomechanical_focus',
                                        'quality_rules']
```

`derive_biomarkers()`는 생성 시점에 provenance를 강제한다:
원천 FeatureRecord / BiomechRecord의 `source_fields`가 비어 있던 레코드는 BiomarkerRecord
목록에서 조용히 제거된다 (기저 레코드가 이미 `ValueError`를 발생시켰을 것이다).

## 12. 코드 매핑 (Code Mapping)

```text
src/movement/biomarker/__init__.py     BiomarkerRecord, from_feature_record,
                                       from_biomech_record, derive_biomarkers,
                                       derive_interpretations
src/movement/biomarker/scoring.py      BiomarkerScoreRecord, DOMAIN_WEIGHTS,
                                       normalize_domain_weights,
                                       normalize_score_bounds,
                                       load_baseline, save_baseline,
                                       build_baseline_from_records,
                                       derive_biomarkers
src/movement/biomarker/interpretation.py  load_rules, derive_interpretations,
                                          InterpretationRecord; YAML 기반 규칙 엔진;
                                          예외 발생하지 않음
data/definitions/interpretation_rules/squat.yaml   6개 규칙 (floor_hit, dominant_domain,
data/definitions/interpretation_rules/lunge.yaml      load_shift, score 임계값)
data/definitions/interpretation_rules/pike_pushup.yaml
data/definitions/interpretation_rules/plank_shoulder_tap.yaml
scripts/compute_baseline.py            data/reference/baseline_zscore.json 생성
data/reference/baseline_zscore.json    feature_id별 합성 정상 μ, σ
configs/pipeline_default.yaml          biomarker.domain_weights 기본 상대 단위,
                                       biomarker.score_bounds 기본 0–100 척도
tests/test_biomarker_scoring_weights.py  score-domain 가중치 정규화,
                                        score-bound 정규화와 final score
tests/test_interpretation.py           20건: 규칙 로더, 3개 시나리오, 엣지 케이스
```

## 13. 향후 확장 (Planned Extensions)

- 구간별 점수화 (`Descent` 전용, `Ascent` 전용 서브 스코어), phase-aware FeatureRecord
  패밀리로 구동
- 인구 단위 베이스라인 교체 (실제 코호트 데이터), 합성 베이스라인을 폴백으로 보존
- 피처별 z 분산으로부터 `final_score`별 신뢰 구간
- 민감도 분석 이후 운동별 domain-weight profile 정의; 현재 구현은 parameterized weights를
  지원하지만 기본값은 동일 가중으로 둔다.
- 세트 단위 추세 `BiomarkerTrendRecord` (세트 내 반복 간 집계 slope, 피로 시그니처)
- YAML 버전이 베이스라인 도중에 변경될 때의 하위 호환 마이그레이션
