# 운동별 상세 해석 문서 (Per-Exercise Clinical Rationale)

**문서 버전:** 1.0.0  
**최종 갱신:** 2026-05-09  
**영문 동기화:** `docs_eng/clinical/exercises/README.md`는 동일 버전의 영문 번역본이다.

이 폴더는 4대 대상 운동의 생체역학적, 임상적 해석 배경을 자세히 정리한다.
여기서 "임상적"이라는 표현은 질환 진단이나 치료 효과 입증이 아니라, 의료진 또는 전문가가
동작 품질을 해석할 때 참고할 수 있는 관찰 관점과 생체역학적 의미를 뜻한다.

이 문서는 개발 명세가 아니다. 다만 추후 `compensation_candidates`,
`analysis_disrupting_patterns`, feature registry, scoring rule을 정리할 때 참고 근거가 될 수
있다. 어떤 항목을 실제 계산 규칙으로 승격할 때는 `docs/code_revision_plan.md`에 먼저 기록하고,
이후 `docs_eng/pipeline/`, `docs/pipeline/`, YAML, 코드 순서로 반영한다.

---

## 문서 목록

| 운동 | 상세 문서 | 현재 수행 프로토콜 |
|---|---|---|
| 스쿼트 | [squat.md](squat.md) | [exercise_performance_protocol.md §2-1](../../practical_protocols/exercise_performance_protocol.md#2-1-스쿼트-squat) |
| 런지 | [lunge.md](lunge.md) | [exercise_performance_protocol.md §2-2](../../practical_protocols/exercise_performance_protocol.md#2-2-런지-lunge) |
| 파이크 푸쉬업 | [pike_pushup.md](pike_pushup.md) | [exercise_performance_protocol.md §2-3](../../practical_protocols/exercise_performance_protocol.md#2-3-파이크-푸쉬업-pike-push-up) |
| 플랭크 숄더탭 | [plank_shoulder_tap.md](plank_shoulder_tap.md) | [exercise_performance_protocol.md §2-4](../../practical_protocols/exercise_performance_protocol.md#2-4-플랭크-숄더탭-plank-shoulder-tap) |

---

## Asset 관리 원칙

`docs/practical_protocols/assets/`의 이미지는 피험자가 동작을 이해하기 위한 대표 예시 사진이다.
해당 이미지는 수행 프로토콜의 빠른 이해를 위한 것이므로, 상세 해석 문서로 옮기지 않는다.

운동별 상세 해석 문서에 추가되는 그림은 아래 위치에 둔다.

```text
docs/clinical/exercises/assets/<exercise_id>/
docs_eng/clinical/exercises/assets/<exercise_id>/
```

권장 규칙:

1. 대표 수행 사진은 기존 `docs/practical_protocols/assets/`에 둔다.
2. 관절각, 보상 패턴, landmark visibility, 측면/정면 비교처럼 해석 설명을 위한 그림은
   `docs/clinical/exercises/assets/<exercise_id>/`에 둔다.
3. 그림 안에 언어가 들어가지 않는다면 한글/영문 문서에서 같은 파일명과 같은 구도를 사용한다.
4. 그림 안에 한글 또는 영문 label이 들어가면 `*_ko.png`, `*_eng.png`처럼 파일명을 분리한다.
5. 원본 사진과 annotation이 필요한 분석용 그림은 촬영 조건, camera zone, height, participant
   cue를 caption이나 본문에 함께 남긴다.
6. 논문용 최종 figure는 이 폴더의 설명 그림과 구분하여, 추후 `outputs/figures/` 또는 논문용
   figure 정책이 정해진 위치에서 관리한다.

---

## 공통 표기

| 분류 | 의미 |
|---|---|
| 점수화 후보 | 관절 포인트 시계열에서 반복 가능하게 식별될 가능성이 있어, 추후 feature 또는 biomarker로 연결할 수 있는 패턴 |
| 통제 요인 | pose만으로 안정적으로 구분하기 어렵거나 취득 조건에 크게 의존해, 점수화보다 수행/촬영 조건 통제가 더 적절한 패턴 |
| 해석 제한 요인 | 데이터는 사용할 수 있지만 결과 해석 시 신뢰도 저하 또는 혼동 가능성을 함께 표시해야 하는 패턴 |
| 식별 가능성 높음 | 현재 landmark와 권장 camera view에서 비교적 명확하게 관찰 가능 |
| 식별 가능성 중간 | 특정 camera view, visibility, annotation 보조가 있을 때 관찰 가능 |
| 식별 가능성 낮음 | pose 시계열만으로는 안정적 구분이 어렵거나 외부 정보가 필요 |

---

## 단일 측면 촬영에서의 공통 고려사항

편측성 운동이나 측면에서 촬영되는 대칭 운동에서는 카메라에서 먼 쪽 관절이 모델에 의해 잘
추정될 수도 있고, 반대로 가려짐이나 좌우 겹침 때문에 불안정해질 수도 있다. 관절 포인트가
충분히 안정적으로 추출된다면 별도의 방어 로직 없이 기존 feature를 사용한다.

실제 촬영에서 먼 쪽 관절의 visibility가 낮거나 jitter가 반복적으로 관찰되면, 해당 관절을 나쁜
점수로 처리하기보다 해석 신뢰도 또는 feature availability 문제로 분리한다. 특히 대칭 운동의
측면 촬영에서는 좌우 대칭성 자체보다 `hip_center`, `shoulder_center`, 체간 각도, 머리/골반의
수직 변위, 잘 보이는 쪽의 시상면 ROM 같은 centerline 또는 visible-side 지표가 우선될 수 있다.

좌우 대칭성 feature는 양측 관절이 모두 충분한 coverage를 가질 때만 해석한다. 한쪽이 가려진
경우에는 대칭성이 나쁘다고 감점하지 않고, 해당 feature를 산출하지 않거나 low-confidence로
표시하는 것이 보수적이다.
