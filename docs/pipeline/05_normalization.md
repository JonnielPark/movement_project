# 05. 정규화 (Normalization)

**문서 버전:** 1.2.9
**최종 갱신:** 2026-05-21
**영문 동기화:** `docs_eng/pipeline/05_normalization.md`는 동일 버전의 영문 번역본이다.

파이프라인 단계 ⑤. 원시 포즈 좌표를 신체 상대(body-relative) 좌표계로 변환하고,
필요 시 단안 pose의 일관된 관찰 편향을 줄여 분석용 표준 좌표계(canonical analysis space)로
재표현한다.

절대 힘이나 절대 신체 치수를 추정하지 않는다.
⑧ 피처 추출과 ⑨ 생체역학 프록시 모델링에 안정적인 좌표 기반을 제공한다.

---

## 1. 파이프라인 위치 (Pipeline Position)

```text
Pose CSV
→ ① Validation
→ ② Annotation
→ ③ Exercise Definition
→ ④ Preprocessing
→ ⑤ Normalization          ← 본 단계
   ├─ base normalization: hip-center translation + torso-length scale
   └─ optional canonicalization: analysis-space alignment
→ ⑥ Segmentation
→ ⑦ Motion Attribution
→ ⑧ Feature Extraction
```

④ 전처리 이후에 실행된다. 척도 기준(몸통 길이 중앙값)은 엉덩이/어깨 랜드마크가
신뢰도 점검을 통과한 후 더 안정적이기 때문이다.

기본 hip-torso 정규화는 운동 종류별 분기를 하지 않는다. 단, 정적 접지 운동이나 주 운동 평면이
뚜렷한 운동에서는 ⑤ 정규화 내부의 선택 층으로 `canonicalization`을 둘 수 있다. 현재 구현된
하위 prior는 기존 `floor_relative_correction` 구현을 감싸는 `support_plane_alignment`와
prototype `movement_plane_alignment`다. height-aware lateral-width 검토를 위한
protocol-gated `protocol_height_lateral_width_alignment` prior도 추가한다. 활성 prior는 별도
`canon` 좌표와 `canonicalization_report`를 방출한다.

## 2. 방식: hip_torso (Method)

```text
평행이동 기준 : 프레임별 골반 중심 (hip center)
척도 기준     : 시퀀스 단위 몸통 길이 중앙값 (median torso length)
```

(프레임별 척도가 아닌) 시퀀스 단위 중앙값을 사용하면, 단안 깊이 추정의 프레임별 몸통 길이
노이즈로 인한 인위적 골격 떨림이 방지된다.

## 3. 1단계 — 평행이동 (Translation)

골반 중심을 신체 기준 원점으로 사용:

```text
hip_center(t) = (left_hip(t) + right_hip(t)) / 2
```

각 랜드마크가 평행이동된다:

```text
p_translated_i(t) = p_i(t) - hip_center(t)
```

본 단계 이후, 모든 랜드마크는 골반 원점에 대해 표현된다.

## 4. 2단계 — 척도화 (Scale)

몸통 길이를 신체 척도 단위로 사용:

```text
shoulder_center(t) = (left_shoulder(t) + right_shoulder(t)) / 2
torso_length(t)    = distance(hip_center(t), shoulder_center(t))
```

대표 척도로 시퀀스 단위 중앙값을 사용:

```text
s = median(모든 유효 프레임의 torso_length)
```

평행이동된 각 랜드마크를 `s`로 나눈다:

```text
p_norm_i(t) = (p_i(t) - hip_center(t)) / s
```

결과 단위는 `torso_length_ratio` (무차원)이다.

## 5. 출력 칼럼 (Output Columns)

원본 좌표는 보존된다. 정규화된 좌표는 새 칼럼으로 추가된다:

```text
left_knee_x      → 원본 x      left_knee_norm_x → 정규화된 x
left_knee_y      → 원본 y      left_knee_norm_y → 정규화된 y
left_knee_z      → 원본 z      left_knee_norm_z → 정규화된 z
```

참조 칼럼 (YAML에서 `keep_reference_columns: true`인 경우):

```text
hip_center_x, hip_center_y, hip_center_z
shoulder_center_x, shoulder_center_y, shoulder_center_z
torso_length
```

canonicalization이 켜진 경우, 기본 정규화 좌표를 덮어쓰지 않고 별도 `canon` 계열을 추가한다:

```text
left_knee_norm_x   → 기본 정규화 x
left_knee_canon_x  → canonicalization 적용 후 분석용 x
left_knee_canon_y  → canonicalization 적용 후 분석용 y
left_knee_canon_z  → canonicalization 적용 후 분석용 z
```

좌표 계열의 의미는 고정한다.

```text
raw      원본 pose 좌표
norm     hip-torso 기본 정규화 좌표
canon    선택 canonicalization을 거친 분석 좌표
```

## 6. 설정 (Configuration)

```yaml
normalization:
  enabled: true
  method: hip_torso
  keep_reference_columns: true
  canonicalization:
    enabled: false
    coordinate_mode: norm
    output_prefix: canon
    report_only: true
    downstream_coordinate_mode: norm
    data_confidence:
      emit: true
      correction_magnitude_warn_torso: 0.15
      correction_magnitude_fail_torso: 0.30
      residual_warn_torso: 0.08
    support_plane_alignment:
      enabled: false
      method: support_contact_plane
      vertical_axis: y
      support_landmarks: [left_heel, right_heel, left_foot_index, right_foot_index]
      diagnostic_landmarks: [left_heel, right_heel, left_foot_index, right_foot_index]
      visibility_threshold: 0.7
      stability_window_frames: 5
      max_anchor_residual_torso: 0.08
      correction_transform: rigid_rotation
      camera_pitch_deg: 0.0
      camera_roll_deg: 0.0
      correction_strength: 1.0
      max_correction_torso: 0.25
    movement_plane_alignment:
      enabled: false
      method: principal_motion_plane
      fit_landmarks: [left_hip, left_knee, left_ankle, right_hip, right_knee, right_ankle]
      minimum_visible_landmark_ratio: 0.7
      correction_strength: 0.5
      max_rotation_deg: 20.0
      preserve_out_of_plane_residual: true
    protocol_height_lateral_width_alignment:
      enabled: false
      method: height_anchor_lateral_width
      observed_height_level: null
      observed_height_column: camera_height_level
      recommended_height_level: null
      require_height_match: true
      height_anchor_map:
        H1: [left_ankle, right_ankle]
        H2: [left_hip, right_hip]
        H3: [left_shoulder, right_shoulder]
      near_depth_sign: negative
      correction_mode: near_side_attenuation
      correction_strength: 0.3
      max_scale_change: 0.20
      max_correction_torso: 0.15
      min_depth_offset_torso: 0.05
      visibility_threshold: 0.6
      apply_to_landmarks: []
      preserve_anchor_landmarks: true
  # 현재 구현 키. 구현 전환 중에는 아래 키를
  # canonicalization.support_plane_alignment의 하위 호환 alias로 취급한다.
  floor_relative_correction:
    enabled: false
    method: support_contact_plane
    coordinate_mode: norm
    vertical_axis: y
    support_landmarks: [left_heel, right_heel, left_foot_index, right_foot_index]
    diagnostic_landmarks: [left_heel, right_heel, left_foot_index, right_foot_index]
    visibility_threshold: 0.7
    stability_window_frames: 5
    max_anchor_residual_torso: 0.08
    correction_transform: rigid_rotation
    camera_pitch_deg: 0.0
    camera_roll_deg: 0.0
    correction_strength: 1.0
    max_correction_torso: 0.25
```

`report_only: true`이면 `canon` 좌표와 report는 만들 수 있지만, ⑥ 이후 단계의 기본 입력은
계속 `norm` 좌표로 둔다. `downstream_coordinate_mode: canon`은 노트북 검토와 robustness
평가 이후에만 허용한다.

이번 구현 pass의 현재 결정은 `canon` 좌표를 visualization/review-only로 유지하는 것이다.
파이프라인 설정은 `report_only: true`, `downstream_coordinate_mode: norm`을 유지하며,
⑥ Segmentation, ⑧ Feature Extraction, ⑨ Biomechanical Proxy, ⑩ Biomarker Scoring은 계속
기본 `norm` 좌표 계열을 입력으로 사용한다.

## 7. 정규화 리포트 (Normalization Report)

```python
norm_df, norm_report = normalize_pose_by_hip_torso(df, landmarks)
```

리포트 필드:

```python
{
    "method": str,
    "num_frames": int,
    "scale_method": str,
    "scale_value": float,          # 몸통 길이 중앙값 (원시 단위)
    "min_torso_length": float,
    "max_torso_length": float,
    "median_torso_length": float,
    "num_invalid_torso_frames": int,
    "num_normalized_landmarks": int,
}
```

canonicalization이 켜진 경우 `norm_report` 안에 `canonicalization_report`를 추가한다.

```python
{
    "enabled": bool,
    "status": "skipped" | "applied" | "partial" | "rejected",
    "coordinate_mode": "norm",
    "output_prefix": "canon",
    "report_only": bool,
    "downstream_coordinate_mode": "norm" | "canon",
    "active_priors": list[str],
    "applied_priors": list[str],
    "skipped_priors": dict[str, str],
    "max_correction_torso": float,
    "median_correction_torso": float,
    "residual_after_fit_torso": float | None,
    "data_confidence": {
        "level": "high" | "moderate" | "low",
        "reasons": list[str],
    },
    "prior_reports": {
        "support_plane_alignment": dict | None,
        "movement_plane_alignment": dict | None,
        "protocol_height_lateral_width_alignment": dict | None,
    },
}
```

`data_confidence.level`은 점수 감점이 아니라 해석 신뢰도다. 보정량이 크더라도 관절 변화량이
안정적이면 movement quality score는 높게 남을 수 있고, 대신 confidence note로 해석 주의를
표시한다.

## 8. 다른 단계와의 관계 (Relationship to Other Steps)

- **④ 전처리**: 척도 오염을 막기 위해, 정규화 이전에 비신뢰 랜드마크
  (낮은 가시성, 스왑 보정 대상)를 해결하거나 표시해 두어야 한다.
- **⑦ 모션 어트리뷰션**: 정규화 좌표를 사용한다. 신체 크기와 카메라 거리 효과가 이미 제거되어
  반복별 동작 에너지(motion energy) 비교가 더 일관된다.
- **⑨ 생체역학 프록시**: CoM과 모멘트 암 추정의 입력으로 정규화 좌표를 사용한다.
  본 단계는 좌표계를 제공하고, ⑨가 생체역학 계산을 추가한다.
- **⑩ 점수화**: `canon` 좌표 사용 여부와 무관하게 data confidence는 movement quality score와
  분리한다. 낮은 confidence는 감점이 아니라 해석 보류 또는 주의 note로 처리한다.

## 9. 선택 정규화 층: canonicalization

본 연구의 목적은 단안 pose를 실제 3D 공간으로 완전 복원하는 것이 아니다. raw skeleton이
3D 시각화에서 비틀려 보이더라도, 같은 landmark가 같은 신체 부위를 안정적으로 추적하고 오차가
시퀀스 안에서 어느 정도 일관되다면 관절의 상대 궤적과 시간적 변화량은 평가 가능하다.

`canonicalization`은 이 관점에서 raw/norm pose를 좋은 동작 template에 맞추는 절차가 아니라,
카메라와 monocular depth artifact 때문에 좌표계에 섞인 일관된 관찰 편향을 완화해
운동 패턴 평가에 적합한 `canonical analysis space`를 만드는 선택 층이다. 따라서 knee valgus,
heel lift, trunk lean처럼 실제 수행에서 나타난 보상 움직임은 지워서는 안 된다.

현재의 non-calibrated monocular workflow에서는 canonicalization을 기본 `norm` 좌표 뒤에 둔다.
이는 의도적인 순서다. 먼저 hip-center translation과 torso-length scaling으로 피험자 위치,
카메라 거리, 신체 크기 효과를 제거한 뒤, 선택 prior가 무차원 torso-length 단위에서 작동하게
한다. 이렇게 해야 보정량, residual threshold, confidence report를 피험자와 영상 간 비교 가능한
형태로 유지할 수 있다. raw 좌표는 audit를 위해 보존하지만, 현재 prior의 기본 적용 공간은 아니다.

권장 출력 구조는 세 좌표 계열을 모두 보존하는 것이다.

```text
raw 좌표
    원본 pose 좌표. 절대 덮어쓰지 않는다.

norm 좌표
    hip-center translation + torso-length scale을 적용한 기본 정규화 좌표.

canon 좌표
    canonicalization을 통과한 분석용 좌표. 최종 feature/biomech 입력 후보지만,
    보정량과 confidence report가 함께 해석되어야 한다.
```

canonicalization이 사용할 수 있는 prior는 다음처럼 나눈다.

```text
support_plane_alignment
    접지 landmark 기반 pseudo-floor / support-plane 정렬.

movement_plane_alignment
    스쿼트, 런지처럼 주 운동 평면이 뚜렷한 운동에서 hip-knee-ankle 등
    주요 관절 궤적의 공통 운동 평면을 안정화.

protocol_height_lateral_width_alignment
    촬영 height metadata를 gate로 사용한 뒤, height-specific body anchor를 중심으로
    depth-dependent lateral-width prior를 보수적으로 적용한다. H1은 지지/발목 높이 anchor,
    H2는 골반 / hip-center, H3는 어깨선으로 매핑한다. review-only prior이며 렌즈 보정이 아니다.

camera_prior
    camera zone, height level, pitch/roll 등 기록 정보를 보정량 해석과
    confidence/provenance에 반영. calibrated reprojection은 수행하지 않는다.
```

### 9.1 Canonicalization Prior 적용 순서

초기 구현 순서는 다음처럼 제한한다.

```text
1. support_plane_alignment
   정적 접지 운동의 pseudo-floor artifact를 완화한다.

2. movement_plane_alignment
   squat/lunge처럼 주 운동 평면이 뚜렷한 운동에서만 적용한다.
   실제 관상면 보상(knee valgus/varus)이나 heel lift를 지우지 않도록,
   out-of-plane residual은 보존하고 report에 남긴다.

3. protocol_height_lateral_width_alignment
   연구자가 검토 metadata를 명시적으로 override하지 않는 한, observed camera height가 운동
   프로토콜과 일치할 때만 적용한다. H1/H2/H3 anchor를 중심으로 near-side lateral spread
   과장을 완화하고, far-side depth compression은 물리적 위치를 만들어내기보다 confidence
   context로 기록한다.

```

Body-axis alignment는 현재 코드의 활성 prior가 아니다. 골반/어깨 축 정렬은 너무 이른 단계에서
적용하면 실제 골반 회전, 체간 기울기, 횡단면 보상 움직임을 지울 수 있으므로, anthropometric
skeleton prior가 구체화된 뒤 별도 검토 대상으로 남긴다.

여러 prior가 함께 켜져도 각 prior는 독립 report를 남긴다. 한 prior가 `rejected`되어도 나머지
prior가 실행될 수 있으며, 최종 `canonicalization_report.status`는 `partial`로 표시한다.

### 9.2 현재 구현된 prior: floor_relative_correction

현재 구현된 `floor_relative_correction`은 위 canonicalization 중 `support_plane_alignment`에
해당하는 초기 prior다. 일부 실제 단안 영상에서는 카메라 각도와 depth artifact 때문에 평평한
바닥이 좌표계 안에서 기울어진 것처럼 보이거나, 카메라에서 먼 쪽 발이 실제보다 높게 추정될 수
있다. 이를 완화하기 위해 기본 hip-torso 정규화 이후, ⑥ 세그멘테이션 이전에 선택적으로
실행할 수 있다.

이 prior는 발을 강제로 고정하지 않는다. 접지 후보 랜드마크로 pose 좌표계 내부의
`pseudo-floor reference`를 추정하고, 그 기울기 성분을 전체 좌표에 부분적으로 적용한다. raw
좌표와 norm 좌표는 보존되며, 보정 좌표와 보정량, floor-relative diagnostic residual은 새
칼럼과 report로만 추가된다.

보정은 발이나 다리 landmark에만 적용하는 것이 아니다. 예를 들어 카메라가 수평에 가깝더라도
단안 depth artifact 때문에 카메라에서 먼 쪽 발과 팔이 함께 높게 추정되는 경우, support-contact
landmark로 추정한 pseudo-floor 기울기를 각 landmark의 좌표 위치에서 평가하여 팔, 몸통, 머리까지
요청된 전체 landmark의 수직 좌표에 같은 원리로 적용한다. 즉, 보정은 "발을 바닥으로 끌어내리는"
처리가 아니라, 각 지점의 `pseudo-floor` 대비 상대 높이를 보존하면서 좌표계에 섞인 공통
floor-tilt 성분을 줄이는 처리다.

지원하는 transform mode는 두 가지다.

```text
rigid_rotation
    기본 검토 mode. 전체 3D pose를 하나의 rigid body처럼 회전시켜 observed pseudo-floor
    normal이 target pseudo-floor normal에 가까워지게 한다. 분절 기하와 좌우 평행 구조를
    더 잘 보존한다.

vertical_shear
    기존 비교 mode. observed pseudo-floor와 target plane의 local 차이만큼 수직 좌표만
    조정한다. 접지 높이는 안정화할 수 있지만 skeleton이 시각적으로 휘어 보일 수 있다.
```

현재 구현 상태:

```text
module              src/movement/stages/floor_reference.py
기본 상태           비활성화
기본 방식           support_contact_plane
기본 transform       rigid_rotation
현재 fit space      정규화 pose 좌표(`<landmark>_norm_x/y/z`)
출력 mode           `<landmark>_floor_x/y/z`
진단 값             `<landmark>_floor_height`, 보정량, report note
```

기본 카메라 각도 prior는 수평 카메라다.

```text
camera_pitch_deg = 0.0
camera_roll_deg  = 0.0
```

이 값은 calibrated camera extrinsic이 아니다. pose 좌표계 안에서 보존할 목표
pseudo-floor 기울기를 지정하는 파라미터다. 기본 수평 카메라 prior에서는 support-contact
landmark로 fit한 plane을 평평한 target plane과 비교한다. 촬영 조건상 pose 좌표계 안에서
일부 기울기를 보존해야 한다고 판단되면 `camera_pitch_deg`와 `camera_roll_deg`를 조정할 수
있고, 이 경우 목표 기울기를 초과하는 관찰 tilt 성분만 완화한다. 기본 `vertical_axis: y`
기준에서는 `camera_roll_deg`가 x방향 target slope, `camera_pitch_deg`가 z방향 target
slope로 매핑된다.

카메라 높이는 현재 floor-relative correction의 계산 파라미터가 아니다. 운동 정의와 recording
metadata에는 촬영 조건 검토를 위한 `camera_height_level` provenance를 둘 수 있고, 현재 스쿼트
프로토콜의 권장 높이는 H2(지면 80-110 cm)다. 다만 파이프라인은 camera intrinsic/extrinsic이나
실제 camera-to-floor distance를 추정하지 않으므로, 카메라 높이를 pseudo-floor transform 계산에
직접 사용하지 않는다. 이 영향은 현재 단계에서는 confidence/provenance 요인 또는 향후 robustness
condition으로 다루는 것이 적절하다.

설계 제약:

```text
원본 보존
    raw 좌표와 normalized 좌표를 덮어쓰지 않는다.

발 고정 금지
    개별 발 landmark를 floor line에 강제로 붙이지 않는다.

전체 pose 보정
    추정된 floor-tilt 성분은 fitting에 사용한 접지 landmark만이 아니라
    요청된 전체 landmark에 적용한다. 따라서 카메라에서 먼 쪽 팔이나 몸통도
    동일한 pseudo-floor 기준으로 보정 좌표를 갖는다.

rigid geometry 우선
    실제 샘플 검토에서는 전체 pose를 함께 회전하는 `rigid_rotation`을 우선 사용한다.
    `vertical_shear`는 디버깅과 비교를 위해 남기지만, 분절 기하를 보존한다고 가정하지 않는다.

진단 신호 보존
    heel lift, toe loading, 실제 접지 변화 가능성은 floor-height residual과
    confidence note로 남긴다.

캘리브레이션 아님
    pseudo-floor는 pose 내부 기준이며, 물리적 바닥면이 아니다.
    `camera_pitch_deg`와 `camera_roll_deg`는 target pose-coordinate prior를
    파라미터화할 뿐, 카메라 intrinsic/extrinsic이나 perspective reprojection을
    추정하지 않는다.
```

리포트에는 method, enabled/status, correction transform, support/diagnostic landmarks,
anchor count, observed plane coefficients, target plane coefficients, camera-angle prior,
correction strength, effective correction strength, max/median correction,
anchor residual summary, excluded-anchor reasons, confidence notes가 포함된다.

### 9.3 현재 구현된 prior: movement_plane_alignment

`movement_plane_alignment`는 주 운동 평면이 뚜렷한 운동을 위한 prototype prior이며, 현재는
최종 scoring 기본값이 아니라 squat/lunge 검토용으로 둔다. 이 prior는 hip-knee-ankle의
프레임 간 변위 벡터에서 지배적인 수평 운동 축을 추정한 뒤, 설정된 수직축을 기준으로 제한된
rigid rotation을 적용하여 공통 운동 방향을 canonical sagittal analysis plane에 가깝게 맞춘다.

이 prior는 신체를 template plane에 납작하게 맞추지 않는다. 전체 pose를 하나의 rigid body처럼
회전하며, 남는 out-of-plane motion은 `canon` 좌표와 prior report에 그대로 남긴다. 따라서
knee valgus, trunk lean, heel lift, 비대칭 제어처럼 실제 수행에서 나타날 수 있는 신호는 이후
feature/biomechanical interpretation에서 계속 확인할 수 있다.

현재 구현 상태:

```text
module              src/movement/stages/canonicalization.py
기본 상태           비활성화
기본 방식           principal_motion_plane
fit landmarks       사용 가능한 left/right hip, knee, ankle
transform           수직축 기준 capped rigid rotation
target plane        수직축 + 두 번째 수평축 (기본 y-z)
출력 mode           `<landmark>_canon_x/y/z` 갱신
진단 값             rotation angle, motion-vector count, coverage, residual ratio,
                    correction magnitude, excluded-landmark reasons
```

리포트에는 요청/적용 rotation angle, 추정된 primary movement axis, landmark coverage,
alignment 전후 out-of-plane residual motion ratio, torso-length-normalized 보정량이 포함된다.
큰 residual은 자동으로 movement quality가 낮다는 뜻이 아니다. 노트북 검토와 robustness simulation을
통해 `canon` 좌표의 downstream 승격 여부를 결정하기 전까지는 data confidence와 해석 맥락으로만
사용한다.

### 9.4 계획/프로토타입 prior: protocol_height_lateral_width_alignment

`protocol_height_lateral_width_alignment` prior는 정면 또는 대각 시점에서 카메라에 가까운 팔/다리가
좌우로 과장되어 보이고, 먼 쪽 팔다리는 몸쪽으로 압축되어 보이는 검토 패턴을 다룬다. 이 prior는
렌즈 모델이 아니라 촬영 protocol metadata를 gate로 사용한다.

```text
1. `observed_height_level` 또는 `camera_height_level`에서 관찰 카메라 높이를 확인한다.
2. 운동별 recommended height level과 비교한다.
3. height가 일치하면 신체 anchor를 선택한다:
   H1 → 지지/발목 높이 anchor
   H2 → 골반 / hip-center anchor
   H3 → shoulder-center / shoulder-line anchor
4. `canon` 좌표에서만 제한된 lateral-width attenuation을 적용하고,
   원본 `norm` 좌표는 그대로 보존한다.
```

현재 스쿼트 프로토콜은 H2가 권장 높이이므로 골반 / hip-center anchor를 사용한다. 첫 구현은
보수적으로 둔다. near-side lateral spread 과장은 완화할 수 있지만, far-side expansion은 후속
robustness test가 정당화하기 전까지 confidence issue로만 기록한다. 이렇게 해야 low-visibility
far-side joint에 근거 없는 좌표를 만들어내지 않는다.

이 prior는 카메라 캘리브레이션, 렌즈 보정, perspective reprojection이 아니다. 시각 검토와
data-confidence reporting을 위한 protocol-gated pose-internal prior다.

첫 검토 게이트는 합성 샘플용 `notebook/04_normalization_test.ipynb`와 실제 스쿼트 샘플용
`notebook/15_real_squat_import_visualization_test.ipynb`다. 파일럿 검토와 robustness 검증이
끝나기 전까지 floor/canon 좌표는 최종 점수 산출의 기본 downstream 입력으로 사용하지 않는다.

## 10. 향후 확장 (Planned Extensions)

- 가시성 가중 척도 추정
- 중앙값 계산 이전의 몸통 길이 이상값 제거
- 운동 정의 필드로 구동되는 운동별 canonicalization prior 선택
- 주 운동 평면 기반 `movement_plane_alignment` 노트북/robustness 평가
- 프로토콜 높이 기반 좌우폭 prior robustness 평가
- support-plane prior 안정성 검증과 legacy `floor_relative_correction` 명칭 축소
