from pathlib import Path
from typing import Union

import pandas as pd
import yaml


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


def load_participant_profile_yaml(path: Union[str, Path]) -> dict:
    """
    Load a de-identified participant profile YAML.

    The profile provides analysis provenance such as participant_id,
    anthropometry metadata, and common-subject skeleton selection. It must not be
    treated as subject-specific body reconstruction or as scoring input by
    itself.
    """
    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(f"Participant profile YAML not found: {path}")

    with path.open("r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}

    if not isinstance(raw, dict):
        raise ValueError("Participant profile YAML must contain a mapping.")

    profile = raw.get("participant_profile")
    if not isinstance(profile, dict):
        raise ValueError("Participant profile YAML must contain 'participant_profile'.")

    participant_id = profile.get("participant_id")
    if not isinstance(participant_id, str) or not participant_id.strip():
        raise ValueError(
            "participant_profile.participant_id must be a non-empty string."
        )

    policy = profile.get("policy", {})
    if policy and not isinstance(policy, dict):
        raise ValueError("participant_profile.policy must be a mapping when provided.")

    if policy.get("contains_direct_identifiers") is True:
        raise ValueError("Participant profile must not contain direct identifiers.")

    return profile


def print_data_summary(df: pd.DataFrame) -> None:
    """
    Print simple summary of pose dataframe.
    """
    print("Data shape:", df.shape)
    print("Frame range:", df["frame"].min(), "to", df["frame"].max())
    print("Timestamp range:", df["timestamp"].min(), "to", df["timestamp"].max())
