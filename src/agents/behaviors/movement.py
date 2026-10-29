"""Déplacement guidé par le Ratio d'Efficience Énergétique (Central-Place Foraging Theory).

Aucune limite de distance fixe (`max_range_from_nest` supprimé) :
Pour toute case candidate `c` dans le disque de perception :
1. Coût énergétique marginal de transport :
   - Immature (nomade) : E_vol(c) = step_cost * d(pos, c)
   - Adulte (retour au nid obligatoire le soir) :
     E_vol(c) = step_cost * max(0, d(pos, c) + d(c, nid) - d(pos, nid))
     (mesure le surcoût énergétique total de l'aller-retour induit par le choix de `c`).
2. Ratio d'Efficience Énergétique (Ydenberg 1994) :
     eta(c) = E[Gain](c) / (hunt_attempt_cost + E_vol(c))
3. Contraintes physiques naturelles :
   - Temps diurne : d(pos, c) + 1 (attaque) + d(c, nid) <= remaining_steps
   - Énergie disponible : coût total aller-retour < satiété actuelle de l'aigle.
"""
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

        self.vision_radius = int(mv.get("vision_radius", 7))
        self.beta = float(fg.get("vegetation_penalty_exp", 1.25))
        self.exploration_noise = float(mv.get("exploration_noise", 0.15))
        self.recent_visit_penalty = float(mv.get("recent_visit_penalty", 0.40))
        self.step_cost = float(met.get("active_step_cost", 0.85))
        self.hunt_attempt_cost = float(met.get("hunt_attempt_cost", 1.8))
        self.min_efficiency_ratio = float(met.get("min_foraging_efficiency_ratio", 1.25))
        self._peak_gain: Optional[float] = None

    # ----------------------------------------------------------------- Helpers
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

    # ------------------------------------------------------------ Attractivité
    def compute_expected_gain_map(self, world: WorldMap) -> np.ndarray:
        """Espérance de gain brute E[Gain](y, x) en points de satiété."""
        return compute_expected_gain_map(world, self.species_config)

    def compute_attractiveness_map(self, world: WorldMap) -> np.ndarray:
        """Version normalisée dans [0, 1] de E[Gain](y, x) pour la compatibilité Dashboard."""
        eg = self.compute_expected_gain_map(world)
        if self._peak_gain is None:
            self._peak_gain = float(eg.max())
        if self._peak_gain <= 0:
            return eg
        return np.clip(eg / self._peak_gain, 0.0, 1.0)

    # -------------------------------------------------------------- Décision
    def evaluate_and_select_step(
        self,
        agent: "Eagle",
        world: WorldMap,
        expected_gain_map: np.ndarray,
        rng: np.random.Generator,
        remaining_steps: int,
        hunting: bool,
    ) -> Tuple[Cell, float]:
        """Choisit le prochain pas `nxt` et retourne `(nxt, best_alternative_efficiency)`.
        Aucune limite de distance codée en dur : seules la lumière du jour (`remaining_steps`),
        l'énergie disponible (`agent.satiety`) et la rentabilité (`eta >= min_efficiency_ratio`)
        régissent l'éloignement de l'aigle.
        """
        pos = agent.position
        nest = agent.nest_position if agent.is_territorial else None

        # Mode repos/patrouille : reste près du dortoir
        if not hunting:
            if nest is not None and chebyshev(pos, nest) >= remaining_steps:
                return self.step_toward(pos, nest), 0.0
            cells = self.visible_cells(pos, world.grid_size, radius=1)
            if nest is not None:
                d_nest = np.maximum(np.abs(cells[:, 0] - nest[0]), np.abs(cells[:, 1] - nest[1]))
                cells = cells[d_nest <= remaining_steps - 1]
                if len(cells) == 0:
                    return self.step_toward(pos, nest), 0.0
            idx = int(rng.integers(len(cells)))
            return (int(cells[idx, 0]), int(cells[idx, 1])), 0.0

        # Mode chasse : évalue les cases visibles
        cells = self.visible_cells(pos, world.grid_size, self.vision_radius)
        d_cur = np.maximum(np.abs(cells[:, 0] - pos[0]), np.abs(cells[:, 1] - pos[1]))

        if nest is not None:
            cur_to_nest = chebyshev(pos, nest)
            d_nest = np.maximum(np.abs(cells[:, 0] - nest[0]), np.abs(cells[:, 1] - nest[1]))
            # Coût marginal de détour aller-retour : aller en `c` puis rentrer au nid vs rentrer maintenant
            extra_flight_steps = np.maximum(0, d_cur + d_nest - cur_to_nest)
            total_trip_energy = self.hunt_attempt_cost + self.step_cost * (d_cur + d_nest)

            # Faisabilité purement physique : avant la tombée de la nuit ET avant épuisement énergétique
            feasible = (
                (d_nest > 0)
                & (d_cur + 1 + d_nest <= remaining_steps)
                & (total_trip_energy < agent.satiety)
            )
        else:
            extra_flight_steps = d_cur
            total_trip_energy = self.hunt_attempt_cost + self.step_cost * d_cur
            feasible = (d_cur + 1 <= remaining_steps) & (total_trip_energy < agent.satiety)

        if not np.any(feasible):
            # Il est l'heure de rentrer au nid avant la nuit (ou plus assez d'énergie)
            if nest is not None and pos != nest:
                return self.step_toward(pos, nest), -1e9
            return pos, -1e9

        cand = cells[feasible]
        cand_d_cur = d_cur[feasible]
        cand_extra_steps = extra_flight_steps[feasible]

        # Calcul du Ratio d'Efficience Énergétique : eta(c) = E[Gain](c) / Coût_marginal_total(c)
        raw_gains = expected_gain_map[cand[:, 0], cand[:, 1]].astype(float)
        marginal_costs = self.hunt_attempt_cost + self.step_cost * cand_extra_steps
        efficiencies = raw_gains / np.maximum(marginal_costs, 1e-6)

        if self.recent_visit_penalty and agent.recent_positions:
            recent = set(agent.recent_positions)
            visited = np.fromiter(
                ((int(r), int(c)) in recent for r, c in cand), dtype=bool, count=len(cand)
            )
            efficiencies -= self.recent_visit_penalty * visited

        # Filtre de rentabilité énergétique : un prédateur ne se déplace pas à perte
        profitable = efficiencies >= self.min_efficiency_ratio
        if not np.any(profitable):
            if nest is not None and pos != nest:
                return self.step_toward(pos, nest), -1e9
            return pos, -1e9

        noisy_eff = efficiencies.copy()
        if self.exploration_noise > 0:
            noisy_eff += rng.uniform(0.0, self.exploration_noise, size=len(cand))

        # Meilleure efficience *ailleurs* que sur la case courante (d_cur > 0)
        other_mask = (cand_d_cur > 0) & profitable
        best_alt_efficiency = float(efficiencies[other_mask].max()) if np.any(other_mask) else -1e9

        if np.any(other_mask):
            other_cand = cand[other_mask]
            other_scores = noisy_eff[other_mask]
            best_cell = other_cand[int(np.argmax(other_scores))]
        else:
            best_cell = cand[int(np.argmax(noisy_eff))]

        target: Cell = (int(best_cell[0]), int(best_cell[1]))
        nxt = self.step_toward(pos, target)

        # Sécurité crépusculaire : pouvoir toujours rejoindre le nid avant la fin du jour
        if nest is not None and chebyshev(nxt, nest) > remaining_steps - 1:
            nxt = self.step_toward(pos, nest)
        return nxt, best_alt_efficiency

    def select_next_step(
        self,
        agent: "Eagle",
        world: WorldMap,
        attractiveness_map: np.ndarray,
        rng: np.random.Generator,
        remaining_steps: int = 1,
        hunting: bool = True,
    ) -> Cell:
        eg_map = self.compute_expected_gain_map(world)
        nxt, _ = self.evaluate_and_select_step(
            agent, world, eg_map, rng, remaining_steps, hunting
        )
        return nxt