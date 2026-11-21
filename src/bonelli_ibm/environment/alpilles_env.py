"""Biophysical environment engine for the Alpilles massif (EPSG:2154, 10 m grid)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

from bonelli_ibm.core.config import EnvironmentConfig


class AlpillesEnvironment:
    """Full biophysical environment engine for the Massif des Alpilles.

    Implements ``EnvironmentInterface`` using the static-10 m-in-RAM + lazy
    pointwise evaluation strategy defined in ADR-02 and the multi-scale
    schedule defined in ``ODD_Env_Dynamique_et_Planification.md``.
    """

    def __init__(
        self,
        env_config: EnvironmentConfig,
        rng: np.random.Generator,
        data_dir: str | Path | None = None,
    ) -> None:
        """Initialize the Alpilles environment engine.

        Args:
            env_config: Validated Alpilles configuration (``alpilles.yaml``).
            rng: Centralized reproducible NumPy Generator.
            data_dir: Optional root directory containing RGE ALTI, OSO Theia,
                and meteorological forcing files.
        """
        raise NotImplementedError

    def initialize(self) -> None:
        """Load and align static 10 m rasters in EPSG:2154 and run warmup year."""
        raise NotImplementedError

    def step_daily(self, julian_day: int) -> None:
        """Execute daily update (ephemeris, ``theta_0``, GDD/NDVI phenology, KBI).

        Args:
            julian_day: Day of year in ``[1, 365]``.
        """
        raise NotImplementedError

    def step_hourly(self, julian_day: int, hour: int) -> None:
        """Execute hourly update (weather forcing, Mistral cutoff, ``w*``, circadian weights).

        Args:
            julian_day: Day of year in ``[1, 365]``.
            hour: Solar hour in ``[0, 23]``.
        """
        raise NotImplementedError

    def interpolate_2step(
        self,
        variable_name: str,
        x: float,
        y: float,
        t: float,
    ) -> float:
        """Evaluate a continuous environmental field via Movebank Env-DATA 2-step interpolation.

        Performs spatial bilinear interpolation at bracketing timestamps ``t_prev <= t <= t_next``
        followed by temporal inverse-distance weighting (exponent ``p = 1``).

        Args:
            variable_name: Name of the meteorological or satellite field to interpolate.
            x: Easting coordinate in meters (EPSG:2154).
            y: Northing coordinate in meters (EPSG:2154).
            t: Continuous simulation timestamp in seconds.

        Returns:
            Interpolated scalar value at ``(x, y, t)``.
        """
        raise NotImplementedError

    def get_weather(self, x: float, y: float, t: float) -> dict[str, float]:
        """Return interpolated meteorological forcing and solar ephemeris at (x, y, t).

        Args:
            x: Easting coordinate in meters (EPSG:2154).
            y: Northing coordinate in meters (EPSG:2154).
            t: Simulation time in seconds.

        Returns:
            Dictionary of meteorological and solar ephemeris variables.
        """
        raise NotImplementedError

    def get_aerology(self, x: float, y: float, z: float, t: float) -> float:
        """Evaluate ``w_uplift = w_oro + w_th`` lazily at ``(x, y, z, t)``.

        Args:
            x: Easting coordinate in meters (EPSG:2154).
            y: Northing coordinate in meters (EPSG:2154).
            z: Altitude above sea level in meters.
            t: Simulation time in seconds.

        Returns:
            Total vertical air velocity ``w_uplift`` in m/s.
        """
        raise NotImplementedError

    def get_cell_habitat(self, x: float, y: float) -> dict[str, float]:
        """Return O(1)-indexed topographic, habitat, and trophic attributes at (x, y).

        Args:
            x: Easting coordinate in meters (EPSG:2154).
            y: Northing coordinate in meters (EPSG:2154).

        Returns:
            Dictionary of local cell habitat attributes.
        """
        raise NotImplementedError

    def sample_prey_encounter(self, x: float, y: float, t: float) -> dict[str, Any]:
        """Sample an inhomogeneous Poisson wild-prey encounter event at (x, y, t).

        Args:
            x: Easting coordinate in meters (EPSG:2154).
            y: Northing coordinate in meters (EPSG:2154).
            t: Simulation time in seconds.

        Returns:
            Dictionary describing whether a wild prey group was detected and its attributes.
        """
        raise NotImplementedError

    def get_territorial_context(
        self, x: float, y: float, territory_id: int
    ) -> dict[str, Any]:
        """Return natural nest coordinates and neighboring K95% overlap weights.

        Args:
            x: Easting coordinate in meters (EPSG:2154).
            y: Northing coordinate in meters (EPSG:2154).
            territory_id: Territory identifier of the querying agent.

        Returns:
            Dictionary with keys ``nest_sites`` and ``neighbor_k95_mask``.
        """
        raise NotImplementedError
