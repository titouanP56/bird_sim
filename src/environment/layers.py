"""Couches spatiales de l'environnement (une matrice numpy 2D par couche)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterator, List, Optional, Tuple

import numpy as np


@dataclass
class TopographyLayer:
    """Relief discret (IDs entiers) + élévation continue optionnelle.

    Attributes:
        types: matrice (H, W) d'entiers, ID de type de relief (ex: 0..3).
        elevation: matrice (H, W) de floats normalisés dans [0, 1], ou None.
        labels: mapping {id: nom lisible} issu de la configuration.
    """

    types: np.ndarray
    elevation: Optional[np.ndarray] = None
    labels: Dict[int, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.types = np.asarray(self.types, dtype=int)
        if self.types.ndim != 2:
            raise ValueError("TopographyLayer.types doit être une matrice 2D.")
        if self.elevation is not None:
            self.elevation = np.asarray(self.elevation, dtype=float)
            if self.elevation.shape != self.types.shape:
                raise ValueError("elevation et types doivent avoir la même forme.")

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
    """Ensemble dynamique de cartes de densité de proies.

    Aucune espèce n'est codée en dur : les noms proviennent de la configuration.
    Accès par nom : ``layer["lapin"]``, itération : ``for name in layer``.
    """

    def __init__(self, shape: Tuple[int, int]) -> None:
        self._shape = tuple(shape)
        self._densities: Dict[str, np.ndarray] = {}

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
