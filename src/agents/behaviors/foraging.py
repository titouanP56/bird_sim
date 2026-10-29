"""Mécanique de chasse probabiliste fondée sur le Ratio d'Efficience Énergétique (Ydenberg 1994).

1. Pour chaque case (y, x), l'espérance de gain énergétique E[Gain](y, x) d'un piqué est :
       E[Gain](y, x) = sum_p P(cibler p | y, x) * P(capturer p | y, x) * Gain_p
2. Le Ratio d'Efficience d'une attaque immédiate sur la case courante est :
       eta_here = E[Gain](cell) / hunt_attempt_cost
3. L'aigle déclenche un piqué sur sa case actuelle si et seulement si :
   - Il lui reste assez de temps diurne (remaining_steps - 1 >= dist_au_nid) et d'énergie
     pour rentrer dormir au nid après l'attaque,
   - eta_here >= min_foraging_efficiency_ratio (l'attaque est énergétiquement rentable),
   - eta_here >= best_alternative_efficiency (il n'est pas plus efficient de poursuivre son vol
     vers une autre case visible en tenant compte du coût de transport aller-retour).
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, Optional, Set, Tuple

import numpy as np

from src.environment.map import WorldMap

if TYPE_CHECKING:  # pragma: no cover
    from src.agents.bird import Eagle

Cell = Tuple[int, int]


def effective_visibility_map(world: WorldMap, beta: float) -> np.ndarray:
    """Matrice 2D de visibilité effective : (1 - veg)^beta * (1 - fear)."""
    veg_factor = np.clip(1.0 - world.get_vegetation(), 0.0, 1.0) ** beta
    return veg_factor * (1.0 - world.fear_layer.fear)


def effective_visibility(world: WorldMap, y: int, x: int, beta: float) -> float:
    veg = float(world.get_vegetation()[y, x])
    fear = float(world.fear_layer.fear[y, x])
    return ((1.0 - veg) ** beta) * (1.0 - fear)


def compute_expected_gain_map(world: WorldMap, species_config: Dict[str, Any]) -> np.ndarray:
    """Calcule de façon vectorisée l'espérance mathématique de gain E[Gain](y, x)
    (en points de satiété) d'une tentative de chasse sur chaque case de la carte.
    """
    fg = species_config.get("foraging", {})
    diet = fg.get("diet", {})
    base_prob = float(fg.get("base_capture_prob", 0.40))
    beta = float(fg.get("vegetation_penalty_exp", 1.25))

    vis = effective_visibility_map(world, beta)
    shape = world.grid_size
    total_weights = np.zeros(shape, dtype=float)
    weighted_expected_satiety = np.zeros(shape, dtype=float)

    for name, spec in diet.items():
        if name not in world.prey_layer:
            continue
        d = world.get_prey_density(name)
        pref = float(spec.get("preference", 1.0))
        gain = float(spec.get("satiety_gain", 30.0))

        w = pref * d
        saturation = 1.0 - np.exp(-d)
        p_capture = base_prob * saturation * vis

        total_weights += w
        weighted_expected_satiety += w * p_capture * gain

    safe_total = np.where(total_weights > 1e-9, total_weights, 1.0)
    expected_gain = np.where(total_weights > 1e-9, weighted_expected_satiety / safe_total, 0.0)
    return expected_gain


def should_attempt_hunt(
    agent: "Eagle",
    cell: Cell,
    best_alternative_efficiency: float,
    expected_gain_map: np.ndarray,
    remaining_steps: int,
    attempted_cells: Set[Cell],
) -> bool:
    """Décision par Ratio d'Efficience Énergétique (Gain espéré / Coût dépensé) :
    - Aucune barrière géométrique artificielle : seules comptent la contrainte de rentrer
      avant la nuit (`remaining_steps - 1 >= dist_to_nest`) et la réserve d'énergie.
    """
    if remaining_steps < 1:
        return False
    if cell in attempted_cells:
        return False

    if agent.is_territorial and agent.nest_position is not None:
        if cell == agent.nest_position:
            return False
        dist_to_nest = max(
            abs(cell[0] - agent.nest_position[0]),
            abs(cell[1] - agent.nest_position[1]),
        )
        # 1. Contrainte diurne : après avoir pris 1 pas de temps pour attaquer,
        #    il doit rester au moins `dist_to_nest` pas avant la nuit pour rentrer au nid.
        if remaining_steps - 1 < dist_to_nest:
            return False
        # 2. Contrainte énergétique : garder assez d'énergie pour l'attaque + le vol retour
        return_energy_needed = agent.hunt_attempt_cost + agent.active_step_cost * dist_to_nest
        if agent.satiety <= return_energy_needed:
            return False

    cost_here = max(agent.hunt_attempt_cost, 1e-6)
    efficiency_here = float(expected_gain_map[cell]) / cost_here

    if efficiency_here < agent.min_efficiency_ratio:
        return False

    return efficiency_here >= best_alternative_efficiency - 1e-6


def attempt_hunt(agent: "Eagle", world: WorldMap, rng: np.random.Generator) -> Optional[str]:
    """Exécute un piqué sur la case courante (coûte `hunt_attempt_cost` en énergie et 1 pas diurne)."""
    cfg = agent.foraging_cfg
    y, x = agent.position
    visibility = effective_visibility(world, y, x, agent.movement.beta)
    world.fear_layer.register_hunt_attempt(y, x, float(cfg["fear_spike_on_attempt"]))

    species, weights = [], []
    for name, spec in cfg["diet"].items():
        if name in world.prey_layer:
            species.append(name)
            weights.append(float(spec["preference"]) * float(world.get_prey_density(name)[y, x]))
    total = float(np.sum(weights))
    if total <= 0.0:
        return None

    target = species[int(rng.choice(len(species), p=np.asarray(weights) / total))]
    density = float(world.get_prey_density(target)[y, x])
    saturation = 1.0 - np.exp(-density)
    p = float(cfg["base_capture_prob"]) * saturation * visibility
    if rng.random() >= p:
        return None

    spec = cfg["diet"][target]
    world.prey_layer.consume(target, y, x, float(spec["biomass_taken"]))
    agent.satiety = min(agent.max_satiety, agent.satiety + float(spec["satiety_gain"]))
    return target