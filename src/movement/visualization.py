"""
Visualization utilities for pose data.

This module creates Plotly-based 3D pose animations.

Supported coordinate modes:
    - coord_mode="raw"  : use <landmark>_x, <landmark>_y, <landmark>_z
    - coord_mode="norm" : use <landmark>_norm_x, <landmark>_norm_y, <landmark>_norm_z
"""

import plotly.graph_objects as go

from .utils import get_frame_data, compute_plot_ranges, validate_landmark_columns


def create_pose_animation(
    df,
    landmarks: list[str],
    connections: list[tuple[str, str]],
    coord_mode: str = "raw",
    frame_duration: int = 100,
    height: int = 750,
    width: int = 1000,
    padding: float = 0.1,
    title: str = None,
    show_text: bool = True,
):
    """
    Create an interactive 3D pose animation with Play/Pause and frame slider.

    Parameters
    ----------
    df : pd.DataFrame
        Pose dataframe.
    landmarks : list[str]
        Landmark names.
    connections : list[tuple[str, str]]
        Skeleton connections.
    coord_mode : str
        Coordinate mode.

        - "raw"  : use raw pose coordinates
        - "norm" : use normalized pose coordinates

    frame_duration : int
        Frame duration in milliseconds. Smaller value means faster playback.
    height : int
        Plot height.
    width : int
        Plot width.
    padding : float
        Axis range padding.
    title : str
        Plot title. If None, title is generated automatically.
    show_text : bool
        If True, show landmark names.

    Returns
    -------
    go.Figure
        Plotly animation figure.
    """
    if df.empty:
        raise ValueError("Input dataframe is empty.")

    if coord_mode not in ["raw", "norm"]:
        raise ValueError(
            f"Unsupported coord_mode: {coord_mode}. "
            "Use 'raw' or 'norm'."
        )

    missing_cols = validate_landmark_columns(
        df=df,
        landmarks=landmarks,
        coord_mode=coord_mode,
        require_visibility=False,
    )

    if missing_cols:
        raise ValueError(
            f"Missing columns for coord_mode='{coord_mode}': {missing_cols}"
        )

    if title is None:
        title = f"3D Pose Animation ({coord_mode})"

    x_range, y_range, z_range = compute_plot_ranges(
        df=df,
        landmarks=landmarks,
        padding=padding,
        coord_mode=coord_mode,
    )

    fig = go.Figure(
        data=get_frame_data(
            row=df.iloc[0],
            landmarks=landmarks,
            connections=connections,
            coord_mode=coord_mode,
            show_text=show_text,
        )
    )

    fig.frames = [
        go.Frame(
            data=get_frame_data(
                row=df.iloc[i],
                landmarks=landmarks,
                connections=connections,
                coord_mode=coord_mode,
                show_text=show_text,
            ),
            name=str(i),
        )
        for i in range(len(df))
    ]

    sliders = [{
        "active": 0,
        "currentvalue": {"prefix": "Frame: "},
        "pad": {"t": 50},
        "steps": [
            {
                "args": [
                    [str(i)],
                    {"frame": {"duration": 0, "redraw": True}},
                ],
                "label": str(i),
                "method": "animate",
            }
            for i in range(len(df))
        ],
    }]

    updatemenus = [{
        "type": "buttons",
        "showactive": False,
        "buttons": [
            {
                "label": "Play",
                "method": "animate",
                "args": [
                    None,
                    {
                        "frame": {
                            "duration": frame_duration,
                            "redraw": True,
                        },
                        "transition": {"duration": 0},
                        "fromcurrent": True,
                        "mode": "immediate",
                    },
                ],
            },
            {
                "label": "Pause",
                "method": "animate",
                "args": [
                    [None],
                    {
                        "frame": {"duration": 0, "redraw": False},
                        "mode": "immediate",
                    },
                ],
            },
        ],
    }]

    fig.update_layout(
        title=title,
        height=height,
        width=width,
        scene=dict(
            xaxis=dict(title="X: Left-Right", range=x_range),
            yaxis=dict(title="Y: Depth", range=y_range),
            zaxis=dict(title="Z: Height", range=z_range),
            aspectmode="cube",
        ),
        sliders=sliders,
        updatemenus=updatemenus,
        showlegend=True,
    )

    return fig


def create_pose_comparison_animation(
    df,
    landmarks: list[str],
    connections: list[tuple[str, str]],
    coord_modes: tuple[str, str] = ("raw", "norm"),
    names: tuple[str, str] = ("Raw", "Normalized"),
    frame_duration: int = 100,
    height: int = 750,
    width: int = 1000,
    padding: float = 0.1,
    title: str = "Raw vs Normalized Pose Coordinates",
    show_text: bool = False,
):
    """
    Create an interactive 3D animation comparing two coordinate modes.

    This is mainly intended for debugging coordinate transformations.

    Parameters
    ----------
    df : pd.DataFrame
        Pose dataframe.
    landmarks : list[str]
        Landmark names.
    connections : list[tuple[str, str]]
        Skeleton connections.
    coord_modes : tuple[str, str]
        Coordinate modes to compare.

        Example:
            ("raw", "norm")

    names : tuple[str, str]
        Display names for each coordinate mode.
    frame_duration : int
        Frame duration in milliseconds.
    height : int
        Plot height.
    width : int
        Plot width.
    padding : float
        Axis range padding.
    title : str
        Plot title.
    show_text : bool
        If True, show landmark names.

    Returns
    -------
    go.Figure
        Plotly animation figure.
    """
    if df.empty:
        raise ValueError("Input dataframe is empty.")

    if len(coord_modes) != 2:
        raise ValueError("coord_modes must contain exactly two modes.")

    if len(names) != 2:
        raise ValueError("names must contain exactly two labels.")

    mode_a, mode_b = coord_modes
    name_a, name_b = names

    for mode in coord_modes:
        if mode not in ["raw", "norm"]:
            raise ValueError(
                f"Unsupported coord_mode: {mode}. "
                "Use 'raw' or 'norm'."
            )

        missing_cols = validate_landmark_columns(
            df=df,
            landmarks=landmarks,
            coord_mode=mode,
            require_visibility=False,
        )

        if missing_cols:
            raise ValueError(
                f"Missing columns for coord_mode='{mode}': {missing_cols}"
            )

    def _get_overlay_frame(row):
        traces_a = get_frame_data(
            row=row,
            landmarks=landmarks,
            connections=connections,
            coord_mode=mode_a,
            show_text=show_text,
        )

        traces_b = get_frame_data(
            row=row,
            landmarks=landmarks,
            connections=connections,
            coord_mode=mode_b,
            show_text=show_text,
        )

        traces_a[0].name = f"{name_a} Landmarks"
        traces_a[1].name = f"{name_a} Skeleton"
        traces_b[0].name = f"{name_b} Landmarks"
        traces_b[1].name = f"{name_b} Skeleton"

        traces_a[0].marker.color = "blue"
        traces_a[1].line.color = "blue"

        traces_b[0].marker.color = "red"
        traces_b[1].line.color = "red"

        return traces_a + traces_b

    x_range_a, y_range_a, z_range_a = compute_plot_ranges(
        df=df,
        landmarks=landmarks,
        padding=padding,
        coord_mode=mode_a,
    )

    x_range_b, y_range_b, z_range_b = compute_plot_ranges(
        df=df,
        landmarks=landmarks,
        padding=padding,
        coord_mode=mode_b,
    )

    x_range = [
        min(x_range_a[0], x_range_b[0]),
        max(x_range_a[1], x_range_b[1]),
    ]

    y_range = [
        min(y_range_a[0], y_range_b[0]),
        max(y_range_a[1], y_range_b[1]),
    ]

    z_range = [
        min(z_range_a[0], z_range_b[0]),
        max(z_range_a[1], z_range_b[1]),
    ]

    fig = go.Figure(
        data=_get_overlay_frame(df.iloc[0])
    )

    fig.frames = [
        go.Frame(
            data=_get_overlay_frame(df.iloc[i]),
            name=str(i),
        )
        for i in range(len(df))
    ]

    sliders = [{
        "active": 0,
        "currentvalue": {"prefix": "Frame: "},
        "pad": {"t": 50},
        "steps": [
            {
                "args": [
                    [str(i)],
                    {"frame": {"duration": 0, "redraw": True}},
                ],
                "label": str(i),
                "method": "animate",
            }
            for i in range(len(df))
        ],
    }]

    updatemenus = [{
        "type": "buttons",
        "showactive": False,
        "buttons": [
            {
                "label": "Play",
                "method": "animate",
                "args": [
                    None,
                    {
                        "frame": {
                            "duration": frame_duration,
                            "redraw": True,
                        },
                        "transition": {"duration": 0},
                        "fromcurrent": True,
                        "mode": "immediate",
                    },
                ],
            },
            {
                "label": "Pause",
                "method": "animate",
                "args": [
                    [None],
                    {
                        "frame": {"duration": 0, "redraw": False},
                        "mode": "immediate",
                    },
                ],
            },
        ],
    }]

    fig.update_layout(
        title=title,
        height=height,
        width=width,
        scene=dict(
            xaxis=dict(title="X: Left-Right", range=x_range),
            yaxis=dict(title="Y: Depth", range=y_range),
            zaxis=dict(title="Z: Height", range=z_range),
            aspectmode="cube",
        ),
        sliders=sliders,
        updatemenus=updatemenus,
        showlegend=True,
    )

    return fig