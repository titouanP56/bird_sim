"""Generic territorial raptor agent decoupled via EnvironmentInterface."""

from __future__ import annotations

from typing import Any

import numpy as np

from bonelli_ibm.core.config import SpeciesConfig
from bonelli_ibm.core.interfaces import EnvironmentInterface
from bonelli_ibm.core.types import (
    AgentState,
    AgentTelemetry,
    FlightMode,
    PhenologyPhase,
    Sex,
)


class RaptorAgent:
    """Individual-based model agent representing a territorial raptor.

    Implements the 4-stage behavioral loop specified in
    ``ODD_Agent_Cycle_Comportemental.md``:
      1. ``perceive_environment(env, t)``
      2. ``update_behavioral_state()``
      3. ``execute_movement_and_action(env, t, dt)``
      4. ``update_energetics_and_memory(dt)``

    Depends exclusively on ``EnvironmentInterface`` (never on concrete
    environment implementations) and a validated ``SpeciesConfig``.
    """

    def __init__(
        self,
        agent_id: int,
        territory_id: int,
        sex: Sex,
        age: int,
        experience: int,
        breeding_status: bool,
        nest_pos: tuple[float, float, float],
        species_config: SpeciesConfig,
        rng: np.random.Generator,
        initial_pos: tuple[float, float, float] | None = None,
        initial_energy_kj: float = 0.0,
    ) -> None:
        """Initialize a RaptorAgent with life-history attributes and species parameters.

        Args:
            agent_id: Unique individual identifier.
            territory_id: Identifier of the occupied breeding territory.
            sex: Individual sex (``MALE`` or ``FEMALE``).
            age: Absolute age in years.
            experience: Years of presence on the breeding site (0 => new recruit).
            breeding_status: True if the pair attempts breeding in the current year.
            nest_pos: Active natural nest coordinates ``(x, y, z)`` in meters (EPSG:2154).
            species_config: Validated species parameter configuration.
            rng: Centralized reproducible NumPy Generator.
            initial_pos: Optional starting 3D coordinates ``(x, y, z)``; defaults to ``nest_pos``.
            initial_energy_kj: Initial internal assimilated energy reserve in kJ.
        """
        raise NotImplementedError

    def perceive_environment(self, env: EnvironmentInterface, t: float) -> dict[str, Any]:
        """Query local weather, aerology, habitat, territorial context, and prey.

        Args:
            env: Environment implementing ``EnvironmentInterface``.
            t: Current simulation timestamp in seconds.

        Returns:
            Aggregated perception dictionary consumed by FSM and movement submodels.
        """
        raise NotImplementedError

    def update_behavioral_state(
        self,
        perceptions: dict[str, Any],
        julian_day: int,
        solar_hour: float,
    ) -> tuple[AgentState, FlightMode]:
        """Evaluate the daily FSM and update behavioral state and flight mode.

        Args:
            perceptions: Output of ``perceive_environment``.
            julian_day: Day of year in ``[1, 365]``.
            solar_hour: Current solar hour in decimal hours ``[0, 24)``.

        Returns:
            Tuple ``(new_behavioral_state, new_flight_mode)``.
        """
        raise NotImplementedError

    def execute_movement_and_action(
        self,
        env: EnvironmentInterface,
        perceptions: dict[str, Any],
        t: float,
        dt: float,
    ) -> None:
        """Execute step-selection movement, hunting attack, feeding, or nest attendance.

        Args:
            env: Environment implementing ``EnvironmentInterface``.
            perceptions: Output of ``perceive_environment``.
            t: Current simulation timestamp in seconds.
            dt: Step duration in seconds.
        """
        raise NotImplementedError

    def update_energetics_and_memory(
        self,
        perceptions: dict[str, Any],
        dt: float,
    ) -> None:
        """Update energy expenditure, digestive assimilation, ODBA, and spatial memory.

        Args:
            perceptions: Output of ``perceive_environment``.
            dt: Step duration in seconds.
        """
        raise NotImplementedError

    def step(
        self,
        env: EnvironmentInterface,
        t: float,
        dt: float,
        julian_day: int,
        solar_hour: float,
    ) -> AgentTelemetry:
        """Execute one complete behavioral time step ``t -> t + dt``.

        Args:
            env: Environment implementing ``EnvironmentInterface``.
            t: Current simulation timestamp in seconds.
            dt: Step duration in seconds (300 s diurnal, 3600 s nocturnal).
            julian_day: Day of year in ``[1, 365]``.
            solar_hour: Current solar hour in decimal hours ``[0, 24)``.

        Returns:
            Instantaneous ``AgentTelemetry`` snapshot after updating state.
        """
        raise NotImplementedError

    def update_phenology(self, julian_day: int) -> PhenologyPhase:
        """Update the pair's annual breeding phenology phase for ``julian_day``.

        Args:
            julian_day: Day of year in ``[1, 365]``.

        Returns:
            Updated ``PhenologyPhase``.
        """
        raise NotImplementedError

    def reset_daily_metrics(self) -> None:
        """Reset daily telemetry accumulators at the start of a new day."""
        raise NotImplementedError

    def get_telemetry(self, t: float, julian_day: int) -> AgentTelemetry:
        """Build an immutable ``AgentTelemetry`` snapshot of the current state.

        Args:
            t: Current simulation timestamp in seconds.
            julian_day: Day of year in ``[1, 365]``.

        Returns:
            Frozen ``AgentTelemetry`` dataclass.
        """
        raise NotImplementedError
