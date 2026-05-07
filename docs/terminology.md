# 용어집 (Terminology)

**문서 버전:** 1.4.1
**최종 갱신:** 2026-05-08
**영문 동기화:** `docs_eng/terminology.md`는 동일 버전의 영문 번역본이다.

본 문서는 일반 용어 사전이 아니다. 통상적인 의미로 충분히 이해되는 단계명, 좌표 shape,
단위 표기, 운동 목록은 각 파이프라인 문서와 코드 docstring에서 다룬다.
여기에는 **본 연구에서 의미를 좁혀 쓰거나, 일반적 의미와 혼동되면 안 되는 용어**만 남긴다.

---

## 1. 연구 범위와 출력 의미 (Scope and Output Meaning)

| 용어 | 본 연구에서의 고정 의미 |
|---|---|
| 동작 품질 (Movement quality) | 과제 성공 여부가 아니라 관절 정렬, 좌·우 대칭성, CoM 안정성, 보상 움직임처럼 생체역학적으로 해석 가능한 움직임 특성을 뜻한다. |
| 디지털 바이오마커 (Digital biomarker) | 추적 가능한 산출 근거(`source_fields` provenance)를 가진 무차원 또는 상대 정규화 동작 품질 지표. 진단 라벨이나 임상 효능 지표가 아니다. |
| 생체역학 프록시 (Biomechanical proxy) | 단안 포즈 데이터로부터 계산 가능한 생체역학적 대리 지표. 실제 힘, 질량, 절대 토크를 직접 추정하지 않는다. |
| 상대 부하 분포 경향 (Relative load distribution tendency) | 관절·분절 간 부하가 어느 쪽으로 더 치우치는지 나타내는 상대적 경향. `N`, `N·m`, `kg` 같은 절대 단위를 산출하지 않는다. |
| 모멘트 암 프록시 (Moment-arm proxy) | 관절 중심과 기준 작용선 사이의 정규화 거리. 절대 토크 계산이 아니라 상대 부하 분포를 해석하기 위한 단순화 지표로 사용한다. |
| 합성 정상 베이스라인 (Synthetic-normal baseline) | 정상 조건의 합성 파이프라인 실행에서 얻은 지표별 기준 통계. 임상적 정상/비정상 라벨이 아니라 Z-score 계산용 참조 분포다. |
| 동작 품질 점수 (Movement quality score) | 합성 정상 베이스라인 대비 Z-score 감점 방식으로 계산하는 반복(rep) 단위 종합 점수(0–100). 임상 진단 점수가 아니다. |

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
| 운동 정의 (Exercise definition) | 운동 이름 자체가 아니라 YAML 객체를 뜻한다. 운동별 landmarks, phase 설정, 보상 후보, feature domain, quality rules를 포함하며 후속 단계의 기준 객체가 된다. |
| 보상 움직임 (Compensatory movement) | 주 작업을 대체하거나 왜곡하는 비주요 움직임. 본 연구에서는 YAML의 `compensation_candidates`와 코드의 보상 규칙 레지스트리에 등록된 후보만 바이오마커로 산출한다. |
| 검증 (Validation) | 입력 포즈 데이터의 구조적·형식적 무결성 점검. 강건성 평가와 구분하며, 데이터를 수정하지 않는다. |
| 강건성 평가 (Robustness evaluation) | 노이즈, 가려짐, ROM 제한, 속도 스파이크 등을 주입한 합성 조건에서 지표 반응성과 일관성을 확인하는 평가. 입력 무결성 검증과 다르다. |
| 가시성 기반 신뢰도 가중 (Visibility-based confidence weighting) | 생체역학 프록시 계산에서 주요 랜드마크 가시성을 프레임 가중치로 사용하는 방식. 낮은 가시성 프레임은 지표 계산 영향이 줄거나 제외된다. |

---

## 4. 사용하지 않을 용어 (Terms Not to Use)

범위를 과장하거나 오해를 유발하는 표현.

| 사용 금지 | 사유 / 대체 표현 |
|---|---|
| "임상적으로 유의(clinically significant)" | 본 프로젝트는 임상 효능 검증이 아닌 공학적 강건성 검증이다. → "생체역학 기준으로부터의 편차를 일관되게 식별한다" |
| "질병을 진단/예측한다" | 진단 도구가 아니다. → "향후 임상 데이터 연구의 참조 지표로 활용 가능"처럼 범위를 명시한다. |
| 절대 토크/부하 (N·m, kg) | 단안 비전으로는 추정하지 않는다. → "관절 간 상대적 부하 분포 경향" |
| "정상/비정상(normal/abnormal)" 이분법 | 합성 비정상 데이터는 시뮬레이션 라벨이며 임상 진단이 아니다. → "참조 동작 / 합성 변형(synthetic variant)" |
| "환자 데이터" | 입력은 합성 데이터와 정상 동작 데이터이다. 임상 데이터를 명시적으로 지칭할 때만 사용한다. |
| "자동 탐지(automatic detection)" 단독 표현 | rep/phase 분할은 실패 지점 기록과 수동 개입을 포함하는 반자동 절차이다. → "반자동 분할", "수동 검토 후 확정" |
