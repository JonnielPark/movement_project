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
from typing import Any, Mapping

import yaml


_REGISTRY_FILES: dict[str, str] = {
    "schema": "exercise_authoring_schema.yaml",
    "movement_patterns": "movement_patterns.yaml",
    "support_templates": "support_templates.yaml",
    "phase_templates": "phase_templates.yaml",
    "landmark_sets": "landmark_sets.yaml",
    "analysis_templates": "analysis_templates.yaml",
    "performance_templates": "performance_templates.yaml",
    "camera_templates": "camera_templates.yaml",
}

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_REGISTRY_DIR = _PROJECT_ROOT / "data" / "registries"
DEFAULT_DRAFT_ROOT = _PROJECT_ROOT / "data" / "processed" / "authoring_drafts"

_ARTIFACT_PATHS: dict[str, str] = {
    "exercise_definition": "data/definitions/exercises/{exercise_id}.yaml",
    "analysis_profile": "data/definitions/analysis_profiles/{exercise_id}.yaml",
    "performance_protocol": "data/protocols/performance/{exercise_id}.yaml",
    "camera_protocol": "data/protocols/camera/{exercise_id}.yaml",
}

_GENERATED_BY = "exercise_authoring_notebook"


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
    primary_plane: str
    phase_template: str
    counting_template: str
    camera_template: str
    analysis_template: str
    description: str = ""
    tags: tuple[str, ...] = field(default_factory=tuple)
    secondary_planes: tuple[str, ...] = field(default_factory=tuple)
    author_notes: str = ""

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> "ExerciseAuthoringSpec":
        """Create a spec from notebook/UI dictionary values."""
        return cls(
            exercise_id=str(raw["exercise_id"]),
            display_name=str(raw["display_name"]),
            movement_pattern=str(raw["movement_pattern"]),
            posture_type=str(raw["posture_type"]),
            laterality=str(raw["laterality"]),
            support_template=str(raw["support_template"]),
            primary_body_regions=tuple(raw.get("primary_body_regions") or ()),
            primary_plane=str(raw["primary_plane"]),
            phase_template=str(raw["phase_template"]),
            counting_template=str(raw["counting_template"]),
            camera_template=str(raw["camera_template"]),
            analysis_template=str(raw["analysis_template"]),
            description=str(raw.get("description") or ""),
            tags=tuple(raw.get("tags") or ()),
            secondary_planes=tuple(raw.get("secondary_planes") or ()),
            author_notes=str(raw.get("author_notes") or ""),
        )

    def as_dict(self) -> dict[str, Any]:
        """Return a YAML-friendly representation of the authoring spec."""
        return {
            "exercise_id": self.exercise_id,
            "display_name": self.display_name,
            "movement_pattern": self.movement_pattern,
            "posture_type": self.posture_type,
            "laterality": self.laterality,
            "support_template": self.support_template,
            "primary_body_regions": list(self.primary_body_regions),
            "primary_plane": self.primary_plane,
            "secondary_planes": list(self.secondary_planes),
            "phase_template": self.phase_template,
            "counting_template": self.counting_template,
            "camera_template": self.camera_template,
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

    return registries


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
        "camera_template": (
            spec.camera_template,
            registries["camera_templates"].get("templates") or {},
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
    camera = _registry_item(
        registries["camera_templates"], "templates", spec.camera_template
    )
    landmark_set_id = analysis.get("landmark_set")
    landmark_set = _registry_item(
        registries["landmark_sets"], "sets", str(landmark_set_id)
    )

    classification = deepcopy(pattern.get("classification") or {})
    classification.update(
        {
            "posture_type": spec.posture_type,
            "laterality": spec.laterality,
            "primary_plane": spec.primary_plane,
            "secondary_planes": list(spec.secondary_planes),
        }
    )

    description = spec.description or str(pattern.get("default_description") or "")
    tags = list(spec.tags or pattern.get("default_tags") or [])

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
        "joint_actions": deepcopy(pattern.get("joint_actions") or {}),
        "biomechanical_identity": {
            **deepcopy(pattern.get("biomechanical_identity") or {}),
            "primary_body_regions": list(spec.primary_body_regions),
        },
        "authoring_spec": spec.as_dict(),
    }
    if spec.author_notes:
        exercise_definition["author_notes"] = spec.author_notes

    analysis_profile = {
        **_metadata(
            [
                "compensation_candidates",
                "quality_rules",
                "feature_domains",
            ]
        ),
        "exercise_id": spec.exercise_id,
        "analysis_template": spec.analysis_template,
        "landmark_set": landmark_set_id,
        "landmarks": deepcopy(landmark_set["landmarks"]),
        "angle_definitions": deepcopy(landmark_set["angle_definitions"]),
        "rep_segmentation": deepcopy(phase["rep_segmentation"]),
        "phase_segmentation": deepcopy(phase["phase_segmentation"]),
        "biomechanical_focus": deepcopy(analysis["biomechanical_focus"]),
        "compensation_candidates": deepcopy(analysis["compensation_candidates"]),
        "feature_domains": deepcopy(analysis["feature_domains"]),
        "quality_rules": deepcopy(analysis["quality_rules"]),
    }

    performance_protocol = {
        **_metadata(["participant_cues", "analysis_disrupting_patterns"]),
        "exercise_id": spec.exercise_id,
        "counting_template": spec.counting_template,
        "performance_protocol": performance,
    }

    camera_protocol = {
        **_metadata(["view_metric_reliability", "primary_observation_purpose"]),
        "exercise_id": spec.exercise_id,
        "camera_template": spec.camera_template,
        **camera,
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
    "draft_artifact_paths",
    "generate_authoring_artifacts",
    "load_authoring_registries",
    "validate_authoring_spec",
    "write_authoring_draft_artifacts",
]
