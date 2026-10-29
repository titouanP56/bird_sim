"""Couches spatiales de l'environnement (une matrice numpy 2D par couche)."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterator, List, Optional, Tuple

import numpy as np


@dataclass
class TopographyLayer:
    """Relief discret (IDs entiers) + élévation et pente continues optionnelles."""
    types: np.ndarray
    elevation: Optional[np.ndarray] = None
    slope: Optional[np.ndarray] = None
    labels: Dict[int, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.types = np.asarray(self.types, dtype=int)
        if self.types.ndim != 2:
            raise ValueError("TopographyLayer.types doit être une matrice 2D.")
        if self.elevation is not None:
            self.elevation = np.asarray(self.elevation, dtype=float)
            if self.elevation.shape != self.types.shape:
                raise ValueError("elevation et types doivent avoir la même forme.")
        if self.slope is not None:
            self.slope = np.asarray(self.slope, dtype=float)
            if self.slope.shape != self.types.shape:
                raise ValueError("slope et types doivent avoir la même forme.")

    @property
    def shape(self) -> Tuple[int, int]:
        return self.types.shape

    def mask(self, type_id: int) -> np.ndarray:
        """Masque booléen des cellules d'un type de relief donné."""
        return self.types == type_id

    def proportions(self) -> Dict[int, float]:
        """Fraction de la carte occupée par chaque type déclaré."""
        total = self.types.size
        ids = self.labels.keys() if self.labels else np.unique(self.types)
        return {int(i): float(np.count_nonzero(self.types == i)) / total for i in ids}


@dataclass
class VegetationLayer:
    """Densité / fermeture végétale continue, bornée dans [0, 1]."""
    density: np.ndarray

    def __post_init__(self) -> None:
        self.density = np.clip(np.asarray(self.density, dtype=float), 0.0, 1.0)
        if self.density.ndim != 2:
            raise ValueError("VegetationLayer.density doit être une matrice 2D.")

    @property
    def shape(self) -> Tuple[int, int]:
        return self.density.shape


class PreyLayer:
    """Ensemble dynamique de cartes de densité de proies."""

    def __init__(self, shape: Tuple[int, int]) -> None:
        self._shape = tuple(shape)
        self._densities: Dict[str, np.ndarray] = {}
        self._capacity: Dict[str, np.ndarray] = {}

    @property
    def shape(self) -> Tuple[int, int]:
        return self._shape

    @property
    def species(self) -> List[str]:
        return list(self._densities.keys())

    def add(self, name: str, density: np.ndarray) -> None:
        density = np.asarray(density, dtype=float)
        if density.shape != self._shape:
            raise ValueError(
                f"Densité '{name}' de forme {density.shape}, attendu {self._shape}."
            )
        self._densities[name] = np.clip(density, 0.0, None)
        self._capacity[name] = self._densities[name].copy()

    def consume(self, species: str, y: int, x: int, amount: float) -> float:
        """Retire `amount` individus de la case (y, x) ; retourne la quantité réellement prélevée."""
        d = self.get(species)
        taken = float(min(max(amount, 0.0), d[y, x]))
        d[y, x] -= taken
        return taken

    def regenerate_daily(self, regen_rate: float = 0.005) -> None:
        """Croissance logistique quotidienne vers la densité initiale."""
        for name, d in self._densities.items():
            k = self._capacity[name]
            safe_k = np.where(k > 0, k, 1.0)
            growth = regen_rate * np.maximum(d, 0.02 * k) * (1.0 - d / safe_k)
            d += np.where(k > 0, growth, 0.0)
            np.clip(d, 0.0, k, out=d)

    def get(self, name: str) -> np.ndarray:
        try:
            return self._densities[name]
        except KeyError as exc:
            raise KeyError(
                f"Proie inconnue '{name}'. Disponibles : {self.species}"
            ) from exc

    def as_tensor(self) -> Tuple[np.ndarray, List[str]]:
        """Empile les cartes en tenseur 3D (n_especes, H, W) + liste d'index."""
        names = self.species
        if not names:
            return np.zeros((0, *self._shape)), names
        return np.stack([self._densities[n] for n in names]), names

    def __getitem__(self, name: str) -> np.ndarray:
        return self.get(name)

    def __contains__(self, name: object) -> bool:
        return name in self._densities

    def __iter__(self) -> Iterator[str]:
        return iter(self._densities)

    def __len__(self) -> int:
        return len(self._densities)


class FearLayer:
    """Effarouchement des proies [0, max_fear] piloté par la configuration YAML."""

    def __init__(
        self,
        shape: Tuple[int, int],
        max_fear: float = 0.90,
        neighbor_share: float = 0.0,
    ) -> None:
        self.fear = np.zeros(tuple(shape), dtype=float)
        self.max_fear = float(max_fear)
        self.neighbor_share = float(neighbor_share)

    @property
    def shape(self) -> Tuple[int, int]:
        return self.fear.shape

    def register_hunt_attempt(self, y: int, x: int, spike: float) -> None:
        rows, cols = self.fear.shape
        self.fear[y, x] += spike
        if self.neighbor_share > 0.0:
            for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                ny, nx = y + dy, x + dx
                if 0 <= ny < rows and 0 <= nx < cols:
                    self.fear[ny, nx] += spike * self.neighbor_share
        np.clip(self.fear, 0.0, self.max_fear, out=self.fear)

    def step_decay(self, decay_rate: float) -> None:
        self.fear = np.clip(self.fear - decay_rate, 0.0, self.max_fear)