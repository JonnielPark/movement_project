# 개요 (Overview)

**문서 버전:** 1.4.6
**최종 갱신:** 2026-05-08
**영문 동기화:** [docs_eng/overview.md](../docs_eng/overview.md)는 동일 내용의 영문 번역본이다.

본 문서는 분석 파이프라인(pipeline)의 전체 설계를 기술한다.
용어 정의는 [`docs/terminology.md`](terminology.md)를 참조한다.

---

## 문서 인덱스 (Document Index)

| 버전 | 파일 | 내용 |
|---|---|---|
| 1.4.2 | [terminology.md](terminology.md) | 연구 특화 용어와 임상 표현 원칙 |
| 1.4.6 | [overview.md](overview.md) | 전체 파이프라인 개요 |
| 1.2.3 | [practical_protocols/camera_protocol.md](practical_protocols/camera_protocol.md) | 대상 운동별 촬영 프로토콜 |
| 1.0.3 | [practical_protocols/exercise_performance_protocol.md](practical_protocols/exercise_performance_protocol.md) | 대상 운동별 수행 프로토콜 |
| 1.0.0 | [00_data_format.md](pipeline/00_data_format.md) | 입력 CSV 데이터 포맷 |
| 1.0.0 | [01_validation.md](pipeline/01_validation.md) | ① Validation |
| 1.1.1 | [02_annotation.md](pipeline/02_annotation.md) | ② Annotation |
| 1.4.3 | [03_exercise_definition.md](pipeline/03_exercise_definition.md) | ③ Exercise Definition YAML |
| 1.0.0 | [04_preprocessing.md](pipeline/04_preprocessing.md) | ④ Preprocessing |
| 1.0.0 | [05_normalization.md](pipeline/05_normalization.md) | ⑤ Normalization |
| 1.2.0 | [06_segmentation.md](pipeline/06_segmentation.md) | ⑥ Segmentation |
| 1.0.0 | [07_motion_attribution.md](pipeline/07_motion_attribution.md) | ⑦ Motion Attribution |
| 1.0.1 | [08_feature_extraction.md](pipeline/08_feature_extraction.md) | ⑧ Feature Extraction |
| 1.0.0 | [09_biomechanical_proxy.md](pipeline/09_biomechanical_proxy.md) | ⑨ Biomech Proxy |
| 1.0.0 | [10_biomarker_scoring.md](pipeline/10_biomarker_scoring.md) | ⑩ Biomarker Scoring |
| 1.0.1 | [11_visualization.md](pipeline/11_visualization.md) | ⑪ Visualization |
| 1.0.0 | [12_insilico_simulation.md](pipeline/12_insilico_simulation.md) | ⑫ In-silico Simulation |

---

## 1. 핵심 설계: YAML 객체로서의 운동 정의 (Exercise Definitions as YAML Objects)

각 운동은 `data/definitions/exercises/<exercise_id>.yaml`의 YAML 객체로 기술한다.
모든 파이프라인 단계는 동일한 `ExerciseDefinition` 객체를 소비하며, 운동별 동작은
YAML 필드에서 결정된다.

운동 YAML에 정의되는 필드:

```text
classification        laterality, primary_plane, movement_chain, posture_type
landmarks             primary_joints, critical_landmarks, bilateral_pairs, base_of_support
phases                구간 모델 (예: eccentric / concentric)
rep_segmentation      반복 경계 검출 설정
phase_segmentation    반복 내부 phase 검출 설정
performance_protocol  피험자 안내 기준 카운트와 좌우 수행 순서 규칙
camera_protocol       권장 촬영 zone/height와 경고 정책
compensation_candidates  모니터링할 움직임 패턴
feature_domains       활성화할 공간/시간/제어 피처
biomechanical_focus   계산할 프록시(proxy) 지표
quality_rules         가시성 임계값, 최대 보간 갭 등
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
    ⑥  Segmentation        관절 움직임 추적 기반 rep/phase 반자동 분할
    ⑦  Motion Attribution   반복별 활성 측(active-side) 일관성 검사
    ⑧  Feature Extraction   공간/시간/제어 피처(반복 단위 + 구간 단위)
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
    Phase summary       — summarize_phase_to_rep() 계층 집계 (예: Descent/Ascent ROM 비율)
    생체역학 프록시 테이블 — BiomechRecord 목록, 반복 단위, 가시성(visibility) 가중
    바이오마커 기록 목록 — BiomarkerRecord (개별 지표 패스스루)
    바이오마커 점수 목록 — BiomarkerScoreRecord (반복별 Z-score 종합, 0–100)
    해석 기록 목록      — InterpretationRecord (반복별 YAML 규칙 기반 서술 라벨)
    세그멘테이션 리포트 — SegmentationReport 목록, 반복당 1개
    분할 실패 지점 기록 — SegmentationFailurePoint 목록, 수동 개입 필요 프레임/구간
    시각화 도형 (figures)
```

---

## 3. 단계별 처리 및 산출물 표 (Stage Processing and Outputs)

| 단계 | 입력/참조 정보 | 주요 처리 | 산출물 |
|---|---|---|---|
| ① Validation | Pose CSV | 필수 칼럼, 프레임 순서, 시간값, 랜드마크 좌표 구조, 결측 패턴을 검사한다. | Validation report |
| ② Annotation | Pose DataFrame, Annotation CSV, recording metadata(선택) | 수동 어노테이션 정보를 프레임 단위로 병합하고 `exercise_type`, `pattern`, `starting_side`, 초기 `phase`, 촬영 provenance 칼럼을 구성한다. | Annotation이 병합된 DataFrame |
| ③ Exercise Definition | `exercise_type`, exercise YAML | 운동별 YAML을 로드하여 `ExerciseDefinition` 객체를 생성하고, 없을 경우 `generic.yaml`을 적용한다. `camera_protocol`은 촬영 권장 조건과 경고 정책의 정의 메타데이터로 보존한다. | ExerciseDefinition, camera protocol metadata |
| ④ Preprocessing | Pose DataFrame, `quality_rules` | 신뢰도 칼럼을 확인하고, 좌우 swap 후보, 결측값, 짧은 gap, 급격한 좌표 변화를 보정하며 필요한 경우 smoothing을 적용한다. | Preprocessed DataFrame, preprocessing report |
| ⑤ Normalization | Preprocessed DataFrame | 골반 중심 기준으로 좌표를 평행이동하고, 시퀀스 단위 몸통 길이 중앙값으로 척도화한다. | Normalized DataFrame |
| ⑥ Segmentation | Normalized DataFrame, `rep_segmentation`, `phase_segmentation` | 관절 움직임 기반으로 반복 경계를 산출하고, 반복 내부 phase를 라벨링한다. 불확실한 구간은 실패 지점으로 기록하고 수동 개입 결과를 반영한다. | `rep_id`, `phase`, SegmentationReport, SegmentationFailurePoint |
| ⑦ Motion Attribution | Segmented DataFrame, laterality/pattern 설정 | 반복별 활성 측을 추정하고, 교대 운동의 좌우 순서와 주동측 일관성을 검사한다. | active-side flag, attribution report |
| ⑧ Feature Extraction | Segmented DataFrame, `feature_domains` | 반복 단위 및 phase 단위의 ROM, symmetry, trajectory, tempo, variability, compensation feature를 계산한다. | FeatureRecord 목록, feature DataFrame |
| ⑨ Biomech Proxy | Normalized/featured DataFrame, `biomechanical_focus` | CoM 궤적, 모멘트 암 프록시, load-shift 등 상대적 생체역학 지표를 계산한다. | BiomechRecord 목록 |
| ⑩ Biomarker Derivation | FeatureRecord, BiomechRecord, baseline | 개별 지표를 BiomarkerRecord로 변환하고, Z-score 기반 도메인 점수와 종합 점수를 산출한다. | BiomarkerRecord, BiomarkerScoreRecord, InterpretationRecord |
| ⑪ Visualization | 단계별 DataFrame, records, reports | 신뢰도, 관절각, phase, feature, biomarker 결과를 진단 및 결과 차트로 시각화한다. | figures |
| ⑫ Simulation | 정상 또는 기준 시퀀스, injector 설정 | 노이즈, 가려짐, ROM 제한, 속도 스파이크 등 조건을 주입하고 지표 반응성을 평가한다. | synthetic dataset, robustness report |

---

## 4. 피처 도메인 (Feature Domains)

```text
공간(Spatial)
    ROM (가동 범위)
    좌·우 대칭(symmetry)
    궤적(trajectory) 형태

시간(Temporal)
    템포(tempo, 수행 속도)
    반복 간 변동성

제어(Control)
    CoM 안정성 (골반 중심 변위 표준편차)
    보상 움직임 — 규칙 기반 레지스트리:
        knee_valgus / knee_varus     관상면(frontal-plane) hip-ankle 라인 대비 무릎 편차
        lateral_pelvic_shift         골반 중심 측방 변위
        excessive_trunk_flexion      수직 대비 체간 기울기 각
        heel_lift                    반복 최저점 대비 발뒤꿈치 들림
        pelvis_rotation              좌·우 골반 깊이 비대칭 (횡단면 프록시)
```

특정 운동에 어떤 도메인이 활성인지는 운동 YAML의 `feature_domains` 필드로 제어된다.

---

## 5. 어노테이션 전략 (Annotation Strategy)

② Annotation은 사용자가 준비한 수동 어노테이션 CSV를 포즈 데이터프레임에 병합한다.
어노테이션 파일이 공급되지 않으면 전체 시퀀스가 단일 분석 구간으로 처리된다.

후속 단계를 구동하는 주요 어노테이션 칼럼:

```text
exercise_type      어떤 운동 YAML을 로드할지 식별 (③)
pattern            bilateral | alternating
starting_side      교대 운동에서 첫 활성 측 (⑦)
```

[02_annotation.md](pipeline/02_annotation.md) 참조.

---

## 6. 세그멘테이션 전략 (Segmentation Strategy)

⑥ Segmentation은 두 하위 절차로 나뉜다. 신규 `rep_segmentation`은 관절 움직임을 추적해
반복 경계를 반자동으로 확정하고, 기존 `phase_segmentation`은 확정된 반복 내부에서 하강,
정지, 상승 같은 phase를 나눈다. 자동 인식이 불명확하면 사용자가 중간에 개입하여 반복
경계나 phase 라벨을 강제로 지정한다.

분할 실패 지점은 `SegmentationFailurePoint`로 기록한다. 실패 수준은 다음처럼 처리한다.

```text
rep_boundary 실패      해당 반복/구간은 수동 보정 전까지 반복 단위·구간 단위 분석에서 제외
phase_boundary 실패    반복 단위 지표는 유지하되, 해당 반복의 구간 단위 지표는 산출하지 않음
optional_phase 실패    Turnaround_Hold 등 선택 구간만 생략하고 coarse phase로 계속 진행
```

수동 개입으로 경계가 확정되면 `rep_segmentation_source` 또는 `phase_segmentation_source`를
`manual_override`로 남기고 후속 단계는 확정된 라벨만 사용한다. 실패 지점은 조용히 보간하거나
성공으로 간주하지 않는다.

[06_segmentation.md](pipeline/06_segmentation.md) 참조.

---

## 7. 정규화 전략 (Normalization Strategy)

```text
평행이동 기준 : 프레임별 골반 중심
척도 기준     : 시퀀스 단위 몸통 길이 중앙값
```

(프레임별 척도가 아닌) 시퀀스 단위 중앙값을 사용하는 것은, 단안 데이터의 프레임별 몸통 길이
노이즈로 인한 인위적 골격 떨림을 방지하기 위함이다.

이후 모든 피처와 바이오마커는 `torso_length_ratio` 단위(무차원) 또는 도(degree)로 표현된다.
절대 힘·길이 단위는 사용하지 않는다.

[05_normalization.md](pipeline/05_normalization.md) 참조.

---

## 8. 개발 로드맵 (Development Roadmap)

```text
2026.03 – 2026.05  환경 구축 및 파이프라인 설계
  [완료]  Pose CSV 로딩, 검증, 3D 시각화
  [완료]  좌표 정규화, 어노테이션
  [완료]  Exercise definition 스키마, YAML 로더, generic 폴백
  [완료]  파이프라인 러너 + 전처리
  [완료]  Motion attribution 모듈 (⑦)
  [완료]  features / biomech / biomarker / simulation 모듈 스캐폴딩

2026.06 – 2026.09  피처 추출 (⑧)
  [완료]  compute_rom() — YAML angle_definitions(points + vertex index 형식)와 연결
  [완료]  compute_symmetry() — 반복별 좌·우 ROM 대칭 지수
  [완료]  compute_shape() — 반복별 주요 관절 호 길이(arc length)
  [완료]  extract_rep_features() — 반복별 공간/시간/제어 피처 추출
  [완료]  features_to_dataframe() — FeatureRecord 목록 → DataFrame 내보내기
  [완료]  파이프라인 ⑧ 연결 — extract_rep_features()를 run_pipeline()에 결선
  [완료]  보상 규칙 엔진 — COMPENSATION_RULES 레지스트리 (knee_valgus, knee_varus, lateral_pelvic_shift, excessive_trunk_flexion, heel_lift, pelvis_rotation)
  Visualization: 신뢰도 오버레이, 관절각 시계열, 단계별 결과 차트

2026.10 – 2027.01  생체역학 프록시 모델링 및 바이오마커 도출 (⑨–⑩)
  [완료]  CoM 궤적 지표 — 반복 단위 (range_x, range_z, path_length) + 가시성 가중
  [완료]  모멘트 암 프록시 — 무릎/엉덩이 시상면, 반복 단위 + 가시성 가중
  [완료]  extract_rep_biomech() 오케스트레이터를 파이프라인 ⑨에 결선
  [완료]  바이오마커 레코드 변환 (FeatureRecord / BiomechRecord → BiomarkerRecord)
  [완료]  BiomarkerScoreRecord — Z-score 감점, 동적 하한(dynamic floor), 도메인 종합 점수 (0–100)
  [완료]  derive_biomarkers() 진입점을 파이프라인 ⑩에 결선
  [완료]  합성 정상 베이스라인 (data/reference/baseline_zscore.json, scripts/compute_baseline.py)
  [진행]  Segmentation (⑥) — `rep_segmentation` 반복 경계 검출 + 기존 `phase_segmentation` phase 분할; 실패 시 수동 개입
  [계획]  Exercise YAML의 `phases` 정의를 반자동 phase 라벨 및 구간 단위 피처와 연결
  [완료]  FeatureRecord.phase 필드; extract_rep_features()가 반복 단위 + 구간 단위 레코드 방출
  [완료]  summarize_phase_to_rep() 계층 집계기 (Descent/Ascent ROM 비율)
  [완료]  Load-shift OLS — biomech/load_shift.py의 compute_load_shift(); 지표 biomech.load_shift.<joint>.<side>.slope (torso_length_ratio_per_rep); ≥ 3 반복 필요; test_biomech_load_shift.py (17건)
  [완료]  YAML 기반 해석 규칙 — biomarker/interpretation.py의 derive_interpretations(); 4개 운동 규칙 파일 (data/definitions/interpretation_rules/); InterpretationRecord; test_interpretation.py (20건)
  [완료]  임상 피처 매핑 — docs/clinical/per_exercise_mapping.md (§5.5/§5.6) + data/definitions/clinical/feature_meanings.yaml (대시보드 툴팁용 YAML 미러)

2027.02 – 2027.05  강건성 시뮬레이션 및 평가
  [부분]  시뮬레이션 조건 인젝터(injector) — 노이즈, 가려짐, ROM 제한, 속도 스파이크
  강건성 실험 러너 스크립트 (scripts/run_robustness_experiment.py)
  바이오마커 출력의 단조성(monotonicity) / 반응성(responsiveness) / 특이도(specificity) 분석
```
