"""
통계적 인체 계측 비율 (Anthropometric Model)

Winter (1990) 기준 분절 질량 비율과 분절 중심 위치 비율.

모든 비율은 무차원(전신 질량 = 1.0, 분절 길이 = 1.0 기준).
개인별 절대값(kg, m)을 산출하지 않는다.

Reference:
  Winter, D.A. (1990). Biomechanics and Motor Control of Human Movement.
  Wiley-Interscience. Table 4.1.
"""
from __future__ import annotations


# ── 분절 질량 비율 (전신 질량 = 1.0) ─────────────────────────────────────────
# 출처: Winter (1990) Table 4.1, 남녀 평균값
SEGMENT_MASS_RATIO: dict[str, float] = {
    "head":          0.081,
    "trunk":         0.497,
    "upper_arm":     0.028,   # 단측
    "forearm":       0.016,   # 단측
    "hand":          0.006,   # 단측
    "thigh":         0.100,   # 단측
    "shank":         0.0465,  # 단측
    "foot":          0.0145,  # 단측
}

# ── 분절 중심 위치 (근위단으로부터의 비율) ────────────────────────────────────
SEGMENT_COM_RATIO: dict[str, float] = {
    "head":      0.50,
    "trunk":     0.43,
    "upper_arm": 0.436,
    "forearm":   0.430,
    "hand":      0.506,
    "thigh":     0.433,
    "shank":     0.433,
    "foot":      0.50,
}

# ── 분절 ↔ 랜드마크 매핑 (proximal, distal) ───────────────────────────────────
# proximal endpoint → distal endpoint (정규화 컬럼명)
SEGMENT_ENDPOINTS: dict[str, tuple[str, str]] = {
    "left_upper_arm":  ("left_shoulder",  "left_elbow"),
    "right_upper_arm": ("right_shoulder", "right_elbow"),
    "left_forearm":    ("left_elbow",     "left_wrist"),
    "right_forearm":   ("right_elbow",    "right_wrist"),
    "left_thigh":      ("left_hip",       "left_knee"),
    "right_thigh":     ("right_hip",      "right_knee"),
    "left_shank":      ("left_knee",      "left_ankle"),
    "right_shank":     ("right_knee",     "right_ankle"),
    "trunk":           ("left_hip",       "left_shoulder"),   # 중심선 근사
}

# ── 분절명 → Winter 분절명 매핑 ───────────────────────────────────────────────
SEGMENT_TO_WINTER: dict[str, str] = {
    "left_upper_arm":  "upper_arm",
    "right_upper_arm": "upper_arm",
    "left_forearm":    "forearm",
    "right_forearm":   "forearm",
    "left_thigh":      "thigh",
    "right_thigh":     "thigh",
    "left_shank":      "shank",
    "right_shank":     "shank",
    "trunk":           "trunk",
}


def get_segment_mass_ratio(segment_name: str) -> float:
    """분절 질량 비율 반환 (전신 질량 = 1.0).

    Parameters
    ----------
    segment_name : str
        SEGMENT_ENDPOINTS의 키 또는 Winter 분절명.

    Returns
    -------
    float
        질량 비율 (0 < value < 1).

    Raises
    ------
    KeyError
        알 수 없는 분절명.
    """
    winter_name = SEGMENT_TO_WINTER.get(segment_name, segment_name)
    if winter_name not in SEGMENT_MASS_RATIO:
        raise KeyError(
            f"알 수 없는 분절명: '{segment_name}'. "
            f"사용 가능: {list(SEGMENT_MASS_RATIO.keys())}"
        )
    return SEGMENT_MASS_RATIO[winter_name]


def get_segment_com_ratio(segment_name: str) -> float:
    """분절 중심 위치 비율 반환 (근위단으로부터의 비율).

    Parameters
    ----------
    segment_name : str

    Returns
    -------
    float
        위치 비율 (0 < value < 1).
    """
    winter_name = SEGMENT_TO_WINTER.get(segment_name, segment_name)
    if winter_name not in SEGMENT_COM_RATIO:
        raise KeyError(
            f"알 수 없는 분절명: '{segment_name}'. "
            f"사용 가능: {list(SEGMENT_COM_RATIO.keys())}"
        )
    return SEGMENT_COM_RATIO[winter_name]
