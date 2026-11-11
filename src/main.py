"""Point d'entrée - Simulation sur 3 ans (1095 jours) :
Femelle adulte territoriale sur falaise + Mâle immature en plaine -> Couple & Reproduction.
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
    parser = argparse.ArgumentParser(description="Bird sim - Cycle de vie sur 3 ans, Couple & Reproduction")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG, help="YAML environnement")
    parser.add_argument("--species", type=Path, default=DEFAULT_SPECIES, help="YAML espèce")
    parser.add_argument("--days", type=int, default=1095, help="Nombre de jours (défaut: 1095 = 3 ans)")
    parser.add_argument("--state", choices=["adult", "immature", "both"], default="both",
                        help="both = Femelle adulte sur falaise + Mâle immature en plaine")
    parser.add_argument("--seed", type=int, default=None,
                        help="Graine de la simulation (défaut : graine du monde)")
    parser.add_argument("--animate", action="store_true", help="Animation interactive jour par jour")
    parser.add_argument("--interval", type=int, default=120, help="Délai entre images (ms)")
    parser.add_argument("--env-only", action="store_true",
                        help="N'afficher que les cartes d'environnement")
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

    print("\n" + "=" * 72)
    print("CHRONOLOGIE SOCIALE & REPRODUCTIVE (3 ANS)")
    print("=" * 72)
    for _, msg in sim.social_events:
        print("  *", msg)
    for pair_key, bnest in sim.breeding_nests.items():
        print(f"  [Nid {bnest.nest_position} - Couple #{pair_key[0]} & #{pair_key[1]}] "
              f"Total jeunes émancipés : {bnest.total_fledged}")
        for d, ev in bnest.events_log:
            y = ((d - 1) // 365) + 1
            doy = ((d - 1) % 365) + 1
            print(f"    - Jour {d:4d} (Année {y}, J{doy:03d}) : {ev}")

    def suffixed(path, tag):
        if not path or len(sim.eagles) == 1:
            return path
        p = Path(path)
        return str(p.with_name(f"{p.stem}_{tag}{p.suffix}"))

    anims = []
    # Affiche les dashboards des individus fondateurs (et des jeunes émancipés s'il y en a)
    for i, eagle in enumerate(sim.eagles):
        tag = f"aigle{eagle.agent_id}_{eagle.sex}"
        print()
        print(sim.collectors[i].summary())
        dashboard.render_simulation_summary(sim, i, show=False,
                                            save_path=suffixed(args.save, tag))
        if args.animate or args.save_gif:
            anims.append(dashboard.animate_simulation(
                sim, i, interval_ms=args.interval,
                save_gif=suffixed(args.save_gif, tag), show=False))

    if not args.no_show:
        plt.show()
    del anims


if __name__ == "__main__":
    main()