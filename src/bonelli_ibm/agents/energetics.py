"""Pure biophysical functions for flight energetics, digestion, and breeding fitness."""

from __future__ import annotations

from bonelli_ibm.core.config import SpeciesConfig
from bonelli_ibm.core.types import Sex


def compute_flapping_fraction(
    w_uplift_ms: float,
    wind_speed_ms: float,
    rainfall_mm: float,
    species_config: SpeciesConfig,
    gamma_rain: float = 0.0,
    gamma_wind: float = 0.0,
) -> float:
    """Compute the fraction of flight spent flapping ``alpha_flap`` in ``[0, 1]``.

    Implements:
        ``alpha_flap = clip(1 - w_uplift / w_sink_min + gamma_rain * Rain
                            + gamma_wind * I(W not in [2.5, 7.5]), 0, 1)``

    Args:
        w_uplift_ms: Total vertical air velocity ``w_uplift`` in m/s.
        wind_speed_ms: Local horizontal wind speed ``W_t`` in m/s.
        rainfall_mm: Local hourly rainfall ``Rain_t`` in mm.
        species_config: Validated species configuration.
        gamma_rain: Sensitivity coefficient for rainfall penalty (1/mm).
        gamma_wind: Penalty applied when wind speed lies outside the optimal band.

    Returns:
        Flapping flight fraction ``alpha_flap`` bounded to ``[0.0, 1.0]``.
    """
    raise NotImplementedError


def compute_energy_expenditure(
    sex: Sex,
    is_flying: bool,
    alpha_flap: float,
    temp_c: float,
    dt_s: float,
    species_config: SpeciesConfig,
) -> float:
    """Compute instantaneous energy expenditure ``Delta E_out`` (kJ) over ``dt_s``.

    Accounts for sex-specific BMR, locomotion mode multipliers (perched,
    soaring/gliding, flapping), and thermoregulation cost ``E_thermo(T_t)``.

    Args:
        sex: Individual sex (``MALE`` or ``FEMALE``).
        is_flying: True if ``||v|| > flight_speed_threshold_ms``.
        alpha_flap: Flapping fraction in ``[0, 1]``.
        temp_c: Ambient air temperature in degrees Celsius.
        dt_s: Time step duration in seconds.
        species_config: Validated species configuration.

    Returns:
        Energy expended during ``dt_s`` in kJ.
    """
    raise NotImplementedError


def compute_digestive_assimilation(
    crop_mass_g: float,
    dt_s: float,
    species_config: SpeciesConfig,
) -> tuple[float, float]:
    """Compute digested food mass and assimilated energy ``Delta E_in`` (kJ).

    Implements:
        ``Delta m_dig = min(C, r_dig * dt)``
        ``C_new = C - Delta m_dig``
        ``Delta E_in = Delta m_dig * epsilon_assim * e_prey``

    Args:
        crop_mass_g: Current crop food mass ``C_t`` in grams.
        dt_s: Time step duration in seconds.
        species_config: Validated species configuration.

    Returns:
        Tuple ``(remaining_crop_mass_g, assimilated_energy_kj)``.
    """
    raise NotImplementedError


def compute_breeding_probabilities(
    is_new_male: bool,
    is_new_female: bool,
    rearing_temp_max_c: float,
) -> tuple[float, float, float]:
    """Compute annual breeding, hatching, and fledging probabilities.

    Captures recruitment penalties (new male, new female, or both) and thermal
    stress on nestlings during rearing (``beta_Tmax = -0.48``).

    Args:
        is_new_male: True if the territorial male is newly recruited (``Exp == 0``).
        is_new_female: True if the territorial female is newly recruited (``Exp == 0``).
        rearing_temp_max_c: Mean/peak maximum air temperature during rearing (°C).

    Returns:
        Tuple ``(p_breed, p_hatch, p_fledge)`` with each probability in ``[0, 1]``.
    """
    raise NotImplementedError
