"""Synthetic GIS-free environment stub for rapid MVP testing (ADR-03)."""

from __future__ import annotations

from typing import Any

import numpy as np

from bonelli_ibm.core.config import EnvironmentConfig


class MockEnvironment:
    """Lightweight synthetic environment implementing ``EnvironmentInterface``.

    Allows unit testing and v1 MVP execution of ``RaptorAgent`` without
    requiring real GIS raster files (``rasterio`` / ``xarray``).
    """

    def __init__(
        self,
        env_config: EnvironmentConfig,
        rng: np.random.Generator,
    ) -> None:
        """Initialize the synthetic environment from validated configuration.

        Args:
            env_config: Validated environment configuration.
            rng: Centralized reproducible NumPy Generator.
        """
        raise NotImplementedError

    def initialize(self) -> None:
        """Prepare synthetic spatial fields and default nest/territory topology."""
        raise NotImplementedError

    def step_daily(self, julian_day: int) -> None:
        """Update synthetic solar ephemeris and seasonal KBI for ``julian_day``.

        Args:
            julian_day: Day of year in ``[1, 365]``.
        """
        raise NotImplementedError

    def step_hourly(self, julian_day: int, hour: int) -> None:
        """Update synthetic synoptic weather and global ``w*`` for ``hour``.

        Args:
            julian_day: Day of year in ``[1, 365]``.
            hour: Solar hour in ``[0, 23]``.
        """
        raise NotImplementedError

    def get_weather(self, x: float, y: float, t: float) -> dict[str, float]:
        """Return synthetic local meteorological forcing and ephemeris at (x, y, t).

        Args:
            x: Easting coordinate in meters (EPSG:2154).
            y: Northing coordinate in meters (EPSG:2154).
            t: Simulation time in seconds.

        Returns:
            Dictionary of meteorological and solar ephemeris variables.
        """
        raise NotImplementedError

    def get_aerology(self, x: float, y: float, z: float, t: float) -> float:
        """Return synthetic total vertical uplift ``w_uplift`` (m/s) at (x, y, z, t).

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
        """Return synthetic topographic, habitat, and trophic attributes at (x, y).

        Args:
            x: Easting coordinate in meters (EPSG:2154).
            y: Northing coordinate in meters (EPSG:2154).

        Returns:
            Dictionary of local cell habitat attributes.
        """
        raise NotImplementedError

    def sample_prey_encounter(self, x: float, y: float, t: float) -> dict[str, Any]:
        """Draw a synthetic wild-prey encounter event at (x, y, t).

        Args:
            x: Easting coordinate in meters (EPSG:2154).
            y: Northing coordinate in meters (EPSG:2154).
            t: Simulation time in seconds.

        Returns:
            Dictionary describing whether a prey group was detected and its attributes.
        """
        raise NotImplementedError

    def get_territorial_context(
        self, x: float, y: float, territory_id: int
    ) -> dict[str, Any]:
        """Return synthetic natural nest sites and neighboring K95% mask.

        Args:
            x: Easting coordinate in meters (EPSG:2154).
            y: Northing coordinate in meters (EPSG:2154).
            territory_id: Territory identifier of the querying agent.

        Returns:
            Dictionary with keys ``nest_sites`` and ``neighbor_k95_mask``.
        """
        raise NotImplementedError
