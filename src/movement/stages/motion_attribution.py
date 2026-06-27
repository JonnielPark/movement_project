"""Legacy compatibility shim for Feature Extraction side-role context.

New code should import from `movement.features.side_role_context` or
`movement.side_role_context`. This module remains so older notebooks and tests
that import motion-attribution names continue to resolve to the same
implementation.
"""

from movement.features.side_role_context import (
    AttributionReport,
    AttributionThresholds,
    SideRoleContextReport,
    SideRoleContextThresholds,
    attribute_motion,
    resolve_side_role_context,
)

__all__ = [
    "SideRoleContextThresholds",
    "SideRoleContextReport",
    "resolve_side_role_context",
    "AttributionThresholds",
    "AttributionReport",
    "attribute_motion",
]
