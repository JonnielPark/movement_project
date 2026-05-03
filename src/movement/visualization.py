"""
⑩ 시각화 / 보고서 (Visualization)

포즈 데이터·분석 결과의 인터랙티브 시각화 및 단계별 진단 보고 함수.
pipeline ①~⑨ 외부에서 독립 호출한다.

현재 구현:
    create_pose_animation()            — Plotly 3D 포즈 애니메이션
    create_pose_comparison_animation() — Raw vs Normalized 좌표 비교 애니메이션

계획된 함수 (구현 예정):
    plot_reliability_overlay()         — 프레임별 신뢰도 마스크 오버레이
    plot_joint_angle_timeseries()      — 관절각 시계열 (deg)
    plot_rep_timeline()                — 반복 단위 타임라인 + 구간 레이블
    plot_attribution_chart()           — 활성 측 귀속 결과 차트
    plot_biomarker_radar()             — 바이오마커 레이더 차트

좌표 모드:
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


# ── 계획된 시각화 함수 (구현 예정) ───────────────────────────────────────────────

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
    """프레임별 신뢰도 마스크를 3D 포즈 위에 오버레이한다.

    신뢰도가 낮은 랜드마크를 다른 색상·크기로 표시하여
    ④ 전처리 단계의 신뢰도 탐지 결과를 시각적으로 확인한다.

    Parameters
    ----------
    df : pd.DataFrame
    landmarks : list[str]
    connections : list[tuple[str, str]]
    reliability_col : str
        신뢰도 플래그 컬럼명 (예: "reliability_flag").
    coord_mode : str
        "raw" 또는 "norm".
    frame_duration : int
    height : int
    width : int

    Returns
    -------
    go.Figure
    """
    raise NotImplementedError("plot_reliability_overlay는 아직 구현되지 않았습니다.")


def plot_joint_angle_timeseries(
    df,
    joint_triplets: list[tuple[str, str, str]],
    joint_labels: list[str] | None = None,
    rep_ranges: list[tuple[int, int]] | None = None,
    coord_mode: str = "norm",
    height: int = 400,
    width: int = 900,
) -> "go.Figure":
    """관절각 시계열을 프레임별로 플롯한다 (단위: degree).

    반복 단위(rep) 구간을 배경 음영으로 표시하여
    ROM 특징 추출(⑦) 결과와 연계해 해석할 수 있도록 한다.

    Parameters
    ----------
    df : pd.DataFrame
    joint_triplets : list[tuple[str, str, str]]
        (proximal, vertex, distal) 랜드마크 3중쌍 목록.
    joint_labels : list[str], optional
        각 관절의 표시 레이블. None이면 "joint_0", "joint_1", ... 사용.
    rep_ranges : list[tuple[int, int]], optional
        반복 구간 (start_frame, end_frame) 목록.
    coord_mode : str
        "raw" 또는 "norm".
    height : int
    width : int

    Returns
    -------
    go.Figure
    """
    raise NotImplementedError("plot_joint_angle_timeseries는 아직 구현되지 않았습니다.")


def plot_rep_timeline(
    df,
    segment_col: str = "segment_type",
    rep_col: str = "rep_id",
    set_col: str = "set_id",
    height: int = 200,
    width: int = 900,
) -> "go.Figure":
    """반복 단위 타임라인과 구간 레이블을 표시한다.

    ② annotation 결과를 한눈에 확인하고,
    분석 대상 구간(use_for_analysis=True)을 강조 표시한다.

    Parameters
    ----------
    df : pd.DataFrame
        annotation 컬럼(segment_type, rep_id, set_id, use_for_analysis)이 포함된 데이터프레임.
    segment_col : str
    rep_col : str
    set_col : str
    height : int
    width : int

    Returns
    -------
    go.Figure
    """
    raise NotImplementedError("plot_rep_timeline는 아직 구현되지 않았습니다.")


def plot_attribution_chart(
    df,
    attribution_col: str = "detected_active_limb",
    confidence_col: str = "attribution_confidence",
    expected_col: str = "expected_active_limb",
    height: int = 300,
    width: int = 900,
) -> "go.Figure":
    """⑥ motion_attribution 결과를 프레임별 차트로 표시한다.

    감지된 활성 측(detected)과 기대 측(expected)의 일치 여부와
    귀속 신뢰도(attribution_confidence)를 함께 시각화한다.

    Parameters
    ----------
    df : pd.DataFrame
        motion_attribution 출력 컬럼이 포함된 데이터프레임.
    attribution_col : str
    confidence_col : str
    expected_col : str
    height : int
    width : int

    Returns
    -------
    go.Figure
    """
    raise NotImplementedError("plot_attribution_chart는 아직 구현되지 않았습니다.")


def plot_biomarker_radar(
    biomarker_records: list,
    reference_records: list | None = None,
    height: int = 500,
    width: int = 600,
) -> "go.Figure":
    """⑨ 지표화 결과를 레이더 차트로 표시한다.

    각 바이오마커 축을 정규화된 참조 범위 기준으로 표시하며,
    참조 레코드(reference_records)를 함께 전달하면 비교 오버레이가 추가된다.

    Parameters
    ----------
    biomarker_records : list[BiomarkerRecord]
        피험자 바이오마커 레코드 목록.
    reference_records : list[BiomarkerRecord], optional
        비교 기준 바이오마커 레코드 목록. None이면 단일 피험자만 표시.
    height : int
    width : int

    Returns
    -------
    go.Figure
    """
    raise NotImplementedError("plot_biomarker_radar는 아직 구현되지 않았습니다.")

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