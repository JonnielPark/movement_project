"""
Pose utility functions.

This module contains low-level pose operations:
- extract joint coordinates
- convert MediaPipe coordinates to visualization coordinates
- create Plotly frame data
"""

import numpy as np
import plotly.graph_objects as go


def get_joint(row, joint_name: str) -> np.ndarray:
    """
    Get raw MediaPipe 3D coordinate of a joint.

    Raw MediaPipe-like coordinate:
    - x: left-right
    - y: image vertical
    - z: depth

    Parameters
    ----------
    row : pd.Series
        A single frame row.
    joint_name : str
        Landmark name.

    Returns
    -------
    np.ndarray
        [x, y, z]
    """
    return np.array([
        row[f"{joint_name}_x"],
        row[f"{joint_name}_y"],
        row[f"{joint_name}_z"],
    ], dtype=float)


def get_plot_coord(row, joint_name: str) -> np.ndarray:
    """
    Convert raw MediaPipe coordinate to visualization coordinate.

    Raw MediaPipe:
    - x = left-right
    - y = image vertical, larger value means lower in image
    - z = depth

    Plot coordinate:
    - X = left-right
    - Y = depth
    - Z = height

    Mapping:
    - plot_x = raw_x
    - plot_y = raw_z
    - plot_z = -raw_y

    Parameters
    ----------
    row : pd.Series
        A single frame row.
    joint_name : str
        Landmark name.

    Returns
    -------
    np.ndarray
        [plot_x, plot_y, plot_z]
    """
    raw = get_joint(row, joint_name)

    return np.array([
        raw[0],
        raw[2],
        -raw[1],
    ], dtype=float)


def get_frame_data(row, landmarks: list[str], connections: list[tuple[str, str]]):
    """
    Create Plotly Scatter3d traces for one frame.

    Parameters
    ----------
    row : pd.Series
        A single frame row.
    landmarks : list[str]
        Landmark names.
    connections : list[tuple[str, str]]
        Skeleton connections.

    Returns
    -------
    list
        Plotly traces for landmarks and skeleton.
    """
    coords = {
        lm: get_plot_coord(row, lm)
        for lm in landmarks
    }

    xs = [coords[lm][0] for lm in landmarks]
    ys = [coords[lm][1] for lm in landmarks]
    zs = [coords[lm][2] for lm in landmarks]

    line_x = []
    line_y = []
    line_z = []

    for a, b in connections:
        line_x += [coords[a][0], coords[b][0], None]
        line_y += [coords[a][1], coords[b][1], None]
        line_z += [coords[a][2], coords[b][2], None]

    return [
        go.Scatter3d(
            x=xs,
            y=ys,
            z=zs,
            mode="markers+text",
            text=landmarks,
            textposition="top center",
            marker=dict(size=4),
            name="Pose Landmarks",
            showlegend=True,
        ),
        go.Scatter3d(
            x=line_x,
            y=line_y,
            z=line_z,
            mode="lines",
            line=dict(width=5),
            name="Skeleton",
            showlegend=True,
        ),
    ]


def compute_plot_ranges(df, landmarks: list[str], padding: float = 0.1):
    """
    Compute fixed plot ranges for transformed visualization coordinates.

    This prevents the camera view from changing during animation.

    Parameters
    ----------
    df : pd.DataFrame
        Pose dataframe.
    landmarks : list[str]
        Landmark names.
    padding : float
        Extra margin around min/max values.

    Returns
    -------
    tuple[list[float], list[float], list[float]]
        x_range, y_range, z_range
    """
    x_cols = [f"{lm}_x" for lm in landmarks]
    y_cols = [f"{lm}_y" for lm in landmarks]
    z_cols = [f"{lm}_z" for lm in landmarks]

    x_range = [
        df[x_cols].min().min() - padding,
        df[x_cols].max().max() + padding,
    ]

    # Plot Y uses raw z
    y_range = [
        df[z_cols].min().min() - padding,
        df[z_cols].max().max() + padding,
    ]

    # Plot Z uses -raw y
    z_range = [
        -df[y_cols].max().max() - padding,
        -df[y_cols].min().min() + padding,
    ]

    return x_range, y_range, z_range


def validate_landmark_columns(df, landmarks: list[str]) -> list[str]:
    """
    Check whether all landmark coordinate columns exist.

    Parameters
    ----------
    df : pd.DataFrame
        Pose dataframe.
    landmarks : list[str]
        Landmark names.

    Returns
    -------
    list[str]
        Missing column names. Empty list means valid.
    """
    required_cols = []

    for lm in landmarks:
        required_cols.extend([
            f"{lm}_x",
            f"{lm}_y",
            f"{lm}_z",
            f"{lm}_visibility",
        ])

    missing_cols = [
        col for col in required_cols
        if col not in df.columns
    ]

    return missing_cols