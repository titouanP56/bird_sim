"""Module de télémétrie découplé (Pattern Observer) pour la simulation Bonelli-IBM.

Accumule les états journaliers et sous-étapes en structures Python natives légères
pendant l'exécution, puis compile des pandas.DataFrame typés (int16/float32/category)
pour l'analyse interactive sans fuite de mémoire.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

if TYPE_CHECKING:  # pragma: no cover
    from src.agents.behaviors.reproduction import BreedingNest
    from src.agents.bird import DayReport, Eagle
    from src.environment.map import WorldMap

Cell = Tuple[int, int]


@dataclass
class CompiledTelemetry:
    """Conteneur immuable des DataFrames optimisés et matrices environnementales."""

    daily_df: pd.DataFrame
    substeps_df: pd.DataFrame
    captures_df: pd.DataFrame
    ontogeny_df: pd.DataFrame
    pairing_df: pd.DataFrame
    defense_events_df: pd.DataFrame
    repro_events_df: pd.DataFrame
    agent_metadata: Dict[int, Dict[str, Any]]
    topography_names: Dict[int, str]
    topography_colors: Dict[int, str]
    elevation_grid: np.ndarray
    topography_grid: np.ndarray
    vegetation_grid: np.ndarray
    thermal_uplift_grid: np.ndarray
    final_fear_grid: np.ndarray
    mean_fear_grid: np.ndarray
    final_presence_grid: np.ndarray
    final_owner_grid: np.ndarray
    prey_grids: Dict[str, np.ndarray]
    grid_size: Tuple[int, int]
    cell_size_km: float
    seed: int
    n_days_simulated: int


class TelemetryLogger:
    """Observateur passif du moteur de simulation.

    Stocke les observations jour par jour dans des listes de dictionnaires plats
    et génère un objet `CompiledTelemetry` à la fin du run.
    """

    def __init__(self) -> None:
        self._daily_records: List[Dict[str, Any]] = []
        self._substep_records: List[Dict[str, Any]] = []
        self._capture_records: List[Dict[str, Any]] = []
        self._defense_records: List[Dict[str, Any]] = []
        self._agent_meta: Dict[int, Dict[str, Any]] = {}
        self._prev_defense_counts: Dict[int, int] = {}
        self._prev_expelled_counts: Dict[int, int] = {}

        self._fear_accumulator: Optional[np.ndarray] = None
        self._fear_days_count: int = 0
        self._seed: int = 42
        self._last_day: int = 0
        self.compiled: Optional[CompiledTelemetry] = None

    def on_simulation_start(
        self,
        world: "WorldMap",
        eagles: List["Eagle"],
        seed: Optional[int],
    ) -> None:
        """Initialise les tampons de télémétrie avant le premier pas de temps.

        Args:
            world: Instance de la carte contenant les couches statiques et dynamiques.
            eagles: Liste initiale des agents fondateurs.
            seed: Graine aléatoire utilisée pour la simulation.
        """
        assert world is not None, "WorldMap ne peut pas être None."
        self._fear_accumulator = np.zeros(world.grid_size, dtype=np.float64)
        self._fear_days_count = 0
        self._seed = int(seed if seed is not None else (world.seed or 42))

        for eagle in eagles:
            self._register_or_update_agent_meta(eagle, spawn_day=1)

    def _register_or_update_agent_meta(self, eagle: "Eagle", spawn_day: int) -> None:
        """Enregistre ou met à jour les métadonnées descriptives d'un aigle."""
        if eagle.agent_id not in self._agent_meta:
            self._agent_meta[eagle.agent_id] = {
                "agent_id": int(eagle.agent_id),
                "sex": str(eagle.sex),
                "spawn_day": int(spawn_day),
                "initial_state": str(eagle.state),
                "initial_age_days": int(eagle.age_days),
                "nest_position": eagle.nest_position,
                "parent_nest": eagle.parent_nest,
                "label": f"Aigle #{eagle.agent_id} ({eagle.sex})",
            }
            self._prev_defense_counts[eagle.agent_id] = int(eagle.defense_count)
            self._prev_expelled_counts[eagle.agent_id] = int(eagle.expelled_count)
        else:
            if eagle.nest_position is not None:
                self._agent_meta[eagle.agent_id]["nest_position"] = eagle.nest_position

    def log_step(
        self,
        day: int,
        world: "WorldMap",
        eagles: List["Eagle"],
        daily_reports: Dict[int, Tuple[Cell, "DayReport"]],
        breeding_nests: Dict[Tuple[int, int], "BreedingNest"],
    ) -> None:
        """Capture l'état de tous les agents vivants à la fin du jour `day`.

        Args:
            day: Jour courant de la simulation (1..N).
            world: Carte du monde mise à jour après l'action des agents.
            eagles: Liste complète des aigles (fondateurs + jeunes émancipés).
            daily_reports: Dictionnaire {agent_id: (position_depart, DayReport)}.
            breeding_nests: Dictionnaire des aires de reproduction actives.
        """
        assert day >= 1, f"Le jour de simulation doit être >= 1 (reçu: {day})."
        self._last_day = day

        if self._fear_accumulator is not None:
            self._fear_accumulator += world.fear_layer.fear
            self._fear_days_count += 1

        topo_grid = world.get_topography()
        eagle_by_id: Dict[int, "Eagle"] = {e.agent_id: e for e in eagles}

        for eagle in eagles:
            self._register_or_update_agent_meta(eagle, spawn_day=day)

            if eagle.agent_id not in daily_reports:
                continue

            start_cell, report = daily_reports[eagle.agent_id]
            substeps = report.substeps
            end_cell = substeps[-1] if substeps else start_cell

            # Calcul de la distance au partenaire (en norme de Chebyshev et Euclidienne km)
            partner_dist_km: float = np.nan
            partner_id_val: int = int(eagle.partner_id) if eagle.partner_id is not None else -1
            if eagle.partner_id is not None and eagle.partner_id in eagle_by_id:
                partner = eagle_by_id[eagle.partner_id]
                if partner.alive:
                    dy = float(end_cell[0] - partner.position[0])
                    dx = float(end_cell[1] - partner.position[1])
                    partner_dist_km = float(np.hypot(dy, dx) * world.cell_size_km)

            # Enregistrement des sous-étapes spatiales et comptage par habitat topographique
            path_cells = [start_cell] + list(substeps)
            step_path_arr = np.asarray(path_cells, dtype=np.int32)
            daily_dist_cells = float(
                np.linalg.norm(np.diff(step_path_arr, axis=0), axis=1).sum()
            )

            for step_idx, cell in enumerate(substeps):
                r, c = int(cell[0]), int(cell[1])
                topo_id = int(topo_grid[r, c])
                self._substep_records.append(
                    {
                        "day": int(day),
                        "substep": int(step_idx + 1),
                        "agent_id": int(eagle.agent_id),
                        "row": r,
                        "col": c,
                        "topo_id": topo_id,
                        "mode": str(report.mode),
                        "is_hunt_habitat": bool(report.mode == "CHASSE_ACTIVE"),
                    }
                )

            # Détection des événements de défense territoriale ou d'expulsion survenus ce jour
            prev_def = self._prev_defense_counts.get(eagle.agent_id, 0)
            if eagle.defense_count > prev_def:
                self._defense_records.append(
                    {
                        "day": int(day),
                        "agent_id": int(eagle.agent_id),
                        "event_type": "DEFENSE_GAGNEE",
                        "row": int(end_cell[0]),
                        "col": int(end_cell[1]),
                        "count_delta": int(eagle.defense_count - prev_def),
                    }
                )
            self._prev_defense_counts[eagle.agent_id] = int(eagle.defense_count)

            prev_exp = self._prev_expelled_counts.get(eagle.agent_id, 0)
            if eagle.expelled_count > prev_exp:
                self._defense_records.append(
                    {
                        "day": int(day),
                        "agent_id": int(eagle.agent_id),
                        "event_type": "EXPULSION_SUBIE",
                        "row": int(end_cell[0]),
                        "col": int(end_cell[1]),
                        "count_delta": int(eagle.expelled_count - prev_exp),
                    }
                )
            self._prev_expelled_counts[eagle.agent_id] = int(eagle.expelled_count)

            # Enregistrement d'une capture éventuelle
            if report.captured is not None:
                self._capture_records.append(
                    {
                        "day": int(day),
                        "agent_id": int(eagle.agent_id),
                        "prey_species": str(report.captured),
                        "row": int(end_cell[0]),
                        "col": int(end_cell[1]),
                        "topo_id": int(topo_grid[int(end_cell[0]), int(end_cell[1])]),
                    }
                )

            # Bilan journalier de l'individu
            self._daily_records.append(
                {
                    "day": int(day),
                    "agent_id": int(eagle.agent_id),
                    "age_days": int(eagle.age_days),
                    "state": str(report.state),
                    "mode": str(report.mode),
                    "satiety_start": float(report.satiety_start),
                    "satiety_peak": float(report.satiety_peak),
                    "satiety_end": float(report.satiety_end),
                    "energy_cost": float(report.cost),
                    "attempts": int(report.attempts),
                    "captured_bool": int(1 if report.captured is not None else 0),
                    "captured_species": str(report.captured) if report.captured else "Aucune",
                    "moves": int(report.moves),
                    "distance_km": float(daily_dist_cells * world.cell_size_km),
                    "row": int(end_cell[0]),
                    "col": int(end_cell[1]),
                    "partner_id": partner_id_val,
                    "partner_dist_km": partner_dist_km,
                    "alive": bool(report.alive),
                }
            )

    @staticmethod
    def compute_thermal_orographic_layer(world: "WorldMap") -> np.ndarray:
        """Calcule l'indice d'ascendance thermique et orographique dans [0, 1].

        En accord avec la physique du modèle :
        1. Effet orographique : portance mécanique maximale le long des ruptures de pente
           et falaises (topographie = 3 et fort gradient `slope`).
        2. Effet thermique : réchauffement différentiel accru sur les pentes exposées au Sud
           (Adret : `gy < 0` dans la convention Nord=0 -> Sud=49) et les milieux ouverts.

        Args:
            world: Instance de WorldMap.

        Returns:
            Matrice numpy 2D (float32) normalisée dans [0, 1].
        """
        elev = world.get_elevation()
        topo = world.get_topography()
        veg = world.get_vegetation()

        if elev is None:
            return (topo == 3).astype(np.float32)

        gy, gx = np.gradient(elev)
        slope = np.hypot(gx, gy)
        max_slope = float(slope.max()) if slope.max() > 0 else 1.0
        orographic_lift = np.clip(slope / max_slope, 0.0, 1.0)
        cliff_bonus = np.where(topo == 3, 0.35, 0.0)

        # Exposition Sud (Adret) : gy > 0 quand l'altitude descend du Nord vers le Sud
        south_aspect = np.clip(np.tanh(gy / 0.04), -1.0, 1.0)
        albedo_openness = 1.0 - 0.5 * veg
        thermal_lift = np.clip(0.5 * (south_aspect + 1.0) * albedo_openness, 0.0, 1.0)

        combined = np.clip(0.55 * orographic_lift + 0.30 * thermal_lift + cliff_bonus, 0.0, 1.0)
        return combined.astype(np.float32)

    def finalize(
        self,
        world: "WorldMap",
        breeding_nests: Dict[Tuple[int, int], "BreedingNest"],
        social_events: List[Tuple[int, str]],
    ) -> CompiledTelemetry:
        """Compile les listes de dictionnaires en DataFrames Pandas à empreinte mémoire réduite.

        Args:
            world: Carte du monde à l'état final.
            breeding_nests: Dictionnaire des nids reproducteurs pour extraire les événements.
            social_events: Journal global des événements sociaux.

        Returns:
            Instance de `CompiledTelemetry` prête pour le Dashboard NiceGUI.
        """
        # 1. DataFrame journalier optimisé
        if self._daily_records:
            daily_df = pd.DataFrame.from_records(self._daily_records)
            daily_df["day"] = daily_df["day"].astype("int16")
            daily_df["agent_id"] = daily_df["agent_id"].astype("int16")
            daily_df["age_days"] = daily_df["age_days"].astype("int32")
            daily_df["state"] = daily_df["state"].astype("category")
            daily_df["mode"] = daily_df["mode"].astype("category")
            for col_f in ("satiety_start", "satiety_peak", "satiety_end", "energy_cost", "distance_km", "partner_dist_km"):
                daily_df[col_f] = daily_df[col_f].astype("float32")
            for col_i in ("attempts", "captured_bool", "moves", "row", "col", "partner_id"):
                daily_df[col_i] = daily_df[col_i].astype("int16")
            daily_df["captured_species"] = daily_df["captured_species"].astype("category")
        else:
            daily_df = pd.DataFrame()

        # 2. DataFrame des sous-étapes spatiales
        if self._substep_records:
            substeps_df = pd.DataFrame.from_records(self._substep_records)
            substeps_df["day"] = substeps_df["day"].astype("int16")
            substeps_df["substep"] = substeps_df["substep"].astype("int8")
            substeps_df["agent_id"] = substeps_df["agent_id"].astype("int16")
            substeps_df["row"] = substeps_df["row"].astype("int16")
            substeps_df["col"] = substeps_df["col"].astype("int16")
            substeps_df["topo_id"] = substeps_df["topo_id"].astype("int8")
            substeps_df["mode"] = substeps_df["mode"].astype("category")
        else:
            substeps_df = pd.DataFrame()

        # 3. DataFrame des captures
        if self._capture_records:
            captures_df = pd.DataFrame.from_records(self._capture_records)
            captures_df["day"] = captures_df["day"].astype("int16")
            captures_df["agent_id"] = captures_df["agent_id"].astype("int16")
            captures_df["prey_species"] = captures_df["prey_species"].astype("category")
            captures_df["row"] = captures_df["row"].astype("int16")
            captures_df["col"] = captures_df["col"].astype("int16")
            captures_df["topo_id"] = captures_df["topo_id"].astype("int8")
        else:
            captures_df = pd.DataFrame(
                columns=["day", "agent_id", "prey_species", "row", "col", "topo_id"]
            )

        # 4. DataFrames d'ontogénie et d'appariement (Gantt Charts)
        ontogeny_df = self._build_intervals_df(daily_df, group_col="state")
        pairing_df = self._build_pairing_intervals_df(daily_df)

        # 5. DataFrame des événements de défense territoriale
        if self._defense_records:
            defense_events_df = pd.DataFrame.from_records(self._defense_records)
            defense_events_df["day"] = defense_events_df["day"].astype("int16")
            defense_events_df["agent_id"] = defense_events_df["agent_id"].astype("int16")
            defense_events_df["event_type"] = defense_events_df["event_type"].astype("category")
        else:
            defense_events_df = pd.DataFrame(
                columns=["day", "agent_id", "event_type", "row", "col", "count_delta"]
            )

        # 6. Événements reproducteurs des nids (Ponte, Éclosion, Envol, Émancipation)
        repro_rows: List[Dict[str, Any]] = []
        for pair_key, bnest in breeding_nests.items():
            for ev_day, ev_text in bnest.events_log:
                repro_rows.append(
                    {
                        "day": int(ev_day),
                        "female_id": int(bnest.female_id),
                        "male_id": int(bnest.male_id),
                        "nest_row": int(bnest.nest_position[0]),
                        "nest_col": int(bnest.nest_position[1]),
                        "event": str(ev_text),
                    }
                )
        repro_events_df = pd.DataFrame.from_records(repro_rows) if repro_rows else pd.DataFrame(
            columns=["day", "female_id", "male_id", "nest_row", "nest_col", "event"]
        )

        # Extraction des métadonnées topographiques et matrices environnementales
        topo_types_cfg = world.topography_types
        topo_names = {tid: str(cfg.get("name", f"Relief {tid}")) for tid, cfg in topo_types_cfg.items()}
        topo_colors = {tid: str(cfg.get("color", "#888888")) for tid, cfg in topo_types_cfg.items()}

        mean_fear = (
            (self._fear_accumulator / max(self._fear_days_count, 1)).astype(np.float32)
            if self._fear_accumulator is not None
            else world.fear_layer.fear.astype(np.float32)
        )
        prey_grids = {
            sp: world.get_prey_density(sp).astype(np.float32).copy()
            for sp in world.prey_names
        }

        self.compiled = CompiledTelemetry(
            daily_df=daily_df,
            substeps_df=substeps_df,
            captures_df=captures_df,
            ontogeny_df=ontogeny_df,
            pairing_df=pairing_df,
            defense_events_df=defense_events_df,
            repro_events_df=repro_events_df,
            agent_metadata=self._agent_meta,
            topography_names=topo_names,
            topography_colors=topo_colors,
            elevation_grid=world.get_elevation().astype(np.float32).copy(),
            topography_grid=world.get_topography().astype(np.int16).copy(),
            vegetation_grid=world.get_vegetation().astype(np.float32).copy(),
            thermal_uplift_grid=self.compute_thermal_orographic_layer(world),
            final_fear_grid=world.fear_layer.fear.astype(np.float32).copy(),
            mean_fear_grid=mean_fear,
            final_presence_grid=world.presence_layer.presence.astype(np.float32).copy(),
            final_owner_grid=world.presence_layer.owner_id.astype(np.int16).copy(),
            prey_grids=prey_grids,
            grid_size=world.grid_size,
            cell_size_km=world.cell_size_km,
            seed=self._seed,
            n_days_simulated=self._last_day,
        )

        # Libération immédiate des tampons bruts pour minimiser la RAM
        self._daily_records.clear()
        self._substep_records.clear()
        self._capture_records.clear()
        self._defense_records.clear()

        return self.compiled

    @staticmethod
    def _build_intervals_df(daily_df: pd.DataFrame, group_col: str) -> pd.DataFrame:
        """Agrège une série journalière d'états en intervalles [start_day, end_day] pour Gantt."""
        if daily_df.empty:
            return pd.DataFrame(columns=["agent_id", "label", "start_day", "end_day", "duration_days"])

        intervals: List[Dict[str, Any]] = []
        for agent_id, group in daily_df.groupby("agent_id", observed=True):
            sorted_g = group.sort_values("day")
            vals = sorted_g[group_col].astype(str).to_numpy()
            days = sorted_g["day"].to_numpy()
            if len(days) == 0:
                continue

            start_d = int(days[0])
            curr_val = vals[0]
            prev_d = int(days[0])

            for d, v in zip(days[1:], vals[1:]):
                if v != curr_val or int(d) > prev_d + 1:
                    intervals.append(
                        {
                            "agent_id": int(agent_id),
                            "label": str(curr_val),
                            "start_day": start_d,
                            "end_day": prev_d,
                            "duration_days": prev_d - start_d + 1,
                        }
                    )
                    start_d = int(d)
                    curr_val = v
                prev_d = int(d)

            intervals.append(
                {
                    "agent_id": int(agent_id),
                    "label": str(curr_val),
                    "start_day": start_d,
                    "end_day": prev_d,
                    "duration_days": prev_d - start_d + 1,
                }
            )
        return pd.DataFrame.from_records(intervals)

    @staticmethod
    def _build_pairing_intervals_df(daily_df: pd.DataFrame) -> pd.DataFrame:
        """Extrait les intervalles temporels passés en couple avec chaque partenaire."""
        if daily_df.empty:
            return pd.DataFrame(
                columns=["agent_id", "partner_id", "partner_label", "start_day", "end_day", "duration_days"]
            )

        paired = daily_df[daily_df["partner_id"] > 0]
        if paired.empty:
            return pd.DataFrame(
                columns=["agent_id", "partner_id", "partner_label", "start_day", "end_day", "duration_days"]
            )

        intervals: List[Dict[str, Any]] = []
        for (agent_id, partner_id), group in paired.groupby(["agent_id", "partner_id"], observed=True):
            days = group.sort_values("day")["day"].to_numpy()
            if len(days) == 0:
                continue
            start_d = int(days[0])
            prev_d = int(days[0])
            for d in days[1:]:
                if int(d) > prev_d + 1:
                    intervals.append(
                        {
                            "agent_id": int(agent_id),
                            "partner_id": int(partner_id),
                            "partner_label": f"En couple avec Aigle #{int(partner_id)}",
                            "start_day": start_d,
                            "end_day": prev_d,
                            "duration_days": prev_d - start_d + 1,
                        }
                    )
                    start_d = int(d)
                prev_d = int(d)
            intervals.append(
                {
                    "agent_id": int(agent_id),
                    "partner_id": int(partner_id),
                    "partner_label": f"En couple avec Aigle #{int(partner_id)}",
                    "start_day": start_d,
                    "end_day": prev_d,
                    "duration_days": prev_d - start_d + 1,
                }
            )
        return pd.DataFrame.from_records(intervals)