# 10. 시각화 (Visualization)

**문서 버전:** 1.1.2
**최종 갱신:** 2026-07-07
**영문 동기화:** `docs_eng/pipeline/10_visualization.md`는 동일 버전의 영문 번역본이다.

파이프라인 단계 ⑩은 ①-⑨ runner 밖에서 호출된다. Pose data, 중간 report, feature, biomech
proxy, biomarker output을 diagnostic review와 논문 figure용으로 렌더링한다.

Visualization 함수는 figure object를 반환하며 입력 데이터를 변경하면 안 된다.

---

## 1. 역할 (Role)

```text
Diagnostic review
    raw data, preprocessing, normalization/canonicalization analysis evidence, segmentation boundary,
    feature availability를 점검한다.

Result reporting
    feature, biomech, biomarker, robustness output을 source field까지 추적 가능한 형태로
    제시한다.
```

Visualization layer는 scored result 옆에 confidence/provenance를 함께 보여줘야 한다. 특히
computed-but-withheld feature와 low-confidence depth-dependent metric을 숨기지 않는다.

---

## 2. 단계별 범위 (Step Coverage)

```text
④ Preprocessing       reliability overlay와 before/after quality view
⑤ Normalization       raw/norm 비교
⑤-1 Canonicalization   norm/canon/analysis evidence 비교
⑥ Segmentation        rep/phase boundary와 failure point
⑦ Feature Extraction  side-role context, joint angle, ROM, feature availability
⑧ Biomech Proxy       CoM과 moment-arm/load-shift proxy
⑨ Biomarker Scoring   domain score, deduction, withheld feature
⑪ Simulation          robustness sensitivity curve
```

---

## 3. Provenance Convention

Figure에는 다음 정보가 드러나야 한다.

```text
record id / rep id / phase
feature_id 또는 metric_id
value와 unit
availability와 confidence reason
source_fields
관련되는 경우 deduction 또는 withheld-feature reason
```

Interactive figure는 hover text를 사용할 수 있고, 논문용 static figure는 caption, legend, side
summary를 사용한다.

---

## 4. 구현된 함수 (Implemented Functions)

```text
create_pose_animation
    raw, norm, 사용 가능한 analysis-space coordinate mode에 대한 Plotly 3D pose animation.

create_pose_comparison_animation
    raw vs norm 또는 norm vs canon처럼 두 coordinate mode를 겹쳐 visual QC를 수행.
```

선택 `floor`/analysis-space coordinate mode는 review tool이며 downstream promotion을 의미하지 않는다.

발표용 review를 위해 `notebook/20_stage_checks/30_visualization_test.ipynb`는 먼저 감지된
1번째 rep의 시작부터 10번째 rep의 끝까지를 recording-view orientation으로 보여주는 Plotly
Play/Pause animation을 구성한다. 이 view는 normalized (`norm`) coordinate를 우선 사용하며,
rep 사이 transition frame을 유지하여 재생 시간이 실제 기록된 동작 시간에 더 가깝게 유지되도록
한다. Interactive view를 따로 열거나 슬라이드용으로 화면 녹화할 수 있도록
`data/processed/visualization/` 아래 HTML playback 파일도 저장한다.

브라우저 기반 Plotly 3D animation은 렌더링 속도의 영향을 받으므로, 노트북은 발표용 playback에서
렌더링할 frame을 일부 줄일 수 있다. 이때 첫 frame, 마지막 frame, 전체 timestamp duration은
보존하므로 선택된 10rep 구간의 원본 pose data 자체는 변경하지 않는다.

---

## 5. 계획된 Reporting Functions

Visualization stub은 구현 착수 전까지 의도적으로 유지한다.

```text
plot_reliability_overlay
plot_joint_angle_timeseries
plot_rep_timeline
plot_side_role_context_chart
plot_phase_segmentation
plot_biomech_overlay
plot_biomarker_radar
plot_biomech_load_shift
plot_side_role_context_heatmap
plot_robustness_sensitivity
plot_biomarker_score_breakdown
save_figure(fig, path, fmt='svg')
```

계획된 함수는 metric을 내부에서 다시 계산하지 말고 안정화된 pipeline record/report를 소비해야 한다.

---

## 6. 구현 규칙 (Implementation Rules)

```text
Notebook exploration       Plotly 사용 가능
Publication figures        matplotlib/seaborn + svg/pdf/png export
Input mutation             금지
source_fields              hover/caption/side summary에 보존
Low confidence             plotted value 옆에 표시
Language                   향후 Korean/English label runtime 선택 가능
```

---

## 7. 코드 매핑 (Code Mapping)

```text
src/movement/reporting/visualization.py  implemented animations + planned stubs
src/movement/core/utils.py               frame extraction, plot ranges,
                                         landmark-column validation
notebook/00_setup/02_raw_visualization_test.ipynb          raw pose animation
notebook/20_stage_checks/23_preprocessing_test.ipynb             reliability review
notebook/20_stage_checks/24_normalization_test.ipynb             raw/norm review
notebook/20_stage_checks/25_canonicalization_test.ipynb          norm/canon analysis-evidence review
notebook/20_stage_checks/27_feature_extraction_test.ipynb
                                                             feature + side-role context review
notebook/20_stage_checks/30_visualization_test.ipynb             norm recording-view 10-rep
                                                             presentation playback
```

---

## 8. 향후 확장 (Planned Extensions)

- 논문용 figure export helper.
- Deduction과 withheld-feature를 나란히 보여주는 summary.
- Simulation runner가 생긴 뒤 robustness sensitivity figure.
- Set-level consistency review용 per-rep small multiples.
