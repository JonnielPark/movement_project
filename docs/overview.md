# 개요 (Overview)

**문서 버전:** 1.4.38
**최종 갱신:** 2026-06-27
**영문 동기화:** [docs_eng/overview.md](../docs_eng/overview.md)는 동일 내용의 영문 번역본이다.

본 문서는 분석 파이프라인(pipeline)의 전체 설계를 기술한다.
용어 정의는 [`docs/terminology.md`](terminology.md)를 참조한다.

---

## 문서 인덱스 (Document Index)

| 버전 | 파일 | 내용 |
|---|---|---|
| 1.6.2 | [terminology.md](terminology.md) | 연구 특화 용어와 임상 표현 원칙 |
| 1.4.38 | [overview.md](overview.md) | 전체 파이프라인 개요 |
| 1.4.0 | [practical_protocols/camera_protocol.md](practical_protocols/camera_protocol.md) | 대상 운동별 촬영 프로토콜 |
| 1.1.0 | [practical_protocols/exercise_performance_protocol.md](practical_protocols/exercise_performance_protocol.md) | 대상 운동별 수행 프로토콜 |
| 0.2.22 | [practical_protocols/exercise_authoring_notebook.md](practical_protocols/exercise_authoring_notebook.md) | notebook 우선 운동 작성과 YAML 생성 계획 |
| 1.1.0 | [clinical/exercises/README.md](clinical/exercises/README.md) | 운동별 상세 해석 문서 |
| 1.1.0 | [00_data_format.md](pipeline/00_data_format.md) | 입력 CSV 데이터 포맷 |
| 1.1.0 | [01_validation.md](pipeline/01_validation.md) | ① Validation |
| 1.2.0 | [02_annotation.md](pipeline/02_annotation.md) | ② Annotation |
| 1.6.1 | [03_exercise_definition.md](pipeline/03_exercise_definition.md) | ③ Exercise Definition YAML |
| 1.2.0 | [04_preprocessing.md](pipeline/04_preprocessing.md) | ④ Preprocessing |
| 2.0.0 | [05_normalization.md](pipeline/05_normalization.md) | ⑤ Normalization |
| 2.0.0 | [06_canonicalization.md](pipeline/06_canonicalization.md) | ⑥ Canonicalization |
| 1.3.0 | [07_segmentation.md](pipeline/07_segmentation.md) | ⑦ Segmentation |
| 1.2.4 | [08_feature_extraction.md](pipeline/08_feature_extraction.md) | ⑧ Feature Extraction |
| 1.2.0 | [09_biomechanical_proxy.md](pipeline/09_biomechanical_proxy.md) | ⑨ Biomech Proxy |
| 1.2.0 | [10_biomarker_scoring.md](pipeline/10_biomarker_scoring.md) | ⑩ Biomarker Scoring |
| 1.1.0 | [11_visualization.md](pipeline/11_visualization.md) | ⑪ Visualization |
| 1.1.0 | [12_insilico_simulation.md](pipeline/12_insilico_simulation.md) | ⑫ In-silico Simulation |

---

## 분석 범위와 해석 원리 (Analytical Scope and Interpretation Principle)

본 연구는 단안 3D pose 시계열을 입력으로 받아 관절 중심과 신체 분절의 움직임을 시간축에서
추적한다. 입력 데이터는 pose CSV, 선택적 annotation, recording metadata, 운동 정의 YAML로
구성되며, 이 정보는 동일한 `ExerciseDefinition` 객체와 단계별 report를 통해 파이프라인
전반에서 공유된다.

분석 원리는 절대 힘이나 절대 토크를 복원하는 것이 아니라, 개인 신체 척도로 정규화된 관절
각도, 분절 궤적, 좌우 대칭성, CoM 안정성, moment-arm proxy, 상대 부하 전이, 보상 움직임
후보를 반복(rep) 및 구간(phase) 단위로 산출하는 것이다. 이를 통해 단안 카메라 환경에서도
관찰 가능한 움직임을 생체역학적으로 해석 가능한 feature와 digital biomarker로 변환한다.

따라서 결과물은 반복별/구간별 feature table, biomechanical proxy table, biomarker score,
해석 규칙 기반 narrative label, provenance가 포함된 report와 figure로 구성된다. 이 결과는
의료진 또는 연구자가 동작 품질, 좌우 수행 일관성, 상대 부하 분포, 보상 전략을 검토할 수
있도록 구조화된 정량 정보를 제공한다.

근육 동원과 관련된 해석은 이 원리 안에서 관절·분절 수준으로 제한한다. 관절 각도, 지지
자세, 외부 부하, 수행 속도, 개인 해부학적 차이에 따라 근육의 moment arm과 동원 전략은
달라질 수 있으므로, 본 연구의 활성 측, 상대 부하 전이, moment-arm proxy, 보상 움직임은
특정 근육 활성의 직접 증거가 아니라 관찰 가능한 움직임에서 유도한 해석 가능한 경향성으로
다룬다.

현재 파이프라인의 우선 적용 범위는 비기구 기반의 제자리 반복 운동이다. 스쿼트, 런지,
파이크 푸쉬업, 플랭크 숄더탭은 외부 기구나 넓은 공간 이동 추적 없이도 단안 3D pose에서
반복 단위 관절·분절 움직임을 비교하기에 적합하다. 반대로 덤벨, 밴드, 바벨 같은 기구 사용
운동은 기구 위치, 외부 부하 metadata, 손-기구 접촉 상태, 저항 방향을 추가로 기록해야 한다.
점프, 달리기, 방향전환처럼 고동적이거나 공간 이동이 큰 운동은 지면 접촉 이벤트, 공중 phase,
전역 이동 경로, tracking continuity, 더 복잡한 event segmentation 및 camera protocol 확장이
필요하다. 따라서 현재 결과는 이 범위 안에서의 공학적 타당성과 강건성 검증으로 해석한다.

---

## 1. 핵심 설계: YAML 객체로서의 운동 정의 (Exercise Definitions as YAML Objects)

각 운동은 `exercise_id`로 조립되는 `ExerciseContext`에서 로드한다. 현재 대상 운동은 split
YAML 산출물을 사용한다. Exercise definition은 운동 정체성만 유지하고, analysis,
performance, camera 설정은 별도 파일에 둔다. loader는 하위 호환을 위해 legacy combined
exercise YAML도 계속 지원하며, 후속 파이프라인 단계에는 기존과 같은 `ExerciseDefinition`
객체를 반환한다. [exercise_authoring_notebook.md](practical_protocols/exercise_authoring_notebook.md)를
참조한다.

split YAML 산출물에 정의되는 필드:

```text
data/definitions/exercises/<exercise_id>.yaml
classification        laterality, primary_plane, movement_chain, posture_type
phases                구간 모델 (예: eccentric / concentric)

data/definitions/analysis_profiles/<exercise_id>.yaml
landmarks             primary_joints, critical_landmarks, bilateral_pairs
rep_segmentation      반복 경계 검출 설정
phase_segmentation    반복 내부 phase 검출 설정
compensation_candidates  모니터링할 움직임 패턴
feature_domains       활성화할 공간/시간/제어 피처
biomechanical_focus   계산할 프록시(proxy) 지표
quality_rules         가시성 임계값, 최대 보간 갭 등

data/protocols/performance/<exercise_id>.yaml
performance_protocol  피험자 안내 기준 카운트와 좌우 수행 순서 규칙

data/protocols/camera/<exercise_id>.yaml
camera_protocol       권장 촬영 zone/height와 경고 정책
view_metric_reliability  zone별 metric-family reliability prior
```

운동별 YAML이 없을 경우 일반 폴백(generic fallback) 정의(`generic.yaml`)가 로드된다.

---

## 2. 파이프라인 단계 (Pipeline Steps)

```text
입력
    Pose CSV           단안 3D 포즈 시계열
    Annotation 파일    (선택) 구간 및 반복 라벨
    Recording metadata (선택) session_id, set_index, camera zone/height
    Exercise YAML      운동 정의

단계
    ①  Validation           구조적 무결성 검사 — 데이터 미수정
    ②  Annotation           어노테이션 파일에서 구간/반복 메타데이터 병합
    ③  Exercise Definition  ExerciseDefinition 객체 로드(미존재 시 generic 폴백)
    ④  Preprocessing        신뢰도 검출, 좌·우 스왑(swap) 보정, 보간(interpolation), 평활화(smoothing)
    ⑤  Normalization        골반 중심 평행이동 + 몸통 길이 중앙값 척도화
    ⑥  Canonicalization     선택 analysis-space 후보 좌표(raw/norm 보존)
    ⑦  Segmentation         관절 움직임 추적 기반 rep/phase 반자동 분할
    ⑧  Feature Extraction   side-role context resolution + 공간/시간/제어 피처 + audit reports
    ⑨  Biomech Proxy        CoM, 모멘트 암(moment arms), 인체 계측(Winter 1990)
    ⑩  Biomarker Derivation BiomarkerRecord(개별 지표) + BiomarkerScoreRecord(반복 단위 종합)
    ⑪  Visualization        ①–⑩ 러너(runner) 외부에서 호출; 진단 및 결과 차트
    ⑫  Simulation           강건성 시뮬레이션, 러너 외부에서 호출

출력
    단계별 데이터프레임(DataFrame) (칼럼 누적)
    단계별 리포트(report) 딕셔너리
    rep_id             — 반자동 또는 수동 확정 반복 ID
    phase 칼럼          — 'Descent' | 'Ascent' | 'Turnaround_Hold' | 'Lift' | 'Tap' | 'Return' | NA
    Feature 테이블      — FeatureRecord 목록, 반복 단위(phase=None) + 구간 단위(phase=str)
    Feature audit reports — feature-registry coverage + compensation availability + analysis-disrupting pattern detectability
    Phase summary       — summarize_phase_to_rep() 계층 집계 (예: Descent/Ascent ROM 비율)
    생체역학 프록시 테이블 — BiomechRecord 목록, 반복 단위, 가시성(visibility) 가중
    바이오마커 기록 목록 — BiomarkerRecord (개별 지표 패스스루)
    바이오마커 점수 목록 — BiomarkerScoreRecord (반복별 Z-score 종합, 기본 0–100의 조정 가능 척도)
    해석 기록 목록      — InterpretationRecord (반복별 YAML 규칙 기반 서술 라벨)
    수행 provenance report — actual_rep_count / failure-point metadata 기반 confidence note
    canonicalization report — 선택 좌표 표준화 prior, correction magnitude, confidence note
    세그멘테이션 리포트 — SegmentationReport 목록, 반복당 1개
    분할 실패 지점 기록 — SegmentationFailurePoint 목록, 수동 개입 필요 프레임/구간
    시각화 도형 (figures)
```

---

## 3. 단계별 처리 및 산출물 표 (Stage Processing and Outputs)

| 단계 | 입력/참조 정보 | 주요 처리 | 산출물 |
|---|---|---|---|
| ① Validation | Pose CSV | 필수 칼럼, 프레임 순서, 시간값, 랜드마크 좌표 구조, 결측 패턴을 검사한다. | Validation report |
| ② Annotation | Pose DataFrame, Annotation CSV, recording metadata(선택) | 수동 어노테이션 정보를 프레임 단위로 병합하고 `exercise_id`, `execution_pattern`, `starting_side`, 초기 `phase`, 촬영 provenance 칼럼, performance/failure provenance 요약을 구성한다. | Annotation이 병합된 DataFrame, annotation report |
| ③ Exercise Definition | `exercise_id`, split YAML 산출물 또는 legacy combined YAML | `ExerciseContext`를 로드하고 하위 호환 `ExerciseDefinition`을 반환한다. 없을 경우 `generic.yaml`을 적용한다. `camera_protocol`은 촬영 권장 조건과 경고 정책의 메타데이터로 보존한다. | ExerciseContext, ExerciseDefinition, camera protocol metadata |
| ④ Preprocessing | Pose DataFrame, `quality_rules` | 신뢰도 칼럼을 확인하고, 좌우 swap 후보, 결측값, 짧은 gap, 급격한 좌표 변화를 보정하며 필요한 경우 smoothing을 적용한다. | Preprocessed DataFrame, preprocessing report |
| ⑤ Normalization | Preprocessed DataFrame | 골반 중심 기준으로 좌표를 평행이동하고, 시퀀스 단위 몸통 길이 중앙값으로 척도화한다. | Normalized DataFrame |
| ⑥ Canonicalization | Normalized DataFrame, 운동/카메라/지지면 prior | support-plane, movement-plane, protocol-height, anthropometric prior를 이용해 선택 analysis-space 후보 좌표 계열을 방출할 수 있다. raw/norm/candidate 좌표 계열은 분리하고 모든 후보는 confidence, burden, residual, sensitivity provenance와 함께 보고한다. | 선택 후보 좌표 columns, canonicalization report, correction diagnostics |
| ⑦ Segmentation | Normalized DataFrame, `rep_segmentation`, `phase_segmentation` | 관절 움직임 기반으로 반복 경계를 산출하고, 반복 내부 phase를 라벨링한다. 불확실한 구간은 실패 지점으로 기록하고 수동 개입 결과를 반영한다. | `rep_id`, `phase`, SegmentationReport, SegmentationFailurePoint |
| ⑧ Feature Extraction | Segmented DataFrame, `feature_domains`, `performance_protocol.analysis_disrupting_patterns`, side-role 설정 | Feature extraction 내부에서 side-role context를 해석한 뒤 반복 단위 및 phase 단위의 range of motion, role alignment, movement path, tempo, variability, compensation feature를 계산하고 feature-registry coverage, compensation-candidate availability, analysis-disrupting pattern detectability를 보고한다. | FeatureRecord 목록, feature DataFrame, feature-role-context report, audit reports |
| ⑨ Biomech Proxy | Normalized/featured DataFrame, `biomechanical_focus` | CoM 궤적, 모멘트 암 프록시, load-shift 등 상대적 생체역학 지표를 계산한다. | BiomechRecord 목록 |
| ⑩ Biomarker Derivation | FeatureRecord, BiomechRecord, baseline | 개별 지표를 BiomarkerRecord로 변환하고, Z-score 기반 도메인 점수와 종합 점수를 산출한다. 좌표 보정량과 관측 품질은 movement quality score와 분리된 data-confidence/provenance로 해석한다. | BiomarkerRecord, BiomarkerScoreRecord, InterpretationRecord |
| ⑪ Visualization | 단계별 DataFrame, records, reports | 신뢰도, 관절각, phase, feature, biomarker 결과를 진단 및 결과 차트로 시각화한다. | figures |
| ⑫ Simulation | 정상 또는 기준 시퀀스, injector 설정 | 노이즈, 가려짐, ROM 제한, 속도 스파이크 등 조건을 주입하고 지표 반응성을 평가한다. | synthetic dataset, robustness report |

---

## 4. 활성 피처 계열 (Active Feature Families)

세부 수식과 임계값은 각 단계 문서에 둔다. 개요 문서에서는 현재 활성 계열만 요약한다.

```text
Spatial            ROM, 좌우 대칭, 궤적 형태, 보상 움직임 후보
Temporal           tempo와 반복 간 변동성
Control            CoM 안정성, 경로 일관성, smoothness, provenance gate
Biomech proxy      CoM 궤적, moment-arm proxy, 상대 load-shift 경향
Biomarker output   개별 metric record, Z-score 도메인/종합 점수, 규칙 기반 label
```

Feature availability와 관측 신뢰도는 movement quality와 분리한다. 낮은 신뢰도의 촬영 view,
낮은 visibility, 모델 depth 한계는 자동 감점이 아니라 provenance 또는 withholding logic으로
표현한다.

---

## 5. 핵심 운영 원칙 (Core Operating Rules)

- Annotation은 운동 식별자, 수행 패턴, 좌우 순서, protocol grouping, recording provenance를
  제공한다. [02_annotation.md](pipeline/02_annotation.md) 참조.
- Segmentation은 확정된 `rep_id`와 `phase`를 방출한다. 실패 지점은 수동 확인 전까지 해당
  구간이 반복 단위 또는 구간 단위 지표를 구동하지 않게 한다.
  [07_segmentation.md](pipeline/07_segmentation.md) 참조.
- Normalization은 프레임별 골반 중심 평행이동과 시퀀스 단위 몸통 길이 중앙값 척도화를
  사용한다. 후속 값은 무차원 `torso_length_ratio` 또는 도(degree) 단위로 유지하며,
  절대 힘/길이 단위는 사용하지 않는다. [05_normalization.md](pipeline/05_normalization.md) 참조.
- 선택 `canonicalization`은 raw/norm 좌표를 보존하고 별도 후보 좌표와 confidence/correction
  report를 방출한다. 좋은 동작 template에 맞추거나 실제 보상 움직임을 지우는 용도로 사용하지
  않는다. [06_canonicalization.md](pipeline/06_canonicalization.md) 참조.

---

## 6. 현재 개발 상태 (Current Development Status)

```text
구현됨
    ①-⑩ pipeline runner, split exercise YAML loading, annotation, preprocessing,
    normalization, canonicalization candidate reports, segmentation, feature-side-role context, features, biomech proxy,
    biomarker scoring, interpretation rules, synthetic-normal baseline.

Review-only / 기본 비활성
    support-plane, movement-plane, protocol-height lateral-width를 포함한
    canonicalization prior. 노트북 검토와 robustness 근거가 생기기 전까지
    후속 단계는 계속 norm 좌표를 사용한다.

부분 구현
    far-side landmark stabilization, simulation injector, visualization scaffolding.
    Visualization stub은 ⑪ Visualization 착수 전까지 의도적으로 유지한다.

다음 설계 gate
    Size Korea 8차 3D full-body automatic aggregate ratio를 느슨한 engineering envelope로
    사용하는 Stage A anthropometric skeleton prior for depth plausibility.
    이는 calibrated 3D reconstruction이나 empirical P5/P95 prior가 아니라
    confidence/provenance support여야 한다.

현재 범위 밖
    calibrated camera reprojection, Kalman filtering, full dashboard, Phantom 3D,
    절대 torque/force estimation, 실제 환자군 validation.
```

상세 작업 순서는 로컬 실행 계획 문서인 [`code_revision_plan.md`](code_revision_plan.md)에
둔다. 이 파일은 publication-facing overview가 아니다.
