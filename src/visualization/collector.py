"""Collecte des données journalières de la simulation."""

from __future__ import annotations

from collections import Counter
from typing import TYPE_CHECKING, Dict, List, Optional, Tuple

import numpy as np

from src.environment.map import WorldMap

if TYPE_CHECKING:  # pragma: no cover
    from src.agents.bird import DayReport, Eagle

Cell = Tuple[int, int]


class SimulationCollector:
    """Enregistre, pour chaque jour t, positions, occupation, satiété et activité."""

    def __init__(self, world: WorldMap, attractiveness_map: np.ndarray,
                 eagle: Optional["Eagle"] = None) -> None:
        self.world = world
        self.eagle = eagle
        self.attractiveness_map = attractiveness_map
        self.topo_ids = sorted(world.topography_types)

        self.spawn_position: Cell | None = None
        self.days: List[int] = []
        self.daily_positions: List[Cell] = []          # position de fin de journée
        self.daily_substeps: List[List[Cell]] = []     # sous-étapes de chaque jour
        self.daily_mean_attractiveness: List[float] = []
        self.daily_distance: List[float] = []          # en cellules (euclidien)
        self.daily_topo_counts: List[Dict[int, int]] = []
        self.occupancy_grid = np.zeros(world.grid_size, dtype=int)

        self.daily_modes: List[str] = []
        self.daily_attempts: List[int] = []
        self.satiety_start: List[float] = []
        self.satiety_peak: List[float] = []
        self.satiety_end: List[float] = []
        self.captures: List[Tuple[int, str]] = []      # (jour, espèce)
        self.died_on_day: Optional[int] = None

        self._fear_sum = np.zeros(world.grid_size, dtype=float)
        self._fear_days = 0

    # -------------------------------------------------------------- Écriture
    def record_spawn(self, position: Cell) -> None:
        self.spawn_position = position
        self.occupancy_grid[position] += 1

    def record_day(self, day: int, report: "DayReport", start: Cell) -> None:
        substeps = report.substeps
        topo = self.world.get_topography()
        path = np.array([start] + list(substeps))
        for cell in substeps:
            self.occupancy_grid[cell] += 1

        rows, cols = path[1:, 0], path[1:, 1]
        counts = {tid: 0 for tid in self.topo_ids}
        for tid in topo[rows, cols]:
            counts[int(tid)] += 1

        self.days.append(day)
        self.daily_positions.append(substeps[-1])
        self.daily_substeps.append(list(substeps))
        self.daily_mean_attractiveness.append(float(self.attractiveness_map[rows, cols].mean()))
        self.daily_distance.append(float(np.linalg.norm(np.diff(path, axis=0), axis=1).sum()))
        self.daily_topo_counts.append(counts)

        self.daily_modes.append(report.mode)
        self.daily_attempts.append(report.attempts)
        self.satiety_start.append(report.satiety_start)
        self.satiety_peak.append(report.satiety_peak)
        self.satiety_end.append(report.satiety_end)
        if report.captured:
            self.captures.append((day, report.captured))
        if not report.alive and self.died_on_day is None:
            self.died_on_day = day

    def record_fear(self, fear: np.ndarray) -> None:
        self._fear_sum += fear
        self._fear_days += 1

    # --------------------------------------------------------------- Lecture
    @property
    def full_path(self) -> List[Cell]:
        """Spawn + toutes les sous-étapes dans l'ordre chronologique."""
        head = [self.spawn_position] if self.spawn_position is not None else []
        return head + [c for day in self.daily_substeps for c in day]

    @property
    def step_times(self) -> np.ndarray:
        """Jour (fractionnaire) d'arrivée de chaque sous-étape de `full_path[1:]`."""
        t: List[float] = []
        for day, sub in zip(self.days, self.daily_substeps):
            n = len(sub)
            t.extend(day - 1 + (k + 1) / n for k in range(n))
        return np.array(t)

    @property
    def mean_fear_map(self) -> np.ndarray:
        return self._fear_sum / max(self._fear_days, 1)

    def diet_counts(self) -> Counter:
        return Counter(sp for _, sp in self.captures)

    def topo_time_fractions(self) -> np.ndarray:
        """Matrice (n_jours, n_reliefs) des fractions de temps par relief."""
        m = np.array([[d[t] for t in self.topo_ids] for d in self.daily_topo_counts], dtype=float)
        return m / np.maximum(m.sum(axis=1, keepdims=True), 1)

    def topo_totals(self) -> Dict[int, float]:
        n = max(sum(sum(d.values()) for d in self.daily_topo_counts), 1)
        return {t: sum(d[t] for d in self.daily_topo_counts) / n for t in self.topo_ids}

    def summary(self) -> str:
        types = self.world.topography_types
        visited = int((self.occupancy_grid > 0).sum())
        total_cells = self.occupancy_grid.size
        totals = {t: sum(d[t] for d in self.daily_topo_counts) for t in self.topo_ids}
        n_steps = max(sum(totals.values()), 1)
        favourite = max(totals, key=totals.get)
        hunt = sum(m == "CHASSE_ACTIVE" for m in self.daily_modes)
        rest = len(self.daily_modes) - hunt
        diet = self.diet_counts()
        name = self.eagle.name if self.eagle is not None else "Aigle"
        status = (f"MORT d'inanition au jour {self.died_on_day}" if self.died_on_day
                  else f"vivant (S finale = {self.satiety_end[-1]:.0f})")
        lines = [
            f"=== {name} : {status} ===",
            f"Simulation : {len(self.days)} jours  |  {n_steps} déplacements",
            f"  Jours chasse / repos: {hunt} / {rest}  |  tentatives : {sum(self.daily_attempts)}",
            f"  Captures            : {len(self.captures)}  "
            + (", ".join(f"{k}={v}" for k, v in diet.items()) or "aucune"),
            f"  Cases visitées      : {visited} / {total_cells} ({visited / total_cells:.1%})",
            f"  Attractivité moyenne: {np.mean(self.daily_mean_attractiveness):.3f}"
            f"  (moyenne carte = {self.attractiveness_map.mean():.3f})",
            f"  Distance totale     : {sum(self.daily_distance):.1f} cellules"
            f"  ({np.mean(self.daily_distance):.1f} / jour)",
            f"  Relief préféré      : {types[favourite].get('name', favourite)}",
            "  Temps par relief    :",
        ]
        for t in self.topo_ids:
            lines.append(f"    {types[t].get('name', t):<10} {totals[t] / n_steps:6.1%}")
        return "\n".join(lines)
