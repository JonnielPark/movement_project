"""
Exercise definition loader for the movement analysis pipeline.

Loads and validates exercise YAML files from data/exercise_definitions/.
Each definition describes the biomechanical properties of an exercise and
drives downstream feature extraction, proxy modeling, and scoring.

Run order context:
    Validation → Annotation → Exercise Definition Loading → Preprocessing → ...

Public API
----------
load_exercise_definition(exercise_id, definitions_dir) -> ExerciseDefinition
load_all_exercise_definitions(definitions_dir)         -> dict[str, ExerciseDefinition]
"""
from __future__ import annotations

import warnings
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


# ── Controlled vocabulary ─────────────────────────────────────────────────────
# Source: docs/04_exercise_definition.md — Field Dictionary

_VOCAB: dict[str, frozenset[str]] = {
    "classification.family": frozenset({
        "lower_body", "upper_body", "core", "full_body",
        "balance", "locomotion", "mobility", "plyometric", "rehabilitation",
    }),
    "classification.posture_type": frozenset({
        "standing", "standing_split", "single_leg_standing",
        "kneeling", "half_kneeling", "quadruped",
        "prone", "supine", "side_lying",
        "seated", "plank", "side_plank",
        "inverted", "inverted_closed_chain", "hanging",
        "locomotion", "transitioning",
    }),
    "classification.kinetic_chain": frozenset({
        "open_chain", "closed_chain", "mixed_chain",
        "closed_chain_alternating", "open_chain_alternating",
    }),
    "classification.laterality": frozenset({
        "bilateral_symmetric", "bilateral_asymmetric",
        "unilateral_left", "unilateral_right", "unilateral_unspecified",
        "alternating", "anti_rotation", "cross_body",
    }),
    "classification.primary_plane": frozenset({
        "sagittal", "frontal", "transverse", "multiplanar", "static",
    }),
    "phase_model.type": frozenset({
        "resistance_phase", "task_phase", "static_hold",
        "cyclic", "locomotion_phase", "balance_phase",
        "transition_phase", "custom",
    }),
    "biomechanical_focus.expected_com_motion": frozenset({
        "minimal", "vertical",
        "anterior_posterior", "medial_lateral",
        "vertical_and_anterior_posterior", "vertical_and_medial_lateral",
        "rotational", "multidirectional",
    }),
    "biomechanical_focus.stability_requirement": frozenset({
        "low", "medium", "high", "very_high",
    }),
    "view_requirements.occlusion_risk": frozenset({
        "low", "medium", "high", "very_high",
    }),
}

_REQUIRED_FIELDS: tuple[str, ...] = (
    "exercise_id",
    "classification",
    "phase_model",
    "landmarks",
    "compensation_candidates",
    "feature_domains",
    "quality_rules",
)

_PHASE_RATIO_TOLERANCE: float = 0.02
_GENERIC_ID = "generic"


# ── Dataclasses ───────────────────────────────────────────────────────────────

@dataclass
class PhaseModel:
    type: str
    expected_ratio: dict[str, float] = field(default_factory=dict)


@dataclass
class LandmarkSpec:
    model: str
    primary_joints: list[str] = field(default_factory=list)
    secondary_joints: list[str] = field(default_factory=list)
    critical_landmarks: list[int] = field(default_factory=list)
    optional_landmarks: list[int] = field(default_factory=list)


@dataclass
class BiomechanicalFocus:
    expected_com_motion: str = "minimal"
    stability_requirement: str = "low"
    main_load_regions: list[str] = field(default_factory=list)
    primary_constraints: list[str] = field(default_factory=list)


@dataclass
class FeatureDomains:
    spatial: list[str] = field(default_factory=list)
    temporal: list[str] = field(default_factory=list)
    control: list[str] = field(default_factory=list)
    biomechanical_proxy: list[str] = field(default_factory=list)


@dataclass
class QualityRules:
    minimum_visible_landmark_ratio: float = 0.8
    minimum_critical_landmark_ratio: float = 0.9
    max_missing_gap_frames: int = 10
    max_interpolation_gap_frames: int = 3
    exclude_rep_if_critical_landmark_missing: bool = True
    exclude_rep_if_phase_missing: bool = False
    allow_partial_feature_output: bool = True


@dataclass
class ExerciseDefinition:
    """
    Parsed exercise definition. Carries the biomechanical properties that drive
    downstream feature extraction, proxy modeling, and scoring.

    The `is_generic_fallback` flag is True when the generic definition was
    loaded due to a missing exercise_type or a missing YAML file.
    Downstream modules should emit a warning when this flag is True, because
    compensation biomarkers will not be produced.

    Coordinate convention inherited from the pipeline: (T, J, 3) = (frame, joint_index, xyz).

    Parameters
    ----------
    exercise_id : str
    display_name : str
    version : str
    is_generic_fallback : bool
    classification : dict[str, Any]
        Raw classification block (family, posture_type, kinetic_chain,
        laterality, primary_plane, movement_pattern, ...).
    phase_model : PhaseModel
    landmarks : LandmarkSpec
    angle_definitions : dict[str, Any]
    joint_actions : dict[str, list[str]]
        Keys: "primary", "secondary".
    biomechanical_focus : BiomechanicalFocus
    compensation_candidates : list[str]
    feature_domains : FeatureDomains
    quality_rules : QualityRules
    """
    exercise_id: str
    display_name: str
    version: str
    is_generic_fallback: bool
    classification: dict[str, Any]
    phase_model: PhaseModel
    landmarks: LandmarkSpec
    angle_definitions: dict[str, Any]
    joint_actions: dict[str, list[str]]
    biomechanical_focus: BiomechanicalFocus
    compensation_candidates: list[str]
    feature_domains: FeatureDomains
    quality_rules: QualityRules


# ── Validation ────────────────────────────────────────────────────────────────

def _check_required_fields(raw: dict, exercise_id: str) -> list[str]:
    return [
        f"missing required field: '{f}'"
        for f in _REQUIRED_FIELDS
        if f not in raw
    ]


def _check_vocabulary(raw: dict, exercise_id: str) -> list[str]:
    clf = raw.get("classification", {})
    bio = raw.get("biomechanical_focus", {})
    vr = raw.get("view_requirements", {})
    pm = raw.get("phase_model", {})

    checks = [
        ("classification.family",                        clf.get("family")),
        ("classification.posture_type",                  clf.get("posture_type")),
        ("classification.kinetic_chain",                 clf.get("kinetic_chain")),
        ("classification.laterality",                    clf.get("laterality")),
        ("classification.primary_plane",                 clf.get("primary_plane")),
        ("phase_model.type",                             pm.get("type")),
        ("biomechanical_focus.expected_com_motion",      bio.get("expected_com_motion")),
        ("biomechanical_focus.stability_requirement",    bio.get("stability_requirement")),
        ("view_requirements.occlusion_risk",             vr.get("occlusion_risk")),
    ]

    return [
        f"[{exercise_id}] '{key}' value '{val}' is not in controlled vocabulary"
        for key, val in checks
        if val is not None and val not in _VOCAB.get(key, frozenset())
    ]


def _check_phase_ratio(raw: dict, exercise_id: str) -> list[str]:
    pm = raw.get("phase_model", {})
    pm_type = pm.get("type", "")
    ratio = pm.get("expected_ratio", {})

    if pm_type in ("resistance_phase", "task_phase") and ratio:
        total = sum(float(v) for v in ratio.values())
        if abs(total - 1.0) > _PHASE_RATIO_TOLERANCE:
            return [
                f"[{exercise_id}] phase_model.expected_ratio sums to {total:.3f}, "
                f"expected 1.0 ± {_PHASE_RATIO_TOLERANCE}"
            ]
    return []


def _validate(raw: dict) -> tuple[list[str], list[str]]:
    """Return (errors, warnings). Errors block loading; warnings are emitted but do not block."""
    ex_id = raw.get("exercise_id", "<unknown>")
    errors = _check_required_fields(raw, ex_id)
    warns = _check_vocabulary(raw, ex_id) + _check_phase_ratio(raw, ex_id)
    return errors, warns


# ── Parsing ───────────────────────────────────────────────────────────────────

def _parse(raw: dict, is_generic_fallback: bool = False) -> ExerciseDefinition:
    pm = raw.get("phase_model", {})
    lm = raw.get("landmarks", {})
    bio = raw.get("biomechanical_focus", {})
    fd = raw.get("feature_domains", {})
    qr = raw.get("quality_rules", {})
    ja = raw.get("joint_actions", {})

    return ExerciseDefinition(
        exercise_id=raw.get("exercise_id", _GENERIC_ID),
        display_name=raw.get("display_name", "Unknown"),
        version=raw.get("version", "0.0.0"),
        is_generic_fallback=is_generic_fallback,
        classification=raw.get("classification", {}),
        phase_model=PhaseModel(
            type=pm.get("type", "cyclic"),
            expected_ratio={k: float(v) for k, v in pm.get("expected_ratio", {}).items()},
        ),
        landmarks=LandmarkSpec(
            model=lm.get("model", "mediapipe_pose_33"),
            primary_joints=list(lm.get("primary_joints") or []),
            secondary_joints=list(lm.get("secondary_joints") or []),
            critical_landmarks=list(lm.get("critical_landmarks") or []),
            optional_landmarks=list(lm.get("optional_landmarks") or []),
        ),
        angle_definitions=raw.get("angle_definitions") or {},
        joint_actions={
            "primary": list(ja.get("primary") or []),
            "secondary": list(ja.get("secondary") or []),
        },
        biomechanical_focus=BiomechanicalFocus(
            expected_com_motion=bio.get("expected_com_motion", "minimal"),
            stability_requirement=bio.get("stability_requirement", "low"),
            main_load_regions=list(bio.get("main_load_regions") or []),
            primary_constraints=list(bio.get("primary_constraints") or []),
        ),
        compensation_candidates=list(raw.get("compensation_candidates") or []),
        feature_domains=FeatureDomains(
            spatial=list(fd.get("spatial") or []),
            temporal=list(fd.get("temporal") or []),
            control=list(fd.get("control") or []),
            biomechanical_proxy=list(fd.get("biomechanical_proxy") or []),
        ),
        quality_rules=QualityRules(
            minimum_visible_landmark_ratio=float(qr.get("minimum_visible_landmark_ratio", 0.8)),
            minimum_critical_landmark_ratio=float(qr.get("minimum_critical_landmark_ratio", 0.9)),
            max_missing_gap_frames=int(qr.get("max_missing_gap_frames", 10)),
            max_interpolation_gap_frames=int(qr.get("max_interpolation_gap_frames", 3)),
            exclude_rep_if_critical_landmark_missing=bool(
                qr.get("exclude_rep_if_critical_landmark_missing", True)
            ),
            exclude_rep_if_phase_missing=bool(qr.get("exclude_rep_if_phase_missing", False)),
            allow_partial_feature_output=bool(qr.get("allow_partial_feature_output", True)),
        ),
    )


def _load_raw(yaml_path: Path) -> dict:
    with open(yaml_path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


# ── Public API ────────────────────────────────────────────────────────────────

def load_exercise_definition(
    exercise_id: str | None,
    definitions_dir: Path | str,
) -> ExerciseDefinition:
    """
    Load an exercise definition YAML for the given exercise_id.

    Falls back to the generic definition when:
    - exercise_id is None or empty
    - the corresponding YAML file is not found in definitions_dir

    Parameters
    ----------
    exercise_id : str | None
        Lowercase snake_case exercise identifier (e.g., "squat").
        None triggers generic fallback.
    definitions_dir : Path | str
        Directory containing exercise definition YAML files.

    Returns
    -------
    ExerciseDefinition

    Raises
    ------
    FileNotFoundError
        When the generic fallback YAML itself cannot be found.
    ValueError
        When a loaded YAML fails required-field validation.
    """
    definitions_dir = Path(definitions_dir)
    is_fallback = False

    if not exercise_id:
        warnings.warn(
            "exercise_id is None or empty — loading generic fallback definition. "
            "Biomarker output will be restricted to exercise-agnostic features.",
            stacklevel=2,
        )
        exercise_id = _GENERIC_ID
        is_fallback = True

    yaml_path = definitions_dir / f"{exercise_id}.yaml"

    if not yaml_path.exists():
        if exercise_id != _GENERIC_ID:
            warnings.warn(
                f"Exercise definition not found: '{yaml_path}'. "
                "Loading generic fallback. Biomarker output will be restricted.",
                stacklevel=2,
            )
            yaml_path = definitions_dir / f"{_GENERIC_ID}.yaml"
            is_fallback = True
        if not yaml_path.exists():
            raise FileNotFoundError(
                f"Generic fallback definition not found at: '{yaml_path}'"
            )

    raw = _load_raw(yaml_path)
    errors, warns = _validate(raw)
    for w in warns:
        warnings.warn(w, stacklevel=2)
    if errors:
        raise ValueError(
            f"Exercise definition '{yaml_path}' failed validation:\n"
            + "\n".join(f"  - {e}" for e in errors)
        )

    return _parse(raw, is_generic_fallback=is_fallback)


def load_all_exercise_definitions(
    definitions_dir: Path | str,
) -> dict[str, ExerciseDefinition]:
    """
    Load and validate all YAML exercise definitions in a directory.

    Files that fail required-field validation are skipped with a warning.

    Parameters
    ----------
    definitions_dir : Path | str
        Directory containing exercise definition YAML files.

    Returns
    -------
    dict[str, ExerciseDefinition]
        Maps exercise_id → ExerciseDefinition. The generic entry (if present)
        is included and has is_generic_fallback=True.
    """
    definitions_dir = Path(definitions_dir)
    result: dict[str, ExerciseDefinition] = {}

    for yaml_path in sorted(definitions_dir.glob("*.yaml")):
        raw = _load_raw(yaml_path)
        errors, warns = _validate(raw)
        for w in warns:
            warnings.warn(w, stacklevel=2)
        if errors:
            warnings.warn(
                f"Skipping '{yaml_path.name}': validation failed:\n"
                + "\n".join(f"  - {e}" for e in errors),
                stacklevel=2,
            )
            continue

        ex_id = raw.get("exercise_id", yaml_path.stem)
        is_fallback = ex_id == _GENERIC_ID
        result[ex_id] = _parse(raw, is_generic_fallback=is_fallback)

    return result
