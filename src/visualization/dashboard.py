"""Tableau de bord visuel : une heatmap par couche de l'environnement."""

from __future__ import annotations

import math
from typing import Optional

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import BoundaryNorm, ListedColormap

from src.environment.map import WorldMap

_DEFAULT_TOPO_COLORS = ["#e6d8a8", "#c2a66b", "#8a6a4a", "#4a4a52", "#2b2b30"]
_BG = "#14161c"
_FG = "#e8e6e1"


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
