"""Génération procédurale corrélée des couches, en cascade :
    Topographie (Terrasses calcaires + Falaises fines 1 case par NMS) -> Végétation -> Proies
"""
from __future__ import annotations

from typing import Any, Dict, Mapping

import numpy as np

from .layers import PreyLayer, TopographyLayer, VegetationLayer


def gaussian_blur(field: np.ndarray, sigma: float) -> np.ndarray:
    """Flou gaussien séparable 2D (bords en mode 'reflect')."""
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
    """Bruit spatialement corrélé, centré-réduit (moyenne 0, écart-type 1)."""
    noise = gaussian_blur(rng.standard_normal(shape), sigma)
    std = noise.std()
    return (noise - noise.mean()) / (std if std > 0 else 1.0)


def _normalize(field: np.ndarray) -> np.ndarray:
    lo, hi = field.min(), field.max()
    return (field - lo) / (hi - lo) if hi > lo else np.zeros_like(field)


def _int_keys(mapping: Mapping[Any, Any]) -> Dict[int, Any]:
    return {int(k): v for k, v in mapping.items()}


def _thin_cliffs_nms(slope: np.ndarray, gy: np.ndarray, gx: np.ndarray) -> np.ndarray:
    """Suppression des Non-Maxima (NMS type Canny) le long de la direction du gradient.

    Une falaise est un objet linéaire (rupture de pente) et non une surface large :
    une cellule (r, c) n'est conservée comme crête de pente que si sa pente `slope[r, c]`
    est un maximum local par rapport à ses deux voisines situées en amont et en aval
    de la ligne de plus grande pente. Garantit des barres rocheuses de 1 case d'épaisseur.
    """
    rows, cols = slope.shape
    angle = np.mod(np.rad2deg(np.arctan2(gy, gx)), 180.0)

    s_pad = np.pad(slope, 1, mode="edge")
    center = s_pad[1:-1, 1:-1]

    # 4 directions quantifiées du gradient : Est-Ouest (0°), Diag NE-SO (45°), Nord-Sud (90°), Diag NO-SE (135°)
    d0 = (angle < 22.5) | (angle >= 157.5)
    d45 = (angle >= 22.5) & (angle < 67.5)
    d90 = (angle >= 67.5) & (angle < 112.5)
    d135 = (angle >= 112.5) & (angle < 157.5)

    n1 = np.zeros_like(slope)
    n2 = np.zeros_like(slope)

    # Axe horizontal (voisin gauche / droite)
    n1[d0] = s_pad[1:-1, :-2][d0]
    n2[d0] = s_pad[1:-1, 2:][d0]

    # Diagonale 45°
    n1[d45] = s_pad[:-2, :-2][d45]
    n2[d45] = s_pad[2:, 2:][d45]

    # Axe vertical (voisin haut / bas)
    n1[d90] = s_pad[:-2, 1:-1][d90]
    n2[d90] = s_pad[2:, 1:-1][d90]

    # Diagonale 135°
    n1[d135] = s_pad[:-2, 2:][d135]
    n2[d135] = s_pad[2:, :-2][d135]

    # Maximum local strict d'un côté, large de l'autre (évite d'effacer les crêtes symétriques)
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
        p = self.config.get("topography_generation", {})
        rows, cols = self.shape
        y, x = np.meshgrid(
            np.linspace(0.0, 1.0, rows), np.linspace(0.0, 1.0, cols), indexing="ij"
        )

        phase = self.rng.uniform(0, 2 * np.pi)
        y_ridge = p.get("ridge_center", 0.5) + p.get("ridge_sinuosity", 0.05) * np.sin(
            2 * np.pi * 1.5 * x + phase
        )
        dy = y - y_ridge

        half_len = max(p.get("ridge_length", 0.8) / 2.0, 1e-6)
        taper = np.exp(-(((x - 0.5) / half_len) ** 6))

        # Massif calcaire à sommet tabulaire (causse / plateau sommital)
        ridge_raw = np.exp(-0.5 * (dy / p.get("ridge_width", 0.11)) ** 2)
        flatness = float(p.get("ridge_flatness", 1.45))
        ridge = np.clip(ridge_raw * flatness, 0.0, 1.0)

        # Fonction de terrasse sigmoïde sur les flancs pour créer de vraies cuestas calcaires
        sharpness = float(p.get("terrace_sharpness", 5.0))
        if sharpness > 0:
            ridge = 0.65 * ridge + 0.35 * (1.0 / (1.0 + np.exp(-sharpness * (ridge - 0.55))))

        piedmont = np.exp(-0.5 * (dy / p.get("plateau_width", 0.25)) ** 2)
        piedmont = np.clip(piedmont * 1.6, 0.0, 1.0)

        relief = (ridge + p.get("plateau_strength", 0.48) * piedmont) * taper
        relief += p.get("noise_amplitude", 0.18) * smooth_noise(
            self.shape, p.get("noise_sigma", 3.0), self.rng
        )
        elevation = _normalize(relief)

        gy, gx = np.gradient(elevation)
        slope = np.hypot(gx, gy)

        upland_min = float(
            p.get("upland_min_elevation", self.topo_types.get(1, {}).get("min_elevation", 0.28))
        )
        cliff_min = float(
            p.get("cliff_min_elevation", self.topo_types.get(3, {}).get("min_elevation", 0.22))
        )
        hill_thr = float(p.get("hill_slope_threshold", 0.032))
        cliff_thr = float(p.get("cliff_slope_threshold", 0.052))

        types = np.zeros(self.shape, dtype=int)  # 0 : Plaine

        # 1 : Plateau (hauteur + pente faible : replats de piémont et sommets plats)
        if 1 in self.topo_types:
            types[(elevation >= upland_min) & (slope < hill_thr)] = 1

        # 2 : Versant (hauteur + pente modérée à forte hors ligne de rupture)
        if 2 in self.topo_types:
            types[(elevation >= upland_min) & (slope >= hill_thr)] = 2

        # 3 : Falaise (uniquement les lignes de rupture de pente de 1 case d'épaisseur via NMS)
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
        vmin = np.zeros(self.shape)
        vmax = np.ones(self.shape)
        for type_id, rule in rules.items():
            m = topo.mask(type_id)
            mean[m] = rule.get("mean", 0.5)
            amp[m] = base_amp * rule.get("variability", 1.0)
            vmin[m] = rule.get("min", 0.0)
            vmax[m] = rule.get("max", 1.0)

        density = mean + amp * noise
        density = gaussian_blur(density, p.get("smoothing_sigma", 0.0))
        density = np.clip(density, vmin, vmax)
        return VegetationLayer(density=density)

    # ----------------------------------------------------------------- 3. Proies
    def generate_preys(
        self, topo: TopographyLayer, veg: VegetationLayer
    ) -> PreyLayer:
        p = self.config.get("prey_generation", {})
        layer = PreyLayer(self.shape)

        for name, spec in (self.config.get("preys") or {}).items():
            weights = _int_keys(spec.get("preferred_topography", {}))
            topo_score = np.zeros(self.shape)
            for type_id, w in weights.items():
                topo_score[topo.mask(type_id)] = float(w)

            v_lo, v_hi = spec.get("optimal_vegetation", [0.0, 1.0])
            tol = max(float(spec.get("vegetation_tolerance", 0.15)), 1e-6)
            v = veg.density
            dist = np.where(v < v_lo, v_lo - v, np.where(v > v_hi, v - v_hi, 0.0))
            veg_score = np.exp(-0.5 * (dist / tol) ** 2)

            habitat = topo_score * veg_score

            noise = smooth_noise(self.shape, p.get("noise_sigma", 2.0), self.rng)
            habitat *= np.clip(1.0 + spec.get("noise_amplitude", 0.2) * noise, 0.0, None)

            peak = habitat.max()
            habitat = habitat / peak if peak > 0 else habitat
            layer.add(name, habitat * float(spec.get("max_density", 1.0)))

        return layer

    # ---------------------------------------------------------------- Cascade
    def generate(self):
        topo = self.generate_topography()
        veg = self.generate_vegetation(topo)
        preys = self.generate_preys(topo, veg)
        return topo, veg, preys