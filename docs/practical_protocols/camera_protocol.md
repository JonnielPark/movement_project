# 대상 운동별 촬영 프로토콜 (Camera Filming Protocol per Exercise)

**문서 버전:** 1.2.3
**최종 갱신:** 2026-05-08
**영문 동기화:** [docs_eng/practical_protocols/camera_protocol.md](../../docs_eng/practical_protocols/camera_protocol.md)는 동일 내용의 영문 번역본이다.

본 문서는 단안 비전(monocular vision) 환경에서 포즈 데이터 왜곡을 줄이고, 반복 가능한
분석 조건을 확보하기 위한 데이터 취득 가이드이다. 사용자의 일상 환경을 고려해 인위적
통제는 최소화하되, 운동별 핵심 보상 움직임을 관찰하기 위한 최소 촬영 조건을 정의한다.

이 프로토콜은 좌표 보정 알고리즘이 아니다. 권장 촬영 구역을 벗어난 데이터도 파이프라인에서
강제로 거부하지 않으며, 촬영 조건은 provenance와 경고 정보로 남긴다.

---

## 1. 촬영 구역 매트릭스 (Camera Zone Matrix)

피험자 또는 기준 매트 중심은 촬영 Zone이 아니라 `reference_origin`으로 정의한다. 카메라는
이 origin을 둘러싼 원형 촬영 링(circular filming ring) 위에 두며, 기본 권장 거리는 반경
200-250 cm이다. 촬영 위치는 방위각(azimuth), 링 위의 거리, 높이(height level)를 조합해
표현한다.

Zone은 거리 차이가 아니라 관찰 방향 차이를 의미한다. 모든 Zone은 동일하게 반경
200-250 cm를 권장하며, 방위각 허용 범위는 약 ±10도로 둔다.
도식에서는 `Z1`을 위쪽에 두고 양(+)의 방위각이 시계 방향으로 증가한다고 본다.
따라서 `Z4`는 링의 우하단, `Z6`는 좌하단에 놓인다.

![Camera-zone protocol for exercise filming](assets/camera_zone_protocol.png)

*그림 1. Camera zone은 `reference_origin`을 중심으로 한 동일 반경 200-250 cm
촬영 링의 방위각 구역으로 정의하며, 높이 레벨은 별도 메타데이터로 기록한다.*

| Zone | 방위각/위치 | 주 관찰 평면 | 링 위 위치 |
|---|---|---|---|
| Z1 | 정면, 0도 | 관상면 | 반경 200-250 cm, ±10도 |
| Z2 | 전면 우측 대각선, +45도 | 관상면 + 시상면 혼합 | 반경 200-250 cm, ±10도 |
| Z3 | 우측면, +90도 | 시상면 | 반경 200-250 cm, ±10도 |
| Z4 | 후면 우측 대각선, +135도 | 후면 관상면 + 시상면 혼합 | 반경 200-250 cm, ±10도 |
| Z5 | 후면, 180도 | 후면 관상면 | 반경 200-250 cm, ±10도 |
| Z6 | 후면 좌측 대각선, -135도 | 후면 관상면 + 시상면 혼합 | 반경 200-250 cm, ±10도 |
| Z7 | 좌측면, -90도 | 시상면 | 반경 200-250 cm, ±10도 |
| Z8 | 전면 좌측 대각선, -45도 | 관상면 + 시상면 혼합 | 반경 200-250 cm, ±10도 |

높이는 다음 세 단계로 기록한다.

| Height | 높이 | 용도 |
|---|---|---|
| H1 | 지면으로부터 0-30 cm | 플랭크, 파이크 푸쉬업 등 지면 밀착형 운동 |
| H2 | 지면으로부터 80-110 cm | 스쿼트, 런지 등 하체 운동 |
| H3 | 지면으로부터 140-170 cm | 전신 또는 상체 중심 운동 |

---

## 2. 기준 매트 기반 물리적 앵커 (Reference-Mat Physical Anchor)

별도 캘리브레이션 도구 없이 사용자가 거리와 방향을 맞출 수 있도록 기준 매트(reference mat)를
물리적 앵커로 사용한다. 표준 기준 매트 크기는 대략 180 cm × 60 cm로 간주한다.

| 항목 | Zone | 가이드 |
|---|---|---|
| 거리 | 전체 Zone | 스마트폰 화면에 기준 매트 전체가 들어오도록 약 3걸음, 즉 200-250 cm 뒤로 이동한다. |
| 정면 촬영 | `Z1` | 기준 매트의 전방 중심선 위에 카메라를 두고 `reference_origin`을 향하게 한다. 화면에서 매트의 좌우가 대략 대칭으로 보이도록 맞춘다. 현재 또는 추후 정면 관상면 추적이 중요한 운동을 위한 선택지이다. |
| 후면 촬영 | `Z5` | 기준 매트의 후방 중심선 위에 카메라를 두고 `reference_origin`을 향하게 한다. 같은 origin을 유지하면서 추후 후면 운동이나 후면 보상 패턴을 촬영하기 위한 선택지이다. |
| 전방 대각 촬영 | `Z2` / `Z8` | 기준 매트의 전방에서 약 45도 대각선 위치에 카메라를 두고, 가까운 앞쪽 모서리 또는 `reference_origin`을 향하게 한다. 관상면과 시상면 정보를 함께 보는 혼합 관찰에 사용한다. |
| 후방 대각 촬영 | `Z4` / `Z6` | 기준 매트의 후방에서 약 45도 대각선 위치에 카메라를 두고, 가까운 뒤쪽 모서리 또는 `reference_origin`을 향하게 한다. 추후 후면-시상면 혼합 관찰이 필요한 운동을 위한 선택지이다. |
| 측면 촬영 | `Z3` / `Z7` | 기준 매트의 긴 변이 화면 중심축과 평행하도록 맞추고 `reference_origin`을 향하게 한다. 시상면 관찰에 사용한다. |

기준 매트가 없거나 권장 거리에서 촬영하지 못한 경우에도 데이터는 수용한다. 단, 해당 조건은
촬영 메타데이터와 결과 리포트에 경고로 남긴다.

---

## 3. 대상 운동별 권장 세팅 (Per-Exercise Recommended Settings)

| 대상 운동 | 권장 Zone | 권장 높이 | 관찰 목적 |
|---|---|---|---|
| 스쿼트 | Z2 / Z8 | H2 | 전방 대각 시점에서 무릎 외반(valgus)과 고관절 굴곡 깊이를 함께 관찰 |
| 런지 | Z3 / Z7 | H2 | 무릎 전방 이동과 체간/하지 시상면 정렬 관찰 |
| 파이크 푸쉬업 | Z3 / Z7 | H1 | 어깨 각도와 힙 힌지 구조 변화 관찰 |
| 플랭크 숄더탭 | Z2 / Z8 | H1 | 체중 이동 중 골반 회전과 측방 흔들림 관찰 |

권장 구역은 가장 적합한 관찰 조건을 의미한다. 실제 파이프라인은 권장 구역 밖의 데이터도
처리하되, 해석 시 촬영 조건으로 인한 신뢰도 저하 가능성을 함께 표시한다.

---

## 4. 원테이크 및 세션 관리 (One-Take Session Protocol)

1. 각 세트는 녹화 시작 후 별도의 정적 대기 시간 없이 10회를 연속 수행한다.
2. 여러 세트를 촬영할 때는 세트별 파일로 분리하되, `session_id`와 `set_index`로 하나의
   시계열 세션에 속한다는 정보를 보존한다.
3. 인위적인 T-pose 캘리브레이션은 요구하지 않는다. 정규화 단계는 기존 원칙대로 전체
   시퀀스의 몸통 길이 중앙값과 매 프레임 골반 중심점을 사용한다.

10회 연속 수행은 후반 반복에서 나타나는 피로 관련 보상 움직임을 관찰하기 위한 취득
전략이다. 이 자체가 피로를 진단한다는 의미는 아니며, 파이프라인은 반복 간 변화 추세를
정량화하는 데 사용한다.

---

## 5. 파이프라인 반영 방식 (Pipeline Usage)

촬영 프로토콜은 다음 위치에서 메타데이터로 사용한다.

```text
data/camera/camera_zones.yaml
    Z1-Z8 polar-ring 구역, reference_origin, H1-H3 높이, anchor, out_of_zone 정책의 공통 정의

data/definitions/exercises/<exercise_id>.yaml
    camera_protocol 블록에 운동별 권장 zone, height, 관찰 목적 기록

Annotation 또는 recording metadata
    session_id, recording_id, set_index, camera_zone, camera_height_level,
    reference_mat_used, filming_protocol_status 등 선택 칼럼 기록
```

처리 정책:

```text
권장 구역 일치          provenance로 기록하고 정상 처리
권장 구역 불일치        경고를 남기고 정상 처리
촬영 구역 미기록        unknown으로 기록하고 정상 처리
기준 매트 미사용         경고를 남기되 강제 제외하지 않음
카메라 각도 보정         수행하지 않음
좌표 재투영 보정         수행하지 않음
```

시점(viewpoint) 변화가 지표에 미치는 영향은 ⑫ Simulation에서 강건성 조건으로 평가한다.
⑪ Visualization은 촬영 조건 경고를 결과 해석 옆에 표시할 수 있다.

관련 문서:

- [exercise_performance_protocol.md](exercise_performance_protocol.md)
- [02_annotation.md](../pipeline/02_annotation.md)
- [03_exercise_definition.md](../pipeline/03_exercise_definition.md)
- [12_insilico_simulation.md](../pipeline/12_insilico_simulation.md)
