---
tags:
  - ibm
  - odd
  - roadmap
  - jalon-1
  - obsidian
type: milestone-spec
parent: "[[feuille_de_route_ibm]]"
status: in-progress
---

# Jalon 1 : Spécification Conceptuelle (Protocole ODD)

- **Référence parente :** [[feuille_de_route_ibm]] (Section Jalon 1)
- **Objectif :** Figer l'ensemble des règles biologiques et physiques sous forme de spécifications chiffrées avant toute décision technique d'architecture logicielle ([[Jalon 2]]).

## Sous-étape 1.1 : Spécification de l'Agent (ODD Espèce)

Traduire la biologie de l'Aigle de Bonelli (*Aquila fasciata*) en variables et règles mathématiques, en séparant la mécanique générique (rapace planeur) des paramètres spécifiques à l'espèce.

- **Actions à mener :**
  - Lister les variables d'état internes d'un individu (position 3D, énergie $E$, jabot $C$, sexe, expérience, phase phénologique).
  - Formaliser la machine à états finis (FSM) journalière et l'ordonnancement d'un pas de temps $\Delta t$.
  - Écrire les équations biophysiques (dépense énergétique par mode de vol, succès d'attaque GLMM, sélection de pas SSF).
  - Isoler les paramètres chiffrés et taguer les valeurs manquantes avec `[À CALIBRER]`.
- **Résultats attendus :**
  - [x] Note `ODD_Agent_Variables_Etat_et_Parametres` rédigée (incluant l'ébauche de `bonelli.yaml`).
  - [x] Note `ODD_Agent_Cycle_Comportemental` rédigée (diagramme FSM + règles de transition).
  - [x] Note [[ODD_Agent_Sous_Modeles_Biophysiques]] rédigée (équations énergie + déplacement).

## Sous-étape 1.2 : Définition du Contrat d'Interface Environnementale

Établir la liste stricte des données que l'agent doit percevoir pour prendre ses décisions, sans jamais dépendre de la structure interne des futures cartes SIG.

- **Actions à mener :**
  - Recenser chaque variable environnementale appelée dans les équations de la sous-étape 1.1 (météo, ascendance verticale $w_{uplift}$, détectabilité proies, dérangement, emprises territoriales).
  - Définir les signatures exactes des méthodes de requête (`EnvironmentInterface`).
  - Spécifier les types, unités et plages de valeurs garanties pour chaque donnée retournée.
- **Résultats attendus :**
  - [x] Note [[Interface_Environnement_Schema_Complet]] finalisée (compléter le schéma des dictionnaires de retour et des unités).

## Sous-étape 1.3 : Spécification de l'Environnement (ODD Territoire — Alpilles)

Décrire la physique et l'écologie du massif des Alpilles uniquement à travers le prisme des besoins identifiés à la sous-étape 1.2.

- **Actions à mener :**
  - Définir l'emprise spatiale (bounding box en Lambert-93 / EPSG:2154) et recenser les couches SIG sources (MNT, occupation du sol CORINE/OSO, falaises, sentiers).
  - Écrire les équations de transformation des données brutes en variables utiles à l'agent (calcul d'ascendance orographique et thermique $w_{uplift}$, indice de stabilité trophique KBI, indice de dérangement temporel).
  - Séparer les calculs physiques génériques des constantes locales des Alpilles.
- **Résultats attendus :**
  - [ ] Note [[ODD_Env_Couches_Spatiales_et_Parametres]] rédigée (incluant l'ébauche de `alpilles.yaml`).
  - [ ] Note [[ODD_Env_Aerologie_et_Meteo]] rédigée (forçage météo + physique des ascendances).
  - [ ] Note [[ODD_Env_Ressources_Trophiques_et_Derangement]] rédigée (guildes de proies, KBI et fréquentation humaine).

## Sous-étape 1.4 : Audit de Cohérence & Alignement des Échelles

Vérifier que les spécifications Agent et Environnement s'emboîtent sans contradiction mathématique ou d'échelle avant de passer au code.

- **Actions à mener :**
  - **Contrôle des unités et clés :** Vérifier que 100 % des variables appelées par [[ODD_Agent_Sous_Modeles_Biophysiques]] sont produites avec le même nom et la même unité dans [[Interface_Environnement_Schema_Complet]].
  - **Contrôle d'échelle spatio-temporelle :** Confronter le pas de temps de l'agent ($\Delta t = 5\text{ min}$, soit $\approx 3,6\text{ km}$ parcourus en croisière) à la finesse des phénomènes locaux (rayon de $20\text{ m}$ autour d'une proie, tampon de $25\text{ m}$ au nid).
  - **Séparation Règles vs Validation :** Isoler les régressions statistiques journalières (portée $R_{day}$, rectitude $St_{day}$) dans une note dédiée aux métriques de validation future (Jalon 6) pour ne pas les mélanger aux règles de mouvement pas-à-pas.
- **Résultats attendus :**
  - [ ] Note [[Metriques_Validation_Empirique]] créée (cibles statistiques pour le calibrage).
  - [ ] Liste des verrous d'échelle prêts à être tranchés sous forme d'ADR au démarrage du Jalon 2 de [[feuille_de_route_ibm]] (ex. choix de la résolution de grille et méthode d'échantillonnage le long d'un segment de vol).

## Critère de validation finale (Go / No-Go Jalon 1)

- [ ] Toutes les notes ODD Agent et Environnement ont le statut `status: validated`.
- [ ] Aucune variable requise par l'agent n'est absente de l'interface environnementale.
- [ ] Les fichiers de configuration `bonelli.yaml` et `alpilles.yaml` sont structurés, même si certains paramètres portent encore la mention `[À CALIBRER]`.