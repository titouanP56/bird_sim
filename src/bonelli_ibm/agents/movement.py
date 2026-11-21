"""Step-Selection Function (SSF) movement and spatial memory submodels."""

from __future__ import annotations

import numpy as np

from bonelli_ibm.core.types import PhenologyPhase, Sex


def compute_cell_utility(
    w_uplift_norm: float,
    apparent_habitat_quality: float,
    memory_value: float,
    experience_years: int,
    dist_to_nest_km: float,
    neighbor_k95_intensity: float,
    sex: Sex,
    breeding_phase: PhenologyPhase,
    w_up: float,
    w_hunt: float,
    w_cpf: float,
    w_terr: float,
    k_mem: float,
) -> float:
    """Evaluate the local Step-Selection Function utility score ``U(c')``.

    Implements the zero-human 4-term mechanistic utility equation from
    ``ODD_Agent_Sous_Modeles_Biophysiques.md``:
        ``U(c') = w_up * w_uplift_norm
                  + w_hunt * [(1 - lambda_Exp) * H_apparent + lambda_Exp * M(c')]
                  - w_cpf * d_km(c', p_nest)
                  - w_terr * I_neighbor(c')``
    with ``lambda_Exp = 1 - exp(-k_mem * Exp)``.

    Important:
        ``dist_to_nest_km`` MUST be expressed in **kilometers** (not meters)
        so that the Central Place Forager penalty remains on the same order of
        magnitude as the other terms of ``U(c')``.

    Args:
        w_uplift_norm: Normalized vertical uplift gradient for candidate cell ``c'``.
        apparent_habitat_quality: Immediate foraging attractiveness ``H_apparent(c')``
            combining ``D_CLC`` and seasonal ``KBI`` stability.
        memory_value: Stored cognitive attractiveness ``M(c')`` from spatial memory.
        experience_years: Years of territory tenure ``Exp >= 0``.
        dist_to_nest_km: Distance from candidate cell ``c'`` to active nest in **kilometers**.
        neighbor_k95_intensity: Membership weight ``I_neighbor(c')`` in ``[0, 1]`` for
            neighboring pairs' ``K95%`` home ranges.
        sex: Individual sex modulating the Central Place Forager constraint.
        breeding_phase: Current phenological phase modulating the CPF weight.
        w_up: Weight of vertical uplift attraction.
        w_hunt: Weight of foraging quality and spatial memory.
        w_cpf: Weight of Central Place Forager distance penalty (per km).
        w_terr: Weight of territorial exclusion penalty.
        k_mem: Learning rate controlling how quickly ``lambda_Exp`` approaches 1.

    Returns:
        Scalar utility score ``U(c')``.
    """
    raise NotImplementedError


def select_next_cell(
    candidate_coords: np.ndarray,
    utilities: np.ndarray,
    rng: np.random.Generator,
) -> int:
    """Sample a candidate cell index using a numerically stable Softmax kernel.

    Args:
        candidate_coords: Array of shape ``(N, 2)`` or ``(N, 3)`` of reachable cells
            within ``d(c, c') <= v_cruise * dt``.
        utilities: 1D array of shape ``(N,)`` containing ``U(c')`` values.
        rng: Centralized reproducible NumPy Generator.

    Returns:
        Selected index in ``[0, N - 1]``.
    """
    raise NotImplementedError


def update_spatial_memory(
    spatial_memory: dict[tuple[int, int], float],
    cell_index: tuple[int, int],
    observed_reward: float,
    learning_rate: float,
) -> float:
    """Update cognitive map attractiveness ``M(i, j)`` after visiting a cell.

    Args:
        spatial_memory: Mutable mapping from grid cell ``(i, j)`` to memory score.
        cell_index: Visited grid cell coordinates ``(i, j)``.
        observed_reward: Combined foraging success and uplift reward signal.
        learning_rate: Exponential moving average update weight in ``(0, 1]``.

    Returns:
        Updated memory value for ``cell_index``.
    """
    raise NotImplementedError
