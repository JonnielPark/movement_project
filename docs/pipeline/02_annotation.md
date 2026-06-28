# 02. 어노테이션 (Annotation)

**문서 버전:** 1.2.0
**최종 갱신:** 2026-05-21
**영문 동기화:** `docs_eng/pipeline/02_annotation.md`는 동일 버전의 영문 번역본이다.

파이프라인 단계 ②는 사용자가 준비한 구간 메타데이터를 포즈 데이터프레임에 병합한다.
수동 라벨, 촬영 provenance, 수행 provenance를 보존한다.
rep/phase 경계를 추정하거나 프레임을 삭제하거나 좌표를 수정하지 않는다.
rep/phase 경계 추정과 segmentation failure 처리는
[07_segmentation.md](07_segmentation.md)에서 담당한다.

---

## 1. 파이프라인 위치 (Pipeline Position)

```text
Pose CSV
→ ① Validation
→ ② Annotation             ← 본 단계
→ ③ Exercise Definition
→ ④ Preprocessing
→ 후속 단계
```

② 단계는 ③ 이전에 실행된다. `exercise_id`가 운동 정의 YAML을 선택하기 때문이다.

## 2. 출력 계약 (Output Contract)

본 단계가 추가하거나 채우는 frame-level 칼럼:

```text
use_for_analysis    bool      분석 포함 여부
segment_type        str       full_sequence | baseline | idle | rep | rest | transition | excluded
set_id              Int64     nullable 세트 식별자
rep_id              Int64     nullable 반복 식별자
phase               object    선택 수동 phase 라벨; ⑦에서 확정
note                str       선택 구간 기록
exercise_id         str       운동 정의 식별자
execution_pattern   str       bilateral | alternating; 관찰된 좌우/순서 pattern
starting_side       str       left | right; 교대/단측 운동 컨텍스트
session_id          str       선택 취득 세션 식별자
recording_id        str       선택 촬영 파일 식별자
set_index           Int64     세션 내 세트 순서
camera_zone         str       Z1-Z8 | unknown
camera_height_level str       H1-H3 | unknown
reference_mat_used  bool      nullable 기준 앵커 사용 여부
filming_protocol_status str   recommended | out_of_zone | no_anchor | unknown
performance_protocol_status str completed | partial | stopped_at_failure_point | unknown
actual_rep_count    Int64     실제 완료한 관찰 count
failure_point_frame Int64     관찰된 protocol 중단/실패 프레임
failure_rep_id      Int64     protocol failure가 처음 나타난 rep
failure_reason      str       posture_breakdown | inconsistent_rom | side_order_error | pain_or_risk | participant_stop | unknown
performance_note    str       수행 관련 자유 기록
rep_side_sequence   str       관찰된 좌우 순서, 예: right,left,right,left
side_block_size     Int64     해당 시 관찰된 같은 측 블록 크기
rep_unit            str       repetition | tap | 기타 운동 정의 단위
protocol_cycle_id   Int64     원자 반복을 묶는 사용자 안내 기준 cycle id
```

후속 사용:

```text
exercise_id                   → ③ exercise definition 로딩
execution_pattern / starting_side
                               → ④ L/R 점검 및 ⑧ Feature Extraction role context
phase                          → 본 단계에서 보존, ⑦에서 수용/거부
filming provenance             → warning/report 컨텍스트만 제공
performance provenance         → warning/report 컨텍스트만 제공
rep_side_sequence 계열          → ③ performance_protocol과 비교
```

## 3. 어노테이션 CSV (Annotation CSV)

필수 칼럼:

```text
segment_type, set_id, rep_id, start_frame, end_frame, use_for_analysis
```

선택 칼럼은 2절에 나열한 나머지 출력 컨텍스트 필드이다.

최소 예시:

```csv
segment_type,set_id,rep_id,start_frame,end_frame,use_for_analysis,exercise_id,execution_pattern,starting_side
baseline,,,20,60,false,squat,bilateral,
rep,1,1,85,160,true,squat,bilateral,
rep,1,2,170,245,true,squat,bilateral,
rest,1,,246,320,false,squat,bilateral,
rep,2,1,340,415,true,squat,bilateral,
idle,,,416,460,false,squat,bilateral,
```

교대 운동에서는 `starting_side`가 첫 기대 활성 측을 정의한다.
예를 들어 `plank_shoulder_tap`에서 `execution_pattern=alternating`,
`starting_side=right`이면 rep 1은 right, rep 2는 left로 이어진다.

## 4. 동작 (Behavior)

어노테이션 CSV가 제공된 경우:

```text
1. 필수 칼럼, segment_type 값, 프레임 범위, 중첩 여부를 검증한다.
2. 모든 프레임을 use_for_analysis = False로 초기화한다.
3. 선언된 inclusive frame range에 구간 메타데이터를 적용한다.
4. 어떤 구간에도 포함되지 않은 프레임은 제외 상태로 남긴다.
5. 원본 frame 번호는 보존한다.
```

어노테이션 CSV가 없는 경우:

```text
use_for_analysis = True
segment_type     = full_sequence
set_id / rep_id  = None
phase            = None
exercise_id      = None   → ③은 generic fallback 로딩
execution_pattern = bilateral
starting_side    = None
camera_zone      = unknown
camera_height_level = unknown
filming_protocol_status = unknown
```

리포트는 `annotation_provided = False`와
`performance_provenance.available = False`를 기록한다.

## 5. Provenance 정책 (Provenance Policy)

촬영 및 수행 메타데이터는 provenance이며 자동 보정 규칙이 아니다.

```text
metadata 누락                       → annotation은 계속 성공
out-of-zone 촬영 상태               → warning/report만 제공
낮은 actual_rep_count               → movement-quality 직접 감점 아님
failure_point_frame                 → 관찰된 protocol 중단 지점, segmentation failure 아님
side-sequence 불일치                → ⑦이 motion evidence로 flag하지 않는 한 warning/provenance
```

annotation report는 압축된 performance summary를 노출한다:

```text
performance_provenance.available
performance_provenance.policy = warning_provenance_only
performance_provenance.forced_exclusion = false
performance_provenance.score_penalty_applied = false
performance_provenance.records
performance_provenance.summary
performance_provenance.interpretation_confidence_notes
```

## 6. 범위 (Scope)

지원:

```text
- Full-sequence fallback
- 세트 단위 및 반복 단위 annotation
- baseline / idle / rep / rest / transition / excluded 구간
- 운동 컨텍스트 전파
- 수동 phase 라벨 보존
- 촬영 및 수행 provenance 보존
- runner report용 performance/failure provenance 요약
```

범위 외:

```text
- rep/phase 경계 자동 또는 반자동 추정
- segmentation failure-point 검출
- 카메라 각도 보정 또는 좌표 재투영
- 촬영 조건 불일치만으로 강제 제외
- count 또는 failure metadata만으로 점수 감점
- 좌표 수정
```

## 7. 코드 매핑 (Code Mapping)

```text
src/movement/stages/annotation.py
    ANNOTATION_REQUIRED_COLUMNS / ANNOTATION_OPTIONAL_COLUMNS
    VALID_SEGMENT_TYPES / ANNOTATION_OUTPUT_COLUMNS
    load_annotation_csv()
    validate_annotation()
    apply_annotation()
    summarize_performance_provenance()

tests/test_annotation_metadata.py
```
