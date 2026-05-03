# 07. 귀속 (Motion Attribution)

본 단계는 **반복 단위에서 실제로 움직인 측이 운동 정의가 기대하는 측과 일치하는지**를 확인한다. 단일 비전 환경에서는 ④ 전처리(프레임 단위)의 좌우 라벨 보정만으로 해결되지 않는 사례가 있다. 예를 들어 작용 측 사지가 가려진 동안 정지된 측이 움직인 것처럼 보고되거나, 라벨이 한 프레임이 아니라 반복 전체에 걸쳐 어긋나는 경우다. 이런 사례는 한 반복 전체의 motion energy를 운동의 기대 패턴과 비교해야 식별할 수 있다.

본 단계는 좌표를 수정하지 않는다. 반복 단위 라벨 일관성에 관한 메타데이터만 추가한다.

> 용어는 [`_terminology.md`](_terminology.md)의 단일 정의를 따른다.

---

## 1. 분석 단계에서의 위치

```text
Pose CSV
→ ① 데이터 검증
→ ② Annotation 적용
→ ③ 운동 정의 로딩
→ ④ 전처리
→ ⑤ 정규화
→ ⑥ 귀속                  ← 본 단계
→ ⑦ 특징 추출
```

본 단계가 요구하는 입력:

```text
- 반복 경계 (annotation에서)
- 운동 맥락 (annotation의 exercise_type, pattern, starting_side)
- 운동 정의 (laterality, primary_joints)
- 정규화된 좌표 (⑤ 정규화에서)
```

신체 기준 좌표를 사용해 motion energy 비교가 절대 신체 크기·카메라 거리에 영향받지 않도록 한다.

## 2. 설계 원칙

본 단계는 **라벨 일관성을 결정**하지, 동작의 질을 평가하지 않는다.

```text
허용:
- 반복 동안 어느 측이 더 많이 움직였는지 검출
- 검출된 활성 측을 기대 활성 측과 비교
- 반복 단위 일관성 표시
- 충분한 확신이 있을 때 라벨만 보정 (좌표 변경 없음)
- 귀속 보고서 산출

금지:
- 반복이 “잘 수행되었는지” 판단
- 동작 품질 점수 산출
- 좌표 변경
- 반복 경계 변경
```

운동별 품질 평가는 ⑦ 특징 추출, ⑧ 생체역학적 근사 모델링, ⑨ 지표화의 책임이다.

## 3. 적용 조건

본 단계는 운동 정의의 `classification.laterality`(annotation의 `pattern`과 교차 점검)에 따라 활성 여부가 결정된다.

```text
laterality = bilateral_symmetric  → 본 단계는 건너뛴다 (반복 단위 활성 측 개념이 없음)
laterality = alternating          → 본 단계가 실행되어 귀속 메타데이터를 산출
laterality = unilateral_*         → 본 단계가 실행되며 선언된 측이 기대 활성 측이 됨
laterality unknown / generic      → 본 단계는 건너뛴다 (안전한 기본)
```

스쿼트, 파이크 푸쉬업과 같은 양측 대칭 운동에서는 “반복별 기대 활성 측” 개념이 없으므로 귀속이 의미를 갖지 않는다.

## 4. 활성 측 검출

annotation의 `segment_type = rep` 구간에서 좌·우 paired 랜드마크에 대한 motion energy를 산출한다.

```text
반복 윈도우 [start, end]:

left_motion  = Σ |p_left_landmark(t+1)  - p_left_landmark(t)|
right_motion = Σ |p_right_landmark(t+1) - p_right_landmark(t)|

motion_share = max(left_motion, right_motion)
              / (left_motion + right_motion + ε)
```

귀속에 사용되는 paired 랜드마크는 운동 정의의 `landmarks.primary_joints`에서 결정된다 (필요 시 운동별 설정으로 override 가능).

```text
plank_shoulder_tap : left_wrist  vs right_wrist
lunge              : left_knee   vs right_knee
                     (전방 다리에 더 큰 수직 변위가 발생)
```

여러 paired 랜드마크의 `motion_share` 값을 가중합으로 결합해 단일 잡음 랜드마크에 대한 민감도를 줄일 수 있다.

## 5. 검출 결과 처리

```text
if motion_share > τ_active (default: 0.7):
    detected_active = motion이 더 큰 측
    attribution_confidence = motion_share

elif τ_ambiguous < motion_share <= τ_active (default: 0.55 ~ 0.7):
    detected_active = "ambiguous"
    attribution_confidence = motion_share

else:
    detected_active = "bilateral"
    attribution_confidence = 1 - motion_share
```

## 6. 기대 활성 측

annotation의 `pattern`과 `starting_side`로부터 도출되며, 운동 정의의 `laterality`와 교차 점검된다.

```text
pattern = alternating, starting_side = right:
  rep 1 → right
  rep 2 → left
  rep 3 → right
  rep 4 → left
  ...

pattern = alternating, starting_side = left:
  rep 1 → left
  rep 2 → right
  ...
```

`starting_side`가 누락되면 본 단계는 첫 반복의 검출된 활성 측을 시작 측으로 가정하고 이후 반복에 대해 교번을 적용한다.

## 7. 일관성 점검과 조치

각 반복의 검출 활성 측을 기대 활성 측과 비교한다.

```text
case A: detected_active == expected_active
        attribution_consistent = True
        action = "accept"

case B: detected_active != expected_active
        AND attribution_confidence > τ_swap (default: 0.85)
        attribution_consistent = False
        action = "swap"     (반복 윈도우 내 라벨만 교체)
                or "flag"   (보수 모드일 때)

case C: detected_active != expected_active
        AND attribution_confidence <= τ_swap
        attribution_consistent = False
        action = "flag"

case D: detected_active in {"ambiguous", "bilateral"}
        attribution_consistent = None
        action = "flag"
```

기본값은 보수 모드(conservative)이며 `flag`만을 사용한다. 자동 보정(`swap`)은 강건성 시뮬레이션 검증에서 false-correction 비율이 충분히 낮음이 확인된 후에 활성화한다.

## 8. 출력 컬럼

다음 컬럼이 추가되며, `rep` 구간 안의 프레임에서만 채워지고 그 외에는 null이다.

```text
detected_active_limb       'left' | 'right' | 'bilateral' | 'ambiguous' | None
expected_active_limb       'left' | 'right' | None
attribution_consistent     bool | None
attribution_confidence     float (0~1) | None
attribution_action         'accept' | 'flag' | 'swap' | None
```

## 9. 귀속 보고서

```text
method
exercise_type
laterality
pattern
starting_side
num_reps
num_consistent
num_flagged
num_swapped
num_ambiguous
num_bilateral
thresholds:
  τ_active
  τ_ambiguous
  τ_swap
landmark_pairs_used
mode: 'conservative' | 'auto_correct'
```

본 보고서는 결정 과정 전체를 감사 가능하게 만든다.

## 10. 설정 (초안)

```yaml
motion_attribution:
  enabled: false
  thresholds:
    active: 0.70
    ambiguous: 0.55
    swap: 0.85
  mode: conservative           # 'conservative' | 'auto_correct'
  landmark_pairs:              # 선택; 누락 시 landmarks.primary_joints로 폴백
    plank_shoulder_tap:
      - [left_wrist, right_wrist]
    lunge:
      - [left_knee, right_knee]
      - [left_ankle, right_ankle]
```

운동 정의의 `laterality`가 `bilateral_symmetric`이면 본 단계는 `enabled` 값과 무관하게 건너뛴다.

## 11. ④ 전처리와의 관계

④ 전처리는 프레임 단위로 작동한다. 짧은 좌우 라벨 스왑 사건은 보정할 수 있지만, 작용 측이 가려진 상태에서 반복 전체에 걸친 라벨 어긋남은 신뢰성 있게 검출하지 못한다.

본 단계는 정규화된 데이터에서 반복 단위로 작동하며, 반복 경계와 운동 맥락을 함께 사용해 더 상위 레벨의 일관성 점검을 수행한다.

```text
④ 전처리          → 프레임 단위 신뢰도 / 라벨 정확성
⑥ 귀속 (본 단계)   → 반복 단위 활성 측 일관성
```

따라서 ④ 전처리에서 스왑 보정 없이 통과한 반복도, 본 단계에서 활성 측이 기대 패턴과 다르면 표시된다.

## 12. ⑦ 특징 추출과의 관계

⑦ 특징 추출은 본 단계의 메타데이터를 읽어 반복 단위 특징을 어느 측에 귀속할지 결정한다.

```text
attribution_consistent == True
  반복의 특징은 기대 활성 측에 귀속된다.

attribution_consistent == False AND action == 'flag'
  특징은 산출되지만, 측별 집계에서 가중 하락 또는 제외된다 (정의에 따라).

attribution_consistent == False AND action == 'swap'
  반복 안의 좌우 라벨은 교체된 상태로 특징이 산출된다.
```

이로써 ⑦ 특징 추출 코드가 라벨 보정 로직을 갖지 않게 된다.

## 13. 초기 완료 기준

```text
1. motion_attribution.py 가 존재한다.
2. 양측 대칭 운동에서 본 단계가 자동으로 건너뛰어진다 (운동 정의의 laterality 기반).
3. annotation의 rep 윈도우에서 motion energy가 산출된다.
4. 검출 활성 측과 confidence 값이 산출된다.
5. 기대 활성 측이 pattern·starting_side로부터 도출된다.
6. 귀속 컬럼이 데이터프레임에 추가된다.
7. 보수 모드는 라벨을 변경하지 않고 표시만 한다.
8. 귀속 보고서가 반환된다.
9. pipeline.py 가 본 단계를 활성화해 실행할 수 있다.
10. notebook/08_motion_attribution_test.ipynb 가 동작을 검증한다.
```

## 14. 향후 확장

- 운동별 학습 가중치를 사용한 다중 랜드마크 motion-share
- tap-style 운동에 대한 수직축 또는 normal-axis motion energy
- HMM 기반 phase 인식으로 `starting_side` 없이 활성 측 추론
- 강건성 시뮬레이션 검증 후 자동 보정 활성화
- 반복별 motion energy 시각화 (수동 검토용)
- 합성 가려짐 조건에서의 반복 단위 귀속 평가 (강건성 시뮬레이션과 연계)
