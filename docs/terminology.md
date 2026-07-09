# 용어집 (Terminology)

**문서 버전:** 1.8.4
**최종 갱신:** 2026-07-09
**영문 동기화:** `docs_eng/terminology.md`는 동일 버전의 영문 번역본이다.

본 문서는 일반 용어 사전이 아니다. 통상적인 의미로 충분히 이해되는 단계명, 좌표 shape,
단위 표기, 운동 목록은 각 파이프라인 문서와 코드 docstring에서 다룬다.
여기에는 **본 연구에서 의미를 좁혀 쓰거나, 일반적 의미와 혼동되면 안 되는 용어**만 남긴다.

---

## 1. 연구 범위와 출력 의미 (Scope and Output Meaning)

| 용어 | 본 연구에서의 고정 의미 |
|---|---|
| 동작 품질 (Movement quality) | 과제 성공 여부가 아니라 관절 정렬, 좌·우 대칭성, CoM 안정성, 보상 움직임처럼 생체역학적으로 해석 가능한 움직임 특성을 뜻한다. |
| 디지털 바이오마커 (Digital biomarker) | 점수화와 검토에 필요한 운영 메타데이터를 명시적으로 가진 무차원 또는 상대 정규화 동작 품질 지표. 진단 라벨이나 임상 효능 지표가 아니다. |
| 생체역학 프록시 (Biomechanical proxy) | 단안 포즈 데이터로부터 계산 가능한 생체역학적 대리 지표. 실제 힘, 질량, 절대 토크를 직접 추정하지 않는다. |
| 상대 부하 분포 경향 (Relative load distribution tendency) | 관절·분절 간 부하가 어느 쪽으로 더 치우치는지 나타내는 상대적 경향. `N`, `N·m`, `kg` 같은 절대 단위를 산출하지 않는다. |
| 모멘트 암 프록시 (Moment-arm proxy) | 관절 중심과 기준 작용선 사이의 정규화 거리. 절대 토크 계산이 아니라 상대 부하 분포를 해석하기 위한 단순화 지표로 사용한다. |
| 근육별 활성도 / 타겟 근육 동원 (Muscle-specific activation / target-muscle recruitment) | 특정 근육의 전기적 활성, 힘 기여도, 또는 선택적 동원을 뜻한다. 본 연구는 이를 단안 pose에서 직접 추정하지 않는다. 산출물은 관절·분절 수준의 경향, 활성 측, 보상 움직임을 설명할 수 있지만 특정 근육 활성의 직접 증거로 해석하지 않는다. |
| 합성 정상 베이스라인 (Synthetic-normal baseline) | 정상 조건의 합성 파이프라인 실행에서 얻은 지표별 기준 통계. 임상적 정상/비정상 라벨이 아니라 Z-score 계산용 참조 분포다. |
| 동작 품질 점수 (Movement quality score) | 합성 정상 베이스라인 대비 Z-score 감점 방식으로 계산하는 반복(rep) 단위 종합 점수(0–100). 임상 진단 점수가 아니며, 관측 데이터 신뢰도와 분리해 해석한다. |
| 데이터 신뢰도 (Data confidence) | landmark confidence, 좌우 swap 위험, 보정 요약 confidence, quality gravity처럼 입력 관측과 좌표 표준화의 신뢰성을 나타내는 별도 요약. 움직임 품질 점수 자체가 아니며, 점수를 깎는 직접 penalty로 쓰지 않는다. |
| 품질 그래비티 (`quality_gravity`) (Quality gravity) | 좌표 계열, feature, 또는 비교가 downstream에서 얼마나 신뢰를 가지고 반영될 수 있는지를 요약하는 표준 품질 가중치. Confidence, availability gate, correction cap, residual 진단값, burden 진단값, sensitivity check에서 유도할 수 있지만 raw residual과 burden 값은 명시적 검토가 필요한 경우가 아니면 stage report 또는 audit export에 둔다. Downstream scoring은 raw residual/burden field를 다시 해석하지 않고 `quality_gravity`를 소비해야 한다. |
| 랜드마크 신뢰도 (Landmark confidence) | landmark 관측 품질을 나타내는 표준 필드. 해당 landmark 관측값을 후속 계산에 믿고 사용할 수 있는지를 답한다. MediaPipe `visibility`나 YOLO keypoint confidence 같은 backend별 필드는 ① Validation/schema harmonization에서 `<landmark>_confidence`로 매핑해야 한다. 그 이후 pipeline payload, config, report, notebook은 confidence 용어만 사용한다. |
| 원본 포즈 데이터 (Raw pose data) | 영상 또는 pose estimator에서 처음 저장된 frame-level pose table. 최소 `<landmark>_x/y`, backend가 제공한 경우 선택 `<landmark>_z`, 그리고 ① schema harmonization 이후 표준 `<landmark>_confidence`를 가진다. Backend별 `visibility`는 raw import alias로만 허용하며 downstream pipeline payload에는 남기지 않는다. 누락된 z는 `NaN` placeholder로 나타날 수 있지만, 이는 여전히 depth evidence가 없다는 뜻이다. |
| 전처리 포즈 데이터 (Preprocessed pose data) | ④ Preprocessing 이후의 pose table. raw coordinate column은 보존하고 `<landmark>_observed_reliable`, `<landmark>_usable`, `preprocessing_valid` 같은 운영 품질/상태 column을 추가할 수 있다. 세부 처리 이력은 downstream payload가 아니라 preprocessing report에 둔다. "preprocessing 된 raw data" 대신 이 용어를 사용한다. |
| 정규화 포즈 데이터 (Normalized pose data) | ⑤ Normalization 이후의 pose table. 전처리 포즈 데이터에 `<landmark>_norm_x/y/z` 신체 기준 정규화 좌표 계열과 `normalized_evidence_axes`, `z_axis_policy`, `z_evaluable` 같은 depth-evidence metadata를 추가한 상태다. Backend에 z가 없던 경우 `norm_z`는 선택 canonicalization이 analysis z evidence를 만들기 전까지 `NaN` placeholder로 남는다. |
| 보정 포즈 데이터 (Canonicalized pose data) | ⑤-1 선택 canonicalization 이후의 output. 정규화 포즈 데이터에 `canon` 또는 `corrected_3d_hypothesis` 같은 analysis-space 좌표 계열과 confidence, availability, `quality_gravity` 같은 payload 요약을 추가한다. Raw residual과 burden 세부값은 canonicalization report 또는 audit export에 둔다. 이후 scoring policy가 명시적으로 승격하기 전까지 기본 downstream/scoring 입력은 아니다. |
| 좌표 축 계약 (Coordinate-axis contract) | 좌표 shape와 좌표 evidence를 명시적으로 구분하는 계약. 작업 table은 `axes=[x,y,z]`로 harmonize될 수 있지만, `observed_axes`, `z_source`, `z_fill_policy`, `z_evaluable`로 z가 backend model-depth evidence인지, canonical hypothesis인지, 단순 `NaN` placeholder인지 밝혀야 한다. 없는 z축을 0으로 채워 3D처럼 가장하지 않는다. |
| 2D 포즈 데이터 (2D pose data) | YOLO pose처럼 recording-view x/y와 confidence만 제공하고 model depth z를 제공하지 않는 pose backend output. `NaN` z placeholder를 추가해 xyz schema로 harmonize할 수 있지만, depth-sensitive feature와 score 기여는 별도 analysis evidence 없이는 제한한다. |

모든 생체역학 출력은 상대 지표다. 절대 힘·질량·토크 단위가 출력에 등장하면 문서 또는 코드
오류로 간주한다.

---

## 2. Phase와 Segmentation (Phase and Segmentation)

| 용어 | 본 연구에서의 고정 의미 |
|---|---|
| 구간 (Phase) | 한 반복(rep) 내부의 하위 구간. 본 연구에서는 두 체계를 분리한다: `phase_model.expected_ratio`의 운동학적(kinetic) 라벨과, ⑥ Segmentation이 `phase` 칼럼에 쓰는 기구학적(kinematic) 라벨. |
| 기구학적 구간 (Kinematic phase) | 기준 랜드마크의 움직임 방향으로 정의되는 phase. 예: `Descent`, `Ascent`, `Turnaround_Hold`, `Lift`, `Tap`, `Return`. `eccentric`, `concentric` 같은 kinetic 라벨과 혼용하지 않는다. |
| 반복 분할 (Rep segmentation) | `rep_segmentation` 설정을 사용해 반복 시작·종료 경계를 반자동으로 확정하고 `rep_id`를 만드는 절차. |
| 구간 분할 (Phase segmentation) | 기존 `phase_segmentation` 코드 식별자와 YAML 키를 유지하며, 확정된 반복 내부에서 기구학적 phase 경계를 나누는 절차. |
| 분할 실패 지점 (Segmentation failure point) | rep 또는 phase 경계를 신뢰 가능하게 결정하지 못한 프레임/구간. 실패 지점은 숨기지 않고 기록하며, 수동 개입 전에는 해당 범위의 관련 지표를 산출하지 않는다. |
| 방향전환 정지 구간 (Turnaround_Hold) | 변곡 프레임 주변의 선택적 기구학적 phase 라벨. 기준 랜드마크가 한 방향으로 움직이다가 잠시 정지한 뒤 반대 방향으로 전환되는 구간을 뜻한다. `phase_segmentation.turnaround_hold` 설정으로 관리한다. |

---

## 3. 분석 단위와 검증 용어 (Analysis Unit and Evaluation Terms)

| 용어 | 본 연구에서의 고정 의미 |
|---|---|
| 운동 정의 (Exercise definition) | 운동 이름 자체가 아니라 운동 정체성 YAML 객체를 뜻한다. 목표 스키마에서는 이 동작이 무엇인지, 즉 classification, support, 주요 신체 영역, phase model, joint actions, 생체역학적 정체성을 기술한다. 마이그레이션 중에는 loader 호환성을 위해 기존 통합 YAML에 analysis와 protocol 필드가 남아 있을 수 있다. |
| 운동 작성 스펙 (Exercise authoring spec) | notebook 또는 향후 UI에서 연구자의 선택값으로 만드는 작은 초안 객체. exercise definition, analysis profile, performance protocol, camera protocol YAML 산출물을 생성하는 입력이며, 파이프라인이 직접 소비하는 실행 기준 파일은 아니다. |
| 분석 프로필 (Analysis profile) | 운동 정체성에서 분리된 운동별 분석 설정. segmentation 설정, landmark set, angle definition, 활성 feature domain, quality-rule override, compensation-pattern 초안 등을 포함한다. |
| 운동 런타임 컨텍스트 (`ExerciseContext`) | 하나의 `exercise_id`에 대해 exercise definition과 관련 analysis, performance, camera YAML 산출물을 조합한 런타임 객체. 과도하게 큰 단일 exercise-definition YAML 객체를 파이프라인 전체에 전달하는 현재 구조의 목표 대체 형태다. |
| 움직임 템플릿 ID (Movement template ID) | joint action과 context 조합에서 도출되는 exercise definition의 분석 템플릿 classification key. 예: `bilateral_lower_body_closed_chain`. 프레임 단위 annotation의 좌우/순서 pattern이 아니며, 운동 표시명만으로 결정하면 안 된다. |
| 움직임 패턴 (Movement pattern) | 마이그레이션 동안 `movement_template_id`를 가리키는 deprecated compatibility name. 새 문서와 코드는 exercise-definition 분석 템플릿을 말할 때 `movement_template_id`를 사용한다. |
| 실행 패턴 (Execution pattern) | recording 안에서 관찰·표기된 수행의 좌우/순서 방식을 나타내는 frame 또는 segment 수준 값. 예: `bilateral`, `alternating`. `movement_template_id`와 구분되며 운동의 생체역학적 정체성으로 사용하지 않는다. |
| 수행 실패 지점 (Performance failure point) | 피험자가 통증 없이 움직일 수 있더라도 해당 운동의 기본 자세, ROM, 리듬, 지지 기저면, 좌우 순서를 더 이상 일관되게 유지하지 못하기 시작하는 최초 반복/프레임 또는 recording 종료 지점. 근력이나 피로의 임상 진단 기준이 아니라 실제 반복 수와 중단 사유를 남기기 위한 취득/annotation 표지이며, 분할 실패 지점과 구분한다. |
| 보상 움직임 (Compensatory movement) | 주 작업을 대체하거나 왜곡하는 비주요 움직임. 본 연구에서는 YAML의 `compensation_patterns`와 코드의 보상 규칙 레지스트리에 등록된 패턴만 바이오마커로 산출한다. |
| 검증 (Validation) | 입력 포즈 데이터의 구조적·형식적 무결성 점검. 강건성 평가와 구분한다. 2D pose backend에 대해 `NaN` z placeholder를 추가하는 schema harmonization을 포함할 수 있지만, 측정 evidence를 발명하거나 backend 제공 좌표를 덮어쓰면 안 된다. |
| 강건성 평가 (Robustness evaluation) | 노이즈, 가려짐, ROM 제한, 속도 스파이크 등을 주입한 합성 조건에서 지표 반응성과 일관성을 확인하는 평가. 입력 무결성 검증과 다르다. |
| 랜드마크 신뢰도 가중 (Landmark-confidence weighting) | 생체역학 프록시 계산에서 주요 랜드마크 confidence를 프레임 가중치로 사용하는 방식. Low-confidence frame은 지표 계산 영향이 줄거나 제외된다. |
| 시점-지표 신뢰도 (View-metric reliability) | 특정 camera zone이 특정 metric family를 얼마나 잘 뒷받침하는지 나타내는 운동 정의 수준의 prior. 좌표 보정이나 landmark 품질과 분리되며, `high`, `moderate`, `low`, `not_assessed` 같은 값으로 보고와 scoring eligibility를 안내한다. |
| 피처 컨텍스트 해석 (Feature-context resolution) | ⑦ Feature Extraction 앞단의 준비 단계. 운동 정의, segmentation, side-role evidence, bilateral-symmetry context, 관측 신뢰도를 `role_context`, availability reason, `source_fields`로 변환한다. 좌표를 수정하거나 rep/phase를 다시 라벨링하거나 score를 만들지 않는다. |
| 피처 산출 가능성 (Feature availability) | landmark coverage, geometry plausibility, swap risk, view-metric reliability를 확인한 뒤, 계산 가능한 값이 scoring에 들어갈 수 있는지 결정하는 피처별 판정. 숫자값을 계산할 수 있다는 사실과 구분한다. |
| 관절 범위 (Range of motion) | 관절 각도 범위 근거를 나타내는 spatial feature family. `spatial.range_of_motion.xy.<joint_angle>`와 `spatial.range_of_motion.xyz.<joint_angle>`처럼 명시적 `xy`/`xyz` variant로 방출한다. 이전 내부 `rom` family 이름을 대체한다. |
| 움직임 경로 (Movement path) | landmark path length 근거를 나타내는 spatial feature family. `spatial.movement_path.arc_length_xy.<landmark>` 또는 `spatial.movement_path.arc_length_xyz.<landmark>`로 방출하고, 단일축 `axis_path_*` diagnostic은 명시적으로 승격하기 전까지 report-only로 둔다. 이전 내부 `trajectory` 또는 `shape` family 이름을 대체한다. |
| 지지 일관성 (Support consistency) | support-point drift, support-width variation, support-center drift처럼 recording-view에서 고정 지지 조건이 얼마나 일관되게 보이는지 나타내는 spatial feature family. CoP/CoM류 생체역학적 안정성 proxy가 아니며, 부하 중심 또는 질량 중심 해석은 ⑧ Biomechanical Proxy에서 다룬다. |
| 역할 정렬 (Role alignment) | 좌/우, 전/후, 지지/이동, active/passive side처럼 운동 정의에서 기대되는 역할 간 비교를 나타내는 spatial feature family. Bilateral squat에서는 현재 좌우 range-of-motion 또는 support-consistency 비교를 방출하지만, 용어 자체는 bilateral symmetry에만 한정되지 않는다. |
| 구간 프로파일 (Phase profile) | Kinematic phase 사이에서 feature 값의 양상이 어떻게 달라지는지 rep 단위로 요약하는 domain-local summary layer. 예: `spatial.phase_profile.range_of_motion_ratio.descent_ascent`. 같은 패턴은 향후 `temporal.phase_profile.*`, `control.phase_profile.*`, `biomech.phase_profile.*` 아래에도 존재할 수 있으며, 별도 segmentation 단계가 아니다. |
| 분석 근거 (Analysis evidence) | Availability, confidence, `quality_gravity`, sensitivity 같은 운영 메타데이터를 담는 계산 좌표 계열, feature, 또는 비교. Scoring 전에 생성되며 final-score contribution을 그 자체로 정의하지 않는다. Raw residual/burden 값은 명시적 review export로 승격하지 않는 한 stage-local 진단값이다. |
| 단계 리포트 / 감사 메타데이터 (Stage report / audit metadata) | 디버깅, 재현성, 검토를 위해 각 파이프라인 단계가 별도로 내보내는 sidecar report. 적용 rule, source/config reference, warning, 알고리즘 선택을 기록한다. 직접 downstream payload가 아니며 scoring 필수 입력으로 요구하지 않는다. |
| 감사 참조 (`source_fields`) (Audit references) | record가 어떤 YAML field, 알고리즘, source column의 영향을 받았는지 설명하기 위한 선택적 trace reference. 필수 record payload가 아니며, scoring은 availability, evidence axes, depth dependency, focus tier, feature family 같은 명시적 운영 필드를 사용해야 한다. |
| 카메라 근측/원측 (Near-side / far-side) | 카메라 기준 observation-confidence context. `Near-side`는 카메라에 더 가까운 landmark 또는 body side, `far-side`는 카메라에서 더 먼 쪽을 뜻한다. 해부학적 품질 라벨이 아니라 confidence 해석에 사용한다. |
| 원측 jitter (Far-side jitter) | 카메라에서 먼 쪽 landmark의 불안정성. confidence drop, velocity/acceleration spike, segment-length inconsistency, swap risk로 요약한다. 보상 움직임 지표가 아니라 data-confidence signal이다. |

---

## 4. 좌표 보정 용어 (Coordinate-Correction Terms)

| 용어 | 본 연구에서의 고정 의미 |
|---|---|
| 분석 좌표 표준화 (Analysis-space canonicalization) | Normalization 아래의 선택 ⑤-1 하위 단계. ⑤의 `norm` 좌표를 입력으로 받아 일관된 단안 관찰 편향을 줄이기 위한 analysis-space 좌표 계열을 추가할 수 있다. 좋은 동작으로 맞추는 template fitting이나 절대 3D 복원이 아니다. |
| 표준 분석 좌표계 (Canonical analysis space) | 골반 중심, 몸통 길이, 운동별 주 운동 평면, 지지면 prior 등을 이용해 정의하는 분석용 좌표계. 해부학적 절대 좌표나 calibrated world coordinate가 아니라, 관절의 상대 궤적과 시간적 변화량을 비교하기 위한 좌표 표현이다. |
| Canonical depth hypothesis | 2D 또는 저신뢰 단안 depth 입력에서 ⑤-1 Canonicalization이 생성할 수 있는 분석용 analysis z evidence. x/y projection, 분절 길이 plausibility, 지지 조건, 시간적 연속성 같은 prior로 제한되며, measured depth, calibrated 3D, 또는 ground truth가 아니다. Confidence와 `quality_gravity` 요약을 가진 analysis evidence로만 취급하며, raw burden/residual 진단값은 ⑤-1 report에 둔다. |
| Pseudo-floor reference | 실제 바닥의 물리적 위치가 아니라, 단안 pose 좌표계 안에서 운동정의 기반 지지 랜드마크로 추정한 apparent floor 기준. 카메라 캘리브레이션이나 절대 3D 복원이 아니다. |
| 바닥 기준 보정 (Floor-relative correction) | 정적 support-consistency 맥락에서 pseudo-floor reference의 기울기 성분을 이용해 apparent floor artifact를 완화하는 support-plane prior. 현재는 analysis-space canonicalization의 `support_plane_alignment` 하위 필터로 다룬다. raw/norm 좌표는 보존하고 analysis-space 좌표를 추가할 수 있으며, raw residual은 review export가 필요하지 않은 한 report-local 진단값으로 둔다. |
| 지지 랜드마크 (Support landmark) | 스쿼트의 발, 플랭크의 손/발처럼 운동 정의상 바닥 또는 지지면 접촉에 참여한다고 기대되는 랜드마크. 실제 보상 움직임을 지울 위험이 있으므로, 항상 고정 anchor로 쓰지 않고 confidence와 안정성 조건을 통과한 경우에만 pseudo-floor 추정에 사용한다. |
| 프로토콜 높이 기반 좌우폭 정렬 (Protocol-height lateral-width alignment) | 관찰된 카메라 높이가 운동별 촬영 프로토콜과 맞는지 먼저 확인한 뒤, 해당 height level에 맞는 신체 anchor를 사용해 depth-dependent lateral-width bias를 완화하는 analysis-evidence canonicalization prior. H1은 지지/발목 높이 anchor, H2는 골반/hip-center anchor, H3는 어깨선 anchor를 사용한다. 렌즈 캘리브레이션, perspective reprojection, template fitting이 아니다. |
| 인체계측 스켈레톤 prior (Anthropometric skeleton prior) | 단안 depth 동작을 검토하기 위한 느슨한 신체 분절 길이 plausibility envelope. Stage A에서는 Size Korea aggregate ratio를 engineering envelope로만 사용할 수 있으며, empirical percentile prior, calibrated 3D reconstruction, subject-specific skeleton fitting이 아니다. |
| 보수적 engineering range (Conservative engineering range) | aggregate anthropometric ratio 주변에 연구자가 넓게 정의한 tolerance. impossible skeleton behavior와 data-confidence 문제를 잡기 위한 것이며 population P5/P95 추정이 아니다. |
| 개인별 empirical 인체계측 prior (Row-level empirical anthropometric prior) | 비식별 개인별 anthropometric row가 있어야 가능한 향후 upgrade. 같은 개인 안에서 segment/stature ratio를 계산한 뒤 P1/P99 또는 P5/P95를 요약한다. |
| Depth residual correction | x/y evidence, segment-length plausibility, confidence, correction cap이 모두 허용할 때만 시도할 수 있는 bounded analysis-evidence depth-axis bounded 보정. raw 또는 base normalized coordinate를 덮어쓰지 않는다. Raw residual/burden 진단값은 ⑤-1 report 또는 audit export 안에 두며, 해당 evidence가 승격될 때 downstream payload는 `quality_gravity`를 사용한다. |
| 관절 plausibility (Articulation plausibility) | 불가능한 joint-angle 또는 reverse-bending configuration을 다루는 별도 guard. data confidence를 낮추거나 feature를 unavailable로 표시하며, movement-quality를 직접 감점하지 않는다. |

---

## 5. 임상 표현 사용 원칙 (Clinical Language Use)

본 연구는 임상적 해석을 배제하지 않는다. 다만 실제 임상시험, 환자군 대상 검증, 진단 성능
평가를 수행한 연구가 아니므로, 표현은 **임상적 해석 가능성**과 **의료진 판단 보조**의
범위 안에서 사용한다.

| 표현 유형 | 사용 원칙 |
|---|---|
| 임상적 해석 / 임상적 의미 | 허용한다. 단, 지표가 특정 질환을 진단하거나 치료 효과를 입증한다는 의미로 확장하지 않는다. |
| 임상적으로 유의하다 | 실제 임상 데이터와 통계적/임상적 유의성 검정이 있을 때만 사용한다. 본 연구 단계에서는 "임상적 해석 가능성이 있다", "의료진 판단을 보조할 수 있다"로 표현한다. |
| 질병을 진단/예측한다 | 사용하지 않는다. "추후 임상 연구에서 평가할 수 있는 탐색 지표", "의료진의 평가를 보조하는 정량 정보"로 표현한다. |
| 민감도/특이도/진단 정확도 | 임상 라벨과 진단 성능 평가 설계가 있을 때만 사용한다. 본 연구에서는 강건성, 반응성, 일관성으로 표현한다. |
| 정상/비정상 | 임상 기준이 없는 경우 이분법으로 쓰지 않는다. "참조 동작", "합성 변형", "기준 대비 편차"로 표현한다. |
| 환자 데이터 | 실제 환자군 자료를 사용할 때만 쓴다. 현재 입력은 합성 데이터와 정상 동작 데이터이므로 "대상자", "참여자", "샘플"을 기본 표현으로 둔다. |
| 절대 토크/부하 | 사용하지 않는다. 단안 포즈 기반 출력은 절대 단위가 아니라 "관절 간 상대적 부하 분포 경향"이다. |
| 자동 탐지 | 단독으로 쓰지 않는다. rep/phase 분할은 실패 지점 기록과 수동 개입을 포함하는 반자동 절차이므로 "반자동 분할", "수동 검토 후 확정"으로 표현한다. |

권장 문장 예시:

```text
본 지표는 특정 질환의 진단 목적이 아니라, 의료진이 동작 품질을 생체역학적으로 해석할 때
참고할 수 있는 정량 정보로 설계되었다.

관찰된 보상 움직임은 특정 병리의 직접 증거가 아니라, 추가 임상 평가에서 확인할 수 있는
움직임 전략 analysis evidence로 해석한다.

본 파이프라인의 생체역학 지표는 단안 포즈 데이터 기반 상대 지표이며, 절대 근력·관절 토크
또는 임상 예후를 직접 의미하지 않는다.

이 결과는 의료진의 운동 평가를 대체하지 않고, 반복별 움직임 패턴과 보상 전략을 구조화하여
임상적 추론을 보조하는 정보를 제공한다.

임상적 의미는 자문위원 검토와 후속 임상 데이터 연구를 통해 추가 검증될 필요가 있다.
```
