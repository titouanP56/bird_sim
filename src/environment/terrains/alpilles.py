"""Stratégie de génération de relief : Massif calcaire plissé (type Alpilles).
Génère un double chaînon Est-Ouest avec des plateaux de piémont.
"""
from typing import Any, Mapping, Tuple

import numpy as np

# On importe les outils génériques depuis le chef d'orchestre
from src.environment.generators import _normalize, smooth_noise


def generate_elevation(
    shape: Tuple[int, int], config: Mapping[str, Any], rng: np.random.Generator
) -> np.ndarray:
    """Calcule la matrice d'altitude z brute pour le relief des Alpilles."""
    p = config.get("topography_generation", {})
    rows, cols = shape
    y, x = np.meshgrid(
        np.linspace(0.0, 1.0, rows), np.linspace(0.0, 1.0, cols), indexing="ij"
    )

    phase = rng.uniform(0, 2 * np.pi)
    sin_wave = p.get("ridge_sinuosity", 0.045) * np.sin(2 * np.pi * 1.5 * x + phase)
    y_main = p.get("ridge_center", 0.44) + sin_wave
    dy_main = y - y_main

    half_len = max(p.get("ridge_length", 0.82) / 2.0, 1e-6)
    taper = np.exp(-(((x - 0.5) / half_len) ** 6))

    # 1. Chaînon calcaire principal étroit à sommet tabulaire
    w_main = float(p.get("ridge_width", 0.075))
    ridge_main = np.exp(-0.5 * (dy_main / w_main) ** 2)
    flatness = float(p.get("ridge_flatness", 1.35))
    ridge_main = np.clip(ridge_main * flatness, 0.0, 1.0)

    # 2. Second chaînon calcaire parallèle au Sud (structure plissée)
    sec_offset = float(p.get("secondary_ridge_offset", 0.14))
    w_sec = float(p.get("secondary_ridge_width", 0.055))
    sec_strength = float(p.get("secondary_ridge_strength", 0.65))
    y_sec = y_main + sec_offset + 0.02 * np.cos(2 * np.pi * 2.0 * x + phase)
    ridge_sec = sec_strength * np.exp(-0.5 * ((y - y_sec) / w_sec) ** 2)
    ridge_sec = np.clip(ridge_sec * flatness, 0.0, 1.0)

    ridges = np.maximum(ridge_main, ridge_sec)

    # Fonction de cuesta (rupture de pente franche sur les flancs calcaires)
    sharpness = float(p.get("terrace_sharpness", 6.0))
    if sharpness > 0:
        ridges = 0.60 * ridges + 0.40 * (1.0 / (1.0 + np.exp(-sharpness * (ridges - 0.52))))

    # 3. Vastes plateaux calcaires de piémont et combes intérieures
    y_mid = 0.5 * (y_main + y_sec)
    piedmont = np.exp(-0.5 * ((y - y_mid) / p.get("plateau_width", 0.26)) ** 2)
    piedmont = np.clip(piedmont * 1.65, 0.0, 1.0)

    relief = (ridges + p.get("plateau_strength", 0.52) * piedmont) * taper
    relief += p.get("noise_amplitude", 0.16) * smooth_noise(
        shape, p.get("noise_sigma", 2.6), rng
    )

    return _normalize(relief)
