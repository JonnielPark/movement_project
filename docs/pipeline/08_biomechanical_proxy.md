# 08. 생체역학 프록시 (Biomechanical Proxy)

**문서 버전:** 1.3.1
**최종 갱신:** 2026-06-29
**영문 동기화:** `docs_eng/pipeline/08_biomechanical_proxy.md`는 동일 버전의 영문 번역본이다.

파이프라인 단계 ⑧은 정규화된 포즈 데이터에서 단순화된 생체역학 프록시 지표를 계산한다:
무게중심(CoM) 궤적 proxy, 2D moment-arm proxy, 세트 내 load-shift tendency.
단일 카메라 환경에서는 절대 힘, 토크, calibrated vertical displacement, 피험자 질량을
추정할 수 없다. 출력은 상대적 부하 분포 경향만 설명한다.

현재 MediaPipe 계열 단안 `z`는 calibrated depth 또는 gravity axis가 아니라 model-depth
evidence이므로, ⑧ 출력은 기본적으로 low-confidence biomechanical proxy evidence로 방출한다.
값은 보고하고 점검할 수 있지만, availability/provenance metadata에 근거한 후속 scoring 정책이
명시적으로 weight를 올리기 전까지 강한 composite-score evidence가 되면 안 된다.

허용 출력 단위는 `torso_length_ratio`, `torso_length_ratio_per_rep`, `degree`,
`dimensionless`이다. `N`, `N·m`, `kg`, `m` 같은 절대 단위는 버그로 간주한다.

---

## 1. 파이프라인 위치 (Pipeline Position)

```text
Pose CSV
→ ① Validation
→ ② Annotation
→ ③ Exercise Definition
→ ④ Preprocessing
→ ⑤ Normalization
→ optional ⑤-1 Canonicalization
→ ⑥ Segmentation
→ ⑦ Feature Extraction
→ ⑧ Biomech Proxy              ← 본 단계
→ ⑨ Biomarker Scoring
```

필수 입력:

```text
정규화 좌표                     ⑤의 <landmark>_norm_x/y/z
가시성 칼럼 (선택)              <landmark>_confidence
반복 경계                       segment_type == rep, rep_id
운동 정의 필드                  landmarks.primary_joints
                                biomechanical_focus.main_load_regions
                                biomechanical_focus.expected_com_motion
                                quality_rules.minimum_confident_landmark_ratio
```

포즈 데이터프레임은 수정하지 않는다. 본 단계는 `BiomechRecord` 행을 생성한다.

## 2. 설계 경계 (Design Boundaries)

허용:

```text
- 인구집단 수준의 분절 질량 및 CoM 비율
- 분절 질량 가중 프록시로서의 전신 CoM
- 투영 평면에서의 2D moment-arm proxy 거리
- 단안 환경 강건성을 위한 confidence 기반 frame 제외
- 관절 간 상대적 부하 분포 경향
```

현재 구현에서 불허:

```text
- 절대 힘 또는 토크
- 피험자 질량, 외부 부하, kg 기반 스케일링
- meter/mm 출력
- model-depth 값을 calibrated gravity/depth evidence로 취급
- 단일 frame 순간 관절힘 주장
- 임상 진단 또는 질환 분류
```

향후 키 범주 또는 인체치수 조사 기반 prior는 코드 구현 전에 무차원 상대 skeleton constraint로
문서화되어야 한다.

## 3. 인체계측 모델 (Anthropometric Model)

`biomech/anthropometry.py`는 Winter 계열 분절 비율을 인코딩한다:

```text
SEGMENT_MASS_RATIO   head, trunk, thigh, shank, foot, upper_arm, forearm, hand
SEGMENT_COM_RATIO    근위 endpoint에서부터의 분절 길이 비율
SEGMENT_ENDPOINTS    각 분절을 정의하는 landmark pair
```

모든 비율은 무차원이다. 현재 trunk proxy는 hip-to-shoulder line을 사용한다.
이는 상대 proxy trend에는 충분하지만 절대 trunk mass location 추정에는 적합하지 않다.

이 Winter 계열 모델은 [05_1_canonicalization.md](05_1_canonicalization.md)에 정의한 Size Korea 기반
`anthropometric_skeleton_prior`와 분리한다. Winter 비율은 ⑧ 안에서 CoM과 segment-mass proxy
계산에 사용한다. Size Korea prior는 ⑤-1 안에서 단안 depth confidence와 analysis evidence를
위한 느슨한 segment-length plausibility envelope다. 두 prior를 하나의
subject-specific skeleton model로 합치지 않는다.

현재 정책:

```text
Winter anthropometry         ⑧의 CoM / segment-mass proxy
Size Korea aggregate prior   ⑤-1의 segment-length plausibility envelope
row-level Size Korea prior   raw data가 있을 때만 future empirical upgrade
foot segment conflict        Size Korea full-body auto source에서는 foot unavailable;
                             Winter foot mass ratio는 CoM proxy에 남을 수 있음
```

## 4. 계산 지표 (Computed Metrics)

CoM metrics:

```text
biomech.com.range_x      좌우 CoM 변위 범위
biomech.com.range_z      normalized z-axis CoM 변위 범위
biomech.com.path_length  전체 CoM 궤적 길이
unit                     torso_length_ratio
```

2D moment-arm proxies:

```text
biomech.moment_arm.knee.<side>.median
biomech.moment_arm.hip.<side>.median
unit = torso_length_ratio
```

값은 현재 정규화 투영에서 CoM에서 부하 부담 관절축 proxy까지의 frame별 수직 거리 중앙값이다.
관절은 `biomechanical_focus.main_load_regions`에서 선택한다. 현재 구현은 hip과 knee proxy를
산출하며, ankle proxy는 아직 구현하지 않았다.

세트 내 load shift:

```text
biomech.load_shift.<joint>.<side>.slope
unit = torso_length_ratio_per_rep
rep_id = None
```

이는 rep-level moment-arm median을 `rep_id`에 대해 회귀한 OLS slope이다.
비유한한(non-finite) moment-arm median은 fitting 전에 제외한다. 서로 다른
`rep_id`를 가진 유효 rep가 최소 3개 필요하며, 그보다 적으면 load-shift record를
만들지 않는다. 이 지표는 상대 추세이며 피로 진단이 아니다.

## 5. confidence 처리 (confidence Handling)

각 frame에서 primary joints의 confidence를 평균한다:

```text
mean_vis(t) < quality_rules.minimum_confident_landmark_ratio → frame 제외
otherwise                                                  → frame 포함
```

Record metadata:

```text
confidence_weight_applied
n_frames_used
n_frames_excluded_low_confidence
```

`extract_rep_biomech(..., use_confidence_weight=False)`는 ⑪ simulation의 ablation 실험을 위해
이 제외를 비활성화한다.

## 6. 출력 계약 (Output Contract)

```python
@dataclass
class BiomechRecord:
    metric_id: str
    exercise_id: str
    rep_id: int | None
    value: float
    unit: str
    source_fields: list[str]
    note: str | None
    confidence_weight_applied: bool
    n_frames_used: int
    n_frames_excluded_low_confidence: int
    availability: str = "low_confidence"
    availability_reasons: list[str] = field(default_factory=list)
    depth_dependency: str = "high"
    model_depth_reliability: str = "low"
    landmark_quality: str = "unknown"
```

검증 규칙:

```text
unit은 torso_length_ratio | torso_length_ratio_per_rep | degree | dimensionless 중 하나
source_fields는 비어 있으면 안 됨
availability는 assessed | low_confidence | not_assessed 중 하나
depth_dependency는 none | low | moderate | high | unknown 중 하나
model_depth_reliability는 high | moderate | low | unknown 중 하나
```

기본 availability 정책:

```text
CoM trajectory proxies       low_confidence; model-depth 및 segment-ratio proxy
moment-arm proxies           low_confidence; model-depth input을 가진 projected 2D proxy
load-shift slopes            low_confidence; low-confidence moment-arm record에서 파생
```

이 정책은 ⑨를 보고와 이후 비교에는 사용할 수 있게 두면서, calibration 없는 monocular-depth proxy
값이 조용히 강한 score로 들어가는 것을 막는다.

저장되는 stage-check 산출물:

```text
data/processed/biomech/<recording_id>_biomech.csv
    BiomechRecord tabular output. 필수 column은 metric_id, exercise_id, rep_id,
    value, unit, source_fields, note, confidence_weight_applied, n_frames_used,
    n_frames_excluded_low_confidence, availability, availability_reasons,
    depth_dependency, model_depth_reliability, landmark_quality다.

data/processed/biomech/<recording_id>_biomech_qc.json
    Follow-along check용 compact count. row count, unit count,
    availability count, metric-family count, missing source_fields 등을 담는다.
```

CSV round-trip은 row count와 필수 column을 보존해야 한다. `source_fields`,
`availability_reasons` 같은 구조화 field는 CSV 호환성을 위해 직렬화할 수 있다.

## 7. 진입점 (Entry Point)

```python
from movement.biomech import extract_rep_biomech

biomech_records = extract_rep_biomech(
    df,
    exercise_definition,
    use_confidence_weight=True,
)
```

동작:

```text
- rep annotation이 있으면 rep별 record 계산
- annotation이 없으면 sequence-level record로 fallback
- quality_rules에서 confidence threshold 참조
- 3개 이상의 유효 rep에서 moment-arm metric이 있으면 load-shift record 추가
```

## 8. Provenance

모든 record는 계산을 제어한 exercise-definition field를 참조한다:

```text
biomech.com.*           biomechanical_focus.expected_com_motion
                        biomechanical_focus.stability_requirement
biomech.moment_arm.*    biomechanical_focus.main_load_regions
                        biomechanical_focus.expected_com_motion
biomech.load_shift.*    biomech.moment_arm.* records에서 파생
```

⑨ Biomarker Scoring은 biomarker record로 변환할 때 이 field를 보존한다.
Composite scoring은 후속 scoring 정책이 명시적으로 달리 정하지 않는 한
`availability != assessed`를 withheld 또는 minimal-weight evidence로 다뤄야 한다.

## 9. 코드 매핑 (Code Mapping)

```text
src/movement/biomech/__init__.py         BiomechRecord, extract_rep_biomech
src/movement/biomech/anthropometry.py    segment ratios and endpoints
src/movement/biomech/com.py              estimate_com, compute_com_metrics,
                                         compute_confidence_weights
src/movement/biomech/moment_arm.py       compute_moment_arms
src/movement/biomech/load_shift.py       compute_load_shift

tests/test_biomech_load_shift.py
```

