"""Foraging and hunting attack success submodels (v1 baseline & v2 GLMM)."""

from __future__ import annotations

import numpy as np

from bonelli_ibm.core.config import SpeciesConfig
from bonelli_ibm.core.types import OpennessClass, PreyEncounter, PreyPosition


def compute_attack_success_probability(
    group_size: int,
    openness_class: OpennessClass,
    prey_position: PreyPosition,
    is_surprise: bool,
    species_config: SpeciesConfig,
) -> float:
    """Compute hunting attack capture probability ``P_succ`` in ``[0, 1]``.

    In **v1** (``species_config.features.use_glmm_attack == False``), returns
    the empirical baseline probability ``baseline_attack_success_prob`` (0.282).

    In **v2** (``use_glmm_attack == True``), evaluates the logistic GLMM from
    Martínez et al. (2014):
        ``logit(P_succ) = beta_0 + beta_group * G + beta_hab * I_open
                          + beta_loc * I_air + beta_mode * I_surprise``

    Args:
        group_size: Prey group size ``G`` in ``[1, 50]``.
        openness_class: Local 20 m habitat openness (``OPEN`` vs ``CLOSED``).
        prey_position: Initial prey position (``SOIL`` vs ``AIR``).
        is_surprise: True if launched by surprise using relief masking or a perch.
        species_config: Validated species configuration.

    Returns:
        Capture probability ``P_succ`` in ``[0.0, 1.0]``.
    """
    raise NotImplementedError


def resolve_hunting_attack(
    encounter: PreyEncounter,
    openness_class: OpennessClass,
    is_surprise: bool,
    species_config: SpeciesConfig,
    rng: np.random.Generator,
) -> tuple[bool, float]:
    """Perform a Bernoulli draw for a hunting attack and return captured biomass.

    Args:
        encounter: Detected ``PreyEncounter`` event.
        openness_class: Local 20 m habitat openness around the prey.
        is_surprise: True if the attack is conducted by surprise.
        species_config: Validated species configuration.
        rng: Centralized reproducible NumPy Generator.

    Returns:
        Tuple ``(succeeded, captured_mass_g)`` where ``captured_mass_g`` is ``0.0``
        upon failure.
    """
    raise NotImplementedError
