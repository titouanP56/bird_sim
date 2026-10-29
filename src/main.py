"""Point d'entrée - Étape 3 : satieté, chasse active, effarouchement & états.

Usage :
    python src/main.py                         # adulte + immature, 60 jours, dashboards
    python src/main.py --state adult           # seulement l'adulte territorial
    python src/main.py --state immature        # seulement l'immature en dispersion
    python src/main.py --animate               # + animation jour par jour
    python src/main.py --env-only              # cartes d'environnement (Étape 1)
    python src/main.py --days 60 --seed 7 --save sim.png --save-gif sim.gif --no-show
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.environment.map import WorldMap  # noqa: E402

DEFAULT_CONFIG = PROJECT_ROOT / "configs" / "environments" / "alpilles.yaml"
DEFAULT_SPECIES = PROJECT_ROOT / "configs" / "species" / "bonelli.yaml"


def main() -> None:
    parser = argparse.ArgumentParser(description="Bird sim - Étape 3 : satieté & états de vie")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG, help="YAML environnement")
    parser.add_argument("--species", type=Path, default=DEFAULT_SPECIES, help="YAML espèce")
    parser.add_argument("--days", type=int, default=60, help="Nombre de jours (ticks)")
    parser.add_argument("--state", choices=["adult", "immature", "both"], default="both",
                        help="État de vie simulé (both = adulte + immature côte à côte)")
    parser.add_argument("--seed", type=int, default=None,
                        help="Graine de la simulation (défaut : graine du monde)")
    parser.add_argument("--animate", action="store_true", help="Animation interactive jour par jour")
    parser.add_argument("--interval", type=int, default=120, help="Délai entre images (ms)")
    parser.add_argument("--env-only", action="store_true",
                        help="N'afficher que les cartes d'environnement (Étape 1)")
    parser.add_argument("--save", type=str, default=None, help="Chemin PNG optionnel")
    parser.add_argument("--save-gif", type=str, default=None, help="Chemin GIF de l'animation")
    parser.add_argument("--no-show", action="store_true", help="Ne pas ouvrir de fenêtre")
    args = parser.parse_args()

    if args.no_show:
        import matplotlib
        matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    from src.agents.bird import ADULT, IMMATURE
    from src.engine.simulation import Simulation
    from src.visualization.dashboard import Dashboard

    world = WorldMap.from_yaml(args.config)
    print(world.summary())
    dashboard = Dashboard(world)

    if args.env_only:
        dashboard.render(show=not args.no_show, save_path=args.save)
        return

    states = {"adult": [ADULT], "immature": [IMMATURE], "both": [ADULT, IMMATURE]}[args.state]
    sim = Simulation(world, args.species, n_days=args.days, seed=args.seed, states=states)
    for e in sim.eagles:
        print(f"\n{e.name} apparaît en {e.position} (seed={sim.seed})")
    sim.run()

    def suffixed(path, tag):
        if not path or len(sim.eagles) == 1:
            return path
        p = Path(path)
        return str(p.with_name(f"{p.stem}_{tag}{p.suffix}"))

    anims = []
    for i, eagle in enumerate(sim.eagles):
        tag = "adulte" if eagle.is_territorial else "immature"
        print()
        print(sim.collectors[i].summary())
        dashboard.render_simulation_summary(sim, i, show=False,
                                            save_path=suffixed(args.save, tag))
        if args.animate or args.save_gif:
            anims.append(dashboard.animate_simulation(
                sim, i, interval_ms=args.interval,
                save_gif=suffixed(args.save_gif, tag), show=False))
    if not args.no_show:
        plt.show()  # ouvre les dashboards (+ animations si demandées) simultanément
    del anims


if __name__ == "__main__":
    main()
