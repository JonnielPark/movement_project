# 13. In-Silico Simulation

**문서 버전:** 1.1.0
**최종 갱신:** 2026-05-21
**영문 동기화:** `docs_eng/pipeline/13_insilico_simulation.md`는 동일 버전의 영문 번역본이다.

파이프라인 단계 ⑬은 외부 robustness harness다. Synthetic 또는 reference pose data에 통제된
distortion을 주입하고 analysis pipeline을 다시 실행해 metric이 어떻게 반응하는지 요약한다.

이는 공학적 검증이며 clinical validation 또는 diagnostic accuracy가 아니다.

---

## 1. 파이프라인 위치 (Pipeline Position)

```text
Base pose sample → distortion copy → ①-⑪ pipeline replay → robustness summary
```

Simulation은 `run_pipeline()`에서 호출하지 않는다.

입력:

```text
base synthetic/reference pose data
exercise YAML
configs/pipeline_default.yaml의 simulation settings
```

---

## 2. 설계 계약 (Design Contract)

허용:

```text
DataFrame 사본에 distortion injection
적용된 condition과 level log
metric responsiveness / monotonicity / specificity check
⑫ visualization을 위한 long-format output
```

금지:

```text
source data in-place mutation
절대 physical unit
synthetic label을 clinical diagnosis로 사용
pipeline warning 또는 failure mode 숨김
```

---

## 3. 구현된 Distortions

`src/movement/simulation/synthetic.py`는 다음을 제공한다.

```text
add_gaussian_noise       coordinate jitter
add_occlusion            NaN coordinates와 선택 zero visibility
add_velocity_spike       abrupt coordinate jump
restrict_rom             bounded joint-angle restriction
generate_squat_csv       synthetic squat sample generator
```

각 distortion은 `(modified_df, log_dict)`를 반환하고 입력을 변경하지 않는다.

---

## 4. 계획된 Experiment Matrix

```text
Gaussian noise           coordinate-noise robustness
Occlusion                missing/low-visibility robustness
Velocity spike           preprocessing outlier behavior
ROM restriction          limited movement에 대한 responsiveness
Viewpoint variation      계획; camera-zone/view sensitivity
Compensation injection   계획; named compensation-pattern robustness
```

Condition level은 notebook에 하드코딩하지 않고 config grid와 맞춘다.

---

## 5. Robustness Metrics

```text
monotonicity
    distortion strength가 증가할 때 target metric이 일관된 방향으로 변하는가?

responsiveness
    matched distortion에 의도한 metric이 반응하는가?

specificity
    unmatched distortion에서 관련 없는 metric이 비교적 안정적인가?

false_correction_rate
    distortion 아래에서 motion attribution이 잘못된 side correction을 만드는가?
```

Metric은 rep level과, 가능하면 phase level에서 요약한다.

---

## 6. 계획된 Runner

```text
scripts/run_robustness_experiment.py
    config와 base sample 로드
    condition grid 구성
    distortion 적용
    ①-⑪ pipeline 실행
    FeatureRecord, BiomechRecord, BiomarkerScoreRecord summary 수집
    long-format CSV와 markdown summary 작성
```

Long-format output은 다음 key를 사용한다.

```text
condition × level × exercise × rep × phase × metric
```

그래야 `plot_robustness_sensitivity()`가 바로 소비할 수 있다.

---

## 7. 코드 매핑 (Code Mapping)

```text
src/movement/simulation/synthetic.py   distortion functions and sample generator
src/movement/simulation/__init__.py    public re-exports
configs/pipeline_default.yaml          simulation section
scripts/run_robustness_experiment.py   planned runner
tests/test_simulation.py               planned behavior tests
```

---

## 8. 향후 확장 (Planned Extensions)

- Viewpoint variation injector.
- Named compensation-pattern injection.
- Noise + occlusion combined condition.
- Per-exercise grid pruning.
- Markdown summary의 failure-mode catalog.
- Random seed 반복에 대한 bootstrap confidence band.
