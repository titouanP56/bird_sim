---
tags:
  - ibm
  - pilotage
  - jalon-2
  - architecture
  - adr
type: milestone
status: todo
---

# Jalon 2 — Architecture Technique et Choix Structurants

> **Liens internes :** [[feuille_de_route_ibm]] | [[jalon_1_specifications_odd]] | [[Interface_Requise_Environnement]]

## Objectif Global du Jalon

Traduire les spécifications scientifiques du Jalon 1 en une architecture logicielle Python **modulaire, performante, native (sans dépendance lourde à WSL2) et optimisée pour le développement assisté par IA** (fichiers courts, faible couplage, typage strict). Aucune logique métier complexe n'est codée dans ce jalon : on tranche les choix techniques via des **ADR** (*Architecture Decision Records*) et on pose les fondations propres du dépôt avant d'attaquer le MVP au Jalon 3.

---

## Sous-étape 2.1 — Arbitrage du Moteur de Simulation et des Performances

**Objectif :** Choisir les bibliothèques Python adaptées et dimensionner les grilles et les calculs pour garantir des simulations rapides sur un cycle annuel complet ($\Delta t = 5\text{ min}$, soit $105\,120$ pas de temps par an).

**Ce qu'il faut faire :**
- [ ] Comparer 2 à 3 options pour le moteur de simulation (ex : framework `Mesa` / `Mesa-Geo` vs moteur Python/NumPy sur mesure) sur la vitesse, la simplicité et la maintenabilité, puis **trancher**.
- [ ] Évaluer l'empreinte RAM et CPU du massif des Alpilles en `EPSG:2154` (grille maîtresse à $10\text{ m}$ vs stratégies de cache / vectorisation `numpy` et `xarray`).
- [ ] Définir la gestion centralisée du hasard (`numpy.random.Generator` et `seed`) pour garantir une reproductibilité stricte à 100 %.

**Livrables (`docs/02_Technique/`) :**
- `ADR_01_Stack_et_Moteur_Simulation.md`
- `ADR_02_Resolution_Grille_et_Performances.md`

---

## Sous-étape 2.2 — Architecture Logicielle Modulaire & Périmètre MVP (v1 vs v2)

**Objectif :** Fixer l'organisation exacte des dossiers et modules pour isoler le moteur générique (`Core`) des fichiers de configuration (`bonelli.yaml`, `alpilles.yaml`), tout en définissant ce qui sera activé dès la première version.

**Ce qu'il faut faire :**
- [ ] Concevoir l'arborescence cible du code (`src/core/`, `src/agents/`, `src/environment/`, `src/io/`, `configs/`, `tests/`).
- [ ] Vérifier l'absence de dépendances circulaires et formaliser l'injection de `EnvironmentInterface` dans `RaptorAgent`.
- [ ] Tracer la frontière exacte entre la **v1 (MVP vital)** (vol plané/battu, énergie de base, taux de capture fixe, terrain simplifié) et la **v2 (raffinement)** (GLMM complet d'attaque, couvert arbustif à $20\text{ m}$, thermiques 3D complets).

**Livrables (`docs/02_Technique/`) :**
- `ADR_03_Architecture_Logicielle_et_Perimetre_MVP.md`
- `Schema_Architecture_et_Flux.md` (arborescence détaillée + diagramme de composants Mermaid).

---

## Sous-étape 2.3 — Contrats de Données, Configurations YAML et Squelettes (Stubs)

**Objectif :** Convertir les fiches ODD en interfaces Python strictement typées et en fichiers de configuration validés automatiquement, afin que chaque futur module ait un cahier des charges non ambigu.

**Ce qu'il faut faire :**
- [ ] Choisir le mécanisme de validation des fichiers de configuration (ex : `Pydantic` + `PyYAML`) et le format d'export des résultats de simulation (ex : `Parquet` / `CSV`) pour préparer la comparaison avec [[Cibles_Validation_GPS]].
- [ ] Créer les premiers fichiers `configs/species/bonelli.yaml` et `configs/environments/alpilles.yaml` (avec les paramètres v1 actifs et les paramètres v2 commentés).
- [ ] Générer les squelettes de classes et fonctions (*stubs* avec `Protocol`, `dataclass`, `Enum`, *type hints* et docstrings complètes, sans implémentation métier).

**Livrables :**
- `docs/02_Technique/ADR_04_Validation_Config_et_Format_Sorties.md`
- Fichiers de configuration initiaux dans `configs/`.
- Squelettes de modules Python dans `src/`.

---

## Sous-étape 2.4 — Socle Qualité, Dépendances et Tests de Fumée

**Objectif :** Mettre en place un environnement de développement reproductible et automatisé prêt à accueillir le code du Jalon 3.

**Ce qu'il faut faire :**
- [ ] Configurer `pyproject.toml` à la racine du dépôt (dépendances Python, `pytest`, linter/formateur `ruff`, vérificateur de types).
- [ ] Mettre en place le dossier `tests/` avec un premier *smoke test* vérifiant que les configurations YAML se chargent sans erreur et que les interfaces sont cohérentes.
- [ ] Valider le passage au vert de `pytest` et fusionner la branche sur `main`.

**Livrables :**
- `pyproject.toml` à la racine du dépôt.
- Dossier `tests/` initialisé avec un premier test fonctionnel.

---

## Critères de Validation du Jalon 2

- [ ] Les 4 ADR sont rédigés, arbitrés et rangés dans `docs/02_Technique/`.
- [ ] L'arborescence `src/`, `configs/` et `tests/` existe et respecte la séparation `Core` / données.
- [ ] Le chargement de `bonelli.yaml` et `alpilles.yaml` passe les tests automatisés (`pytest`).
- [ ] La branche `arch/jalon-2-technique` est fusionnée sur `main` (`--no-ff`).