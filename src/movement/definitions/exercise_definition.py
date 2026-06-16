"""
③ Exercise Definition Loading

Loads and validates exercise YAML files from data/definitions/exercises/.
Each ExerciseDefinition object describes the biomechanical properties of an exercise
and drives downstream feature extraction, proxy modeling, and biomarker derivation.

Pipeline position: after ② annotation, before ④ preprocessing.

Public API
----------
load_exercise_context(exercise_id, definitions_dir)    -> ExerciseContext
load_exercise_definition(exercise_id, definitions_dir) -> ExerciseDefinition
load_all_exercise_definitions(definitions_dir)         -> dict[str, ExerciseDefinition]
"""

from __future__ import annotations

import warnings
from copy import deepcopy
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


# ── Controlled vocabulary ─────────────────────────────────────────────────────
# Source: docs/pipeline/03_exercise_definition.md — Field Dictionary

_VOCAB: dict[str, frozenset[str]] = {
    "classification.family": frozenset(
        {
            "lower_body",
            "upper_body",
            "core",
            "full_body",
            "balance",
            "locomotion",
            "mobility",
            "plyometric",
            "rehabilitation",
        }
    ),
    "classification.posture_type": frozenset(
        {
            "standing",
            "standing_split",
            "single_leg_standing",
            "kneeling",
            "half_kneeling",
            "quadruped",
            "prone",
            "supine",
            "side_lying",
            "seated",
            "plank",
            "side_plank",
            "inverted",
            "inverted_closed_chain",
            "hanging",
            "locomotion",
            "transitioning",
        }
    ),
    "classification.kinetic_chain": frozenset(
        {
            "open_chain",
            "closed_chain",
            "mixed_chain",
            "closed_chain_alternating",
            "open_chain_alternating",
        }
    ),
    "classification.laterality": frozenset(
        {
            "bilateral_symmetric",
            "bilateral_asymmetric",
            "unilateral_left",
            "unilateral_right",
            "unilateral_unspecified",
            "alternating",
            "anti_rotation",
            "cross_body",
        }
    ),
    "classification.primary_plane": frozenset(
        {
            "sagittal",
            "frontal",
            "transverse",
            "multiplanar",
            "static",
        }
    ),
    "phase_model.type": frozenset(
        {
            "resistance_phase",
            "task_phase",
            "static_hold",
            "cyclic",
            "locomotion_phase",
            "balance_phase",
            "transition_phase",
            "custom",
        }
    ),
    "biomechanical_focus.expected_com_motion": frozenset(
        {
            "minimal",
            "vertical",
            "anterior_posterior",
            "medial_lateral",
            "vertical_and_anterior_posterior",
            "vertical_and_medial_lateral",
            "rotational",
            "multidirectional",
        }
    ),
    "biomechanical_focus.stability_requirement": frozenset(
        {
            "low",
            "medium",
            "high",
            "very_high",
        }
    ),
    "view_requirements.occlusion_risk": frozenset(
        {
            "low",
            "medium",
            "high",
            "very_high",
        }
    ),
    "rep_segmentation.reference_axis": frozenset(
        {
            "vertical",
            "anterior_posterior",
            "medial_lateral",
        }
    ),
    "rep_segmentation.boundary_logic": frozenset(
        {
            "local_minimum",
            "local_maximum",
            "zero_crossing",
        }
    ),
    "phase_segmentation.reference_axis": frozenset(
        {
            "vertical",
            "anterior_posterior",
            "medial_lateral",
        }
    ),
    "phase_segmentation.split_logic": frozenset(
        {
            "local_minimum",
            "local_maximum",
            "zero_crossing",
        }
    ),
    "phase_segmentation.multi_inflection_policy": frozenset(
        {
            "global_extremum",
            "first",
            "reject_rep",
        }
    ),
    "performance_protocol.counting.count_unit": frozenset(
        {
            "repetition",
            "left_right_pair",
            "hold_seconds",
        }
    ),
    "performance_protocol.prescription.count_unit": frozenset(
        {
            "repetition",
            "left_right_pair",
            "hold_seconds",
        }
    ),
    "performance_protocol.side_sequence.mode": frozenset(
        {
            "none",
            "alternating_each_rep",
            "same_side_block_then_switch",
        }
    ),
    "performance_protocol.side_sequence.first_side_source": frozenset(
        {
            "annotation.starting_side",
        }
    ),
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
_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_DEFAULT_CAMERA_ZONES_PATH = _PROJECT_ROOT / "data" / "camera" / "camera_zones.yaml"
_DEFAULT_ANALYSIS_PROFILES_DIR = (
    _PROJECT_ROOT / "data" / "definitions" / "analysis_profiles"
)
_DEFAULT_ANALYSIS_PRESETS_PATH = (
    _PROJECT_ROOT / "data" / "definitions" / "analysis_presets.yaml"
)
_DEFAULT_PERFORMANCE_PROTOCOLS_DIR = (
    _PROJECT_ROOT / "data" / "protocols" / "performance"
)
_DEFAULT_CAMERA_PROTOCOLS_DIR = _PROJECT_ROOT / "data" / "protocols" / "camera"
_OUT_OF_ZONE_POLICY = "warn_and_continue"
_COORDINATE_CORRECTION_POLICY = "none"


# ── Dataclasses ───────────────────────────────────────────────────────────────


@dataclass
class PhaseModel:
    type: str
    expected_ratio: dict[str, float] = field(default_factory=dict)


@dataclass
class SmoothingSpec:
    """Smoothing parameters for phase segmentation trajectory preprocessing."""

    method: str = "savitzky_golay"  # savitzky_golay | butterworth | rolling_median
    window_frames: int = 7  # must be odd for Savitzky-Golay
    polyorder: int = 3


@dataclass
class TurnaroundHoldSpec:
    """Turnaround-hold phase specification: frames around motion reversal."""

    enabled: bool = True
    half_window_frames: int = 3  # ±N frames around the inflection frame


# Backward-compatible alias for older imports and YAML terminology.
BottomHoldSpec = TurnaroundHoldSpec


@dataclass
class RepSegmentationSpec:
    """
    Repetition-boundary segmentation specification.

    Describes how to detect repetition start/end boundaries from a smoothed
    reference-landmark trajectory. The confirmed intervals become `rep_id`
    labels before intra-rep phase segmentation runs.
    """

    reference_landmark: str = "hip_center"
    reference_axis: str = "vertical"
    boundary_logic: str = "local_maximum"
    smoothing: SmoothingSpec = field(default_factory=SmoothingSpec)
    minimum_rep_length_frames: int = 8
    minimum_boundary_distance_frames: int = 8
    minimum_reps: int = 1
    boundary_prominence: float | None = None
    include_endpoints: bool = True


@dataclass
class PhaseSegmentationSpec:
    """
    Kinematic phase segmentation specification for semi-automatic intra-rep phase splitting.

    Describes how to detect the turn-around point (inflection frame) within each rep
    using the smoothed trajectory of a reference landmark along a reference axis.
    The result partitions each rep into kinematic phases (e.g., Descent / Ascent).

    These labels are kinematic (trajectory-based), not kinetic (muscle-action-based).
    The biomechanical interpretation of each phase is provided separately by the exercise.
    """

    reference_landmark: str = "hip_center"
    reference_axis: str = "vertical"  # maps to norm_z (vertical), norm_y, norm_x
    phase_sequence: list[str] = field(default_factory=list)
    split_logic: str | list[str] = (
        "local_minimum"  # local_minimum | local_maximum | zero_crossing
    )
    smoothing: SmoothingSpec = field(default_factory=SmoothingSpec)
    turnaround_hold: TurnaroundHoldSpec = field(default_factory=TurnaroundHoldSpec)
    minimum_rep_length_frames: int = 8
    multi_inflection_policy: str = (
        "global_extremum"  # global_extremum | first | reject_rep
    )


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
class PerformanceCountingSpec:
    """Backward-compatible participant-facing counting rule mirror."""

    target_count: int = 10
    count_unit: str = "repetition"
    segmentation_reps_per_count: int = 1


@dataclass
class PerformancePrescriptionSpec:
    """Planned acquisition prescription for one exercise protocol."""

    target_sets: int = 1
    target_count_per_set: int = 10
    count_unit: str = "repetition"
    segmentation_reps_per_count: int = 1
    rest_between_sets_s: list[int] = field(default_factory=list)


@dataclass
class PerformanceSideSequenceSpec:
    """Expected left/right order for exercises with side-specific execution."""

    mode: str = "none"
    block_size_counts: int | None = None
    first_side_source: str | None = None


@dataclass
class PerformanceCompletionSpec:
    """Completion policy for practical acquisition, not automatic data exclusion."""

    allow_partial_completion: bool = False
    recommended_sets: int = 1


@dataclass
class PerformanceProtocolSpec:
    """
    Practical exercise-performance protocol metadata.

    Separates planned acquisition prescription and participant-facing count rules
    from `rep_segmentation`, so one protocol count may correspond to one or more
    segmented atomic repetitions. This preserves the biomechanical meaning of
    protocol execution without forcing segmentation to use the same unit.
    """

    prescription: PerformancePrescriptionSpec = field(
        default_factory=PerformancePrescriptionSpec
    )
    counting: PerformanceCountingSpec = field(default_factory=PerformanceCountingSpec)
    side_sequence: PerformanceSideSequenceSpec = field(
        default_factory=PerformanceSideSequenceSpec
    )
    completion: PerformanceCompletionSpec = field(
        default_factory=PerformanceCompletionSpec
    )
    participant_cues: list[str] = field(default_factory=list)
    analysis_disrupting_patterns: list[str] = field(default_factory=list)
    allowed_side_sequence_modes: list[str] = field(default_factory=list)


@dataclass
class CameraProtocolSpec:
    """
    Recommended filming-condition metadata for one exercise.

    This preserves camera zone and height recommendations for provenance and
    interpretation confidence. It must not trigger coordinate correction,
    reprojection, or forced exclusion; mismatches are warning/reporting signals.
    """

    recommended_zones: list[str] = field(default_factory=list)
    recommended_height: str | None = None
    anchor: str | None = None
    distance_cm: list[int] = field(default_factory=list)
    primary_observation_purpose: list[str] = field(default_factory=list)
    out_of_zone_policy: str = _OUT_OF_ZONE_POLICY
    coordinate_correction: str = _COORDINATE_CORRECTION_POLICY

    def as_dict(self) -> dict[str, Any]:
        return {
            "recommended_zones": self.recommended_zones,
            "recommended_height": self.recommended_height,
            "anchor": self.anchor,
            "distance_cm": self.distance_cm,
            "primary_observation_purpose": self.primary_observation_purpose,
            "out_of_zone_policy": self.out_of_zone_policy,
            "coordinate_correction": self.coordinate_correction,
        }


@dataclass
class ExerciseDefinition:
    """
    Parsed exercise definition. Carries the biomechanical properties that drive
    downstream feature extraction, proxy modeling, and scoring.

    The `is_generic_fallback` flag is True when the generic definition was
    loaded due to a missing exercise_type or a missing YAML file.
    Downstream modules should emit a warning when this flag is True, because
    compensation biomarkers will not be produced.

    The `rep_segmentation` and `phase_segmentation` fields are None for the
    generic fallback or when the YAML does not declare those blocks.
    `rep_segmentation` controls repetition-boundary detection; `phase_segmentation`
    controls intra-rep kinematic phase splitting.

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
    rep_segmentation : RepSegmentationSpec | None
        Repetition-boundary splitter spec. None → rep splitting is skipped.
    phase_segmentation : PhaseSegmentationSpec | None
        Kinematic phase splitter spec. None → phase splitting is skipped.
    performance_protocol : PerformanceProtocolSpec | None
        Practical participant-facing counting and side-sequence metadata.
        None → no exercise-specific performance protocol was declared.
    camera_protocol : CameraProtocolSpec | None
        Recommended filming-condition metadata. None → no exercise-specific
        camera recommendation was declared.
    view_metric_reliability : dict[str, Any]
        Per-camera-zone metric reliability prior. It is used for confidence and
        feature-availability reporting, not for coordinate correction.
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
    rep_segmentation: RepSegmentationSpec | None = None
    phase_segmentation: PhaseSegmentationSpec | None = None
    performance_protocol: PerformanceProtocolSpec | None = None
    camera_protocol: CameraProtocolSpec | None = None
    view_metric_reliability: dict[str, Any] = field(default_factory=dict)


@dataclass
class ExerciseContext:
    """
    Runtime exercise context assembled from split YAML artifacts.

    The split source keeps exercise identity separate from analysis, performance,
    and camera protocol settings while exposing a backward-compatible
    ExerciseDefinition object for existing pipeline stages.
    """

    exercise_id: str
    exercise_definition: ExerciseDefinition
    exercise_identity: dict[str, Any]
    analysis_profile: dict[str, Any] = field(default_factory=dict)
    performance_protocol: dict[str, Any] = field(default_factory=dict)
    camera_protocol: dict[str, Any] = field(default_factory=dict)
    source_paths: dict[str, Path] = field(default_factory=dict)
    is_split_source: bool = False


# ── Validation ────────────────────────────────────────────────────────────────


def _check_required_fields(raw: dict, exercise_id: str) -> list[str]:
    return [f"missing required field: '{f}'" for f in _REQUIRED_FIELDS if f not in raw]


def _check_vocabulary(raw: dict, exercise_id: str) -> list[str]:
    clf = raw.get("classification", {})
    bio = raw.get("biomechanical_focus", {})
    vr = raw.get("view_requirements", {})
    pm = raw.get("phase_model", {})
    rs = raw.get("rep_segmentation") or {}
    ps = raw.get("phase_segmentation") or {}
    pp = raw.get("performance_protocol") or {}
    pc = pp.get("counting") or {}
    prescription = pp.get("prescription") or {}
    pss = pp.get("side_sequence") or {}

    checks = [
        ("classification.family", clf.get("family")),
        ("classification.posture_type", clf.get("posture_type")),
        ("classification.kinetic_chain", clf.get("kinetic_chain")),
        ("classification.laterality", clf.get("laterality")),
        ("classification.primary_plane", clf.get("primary_plane")),
        ("phase_model.type", pm.get("type")),
        ("biomechanical_focus.expected_com_motion", bio.get("expected_com_motion")),
        ("biomechanical_focus.stability_requirement", bio.get("stability_requirement")),
        ("view_requirements.occlusion_risk", vr.get("occlusion_risk")),
        ("rep_segmentation.reference_axis", rs.get("reference_axis") if rs else None),
        ("rep_segmentation.boundary_logic", rs.get("boundary_logic") if rs else None),
        ("phase_segmentation.reference_axis", ps.get("reference_axis") if ps else None),
        (
            "phase_segmentation.multi_inflection_policy",
            ps.get("multi_inflection_policy") if ps else None,
        ),
        (
            "performance_protocol.counting.count_unit",
            pc.get("count_unit") if pp else None,
        ),
        (
            "performance_protocol.prescription.count_unit",
            prescription.get("count_unit") if pp else None,
        ),
        (
            "performance_protocol.side_sequence.mode",
            pss.get("mode") if pp else None,
        ),
        (
            "performance_protocol.side_sequence.first_side_source",
            pss.get("first_side_source") if pp else None,
        ),
    ]

    warns = [
        f"[{exercise_id}] '{key}' value '{val}' is not in controlled vocabulary"
        for key, val in checks
        if val is not None and val not in _VOCAB.get(key, frozenset())
    ]

    # split_logic can be a string or a list — validate each entry
    sl = ps.get("split_logic") if ps else None
    if sl is not None:
        sl_list = sl if isinstance(sl, list) else [sl]
        for s in sl_list:
            if s not in _VOCAB["phase_segmentation.split_logic"]:
                warns.append(
                    f"[{exercise_id}] 'phase_segmentation.split_logic' value '{s}' "
                    "is not in controlled vocabulary"
                )

    return warns


def _check_performance_protocol(raw: dict, exercise_id: str) -> list[str]:
    pp = raw.get("performance_protocol") or {}
    if not pp:
        return []

    errors: list[str] = []
    prescription = pp.get("prescription") or {}
    counting = pp.get("counting") or {}
    side_sequence = pp.get("side_sequence") or {}
    completion = pp.get("completion") or {}

    target_sets = int(
        prescription.get("target_sets", completion.get("recommended_sets", 1))
    )
    target_count_per_set = int(
        prescription.get("target_count_per_set", counting.get("target_count", 10))
    )
    segmentation_reps_per_count = int(
        prescription.get(
            "segmentation_reps_per_count",
            counting.get("segmentation_reps_per_count", 1),
        )
    )
    rest_between_sets = list(prescription.get("rest_between_sets_s") or [])

    if target_sets < 1:
        errors.append(
            f"[{exercise_id}] performance_protocol.prescription.target_sets "
            "must be >= 1"
        )
    if target_count_per_set < 1:
        errors.append(
            f"[{exercise_id}] performance_protocol.prescription."
            "target_count_per_set must be >= 1"
        )
    if segmentation_reps_per_count < 1:
        errors.append(
            f"[{exercise_id}] performance_protocol.prescription."
            "segmentation_reps_per_count must be >= 1"
        )

    if "target_count_per_set" in prescription and "target_count" in counting:
        if int(prescription["target_count_per_set"]) != int(counting["target_count"]):
            errors.append(
                f"[{exercise_id}] performance_protocol.counting.target_count "
                "must mirror performance_protocol.prescription.target_count_per_set"
            )
    if "count_unit" in prescription and "count_unit" in counting:
        if prescription["count_unit"] != counting["count_unit"]:
            errors.append(
                f"[{exercise_id}] performance_protocol.counting.count_unit "
                "must mirror performance_protocol.prescription.count_unit"
            )
    if (
        "segmentation_reps_per_count" in prescription
        and "segmentation_reps_per_count" in counting
    ):
        if int(prescription["segmentation_reps_per_count"]) != int(
            counting["segmentation_reps_per_count"]
        ):
            errors.append(
                f"[{exercise_id}] performance_protocol.counting."
                "segmentation_reps_per_count must mirror "
                "performance_protocol.prescription.segmentation_reps_per_count"
            )
    if "target_sets" in prescription and "recommended_sets" in completion:
        if int(prescription["target_sets"]) != int(completion["recommended_sets"]):
            errors.append(
                f"[{exercise_id}] performance_protocol.completion.recommended_sets "
                "must mirror performance_protocol.prescription.target_sets"
            )

    if rest_between_sets:
        if len(rest_between_sets) != 2:
            errors.append(
                f"[{exercise_id}] performance_protocol.prescription."
                "rest_between_sets_s must contain [min_seconds, max_seconds]"
            )
        else:
            min_rest, max_rest = int(rest_between_sets[0]), int(rest_between_sets[1])
            if min_rest < 0 or max_rest < 0 or min_rest > max_rest:
                errors.append(
                    f"[{exercise_id}] performance_protocol.prescription."
                    "rest_between_sets_s must be a non-negative ascending range"
                )

    recommended_sets = int(completion.get("recommended_sets", target_sets))
    if recommended_sets < 1:
        errors.append(
            f"[{exercise_id}] performance_protocol.completion.recommended_sets "
            "must be >= 1"
        )

    mode = side_sequence.get("mode", "none")
    block_size = side_sequence.get("block_size_counts")
    allowed_modes = list(pp.get("allowed_side_sequence_modes") or [mode])
    known_side_modes = _VOCAB["performance_protocol.side_sequence.mode"]

    unknown_allowed_modes = [
        allowed_mode
        for allowed_mode in allowed_modes
        if allowed_mode not in known_side_modes
    ]
    if unknown_allowed_modes:
        errors.append(
            f"[{exercise_id}] performance_protocol.allowed_side_sequence_modes "
            f"contains unknown mode(s): {unknown_allowed_modes}"
        )
    if mode not in allowed_modes:
        errors.append(
            f"[{exercise_id}] performance_protocol.side_sequence.mode '{mode}' "
            "must be included in performance_protocol.allowed_side_sequence_modes"
        )

    if mode == "same_side_block_then_switch":
        if block_size is None or int(block_size) < 1:
            errors.append(
                f"[{exercise_id}] performance_protocol.side_sequence."
                "block_size_counts must be >= 1 when mode is "
                "'same_side_block_then_switch'"
            )

    return errors


def _load_camera_reference(path: Path = _DEFAULT_CAMERA_ZONES_PATH) -> dict[str, Any]:
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _check_camera_protocol(raw: dict, exercise_id: str) -> list[str]:
    cp = raw.get("camera_protocol") or {}
    if not cp:
        return []

    errors: list[str] = []
    reference = _load_camera_reference()
    known_zones = set((reference.get("zones") or {}).keys())
    known_heights = set((reference.get("height_levels") or {}).keys())

    recommended_zones = list(cp.get("recommended_zones") or [])
    if known_zones:
        unknown_zones = [zone for zone in recommended_zones if zone not in known_zones]
        if unknown_zones:
            errors.append(
                f"[{exercise_id}] camera_protocol.recommended_zones contains "
                f"unknown zone(s): {unknown_zones}"
            )

    recommended_height = cp.get("recommended_height")
    if recommended_height is not None and known_heights:
        if recommended_height not in known_heights:
            errors.append(
                f"[{exercise_id}] camera_protocol.recommended_height "
                f"'{recommended_height}' is not defined in data/camera/camera_zones.yaml"
            )

    out_of_zone_policy = cp.get("out_of_zone_policy", _OUT_OF_ZONE_POLICY)
    if out_of_zone_policy != _OUT_OF_ZONE_POLICY:
        errors.append(
            f"[{exercise_id}] camera_protocol.out_of_zone_policy must be "
            f"'{_OUT_OF_ZONE_POLICY}'"
        )

    coordinate_correction = cp.get(
        "coordinate_correction", _COORDINATE_CORRECTION_POLICY
    )
    if coordinate_correction != _COORDINATE_CORRECTION_POLICY:
        errors.append(
            f"[{exercise_id}] camera_protocol.coordinate_correction must be "
            f"'{_COORDINATE_CORRECTION_POLICY}'"
        )

    return errors


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
    errors = (
        _check_required_fields(raw, ex_id)
        + _check_performance_protocol(raw, ex_id)
        + _check_camera_protocol(raw, ex_id)
    )
    warns = _check_vocabulary(raw, ex_id) + _check_phase_ratio(raw, ex_id)
    return errors, warns


# ── Parsing ───────────────────────────────────────────────────────────────────


def _parse_rep_segmentation(rs: dict | None) -> RepSegmentationSpec | None:
    """Parse a rep_segmentation YAML block into a RepSegmentationSpec, or None."""
    if not rs:
        return None
    sm = rs.get("smoothing") or {}
    prominence = rs.get("boundary_prominence", None)
    return RepSegmentationSpec(
        reference_landmark=rs.get("reference_landmark", "hip_center"),
        reference_axis=rs.get("reference_axis", "vertical"),
        boundary_logic=rs.get("boundary_logic", "local_maximum"),
        smoothing=SmoothingSpec(
            method=sm.get("method", "savitzky_golay"),
            window_frames=int(sm.get("window_frames", 7)),
            polyorder=int(sm.get("polyorder", 3)),
        ),
        minimum_rep_length_frames=int(rs.get("minimum_rep_length_frames", 8)),
        minimum_boundary_distance_frames=int(
            rs.get("minimum_boundary_distance_frames", 8)
        ),
        minimum_reps=int(rs.get("minimum_reps", 1)),
        boundary_prominence=None if prominence is None else float(prominence),
        include_endpoints=bool(rs.get("include_endpoints", True)),
    )


def _parse_phase_segmentation(ps: dict | None) -> PhaseSegmentationSpec | None:
    """Parse a phase_segmentation YAML block into a PhaseSegmentationSpec, or None."""
    if not ps:
        return None
    sm = ps.get("smoothing") or {}
    th = ps.get("turnaround_hold") or ps.get("bottom_hold") or {}
    sl = ps.get("split_logic", "local_minimum")
    return PhaseSegmentationSpec(
        reference_landmark=ps.get("reference_landmark", "hip_center"),
        reference_axis=ps.get("reference_axis", "vertical"),
        phase_sequence=list(ps.get("phase_sequence") or []),
        split_logic=sl if isinstance(sl, list) else str(sl),
        smoothing=SmoothingSpec(
            method=sm.get("method", "savitzky_golay"),
            window_frames=int(sm.get("window_frames", 7)),
            polyorder=int(sm.get("polyorder", 3)),
        ),
        turnaround_hold=TurnaroundHoldSpec(
            enabled=bool(th.get("enabled", True)),
            half_window_frames=int(th.get("half_window_frames", 3)),
        ),
        minimum_rep_length_frames=int(ps.get("minimum_rep_length_frames", 8)),
        multi_inflection_policy=ps.get("multi_inflection_policy", "global_extremum"),
    )


def _parse_performance_protocol(pp: dict | None) -> PerformanceProtocolSpec | None:
    """Parse a performance_protocol YAML block into a PerformanceProtocolSpec."""
    if not pp:
        return None

    prescription = pp.get("prescription") or {}
    counting = pp.get("counting") or {}
    side_sequence = pp.get("side_sequence") or {}
    completion = pp.get("completion") or {}
    block_size = side_sequence.get("block_size_counts")
    target_sets = int(
        prescription.get("target_sets", completion.get("recommended_sets", 1))
    )
    target_count_per_set = int(
        prescription.get("target_count_per_set", counting.get("target_count", 10))
    )
    count_unit = prescription.get(
        "count_unit",
        counting.get("count_unit", "repetition"),
    )
    segmentation_reps_per_count = int(
        prescription.get(
            "segmentation_reps_per_count",
            counting.get("segmentation_reps_per_count", 1),
        )
    )

    return PerformanceProtocolSpec(
        prescription=PerformancePrescriptionSpec(
            target_sets=target_sets,
            target_count_per_set=target_count_per_set,
            count_unit=count_unit,
            segmentation_reps_per_count=segmentation_reps_per_count,
            rest_between_sets_s=[
                int(v) for v in list(prescription.get("rest_between_sets_s") or [])
            ],
        ),
        counting=PerformanceCountingSpec(
            target_count=int(counting.get("target_count", target_count_per_set)),
            count_unit=counting.get("count_unit", count_unit),
            segmentation_reps_per_count=int(
                counting.get("segmentation_reps_per_count", segmentation_reps_per_count)
            ),
        ),
        side_sequence=PerformanceSideSequenceSpec(
            mode=side_sequence.get("mode", "none"),
            block_size_counts=None if block_size is None else int(block_size),
            first_side_source=side_sequence.get("first_side_source"),
        ),
        completion=PerformanceCompletionSpec(
            allow_partial_completion=bool(
                completion.get("allow_partial_completion", False)
            ),
            recommended_sets=int(completion.get("recommended_sets", target_sets)),
        ),
        participant_cues=list(pp.get("participant_cues") or []),
        analysis_disrupting_patterns=list(pp.get("analysis_disrupting_patterns") or []),
        allowed_side_sequence_modes=list(
            pp.get("allowed_side_sequence_modes") or [side_sequence.get("mode", "none")]
        ),
    )


def _parse_camera_protocol(cp: dict | None) -> CameraProtocolSpec | None:
    """Parse a camera_protocol YAML block into a CameraProtocolSpec."""
    if not cp:
        return None

    distance = cp.get("distance_cm") or []
    return CameraProtocolSpec(
        recommended_zones=list(cp.get("recommended_zones") or []),
        recommended_height=cp.get("recommended_height"),
        anchor=cp.get("anchor"),
        distance_cm=[int(v) for v in distance],
        primary_observation_purpose=list(cp.get("primary_observation_purpose") or []),
        out_of_zone_policy=cp.get("out_of_zone_policy", _OUT_OF_ZONE_POLICY),
        coordinate_correction=cp.get(
            "coordinate_correction", _COORDINATE_CORRECTION_POLICY
        ),
    )


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
            expected_ratio={
                k: float(v) for k, v in pm.get("expected_ratio", {}).items()
            },
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
            minimum_visible_landmark_ratio=float(
                qr.get("minimum_visible_landmark_ratio", 0.8)
            ),
            minimum_critical_landmark_ratio=float(
                qr.get("minimum_critical_landmark_ratio", 0.9)
            ),
            max_missing_gap_frames=int(qr.get("max_missing_gap_frames", 10)),
            max_interpolation_gap_frames=int(qr.get("max_interpolation_gap_frames", 3)),
            exclude_rep_if_critical_landmark_missing=bool(
                qr.get("exclude_rep_if_critical_landmark_missing", True)
            ),
            exclude_rep_if_phase_missing=bool(
                qr.get("exclude_rep_if_phase_missing", False)
            ),
            allow_partial_feature_output=bool(
                qr.get("allow_partial_feature_output", True)
            ),
        ),
        rep_segmentation=_parse_rep_segmentation(raw.get("rep_segmentation")),
        phase_segmentation=_parse_phase_segmentation(raw.get("phase_segmentation")),
        performance_protocol=_parse_performance_protocol(
            raw.get("performance_protocol")
        ),
        camera_protocol=_parse_camera_protocol(raw.get("camera_protocol")),
        view_metric_reliability=dict(raw.get("view_metric_reliability") or {}),
    )


def _load_raw(yaml_path: Path) -> dict:
    with open(yaml_path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _default_analysis_profiles_dir(definitions_dir: Path) -> Path:
    if definitions_dir.name == "exercises":
        return definitions_dir.parent / "analysis_profiles"
    return _DEFAULT_ANALYSIS_PROFILES_DIR


def _default_analysis_presets_path(definitions_dir: Path) -> Path:
    if definitions_dir.name == "exercises":
        return definitions_dir.parent / "analysis_presets.yaml"
    return _DEFAULT_ANALYSIS_PRESETS_PATH


def _default_protocol_dir(definitions_dir: Path, protocol_name: str) -> Path:
    if (
        definitions_dir.name == "exercises"
        and definitions_dir.parent.name == "definitions"
    ):
        return definitions_dir.parent.parent / "protocols" / protocol_name
    return _PROJECT_ROOT / "data" / "protocols" / protocol_name


def _is_split_identity(raw: dict) -> bool:
    """Return True when an exercise YAML needs companion split artifacts."""
    if raw.get("exercise_id") == _GENERIC_ID:
        return False
    return any(field not in raw for field in _REQUIRED_FIELDS)


def _unwrap_named_block(raw: dict, key: str) -> dict:
    block = raw.get(key)
    if isinstance(block, dict):
        return block
    return raw


def _deep_merge_dict(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = deepcopy(base)
    for key, value in override.items():
        existing = merged.get(key)
        if isinstance(existing, dict) and isinstance(value, dict):
            merged[key] = _deep_merge_dict(existing, value)
        else:
            merged[key] = deepcopy(value)
    return merged


def _preset_names(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list) and all(isinstance(item, str) for item in value):
        return list(value)
    raise ValueError("analysis profile preset selection must be a string or list")


def _expand_analysis_profile_presets(
    analysis_profile: dict[str, Any],
    *,
    presets_path: Path,
    exercise_id: str,
) -> dict[str, Any]:
    selections = analysis_profile.get("presets") or {}
    if not selections:
        return deepcopy(analysis_profile)
    if not isinstance(selections, dict):
        raise ValueError(
            f"[{exercise_id}] analysis profile 'presets' must be a mapping"
        )
    if not presets_path.exists():
        raise FileNotFoundError(
            f"Analysis profile '{exercise_id}' selected presets, but no preset "
            f"catalog was found at: '{presets_path}'"
        )

    catalog = _load_raw(presets_path)
    expanded: dict[str, Any] = {}
    for group_name, selected in selections.items():
        group = catalog.get(group_name)
        if not isinstance(group, dict):
            raise ValueError(
                f"[{exercise_id}] analysis preset group '{group_name}' "
                f"was not found in '{presets_path}'"
            )
        for preset_name in _preset_names(selected):
            block = group.get(preset_name)
            if not isinstance(block, dict):
                raise ValueError(
                    f"[{exercise_id}] analysis preset '{group_name}."
                    f"{preset_name}' was not found in '{presets_path}'"
                )
            expanded = _deep_merge_dict(expanded, block)

    explicit_profile = {
        key: value for key, value in analysis_profile.items() if key != "presets"
    }
    return _deep_merge_dict(expanded, explicit_profile)


def _compose_split_raw(
    identity: dict,
    analysis_profile: dict,
    performance_protocol: dict | None,
    camera_protocol: dict | None,
) -> dict:
    """Merge split YAML artifacts into the legacy raw shape consumed by _parse."""
    raw = deepcopy(identity)
    raw["phase_model"] = deepcopy(identity.get("phase_model") or {})
    raw["landmarks"] = deepcopy(analysis_profile.get("landmarks") or {})
    raw["angle_definitions"] = deepcopy(analysis_profile.get("angle_definitions") or {})
    raw["biomechanical_focus"] = deepcopy(
        analysis_profile.get("biomechanical_focus") or {}
    )
    raw["compensation_candidates"] = deepcopy(
        analysis_profile.get("compensation_candidates") or []
    )
    raw["feature_domains"] = deepcopy(analysis_profile.get("feature_domains") or {})
    raw["quality_rules"] = deepcopy(analysis_profile.get("quality_rules") or {})
    raw["rep_segmentation"] = deepcopy(analysis_profile.get("rep_segmentation") or {})
    raw["phase_segmentation"] = deepcopy(
        analysis_profile.get("phase_segmentation") or {}
    )

    if "joint_actions" not in raw:
        raw["joint_actions"] = deepcopy(analysis_profile.get("joint_actions") or {})

    if performance_protocol:
        raw["performance_protocol"] = deepcopy(
            _unwrap_named_block(performance_protocol, "performance_protocol")
        )
    if camera_protocol:
        raw["camera_protocol"] = deepcopy(
            _unwrap_named_block(camera_protocol, "camera_protocol")
        )
        raw["view_metric_reliability"] = deepcopy(
            camera_protocol.get("view_metric_reliability") or {}
        )

    return raw


# ── Public API ────────────────────────────────────────────────────────────────


def load_exercise_context(
    exercise_id: str | None,
    definitions_dir: Path | str,
    *,
    analysis_profiles_dir: Path | str | None = None,
    analysis_presets_path: Path | str | None = None,
    performance_protocols_dir: Path | str | None = None,
    camera_protocols_dir: Path | str | None = None,
) -> ExerciseContext:
    """
    Load the runtime exercise context for one exercise_id.

    The loader accepts both the legacy combined exercise YAML and the split YAML
    layout introduced for notebook-first exercise authoring. In split mode, the
    companion analysis profile is required. Analysis profiles may select reusable
    preset blocks before exercise-specific overrides are applied. Performance and
    camera protocol files are optional metadata.
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
            exercise_id = _GENERIC_ID
            is_fallback = True
        if not yaml_path.exists():
            raise FileNotFoundError(
                f"Generic fallback definition not found at: '{yaml_path}'"
            )

    identity = _load_raw(yaml_path)
    raw = identity
    source_paths = {"exercise_definition": yaml_path}
    split_source = _is_split_identity(identity)
    analysis_profile: dict[str, Any] = {}
    performance_protocol: dict[str, Any] = {}
    camera_protocol: dict[str, Any] = {}

    if split_source:
        resolved_analysis_dir = (
            Path(analysis_profiles_dir)
            if analysis_profiles_dir is not None
            else _default_analysis_profiles_dir(definitions_dir)
        )
        resolved_performance_dir = (
            Path(performance_protocols_dir)
            if performance_protocols_dir is not None
            else _default_protocol_dir(definitions_dir, "performance")
        )
        resolved_camera_dir = (
            Path(camera_protocols_dir)
            if camera_protocols_dir is not None
            else _default_protocol_dir(definitions_dir, "camera")
        )
        resolved_presets_path = (
            Path(analysis_presets_path)
            if analysis_presets_path is not None
            else _default_analysis_presets_path(definitions_dir)
        )

        analysis_path = resolved_analysis_dir / f"{exercise_id}.yaml"
        performance_path = resolved_performance_dir / f"{exercise_id}.yaml"
        camera_path = resolved_camera_dir / f"{exercise_id}.yaml"

        if not analysis_path.exists():
            raise FileNotFoundError(
                f"Split exercise definition '{exercise_id}' requires an "
                f"analysis profile at: '{analysis_path}'"
            )

        analysis_profile = _load_raw(analysis_path)
        source_paths["analysis_profile"] = analysis_path
        if analysis_profile.get("presets"):
            analysis_profile = _expand_analysis_profile_presets(
                analysis_profile,
                presets_path=resolved_presets_path,
                exercise_id=exercise_id,
            )
            source_paths["analysis_presets"] = resolved_presets_path

        if performance_path.exists():
            performance_protocol = _load_raw(performance_path)
            source_paths["performance_protocol"] = performance_path
        if camera_path.exists():
            camera_protocol = _load_raw(camera_path)
            source_paths["camera_protocol"] = camera_path

        raw = _compose_split_raw(
            identity,
            analysis_profile,
            performance_protocol or None,
            camera_protocol or None,
        )

    errors, warns = _validate(raw)
    for w in warns:
        warnings.warn(w, stacklevel=2)
    if errors:
        raise ValueError(
            f"Exercise definition '{yaml_path}' failed validation:\n"
            + "\n".join(f"  - {e}" for e in errors)
        )

    definition = _parse(raw, is_generic_fallback=is_fallback)
    return ExerciseContext(
        exercise_id=definition.exercise_id,
        exercise_definition=definition,
        exercise_identity=identity,
        analysis_profile=analysis_profile,
        performance_protocol=performance_protocol,
        camera_protocol=camera_protocol,
        source_paths=source_paths,
        is_split_source=split_source,
    )


def load_exercise_definition(
    exercise_id: str | None,
    definitions_dir: Path | str,
    *,
    analysis_profiles_dir: Path | str | None = None,
    analysis_presets_path: Path | str | None = None,
    performance_protocols_dir: Path | str | None = None,
    camera_protocols_dir: Path | str | None = None,
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
    return load_exercise_context(
        exercise_id,
        definitions_dir,
        analysis_profiles_dir=analysis_profiles_dir,
        analysis_presets_path=analysis_presets_path,
        performance_protocols_dir=performance_protocols_dir,
        camera_protocols_dir=camera_protocols_dir,
    ).exercise_definition


def load_all_exercise_definitions(
    definitions_dir: Path | str,
    *,
    analysis_profiles_dir: Path | str | None = None,
    analysis_presets_path: Path | str | None = None,
    performance_protocols_dir: Path | str | None = None,
    camera_protocols_dir: Path | str | None = None,
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
        try:
            raw = _load_raw(yaml_path)
            ex_id = raw.get("exercise_id", yaml_path.stem)
            context = load_exercise_context(
                ex_id,
                definitions_dir,
                analysis_profiles_dir=analysis_profiles_dir,
                analysis_presets_path=analysis_presets_path,
                performance_protocols_dir=performance_protocols_dir,
                camera_protocols_dir=camera_protocols_dir,
            )
        except (FileNotFoundError, ValueError) as exc:
            warnings.warn(
                f"Skipping '{yaml_path.name}': validation failed:\n" f"  - {exc}",
                stacklevel=2,
            )
            continue

        result[context.exercise_id] = context.exercise_definition

    return result
