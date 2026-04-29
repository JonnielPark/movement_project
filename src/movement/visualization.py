"""
Visualization utilities for pose data.

This module creates Plotly-based 3D pose animations.
"""

import plotly.graph_objects as go

from .utils import get_frame_data, compute_plot_ranges


def create_pose_animation(
    df,
    landmarks: list[str],
    connections: list[tuple[str, str]],
    frame_duration: int = 100,
    height: int = 750,
    width: int = 1000,
    padding: float = 0.1,
    title: str = "MediaPipe 3D Pose Animation",
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
    frame_duration : int
        Frame duration in milliseconds. Smaller value means faster playback.
    height : int
        Plot height.
    width : int
        Plot width.
    padding : float
        Axis range padding.
    title : str
        Plot title.

    Returns
    -------
    go.Figure
        Plotly animation figure.
    """
    if df.empty:
        raise ValueError("Input dataframe is empty.")

    x_range, y_range, z_range = compute_plot_ranges(
        df=df,
        landmarks=landmarks,
        padding=padding,
    )

    fig = go.Figure(
        data=get_frame_data(
            df.iloc[0],
            landmarks=landmarks,
            connections=connections,
        )
    )

    fig.frames = [
        go.Frame(
            data=get_frame_data(
                df.iloc[i],
                landmarks=landmarks,
                connections=connections,
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