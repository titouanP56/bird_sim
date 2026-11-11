"""Génération procédurale universelle des couches environnementales.
Utilise le Design Pattern Strategy pour déléguer l'équation de l'altitude z
à des modules spécifiques (ex: terrains/alpilles.py, terrains/calanques.py).
"""
from __future__ import annotations

import importlib
from typing import Any, Dict, Mapping

import numpy as np

from .layers import PreyLayer, TopographyLayer, VegetationLayer


def gaussian_blur(field: np.ndarray, sigma: float) -> np.ndarray:
    if sigma <= 0:
        return field.copy()
    radius = max(1, int(np.ceil(3.0 * sigma)))
    x = np.arange(-radius, radius + 1, dtype=float)
    kernel = np.exp(-0.5 * (x / sigma) ** 2)
    kernel /= kernel.sum()

    out = field.astype(float)
    for axis in (0, 1):
        pad = [(0, 0), (0, 0)]
        pad[axis] = (radius, radius)
        padded = np.pad(out, pad, mode="reflect")
        n = out.shape[axis]
        acc = np.zeros_like(out)
        for i, k in enumerate(kernel):
            sl = [slice(None), slice(None)]
            sl[axis] = slice(i, i + n)
            acc += k * padded[tuple(sl)]
        out = acc
    return out


def smooth_noise(shape, sigma: float, rng: np.random.Generator) -> np.ndarray:
    noise = gaussian_blur(rng.standard_normal(shape), sigma)
    std = noise.std()
    return (noise - noise.mean()) / (std if std > 0 else 1.0)


def _normalize(field: np.ndarray) -> np.ndarray:
    lo, hi = field.min(), field.max()
    return (field - lo) / (hi - lo) if hi > lo else np.zeros_like(field)


def _int_keys(mapping: Mapping[Any, Any]) -> Dict[int, Any]:
    return {int(k): v for k, v in mapping.items()}


def _thin_cliffs_nms(slope: np.ndarray, gy: np.ndarray, gx: np.ndarray) -> np.ndarray:
    """Suppression des Non-Maxima (NMS) le long de la direction du gradient."""
    angle = np.mod(np.rad2deg(np.arctan2(gy, gx)), 180.0)

    s_pad = np.pad(slope, 1, mode="edge")
    center = s_pad[1:-1, 1:-1]

    d0 = (angle < 22.5) | (angle >= 157.5)
    d45 = (angle >= 22.5) & (angle < 67.5)
    d90 = (angle >= 67.5) & (angle < 112.5)
    d135 = (angle >= 112.5) & (angle < 157.5)

    n1, n2 = np.zeros_like(slope), np.zeros_like(slope)
    n1[d0], n2[d0] = s_pad[1:-1, :-2][d0], s_pad[1:-1, 2:][d0]
    n1[d45], n2[d45] = s_pad[:-2, :-2][d45], s_pad[2:, 2:][d45]
    n1[d90], n2[d90] = s_pad[:-2, 1:-1][d90], s_pad[2:, 1:-1][d90]
    n1[d135], n2[d135] = s_pad[:-2, 2:][d135], s_pad[2:, :-2][d135]

    return (center >= n1) & (center > n2)


class EnvironmentGenerator:
    """Génère toutes les couches à partir d'un dictionnaire de configuration."""

    def __init__(self, config: Mapping[str, Any]) -> None:
        self.config = config
        rows, cols = config["grid_size"]
        self.shape = (int(rows), int(cols))
        self.rng = np.random.default_rng(config.get("seed"))
        self.topo_types = _int_keys(config["topography_types"])

    # ------------------------------------------------------------------ 1. Relief
    def generate_topography(self) -> TopographyLayer:
        # 1. Chargement dynamique de la stratégie d'élévation
        archetype = self.config.get("terrain_archetype", "alpilles")
        try:
            terrain_module = importlib.import_module(f"src.environment.terrains.{archetype}")
        except ImportError as exc:
            raise ValueError(f"Archétype de terrain inconnu ou introuvable : '{archetype}'") from exc

        # 2. Exécution de la mathématique spécifique à la carte
        elevation = terrain_module.generate_elevation(self.shape, self.config, self.rng)

        # 3. Application de la physique universelle (Gradient, Pente, Seuils)
        gy, gx = np.gradient(elevation)
        slope = np.hypot(gx, gy)

        p = self.config.get("topography_generation", {})
        upland_min = float(p.get("upland_min_elevation", self.topo_types.get(1, {}).get("min_elevation", 0.25)))
        cliff_min = float(p.get("cliff_min_elevation", self.topo_types.get(3, {}).get("min_elevation", 0.26)))
        hill_thr = float(p.get("hill_slope_threshold", 0.048))
        cliff_thr = float(p.get("cliff_slope_threshold", 0.056))

        types = np.zeros(self.shape, dtype=int)  # 0 : Plaine

        if 1 in self.topo_types:
            types[(elevation >= upland_min) & (slope < hill_thr)] = 1

        if 2 in self.topo_types:
            types[(elevation >= upland_min) & (slope >= hill_thr)] = 2

        if 3 in self.topo_types:
            ridge_line = _thin_cliffs_nms(slope, gy, gx)
            is_cliff = (elevation >= cliff_min) & (slope >= cliff_thr) & ridge_line
            types[is_cliff] = 3

        labels = {i: s.get("name", str(i)) for i, s in self.topo_types.items()}
        return TopographyLayer(types=types, elevation=elevation, slope=slope, labels=labels)

    # ------------------------------------------------------------- 2. Végétation
    def generate_vegetation(self, topo: TopographyLayer) -> VegetationLayer:
        p = self.config.get("vegetation_generation", {})
        rules = _int_keys(self.config.get("vegetation_topography_rules", {}))
        noise = smooth_noise(self.shape, p.get("noise_sigma", 2.0), self.rng)
        base_amp = p.get("noise_amplitude", 0.18)

        mean = np.full(self.shape, 0.5)
        amp = np.full(self.shape, base_amp)
        vmin, vmax = np.zeros(self.shape), np.ones(self.shape)
        
        for type_id, rule in rules.items():
            m = topo.mask(type_id)
            mean[m] = rule.get("mean", 0.5)
            amp[m] = base_amp * rule.get("variability", 1.0)
            vmin[m], vmax[m] = rule.get("min", 0.0), rule.get("max", 1.0)

        density = mean + amp * noise

        # Effet Universel : Exposition au soleil (Adret vs Ubac) basé sur le gradient Nord-Sud
        aspect_inf = float(p.get("aspect_influence", 0.16))
        if topo.elevation is not None and aspect_inf > 0.0:
            gy, _ = np.gradient(topo.elevation)
            norm_gy = np.tanh(gy / 0.04)
            upland_mask = (topo.types == 1) | (topo.types == 2)
            density[upland_mask] += (aspect_inf * norm_gy)[upland_mask]

        density = gaussian_blur(density, p.get("smoothing_sigma", 0.7))
        density = np.clip(density, vmin, vmax)
        return VegetationLayer(density=density)

    # ----------------------------------------------------------------- 3. Proies
    def generate_preys(self, topo: TopographyLayer, veg: VegetationLayer) -> PreyLayer:
        p = self.config.get("prey_generation", {})
        layer = PreyLayer(self.shape)

        for name, spec in (self.config.get("preys") or {}).items():
            weights = _int_keys(spec.get("preferred_topography", {}))
            topo_score = np.zeros(self.shape)
            for type_id, w in weights.items():
                topo_score[topo.mask(type_id)] = float(w)

            v_lo, v_hi = spec.get("optimal_vegetation", [0.0, 1.0])
            tol = max(float(spec.get("vegetation_tolerance", 0.15)), 1e-6)
            dist = np.where(veg.density < v_lo, v_lo - veg.density, np.where(veg.density > v_hi, veg.density - v_hi, 0.0))
            
            habitat = topo_score * np.exp(-0.5 * (dist / tol) ** 2)
            noise = smooth_noise(self.shape, p.get("noise_sigma", 2.0), self.rng)
            habitat *= np.clip(1.0 + spec.get("noise_amplitude", 0.2) * noise, 0.0, None)
            
            peak = habitat.max()
            layer.add(name, (habitat / peak if peak > 0 else habitat) * float(spec.get("max_density", 1.0)))

        return layer

    def generate(self):
        topo = self.generate_topography()
        veg = self.generate_vegetation(topo)
        return topo, veg, self.generate_preys(topo, veg)