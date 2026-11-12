"""Module d'export multi-format (Markdown IA, JSON, CSV et PNG) pour Bonelli-IBM.

Génère une archive ZIP complète en mémoire prête à être fournie à un agent IA
ou utilisée pour de l'analyse scientifique externe.
"""

from __future__ import annotations

import io
import json
import zipfile
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List

import matplotlib
import matplotlib.pyplot as plt
import pandas as pd

if TYPE_CHECKING:  # pragma: no cover
    from src.analytics.telemetry import CompiledTelemetry
    from src.engine.simulation import Simulation


def build_ai_markdown_report(telemetry: "CompiledTelemetry") -> str:
    """Génère un rapport Markdown structuré optimisé pour le contexte d'un LLM / Agent IA.

    Args:
        telemetry: Objet CompiledTelemetry contenant les DataFrames et métadonnées.

    Returns:
        Chaîne Markdown complète décrivant le paramétrage et les résultats émergents.
    """
    assert telemetry is not None, "La télémétrie ne peut pas être None."
    lines: List[str] = [
        "# RAPPORT D'ANALYSE DE SIMULATION — BONELLI-IBM (AI-READY)",
        f"- **Date de génération** : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"- **Graine stochastique (Seed)** : `{telemetry.seed}`",
        f"- **Durée simulée** : `{telemetry.n_days_simulated}` jours ({telemetry.n_days_simulated / 365.0:.2f} ans)",
        f"- **Grille spatiale** : `{telemetry.grid_size[0]}x{telemetry.grid_size[1]}` cellules "
        f"(1 cellule = {telemetry.cell_size_km * 1000:.0f}m)",
        f"- **Nombre total d'individus suivis** : `{len(telemetry.agent_metadata)}`",
        "",
        "---",
        "## 1. SYNTHÈSE PAR INDIVIDU (MÉTABOLISME, CHASSE & SOCIAL)",
    ]

    df = telemetry.daily_df
    cap_df = telemetry.captures_df
    sub_df = telemetry.substeps_df

    for aid, meta in sorted(telemetry.agent_metadata.items()):
        sub = df[df["agent_id"] == aid].sort_values("day") if not df.empty else pd.DataFrame()
        if sub.empty:
            continue

        alive_final = bool(sub["alive"].iloc[-1])
        last_day = int(sub["day"].iloc[-1])
        status_str = "Vivant" if alive_final else f"Mort d'inanition au jour {last_day}"
        mean_sat = float(sub["satiety_end"].mean())
        min_sat = float(sub["satiety_end"].min())
        total_attempts = int(sub["attempts"].sum())
        total_captures = int(sub["captured_bool"].sum())
        success_rate = (total_captures / total_attempts * 100.0) if total_attempts > 0 else 0.0
        total_dist_km = float(sub["distance_km"].sum())

        # Répartition de l'emploi du temps
        mode_counts = sub["mode"].value_counts(normalize=True).to_dict()
        modes_str = ", ".join(f"{k}: {v * 100:.1f}%" for k, v in mode_counts.items())

        # Bilan des proies
        agent_caps = cap_df[cap_df["agent_id"] == aid] if not cap_df.empty else pd.DataFrame()
        prey_counts = agent_caps["prey_species"].value_counts().to_dict() if not agent_caps.empty else {}
        prey_str = ", ".join(f"{k}: {int(v)}" for k, v in prey_counts.items()) or "Aucune capture"

        # Habitats fréquentés en chasse
        if not sub_df.empty:
            h_steps = sub_df[(sub_df["agent_id"] == aid) & (sub_df["is_hunt_habitat"])]
            if h_steps.empty:
                h_steps = sub_df[sub_df["agent_id"] == aid]
            topo_vc = h_steps["topo_id"].value_counts(normalize=True).to_dict()
            hab_str = ", ".join(
                f"{telemetry.topography_names.get(int(tid), str(tid))}: {frac * 100:.1f}%"
                for tid, frac in sorted(topo_vc.items())
            )
        else:
            hab_str = "N/A"

        # Extraction préalable des variables pour compatibilité Python 3.11 (sans backslash dans f-string)
        label_str = str(meta["label"])
        spawn_day = int(meta["spawn_day"])
        init_state = str(meta["initial_state"])
        final_state = str(meta.get("final_state", init_state))
        partner_id = meta.get("partner_id")
        partner_str = f"Aigle #{partner_id}" if partner_id else "Célibataire"
        nest_pos_str = str(meta.get("nest_position"))
        def_count = int(meta.get("defense_count", 0))
        exp_count = int(meta.get("expelled_count", 0))
        daily_avg_km = total_dist_km / max(len(sub), 1)

        lines.extend(
            [
                f"### {label_str} (ID #{aid})",
                f"- **Statut final** : {status_str} (Suivi du J{spawn_day} au J{last_day})",
                f"- **Stade initial → final** : `{init_state}` → `{final_state}`",
                f"- **Partenaire** : `{partner_str}` | **Aire (Nid)** : `{nest_pos_str}`",
                f"- **Interactions territoriales** : `{def_count}` intrus expulsés | `{exp_count}` expulsions subies",
                f"- **Énergie & Satiété** : Satiété moyenne = `{mean_sat:.1f}/100` (Min = `{min_sat:.1f}`)",
                f"- **Efficacité de chasse** : `{total_captures}` captures sur `{total_attempts}` attaques "
                f"(Taux de réussite = `{success_rate:.1f}%`)",
                f"- **Régime alimentaire** : {prey_str}",
                f"- **Budget d'activité** : {modes_str}",
                f"- **Habitats de chasse exploités** : {hab_str}",
                f"- **Distance totale parcourue** : `{total_dist_km:.1f} km` (`{daily_avg_km:.2f} km/jour`)",
                "",
            ]
        )

    lines.extend(
        [
            "---",
            "## 2. CHRONOLOGIE REPRODUCTIVE DES NIDS",
        ]
    )
    if telemetry.repro_events_df.empty:
        lines.append("_Aucun événement reproducteur enregistré durant la simulation._")
    else:
        for _, row in telemetry.repro_events_df.iterrows():
            ev_day = int(row["day"])
            fem_id = int(row["female_id"])
            mal_id = int(row["male_id"])
            n_row = int(row["nest_row"])
            n_col = int(row["nest_col"])
            cat_str = str(row["category"])
            ev_str = str(row["event"])
            lines.append(
                f"- **Jour {ev_day}** (Couple Femelle #{fem_id} & Mâle #{mal_id}, "
                f"Nid `({n_row}, {n_col})`) : **{cat_str}** — {ev_str}"
            )

    mean_fear_val = float(telemetry.mean_fear_grid.mean())
    max_fear_val = float(telemetry.mean_fear_grid.max())
    mean_therm_val = float(telemetry.thermal_uplift_grid.mean())

    lines.extend(
        [
            "",
            "---",
            "## 3. ÉTAT FINAL DE L'ENVIRONNEMENT & BIOMASSE DES PROIES",
            f"- **Effarouchement moyen (Fear Layer)** : `{mean_fear_val:.4f}` (Max = `{max_fear_val:.3f}`)",
            f"- **Indice moyen d'ascendance orographique/thermique** : `{mean_therm_val:.3f}`",
        ]
    )
    for sp, grid in telemetry.prey_grids.items():
        total_sp = float(grid.sum())
        max_sp = float(grid.max())
        lines.append(
            f"- **Biomasse finale `{sp}`** : Total = `{total_sp:.1f}` individus "
            f"(Densité max/case = `{max_sp:.2f}`)"
        )

    return "\n".join(lines)


def build_ai_json_summary(telemetry: "CompiledTelemetry") -> Dict[str, Any]:
    """Construit un dictionnaire JSON structuré résumant toute la simulation pour un parseur IA."""
    df = telemetry.daily_df
    agents_summary: Dict[str, Any] = {}

    for aid, meta in sorted(telemetry.agent_metadata.items()):
        sub = df[df["agent_id"] == aid] if not df.empty else pd.DataFrame()
        attempts = int(sub["attempts"].sum()) if not sub.empty else 0
        captures = int(sub["captured_bool"].sum()) if not sub.empty else 0
        agents_summary[str(aid)] = {
            "metadata": {
                k: (list(v) if isinstance(v, tuple) else v)
                for k, v in meta.items()
            },
            "days_tracked": int(len(sub)),
            "alive_at_end": bool(sub["alive"].iloc[-1]) if not sub.empty else False,
            "mean_satiety": round(float(sub["satiety_end"].mean()), 2) if not sub.empty else 0.0,
            "min_satiety": round(float(sub["satiety_end"].min()), 2) if not sub.empty else 0.0,
            "total_hunt_attempts": attempts,
            "total_captures": captures,
            "attack_success_rate_pct": round((captures / attempts * 100.0) if attempts > 0 else 0.0, 2),
            "total_distance_km": round(float(sub["distance_km"].sum()), 2) if not sub.empty else 0.0,
            "activity_modes_days": (
                {str(k): int(v) for k, v in sub["mode"].value_counts().items()}
                if not sub.empty
                else {}
            ),
        }

    return {
        "simulation_parameters": {
            "seed": int(telemetry.seed),
            "n_days_simulated": int(telemetry.n_days_simulated),
            "grid_size": list(telemetry.grid_size),
            "cell_size_km": float(telemetry.cell_size_km),
        },
        "environment_final_state": {
            "mean_fear": round(float(telemetry.mean_fear_grid.mean()), 4),
            "max_fear": round(float(telemetry.mean_fear_grid.max()), 4),
            "prey_totals": {
                sp: round(float(grid.sum()), 1) for sp, grid in telemetry.prey_grids.items()
            },
        },
        "agents": agents_summary,
        "reproduction_events": telemetry.repro_events_df.to_dict(orient="records"),
    }


def create_export_zip_bytes(
    telemetry: "CompiledTelemetry",
    sim: "Simulation | None" = None,
) -> bytes:
    """Assemble le rapport IA Markdown, le JSON, les CSV et les planches PNG dans une archive ZIP en mémoire.

    Args:
        telemetry: Télémétrie compilée à la fin du run.
        sim: Instance optionnelle de `Simulation` permettant de générer les planches PNG Matplotlib.

    Returns:
        Octets bruts (`bytes`) du fichier ZIP prêt au téléchargement.
    """
    buffer = io.BytesIO()

    with zipfile.ZipFile(buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        # 1. Rapport Markdown prêt pour le prompt d'une IA
        md_report = build_ai_markdown_report(telemetry)
        zf.writestr("AI_CONTEXT_REPORT.md", md_report.encode("utf-8"))

        # 2. Résumé structuré JSON
        json_summary = build_ai_json_summary(telemetry)
        zf.writestr(
            "ai_summary.json",
            json.dumps(json_summary, indent=2, ensure_ascii=False).encode("utf-8"),
        )

        # 3. Tables de données CSV complètes
        zf.writestr("data/daily_metrics.csv", telemetry.daily_df.to_csv(index=False).encode("utf-8"))
        zf.writestr("data/captures.csv", telemetry.captures_df.to_csv(index=False).encode("utf-8"))
        zf.writestr("data/ontogeny_intervals.csv", telemetry.ontogeny_df.to_csv(index=False).encode("utf-8"))
        zf.writestr("data/pairing_intervals.csv", telemetry.pairing_df.to_csv(index=False).encode("utf-8"))
        zf.writestr("data/defense_events.csv", telemetry.defense_events_df.to_csv(index=False).encode("utf-8"))
        zf.writestr("data/reproduction_events.csv", telemetry.repro_events_df.to_csv(index=False).encode("utf-8"))

        # 4. Génération des images haute résolution (.png) pour vision IA
        if sim is not None:
            matplotlib.use("Agg")
            from src.visualization.dashboard import Dashboard as MplDashboard

            mpl_dash = MplDashboard(sim.world)

            fig_env = mpl_dash.render(show=False)
            img_env_buf = io.BytesIO()
            fig_env.savefig(img_env_buf, format="png", dpi=140, facecolor=fig_env.get_facecolor())
            plt.close(fig_env)
            zf.writestr("figures/environment_layers.png", img_env_buf.getvalue())

            for idx, eagle in enumerate(sim.eagles):
                if not sim.collectors[idx].days:
                    continue
                fig_eagle = mpl_dash.render_simulation_summary(sim, eagle_index=idx, show=False)
                img_eagle_buf = io.BytesIO()
                fig_eagle.savefig(
                    img_eagle_buf, format="png", dpi=130, facecolor=fig_eagle.get_facecolor()
                )
                plt.close(fig_eagle)
                zf.writestr(
                    f"figures/eagle_{eagle.agent_id}_{eagle.sex}_summary.png",
                    img_eagle_buf.getvalue(),
                )

    buffer.seek(0)
    return buffer.getvalue()