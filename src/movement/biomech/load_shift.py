"""
⑨ Biomechanical Load Shift — within-set joint load migration trend.

Dissertation §6.5: as reps accumulate within a set, load redistributes
between joints (e.g. knee moment-arm decreases while hip moment-arm increases),
indicating fatigue-driven or compensation-driven load migration.

Method:
    OLS slope of per-rep moment-arm median ~ rep_id for each (joint × side).
    Input records come from biomech.moment_arm (compute_moment_arms output).

Unit: torso_length_ratio_per_rep (TLR/rep).
    A negative slope for the knee means the knee moment-arm is shrinking
    across reps — consistent with load shifting away from the knee.

Minimum reps: 3. Fewer reps yield an unreliable slope and are skipped.
"""

from __future__ import annotations

import re
from collections import defaultdict

import numpy as np

from movement.biomech import BiomechRecord

# Matches metric_ids produced by compute_moment_arms, e.g.:
#   biomech.moment_arm.knee.left.median
#   biomech.moment_arm.hip.right.median
#   biomech.moment_arm.shoulder.left.median
_MOMENT_ARM_RE = re.compile(
    r"^biomech\.moment_arm\.(?P<joint>\w+)\.(?P<side>\w+)\.median$"
)

_MIN_REPS = 3


def _make_note(joint: str, side: str, slope: float) -> str:
    """Human-readable biomechanical interpretation of the slope."""
    direction = "decreasing" if slope < 0 else "increasing"
    abs_s = abs(slope)
    suffix = ""
    if joint == "knee" and slope < 0:
        suffix = "; possible load shift toward hip"
    elif joint == "hip" and slope > 0:
        suffix = "; possible progressive hip-load accumulation"
    elif joint == "knee" and slope > 0:
        suffix = "; increasing knee-extensor demand across reps"
    elif joint == "shoulder" and slope < 0:
        suffix = "; decreasing shoulder moment-arm across reps"
    return (
        f"{joint.capitalize()} moment-arm {direction} at "
        f"{slope:+.4f} TLR/rep ({side} side){suffix}"
    )


def compute_load_shift(
    rep_records: list[BiomechRecord],
) -> list[BiomechRecord]:
    """Detect within-set load migration by regressing per-rep moment-arm medians.

    Takes the output of compute_moment_arms (one BiomechRecord per rep per joint-side)
    and fits an OLS line to moment_arm.median ~ rep_id for each (joint × side) pair.
    Returns one BiomechRecord per pair whose slope captures the directional trend.

    Biomechanical meaning: a negative knee slope alongside a positive hip slope
    indicates the load redistribution pattern typical of quadriceps fatigue —
    the moment-arm shortens at the knee while lengthening at the hip.

    Parameters
    ----------
    rep_records : list[BiomechRecord]
        Per-rep BiomechRecord list (typically from compute_moment_arms).
        Records without a numeric rep_id are ignored.

    Returns
    -------
    list[BiomechRecord]
        One set-level BiomechRecord per (joint × side) that had ≥ 3 reps.
        metric_id format: ``biomech.load_shift.<joint>.<side>.slope``
        unit: ``torso_length_ratio_per_rep``
    """
    # Group (rep_id, value) pairs by (exercise_id, joint, side)
    grouped: dict[tuple[str, str, str], list[tuple[int, float]]] = defaultdict(list)
    source_map: dict[tuple[str, str, str], list[str]] = {}
    ex_map: dict[tuple[str, str, str], str] = {}

    for rec in rep_records:
        if rec.rep_id is None:
            continue
        m = _MOMENT_ARM_RE.match(rec.metric_id)
        if m is None:
            continue
        joint = m.group("joint")
        side = m.group("side")
        key = (rec.exercise_id, joint, side)
        grouped[key].append((rec.rep_id, rec.value))
        source_map.setdefault(key, list(rec.source_fields))
        ex_map[key] = rec.exercise_id

    results: list[BiomechRecord] = []

    for (ex_id, joint, side), rep_vals in grouped.items():
        if len(rep_vals) < _MIN_REPS:
            continue

        rep_vals_sorted = sorted(rep_vals, key=lambda x: x[0])
        rep_ids = np.array([v[0] for v in rep_vals_sorted], dtype=float)
        medians = np.array([v[1] for v in rep_vals_sorted], dtype=float)

        # OLS slope via numpy polyfit (degree-1 polynomial)
        slope = float(np.polyfit(rep_ids, medians, 1)[0])

        sf = list(source_map.get((ex_id, joint, side), []))
        sf.append("biomech.load_shift.compute_load_shift")

        results.append(
            BiomechRecord(
                metric_id=f"biomech.load_shift.{joint}.{side}.slope",
                exercise_id=ex_id,
                rep_id=None,
                value=round(slope, 6),
                unit="torso_length_ratio_per_rep",
                source_fields=sf,
                note=_make_note(joint, side, slope),
                visibility_weight_applied=False,
                n_frames_used=len(rep_vals),
                n_frames_excluded_low_visibility=0,
            )
        )

    return results
