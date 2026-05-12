# 12. 인실리코 시뮬레이션 (In-silico Simulation)

**문서 버전:** 1.0.1
**최종 갱신:** 2026-05-06  
**영문 동기화:** `docs_eng/pipeline/12_insilico_simulation.md`는 동일 버전의 영문 번역본이다.

파이프라인 단계 ⑫. ①–⑩ 러너 외부에서 독립적으로 호출된다. 정상 합성 포즈 데이터에
통제된 왜곡(distortion)을 주입하고 파이프라인을 재실행하여, 현실적인 단안 데이터 열화
조건에서 본 프레임워크가 어떻게 동작하는지를 특성화하는 공학적 강건성 하니스(harness).

본 단계는 **공학적 검증(engineering verification)** 이며 임상 검증(clinical validation)이
아니다. 환자 단위 출력을 생성하지 않으며, 결과를 진단 정확도로 보고해서는 안 된다.
학위논문 §8에 해당.

---

## 1. 파이프라인 위치 (Pipeline Position)

```text
Pose CSV
→ ① ~ ⑩ 분석 파이프라인 (정상 흐름)
                                       ↑
                                       │
   ⑫ Simulation  ──── 왜곡 주입 ────────┘
                  (①–⑩ 러너 외부에서 호출)
```

시뮬레이션은 `run_pipeline()`이 호출하지 **않는다**. 왜곡된 데이터에 대해 파이프라인을
반복 실행하고 결과 `BiomarkerScoreRecord` 및 `BiomechRecord` 출력을 집계하는 별도 러너이다.

필수 입력:
```text
정상 합성 포즈 데이터              data/pose/sample/mediapipe_squat_synthetic.csv
                                  (또는 파이프라인 내부 생성기)
운동 YAML                          ROM 제한이 사용하는 관절 트리플렛 설정
왜곡 설정                          configs/pipeline_default.yaml :: simulation
```

## 2. 설계 원칙 (Design Principle)

```text
허용:
    입력 데이터프레임 사본에 대한 왜곡 주입
    적용된 내용을 정확히 기록한 왜곡별 로그 dict
    공학적 강건성 지표 (단조성, 반응성, 특이도)
    후속 평가용 합성 비정상 라벨링
    가시성 가중 vs. 비가중 biomech 프록시의 A/B 비교

불허:
    원본 입력 데이터프레임을 in-place로 수정
    절대 단위 도입 (하니스는 전 구간 무차원)
    "정상 / 비정상" 라벨을 임상 진단으로 사용
    시뮬레이션 출력을 환자 데이터 대용으로 사용
    파이프라인 경고 억제 (하니스는 실패 모드를 드러내야 함)
```

## 3. 왜곡 함수 (Distortion Functions)

`simulation/synthetic.py`는 4개의 왜곡 인젝터를 제공한다. 각 함수는 `(modified_df, log_dict)`
튜플을 반환하며, 원본 데이터프레임은 변형되지 않는다.

### 3-1. 가우시안 노이즈 (Gaussian Noise)

포즈 추정기 측정 노이즈를 모사하는 좌표 jitter.

```python
add_gaussian_noise(
    df,
    sigma_torso_ratio=0.01,    # 몸통 길이의 1 %
    landmarks=None,            # None → 모든 랜드마크
    seed=42,
)
```

### 3-2. 가려짐 (Occlusion)

지정 프레임 범위에서 랜드마크 좌표를 NaN으로, 가시성을 0으로 설정한다.
④ 전처리의 신뢰도 게이팅과 ⑨ 가시성 가중을 검증한다.

```python
add_occlusion(
    df,
    target_landmarks=["left_knee"],
    frame_range=(120, 180),
    zero_visibility=True,
)
```

### 3-3. 속도 스파이크 (Velocity Spike)

지정 프레임에 위치 점프를 삽입한다; ④ 전처리 내부 속도 이상값 검출기를 검증한다.

```python
add_velocity_spike(
    df,
    target_landmarks=["right_ankle"],
    spike_frames=[150],
    spike_magnitude_torso_ratio=0.5,
    seed=42,
)
```

### 3-4. ROM 제한 (ROM Restriction)

관절 트리플렛의 원위(distal) 랜드마크를 조정하여 끼인각이 `restriction_deg`를 초과하지
않도록 한다. 강직 또는 통증 회피로 인한 굴곡 제한 패턴을 모사한다.

```python
restrict_rom(
    df,
    joint="left_knee",
    restriction_deg=90.0,
    landmarks_triplet=("left_hip", "left_knee", "left_ankle"),
    rep_frames=[(85, 160), (170, 245)],
)
```

## 4. 실험 조건 매트릭스 (Experimental Condition Matrix)

`configs/pipeline_default.yaml :: simulation`의 미러:

| 조건                      | 수준                                       | 의도                                              |
|--------------------------|--------------------------------------------|---------------------------------------------------|
| 시점 변동                 | 정면 대비 ±15°, ±30°                       | 단안 시점 변동에 대한 강건성                      |
| ROM 제한 (knee)           | 30°, 60°, 90° 한계                         | 보상 패턴에 대한 반응성                           |
| 가우시안 노이즈 σ         | 0.005, 0.01, 0.02 (`torso_length_ratio`)   | 좌표 노이즈에 대한 강건성                         |
| 가려짐 지속 시간          | 5, 15, 30 프레임                           | 가려짐에 대한 강건성                              |
| 속도 스파이크 크기        | 0.2, 0.5, 1.0 (`torso_length_ratio`)       | 추정 불안정성에 대한 강건성                       |

매트릭스는 운영자가 수준을 추가하기 위해 Python 코드를 편집할 필요가 없도록 YAML에
1:1로 미러링된다.

## 5. 강건성 지표 (Robustness Metrics)

학위논문 §4.5의 phase-resolved 단조성을 보고할 수 있도록, 반복 단위와 구간 단위
(Descent / Ascent 별도) 모두에서 계산된다.

```text
monotonicity (단조성)      왜곡 강도가 증가할 때 지표가 일관된 방향으로 움직이는가?
                           출력: 왜곡 수준과 지표 사이의 Spearman ρ.

responsiveness (반응성)    시뮬레이션된 보상이 추적 후보와 일치할 때 지표가 반응하는가?
                           출력: 왜곡 수준별 감점 크기.

specificity (특이도)       해당 왜곡에서 무관한 지표는 평탄하게 유지되는가
                           (위양성 통제)?
                           출력: 왜곡 수준별 off-target 지표의 drift.

false_correction_rate      ⑦ Motion Attribution의 auto_correct가 해당 왜곡에서
                           얼마나 자주 잘못 작동하는가?
                           출력: attribution_consistent가 True여야 하는데도
                                 action='swap'이 발생한 반복 비율.
```

지표는 일치 왜곡에서 단조성이 높고 **그리고** 비일치 왜곡에서 특이도 drift가 낮을 때 "강건"으로 판단된다.

## 6. 강건성 실험 러너 (Robustness Experiment Runner, 계획)

```python
# scripts/run_robustness_experiment.py
def main():
    cfg          = load_pipeline_config(...)
    base_samples = load_normal_synthetic_samples(...)
    grid         = build_experiment_grid(cfg.simulation)

    results = []
    for sample in base_samples:
        for condition_name, level in grid:
            distorted = apply_distortion(sample, condition_name, level)
            report    = run_pipeline(distorted, cfg)
            results.append(summarize(report, condition_name, level))

    write_results_csv(results, "outputs/robustness_<timestamp>.csv")
    write_summary_report(results, "outputs/robustness_<timestamp>.md")
```

각 결과 행은 `condition × level × metric × phase`로 키된 long-format CSV에 저장되어,
⑪ 시각화의 `plot_robustness_sensitivity()`가 직접 소비할 수 있도록 한다.

## 7. 완료 기준 (Done Criteria)

```text
1. simulation/synthetic.py가 5개 왜곡 함수를 모두 구현한다
   (§3의 4개 왜곡 + 계획된 시점 변동).
2. scripts/run_robustness_experiment.py가 전체 그리드를 순회하고
   long-format CSV와 요약 md를 작성한다.
3. monotonicity / responsiveness / specificity 점수가 반복 단위와 구간 단위에서 계산된다.
4. tests/test_simulation.py가 각 왜곡 함수의 기본 단조 동작을 검증한다.
5. configs/pipeline_default.yaml의 simulation 섹션이 본 러너와 1:1로 매핑된다.
```

## 8. 코드 매핑 (Code Mapping)

```text
src/movement/simulation/__init__.py    왜곡 함수 재익스포트
src/movement/simulation/synthetic.py   add_gaussian_noise, add_occlusion,
                                       add_velocity_spike, restrict_rom,
                                       generate_squat_csv
scripts/run_robustness_experiment.py   계획: 조건 그리드 러너
configs/pipeline_default.yaml          simulation: 섹션이 §4 매트릭스를 미러
notebook/14_simulation_robustness_test.ipynb   계획된 데모
```

## 9. 다른 단계와의 관계 (Relationship to Other Steps)

- **④ 전처리** — 강건성 대상; `restrict_rom`과 `add_velocity_spike`는 속도 이상값 검출기와
  가시성 게이팅 로직을 시험한다. ④가 진정한 보상 패턴을 정상처럼 보이는 데이터로 보정하지
  **않음**을 검증한다.
- **⑦ 모션 어트리뷰션** — `false_correction_rate`는 `auto_correct` 모드를 기본 비활성에서
  기본 활성으로 승격하기 위한 게이팅 지표이다.
- **⑨ 생체역학 프록시** — 가시성 가중 A/B 비교는 저신뢰 프레임 제외가 전체 안정성에
  기여하는 정도를 표면화한다.
- **⑩ 바이오마커 도출** — 합성 정상 베이스라인은 **왜곡되지 않은** 합성 데이터에 파이프라인을
  실행하여 생성되며, 이후 시뮬레이션이 그 베이스라인 대비 왜곡 데이터의 Z-score 감점을 평가한다.
- **⑪ 시각화** — `plot_robustness_sensitivity()`가 러너가 산출한 long-format CSV를 소비한다.

## 10. 향후 확장 (Planned Extensions)

- **시점 변동 인젝터** — 포즈 추정 이전에 신체 수직축 기준 3D 회전으로 ±15° / ±30°
  카메라 오프셋을 합성; §4 매트릭스 완성에 필요
- **결합 왜곡 모드** — 현실적 악조건 녹화를 모사하기 위한 노이즈 + 가려짐 동시 발생
- **보상 패턴 합성** — 순수 기하학적 ROM 제한이 아닌 운동 정의 기반 궤적 변형을 사용한
  명명된 보상 패턴(knee valgus, lateral pelvic shift 등)의 프로그램적 주입
- **운동별 그리드 가지치기** — 운동에 비적용되는 조건 건너뛰기
  (예: `pike_pushup`에는 무릎 ROM 제한이 무의미)
- **실패 모드 카탈로그** — 파이프라인이 예외를 발생시킨 모든 (condition, level)을 나열한
  자동 생성 md 리포트
- **지표별 부트스트랩 CI** — 다중 시드로 그리드 반복, monotonicity / responsiveness 점수에
  95 % CI 밴드 부착
- **실데이터 스왑 테스트** — 소수의 실제 녹화 코퍼스를 로드하여 동일 왜곡 주입;
  합성 케이스와의 행동 parity 검증 (임상 검증과는 별개)
