# 국민체조 상세 해석 배경 (Korean National Gymnastics Rationale)

**문서 버전:** 0.1.4
**최종 갱신:** 2026-07-14
**영문 동기화:** `docs_eng/clinical/exercises/korean_national_gymnastics.md`는 동일 버전의 영문 번역본이다.

본 문서는 통상적으로 알려진 국민체조 sequence와 이를 draft multi-block exercise-session 예시로
표현하는 방식을 요약한다. 진단 기준도 아니고, 건강 효과 주장도 아니며, 코드 명세도 아니다.

관련 문서:

- 운동 세션 YAML: [korean_national_gymnastics.yaml](../../../data/definitions/exercise_sessions/korean_national_gymnastics.yaml)
- 종목별 운동 YAML: `data/definitions/exercises/korean_national_gymnastics_*.yaml`
- indexed 종목별 분석 프로파일: `data/definitions/analysis_profiles/korean_national_gymnastics.yaml`
- 공유 촬영 프로토콜: `data/protocols/camera/korean_national_gymnastics.yaml`
- 참고 출처: [위키백과, 국민체조](https://ko.wikipedia.org/wiki/%EA%B5%AD%EB%AF%BC%EC%B2%B4%EC%A1%B0), 2026-07-14 확인

---

## 1. 연구 내 역할 (Study Role)

국민체조는 multi-block sequence 예시로 사용한다. 본 프로젝트에서의 역할은 방법론적이다.
여러 개의 검토된 운동 정의를 하나의 순서 있는 session으로 조합할 수 있는지 확인하며, 별도의
"혼합형 운동" category나 stage-level hardcoded branch를 만들기 위한 예시가 아니다.

운동 선택 자체가 framework의 범위를 정의하지 않는다. 같은 분석 구조는 exercise definition,
analysis profile, camera protocol, performance protocol, feature-availability policy, scoring
policy에 의해 구동되어야 한다.

## 2. 통상 Sequence 맥락 (Conventional Sequence Context)

통상적으로 설명되는 국민체조는 1977년부터 대한민국에서 보급된 12개 동작의 도수체조 sequence로,
음악과 구령에 맞추어 수행되는 것으로 알려져 있다. 공개된 순서에는 12개 본동작 전에
준비 동작, 보통 제자리걷기로 설명되는 구간도 포함된다.

현재 프로젝트에서는 준비 동작을 분석 block이 아니라 setup/reference context로 둔다. 데이터 취득과
분석은 모두 되풀이 구간부터 시작하며, 숨쉬기부터 뜀뛰기까지의 첫 진행은 이 프로젝트 session에
포함하지 않는다. 실행 가능한 draft session은 아래 current-analysis column의 12개 block 순서를
따른다.

| 통상 순서 | Section ID | 한글 종목명 | 통상 동작 cue | 현재 분석 상태 |
|---|---|---|---|---|
| 0 | setup_reference | 준비 | 제자리걷기 | setup only; session block으로 취득/분석하지 않음 |
| 1 | breathing_start | 숨쉬기 | 팔을 앞으로 들어 옆으로 내리며 숨쉬기 | analysis block 01 |
| 2 | leg | 다리운동 | 무릎 굽혀 펴기 | analysis block 02 |
| 3 | arm | 팔운동 | 팔을 들고 흔들며 앞뒤로 휘돌리기 | analysis block 03 |
| 4 | neck | 목운동 | 목 휘돌리기 | analysis block 04 |
| 5 | chest | 가슴운동 | 가슴 젖히기 | analysis block 05 |
| 6 | side | 옆구리운동 | 몸을 좌우로 굽혀 펴기 | analysis block 06 |
| 7 | back_abdomen | 등배운동 | 몸을 앞으로 굽히고 뒤로 젖히기 | analysis block 07 |
| 8 | trunk | 몸통운동 | 몸통을 좌우로 돌려 틀기 | analysis block 08 |
| 9 | whole_body | 온몸운동 | 노젓기 또는 그물매기 형태의 전신 동작 | analysis block 09 |
| 10 | jumping | 뜀뛰기 | 뜀뛰기 구간 | analysis block 10 |
| 11 | limbs | 팔다리운동 | 팔을 흔들며 무릎을 굽혀 펴고 한 발 들기 | analysis block 11 |
| 12 | breathing_cooldown | 숨고르기 | 팔을 들어 숨 고르기 | analysis block 12 |

위 표는 통상 section label과 넓은 동작 cue만 기록한다. 최종 segmentation, threshold, 점수화
가능 여부를 정의하지 않는다.

## 3. 실행 컨텍스트 (Execution Context)

| Item | Current setting | Interpretation intent |
|---|---|---|
| Session type | 12개 취득/분석 대상 section exercise definition의 ordered composition | 되풀이 구간 순서와 section provenance 검증 |
| Classification | standing, mostly bilateral, multi-plane calisthenic sequence | section별 movement identity 보존 |
| Segmentation | section/event model pending | 모든 section을 squat-like repetition logic에 억지로 맞추지 않기 |
| Performance | 되풀이 구간 취득/분석 session, section별 `repeat_count: 1` | 운동량 처방보다 조합 구조를 보여주는 예시 |
| Rest | draft session에서 `rest_between_blocks_s: 0` | 기본값은 연속 수행 routine |
| Camera | Z1, H2 | 정면 허리높이 전신 coverage |
| Biomech focus | 상대 관절/분절 움직임, timing, symmetry, stability | 절대 force/torque 또는 임상 outcome 추론 금지 |

실행 기준은 YAML이다. 이 문서는 draft가 필요한 이유와 다음 검토 대상을 설명한다.

Section exercise YAML은 하나의 camera protocol과 하나의 indexed analysis-profile file을 공유한다.
연속 촬영 중 camera setting은 변하지 않고, profile file 맨 앞의 `index`가 목차 역할을 하며
section별 analysis entry는 `profiles` 아래에 따로 유지된다.

## 4. 관찰 대상 (Observation Targets)

```text
section order                 12개 취득/분석 block의 고정 진행 순서
section boundary timing        section별 시작/종료 일관성
tempo and smoothness           section 내/section 간 rhythm continuity
bilateral upper-limb symmetry  arm path와 range의 좌우 일관성
trunk centerline control       lateral bend, rotation, forward/back extension
lower-limb support pattern     knee bend/extension, one-foot lift, jumping rhythm
whole-body coordination        상·하지 동작의 동기화
```

위 항목은 후보 관찰 대상이다. Pipeline 문서, section별 analysis profile, 테스트에서 단위,
confidence 처리, availability rule이 정의된 뒤에만 계산 feature가 된다.

## 5. 후보 Movement-Quality Pattern

| Pattern | Interpretation direction | Detectability | Status |
|---|---|---|---|
| section order error | 기대 sequence와 다른 순서로 수행 | section annotation이 있으면 높음 | review candidate |
| incomplete section transition | section boundary 또는 동작 cue가 누락 | 중간; annotation 또는 event model 필요 | review candidate |
| asymmetric arm path | 좌우 상지 range 또는 path 불일치 | 정면 view에서 중간-높음 | review candidate |
| excessive trunk bias | 지속적인 lateral, rotational, forward/back deviation | 중간; section 의존 | review candidate |
| unstable support | 의도된 cue 밖의 foot repositioning 또는 support consistency 저하 | 중간 | review candidate |
| jump rhythm inconsistency | 불규칙한 jump timing 또는 landing pattern | 중간; event model 필요 | review candidate |
| camera-facing direction change | 기대 정면 view에서 벗어난 몸통 방향 전환 | metadata/video review가 있으면 높음 | control/limitation factor |
| low landmark confidence in neck or arms | pose uncertainty로 section 해석 제한 | 중간 | interpretation-limitation factor |

위 용어는 movement-quality proxy와 data-quality limitation이지 진단이 아니다.

## 6. View 및 품질 제한 (View And Quality Limits)

현재 draft의 권장 촬영은 정면 view(`Z1`)와 허리높이(`H2`)다. 이 조건은 전신 coverage,
좌우 비교, arm-path review, 큰 frontal trunk movement 확인에 적합하다.

정면 view는 depth-sensitive sagittal interpretation에는 약하다. 특히 몸을 앞으로/뒤로 굽히는
동작과 일부 jumping/landing 세부 정보는 section별 feature-availability policy를 검토하기 전까지
low-confidence 또는 report-only로 두는 것이 적절하다.

목운동도 현재 pose landmark의 제약을 받는다. Head/shoulder landmark로 coarse movement review는
가능할 수 있지만, 추가 validation 없이 자세한 cervical range-of-motion 주장을 하면 안 된다.

## 7. 개발 경계 (Development Boundary)

국민체조를 canonical runtime 예시로 승격하기 전에:

```text
1. section을 하나씩 검토하며 placeholder phase/event model을 교체한다.
2. 필요한 section에 count unit 또는 event label을 정의한다.
3. section 수행 기대치가 검토된 뒤 performance protocol file을 추가한다.
4. 현재 Z1/H2 draft를 넘어 camera view-metric reliability를 확장한다.
5. 점수를 활성화하기 전에 feature availability와 scoring eligibility를 정의한다.
6. 승격된 section model마다 테스트를 추가한다.
```

그 전까지 국민체조는 유용한 composition 예시이자 구조화된 authoring target이지, 최종 점수화
운동이 아니다.
