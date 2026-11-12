"""Application Web Interactive NiceGUI & Plotly pour Bonelli-IBM.

Direction Artistique : "Ciel, Vents & Calcaire des Alpilles" (Thème Clair & Nature)
- Bandeau supérieur en dégradé bleu ciel prolongé par de grandes vagues SVG aériennes.
- Frise verticale de tourbillons d'air / vents (blanc & crème) entre la sidebar et les graphes.
- Polices et titres en bleu marine profond (#1e3a5f) et gris ardoise (#475569).
- Fonds de cartes basés sur les vrais habitats topographiques (Plaine, Plateau, Versant, Falaise).
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
from scipy.ndimage import gaussian_filter

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.agents.bird import ADULT, IMMATURE, STATE_LABELS, SUBADULT  # noqa: E402
from src.analytics.telemetry import CompiledTelemetry, TelemetryLogger  # noqa: E402
from src.engine.simulation import Simulation  # noqa: E402
from src.environment.map import WorldMap  # noqa: E402

DEFAULT_ENV_YAML = PROJECT_ROOT / "configs" / "environments" / "alpilles.yaml"
DEFAULT_SPECIES_YAML = PROJECT_ROOT / "configs" / "species" / "bonelli.yaml"

# =============================================================================
# Direction Artistique : Palette "Nature, Ciel & Calcaire"
# =============================================================================
PLOTLY_TEMPLATE = "plotly_white"
PAGE_BG = "#f4f7f9"        # Fond général clair légèrement azuré/pierre
CARD_BG = "#ffffff"        # Fond blanc pur pour les cartes de graphiques
PLOT_BG = "#f8fafc"        # Fond intérieur des graphes très doux
SIDEBAR_BG = "#eef5fb"     # Bleu brume très clair pour la barre latérale
TEXT_NAVY = "#1e3a5f"      # Bleu marine profond (titres et valeurs clés)
TEXT_SLATE = "#475569"     # Gris ardoise (axes, sous-titres, labels)
GRID_COLOR = "#e2e8f0"     # Grille fine gris perle

# Couleurs de courbes et séries (harmonisées avec la DA)
NAVY_PRIMARY = "#1e3a5f"
SKY_ACCENT = "#0284c7"
TEAL_NATURE = "#0d9488"
OCHRE_STONE = "#d97706"
CORAL_ALERT = "#e11d48"
SLATE_MUTED = "#64748b"

MODE_LABELS_FR: Dict[str, str] = {
    "CHASSE_ACTIVE": "Chasse active",
    "REPOS_PATROUILLE": "Repos / Patrouille",
    "PARADE_NUPTIALE": "Parade nuptiale",
    "INCUBATION_NID": "Incubation au nid",
    "DEFENSE_TERRITOIRE": "Défense territoire",
}

MODE_COLORS: Dict[str, str] = {
    "Chasse active": "#1e3a5f",       # Bleu marine profond
    "Repos / Patrouille": "#38bdf8",  # Bleu ciel
    "Parade nuptiale": "#eab308",     # Ocre doré
    "Incubation au nid": "#10b981",   # Vert sauge
    "Défense territoire": "#f43f5e",  # Corail vif
}

STATE_COLORS: Dict[str, str] = {
    "OEUF_INCUBATION": "#93c5fd",
    "JUVENILE_DEPENDANT": "#38bdf8",
    "IMMATURE_DISPERSION": "#64748b",
    "SUBADULTE_PROSPECTEUR": "#d97706",
    "ADULTE_TERRITORIAL": "#1e3a5f",
}

REPRO_EVENT_STYLE: Dict[str, Dict[str, str]] = {
    "Ponte": {"color": "#0284c7", "dash": "dot"},
    "Éclosion": {"color": "#0d9488", "dash": "dash"},
    "Envol": {"color": "#d97706", "dash": "dashdot"},
    "Émancipation": {"color": "#1e3a5f", "dash": "solid"},
    "Perte / Échec": {"color": "#e11d48", "dash": "dot"},
}

# Décorations SVG : Grandes vagues bleu ciel & Frise verticale de tourbillons de vent crème
SKY_WAVES_SVG = """
<div style="width: 100%; overflow: hidden; line-height: 0; background: linear-gradient(180deg, #7dd3fc 0%, #bae6fd 55%, #f4f7f9 100%);">
    <svg viewBox="0 0 1440 100" preserveAspectRatio="none" style="width: 100%; height: 68px; display: block;">
        <path d="M0,35 C280,95 520,-15 840,45 C1120,95 1300,15 1440,40 L1440,100 L0,100 Z"
              fill="#e0f2fe" opacity="0.65"></path>
        <path d="M0,60 C360,5 720,105 1100,35 C1280,5 1380,50 1440,65 L1440,100 L0,100 Z"
              fill="#f4f7f9" opacity="1.0"></path>
    </svg>
</div>
"""

WIND_SWIRLS_SVG = """
<div style="width: 34px; height: 100%; min-height: 85vh; background: linear-gradient(90deg, #eef5fb 0%, #f4f7f9 100%);
            display: flex; flex-direction: column; align-items: center; justify-content: space-around;
            padding: 18px 0; user-select: none;">
    <svg width="28" height="720" viewBox="0 0 28 720" fill="none" xmlns="http://www.w3.org/2000/svg">
        <g stroke="#fffbeb" stroke-width="2.4" stroke-linecap="round">
            <path d="M4,40 C16,25 24,45 14,55 C6,62 2,50 10,45" />
            <path d="M6,95 Q22,80 12,115 T20,135" stroke="#fef3c7" />
            <path d="M3,175 C18,160 25,180 15,190 C7,198 4,185 12,180" />
            <path d="M8,240 C22,225 6,260 18,275" stroke="#fde68a" opacity="0.85" />
            <path d="M4,320 C16,305 24,325 14,335 C6,342 2,330 10,325" />
            <path d="M6,385 Q22,370 12,405 T20,425" stroke="#fef3c7" />
            <path d="M3,475 C18,460 25,480 15,490 C7,498 4,485 12,480" />
            <path d="M8,540 C22,525 6,560 18,575" stroke="#fde68a" opacity="0.85" />
            <path d="M4,620 C16,605 24,625 14,635 C6,642 2,630 10,625" />
            <path d="M6,675 Q22,660 12,695" stroke="#fef3c7" />
        </g>
        <g stroke="#bae6fd" stroke-width="1.2" stroke-linecap="round" opacity="0.65">
            <path d="M8,43 C17,30 22,47 14,54" />
            <path d="M7,178 C19,164 23,182 15,189" />
            <path d="M8,323 C17,310 22,327 14,334" />
            <path d="M7,478 C19,464 23,482 15,489" />
            <path d="M8,623 C17,610 22,627 14,634" />
        </g>
    </svg>
</div>
"""


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
    """Exécute la simulation dans un thread worker pour ne pas bloquer l'UI."""
    n_days = max(1, int(round(years * 365)))
    with open(DEFAULT_ENV_YAML, "r", encoding="utf-8") as f:
        import yaml
        env_cfg = yaml.safe_load(f)
    env_cfg["seed"] = int(seed)
    world = WorldMap(env_cfg)

    initial_specs: List[Dict[str, Any]] = []
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
# Helpers Esthétiques & Fond Topographique (Plaine, Plateau, Versant, Falaise)
# =============================================================================

def _apply_nature_layout(
    fig: go.Figure,
    title: str,
    height: int = 390,
    top_margin: int = 68,
    legend_bottom: bool = False,
) -> go.Figure:
    """Applique la Direction Artistique claire (bleu marine & gris ardoise) à une figure Plotly."""
    legend_cfg = (
        dict(
            orientation="h",
            yanchor="top",
            y=-0.16,
            xanchor="center",
            x=0.5,
            font=dict(color=TEXT_SLATE, size=11),
            bgcolor="rgba(255,255,255,0.85)",
        )
        if legend_bottom
        else dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1.0,
            font=dict(color=TEXT_SLATE, size=11),
            bgcolor="rgba(255,255,255,0.75)",
        )
    )

    fig.update_layout(
        template=PLOTLY_TEMPLATE,
        title=dict(
            text=f"<b>{title}</b>",
            font=dict(size=15, color=TEXT_NAVY, family="Inter, Segoe UI, sans-serif"),
            x=0.01,
            xanchor="left",
        ),
        font=dict(color=TEXT_SLATE, family="Inter, Segoe UI, sans-serif"),
        paper_bgcolor=CARD_BG,
        plot_bgcolor=PLOT_BG,
        height=height,
        margin=dict(l=50, r=28, t=top_margin, b=65 if legend_bottom else 45),
        legend=legend_cfg,
    )
    fig.update_xaxes(gridcolor=GRID_COLOR, zerolinecolor=GRID_COLOR, title_font=dict(color=TEXT_NAVY, size=12))
    fig.update_yaxes(gridcolor=GRID_COLOR, zerolinecolor=GRID_COLOR, title_font=dict(color=TEXT_NAVY, size=12))
    for ann in fig.layout.annotations:
        ann.font = dict(size=13, color=TEXT_NAVY, family="Inter, Segoe UI, sans-serif")
    return fig


def _add_topographic_base_layer(
    fig: go.Figure,
    telemetry: CompiledTelemetry,
    show_topo_colorbar: bool = False,
) -> None:
    """Ajoute le fond des habitats topographiques (Plaine, Plateau, Versant, Falaise) + courbes d'altitude."""
    topo_ids = sorted(telemetry.topography_names.keys())
    n_t = len(topo_ids)
    # Construction d'une colorscale discrète fidèle au YAML (Plaine, Plateau, Versant, Falaise)
    discrete_cscale = []
    for k, tid in enumerate(topo_ids):
        col = telemetry.topography_colors.get(tid, "#e6d8a8")
        lo, hi = k / n_t, (k + 1) / n_t
        discrete_cscale.append([lo, col])
        discrete_cscale.append([hi, col])

    custom_names = np.vectorize(lambda t: telemetry.topography_names.get(int(t), str(t)))(
        telemetry.topography_grid
    )

    fig.add_trace(
        go.Heatmap(
            z=telemetry.topography_grid,
            customdata=np.dstack([custom_names, telemetry.elevation_grid]),
            colorscale=discrete_cscale,
            zmin=-0.5,
            zmax=n_t - 0.5,
            showscale=show_topo_colorbar,
            colorbar=dict(
                title=dict(text="Relief", font=dict(color=TEXT_NAVY, size=11)),
                tickvals=topo_ids,
                ticktext=[telemetry.topography_names[i] for i in topo_ids],
                thickness=12,
                len=0.55,
                x=1.02,
                y=0.75,
            ),
            hovertemplate="Case (Y=%{y}, X=%{x})<br>Habitat : <b>%{customdata[0]}</b><br>Altitude norm. : %{customdata[1]:.2f}<extra></extra>",
            name="Topographie",
        )
    )

    # Courbes de niveau d'altitude (isolignes fines comme sur une carte IGN)
    fig.add_trace(
        go.Contour(
            z=telemetry.elevation_grid,
            contours=dict(coloring="none", showlabels=False),
            ncontours=8,
            line=dict(color="rgba(30, 58, 95, 0.28)", width=0.9),
            showscale=False,
            hoverinfo="skip",
            name="Isolignes d'altitude",
        )
    )


# =============================================================================
# Constructeurs de Graphiques Plotly
# =============================================================================

def build_satiety_comparison_fig(telemetry: CompiledTelemetry, agent_ids: List[int]) -> go.Figure:
    """Courbes de satiété côte-à-côte avec axes X et Y synchronisés."""
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
                name="Satiété fin de journée",
                line=dict(color=NAVY_PRIMARY, width=1.8),
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
                name="Pic après repas",
                line=dict(color=SKY_ACCENT, width=1.0, dash="dot"),
                opacity=0.65,
                showlegend=(idx == 1),
            ),
            row=1,
            col=idx,
        )
        fig.add_hline(
            y=65.0,
            line_dash="dash",
            line_color=CORAL_ALERT,
            annotation_text="Seuil Faim (65)" if idx == 1 else None,
            annotation_font_color=CORAL_ALERT,
            row=1,
            col=idx,
        )
        fig.update_xaxes(title_text="Jour de simulation", matches="x", row=1, col=idx)
        if idx == 1:
            fig.update_yaxes(title_text="Satiété S [0 - 100]", range=[0, 105], row=1, col=idx)

    return _apply_nature_layout(fig, "Évolution de la Satiété & Seuil Métabolique (Axes X Synchronisés)")


def build_attack_success_fig(
    telemetry: CompiledTelemetry,
    agent_ids: List[int],
    show_repro_events: bool = True,
) -> go.Figure:
    """Taux de réussite des attaques (moyenne glissante 14j) + option d'affichage des événements poussins."""
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
    repro_df = telemetry.repro_events_df
    added_legend_cats: set[str] = set()

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
                line=dict(color=SKY_ACCENT, width=2.2),
                fill="tozeroy",
                fillcolor="rgba(2, 132, 199, 0.14)",
                showlegend=(idx == 1),
            ),
            row=1,
            col=idx,
        )

        # Superposition optionnelle des événements reproducteurs (Ponte, Éclosion, Envol, Émancipation)
        if show_repro_events and not repro_df.empty:
            agent_repro = repro_df[(repro_df["female_id"] == aid) | (repro_df["male_id"] == aid)]
            for _, r_ev in agent_repro.iterrows():
                ev_day = int(r_ev["day"])
                cat = str(r_ev["category"])
                ev_label = str(r_ev["event"])
                style = REPRO_EVENT_STYLE.get(cat, {"color": SLATE_MUTED, "dash": "dot"})
                show_in_leg = cat not in added_legend_cats
                if show_in_leg:
                    added_legend_cats.add(cat)

                fig.add_trace(
                    go.Scatter(
                        x=[ev_day, ev_day],
                        y=[0, 100],
                        mode="lines+markers",
                        name=f"Événement : {cat}",
                        line=dict(color=style["color"], width=1.8, dash=style["dash"]),
                        marker=dict(size=6, color=style["color"], symbol="diamond"),
                        hovertemplate=f"<b>Jour {ev_day}</b><br>{ev_label}<extra></extra>",
                        showlegend=show_in_leg,
                    ),
                    row=1,
                    col=idx,
                )

        fig.update_xaxes(title_text="Jour de simulation", matches="x", row=1, col=idx)
        if idx == 1:
            fig.update_yaxes(title_text="Réussite (%)", range=[0, 103], row=1, col=idx)

    return _apply_nature_layout(
        fig,
        "Taux de Réussite des Attaques (Moyenne Glissante 14 Jours)",
        height=400,
    )


def build_prey_balance_fig(telemetry: CompiledTelemetry, agent_ids: List[int]) -> go.Figure:
    """Bilan des proies capturées côte-à-côte par individu."""
    n = max(1, len(agent_ids))
    titles = [telemetry.agent_metadata[aid]["label"] for aid in agent_ids]
    fig = make_subplots(rows=1, cols=n, shared_yaxes=True, subplot_titles=titles, horizontal_spacing=0.06)

    cap_df = telemetry.captures_df
    all_species = sorted(list(telemetry.prey_grids.keys()))
    bar_colors = [NAVY_PRIMARY, SKY_ACCENT, TEAL_NATURE, OCHRE_STONE]

    for idx, aid in enumerate(agent_ids, start=1):
        sub = cap_df[cap_df["agent_id"] == aid] if not cap_df.empty else pd.DataFrame()
        counts = sub["prey_species"].value_counts().to_dict() if not sub.empty else {}
        y_vals = [int(counts.get(sp, 0)) for sp in all_species]
        fig.add_trace(
            go.Bar(
                x=[sp.capitalize() for sp in all_species],
                y=y_vals,
                text=y_vals,
                textposition="outside",
                marker_color=bar_colors[: len(all_species)],
                name=f"Captures #{aid}",
                showlegend=False,
            ),
            row=1,
            col=idx,
        )
        fig.update_xaxes(title_text="Espèce proie", row=1, col=idx)
        if idx == 1:
            max_y = max(y_vals + [5]) * 1.2
            fig.update_yaxes(title_text="Nombre de captures", range=[0, max_y], row=1, col=idx)

    return _apply_nature_layout(fig, "Bilan des Proies Capturées par Espèce", height=380)


def build_time_budget_fig(telemetry: CompiledTelemetry, agent_ids: List[int]) -> go.Figure:
    """Répartition de l'emploi du temps avec légende basse sans collision sur le titre."""
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
        raw_codes = [str(k) for k in vc.index]
        clean_labels = [MODE_LABELS_FR.get(code, code) for code in raw_codes]
        values = [int(v) for v in vc.values]
        colors = [MODE_COLORS.get(lbl, SLATE_MUTED) for lbl in clean_labels]

        fig.add_trace(
            go.Pie(
                labels=clean_labels,
                values=values,
                hole=0.46,
                domain=dict(y=[0.08, 0.86]),
                marker=dict(colors=colors, line=dict(color="#ffffff", width=2)),
                textinfo="percent",
                textposition="inside",
                insidetextorientation="horizontal",
                hovertemplate="<b>%{label}</b><br>%{value} jours (%{percent})<extra></extra>",
                showlegend=(idx == 1),
            ),
            row=1,
            col=idx,
        )

    return _apply_nature_layout(
        fig,
        "Emploi du Temps Journalier (Chasse, Repos, Parade, Incubation)",
        height=400,
        top_margin=72,
        legend_bottom=True,
    )


def build_spatial_displacement_fig(
    telemetry: CompiledTelemetry,
    agent_id: int,
    max_day: int,
) -> go.Figure:
    """Carte interactive des déplacements sur le vrai fond topographique (Plaine, Plateau, Versant, Falaise)."""
    fig = go.Figure()
    rows, cols = telemetry.grid_size

    # 1. Fond topographique discret (Plaine, Plateau, Versant, Falaise) + Courbes de niveau
    _add_topographic_base_layer(fig, telemetry, show_topo_colorbar=True)

    # 2. Trajectoire et points de passage de l'aigle jusqu'au jour max_day
    sub_df = telemetry.substeps_df
    if not sub_df.empty:
        agent_steps = sub_df[(sub_df["agent_id"] == agent_id) & (sub_df["day"] <= max_day)]
        if not agent_steps.empty:
            fig.add_trace(
                go.Scatter(
                    x=agent_steps["col"],
                    y=agent_steps["row"],
                    mode="lines+markers",
                    line=dict(color="rgba(30, 58, 95, 0.45)", width=1.4),
                    marker=dict(
                        size=5.5,
                        color=agent_steps["day"],
                        colorscale="YlGnBu",
                        colorbar=dict(
                            title=dict(text="Jour", font=dict(color=TEXT_NAVY, size=11)),
                            thickness=12,
                            len=0.42,
                            x=1.02,
                            y=0.20,
                        ),
                        line=dict(width=0.6, color=TEXT_NAVY),
                        showscale=True,
                    ),
                    text=[
                        f"Jour {d} (Pas {s}) — {MODE_LABELS_FR.get(str(m), str(m))}"
                        for d, s, m in zip(agent_steps["day"], agent_steps["substep"], agent_steps["mode"])
                    ],
                    hoverinfo="text",
                    name="Déplacements",
                )
            )
            last_pt = agent_steps.iloc[-1]
            fig.add_trace(
                go.Scatter(
                    x=[last_pt["col"]],
                    y=[last_pt["row"]],
                    mode="markers",
                    marker=dict(size=13, color=CORAL_ALERT, symbol="star", line=dict(width=1.5, color="white")),
                    name=f"Position J{int(last_pt['day'])}",
                )
            )

    meta = telemetry.agent_metadata.get(agent_id, {})
    nest_pos = meta.get("nest_position") or meta.get("parent_nest")
    if nest_pos is not None:
        fig.add_trace(
            go.Scatter(
                x=[nest_pos[1]],
                y=[nest_pos[0]],
                mode="markers",
                marker=dict(size=14, color="#ffffff", symbol="hexagon", line=dict(width=2.5, color=NAVY_PRIMARY)),
                name="Aire (Nid falaise)",
            )
        )

    fig.update_xaxes(title_text="Ouest → Est (cellules)", range=[-0.5, cols - 0.5], constrain="domain")
    fig.update_yaxes(
        title_text="Nord → Sud (cellules)",
        range=[rows - 0.5, -0.5],
        scaleanchor="x",
        scaleratio=1,
    )
    label = meta.get("label", f"Aigle #{agent_id}")
    return _apply_nature_layout(
        fig,
        f"Déplacements sur Topographie (J1 à J{max_day}) — {label}",
        height=490,
        legend_bottom=True,
    )


def build_territory_defense_fig(telemetry: CompiledTelemetry, agent_id: int) -> go.Figure:
    """Carte du territoire et des expulsions sur fond topographique avec gradient de couleur territorial."""
    fig = go.Figure()
    rows, cols = telemetry.grid_size

    # 1. Fond topographique (Plaine, Plateau, Versant, Falaise) + Courbes d'altitude
    _add_topographic_base_layer(fig, telemetry, show_topo_colorbar=False)

    # 2. Calcul du champ territorial de l'individu (et de son couple s'il partage un nid)
    meta = telemetry.agent_metadata.get(agent_id, {})
    terr_id = int(meta.get("territory_id", 0))
    partner_id = meta.get("partner_id")
    nest_pos = meta.get("nest_position")

    own_occ = telemetry.agent_occupancy_grids.get(
        agent_id, np.zeros((rows, cols), dtype=np.float32)
    ).copy()
    if partner_id is not None and int(partner_id) in telemetry.agent_occupancy_grids:
        # Combine l'occupation du couple et l'empreinte territoriale du nid
        own_occ = 0.7 * own_occ + 0.3 * telemetry.agent_occupancy_grids[int(partner_id)]

    if terr_id > 0:
        owner_bonus = (telemetry.final_owner_grid == terr_id).astype(np.float32) * telemetry.final_presence_grid
        own_occ = own_occ + owner_bonus * float(max(own_occ.max(), 10.0))

    # Lissage gaussien pour créer un gradient continu de présence territoriale par-dessus le relief
    smoothed_territory = gaussian_filter(own_occ, sigma=1.15)
    max_val = float(smoothed_territory.max())
    if max_val > 0:
        norm_territory = smoothed_territory / max_val
        # Masque les zones en dessous de 4% pour laisser le relief parfaitement visible autour du territoire
        masked_territory = np.where(norm_territory >= 0.04, norm_territory, np.nan)

        fig.add_trace(
            go.Heatmap(
                z=masked_territory,
                colorscale=[
                    [0.0, "rgba(56, 189, 248, 0.12)"],
                    [0.35, "rgba(2, 132, 199, 0.42)"],
                    [0.70, "rgba(30, 58, 95, 0.65)"],
                    [1.0, "rgba(225, 29, 72, 0.82)"],
                ],
                zmin=0.0,
                zmax=1.0,
                colorbar=dict(
                    title=dict(text="Intensité<br>Territoire", font=dict(color=TEXT_NAVY, size=11)),
                    thickness=12,
                    len=0.65,
                    x=1.02,
                ),
                hovertemplate="Case (Y=%{y}, X=%{x})<br>Intensité territoriale : <b>%{z:.0%}</b><extra></extra>",
                name="Gradient Territorial",
            )
        )

        # Contour extérieur du domaine vital (isocontour à 15% d'intensité)
        fig.add_trace(
            go.Contour(
                z=norm_territory,
                contours=dict(start=0.15, end=0.15, size=1.0, coloring="none"),
                line=dict(color=NAVY_PRIMARY, width=2.4, dash="solid"),
                showscale=False,
                hoverinfo="skip",
                name="Frontière Domaine Vital",
            )
        )

    # 3. Événements d'expulsion d'intrus (réalisés par l'aigle ou son partenaire sur le territoire)
    def_df = telemetry.defense_events_df
    if not def_df.empty:
        # Montre les défenses faites par l'aigle, ainsi que celles de son partenaire sur le même territoire
        team_ids = [agent_id] + ([int(partner_id)] if partner_id is not None and int(partner_id) > 0 else [])
        sub_def = def_df[def_df["agent_id"].isin(team_ids)]

        won = sub_def[sub_def["event_type"] == "DEFENSE_GAGNEE"]
        if not won.empty:
            fig.add_trace(
                go.Scatter(
                    x=won["col"],
                    y=won["row"],
                    mode="markers",
                    marker=dict(
                        size=12,
                        color=OCHRE_STONE,
                        symbol="diamond",
                        line=dict(width=1.8, color="white"),
                    ),
                    text=[
                        f"Jour {d} : Intrus intercepté et expulsé par Aigle #{a}"
                        for d, a in zip(won["day"], won["agent_id"])
                    ],
                    hoverinfo="text",
                    name=f"Intrus expulsés ({len(won)})",
                )
            )

        exp = def_df[(def_df["agent_id"] == agent_id) & (def_df["event_type"] == "EXPULSION_SUBIE")]
        if not exp.empty:
            fig.add_trace(
                go.Scatter(
                    x=exp["col"],
                    y=exp["row"],
                    mode="markers",
                    marker=dict(
                        size=11,
                        color=CORAL_ALERT,
                        symbol="x",
                        line=dict(width=1.5, color="white"),
                    ),
                    text=[f"Jour {d} : Expulsion subie hors d'un territoire" for d in exp["day"]],
                    hoverinfo="text",
                    name=f"Expulsions subies ({len(exp)})",
                )
            )

    # 4. Position de l'aire (Nid sur falaise)
    if nest_pos is not None:
        fig.add_trace(
            go.Scatter(
                x=[nest_pos[1]],
                y=[nest_pos[0]],
                mode="markers",
                marker=dict(
                    size=16,
                    color="#ffffff",
                    symbol="hexagon",
                    line=dict(width=3.0, color=CORAL_ALERT),
                ),
                hovertemplate=f"<b>Aire de nidification</b><br>Falaise ({nest_pos[0]}, {nest_pos[1]})<extra></extra>",
                name="Nid (Falaise)",
            )
        )

    fig.update_xaxes(title_text="Ouest → Est (cellules)", range=[-0.5, cols - 0.5], constrain="domain")
    fig.update_yaxes(title_text="Nord → Sud (cellules)", range=[rows - 0.5, -0.5], scaleanchor="x", scaleratio=1)
    label = meta.get("label", f"Aigle #{agent_id}")
    def_cnt = int(meta.get("defense_count", 0))
    return _apply_nature_layout(
        fig,
        f"Territoire, Relief & Expulsions ({def_cnt} défenses) — {label}",
        height=490,
        legend_bottom=True,
    )


def build_hunting_habitats_fig(telemetry: CompiledTelemetry, agent_ids: List[int]) -> go.Figure:
    """Diagramme en barres de fréquentation des habitats de chasse (Plaine, Plateau, Versant, Falaise)."""
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
                marker=dict(color=topo_colors, line=dict(color=TEXT_NAVY, width=1.0)),
                text=[f"{p:.1f}%" for p in pcts],
                textposition="outside",
                showlegend=False,
            ),
            row=1,
            col=idx,
        )
        fig.update_xaxes(title_text="Habitat topographique", row=1, col=idx)
        if idx == 1:
            fig.update_yaxes(title_text="Temps en chasse (%)", range=[0, 108], row=1, col=idx)

    return _apply_nature_layout(fig, "Habitats de Chasse Exploités (Plaine, Plateau, Versant, Falaise)", height=370)


def build_life_gantt_fig(telemetry: CompiledTelemetry, agent_ids: List[int]) -> go.Figure:
    """Timeline de vie (Gantt des stades) et périodes en couple."""
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

        if spawn_day > 105 and meta.get("parent_nest") is not None:
            egg_start = max(1, spawn_day - 140)
            chick_start = max(1, spawn_day - 100)
            fig.add_trace(
                go.Bar(
                    x=[chick_start - egg_start],
                    y=["Stade de vie"],
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
                    y=["Stade de vie"],
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

        sub_ont = ont_df[ont_df["agent_id"] == aid] if not ont_df.empty else pd.DataFrame()
        for _, row in sub_ont.iterrows():
            st_code = str(row["label"])
            st_display = STATE_LABELS.get(st_code, st_code)
            fig.add_trace(
                go.Bar(
                    x=[int(row["duration_days"])],
                    y=["Stade de vie"],
                    base=[int(row["start_day"])],
                    orientation="h",
                    name=st_display,
                    marker_color=STATE_COLORS.get(st_code, SKY_ACCENT),
                    hovertemplate=(
                        f"{st_display}<br>J{int(row['start_day'])} → J{int(row['end_day'])} "
                        f"({int(row['duration_days'])} j)<extra></extra>"
                    ),
                    showlegend=(idx == 1),
                ),
                row=1,
                col=idx,
            )

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
                    marker_color=OCHRE_STONE,
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
    return _apply_nature_layout(
        fig,
        "Timeline Ontogénique (Gantt) & Intervalles d'Appariement",
        height=340,
    )


def build_partner_distance_fig(telemetry: CompiledTelemetry, agent_ids: List[int]) -> go.Figure:
    """Courbe de distance moyenne au partenaire au cours du temps."""
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
                    line=dict(color="rgba(100, 116, 139, 0.30)", width=1),
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
                    line=dict(color=NAVY_PRIMARY, width=2.2),
                    showlegend=(idx == 1),
                ),
                row=1,
                col=idx,
            )
        fig.update_xaxes(title_text="Jour", matches="x", row=1, col=idx)
        if idx == 1:
            fig.update_yaxes(title_text="Distance au partenaire (km)", row=1, col=idx)

    return _apply_nature_layout(fig, "Distance Inter-Partenaires au sein du Couple (km)")


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
    return _apply_nature_layout(
        fig,
        f"{title} (1 case = {cell_size_km * 1000:.0f}m)",
        height=460,
    )


# =============================================================================
# Pages NiceGUI : Route `/` (Setup) et Route `/results` (Dashboard)
# =============================================================================

@ui.page("/")
def index_page() -> None:
    """Page d'accueil : DA Ciel & Nature, vagues aériennes, paramètres et lancement asynchrone."""
    ui.colors(primary=NAVY_PRIMARY, secondary=SKY_ACCENT, accent=OCHRE_STONE)
    ui.query("body").style(f"background-color: {PAGE_BG}; color: {TEXT_NAVY}; margin: 0; padding: 0;")

    last_seed = int(app.storage.user.get("last_seed", 42))
    use_random_seed_init = bool(app.storage.user.get("use_random_seed", False))

    # Bandeau Ciel Supérieur + Grandes Vagues SVG
    with ui.column().classes("w-full gap-0"):
        with ui.row().classes(
            "w-full px-8 pt-6 pb-2 items-center justify-between "
            "bg-gradient-to-b from-[#38bdf8] via-[#7dd3fc] to-[#7dd3fc]"
        ):
            with ui.row().classes("items-center gap-3"):
                ui.icon("flight", size="40px", color="white").classes("drop-shadow")
                with ui.column().classes("gap-0"):
                    ui.label("Bonelli-IBM — Massif des Alpilles").classes(
                        "text-3xl font-extrabold text-[#1e3a5f] tracking-tight"
                    )
                    ui.label(
                        "Modélisation écologique mécaniciste First Principles de l'Aigle de Bonelli (Aquila fasciata)"
                    ).classes("text-sm font-medium text-[#1e3a5f]/80")

        ui.html(SKY_WAVES_SVG).classes("w-full")

    # Carte centrale de configuration
    with ui.column().classes("w-full max-w-3xl mx-auto px-6 py-4 gap-6"):
        with ui.card().classes(
            "w-full p-8 bg-white border border-sky-100 shadow-lg rounded-2xl gap-5"
        ):
            with ui.row().classes("items-center gap-2"):
                ui.icon("tune", color="primary", size="26px")
                ui.label("Paramètres Temporels & Démographiques").classes(
                    "text-xl font-bold text-[#1e3a5f]"
                )

            with ui.grid(columns=2).classes("w-full gap-5"):
                years_input = ui.number(
                    label="Durée de la simulation (Années)",
                    value=3.0,
                    min=0.1,
                    max=15.0,
                    step=0.5,
                    format="%.1f",
                ).classes("w-full").props("outlined color=primary")

                adults_input = ui.number(
                    label="Adultes territoriaux initiaux",
                    value=1,
                    min=0,
                    max=10,
                    step=1,
                    format="%d",
                ).classes("w-full").props("outlined color=primary")

                immatures_input = ui.number(
                    label="Immatures en dispersion initiaux",
                    value=1,
                    min=0,
                    max=15,
                    step=1,
                    format="%d",
                ).classes("w-full").props("outlined color=primary")

                subadults_input = ui.number(
                    label="Subadultes prospecteurs initiaux",
                    value=0,
                    min=0,
                    max=10,
                    step=1,
                    format="%d",
                ).classes("w-full").props("outlined color=primary")

            ui.separator().classes("my-2 bg-slate-200")

            with ui.row().classes("items-center gap-2"):
                ui.icon("casino", color="secondary", size="26px")
                ui.label("Contrôle du Générateur Stochastique (Seed)").classes(
                    "text-xl font-bold text-[#1e3a5f]"
                )

            with ui.row().classes("w-full items-center gap-8"):
                random_seed_switch = ui.switch(
                    "Seed aléatoire",
                    value=use_random_seed_init,
                ).props("color=primary").classes("text-[#475569] font-medium")

                seed_number_input = ui.number(
                    label="Valeur de la Seed (mémorisée en cache)",
                    value=last_seed,
                    min=1,
                    max=999_999_999,
                    step=1,
                    format="%d",
                ).classes("w-64").props("outlined color=primary")

                seed_number_input.bind_visibility_from(
                    random_seed_switch,
                    "value",
                    backward=lambda is_rand: not is_rand,
                )

            status_row = ui.row().classes("w-full items-center gap-3 mt-1")
            with status_row:
                spinner = ui.spinner("dots", size="lg", color="primary")
                spinner.visible = False
                status_label = ui.label("").classes("text-sm font-medium text-[#475569]")

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
                    f"Calcul de la dynamique écologique en cours ({int(round(years_val * 365))} jours, Seed={chosen_seed})..."
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
                    ui.notify("Simulation terminée ! Redirection vers le tableau de bord...", type="positive")
                    await asyncio.sleep(0.15)
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
            ).classes(
                "w-full py-3.5 mt-3 text-white font-bold rounded-xl shadow-md "
                "bg-gradient-to-r from-[#1e3a5f] to-[#0284c7]"
            )


@ui.page("/results")
def results_page() -> None:
    """Page de résultats avec DA Ciel/Vagues, frise de vents crème et cartes topographiques."""
    ui.colors(primary=NAVY_PRIMARY, secondary=SKY_ACCENT, accent=OCHRE_STONE)
    ui.query("body").style(f"background-color: {PAGE_BG}; color: {TEXT_NAVY}; margin: 0; padding: 0;")

    telemetry = APP_STATE.telemetry
    if telemetry is None or telemetry.daily_df.empty:
        with ui.column().classes("w-full max-w-xl mx-auto p-12 items-center gap-4"):
            ui.icon("warning", size="48px", color="warning")
            ui.label("Aucune donnée de simulation disponible en mémoire.").classes(
                "text-xl font-bold text-[#1e3a5f]"
            )
            ui.button("Retour à la configuration (/)", on_click=lambda: ui.navigate.to("/")).props("color=primary")
        return

    all_agent_options: Dict[int, str] = {
        aid: meta["label"] for aid, meta in sorted(telemetry.agent_metadata.items())
    }
    default_selected = list(all_agent_options.keys())[:2]
    ui_state: Dict[str, Any] = {
        "selected_agents": default_selected,
        "active_category": "nutrition",
        "time_slider_day": int(telemetry.n_days_simulated),
        "show_repro_on_attack": True,
    }

    # 1. Bandeau Fixe Supérieur en Dégradé Bleu Ciel
    with ui.header().classes(
        "bg-gradient-to-r from-[#bae6fd] via-[#7dd3fc] to-[#bae6fd] "
        "text-[#1e3a5f] shadow-sm items-center justify-between px-6 py-2"
    ):
        with ui.row().classes("items-center gap-3"):
            ui.button(icon="arrow_back", on_click=lambda: ui.navigate.to("/")).props(
                "flat round color=primary"
            )
            ui.icon("flight", size="28px", color="primary")
            ui.label(
                f"Bonelli-IBM Analytics  •  {telemetry.n_days_simulated} jours  •  Seed {telemetry.seed}"
            ).classes("text-lg font-extrabold tracking-tight text-[#1e3a5f]")

        with ui.tabs().classes("text-[#1e3a5f] font-semibold") as main_tabs:
            tab_ind = ui.tab("individus", label="Individus", icon="pets")
            tab_env = ui.tab("environnement", label="Environnement", icon="terrain")

    # 2. Barre Latérale (Sidebar) Claire & Nature
    with ui.left_drawer(value=True).classes(
        "bg-[#eef5fb] border-r border-sky-200 p-4 gap-2"
    ):
        ui.label("Catégories d'Analyse").classes(
            "text-xs uppercase tracking-wider text-[#475569] font-bold mb-1"
        )

        def select_category(cat_key: str) -> None:
            ui_state["active_category"] = cat_key
            main_tabs.set_value("individus")
            render_individuals_content.refresh()

        ui.button(
            "1. Nutrition & Énergie",
            icon="restaurant",
            on_click=lambda: select_category("nutrition"),
        ).classes("w-full justify-start font-semibold text-[#1e3a5f]").props("flat")

        ui.button(
            "2. Spatial & Territoire",
            icon="map",
            on_click=lambda: select_category("spatial"),
        ).classes("w-full justify-start font-semibold text-[#1e3a5f]").props("flat")

        ui.button(
            "3. Démographie & Social",
            icon="groups",
            on_click=lambda: select_category("social"),
        ).classes("w-full justify-start font-semibold text-[#1e3a5f]").props("flat")

        ui.separator().classes("my-3 bg-sky-200")
        ui.label("Couches Environnement").classes(
            "text-xs uppercase tracking-wider text-[#475569] font-bold mb-1"
        )
        ui.button(
            "Heatmaps Biotope & Proies",
            icon="layers",
            on_click=lambda: main_tabs.set_value("environnement"),
        ).classes("w-full justify-start font-semibold text-[#0284c7]").props("flat")

    # 3. Ligne Haute : Grandes Vagues Bleu Ciel entre le bandeau fixe et le reste
    ui.html(SKY_WAVES_SVG).classes("w-full -mt-4")

    # 4. Corps Principal : Frise verticale de Vents / Tourbillons (Blanc/Crème) + Zone des Graphes
    with ui.row().classes("w-full no-wrap items-stretch gap-0 px-2 pb-8"):
        # Séparateur artistique : petits signes de vents / tourbillons crème entre la sidebar et les graphes
        ui.html(WIND_SWIRLS_SVG).classes("shrink-0")

        with ui.tab_panels(main_tabs, value=tab_ind).classes("col-grow bg-transparent px-4 py-0"):

            # =================================================================
            # ONGLET 1 : INDIVIDUS (Comparaison Side-by-Side)
            # =================================================================
            with ui.tab_panel(tab_ind).classes("w-full gap-4 p-0"):
                with ui.card().classes(
                    "w-full p-4 bg-white border border-slate-200 shadow-sm rounded-xl"
                ):
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
                        ).classes("w-96").props("outlined use-chips color=primary")

                        with ui.row().classes("items-center gap-3"):
                            ui.chip(
                                f"{len(all_agent_options)} individus suivis",
                                icon="pets",
                                color="primary",
                            ).props("outline")

                @ui.refreshable
                def render_individuals_content() -> None:
                    selected_ids: List[int] = sorted(ui_state["selected_agents"])
                    if not selected_ids:
                        ui.label("Sélectionnez au moins un aigle dans le menu ci-dessus.").classes(
                            "text-[#475569]"
                        )
                        return

                    cat = ui_state["active_category"]

                    # --- CATÉGORIE 1 : NUTRITION ---
                    if cat == "nutrition":
                        with ui.row().classes("w-full items-center justify-between mt-2"):
                            ui.label("Catégorie Nutrition & Métabolisme Énergétique").classes(
                                "text-xl font-extrabold text-[#1e3a5f]"
                            )

                        with ui.column().classes("w-full gap-5"):
                            fig_sat = build_satiety_comparison_fig(telemetry, selected_ids)
                            with ui.card().classes("w-full p-2 bg-white border border-slate-200 shadow-sm rounded-xl"):
                                ui.plotly(fig_sat).classes("w-full")

                            # Bloc Taux de Réussite avec case à cocher pour les événements reproducteurs
                            with ui.card().classes("w-full p-3 bg-white border border-slate-200 shadow-sm rounded-xl gap-2"):
                                with ui.row().classes("w-full items-center justify-end px-2"):
                                    def on_toggle_repro(e: Any) -> None:
                                        ui_state["show_repro_on_attack"] = bool(e.value)
                                        render_attack_chart.refresh()

                                    ui.checkbox(
                                        "Afficher les événements des poussins (Ponte, Éclosion, Envol, Émancipation)",
                                        value=ui_state["show_repro_on_attack"],
                                        on_change=on_toggle_repro,
                                    ).classes("text-sm font-semibold text-[#1e3a5f]").props("color=primary")

                                @ui.refreshable
                                def render_attack_chart() -> None:
                                    fig_att = build_attack_success_fig(
                                        telemetry,
                                        selected_ids,
                                        show_repro_events=ui_state["show_repro_on_attack"],
                                    )
                                    ui.plotly(fig_att).classes("w-full")

                                render_attack_chart()

                            with ui.grid(columns=2).classes("w-full gap-5"):
                                with ui.card().classes("w-full p-2 bg-white border border-slate-200 shadow-sm rounded-xl"):
                                    fig_prey = build_prey_balance_fig(telemetry, selected_ids)
                                    ui.plotly(fig_prey).classes("w-full")

                                with ui.card().classes("w-full p-2 bg-white border border-slate-200 shadow-sm rounded-xl"):
                                    fig_budget = build_time_budget_fig(telemetry, selected_ids)
                                    ui.plotly(fig_budget).classes("w-full")

                    # --- CATÉGORIE 2 : SPATIAL ---
                    elif cat == "spatial":
                        ui.label("Catégorie Spatiale, Domaine Vital & Habitats de Chasse").classes(
                            "text-xl font-extrabold text-[#1e3a5f] mt-2"
                        )
                        with ui.card().classes("w-full p-4 bg-white border border-slate-200 shadow-sm rounded-xl"):
                            with ui.row().classes("w-full items-center gap-6"):
                                ui.icon("schedule", color="primary", size="24px")
                                day_label = ui.label(
                                    f"Time Slider — Trajectoires cumulées jusqu'au Jour {ui_state['time_slider_day']}"
                                ).classes("font-bold text-[#1e3a5f] w-80")

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
                                ).classes("col-grow").props("label-always color=primary")

                        @ui.refreshable
                        def render_spatial_maps() -> None:
                            n_cols = min(len(selected_ids), 2)
                            with ui.grid(columns=n_cols).classes("w-full gap-5"):
                                for aid in selected_ids:
                                    with ui.card().classes("w-full p-2 bg-white border border-slate-200 shadow-sm rounded-xl"):
                                        fig_disp = build_spatial_displacement_fig(
                                            telemetry, aid, ui_state["time_slider_day"]
                                        )
                                        ui.plotly(fig_disp).classes("w-full")

                            with ui.grid(columns=n_cols).classes("w-full gap-5 mt-3"):
                                for aid in selected_ids:
                                    with ui.card().classes("w-full p-2 bg-white border border-slate-200 shadow-sm rounded-xl"):
                                        fig_terr = build_territory_defense_fig(telemetry, aid)
                                        ui.plotly(fig_terr).classes("w-full")

                        render_spatial_maps()

                        with ui.card().classes("w-full p-2 bg-white border border-slate-200 shadow-sm rounded-xl mt-3"):
                            fig_hab = build_hunting_habitats_fig(telemetry, selected_ids)
                            ui.plotly(fig_hab).classes("w-full")

                    # --- CATÉGORIE 3 : DÉMOGRAPHIE & SOCIAL ---
                    elif cat == "social":
                        ui.label("Catégorie Démographie, Ontogénie & Dynamique de Couple").classes(
                            "text-xl font-extrabold text-[#1e3a5f] mt-2"
                        )
                        with ui.column().classes("w-full gap-5"):
                            with ui.card().classes("w-full p-2 bg-white border border-slate-200 shadow-sm rounded-xl"):
                                fig_gantt = build_life_gantt_fig(telemetry, selected_ids)
                                ui.plotly(fig_gantt).classes("w-full")

                            with ui.card().classes("w-full p-2 bg-white border border-slate-200 shadow-sm rounded-xl"):
                                fig_pdist = build_partner_distance_fig(telemetry, selected_ids)
                                ui.plotly(fig_pdist).classes("w-full")

                            if not telemetry.repro_events_df.empty:
                                with ui.card().classes("w-full p-4 bg-white border border-slate-200 shadow-sm rounded-xl"):
                                    ui.label("Journal Phénologique des Nids Reproducteurs").classes(
                                        "text-md font-bold text-[#1e3a5f] mb-2"
                                    )
                                    ui.table.from_pandas(telemetry.repro_events_df).classes("w-full").props("flat bordered")

                render_individuals_content()

            # =================================================================
            # ONGLET 2 : ENVIRONNEMENT (Heatmaps Plotly Zoomables)
            # =================================================================
            with ui.tab_panel(tab_env).classes("w-full gap-4 p-0"):
                ui.label("Cartographie Interactive des Couches Environnementales (Zoom & Pan)").classes(
                    "text-xl font-extrabold text-[#1e3a5f]"
                )
                with ui.grid(columns=2).classes("w-full gap-5"):
                    with ui.card().classes("w-full p-2 bg-white border border-slate-200 shadow-sm rounded-xl"):
                        fig_therm = build_environment_heatmap(
                            telemetry.thermal_uplift_grid,
                            "Ascendances Thermiques & Orographiques (Adret / Falaises)",
                            "YlGnBu",
                            "Portance [0-1]",
                            telemetry.cell_size_km,
                        )
                        ui.plotly(fig_therm).classes("w-full")

                    with ui.card().classes("w-full p-2 bg-white border border-slate-200 shadow-sm rounded-xl"):
                        fig_fear = build_environment_heatmap(
                            telemetry.mean_fear_grid,
                            "Fear Layer — Vigilance & Effarouchement Moyen des Proies",
                            "YlOrRd",
                            "Peur [0-0.9]",
                            telemetry.cell_size_km,
                        )
                        ui.plotly(fig_fear).classes("w-full")

                ui.label("Couches de Densité des Proies (État Final)").classes(
                    "text-lg font-extrabold text-[#1e3a5f] mt-4"
                )
                with ui.grid(columns=2).classes("w-full gap-5"):
                    for prey_name, prey_matrix in telemetry.prey_grids.items():
                        with ui.card().classes("w-full p-2 bg-white border border-slate-200 shadow-sm rounded-xl"):
                            fig_prey_map = build_environment_heatmap(
                                prey_matrix,
                                f"Densité de Proies : {prey_name.capitalize()} (Total = {prey_matrix.sum():.0f} ind.)",
                                "Tealgrn",
                                "Ind. / case",
                                telemetry.cell_size_km,
                            )
                            ui.plotly(fig_prey_map).classes("w-full")


def main() -> None:
    """Point d'entrée du serveur NiceGUI."""
    ui.run(
        title="Bonelli-IBM — Dashboard Analytique",
        storage_secret="bonelli-ibm-secret-key-2026",
        dark=False,
        reload=False,
        port=8080,
    )


if __name__ in {"__main__", "__mp_main__"}:
    main()