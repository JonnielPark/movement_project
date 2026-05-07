# 01. 검증 (Validation)

**문서 버전:** 1.0.0  
**최종 갱신:** 2026-05-06  
**영문 동기화:** `docs_eng/pipeline/01_validation.md`는 동일 버전의 영문 번역본이다.

파이프라인 단계 ①. 입력 포즈 데이터의 구조적·형식적 무결성을 점검한다.
데이터를 수정하지 않으며 진단 리포트(report) 딕셔너리를 반환한다.

참고: 여기서의 "검증(validation)"은 데이터 무결성 점검만을 의미한다.
강건성 평가(robustness evaluation, 합성 데이터를 활용한 시뮬레이션 기반 시험)는 별개의 개념이다.

---

## 1. 파이프라인 위치 (Pipeline Position)

```text
Pose CSV
→ ① Validation             ← 본 단계
→ ② Annotation
→ ③ Exercise Definition
→ ④ Preprocessing
→ ⑤ Normalization
→ ⑥ Segmentation
→ ⑦ Motion Attribution
→ ⑧ Feature Extraction
```

다른 모든 단계 이전에 실행된다. 후속 단계는 검증 리포트가 확인한 무결성 가정에 의존할 수 있다.

## 2. 점검 항목 (Checks)

| 점검 | 설명 |
|---|---|
| 필수 칼럼 | `frame`, `timestamp`, 랜드마크 좌표 칼럼 |
| 프레임 연속성 | frame 인덱스의 갭 |
| 프레임 중복 | 반복된 frame 값 |
| 타임스탬프 단조성 | 양수가 아닌 시간 차분 |
| 추정 FPS | timestamp 차분의 중앙값에서 도출 |
| 결측값 비율 | 좌표 칼럼별 |
| 가시성 품질 | 분포 / 임계값 미만 비율 (가시성 칼럼이 있을 때) |

## 3. 출력 (Output)

```python
report = run_basic_validation(
    df=df,
    required_columns=make_required_columns(),
    coordinate_columns=make_coordinate_columns(),
    visibility_columns=make_visibility_columns(),
)
print(report["passed"])   # bool
```

리포트 구조:

```python
{
    "passed": bool,
    "required_columns": {
        "passed": bool,
        "missing_columns": list[str],
        "num_missing_columns": int,
    },
    "frame_continuity": {
        "passed": bool,
        "start_frame": int,
        "end_frame": int,
        "num_frames": int,
        "num_missing_frames": int,
        "missing_frames": list[int],
        "num_duplicated_frames": int,
        "duplicated_frames": list[int],
    },
    "timestamp": {
        "passed": bool,
        "num_timestamps": int,
        "median_dt": float,
        "estimated_fps": float | None,
        "min_dt": float,
        "max_dt": float,
        "num_non_positive_diffs": int,
    },
    "missing_values": {
        "passed": bool,
        "num_columns": int,
        "total_missing_values": int,
        "missing_ratio_by_column": dict[str, float],
    },
    "visibility": { ... },   # visibility_columns가 제공된 경우에만
}
```

## 4. 설계 원칙 (Design Principle)

본 단계는 잠재 이슈를 보고할 뿐이며, 보정하지 않는다.

- 짧은 갭 → ④ 전처리의 보간(interpolation)에서 처리.
- 노이즈가 있는 궤적 → ④ 전처리의 평활화(smoothing)에서 처리.
- 낮은 가시성 → ④ 전처리의 신뢰도 게이팅에서 처리.

검증 실패는 자동 폐기 신호가 아니라 수동 검토 신호이다.

## 5. 임계값 (Thresholds)

`configs/pipeline_default.yaml`에서 설정:

```yaml
validation:
  missing_value_threshold: 0.05   # 칼럼 결측 비율 > 5% → 경고
  visibility_threshold: 0.5       # 랜드마크 가시성 품질 임계값
```

## 6. 향후 확장 (Planned Extensions)

- 결측값 히트맵(heatmap) 시각화 (⑩ 단계)
- 좌표 단위 자동 판별 (픽셀 vs. 정규화)
- 시간 갭 분포 통계 강화
