# 03. 어노테이션 및 세그멘테이션 (Annotation & Segmentation)

**문서 버전:** 1.1.0
**최종 갱신:** 2026-05-07
**버전 규칙:** Semantic Versioning 2.0.0 (`MAJOR.MINOR.PATCH`)
**영문 동기화:** `docs_eng/pipeline/03_annotation_and_segmentation.md`는 동일 버전의 영문 번역본이다.

본 문서는 파이프라인 ② Annotation과 ⑥ Phase Segmentation의 경계 및 실패 처리 정책을
정의한다. ② Annotation은 사용자가 준비한 수동 어노테이션 CSV를 포즈 데이터프레임에
병합한다. ⑥ Phase Segmentation은 관절 움직임을 추적하여 rep/phase 경계를 반자동으로
분리하고, 자동 인식이 불명확한 지점은 실패 지점으로 기록한 뒤 수동 개입으로 확정한다.

두 단계 모두 프레임을 삭제하거나 좌표를 수정하지 않는다.

---

## 1. 파이프라인 위치 (Pipeline Position)

```text
Pose CSV
→ ① Validation
→ ② Annotation             ← 수동 어노테이션 병합
→ ③ Exercise Definition
→ ④ Preprocessing
→ ⑤ Normalization
→ ⑥ Phase Segmentation     ← rep/phase 반자동 분할 + 실패 지점 기록
→ ⑦ Motion Attribution
→ 후속 단계
```

② 단계는 ③ 이전에 실행된다. 여기서 선언된 `exercise_type`이 어떤 운동 YAML을 로드할지
식별하기 때문이다.

## 2. ② Annotation 출력 칼럼 (Annotation Output Columns)

```text
use_for_analysis    bool      분석에 포함할지 여부
segment_type        str       full_sequence | baseline | idle | rep | rest | transition | excluded
set_id              Int64     nullable
rep_id              Int64     nullable
phase               object    nullable (②에서는 기본적으로 미채움)
exercise_type       str       운동 정의 YAML 식별자
pattern             str       bilateral | alternating
starting_side       str       left | right (좌·우 교대 운동에 한함)
```

`exercise_type`은 ③ 운동 정의 로딩을 구동한다.
`pattern`과 `starting_side`는 ④ 전처리의 좌·우 스왑(swap) 검출 및 ⑦ 모션 어트리뷰션을 구동한다.

## 3. ⑥ Phase Segmentation 출력 칼럼 (Phase Segmentation Output Columns)

⑥은 ②에서 예약한 `phase` 칼럼을 채우고, 실패 또는 수동 보정 여부를 추적하기 위한
메타데이터를 추가한다.

```text
phase                    object    Descent | Ascent | Bottom_Hold | Lift | Tap | Return | NA
segmentation_status      str       not_run | success | failed | manual_override | skipped
segmentation_source      str       annotation | semi_auto | manual_override | fallback
segmentation_failure_id  str       nullable; 실패 지점 리포트와 연결되는 식별자
```

## 4. 어노테이션 계층 (Annotation Hierarchy)

```text
recording
└─ set          동일 운동의 연속된 반복 묶음
   └─ rep       1회의 완전한 동작 사이클
      └─ phase  반복 내 하위 구간
```

## 5. segment_type 값 (segment_type Values)

```text
full_sequence   어노테이션 파일이 없을 때의 기본값
baseline        동작 시작 전의 안정된 직립 자세
idle            대기 또는 비운동 구간
rep             1회 완전한 반복
rest            세트 간 휴식
transition      특정 반복에 귀속되지 않는 구간
excluded        명시적으로 무효 처리한 구간
```

## 6. 어노테이션 파일 포맷 (Annotation File Format)

최소 필수 칼럼:

```text
segment_type, set_id, rep_id, start_frame, end_frame, use_for_analysis
```

선택 칼럼:

```text
exercise_type, pattern, starting_side, phase, note
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

## 7. 어노테이션 미제공 폴백 (No-Annotation Fallback)

어노테이션 파일이 제공되지 않아도 ②는 실패하지 않는다. 적용되는 기본값:

```text
use_for_analysis = True  (전 프레임)
segment_type     = full_sequence
set_id           = None
rep_id           = None
phase            = None
exercise_type    = None   → ③ 단계는 generic 폴백 정의를 로드
pattern          = bilateral
starting_side    = None
```

리포트는 `annotation_provided = False`로 기록된다.

## 8. 어노테이션이 제공된 경우 (When Annotation is Provided)

```text
1. 모든 프레임을 use_for_analysis = False로 초기화한다.
2. 어노테이션 파일에서 선언된 구간에 대해 use_for_analysis 값을 적용한다.
3. 어떤 어노테이션 구간에도 포함되지 않는 프레임은 분석에서 제외된다.
4. 운동 컨텍스트 칼럼(exercise_type, pattern, starting_side)은
   해당 구간 내의 모든 프레임으로 전파된다.
```

## 9. ⑥ Phase Segmentation 전략 (Phase Segmentation Strategy)

⑥은 운동 YAML의 기준 랜드마크, 기준 축, 기대 phase 순서를 사용해 rep/phase 경계를
반자동으로 추정한다. 자동 추정은 다음 중 하나라도 불명확하면 성공으로 간주하지 않는다.

```text
- 기준 랜드마크의 가시성이 부족함
- 기준 축 움직임의 ROM이 너무 작음
- 후보 경계가 없거나 여러 개라 하나로 결정할 수 없음
- 경계 순서가 운동 YAML의 phase 순서와 맞지 않음
- 수동으로 지정된 경계와 자동 후보가 허용 오차 밖에서 충돌함
```

이 경우 ⑥은 해당 프레임 또는 프레임 구간을 `SegmentationFailurePoint`로 기록한다.
실패 지점은 보간하거나 성공으로 간주하지 않는다.

## 10. 분할 실패 지점 기록 (Segmentation Failure Point Record)

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

## 11. 실패 수준별 파이프라인 처리 (Pipeline Handling by Failure Level)

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

수동 개입으로 실패 지점이 해결되면 `segmentation_status = manual_override`,
`segmentation_source = manual_override`로 기록한다. 수동 보정값은 좌표를 수정하지 않고
경계/라벨 메타데이터만 확정한다.

## 12. 중첩 정책 (Overlap Policy)

중첩된 어노테이션 구간 또는 서로 충돌하는 수동 보정 구간은 오류로 처리된다. 본 단계는
오류를 발생시키거나 리포트에 실패를 기록한다 (조용히 덮어쓰지 않는다).

## 13. 프레임 인덱스 규약 (Frame Index Convention)

원본 `frame` 칼럼 값은 보존된다. 본 문서의 어느 단계도 프레임을 재번호 매기지 않는다.

## 14. 현재 범위 (Current Scope)

지원 항목:

```text
- 전 시퀀스 폴백(어노테이션 파일 없음)
- 세트 단위 및 반복 단위 어노테이션
- idle / baseline / rest / excluded 구간 표시
- use_for_analysis 마스크
- 운동 컨텍스트 칼럼 (exercise_type, pattern, starting_side)
- ⑥ Phase Segmentation의 반자동 rep/phase 분할 설계
- 분할 실패 지점 기록 및 실패 수준별 파이프라인 처리 정책
```

범위 외 항목:

```text
- 실패 지점 검토 없는 완전 자동 분할
- 좌표값 수정
- 분할 실패를 임의 보간하여 성공으로 처리하는 정책
```
