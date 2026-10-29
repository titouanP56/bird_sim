"""Tableau de bord visuel : couches de l'environnement + rendu de la simulation."""

from __future__ import annotations

import math
from typing import TYPE_CHECKING, Optional

import matplotlib.patheffects as pe
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.animation import FuncAnimation, PillowWriter
from matplotlib.collections import LineCollection
from matplotlib.colors import BoundaryNorm, ListedColormap, Normalize
from matplotlib.patches import Circle

from src.environment.map import WorldMap

if TYPE_CHECKING:  # pragma: no cover
    from src.engine.simulation import Simulation

_DEFAULT_TOPO_COLORS = ["#e6d8a8", "#c2a66b", "#8a6a4a", "#4a4a52", "#2b2b30"]
_BG = "#14161c"
_FG = "#e8e6e1"
_MUTED = "#9a98a0"
_GRID = "#3a3d47"
_ATTR_CMAP = "viridis"
_TIME_CMAP = "cool"
_OUTLINE = [pe.Stroke(linewidth=3.2, foreground="black", alpha=0.6), pe.Normal()]


class Dashboard:
    """Affiche toutes les couches d'une WorldMap dans une seule figure."""

    def __init__(self, world: WorldMap, n_cols: int = 3, prey_cmap: str = "YlOrRd"):
        self.world = world
        self.n_cols = n_cols
        self.prey_cmap = prey_cmap

    # ----------------------------------------------------------------- Helpers
    @staticmethod
    def _style_axes(ax, title: str) -> None:
        ax.set_title(title, color=_FG, fontsize=12, fontweight="bold", pad=8)
        ax.set_xticks([])
        ax.set_yticks([])
        for spine in ax.spines.values():
            spine.set_color("#3a3d47")
        ax.set_xlabel("Ouest  ←  →  Est", color="#9a98a0", fontsize=8)
        ax.set_ylabel("Sud  ←  →  Nord", color="#9a98a0", fontsize=8)

    @staticmethod
    def _style_colorbar(cbar, label: str = "") -> None:
        cbar.ax.tick_params(colors=_FG, labelsize=8)
        cbar.outline.set_edgecolor("#3a3d47")
        if label:
            cbar.set_label(label, color=_FG, fontsize=9)

    def _cliff_outline(self, ax) -> None:
        """Contour des falaises, repère spatial commun aux cartes de proies."""
        topo = self.world.get_topography()
        cliff_id = max(self.world.topography_types)
        if np.any(topo == cliff_id):
            ax.contour(
                (topo == cliff_id).astype(float), levels=[0.5],
                colors="#2b6cb0", linewidths=0.8, alpha=0.7,
            )

    # ------------------------------------------------------------------ Panels
    def _plot_topography(self, fig, ax) -> None:
        types = self.world.topography_types
        ids = sorted(types)
        colors = [
            types[i].get("color", _DEFAULT_TOPO_COLORS[k % len(_DEFAULT_TOPO_COLORS)])
            for k, i in enumerate(ids)
        ]
        cmap = ListedColormap(colors)
        bounds = [i - 0.5 for i in ids] + [ids[-1] + 0.5]
        norm = BoundaryNorm(bounds, cmap.N)

        im = ax.imshow(self.world.get_topography(), cmap=cmap, norm=norm,
                       interpolation="nearest")
        # Courbes de niveau de l'élévation pour la lecture du relief
        elev = self.world.get_elevation()
        if elev is not None:
            ax.contour(elev, levels=8, colors="black", linewidths=0.4, alpha=0.35)

        self._style_axes(ax, "Topographie")
        cbar = fig.colorbar(im, ax=ax, ticks=ids, fraction=0.046, pad=0.04)
        cbar.ax.set_yticklabels([types[i].get("name", str(i)) for i in ids])
        self._style_colorbar(cbar)

    def _plot_vegetation(self, fig, ax) -> None:
        veg = self.world.get_vegetation()
        im = ax.imshow(veg, cmap="YlGn", vmin=0.0, vmax=1.0, interpolation="nearest")

        strata = self.world.vegetation_strata
        inner = sorted({s["max"] for s in strata if 0.0 < s["max"] < 1.0})
        if inner:
            ax.contour(veg, levels=inner, colors="#1f3d2b", linewidths=0.6,
                       linestyles="--", alpha=0.6)

        self._style_axes(ax, "Densité de végétation")
        # Colorbar : une étiquette par strate (au centre de la bande),
        # séparateurs aux seuils de fermeture
        mids = [0.5 * (s["min"] + s["max"]) for s in strata]
        cbar = fig.colorbar(im, ax=ax, ticks=mids, fraction=0.046, pad=0.04)
        cbar.ax.set_yticklabels(
            [f"{s['name']}\n{s['min']:.1f}–{s['max']:.1f}" for s in strata]
        )
        for edge in inner:
            cbar.ax.axhline(edge, color=_BG, linewidth=1.5)
        self._style_colorbar(cbar)

    def _plot_prey(self, fig, ax, name: str) -> None:
        density = self.world.get_prey_density(name)
        spec = self.world.prey_config(name)
        vmax = float(spec.get("max_density", density.max() or 1.0))
        im = ax.imshow(density, cmap=self.prey_cmap, vmin=0.0, vmax=vmax,
                       interpolation="nearest")
        self._cliff_outline(ax)
        display = spec.get("display_name", name)
        self._style_axes(ax, f"{display}  ({name})")
        cbar = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
        self._style_colorbar(cbar, "Densité (ind./cellule)")
        ax.text(0.02, 0.02, f"Σ ≈ {density.sum():.0f} ind.", transform=ax.transAxes,
                fontsize=8, color="black",
                bbox=dict(boxstyle="round,pad=0.25", fc="white", alpha=0.7, lw=0))

    # ------------------------------------------------------------------ Render
    def render(self, show: bool = True, save_path: Optional[str] = None):
        preys = self.world.prey_names
        n_panels = 2 + len(preys)
        n_cols = min(self.n_cols, n_panels)
        n_rows = math.ceil(n_panels / n_cols)

        fig, axes = plt.subplots(n_rows, n_cols, figsize=(5.6 * n_cols, 5.0 * n_rows),
                                 squeeze=False)
        fig.patch.set_facecolor(_BG)
        flat = axes.ravel()

        self._plot_topography(fig, flat[0])
        self._plot_vegetation(fig, flat[1])
        for ax, name in zip(flat[2:], preys):
            self._plot_prey(fig, ax, name)
        for ax in flat[n_panels:]:
            ax.set_visible(False)

        rows, cols = self.world.grid_size
        fig.suptitle(
            f"{self.world.biome_name}   —   grille {rows}×{cols}   ·   seed {self.world.seed}",
            color=_FG, fontsize=15, fontweight="bold",
        )
        fig.tight_layout(rect=(0, 0, 1, 0.96))

        if save_path:
            fig.savefig(save_path, dpi=130, facecolor=fig.get_facecolor())
        if show:
            plt.show()
        return fig

    # =============================================================== Simulation
    @staticmethod
    def _style_chart(ax, title: str, xlabel: str = "", ylabel: str = "") -> None:
        ax.set_facecolor("#1b1e26")
        ax.set_title(title, color=_FG, fontsize=11, fontweight="bold", pad=6)
        ax.tick_params(colors=_MUTED, labelsize=8)
        for spine in ax.spines.values():
            spine.set_color(_GRID)
        ax.grid(color=_GRID, linewidth=0.5, alpha=0.6)
        ax.set_xlabel(xlabel, color=_MUTED, fontsize=8)
        ax.set_ylabel(ylabel, color=_MUTED, fontsize=8)

    @staticmethod
    def _time_trail(ax, path: np.ndarray, n_days: int, times: np.ndarray) -> LineCollection:
        """Trajectoire (x=col, y=ligne) colorée par le temps (Jour 0 -> Jour n)."""
        xy = path[:, ::-1].astype(float)
        segments = np.stack([xy[:-1], xy[1:]], axis=1)
        lc = LineCollection(segments, cmap=_TIME_CMAP, norm=Normalize(0, n_days),
                            linewidths=1.8, alpha=0.95, path_effects=_OUTLINE)
        lc.set_array(times)  # jour (fractionnaire) d'arrivée de chaque segment
        ax.add_collection(lc)
        return lc

    @staticmethod
    def _start_end_markers(ax, start, end) -> None:
        ax.scatter([start[1]], [start[0]], marker="*", s=260, c="#ffd166",
                   edgecolors="black", linewidths=0.9, zorder=6, label="Départ (J1)")
        ax.scatter([end[1]], [end[0]], marker="^", s=150, c="#ef476f",
                   edgecolors="black", linewidths=0.9, zorder=6, label="Arrivée")

    @staticmethod
    def _legend(ax) -> None:
        leg = ax.legend(loc="lower left", fontsize=7, facecolor=_BG, edgecolor=_GRID,
                        labelcolor=_FG, framealpha=0.85)
        leg.set_zorder(10)

    # ---------------------------------------------------- Panneaux simulation
    def _nest_marker(self, ax, eagle) -> None:
        if eagle is not None and eagle.nest_position is not None:
            ax.scatter([eagle.nest_position[1]], [eagle.nest_position[0]], marker="H", s=210,
                       c="#ffffff", edgecolors="#ef476f", linewidths=2.0, zorder=7,
                       label="Nid (falaise)")

    def _panel_attractiveness_path(self, fig, ax, sim: "Simulation", col, eagle) -> None:
        path = np.array(col.full_path)
        im = ax.imshow(sim.attractiveness_map, cmap=_ATTR_CMAP, vmin=0, vmax=1,
                       interpolation="nearest")
        self._cliff_outline(ax)
        lc = self._time_trail(ax, path, sim.n_days, col.step_times)
        ends = np.array(col.daily_positions)
        ax.scatter(ends[:, 1], ends[:, 0], c=col.days, cmap=_TIME_CMAP,
                   norm=Normalize(0, sim.n_days), s=22, edgecolors="black",
                   linewidths=0.5, zorder=5)
        self._start_end_markers(ax, path[0], path[-1])
        self._nest_marker(ax, eagle)
        self._style_axes(ax, "Trajectoire sur attractivité des proies")
        self._legend(ax)
        cbar = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
        self._style_colorbar(cbar, "Attractivité perçue (initiale)")
        cax = ax.inset_axes([0.62, 0.94, 0.35, 0.025])
        cbar_t = fig.colorbar(lc, cax=cax, orientation="horizontal")
        cbar_t.set_ticks([0, sim.n_days // 2, sim.n_days])
        cbar_t.ax.tick_params(colors=_FG, labelsize=7, length=2)
        cbar_t.ax.xaxis.set_ticks_position("bottom")
        cbar_t.outline.set_edgecolor("black")
        cax.set_title("Jour", color=_FG, fontsize=7, pad=2,
                      path_effects=_OUTLINE)

    def _panel_topography_path(self, fig, ax, sim: "Simulation") -> None:
        col = sim.collector
        self._plot_topography(fig, ax)
        ends = np.array([col.spawn_position] + col.daily_positions)
        ax.plot(ends[:, 1], ends[:, 0], color="white", lw=1.0, alpha=0.7, zorder=4)
        ax.scatter(ends[1:, 1], ends[1:, 0], c=col.days, cmap=_TIME_CMAP,
                   norm=Normalize(0, sim.n_days), s=34, edgecolors="black",
                   linewidths=0.6, zorder=5)
        self._start_end_markers(ax, ends[0], ends[-1])
        for d in (1, len(col.days) // 2, len(col.days)):
            if d >= 1:
                r, c = col.daily_positions[d - 1]
                ax.annotate(f"J{d}", (c, r), xytext=(4, 4), textcoords="offset points",
                            color=_FG, fontsize=7, fontweight="bold", path_effects=_OUTLINE)
        self._style_axes(ax, "Positions journalières sur topographie")
        self._legend(ax)

    def _panel_occupancy(self, fig, ax, sim: "Simulation") -> None:
        occ = sim.collector.occupancy_grid
        ax.imshow(self.world.get_elevation(), cmap="gray", alpha=0.35, interpolation="bilinear")
        masked = np.ma.masked_equal(occ, 0)
        im = ax.imshow(masked, cmap="inferno", interpolation="nearest",
                       vmin=1, vmax=max(int(occ.max()), 2))
        self._cliff_outline(ax)
        visited = int((occ > 0).sum())
        self._style_axes(ax, "Domaine vital : occupation sur le mois")
        cbar = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
        self._style_colorbar(cbar, "Passages / case")
        r, c = np.unravel_index(np.argmax(occ), occ.shape)
        ax.scatter([c], [r], marker="o", s=140, facecolors="none", edgecolors="#7cf",
                   linewidths=1.5, zorder=6)
        ax.text(0.02, 0.02, f"{visited} cases visitées · max {occ.max()} passages",
                transform=ax.transAxes, fontsize=8, color="black",
                bbox=dict(boxstyle="round,pad=0.25", fc="white", alpha=0.75, lw=0))

    def _panel_metrics(self, fig, cell, sim: "Simulation") -> None:
        col = sim.collector
        days = np.array(col.days)
        sub = cell.subgridspec(2, 1, height_ratios=[1.25, 1], hspace=0.55)
        ax1 = fig.add_subplot(sub[0])
        ax2 = fig.add_subplot(sub[1], sharex=ax1)

        # Attractivité moyenne journalière vs moyenne globale de la carte
        attr = np.array(col.daily_mean_attractiveness)
        glob = float(sim.attractiveness_map.mean())
        ax1.fill_between(days, glob, attr, where=attr >= glob, color="#06d6a0", alpha=0.18)
        ax1.plot(days, attr, color="#06d6a0", lw=2, marker="o", ms=3.5, label="Cases visitées")
        ax1.axhline(glob, color=_MUTED, ls="--", lw=1.2, label=f"Moyenne carte ({glob:.2f})")
        ax1.set_ylim(0, 1.02)
        self._style_chart(ax1, "Attractivité moyenne des cases visitées", ylabel="Attractivité")
        ax1.legend(fontsize=7, facecolor=_BG, edgecolor=_GRID, labelcolor=_FG, loc="lower right")
        ax1b = ax1.twinx()
        ax1b.bar(days, col.daily_distance, color="#ffd166", alpha=0.18, width=0.8)
        ax1b.set_ylabel("Distance (cell.)", color="#ffd166", fontsize=8)
        ax1b.tick_params(colors="#ffd166", labelsize=7)
        ax1b.set_zorder(ax1.get_zorder() - 1)
        ax1.patch.set_visible(False)
        for spine in ax1b.spines.values():
            spine.set_color(_GRID)

        # Répartition du temps passé par relief (barres empilées)
        types = self.world.topography_types
        frac = col.topo_time_fractions()
        bottom = np.zeros(len(days))
        for k, tid in enumerate(col.topo_ids):
            color = types[tid].get("color", _DEFAULT_TOPO_COLORS[k % len(_DEFAULT_TOPO_COLORS)])
            total = frac[:, k].mean()
            ax2.bar(days, frac[:, k], bottom=bottom, color=color, width=0.85,
                    edgecolor=_BG, linewidth=0.4,
                    label=f"{types[tid].get('name', tid)} {total:.0%}")
            bottom += frac[:, k]
        ax2.set_ylim(0, 1)
        ax2.set_xlim(0.4, max(sim.n_days, days[-1]) + 0.6)
        self._style_chart(ax2, "Temps passé par type de relief", xlabel="Jour", ylabel="Fraction")
        ax2.legend(fontsize=7, ncol=len(col.topo_ids), facecolor=_BG, edgecolor=_GRID,
                   labelcolor=_FG, loc="upper center", bbox_to_anchor=(0.5, -0.32))

    # ------------------------------------------------ Panneaux Étape 3
    def _panel_occupancy_nest(self, fig, ax, sim: "Simulation", col, eagle) -> None:
        occ = col.occupancy_grid
        ax.imshow(self.world.get_elevation(), cmap="gray", alpha=0.35, interpolation="bilinear")
        masked = np.ma.masked_equal(occ, 0)
        im = ax.imshow(masked, cmap="inferno", interpolation="nearest",
                       vmin=1, vmax=max(int(occ.max()), 2))
        self._cliff_outline(ax)
        self._nest_marker(ax, eagle)
        visited = int((occ > 0).sum())
        self._style_axes(ax, "Domaine vital : carte d'occupation")
        cbar = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
        self._style_colorbar(cbar, "Passages / case")
        ax.text(0.02, 0.02, f"{visited} cases visitées · max {occ.max()} passages",
                transform=ax.transAxes, fontsize=8, color="black",
                bbox=dict(boxstyle="round,pad=0.25", fc="white", alpha=0.75, lw=0))

    def _panel_fear(self, fig, ax, sim: "Simulation", col, eagle) -> None:
        fear = col.mean_fear_map
        im = ax.imshow(fear, cmap="magma", vmin=0, vmax=max(float(fear.max()), 0.05),
                       interpolation="nearest")
        self._cliff_outline(ax)
        self._nest_marker(ax, eagle)
        self._style_axes(ax, "Effarouchement moyen des proies")
        cbar = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
        self._style_colorbar(cbar, "Effarouchement moyen")

    def _panel_satiety(self, fig, ax, sim: "Simulation", col, eagle) -> None:
        thr = eagle.hunger_threshold
        xs, ys = [0.0], [col.satiety_start[0]]
        for d, s0, sp, s1 in zip(col.days, col.satiety_start, col.satiety_peak, col.satiety_end):
            xs += [d - 0.5, d]
            ys += [sp, s1]
        # Plages de repos
        for d, mode in zip(col.days, col.daily_modes):
            if mode != "CHASSE_ACTIVE":
                ax.axvspan(d - 1, d, color="#4cc9f0", alpha=0.10, lw=0)
        ax.plot(xs, ys, color="#06d6a0", lw=1.8)
        ax.axhline(thr, color="#ef476f", ls="--", lw=1.2, label=f"Seuil de faim ({thr:.0f})")
        prey_colors = {}
        palette = ["#ffd166", "#ef476f", "#4cc9f0", "#b5e48c", "#f4a261"]
        for day, sp in col.captures:
            c = prey_colors.setdefault(sp, palette[len(prey_colors) % len(palette)])
            ax.scatter([day - 0.5], [col.satiety_peak[day - 1]], s=70, c=c, edgecolors="black",
                       linewidths=0.8, zorder=5,
                       label=sp if sp not in ax.get_legend_handles_labels()[1] else None)
        if col.died_on_day:
            ax.scatter([col.died_on_day], [0], marker="X", s=140, c="#ef476f",
                       edgecolors="white", zorder=6, label="Mort")
        ax.set_ylim(0, eagle.max_satiety + 4)
        ax.set_xlim(0, max(sim.n_days, 1))
        self._style_chart(ax, "Satieté S (zones bleues = repos)", xlabel="Jour", ylabel="Satieté")
        ax.legend(fontsize=7, facecolor=_BG, edgecolor=_GRID, labelcolor=_FG, loc="lower right",
                  ncol=2)

    def _panel_activity_diet(self, fig, cell, sim: "Simulation", col, eagle) -> None:
        sub = cell.subgridspec(1, 2, width_ratios=[1, 1.5], wspace=0.45)
        ax1, ax2 = fig.add_subplot(sub[0]), fig.add_subplot(sub[1])
        hunt = sum(m == "CHASSE_ACTIVE" for m in col.daily_modes)
        rest = len(col.daily_modes) - hunt
        bars = ax1.bar(["Chasse", "Repos"], [hunt, rest], color=["#ef476f", "#4cc9f0"])
        ax1.bar_label(bars, color=_FG, fontsize=8)
        self._style_chart(ax1, "Activité", ylabel="Jours")
        ax1.set_ylim(0, max(hunt, rest, 1) * 1.2)
        ax1.text(0.5, 0.9, f"{hunt / max(hunt + rest, 1):.0%} chasse", transform=ax1.transAxes,
                 ha="center", color=_FG, fontsize=8)

        diet = col.diet_counts()
        names = list(self.world.prey_names)
        counts = [diet.get(n, 0) for n in names]
        bars = ax2.bar(names, counts, color="#ffd166")
        ax2.bar_label(bars, color=_FG, fontsize=8)
        self._style_chart(ax2, f"Régime ({sum(counts)} proies)", ylabel="Captures")
        ax2.set_ylim(0, max(counts + [1]) * 1.25)
        ax2.tick_params(axis="x", labelrotation=30)

    def _panel_topo_frequency(self, fig, ax, sim: "Simulation", col, eagle) -> None:
        types = self.world.topography_types
        totals = col.topo_totals()
        ids = col.topo_ids
        colors = [types[t].get("color", _DEFAULT_TOPO_COLORS[k % len(_DEFAULT_TOPO_COLORS)])
                  for k, t in enumerate(ids)]
        vals = [totals[t] for t in ids]
        bars = ax.bar([types[t].get("name", str(t)) for t in ids], vals, color=colors,
                      edgecolor=_GRID)
        ax.bar_label(bars, labels=[f"{v:.0%}" for v in vals], color=_FG, fontsize=8)
        ax.set_ylim(0, max(vals + [0.1]) * 1.2)
        self._style_chart(ax, "Fréquentation topographique", ylabel="Fraction du temps")

    # -------------------------------------------------------- Rendu synthèse
    def render_simulation_summary(self, sim: "Simulation", eagle_index: int = 0,
                                  show: bool = True, save_path: Optional[str] = None):
        """Planche synthèse 6 panneaux pour l'aigle `eagle_index`."""
        eagle, col = sim.eagles[eagle_index], sim.collectors[eagle_index]
        fig = plt.figure(figsize=(21, 11.5))
        fig.patch.set_facecolor(_BG)
        gs = fig.add_gridspec(2, 3, hspace=0.30, wspace=0.28)

        self._panel_attractiveness_path(fig, fig.add_subplot(gs[0, 0]), sim, col, eagle)
        self._panel_occupancy_nest(fig, fig.add_subplot(gs[0, 1]), sim, col, eagle)
        self._panel_fear(fig, fig.add_subplot(gs[0, 2]), sim, col, eagle)
        self._panel_satiety(fig, fig.add_subplot(gs[1, 0]), sim, col, eagle)
        self._panel_activity_diet(fig, gs[1, 1], sim, col, eagle)
        self._panel_topo_frequency(fig, fig.add_subplot(gs[1, 2]), sim, col, eagle)

        sp = sim.species_config
        status = f"mort au jour {col.died_on_day}" if col.died_on_day else "vivant"
        fig.suptitle(
            f"{eagle.name}   —   {self.world.biome_name}   ·   {len(col.days)} jours ({status})"
            f"   ·   seed {sim.seed}",
            color=_FG, fontsize=15, fontweight="bold",
        )
        fig.subplots_adjust(left=0.04, right=0.97, top=0.92, bottom=0.07)

        if save_path:
            fig.savefig(save_path, dpi=120, facecolor=fig.get_facecolor())
        if show:
            plt.show()
        return fig

    # -------------------------------------------------------------- Animation
    def animate_simulation(self, sim: "Simulation", eagle_index: int = 0,
                           interval_ms: int = 200, save_gif: Optional[str] = None,
                           trail_days: int = 3, show: bool = True) -> FuncAnimation:
        """Animation pas à pas sur la carte d'attractivité initiale."""
        eagle, col = sim.eagles[eagle_index], sim.collectors[eagle_index]
        path = np.array(col.full_path)
        n_days = len(col.days)
        radius = eagle.movement.vision_radius
        # jour et rang du pas pour chaque image (image 0 = apparition)
        frame_day = [0] + [d for d, sub in zip(col.days, col.daily_substeps) for _ in sub]
        frame_sub = [0] + [k + 1 for sub in col.daily_substeps for k in range(len(sub))]
        frame_len = [0] + [len(sub) for sub in col.daily_substeps for _ in sub]
        trail_len = max(1, trail_days * int(np.mean([len(s) for s in col.daily_substeps])))

        fig, ax = plt.subplots(figsize=(8.2, 7.6))
        fig.patch.set_facecolor(_BG)
        im = ax.imshow(sim.attractiveness_map, cmap=_ATTR_CMAP, vmin=0, vmax=1,
                       interpolation="nearest")
        self._cliff_outline(ax)
        self._style_axes(ax, "")
        cbar = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
        self._style_colorbar(cbar, "Attractivité perçue (initiale)")
        ax.scatter([path[0, 1]], [path[0, 0]], marker="*", s=200, c="#ffd166",
                   edgecolors="black", linewidths=0.8, zorder=4)
        self._nest_marker(ax, eagle)
        rows, cols = self.world.grid_size
        ax.set_xlim(-0.5, cols - 0.5)
        ax.set_ylim(rows - 0.5, -0.5)

        trail = LineCollection([], cmap="Greys_r", norm=Normalize(0, 1), linewidths=2.2,
                               path_effects=_OUTLINE, zorder=5)
        ax.add_collection(trail)
        vision = Circle((path[0, 1], path[0, 0]), radius, fill=True, fc="white", alpha=0.08,
                        ec="none", zorder=6)
        vision_edge = Circle((path[0, 1], path[0, 0]), radius, fill=False, ec="white",
                             ls="--", lw=1.4, zorder=6)
        ax.add_patch(vision)
        ax.add_patch(vision_edge)
        (eagle_pt,) = ax.plot([], [], marker="o", ms=11, mfc="#ef476f", mec="white",
                              mew=1.6, ls="none", zorder=7)
        title = ax.set_title("", color=_FG, fontsize=12, fontweight="bold", pad=10)
        info = ax.text(0.02, 0.98, "", transform=ax.transAxes, va="top", fontsize=8.5,
                       color=_FG, family="monospace",
                       bbox=dict(boxstyle="round,pad=0.35", fc=_BG, alpha=0.8, ec=_GRID))
        attr_map = sim.attractiveness_map

        def update(i: int):
            r, c = path[i]
            day = frame_day[i]
            lo = max(0, i - trail_len)
            seg_xy = path[lo:i + 1, ::-1].astype(float)
            if len(seg_xy) >= 2:
                segs = np.stack([seg_xy[:-1], seg_xy[1:]], axis=1)
                trail.set_segments(segs)
                trail.set_array(np.linspace(0.25, 1.0, len(segs)))
            else:
                trail.set_segments([])
            vision.center = vision_edge.center = (c, r)
            eagle_pt.set_data([c], [r])
            title.set_text(f"{eagle.name}   —   Jour {day} / {n_days}")
            if day == 0:
                info.set_text(f"apparition   pos=({r:2d},{c:2d})")
            else:
                info.set_text(f"pas {frame_sub[i]}/{frame_len[i]}   pos=({r:2d},{c:2d})\n"
                              f"{col.daily_modes[day - 1]}\n"
                              f"S fin de jour = {col.satiety_end[day - 1]:.0f}")
            return trail, vision, vision_edge, eagle_pt, title, info

        anim = FuncAnimation(fig, update, frames=len(path), interval=interval_ms,
                             blit=False, repeat=True)
        fig.tight_layout()

        if save_gif:
            anim.save(save_gif, writer=PillowWriter(fps=max(1, round(1000 / interval_ms))),
                      savefig_kwargs={"facecolor": fig.get_facecolor()})
        if show:
            plt.show()
        return anim
