"""
Statistical Anthropometric Model

Segment mass ratios and segment center-of-mass ratios from Winter (1990).

All ratios are dimensionless (whole-body mass = 1.0, segment length = 1.0).
Individual absolute values (kg, m) are not computed.

Reference:
  Winter, D.A. (1990). Biomechanics and Motor Control of Human Movement.
  Wiley-Interscience. Table 4.1.
"""
from __future__ import annotations


# ── Segment mass ratios (whole-body mass = 1.0) ───────────────────────────────
# Source: Winter (1990) Table 4.1, male/female average
SEGMENT_MASS_RATIO: dict[str, float] = {
    "head":          0.081,
    "trunk":         0.497,
    "upper_arm":     0.028,   # unilateral
    "forearm":       0.016,   # unilateral
    "hand":          0.006,   # unilateral
    "thigh":         0.100,   # unilateral
    "shank":         0.0465,  # unilateral
    "foot":          0.0145,  # unilateral
}

# ── Segment CoM position (ratio from proximal end) ────────────────────────────
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

# ── Segment ↔ landmark mapping (proximal, distal) ─────────────────────────────
# proximal endpoint → distal endpoint (normalized column names)
SEGMENT_ENDPOINTS: dict[str, tuple[str, str]] = {
    "left_upper_arm":  ("left_shoulder",  "left_elbow"),
    "right_upper_arm": ("right_shoulder", "right_elbow"),
    "left_forearm":    ("left_elbow",     "left_wrist"),
    "right_forearm":   ("right_elbow",    "right_wrist"),
    "left_thigh":      ("left_hip",       "left_knee"),
    "right_thigh":     ("right_hip",      "right_knee"),
    "left_shank":      ("left_knee",      "left_ankle"),
    "right_shank":     ("right_knee",     "right_ankle"),
    "trunk":           ("left_hip",       "left_shoulder"),   # center-line approximation
}

# ── Segment name → Winter segment name mapping ────────────────────────────────
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
    """Return segment mass ratio (whole-body mass = 1.0).

    Parameters
    ----------
    segment_name : str
        Key from SEGMENT_ENDPOINTS or a Winter segment name.

    Returns
    -------
    float
        Mass ratio (0 < value < 1).

    Raises
    ------
    KeyError
        Unknown segment name.
    """
    winter_name = SEGMENT_TO_WINTER.get(segment_name, segment_name)
    if winter_name not in SEGMENT_MASS_RATIO:
        raise KeyError(
            f"Unknown segment name: '{segment_name}'. "
            f"Available: {list(SEGMENT_MASS_RATIO.keys())}"
        )
    return SEGMENT_MASS_RATIO[winter_name]


def get_segment_com_ratio(segment_name: str) -> float:
    """Return segment CoM position ratio (from proximal end).

    Parameters
    ----------
    segment_name : str

    Returns
    -------
    float
        Position ratio (0 < value < 1).
    """
    winter_name = SEGMENT_TO_WINTER.get(segment_name, segment_name)
    if winter_name not in SEGMENT_COM_RATIO:
        raise KeyError(
            f"Unknown segment name: '{segment_name}'. "
            f"Available: {list(SEGMENT_COM_RATIO.keys())}"
        )
    return SEGMENT_COM_RATIO[winter_name]
