"""Application Web Interactive NiceGUI & Plotly pour Bonelli-IBM.

Fournit deux routes :
- `/` : Configuration des paramètres de simulation, gestion de la Seed avec cache,
        exécution asynchrone non-bloquante et redirection automatique.
- `/results` : Analyse comparative multi-individus (Side-by-Side, axes X synchronisés)
               et inspection des couches environnementales (Heatmaps zoomables).
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from nicegui import app, run, ui
from plotly.subplots import make_subplots

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.agents.bird import ADULT, IMMATURE, STATE_LABELS, SUBADULT  # noqa: E402
from src.analytics.telemetry import CompiledTelemetry, TelemetryLogger  # noqa: E402
from src.engine.simulation import Simulation  # noqa: E402
from src.environment.map import WorldMap  # noqa: E402

DEFAULT_ENV_YAML = PROJECT_ROOT / "configs" / "environments" / "alpilles.yaml"
DEFAULT_SPECIES_YAML = PROJECT_ROOT / "configs" / "species" / "bonelli.yaml"

# Palette sombre cohérente avec l'esthétique scientifique du projet
PLOTLY_TEMPLATE = "plotly_dark"
PAPER_BG = "#14161c"
PLOT_BG = "#1b1e26"
ACCENT_GREEN = "#06d6a0"
ACCENT_RED = "#ef476f"
ACCENT_GOLD = "#ffd166"
ACCENT_BLUE = "#4cc9f0"

MODE_COLORS: Dict[str, str] = {
    "CHASSE_ACTIVE": "#ef476f",
    "REPOS_PATROUILLE": "#4cc9f0",
    "PARADE_NUPTIALE": "#ffd166",
    "INCUBATION_NID": "#b5e48c",
    "DEFENSE_TERRITOIRE": "#f4a261",
}

STATE_COLORS: Dict[str, str] = {
    "OEUF_INCUBATION": "#e0aaff",
    "JUVENILE_DEPENDANT": "#b5e48c",
    "IMMATURE_DISPERSION": "#4cc9f0",
    "SUBADULTE_PROSPECTEUR": "#ffd166",
    "ADULTE_TERRITORIAL": "#06d6a0",
}


class SimulationAppState:
    """État partagé en mémoire contenant la dernière télémétrie compilée."""

    def __init__(self) -> None:
        self.telemetry: Optional[CompiledTelemetry] = None
        self.is_running: bool = False


APP_STATE = SimulationAppState()


def _execute_simulation_sync(
    years: float,
    n_adults: int,
    n_immatures: int,
    n_subadults: int,
    seed: int,
) -> CompiledTelemetry:
    """Fonction pure exécutée dans un thread séparé (`run.io_bound` / `run.cpu_bound`).

    Args:
        years: Durée de la simulation en années.
        n_adults: Nombre d'adultes territoriaux initiaux.
        n_immatures: Nombre d'immatures en dispersion initiaux.
        n_subadults: Nombre de subadultes prospecteurs initiaux.
        seed: Graine aléatoire entière.

    Returns:
        Objet `CompiledTelemetry` contenant tous les DataFrames Pandas.
    """
    n_days = max(1, int(round(years * 365)))
    with open(DEFAULT_ENV_YAML, "r", encoding="utf-8") as f:
        import yaml
        env_cfg = yaml.safe_load(f)
    env_cfg["seed"] = int(seed)
    world = WorldMap(env_cfg)

    initial_specs: List[Dict[str, Any]] = []
    # Si configuration par défaut (1 adulte + 1 immature), conserve le scénario canonique F/M
    if n_adults == 1 and n_immatures == 1 and n_subadults == 0:
        initial_specs = [
            {"state": ADULT, "sex": "F", "age_days": 1460},
            {"state": IMMATURE, "sex": "M", "age_days": 650},
        ]
    else:
        idx = 0
        for _ in range(n_adults):
            initial_specs.append({"state": ADULT, "sex": "F" if idx % 2 == 0 else "M", "age_days": 1460})
            idx += 1
        for _ in range(n_subadults):
            initial_specs.append({"state": SUBADULT, "sex": "M" if idx % 2 == 0 else "F", "age_days": 850})
            idx += 1
        for _ in range(n_immatures):
            initial_specs.append({"state": IMMATURE, "sex": "M" if idx % 2 == 0 else "F", "age_days": 600})
            idx += 1

    if not initial_specs:
        initial_specs = [{"state": ADULT, "sex": "F", "age_days": 1460}]

    logger = TelemetryLogger()
    sim = Simulation(
        world=world,
        species_config=DEFAULT_SPECIES_YAML,
        n_days=n_days,
        seed=int(seed),
        initial_specs=initial_specs,
        telemetry=logger,
    )
    sim.run()
    assert logger.compiled is not None, "La compilation de la télémétrie a échoué."
    return logger.compiled


# =============================================================================
# Constructeurs de Graphiques Plotly (Individus & Environnement)
# =============================================================================

def _apply_dark_layout(fig: go.Figure, title: str, height: int = 380) -> go.Figure:
    """Applique un thème sombre uniforme à une figure Plotly."""
    fig.update_layout(
        template=PLOTLY_TEMPLATE,
        title=dict(text=title, font=dict(size=15, color="#e8e6e1")),
        paper_bgcolor=PAPER_BG,
        plot_bgcolor=PLOT_BG,
        height=height,
        margin=dict(l=45, r=25, t=55, b=40),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1.0),
    )
    return fig


def build_satiety_comparison_fig(telemetry: CompiledTelemetry, agent_ids: List[int]) -> go.Figure:
    """Construit les courbes de satiété côte-à-côte avec axes X et Y synchronisés."""
    n = max(1, len(agent_ids))
    titles = [telemetry.agent_metadata[aid]["label"] for aid in agent_ids]
    fig = make_subplots(
        rows=1,
        cols=n,
        shared_xaxes=True,
        shared_yaxes=True,
        subplot_titles=titles,
        horizontal_spacing=0.04,
    )
    df = telemetry.daily_df
    for idx, aid in enumerate(agent_ids, start=1):
        sub = df[df["agent_id"] == aid].sort_values("day")
        if sub.empty:
            continue
        fig.add_trace(
            go.Scatter(
                x=sub["day"],
                y=sub["satiety_end"],
                mode="lines",
                name=f"Satiété fin J (#{aid})",
                line=dict(color=ACCENT_GREEN, width=2),
                showlegend=(idx == 1),
            ),
            row=1,
            col=idx,
        )
        fig.add_trace(
            go.Scatter(
                x=sub["day"],
                y=sub["satiety_peak"],
                mode="lines",
                name="Pic journalier",
                line=dict(color=ACCENT_GOLD, width=1, dash="dot"),
                opacity=0.65,
                showlegend=(idx == 1),
            ),
            row=1,
            col=idx,
        )
        fig.add_hline(
            y=65.0,
            line_dash="dash",
            line_color=ACCENT_RED,
            annotation_text="Seuil Faim (65)" if idx == 1 else None,
            row=1,
            col=idx,
        )
        fig.update_xaxes(title_text="Jour de simulation", matches="x", row=1, col=idx)
        if idx == 1:
            fig.update_yaxes(title_text="Satiété S [0 - 100]", range=[0, 105], row=1, col=idx)

    return _apply_dark_layout(fig, "Évolution de la Satiété & Seuil Métabolique (Axes X Synchronisés)")


def build_attack_success_fig(telemetry: CompiledTelemetry, agent_ids: List[int]) -> go.Figure:
    """Construit le taux de réussite des attaques (moyenne glissante sur 14 jours) synchronisé en X."""
    n = max(1, len(agent_ids))
    titles = [telemetry.agent_metadata[aid]["label"] for aid in agent_ids]
    fig = make_subplots(
        rows=1,
        cols=n,
        shared_xaxes=True,
        shared_yaxes=True,
        subplot_titles=titles,
        horizontal_spacing=0.04,
    )
    df = telemetry.daily_df
    for idx, aid in enumerate(agent_ids, start=1):
        sub = df[df["agent_id"] == aid].sort_values("day").copy()
        if sub.empty:
            continue
        daily_rate = np.where(sub["attempts"] > 0, sub["captured_bool"] / sub["attempts"], np.nan)
        rolling_rate = (
            pd.Series(daily_rate, index=sub["day"])
            .rolling(window=14, min_periods=1)
            .mean()
            * 100.0
        )
        fig.add_trace(
            go.Scatter(
                x=sub["day"],
                y=rolling_rate,
                mode="lines",
                name="Taux réussite (moy. glissante 14j)",
                line=dict(color=ACCENT_BLUE, width=2.2),
                fill="tozeroy",
                fillcolor="rgba(76, 201, 240, 0.15)",
                showlegend=(idx == 1),
            ),
            row=1,
            col=idx,
        )
        fig.update_xaxes(title_text="Jour", matches="x", row=1, col=idx)
        if idx == 1:
            fig.update_yaxes(title_text="Réussite (%)", range=[0, 100], row=1, col=idx)

    return _apply_dark_layout(fig, "Taux de Réussite des Attaques (Moyenne Glissante 14 Jours)")


def build_prey_balance_fig(telemetry: CompiledTelemetry, agent_ids: List[int]) -> go.Figure:
    """Construit le bilan des proies capturées côte-à-côte par individu."""
    n = max(1, len(agent_ids))
    titles = [telemetry.agent_metadata[aid]["label"] for aid in agent_ids]
    fig = make_subplots(rows=1, cols=n, shared_yaxes=True, subplot_titles=titles, horizontal_spacing=0.05)

    cap_df = telemetry.captures_df
    all_species = sorted(list(telemetry.prey_grids.keys()))

    for idx, aid in enumerate(agent_ids, start=1):
        sub = cap_df[cap_df["agent_id"] == aid] if not cap_df.empty else pd.DataFrame()
        counts = sub["prey_species"].value_counts().to_dict() if not sub.empty else {}
        y_vals = [int(counts.get(sp, 0)) for sp in all_species]
        fig.add_trace(
            go.Bar(
                x=all_species,
                y=y_vals,
                text=y_vals,
                textposition="auto",
                marker_color=ACCENT_GOLD,
                name=f"Captures #{aid}",
                showlegend=False,
            ),
            row=1,
            col=idx,
        )
        fig.update_xaxes(title_text="Espèce proie", row=1, col=idx)
        if idx == 1:
            fig.update_yaxes(title_text="Nombre de captures", row=1, col=idx)

    return _apply_dark_layout(fig, "Bilan des Proies Capturées par Espèce", height=340)


def build_time_budget_fig(telemetry: CompiledTelemetry, agent_ids: List[int]) -> go.Figure:
    """Construit la répartition de l'emploi du temps (Chasse, Repos, Parade, Incubation, Défense)."""
    n = max(1, len(agent_ids))
    titles = [telemetry.agent_metadata[aid]["label"] for aid in agent_ids]
    specs = [[{"type": "domain"} for _ in range(n)]]
    fig = make_subplots(rows=1, cols=n, specs=specs, subplot_titles=titles)

    df = telemetry.daily_df
    for idx, aid in enumerate(agent_ids, start=1):
        sub = df[df["agent_id"] == aid]
        if sub.empty:
            continue
        vc = sub["mode"].value_counts()
        labels = [str(k) for k in vc.index]
        values = [int(v) for v in vc.values]
        colors = [MODE_COLORS.get(lbl, "#888888") for lbl in labels]
        fig.add_trace(
            go.Pie(
                labels=labels,
                values=values,
                hole=0.42,
                marker=dict(colors=colors),
                textinfo="percent+label",
            ),
            row=1,
            col=idx,
        )

    return _apply_dark_layout(fig, "Emploi du Temps Journalier (Ratio Chasse / Repos / Parade / Incubation)", height=360)


def build_spatial_displacement_fig(
    telemetry: CompiledTelemetry,
    agent_id: int,
    max_day: int,
) -> go.Figure:
    """Carte interactive des déplacements d'un individu sur fond topographique jusqu'au jour `max_day`."""
    fig = go.Figure()
    rows, cols = telemetry.grid_size

    # Fond topographique discret + courbes d'altitude
    fig.add_trace(
        go.Heatmap(
            z=telemetry.elevation_grid,
            colorscale="Earth",
            showscale=False,
            opacity=0.55,
            hoverinfo="skip",
            name="Altitude",
        )
    )

    sub_df = telemetry.substeps_df
    if not sub_df.empty:
        agent_steps = sub_df[(sub_df["agent_id"] == agent_id) & (sub_df["day"] <= max_day)]
        if not agent_steps.empty:
            fig.add_trace(
                go.Scatter(
                    x=agent_steps["col"],
                    y=agent_steps["row"],
                    mode="lines+markers",
                    line=dict(color="rgba(255, 255, 255, 0.35)", width=1.2),
                    marker=dict(
                        size=5,
                        color=agent_steps["day"],
                        colorscale="Turbo",
                        colorbar=dict(title="Jour", thickness=12),
                        showscale=True,
                    ),
                    text=[
                        f"Jour {d} (Pas {s}) - {m}"
                        for d, s, m in zip(agent_steps["day"], agent_steps["substep"], agent_steps["mode"])
                    ],
                    hoverinfo="text",
                    name="Trajectoire",
                )
            )
            # Marqueur de position courante au jour max_day
            last_pt = agent_steps.iloc[-1]
            fig.add_trace(
                go.Scatter(
                    x=[last_pt["col"]],
                    y=[last_pt["row"]],
                    mode="markers",
                    marker=dict(size=13, color=ACCENT_RED, symbol="star", line=dict(width=1.5, color="white")),
                    name=f"Position J{int(last_pt['day'])}",
                )
            )

    meta = telemetry.agent_metadata.get(agent_id, {})
    nest_pos = meta.get("nest_position")
    if nest_pos is not None:
        fig.add_trace(
            go.Scatter(
                x=[nest_pos[1]],
                y=[nest_pos[0]],
                mode="markers",
                marker=dict(size=14, color="#ffffff", symbol="hexagon", line=dict(width=2, color=ACCENT_RED)),
                name="Aire (Nid falaise)",
            )
        )

    fig.update_xaxes(title_text="Ouest -> Est (cellules)", range=[-0.5, cols - 0.5], constrain="domain")
    fig.update_yaxes(
        title_text="Nord -> Sud (cellules)",
        range=[rows - 0.5, -0.5],
        scaleanchor="x",
        scaleratio=1,
    )
    label = meta.get("label", f"Aigle #{agent_id}")
    return _apply_dark_layout(fig, f"Déplacements Cumulés (J1 à J{max_day}) — {label}", height=460)


def build_territory_defense_fig(telemetry: CompiledTelemetry, agent_id: int) -> go.Figure:
    """Carte du territoire (présence territoriale, contours, nid et événements de défense/expulsion)."""
    fig = go.Figure()
    rows, cols = telemetry.grid_size

    # Couche d'intensité de présence territoriale
    fig.add_trace(
        go.Heatmap(
            z=telemetry.final_presence_grid,
            colorscale="Viridis",
            zmin=0.0,
            zmax=1.0,
            colorbar=dict(title="Présence", thickness=12),
            opacity=0.80,
            name="Marquage territorial",
        )
    )

    # Contour du polygone territorial de l'individu (owner_id == agent_id)
    owner_mask = (telemetry.final_owner_grid == agent_id).astype(np.float32)
    if np.any(owner_mask > 0):
        fig.add_trace(
            go.Contour(
                z=owner_mask,
                contours=dict(start=0.5, end=0.5, size=1.0, coloring="none"),
                line=dict(color=ACCENT_GOLD, width=2.5, dash="solid"),
                showscale=False,
                name="Frontière Territoire",
            )
        )

    # Événements de défense et d'expulsion
    def_df = telemetry.defense_events_df
    if not def_df.empty:
        sub_def = def_df[def_df["agent_id"] == agent_id]
        won = sub_def[sub_def["event_type"] == "DEFENSE_GAGNEE"]
        if not won.empty:
            fig.add_trace(
                go.Scatter(
                    x=won["col"],
                    y=won["row"],
                    mode="markers",
                    marker=dict(size=11, color=ACCENT_GREEN, symbol="shield", line=dict(width=1, color="black")),
                    text=[f"Jour {d} : Interception intrus" for d in won["day"]],
                    name="Défense gagnée",
                )
            )
        exp = sub_def[sub_def["event_type"] == "EXPULSION_SUBIE"]
        if not exp.empty:
            fig.add_trace(
                go.Scatter(
                    x=exp["col"],
                    y=exp["row"],
                    mode="markers",
                    marker=dict(size=11, color=ACCENT_RED, symbol="x", line=dict(width=1, color="white")),
                    text=[f"Jour {d} : Expulsion subie" for d in exp["day"]],
                    name="Expulsion subie",
                )
            )

    meta = telemetry.agent_metadata.get(agent_id, {})
    nest_pos = meta.get("nest_position")
    if nest_pos is not None:
        fig.add_trace(
            go.Scatter(
                x=[nest_pos[1]],
                y=[nest_pos[0]],
                mode="markers",
                marker=dict(size=15, color="#ffffff", symbol="hexagon", line=dict(width=2.5, color=ACCENT_RED)),
                name="Nid",
            )
        )

    fig.update_xaxes(title_text="Ouest -> Est", range=[-0.5, cols - 0.5], constrain="domain")
    fig.update_yaxes(title_text="Nord -> Sud", range=[rows - 0.5, -0.5], scaleanchor="x", scaleratio=1)
    label = meta.get("label", f"Aigle #{agent_id}")
    return _apply_dark_layout(fig, f"Domaine Vital, Frontières & Défenses — {label}", height=440)


def build_hunting_habitats_fig(telemetry: CompiledTelemetry, agent_ids: List[int]) -> go.Figure:
    """Construit le diagramme en barres de fréquentation des habitats de chasse (Plaine, Plateau, Versant, Falaise)."""
    n = max(1, len(agent_ids))
    titles = [telemetry.agent_metadata[aid]["label"] for aid in agent_ids]
    fig = make_subplots(rows=1, cols=n, shared_yaxes=True, subplot_titles=titles, horizontal_spacing=0.05)

    sub_df = telemetry.substeps_df
    topo_ids = sorted(telemetry.topography_names.keys())
    topo_labels = [telemetry.topography_names[tid] for tid in topo_ids]
    topo_colors = [telemetry.topography_colors[tid] for tid in topo_ids]

    for idx, aid in enumerate(agent_ids, start=1):
        if not sub_df.empty:
            hunt_steps = sub_df[(sub_df["agent_id"] == aid) & (sub_df["is_hunt_habitat"])]
            if hunt_steps.empty:
                hunt_steps = sub_df[sub_df["agent_id"] == aid]
            vc = hunt_steps["topo_id"].value_counts(normalize=True).to_dict()
        else:
            vc = {}
        pcts = [float(vc.get(tid, 0.0)) * 100.0 for tid in topo_ids]
        fig.add_trace(
            go.Bar(
                x=topo_labels,
                y=pcts,
                marker_color=topo_colors,
                text=[f"{p:.1f}%" for p in pcts],
                textposition="auto",
                showlegend=False,
            ),
            row=1,
            col=idx,
        )
        fig.update_xaxes(title_text="Type de relief", row=1, col=idx)
        if idx == 1:
            fig.update_yaxes(title_text="Temps en chasse (%)", range=[0, 100], row=1, col=idx)

    return _apply_dark_layout(fig, "Habitats de Chasse Exploités (Plaine, Plateau, Versant, Falaise)", height=350)


def build_life_gantt_fig(telemetry: CompiledTelemetry, agent_ids: List[int]) -> go.Figure:
    """Timeline de vie (Gantt des stades : œuf, juvénile, immature, subadulte, adulte) et périodes en couple."""
    n = max(1, len(agent_ids))
    titles = [telemetry.agent_metadata[aid]["label"] for aid in agent_ids]
    fig = make_subplots(
        rows=1,
        cols=n,
        shared_xaxes=True,
        subplot_titles=titles,
        horizontal_spacing=0.05,
    )

    ont_df = telemetry.ontogeny_df
    pair_df = telemetry.pairing_df

    for idx, aid in enumerate(agent_ids, start=1):
        meta = telemetry.agent_metadata.get(aid, {})
        spawn_day = int(meta.get("spawn_day", 1))

        # Si l'individu est un jeune né durant la simulation (spawn_day > 105),
        # reconstitue ses phases pré-émancipation (Œuf ~40j + Poussin au nid ~100j)
        if spawn_day > 105 and meta.get("parent_nest") is not None:
            egg_start = max(1, spawn_day - 140)
            chick_start = max(1, spawn_day - 100)
            fig.add_trace(
                go.Bar(
                    x=[chick_start - egg_start],
                    y=["Stade Ontogénique"],
                    base=[egg_start],
                    orientation="h",
                    name="Œuf (Incubation)",
                    marker_color=STATE_COLORS["OEUF_INCUBATION"],
                    hovertemplate=f"Œuf: J{egg_start} à J{chick_start}<extra></extra>",
                    showlegend=(idx == 1),
                ),
                row=1,
                col=idx,
            )
            fig.add_trace(
                go.Bar(
                    x=[spawn_day - chick_start],
                    y=["Stade Ontogénique"],
                    base=[chick_start],
                    orientation="h",
                    name=STATE_LABELS.get("JUVENILE_DEPENDANT", "Juvénile au nid"),
                    marker_color=STATE_COLORS["JUVENILE_DEPENDANT"],
                    hovertemplate=f"Juvénile au nid: J{chick_start} à J{spawn_day}<extra></extra>",
                    showlegend=(idx == 1),
                ),
                row=1,
                col=idx,
            )

        # Stades de vie actifs observés
        sub_ont = ont_df[ont_df["agent_id"] == aid] if not ont_df.empty else pd.DataFrame()
        for _, row in sub_ont.iterrows():
            st_code = str(row["label"])
            st_display = STATE_LABELS.get(st_code, st_code)
            fig.add_trace(
                go.Bar(
                    x=[int(row["duration_days"])],
                    y=["Stade Ontogénique"],
                    base=[int(row["start_day"])],
                    orientation="h",
                    name=st_display,
                    marker_color=STATE_COLORS.get(st_code, ACCENT_BLUE),
                    hovertemplate=(
                        f"{st_display}<br>J{int(row['start_day'])} → J{int(row['end_day'])} "
                        f"({int(row['duration_days'])} j)<extra></extra>"
                    ),
                    showlegend=(idx == 1),
                ),
                row=1,
                col=idx,
            )

        # Intervalles de temps passés en couple superposés
        sub_pair = pair_df[pair_df["agent_id"] == aid] if not pair_df.empty else pd.DataFrame()
        for _, prow in sub_pair.iterrows():
            p_lbl = str(prow["partner_label"])
            fig.add_trace(
                go.Bar(
                    x=[int(prow["duration_days"])],
                    y=[p_lbl],
                    base=[int(prow["start_day"])],
                    orientation="h",
                    name=p_lbl,
                    marker_color=ACCENT_RED,
                    hovertemplate=(
                        f"{p_lbl}<br>J{int(prow['start_day'])} → J{int(prow['end_day'])} "
                        f"({int(prow['duration_days'])} j)<extra></extra>"
                    ),
                    showlegend=(idx == 1),
                ),
                row=1,
                col=idx,
            )

        fig.update_xaxes(title_text="Jour de simulation", matches="x", row=1, col=idx)

    fig.update_layout(barmode="overlay")
    return _apply_dark_layout(
        fig,
        "Timeline Ontogénique (Gantt) & Intervalles d'Appariement (Axes X Synchronisés)",
        height=320,
    )


def build_partner_distance_fig(telemetry: CompiledTelemetry, agent_ids: List[int]) -> go.Figure:
    """Courbe de distance moyenne au partenaire au cours du temps (axes X synchronisés)."""
    n = max(1, len(agent_ids))
    titles = [telemetry.agent_metadata[aid]["label"] for aid in agent_ids]
    fig = make_subplots(
        rows=1,
        cols=n,
        shared_xaxes=True,
        shared_yaxes=True,
        subplot_titles=titles,
        horizontal_spacing=0.04,
    )
    df = telemetry.daily_df
    for idx, aid in enumerate(agent_ids, start=1):
        sub = df[(df["agent_id"] == aid) & (df["partner_id"] > 0)].sort_values("day")
        if not sub.empty:
            rolling_dist = sub["partner_dist_km"].rolling(window=7, min_periods=1).mean()
            fig.add_trace(
                go.Scatter(
                    x=sub["day"],
                    y=sub["partner_dist_km"],
                    mode="lines",
                    name="Distance journalière (km)",
                    line=dict(color="rgba(255, 209, 102, 0.35)", width=1),
                    showlegend=(idx == 1),
                ),
                row=1,
                col=idx,
            )
            fig.add_trace(
                go.Scatter(
                    x=sub["day"],
                    y=rolling_dist,
                    mode="lines",
                    name="Moyenne glissante (7j)",
                    line=dict(color=ACCENT_GOLD, width=2.2),
                    showlegend=(idx == 1),
                ),
                row=1,
                col=idx,
            )
        fig.update_xaxes(title_text="Jour", matches="x", row=1, col=idx)
        if idx == 1:
            fig.update_yaxes(title_text="Distance au partenaire (km)", row=1, col=idx)

    return _apply_dark_layout(fig, "Distance Inter-Partenaires au sein du Couple (km)")


def build_environment_heatmap(
    matrix: np.ndarray,
    title: str,
    colorscale: str,
    colorbar_title: str,
    cell_size_km: float,
) -> go.Figure:
    """Génère une Heatmap Plotly Express zoomable pour une couche numpy 2D."""
    fig = px.imshow(
        matrix,
        color_continuous_scale=colorscale,
        origin="upper",
        aspect="equal",
        labels=dict(x="Ouest → Est (cellules)", y="Nord → Sud (cellules)", color=colorbar_title),
    )
    fig.update_traces(
        hovertemplate="Ligne (Y): %{y}<br>Colonne (X): %{x}<br>Valeur: %{z:.3f}<extra></extra>"
    )
    return _apply_dark_layout(
        fig,
        f"{title} (1 case = {cell_size_km * 1000:.0f}m)",
        height=460,
    )


# =============================================================================
# Pages NiceGUI : Route `/` (Setup) et Route `/results` (Dashboard)
# =============================================================================

@ui.page("/")
def index_page() -> None:
    """Page d'accueil : paramétrage de la simulation, gestion de la Seed et lancement asynchrone."""
    ui.colors(primary="#06d6a0", secondary="#4cc9f0", accent="#ffd166", dark="#14161c")
    ui.query("body").style(f"background-color: {PAPER_BG}; color: #e8e6e1;")

    last_seed = int(app.storage.user.get("last_seed", 42))
    use_random_seed_init = bool(app.storage.user.get("use_random_seed", False))

    with ui.column().classes("w-full max-w-3xl mx-auto p-8 gap-6"):
        with ui.row().classes("items-center gap-3"):
            ui.icon("flight", size="36px", color="primary")
            ui.label("Bonelli-IBM — Configuration & Lancement").classes("text-3xl font-bold")

        ui.markdown(
            "Simulation écologique mécaniciste **First Principles** de l'Aigle de Bonelli "
            "(*Aquila fasciata*) dans le massif des Alpilles."
        ).classes("text-gray-300")

        with ui.card().classes("w-full p-6 bg-[#1b1e26] border border-gray-700 rounded-xl gap-4"):
            ui.label("Paramètres Temporels & Démographiques").classes("text-xl font-semibold text-[#06d6a0]")

            with ui.grid(columns=2).classes("w-full gap-4"):
                years_input = ui.number(
                    label="Durée de la simulation (Années)",
                    value=3.0,
                    min=0.1,
                    max=15.0,
                    step=0.5,
                    format="%.1f",
                ).classes("w-full").props("dark outlined")

                adults_input = ui.number(
                    label="Adultes territoriaux initiaux",
                    value=1,
                    min=0,
                    max=10,
                    step=1,
                    format="%d",
                ).classes("w-full").props("dark outlined")

                immatures_input = ui.number(
                    label="Immatures en dispersion initiaux",
                    value=1,
                    min=0,
                    max=15,
                    step=1,
                    format="%d",
                ).classes("w-full").props("dark outlined")

                subadults_input = ui.number(
                    label="Subadultes prospecteurs initiaux",
                    value=0,
                    min=0,
                    max=10,
                    step=1,
                    format="%d",
                ).classes("w-full").props("dark outlined")

            ui.separator().classes("my-2 bg-gray-700")
            ui.label("Contrôle du Générateur Stochastique (Seed)").classes("text-xl font-semibold text-[#ffd166]")

            with ui.row().classes("w-full items-center gap-6"):
                random_seed_switch = ui.switch(
                    "Seed aléatoire",
                    value=use_random_seed_init,
                ).props("color=amber")

                seed_number_input = ui.number(
                    label="Valeur de la Seed (mémorisée en cache)",
                    value=last_seed,
                    min=1,
                    max=999_999_999,
                    step=1,
                    format="%d",
                ).classes("w-64").props("dark outlined")

                seed_number_input.bind_visibility_from(
                    random_seed_switch,
                    "value",
                    backward=lambda is_rand: not is_rand,
                )

            status_row = ui.row().classes("w-full items-center gap-3 mt-2")
            with status_row:
                spinner = ui.spinner("dots", size="lg", color="primary")
                spinner.visible = False
                status_label = ui.label("").classes("text-sm text-gray-300")

            async def on_launch_click() -> None:
                if APP_STATE.is_running:
                    return
                APP_STATE.is_running = True
                launch_btn.disable()
                spinner.visible = True

                is_random = bool(random_seed_switch.value)
                app.storage.user["use_random_seed"] = is_random

                if is_random:
                    chosen_seed = int(np.random.default_rng().integers(1, 100_000))
                else:
                    chosen_seed = int(seed_number_input.value or 42)
                    app.storage.user["last_seed"] = chosen_seed

                years_val = float(years_input.value or 3.0)
                n_ad = int(adults_input.value or 0)
                n_im = int(immatures_input.value or 0)
                n_sub = int(subadults_input.value or 0)

                if n_ad + n_im + n_sub <= 0:
                    ui.notify("Veuillez sélectionner au moins 1 individu initial.", type="warning")
                    APP_STATE.is_running = False
                    launch_btn.enable()
                    spinner.visible = False
                    return

                status_label.text = (
                    f"Simulation en cours ({int(round(years_val * 365))} jours, Seed={chosen_seed})..."
                )
                try:
                    compiled = await run.io_bound(
                        _execute_simulation_sync,
                        years_val,
                        n_ad,
                        n_im,
                        n_sub,
                        chosen_seed,
                    )
                    APP_STATE.telemetry = compiled
                    ui.notify("Simulation terminée avec succès ! Redirection...", type="positive")
                    await asyncio.sleep(0.2)
                    ui.navigate.to("/results")
                except Exception as exc:
                    ui.notify(f"Erreur durant la simulation : {exc}", type="negative")
                    status_label.text = f"Erreur : {exc}"
                finally:
                    APP_STATE.is_running = False
                    launch_btn.enable()
                    spinner.visible = False

            launch_btn = ui.button(
                "Lancer la simulation",
                icon="play_arrow",
                on_click=on_launch_click,
            ).classes("w-full py-3 mt-4 text-black font-bold bg-[#06d6a0]")


@ui.page("/results")
def results_page() -> None:
    """Page de résultats : Onglets Individus (Comparaison Side-by-Side) & Environnement (Heatmaps)."""
    ui.colors(primary="#06d6a0", secondary="#4cc9f0", accent="#ffd166", dark="#14161c")
    ui.query("body").style(f"background-color: {PAPER_BG}; color: #e8e6e1;")

    telemetry = APP_STATE.telemetry
    if telemetry is None or telemetry.daily_df.empty:
        with ui.column().classes("w-full max-w-xl mx-auto p-12 items-center gap-4"):
            ui.icon("warning", size="48px", color="warning")
            ui.label("Aucune donnée de simulation disponible en mémoire.").classes("text-xl font-bold")
            ui.button("Retour à la configuration (/)", on_click=lambda: ui.navigate.to("/")).props("color=primary")
        return

    # État local de l'interface /results
    all_agent_options: Dict[int, str] = {
        aid: meta["label"] for aid, meta in sorted(telemetry.agent_metadata.items())
    }
    default_selected = list(all_agent_options.keys())[:2]
    ui_state: Dict[str, Any] = {
        "selected_agents": default_selected,
        "active_category": "nutrition",  # "nutrition" | "spatial" | "social"
        "time_slider_day": int(telemetry.n_days_simulated),
    }

    # En-tête supérieur avec navigation par Tabs ("Individus" et "Environnement")
    with ui.header().classes("bg-[#1b1e26] border-b border-gray-700 items-center justify-between px-6 py-2"):
        with ui.row().classes("items-center gap-4"):
            ui.button(icon="arrow_back", on_click=lambda: ui.navigate.to("/")).props("flat round color=white")
            ui.label(
                f"Bonelli-IBM Analytics  |  {telemetry.n_days_simulated} jours  |  Seed {telemetry.seed}"
            ).classes("text-lg font-bold text-[#06d6a0]")

        with ui.tabs().classes("text-white") as main_tabs:
            tab_ind = ui.tab("individus", label="Individus", icon="pets")
            tab_env = ui.tab("environnement", label="Environnement", icon="terrain")

    # Barre latérale (Sidebar) pour naviguer entre les catégories de graphiques
    with ui.left_drawer(value=True).classes("bg-[#1b1e26] border-r border-gray-700 p-4 gap-3") as sidebar:
        ui.label("Catégories d'Analyse").classes("text-xs uppercase tracking-wider text-gray-400 font-bold")

        def select_category(cat_key: str) -> None:
            ui_state["active_category"] = cat_key
            main_tabs.set_value("individus")
            render_individuals_content.refresh()

        ui.button(
            "1. Nutrition & Énergie",
            icon="restaurant",
            on_click=lambda: select_category("nutrition"),
        ).classes("w-full justify-start").props("flat color=white")

        ui.button(
            "2. Spatial & Territoire",
            icon="map",
            on_click=lambda: select_category("spatial"),
        ).classes("w-full justify-start").props("flat color=white")

        ui.button(
            "3. Démographie & Social",
            icon="groups",
            on_click=lambda: select_category("social"),
        ).classes("w-full justify-start").props("flat color=white")

        ui.separator().classes("my-3 bg-gray-700")
        ui.label("Couches Environnement").classes("text-xs uppercase tracking-wider text-gray-400 font-bold")
        ui.button(
            "Heatmaps Biotope & Proies",
            icon="layers",
            on_click=lambda: main_tabs.set_value("environnement"),
        ).classes("w-full justify-start").props("flat color=amber")

    # Contenu principal piloté par les Tabs supérieurs
    with ui.tab_panels(main_tabs, value=tab_ind).classes("w-full bg-transparent p-4"):

        # =====================================================================
        # ONGLET 1 : INDIVIDUS (Comparaison Dynamique Side-by-Side)
        # =====================================================================
        with ui.tab_panel(tab_ind).classes("w-full gap-4 p-0"):
            with ui.card().classes("w-full p-4 bg-[#1b1e26] border border-gray-700 rounded-xl"):
                with ui.row().classes("w-full items-center justify-between gap-4"):
                    def on_agent_selection_change(e: Any) -> None:
                        vals = e.value if e.value else [list(all_agent_options.keys())[0]]
                        ui_state["selected_agents"] = [int(v) for v in vals]
                        render_individuals_content.refresh()

                    ui.select(
                        options=all_agent_options,
                        value=default_selected,
                        multiple=True,
                        label="Sélectionner 1 à N aigles à comparer (Side-by-Side)",
                        on_change=on_agent_selection_change,
                    ).classes("w-96").props("dark outlined use-chips")

                    with ui.row().classes("gap-2"):
                        ui.chip(
                            f"{len(all_agent_options)} individus suivis",
                            icon="info",
                            color="primary",
                        ).props("outline")

            @ui.refreshable
            def render_individuals_content() -> None:
                selected_ids: List[int] = sorted(ui_state["selected_agents"])
                if not selected_ids:
                    ui.label("Sélectionnez au moins un aigle dans le menu ci-dessus.").classes("text-gray-400")
                    return

                cat = ui_state["active_category"]

                # --- CATÉGORIE 1 : NUTRITION ---
                if cat == "nutrition":
                    ui.label("Catégorie Nutrition & Métabolisme Énergétique").classes(
                        "text-xl font-bold text-[#06d6a0] mt-2"
                    )
                    with ui.column().classes("w-full gap-4"):
                        fig_sat = build_satiety_comparison_fig(telemetry, selected_ids)
                        ui.plotly(fig_sat).classes("w-full rounded-xl overflow-hidden")

                        fig_att = build_attack_success_fig(telemetry, selected_ids)
                        ui.plotly(fig_att).classes("w-full rounded-xl overflow-hidden")

                        with ui.grid(columns=2).classes("w-full gap-4"):
                            fig_prey = build_prey_balance_fig(telemetry, selected_ids)
                            ui.plotly(fig_prey).classes("w-full rounded-xl overflow-hidden")

                            fig_budget = build_time_budget_fig(telemetry, selected_ids)
                            ui.plotly(fig_budget).classes("w-full rounded-xl overflow-hidden")

                # --- CATÉGORIE 2 : SPATIAL ---
                elif cat == "spatial":
                    ui.label("Catégorie Spatiale, Domaine Vital & Habitats de Chasse").classes(
                        "text-xl font-bold text-[#4cc9f0] mt-2"
                    )
                    with ui.card().classes("w-full p-4 bg-[#1b1e26] border border-gray-700 rounded-xl"):
                        with ui.row().classes("w-full items-center gap-6"):
                            ui.icon("schedule", color="secondary", size="24px")
                            day_label = ui.label(
                                f"Time Slider — Trajectoires cumulées jusqu'au Jour {ui_state['time_slider_day']}"
                            ).classes("font-semibold w-80")

                            def on_slider_change(e: Any) -> None:
                                ui_state["time_slider_day"] = int(e.value)
                                day_label.text = (
                                    f"Time Slider — Trajectoires cumulées jusqu'au Jour {int(e.value)}"
                                )
                                render_spatial_maps.refresh()

                            ui.slider(
                                min=1,
                                max=max(1, telemetry.n_days_simulated),
                                step=1,
                                value=ui_state["time_slider_day"],
                                on_change=on_slider_change,
                            ).classes("col-grow").props("label-always color=secondary")

                    @ui.refreshable
                    def render_spatial_maps() -> None:
                        n_cols = min(len(selected_ids), 3)
                        with ui.grid(columns=n_cols).classes("w-full gap-4"):
                            for aid in selected_ids:
                                fig_disp = build_spatial_displacement_fig(
                                    telemetry, aid, ui_state["time_slider_day"]
                                )
                                ui.plotly(fig_disp).classes("w-full rounded-xl overflow-hidden")

                        with ui.grid(columns=n_cols).classes("w-full gap-4 mt-2"):
                            for aid in selected_ids:
                                fig_terr = build_territory_defense_fig(telemetry, aid)
                                ui.plotly(fig_terr).classes("w-full rounded-xl overflow-hidden")

                    render_spatial_maps()

                    fig_hab = build_hunting_habitats_fig(telemetry, selected_ids)
                    ui.plotly(fig_hab).classes("w-full rounded-xl overflow-hidden mt-2")

                # --- CATÉGORIE 3 : DÉMOGRAPHIE & SOCIAL ---
                elif cat == "social":
                    ui.label("Catégorie Démographie, Ontogénie & Dynamique de Couple").classes(
                        "text-xl font-bold text-[#ffd166] mt-2"
                    )
                    with ui.column().classes("w-full gap-4"):
                        fig_gantt = build_life_gantt_fig(telemetry, selected_ids)
                        ui.plotly(fig_gantt).classes("w-full rounded-xl overflow-hidden")

                        fig_pdist = build_partner_distance_fig(telemetry, selected_ids)
                        ui.plotly(fig_pdist).classes("w-full rounded-xl overflow-hidden")

                        if not telemetry.repro_events_df.empty:
                            with ui.card().classes("w-full p-4 bg-[#1b1e26] border border-gray-700 rounded-xl"):
                                ui.label("Journal Phénologique des Nids Reproducteurs").classes(
                                    "text-md font-bold text-[#06d6a0] mb-2"
                                )
                                ui.table.from_pandas(telemetry.repro_events_df).classes("w-full").props("dark flat")

            render_individuals_content()

        # =====================================================================
        # ONGLET 2 : ENVIRONNEMENT (Heatmaps Plotly Zoomables)
        # =====================================================================
        with ui.tab_panel(tab_env).classes("w-full gap-4 p-0"):
            ui.label("Cartographie Interactive des Couches Environnementales (Zoom & Pan)").classes(
                "text-xl font-bold text-[#06d6a0]"
            )
            with ui.grid(columns=2).classes("w-full gap-4"):
                # 1. Ascendances thermiques & orographiques
                fig_therm = build_environment_heatmap(
                    telemetry.thermal_uplift_grid,
                    "Ascendances Thermiques & Orographiques (Adret / Falaises)",
                    "Turbo",
                    "Portance [0-1]",
                    telemetry.cell_size_km,
                )
                ui.plotly(fig_therm).classes("w-full rounded-xl overflow-hidden")

                # 2. Fear Layer (Effarouchement moyen des proies)
                fig_fear = build_environment_heatmap(
                    telemetry.mean_fear_grid,
                    "Fear Layer — Vigilance & Effarouchement Moyen des Proies",
                    "Magma",
                    "Peur [0-0.9]",
                    telemetry.cell_size_km,
                )
                ui.plotly(fig_fear).classes("w-full rounded-xl overflow-hidden")

            ui.label("Couches de Densité des Proies (État Final)").classes(
                "text-lg font-bold text-[#ffd166] mt-4"
            )
            with ui.grid(columns=2).classes("w-full gap-4"):
                for prey_name, prey_matrix in telemetry.prey_grids.items():
                    fig_prey_map = build_environment_heatmap(
                        prey_matrix,
                        f"Densité de Proies : {prey_name.capitalize()} (Total = {prey_matrix.sum():.0f} ind.)",
                        "YlOrRd",
                        "Ind. / case",
                        telemetry.cell_size_km,
                    )
                    ui.plotly(fig_prey_map).classes("w-full rounded-xl overflow-hidden")


def main() -> None:
    """Point d'entrée du serveur NiceGUI."""
    ui.run(
        title="Bonelli-IBM — Dashboard Analytique",
        storage_secret="bonelli-ibm-secret-key-2026",
        dark=True,
        reload=False,
        port=8080,
    )


if __name__ in {"__main__", "__mp_main__"}:
    main()