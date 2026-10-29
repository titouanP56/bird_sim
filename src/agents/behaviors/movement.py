"""Déplacement guidé par le Ratio d'Efficience Énergétique et l'avantage du vol plané."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, Optional, Tuple

import numpy as np

from src.agents.behaviors.foraging import compute_expected_gain_map
from src.environment.map import WorldMap

if TYPE_CHECKING:  # pragma: no cover
    from src.agents.bird import Eagle

Cell = Tuple[int, int]


def chebyshev(a: Cell, b: Cell) -> int:
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


class ForagingMovement:
    """Règles de déplacement d'un rapace maximisant son ratio d'efficience énergétique."""

    def __init__(self, species_config: Dict[str, Any]) -> None:
        self.species_config = species_config
        mv = species_config.get("movement", {})
        fg = species_config.get("foraging", {})
        met = species_config.get("metabolism", {})
        soc = species_config.get("social", {})

        self.vision_radius = int(mv.get("vision_radius", 7))
        self.beta = float(fg.get("vegetation_penalty_exp", 1.25))
        self.exploration_noise = float(mv.get("exploration_noise", 0.15))
        self.recent_visit_penalty = float(mv.get("recent_visit_penalty", 0.35))
        self.step_cost = float(met.get("active_step_cost", 0.85))
        self.hunt_attempt_cost = float(met.get("hunt_attempt_cost", 1.5))
        self.min_efficiency_ratio = float(met.get("min_foraging_efficiency_ratio", 0.80))
        self.intruder_aversion = float(soc.get("intruder_presence_aversion", 2.5))
        self._peak_gain: Optional[float] = None

    @staticmethod
    def _disk_offsets(radius: int) -> np.ndarray:
        r = np.arange(-radius, radius + 1)
        dr, dc = np.meshgrid(r, r, indexing="ij")
        mask = dr ** 2 + dc ** 2 <= radius ** 2
        return np.stack([dr[mask], dc[mask]], axis=1)

    def visible_cells(self, position: Cell, grid_size: Tuple[int, int],
                      radius: Optional[int] = None) -> np.ndarray:
        rows, cols = grid_size
        offsets = self._disk_offsets(self.vision_radius if radius is None else radius)
        cells = offsets + np.asarray(position)
        inside = (cells[:, 0] >= 0) & (cells[:, 0] < rows) & (cells[:, 1] >= 0) & (cells[:, 1] < cols)
        return cells[inside]

    @staticmethod
    def step_toward(src: Cell, dst: Cell) -> Cell:
        return (src[0] + int(np.sign(dst[0] - src[0])), src[1] + int(np.sign(dst[1] - src[1])))

    def compute_expected_gain_map(self, world: WorldMap, tandem_bonus: float = 1.0) -> np.ndarray:
        return compute_expected_gain_map(world, self.species_config, tandem_bonus=tandem_bonus)

    def compute_attractiveness_map(self, world: WorldMap) -> np.ndarray:
        eg = self.compute_expected_gain_map(world)
        if self._peak_gain is None:
            self._peak_gain = float(eg.max())
        if self._peak_gain <= 0:
            return eg
        return np.clip(eg / self._peak_gain, 0.0, 1.0)

    def evaluate_and_select_step(
        self,
        agent: "Eagle",
        world: WorldMap,
        expected_gain_map: np.ndarray,
        rng: np.random.Generator,
        remaining_steps: int,
        hunting: bool,
        social_goal: Optional[Cell] = None,
    ) -> Tuple[Cell, float]:
        pos = agent.position
        nest = agent.nest_position if agent.is_territorial else None
        step_cost = agent.effective_step_cost

        if social_goal is not None and agent.satiety >= 45.0:
            return self.step_toward(pos, social_goal), -1e9

        if not hunting:
            if nest is not None and chebyshev(pos, nest) >= remaining_steps:
                return self.step_toward(pos, nest), 0.0
            cells = self.visible_cells(pos, world.grid_size, radius=1)
            if nest is not None:
                d_nest = np.maximum(np.abs(cells[:, 0] - nest[0]), np.abs(cells[:, 1] - nest[1]))
                cells = cells[d_nest <= min(2, remaining_steps - 1)]
                if len(cells) == 0:
                    return self.step_toward(pos, nest), 0.0
            idx = int(rng.integers(len(cells)))
            return (int(cells[idx, 0]), int(cells[idx, 1])), 0.0

        cells = self.visible_cells(pos, world.grid_size, self.vision_radius)
        d_cur = np.maximum(np.abs(cells[:, 0] - pos[0]), np.abs(cells[:, 1] - pos[1]))

        if nest is not None:
            cur_to_nest = chebyshev(pos, nest)
            d_nest = np.maximum(np.abs(cells[:, 0] - nest[0]), np.abs(cells[:, 1] - nest[1]))
            total_trip_energy = self.hunt_attempt_cost + step_cost * (d_cur + d_nest)
            feasible = (
                (d_nest > 0)
                & (d_cur + 1 + d_nest <= remaining_steps)
                & (total_trip_energy < agent.satiety)
            )
        else:
            total_trip_energy = self.hunt_attempt_cost + step_cost * d_cur
            feasible = (d_cur + 1 <= remaining_steps) & (total_trip_energy < agent.satiety)

        if not np.any(feasible):
            if nest is not None and pos != nest:
                return self.step_toward(pos, nest), -1e9
            return pos, -1e9

        cand = cells[feasible]
        cand_d_cur = d_cur[feasible]

        raw_gains = expected_gain_map[cand[:, 0], cand[:, 1]].astype(float)
        if nest is not None:
            cand_d_nest = np.maximum(np.abs(cand[:, 0] - nest[0]), np.abs(cand[:, 1] - nest[1]))
            total_costs = self.hunt_attempt_cost + step_cost * (cand_d_cur + cand_d_nest + cur_to_nest)
        else:
            total_costs = self.hunt_attempt_cost + step_cost * cand_d_cur

        if not agent.is_territorial and agent.state == "IMMATURE_DISPERSION":
            pres = world.presence_layer.presence[cand[:, 0], cand[:, 1]]
            total_costs = total_costs * (1.0 + self.intruder_aversion * pres)

        efficiencies = raw_gains / np.maximum(total_costs, 1e-6)

        if social_goal is not None:
            d_goal_now = chebyshev(pos, social_goal)
            d_goal_cand = np.maximum(
                np.abs(cand[:, 0] - social_goal[0]),
                np.abs(cand[:, 1] - social_goal[1]),
            )
            efficiencies += 0.35 * np.sign(d_goal_now - d_goal_cand)

        if self.recent_visit_penalty and agent.recent_positions:
            recent = set(agent.recent_positions)
            visited = np.fromiter(
                ((int(r), int(c)) in recent for r, c in cand), dtype=bool, count=len(cand)
            )
            efficiencies -= self.recent_visit_penalty * visited

        noisy_eff = efficiencies.copy()
        if self.exploration_noise > 0:
            noisy_eff += rng.uniform(0.0, self.exploration_noise, size=len(cand))

        # Toujours considérer la meilleure alternative hors de la case courante
        # (pas de grève de la faim : l'aigle choisit la moins mauvaise option s'il a faim)
        other_mask = cand_d_cur > 0
        best_alt_efficiency = float(efficiencies[other_mask].max()) if np.any(other_mask) else -1e9

        if np.any(other_mask):
            other_cand = cand[other_mask]
            other_scores = noisy_eff[other_mask]
            best_cell = other_cand[int(np.argmax(other_scores))]
        else:
            best_cell = cand[int(np.argmax(noisy_eff))]

        target: Cell = (int(best_cell[0]), int(best_cell[1]))
        nxt = self.step_toward(pos, target)

        if nest is not None and chebyshev(nxt, nest) > remaining_steps - 1:
            nxt = self.step_toward(pos, nest)
        return nxt, best_alt_efficiency