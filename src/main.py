"""Point d'entrée - Étape 1 : génération et visualisation de l'environnement.

Usage :
    python src/main.py
    python -m src.main --config configs/environments/alpilles.yaml --save world.png
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.environment.map import WorldMap  # noqa: E402
from src.visualization.dashboard import Dashboard  # noqa: E402

DEFAULT_CONFIG = PROJECT_ROOT / "configs" / "environments" / "alpilles.yaml"


def main() -> None:
    parser = argparse.ArgumentParser(description="Bird sim - environnement V1")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--save", type=str, default=None, help="Chemin PNG optionnel")
    parser.add_argument("--no-show", action="store_true", help="Ne pas ouvrir la fenêtre")
    args = parser.parse_args()

    world = WorldMap.from_yaml(args.config)
    print(world.summary())

    if args.no_show:
        import matplotlib
        matplotlib.use("Agg")
    Dashboard(world).render(show=not args.no_show, save_path=args.save)


if __name__ == "__main__":
    main()
