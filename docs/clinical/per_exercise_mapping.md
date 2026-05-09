# 운동별 피처 × 임상적 의미 매핑 (Per-Exercise Feature × Clinical Meaning Mapping)

**문서 버전:** 1.0.0  
**최종 갱신:** 2026-05-06  
**영문 동기화:** `docs_eng/clinical/per_exercise_mapping.md`는 동일 버전의 영문 번역본이다.

**학위논문 §5.5 / §5.6.** 4개 검증 운동 전체의 활성 피처와 단위, 생체역학적 해석.

- 용어집: [`docs/terminology.md`](../terminology.md)
- 피처 추출 코드: [`src/movement/features/`](../../src/movement/features/)
- YAML 미러 (대시보드 툴팁): [`data/definitions/clinical/feature_meanings.yaml`](../../data/definitions/clinical/feature_meanings.yaml)
- 금지 어휘 규칙: [`docs/code_revision_plan.md §0`](../code_revision_plan.md) 원칙 4

---

## 표기 안내 (Notes)

| 용어 | 정의 |
|---|---|
| **rep** | 반복(repetition)당 1개 레코드 방출 (phase = None) |
| **rep / phase** | 추가로 (rep × phase)당 소문자 phase 접미사로 방출, 예: `spatial.rom.left_knee_angle.descent` |
| **set** | 세트 내 모든 반복을 포괄하는 1개 레코드 |
| **rep \*** | 템플릿: 반복당 1개 레코드; N = 반복 번호 (예: `temporal.tempo.rep_1`) |

구간(phase) 단위 변형은 `PHASE_AWARE_FEATURE_FAMILIES` (`spatial.rom`, `spatial.shape`,
`control.stability`)에 속한 피처에서만 방출된다. 보상(compensation) 피처는 후보 규칙이
전체 반복 궤적 위에서 동작하므로 반복 단위 전용이다.

**구현된** 보상 규칙만 나열한다. 운동 YAML의 후보 중 `COMPENSATION_RULES`에 매칭 항목이
없는 것은 런타임에 `UserWarning`을 발생시키며 본 표에서 생략된다.

---

## Squat (스쿼트)

| feature_id | domain | unit | level | clinical_meaning |
|---|---|---|---|---|
| `spatial.rom.left_hip_angle` | spatial | degree | rep / phase | 좌측 엉덩이 시상면 ROM (끼인각 max − min). 제한된 ROM은 엉덩이 굴근(hip-flexor) 신장성 제한 또는 통증 회피 가드를 반영할 수 있다. |
| `spatial.rom.right_hip_angle` | spatial | degree | rep / phase | 우측 엉덩이 시상면 ROM; 단측 엉덩이 가동성 제한 검출을 위해 좌측과 비교한다. |
| `spatial.rom.left_knee_angle` | spatial | degree | rep / phase | 좌측 무릎 시상면 ROM. 감소된 ROM은 하강 깊이를 제한하는 대퇴사두근(quadriceps) 또는 햄스트링 강직(stiffness)의 흔한 지표이다. |
| `spatial.rom.right_knee_angle` | spatial | degree | rep / phase | 우측 무릎 시상면 ROM; 양측 비교는 부하 회피 비대칭을 드러낸다. |
| `spatial.rom.left_ankle_angle` | spatial | degree | rep / phase | 좌측 발목 발등굽힘(dorsiflexion) ROM. 발등굽힘은 스쿼트 깊이와 발뒤꿈치 접지에 대한 일차 구조적 제약이다. |
| `spatial.rom.right_ankle_angle` | spatial | degree | rep / phase | 우측 발목 발등굽힘 ROM; 좌측과의 비대칭은 보상적 체간(trunk) 기울기 또는 발뒤꿈치 들림(heel lift)을 유발하는 경우가 많다. |
| `spatial.symmetry.hip` | spatial | dimensionless_cv | rep | 좌·우 엉덩이 ROM 대칭 지수 (0 = 완전 대칭; 클수록 비대칭). 지속적 비대칭은 더 가동성이 큰 측으로의 보상 부하를 시사한다. |
| `spatial.symmetry.knee` | spatial | dimensionless_cv | rep | 좌·우 무릎 ROM 대칭 지수. 양측 무릎 가동성 불균형은 변경된 스쿼트 역학에서 인지된 패턴이다. |
| `spatial.symmetry.ankle` | spatial | dimensionless_cv | rep | 좌·우 발목 ROM 대칭 지수. 발목 가동성 비대칭은 보상적 발뒤꿈치 들림 또는 측방 골반 이동의 기저인 경우가 많다. |
| `spatial.shape.arc_length.left_hip` | spatial | torso_length_ratio | rep / phase | 좌측 엉덩이 관절 궤적의 호 길이. 긴 호는 측방 또는 전방 흔들림을 시사하여 비수직 CoM 하강을 의미한다. |
| `spatial.shape.arc_length.right_hip` | spatial | torso_length_ratio | rep / phase | 우측 엉덩이 궤적 호 길이; 비대칭 엉덩이 흔들림 검출을 위해 좌측과 비교한다. |
| `spatial.shape.arc_length.left_knee` | spatial | torso_length_ratio | rep / phase | 좌측 무릎 궤적 호 길이. 높은 값은 보상적 전방 또는 측방 무릎 트래킹 편차를 시사한다. |
| `spatial.shape.arc_length.right_knee` | spatial | torso_length_ratio | rep / phase | 우측 무릎 궤적 호 길이; 단측 트래킹 편차 검출을 위해 양측 비교. |
| `spatial.shape.arc_length.left_ankle` | spatial | torso_length_ratio | rep / phase | 좌측 발목 궤적 호 길이. 최소가 아닌 값은 발 굴림(foot roll) 또는 일시적 발뒤꿈치 들림 에피소드를 시사한다. |
| `spatial.shape.arc_length.right_ankle` | spatial | torso_length_ratio | rep / phase | 우측 발목 궤적 호 길이; 단측 발 불안정성 검출을 위해 좌측과 비교. |
| `spatial.phase_rom_ratio.descent_ascent` | spatial | dimensionless | rep | 평균 Descent ROM 대 평균 Ascent ROM의 비율. 1을 초과하는 값은 복귀 phase보다 부하 수용(하강) 동안 더 큰 가동범위를 시사한다. |
| `temporal.tempo.rep_*` | temporal | second | rep | 각 개별 반복의 지속 시간. 반복 간 급격한 변화는 페이싱 불안정 또는 피로 주도 템포 drift를 시사한다. |
| `temporal.variability.tempo_cv` | temporal | dimensionless_cv | set | 세트 내 반복 지속 시간의 변동 계수(CV). 높은 값은 일관성 없는 동작 템포를 시사하여, 다른 지표의 세트 내 비교 가능성을 떨어뜨린다. |
| `control.stability.hip_center_x_std` | control | torso_length_ratio | rep / phase | 골반 중심 측방 변위의 표준편차. 명목상 수직 부하 과제에서 높은 값은 측방 CoM 불안정성을 시사한다. |
| `control.stability.hip_center_z_std` | control | torso_length_ratio | rep / phase | 골반 중심 수직 변위의 표준편차. 하강/상승 궤적의 평활도를 반영하며, 높은 변동성은 운동 제어 비일관성을 시사한다. |
| `control.compensation.knee_valgus.left` | control | torso_length_ratio | rep | 관상면 hip-ankle 라인 대비 좌측 무릎 내측 편차 피크. 외반(valgus) 붕괴는 부하 시 엉덩이 외전근(hip-abductor) 활성 부족을 시사한다. |
| `control.compensation.knee_valgus.right` | control | torso_length_ratio | rep | 우측 무릎 내측 편차 피크. 좌·우 비대칭 외반은 단측 엉덩이 외전근 요구 또는 구조적 차이를 가리킨다. |
| `control.compensation.knee_varus.left` | control | torso_length_ratio | rep | 좌측 무릎 외측 편차 피크. 내반(varus) 경향은 IT-band 강직, 넓은 스탠스 역학, 또는 보상적 buttressing을 반영할 수 있다. |
| `control.compensation.knee_varus.right` | control | torso_length_ratio | rep | 우측 무릎 외측 편차 피크; 양측 비교는 구조적 내반과 단측 보상을 구분한다. |
| `control.compensation.excessive_trunk_flexion` | control | degree | rep | 수직축 대비 체간 기울기 피크. 과도한 전방 기울기는 무릎 신근 메커니즘에서 엉덩이와 요추로 부하를 재분배한다. |
| `control.compensation.lateral_pelvic_shift` | control | torso_length_ratio | rep | 반복 평균 베이스라인 대비 측방 골반 변위 피크. 흔히 단측 엉덩이 또는 발목 가동성 제한에 후속하는 체중 이동 보상을 시사한다. |
| `control.compensation.heel_lift.left` | control | torso_length_ratio | rep | 반복 최저 발뒤꿈치 높이 위로의 좌측 발뒤꿈치 들림 피크. 제한된 발목 발등굽힘을 보상하고 forefoot 부하를 증가시켜 무릎 트래킹 역학을 변경한다. |
| `control.compensation.heel_lift.right` | control | torso_length_ratio | rep | 우측 발뒤꿈치 들림 피크; 단측 발목 발등굽힘 제한 검출을 위해 좌측과 비교. |
| `control.compensation.pelvic_rotation` | control | torso_length_ratio | rep | 좌·우 엉덩이 깊이 비대칭 피크 (횡단면 프록시). 0이 아닌 값은 코어 안정성 제한 또는 단측 사지 보상을 반영할 수 있는 골반 회전을 시사한다. |

---

## Lunge (런지)

| feature_id | domain | unit | level | clinical_meaning |
|---|---|---|---|---|
| `spatial.rom.left_hip_angle` | spatial | degree | rep / phase | split-stance 자세에서의 좌측 엉덩이 시상면 ROM. 앞다리(forward leg)의 감소된 ROM은 하강 깊이를 제한할 수 있고, 뒷다리(rear leg)에서는 엉덩이 굴근 신장성을 반영한다. |
| `spatial.rom.right_hip_angle` | spatial | degree | rep / phase | 우측 엉덩이 시상면 ROM; 부하 다리와 trailing 다리는 반복마다 교대되므로 측 × 반복 상호작용이 중요하다. |
| `spatial.rom.left_knee_angle` | spatial | degree | rep / phase | 좌측 무릎 시상면 ROM. 런지에서 앞다리 무릎 ROM 감소는 종종 과도한 체간 기울기 또는 발뒤꿈치 들림과 함께 나타난다. |
| `spatial.rom.right_knee_angle` | spatial | degree | rep / phase | 우측 무릎 시상면 ROM; 앞다리와 trailing 다리 사이의 비대칭은 사지 간 부하 전략을 반영한다. |
| `spatial.rom.left_ankle_angle` | spatial | degree | rep / phase | 좌측 발목 발등굽힘 ROM. 런지에서 앞다리 발목 제한은 보상적 체간 기울기의 일차 동인이다. |
| `spatial.rom.right_ankle_angle` | spatial | degree | rep / phase | 우측 발목 발등굽힘 ROM; trailing 다리 발목 ROM은 후족부 위치와 엉덩이 신전 역량을 결정한다. |
| `spatial.symmetry.hip` | spatial | dimensionless_cv | rep | 세트 전 반복에 걸친 좌·우 엉덩이 ROM 대칭 지수. 지속적 비대칭은 우세 사지와 비우세 사지 간의 단측 부하 선호를 시사한다. |
| `spatial.symmetry.knee` | spatial | dimensionless_cv | rep | 좌·우 무릎 ROM 대칭 지수. 런지의 양측 무릎 가동성 불균형은 교대 부하 패턴에 의해 증폭된다. |
| `spatial.symmetry.ankle` | spatial | dimensionless_cv | rep | 좌·우 발목 ROM 대칭 지수. split-stance 운동에서 발목 비대칭은 가시적인 골반 보상을 만드는 경향이 있다. |
| `spatial.shape.arc_length.left_hip` | spatial | torso_length_ratio | rep / phase | 좌측 엉덩이 궤적의 호 길이. 런지에서 높은 값은 과도한 전후방 흔들림 또는 측방 체간 기울기를 시사한다. |
| `spatial.shape.arc_length.right_hip` | spatial | torso_length_ratio | rep / phase | 우측 엉덩이 궤적의 호 길이; 좌측과의 비대칭은 교대 반복에 걸친 부하 불균형을 반영한다. |
| `spatial.shape.arc_length.left_knee` | spatial | torso_length_ratio | rep / phase | 좌측 무릎 궤적의 호 길이. 높은 호는 split-stance 부하 phase 동안의 내·외측 무릎 불안정성을 시사한다. |
| `spatial.shape.arc_length.right_knee` | spatial | torso_length_ratio | rep / phase | 우측 무릎 궤적의 호 길이; 단측 무릎 트래킹 편차 검출을 위해 좌측과 비교. |
| `spatial.shape.arc_length.left_ankle` | spatial | torso_length_ratio | rep / phase | 좌측 발목 궤적의 호 길이. 최소가 아닌 값은 하강 동안의 발 굴림 또는 접촉 불안정성을 시사한다. |
| `spatial.shape.arc_length.right_ankle` | spatial | torso_length_ratio | rep / phase | 우측 발목 궤적의 호 길이; 단측 발 위치 불안정성 검출을 위해 양측 비교. |
| `spatial.phase_rom_ratio.descent_ascent` | spatial | dimensionless | rep | 평균 Descent ROM 대 평균 Ascent ROM 비율. 1 초과 값은 부하 수용 ROM이 회복 ROM보다 큼을 시사하여 braking 우위 역학을 가리킨다. |
| `temporal.tempo.rep_*` | temporal | second | rep | 각 개별 반복의 지속 시간. 좌·우 반복 지속 시간이 비교되어야 하는 교대 운동에서 반복 간 변동성이 특히 의미 있다. |
| `temporal.variability.tempo_cv` | temporal | dimensionless_cv | set | 세트 내 반복 지속 시간의 변동 계수. 높은 값은 교대 사지 타이밍 비대칭 또는 피로 효과를 시사할 수 있다. |
| `control.stability.hip_center_x_std` | control | torso_length_ratio | rep / phase | 골반 중심 측방 변위의 표준편차. 런지에서 높은 값은 split-stance 전환 중 빈약한 내·외측 CoM 제어를 반영한다. |
| `control.stability.hip_center_z_std` | control | torso_length_ratio | rep / phase | 골반 중심 수직 변위의 표준편차. 시상면에서 하강/상승 궤적의 평활도를 반영. |
| `control.compensation.knee_valgus.left` | control | torso_length_ratio | rep | 관상면 hip-ankle 라인 대비 좌측 무릎 내측 편차 피크. 런지에서 외반은 앞다리의 고부하 하강 phase에서 더 발생하기 쉽다. |
| `control.compensation.knee_valgus.right` | control | torso_length_ratio | rep | 우측 무릎 내측 편차 피크. 교대 반복에서 좌·우 비교는 사지 간 외반 비대칭을 정량화한다. |
| `control.compensation.excessive_trunk_flexion` | control | degree | rep | 수직축 대비 체간 기울기 피크. 런지에서 과도한 기울기는 종종 앞다리 발목 발등굽힘 제한에 대한 2차 보상이다. |
| `control.compensation.lateral_pelvic_shift` | control | torso_length_ratio | rep | 반복 평균 베이스라인 대비 측방 골반 변위 피크. split-stance에서 측방 이동은 지지 기저면 위에서 골반 정렬을 유지하기 어려움을 시사한다. |
| `control.compensation.heel_lift.left` | control | torso_length_ratio | rep | 반복 최저점 위로의 좌측 발뒤꿈치 들림 피크. 런지에서 앞다리 발뒤꿈치 들림은 발목 발등굽힘 제한을 시사하고; trailing 다리 발뒤꿈치 들림은 하강 동안 통상 기대된다. |
| `control.compensation.heel_lift.right` | control | torso_length_ratio | rep | 우측 발뒤꿈치 들림 피크; 컨텍스트(앞다리 vs trailing 다리)는 교대 어노테이션으로부터 추론되어야 한다. |

---

## Pike Push-up (파이크 푸쉬업)

| feature_id | domain | unit | level | clinical_meaning |
|---|---|---|---|---|
| `spatial.rom.left_shoulder_angle` | spatial | degree | rep / phase | 좌측 어깨 시상면 ROM (hip–shoulder–elbow 각, 정점은 어깨). 제한된 ROM은 부하 시 어깨 굴곡(shoulder-flexion) 범위 제한을 반영한다. |
| `spatial.rom.right_shoulder_angle` | spatial | degree | rep / phase | 우측 어깨 시상면 ROM; 양측 어깨 가동성 비대칭 검출을 위해 좌측과 비교. |
| `spatial.rom.left_elbow_angle` | spatial | degree | rep / phase | 좌측 팔꿈치 시상면 ROM. 제한된 팔꿈치 ROM은 머리 하강을 제한하며 팔꿈치 굴근 근력 또는 가동성 제한을 시사할 수 있다. |
| `spatial.rom.right_elbow_angle` | spatial | degree | rep / phase | 우측 팔꿈치 시상면 ROM; 양측 비교는 팔꿈치에서의 측방 부하 비대칭을 드러낸다. |
| `spatial.rom.left_hip_angle` | spatial | degree | rep / phase | piked 자세에서의 좌측 엉덩이 각. 변동은 push 동작 동안 골반 기울기 전략과 체간 강성을 반영한다. |
| `spatial.rom.right_hip_angle` | spatial | degree | rep / phase | 우측 엉덩이 각; 양측 비교는 역방향 지지 동안의 골반 비대칭을 검출한다. |
| `spatial.symmetry.shoulder` | spatial | dimensionless_cv | rep | 좌·우 어깨 ROM 대칭 지수. 비대칭은 양팔 사이의 불균등한 부하 분포를 시사하며, 어깨 과사용 위험 인자이다. |
| `spatial.symmetry.elbow` | spatial | dimensionless_cv | rep | 좌·우 팔꿈치 ROM 대칭 지수. 팔꿈치 비대칭은 종종 어깨 비대칭과 함께 나타나며 손 위치 보상을 반영한다. |
| `spatial.symmetry.hip` | spatial | dimensionless_cv | rep | piked 자세에서 좌·우 엉덩이 각 대칭 지수. 0이 아닌 값은 역방향 지지 phase 동안의 골반 측방 기울기를 시사. |
| `spatial.shape.arc_length.left_shoulder` | spatial | torso_length_ratio | rep / phase | 좌측 어깨 궤적의 호 길이. 높은 호는 순수 시상면 하강이 아닌 견갑(scapular) winging 또는 어깨 붕괴를 시사. |
| `spatial.shape.arc_length.right_shoulder` | spatial | torso_length_ratio | rep / phase | 우측 어깨 궤적의 호 길이; 좌측과의 비대칭은 단측 견갑 불안정성을 드러낸다. |
| `spatial.shape.arc_length.left_elbow` | spatial | torso_length_ratio | rep / phase | 좌측 팔꿈치 궤적의 호 길이. 비선형 경로는 push phase 동안의 elbow-flare 또는 inward-drift 보상을 시사. |
| `spatial.shape.arc_length.right_elbow` | spatial | torso_length_ratio | rep / phase | 우측 팔꿈치 궤적의 호 길이; 양측 비교는 비대칭 팔꿈치 트래킹을 검출. |
| `spatial.shape.arc_length.left_wrist` | spatial | torso_length_ratio | rep / phase | 좌측 손목 궤적의 호 길이. 손목 호는 손 위치 안정성을 반영; 높은 값은 접촉점 drift를 시사. |
| `spatial.shape.arc_length.right_wrist` | spatial | torso_length_ratio | rep / phase | 우측 손목 궤적의 호 길이; 비대칭 손 접촉 불안정성 검출을 위해 좌측과 비교. |
| `spatial.phase_rom_ratio.descent_ascent` | spatial | dimensionless | rep | 평균 Descent ROM 대 평균 Ascent ROM 비율. 1 초과 값은 원심성(eccentric, lowering) phase 동안 더 큰 범위를 시사하여 통제된 하강 전략을 반영. |
| `temporal.tempo.rep_*` | temporal | second | rep | 각 개별 반복의 지속 시간. 파이크 푸쉬업에서 느린 반복은 긴장 시간을 늘리고; 급격한 단축은 피로 관련 폼 붕괴를 시사. |
| `temporal.variability.tempo_cv` | temporal | dimensionless_cv | set | 세트 내 반복 지속 시간의 변동 계수. 상체 push 과제의 시간적 비일관성은 종종 폼 악화에 선행. |
| `control.stability.hip_center_x_std` | control | torso_length_ratio | rep / phase | 골반 중심 측방 변위의 표준편차. piked 자세에서 측방 엉덩이 흔들림은 상체 push 동안의 체간 또는 코어 불안정성을 시사. |
| `control.stability.hip_center_z_std` | control | torso_length_ratio | rep / phase | piked 자세에서 골반 중심 수직 변위의 표준편차. push 사이클 동안 엉덩이 위치가 얼마나 잘 유지되는지 반영. |

> **참고 — 보류 중인 보상 피처.** 다음 파이크 푸쉬업 후보들은 운동 YAML에 등록되어 있으나
> 아직 `COMPENSATION_RULES`에 구현된 규칙이 없다:
> `elbow_flare`, `elbow_asymmetry`, `shoulder_asymmetry`, `shoulder_collapse`,
> `shoulder_elevation_compensation`, `scapular_instability_proxy`, `insufficient_head_descent`,
> `head_forward_shift`, `hip_drop`, `hip_pike`, `lateral_trunk_lean`.
> 규칙 구현 시 본 표에 추가될 예정.

---

## Plank Shoulder Tap (플랭크 숄더탭)

| feature_id | domain | unit | level | clinical_meaning |
|---|---|---|---|---|
| `spatial.rom.left_shoulder_angle` | spatial | degree | rep / phase | plank 자세에서의 좌측 어깨 각 (hip–shoulder–elbow). 반복 간 변동은 anti-rotation 과제 동안의 체간 위치 drift를 시사. |
| `spatial.rom.right_shoulder_angle` | spatial | degree | rep / phase | 우측 어깨 각; 양측 비교는 교대 탭 동안의 비대칭 견갑 부하를 검출. |
| `spatial.rom.left_elbow_angle` | spatial | degree | rep / phase | plank-support 자세에서의 좌측 팔꿈치 각. 팔꿈치 각 변동은 반대측 탭 phase 동안 지지 팔의 안정성을 반영. |
| `spatial.rom.right_elbow_angle` | spatial | degree | rep / phase | 우측 팔꿈치 각; 비대칭 지지 팔 역학 검출을 위해 좌측과 비교. |
| `spatial.rom.left_hip_angle` | spatial | degree | rep / phase | plank 자세에서의 좌측 엉덩이 각. phase에 걸친 변화는 코어 안정성이 손상될 때 엉덩이 굴곡 보상을 시사. |
| `spatial.rom.right_hip_angle` | spatial | degree | rep / phase | 우측 엉덩이 각; 양측 비교는 한 손이 떨어진 지지 동안의 골반 측방 기울기를 검출. |
| `spatial.symmetry.shoulder` | spatial | dimensionless_cv | rep | 모든 반복에 걸친 좌·우 어깨 각 대칭 지수. 비대칭은 지지 팔과 탭 팔 사이의 불균등한 견갑 부하를 시사. |
| `spatial.symmetry.elbow` | spatial | dimensionless_cv | rep | 좌·우 팔꿈치 각 대칭 지수. plank에서 팔꿈치 비대칭은 종종 측방 CoM 이동에서의 보상적 팔꿈치 재배치를 반영. |
| `spatial.symmetry.hip` | spatial | dimensionless_cv | rep | 좌·우 엉덩이 각 대칭 지수. 0이 아닌 값은 본 운동에서 흔한 체간 불안정성 보상인 지속적 골반 기울기를 시사. |
| `spatial.shape.arc_length.left_wrist` | spatial | torso_length_ratio | rep / phase | 좌측 손목 궤적의 호 길이. 좌측 탭 반복 동안 활성 손목이 더 큰 호를 가져야 하며; 지지 손목에서 높은 값은 접촉 불안정성을 시사. |
| `spatial.shape.arc_length.right_wrist` | spatial | torso_length_ratio | rep / phase | 우측 손목 궤적의 호 길이; 반복마다 어느 측이 탭 손인지 확인하기 위해 좌측과 비교. |
| `spatial.shape.arc_length.left_shoulder` | spatial | torso_length_ratio | rep / phase | 좌측 어깨 궤적의 호 길이. 관상면에서 큰 호는 탭 동안의 측방 체간 기울기 보상을 시사. |
| `spatial.shape.arc_length.right_shoulder` | spatial | torso_length_ratio | rep / phase | 우측 어깨 궤적의 호 길이; 양측 비교는 교대 사지 부하로 유발된 비대칭 체간 흔들림을 검출. |
| `temporal.tempo.rep_*` | temporal | second | rep | 각 개별 탭 사이클의 지속 시간. 리듬 일관성은 본 anti-rotation 안정성 과제의 핵심 품질 지표. |
| `temporal.variability.tempo_cv` | temporal | dimensionless_cv | set | 탭 사이클 지속 시간의 변동 계수. 높은 변동성은 anti-rotation 요구 하에 안정된 동작 리듬을 유지하는 데 어려움을 시사. |
| `control.stability.hip_center_x_std` | control | torso_length_ratio | rep / phase | 골반 중심 측방 변위의 표준편차. 본 운동의 일차 안정성 지표; 높은 값은 탭 동안 내·외측 CoM 이동을 통제하지 못함을 직접 반영. |
| `control.stability.hip_center_z_std` | control | torso_length_ratio | rep / phase | plank 자세에서 골반 중심 수직 변위의 표준편차. 0이 아닌 변동은 종종 hip-drop 또는 hip-lift 보상에 후속하는 수직 체간 진동을 시사. |
| `control.compensation.pelvic_rotation` | control | torso_length_ratio | rep | 좌·우 엉덩이 깊이 비대칭 피크 (횡단면 프록시). 본 운동에서 골반 회전은 anti-rotation 코어 제어 부족에 대한 가장 직접적인 보상. |
| `control.compensation.lateral_pelvic_shift` | control | torso_length_ratio | rep | 반복 평균 베이스라인 대비 측방 골반 변위 피크. 한 손 떨어진 phase 동안 체중이 지지 팔 쪽으로 측방 이동하는 정도를 반영. |

> **참고 — 보류 중인 보상 피처.** 다음 플랭크 숄더탭 후보들은 운동 YAML에 등록되어 있으나
> 아직 `COMPENSATION_RULES`에 구현된 규칙이 없다:
> `trunk_rotation`, `lateral_trunk_lean`, `hip_drop`, `shoulder_collapse`, `shoulder_asymmetry`,
> `excessive_com_lateral_shift`, `excessive_com_variability`, `left_right_timing_variability`,
> `phase_timing_asymmetry`, `movement_discontinuity`.
> 규칙 구현 시 본 표에 추가될 예정.

---

## 운동 간 요약 (Cross-Exercise Summary)

| feature_id 접두어 | 활성 운동 | 도메인 | 비고 |
|---|---|---|---|
| `spatial.rom.*` | 4종 전체 | spatial | 관절은 운동에 따라 다름 (squat/lunge는 하체; pike_pushup / plank_shoulder_tap은 상체 + 엉덩이) |
| `spatial.symmetry.*` | 4종 전체 | spatial | 짝은 `angle_definitions`의 `left_` / `right_` 항목에서 도출 |
| `spatial.shape.arc_length.*` | 4종 전체 | spatial | 관절은 `landmarks.primary_joints`에서; 운동에 따라 다름 |
| `spatial.phase_rom_ratio.descent_ascent` | squat, lunge, pike_pushup | spatial | plank_shoulder_tap에서는 방출되지 않음 (phases: Lift / Tap / Return) |
| `temporal.tempo.rep_*` | 4종 전체 | temporal | |
| `temporal.variability.tempo_cv` | 4종 전체 | temporal | ≥ 2 반복 필요 |
| `control.stability.hip_center_x_std` | 4종 전체 | control | CoM 측방 안정성 프록시 |
| `control.stability.hip_center_z_std` | 4종 전체 | control | CoM 수직 안정성 프록시 |
| `control.compensation.knee_valgus.*` | squat, lunge | control | 하체 관상면 보상 |
| `control.compensation.knee_varus.*` | squat | control | 하체 외측 무릎 편차 |
| `control.compensation.excessive_trunk_flexion` | squat, lunge | control | 체간 기울기 보상 (직립 운동) |
| `control.compensation.lateral_pelvic_shift` | squat, lunge, plank_shoulder_tap | control | |
| `control.compensation.heel_lift.*` | squat, lunge | control | 발목 발등굽힘 제한 프록시 |
| `control.compensation.pelvic_rotation` | squat, plank_shoulder_tap | control | 횡단면 골반 비대칭 프록시 |
