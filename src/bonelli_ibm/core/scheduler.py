"""Multi-scale simulation scheduler orchestrating t=0, 24h, 1h, and 5min loops."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import numpy as np

from bonelli_ibm.core.config import SimulationConfig
from bonelli_ibm.core.interfaces import EnvironmentInterface
from bonelli_ibm.core.types import AgentTelemetry


class SimulationScheduler:
    """Multi-scale time orchestrator for Bonelli-IBM simulations.

    Synchronizes the four nested temporal scales defined in
    ``ODD_Env_Dynamique_et_Planification.md``:
      1. Static initialization (``t = 0``) and optional warmup year.
      2. Daily update (``dt = 24 h``): ephemeris, phenology, seasonal KBI, ``theta_0``.
      3. Hourly update (``dt = 1 h``): synoptic weather, Mistral cutoff, ``w*``, circadian weights.
      4. Behavioral step (``dt = 5 min`` diurnal / ``60 min`` nocturnal): agent perception,
         FSM transition, movement/action, energetics, and telemetry recording.

    Note:
        To preserve strict architectural decoupling, this module never imports
        ``bonelli_ibm.agents`` or ``bonelli_ibm.environment``.
    """

    def __init__(
        self,
        sim_config: SimulationConfig,
        environment: EnvironmentInterface,
        agents: Sequence[Any],
        rng: np.random.Generator,
    ) -> None:
        """Initialize the scheduler with validated configuration and injected components.

        Args:
            sim_config: Global simulation timing, seed, and feature-flag settings.
            environment: Environment engine implementing ``EnvironmentInterface``.
            agents: Sequence of autonomous agent instances exposing a ``step(env, t)`` API.
            rng: Centralized reproducible NumPy Generator.
        """
        raise NotImplementedError

    def initialize(self) -> None:
        """Execute static initialization at ``t = 0`` and optional warmup year.

        Loads/prepares static spatial layers in the environment, initializes
        agent positions at their roost/nest sites, and runs the configured
        ``warmup_years`` spin-up to stabilize initial vegetation states.
        """
        raise NotImplementedError

    def step_daily(self, julian_day: int) -> None:
        """Advance daily environmental and phenological dynamics (``dt = 24 h``).

        Updates solar ephemeris, diurnal surface potential temperature ``theta_0``,
        vegetation GDD/NDVI phenology, ectotherm hibernation state, seasonal KBI,
        and resets daily agent telemetry accumulators.

        Args:
            julian_day: Day of year in ``[1, 365]``.
        """
        raise NotImplementedError

    def step_hourly(self, julian_day: int, hour: int) -> None:
        """Advance hourly synoptic weather and boundary-layer states (``dt = 1 h``).

        Ingests weather forcing, evaluates the Mistral shear cutoff (12.87 m/s),
        updates surface heat fluxes, Deardorff velocity ``w*``, Monin-Obukhov
        length ``L``, and prey circadian activity weights.

        Args:
            julian_day: Day of year in ``[1, 365]``.
            hour: Solar hour of day in ``[0, 23]``.
        """
        raise NotImplementedError

    def step_behavioral(self, t: float, dt: float) -> list[AgentTelemetry]:
        """Execute one behavioral and kinematic step across all agents (``dt = 5 min``).

        Args:
            t: Current simulation timestamp in seconds.
            dt: Step duration in seconds (300 s diurnal, 3600 s nocturnal).

        Returns:
            List of instantaneous ``AgentTelemetry`` snapshots produced at time ``t``.
        """
        raise NotImplementedError

    def run(self) -> list[AgentTelemetry]:
        """Run the full simulation across ``sim_config.duration_days``.

        Orchestrates ``initialize()``, then nested ``step_daily()``,
        ``step_hourly()``, and ``step_behavioral()`` loops.

        Returns:
            Complete sequence of recorded ``AgentTelemetry`` snapshots.
        """
        raise NotImplementedError
