"""Point d'entrée CLI pour lancer l'interface web interactive NiceGUI de Bonelli-IBM."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Résolution automatique de la racine du projet (compatible si placé à la racine ou dans src/)
CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parent if CURRENT_DIR.name == "src" else CURRENT_DIR

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from nicegui import ui  # noqa: E402
import src.analytics.dashboard as dashboard_routes  # noqa: E402, F401


def parse_args() -> argparse.Namespace:
    """Analyse les arguments en ligne de commande pour le serveur web.

    Returns:
        Espace de noms contenant `host`, `port`, `no_browser` et `reload`.
    """
    parser = argparse.ArgumentParser(
        description="Lance le Dashboard interactif NiceGUI pour Bonelli-IBM."
    )
    parser.add_argument(
        "--host",
        type=str,
        default="127.0.0.1",
        help="Adresse d'écoute du serveur (défaut : 127.0.0.1).",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8080,
        help="Port HTTP du serveur NiceGUI (défaut : 8080).",
    )
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Ne pas ouvrir automatiquement l'onglet dans le navigateur.",
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Active le rechargement à chaud (mode développement uniquement).",
    )
    return parser.parse_args()


def main() -> None:
    """Valide les paramètres réseau et démarre l'application NiceGUI."""
    args = parse_args()
    assert 1 <= args.port <= 65535, f"Port réseau invalide : {args.port}"

    ui.run(
        host=args.host,
        port=args.port,
        title="Bonelli-IBM — Dashboard Analytique",
        storage_secret="bonelli-ibm-secret-key-2026",
        dark=False,
        show=not args.no_browser,
        reload=args.reload,
    )


if __name__ in {"__main__", "__mp_main__"}:
    main()