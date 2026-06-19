# 대상 운동별 촬영 프로토콜 (Camera Filming Protocol per Exercise)

**문서 버전:** 1.4.3
**최종 갱신:** 2026-06-19
**영문 동기화:** [docs_eng/practical_protocols/camera_protocol.md](../../docs_eng/practical_protocols/camera_protocol.md)는 동일 내용의 영문 번역본이다.

본 문서는 단안 포즈 분석을 재현 가능하게 만들기 위한 최소 촬영 조건을 정의한다.
이는 취득 가이드이자 provenance schema이며, 카메라 calibration 또는 좌표 보정 알고리즘이
아니다. 권장 구역 밖에서 촬영한 데이터도 처리하되, 촬영 조건은 warning/provenance metadata로
남긴다.

---

## 1. Camera Zone 모델 (Camera Zone Model)

`reference_origin`은 피험자 또는 기준 매트 중심이다. 카메라 위치는 azimuth zone, radial
distance, height level로 표현한다. 기본 권장 거리는 `reference_origin` 주위 200-250 cm 링이다.

![Camera-zone protocol for exercise filming](assets/camera_zone_protocol.png)

| Zone | 방향 | 주 관찰 평면 |
|---|---|---|
| Z1 | 정면, 0도 | 관상면 |
| Z2 | 전면 우측 대각선, +45도 | 관상면 + 시상면 혼합 |
| Z3 | 우측면, +90도 | 시상면 |
| Z4 | 후면 우측 대각선, +135도 | 후면 + 시상면 혼합 |
| Z5 | 후면, 180도 | 후면 관상면 |
| Z6 | 후면 좌측 대각선, -135도 | 후면 + 시상면 혼합 |
| Z7 | 좌측면, -90도 | 시상면 |
| Z8 | 전면 좌측 대각선, -45도 | 관상면 + 시상면 혼합 |

모든 zone은 같은 radial-distance 권장값과 약 +/-10도 azimuth 허용 범위를 사용한다.

| Height | 범위 | 주요 용도 |
|---|---|---|
| H1 | 지면에서 0-30 cm | floor-based exercise |
| H2 | 지면에서 80-110 cm | 하체 운동 |
| H3 | 지면에서 140-170 cm | 상체 또는 전신 운동 |

선택 canonicalization prior는 height를 보수적 body anchor 선택에만 사용할 수 있다:

```text
H1 → support / ankle-level anchor
H2 → pelvis / hip-center anchor
H3 → shoulder-center / shoulder-line anchor
```

이는 lens correction, camera intrinsic/extrinsic 추정, 물리 좌표 재투영이 아니다.

## 2. 기준 매트 (Reference Mat)

기준 매트는 약 180 cm x 60 cm로 간주하는 사용자 배치 보조 도구이다.
별도 calibration 장치 없이 거리와 방향을 맞추기 위한 목적이다.

Pipeline policy:

```text
mat corners detected automatically      no
mat size inferred from video            no
perspective transform estimated         no
camera calibration performed            no
metadata stored                         reference_mat_used, filming warnings
```

매트가 없어도 recording은 수용하며, 해당 조건을 metadata로 기록한다.

## 3. 권장 View-Family/H 세팅 (Recommended View-Family/H Settings)

Camera authoring은 exact left/right `Z` 선택이나 운동 이름별 camera preset이 아니라
view-family/H 조합을 기준으로 한다. Exercise authoring notebook은 posture, support, laterality,
joint actions, primary movement plane에서 권장 조합을 산출한다. 추천되지 않은 조합도 계속 선택
가능하며, 제외 규칙이 아니라 provenance로 기록하고 view-metric reliability를 낮추는 근거로
사용한다.

| Exercise | 권장 zone | Height | 주 관찰 목적 |
|---|---|---|---|
| Squat | Z2 / Z8 | H2 | knee tracking + hip-flexion depth |
| Lunge | Z3 / Z7 | H2 | anterior knee travel + sagittal trunk/lower-limb alignment |
| Pike push-up | Z3 / Z7 | H1 | shoulder angle + inverted-V hip geometry |
| Plank shoulder tap | Z2 / Z8 | H1 | pelvic rotation + lateral sway during weight shift |

권장 세팅은 reliability prior이지 포함/제외 규칙이 아니다. 같은 recording 안에서도 어떤 metric
family는 잘 지지되고, 다른 metric family는 제한될 수 있다.

좌우 mirror zone은 운동 정의의 추천 관점에서는 equivalent로 취급한다. 예를 들어 `Z2`와 `Z8`은
모두 front-oblique view이고, `Z3`와 `Z7`은 모두 sagittal side view이며, `Z4`와 `Z6`은 모두
rear-oblique view이다. Exercise definition은 view family를 저장하고, concrete recording metadata는
관측된 exact `Z`를 알고 있을 때만 저장하면 된다.

Recommended position과 non-recommended position은 함께 export될 수 있다:

```yaml
camera_protocol:
  selected_view:
    view_family: front_oblique
    member_zones: [Z2, Z8]
    height: H2
    recommendation_status: recommended
  recommended_view_positions:
    - {view_family: front_oblique, member_zones: [Z2, Z8], height: H2}
  non_recommended_view_positions:
    - {view_family: side, member_zones: [Z3, Z7], height: H2}
  recommended_zones: [Z2, Z8]
```

## 4. 시점 신뢰도 (View Reliability)

Feature interpretation은 세 개념을 분리한다:

```text
metric_computed        numeric feature 계산 가능 여부
view_reliability       camera view가 해당 해석을 지지하는 정도
feature_availability   visibility, geometry, swap risk, view reliability가 scoring을 허용하는지
```

Reliability levels:

```text
high            landmark quality가 충분하면 scoring 가능
moderate        confidence/provenance note와 함께 scoring 가능
low             강한 추가 근거가 없으면 report/review 전용
not_assessed    scoring하지 않음
```

View-family summary:

| View family | Typical zones | 강한 해석 | 약한 해석 |
|---|---|---|---|
| Frontal | Z1, Z5 | bilateral symmetry, frontal knee/pelvis/trunk alignment | sagittal ROM, depth, heel lift |
| Oblique | Z2, Z8, Z4, Z6 | mixed frontal-sagittal review | 세밀한 pure-plane 해석 |
| Side | Z3, Z7 | sagittal ROM, anterior knee travel, trunk lean, step length | left/right symmetry, valgus/varus, lateral shift |

단측 또는 교대 운동은 role-based 해석을 우선한다:

```text
forward_leg / trailing_leg
active_side / support_side
near_side / far_side
```

Side-to-side scoring은 active-side provenance와 near/far visibility reliability가 기록된 경우에만
허용한다.

## 5. 세션 프로토콜 (Session Protocol)

```text
set recording                  가능하면 one take
default pilot acquisition      운동별 3세트, 세트당 10 count
multi-set storage              세트별 별도 recording 허용
session linkage                session_id + set_index
static calibration pose        필요 없음
normalization scale            sequence median torso length + per-frame hip center
```

10회 연속 반복은 세트 내 trend 관찰을 위한 취득 전략이다. 피로 진단을 의미하지 않는다.

## 6. 파이프라인 사용 (Pipeline Use)

Primary data locations:

```text
data/camera/camera_zones.yaml
data/protocols/camera/<exercise_id>.yaml
annotation columns: camera_zone, camera_height_level, reference_mat_used,
                    filming_protocol_status
```

Processing policy:

```text
recommended zone matched       정상 처리, provenance 기록
recommended zone mismatched    warning 후 정상 처리
filming zone missing           unknown 기록 후 정상 처리
reference mat absent           warning, 강제 제외 없음
coordinate reprojection        적용하지 않음
view_metric_reliability        confidence/provenance gate, 좌표 보정 아님
```

⑥ Canonicalization은 pose-internal floor 또는 height prior를 candidate evidence로 추가할 수 있다.
이 prior는 side view를 실제 frontal observation으로 만들지 않는다. Bilateral symmetry feature는
충분한 visibility, plausible segment geometry, 낮은 swap risk, 지지 가능한 view가 확인될 때만
scoring에 들어간다.

관련 문서:

- [exercise_performance_protocol.md](exercise_performance_protocol.md)
- [02_annotation.md](../pipeline/02_annotation.md)
- [03_exercise_definition.md](../pipeline/03_exercise_definition.md)
- [05_normalization.md](../pipeline/05_normalization.md)
- [06_canonicalization.md](../pipeline/06_canonicalization.md)
- [13_insilico_simulation.md](../pipeline/13_insilico_simulation.md)
