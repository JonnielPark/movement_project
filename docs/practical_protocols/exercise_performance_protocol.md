# 대상 운동별 수행 프로토콜 (Exercise Performance Protocol per Exercise)

**문서 버전:** 1.1.0
**최종 갱신:** 2026-05-21
**영문 동기화:** [docs_eng/practical_protocols/exercise_performance_protocol.md](../../docs_eng/practical_protocols/exercise_performance_protocol.md)는 동일 내용의 영문 번역본이다.

본 문서는 데이터 취득을 위한 표준 수행 지침을 정의한다.
"표준 수행"은 단안 포즈 취득 목표를 재현 가능하게 만드는 기준이며, 임상적 교정 기준이 아니다.
동일한 failure-point 및 provenance 규칙은 향후 추가 운동에도 적용한다.

카메라 배치는 [camera_protocol.md](camera_protocol.md)를 따른다. 상세 생체역학적 근거와
scoring-candidate/control-factor 구분은 `docs/clinical/exercises/`에 둔다.

---

## 1. 공통 규칙 (Common Rules)

```text
default pilot unit          하루 1운동, 운동별 3세트, 세트당 10 count
recording structure         가능하면 세트별 one take
rest                        세트 간 2-3분; 운동 종류 간 15-20분
clothing                    관절이 보이도록 착용; landmark를 가리는 헐렁한 옷 회피
environment                 거울 반사나 다른 사람이 없는 공간
arm motion                  팔 반동이 분석 대상이 아니면 손 고정
participant safety          통증 또는 부상 위험 시 중단
metadata                    actual count와 performance note 기록
```

카메라를 의식해 인위적으로 더 깔끔한 반복을 수행하지 않는다. 자세가 무너지면 통증 없는 범위에서만
계속하고, 실제로 일어난 일을 기록한다.

## 2. Failure-Point 정책 (Failure-Point Policy)

모든 운동은 performance failure-point 기록을 지원한다. Performance failure point는 피험자가
해당 운동의 핵심 조건을 더 이상 일관되게 유지하지 못하는 첫 rep/frame 또는 recording endpoint이다:

```text
baseline posture
range of motion
rhythm
base of support
left-right sequence
```

이 표지는 취득/annotation provenance이다. 근력, 피로, 질환을 진단하지 않으며, 자동 점수 감점
규칙도 아니다.

분석을 방해하는 수행 패턴은 note에 기록한다. 관절 포인트 시계열에서 반복 가능하게 보이는 패턴은
scoring candidate가 될 수 있고, 포즈 데이터만으로 안정적으로 분리하기 어려운 패턴은 취득 통제 또는
해석 제한 요인으로 남긴다.

## 3. 운동별 프로토콜 (Per-Exercise Protocols)

| Exercise | Image | Camera | Count target | Participant cue | Analysis-disrupting patterns |
|---|---|---|---|---|---|
| Squat | `assets/exercise_squat.png` | Z2/Z8, H2 | 10 reps | 발 어깨너비; 손 고정; 엉덩이를 뒤로 빼며 허벅지 수평에 가깝게 내려갔다가 일어남. | arm swing assist; heel lift/foot repositioning; knees inward/outward; inconsistent depth; excessive trunk folding |
| Lunge | `assets/exercise_lunge.png` | Z3/Z7, H2 | 앞발별 5 reps | 한 발을 앞으로; 손은 pelvis/waist; 양 무릎이 약 90도에 가깝게 수직 하강; 몸을 돌리지 않고 앞발 교대. | changing step length; arm swing/trunk extension assist; excessive trunk flexion; body turn during side switch; unstable foot contact |
| Pike push-up | `assets/exercise_pike_pushup.png` | Z3/Z7, H1 | 10 reps 또는 clean maximum | 엉덩이를 높인 inverted V; 정수리를 손 사이 바닥 쪽으로 내림; 어깨로 밀어 올라옴. | hips dropping; head forward beyond hands; excessive elbow flare; shallow/inconsistent depth; hand/foot repositioning |
| Plank shoulder tap | `assets/exercise_plank_shoulder_tap.png` | Z2/Z8, H1 | 10 protocol cycles | high plank; trunk/hips 고정; 반대쪽 어깨 tap; left+right tap = 1 protocol cycle. | pelvic rotation/shift; hips too high/low; hand/foot repositioning; wrong side order; hand lift without tap |

상세 근거:

```text
squat                ../clinical/exercises/squat.md
lunge                ../clinical/exercises/lunge.md
pike_pushup          ../clinical/exercises/pike_pushup.md
plank_shoulder_tap   ../clinical/exercises/plank_shoulder_tap.md
```

## 4. 파이프라인 사용 (Pipeline Use)

Performance protocol field는 split YAML로 표현한다:

```text
data/protocols/performance/<exercise_id>.yaml
```

Annotation은 다음을 기록할 수 있다:

```text
performance_protocol_status
actual_rep_count
failure_point_frame
failure_rep_id
failure_reason
performance_note
rep_side_sequence
side_block_size
rep_unit
protocol_cycle_id
```

이 field들은 report, ⑨ Feature Extraction role context, feature availability, interpretation-confidence note를
위한 provenance이다. 그 자체로 자동 movement-quality penalty가 되지 않는다.
