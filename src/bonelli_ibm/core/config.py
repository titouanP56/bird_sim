"""Pydantic v2 configuration schemas and YAML loaders for species, environment, and runs."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

from bonelli_ibm.core.types import OpennessClass, PreyPosition


class _StrictModel(BaseModel):
    """Base Pydantic model rejecting unknown keys to fail fast on YAML typos."""

    model_config = ConfigDict(extra="forbid")


# ------------------------------------------------------------------------------
# Feature flags (v1 -> v2)
# ------------------------------------------------------------------------------


class SpeciesFeatureFlags(_StrictModel):
    """Feature flags controlling v1/v2 behavioral refinements on the species side."""

    use_glmm_attack: bool = False


class EnvironmentFeatureFlags(_StrictModel):
    """Feature flags controlling v1/v2 physical refinements on the environment side."""

    use_3d_thermals: bool = False
    use_dynamic_phenology: bool = False


class FeatureFlags(_StrictModel):
    """Unified v1/v2 feature flags at the simulation level."""

    use_glmm_attack: bool = False
    use_3d_thermals: bool = False
    use_dynamic_phenology: bool = False


# ------------------------------------------------------------------------------
# Species configuration (bonelli.yaml)
# ------------------------------------------------------------------------------


class MorphologyConfig(_StrictModel):
    """Morphological parameters and reversed sexual dimorphism."""

    body_mass_range_g: tuple[float, float]
    body_mass_male_mean_g: float = Field(gt=0.0)
    body_mass_female_mean_g: float = Field(gt=0.0)
    wing_span_m: float = Field(gt=0.0)
    wing_area_m2: float = Field(gt=0.0)

    @model_validator(mode="after")
    def _validate_mass_range(self) -> MorphologyConfig:
        low, high = self.body_mass_range_g
        if low <= 0.0 or low >= high:
            raise ValueError("body_mass_range_g must satisfy 0 < min < max.")
        return self


class KinematicsConfig(_StrictModel):
    """Flight speed thresholds, sink rate, and wind response parameters."""

    flight_speed_threshold_ms: float = Field(gt=0.0)
    cruise_speed_soaring_ms: float = Field(gt=0.0)
    cruise_speed_flapping_ms: float = Field(gt=0.0)
    stoop_attack_speed_ms: float = Field(gt=0.0)
    min_sink_rate_ms: float = Field(gt=0.0)
    optimal_wind_speed_ms: float = Field(ge=0.0)
    wind_speed_optimal_band_ms: tuple[float, float]

    @model_validator(mode="after")
    def _validate_wind_band(self) -> KinematicsConfig:
        low, high = self.wind_speed_optimal_band_ms
        if low < 0.0 or low >= high:
            raise ValueError("wind_speed_optimal_band_ms must satisfy 0 <= min < max.")
        return self


class EnergeticsConfig(_StrictModel):
    """Metabolic rates, locomotion multipliers, digestion, and prey masses."""

    bmr_male_kj_day: float = Field(gt=0.0)
    bmr_female_kj_day: float = Field(gt=0.0)
    cost_perched_mult_bmr: float = Field(gt=0.0)
    cost_soaring_mult_bmr: float = Field(gt=0.0)
    cost_flapping_mult_bmr: float = Field(gt=0.0)
    odba_to_kj_coeff: float = Field(gt=0.0)
    max_crop_capacity_g: float = Field(gt=0.0)
    digestive_rate_g_s: float = Field(gt=0.0)
    assimilation_efficiency: float = Field(gt=0.0, le=1.0)
    energy_density_prey_kj_g: float = Field(gt=0.0)
    prey_standard_masses_g: dict[str, float]

    @model_validator(mode="after")
    def _validate_prey_masses(self) -> EnergeticsConfig:
        for name, mass in self.prey_standard_masses_g.items():
            if mass <= 0.0:
                raise ValueError(f"Prey mass for '{name}' must be > 0, got {mass}.")
        return self


class ForagingConfig(_StrictModel):
    """Visual detection, habitat openness thresholds, and attack GLMM coefficients."""

    prey_detection_radius_m: float = Field(gt=0.0)
    vegetation_assessment_radius_m: float = Field(gt=0.0)
    open_habitat_cover_max_pct: float = Field(ge=0.0, le=100.0)
    favorable_hunting_spot_thresh: float = Field(ge=0.0, le=1.0)
    give_up_time_s: float = Field(gt=0.0)
    baseline_attack_success_prob: float = Field(ge=0.0, le=1.0)
    glmm_attack_intercept: float
    glmm_attack_beta_group_size: float
    glmm_attack_beta_open_hab: float
    glmm_attack_beta_prey_air: float
    glmm_attack_beta_surprise: float


class SpatialConfig(_StrictModel):
    """Home range kernels, territorial overlap, and nest visit parameters."""

    home_range_k95_mean_km2: float = Field(gt=0.0)
    home_range_k75_mean_km2: float = Field(gt=0.0)
    home_range_k50_mean_km2: float = Field(gt=0.0)
    max_neighbor_overlap_pct: float = Field(ge=0.0, le=100.0)
    nests_per_territory: tuple[int, int]
    nest_buffer_radius_m: float = Field(gt=0.0)
    nest_excursion_min_time_s: float = Field(gt=0.0)

    @model_validator(mode="after")
    def _validate_nests_range(self) -> SpatialConfig:
        low, high = self.nests_per_territory
        if low < 1 or low > high:
            raise ValueError("nests_per_territory must satisfy 1 <= min <= max.")
        return self


class SpeciesConfig(_StrictModel):
    """Top-level validated configuration for a raptor species (e.g. bonelli.yaml)."""

    species_name: str = Field(min_length=1)
    features: SpeciesFeatureFlags = Field(default_factory=SpeciesFeatureFlags)
    morphology: MorphologyConfig
    kinematics: KinematicsConfig
    energetics: EnergeticsConfig
    foraging: ForagingConfig
    spatial: SpatialConfig


# ------------------------------------------------------------------------------
# Environment configuration (alpilles.yaml)
# ------------------------------------------------------------------------------


class SpatialExtentConfig(_StrictModel):
    """Geographic bounding box and protected area metrics in EPSG:2154."""

    bbox: tuple[float, float, float, float]
    length_ew_km: float = Field(gt=0.0)
    width_ns_km: float = Field(gt=0.0)
    karst_unit_ha: float = Field(gt=0.0)
    natura2000_ha: float = Field(gt=0.0)

    @model_validator(mode="after")
    def _validate_bbox(self) -> SpatialExtentConfig:
        xmin, ymin, xmax, ymax = self.bbox
        if xmin >= xmax or ymin >= ymax:
            raise ValueError("bbox must satisfy xmin < xmax and ymin < ymax.")
        return self


class SpatialReferenceConfig(_StrictModel):
    """Coordinate reference system and multi-resolution grid settings."""

    crs: str = Field(min_length=1)
    master_grid_resolution_m: float = Field(gt=0.0)
    dem_native_resolution_m: float = Field(gt=0.0)
    extent: SpatialExtentConfig


class ElevationConfig(_StrictModel):
    """Key elevation landmarks of the massif in m NGF."""

    piedmont_min: float
    combes_range: tuple[float, float]
    summit_max: float = Field(gt=0.0)

    @model_validator(mode="after")
    def _validate_elevations(self) -> ElevationConfig:
        low, high = self.combes_range
        if low >= high:
            raise ValueError("combes_range must satisfy min < max.")
        if self.piedmont_min >= self.summit_max:
            raise ValueError("piedmont_min must be strictly less than summit_max.")
        return self


class StructuralCompartmentConfig(_StrictModel):
    """Geomorphological compartment parameters."""

    dominant_aspect: str = Field(min_length=1)
    slope_deg: float = Field(ge=0.0, le=90.0)
    substrate: str = Field(min_length=1)
    albedo: float = Field(ge=0.0, le=1.0)


class TopographyConfig(_StrictModel):
    """Topographic reference values and geomorphological compartments."""

    elevation_m_ngf: ElevationConfig
    structural_compartments: dict[str, StructuralCompartmentConfig]


class HabitatFaciesConfig(_StrictModel):
    """Biophysical properties of one OSO Theia / Natura 2000 ecological facies."""

    oso_code: int = Field(ge=0)
    albedo: float = Field(ge=0.0, le=1.0)
    roughness_z0_m: float = Field(gt=0.0)
    displacement_d0_m: float = Field(ge=0.0)
    hydric_state_mu: float = Field(ge=0.0, le=1.0)
    bowen_ratio_beta: float = Field(gt=0.0)
    shrub_canopy_cover_pct: float = Field(ge=0.0, le=100.0)
    openness_class: OpennessClass
    prey_detectability_d_clc: float = Field(ge=0.0, le=1.0)
    perch_availability_ha: float = Field(ge=0.0)


class VegetationDynamicsConfig(_StrictModel):
    """Long-term woody closure, natural wildfire, and GDD phenology settings."""

    progressive_closure_rate_pct_yr: float = Field(ge=0.0, le=100.0)
    closure_threshold_pct: float = Field(ge=0.0, le=100.0)
    natural_fire_return_period_yr: float = Field(gt=0.0)
    post_fire_canopy_cover_pct: float = Field(ge=0.0, le=100.0)
    post_fire_albedo: float = Field(ge=0.0, le=1.0)
    gdd_base_temp_c: float


class HabitatsConfig(_StrictModel):
    """Ecological facies catalog and vegetation succession parameters."""

    facies: dict[str, HabitatFaciesConfig]
    vegetation_dynamics: VegetationDynamicsConfig


class SeasonalFrequencyConfig(_StrictModel):
    """Seasonal percentage breakdown of Mistral occurrence."""

    winter: float = Field(ge=0.0, le=100.0)
    spring: float = Field(ge=0.0, le=100.0)
    summer: float = Field(ge=0.0, le=100.0)
    autumn: float = Field(ge=0.0, le=100.0)


class MistralRegimeConfig(_StrictModel):
    """Mistral synoptic wind regime and thermal cutoff thresholds."""

    direction_sector_deg: tuple[float, float]
    established_speed_threshold_ms: float = Field(gt=0.0)
    thermal_cutoff_speed_ms: float = Field(gt=0.0)
    min_duration_h: float = Field(gt=0.0)
    annual_frequency_days: float = Field(ge=0.0, le=366.0)
    seasonal_frequency_pct: SeasonalFrequencyConfig
    established_mean_speed_ms: float = Field(gt=0.0)
    gust_max_speed_ms: float = Field(gt=0.0)
    pbl_height_zi_mistral_m: float = Field(gt=0.0)
    pbl_height_zi_convective_m: float = Field(gt=0.0)


class ClimatologyConfig(_StrictModel):
    """Reference weather station monthly normals and Mistral regime."""

    reference_station: str = Field(min_length=1)
    monthly_normals: dict[
        Literal[
            "jan",
            "feb",
            "mar",
            "apr",
            "may",
            "jun",
            "jul",
            "aug",
            "sep",
            "oct",
            "nov",
            "dec",
        ],
        tuple[float, float, float, float, float, float, float],
    ]
    mistral_regime: MistralRegimeConfig


class CircadianActivityConfig(_StrictModel):
    """Circadian activity profile with 24 hourly weights in [0, 1] per season."""

    summer: str = Field(min_length=1)
    winter: str = Field(min_length=1)
    hourly_weights_summer: list[float] = Field(min_length=24, max_length=24)
    hourly_weights_winter: list[float] = Field(min_length=24, max_length=24)

    @model_validator(mode="after")
    def _validate_weights(self) -> CircadianActivityConfig:
        for season_name, weights in (
            ("summer", self.hourly_weights_summer),
            ("winter", self.hourly_weights_winter),
        ):
            if any(w < 0.0 or w > 1.0 for w in weights):
                raise ValueError(
                    f"Circadian hourly weights for '{season_name}' must be in [0, 1]."
                )
        return self


class KBISeasonalRangeConfig(_StrictModel):
    """Seasonal Kilometric Biomass Index (KBI) ranges in g/km (wild prey only)."""

    breeding_mar: tuple[float, float]
    post_fledging_jun: tuple[float, float]
    non_breeding_nov: tuple[float, float]
    home_range_baseline: tuple[float, float]

    @model_validator(mode="after")
    def _validate_ranges(self) -> KBISeasonalRangeConfig:
        fields = (
            "breeding_mar",
            "post_fledging_jun",
            "non_breeding_nov",
            "home_range_baseline",
        )
        for name in fields:
            low, high = getattr(self, name)
            if low < 0.0 or low > high:
                raise ValueError(f"{name} must satisfy 0 <= min <= max.")
        return self


class PreyGuildConfig(_StrictModel):
    """Wild prey guild parameters (strictly excluding restocking / game releases)."""

    mean_body_mass_g: float = Field(gt=0.0)
    group_size_G: int = Field(ge=1, le=50)
    initial_position: PreyPosition
    preferred_habitats: list[int] = Field(min_length=1)
    spatial_density_ind_ha: float = Field(ge=0.0)
    epizootic_mortality_pct: float | None = Field(default=None, ge=0.0, le=100.0)
    hibernation_start_julian_day: int | None = Field(default=None, ge=1, le=365)
    hibernation_end_julian_day: int | None = Field(default=None, ge=1, le=365)
    circadian_activity: CircadianActivityConfig


class PreyGuildsConfig(_StrictModel):
    """Wild trophic resource guilds and seasonal KBI ranges."""

    kbi_seasonal_range_g_km: KBISeasonalRangeConfig
    oryctolagus_cuniculus: PreyGuildConfig
    alectoris_rufa: PreyGuildConfig
    timon_lepidus: PreyGuildConfig
    secondary_avifauna: PreyGuildConfig


class EnvironmentConfig(_StrictModel):
    """Top-level validated configuration for a biophysical territory (e.g. alpilles.yaml)."""

    environment_name: str = Field(min_length=1)
    features: EnvironmentFeatureFlags = Field(default_factory=EnvironmentFeatureFlags)
    spatial_reference: SpatialReferenceConfig
    topography: TopographyConfig
    habitats: HabitatsConfig
    climatology: ClimatologyConfig
    prey_guilds: PreyGuildsConfig


# ------------------------------------------------------------------------------
# Simulation run configuration
# ------------------------------------------------------------------------------


class SimulationConfig(_StrictModel):
    """Global simulation scheduling, reproducibility, and v1/v2 feature-flag settings."""

    seed: int = Field(default=42, ge=0)
    start_julian_day: int = Field(default=1, ge=1, le=365)
    duration_days: int = Field(default=365, gt=0)
    dt_behavioral_s: float = Field(default=300.0, gt=0.0)
    dt_night_s: float = Field(default=3600.0, gt=0.0)
    dt_hourly_s: float = Field(default=3600.0, gt=0.0)
    dt_daily_s: float = Field(default=86400.0, gt=0.0)
    warmup_years: int = Field(default=1, ge=0)
    features: FeatureFlags = Field(default_factory=FeatureFlags)


# ------------------------------------------------------------------------------
# YAML loader helpers
# ------------------------------------------------------------------------------


def _load_yaml_file(path: str | Path) -> dict:
    """Read and parse a YAML mapping from disk."""
    file_path = Path(path)
    with file_path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"Expected a YAML mapping in '{file_path}', got {type(data).__name__}.")
    return data


def load_species_config(path: str | Path) -> SpeciesConfig:
    """Load and validate a species YAML configuration file.

    Args:
        path: Path to the species YAML file (e.g. ``configs/species/bonelli.yaml``).

    Returns:
        Validated ``SpeciesConfig`` instance.
    """
    return SpeciesConfig.model_validate(_load_yaml_file(path))


def load_environment_config(path: str | Path) -> EnvironmentConfig:
    """Load and validate an environment YAML configuration file.

    Args:
        path: Path to the environment YAML file (e.g. ``configs/environments/alpilles.yaml``).

    Returns:
        Validated ``EnvironmentConfig`` instance.
    """
    return EnvironmentConfig.model_validate(_load_yaml_file(path))
