"""
Pipeline configuration and runner for movement analysis.

Each step can be toggled via its `enabled` flag in configs/pipeline_default.yaml.
Steps not yet implemented raise NotImplementedError when enabled=True.

Run order:
    validation → preprocessing → normalization → annotation → features → biomech → scoring
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

from movement.config import (
    LANDMARKS,
    make_coordinate_columns,
    make_required_columns,
    make_visibility_columns,
)
from movement.normalization import normalize_pose_by_hip_torso
from movement.validation import run_basic_validation


# ── Step configs ──────────────────────────────────────────────────────────────

@dataclass
class ValidationConfig:
    enabled: bool = True
    missing_value_threshold: float = 0.05
    visibility_threshold: float = 0.5


@dataclass
class KalmanConfig:
    enabled: bool = False
    process_noise: float = 0.01
    measurement_noise: float = 0.1


@dataclass
class PreprocessingConfig:
    enabled: bool = False
    kalman_filter: KalmanConfig = field(default_factory=KalmanConfig)


@dataclass
class NormalizationConfig:
    enabled: bool = True
    method: str = "hip_torso"
    keep_reference_columns: bool = True


@dataclass
class AnnotationConfig:
    enabled: bool = False


@dataclass
class SpatialConfig:
    rom: bool = False
    symmetry: bool = False
    shape: bool = False


@dataclass
class TemporalConfig:
    tempo: bool = False
    variability: bool = False


@dataclass
class ControlConfig:
    stability: bool = False
    compensation: bool = False


@dataclass
class FeaturesConfig:
    enabled: bool = False
    spatial: SpatialConfig = field(default_factory=SpatialConfig)
    temporal: TemporalConfig = field(default_factory=TemporalConfig)
    control: ControlConfig = field(default_factory=ControlConfig)


@dataclass
class BiomechConfig:
    enabled: bool = False


@dataclass
class ScoringConfig:
    enabled: bool = False


@dataclass
class InputConfig:
    path: str = "data/sample/mediapipe_forward_bend_sample.csv"


@dataclass
class OutputConfig:
    save_processed: bool = False
    processed_path: str = "data/processed/normalized.csv"
    save_report: bool = False
    report_path: str = "data/processed/report.json"


@dataclass
class PipelineConfig:
    input: InputConfig = field(default_factory=InputConfig)
    validation: ValidationConfig = field(default_factory=ValidationConfig)
    preprocessing: PreprocessingConfig = field(default_factory=PreprocessingConfig)
    normalization: NormalizationConfig = field(default_factory=NormalizationConfig)
    annotation: AnnotationConfig = field(default_factory=AnnotationConfig)
    features: FeaturesConfig = field(default_factory=FeaturesConfig)
    biomech: BiomechConfig = field(default_factory=BiomechConfig)
    scoring: ScoringConfig = field(default_factory=ScoringConfig)
    output: OutputConfig = field(default_factory=OutputConfig)


# ── Config loader ─────────────────────────────────────────────────────────────

def load_pipeline_config(path: Path | str) -> PipelineConfig:
    """Load PipelineConfig from a YAML file."""
    with open(path, encoding="utf-8") as f:
        raw: dict = yaml.safe_load(f) or {}

    inp = raw.get("input", {})
    val = raw.get("validation", {})
    pre = raw.get("preprocessing", {})
    kal = pre.get("kalman_filter", {})
    nor = raw.get("normalization", {})
    ann = raw.get("annotation", {})
    feat = raw.get("features", {})
    sp = feat.get("spatial", {})
    te = feat.get("temporal", {})
    co = feat.get("control", {})
    bio = raw.get("biomech", {})
    sc = raw.get("scoring", {})
    out = raw.get("output", {})

    return PipelineConfig(
        input=InputConfig(
            path=inp.get("path", "data/sample/mediapipe_forward_bend_sample.csv"),
        ),
        validation=ValidationConfig(
            enabled=val.get("enabled", True),
            missing_value_threshold=val.get("missing_value_threshold", 0.05),
            visibility_threshold=val.get("visibility_threshold", 0.5),
        ),
        preprocessing=PreprocessingConfig(
            enabled=pre.get("enabled", False),
            kalman_filter=KalmanConfig(
                enabled=kal.get("enabled", False),
                process_noise=kal.get("process_noise", 0.01),
                measurement_noise=kal.get("measurement_noise", 0.1),
            ),
        ),
        normalization=NormalizationConfig(
            enabled=nor.get("enabled", True),
            method=nor.get("method", "hip_torso"),
            keep_reference_columns=nor.get("keep_reference_columns", True),
        ),
        annotation=AnnotationConfig(
            enabled=ann.get("enabled", False),
        ),
        features=FeaturesConfig(
            enabled=feat.get("enabled", False),
            spatial=SpatialConfig(
                rom=sp.get("rom", False),
                symmetry=sp.get("symmetry", False),
                shape=sp.get("shape", False),
            ),
            temporal=TemporalConfig(
                tempo=te.get("tempo", False),
                variability=te.get("variability", False),
            ),
            control=ControlConfig(
                stability=co.get("stability", False),
                compensation=co.get("compensation", False),
            ),
        ),
        biomech=BiomechConfig(
            enabled=bio.get("enabled", False),
        ),
        scoring=ScoringConfig(
            enabled=sc.get("enabled", False),
        ),
        output=OutputConfig(
            save_processed=out.get("save_processed", False),
            processed_path=out.get("processed_path", "data/processed/normalized.csv"),
            save_report=out.get("save_report", False),
            report_path=out.get("report_path", "data/processed/report.json"),
        ),
    )


# ── Pipeline runner ───────────────────────────────────────────────────────────

def run_pipeline(
    df: pd.DataFrame,
    config: PipelineConfig,
    landmarks: list[str] | None = None,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """
    Run the movement analysis pipeline on a pose dataframe.

    Steps are executed in order only when their `enabled` flag is True.
    Not-yet-implemented steps raise NotImplementedError when enabled.

    Parameters
    ----------
    df : pd.DataFrame
        Input pose dataframe. Shape: (T, J*4+2) — frame, timestamp, landmark xyz + visibility.
    config : PipelineConfig
        Loaded from YAML via load_pipeline_config().
    landmarks : list[str], optional
        Landmark name list. Defaults to movement.config.LANDMARKS.

    Returns
    -------
    df : pd.DataFrame
        Processed dataframe with columns added by each enabled step.
    report : dict
        Per-step result dicts, keyed by step name.
    """
    if landmarks is None:
        landmarks = LANDMARKS

    report: dict[str, Any] = {}

    # Step 1: Validation
    if config.validation.enabled:
        validation_report = run_basic_validation(
            df=df,
            required_columns=make_required_columns(landmarks),
            coordinate_columns=make_coordinate_columns(landmarks),
            visibility_columns=make_visibility_columns(landmarks),
        )
        report["validation"] = validation_report
        if not validation_report["passed"]:
            print("[WARN] validation: one or more checks failed.")

    # Step 2: Preprocessing
    if config.preprocessing.enabled:
        raise NotImplementedError(
            "preprocessing step is not yet implemented. Set preprocessing.enabled: false."
        )

    # Step 3: Normalization
    if config.normalization.enabled:
        df, norm_report = normalize_pose_by_hip_torso(
            df=df,
            landmarks=landmarks,
            keep_reference_columns=config.normalization.keep_reference_columns,
        )
        report["normalization"] = norm_report

    # Step 4: Annotation
    if config.annotation.enabled:
        raise NotImplementedError(
            "annotation step is not yet implemented. Set annotation.enabled: false."
        )

    # Step 5: Features
    if config.features.enabled:
        raise NotImplementedError(
            "features step is not yet implemented. Set features.enabled: false."
        )

    # Step 6: Biomech
    if config.biomech.enabled:
        raise NotImplementedError(
            "biomech step is not yet implemented. Set biomech.enabled: false."
        )

    # Step 7: Scoring
    if config.scoring.enabled:
        raise NotImplementedError(
            "scoring step is not yet implemented. Set scoring.enabled: false."
        )

    return df, report
