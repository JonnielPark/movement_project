"""
MediaPipe Pose configuration

- LANDMARKS: 33 pose landmarks
- CONNECTIONS: skeleton structure
"""

# 33 MediaPipe Pose landmarks
LANDMARKS = [
    "nose",
    "left_eye_inner",
    "left_eye",
    "left_eye_outer",
    "right_eye_inner",
    "right_eye",
    "right_eye_outer",
    "left_ear",
    "right_ear",
    "mouth_left",
    "mouth_right",
    "left_shoulder",
    "right_shoulder",
    "left_elbow",
    "right_elbow",
    "left_wrist",
    "right_wrist",
    "left_pinky",
    "right_pinky",
    "left_index",
    "right_index",
    "left_thumb",
    "right_thumb",
    "left_hip",
    "right_hip",
    "left_knee",
    "right_knee",
    "left_ankle",
    "right_ankle",
    "left_heel",
    "right_heel",
    "left_foot_index",
    "right_foot_index",
]


# Skeleton connections (MediaPipe style)
CONNECTIONS = [
    # Face
    ("nose", "left_eye_inner"),
    ("left_eye_inner", "left_eye"),
    ("left_eye", "left_eye_outer"),
    ("left_eye_outer", "left_ear"),
    ("nose", "right_eye_inner"),
    ("right_eye_inner", "right_eye"),
    ("right_eye", "right_eye_outer"),
    ("right_eye_outer", "right_ear"),
    ("mouth_left", "mouth_right"),
    # Torso
    ("left_shoulder", "right_shoulder"),
    ("left_shoulder", "left_hip"),
    ("right_shoulder", "right_hip"),
    ("left_hip", "right_hip"),
    # Left arm
    ("left_shoulder", "left_elbow"),
    ("left_elbow", "left_wrist"),
    ("left_wrist", "left_pinky"),
    ("left_wrist", "left_index"),
    ("left_wrist", "left_thumb"),
    ("left_pinky", "left_index"),
    # Right arm
    ("right_shoulder", "right_elbow"),
    ("right_elbow", "right_wrist"),
    ("right_wrist", "right_pinky"),
    ("right_wrist", "right_index"),
    ("right_wrist", "right_thumb"),
    ("right_pinky", "right_index"),
    # Left leg
    ("left_hip", "left_knee"),
    ("left_knee", "left_ankle"),
    ("left_ankle", "left_heel"),
    ("left_ankle", "left_foot_index"),
    ("left_heel", "left_foot_index"),
    # Right leg
    ("right_hip", "right_knee"),
    ("right_knee", "right_ankle"),
    ("right_ankle", "right_heel"),
    ("right_ankle", "right_foot_index"),
    ("right_heel", "right_foot_index"),
]


def make_coordinate_columns(
    landmarks=None,
    axes=("x", "y", "z"),
):
    """
    Create coordinate column names from landmark names.
    Example:
        nose_x, nose_y, nose_z
    """
    if landmarks is None:
        landmarks = LANDMARKS

    return ["{}_{}".format(landmark, axis) for landmark in landmarks for axis in axes]


def make_confidence_columns(
    landmarks=None,
):
    """
    Create canonical landmark-confidence column names.
    Example:
        nose_confidence
    """
    if landmarks is None:
        landmarks = LANDMARKS

    return ["{}_confidence".format(landmark) for landmark in landmarks]


def make_required_columns(
    landmarks=None,
    axes=("x", "y", "z"),
):
    """
    Create required columns for pose dataframe.
    """
    if landmarks is None:
        landmarks = LANDMARKS

    return ["frame", "timestamp"] + make_coordinate_columns(landmarks, axes=axes)
