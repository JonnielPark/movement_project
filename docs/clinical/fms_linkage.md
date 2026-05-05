# FMS 연계 매핑

**문서 버전:** 1.0.0  
**최종 갱신:** 2026-05-06  
**버전 규칙:** Semantic Versioning 2.0.0 (`MAJOR.MINOR.PATCH`)  
**영문 동기화:** `docs_eng/clinical/fms_linkage.md`는 동일 버전의 영문 번역본이다.

본 문서는 FMS 채점표를 복제하지 않는다. `movement_project`의 feature/domain 기반 감점이
FMS식 움직임 관찰 항목과 어떤 방향으로 평행한지 설명하고, 대시보드가 사용할 수 있는
traffic-light 보조 라벨을 정의한다.

## 원칙

- Green / Yellow / Red는 FMS 점수가 아니라 `BiomarkerScoreRecord.final_score`의 보조 해석 라벨이다.
- 원문 채점 문구를 복사하지 않고, 인용 정보와 feature 연결만 남긴다.
- “진단”, “환자 분류”, “임상적으로 유의” 같은 표현은 사용하지 않는다.
- 모든 매핑은 `data/clinical/fms_mapping.yaml`을 단일 소스로 사용한다.

## 운동별 연결

| 운동 | FMS식 참조 패턴 | 주요 연결 feature |
|---|---|---|
| Squat | deep squat 유사 패턴 | knee valgus, trunk flexion, heel lift, knee ROM symmetry |
| Lunge | inline lunge 유사 패턴 | hip-center stability, knee valgus, trunk flexion, heel lift |
| Pike push-up | trunk stability push-up 유사 패턴 | shoulder symmetry, elbow symmetry, hip-center stability, shoulder ROM |
| Plank shoulder tap | rotary stability 유사 패턴 | pelvic rotation, lateral pelvic shift, shoulder symmetry, tempo CV |

## 구현 표면

```text
data/clinical/fms_mapping.yaml
src/movement/clinical.py
tests/test_fms_mapping.py
```

`traffic_light_for_score()`는 숫자 점수 또는 `final_score`와 `exercise_id`를 가진 record를 받아
`TrafficLightLabel`을 반환한다. 반환값에는 YAML provenance가 포함되어 reporting / dashboard에서
라벨의 출처를 추적할 수 있다.
