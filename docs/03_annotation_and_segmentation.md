# 03. 어노테이션 및 세그멘테이션 (Annotation & Segmentation)

**문서 버전:** 1.0.0  
**최종 갱신:** 2026-05-06  
**버전 규칙:** Semantic Versioning 2.0.0 (`MAJOR.MINOR.PATCH`)  
**영문 동기화:** `docs_eng/03_annotation_and_segmentation.md`는 동일 버전의 영문 번역본이다.

파이프라인 단계 ②. 사전에 라벨링된 구간(segment) 메타데이터를 포즈 데이터프레임에 병합한다.
자동 반복 검출(automatic rep detection)을 수행하지 않으며, 프레임 삭제·좌표 수정도 하지 않는다.

---

## 1. 파이프라인 위치 (Pipeline Position)

```text
Pose CSV
→ ① Validation
→ ② Annotation             ← 본 단계
→ ③ Exercise Definition
→ ④ Preprocessing
→ ⑤ Normalization
→ ⑥ Phase Segmentation
→ ⑦ Motion Attribution
→ 후속 단계
```

② 단계는 ③ 이전에 실행된다. 여기서 선언된 `exercise_type`이 어떤 운동 YAML을 로드할지 식별하기 때문이다.

## 2. 추가되는 출력 칼럼 (Output Columns Added)

```text
use_for_analysis    bool      분석에 포함할지 여부
segment_type        str       full_sequence | baseline | idle | rep | rest | transition | excluded
set_id              Int64     nullable
rep_id              Int64     nullable
phase               object    nullable (구간 단위 분석용 예약, 본 단계에서는 미채움)
exercise_type       str       운동 정의 YAML 식별자
pattern             str       bilateral | alternating
starting_side       str       left | right (좌·우 교대 운동에 한함)
```

`exercise_type`은 ③ 운동 정의 로딩을 구동한다.
`pattern`과 `starting_side`는 ④ 전처리의 좌·우 스왑(swap) 검출 및 ⑦ 모션 어트리뷰션을 구동한다.

## 3. 어노테이션 계층 (Annotation Hierarchy)

```text
recording
└─ set          동일 운동의 연속된 반복 묶음
   └─ rep       1회의 완전한 동작 사이클
      └─ phase  반복 내 하위 구간 (예약; 본 단계에서는 분석에 사용되지 않음)
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
```

리포트는 `annotation_provided = False`로 기록된다.

## 7. 어노테이션이 제공된 경우 (When Annotation is Provided)

```text
1. 모든 프레임을 use_for_analysis = False로 초기화한다.
2. 어노테이션 파일에서 선언된 구간에 대해 use_for_analysis 값을 적용한다.
3. 어떤 어노테이션 구간에도 포함되지 않는 프레임은 분석에서 제외된다.
4. 운동 컨텍스트 칼럼(exercise_type, pattern, starting_side)은
   해당 구간 내의 모든 프레임으로 전파된다.
```

## 8. 중첩 정책 (Overlap Policy)

중첩된 어노테이션 구간은 오류로 처리된다. 본 단계는 오류를 발생시키거나 어노테이션 리포트에
실패를 기록한다 (조용히 덮어쓰지 않는다).

## 9. 프레임 인덱스 규약 (Frame Index Convention)

원본 `frame` 칼럼 값은 보존된다. 본 단계는 프레임을 재번호 매기지 않는다.

## 10. 초기 범위 (Initial Scope)

지원 항목:
```text
- 전 시퀀스 폴백(어노테이션 파일 없음)
- 세트 단위 및 반복 단위 어노테이션
- idle / baseline / rest / excluded 구간 표시
- use_for_analysis 마스크
- 운동 컨텍스트 칼럼 (exercise_type, pattern, starting_side)
```

범위 외 항목:
```text
- 자동 분할(automatic segmentation)
- 자동 반복 검출
- 자동 구간 검출
- 구간 단위 분석
```
