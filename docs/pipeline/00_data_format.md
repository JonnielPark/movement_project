# 00. 데이터 포맷 (Data Format)

**문서 버전:** 1.2.3
**최종 갱신:** 2026-09-10
**영문 동기화:** `docs_eng/pipeline/00_data_format.md`는 동일 버전의 영문 번역본이다.

단안 3D pose time-series CSV 입력 규격.

---

## 1. 입력 계약 (Input Contract)

현재 pipeline은 MediaPipe-style 33-landmark CSV를 기대한다:

```text
one row = one frame
required scalar columns = frame, timestamp
coordinate columns = <landmark>_x, <landmark>_y, <landmark>_z
optional confidence columns = <landmark>_confidence
landmark names = src/movement/core/config.py
```

다른 engine은 실제 export schema가 확보되기 전까지 adapter 대상이다. 현재 pipeline에 넣기 전에
이 schema로 변환한다.

YOLOv11 같은 향후 pose engine은 운동별 예외 처리로 넣지 않고 pose-backend adapter를 통해
들어오게 한다. Adapter는 native keypoint를 pipeline landmark schema로 mapping하고, native
confidence를 confidence 또는 confidence provenance로 변환하며, engine name, model version,
coordinate convention, depth availability 같은 source metadata를 기록할 수 있다. Engine이
native depth를 제공하지 않는다면 depth를 신뢰 가능한 evidence로 합성하지 않는다. 대신
depth-dependent downstream record에는 unavailable 또는 low-confidence provenance를 남기고,
추후 scoring policy가 해당 source를 명시적으로 지원할 때까지 score evidence로 승격하지 않는다.

MediaPipe 기반 분석과 점수화가 안정화된 뒤에는 같은 exercise definition을 사용해 MediaPipe와
YOLOv11 output을 비교하는 engineering model-dependence study를 수행할 수 있다. 비교 항목은
운동 정의와 canonicalization evidence가 backend별 evidence availability, confidence,
`quality_gravity`, report-local burden/residual 진단값, feature sensitivity를 얼마나 바꾸는지다.
이를 clinical validation이나 특정 pose engine이 생체역학적으로 정답이라는 증명으로 표현하지 않는다.

## 2. 필수 칼럼 (Required Columns)

```text
frame        integer frame index; sortable and monotonically increasing
timestamp    seconds since recording start; float
```

① Validation은 이 칼럼을 duplicate/gap check와 FPS estimation에 사용한다.

## 3. Landmark Columns

예시:

```text
left_knee_x
left_knee_y
left_knee_z
left_knee_confidence
```

confidence는 권장한다. 단안 pose engine은 landmark를 완전히 누락하기보다 low-quality landmark로
반환하는 경우가 많다. ④ Preprocessing과 후속 reliability gate는 confidence metadata가 있으면 사용한다.

## 4. CSV 예시 (CSV Example)

```text
frame,timestamp,nose_x,nose_y,nose_z,nose_confidence,left_shoulder_x,...
0,0.000,0.51,0.23,-0.12,0.98,0.42,...
1,0.033,0.52,0.24,-0.13,0.97,0.43,...
```

Sample file:

```text
data/pose/sample/mediapipe_squat_demo_10rep_output_pose.csv
data/pose/sample/mediapipe_squat_demo_10rep_annotation.csv
data/examples/participants/demo_squat_10rep.yaml
```

## 5. Participant Analysis Metadata YAML

Participant profile YAML은 선택적인 analysis metadata다. 이는 IRB 대상자 등록부나 동의/철회
기록이 아니며, pose 분석 재현성에 필요한 비식별 실행 조건만 담는다. 이름, 생년월일, 연락처,
연구번호, 원본 영상 참조 같은 직접 또는 연결 식별자는 포함하지 않는다.

권장 위치:

```text
data/private/participants/<scope>/<participant_id>.yaml       실제 참여자 유래 로컬 metadata
data/examples/participants/<example_id>.yaml                  synthetic/demo 예시
```

최소 schema:

```yaml
participant_profile:
  schema_version: "0.1.0"
  participant_id: demo_subject_001
  anthropometry:
    sex: male
    height_cm: 175
    height_bin: 171-175cm
  common_subject_skeleton:
    profile_id: male_175cm
    matrix_path: data/reference/anthropometry/common_subject_skeleton_matrix.yaml
    model_path: data/reference/anthropometry/common_subject_skeleton_male_175cm.yaml
  policy:
    deidentified: true
    used_for_scoring: false
```

현재 단계에서 participant YAML은 provenance와 review input일 뿐이다. Height는 pose 좌표를
cm/m로 rescale하는 데 사용하지 않으며, common-subject skeleton은 subject-specific body
reconstruction이 아니다.

실제 참여자 유래 profile 또는 pose CSV는 비식별 처리되어 있어도 Git에 커밋하지 않는다.

## 6. 좌표와 단위 정책 (Coordinate And Unit Policy)

입력 좌표는 ⑤ Normalization 전까지 pose engine의 native coordinate convention을 유지한다.
후속 feature와 biomarker는 body-relative unit을 사용한다:

```text
torso_length_ratio
degree
dimensionless / dimensionless_cv
second
```

절대 힘, 토크, 질량, 물리 길이 출력은 사용하지 않는다.

## 7. 데이터 위치 (Data Locations)

```text
data/pose/sample/   synthetic/demo joint-point CSV input
data/examples/participants/ synthetic/demo participant profile YAML
data/pose/mediapipe/ 로컬 pose-backend export; 실제 참여자 유래 파일은 commit 대상 아님
data/private/       로컬/private 분석 metadata와 실제 참여자 유래 파일; gitignored
data/definitions/   exercise definitions and interpretation YAML
data/protocols/     performance and camera protocol YAML
data/reference/     reference statistics
data/processed/     pipeline outputs; gitignored
```

Raw video는 이 repository의 analysis input이 아니다. 공유 가능한 입력은 synthetic/demo 또는
명시적으로 공개 가능한 joint-point CSV로 제한한다. 실제 참여자 유래 pose CSV는 비식별 상태라도
별도 접근통제 저장소에서 관리한다.
