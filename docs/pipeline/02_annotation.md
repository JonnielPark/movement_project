# 02. 어노테이션 (Annotation)

**문서 버전:** 1.1.5
**최종 갱신:** 2026-05-10
**영문 동기화:** `docs_eng/pipeline/02_annotation.md`는 동일 버전의 영문 번역본이다.

파이프라인 단계 ②. 사용자가 준비한 어노테이션 CSV의 구간(segment) 메타데이터를 포즈
데이터프레임에 병합한다. 본 단계는 수동 메타데이터와 촬영 provenance를 병합하고 전파하는
단계이며, rep/phase 경계를 자동 또는 반자동으로 추정하지 않는다. rep/phase 경계 추정과
실패 지점 기록은 [06_segmentation.md](06_segmentation.md)에서 담당한다.

본 단계는 프레임을 삭제하거나 좌표를 수정하지 않는다.

---

## 1. 파이프라인 위치 (Pipeline Position)

```text
Pose CSV
→ ① Validation
→ ② Annotation             ← 본 단계
→ ③ Exercise Definition
→ ④ Preprocessing
→ ⑤ Normalization
→ ⑥ Segmentation
→ ⑦ Motion Attribution
→ 후속 단계
```

② 단계는 ③ 이전에 실행된다. 여기서 선언된 `exercise_type`이 어떤 운동 YAML을 로드할지
식별하기 때문이다.

## 2. 출력 칼럼 (Output Columns)

```text
use_for_analysis    bool      분석에 포함할지 여부
segment_type        str       full_sequence | baseline | idle | rep | rest | transition | excluded
set_id              Int64     nullable
rep_id              Int64     nullable
phase               object    nullable; 수동으로 제공된 phase 라벨이 있으면 보존
note                str       nullable; 구간별 자유 기록
exercise_type       str       운동 정의 YAML 식별자
pattern             str       bilateral | alternating
starting_side       str       left | right (좌·우 교대 운동에 한함)
session_id          str       nullable; 여러 recording을 하나의 세션으로 묶는 식별자
recording_id        str       nullable; 원테이크 촬영 파일 식별자
set_index           Int64     nullable; 세션 내 세트 순번
camera_zone         str       nullable; Z1 | Z2 | Z3 | Z4 | Z5 | Z6 | Z7 | Z8 | unknown
camera_height_level str       nullable; H1 | H2 | H3 | unknown
reference_mat_used  bool      nullable; 기준 매트 앵커 사용 여부
filming_protocol_status str   recommended | out_of_zone | no_anchor | unknown
performance_protocol_status str nullable; completed | partial | stopped_at_failure_point | unknown
actual_rep_count    Int64     nullable; 실제 완료한 protocol count
failure_point_frame Int64     nullable; 수행 실패 지점 또는 중단 지점 프레임
failure_rep_id      Int64     nullable; 수행 실패가 처음 확인된 rep_id
failure_reason      str       nullable; posture_breakdown | inconsistent_rom | side_order_error | pain_or_risk | participant_stop | unknown
performance_note    str       nullable; 수행 품질 또는 중단 사유에 대한 자유 기록
rep_side_sequence   str       nullable; 실제 관찰된 좌우 순서, 예: right,left,right,left 또는 same_side_block_then_switch
side_block_size     Int64     nullable; 해당될 경우 실제 관찰된 같은 측 블록 크기
rep_unit            str       nullable; 관찰된 세그먼트 단위, 예: repetition | tap
protocol_cycle_id   Int64     nullable; 원자 반복을 묶는 피험자 안내 기준 protocol cycle id
```

`exercise_type`은 ③ 운동 정의 로딩을 구동한다.
`pattern`과 `starting_side`는 ④ 전처리의 좌·우 스왑(swap) 검출 및 ⑦ 모션 어트리뷰션을 구동한다.
`phase` 값이 수동으로 제공된 경우 ②는 이를 보존하지만, 라벨 확정 여부와 실패 처리는
⑥ Segmentation에서 판단한다.
촬영 provenance 칼럼은 좌표를 보정하거나 데이터를 제외하는 데 사용하지 않는다. 권장 촬영
조건과의 일치 여부는 결과 리포트나 시각화에서 경고 정보로 표시한다.
수행 provenance 칼럼은 실제 촬영에서 목표 횟수, 수행 실패 지점, 중단 사유가 어떻게 나타났는지
기록하기 위한 값이다. 이 값은 근력·피로를 진단하지 않으며, 자동 제외 규칙으로 사용하지 않는다.
관찰된 count/side-sequence 칼럼(`rep_side_sequence`, `side_block_size`, `rep_unit`,
`protocol_cycle_id`)은 이후 report와 ⑦ Motion Attribution에서 ③ `performance_protocol`과
비교한다. 불일치는 자동 프레임 제외가 아니라 warning/provenance로 남긴다.

A5는 performance/failure provenance가 runner/reporting 출력에서 소비되는 방식을 공식화한다.
위의 프레임 단위 칼럼은 상세 기록으로 유지하고, annotation report는 downstream visualization
또는 interpretation layer가 전체 pose dataframe을 다시 훑지 않고 읽을 수 있는 set-level 요약을
추가로 노출한다.

```text
performance_provenance.available                 bool
performance_provenance.policy                    warning_provenance_only
performance_provenance.forced_exclusion          false
performance_provenance.score_penalty_applied     false
performance_provenance.records                   list[dict]
performance_provenance.summary                   dict
performance_provenance.interpretation_confidence_notes list[str]
```

각 record는 다음을 포함한다.

```text
segment_type, set_id, rep_id, start_frame, end_frame
performance_protocol_status
actual_rep_count
failure_point_frame
failure_rep_id
failure_reason
performance_note
source_fields
```

규칙:

```text
- Performance metadata가 없거나 부분적으로만 있어도 annotation은 실패하지 않는다.
- 실제 반복 수가 낮다는 이유만으로 movement-quality score를 직접 감점하지 않는다.
- 수행 실패 지점은 segmentation failure point가 아니다. 이는 피험자가 protocol task를
  더 이상 유지하지 못하기 시작한 위치를 기록하는 표지다.
- 기본 동작은 warning/provenance only이다. downstream scoring 또는 figure caption에서
  note를 표시할 수 있지만, ②는 프레임을 제외하지 않고 ⑥은 이 metadata만으로 점수를 감점하지 않는다.
```

## 3. 어노테이션 계층 (Annotation Hierarchy)

```text
recording
└─ set          동일 운동의 연속된 반복 묶음
   └─ rep       1회의 완전한 동작 사이클
      └─ phase  반복 내 하위 구간 (선택; ⑥에서 확정)
```

## 4. segment_type 값 (segment_type Values)

```text
full_sequence   어노테이션 파일이 없을 때의 기본값
baseline        동작 시작 전의 안정된 직립 자세
idle            대기 또는 비운동 구간
rep             1회 완전한 반복
rest            세트 간 휴식
transition      특정 반복에 귀속되지 않는 구간
excluded        명시적으로 무효 처리한 구간
```

## 5. 어노테이션 파일 포맷 (Annotation File Format)

최소 필수 칼럼:

```text
segment_type, set_id, rep_id, start_frame, end_frame, use_for_analysis
```

선택 칼럼:

```text
exercise_type, pattern, starting_side, phase, note,
session_id, recording_id, set_index,
camera_zone, camera_height_level, reference_mat_used, filming_protocol_status,
performance_protocol_status, actual_rep_count, failure_point_frame,
failure_rep_id, failure_reason, performance_note,
rep_side_sequence, side_block_size, rep_unit, protocol_cycle_id
```

### 예: 단일 세트, 3 반복

```csv
segment_type,set_id,rep_id,start_frame,end_frame,use_for_analysis,exercise_type,pattern
baseline,,,20,60,false,squat,bilateral
rep,1,1,85,160,true,squat,bilateral
rep,1,2,170,245,true,squat,bilateral
rep,1,3,255,330,true,squat,bilateral
idle,,,331,370,false,squat,bilateral
```

### 예: 두 세트

```csv
segment_type,set_id,rep_id,start_frame,end_frame,use_for_analysis,exercise_type,pattern
baseline,,,20,60,false,squat,bilateral
rep,1,1,85,160,true,squat,bilateral
rep,1,2,170,245,true,squat,bilateral
rep,1,3,255,330,true,squat,bilateral
rest,1,,331,430,false,squat,bilateral
rep,2,1,450,525,true,squat,bilateral
rep,2,2,535,610,true,squat,bilateral
rep,2,3,620,700,true,squat,bilateral
idle,,,701,760,false,squat,bilateral
```

### 예: 좌우 교대 운동 (플랭크 숄더탭)

`starting_side = right`은 rep 1 → 우측 활성, rep 2 → 좌측 활성, 이후 교대 패턴을 의미한다.

```csv
segment_type,set_id,rep_id,start_frame,end_frame,use_for_analysis,exercise_type,pattern,starting_side
baseline,,,0,40,false,plank_shoulder_tap,alternating,right
rep,1,1,50,100,true,plank_shoulder_tap,alternating,right
rep,1,2,110,160,true,plank_shoulder_tap,alternating,right
rep,1,3,170,220,true,plank_shoulder_tap,alternating,right
rep,1,4,230,280,true,plank_shoulder_tap,alternating,right
idle,,,281,320,false,plank_shoulder_tap,alternating,right
```

## 6. 어노테이션 미제공 폴백 (No-Annotation Fallback)

어노테이션 파일이 제공되지 않아도 본 단계는 실패하지 않는다. 적용되는 기본값:

```text
use_for_analysis = True  (전 프레임)
segment_type     = full_sequence
set_id           = None
rep_id           = None
phase            = None
exercise_type    = None   → ③ 단계는 generic 폴백 정의를 로드
pattern          = bilateral
starting_side    = None
session_id       = None
recording_id     = None
set_index        = None
camera_zone      = unknown
camera_height_level = unknown
reference_mat_used = None
filming_protocol_status = unknown
```

리포트는 `annotation_provided = False`로 기록된다.
또한 `performance_provenance.available = False`를 기록한다. annotation metadata가 없다는
이유만으로 수행 실패를 추론하지 않는다.

## 7. 어노테이션이 제공된 경우 (When Annotation is Provided)

```text
1. 모든 프레임을 use_for_analysis = False로 초기화한다.
2. 어노테이션 파일에서 선언된 구간에 대해 use_for_analysis 값을 적용한다.
3. 어떤 어노테이션 구간에도 포함되지 않는 프레임은 분석에서 제외된다.
4. 운동 컨텍스트 칼럼(exercise_type, pattern, starting_side)은
   해당 구간 내의 모든 프레임으로 전파된다.
5. 촬영 provenance 칼럼(session_id, camera_zone 등)은 해당 recording 또는 구간 내의 모든
   프레임으로 전파된다.
```

## 8. 중첩 정책 (Overlap Policy)

중첩된 어노테이션 구간은 오류로 처리된다. 본 단계는 오류를 발생시키거나 어노테이션 리포트에
실패를 기록한다 (조용히 덮어쓰지 않는다).

## 9. 프레임 인덱스 규약 (Frame Index Convention)

원본 `frame` 칼럼 값은 보존된다. 본 단계는 프레임을 재번호 매기지 않는다.

## 10. 현재 범위 (Current Scope)

지원 항목:

```text
- 전 시퀀스 폴백(어노테이션 파일 없음)
- 세트 단위 및 반복 단위 어노테이션
- idle / baseline / rest / excluded 구간 표시
- use_for_analysis 마스크
- 운동 컨텍스트 칼럼 (exercise_type, pattern, starting_side)
- 수동으로 제공된 phase 라벨 보존
- 촬영 provenance 칼럼 보존 (session_id, recording_id, set_index, camera_zone, camera_height_level)
- 관찰된 protocol metadata 보존 (rep_side_sequence, side_block_size, rep_unit, protocol_cycle_id)
- Performance/failure provenance를 annotation report로 요약
```

범위 외 항목:

```text
- rep/phase 경계 자동 또는 반자동 추정
- 분할 실패 지점 기록
- 카메라 각도 보정 또는 좌표 재투영
- 촬영 조건 불일치 데이터의 강제 거부
- 낮은 실제 반복 수 또는 failure metadata만으로 자동 점수 감점
- 좌표값 수정
```
