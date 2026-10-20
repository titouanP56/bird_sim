"""Génération procédurale corrélée des couches, en cascade :

    Topographie  ->  Végétation  ->  Proies

Le bruit spatial est obtenu par lissage gaussien d'un bruit blanc
(implémenté en numpy pur, sans dépendance à scipy).
"""

from __future__ import annotations

from typing import Any, Dict, Mapping

import numpy as np

from .layers import PreyLayer, TopographyLayer, VegetationLayer


# -----------------------------------------------------------------------------
#  Outils de bruit
# -----------------------------------------------------------------------------
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
    """Les clés YAML peuvent être lues en str ou int : on normalise en int."""
    return {int(k): v for k, v in mapping.items()}


# -----------------------------------------------------------------------------
#  Générateur
# -----------------------------------------------------------------------------
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

        # Ligne de crête E-O légèrement sinueuse
        phase = self.rng.uniform(0, 2 * np.pi)
        y_ridge = p.get("ridge_center", 0.5) + p.get("ridge_sinuosity", 0.05) * np.sin(
            2 * np.pi * 1.5 * x + phase
        )
        dy = y - y_ridge

        # Atténuation aux extrémités Est/Ouest (fenêtre super-gaussienne)
        half_len = max(p.get("ridge_length", 0.8) / 2.0, 1e-6)
        taper = np.exp(-(((x - 0.5) / half_len) ** 6))

        ridge = np.exp(-0.5 * (dy / p.get("ridge_width", 0.1)) ** 2)
        piedmont = np.exp(-0.5 * (dy / p.get("plateau_width", 0.24)) ** 2)
        # Plateaux : piémont aplati (terrasses) pour imiter les replats calcaires
        piedmont = np.clip(piedmont * 1.6, 0.0, 1.0)

        relief = (ridge + p.get("plateau_strength", 0.45) * piedmont) * taper
        relief += p.get("noise_amplitude", 0.18) * smooth_noise(
            self.shape, p.get("noise_sigma", 3.0), self.rng
        )
        elevation = _normalize(relief)

        # Classification par seuils d'altitude
        types = np.zeros(self.shape, dtype=int)
        for type_id, spec in sorted(
            self.topo_types.items(), key=lambda kv: kv[1].get("min_elevation", 0.0)
        ):
            types[elevation >= spec.get("min_elevation", 0.0)] = type_id

        # Escarpements : cellules de montagne à forte pente -> falaise
        cliff_id = max(self.topo_types)  # le plus haut ID = relief le plus abrupt
        mountain_id = cliff_id - 1
        slope_thr = p.get("cliff_slope_threshold")
        if slope_thr is not None and mountain_id in self.topo_types:
            gy, gx = np.gradient(elevation)
            slope = np.hypot(gx, gy)
            types[(types == mountain_id) & (slope >= slope_thr)] = cliff_id

        labels = {i: s.get("name", str(i)) for i, s in self.topo_types.items()}
        return TopographyLayer(types=types, elevation=elevation, labels=labels)

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
        # Lissage pour des transitions naturelles, puis contraintes strictes
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
            # Affinité topographique
            weights = _int_keys(spec.get("preferred_topography", {}))
            topo_score = np.zeros(self.shape)
            for type_id, w in weights.items():
                topo_score[topo.mask(type_id)] = float(w)

            # Adéquation végétale : 1 dans l'optimum, décroissance gaussienne hors
            v_lo, v_hi = spec.get("optimal_vegetation", [0.0, 1.0])
            tol = max(float(spec.get("vegetation_tolerance", 0.15)), 1e-6)
            v = veg.density
            dist = np.where(v < v_lo, v_lo - v, np.where(v > v_hi, v - v_hi, 0.0))
            veg_score = np.exp(-0.5 * (dist / tol) ** 2)

            habitat = topo_score * veg_score

            # Légère variation spatiale aléatoire
            noise = smooth_noise(self.shape, p.get("noise_sigma", 2.0), self.rng)
            habitat *= np.clip(1.0 + spec.get("noise_amplitude", 0.2) * noise, 0.0, None)

            peak = habitat.max()
            habitat = habitat / peak if peak > 0 else habitat
            layer.add(name, habitat * float(spec.get("max_density", 1.0)))

        return layer

    # ---------------------------------------------------------------- Cascade
    def generate(self):
        """Génère (topographie, végétation, proies) en cascade."""
        topo = self.generate_topography()
        veg = self.generate_vegetation(topo)
        preys = self.generate_preys(topo, veg)
        return topo, veg, preys
