# 00. 개요 (Overview)

**문서 버전:** 1.0.0  
**최종 갱신:** 2026-05-06  
**버전 규칙:** Semantic Versioning 2.0.0 (`MAJOR.MINOR.PATCH`)  
**영문 동기화:** `docs_eng/00_overview.md`는 동일 버전의 영문 번역본이다.

본 문서는 분석 파이프라인(pipeline)의 전체 설계를 기술한다.
용어 정의는 [`docs/_terminology.md`](_terminology.md)를 참조한다.

---

## 0. 문서 버전 관리 (Document Versioning)

모든 문서는 2026-05-06부터 `1.0.0`으로 버전 표기를 시작한다. 버전 규칙은
Semantic Versioning 2.0.0의 `MAJOR.MINOR.PATCH` 형식을 따른다.

```text
MAJOR  문서 구조, 파이프라인 단계 정의, 공개 API 의미가 호환되지 않게 바뀐 경우
MINOR  새 기능/새 섹션/새 산출물 설명이 추가되었으나 기존 의미와 호환되는 경우
PATCH  오탈자, 번역, 링크, 표현 명확화처럼 의미 변화가 없는 경우
```

운영 규칙:

```text
[필수]
- `docs/`는 한글 기준 문서이다.
- `docs_eng/`는 같은 버전과 같은 내용을 가진 영문 번역본이다.
- `README_eng.md`는 `README.md`의 영문 번역본일 뿐이며 별도 내용을 갖지 않는다.
- `code_revision_plan.md`는 로컬 실행 계획으로 유지하고 git 업로드 대상에서 제외한다.
- `_terminology.md`는 개발 완료 후 최종 문서 번호 prefix를 파일명 앞에 부여한다.
```

같은 폴더 내 문서 인덱스:

| 버전 | 파일 | 내용 | 영문 번역본 |
|---|---|---|---|
| 1.0.0 | [_terminology.md](_terminology.md) | 용어집 | [docs_eng/_terminology.md](../docs_eng/_terminology.md) |
| 1.0.0 | [00_overview.md](00_overview.md) | 전체 파이프라인 개요 | [docs_eng/00_overview.md](../docs_eng/00_overview.md) |
| 1.0.0 | [01_data_format.md](01_data_format.md) | 입력 CSV 데이터 포맷 | [docs_eng/01_data_format.md](../docs_eng/01_data_format.md) |
| 1.0.0 | [02_validation.md](02_validation.md) | ① Validation | [docs_eng/02_validation.md](../docs_eng/02_validation.md) |
| 1.0.0 | [03_annotation_and_segmentation.md](03_annotation_and_segmentation.md) | ② Annotation · ⑥ Phase Segmentation | [docs_eng/03_annotation_and_segmentation.md](../docs_eng/03_annotation_and_segmentation.md) |
| 1.0.0 | [04_exercise_definition.md](04_exercise_definition.md) | ③ Exercise Definition YAML | [docs_eng/04_exercise_definition.md](../docs_eng/04_exercise_definition.md) |
| 1.0.0 | [05_preprocessing.md](05_preprocessing.md) | ④ Preprocessing | [docs_eng/05_preprocessing.md](../docs_eng/05_preprocessing.md) |
| 1.0.0 | [06_normalization.md](06_normalization.md) | ⑤ Normalization | [docs_eng/06_normalization.md](../docs_eng/06_normalization.md) |
| 1.0.0 | [07_motion_attribution.md](07_motion_attribution.md) | ⑦ Motion Attribution | [docs_eng/07_motion_attribution.md](../docs_eng/07_motion_attribution.md) |
| 1.0.0 | [08_feature_extraction.md](08_feature_extraction.md) | ⑧ Feature Extraction | [docs_eng/08_feature_extraction.md](../docs_eng/08_feature_extraction.md) |
| 1.0.0 | [09_biomechanical_proxy.md](09_biomechanical_proxy.md) | ⑨ Biomech Proxy | [docs_eng/09_biomechanical_proxy.md](../docs_eng/09_biomechanical_proxy.md) |
| 1.0.0 | [10_biomarker_scoring.md](10_biomarker_scoring.md) | ⑩ Biomarker Scoring | [docs_eng/10_biomarker_scoring.md](../docs_eng/10_biomarker_scoring.md) |
| 1.0.0 | [11_visualization.md](11_visualization.md) | ⑪ Visualization | [docs_eng/11_visualization.md](../docs_eng/11_visualization.md) |
| 1.0.0 | [12_insilico_simulation.md](12_insilico_simulation.md) | ⑫ In-silico Simulation | [docs_eng/12_insilico_simulation.md](../docs_eng/12_insilico_simulation.md) |

`code_revision_plan.md`는 위 버전 관리 대상에는 포함하지만, git 업로드 대상에서는 제외한다.

---

## 1. 핵심 설계: YAML 객체로서의 운동 정의 (Exercise Definitions as YAML Objects)

운동별 분석 코드를 작성하는 대신, 각 운동을 YAML 객체로 기술한다
(`data/exercise_definitions/<exercise_id>.yaml`). 모든 파이프라인 단계는 동일한
`ExerciseDefinition` 객체를 소비하며, 운동별 동작은 코드 분기가 아니라 YAML 필드에서 비롯된다.

```
이전 : 운동별(스쿼트, 런지, …)로 분리된 분석 코드
이후  : 운동별 YAML 1개, 모든 운동에 동일한 파이프라인 단계 적용
```

운동 YAML에 정의되는 필드:

```text
classification        laterality, primary_plane, movement_chain, posture_type
landmarks             primary_joints, critical_landmarks, bilateral_pairs, base_of_support
phases                구간 모델 (예: eccentric / concentric)
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
    Exercise YAML      운동 정의

단계
    ①  Validation           구조적 무결성 검사 — 데이터 미수정
    ②  Annotation           어노테이션 파일에서 구간/반복 메타데이터 병합
    ③  Exercise Definition  ExerciseDefinition 객체 로드(미존재 시 generic 폴백)
    ④  Preprocessing        신뢰도 검출, 좌·우 스왑(swap) 보정, 보간(interpolation), 평활화(smoothing)
    ⑤  Normalization        골반 중심 평행이동 + 몸통 길이 중앙값 척도화
    ⑥  Phase Segmentation  반복 내 기구학적 구간(Descent/Ascent/…)의 반자동 분할
    ⑦  Motion Attribution   반복별 활성 측(active-side) 일관성 검사
    ⑧  Feature Extraction   공간/시간/제어 피처(반복 단위 + 구간 단위)
    ⑨  Biomech Proxy        CoM, 모멘트 암(moment arms), 인체 계측(Winter 1990)
    ⑩  Biomarker Derivation BiomarkerRecord(개별 지표) + BiomarkerScoreRecord(반복 단위 종합)
    ⑪  Visualization        ①–⑩ 러너(runner) 외부에서 호출; 진단 및 결과 차트
    ⑫  Simulation           강건성 시뮬레이션, 러너 외부에서 호출

출력
    단계별 데이터프레임(DataFrame) (칼럼 누적)
    단계별 리포트(report) 딕셔너리
    phase 칼럼          — 'Descent' | 'Ascent' | 'Bottom_Hold' | 'Lift' | 'Tap' | 'Return' | NA
    Feature 테이블      — FeatureRecord 목록, 반복 단위(phase=None) + 구간 단위(phase=str)
    Phase summary       — summarize_phase_to_rep() 계층 집계 (예: Descent/Ascent ROM 비율)
    생체역학 프록시 테이블 — BiomechRecord 목록, 반복 단위, 가시성(visibility) 가중
    바이오마커 기록 목록 — BiomarkerRecord (개별 지표 패스스루)
    바이오마커 점수 목록 — BiomarkerScoreRecord (반복별 Z-score 종합, 0–100)
    해석 기록 목록      — InterpretationRecord (반복별 YAML 규칙 기반 서술 라벨)
    구간 분할 리포트    — PhaseSegmentationReport 목록, 반복당 1개
    시각화 도형 (figures)
```

② 단계는 ③ 이전에 실행된다. 어노테이션 파일의 `exercise_type` 칼럼이 어떤 운동 YAML을
로드할지 식별하기 때문이다. ③ 이후 모든 단계는 동일한 정의 객체를 참조한다.

---

## 3. 단계 책임 표 (Stage Responsibility Table)

| 단계 | 수행 항목 | 수행하지 않음 |
|---|---|---|
| ① Validation | 무결성 진단 | 데이터 수정 |
| ② Annotation | 프레임 단위 메타데이터 칼럼 추가; `phase`를 NA로 사전 채움 | 좌표 수정 |
| ③ Exercise Definition | ExerciseDefinition 객체 로드 | 어노테이션·좌표 수정 |
| ④ Preprocessing | 데이터 품질 이슈 보정 | 동작 품질 패턴 변경 |
| ⑤ Normalization | 신체 상대 좌표계로 평행이동 + 척도화 | 운동 종류별 분기 |
| ⑥ Phase Segmentation | 반복 프레임의 `phase` 칼럼 채우기(기구학적 라벨) | 기존 비-NA `phase` 값 덮어쓰기; 좌표 수정 |
| ⑦ Motion Attribution | 반복별 활성 측 일관성 플래그 | 좌표·점수 수정 |
| ⑧ Feature Extraction | 반복 단위·구간 단위 공간/시간/제어 피처 계산 | 라벨 보정 |
| ⑨ Biomech Proxy | CoM, 모멘트 암, 상대 부하 분포 계산 | 절대 토크 계산 |
| ⑩ Biomarker Derivation | provenance를 갖춘 BiomarkerRecord + BiomarkerScoreRecord 산출 | source_fields 없는 기록 방출 |
| ⑪ Visualization | 진단·결과 도형 산출 | 데이터 수정 |

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

자동 분할(automatic segmentation)은 본 연구의 범위가 아니다. 반복 경계는 사전에 준비된
어노테이션 CSV로 제공된다. 어노테이션 파일이 공급되지 않으면 전체 시퀀스가 단일 분석 구간으로 처리된다.

후속 단계를 구동하는 주요 어노테이션 칼럼:

```text
exercise_type      어떤 운동 YAML을 로드할지 식별 (③)
pattern            bilateral | alternating
starting_side      교대 운동에서 첫 활성 측 (⑦)
```

[03_annotation_and_segmentation.md](03_annotation_and_segmentation.md) 참조.

---

## 6. 정규화 전략 (Normalization Strategy)

```text
평행이동 기준 : 프레임별 골반 중심
척도 기준     : 시퀀스 단위 몸통 길이 중앙값
```

(프레임별 척도가 아닌) 시퀀스 단위 중앙값을 사용하는 것은, 단안 데이터의 프레임별 몸통 길이
노이즈로 인한 인위적 골격 떨림을 방지하기 위함이다.

이후 모든 피처와 바이오마커는 `torso_length_ratio` 단위(무차원) 또는 도(degree)로 표현된다.
절대 힘·길이 단위는 사용하지 않는다.

[06_normalization.md](06_normalization.md) 참조.

---

## 7. 개발 로드맵 (Development Roadmap)

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
  [완료]  Phase segmentation (⑥) — segment_phases(), SG 평활화 + find_peaks, 파이프라인 결선
  [완료]  Exercise YAML에 phase_segmentation 블록 추가 (v0.2.0); PhaseSegmentationSpec 파싱
  [완료]  FeatureRecord.phase 필드; extract_rep_features()가 반복 단위 + 구간 단위 레코드 방출
  [완료]  summarize_phase_to_rep() 계층 집계기 (Descent/Ascent ROM 비율)
  [완료]  Load-shift OLS — biomech/load_shift.py의 compute_load_shift(); 지표 biomech.load_shift.<joint>.<side>.slope (torso_length_ratio_per_rep); ≥ 3 반복 필요; test_biomech_load_shift.py (17건)
  [완료]  YAML 기반 해석 규칙 — biomarker/interpretation.py의 derive_interpretations(); 4개 운동 규칙 파일 (data/interpretation_rules/); InterpretationRecord; test_interpretation.py (20건)
  [완료]  임상 피처 매핑 — docs/clinical/per_exercise_mapping.md (§5.5/§5.6) + data/clinical/feature_meanings.yaml (대시보드 툴팁용 YAML 미러)

2027.02 – 2027.05  강건성 시뮬레이션 및 평가
  [부분]  시뮬레이션 조건 인젝터(injector) — 노이즈, 가려짐, ROM 제한, 속도 스파이크
  강건성 실험 러너 스크립트 (scripts/run_robustness_experiment.py)
  바이오마커 출력의 단조성(monotonicity) / 반응성(responsiveness) / 특이도(specificity) 분석
```
