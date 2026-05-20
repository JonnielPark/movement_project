# 01. 검증 (Validation)

**문서 버전:** 1.1.0
**최종 갱신:** 2026-05-21
**영문 동기화:** `docs_eng/pipeline/01_validation.md`는 동일 버전의 영문 번역본이다.

파이프라인 단계 ①은 입력 pose data의 구조적 무결성을 점검한다. 데이터를 수정하지 않으며,
⑫ robustness evaluation과 구분된다.

---

## 1. 파이프라인 위치 (Pipeline Position)

```text
Pose CSV
→ ① Validation             ← 본 단계
→ ② Annotation
→ 후속 단계
```

후속 단계는 여기서 확인한 integrity assumption에 의존한다.

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
passed
required_columns
frame_continuity
timestamp
missing_values
visibility     # visibility column이 제공된 경우만
```

## 4. 정책 (Policy)

Validation은 문제를 보고할 뿐 수정하지 않는다.

```text
short gaps          ④ interpolation에서 처리
noisy trajectories  ④ smoothing에서 처리
low visibility      reliability gate에서 처리
failed validation   자동 폐기 기준이 아니라 manual-review signal
```

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
