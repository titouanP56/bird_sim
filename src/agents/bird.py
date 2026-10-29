"""Agents oiseaux — Décision par Ratio d'Efficience Énergétique (sans rayon fixe)."""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Deque, Dict, List, Optional, Set, Tuple, Union

import numpy as np
import yaml

from src.agents.behaviors.foraging import attempt_hunt, should_attempt_hunt
from src.agents.behaviors.movement import ForagingMovement, chebyshev
from src.environment.map import WorldMap

Cell = Tuple[int, int]

ADULT = "ADULTE_TERRITORIAL"
IMMATURE = "IMMATURE_DISPERSION"
STATE_LABELS = {ADULT: "Adulte territorial", IMMATURE: "Immature en dispersion"}

MODE_HUNT = "CHASSE_ACTIVE"
MODE_REST = "REPOS_PATROUILLE"


def load_species_config(path: Union[str, Path]) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


@dataclass
class DayReport:
    """Bilan d'une journée d'un aigle."""
    substeps: List[Cell]
    mode: str
    attempts: int
    captured: Optional[str]
    satiety_start: float
    satiety_peak: float
    satiety_end: float
    cost: float
    moves: int
    alive: bool = True


class Eagle:
    """Aigle individuel : position, satiété, état de vie et mémoire à court terme."""

    def __init__(self, agent_id: int, species_config: Dict[str, Any],
                 state: str = ADULT) -> None:
        if state not in (ADULT, IMMATURE):
            raise ValueError(f"État inconnu '{state}' (attendu {ADULT} ou {IMMATURE}).")
        self.agent_id = agent_id
        self.species_config = species_config
        self.state = state

        mv = species_config.get("movement", {})
        met = species_config.get("metabolism", {})
        self.foraging_cfg: Dict[str, Any] = species_config.get("foraging", {})
        st = species_config.get("life_states", {}).get(state, {})

        self.max_daily_steps = int(mv.get("max_daily_steps", 14))
        self.resting_daily_steps = int(mv.get("resting_daily_steps", 1))
        self.max_satiety = float(met.get("max_satiety", 100.0))
        self.hunger_threshold = float(met.get("hunger_threshold", 65.0))
        self.basal_cost = float(met.get("basal_resting_cost", 9.0))
        self.active_step_cost = float(met.get("active_step_cost", 0.85))
        self.hunt_attempt_cost = float(met.get("hunt_attempt_cost", 1.8))
        self.min_efficiency_ratio = float(met.get("min_foraging_efficiency_ratio", 1.25))

        self.nest_top_fraction = float(st.get("nest_selection_top_fraction", 0.08))
        self.spawn_topography = [int(t) for t in
                                 st.get("roost_topography", st.get("spawn_topography", []))]

        self.movement = ForagingMovement(species_config)
        self.satiety: float = float(met.get("initial_satiety", 80.0))
        self.alive: bool = True
        self.nest_position: Optional[Cell] = None
        self.position: Cell = (-1, -1)
        self.age_days: int = 0
        self.recent_positions: Deque[Cell] = deque(maxlen=int(mv.get("memory_length", 6)))
        self.trajectory: List[Cell] = []

    @property
    def is_territorial(self) -> bool:
        return self.state == ADULT

    @property
    def name(self) -> str:
        return (f"{self.species_config.get('display_name', 'Aigle')} #{self.agent_id} "
                f"({STATE_LABELS[self.state]})")

    # ------------------------------------------------------------------ Cycle
    def spawn(self, world: WorldMap, rng: np.random.Generator) -> Cell:
        """L'adulte s'installe sur une falaise offrant un haut ratio d'efficience énergétique."""
        topo = world.get_topography()
        candidates = np.argwhere(np.isin(topo, self.spawn_topography)) if self.spawn_topography else None
        if candidates is None or len(candidates) == 0:
            candidates = np.argwhere(np.ones_like(topo, dtype=bool))

        r, c = candidates[rng.integers(len(candidates))]
        if self.is_territorial and len(candidates) > 1:
            eg_map = self.movement.compute_expected_gain_map(world)
            k = self.movement.vision_radius
            rows, cols = eg_map.shape
            yy, xx = np.ogrid[:rows, :cols]
            scores = []
            for y, x in candidates:
                y0, y1 = max(0, y - k), min(rows, y + k + 1)
                x0, x1 = max(0, x - k), min(cols, x + k + 1)
                dist = np.maximum(np.abs(yy[y0:y1, :] - y), np.abs(xx[:, x0:x1] - x))
                trip_cost = self.hunt_attempt_cost + 2.0 * self.active_step_cost * dist
                eff = eg_map[y0:y1, x0:x1] / np.maximum(trip_cost, 1e-6)
                scores.append(float(eff[dist > 0].mean()) if np.any(dist > 0) else 0.0)
            scores_arr = np.asarray(scores)
            n_top = max(1, int(len(scores_arr) * self.nest_top_fraction))
            top = np.argsort(scores_arr)[-n_top:]
            r, c = candidates[int(rng.choice(top))]

        self._move_to((int(r), int(c)))
        if self.is_territorial:
            self.nest_position = self.position
        return self.position

    def step_day(self, world: WorldMap, rng: np.random.Generator) -> DayReport:
        """Un tick journalier : l'aigle explore et chasse tant que le ratio d'efficience
        et la lumière du jour le permettent, puis rentre dormir au nid."""
        satiety_start = self.satiety
        hunting = self.satiety < self.hunger_threshold
        mode = MODE_HUNT if hunting else MODE_REST
        remaining = self.max_daily_steps if hunting else self.resting_daily_steps

        expected_gain_map = self.movement.compute_expected_gain_map(world)
        substeps: List[Cell] = []
        moves = attempts = 0
        attempted: Set[Cell] = set()
        captured: Optional[str] = None

        while remaining > 0:
            if captured is not None:
                # Une fois rassasié par une prise, l'adulte rentre au nid et l'immature se perche
                if self.is_territorial and self.position != self.nest_position:
                    nxt = self.movement.step_toward(self.position, self.nest_position)
                    if nxt != self.position:
                        moves += 1
                    self._move_to(nxt)
                    substeps.append(nxt)
                    remaining -= 1
                    continue
                break

            nxt, best_alt_eff = self.movement.evaluate_and_select_step(
                self, world, expected_gain_map, rng, remaining, hunting
            )

            # L'aigle attaque ici si le ratio d'efficience sur place est rentable
            # et meilleur que la poursuite du vol vers `nxt`.
            if hunting and should_attempt_hunt(
                self, self.position, best_alt_eff, expected_gain_map, remaining, attempted
            ):
                attempted.add(self.position)
                attempts += 1
                remaining -= 1
                captured = attempt_hunt(self, world, rng)
                substeps.append(self.position)
                expected_gain_map = self.movement.compute_expected_gain_map(world)
                continue

            if nxt == self.position:
                break

            moves += 1
            self._move_to(nxt)
            substeps.append(nxt)
            remaining -= 1

        # Sécurité crépusculaire : si l'adulte est encore à 1 pas de son aire à la tombée de la nuit
        if self.is_territorial and self.nest_position is not None and self.position != self.nest_position:
            while self.position != self.nest_position:
                nxt = self.movement.step_toward(self.position, self.nest_position)
                moves += 1
                self._move_to(nxt)
                substeps.append(nxt)

        if not substeps:
            substeps.append(self.position)

        peak = self.satiety
        cost = (
            self.basal_cost
            + self.active_step_cost * moves
            + self.hunt_attempt_cost * attempts
        )
        self.satiety = max(0.0, self.satiety - cost)
        if self.satiety <= 0.0:
            self.alive = False
        self.age_days += 1
        return DayReport(
            substeps=substeps, mode=mode, attempts=attempts, captured=captured,
            satiety_start=satiety_start, satiety_peak=peak,
            satiety_end=self.satiety, cost=cost, moves=moves, alive=self.alive,
        )

    def _move_to(self, cell: Cell) -> None:
        self.position = cell
        self.recent_positions.append(cell)
        self.trajectory.append(cell)

    def __repr__(self) -> str:
        return (f"Eagle(id={self.agent_id}, state={self.state}, pos={self.position}, "
                f"S={self.satiety:.0f}, age={self.age_days}j)")