---
tags:
  - ibm
  - adr
  - architecture
  - mvp
type: adr
status: accepted
date: 2026-11-21
---

# ADR-03 — Architecture Logicielle Modulaire et Périmètre MVP (v1 vs v2)

> Cette fiche fixe l'organisation des dossiers du code Python pour garder le projet propre et facile à faire évoluer. Elle trace aussi la frontière entre ce que l'on code en priorité (v1 minimale qui fonctionne) et les raffinements scientifiques gardés pour la suite (v2).

> **Liens internes :** [[jalon_2_architecture_technique]] | [[Interface_Requise_Environnement]] | [[ODD_Agent_Cycle_Comportemental]] | [[ODD_Agent_Sous_Modeles_Biophysiques]]

---

## 1. Contexte et Contraintes

Les fiches ODD contiennent beaucoup de détails scientifiques (couvert arbustif à $20\text{ m}$, thermiques 3D, phénologie journalière, GLMM complet de chasse). Tout coder d'un seul coup augmente fortement le risque de bugs impossibles à diagnostiquer.

De plus, le projet doit pouvoir changer d'espèce ou de massif géographique sans modifier le moteur de base, tout en restant découpé en fichiers courts ($< 200$ lignes) pour travailler efficacement avec des agents IA.

---

## 2. Options Envisagées

* **Option 1 — Scripts plats (`model.py`, `agent.py`, `env.py`) :** Rapide au démarrage, mais crée vite des fichiers géants et des dépendances circulaires difficiles à tester.
* **Option 2 — Architecture modulaire par domaine + Injection de dépendances :** Découpe le code en 4 blocs indépendants (`core`, `agents`, `environment`, `io`) reliés uniquement par des contrats (`Protocol`).
* **Option 3 — Architecture événementielle (*Event Bus / Pub-Sub*) :** Découplage maximal, mais rend le suivi pas à pas d'une trajectoire difficile à déboguer.

---

## 3. Décision Retenue

**Option 2 : Architecture modulaire par domaine avec activation progressive par *feature flags* (v1 $\rightarrow$ v2).**

### Organisation des dossiers (`src/bonelli_ibm/`)
* `core/` : Types de données (`Enum`, `dataclass`), contrat `EnvironmentInterface`, chargement des configs, générateur aléatoire et `scheduler`. **Ne dépend d'aucun autre dossier.**
* `agents/` : `RaptorAgent`, machine à états (`state_machine.py`) et fonctions mathématiques pures (`energetics.py`, `movement.py`, `foraging.py`). Ne connaît l'environnement que via `EnvironmentInterface`.
* `environment/` : `MockEnvironment` (terrain synthétique sans SIG pour tester vite), `AlpillesEnvironment` (vrai terrain), chargeur SIG (`gis_loader.py`), physique de l'air (`aerology.py`) et proies (`trophic.py`).
* `io/` : Export des trajectoires et indicateurs journaliers (`exporter.py`).
* `configs/` : Données pures séparées du code (`species/bonelli.yaml` et `environments/alpilles.yaml`).

### Frontière MVP v1 vs v2 (pilotée par booléens dans les YAML)

| Module | Périmètre **v1 (MVP vital)** | Périmètre **v2 (Raffinement)** |
| :--- | :--- | :--- |
| **Terrain** | `MockEnvironment` simple (ou MNT seul) | Couplage complet `RGE ALTI` $5\text{ m}$ + `OSO Theia` $10\text{ m}$ + `shrub_cover_20m` |
| **Aérologie** | $w_{\text{oro}}$ simplifié + $w^*$ global avec coupure Mistral ($12,87\text{ m/s}$) | Profil 3D trapézoïdal d'Allen + subsidence ($w_e$, $w_D$) |
| **Chasse** | Probabilité de succès fixe ($28,2\%$) + densité simple | GLMM complet (taille de groupe, ouvert/fermé, air/sol, surprise) + rythmes circadiens |
| **Végétation** | Couvert statique | Phénologie par degrés-jours (`GDD`) et séries `NDVI` |

---

## 4. Conséquences

* **Avantages :** On peut faire voler un premier aigle et vérifier son bilan énergétique très tôt sur un `MockEnvironment` sans attendre les fichiers SIG réels. Chaque équation est isolée dans une fonction pure facile à tester unitairement.
* **Point de vigilance :** Respecter strictement la règle de sens des imports (`core` n'importe jamais `agents` ni `environment`) pour éviter toute dépendance circulaire.