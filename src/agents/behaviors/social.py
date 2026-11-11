"""Comportements sociaux : Défense territoriale (Brown 1964), Parade nuptiale et Appariement."""
from __future__ import annotations

from typing import TYPE_CHECKING, List, Optional, Tuple

import numpy as np

from src.environment.map import WorldMap

if TYPE_CHECKING:  # pragma: no cover
    from src.agents.bird import Eagle

Cell = Tuple[int, int]


def chebyshev(a: Cell, b: Cell) -> int:
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


def deposit_territorial_presence(eagle: "Eagle", world: WorldMap, displaying: bool = False) -> None:
    """Un résident territorial marque visuellement son espace (dépôt accru lors d'une parade)."""
    if not eagle.is_territorial or eagle.nest_position is None:
        return
    soc = eagle.species_config.get("social", {})
    amount = float(
        soc.get("presence_deposit_display", 0.65)
        if displaying
        else soc.get("presence_deposit_resident", 0.35)
    )
    radius = 4 if displaying else 2
    y, x = eagle.position
    world.presence_layer.deposit(y, x, eagle.territory_id, amount, radius=radius)


def check_and_defend_territory(
    resident: "Eagle",
    all_eagles: List["Eagle"],
    world: WorldMap,
    expected_gain_map: np.ndarray,
    remaining_steps: int,
) -> Optional[Tuple["Eagle", Cell]]:
    """Modèle de Défendabilité Économique (Jerram Brown, 1964) :
    Le résident inspecte son rayon de vision. S'il voit un intrus (ni partenaire, ni jeune
    du couple) sur une case `c_intrus` dont la valeur trophique pour le nid
    (E[Gain](c_intrus) / Coût_aller_retour_nid) dépasse `defense_efficiency_threshold`,
    ET qu'il a le budget diurne et énergétique pour l'intercepter et rentrer au nid,
    il engage la poursuite et expulse l'intrus.
    """
    if not resident.is_territorial or resident.nest_position is None:
        return None

    soc = resident.species_config.get("social", {})
    min_satiety = float(soc.get("defense_min_satiety", 45.0))
    if resident.satiety < min_satiety:
        return None

    def_threshold = float(soc.get("defense_efficiency_threshold", 1.4))
    chase_cost_res = float(soc.get("chase_energy_cost_resident", 4.0))
    chase_cost_int = float(soc.get("chase_energy_cost_intruder", 8.0))
    push_dist = int(soc.get("expulsion_push_distance", 5))

    nest = resident.nest_position
    vis_r = resident.movement.vision_radius + 2  # vigilance accrue depuis les hauteurs

    for other in all_eagles:
        if not other.alive or other.agent_id == resident.agent_id:
            continue
        if other.agent_id == resident.partner_id:
            continue
        if other.parent_nest == nest and other.state == "JUVENILE_DEPENDANT":
            continue
        # Si c'est un prospecteur mature de sexe opposé et que le résident est célibataire :
        # pas d'agression, c'est un partenaire potentiel !
        if resident.partner_id is None and other.sex != resident.sex and other.is_sexually_mature_or_subadult and other.partner_id is None :
            continue

        d_to_intruder = chebyshev(resident.position, other.position)
        if d_to_intruder > vis_r:
            continue

        # Valeur économique de la case occupée par l'intrus pour le propriétaire du nid
        d_nest = max(1, chebyshev(nest, other.position))
        round_trip_cost = resident.hunt_attempt_cost + 2.0 * resident.active_step_cost * d_nest
        strategic_value = float(expected_gain_map[other.position]) / max(round_trip_cost, 1e-6)

        if strategic_value < def_threshold:
            continue  # Case trop pauvre ou trop lointaine : ne vaut pas l'énergie d'un conflit

        # Vérifie que le résident a le temps d'intercepter (1 pas d'approche) et de rentrer au nid
        step_pos = resident.movement.step_toward(resident.position, other.position)
        if chebyshev(step_pos, nest) > remaining_steps - 1:
            continue

        # Expulsion de l'intrus loin du nid
        dy = other.position[0] - nest[0]
        dx = other.position[1] - nest[1]
        if dy == 0 and dx == 0:
            dy, dx = 1, 1
        norm = max(abs(dy), abs(dx), 1)
        rows, cols = world.grid_size
        new_y = int(np.clip(other.position[0] + round(push_dist * dy / norm), 0, rows - 1))
        new_x = int(np.clip(other.position[1] + round(push_dist * dx / norm), 0, cols - 1))

        other._move_to((new_y, new_x))
        other.satiety = max(0.0, other.satiety - chase_cost_int)
        other.expelled_count += 1
        if other.satiety <= 0.0:
            other.alive = False

        resident.satiety = max(0.0, resident.satiety - chase_cost_res)
        resident.defense_count += 1
        world.presence_layer.deposit(step_pos[0], step_pos[1], resident.territory_id, 0.6, radius=3)
        return other, step_pos

    return None


def find_courtship_target_or_mate(
    prospector: "Eagle",
    all_eagles: List["Eagle"],
    world: WorldMap,
    expected_gain_map: np.ndarray,
    rng: np.random.Generator,
) -> Optional[Cell]:
    """Pour un `SUBADULTE_PROSPECTEUR` (ou adulte non fixé) :
    1. Cherche dans le rayon de balise (`display_beacon_radius`) un résident célibataire
       de sexe opposé (prioritairement en parade nuptiale).
    2. S'il est à <= 2 cases de ce résident, forme le couple (`partner_id`) et s'installe !
    3. Sinon, retourne la position de ce résident pour orienter son vol vers lui.
    4. S'il n'y a aucun célibataire disponible mais que le prospecteur est pleinement
       adulte (`age_days >= adult_maturity_age_days`), cherche une falaise libre riche.
    """
    if prospector.partner_id is not None:
        return None

    soc = prospector.species_config.get("social", {})
    beacon_r = int(soc.get("display_beacon_radius", 28))

    best_mate: Optional["Eagle"] = None
    best_score = -1.0

    for other in all_eagles:
        if not other.alive or other.agent_id == prospector.agent_id:
            continue
        if not other.is_territorial or other.nest_position is None:
            continue
        if other.partner_id is not None or other.sex == prospector.sex:
            continue

        dist = chebyshev(prospector.position, other.nest_position)
        effective_range = beacon_r if other.is_displaying else (beacon_r // 2)
        if dist > effective_range:
            continue

        # Évalue l'attractivité du partenaire (qualité du site + vigueur/parade - distance)
        signal_bonus = 1.5 if other.is_displaying else 1.0
        score = signal_bonus * (other.satiety / max(dist, 1))
        if score > best_score:
            best_score = score
            best_mate = other

    if best_mate is not None and best_mate.nest_position is not None:
        if chebyshev(prospector.position, best_mate.nest_position) <= 2:
            # Appariement réussi !
            form_pair(best_mate, prospector)
            return best_mate.nest_position
        return best_mate.nest_position

    # Si aucun partenaire célibataire n'est détecté, un prospecteur mature cherche une falaise libre
    # Si aucun partenaire célibataire n'est détecté, un prospecteur mature cherche une aire libre
    ont = prospector.species_config.get("ontogeny", {})
    if prospector.age_days >= int(ont.get("adult_maturity_age_days", 1095)):
        topo = world.get_topography()
        
        # Récupération dynamique des reliefs de nidification de l'espèce
        st_cfg = prospector.species_config.get("life_states", {}).get("ADULTE_TERRITORIAL", {})
        roost_topo = st_cfg.get("roost_topography", [3])
        
        valid_cells = np.argwhere(
            np.isin(topo, roost_topo) & (world.presence_layer.owner_id == 0)
        )
        if len(valid_cells) > 0:
            d_cliffs = np.maximum(
                np.abs(valid_cells[:, 0] - prospector.position[0]),
                np.abs(valid_cells[:, 1] - prospector.position[1]),
            )
            nearby = valid_cells[d_cliffs <= prospector.movement.vision_radius * 2]
            if len(nearby) > 0:
                idx = int(rng.integers(len(nearby)))
                target = (int(nearby[idx, 0]), int(nearby[idx, 1]))
                if prospector.position == target:
                    prospector.establish_territory(target)
                return target

    return None


def form_pair(resident: "Eagle", newcomer: "Eagle") -> None:
    """Lie deux aigles de sexe opposé en couple territorial sur l'aire du résident."""
    resident.partner_id = newcomer.agent_id
    newcomer.partner_id = resident.agent_id
    newcomer.state = "ADULTE_TERRITORIAL"
    newcomer.nest_position = resident.nest_position
    newcomer.territory_id = resident.territory_id
    newcomer._move_to(resident.nest_position)