"""
Exercise authoring helpers for notebook-first YAML generation.

This module turns a small researcher-facing ExerciseAuthoringSpec into draft YAML
artifacts. The drafts are intentionally separated by responsibility:
exercise identity, analysis profile, performance protocol, and camera protocol.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping

import yaml


_REGISTRY_FILES: dict[str, str] = {
    "schema": "exercise_authoring_schema.yaml",
    "movement_patterns": "movement_patterns.yaml",
    "support_templates": "support_templates.yaml",
    "phase_templates": "phase_templates.yaml",
    "landmark_sets": "landmark_sets.yaml",
    "analysis_templates": "analysis_templates.yaml",
    "performance_templates": "performance_templates.yaml",
}

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_REGISTRY_DIR = _PROJECT_ROOT / "data" / "registries"
DEFAULT_DRAFT_ROOT = _PROJECT_ROOT / "data" / "processed" / "authoring_drafts"
_CAMERA_ZONE_PATH = _PROJECT_ROOT / "data" / "camera" / "camera_zones.yaml"

_ARTIFACT_PATHS: dict[str, str] = {
    "exercise_definition": "data/definitions/exercises/{exercise_id}.yaml",
    "analysis_profile": "data/definitions/analysis_profiles/{exercise_id}.yaml",
    "performance_protocol": "data/protocols/performance/{exercise_id}.yaml",
    "camera_protocol": "data/protocols/camera/{exercise_id}.yaml",
}

_GENERATED_BY = "exercise_authoring_notebook"

_POSTURE_BODY_GEOMETRY_VALUES: dict[str, tuple[str, ...]] = {
    "standing": ("neutral_upright", "forward_lean_hinge"),
    "floor_supported_prone": (
        "neutral_prone_line",
        "high_hip_inverted_v",
        "quadruped",
    ),
    "kneeling": (
        "neutral_upright",
        "tall_kneeling_upright",
        "half_kneeling_upright",
        "quadruped",
    ),
    "seated": (
        "neutral_upright",
        "seated_flexed_trunk",
        "long_sitting",
        "cross_legged_sitting",
    ),
    "supine": (
        "supine_hooklying",
        "supine_tabletop",
        "supine_straight_leg",
        "supine_hollow",
    ),
    "side_lying": (
        "side_supported",
        "side_plank_line",
        "side_lying_relaxed",
    ),
    "hanging": ("neutral_upright", "hanging_tuck", "hanging_pike"),
    "external_object_supported": (
        "neutral_upright",
        "neutral_prone_line",
        "side_supported",
        "supported_incline_line",
        "machine_supported_fixed_trunk",
        "custom",
    ),
}

_POSTURE_SUPPORT_TEMPLATE_VALUES: dict[str, tuple[str, ...]] = {
    "standing": ("bilateral_feet", "split_stance", "single_foot"),
    "floor_supported_prone": (
        "hands_and_feet",
        "forearms_and_feet",
        "hands_and_knees",
        "hands_and_feet_with_trunk",
    ),
    "kneeling": ("knees_floor", "one_knee_one_foot", "hands_and_knees"),
    "seated": ("seated_base",),
    "supine": ("supine_body_floor",),
    "side_lying": ("side_body_floor",),
    "hanging": ("overhead_hang",),
    "external_object_supported": (
        "external_object",
        "bilateral_feet",
        "split_stance",
        "hands_and_feet",
    ),
}

_JOINT_ACTION_REGION_HINTS: dict[str, tuple[str, ...]] = {
    "hip_flexion_extension": ("hip",),
    "knee_flexion_extension": ("knee",),
    "ankle_dorsiflexion_plantarflexion": ("ankle",),
    "shoulder_flexion_extension": ("shoulder",),
    "elbow_flexion_extension": ("elbow",),
    "wrist_flexion_extension": ("wrist",),
    "trunk_flexion_extension": ("trunk",),
    "trunk_lateral_flexion": ("trunk",),
    "trunk_rotation_proxy": ("trunk",),
    "pelvis_lateral_tilt_proxy": ("pelvis",),
    "pelvis_rotation_proxy": ("pelvis",),
    "pelvis_anterior_posterior_tilt_proxy": ("pelvis",),
    "scapular_stability_proxy": ("shoulder",),
    "anti_rotation_control": ("trunk", "pelvis"),
    "weight_shift_control": ("pelvis",),
}

_LOWER_BODY_BEND_ACTIONS: frozenset[str] = frozenset(
    {
        "hip_flexion_extension",
        "knee_flexion_extension",
        "ankle_dorsiflexion_plantarflexion",
    }
)
_UPPER_BODY_PRESS_ACTIONS: frozenset[str] = frozenset(
    {
        "shoulder_flexion_extension",
        "elbow_flexion_extension",
    }
)
_ANTI_ROTATION_ACTIONS: frozenset[str] = frozenset(
    {
        "anti_rotation_control",
        "weight_shift_control",
        "trunk_rotation_proxy",
        "pelvis_rotation_proxy",
    }
)

_BODY_REGION_ORDER: tuple[str, ...] = (
    "hip",
    "knee",
    "ankle",
    "foot",
    "pelvis",
    "trunk",
    "shoulder",
    "elbow",
    "wrist",
    "hand",
)

_CAMERA_VIEW_FAMILY_DEFAULT_ZONES: dict[str, tuple[str, ...]] = {
    "front": ("Z1",),
    "front_oblique": ("Z2", "Z8"),
    "side": ("Z3", "Z7"),
    "rear_oblique": ("Z4", "Z6"),
    "rear": ("Z5",),
}
_CAMERA_ZONE_TO_VIEW_FAMILY: dict[str, str] = {
    zone: view_family
    for view_family, zones in _CAMERA_VIEW_FAMILY_DEFAULT_ZONES.items()
    for zone in zones
}
_FLOOR_BASED_POSTURES: frozenset[str] = frozenset(
    {"floor_supported_prone", "supine", "side_lying"}
)
_LEGACY_CAMERA_TEMPLATE_DEFAULTS: dict[str, tuple[str, str]] = {
    "front_oblique_lower_body": ("front_oblique", "H2"),
    "side_lower_body": ("side", "H2"),
    "side_floor_upper_body": ("side", "H1"),
    "front_oblique_floor_core": ("front_oblique", "H1"),
}


@dataclass(frozen=True)
class ExerciseAuthoringSpec:
    """
    Small UI-facing draft used to generate exercise YAML artifacts.

    The spec intentionally avoids detailed thresholds and scoring rules. Those are
    generated from registries and marked for researcher review before becoming
    canonical project YAML.
    """

    exercise_id: str
    display_name: str
    movement_pattern: str
    posture_type: str
    laterality: str
    support_template: str
    primary_body_regions: tuple[str, ...]
    primary_joint_actions: tuple[str, ...]
    primary_plane: str
    phase_template: str
    counting_template: str
    camera_view_family: str
    camera_height_level: str
    analysis_template: str
    body_geometry: str = "neutral_upright"
    movement_pattern_source: str = "derived_from_joint_actions_and_context"
    target_sets: int | None = None
    target_count_per_set: int | None = None
    rest_between_sets_s: tuple[int, ...] = field(default_factory=tuple)
    description: str = ""
    tags: tuple[str, ...] = field(default_factory=tuple)
    secondary_joint_actions: tuple[str, ...] = field(default_factory=tuple)
    secondary_planes: tuple[str, ...] = field(default_factory=tuple)
    author_notes: str = ""

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> "ExerciseAuthoringSpec":
        """Create a spec from notebook/UI dictionary values."""
        target_sets = raw.get("target_sets")
        target_count_per_set = raw.get("target_count_per_set")
        rest_between_sets_s = raw.get("rest_between_sets_s") or ()
        camera_view_family = raw.get("camera_view_family")
        camera_height_level = raw.get("camera_height_level")
        camera_zone = raw.get("camera_zone")
        legacy_camera_template = raw.get("camera_template")
        if (
            (camera_view_family is None or camera_height_level is None)
            and legacy_camera_template in _LEGACY_CAMERA_TEMPLATE_DEFAULTS
        ):
            default_view_family, default_height = _LEGACY_CAMERA_TEMPLATE_DEFAULTS[
                str(legacy_camera_template)
            ]
            camera_view_family = camera_view_family or default_view_family
            camera_height_level = camera_height_level or default_height
        if camera_view_family in (None, "") and camera_zone not in (None, ""):
            camera_view_family = _CAMERA_ZONE_TO_VIEW_FAMILY.get(str(camera_zone), "")
        if camera_view_family in (None, ""):
            camera_view_family = ""
        if camera_height_level in (None, ""):
            camera_height_level = ""
        return cls(
            exercise_id=str(raw["exercise_id"]),
            display_name=str(raw["display_name"]),
            movement_pattern=str(raw["movement_pattern"]),
            movement_pattern_source=str(
                raw.get("movement_pattern_source")
                or "derived_from_joint_actions_and_context"
            ),
            posture_type=str(raw["posture_type"]),
            body_geometry=str(raw.get("body_geometry") or "neutral_upright"),
            laterality=str(raw["laterality"]),
            support_template=str(raw["support_template"]),
            primary_body_regions=tuple(raw.get("primary_body_regions") or ()),
            primary_joint_actions=tuple(raw.get("primary_joint_actions") or ()),
            primary_plane=str(raw["primary_plane"]),
            phase_template=str(raw["phase_template"]),
            counting_template=str(raw["counting_template"]),
            camera_view_family=str(camera_view_family),
            camera_height_level=str(camera_height_level),
            analysis_template=str(raw["analysis_template"]),
            target_sets=(
                int(target_sets)
                if target_sets not in (None, "")
                else None
            ),
            target_count_per_set=(
                int(target_count_per_set)
                if target_count_per_set not in (None, "")
                else None
            ),
            rest_between_sets_s=tuple(
                int(value) for value in rest_between_sets_s
            ),
            description=str(raw.get("description") or ""),
            tags=tuple(raw.get("tags") or ()),
            secondary_joint_actions=tuple(raw.get("secondary_joint_actions") or ()),
            secondary_planes=tuple(raw.get("secondary_planes") or ()),
            author_notes=str(raw.get("author_notes") or ""),
        )

    def as_dict(self) -> dict[str, Any]:
        """Return a YAML-friendly representation of the authoring spec."""
        return {
            "exercise_id": self.exercise_id,
            "display_name": self.display_name,
            "movement_pattern": self.movement_pattern,
            "movement_pattern_source": self.movement_pattern_source,
            "posture_type": self.posture_type,
            "body_geometry": self.body_geometry,
            "laterality": self.laterality,
            "support_template": self.support_template,
            "primary_body_regions": list(self.primary_body_regions),
            "primary_joint_actions": list(self.primary_joint_actions),
            "primary_plane": self.primary_plane,
            "secondary_planes": list(self.secondary_planes),
            "secondary_joint_actions": list(self.secondary_joint_actions),
            "phase_template": self.phase_template,
            "counting_template": self.counting_template,
            "target_sets": self.target_sets,
            "target_count_per_set": self.target_count_per_set,
            "rest_between_sets_s": list(self.rest_between_sets_s),
            "camera_view_family": self.camera_view_family,
            "camera_height_level": self.camera_height_level,
            "analysis_template": self.analysis_template,
            "description": self.description,
            "tags": list(self.tags),
            "author_notes": self.author_notes,
        }


def _load_yaml(path: Path) -> dict[str, Any]:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _dump_yaml(data: Mapping[str, Any]) -> str:
    return yaml.safe_dump(
        dict(data),
        allow_unicode=True,
        sort_keys=False,
        default_flow_style=False,
    )


def load_authoring_registries(
    registry_dir: Path | str = DEFAULT_REGISTRY_DIR,
) -> dict[str, Any]:
    """Load all YAML registries that drive exercise authoring choices."""
    registry_dir = Path(registry_dir)
    registries: dict[str, Any] = {}
    missing: list[Path] = []

    for name, filename in _REGISTRY_FILES.items():
        path = registry_dir / filename
        if not path.exists():
            missing.append(path)
            continue
        registries[name] = _load_yaml(path)

    if missing:
        joined = ", ".join(str(path) for path in missing)
        raise FileNotFoundError(f"Missing authoring registry file(s): {joined}")

    if not _CAMERA_ZONE_PATH.exists():
        raise FileNotFoundError(
            f"Missing camera zone registry file: {_CAMERA_ZONE_PATH}"
        )
    registries["camera_zones"] = _load_yaml(_CAMERA_ZONE_PATH)

    return registries


def derive_movement_pattern_from_authoring_axes(
    *,
    posture_type: str,
    body_geometry: str = "neutral_upright",
    laterality: str,
    support_template: str,
    primary_body_regions: Iterable[str],
    primary_joint_actions: Iterable[str] = (),
    secondary_joint_actions: Iterable[str] = (),
) -> str:
    """
    Derive the internal movement-pattern template from atomic authoring axes.

    This keeps researcher input focused on observable biomechanical structure:
    joint actions, contact base, side pattern, posture, and loaded body regions.
    """
    body_regions = tuple(str(region) for region in primary_body_regions)
    regions = set(body_regions)
    primary_actions = tuple(str(action) for action in primary_joint_actions)
    secondary_actions = tuple(str(action) for action in secondary_joint_actions)
    actions = set(primary_actions + secondary_actions)
    lower_body_regions = {"hip", "knee", "ankle", "foot", "pelvis"}
    upper_body_regions = {"shoulder", "elbow", "wrist", "hand"}
    trunk_regions = {"trunk", "pelvis"}
    has_lower_body_focus = bool(regions & lower_body_regions)
    has_upper_body_focus = bool(regions & upper_body_regions)
    has_trunk_focus = bool(regions & trunk_regions)
    has_lower_body_bend = len(actions & _LOWER_BODY_BEND_ACTIONS) >= 2
    has_upper_body_press = _UPPER_BODY_PRESS_ACTIONS.issubset(actions)
    has_anti_rotation = bool(actions & _ANTI_ROTATION_ACTIONS)
    is_bilateral = str(laterality).startswith("bilateral")
    is_floor_supported_prone = posture_type in {"floor_supported_prone", "plank"}

    if (
        support_template == "split_stance"
        and has_lower_body_focus
        and has_lower_body_bend
        and posture_type == "standing"
        and body_geometry == "neutral_upright"
    ):
        return "lunge"

    if (
        support_template == "bilateral_feet"
        and is_bilateral
        and has_lower_body_focus
        and has_lower_body_bend
        and posture_type == "standing"
        and body_geometry == "neutral_upright"
    ):
        return "squat"

    if (
        support_template in {"hands_and_feet", "hands_and_feet_with_trunk"}
        and laterality == "alternating"
        and is_floor_supported_prone
        and body_geometry == "neutral_prone_line"
        and has_anti_rotation
        and (has_trunk_focus or has_upper_body_focus)
    ):
        return "anti_rotation"

    if (
        support_template == "hands_and_feet"
        and is_bilateral
        and is_floor_supported_prone
        and body_geometry == "high_hip_inverted_v"
        and has_upper_body_press
        and has_upper_body_focus
    ):
        return "push"

    raise ValueError(
        "Could not derive movement_pattern from authoring axes: "
        f"posture_type={posture_type}, body_geometry={body_geometry}, "
        f"laterality={laterality}, "
        f"support_template={support_template}, "
        f"primary_body_regions={body_regions}, "
        f"primary_joint_actions={primary_actions}, "
        f"secondary_joint_actions={secondary_actions}"
    )


def suggest_body_regions_from_joint_actions(
    primary_joint_actions: Iterable[str],
    secondary_joint_actions: Iterable[str] = (),
) -> tuple[str, ...]:
    """
    Suggest analysis-focus regions from selected joint actions.

    The result is a UI suggestion, not a hidden rule. The researcher can override
    it when the intended analysis focus differs from the literal action list.
    """
    regions: set[str] = set()
    for action in tuple(primary_joint_actions) + tuple(secondary_joint_actions):
        regions.update(_JOINT_ACTION_REGION_HINTS.get(str(action), ()))

    return tuple(region for region in _BODY_REGION_ORDER if region in regions)


def recommend_phase_templates_for_authoring_axes(
    *,
    posture_type: str,
    body_geometry: str,
    support_template: str,
    primary_joint_actions: Iterable[str] = (),
    secondary_joint_actions: Iterable[str] = (),
    primary_plane: str,
) -> tuple[str, ...]:
    """
    Recommend phase templates from authoring context without hiding alternatives.

    The result orders the notebook dropdown. It is deliberately advisory because
    unusual exercises may need a non-recommended segmentation descriptor.
    """
    primary_actions = tuple(str(action) for action in primary_joint_actions)
    secondary_actions = tuple(str(action) for action in secondary_joint_actions)
    actions = set(primary_actions + secondary_actions)
    recommendations: list[str] = []

    def add(template_id: str) -> None:
        if template_id not in recommendations:
            recommendations.append(template_id)

    has_lower_body_bend = len(actions & _LOWER_BODY_BEND_ACTIONS) >= 2
    has_upper_body_press = _UPPER_BODY_PRESS_ACTIONS.issubset(actions)
    has_anti_rotation = bool(actions & _ANTI_ROTATION_ACTIONS)
    has_reach_action = bool(
        actions
        & {
            "shoulder_flexion_extension",
            "elbow_flexion_extension",
            "wrist_flexion_extension",
        }
    )
    has_rotation_action = bool(
        actions
        & {
            "trunk_rotation_proxy",
            "pelvis_rotation_proxy",
        }
    )

    if primary_plane == "static":
        add("static_hold_center")

    if (
        posture_type == "standing"
        and support_template in {"bilateral_feet", "split_stance", "single_foot"}
        and has_lower_body_bend
    ):
        add("descent_ascent_hip_center")

    if posture_type == "floor_supported_prone":
        if (
            body_geometry == "neutral_prone_line"
            and support_template in {"hands_and_feet", "hands_and_feet_with_trunk"}
            and has_anti_rotation
        ):
            add("lift_tap_return_wrist")
        if body_geometry == "high_hip_inverted_v" or has_upper_body_press:
            add("descent_ascent_nose")

    if posture_type == "supine":
        if body_geometry == "supine_hooklying" and "hip_flexion_extension" in actions:
            add("bridge_lift_lower_hip_center")
        if body_geometry in {"supine_tabletop", "supine_hollow"} and has_anti_rotation:
            add("static_hold_center")

    if has_rotation_action or primary_plane == "transverse":
        add("rotate_return_trunk")

    if (
        posture_type in {"standing", "seated", "external_object_supported"}
        and has_reach_action
        and not has_upper_body_press
    ):
        add("reach_return_wrist")

    return tuple(recommendations)


def recommend_counting_templates_for_authoring_axes(
    *,
    laterality: str,
    phase_template: str,
) -> tuple[str, ...]:
    """
    Recommend counting templates from side pattern and phase context.

    This is an authoring UI hint. Non-recommended templates remain selectable so
    unusual protocols can still be drafted for researcher review.
    """
    recommendations: list[str] = []

    def add(template_id: str) -> None:
        if template_id not in recommendations:
            recommendations.append(template_id)

    if phase_template == "static_hold_center":
        add("timed_hold_seconds")
        return tuple(recommendations)

    if laterality == "alternating":
        if phase_template == "lift_tap_return_wrist":
            add("alternating_left_right_pair")
        add("alternating_left_right_pair")
        add("same_side_block_then_switch_5_each")
        return tuple(recommendations)

    if laterality in {
        "bilateral_symmetric",
        "bilateral_asymmetric",
        "unilateral_left",
        "unilateral_right",
        "unilateral_unspecified",
    }:
        add("repeated_repetition")

    return tuple(recommendations)


def recommend_analysis_templates_for_authoring_axes(
    *,
    posture_type: str,
    body_geometry: str,
    laterality: str,
    support_template: str,
    primary_body_regions: Iterable[str],
    primary_joint_actions: Iterable[str] = (),
    secondary_joint_actions: Iterable[str] = (),
) -> tuple[str, ...]:
    """
    Recommend analysis-profile families from movement descriptors.

    The recommendation orders the authoring UI. It does not hide other analysis
    families because new or unusual exercises may still need researcher review.
    """
    regions = {str(region) for region in primary_body_regions}
    actions = {
        str(action)
        for action in tuple(primary_joint_actions) + tuple(secondary_joint_actions)
    }
    lower_body_regions = {"hip", "knee", "ankle", "foot", "pelvis"}
    upper_body_regions = {"shoulder", "elbow", "wrist", "hand"}
    trunk_regions = {"trunk", "pelvis"}
    has_lower_body_focus = bool(regions & lower_body_regions)
    has_upper_body_focus = bool(regions & upper_body_regions)
    has_trunk_focus = bool(regions & trunk_regions)
    has_lower_body_bend = len(actions & _LOWER_BODY_BEND_ACTIONS) >= 2
    has_upper_body_press = _UPPER_BODY_PRESS_ACTIONS.issubset(actions)
    has_anti_rotation = bool(actions & _ANTI_ROTATION_ACTIONS)
    is_bilateral = str(laterality).startswith("bilateral")
    recommendations: list[str] = []

    def add(template_id: str) -> None:
        if template_id not in recommendations:
            recommendations.append(template_id)

    if (
        posture_type == "standing"
        and support_template == "split_stance"
        and has_lower_body_focus
        and has_lower_body_bend
    ):
        add("alternating_lower_body_split_stance")

    if (
        posture_type == "standing"
        and support_template in {"bilateral_feet", "single_foot"}
        and has_lower_body_focus
        and has_lower_body_bend
    ):
        add("bilateral_lower_body_closed_chain")

    if (
        posture_type == "floor_supported_prone"
        and has_upper_body_focus
        and (has_upper_body_press or body_geometry == "high_hip_inverted_v")
    ):
        add("bilateral_upper_body_inverted_closed_chain")

    if (
        has_anti_rotation
        and (has_trunk_focus or has_upper_body_focus)
        and laterality == "alternating"
    ):
        add("alternating_core_anti_rotation")

    if not recommendations and has_lower_body_focus and has_lower_body_bend:
        add(
            "bilateral_lower_body_closed_chain"
            if is_bilateral
            else "alternating_lower_body_split_stance"
        )
    if not recommendations and has_upper_body_focus and has_upper_body_press:
        add("bilateral_upper_body_inverted_closed_chain")
    if not recommendations and has_anti_rotation:
        add("alternating_core_anti_rotation")

    return tuple(recommendations)


def _camera_position_id(view_family: str, height_level: str) -> str:
    return f"{view_family}/{height_level}"


def _camera_view_family_member_zones(
    camera_zones: Mapping[str, Any],
    view_family: str,
) -> list[str]:
    view_families = camera_zones.get("view_families") or {}
    family = view_families.get(view_family) or {}
    zones = family.get("member_zones")
    if zones:
        return [str(zone) for zone in zones]
    return list(_CAMERA_VIEW_FAMILY_DEFAULT_ZONES.get(view_family, ()))


def _camera_position_entry(
    position_id: str,
    camera_zones: Mapping[str, Any],
) -> dict[str, Any]:
    view_family, height_level = position_id.split("/", maxsplit=1)
    return {
        "view_family": view_family,
        "member_zones": _camera_view_family_member_zones(
            camera_zones,
            view_family,
        ),
        "height": height_level,
    }


def _camera_position_entries(
    position_ids: Iterable[str],
    camera_zones: Mapping[str, Any],
) -> list[dict[str, Any]]:
    return [
        _camera_position_entry(position_id, camera_zones)
        for position_id in position_ids
    ]


def _recommended_camera_height_for_context(
    *,
    posture_type: str,
    primary_body_regions: Iterable[str],
    primary_joint_actions: Iterable[str],
    secondary_joint_actions: Iterable[str],
) -> str:
    regions = {str(region) for region in primary_body_regions}
    actions = {
        str(action)
        for action in tuple(primary_joint_actions) + tuple(secondary_joint_actions)
    }
    upper_regions = {"shoulder", "elbow", "wrist", "hand"}
    lower_regions = {"hip", "knee", "ankle", "foot", "pelvis"}
    has_upper_focus = bool(regions & upper_regions)
    has_lower_focus = bool(regions & lower_regions)
    has_upper_press = _UPPER_BODY_PRESS_ACTIONS.issubset(actions)

    if posture_type in _FLOOR_BASED_POSTURES:
        return "H1"
    if posture_type == "hanging":
        return "H3"
    if has_upper_focus and not has_lower_focus and not has_upper_press:
        return "H3"
    return "H2"


def recommend_camera_positions_for_authoring_axes(
    *,
    posture_type: str,
    laterality: str,
    support_template: str,
    primary_body_regions: Iterable[str],
    primary_joint_actions: Iterable[str] = (),
    secondary_joint_actions: Iterable[str] = (),
    primary_plane: str,
) -> tuple[str, ...]:
    """
    Recommend camera view-family/H combinations from movement context.

    Recommendations are provenance hints for view reliability. They do not
    exclude non-recommended recordings and do not imply camera calibration.
    """
    regions = {str(region) for region in primary_body_regions}
    actions = {
        str(action)
        for action in tuple(primary_joint_actions) + tuple(secondary_joint_actions)
    }
    lower_body_regions = {"hip", "knee", "ankle", "foot", "pelvis"}
    upper_body_regions = {"shoulder", "elbow", "wrist", "hand"}
    has_lower_body_focus = bool(regions & lower_body_regions)
    has_upper_body_focus = bool(regions & upper_body_regions)
    has_lower_body_bend = len(actions & _LOWER_BODY_BEND_ACTIONS) >= 2
    has_upper_body_press = _UPPER_BODY_PRESS_ACTIONS.issubset(actions)
    has_anti_rotation = bool(actions & _ANTI_ROTATION_ACTIONS)
    is_bilateral = str(laterality).startswith("bilateral")

    height_level = _recommended_camera_height_for_context(
        posture_type=posture_type,
        primary_body_regions=regions,
        primary_joint_actions=primary_joint_actions,
        secondary_joint_actions=secondary_joint_actions,
    )

    if (
        posture_type == "standing"
        and support_template == "bilateral_feet"
        and is_bilateral
        and has_lower_body_focus
        and has_lower_body_bend
    ):
        view_families = ("front_oblique",)
    elif (
        posture_type == "standing"
        and has_lower_body_focus
        and has_lower_body_bend
        and not is_bilateral
    ):
        view_families = ("side",)
    elif (
        posture_type == "floor_supported_prone"
        and has_upper_body_focus
        and has_upper_body_press
    ):
        view_families = ("side",)
    elif has_anti_rotation or primary_plane == "transverse":
        view_families = ("front_oblique",)
    elif primary_plane == "sagittal":
        view_families = ("side",)
    elif primary_plane == "frontal":
        view_families = ("front",)
    elif primary_plane == "static":
        view_families = (
            ("front_oblique",)
            if posture_type in _FLOOR_BASED_POSTURES
            else ("front",)
        )
    else:
        view_families = ("front_oblique",)

    return tuple(
        _camera_position_id(view_family, height_level)
        for view_family in view_families
    )


def _camera_observation_purposes(
    spec: ExerciseAuthoringSpec,
) -> list[str]:
    actions = set(spec.primary_joint_actions + spec.secondary_joint_actions)
    has_lower_body_bend = len(actions & _LOWER_BODY_BEND_ACTIONS) >= 2
    has_upper_body_press = _UPPER_BODY_PRESS_ACTIONS.issubset(actions)
    has_anti_rotation = bool(actions & _ANTI_ROTATION_ACTIONS)

    if spec.posture_type == "standing" and has_lower_body_bend:
        if spec.support_template == "split_stance" or spec.laterality == "alternating":
            return [
                "sagittal_lower_limb_alignment",
                "anterior_knee_travel",
                "trunk_lean",
            ]
        return [
            "frontal_knee_alignment",
            "hip_flexion_depth",
            "bilateral_support_symmetry",
        ]
    if spec.posture_type == "floor_supported_prone" and has_upper_body_press:
        return [
            "shoulder_elbow_sagittal_rom",
            "trunk_hip_alignment",
            "support_stability",
        ]
    if has_anti_rotation:
        return [
            "pelvic_rotation",
            "weight_shift_control",
            "lateral_sway",
        ]
    return ["recording_view_review", "landmark_visibility_review"]


def _all_camera_position_ids(camera_zones: Mapping[str, Any]) -> tuple[str, ...]:
    view_families = tuple((camera_zones.get("view_families") or {}).keys())
    height_levels = tuple((camera_zones.get("height_levels") or {}).keys())
    return tuple(
        _camera_position_id(view_family, height_level)
        for height_level in height_levels
        for view_family in view_families
    )


def _build_camera_protocol(
    spec: ExerciseAuthoringSpec,
    registries: Mapping[str, Any],
) -> dict[str, Any]:
    camera_zones = registries["camera_zones"]
    all_position_ids = _all_camera_position_ids(camera_zones)
    recommended_position_ids = recommend_camera_positions_for_authoring_axes(
        posture_type=spec.posture_type,
        laterality=spec.laterality,
        support_template=spec.support_template,
        primary_body_regions=spec.primary_body_regions,
        primary_joint_actions=spec.primary_joint_actions,
        secondary_joint_actions=spec.secondary_joint_actions,
        primary_plane=spec.primary_plane,
    )
    selected_position_id = _camera_position_id(
        spec.camera_view_family,
        spec.camera_height_level,
    )
    recommended_set = set(recommended_position_ids)
    recommendation_status = (
        "recommended"
        if selected_position_id in recommended_set
        else "non_recommended"
    )
    non_recommended_position_ids = tuple(
        position_id
        for position_id in all_position_ids
        if position_id not in recommended_set
    )
    recommended_zones = list(
        dict.fromkeys(
            zone
            for position_id in recommended_position_ids
            for zone in _camera_position_entry(
                position_id,
                camera_zones,
            )["member_zones"]
        )
    )
    recommended_heights = list(
        dict.fromkeys(
            _camera_position_entry(position_id, camera_zones)["height"]
            for position_id in recommended_position_ids
        )
    )
    policy = camera_zones.get("policy") or {}

    return {
        "selected_view": {
            "view_family": spec.camera_view_family,
            "member_zones": _camera_view_family_member_zones(
                camera_zones,
                spec.camera_view_family,
            ),
            "height": spec.camera_height_level,
            "position_id": selected_position_id,
            "recommendation_status": recommendation_status,
        },
        "recommended_view_positions": _camera_position_entries(
            recommended_position_ids,
            camera_zones,
        ),
        "non_recommended_view_positions": _camera_position_entries(
            non_recommended_position_ids,
            camera_zones,
        ),
        "recommendation_source": "authoring_axes",
        "recommended_zones": recommended_zones,
        "recommended_height": (
            recommended_heights[0] if len(recommended_heights) == 1 else None
        ),
        "anchor": "reference_mat",
        "distance_cm": list(camera_zones.get("default_distance_cm") or [200, 250]),
        "primary_observation_purpose": _camera_observation_purposes(spec),
        "out_of_zone_policy": policy.get("out_of_zone", "warn_and_continue"),
        "coordinate_correction": policy.get("coordinate_correction", "none"),
    }


def validate_authoring_spec(
    spec: ExerciseAuthoringSpec,
    registries: Mapping[str, Any],
) -> None:
    """Validate required spec fields and referenced registry template IDs."""
    schema = registries["schema"]
    required_fields = list(schema.get("required_fields") or [])
    spec_dict = spec.as_dict()
    missing_fields = [
        field_name
        for field_name in required_fields
        if spec_dict.get(field_name) in (None, "", [])
    ]
    if missing_fields:
        raise ValueError(
            "Exercise authoring spec is missing required field(s): "
            + ", ".join(missing_fields)
        )

    template_checks = {
        "movement_pattern": (
            spec.movement_pattern,
            registries["movement_patterns"].get("patterns") or {},
        ),
        "support_template": (
            spec.support_template,
            registries["support_templates"].get("templates") or {},
        ),
        "phase_template": (
            spec.phase_template,
            registries["phase_templates"].get("templates") or {},
        ),
        "counting_template": (
            spec.counting_template,
            registries["performance_templates"].get("templates") or {},
        ),
        "analysis_template": (
            spec.analysis_template,
            registries["analysis_templates"].get("templates") or {},
        ),
    }

    unknown: list[str] = []
    for field_name, (template_id, registry) in template_checks.items():
        if template_id not in registry:
            unknown.append(f"{field_name}={template_id}")

    if unknown:
        raise ValueError(
            "Unknown authoring template reference(s): " + ", ".join(unknown)
        )

    camera_zones = registries["camera_zones"]
    known_view_families = camera_zones.get("view_families") or {}
    known_height_levels = camera_zones.get("height_levels") or {}
    if spec.camera_view_family not in known_view_families:
        raise ValueError(f"Unknown camera_view_family={spec.camera_view_family}")
    if spec.camera_height_level not in known_height_levels:
        raise ValueError(
            f"Unknown camera_height_level={spec.camera_height_level}"
        )

    allowed_geometries = _POSTURE_BODY_GEOMETRY_VALUES.get(spec.posture_type)
    if allowed_geometries is None:
        raise ValueError(f"Unknown posture_type={spec.posture_type}")
    if spec.body_geometry not in allowed_geometries:
        allowed = ", ".join(allowed_geometries)
        raise ValueError(
            f"body_geometry={spec.body_geometry} is not compatible with "
            f"posture_type={spec.posture_type}; allowed: {allowed}"
        )

    allowed_support_templates = _POSTURE_SUPPORT_TEMPLATE_VALUES[spec.posture_type]
    if spec.support_template not in allowed_support_templates:
        allowed = ", ".join(allowed_support_templates)
        raise ValueError(
            f"support_template={spec.support_template} is not compatible with "
            f"posture_type={spec.posture_type}; allowed: {allowed}"
        )

    if spec.target_sets is not None and spec.target_sets <= 0:
        raise ValueError("target_sets must be a positive integer")
    if (
        spec.target_count_per_set is not None
        and spec.target_count_per_set <= 0
    ):
        raise ValueError("target_count_per_set must be a positive integer")
    if spec.rest_between_sets_s:
        if len(spec.rest_between_sets_s) != 2:
            raise ValueError("rest_between_sets_s must contain two values")
        rest_min_s, rest_max_s = spec.rest_between_sets_s
        if rest_min_s < 0 or rest_max_s < 0 or rest_min_s > rest_max_s:
            raise ValueError(
                "rest_between_sets_s must be a non-negative [min, max] range"
            )


def _metadata(requires_review: list[str]) -> dict[str, Any]:
    return {
        "status": "draft",
        "generated_by": _GENERATED_BY,
        "requires_review": requires_review,
    }


def _registry_item(
    registry: Mapping[str, Any], section: str, item_id: str
) -> dict[str, Any]:
    section_data = registry.get(section) or {}
    return deepcopy(section_data[item_id])


def _apply_performance_overrides(
    performance: dict[str, Any], spec: ExerciseAuthoringSpec
) -> None:
    prescription = performance.setdefault("prescription", {})
    counting = performance.setdefault("counting", {})
    completion = performance.setdefault("completion", {})

    if spec.target_sets is not None:
        prescription["target_sets"] = spec.target_sets
        completion["recommended_sets"] = spec.target_sets
    else:
        prescription.pop("target_sets", None)
        completion.pop("recommended_sets", None)

    if spec.target_count_per_set is not None:
        prescription["target_count_per_set"] = spec.target_count_per_set
        counting["target_count"] = spec.target_count_per_set

    if spec.rest_between_sets_s:
        prescription["rest_between_sets_s"] = list(spec.rest_between_sets_s)
    else:
        prescription.pop("rest_between_sets_s", None)


def _joint_actions_from_spec(
    pattern: Mapping[str, Any], spec: ExerciseAuthoringSpec
) -> dict[str, list[str]]:
    if spec.primary_joint_actions or spec.secondary_joint_actions:
        return {
            "primary": list(spec.primary_joint_actions),
            "secondary": list(spec.secondary_joint_actions),
        }
    return deepcopy(pattern.get("joint_actions") or {})


def _append_unique(values: Iterable[str], additions: Iterable[str]) -> list[str]:
    merged: list[str] = []
    for value in tuple(values) + tuple(additions):
        item = str(value)
        if item not in merged:
            merged.append(item)
    return merged


def _merge_feature_domain_additions(
    feature_domains: Mapping[str, Any],
    additions: Mapping[str, Iterable[str]],
) -> dict[str, list[str]]:
    merged: dict[str, list[str]] = {
        str(domain): [str(value) for value in values]
        for domain, values in feature_domains.items()
    }
    for domain, values in additions.items():
        merged[str(domain)] = _append_unique(merged.get(str(domain), []), values)
    return merged


def _is_standing_bilateral_lower_body_bend(
    spec: ExerciseAuthoringSpec,
) -> bool:
    actions = set(spec.primary_joint_actions + spec.secondary_joint_actions)
    regions = {str(region) for region in spec.primary_body_regions}
    return (
        spec.posture_type == "standing"
        and spec.support_template == "bilateral_feet"
        and str(spec.laterality).startswith("bilateral")
        and spec.primary_plane == "sagittal"
        and _LOWER_BODY_BEND_ACTIONS.issubset(actions)
        and {"hip", "knee", "ankle"}.issubset(regions)
    )


def _infer_from_authoring_context(
    spec: ExerciseAuthoringSpec,
) -> dict[str, Any]:
    """
    Infer only narrow, explainable additions from structural authoring axes.

    These additions are draft conveniences, not canonical exercise identity.
    They remain review-labeled so a researcher can reject them before promotion.
    """
    inferred_secondary_actions: list[str] = []
    inferred_candidates: list[str] = []
    inferred_feature_domains: dict[str, list[str]] = {}
    active_rules: list[str] = []

    secondary_planes = {str(plane) for plane in spec.secondary_planes}
    if _is_standing_bilateral_lower_body_bend(spec):
        rule_id = "standing_bilateral_feet_sagittal_lower_body_bend"
        if "frontal" in secondary_planes:
            active_rules.append(f"{rule_id}_frontal")
            inferred_secondary_actions.append("pelvis_lateral_tilt_proxy")
            inferred_feature_domains["control"] = _append_unique(
                inferred_feature_domains.get("control", []),
                ["joint_tracking_error"],
            )
        if "transverse" in secondary_planes:
            active_rules.append(f"{rule_id}_transverse")
            inferred_secondary_actions.append("pelvis_rotation_proxy")
            inferred_candidates.append("foot_external_rotation_proxy")
        if secondary_planes & {"frontal", "transverse"}:
            inferred_feature_domains["biomechanical_proxy"] = _append_unique(
                inferred_feature_domains.get("biomechanical_proxy", []),
                ["compensation_load_shift_proxy"],
            )

    review_flags: list[str] = []
    if inferred_secondary_actions:
        review_flags.append("context_inferred_joint_actions")
    if inferred_candidates:
        review_flags.append("context_inferred_compensation_candidates")
    if inferred_feature_domains:
        review_flags.append("context_inferred_feature_domains")

    return {
        "source": "authoring_axes",
        "active_rules": active_rules,
        "inferred_secondary_joint_actions": _append_unique(
            (), inferred_secondary_actions
        ),
        "inferred_compensation_candidates": _append_unique((), inferred_candidates),
        "inferred_feature_domains": inferred_feature_domains,
        "requires_review": review_flags,
    }


def generate_authoring_artifacts(
    spec: ExerciseAuthoringSpec,
    registries: Mapping[str, Any],
) -> dict[str, dict[str, Any]]:
    """
    Generate draft YAML artifact dictionaries from an authoring spec.

    Returns a mapping with four keys:
    `exercise_definition`, `analysis_profile`, `performance_protocol`, and
    `camera_protocol`.
    """
    validate_authoring_spec(spec, registries)

    pattern = _registry_item(
        registries["movement_patterns"], "patterns", spec.movement_pattern
    )
    support = _registry_item(
        registries["support_templates"], "templates", spec.support_template
    )
    phase = _registry_item(
        registries["phase_templates"], "templates", spec.phase_template
    )
    analysis = _registry_item(
        registries["analysis_templates"], "templates", spec.analysis_template
    )
    performance = _registry_item(
        registries["performance_templates"], "templates", spec.counting_template
    )
    _apply_performance_overrides(performance, spec)
    camera_protocol_data = _build_camera_protocol(spec, registries)
    landmark_set_id = analysis.get("landmark_set")
    landmark_set = _registry_item(
        registries["landmark_sets"], "sets", str(landmark_set_id)
    )
    context_inference = _infer_from_authoring_context(spec)

    classification = deepcopy(pattern.get("classification") or {})
    classification.update(
        {
            "posture_type": spec.posture_type,
            "body_geometry": spec.body_geometry,
            "laterality": spec.laterality,
            "movement_pattern_source": spec.movement_pattern_source,
            "primary_plane": spec.primary_plane,
            "secondary_planes": list(spec.secondary_planes),
        }
    )

    description = spec.description or str(pattern.get("default_description") or "")
    tags = list(spec.tags or pattern.get("default_tags") or [])
    joint_actions = _joint_actions_from_spec(pattern, spec)
    joint_actions["secondary"] = _append_unique(
        joint_actions.get("secondary", ()),
        context_inference["inferred_secondary_joint_actions"],
    )
    secondary_joint_actions = _append_unique(
        spec.secondary_joint_actions,
        context_inference["inferred_secondary_joint_actions"],
    )

    exercise_definition = {
        **_metadata(["biomechanical_identity"]),
        "exercise_id": spec.exercise_id,
        "display_name": spec.display_name,
        "description": description,
        "version": "draft",
        "tags": tags,
        "classification": classification,
        "support": support,
        "primary_body_regions": list(spec.primary_body_regions),
        "phase_model": deepcopy(phase["phase_model"]),
        "joint_actions": joint_actions,
        "biomechanical_identity": {
            **deepcopy(pattern.get("biomechanical_identity") or {}),
            "primary_body_regions": list(spec.primary_body_regions),
            "primary_joint_actions": list(spec.primary_joint_actions),
            "secondary_joint_actions": secondary_joint_actions,
        },
        "authoring_spec": spec.as_dict(),
    }
    if context_inference["active_rules"]:
        exercise_definition["authoring_inference"] = {
            "source": context_inference["source"],
            "active_rules": context_inference["active_rules"],
            "inferred_secondary_joint_actions": context_inference[
                "inferred_secondary_joint_actions"
            ],
        }
    if spec.author_notes:
        exercise_definition["author_notes"] = spec.author_notes

    analysis_candidates = _append_unique(
        analysis["compensation_candidates"],
        context_inference["inferred_compensation_candidates"],
    )
    analysis_feature_domains = _merge_feature_domain_additions(
        analysis["feature_domains"],
        context_inference["inferred_feature_domains"],
    )
    analysis_requires_review = _append_unique(
        [
            "compensation_candidates",
            "quality_rules",
            "feature_domains",
        ],
        context_inference["requires_review"],
    )
    analysis_profile = {
        **_metadata(analysis_requires_review),
        "exercise_id": spec.exercise_id,
        "analysis_template": spec.analysis_template,
        "landmark_set": landmark_set_id,
        "landmarks": deepcopy(landmark_set["landmarks"]),
        "angle_definitions": deepcopy(landmark_set["angle_definitions"]),
        "rep_segmentation": deepcopy(phase["rep_segmentation"]),
        "phase_segmentation": deepcopy(phase["phase_segmentation"]),
        "biomechanical_focus": deepcopy(analysis["biomechanical_focus"]),
        "compensation_candidates": analysis_candidates,
        "feature_domains": analysis_feature_domains,
        "quality_rules": deepcopy(analysis["quality_rules"]),
    }
    if context_inference["active_rules"]:
        analysis_profile["authoring_inference"] = context_inference

    performance_protocol = {
        **_metadata(["participant_cues", "analysis_disrupting_patterns"]),
        "exercise_id": spec.exercise_id,
        "counting_template": spec.counting_template,
        "performance_protocol": performance,
    }

    camera_protocol = {
        **_metadata(["view_metric_reliability", "primary_observation_purpose"]),
        "exercise_id": spec.exercise_id,
        "camera_protocol": camera_protocol_data,
        "view_metric_reliability": {
            "structure": spec.laterality,
            "position_recommendation": {
                "selected": camera_protocol_data["selected_view"],
                "recommended_view_positions": camera_protocol_data[
                    "recommended_view_positions"
                ],
                "non_recommended_view_positions": camera_protocol_data[
                    "non_recommended_view_positions"
                ],
            },
        },
    }

    return {
        "exercise_definition": exercise_definition,
        "analysis_profile": analysis_profile,
        "performance_protocol": performance_protocol,
        "camera_protocol": camera_protocol,
    }


def artifact_to_yaml(artifact: Mapping[str, Any]) -> str:
    """Serialize one generated artifact using stable key order."""
    return _dump_yaml(artifact)


def draft_artifact_paths(
    exercise_id: str,
    draft_root: Path | str = DEFAULT_DRAFT_ROOT,
) -> dict[str, Path]:
    """Return draft artifact paths under the authoring draft root."""
    root = Path(draft_root) / exercise_id
    return {
        key: root / relative_path.format(exercise_id=exercise_id)
        for key, relative_path in _ARTIFACT_PATHS.items()
    }


def write_authoring_draft_artifacts(
    artifacts: Mapping[str, Mapping[str, Any]],
    draft_root: Path | str = DEFAULT_DRAFT_ROOT,
    *,
    overwrite: bool = False,
) -> dict[str, Path]:
    """
    Write generated artifacts under data/processed authoring drafts.

    Existing files are protected by default so a notebook preview cannot silently
    replace an earlier reviewed draft.
    """
    exercise_ids = {
        str(artifact.get("exercise_id"))
        for artifact in artifacts.values()
        if artifact.get("exercise_id")
    }
    if len(exercise_ids) != 1:
        raise ValueError("All artifacts must contain the same non-empty exercise_id")

    exercise_id = next(iter(exercise_ids))
    paths = draft_artifact_paths(exercise_id, draft_root=draft_root)
    missing_keys = sorted(set(paths) - set(artifacts))
    if missing_keys:
        raise ValueError("Missing generated artifact(s): " + ", ".join(missing_keys))

    existing = [path for path in paths.values() if path.exists()]
    if existing and not overwrite:
        joined = ", ".join(str(path) for path in existing)
        raise FileExistsError(
            "Draft artifact(s) already exist; pass overwrite=True to replace: " + joined
        )

    for key, path in paths.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(artifact_to_yaml(artifacts[key]), encoding="utf-8")

    return paths


__all__ = [
    "DEFAULT_DRAFT_ROOT",
    "DEFAULT_REGISTRY_DIR",
    "ExerciseAuthoringSpec",
    "artifact_to_yaml",
    "derive_movement_pattern_from_authoring_axes",
    "draft_artifact_paths",
    "generate_authoring_artifacts",
    "load_authoring_registries",
    "recommend_analysis_templates_for_authoring_axes",
    "recommend_camera_positions_for_authoring_axes",
    "recommend_counting_templates_for_authoring_axes",
    "recommend_phase_templates_for_authoring_axes",
    "suggest_body_regions_from_joint_actions",
    "validate_authoring_spec",
    "write_authoring_draft_artifacts",
]
