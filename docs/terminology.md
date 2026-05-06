# 용어집 (Terminology)

**문서 버전:** 1.0.0  
**최종 갱신:** 2026-05-06  
**버전 규칙:** Semantic Versioning 2.0.0 (`MAJOR.MINOR.PATCH`)  
**영문 동기화:** `docs_eng/terminology.md`는 동일 버전의 영문 번역본이다.  
**파일명 정책:** `AGENTS.md` 기준에 따라 `terminology.md`를 표준 파일명으로 유지한다.

본 프로젝트의 표준 용어 정의. 모든 코드, 문서, 노트북은 동일한 용어를 동일한 의미로 사용한다.
새로운 용어를 다른 곳에서 사용하기 전에 먼저 이 문서에 추가한다.

---

## 1. 핵심 개념 (Core Concepts)

| 용어 | 정의 |
|---|---|
| 단안 비전 데이터 (Monocular vision data) | 단일 모바일 카메라에서 추출한 3D 포즈(pose) 시계열. 깊이 센서나 다중 카메라 장비를 사용하지 않는다. |
| 동작 품질 (Movement quality) | 동작의 생체역학적 특성 — 관절 정렬, 무게 중심(CoM) 안정성, 좌·우 대칭성, 관절 간 협응, 보상 작용(compensation) — 을 과제 완수 여부와 독립적으로 평가한 결과. |
| 디지털 바이오마커 (Digital biomarker) | 디지털로 측정된 생리·행동 신호로부터 도출된 해석 가능한 정량 지표. 본 프로젝트에서는 추적 가능한 산출 근거(provenance)를 갖춘 무차원 동작 품질 지표를 의미한다. |
| 해석 가능성 (Interpretability) | 모든 출력 지표가 그 계산을 유발한 운동 정의(exercise definition) 필드까지 역추적 가능한 속성 (`source_fields` provenance). |
| 분석 프레임워크 (Analysis framework) | 포즈 CSV를 일관된 규칙 하에 디지털 바이오마커로 변환하는 순서화된 파이프라인 단계 (①–⑩, 그중 ⑥–⑩이 핵심 분석 단계). 코드 모듈명이 아닌 단계명으로 지칭한다. |

---

## 2. 검증 운동 (Validation Exercises)

서로 다른 운동 특성 조합에서 파이프라인을 검증하기 위해 선정한 4개 대표 운동.
분석 단위는 운동 이름이 아니라 **운동 정의 객체(exercise definition object)** 이다.

| 운동 | exercise_id | 특성 샘플 |
|---|---|---|
| 스쿼트 (Squat) | `squat` | 양측 대칭(bilateral symmetric), 시상면(sagittal) ROM, 닫힌 사슬(closed chain), 수직 CoM |
| 런지 (Lunge) | `lunge` | 좌우 교대(alternating), 시상면, 양측 비대칭 보상 |
| 파이크 푸쉬업 (Pike push-up) | `pike_pushup` | 양측 대칭, 역방향 닫힌 사슬, 상체 협응 |
| 플랭크 숄더탭 (Plank shoulder tap) | `plank_shoulder_tap` | 좌우 교대, 관상면(frontal), 정적 자세 + 동적 과제, CoM 안정성 |

---

## 3. 피처 도메인 (Feature Domains)

동작 품질 특성화를 위한 3개 고정 도메인:

| 도메인 | 영문 표기 | 하위 항목(예) |
|---|---|---|
| 공간적 (Spatial) | Spatial features | ROM, 좌·우 대칭, 궤적 형태 |
| 시간적 (Temporal) | Temporal features | 템포(tempo), 반복 간 변동성, 구간(phase) 지속 시간 |
| 제어적 (Control) | Control features | CoM 안정성, 보상 움직임, 균형 제어 |

"제어(control)" 도메인을 단순히 "안정성(stability)"으로 줄이지 않는다.

---

## 4. 생체역학 핵심 개념 (Biomechanical Key Concepts)

| 용어 | 정의 |
|---|---|
| 관절 정렬 (Joint alignment) | 인접 관절·분절(segment)이 생체역학적으로 일관된 축을 형성하는 정도. 정렬 불량은 보상 작용의 일차 신호로 간주한다. |
| CoM 안정성 (Center of Mass stability) | 추정된 전신 무게 중심이 운동 구간 동안 예측 가능한 궤적을 따르며 비예측 분산이 낮은 정도. |
| 좌·우 대칭 (Left/right symmetry) | 양측 분절·관절 지표가 시간·공간상에서 유사한 정도. `bilateral_symmetric` 운동에서만 직접 평가한다. |
| 관절 간 협응 (Inter-joint coordination) | 다관절 운동 시 인접 관절의 위상과 속도가 생체역학적 기대치와 일치하는 정도. |
| 보상 움직임 (Compensatory movement) | 주된 작업 관절 외의 분절에서 발생하는 비주요 움직임으로, 제한된 ROM·근력 부족·균형 손실을 대체한다. 보상 규칙 레지스트리(COMPENSATION_RULES)를 통해 후보 이름이 기하학적 계산 함수에 매핑되어 탐지된다. |
| 합성 정상 베이스라인 (Synthetic-normal baseline) | 정상 조건의 합성 파이프라인 실행으로 산출된 지표별 (μ, σ) 기준 통계. `data/reference/baseline_zscore.json`에 저장되며, 동작 품질 점수의 Z-score는 절대적 임상 임계값이 아닌 이 베이스라인에 대해 계산된다. |
| 동작 품질 점수 (Movement quality score) | 도메인별 점수의 가중 평균(공간 40 %, 시간 30 %, 제어 20 %, biomech 10 %)으로 계산되는 반복(rep) 단위 종합 점수(0–100). 각 도메인 점수는 합성 정상 베이스라인 대비 Z-score 감점 방식이며, 의무 ROM 비율로부터 도출된 동적 하한(dynamic floor)으로 하방 경계가 설정된다. |
| 무게 중심 (CoM, Center of mass) | 통계적 인체 계측 모델(분절 질량 비율)을 사용하여 추정한 전신 무게 중심. 직립 자세와 엎드린 자세 양쪽에서 추정 가능해야 한다. |
| 모멘트 암 (Moment arm) | 관절 회전축과 작용선(line of action) 사이의 수직 거리. 절대 토크가 아닌 상대적 부하 분포 경향의 단순화된 추정치로 사용한다. |
| 인체 계측 모델 (Anthropometric model) | 분절 길이·질량·관절 중심 위치를 추정하기 위한 통계적 신체 비율 모델. 개인별 절대값이 아닌 상대 정규화 지표 산출에 사용한다. |

모든 출력은 상대적 부하 분포 경향이다. 절대 힘 단위(N·m, kg)는 사용하지 않는다.
출력에 절대 단위가 등장하면 버그로 간주한다.

---

## 5. 운동 정의 용어 (Exercise Definition Terms)

| 용어 | 정의 |
|---|---|
| 운동 정의 (Exercise definition) | 한 운동의 생체역학적 특성을 인코딩한 YAML 객체: 주요 관절(primary joints), 지지 기저면(base of support), 구간 모델(phase model), 보상 후보(compensation candidates), 품질 규칙 등. 분석 단위는 운동 이름이 아닌 운동 정의 객체이다. |
| 구간 (Phase) | 한 반복(rep) 내의 의미 있는 하위 구간. 두 가지 별개의 라벨링 체계가 공존한다: (1) **운동학적(kinetic) 구간** 라벨(eccentric / isometric / concentric)은 `phase_model.expected_ratio`에 저장되어 지속 시간 비율 참조용으로 사용되고, (2) **기구학적(kinematic) 구간** 라벨(Descent / Ascent / Bottom_Hold 등)은 ⑥ Phase Segmentation 단계에서 `phase` 칼럼에 기록된다. 두 체계는 의도적으로 분리되어 있다. |
| 기구학적 구간 (Kinematic phase) | 기준 랜드마크의 운동 방향(예: 골반 중심의 하강 vs. 상승)으로 정의되는 한 반복 내의 궤적 기반 하위 구간. 라벨: `Descent`, `Ascent`, `Bottom_Hold` (저항 운동); `Lift`, `Tap`, `Return` (과제형 운동). ⑥ Phase Segmentation에서 `phase` 칼럼에 기록되며, 운동학적 용어(eccentric, concentric)와 절대 혼용하지 않는다. |
| 변곡 프레임 (Inflection frame) | 기준 랜드마크가 방향을 반전하는 프레임. 평활화된 궤적의 국소 최소·최대로 검출된다. 한 반복을 구성 기구학적 구간들로 분할한다. SG 필터를 적용한 `find_peaks`로 식별되고 `multi_inflection_policy`에 의해 단일 후보로 축약된다. |
| Bottom_Hold | 변곡 프레임 주변 ±N 프레임에 부여하는 선택적 기구학적 구간 라벨. 운동이 가동 범위 하단에서 통제된 등척성(isometric) 유지 구간을 갖는 경우(예: 스쿼트 바닥) 사용한다. `phase_segmentation` 블록의 `bottom_hold.enabled: true`로 활성화된다. |
| Phase segmentation 블록 | 운동 정의의 `phase_segmentation:` YAML 블록으로, ⑥ Phase Segmentation의 기준 랜드마크, 기준 축, 구간 시퀀스, 평활화 파라미터, 변곡 검출 로직을 선언한다. `generic.yaml`에는 없으며, 부재 시 ⑥ 단계는 동작하지 않는다(no-op). |
| 보상 후보 (Compensation candidate) | 특정 운동에서 모니터링할 보상 움직임 유형. 정의에 명시된 후보만 바이오마커로 산출된다. |
| 품질 규칙 (Quality rules) | 분석 적격성을 결정하는 임계값: 가시성 비율(visibility ratio), 최대 갭 프레임 등. |

---

## 6. 처리 단계 용어 (Processing Step Terms)

| 용어 | 정의 |
|---|---|
| 검증 (Validation) | 입력 포즈 데이터의 구조적·형식적 무결성을 점검한다. 데이터를 수정하지 않는다. |
| 강건성 평가 (Robustness evaluation) | 합성 비정상 데이터를 사용해 파이프라인이 노이즈, 가려짐(occlusion), 정렬 변동에 일관되게 반응하는지 평가한다. 검증과 구분된다. |
| 어노테이션 (Annotation) | 분석 구간(set, rep)과 운동 컨텍스트 메타데이터를 표시한다. 칼럼만 추가하며 프레임을 삭제하지 않는다. |
| 전처리 (Preprocessing) | 단안 포즈 데이터의 품질 이슈(낮은 가시성, 분절 길이 불일치, 비정상 관절각, 속도 이상값, 좌·우 라벨 스왑)를 보정한다. 동작 품질 패턴(보상 움직임 등)은 보정하지 않는다. |
| 정규화 (Normalization) | 좌표를 신체 기준 좌표계(골반 중심 평행이동 + 시퀀스 중앙값 몸통 길이 척도)로 변환한다. 신체 크기와 카메라 위치 효과를 제거한다. |
| 모션 어트리뷰션 (Motion attribution) | 반복마다 관찰된 활성 사지(active limb)가 운동이 기대하는 측과 일치하는지 점검한다. 메타데이터만 추가하며 좌표를 수정하지 않는다. |
| 구간 분할 (Phase segmentation) | 반복 내 기구학적 전환점을 검출하여 기구학적 구간 라벨(Descent / Ascent / Bottom_Hold 등)을 `phase` 칼럼에 기록한다. 반복 경계는 어노테이션 CSV로 사람이 큐레이션하며, 반복 내 변곡만 자동화한다. 학위논문 §4.5에 해당. |
| 피처 추출 (Feature extraction) | 정규화 좌표와 운동 정의로부터 공간·시간·제어 도메인 정량 지표를 계산한다. ⑥ Phase Segmentation이 `phase` 칼럼을 채웠을 때, PHASE_AWARE_FEATURE_FAMILIES에 속한 피처는 반복 단위 기록과 더불어 (rep_id, phase) 단위로도 산출된다. |
| 생체역학 프록시 모델링 (Biomechanical proxy modeling) | 통계적 인체 계측, CoM, 모멘트 암 근사를 사용해 상대적 관절 부하 분포 경향을 추정한다. |
| 바이오마커 도출 (Biomarker derivation) | 피처와 프록시 지표를 (1) `source_fields` provenance를 갖춘 개별 `BiomarkerRecord` 항목과 (2) 합성 정상 베이스라인 대비 계산되는 반복 단위 `BiomarkerScoreRecord` 종합 점수(0–100)로 통합한다. |
| 가시성 기반 신뢰도 가중 (Visibility-based confidence weighting) | ⑨ 생체역학 프록시 모델링용 프레임 단위 가중 방식. 프레임 가중치 = 주요 관절 랜드마크의 평균 가시성. `minimum_visible_landmark_ratio` 미만 프레임은 가중치 0으로 지표 계산에서 제외된다. 단안 비전 고유의 깊이 추정 노이즈 영향을 줄인다. |
| 강건성 시뮬레이션 (Robustness simulation) | 정상 동작 데이터에 ROM 제한, 가우시안 노이즈, 가려짐, 속도 스파이크를 주입하여 파이프라인 평가용 합성 비정상 데이터를 생성한다. |

---

## 7. 데이터 및 좌표 규약 (Data and Coordinate Conventions)

| 항목 | 규약 |
|---|---|
| 포즈 좌표 배열 | `(T, J, 3)` = (frame, joint_index, xyz) |
| 단일 프레임 좌표 | `(J, 3)` |
| 각도 단위 | 도(degree). 변수명은 `_deg` 접미사 또는 docstring 주석으로 표기. |
| 시간 단위 | 초(second). 프레임 인덱스는 별도. |
| 정규화 길이 단위 | `torso_length_ratio` (무차원; 시퀀스 중앙값 몸통 길이로 나눔) |
| 좌·우 접두사 | `left_*`, `right_*` (소문자 + 언더스코어) |

---

## 8. 사용하지 않을 용어 (Terms Not to Use)

범위를 과장하거나 오해를 유발하는 표현.

| 사용 금지 | 사유 / 대체 표현 |
|---|---|
| "임상적으로 유의(clinically significant)" | 본 프로젝트는 임상 효능 검증이 아닌 공학적 강건성 검증이다. → "생체역학 기준으로부터의 편차를 일관되게 식별한다" |
| "질병을 진단/예측한다" | 진단 도구가 아니다. → "향후 임상 데이터 연구의 참조 지표로 활용 가능"(범위 명시) |
| 절대 토크/부하 (N·m) | 단안 비전으로는 추정 불가. → "관절 간 상대적 부하 분포 경향" |
| "정상/비정상(normal/abnormal)" 이분법 | 합성 비정상 데이터는 시뮬레이션 라벨이며 임상 진단이 아니다. → "참조 동작 / 합성 변형(synthetic variant)" |
| "환자 데이터" | 입력은 합성 데이터 + 정상 동작 데이터이다. 임상 데이터를 명시적으로 지칭할 때만 사용한다. |
| "자동 탐지(automatic detection)"(무한정) | 일차 분석은 어노테이션 기반이다. 자동 분할(automatic segmentation)은 향후 확장 항목이다. |
