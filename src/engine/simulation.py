"""Moteur temporel multi-annuel : 1 tick = 1 jour, gestion des couples et de la reproduction."""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Sequence, Tuple, Union
import numpy as np

if TYPE_CHECKING:  # pragma: no cover
    from src.analytics.telemetry import TelemetryLogger

from src.agents.behaviors.reproduction import (
    STAGE_INCUBATION,
    STAGE_POST_FLEDGING,
    STAGE_REARING,
    BreedingNest,
)
from src.agents.bird import ADULT, IMMATURE, Eagle, load_species_config
from src.environment.map import WorldMap
from src.visualization.collector import SimulationCollector


class Simulation:
    """Boucle journalière multi-annuelle : ontogénie, interactions sociales et reproduction."""

    def __init__(
        self,
        world: WorldMap,
        species_config: Union[Dict[str, Any], str, Path],
        n_days: int = 1095,
        seed: Optional[int] = None,
        states: Sequence[str] = (ADULT, IMMATURE),
        initial_specs: Optional[List[Dict[str, Any]]] = None,
        telemetry: Optional["TelemetryLogger"] = None,
    ) -> None:
        if not isinstance(species_config, dict):
            species_config = load_species_config(species_config)
        self.world = world
        self.species_config = species_config
        self.n_days = n_days
        self.seed = seed if seed is not None else world.seed
        self.rng = np.random.default_rng(self.seed)
        self.day = 0

        # Par défaut pour "both" : Femelle adulte sur falaise + Mâle immature en plaine
        if initial_specs is None:
            if list(states) == [ADULT, IMMATURE]:
                initial_specs = [
                    {"state": ADULT, "sex": "F", "age_days": 1460},    # Femelle adulte (4 ans)
                    {"state": IMMATURE, "sex": "M", "age_days": 650},  # Mâle immature (~1.8 an)
                ]
            else:
                initial_specs = [
                    {"state": s, "sex": "F" if i % 2 == 0 else "M"}
                    for i, s in enumerate(states)
                ]

        self.eagles: List[Eagle] = []
        for i, spec in enumerate(initial_specs):
            self.eagles.append(
                Eagle(
                    agent_id=i + 1,
                    species_config=species_config,
                    state=spec["state"],
                    sex=spec.get("sex", "F"),
                    age_days=spec.get("age_days"),
                )
            )

        self.attractiveness_map = self.eagles[0].movement.compute_attractiveness_map(world)
        self.collectors: List[SimulationCollector] = [
            SimulationCollector(world, self.attractiveness_map, e) for e in self.eagles
        ]

        spawned_nests = []
        for e, col in zip(self.eagles, self.collectors):
            pos = e.spawn(world, self.rng, avoid_positions=spawned_nests)
            if e.is_territorial:
                spawned_nests.append(pos)
            col.record_spawn(pos)

        self.breeding_nests: Dict[Tuple[int, int], BreedingNest] = {}
        self.social_events: List[Tuple[int, str]] = []
        self.telemetry: Optional["TelemetryLogger"] = telemetry
        if self.telemetry is not None:
            self.telemetry.on_simulation_start(self.world, self.eagles, self.seed)

    @property
    def eagle(self) -> Eagle:
        return self.eagles[0]

    @property
    def collector(self) -> SimulationCollector:
        return self.collectors[0]

    def _get_eagle_by_id(self, agent_id: Optional[int]) -> Optional[Eagle]:
        if agent_id is None:
            return None
        for e in self.eagles:
            if e.agent_id == agent_id:
                return e
        return None

    def _sync_breeding_nests(self) -> None:
        """Crée ou met à jour les structures `BreedingNest` pour chaque couple formé."""
        for e in self.eagles:
            if not e.alive or not e.is_territorial or e.partner_id is None or e.nest_position is None:
                continue
            partner = self._get_eagle_by_id(e.partner_id)
            if partner is None or not partner.alive:
                e.partner_id = None
                continue
            pair_key = (min(e.agent_id, partner.agent_id), max(e.agent_id, partner.agent_id))
            if pair_key not in self.breeding_nests:
                fem = e if e.sex == "F" else partner
                mal = partner if e.sex == "F" else e
                self.breeding_nests[pair_key] = BreedingNest(
                    nest_position=e.nest_position,
                    female_id=fem.agent_id,
                    male_id=mal.agent_id,
                )
                msg = f"Jour {self.day} : Formation du couple #{fem.agent_id} (F) & #{mal.agent_id} (M) au nid {e.nest_position}"
                self.social_events.append((self.day, msg))

    def step(self) -> None:
        self.day += 1
        day_of_year = ((self.day - 1) % 365) + 1
        year = ((self.day - 1) // 365) + 1

        self._sync_breeding_nests()

        # 1. Mise à jour des contraintes reproductives des parents (incubation / nourrissage)
        repro_cfg = self.species_config.get("reproduction", {})
        for e in self.eagles:
            e.is_incubating = False
            e.must_feed_brood = False

        for pair_key, bnest in list(self.breeding_nests.items()):
            fem = self._get_eagle_by_id(bnest.female_id)
            mal = self._get_eagle_by_id(bnest.male_id)
            if fem is None or mal is None or not (fem.alive and mal.alive):
                continue

            fledged = bnest.step_reproduction_day(
                self.day, day_of_year, year, fem, mal, repro_cfg, self.rng
            )
            if bnest.stage == STAGE_INCUBATION:
                fem.is_incubating = True
                mal.must_feed_brood = True
            elif bnest.stage in (STAGE_REARING, STAGE_POST_FLEDGING):
                fem.must_feed_brood = True
                mal.must_feed_brood = True

            # Si des jeunes s'émancipent aujourd'hui, ils deviennent de nouveaux agents en dispersion !
            for _ in range(fledged):
                new_id = len(self.eagles) + 1
                new_sex = "F" if self.rng.random() < 0.5 else "M"
                juv = Eagle(
                    agent_id=new_id,
                    species_config=self.species_config,
                    state=IMMATURE,
                    sex=new_sex,
                    age_days=105,
                    parent_nest=bnest.nest_position,
                )
                juv._move_to(bnest.nest_position)
                col = SimulationCollector(self.world, self.attractiveness_map, juv)
                col.record_spawn(juv.position)
                self.eagles.append(juv)
                self.collectors.append(col)
                self.social_events.append(
                    (self.day, f"Jour {self.day} : Emancipation du jeune #{new_id} ({new_sex}) issu du nid {bnest.nest_position}")
                )

        # 2. Action journalière de chaque aigle
        daily_reports: Dict[int, Any] = {}
        for eagle, col in zip(self.eagles, self.collectors):
            if not eagle.alive:
                continue
            start = eagle.position
            partner = self._get_eagle_by_id(eagle.partner_id)
            report = eagle.step_day(
                self.world, self.rng, day_of_year=day_of_year,
                all_eagles=self.eagles, partner=partner,
            )
            col.record_day(self.day, report, start)
            daily_reports[eagle.agent_id] = (start, report)

        self._sync_breeding_nests()

        for col in self.collectors:
            col.record_fear(self.world.fear_layer.fear)

        if self.telemetry is not None:
            self.telemetry.log_step(
                day=self.day,
                world=self.world,
                eagles=self.eagles,
                daily_reports=daily_reports,
                breeding_nests=self.breeding_nests,
            )

        fg_decay = float(self.species_config.get("foraging", {}).get("fear_daily_decay", 0.12))
        pr_decay = float(self.species_config.get("social", {}).get("presence_daily_decay", 0.08))
        self.world.step_environment_day(fg_decay, pr_decay)

    def run(self, n_days: Optional[int] = None) -> List[SimulationCollector]:
        n = self.n_days if n_days is None else n_days
        self.n_days = max(self.n_days, self.day + n)
        for _ in range(n):
            if not any(e.alive for e in self.eagles):
                break
            self.step()
        if self.telemetry is not None:
            self.telemetry.finalize(self.world, self.breeding_nests, self.social_events)
        return self.collectors