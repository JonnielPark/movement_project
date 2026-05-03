# 03. Annotation 및 분석 구간 (Annotation & Segmentation)

본 단계는 분석 대상 구간(set, 반복rep, 수행 단계phase)과 운동 맥락(`exercise_type`, `pattern`, `starting_side`)을 메타데이터로 표시한다. 프레임을 삭제하지 않고, 메타데이터 컬럼만 추가한다.

> 용어는 [`_terminology.md`](_terminology.md)의 단일 정의를 따른다.

---

## 1. 본 단계의 역할

연구계획서의 “annotation 기반 분석 구간 정의”에 해당하는 단계이다. 자동 분할(automatic segmentation)은 본 연구의 1차 기여 항목이 아니며, 사전에 준비한 annotation 파일로 분석 구간을 명시한다. annotation 파일이 없을 경우 시퀀스 전체를 분석 대상으로 사용한다.

본 단계가 추가하는 메타데이터 컬럼:

```text
use_for_analysis    분석 대상 여부 (bool)
segment_type        구간 종류 (rep, baseline, idle, rest, transition, excluded, full_sequence)
set_id              세트 식별자
rep_id              반복 식별자
phase               수행 단계(선택, 향후 확장)
exercise_type       운동 정의 YAML 식별자
pattern             좌우 패턴 (bilateral / alternating)
starting_side       좌우 교번 운동에서 첫 반복의 활성 측
```

`exercise_type` 컬럼은 ③ 운동 정의 로딩 단계가 어떤 YAML 파일을 적재할지 결정한다.

## 2. 분석 단계에서의 위치

```text
Pose CSV
→ ① 데이터 검증
→ ② Annotation 적용              ← 본 단계
→ ③ 운동 정의 로딩
→ ④ 전처리
→ ⑤ 정규화
→ ⑥ 귀속
→ 후속 단계
```

② Annotation이 ③ 운동 정의 로딩보다 먼저 수행되는 이유: annotation에서 선언된 `exercise_type`을 사용해 운동 정의 YAML을 식별하기 위해서이다.

## 3. 분석 구간의 용어 위계

```text
recording                 한 번의 영상 / 한 개의 포즈 CSV
└─ set                    동일 운동을 연속 수행한 묶음
   └─ rep                 한 반복(완전한 동작 한 사이클)
      └─ phase            반복 내부의 의미 있는 구간 (선택)
```

### 3-1. Recording

하나의 녹화 시퀀스. 한 영상은 다음을 포함할 수 있다.

```text
대기 프레임 (idle)
준비 프레임 (preparation)
하나 이상의 set
세트 간 휴식 (rest)
종료 프레임
```

### 3-2. Set

동일 운동을 연속해서 반복한 묶음.

```text
스쿼트 set 1: 10 reps
스쿼트 set 2: 10 reps
스쿼트 set 3: 10 reps
```

### 3-3. Rep (반복)

한 사이클의 완전한 동작. 예: 스쿼트의 한 반복 = 기립 → 하강 → 최저점 → 상승 → 기립.

본 분석 체계의 1차 분석 단위는 rep이다.

### 3-4. Phase (수행 단계)

반복 내부의 의미 있는 구간. 운동 정의의 `phase_model`이 어떤 단계가 기대되는지 선언한다 (예: 저항성 운동의 `eccentric / isometric / concentric`, 과제형 운동의 `setup / shift / tap / return`). 초기 구현은 phase 컬럼을 보존하지만, phase 단위 분석은 향후 확장으로 둔다.

## 4. 초기 구현 범위

본 단계의 초기 구현이 지원하는 항목:

```text
- annotation 파일이 없을 때 시퀀스 전체 사용 (full-sequence fallback)
- 세트 단위 annotation
- 반복 단위 annotation
- idle / baseline / rest / excluded 구간 표시
- use_for_analysis 마스크
- 운동 맥락 컬럼(exercise_type, pattern, starting_side) 선언
```

본 단계가 초기에 다루지 않는 항목:

```text
- 자동 분할 (automatic segmentation)
- 자동 반복 검출
- 자동 phase 검출
- phase 단위 분석
```

## 5. 설계 원칙: 프레임을 삭제하지 않는다

annotation은 프레임을 물리적으로 잘라내지 않는다. 원본 시퀀스를 보존하면서 메타데이터 컬럼만 추가한다. 이로써 다음이 가능해진다.

```text
- 원본 frame 번호 보존
- 시퀀스 전체 시각화
- annotation 반복 갱신
- idle / 무효 프레임의 분석 제외
- ④ 전처리 / ⑥ 귀속 / ⑦ 특징 추출의 운동-인지 처리
- ③ 운동 정의 단계의 exercise_type 기반 YAML 적재
```

## 6. 최소 annotation 컬럼

```text
segment_type
set_id
rep_id
start_frame
end_frame
use_for_analysis
```

선택 컬럼:

```text
exercise_type
phase
note
```

## 7. 운동 맥락 컬럼

annotation 파일은 운동 단위의 맥락 정보를 함께 선언한다.

```text
exercise_type   운동 정의 YAML 식별자
                예: squat | lunge | pike_pushup | plank_shoulder_tap

pattern         기대되는 좌우 패턴
                bilateral | alternating

starting_side   alternating 운동에서 첫 반복의 활성 측
                left | right
                pattern == bilateral 인 경우 무시
```

권장 작성 방식: recording 단위(또는 한 recording에 다수 운동이 있을 경우 set 단위)에서 `segment_type`이 `full_sequence`, `baseline`, 혹은 set-level marker인 행에 한 번 선언한다.

운동 맥락 행 예 (분석에는 사용하지 않고 맥락만 선언):

```csv
segment_type,set_id,rep_id,start_frame,end_frame,use_for_analysis,exercise_type,pattern,starting_side
full_sequence,,,0,800,false,plank_shoulder_tap,alternating,right
```

이들 컬럼이 후속 단계에서 어떻게 사용되는지:

```text
③ 운동 정의 로딩  → exercise_type으로 YAML 식별
④ 전처리          → 좌우 라벨 스왑 검출 활성화 여부 결정
⑥ 귀속            → 검출된 활성 측과 기대 패턴 비교
⑦ 특징 추출       → 운동별 특징 정의 적용
```

`pattern`이 누락되면 후속 단계는 `bilateral`로 가정한다. `exercise_type`이 누락되면 ③ 운동 정의 단계는 generic fallback 정의를 적재한다 ([`04_exercise_definition.md`](04_exercise_definition.md) §“Fallback Behavior”).

## 8. 권장 segment_type 값과 의미

```text
full_sequence   annotation 미제공 시 기본값
baseline        동작 시작 전 안정 자세
idle            대기 또는 비운동 구간
rep             한 반복
rest            세트 간 휴식
transition      특정 반복에 귀속되지 않은 전이
excluded        명시적으로 무효한 구간
```

## 9. 예시: 단일 세트

스쿼트 1세트, 3반복 예:

```csv
segment_type,set_id,rep_id,start_frame,end_frame,use_for_analysis,exercise_type,pattern
baseline,,,20,60,false,squat,bilateral
rep,1,1,85,160,true,squat,bilateral
rep,1,2,170,245,true,squat,bilateral
rep,1,3,255,330,true,squat,bilateral
idle,,,331,370,false,squat,bilateral
```

## 10. 예시: 다중 세트

스쿼트 2세트, 각 3반복 예:

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

## 11. 예시: 좌우 교번 운동 (Plank Shoulder Tap)

각 반복에서 활성 손이 교대된다.

```csv
segment_type,set_id,rep_id,start_frame,end_frame,use_for_analysis,exercise_type,pattern,starting_side
baseline,,,0,40,false,plank_shoulder_tap,alternating,right
rep,1,1,50,100,true,plank_shoulder_tap,alternating,right
rep,1,2,110,160,true,plank_shoulder_tap,alternating,right
rep,1,3,170,220,true,plank_shoulder_tap,alternating,right
rep,1,4,230,280,true,plank_shoulder_tap,alternating,right
idle,,,281,320,false,plank_shoulder_tap,alternating,right
```

`starting_side = right`은 1번째 반복의 활성 손이 우측, 2번째는 좌측, 이후 교번을 의미한다.

## 12. 선택 컬럼: phase

향후 확장을 위해 `phase` 컬럼을 둘 수 있다. 초기 구현에서는 빈 값으로 두어도 된다.

```csv
segment_type,set_id,rep_id,phase,start_frame,end_frame,use_for_analysis
rep,1,1,,85,160,true
```

## 13. annotation 미제공 정책

annotation 파일이 없으면 분석 단계는 실패하지 않는다. 기본값:

```text
use_for_analysis = True (모든 프레임)
segment_type      = full_sequence
set_id            = None
rep_id            = None
phase             = None
exercise_type     = None
pattern           = bilateral
starting_side     = None
```

annotation 보고서에 다음을 기록한다.

```text
annotation_provided = False
policy = use_full_sequence
num_total_frames
num_analysis_frames
```

`exercise_type`이 선언되지 않았으면 ③ 운동 정의 로딩 단계는 generic fallback 정의를 적재하고, 후속 단계의 운동-인지 처리는 운동 무관 모드(generic mode)로 작동한다.

## 14. annotation 제공 정책

annotation 파일이 있을 경우:

```text
1. 모든 프레임을 use_for_analysis = False 로 초기화한다.
2. annotation 파일에 표시된 구간의 use_for_analysis 값을 갱신한다.
3. annotation에 표시되지 않은 프레임은 분석에서 제외된다.
4. 운동 맥락 컬럼은 해당 구간에 속한 모든 프레임으로 전파된다.
```

annotation에 명시되지 않은 idle / 무효 프레임이 우연히 분석에 포함되는 것을 방지한다.

## 15. 구간 중첩 정책

annotation 구간이 중첩되면 오류로 처리한다. 다음은 잘못된 예이다.

```csv
segment_type,set_id,rep_id,start_frame,end_frame,use_for_analysis
rep,1,1,50,120,true
rep,1,2,100,180,true
```

본 단계의 초기 구현은 중첩 구간을 조용히 덮어쓰지 않는다. 오류를 발생시키거나, annotation 검증 보고서에 실패로 기록한다.

## 16. 프레임 인덱스 규약

수동 annotation은 원본 포즈 CSV의 프레임 인덱스를 사용한다. 본 단계는 원본 `frame` 컬럼을 보존한다. 향후 segment-level frame index를 별도 컬럼으로 추가할 수 있으나, 원본 frame 번호를 덮어쓰지 않는다.

## 17. 분석 단계에서의 의의

annotation 파일은 분석 단계 실행 전에 준비한다. 분석 단계 안에서는 ① 데이터 검증 직후에 메타데이터 레이어로 적용되며, 이후 ③ 운동 정의 로딩 단계가 `exercise_type`을 사용해 YAML 정의 객체를 적재한다.

```text
포즈 CSV 적재
→ ① 데이터 검증
→ ② Annotation 적용
→ ③ 운동 정의 로딩
→ ④ 전처리
→ ⑤ 정규화
→ ⑥ 귀속
→ 후속 단계
```

이 순서가 의도된 이유:

- ④ 전처리는 `exercise_type`, `pattern`(및 운동 정의의 `landmarks`/`quality_rules`)을 읽고 운동별 점검(예: 좌우 라벨 스왑 검출)을 활성화할지 결정한다.
- ⑥ 귀속은 반복 경계, 운동 맥락, 운동 정의의 `laterality`를 읽고 각 반복의 활성 측이 기대 패턴과 일치하는지 검증한다.

본 단계의 핵심 출력은 annotation 메타데이터가 부착된 데이터프레임이다.

```text
입력
  포즈 데이터프레임
  선택적 annotation 파일

출력
  annotation 메타데이터 컬럼이 부착된 포즈 데이터프레임
  annotation 보고서
```

## 18. 초기 완료 기준

```text
1. annotation CSV를 적재할 수 있다.
2. 필수 annotation 컬럼이 점검된다.
3. annotation 미제공 시 full-sequence 모드로 폴백한다.
4. annotation 제공 시 use_for_analysis, segment_type, set_id, rep_id, phase 컬럼이 추가된다.
5. 운동 맥락 컬럼(exercise_type, pattern, starting_side)이 적절히 채워진다.
6. 중첩 구간이 검출된다.
7. 원본 frame 번호가 보존된다.
8. annotation 보고서가 반환된다.
```
