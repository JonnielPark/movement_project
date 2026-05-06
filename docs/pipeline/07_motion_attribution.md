# 07. 모션 어트리뷰션 (Motion Attribution)

**문서 버전:** 1.0.0  
**최종 갱신:** 2026-05-06  
**버전 규칙:** Semantic Versioning 2.0.0 (`MAJOR.MINOR.PATCH`)  
**영문 동기화:** `docs_eng/pipeline/07_motion_attribution.md`는 동일 버전의 영문 번역본이다.

파이프라인 단계 ⑦. 각 반복에서 가장 많이 움직인 사지(limb)가 (어노테이션의
`pattern` / `starting_side`로부터 도출된) 기대 활성 측(active side)과 일치하는지 점검한다.

좌표를 수정하지 않는다. 반복별 메타데이터 칼럼만 추가한다.

---

## 1. 파이프라인 위치 (Pipeline Position)

```text
Pose CSV
→ ① Validation
→ ② Annotation
→ ③ Exercise Definition
→ ④ Preprocessing
→ ⑤ Normalization
→ ⑥ Phase Segmentation
→ ⑦ Motion Attribution     ← 본 단계
→ ⑧ Feature Extraction
```

필수 입력:
```text
반복 경계                  어노테이션 (segment_type = rep)에서 도출
운동 컨텍스트              어노테이션의 exercise_type, pattern, starting_side
운동 정의                  laterality, primary_joints
정규화 좌표                ⑤ Normalization에서
```

정규화 좌표를 사용함으로써, 동작 에너지 비교가 절대 신체 크기와 카메라 거리에 무관하게 된다.

## 2. 활성 조건 (Activation Condition)

```text
laterality = bilateral_symmetric  → 본 단계 건너뜀 (반복별 활성 측 개념 없음)
laterality = alternating          → 반복별 어트리뷰션 실행
laterality = unilateral_*         → 실행; 선언된 측이 기대 활성 측
laterality 미상 / generic         → 건너뜀 (안전 기본값)
```

## 3. 활성 측 검출 (Active Side Detection)

반복 윈도우(`segment_type = rep`) 내에서 좌·우 짝 랜드마크의 동작 에너지를 계산한다:

```text
left_motion  = Σ |p_left_landmark(t+1)  - p_left_landmark(t)|
right_motion = Σ |p_right_landmark(t+1) - p_right_landmark(t)|

motion_share = max(left_motion, right_motion) / (left_motion + right_motion + ε)
```

랜드마크 짝은 운동 정의의 `landmarks.primary_joints`에서 도출된다.
운동별 커스텀 짝은 YAML 설정에서 지정할 수 있다.

예:
```text
plank_shoulder_tap : left_wrist  vs right_wrist
lunge              : left_knee   vs right_knee
```

여러 짝 랜드마크를 결합(가중 평균)하여 단일 노이즈 랜드마크에 대한 민감도를 줄일 수 있다.

## 4. 검출 임계값 (Detection Thresholds)

```text
if motion_share > τ_active (기본값: 0.70):
    detected_active = 더 많이 움직인 측
    confidence = motion_share

elif τ_ambiguous < motion_share ≤ τ_active (기본값: 0.55 – 0.70):
    detected_active = "ambiguous"
    confidence = motion_share

else:
    detected_active = "bilateral"
    confidence = 1 - motion_share
```

## 5. 기대 활성 측 (Expected Active Side)

어노테이션의 `pattern`, `starting_side`에서 도출되며, 운동 정의의 `laterality`와 교차 검증된다.

```text
pattern = alternating, starting_side = right:
    rep 1 → right
    rep 2 → left
    rep 3 → right
    ...

pattern = alternating, starting_side = left:
    rep 1 → left
    rep 2 → right
    ...
```

`starting_side`가 없으면 rep 1의 검출된 활성 측을 시작으로 가정하고, rep 2부터 교대를 적용한다.

## 6. 일관성 점검 및 조치 (Consistency Check and Action)

```text
case A: detected == expected
        attribution_consistent = True
        action = "accept"

case B: detected != expected AND confidence > τ_swap (기본값: 0.85)
        attribution_consistent = False
        action = "swap"   (auto_correct 모드)
             or "flag"   (conservative 모드)

case C: detected != expected AND confidence ≤ τ_swap
        attribution_consistent = False
        action = "flag"

case D: detected in {"ambiguous", "bilateral"}
        attribution_consistent = None
        action = "flag"
```

기본 모드는 `conservative` (표시만 하고 라벨 수정하지 않음).
`auto_correct` (스왑) 모드는 강건성 시뮬레이션에서 오보정율(false-correction rate)이 검증된 후에만 활성화된다.

## 7. 출력 칼럼 (Output Columns)

프레임별로 추가되며, `rep` 구간 내에서만 non-null이다.

```text
detected_active_limb     'left' | 'right' | 'bilateral' | 'ambiguous' | None
expected_active_limb     'left' | 'right' | None
attribution_consistent   bool | None
attribution_confidence   float 0–1 | None
attribution_action       'accept' | 'flag' | 'swap' | None
```

## 8. 어트리뷰션 리포트 (Attribution Report)

```python
attr_df, attr_report = attribute_motion(df, exercise_definition, thresholds, mode)
```

리포트 필드:
```python
{
    "method": str,
    "exercise_type": str,
    "laterality": str,
    "pattern": str,
    "starting_side": str,
    "num_reps": int,
    "num_consistent": int,
    "num_flagged": int,
    "num_swapped": int,
    "num_ambiguous": int,
    "num_bilateral": int,
    "thresholds": {"active": float, "ambiguous": float, "swap": float},
    "landmark_pairs_used": list,
    "mode": str,      # "conservative" | "auto_correct"
    "skipped": bool,
    "skip_reason": str | None,
}
```

## 9. 설정 (Configuration)

```yaml
motion_attribution:
  enabled: false
  thresholds:
    active: 0.70
    ambiguous: 0.55
    swap: 0.85
  mode: conservative        # conservative | auto_correct
```

`bilateral_symmetric` laterality는 `enabled` 플래그와 무관하게 항상 본 단계를 건너뛴다.

## 10. ④ 전처리와의 관계 (Relationship to Preprocessing)

④ 전처리는 프레임 단위로 동작하며 짧은 좌·우 스왑 이벤트를 보정할 수 있다.
전체 반복 동안 활성 사지가 가려져 정지 측이 움직이는 측으로 보이는 경우 같은
반복 단위 라벨 불일치는 신뢰성 있게 검출하지 못한다.

⑦ 모션 어트리뷰션은 반복 경계와 운동 컨텍스트를 사용해 반복 윈도우 단위로 동작하며,
④에서 놓치는 상위 수준의 일관성 이슈를 잡아낸다.

## 11. ⑧ 피처 추출과의 관계 (Relationship to Feature Extraction)

⑧은 어트리뷰션 메타데이터를 사용해 피처를 올바른 측에 할당한다:

```text
attribution_consistent == True
    → 피처가 기대 활성 측에 귀속됨

attribution_consistent == False AND action == "flag"
    → 피처는 계산되나 측별 집계에서 가중치 하향 또는 제외

attribution_consistent == False AND action == "swap"
    → 좌·우 라벨 교환; 보정된 할당 위에서 피처 계산
```

## 12. 향후 확장 (Planned Extensions)

- 운동별 학습 가중치를 사용한 다중 랜드마크 motion-share
- 탭(tap) 형태 운동을 위한 수직축/법선축 동작 에너지
- 어노테이션 없이 starting_side를 추론하기 위한 HMM 기반 구간 인식
- 강건성 시뮬레이션 검증 후 auto_correct 활성화
- 수동 검토용 반복별 동작 에너지 시각화
