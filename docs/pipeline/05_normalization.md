# 05. 정규화 (Normalization)

**문서 버전:** 1.3.0
**최종 갱신:** 2026-05-21
**영문 동기화:** `docs_eng/pipeline/05_normalization.md`는 동일 버전의 영문 번역본이다.

파이프라인 단계 ⑤는 원시 pose 좌표를 신체 상대 좌표계로 변환한다. 명시적으로 켠 경우에는
단안 pose의 일관된 관찰 편향을 줄이는 검토용 canonical 좌표도 생성할 수 있다.

이 단계는 절대 힘, 절대 토크, calibrated 3D, 절대 신체 치수를 추정하지 않는다. ⑧ Feature
Extraction과 ⑨ Biomechanical Proxy의 좌표 기반을 제공한다.

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
   └─ optional canonicalization: review-only candidate coordinates
→ ⑥ Segmentation
→ ⑦ Motion Attribution
→ ⑧ Feature Extraction
```

④ Preprocessing 이후에 실행된다. 신뢰도 낮은 hip/shoulder landmark가 척도 기준에 영향을 주기
전에 보정, 보간, 또는 표시되어야 하기 때문이다.

---

## 2. 기본 정규화 계약 (Base Normalization Contract)

구현된 방식은 `hip_torso`다.

```text
평행이동 기준 : 프레임별 골반 중심
척도 기준     : 시퀀스 단위 몸통 길이 중앙값
출력 단위     : torso_length_ratio (무차원)
```

골반 중심을 신체 상대 원점으로 사용한다.

```text
hip_center(t) = (left_hip(t) + right_hip(t)) / 2
p_translated_i(t) = p_i(t) - hip_center(t)
```

시퀀스 단위 몸통 길이 중앙값을 신체 척도로 사용한다. 프레임별 척도 대신 시퀀스 중앙값을
사용하면 단안 torso-length noise로 인한 인위적 skeleton jitter를 줄일 수 있다.

```text
shoulder_center(t) = (left_shoulder(t) + right_shoulder(t)) / 2
torso_length(t)    = distance(hip_center(t), shoulder_center(t))
s                  = median(valid torso_length)
p_norm_i(t)        = (p_i(t) - hip_center(t)) / s
```

원시 좌표는 절대 덮어쓰지 않는다.

```text
left_knee_x       원본 x
left_knee_norm_x  기본 정규화 x
left_knee_canon_x 선택 canonical 후보 x
```

좌표 계열의 의미는 고정한다.

```text
raw      원본 pose 좌표
norm     hip-torso 기본 정규화 좌표
canon    canonicalization 이후 선택 검토/후보 좌표
```

---

## 3. 설정 계약 (Configuration Contract)

상세 기본값은 `configs/pipeline_default.yaml`에 둔다. 안정적인 계약은 다음과 같다.

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
    data_confidence: ...
    support_plane_alignment: ...
    movement_plane_alignment: ...
    protocol_height_lateral_width_alignment: ...
```

`report_only: true`는 `canon` 좌표와 report를 만들 수 있지만 후속 단계가 계속 `norm` 좌표를
소비한다는 뜻이다. `downstream_coordinate_mode`를 `canon`으로 바꾸려면 노트북 검토, robustness
근거, 명시적 문서 갱신이 선행되어야 한다.

`floor_relative_correction`은 local 또는 legacy config에 남아 있을 수 있다. 이는
`support_plane_alignment`의 하위 호환 alias로 취급하며, 새 작업에서는 canonicalization key를
우선 사용한다.

---

## 4. 리포트 계약 (Report Contract)

`normalize_pose_by_hip_torso(df, landmarks)`는 정규화된 DataFrame과 report를 반환한다.

```python
{
    "method": str,
    "num_frames": int,
    "scale_method": str,
    "scale_value": float,
    "min_torso_length": float,
    "max_torso_length": float,
    "median_torso_length": float,
    "num_invalid_torso_frames": int,
    "num_normalized_landmarks": int,
}
```

canonicalization이 켜진 경우 `canonicalization_report`를 normalization report 안에 추가한다.

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

`data_confidence.level`은 movement-quality score가 아니다. 낮은 confidence는 자동 감점이 아니라
주의, withheld, provenance로 표현한다.

---

## 5. Canonicalization 계약 (Canonicalization Contract)

Canonicalization은 선택 기능이며 기본 비활성화 상태다. 이는 calibrated 3D reconstruction도,
좋은 동작 template fitting도 아니다. 역할은 raw/norm 좌표를 보존한 채 일관된 관찰 편향을
완화하고, knee valgus, heel lift, trunk lean, pelvis rotation 같은 실제 보상 패턴을 남기는 것이다.

현재 활성 prior:

| Prior | 상태 | 목적 | 보호선 |
|---|---|---|---|
| `support_plane_alignment` | 구현됨, 기본 비활성 | 접지 landmark 기반 pose 내부 pseudo-floor/support-plane 검토. 기존 `floor_relative_correction` 로직을 감싼다. | 발을 바닥에 고정하지 않으며 camera calibration이 아니다. |
| `movement_plane_alignment` | prototype, 기본 비활성 | hip-knee-ankle 주 운동 방향을 이용한 수직축 기준 capped rigid rotation. | out-of-plane residual을 보존해 보상 움직임 검토에 남긴다. |
| `protocol_height_lateral_width_alignment` | prototype, 기본 비활성 | H1/H2/H3 body anchor 주변의 보수적 lateral-width attenuation 전에 camera-height metadata를 gate로 사용한다. | 렌즈 보정, reprojection, far-side 좌표 생성이 아니다. |

현재 prior 순서:

```text
1. support_plane_alignment
2. movement_plane_alignment
3. protocol_height_lateral_width_alignment
```

Body-axis alignment는 의도적으로 활성화하지 않는다. 골반/어깨 축 정렬은 너무 일찍 적용하면
실제 골반 회전, 체간 기울기, 횡단면 보상을 지울 수 있으므로, anthropometric skeleton prior가
구체화된 뒤에만 재검토한다.

---

## 6. 후속 단계 규칙 (Downstream Rules)

- ⑥ Segmentation, ⑧ Feature Extraction, ⑨ Biomechanical Proxy, ⑩ Biomarker Scoring은 기본적으로
  `norm` 좌표를 소비한다.
- `canon` 좌표는 승격 기준이 작성되고 테스트되기 전까지 검토용 후보 좌표다.
- Corrected-coordinate magnitude와 residual은 movement-quality 감점이 아니라
  data-confidence/provenance signal이다.
- ④ Preprocessing은 scale 계산 전에 reliability violation을 표시할 수 있지만, 신체 상대 척도화와
  canonical 후보 좌표 생성은 ⑤ Normalization의 책임이다.
- ⑨ Biomechanical Proxy는 정규화 좌표로 상대 CoM, moment-arm, load-shift proxy를 계산한다.
  이 단계로부터 절대 힘, 토크, calibrated physical distance를 추론하지 않는다.

---

## 7. 향후 확장 (Planned Extensions)

- Size Korea-derived ratio source가 문서화된 뒤 segment-length/depth plausibility용
  anthropometric skeleton prior 추가.
- visibility-weighted scale estimation과 torso-length outlier handling.
- exercise definition field 기반 운동별 canonicalization prior 선택.
- `canon` coordinate 승격 전 robustness evaluation.
- local config가 더 이상 의존하지 않으면 legacy `floor_relative_correction` key 점진 축소.
