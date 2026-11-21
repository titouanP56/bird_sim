"""Pure Finite State Machine (FSM) and phenological transition rules."""

from __future__ import annotations

from bonelli_ibm.core.config import SpeciesConfig
from bonelli_ibm.core.types import AgentState, FlightMode, PhenologyPhase, Sex


def compute_phenology_phase(
    julian_day: int,
    breeding_status: bool,
    lay_julian_day: int,
    incubation_days: int = 39,
    rearing_days: int = 63,
    post_fledging_days: int = 90,
) -> PhenologyPhase:
    """Determine the annual breeding phenology phase for a given Julian day.

    Args:
        julian_day: Day of year in ``[1, 365]``.
        breeding_status: True if the pair breeds during the current year.
        lay_julian_day: Egg-laying Julian day ``J_lay``.
        incubation_days: Incubation duration in days (mean 39, range 37-41).
        rearing_days: Nestling rearing duration in days (mean 63, range 55-65).
        post_fledging_days: Post-fledging dependence duration in days (range 77-113).

    Returns:
        Active ``PhenologyPhase``.
    """
    raise NotImplementedError


def next_behavioral_state(
    current_state: AgentState,
    sex: Sex,
    breeding_phase: PhenologyPhase,
    solar_hour: float,
    t_sunrise: float,
    t_sunset: float,
    wind_speed_ms: float,
    rainfall_mm: float,
    dist_to_nest_m: float,
    in_k75: bool,
    prey_detectability: float,
    prey_detected: bool,
    attack_succeeded: bool | None,
    intruder_in_k95: bool,
    crop_mass_g: float,
    time_searching_spot_s: float,
    species_config: SpeciesConfig,
) -> AgentState:
    """Compute the next discrete FSM behavioral state ``Sigma_{t+1}``.

    Evaluates diurnal wake-up/roosting windows, storm shelter rules, female
    nest attendance asymmetry during incubation/rearing, foraging patch
    selection (``D_CLC >= 0.50`` in ``K75%``), prey detection, and territorial
    defense against conspecific intruders in ``K95%``.

    Args:
        current_state: Current ``AgentState`` at time ``t``.
        sex: Individual sex (``MALE`` or ``FEMALE``).
        breeding_phase: Current ``PhenologyPhase``.
        solar_hour: Current solar hour in decimal hours ``[0, 24)``.
        t_sunrise: Sunrise time in decimal hours.
        t_sunset: Sunset time in decimal hours.
        wind_speed_ms: Local horizontal wind speed in m/s.
        rainfall_mm: Local hourly rainfall in mm.
        dist_to_nest_m: Euclidean distance to active nest in meters.
        in_k75: True if the current cell belongs to the pair's ``K75%`` core.
        prey_detectability: Local ``D_CLC`` index in ``[0, 1]``.
        prey_detected: True if a prey group was detected on this step.
        attack_succeeded: Outcome of a hunting attack if ``current_state == HUNTING_ATTACK``.
        intruder_in_k95: True if a non-partner conspecific is detected inside ``K95%``.
        crop_mass_g: Current crop food mass in grams.
        time_searching_spot_s: Elapsed search time on the current patch without detection (s).
        species_config: Validated species parameters.

    Returns:
        Next ``AgentState``.
    """
    raise NotImplementedError


def select_flight_mode(
    state: AgentState,
    w_uplift_ms: float,
    wind_speed_ms: float,
    perch_availability: float,
    species_config: SpeciesConfig,
) -> FlightMode:
    """Select the locomotion mode ``M_flight`` for the updated behavioral state.

    Args:
        state: Target ``AgentState`` for the current step.
        w_uplift_ms: Local vertical uplift velocity ``w_uplift`` in m/s.
        wind_speed_ms: Local horizontal wind speed in m/s.
        perch_availability: Natural perch density in perches/ha.
        species_config: Validated species parameters.

    Returns:
        Selected ``FlightMode`` (``NONE``, ``PERCHED``, ``SOARING_GLIDING``, or ``FLAPPING``).
    """
    raise NotImplementedError
