"""
Robustness Simulation

Injects artificial conditions into normal synthetic pose data to evaluate the
engineering robustness of the analysis framework.

Called outside the ①–⑩ pipeline steps; not included in run_pipeline().

Submodule:
  simulation.synthetic → synthetic data generation and condition injection functions

Supported simulation conditions:
  - ROM restriction : artificially reduce joint range of motion
  - Gaussian noise  : coordinate noise (σ in torso_length_ratio units)
  - Occlusion       : set landmark visibility to 0 and coordinates to NaN
  - Velocity spike  : insert position jumps at specified frames

All functions return a pose dataframe in the same column format as the input
plus a simulation_log dict.

Unit convention: distances/displacements in torso_length_ratio; angles in degree.
Absolute units (N, kg, m) are not used.
"""

from __future__ import annotations

from movement.simulation.synthetic import (  # noqa
    add_gaussian_noise,
    add_occlusion,
    add_velocity_spike,
    generate_squat_csv,
    restrict_rom,
)

__all__ = [
    "add_gaussian_noise",
    "add_occlusion",
    "add_velocity_spike",
    "generate_squat_csv",
    "restrict_rom",
]
