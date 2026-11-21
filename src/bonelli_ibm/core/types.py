"""Core domain enums and dataclasses shared across the simulation."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class AgentState(StrEnum):
    """Discrete behavioral states of the daily Finite State Machine (FSM)."""

    ROOSTING = "ROOSTING"
    NEST_ATTENDANCE = "NEST_ATTENDANCE"
    TRANSIT_SOARING = "TRANSIT_SOARING"
    FORAGING_SEARCH = "FORAGING_SEARCH"
    HUNTING_ATTACK = "HUNTING_ATTACK"
    FEEDING = "FEEDING"
    TERRITORIAL_DEFENSE = "TERRITORIAL_DEFENSE"


class FlightMode(StrEnum):
    """Locomotion mode determining instantaneous energetic expenditure."""

    NONE = "NONE"
    PERCHED = "PERCHED"
    SOARING_GLIDING = "SOARING_GLIDING"
    FLAPPING = "FLAPPING"


class PhenologyPhase(StrEnum):
    """Annual breeding phenology phase at the territory/pair level."""

    NON_BREEDING = "NON_BREEDING"
    PRE_BREEDING = "PRE_BREEDING"
    INCUBATION = "INCUBATION"
    REARING = "REARING"
    POST_FLEDGING = "POST_FLEDGING"


class Sex(StrEnum):
    """Individual sex driving reversed sexual dimorphism and parental roles."""

    MALE = "MALE"
    FEMALE = "FEMALE"


class PreyPosition(StrEnum):
    """Initial physical position of a detected prey item."""

    SOIL = "SOIL"
    AIR = "AIR"


class OpennessClass(StrEnum):
    """Binary habitat openness class derived from local 20 m shrub cover."""

    OPEN = "OPEN"
    CLOSED = "CLOSED"


@dataclass(frozen=True, slots=True)
class WeatherState:
    """Local meteorological and solar ephemeris state at (x, y, t).

    Attributes:
        t_sunrise: Solar sunrise time in decimal hours [0, 24].
        t_sunset: Solar sunset time in decimal hours [0, 24].
        julian_day: Day of year in [1, 365].
        wind_speed: Horizontal wind speed in m/s.
        rainfall: Hourly rainfall accumulation in mm.
        temp_mean: Mean air temperature in degrees Celsius.
        temp_min: Daily minimum air temperature in degrees Celsius.
        temp_max: Daily maximum air temperature in degrees Celsius.
        wind_dir_deg: Meteorological wind origin direction in degrees [0, 360).
        solar_radiation_wm2: Net surface solar radiation Q_S in W/m^2.
        relative_humidity_pct: Relative humidity in percent [0, 100].
        pressure_hpa: Surface atmospheric pressure in hPa (mb).
    """

    t_sunrise: float
    t_sunset: float
    julian_day: int
    wind_speed: float
    rainfall: float
    temp_mean: float
    temp_min: float
    temp_max: float
    wind_dir_deg: float = 0.0
    solar_radiation_wm2: float = 0.0
    relative_humidity_pct: float = 50.0
    pressure_hpa: float = 1013.25


@dataclass(frozen=True, slots=True)
class HabitatState:
    """Local topographic, land-cover, and trophic attributes of a 10 m cell.

    Attributes:
        elevation: Ground altitude above sea level in m (EPSG:2154 / NGF).
        slope: Local terrain slope in degrees [0, 90].
        aspect: Local terrain aspect in degrees [0, 360).
        prey_detectability: CORINE / OSO prey detectability index D_CLC in [0, 1].
        shrub_cover_20m: Mean shrub/canopy cover within a 20 m radius in percent [0, 100].
        openness_class: Binary openness class (OPEN <= 69%, CLOSED >= 70%).
        perch_availability: Density of natural perches in perches/ha.
        kbi_biomass: Kilometric Biomass Index (wild prey only) in g/km.
    """

    elevation: float
    slope: float
    aspect: float
    prey_detectability: float
    shrub_cover_20m: float
    openness_class: OpennessClass
    perch_availability: float
    kbi_biomass: float


@dataclass(frozen=True, slots=True)
class PreyEncounter:
    """Outcome of a stochastic prey encounter draw during FORAGING_SEARCH.

    Attributes:
        detected: True if at least one wild prey group was detected during dt.
        species: Taxon or guild identifier when detected, else None.
        mass_g: Unit fresh body mass of the detected prey in grams.
        group_size: Prey group size G in [1, 50] (0 when not detected).
        position: Initial prey position (SOIL or AIR) when detected, else None.
    """

    detected: bool
    species: str | None = None
    mass_g: float = 0.0
    group_size: int = 0
    position: PreyPosition | None = None


@dataclass(frozen=True, slots=True)
class TerritorialContext:
    """Spatial social topology around (x, y) for a given territory.

    Attributes:
        nest_sites: Coordinates (x, y, z) in meters of natural nest sites for the territory.
        neighbor_k95_mask: Mapping from neighboring territory_id to membership weight in [0, 1].
    """

    nest_sites: list[tuple[float, float, float]] = field(default_factory=list)
    neighbor_k95_mask: dict[int, float] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class AgentTelemetry:
    """Instantaneous telemetry snapshot of a RaptorAgent at timestamp t.

    Attributes:
        agent_id: Unique individual identifier.
        territory_id: Occupied territory identifier.
        t: Simulation timestamp in seconds from start of run.
        julian_day: Day of year in [1, 365].
        x: Easting coordinate in meters (EPSG:2154).
        y: Northing coordinate in meters (EPSG:2154).
        z: Altitude above sea level in meters.
        vx: Velocity component along x in m/s.
        vy: Velocity component along y in m/s.
        vz: Velocity component along z in m/s.
        behavioral_state: Current FSM behavioral state.
        flight_mode: Current locomotion mode.
        breeding_phase: Current phenological breeding phase.
        energy_reserve: Assimilated internal energy reserve in kJ.
        crop_mass: Food mass currently stored in the crop in g.
        daily_time_in_flight: Cumulative diurnal flight proportion in [0, 1].
        daily_distance: Cumulative step length since wake-up in meters.
        daily_range: Median distance from wake-up roost in meters.
        daily_straightness: Daily path straightness index in [0, 1].
        daily_odba: Cumulative daily Overall Dynamic Body Acceleration in g.
    """

    agent_id: int
    territory_id: int
    t: float
    julian_day: int
    x: float
    y: float
    z: float
    vx: float
    vy: float
    vz: float
    behavioral_state: AgentState
    flight_mode: FlightMode
    breeding_phase: PhenologyPhase
    energy_reserve: float
    crop_mass: float
    daily_time_in_flight: float
    daily_distance: float
    daily_range: float
    daily_straightness: float
    daily_odba: float
