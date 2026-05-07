# 06. 세그멘테이션 (Segmentation)

**문서 버전:** 1.1.0
**최종 갱신:** 2026-05-07
**영문 동기화:** `docs_eng/pipeline/06_segmentation.md`는 동일 버전의 영문 번역본이다.

파이프라인 단계 ⑥. 정규화된 관절 움직임을 추적하여 rep 경계와 phase 경계를 반자동으로
분리한다. 이 단계는 phase만 나누는 단계가 아니라, 반복(rep)과 반복 내 구간(phase)을 함께
확정하는 단계이므로 단계명은 `Phase Segmentation`이 아니라 `Segmentation`으로 둔다.
다만 기존 `phase_segmentation` 코드 식별자와 YAML 키는 phase 분할 용도로 유지하고,
새 반복 경계 검출은 `rep_segmentation`으로 분리한다.

자동 인식이 불명확한 지점은 `SegmentationFailurePoint`로 기록하고, 사용자의 수동 개입으로
경계를 확정한다. 본 단계는 프레임을 삭제하거나 좌표를 수정하지 않는다.

---

## 1. 파이프라인 위치 (Pipeline Position)

```text
Pose CSV
→ ① Validation
→ ② Annotation
→ ③ Exercise Definition
→ ④ Preprocessing
→ ⑤ Normalization
→ ⑥ Segmentation          ← 본 단계
→ ⑦ Motion Attribution
→ 후속 단계
```

## 2. 입력 (Inputs)

```text
normalized dataframe   ⑤ Normalization 이후 좌표
annotation metadata    ② Annotation의 set_id, rep_id, use_for_analysis, phase(선택)
exercise definition    ③ Exercise Definition의 rep_segmentation, phase_segmentation 설정
```

## 3. 출력 칼럼 (Output Columns)

```text
rep_id                         Int64     자동/수동 확정된 반복 ID
rep_segmentation_status        str       not_run | success | failed | manual_override | skipped
rep_segmentation_source        str       annotation | semi_auto | manual_override | fallback
rep_segmentation_failure_id    str       nullable; rep 경계 실패 리포트와 연결
phase                          object    Descent | Ascent | Bottom_Hold | Lift | Tap | Return | NA
phase_segmentation_status      str       not_run | success | failed | manual_override | skipped
phase_segmentation_source      str       annotation | semi_auto | manual_override | fallback
phase_segmentation_failure_id  str       nullable; phase 경계 실패 리포트와 연결
```

② Annotation에서 이미 `rep_id` 또는 `phase`가 제공된 경우, ⑥은 이를 후보 라벨로 취급한다.
자동 후보와 수동 후보가 충돌하면 자동으로 덮어쓰지 않고 실패 지점 또는 수동 개입 필요 상태로
기록한다.

## 4. 분할 대상 (Segmentation Targets)

```text
rep boundary      반복 시작/종료 프레임
phase boundary    반복 내부의 기구학적 전환 프레임
optional phase    Bottom_Hold 등 선택적 하위 구간
```

대표 phase 라벨:

```text
저항 운동    Descent | Bottom_Hold | Ascent
과제형 운동  Lift | Tap | Return
```

## 5. 반자동 분할 전략 (Semi-Automatic Segmentation Strategy)

운동 YAML의 두 설정 블록을 순서대로 사용한다.

```text
rep_segmentation      rep 시작/종료 경계를 추정하고 rep_id를 확정
phase_segmentation    확정 rep 내부에서 phase 경계를 추정하고 phase 칼럼을 채움
```

`phase_segmentation`은 기존 코드 식별자와 YAML 키를 그대로 사용한다. 이는 여전히 phase
분할을 뜻하며, 전체 단계명이 `Segmentation`으로 바뀌었다고 해서 `phase_segmentation` 키를
`segmentation`으로 바꾸지 않는다.

운동 YAML의 기준 랜드마크, 기준 축, 기대 phase 순서를 사용해 rep/phase 경계를 추정한다.
자동 추정은 다음 중 하나라도 불명확하면 성공으로 간주하지 않는다.

```text
- 기준 랜드마크의 가시성이 부족함
- 기준 축 움직임의 ROM이 너무 작음
- 후보 경계가 없거나 여러 개라 하나로 결정할 수 없음
- 경계 순서가 운동 YAML의 phase 순서와 맞지 않음
- 수동으로 지정된 경계와 자동 후보가 허용 오차 밖에서 충돌함
```

이 경우 ⑥은 해당 프레임 또는 프레임 구간을 `SegmentationFailurePoint`로 기록한다.
실패 지점은 보간하거나 성공으로 간주하지 않는다.

## 6. 분할 실패 지점 기록 (Segmentation Failure Point Record)

실패 지점 리포트는 최소한 다음 필드를 가진다.

```text
failure_id        str       고유 식별자
failure_level     str       rep_boundary | phase_boundary | optional_phase
set_id            Int64     nullable
rep_id            Int64     nullable
start_frame       int       실패 구간 시작 프레임
end_frame         int       실패 구간 종료 프레임
candidate_frame   int       nullable; 자동 후보 프레임
reason            str       low_visibility | insufficient_rom | missing_candidate |
                            multiple_candidates | order_mismatch | manual_required
confidence        float     nullable; 자동 후보 신뢰도
pipeline_action   str       exclude_range | rep_level_only | coarse_phase_continue |
                            wait_for_manual_override
resolved          bool      수동 개입으로 해결되었는지 여부
resolution_note   str       nullable
```

## 7. 실패 수준별 파이프라인 처리 (Pipeline Handling by Failure Level)

```text
rep_boundary 실패
    - 반복 경계를 확정할 수 없는 경우.
    - 수동 보정 전까지 해당 반복/구간은 반복 단위·구간 단위 분석에서 제외한다.
    - 후속 Feature/Biomech/Biomarker 산출물에는 해당 반복을 방출하지 않는다.

phase_boundary 실패
    - 반복 경계는 확정되었지만 하강/정지/상승 같은 phase 경계가 불명확한 경우.
    - 반복 단위 지표는 유지한다.
    - 해당 반복의 phase 단위 피처와 phase summary는 산출하지 않는다.

optional_phase 실패
    - Bottom_Hold처럼 선택적 phase만 불명확한 경우.
    - 선택 phase는 생략하고 Descent/Ascent 같은 coarse phase로 계속 진행한다.
    - 리포트에는 선택 phase 생략 사유를 남긴다.
```

## 8. 수동 개입 정책 (Manual Intervention Policy)

수동 개입은 실패 지점을 해결하기 위한 경계/라벨 메타데이터 확정이다. 좌표값을 바꾸지 않는다.

```text
rep_segmentation_status 또는 phase_segmentation_status = manual_override
rep_segmentation_source 또는 phase_segmentation_source = manual_override
```

수동 보정값은 후속 단계의 유일한 확정 라벨로 사용한다. 다만 자동 후보와의 차이, 보정 사유,
보정자 메모는 리포트에 남겨 provenance를 보존한다.

## 9. 후속 단계 영향 (Downstream Effects)

```text
⑦ Motion Attribution   확정된 rep_id를 기준으로 활성 측 일관성 판단
⑧ Feature Extraction   rep 단위 피처는 확정 rep 기준, phase 단위 피처는 성공/수동 확정 phase만 사용
⑨ Biomech Proxy        실패로 제외된 반복은 생체역학 프록시 산출에서 제외
⑩ Biomarker Derivation 실패 또는 제외 상태를 provenance에 남김
⑪ Visualization        실패 지점과 수동 보정 경계를 시각적으로 표시
```

## 10. 현재 범위 (Current Scope)

지원 항목:

```text
- 신규 rep_segmentation 기반 반복 경계 분할
- 기존 phase_segmentation 기반 반복 내부 phase 분할
- 수동 phase 라벨과 자동 후보의 충돌 기록
- 분할 실패 지점 기록
- 실패 수준별 파이프라인 처리 정책
- 수동 개입 후 확정 라벨 사용
```

범위 외 항목:

```text
- 실패 지점 검토 없는 완전 자동 분할
- 좌표값 수정
- 분할 실패를 임의 보간하여 성공으로 처리하는 정책
```
