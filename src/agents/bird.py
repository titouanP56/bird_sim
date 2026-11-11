"""Agents oiseaux : Ontogénie, Avantage Aérodynamique de Falaise, Social & Reproduction."""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Deque, Dict, List, Optional, Set, Tuple, Union

import numpy as np
import yaml

from src.agents.behaviors.foraging import attempt_hunt, should_attempt_hunt
from src.agents.behaviors.movement import ForagingMovement, chebyshev
from src.agents.behaviors.social import (
    check_and_defend_territory,
    deposit_territorial_presence,
    find_courtship_target_or_mate,
)
from src.environment.map import WorldMap

Cell = Tuple[int, int]

JUVENILE = "JUVENILE_DEPENDANT"
IMMATURE = "IMMATURE_DISPERSION"
SUBADULT = "SUBADULTE_PROSPECTEUR"
ADULT = "ADULTE_TERRITORIAL"

STATE_LABELS = {
    JUVENILE: "Juvénile au nid",
    IMMATURE: "Immature en dispersion",
    SUBADULT: "Subadulte prospecteur",
    ADULT: "Adulte territorial",
}

MODE_HUNT = "CHASSE_ACTIVE"
MODE_REST = "REPOS_PATROUILLE"
MODE_DISPLAY = "PARADE_NUPTIALE"
MODE_INCUBATE = "INCUBATION_NID"
MODE_DEFEND = "DEFENSE_TERRITOIRE"


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
    state: str
    alive: bool = True


class Eagle:
    """Aigle de Bonelli individuel doté d'un sexe, d'un âge et d'un statut social."""

    def __init__(
        self,
        agent_id: int,
        species_config: Dict[str, Any],
        state: str = ADULT,
        sex: str = "F",
        age_days: Optional[int] = None,
        parent_nest: Optional[Cell] = None,
    ) -> None:
        if state not in STATE_LABELS:
            raise ValueError(f"État inconnu '{state}'.")
        self.agent_id = agent_id
        self.species_config = species_config
        self.state = state
        self.sex = sex.upper()
        self.parent_nest = parent_nest

        ont = species_config.get("ontogeny", {})
        self.emancipation_age = int(ont.get("emancipation_age_days", 100))
        self.subadult_age = int(ont.get("subadult_prospector_age_days", 780))
        self.adult_age = int(ont.get("adult_maturity_age_days", 1095))

        if age_days is None:
            age_days = {
                JUVENILE: 65,
                IMMATURE: 550,
                SUBADULT: 850,
                ADULT: 1460,
            }[state]
        self.age_days: int = int(age_days)

        mv = species_config.get("movement", {})
        met = species_config.get("metabolism", {})
        self.foraging_cfg: Dict[str, Any] = species_config.get("foraging", {})
        st = species_config.get("life_states", {}).get(state, {})

        self.base_daily_steps = int(mv.get("max_daily_steps", 14))
        self.seasonal_amp = int(mv.get("seasonal_step_amplitude", 2))
        self.resting_daily_steps = int(mv.get("resting_daily_steps", 1))
        self.max_satiety = float(met.get("max_satiety", 100.0))
        self.hunger_threshold = float(met.get("hunger_threshold", 65.0))
        self.basal_cost = float(met.get("basal_resting_cost", 8.0))
        self.courtship_extra_cost = float(met.get("courtship_extra_cost", 1.2))
        self.active_step_cost = float(met.get("active_step_cost", 0.85))
        self.cliff_gliding_discount = float(met.get("cliff_gliding_discount", 0.45))
        self.hunt_attempt_cost = float(met.get("hunt_attempt_cost", 1.5))
        self.min_efficiency_ratio = float(met.get("min_foraging_efficiency_ratio", 0.80))

        self.nest_top_fraction = float(st.get("nest_selection_top_fraction", 0.08))
        self.spawn_topography = [int(t) for t in
                                 st.get("roost_topography", st.get("spawn_topography", [0]))]

        self.movement = ForagingMovement(species_config)
        self.satiety: float = float(met.get("initial_satiety", 85.0))
        self.alive: bool = True
        self.nest_position: Optional[Cell] = None
        self.territory_id: int = agent_id if state == ADULT else 0
        self.partner_id: Optional[int] = None
        self.is_displaying: bool = False
        self.is_incubating: bool = False
        self.must_feed_brood: bool = False
        self.defense_count: int = 0
        self.expelled_count: int = 0

        self.position: Cell = (-1, -1)
        self.recent_positions: Deque[Cell] = deque(maxlen=int(mv.get("memory_length", 6)))
        self.trajectory: List[Cell] = []

    @property
    def is_territorial(self) -> bool:
        return self.state == ADULT and self.nest_position is not None

    @property
    def effective_step_cost(self) -> float:
        """Coût énergétique d'1 pas de vol : un aigle partant d'une falaise bénéficie
        de l'énergie potentielle d'altitude (vol plané) et des ascendances orographiques.
        """
        if self.is_territorial:
            return self.active_step_cost * self.cliff_gliding_discount
        return self.active_step_cost

    @property
    def is_sexually_mature_or_subadult(self) -> bool:
        return self.state in (SUBADULT, ADULT) or self.age_days >= self.subadult_age

    @property
    def age_years(self) -> float:
        return self.age_days / 365.0

    @property
    def name(self) -> str:
        sex_sym = "Femelle" if self.sex == "F" else "Mâle"
        return (f"{self.species_config.get('display_name', 'Aigle')} #{self.agent_id} "
                f"[{sex_sym}, {self.age_years:.1f} ans - {STATE_LABELS[self.state]}]")

    def establish_territory(self, cliff_cell: Cell) -> None:
        self.state = ADULT
        self.nest_position = cliff_cell
        self.territory_id = self.agent_id
        self._move_to(cliff_cell)

    def _update_ontogeny(self) -> None:
        if self.state == JUVENILE and self.age_days >= self.emancipation_age:
            self.state = IMMATURE
            self.nest_position = None
        elif self.state == IMMATURE and self.age_days >= self.subadult_age:
            self.state = SUBADULT

    def daylight_steps(self, day_of_year: int) -> int:
        angle = 2.0 * np.pi * (day_of_year - 172) / 365.0
        return max(10, int(round(self.base_daily_steps + self.seasonal_amp * np.cos(angle))))

    # ------------------------------------------------------------------ Spawn
    def spawn(
        self,
        world: WorldMap,
        rng: np.random.Generator,
        avoid_positions: Optional[List[Cell]] = None,
        forced_position: Optional[Cell] = None,
    ) -> Cell:
        if forced_position is not None:
            self._move_to((int(forced_position[0]), int(forced_position[1])))
            if self.state == ADULT:
                self.nest_position = self.position
                deposit_territorial_presence(self, world, displaying=True)
            return self.position

        topo = world.get_topography()
        candidates = np.argwhere(np.isin(topo, self.spawn_topography)) if self.spawn_topography else None
        if candidates is None or len(candidates) == 0:
            candidates = np.argwhere(np.ones_like(topo, dtype=bool))

        if self.state == ADULT and len(candidates) > 1:
            eg_map = self.movement.compute_expected_gain_map(world)
            k = self.movement.vision_radius
            rows, cols = eg_map.shape
            yy, xx = np.ogrid[:rows, :cols]
            step_c = self.active_step_cost * self.cliff_gliding_discount
            scores = []
            for y, x in candidates:
                y0, y1 = max(0, y - k), min(rows, y + k + 1)
                x0, x1 = max(0, x - k), min(cols, x + k + 1)
                dist = np.maximum(np.abs(yy[y0:y1, :] - y), np.abs(xx[:, x0:x1] - x))
                trip_cost = self.hunt_attempt_cost + 2.0 * step_c * dist
                eff = eg_map[y0:y1, x0:x1] / np.maximum(trip_cost, 1e-6)
                valid_eff = np.sort(eff[dist > 0].ravel())
                top_k = valid_eff[-min(20, len(valid_eff)):]
                scores.append(float(top_k.mean()) if len(top_k) > 0 else 0.0)
            scores_arr = np.asarray(scores)
            n_top = max(1, int(len(scores_arr) * self.nest_top_fraction))
            top = np.argsort(scores_arr)[-n_top:]
            r, c = candidates[int(rng.choice(top))]
        else:
            if avoid_positions and len(candidates) > 1:
                dists = np.min(
                    [
                        np.maximum(np.abs(candidates[:, 0] - ay), np.abs(candidates[:, 1] - ax))
                        for ay, ax in avoid_positions
                    ],
                    axis=0,
                )
                far = candidates[dists >= 10]
                if len(far) > 0:
                    candidates = far
            r, c = candidates[rng.integers(len(candidates))]

        self._move_to((int(r), int(c)))
        if self.state == ADULT:
            self.nest_position = self.position
            deposit_territorial_presence(self, world, displaying=True)
        return self.position

    # -------------------------------------------------------------- Pas du jour
    def step_day(
        self,
        world: WorldMap,
        rng: np.random.Generator,
        day_of_year: int = 1,
        all_eagles: Optional[List["Eagle"]] = None,
        partner: Optional["Eagle"] = None,
    ) -> DayReport:
        self._update_ontogeny()
        satiety_start = self.satiety
        all_eagles = all_eagles or []

        # 1. Femelle en incubation (fixée sur le nid)
        if self.is_incubating and self.nest_position is not None:
            self.is_displaying = False
            self._move_to(self.nest_position)
            deposit_territorial_presence(self, world, displaying=False)
            cost = self.basal_cost * 0.80
            self.satiety = max(0.0, self.satiety - cost)
            if self.satiety <= 0.0:
                self.alive = False
            self.age_days += 1
            return DayReport(
                substeps=[self.position], mode=MODE_INCUBATE, attempts=0, captured=None,
                satiety_start=satiety_start, satiety_peak=satiety_start,
                satiety_end=self.satiety, cost=cost, moves=0, state=self.state, alive=self.alive,
            )

        # 2. Besoin de chasser
        partner_incubating = partner is not None and partner.alive and partner.is_incubating
        need_food_for_family = self.must_feed_brood or (partner_incubating and partner.satiety < 85.0)
        hunting = (self.satiety < self.hunger_threshold) or need_food_for_family

        # 3. Mode Parade Nuptiale (uniquement si bien rassasié S >= 72 pour ne pas s'épuiser)
        self.is_displaying = False
        if self.is_territorial and not hunting and self.satiety >= 72.0:
            if self.partner_id is None or (1 <= day_of_year <= 75):
                self.is_displaying = True
                mode = MODE_DISPLAY
            else:
                mode = MODE_REST
        else:
            mode = MODE_HUNT if hunting else MODE_REST

        remaining = self.daylight_steps(day_of_year) if hunting else self.resting_daily_steps

        in_tandem = (
            partner is not None
            and partner.alive
            and not partner.is_incubating
            and hunting
        )
        tandem_mult = float(self.foraging_cfg.get("tandem_prob_multiplier", 1.50)) if in_tandem else 1.0
        expected_gain_map = self.movement.compute_expected_gain_map(world, tandem_bonus=tandem_mult)

        social_goal: Optional[Cell] = None
        if self.state == SUBADULT and self.partner_id is None:
            social_goal = find_courtship_target_or_mate(self, all_eagles, world, expected_gain_map, rng)
            if self.is_territorial:
                hunting = self.satiety < self.hunger_threshold

        substeps: List[Cell] = []
        moves = attempts = 0
        attempted: Set[Cell] = set()
        captured: Optional[str] = None

        while remaining > 0:
            if self.is_territorial and all_eagles:
                defended = check_and_defend_territory(
                    self, all_eagles, world, expected_gain_map, remaining
                )
                if defended is not None:
                    _, step_pos = defended
                    if step_pos != self.position:
                        moves += 1
                    self._move_to(step_pos)
                    substeps.append(step_pos)
                    remaining -= 1
                    mode = MODE_DEFEND
                    continue

            if captured is not None and not need_food_for_family:
                if self.is_territorial and self.position != self.nest_position:
                    nxt = self.movement.step_toward(self.position, self.nest_position)
                    if nxt != self.position:
                        moves += 1
                    self._move_to(nxt)
                    substeps.append(nxt)
                    remaining -= 1
                    continue
                break


            if (
                in_tandem
                and partner is not None
                and partner.position != self.position
                and partner.position != self.nest_position
                and chebyshev(self.position, partner.position) <= 3
                and not partner_incubating
            ):
                nxt = self.movement.step_toward(self.position, partner.position)
                best_alt_eff = -1e9
            else:
                nxt, best_alt_eff = self.movement.evaluate_and_select_step(
                    self, world, expected_gain_map, rng, remaining, hunting, social_goal=social_goal
                )

            if hunting and should_attempt_hunt(
                self, self.position, best_alt_eff, expected_gain_map, remaining, attempted
            ):
                attempted.add(self.position)
                attempts += 1
                remaining -= 1
                captured = attempt_hunt(self, world, rng, partner=partner)
                substeps.append(self.position)
                expected_gain_map = self.movement.compute_expected_gain_map(world, tandem_bonus=tandem_mult)
                if captured is not None and need_food_for_family and self.satiety >= 85.0:
                    need_food_for_family = False
                continue

            if nxt == self.position:
                break

            moves += 1
            self._move_to(nxt)
            substeps.append(nxt)
            remaining -= 1

            if self.state == SUBADULT and self.partner_id is None and social_goal is not None:
                find_courtship_target_or_mate(self, all_eagles, world, expected_gain_map, rng)

        if self.is_territorial and self.nest_position is not None and self.position != self.nest_position:
            while self.position != self.nest_position:
                nxt = self.movement.step_toward(self.position, self.nest_position)
                moves += 1
                self._move_to(nxt)
                substeps.append(nxt)

        if self.is_territorial:
            deposit_territorial_presence(self, world, displaying=self.is_displaying)

        if not substeps:
            substeps.append(self.position)

        peak = self.satiety
        extra_display = self.courtship_extra_cost if self.is_displaying else 0.0
        cost = (
            self.basal_cost
            + extra_display
            + self.effective_step_cost * moves
            + self.hunt_attempt_cost * attempts
        )
        self.satiety = max(0.0, self.satiety - cost)
        if self.satiety <= 0.0:
            self.alive = False
        self.age_days += 1
        return DayReport(
            substeps=substeps, mode=mode, attempts=attempts, captured=captured,
            satiety_start=satiety_start, satiety_peak=peak,
            satiety_end=self.satiety, cost=cost, moves=moves, state=self.state, alive=self.alive,
        )

    def _move_to(self, cell: Cell) -> None:
        self.position = cell
        self.recent_positions.append(cell)
        self.trajectory.append(cell)

    def __repr__(self) -> str:
        return (f"Eagle(id={self.agent_id}, sex={self.sex}, state={self.state}, "
                f"pos={self.position}, S={self.satiety:.0f}, age={self.age_years:.1f}a)")