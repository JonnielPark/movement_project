# 00. 데이터 포맷 (Data Format)

**문서 버전:** 1.1.0
**최종 갱신:** 2026-05-21
**영문 동기화:** `docs_eng/pipeline/00_data_format.md`는 동일 버전의 영문 번역본이다.

단안 3D pose time-series CSV 입력 규격.

---

## 1. 입력 계약 (Input Contract)

현재 pipeline은 MediaPipe-style 33-landmark CSV를 기대한다:

```text
one row = one frame
required scalar columns = frame, timestamp
coordinate columns = <landmark>_x, <landmark>_y, <landmark>_z
optional visibility columns = <landmark>_visibility
landmark names = src/movement/core/config.py
```

다른 engine은 실제 export schema가 확보되기 전까지 adapter 대상이다. 현재 pipeline에 넣기 전에
이 schema로 변환한다.

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
left_knee_visibility
```

Visibility는 권장한다. 단안 pose engine은 landmark를 완전히 누락하기보다 low-quality landmark로
반환하는 경우가 많다. ④ Preprocessing과 후속 reliability gate는 visibility metadata가 있으면 사용한다.

## 4. CSV 예시 (CSV Example)

```text
frame,timestamp,nose_x,nose_y,nose_z,nose_visibility,left_shoulder_x,...
0,0.000,0.51,0.23,-0.12,0.98,0.42,...
1,0.033,0.52,0.24,-0.13,0.97,0.43,...
```

Sample file:

```text
data/pose/sample/mediapipe_squat_synthetic.csv
```

## 5. 좌표와 단위 정책 (Coordinate And Unit Policy)

입력 좌표는 ⑤ Normalization 전까지 pose engine의 native coordinate convention을 유지한다.
후속 feature와 biomarker는 body-relative unit을 사용한다:

```text
torso_length_ratio
degree
dimensionless / dimensionless_cv
second
```

절대 힘, 토크, 질량, 물리 길이 출력은 사용하지 않는다.

## 6. 데이터 위치 (Data Locations)

```text
data/pose/          joint-point CSV input
data/definitions/   exercise definitions and interpretation YAML
data/protocols/     performance and camera protocol YAML
data/reference/     reference statistics
data/processed/     pipeline outputs; gitignored
```

Raw video는 이 repository의 analysis input이 아니다. 공유 가능한 입력은 비식별 joint-point CSV이다.
