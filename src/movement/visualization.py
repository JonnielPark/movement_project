"""
⑩ Visualization

Interactive visualization and diagnostic reporting functions for pose data and analysis results.
Called independently outside the ①–⑨ pipeline steps.

Implemented:
    create_pose_animation()            — Plotly interactive 3D pose animation
    create_pose_comparison_animation() — Raw vs. normalized coordinate comparison animation

Planned (raise NotImplementedError):
    plot_reliability_overlay()         — Per-frame reliability mask overlay
    plot_joint_angle_timeseries()      — Joint angle time series (deg)
    plot_rep_timeline()                — Rep boundary timeline with segment labels
    plot_attribution_chart()           — Active-side attribution result chart
    plot_biomarker_radar()             — Biomarker radar chart

Coordinate modes:
    coord_mode="raw"  : <landmark>_x/y/z
    coord_mode="norm" : <landmark>_norm_x/y/z
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


# ── Planned visualization functions (not yet implemented) ────────────────────────

def plot_reliability_overlay(
    df,
    landmarks: list[str],
    connections: list[tuple[str, str]],
    reliability_col: str = "reliability_flag",
    coord_mode: str = "norm",
    frame_duration: int = 100,
    height: int = 750,
    width: int = 1000,
) -> "go.Figure":
    """Overlay the ④ preprocessing reliability mask on a 3D pose animation.

    Unreliable landmarks are rendered in a distinct color/size.

    Parameters
    ----------
    df : pd.DataFrame
    landmarks : list[str]
    connections : list[tuple[str, str]]
    reliability_col : str
        Column name for the per-landmark reliability flag.
    coord_mode : str
        "raw" or "norm".
    frame_duration : int
    height : int
    width : int

    Returns
    -------
    go.Figure
    """
    raise NotImplementedError("plot_reliability_overlay is not yet implemented.")


def plot_joint_angle_timeseries(
    df,
    joint_triplets: list[tuple[str, str, str]],
    joint_labels: list[str] | None = None,
    rep_ranges: list[tuple[int, int]] | None = None,
    coord_mode: str = "norm",
    height: int = 400,
    width: int = 900,
) -> "go.Figure":
    """Plot joint angle time series per frame (unit: degree).

    Rep ranges are shown as background shading for comparison with ⑦ ROM features.

    Parameters
    ----------
    df : pd.DataFrame
    joint_triplets : list[tuple[str, str, str]]
        (proximal, vertex, distal) landmark triplets.
    joint_labels : list[str], optional
        Display labels for each joint. Defaults to "joint_0", "joint_1", ...
    rep_ranges : list[tuple[int, int]], optional
        (start_frame, end_frame) pairs to shade as reps.
    coord_mode : str
        "raw" or "norm".
    height : int
    width : int

    Returns
    -------
    go.Figure
    """
    raise NotImplementedError("plot_joint_angle_timeseries is not yet implemented.")


def plot_rep_timeline(
    df,
    segment_col: str = "segment_type",
    rep_col: str = "rep_id",
    set_col: str = "set_id",
    height: int = 200,
    width: int = 900,
) -> "go.Figure":
    """Plot ② annotation segment labels as a frame-level timeline.

    Analysis segments (use_for_analysis=True) are highlighted.

    Parameters
    ----------
    df : pd.DataFrame
        Dataframe with annotation columns (segment_type, rep_id, set_id, use_for_analysis).
    segment_col : str
    rep_col : str
    set_col : str
    height : int
    width : int

    Returns
    -------
    go.Figure
    """
    raise NotImplementedError("plot_rep_timeline is not yet implemented.")


def plot_attribution_chart(
    df,
    attribution_col: str = "detected_active_limb",
    confidence_col: str = "attribution_confidence",
    expected_col: str = "expected_active_limb",
    height: int = 300,
    width: int = 900,
) -> "go.Figure":
    """Chart ⑥ motion attribution results per frame.

    Shows detected vs. expected active side and attribution confidence.

    Parameters
    ----------
    df : pd.DataFrame
        Dataframe with motion attribution output columns.
    attribution_col : str
    confidence_col : str
    expected_col : str
    height : int
    width : int

    Returns
    -------
    go.Figure
    """
    raise NotImplementedError("plot_attribution_chart is not yet implemented.")


def plot_biomarker_radar(
    biomarker_records: list,
    reference_records: list | None = None,
    height: int = 500,
    width: int = 600,
) -> "go.Figure":
    """Radar chart of ⑨ biomarker derivation results.

    Each axis is one biomarker. If reference_records is provided,
    a comparison overlay is added.

    Parameters
    ----------
    biomarker_records : list[BiomarkerRecord]
    reference_records : list[BiomarkerRecord], optional
    height : int
    width : int

    Returns
    -------
    go.Figure
    """
    raise NotImplementedError("plot_biomarker_radar is not yet implemented.")

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