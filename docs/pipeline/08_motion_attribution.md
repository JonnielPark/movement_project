# 08. 모션 어트리뷰션 (Motion Attribution)

**문서 버전:** 1.1.1
**최종 갱신:** 2026-06-25
**영문 동기화:** `docs_eng/pipeline/08_motion_attribution.md`는 동일 버전의 영문 번역본이다.

파이프라인 단계 ⑧은 각 반복에서 실제로 움직인 사지가 기대 활성 측과 일치하는지 점검한다.
기대 측은 `performance_protocol.side_sequence`가 있으면 이를 먼저 사용하고, 없으면 annotation의
`execution_pattern` / `starting_side`에서 도출한다. 본 단계는 좌표를 수정하지 않으며, 후속 피처 귀속을
위한 반복 단위 메타데이터 칼럼만 추가한다.

---

## 1. 파이프라인 위치 (Pipeline Position)

```text
Pose CSV
→ ① Validation
→ ② Annotation
→ ③ Exercise Definition
→ ④ Preprocessing
→ ⑤ Normalization
→ ⑥ Canonicalization
→ ⑦ Segmentation
→ ⑧ Motion Attribution     ← 본 단계
→ ⑨ Feature Extraction
```

필수 입력:

```text
반복 경계                  segment_type == rep, rep_id
운동 컨텍스트              exercise_id, execution_pattern, starting_side
운동 정의                  laterality, primary_joints, performance_protocol.side_sequence
정의 준비도                primary_body_regions, joint_actions.primary
정규화 좌표                <landmark>_norm_x/y/z
```

정규화 좌표를 사용하므로 motion-energy 비교가 신체 크기와 카메라 거리의 영향을 덜 받는다.

Stage-check notebook 27은 공통 stage-check pattern을 따르되, 현재 real sample의 편측성에만
묶이면 안 된다:

```text
Data Setup
    real sample을 ⑦ Segmentation까지 준비한다.

Definition Policy Matrix
    사용 가능한 exercise definition을 읽고 laterality, performance side sequence,
    pairable primary joints 같은 definition field를 기준으로 motion-attribution
    policy를 skip, run, conditional, not-yet-implemented로 분류한다.

Definition Field Coverage
    선택된 definition field가 본 단계에서 직접 사용되는지, provenance/context로
    전달되는지, 후속 단계용인지, 아직 미지원인지 표시한다.

Direct Real-Sample Test
    선택된 real sample에 attribute_motion을 실행하고 기대 policy outcome을 확인한다.

Synthetic Applicability Smoke Test
    실행 가능한 definition이 있으면 minimal generated dataframe으로 active-side
    attribution 경로를 확인한다. 새 recording은 필요하지 않다.

Pipeline Integration
    run_pipeline으로 같은 stage를 실행하고 report provenance와 frame-level output
    contract를 확인한다.
```

Stage-check notebook은 하나의 default real sample을 사용할 수 있지만, policy matrix, field
coverage table, synthetic smoke test는 특정 운동 하나에 하드코딩하지 않고 definition-driven이어야
한다. Exercise definition에는 존재하지만 아직 구현되지 않은 항목은 조용히 무시하지 않고
`not_yet_implemented`, `conditional`, 또는 carried-forward context로 표시한다.

편측성/교대성 운동정의의 stage-check policy에서는 `primary_body_regions`와
`joint_actions.primary`를 readiness gate로 취급한다. 이 항목들은 motion-energy 계산식을 바꾸지는
않지만, active-side evidence를 해석하는 데 필요한 authoring context가 비어 있을 때 해당 definition을
완전한 실행 가능 상태로 표시하지 않도록 한다.

## 2. 활성 규칙 (Activation Rules)

```text
bilateral_symmetric       건너뜀; 반복별 활성 측 개념 없음
bilateral_asymmetric      not_yet_implemented; active-side semantics가 정의되기 전까지
                          side-bias/symmetry feature policy로 보낸다
alternating               반복별 실행
unilateral_left/right     실행; 선언된 측이 기대 측
unilateral_unspecified    컨텍스트/근거로 측을 추론할 수 있을 때 실행
unknown / generic         건너뜀
```

`bilateral_symmetric`은 config flag가 켜져 있어도 항상 건너뛴다.
Stage-check readiness preview에서는 편측성/교대성 definition에 pairable primary landmark,
primary body regions, primary joint actions 중 하나라도 빠지면 `conditional`로 낮춘다.

## 3. 검출 방법 (Detection Method)

각 반복 윈도우에서 좌우 짝 landmark의 motion energy를 계산한다:

```text
left_motion  = Σ ||p_left(t+1)  - p_left(t)||
right_motion = Σ ||p_right(t+1) - p_right(t)||
motion_share = max(left_motion, right_motion) / (left_motion + right_motion + ε)
```

짝은 가능하면 `landmarks.primary_joints`에서 선택하고, 불가능하면 기본 shoulder/elbow/wrist/
hip/knee/ankle 짝을 사용한다. tap 동작이나 비대칭 하지 동작은 운동 YAML에서 custom pair를
제공할 수 있다.

판정 임계값:

```text
motion_share > τ_active          → detected_active = left/right, confidence = motion_share
τ_ambiguous < share ≤ τ_active   → detected_active = ambiguous
share ≤ τ_ambiguous              → detected_active = bilateral
```

기본값: `τ_active = 0.70`, `τ_ambiguous = 0.55`, `τ_swap = 0.85`.

## 4. 기대 측 (Expected Side)

우선순위:

```text
1. laterality = unilateral_left/right
2. performance_protocol.side_sequence
3. execution pattern + starting_side
4. starting_side가 없고 근거가 충분할 때 첫 rep의 검출 측
```

지원 side-sequence mode:

```text
alternating_each_rep             rep 1 right, rep 2 left, ...
same_side_block_then_switch      첫 블록은 starting_side, 다음 블록은 반대측
```

기대 측을 결정할 수 없으면 조용히 통과시키지 않고 flag한다.

## 5. 조치 정책 (Action Policy)

```text
detected == expected
    attribution_consistent = True
    action = accept

detected != expected and confidence > τ_swap
    attribution_consistent = False
    action = auto_correct 모드에서는 swap, 그 외 flag

detected != expected and confidence ≤ τ_swap
    attribution_consistent = False
    action = flag

detected in {ambiguous, bilateral}
    attribution_consistent = None
    action = flag
```

기본 모드는 `conservative`이다. 라벨을 변경하지 않는다. `auto_correct`는 향후/실험 모드이며,
강건성 시뮬레이션에서 낮은 오보정율이 확인되기 전까지 비활성으로 둔다.

## 6. 출력 계약 (Output Contract)

프레임별로 추가되며, 값은 `rep` 구간 안에서만 non-null이다:

```text
detected_active_limb     left | right | bilateral | ambiguous | None
expected_active_limb     left | right | None
attribution_consistent   bool | None
attribution_confidence   float 0-1 | None
attribution_action       accept | flag | swap | None
```

Report fields:

```text
method
exercise_id
laterality
execution_pattern
starting_side
num_reps / num_consistent / num_flagged / num_swapped
num_ambiguous / num_bilateral
thresholds = {τ_active, τ_ambiguous, τ_swap}
landmark_pairs_used
performance_side_sequence
expected_side_source
side_sequence_warnings
mode
skipped / skip_reason
```

이 provenance field들은 stage가 skipped인 경우에도 방출한다. Skipped bilateral exercise도
`exercise_id`, `laterality`, 존재한다면 `execution_pattern`, `performance_side_sequence`,
thresholds, skip reason을 보고해야 한다.

## 7. 설정 (Configuration)

```yaml
motion_attribution:
  enabled: false
  thresholds:
    active: 0.70
    ambiguous: 0.55
    swap: 0.85
  mode: conservative        # conservative | auto_correct
```

## 8. 후속 사용 (Downstream Use)

⑨ Feature Extraction은 attribution metadata를 사용해 측별 피처를 귀속하거나 신뢰도를 표시한다:

```text
consistent true       → 기대 활성 측에 피처 귀속
flagged mismatch      → 피처는 계산하되 측 귀속 신뢰도 낮음으로 표시
auto-corrected swap   → 보정된 측 할당으로 피처 계산
ambiguous/bilateral   → 강한 측별 해석을 피함
```

⑧은 ④ Preprocessing을 보완한다. ④는 짧은 frame-level L/R swap을 다루고, ⑧은 segmentation과
운동 컨텍스트를 사용해 rep-level side consistency를 점검한다.

## 9. 코드 매핑 (Code Mapping)

```text
src/movement/stages/motion_attribution.py
    AttributionThresholds
    AttributionReport
    attribute_motion()

tests/test_motion_attribution_protocol_sequence.py
```
