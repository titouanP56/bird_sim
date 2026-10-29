"""Assemblage du monde : chargement YAML + génération des couches."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import yaml

from .generators import EnvironmentGenerator
from .layers import FearLayer, PreyLayer, TopographyLayer, VegetationLayer


class WorldMap:
    """Environnement spatial complet (topographie, végétation, proies, effarouchement)."""

    def __init__(self, config: Dict[str, Any]) -> None:
        self._config = config
        generator = EnvironmentGenerator(config)
        self._topography, self._vegetation, self._preys = generator.generate()

        fear_cfg = config.get("fear_dynamics", {})
        self._fear = FearLayer(
            self._topography.shape,
            max_fear=float(fear_cfg.get("max_fear", 0.90)),
            neighbor_share=float(fear_cfg.get("neighbor_share", 0.0)),
        )
        self._default_fear_decay = float(fear_cfg.get("default_daily_decay", 0.12))

    @classmethod
    def from_yaml(cls, path: Union[str, Path]) -> "WorldMap":
        with open(path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        return cls(config)

    # ------------------------------------------------------------- Métadonnées
    @property
    def config(self) -> Dict[str, Any]:
        return self._config

    @property
    def biome_name(self) -> str:
        return self._config.get("biome_name", "Unknown biome")

    @property
    def seed(self):
        return self._config.get("seed")

    @property
    def cell_size_km(self) -> float:
        return float(self._config.get("cell_size_km", 0.5))

    @property
    def grid_size(self) -> Tuple[int, int]:
        return self._topography.shape

    @property
    def topography_types(self) -> Dict[int, Dict[str, Any]]:
        return {int(k): v for k, v in self._config["topography_types"].items()}

    @property
    def vegetation_strata(self) -> List[Dict[str, Any]]:
        return list(self._config.get("vegetation_strata", []))

    @property
    def prey_names(self) -> List[str]:
        return self._preys.species

    def prey_config(self, name: str) -> Dict[str, Any]:
        return self._config["preys"][name]

    # ------------------------------------------------------------------ Couches
    @property
    def topography_layer(self) -> TopographyLayer:
        return self._topography

    @property
    def vegetation_layer(self) -> VegetationLayer:
        return self._vegetation

    @property
    def prey_layer(self) -> PreyLayer:
        return self._preys

    @property
    def fear_layer(self) -> FearLayer:
        return self._fear

    @property
    def prey_regeneration_rate(self) -> float:
        return float(self._config.get("prey_dynamics", {}).get("regeneration_rate", 0.005))

    # ------------------------------------------------------------- Dynamique
    def step_environment_day(self, fear_decay_rate: Optional[float] = None) -> None:
        decay = self._default_fear_decay if fear_decay_rate is None else float(fear_decay_rate)
        self._fear.step_decay(decay)
        self._preys.regenerate_daily(self.prey_regeneration_rate)

    # ----------------------------------------------------------------- Matrices
    def get_topography(self) -> np.ndarray:
        return self._topography.types

    def get_elevation(self) -> np.ndarray:
        return self._topography.elevation

    def get_slope(self) -> Optional[np.ndarray]:
        return self._topography.slope

    def get_vegetation(self) -> np.ndarray:
        return self._vegetation.density

    def get_prey_density(self, name: str) -> np.ndarray:
        return self._preys[name]

    # ------------------------------------------------------------------ Résumé
    def summary(self) -> str:
        rows, cols = self.grid_size
        km_h, km_w = rows * self.cell_size_km, cols * self.cell_size_km
        lines = [
            f"{self.biome_name}  |  grille {rows}x{cols} "
            f"({km_h:.0f}x{km_w:.0f} km, 1 case = {self.cell_size_km * 1000:.0f}m)  |  seed={self.seed}"
        ]
        lines.append("Topographie :")
        for tid, frac in self._topography.proportions().items():
            lines.append(f"  [{tid}] {self._topography.labels.get(tid, tid):<10} {frac:6.1%}")
        veg = self.get_vegetation()
        lines.append(f"Végétation : moyenne={veg.mean():.2f}  min={veg.min():.2f}  max={veg.max():.2f}")
        for s in self.vegetation_strata:
            frac = np.mean((veg >= s["min"]) & (veg <= s["max"] if s["max"] >= 1.0 else veg < s["max"]))
            lines.append(f"  {s['name']:<18} {frac:6.1%}")
        lines.append("Proies (total individus | max/cellule) :")
        for name in self.prey_names:
            d = self._preys[name]
            lines.append(f"  {name:<10} {d.sum():9.1f} | {d.max():5.2f}")
        return "\n".join(lines)