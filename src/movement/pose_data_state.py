"""Shared pose-data state labels used across pipeline stages."""

from __future__ import annotations

from collections.abc import Iterable

import pandas as pd

RAW_POSE_DATA = "raw_pose_data"
PREPROCESSED_POSE_DATA = "preprocessed_pose_data"
NORMALIZED_POSE_DATA = "normalized_pose_data"
CANONICALIZED_POSE_DATA = "canonicalized_pose_data"

RAW_COORDINATE_FAMILY = "raw"
NORM_COORDINATE_FAMILY = "norm"
CANON_COORDINATE_FAMILY = "canon"
DEFAULT_COORDINATE_AXES = ("x", "y", "z")


def _unique_strings(values: Iterable[str]) -> list[str]:
    result: list[str] = []
    for value in values:
        text = str(value)
        if text and text not in result:
            result.append(text)
    return result


def _has_coordinate_suffix(df: pd.DataFrame, suffix: str) -> bool:
    return any(str(column).endswith(suffix) for column in df.columns)


def _normalize_axes(values: Iterable[str]) -> list[str]:
    axes: list[str] = []
    for value in values:
        axis = str(value)
        if axis in DEFAULT_COORDINATE_AXES and axis not in axes:
            axes.append(axis)
    return axes


def _raw_axis_column(column: str, axis: str) -> bool:
    if not column.endswith(f"_{axis}"):
        return False
    return not any(
        marker in column
        for marker in (
            "_norm_",
            "_canon_",
            "_corrected_3d_hypothesis_",
        )
    )


def _infer_family_axes(df: pd.DataFrame, family: str) -> list[str]:
    columns = [str(column) for column in df.columns]
    axes: list[str] = []
    for axis in DEFAULT_COORDINATE_AXES:
        if family == RAW_COORDINATE_FAMILY:
            has_axis = any(_raw_axis_column(column, axis) for column in columns)
        else:
            has_axis = any(column.endswith(f"_{family}_{axis}") for column in columns)
        if has_axis:
            axes.append(axis)
    return axes


def _infer_coordinate_families(df: pd.DataFrame) -> list[str]:
    families: list[str] = []
    columns = [str(column) for column in df.columns]
    if any(
        column.endswith(("_x", "_y", "_z"))
        and "_norm_" not in column
        and "_canon_" not in column
        and "_corrected_3d_hypothesis_" not in column
        for column in columns
    ):
        families.append(RAW_COORDINATE_FAMILY)
    if _has_coordinate_suffix(df, "_norm_x"):
        families.append(NORM_COORDINATE_FAMILY)
    if _has_coordinate_suffix(df, "_canon_x"):
        families.append(CANON_COORDINATE_FAMILY)
    if any("_corrected_3d_hypothesis_" in column for column in columns):
        families.append("corrected_3d_hypothesis")
    return families


def _infer_pose_data_state(df: pd.DataFrame) -> str | None:
    if any(str(column).startswith("canonicalization_") for column in df.columns):
        return CANONICALIZED_POSE_DATA
    if _has_coordinate_suffix(df, "_canon_x"):
        return CANONICALIZED_POSE_DATA
    if _has_coordinate_suffix(df, "_norm_x"):
        return NORMALIZED_POSE_DATA
    if "preprocessing_valid" in df.columns:
        return PREPROCESSED_POSE_DATA
    return None


def get_pose_data_state(
    df: pd.DataFrame,
    default: str = RAW_POSE_DATA,
) -> str:
    """Return the dataframe's pipeline pose-data state label."""

    value = getattr(df, "attrs", {}).get("pose_data_state")
    if value:
        return str(value)
    inferred = _infer_pose_data_state(df)
    return inferred or default


def get_coordinate_families(
    df: pd.DataFrame,
    default: Iterable[str] = (RAW_COORDINATE_FAMILY,),
) -> list[str]:
    """Return coordinate families known to be present in the dataframe."""

    values = getattr(df, "attrs", {}).get("coordinate_families")
    if isinstance(values, (list, tuple, set)):
        return _unique_strings(values)
    inferred = _infer_coordinate_families(df)
    if inferred:
        return inferred
    return _unique_strings(default)


def get_coordinate_axes(df: pd.DataFrame) -> dict[str, list[str]]:
    """Return available coordinate axes by coordinate family."""

    values = getattr(df, "attrs", {}).get("coordinate_axes")
    if isinstance(values, dict):
        axes_by_family: dict[str, list[str]] = {}
        for family, axes in values.items():
            if isinstance(axes, str):
                normalized = _normalize_axes([axes])
            elif isinstance(axes, Iterable):
                normalized = _normalize_axes(axes)
            else:
                normalized = []
            if normalized:
                axes_by_family[str(family)] = normalized
        if axes_by_family:
            return axes_by_family

    families = get_coordinate_families(df)
    axes_by_family = {}
    for family in families:
        axes = _infer_family_axes(df, family)
        if axes:
            axes_by_family[family] = axes
    return axes_by_family


def get_family_axes(
    df: pd.DataFrame,
    family: str = RAW_COORDINATE_FAMILY,
    default: Iterable[str] = DEFAULT_COORDINATE_AXES,
) -> list[str]:
    """Return available axes for one coordinate family."""

    axes_by_family = get_coordinate_axes(df)
    axes = axes_by_family.get(family)
    if axes:
        return list(axes)
    return _normalize_axes(default)


def set_pose_data_state(
    df: pd.DataFrame,
    state: str,
    coordinate_families: Iterable[str] | None = None,
    coordinate_axes: dict[str, Iterable[str]] | None = None,
) -> pd.DataFrame:
    """Attach a pipeline pose-data state label to a dataframe and return it."""

    df.attrs["pose_data_state"] = state
    if coordinate_families is not None:
        df.attrs["coordinate_families"] = _unique_strings(coordinate_families)
    if coordinate_axes is not None:
        df.attrs["coordinate_axes"] = {
            str(family): _normalize_axes(axes)
            for family, axes in coordinate_axes.items()
            if _normalize_axes(axes)
        }
    return df


def set_coordinate_axes(
    df: pd.DataFrame,
    coordinate_axes: dict[str, Iterable[str]],
) -> pd.DataFrame:
    """Attach coordinate-axis metadata to a dataframe and return it."""

    df.attrs["coordinate_axes"] = {
        str(family): _normalize_axes(axes)
        for family, axes in coordinate_axes.items()
        if _normalize_axes(axes)
    }
    return df


def add_coordinate_family(
    df: pd.DataFrame,
    family: str,
    axes: Iterable[str] | None = None,
) -> pd.DataFrame:
    """Record that a coordinate family has been added to a dataframe."""

    families = get_coordinate_families(df)
    if family not in families:
        families.append(family)
    df.attrs["coordinate_families"] = families
    if axes is not None:
        axes_by_family = get_coordinate_axes(df)
        axes_by_family[family] = _normalize_axes(axes)
        set_coordinate_axes(df, axes_by_family)
    return df
