"""Protocol contracts decoupling generic agent mechanics from environment engines."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class EnvironmentInterface(Protocol):
    """Contract exposed by any biophysical environment to RaptorAgent.

    Strictly follows ``docs/01_Modele/interfaces/Interface_Requise_Environnement.md``
    under the zero-human hypothesis (no anthropogenic disturbance variables).
    """

    def get_weather(self, x: float, y: float, t: float) -> dict[str, float]:
        """Return local meteorological forcing and solar ephemeris at (x, y, t).

        Expected keys include ``t_sunrise``, ``t_sunset``, ``julian_day``,
        ``wind_speed`` (m/s), ``rainfall`` (mm), ``temp_mean`` (°C),
        ``temp_min`` (°C), and ``temp_max`` (°C).

        Args:
            x: Easting coordinate in meters (EPSG:2154).
            y: Northing coordinate in meters (EPSG:2154).
            t: Simulation time in seconds.

        Returns:
            Dictionary of meteorological and ephemeris values.
        """
        ...

    def get_aerology(self, x: float, y: float, z: float, t: float) -> float:
        """Return total vertical air velocity ``w_uplift`` (m/s) at (x, y, z, t).

        Combines orographic uplift ``w_oro`` and thermal convection ``w_th``
        evaluated at height above ground level ``h_AGL = z - z_ground(x, y)``.

        Args:
            x: Easting coordinate in meters (EPSG:2154).
            y: Northing coordinate in meters (EPSG:2154).
            z: Altitude above sea level in meters.
            t: Simulation time in seconds.

        Returns:
            Total vertical uplift velocity ``w_uplift`` in m/s.
        """
        ...

    def get_cell_habitat(self, x: float, y: float) -> dict[str, float]:
        """Return static and seasonal biophysical attributes of the cell at (x, y).

        Expected keys include ``elevation`` (m asl), ``slope`` (deg),
        ``aspect`` (deg), ``prey_detectability`` (D_CLC in [0, 1]),
        ``shrub_cover_20m`` (% in [0, 100]), ``perch_availability`` (perches/ha),
        and ``kbi_biomass`` (g/km, wild populations only).

        Args:
            x: Easting coordinate in meters (EPSG:2154).
            y: Northing coordinate in meters (EPSG:2154).

        Returns:
            Dictionary of local topographic, habitat, and trophic values.
        """
        ...

    def sample_prey_encounter(self, x: float, y: float, t: float) -> dict[str, Any]:
        """Draw a stochastic wild-prey encounter event during FORAGING_SEARCH.

        Expected keys include ``detected`` (bool) and, when detected,
        ``species`` (str), ``mass`` (float, g), ``group_size`` (int in [1, 50]),
        and ``position`` (``"SOIL"`` or ``"AIR"``).

        Args:
            x: Easting coordinate in meters (EPSG:2154).
            y: Northing coordinate in meters (EPSG:2154).
            t: Simulation time in seconds.

        Returns:
            Dictionary describing the prey encounter event.
        """
        ...

    def get_territorial_context(
        self, x: float, y: float, territory_id: int
    ) -> dict[str, Any]:
        """Return natural nest coordinates and neighboring K95% overlap mask.

        Expected keys include ``nest_sites`` (``list[tuple[float, float, float]]``)
        and ``neighbor_k95_mask`` (``dict[int, float]`` with values in [0, 1]).

        Args:
            x: Easting coordinate in meters (EPSG:2154).
            y: Northing coordinate in meters (EPSG:2154).
            territory_id: Territory identifier of the querying agent.

        Returns:
            Dictionary containing nest coordinates and neighbor territory weights.
        """
        ...
