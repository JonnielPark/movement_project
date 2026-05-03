# 01. 데이터 형식 (Data Format)

본 문서는 분석 체계가 입력으로 받는 단일 비전 기반 3D 포즈 시계열 데이터의 형식을 정의한다.

> 용어는 [`_terminology.md`](_terminology.md)의 단일 정의를 따른다.

---

## 1. 입력 데이터 정의

본 프레임워크의 입력은 **단일 모바일 카메라 영상에서 포즈 추정 엔진을 거쳐 산출된 3D 포즈 시계열**이다. 연구계획서 §"연구 방법"에서 명시한 바와 같이, 본 연구는 단일 비전 환경의 가용성과 그 기술적 제약(랜드마크 누락, 심도 정보 불안정성 등)을 분석 체계 안에 명시적으로 둔다.

권장 포즈 추정 엔진은 iPIXEL EXERCITE이며, MediaPipe Pose 33 등 동등한 랜드마크 모델을 사용하는 출력도 본 형식으로 변환해 사용할 수 있다.

## 2. 필수 컬럼

각 CSV 파일은 다음 두 컬럼을 반드시 포함한다.

```text
frame
timestamp
```

- `frame` — 프레임 인덱스 (정수, 정렬 가능해야 함)
- `timestamp` — 각 프레임의 시간(초). 데이터 검증 단계에서 시간 차로 표본화 간격과 FPS를 추정한다.

## 3. 랜드마크 좌표 컬럼

각 랜드마크는 x, y, z 세 축의 컬럼을 갖는다.

```text
<landmark>_x
<landmark>_y
<landmark>_z
```

예:

```text
left_knee_x
left_knee_y
left_knee_z
```

랜드마크 명은 다음 코드 파일에서 정의한다.

```text
src/movement/config.py
```

명명 규약은 [`_terminology.md`](_terminology.md) §7을 따른다 (`left_*`, `right_*` 등).

## 4. 가시도 컬럼 (선택, 권장)

각 랜드마크에는 가시도 컬럼을 둘 수 있다.

```text
<landmark>_visibility
```

가시도 값은 ④ 전처리 단계에서 신뢰도 게이팅에 사용된다. 단일 비전 환경에서는 랜드마크가 누락되기보다는 **낮은 가시도로 보고되는 경우가 흔하므로**, 가시도 컬럼이 있을수록 전처리의 신뢰도 판정이 정확해진다.

## 5. CSV 예시

```text
frame,timestamp,nose_x,nose_y,nose_z,nose_visibility,left_shoulder_x,...
0,0.000,0.51,0.23,-0.12,0.98,0.42,...
1,0.033,0.52,0.24,-0.13,0.97,0.43,...
```

## 6. 현재 가정 사항

```text
1. 한 행은 한 프레임을 의미한다.
2. 각 랜드마크는 x, y, z 세 좌표를 가진다.
3. frame 값은 정렬되어 있거나 정렬 가능하다.
4. timestamp 값은 단조 증가한다.
5. 랜드마크 명은 src/movement/config.py의 정의와 일치한다.
```

위 가정 중 위반 사항이 있으면 ① 데이터 검증 단계에서 보고된다 ([`02_validation.md`](02_validation.md)).

## 7. 좌표계 / 단위 약속

- 입력 좌표는 포즈 추정 엔진이 산출한 원본 단위를 그대로 사용한다 (예: MediaPipe의 정규화 좌표).
- 본 프레임워크는 ⑤ 정규화 단계에서 별도의 신체 기준 좌표계로 변환한다 ([`06_normalization.md`](06_normalization.md)).
- 분석·논문에서 사용하는 모든 길이 비율은 무차원이며, 단위 표기는 `torso_length_ratio`로 통일한다.

## 8. 데이터 처리 윤리

연구·임상 데이터 보호 관행에 따라 다음을 커밋하지 않는다.

- 원본 영상 (raw video)
- 임상 데이터 / 식별 가능 데이터
- 사적 녹화물
- 사적 API 키
- IRB 제한 데이터셋
- 내부 SDK 파일

권장 비공개 폴더 (모두 `.gitignore`):

```text
data/raw/
data/private/
data/clinical/
data/videos/
```

공유 가능한 합성·시연 데이터에 한해 `data/sample/`에 둔다.
