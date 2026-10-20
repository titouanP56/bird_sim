"""Assemblage du monde : chargement YAML + génération des couches."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Tuple, Union

import numpy as np
import yaml

from .generators import EnvironmentGenerator
from .layers import PreyLayer, TopographyLayer, VegetationLayer


class WorldMap:
    """Environnement spatial complet (topographie, végétation, proies)."""

    def __init__(self, config: Dict[str, Any]) -> None:
        self._config = config
        generator = EnvironmentGenerator(config)
        self._topography, self._vegetation, self._preys = generator.generate()

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

    # ----------------------------------------------------------------- Matrices
    def get_topography(self) -> np.ndarray:
        return self._topography.types

    def get_elevation(self) -> np.ndarray:
        return self._topography.elevation

    def get_vegetation(self) -> np.ndarray:
        return self._vegetation.density

    def get_prey_density(self, name: str) -> np.ndarray:
        return self._preys[name]

    # ------------------------------------------------------------------ Résumé
    def summary(self) -> str:
        rows, cols = self.grid_size
        lines = [f"{self.biome_name}  |  grille {rows}x{cols}  |  seed={self.seed}"]
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
