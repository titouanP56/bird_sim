"""Moteur temporel : 1 tick = 1 jour."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Union

import numpy as np

from src.agents.bird import ADULT, Eagle, load_species_config
from src.environment.map import WorldMap
from src.visualization.collector import SimulationCollector


class Simulation:
    """Boucle journalière : chaque aigle vivant agit, puis l'environnement évolue.

    Plusieurs aigles (ex. adulte + immature) partagent le même monde : ils se
    gênent indirectement via l'épuisement des proies et l'effarouchement.
    """

    def __init__(self, world: WorldMap, species_config: Union[Dict[str, Any], str, Path],
                 n_days: int = 30, seed: Optional[int] = None,
                 states: Sequence[str] = (ADULT,)) -> None:
        if not isinstance(species_config, dict):
            species_config = load_species_config(species_config)
        self.world = world
        self.species_config = species_config
        self.n_days = n_days
        self.seed = seed if seed is not None else world.seed
        self.rng = np.random.default_rng(self.seed)
        self.day = 0

        self.eagles: List[Eagle] = [Eagle(i + 1, species_config, s) for i, s in enumerate(states)]
        # Carte d'attractivité initiale (monde intact), identique pour tous les aigles
        self.attractiveness_map = self.eagles[0].movement.compute_attractiveness_map(world)
        for e in self.eagles[1:]:
            e.movement.compute_attractiveness_map(world)
        self.collectors: List[SimulationCollector] = [
            SimulationCollector(world, self.attractiveness_map, e) for e in self.eagles
        ]
        for e, col in zip(self.eagles, self.collectors):
            e.spawn(world, self.rng)
            col.record_spawn(e.position)

    # Raccourcis (premier aigle)
    @property
    def eagle(self) -> Eagle:
        return self.eagles[0]

    @property
    def collector(self) -> SimulationCollector:
        return self.collectors[0]

    def step(self) -> None:
        self.day += 1
        for eagle, col in zip(self.eagles, self.collectors):
            if not eagle.alive:
                continue
            start = eagle.position
            report = eagle.step_day(self.world, self.rng)
            col.record_day(self.day, report, start)
        for col in self.collectors:
            col.record_fear(self.world.fear_layer.fear)
        decay = float(self.species_config.get("foraging", {}).get("fear_daily_decay", 0.12))
        self.world.step_environment_day(decay)

    def run(self, n_days: Optional[int] = None) -> List[SimulationCollector]:
        n = self.n_days if n_days is None else n_days
        self.n_days = max(self.n_days, self.day + n)
        for _ in range(n):
            if not any(e.alive for e in self.eagles):
                break
            self.step()
        return self.collectors
