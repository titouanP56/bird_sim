"""Centralized reproducible random number generator (PCG64)."""

from __future__ import annotations

import numpy as np


def create_rng(seed: int) -> np.random.Generator:
    """Create a reproducible NumPy PCG64 random number generator.

    All stochastic operations in the simulation (step selection, prey encounters,
    attack outcomes) must draw from a generator instantiated via this helper
    rather than Python's global ``random`` module (see ADR-02).

    Args:
        seed: Non-negative integer seed for deterministic initialization.

    Returns:
        A freshly seeded ``numpy.random.Generator`` backed by PCG64.

    Raises:
        ValueError: If ``seed`` is negative.
    """
    if seed < 0:
        raise ValueError(f"RNG seed must be non-negative, got {seed}.")
    return np.random.default_rng(np.random.PCG64(seed))
