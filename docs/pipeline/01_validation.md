# 01. 검증 (Validation)

**문서 버전:** 1.2.1
**최종 갱신:** 2026-06-20
**영문 동기화:** `docs_eng/pipeline/01_validation.md`는 동일 버전의 영문 번역본이다.

파이프라인 단계 ①은 입력 pose data의 구조적 무결성을 점검한다. 데이터를 수정하지 않으며,
⑪ robustness evaluation과 구분된다.

---

## 1. 파이프라인 위치 (Pipeline Position)

```text
Pose CSV
→ ① Validation             ← 본 단계
→ ② Annotation
→ 후속 단계
```

후속 단계는 여기서 확인한 integrity assumption에 의존한다.

MediaPipe가 아닌 pose backend는 pipeline schema로 adapter 변환된 뒤 validation을 수행한다.
Validation 통과는 필수 frame, timestamp, coordinate, optional visibility field가 구조적으로
사용 가능하다는 뜻이다. MediaPipe와 다른 backend가 동일한 depth, visibility, 생체역학 evidence를
제공한다는 의미는 아니다.

## 2. 점검 항목 (Checks)

| Check | Purpose |
|---|---|
| Required columns | `frame`, `timestamp`, coordinate columns |
| Frame continuity | frame-index gap |
| Frame duplicates | duplicated frame values |
| Timestamp monotonicity | non-positive time differences |
| Estimated FPS | median timestamp delta |
| Missing value ratio | coordinate column별 결측률 |
| Visibility quality | visibility column이 있을 때 low-visibility ratio |

## 3. 진입점 (Entry Point)

```python
report = run_basic_validation(
    df=df,
    required_columns=make_required_columns(),
    coordinate_columns=make_coordinate_columns(),
    visibility_columns=make_visibility_columns(),
)
```

Report top-level keys:

```text
passed                  구조적 통과/실패만 반영
structural_passed       같은 blocking decision을 명시적으로 표시
required_columns
frame_continuity
timestamp
missing_values
visibility     # visibility column이 제공된 경우만
warnings
```

## 4. 정책 (Policy)

Validation은 문제를 보고할 뿐 수정하지 않는다.

```text
short gaps          ④ interpolation에서 처리
noisy trajectories  ④ smoothing에서 처리
low visibility      reliability gate에서 처리
failed validation   자동 폐기 기준이 아니라 manual-review signal
```

Visibility quality는 warning/provenance로만 다룬다. Low-visibility report는
`visibility.passed = false`를 만들 수 있지만, 그 이유만으로 top-level `passed`가
false가 되지는 않는다. 후속 reliability gate가 개별 frame, landmark, feature,
proxy record의 사용 가능성을 결정한다.

## 5. 임계값 (Thresholds)

`configs/pipeline_default.yaml`에서 설정한다:

```yaml
validation:
  missing_value_threshold: 0.05
  visibility_threshold: 0.5
```

## 6. 코드 매핑 (Code Mapping)

```text
src/movement/stages/validation.py
src/movement/core/config.py
```
