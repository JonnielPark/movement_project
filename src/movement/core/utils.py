"""
Pose utility functions.

This module contains low-level pose operations:
- select coordinate columns
- extract joint coordinates
- convert pose coordinates to visualization coordinates
- create Plotly frame data
- compute fixed plot ranges
"""

import numpy as np
import plotly.graph_objects as go


def get_coord_columns(landmark: str, coord_mode: str = "raw") -> list[str]:
    """
    Return x, y, z coordinate column names for a landmark.

    Parameters
    ----------
    landmark : str
        Landmark name.
    coord_mode : str
        Coordinate mode.

        - "raw"   -> <landmark>_x, <landmark>_y, <landmark>_z
        - "norm"  -> <landmark>_norm_x, <landmark>_norm_y, <landmark>_norm_z
        - "floor" -> <landmark>_floor_x, <landmark>_floor_y, <landmark>_floor_z
        - "canon" -> <landmark>_canon_x, <landmark>_canon_y, <landmark>_canon_z

    Returns
    -------
    list[str]
        Coordinate column names.
    """
    if coord_mode == "raw":
        return [
            f"{landmark}_x",
            f"{landmark}_y",
            f"{landmark}_z",
        ]

    if coord_mode == "norm":
        return [
            f"{landmark}_norm_x",
            f"{landmark}_norm_y",
            f"{landmark}_norm_z",
        ]

    if coord_mode == "floor":
        return [
            f"{landmark}_floor_x",
            f"{landmark}_floor_y",
            f"{landmark}_floor_z",
        ]

    if coord_mode == "canon":
        return [
            f"{landmark}_canon_x",
            f"{landmark}_canon_y",
            f"{landmark}_canon_z",
        ]

    raise ValueError(
        f"Unsupported coord_mode: {coord_mode}. "
        "Use 'raw', 'norm', 'floor', or 'canon'."
    )


def validate_landmark_columns(
    df,
    landmarks: list[str],
    coord_mode: str = "raw",
    require_confidence: bool = False,
) -> list[str]:
    """
    Check whether required landmark coordinate columns exist.

    Parameters
    ----------
    df : pd.DataFrame
        Pose dataframe.
    landmarks : list[str]
        Landmark names.
    coord_mode : str
        "raw", "norm", "floor", or "canon".
    require_confidence : bool
        If True, also check <landmark>_confidence columns.

    Returns
    -------
    list[str]
        Missing column names. Empty list means valid.
    """
    required_cols = []

    for lm in landmarks:
        required_cols.extend(get_coord_columns(lm, coord_mode=coord_mode))

        if require_confidence:
            required_cols.append(f"{lm}_confidence")

    missing_cols = [col for col in required_cols if col not in df.columns]

    return missing_cols


def get_joint(row, joint_name: str, coord_mode: str = "raw") -> np.ndarray:
    """
    Get 3D coordinate of a joint.

    Parameters
    ----------
    row : pd.Series
        A single frame row.
    joint_name : str
        Landmark name.
    coord_mode : str
        "raw", "norm", "floor", or "canon".

    Returns
    -------
    np.ndarray
        [x, y, z]
    """
    x_col, y_col, z_col = get_coord_columns(
        landmark=joint_name,
        coord_mode=coord_mode,
    )

    return np.array(
        [
            row[x_col],
            row[y_col],
            row[z_col],
        ],
        dtype=float,
    )


def get_plot_coord(
    row,
    joint_name: str,
    coord_mode: str = "raw",
) -> np.ndarray:
    """
    Convert pose coordinate to visualization coordinate.

    Input coordinate:
    - x: left-right
    - y: image vertical or body-relative vertical coordinate
    - z: depth

    Plot coordinate:
    - X = left-right
    - Y = depth
    - Z = height

    Mapping:
    - plot_x = x
    - plot_y = z
    - plot_z = -y

    Parameters
    ----------
    row : pd.Series
        A single frame row.
    joint_name : str
        Landmark name.
    coord_mode : str
        "raw", "norm", "floor", or "canon".

    Returns
    -------
    np.ndarray
        [plot_x, plot_y, plot_z]
    """
    raw = get_joint(
        row=row,
        joint_name=joint_name,
        coord_mode=coord_mode,
    )

    return np.array(
        [
            raw[0],
            raw[2],
            -raw[1],
        ],
        dtype=float,
    )


def get_frame_data(
    row,
    landmarks: list[str],
    connections: list[tuple[str, str]],
    coord_mode: str = "raw",
    show_text: bool = True,
):
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
    coord_mode : str
        "raw", "norm", "floor", or "canon".
    show_text : bool
        If True, show landmark names.

    Returns
    -------
    list
        Plotly traces for landmarks and skeleton.
    """
    coords = {
        lm: get_plot_coord(
            row=row,
            joint_name=lm,
            coord_mode=coord_mode,
        )
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

    text = landmarks if show_text else None
    mode = "markers+text" if show_text else "markers"

    return [
        go.Scatter3d(
            x=xs,
            y=ys,
            z=zs,
            mode=mode,
            text=text,
            textposition="top center",
            marker=dict(size=4),
            name=f"Pose Landmarks ({coord_mode})",
            showlegend=True,
        ),
        go.Scatter3d(
            x=line_x,
            y=line_y,
            z=line_z,
            mode="lines",
            line=dict(width=5),
            name=f"Skeleton ({coord_mode})",
            showlegend=True,
        ),
    ]


def compute_plot_ranges(
    df,
    landmarks: list[str],
    padding: float = 0.1,
    coord_mode: str = "raw",
):
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
    coord_mode : str
        "raw", "norm", "floor", or "canon".

    Returns
    -------
    tuple[list[float], list[float], list[float]]
        x_range, y_range, z_range
    """
    missing_cols = validate_landmark_columns(
        df=df,
        landmarks=landmarks,
        coord_mode=coord_mode,
        require_confidence=False,
    )

    if missing_cols:
        raise ValueError(
            f"Missing columns for coord_mode='{coord_mode}': {missing_cols}"
        )

    x_cols = []
    y_cols = []
    z_cols = []

    for lm in landmarks:
        x_col, y_col, z_col = get_coord_columns(
            landmark=lm,
            coord_mode=coord_mode,
        )
        x_cols.append(x_col)
        y_cols.append(y_col)
        z_cols.append(z_col)

    x_range = [
        df[x_cols].min().min() - padding,
        df[x_cols].max().max() + padding,
    ]

    # Plot Y uses coordinate z
    y_range = [
        df[z_cols].min().min() - padding,
        df[z_cols].max().max() + padding,
    ]

    # Plot Z uses -coordinate y
    z_range = [
        -df[y_cols].max().max() - padding,
        -df[y_cols].min().min() + padding,
    ]

    return x_range, y_range, z_range
