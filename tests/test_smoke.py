"""Smoke tests verifying config loading, RNG reproducibility, and interface contracts."""

from __future__ import annotations

import inspect
from pathlib import Path

import numpy as np

from bonelli_ibm.core.config import (
    SimulationConfig,
    load_environment_config,
    load_species_config,
)
from bonelli_ibm.core.interfaces import EnvironmentInterface
from bonelli_ibm.core.rng import create_rng
from bonelli_ibm.environment.alpilles_env import AlpillesEnvironment
from bonelli_ibm.environment.mock_env import MockEnvironment

REPO_ROOT = Path(__file__).resolve().parents[1]
BONELLI_YAML = REPO_ROOT / "configs" / "species" / "bonelli.yaml"
ALPILLES_YAML = REPO_ROOT / "configs" / "environments" / "alpilles.yaml"

REQUIRED_ENV_METHODS = (
    "get_weather",
    "get_aerology",
    "get_cell_habitat",
    "sample_prey_encounter",
    "get_territorial_context",
)


def test_load_bonelli_species_config() -> None:
    """bonelli.yaml loads and passes strict Pydantic v2 validation without human variables."""
    cfg = load_species_config(BONELLI_YAML)

    assert cfg.species_name == "Aquila fasciata"
    assert cfg.features.use_glmm_attack is False
    assert cfg.kinematics.flight_speed_threshold_ms == 3.0
    assert cfg.kinematics.optimal_wind_speed_ms == 5.0
    assert cfg.foraging.baseline_attack_success_prob == 0.282
    assert cfg.spatial.nest_buffer_radius_m == 25.0
    # Zero-human rule check
    dumped = cfg.model_dump()
    assert "flight_initiation_distance_m" not in str(dumped)
    assert "human_disturbance" not in str(dumped)


def test_load_alpilles_environment_config() -> None:
    """alpilles.yaml loads and passes strict Pydantic v2 validation with known Alpilles values."""
    cfg = load_environment_config(ALPILLES_YAML)

    assert cfg.spatial_reference.crs == "EPSG:2154"
    assert cfg.features.use_3d_thermals is False
    assert cfg.features.use_dynamic_phenology is False
    assert cfg.spatial_reference.extent.karst_unit_ha == 26240.0
    assert cfg.spatial_reference.extent.natura2000_ha == 17334.0
    assert cfg.topography.elevation_m_ngf.summit_max == 498.0
    assert cfg.climatology.mistral_regime.established_mean_speed_ms == 13.9
    assert cfg.climatology.mistral_regime.thermal_cutoff_speed_ms == 12.87
    assert cfg.prey_guilds.timon_lepidus.mean_body_mass_g == 150.0


def test_simulation_config_defaults() -> None:
    """SimulationConfig initializes with valid positive timesteps and v1 feature flags."""
    sim_cfg = SimulationConfig()

    assert sim_cfg.dt_behavioral_s == 300.0
    assert sim_cfg.dt_hourly_s == 3600.0
    assert sim_cfg.dt_daily_s == 86400.0
    assert sim_cfg.features.use_glmm_attack is False
    assert sim_cfg.features.use_3d_thermals is False
    assert sim_cfg.features.use_dynamic_phenology is False


def test_rng_reproducibility() -> None:
    """Same seed produces identical sequences; different seeds diverge."""
    rng_a = create_rng(12345)
    rng_b = create_rng(12345)
    rng_c = create_rng(99999)

    seq_a = rng_a.random(20)
    seq_b = rng_b.random(20)
    seq_c = rng_c.random(20)

    assert np.array_equal(seq_a, seq_b)
    assert not np.array_equal(seq_a, seq_c)


def test_environment_implementations_satisfy_interface() -> None:
    """AlpillesEnvironment and MockEnvironment expose all EnvironmentInterface methods."""
    for env_cls in (AlpillesEnvironment, MockEnvironment):
        assert issubclass(env_cls, EnvironmentInterface)
        for method_name in REQUIRED_ENV_METHODS:
            proto_fn = getattr(EnvironmentInterface, method_name)
            impl_fn = getattr(env_cls, method_name)
            assert callable(impl_fn)
            proto_params = list(inspect.signature(proto_fn).parameters.keys())
            impl_params = list(inspect.signature(impl_fn).parameters.keys())
            assert impl_params == proto_params, (
                f"{env_cls.__name__}.{method_name} signature mismatch: "
                f"{impl_params} != {proto_params}"
            )
