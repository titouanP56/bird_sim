"""Mécanique de chasse probabiliste (Ratio d'Efficience Énergétique + Avantage Falaise)."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, Optional, Set, Tuple

import numpy as np

from src.environment.map import WorldMap

if TYPE_CHECKING:  # pragma: no cover
    from src.agents.bird import Eagle

Cell = Tuple[int, int]


def effective_visibility_map(world: WorldMap, beta: float) -> np.ndarray:
    veg_factor = np.clip(1.0 - world.get_vegetation(), 0.0, 1.0) ** beta
    return veg_factor * (1.0 - world.fear_layer.fear)


def effective_visibility(world: WorldMap, y: int, x: int, beta: float) -> float:
    veg = float(world.get_vegetation()[y, x])
    fear = float(world.fear_layer.fear[y, x])
    return ((1.0 - veg) ** beta) * (1.0 - fear)


def compute_expected_gain_map(
    world: WorldMap,
    species_config: Dict[str, Any],
    tandem_bonus: float = 1.0,
) -> np.ndarray:
    """Calcule l'espérance mathématique de gain E[Gain](y, x) (en points de satiété)."""
    fg = species_config.get("foraging", {})
    diet = fg.get("diet", {})
    base_prob = float(fg.get("base_capture_prob", 0.45)) * tandem_bonus
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
        p_capture = np.clip(base_prob * saturation * vis, 0.0, 0.95)

        total_weights += w
        weighted_expected_satiety += w * p_capture * gain

    safe_total = np.where(total_weights > 1e-9, total_weights, 1.0)
    return np.where(total_weights > 1e-9, weighted_expected_satiety / safe_total, 0.0)


def should_attempt_hunt(
    agent: "Eagle",
    cell: Cell,
    best_alternative_efficiency: float,
    expected_gain_map: np.ndarray,
    remaining_steps: int,
    attempted_cells: Set[Cell],
) -> bool:
    """Décision par Ratio d'Efficience Énergétique (Gain espéré / Coût aller-retour).
    Plus l'aigle a faim, plus son seuil minimal d'exigence diminue (évite toute grève de la faim).
    """
    if remaining_steps < 1:
        return False
    if cell in attempted_cells:
        return False

    step_cost = agent.effective_step_cost

    if agent.is_territorial and agent.nest_position is not None:
        if cell == agent.nest_position:
            return False
        dist_to_nest = max(
            abs(cell[0] - agent.nest_position[0]),
            abs(cell[1] - agent.nest_position[1]),
        )
        if remaining_steps - 1 < dist_to_nest:
            return False
        return_energy_needed = agent.hunt_attempt_cost + step_cost * dist_to_nest
        if agent.satiety <= return_energy_needed:
            return False
        total_cost_here = agent.hunt_attempt_cost + 2.0 * step_cost * dist_to_nest
    else:
        total_cost_here = max(agent.hunt_attempt_cost, 1e-6)

    efficiency_here = float(expected_gain_map[cell]) / max(total_cost_here, 1e-6)

    # Seuil adaptatif : si S est bas, l'aigle accepte des ratios plus faibles pour survivre
    hunger_urgency = np.clip(agent.satiety / max(agent.hunger_threshold, 1.0), 0.25, 1.0)
    effective_min_ratio = agent.min_efficiency_ratio * hunger_urgency

    if efficiency_here < effective_min_ratio:
        return False

    return efficiency_here >= best_alternative_efficiency - 1e-6


def attempt_hunt(
    agent: "Eagle",
    world: WorldMap,
    rng: np.random.Generator,
    partner: Optional["Eagle"] = None,
) -> Optional[str]:
    """Exécute un piqué. Si `partner` chasse en tandem (ou couve au nid), applique la synergie."""
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

    in_tandem = (
        partner is not None
        and partner.alive
        and max(abs(partner.position[0] - y), abs(partner.position[1] - x)) <= 2
        and not partner.is_incubating
    )
    mult = float(cfg.get("tandem_prob_multiplier", 1.50)) if in_tandem else 1.0

    target = species[int(rng.choice(len(species), p=np.asarray(weights) / total))]
    density = float(world.get_prey_density(target)[y, x])
    saturation = 1.0 - np.exp(-density)
    p = min(0.95, float(cfg["base_capture_prob"]) * mult * saturation * visibility)
    if rng.random() >= p:
        return None

    spec = cfg["diet"][target]
    world.prey_layer.consume(target, y, x, float(spec["biomass_taken"]))
    gain = float(spec["satiety_gain"])

    if partner is not None and partner.alive and gain >= 35.0:
        share_ratio = float(cfg.get("tandem_share_ratio", 0.58))
        if partner.is_incubating or in_tandem or partner.satiety < partner.hunger_threshold:
            agent.satiety = min(agent.max_satiety, agent.satiety + gain * share_ratio)
            partner.satiety = min(partner.max_satiety, partner.satiety + gain * share_ratio)
            return target

    agent.satiety = min(agent.max_satiety, agent.satiety + gain)
    return target