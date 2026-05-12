# 09. 생체역학 프록시 (Biomechanical Proxy)

**문서 버전:** 1.0.1
**최종 갱신:** 2026-05-06  
**영문 동기화:** `docs_eng/pipeline/09_biomechanical_proxy.md`는 동일 버전의 영문 번역본이다.

파이프라인 단계 ⑨. 정규화된 포즈 데이터로부터 단순화된 생체역학 프록시 지표
— 무게 중심(CoM) 궤적과 모멘트 암(moment arm) — 을 계산한다.

단일 모바일 카메라 환경은 절대 깊이를 해상할 수 없고 관절 힘을 뉴턴 단위로 추정할 수 없다.
**절대** 토크나 부하를 측정하는 대신, 본 단계는 반복이 진행됨에 따라 *어느* 관절이 더 많은
일을 부담하는지를 설명하는 **상대적** 부하 분포 경향(load-distribution tendency)을 정량화한다.
학위논문 §6에 해당.

모든 출력은 `torso_length_ratio` (무차원) 또는 `degree`이다. 절대 단위(`N`, `N·m`, `kg`, `m`)는
금지된다 — 등장하면 버그로 간주한다.

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
→ ⑧ Feature Extraction
→ ⑨ Biomech Proxy              ← 본 단계
→ ⑩ Biomarker Derivation
```

필수 입력:
```text
정규화 좌표                     ⑤에서 온 <landmark>_norm_x/y/z 칼럼
가시성 칼럼 (선택)              신뢰도 가중을 위한 <landmark>_visibility
반복 경계                       ②에서 온 segment_type == 'rep' + rep_id
운동 정의 필드                  landmarks.primary_joints,
                                biomechanical_focus.main_load_regions,
                                biomechanical_focus.expected_com_motion,
                                quality_rules.minimum_visible_landmark_ratio
```

포즈 데이터프레임을 수정하지 않으며 `BiomechRecord` 행을 생성한다.

## 2. 설계 원칙 (Design Principle)

```text
허용:
    통계적 인체 계측 분절 질량 (Winter 1990)
    분절 질량 가중 평균으로서의 전신 CoM
    2D 투영 모멘트 암 프록시 (시상면 / 관상면)
    단안 노이즈 강건성을 위한 가시성 가중 프레임 제외
    관절 간 상대적 부하 분포 경향

불허:
    절대 힘 / 토크 출력 (N, N·m)
    피험자별 인체 계측 (모든 값은 무차원 비율)
    환자 특이적 질량 / 길이 값
    프레임별 순간 힘 (출력은 반복별 집계)
```

## 3. 인체 계측 모델링 (Anthropometric Modeling)

`biomech/anthropometry.py`는 Winter (1990) Table 4.1 분절 비율을 인코딩한다.
모든 비율은 무차원이다: 전신 질량 = 1.0, 분절 길이 = 1.0.

```text
SEGMENT_MASS_RATIO   head 0.081  trunk 0.497  thigh 0.100  shank 0.0465  foot 0.0145
                     upper_arm 0.028  forearm 0.016  hand 0.006
SEGMENT_COM_RATIO    분절의 근위(proximal) 끝에서부터의 분절 길이 비율
                     (예: 허벅지 CoM은 엉덩이 끝에서 43.3 % 지점)
SEGMENT_ENDPOINTS    각 분절을 정의하는 랜드마크 짝 (proximal, distal)
```

체간(trunk)은 `(left_hip → left_shoulder)` 라인으로 근사된다; 이는 프록시 비율로는 충분하지만
절대 체간 질량 위치 추정에는 부적합한 중심선 프록시이다.

## 4. CoM 추정 (Center of Mass Estimation)

`biomech/com.py — estimate_com()`은 프레임별 CoM 위치 `(T, 3)`를 반환한다:

```text
seg_com(t)        = p_proximal(t) + com_ratio · ( p_distal(t) - p_proximal(t) )
whole_body_CoM(t) = Σ_seg ( mass_ratio · seg_com(t) ) / Σ_seg mass_ratio
```

반복별 요약 지표 (`compute_com_metrics`):

```text
biomech.com.range_x      CoM 측방 변위 범위                  (torso_length_ratio)
biomech.com.range_z      CoM 수직 변위 범위                  (torso_length_ratio)
biomech.com.path_length  CoM 궤적 총 호 길이                  (torso_length_ratio)
```

해석: 시상면 운동(예: 스쿼트) 중 큰 `range_x`는 내·외측 불안정 또는 체중 이동 보상을 시사;
`range_z` 대비 큰 `path_length`는 비효율적 CoM 궤적을 시사한다.

## 5. 2D 모멘트 암 프록시 (2D Moment Arm Proxy)

`biomech/moment_arm.py — compute_moment_arms()`는 2D 평면으로 투영하고 CoM에서
각 부하 부담 관절 축까지의 수직 거리를 취한다.

```text
평면           축 라인                              metric_id
─────────      ─────────────                        ───────────────────────────
xz (시상면)    ankle ↔ knee  (knee 축)              biomech.moment_arm.knee.<side>.median
xz (시상면)    knee  ↔ hip   (hip 축)               biomech.moment_arm.hip.<side>.median
```

프레임별 거리의 **중앙값(median)** 이 보고된다 (단안 이상값에 평균보다 강건).
평가 대상 관절은 `biomechanical_focus.main_load_regions`에서 참조한다:

```text
main_load_regions: [hip, knee, ankle]
    → hip + knee 모멘트 암 산출 (ankle 프록시는 미구현)
```

## 6. 가시성 가중 신뢰도 (Visibility-Weighted Confidence)

단안 포즈 엔진은 가끔 순간적인 깊이 추정 붕괴를 일으킨다. `compute_visibility_weights()`는
이를 평활화하지 않고 프록시 계산에서 제외하여 단조성(monotonicity)을 보존한다:

```text
mean_vis(t) = mean( <primary_joint>_visibility(t) for primary_joints )

if mean_vis(t) < quality_rules.minimum_visible_landmark_ratio:
    weight(t) = 0       (프레임 제외)
else:
    weight(t) = mean_vis(t)
```

출력 레코드에 미치는 영향:
```text
visibility_weight_applied        True / False
n_frames_used                    임계값 통과 후 포함된 프레임 수
n_frames_excluded_low_visibility 제외된 프레임 수
```

`extract_rep_biomech()`에 `use_visibility_weight=False`를 전달하면 A/B 비교가 가능하다;
⑫ 시뮬레이션의 ablation 실험에 유용하다.

## 7. 세트 내 부하 전이 경향 (Within-Set Load-Shift Tendency)

`biomech/load_shift.py — compute_load_shift()`는 세트 내 반복별 모멘트 암 중앙값을
`rep_id`에 대해 회귀하여, 사용자가 피로해짐에 따라 부하가 어떻게 재분배되는지 노출한다.
최소 **3 반복**이 필요하며, 그 외에는 빈 목록을 반환한다.

```text
slope = np.polyfit( rep_ids,  moment_arm_medians,  1 )[0]

metric_id:  biomech.load_shift.<joint>.<side>.slope
unit:       torso_length_ratio_per_rep
rep_id:     None  (세트 단위 — 반복별 아님)
```

해석:
```text
negative slope_knee  ∧ positive slope_hip  → knee → hip 부하 이동
                                             (피로 관련 hip 우위 보상 시그니처)
```

`extract_rep_biomech()`는 `len(rep_ids) ≥ 3`일 때 자동으로 `compute_load_shift()`를 호출한다.
결과는 반환되는 `BiomechRecord` 목록에 추가되어 `biomech.*` 도메인을 통해 ⑩ 바이오마커 점수화로 흐른다.

## 8. 출력: BiomechRecord (Output)

```python
@dataclass
class BiomechRecord:
    metric_id:                            str   # 예: 'biomech.com.range_z'
    exercise_id:                          str
    rep_id:                               int | None
    value:                                float
    unit:                                 str   # torso_length_ratio | torso_length_ratio_per_rep
                                              # | degree | dimensionless
    source_fields:                        list[str]   # 필수 (비면 ValueError)
    note:                                 str | None
    visibility_weight_applied:            bool
    n_frames_used:                        int
    n_frames_excluded_low_visibility:     int
```

단위 검증은 생성 시점에 강제된다: 그 외 단위는 `ValueError`를 발생시킨다. 이는 우발적인
절대 단위 누출이 ⑩ 바이오마커 도출로 전파되는 것을 방지한다.

## 9. 진입점 (Entry Point)

```python
from movement.biomech import extract_rep_biomech

biomech_records = extract_rep_biomech(
    df,
    exercise_definition,
    use_visibility_weight=True,    # 기본값
)
```

동작:
```text
- 어노테이션 칼럼이 있을 때 rep_id를 순회
- 어노테이션이 없으면 시퀀스 단위 계산으로 폴백
- quality_rules에서 minimum_visible_landmark_ratio 참조
- (rep_id × metric)당 1개 레코드 반환
```

## 10. Provenance

모든 BiomechRecord는 그 계산을 유발한 YAML 필드를 참조한다:

```text
biomech.com.*           biomechanical_focus.expected_com_motion,
                        biomechanical_focus.stability_requirement
biomech.moment_arm.*    biomechanical_focus.main_load_regions,
                        biomechanical_focus.expected_com_motion
```

⑩ 바이오마커 도출은 이를 수정 없이 BiomarkerRecord로 통과시켜, 시각화 계층까지 전체
provenance 사슬을 보존한다.

## 11. 코드 매핑 (Code Mapping)

```text
src/movement/biomech/__init__.py         BiomechRecord, extract_rep_biomech,
                                         compute_load_shift
src/movement/biomech/anthropometry.py    Winter (1990) 비율, 분절 끝점
src/movement/biomech/com.py              estimate_com, compute_com_metrics,
                                         compute_visibility_weights
src/movement/biomech/moment_arm.py       compute_moment_arms, _point_to_line_dist_2d
src/movement/biomech/load_shift.py       compute_load_shift; (joint × side)별 OLS slope;
                                         §7 세트 내 추세
tests/test_biomech_load_shift.py         17건: slope 부호, 최소 반복 가드,
                                         메타데이터 포맷, 다관절
```

## 12. 향후 확장 (Planned Extensions)

- 발목(ankle) 모멘트 암 프록시 (foot ↔ ankle 라인, 시상면)
- 단측 / 비대칭 운동(예: 런지)을 위한 관상면 모멘트 암
- 구간 단위 CoM 지표 (Descent vs. Ascent 경로 길이 비대칭)
- 분절별 피험자 적합 분절 길이 추정 (상수 trunk 프록시 대체)
- `pike_pushup`, `plank_shoulder_tap`에 대한 역방향 자세 처리
  (인체 계측 표는 신체 방향 불변이지만, 역방향 닫힌 사슬 자세에서 랜드마크 매핑은
  검증이 필요)
- 가려짐 / 노이즈 환경에서 CoM 안정성의 강건성 검증 (Task C)
```
