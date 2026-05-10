# 00. 데이터 포맷 (Data Format)

**문서 버전:** 1.0.1  
**최종 갱신:** 2026-05-10  
**영문 동기화:** `docs_eng/pipeline/00_data_format.md`는 동일 버전의 영문 번역본이다.

단안(monocular) 3D 포즈 시계열 데이터의 입력 포맷 명세.

---

## 1. 입력 (Input)

포즈 추정 엔진에서 내보낸 CSV 파일. 현재 구현은 MediaPipe-style 33-landmark pose CSV를
입력 전제로 한다. 즉, 한 행(row)은 한 프레임에 해당하며, `frame` / `timestamp` 칼럼과
`src/movement/config.py`에 정의된 랜드마크 이름 기반 칼럼을 사용한다.

iPIXEL EXERCITE를 포함한 다른 엔진은 실제 export schema가 확보되기 전까지 future adapter
대상이다. 현재 파이프라인에 넣기 전에는 이 MediaPipe-style schema로 변환해야 한다.

## 2. 필수 칼럼 (Required Columns)

```text
frame        정수 프레임 인덱스 (정렬 가능, 단조 증가)
timestamp    녹화 시작 이후 경과 초 (float)
```

- `frame` — ① 검증 단계에서 연속성 및 중복 검사에 사용.
- `timestamp` — 샘플링 간격 및 FPS 추정에 사용.

## 3. 랜드마크 좌표 칼럼 (Landmark Coordinate Columns)

각 랜드마크는 3개의 좌표 칼럼을 갖는다:

```text
<landmark>_x
<landmark>_y
<landmark>_z
```

예시:

```text
left_knee_x
left_knee_y
left_knee_z
```

랜드마크 이름은 [src/movement/config.py](../../src/movement/config.py)에 정의되어 있다.
명명 규약: 양측 랜드마크는 `left_*` / `right_*` 접두사를 사용한다.

## 4. 가시성 칼럼 (Visibility Columns, 선택, 권장)

```text
<landmark>_visibility    float 0.0–1.0
```

④ 전처리(preprocessing)에서 신뢰도 게이팅(reliability gating)에 사용된다. 단안 데이터에서
랜드마크가 완전히 누락되는 경우는 드물고, 낮은 가시성으로 보고되는 경우가 더 흔하다.
가시성 칼럼을 포함하면 신뢰도 분류 정확도가 향상된다.

## 5. CSV 예시 (CSV Example)

```text
frame,timestamp,nose_x,nose_y,nose_z,nose_visibility,left_shoulder_x,...
0,0.000,0.51,0.23,-0.12,0.98,0.42,...
1,0.033,0.52,0.24,-0.13,0.97,0.43,...
```

샘플 파일: `data/pose/sample/mediapipe_squat_synthetic.csv`

## 6. 가정 (Assumptions)

```text
1. 한 행 = 한 프레임.
2. 각 랜드마크는 x, y, z 칼럼을 갖는다.
3. frame 값은 정렬 가능하다.
4. timestamp 값은 단조 증가한다.
5. 랜드마크 이름은 src/movement/config.py의 정의와 일치한다.
```

위반 사항은 ① 검증에서 보고된다 ([01_validation.md](01_validation.md) 참조).

## 7. 좌표 규약 (Coordinate Convention)

- 입력 좌표는 포즈 추정 엔진의 원시 단위로 들어온다
  (예: MediaPipe 정규화 이미지 좌표).
- ⑤ 정규화 단계에서 신체 상대 좌표계로 변환된다
  ([05_normalization.md](05_normalization.md) 참조).
- 이후 모든 피처와 바이오마커는 무차원 `torso_length_ratio` 단위 또는 도(degree)를 사용한다.
  절대 힘·길이 단위는 사용하지 않는다.

## 8. 데이터 관리 (Data Management)

`data/`는 분석 대상 CSV와 분석 정의 파일을 분리한다:

```text
data/pose/         관절 포인트 시계열 CSV
data/definitions/  운동 정의, 해석 규칙, 임상 매핑 YAML
data/reference/    합성 정상 베이스라인 등 기준 통계
data/processed/    파이프라인 산출물 (.gitignore)
```

원본 영상은 본 저장소의 분석 대상이 아니다. 공유 가능한 관절 포인트 CSV는
`data/pose/` 아래에 보관하되, 직접 식별자는 익명화한 뒤 커밋한다.
