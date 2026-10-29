"""Cycle annuel de reproduction : Ponte, Incubation, Élevage de la nichée et Émancipation."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

import numpy as np

if TYPE_CHECKING:  # pragma: no cover
    from src.agents.bird import Eagle

Cell = Tuple[int, int]

STAGE_NONE = "HORS_REPRO"
STAGE_COURTSHIP = "PARADE_NUPTIALE"
STAGE_INCUBATION = "INCUBATION"
STAGE_REARING = "ELEVAGE_POUSSINS"
STAGE_POST_FLEDGING = "POST_ENVOL"


@dataclass
class BreedingNest:
    """État reproducteur d'une aire occupée par un couple d'Aigles de Bonelli."""
    nest_position: Cell
    female_id: int
    male_id: int
    stage: str = STAGE_NONE
    days_in_stage: int = 0
    num_chicks: int = 0
    brood_satiety: float = 80.0
    last_Attempt_year: int = -1
    total_fledged: int = 0
    events_log: List[Tuple[int, str]] = field(default_factory=list)

    def step_reproduction_day(
        self,
        day: int,
        day_of_year: int,
        year: int,
        female: "Eagle",
        male: "Eagle",
        repro_cfg: Dict[str, Any],
        rng: np.random.Generator,
    ) -> int:
        """Avance d'un jour le cycle reproducteur du couple.
        Retourne le nombre de jeunes qui prennent leur envol / s'émancipent aujourd'hui.
        """
        if not (female.alive and male.alive):
            self.stage = STAGE_NONE
            self.num_chicks = 0
            return 0

        court_start = int(repro_cfg.get("courtship_start_doy", 15))
        lay_start = int(repro_cfg.get("laying_window_start_doy", 45))
        lay_end = int(repro_cfg.get("laying_window_end_doy", 85))
        min_sat = float(repro_cfg.get("min_satiety_to_lay", 65.0))
        inc_days = int(repro_cfg.get("incubation_days", 40))
        rear_days = int(repro_cfg.get("rearing_days", 65))
        post_days = int(repro_cfg.get("post_fledging_days", 35))
        chick_demand = float(repro_cfg.get("chick_daily_energy_demand", 14.0))

        # 1. Début d'année : entrée en parade nuptiale du couple
        if self.stage == STAGE_NONE and court_start <= day_of_year < lay_start:
            self.stage = STAGE_COURTSHIP
            self.days_in_stage = 0

        # 2. Fenêtre de ponte (Février - Mars)
        if self.stage in (STAGE_NONE, STAGE_COURTSHIP) and lay_start <= day_of_year <= lay_end:
            if self.last_Attempt_year < year and female.satiety >= min_sat and male.satiety >= 55.0:
                probs = repro_cfg.get("clutch_size_probs", [0.35, 0.65])
                self.num_chicks = int(rng.choice([1, 2], p=probs))
                self.stage = STAGE_INCUBATION
                self.days_in_stage = 0
                self.brood_satiety = float(repro_cfg.get("chick_Initial_satiety", 80.0))
                self.last_Attempt_year = year
                female.satiety = max(50.0, female.satiety - 10.0)
                self.events_log.append((day, f"Ponte ({self.num_chicks} oeuf(s))"))
                return 0
        elif self.stage == STAGE_COURTSHIP and day_of_year > lay_end:
            self.stage = STAGE_NONE

        # 3. Incubation : la femelle couve, les oeufs éclosent après `incubation_days`
        if self.stage == STAGE_INCUBATION:
            self.days_in_stage += 1
            if female.satiety < 20.0:
                # Abandon du nid si la femelle meurt de faim (le mâle n'a rien ramené)
                self.events_log.append((day, "Echec incubation (faim)"))
                self.stage = STAGE_NONE
                self.num_chicks = 0
                return 0
            if self.days_in_stage >= inc_days:
                self.stage = STAGE_REARING
                self.days_in_stage = 0
                self.brood_satiety = 85.0
                self.events_log.append((day, f"Eclosion ({self.num_chicks} poussin(s))"))
            return 0

        # 4. Élevage des poussins au nid + Phase post-envol
        if self.stage in (STAGE_REARING, STAGE_POST_FLEDGING):
            self.days_in_stage += 1
            total_demand = self.num_chicks * chick_demand
            self.brood_satiety = max(0.0, self.brood_satiety - total_demand)

            # Les parents transfèrent leur surplus de satiété aux jeunes au nid
            for parent in (female, male):
                if parent.satiety > 55.0 and self.brood_satiety < 95.0:
                    give = min(parent.satiety - 52.0, 100.0 - self.brood_satiety)
                    parent.satiety -= give
                    self.brood_satiety = min(100.0, self.brood_satiety + give * 1.15)

            if self.brood_satiety <= 0.0:
                if self.num_chicks > 1:
                    # Caïnisme / réduction de nichée en cas de disette : 1 seul poussin survit
                    self.num_chicks = 1
                    self.brood_satiety = 45.0
                    self.events_log.append((day, "Perte d'1 poussin (faim)"))
                else:
                    self.events_log.append((day, "Echec nichée (inanition)"))
                    self.num_chicks = 0
                    self.stage = STAGE_NONE
                    return 0

            if self.stage == STAGE_REARING and self.days_in_stage >= rear_days:
                self.stage = STAGE_POST_FLEDGING
                self.days_in_stage = 0
                self.events_log.append((day, f"Envol ({self.num_chicks} jeune(s))"))
                return 0

            if self.stage == STAGE_POST_FLEDGING and self.days_in_stage >= post_days:
                fledged = self.num_chicks
                self.total_fledged += fledged
                self.events_log.append((day, f"Emancipation ({fledged} jeune(s))"))
                self.num_chicks = 0
                self.stage = STAGE_NONE
                self.days_in_stage = 0
                return fledged

        return 0