from pathlib import Path
from typing import Union

import pandas as pd


def load_pose_csv(path: Union[str, Path]) -> pd.DataFrame:
    """
    Load pose landmark CSV data.

    Parameters
    ----------
    path : str | Path
        CSV file path.

    Returns
    -------
    pd.DataFrame
        Loaded pose data.
    """
    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(f"CSV file not found: {path}")

    df = pd.read_csv(path)

    if "frame" not in df.columns:
        raise ValueError("CSV must contain a 'frame' column.")

    if "timestamp" not in df.columns:
        raise ValueError("CSV must contain a 'timestamp' column.")

    return df


def print_data_summary(df: pd.DataFrame) -> None:
    """
    Print simple summary of pose dataframe.
    """
    print("Data shape:", df.shape)
    print("Frame range:", df["frame"].min(), "to", df["frame"].max())
    print("Timestamp range:", df["timestamp"].min(), "to", df["timestamp"].max())