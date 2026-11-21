---
tags:
  - ibm
  - adr
  - performance
  - gis
  - reproducibility
type: adr
status: accepted
date: 2026-11-21
---

# ADR-02 — Résolution de Grille, Performances et Reproductibilité

> Cette fiche définit comment stocker et interroger la carte des Alpilles à $10\text{ m}$ sans saturer la mémoire ni ralentir le processeur. Elle fixe également la règle de gestion du hasard pour que deux simulations identiques donnent exactement le même résultat.

> **Liens internes :** [[jalon_2_architecture_technique]] | [[ODD_Env_Grilles_et_Parametres_Alpilles]] | [[ODD_Env_Sous_Modeles_Physiques]]

---

## 1. Contexte et Contraintes

L'emprise du massif des Alpilles ($\approx 25\text{ km} \times 15\text{ km}$) projetée en `EPSG:2154` sur une grille maîtresse de $10\text{ m} \times 10\text{ m}$ représente environ **$3,75\text{ millions}$ de pixels**.

Recalculer les ascendances ($w_{\text{oro}}$, $w_{\text{th}}$) sur toute la carte à chaque heure d'une année ($8\,760\text{ h}$) coûterait des milliards d'opérations inutiles sur des zones où aucun aigle ne vole.

---

## 2. Options Envisagées

* **Option A — Précalcul 2D complet à chaque heure (*Eager*) :** Recalcule des grilles complètes d'aérologie toutes les heures. Très lent et gourmand en RAM.
* **Option B — Couches statiques $10\text{ m}$ en RAM + Évaluation à la demande (*Lazy*) :** Charge la topographie et l'occupation du sol une seule fois à $t=0$ en mémoire, et ne calcule la physique de l'air qu'aux coordonnées réellement visitées par un oiseau.
* **Option C — Dégradation de la grille à $50\text{ m}$ ou $100\text{ m}$ :** Réduit la mémoire, mais écrase les falaises, les barres calcaires et le calcul du couvert à $20\text{ m}$.

---

## 3. Décision Retenue

**Option B : Grilles statiques à $10\text{ m}$ en RAM + Calcul paresseux (*Lazy*) ponctuel.**

1. **Empreinte mémoire maîtrisée :** Les couches statiques (`elevation`, `slope`, `aspect`, faciès OSO, `shrub_cover_20m`, perchoirs) sont chargées à $t=0$ en `float32` et `uint8` ($\approx 15\text{ Mo}$ par couche, soit $\approx 120\text{ Mo}$ au total).
2. **Calcul à la volée :** À chaque heure, seuls les paramètres globaux de couche limite ($Q_0$, $w^*$, $L$) sont mis à jour. Lors d'un appel à `get_aerology(x, y, z, t)`, la conversion `(x, y)` $\rightarrow$ `(ligne, colonne)` se fait en temps constant $O(1)$ et le calcul de $w_{\text{oro}} + w_{\text{th}}$ n'est exécuté que sur le point demandé (ou le petit vecteur de cases voisines évaluées par l'aigle).
3. **Reproductibilité stricte :** Tout le hasard (tirage Softmax du déplacement, apparition des proies, succès d'attaque) passe par un **unique générateur centralisé** `numpy.random.Generator` (algorithme PCG64) initialisé par une `seed` définie en configuration. L'usage du module global `random` de Python est interdit.

---

## 4. Conséquences

* **Avantages :** Simulation annuelle très rapide sans sacrifier la précision topographique à $10\text{ m}$, consommation RAM négligeable sur un PC standard, et résultats reproductibles à l'identique d'un lancement à l'autre.
* **Point de vigilance :** Si l'on souhaite plus tard afficher une carte complète des thermiques sur tout le massif pour de la visualisation, il faudra une petite fonction dédiée hors de la boucle de simulation.