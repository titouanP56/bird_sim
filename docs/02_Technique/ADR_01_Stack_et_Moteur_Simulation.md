---
tags:
  - ibm
  - adr
  - architecture
  - python
type: adr
status: accepted
date: 2026-11-21
---

# ADR-01 — Choix de la Stack Technique et du Moteur de Simulation

> Cette fiche explique pourquoi nous codons un moteur de simulation Python/NumPy sur mesure plutôt que d'utiliser un framework tout fait comme `Mesa-Geo`. Elle fixe aussi la liste des bibliothèques principales du projet.

> **Liens internes :** [[jalon_2_architecture_technique]] | [[Interface_Requise_Environnement]] | [[ODD_Env_Dynamique_et_Planification]]

---

## 1. Contexte et Contraintes

La simulation doit faire évoluer **peu d'agents** (quelques couples territoriaux, soit $2$ à $20$ aigles) sur un **très grand nombre de pas de temps** ($105\,120$ tours par an à $\Delta t = 5\text{ min}$). À chaque tour, chaque oiseau interroge l'environnement (météo, relief, ascendances, proies).

Trois contraintes supplémentaires guident le choix :
* **Environnement natif Windows :** pas de dépendance lourde à Linux ou WSL2.
* **Découplage strict :** le moteur doit respecter le contrat [[Interface_Requise_Environnement]].
* **Développement assisté par IA :** le code doit rester simple, lisible et sans « magie » cachée de framework.

---

## 2. Options Envisagées

* **Option 1 — Framework `Mesa` + `Mesa-Geo` :** Fournit un moteur multi-agents clé en main avec gestion SIG intégrée (`GeoSpace`, index spatial R-tree). En contrepartie, il impose un héritage rigide, des dépendances SIG parfois complexes sous Windows et un surcoût de calcul inutile pour moins de $50$ agents.
* **Option 2 — Moteur Python / `NumPy` sur mesure :** Une boucle principale simple (~50 lignes) qui orchestre les 4 pas de temps ($t=0$, $24\text{ h}$, $1\text{ h}$, $5\text{ min}$) et relie les agents à l'environnement via un `Protocol` Python.
* **Option 3 — Architecture ECS (*Entity-Component-System*) :** Très performante pour simuler des dizaines de milliers d'entités simples, mais inutilement complexe pour la machine à états détaillée d'un rapace.

---

## 3. Décision Retenue

**Option 2 : Moteur de simulation Python / `NumPy` sur mesure.**

**Stack retenue :**
* **Cœur de calcul :** Python 3.11+, `numpy`, `pandas`, `pyarrow`.
* **Configuration & validation :** `pydantic` (v2) et `pyyaml`.
* **Couche SIG (groupe optionnel `[gis]`) :** `rasterio` et `xarray` uniquement pour le chargement des vrais rasters des Alpilles.
* **Qualité :** `pytest` (tests) et `ruff` (formatage et détection d'erreurs).

---

## 4. Conséquences

* **Avantages :** Installation 100 % native et rapide sous Windows, accès direct aux grilles en mémoire, contrôle total sur l'ordre d'exécution décrit dans [[ODD_Env_Dynamique_et_Planification]], code très facile à maintenir et à faire générer par des agents IA.
* **Point de vigilance :** Il faut coder nous-mêmes le petit ordonnanceur (`scheduler.py`) et l'export des résultats (`exporter.py`), ce qui reste trivial et bien maîtrisé.