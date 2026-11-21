"""Vegetation phenology, habitat openness, and wild-prey Poisson encounter submodels."""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np

from bonelli_ibm.core.config import EnvironmentConfig
from bonelli_ibm.core.types import OpennessClass, PreyEncounter


def compute_gdd(daily_mean_temps_c: Sequence[float], base_temp_c: float) -> float:
    """Accumulate Growing Degree-Days (GDD) from daily mean temperatures.

    Implements ``GDD(J) = sum_{k=1..J} max(0, T_mean(k) - T_base)``.

    Args:
        daily_mean_temps_c: Sequence of daily mean air temperatures (°C) from day 1 to J.
        base_temp_c: Base growth threshold temperature ``T_base`` (°C).

    Returns:
        Accumulated GDD in degree-days.
    """
    raise NotImplementedError


def classify_openness(
    shrub_cover_20m_pct: float, closure_threshold_pct: float = 70.0
) -> OpennessClass:
    """Classify local 20 m habitat openness into ``OPEN`` (< 70%) or ``CLOSED`` (>= 70%).

    Args:
        shrub_cover_20m_pct: Mean shrub/canopy cover within 20 m radius in ``[0, 100]``.
        closure_threshold_pct: Threshold defining closed canopy (default ``70.0``%).

    Returns:
        ``OpennessClass.OPEN`` or ``OpennessClass.CLOSED``.
    """
    raise NotImplementedError


def compute_prey_detectability(
    base_detectability: float,
    shrub_cover_20m_pct: float,
    phenology_factor: float = 1.0,
    closure_threshold_pct: float = 70.0,
) -> float:
    """Compute effective prey detectability ``D_CLC`` in ``[0, 1]``.

    Returns ``0.0`` when ``shrub_cover_20m_pct >= closure_threshold_pct``;
    otherwise returns ``base_detectability * phenology_factor``.

    Args:
        base_detectability: Static facies detectability ``D_base`` in ``[0, 1]``.
        shrub_cover_20m_pct: Local 20 m canopy cover in percent ``[0, 100]``.
        phenology_factor: Seasonal herbaceous height modulation ``phi_pheno(J)`` (1.0 in v1).
        closure_threshold_pct: Canopy closure cutoff in percent (default ``70.0``%).

    Returns:
        Effective detectability index ``D_CLC`` in ``[0.0, 1.0]``.
    """
    raise NotImplementedError


def compute_prey_encounter_rates(
    d_clc: float,
    kbi_g_km: float,
    julian_day: int,
    solar_hour: int,
    facies_id: int,
    env_config: EnvironmentConfig,
    c_det: float = 1.0,
) -> dict[str, float]:
    """Compute instantaneous wild-prey encounter rates ``lambda_s`` (encounters/s) per guild.

    Strictly models wild populations only (rabbit, wild red-legged partridge,
    ocellated lizard with winter hibernation, and secondary avifauna).

    Args:
        d_clc: Local prey detectability index ``D_CLC`` in ``[0, 1]``.
        kbi_g_km: Seasonal Kilometric Biomass Index in g/km.
        julian_day: Day of year in ``[1, 365]``.
        solar_hour: Solar hour in ``[0, 23]``.
        facies_id: Ecological facies identifier in ``[1, 6]``.
        env_config: Validated environment configuration.
        c_det: Scale conversion factor between KBI and detection rate.

    Returns:
        Mapping from prey guild name to instantaneous rate ``lambda_s >= 0`` (1/s).
    """
    raise NotImplementedError


def draw_prey_encounter(
    guild_rates_per_s: dict[str, float],
    dt_s: float,
    env_config: EnvironmentConfig,
    rng: np.random.Generator,
) -> PreyEncounter:
    """Sample a wild-prey encounter over ``dt_s`` via an inhomogeneous Poisson process.

    Computes ``P_encounter = 1 - exp(-sum(lambda_s) * dt_s)``, performs a
    Bernoulli detection draw, then a multinomial guild draw when detected.

    Args:
        guild_rates_per_s: Instantaneous encounter rates ``lambda_s`` (1/s) per guild.
        dt_s: Behavioral step duration in seconds (default 300 s).
        env_config: Validated environment configuration.
        rng: Centralized reproducible NumPy Generator.

    Returns:
        ``PreyEncounter`` describing the draw outcome.
    """
    raise NotImplementedError
