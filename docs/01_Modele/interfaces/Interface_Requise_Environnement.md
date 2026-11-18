---
tags:
  - ibm
  - odd
  - raptor
  - bonelli
  - environment-interface
  - architecture
type: odd-spec
status: draft
---

# Contrat d'Interface : Environnement $\leftrightarrow$ `RaptorAgent`

> **Liens internes :** [[ODD_Agent_Variables_Etat_et_Parametres]] | [[ODD_Agent_Cycle_Comportemental]] | [[ODD_Agent_Sous_Modeles_Biophysiques]] | [[Interface_Requise_Environnement]]

Cette fiche définit le « contrat d'échange » entre la carte et l'oiseau : elle liste toutes les informations que l'environnement doit fournir à l'aigle (météo, courants ascendants, présence de proies, dérangement) et sous quel format. Elle garantit que l'on pourra changer de massif géographique plus tard sans modifier le code de l'oiseau.

## 1. Architecture Modulaire (Protocole `EnvironmentInterface`)

Pour garantir le découplage entre la mécanique générique de l'agent (`RaptorAgent`) et le territoire simulé (ex : massif des Alpilles, péninsule Ibérique), l'environnement doit exposer les méthodes de requête suivantes sans dévoiler sa structure interne de grille ou de maillage :

```python
from typing import Protocol, Tuple, List, Dict

class EnvironmentInterface(Protocol):
    def get_weather(self, x: float, y: float, t: float) -> Dict[str, float]: ...
    def get_aerology(self, x: float, y: float, z: float, t: float) -> float: ...
    def get_cell_habitat(self, x: float, y: float) -> Dict[str, float]: ...
    def sample_prey_encounter(self, x: float, y: float, t: float) -> Dict[str, float]: ...
    def get_territorial_context(self, x: float, y: float, territory_id: int) -> Dict[str, float]: ...
```

---

## 2. Spécification Exhaustive des Variables Environnementales Requises

### 2.1. Forçages Météorologiques et Éphémérides (Grille Méso-Échelle / Globale)

| Variable Exigée | Clé API / Symbole | Type | Unité | Résolution Spatiale | Fréquence de Mise à Jour | Justification Biologique / Rôle dans les Sous-Modèles |
| :--- | :---: | :--- | :---: | :---: | :---: | :--- |
| **Heure solaire & Éphémérides** | `t_sunrise`, `t_sunset`, `julian_day` | `float`, `int` | $\text{h}$, $\text{jour}$ | Globale | Journalière ($24\text{ h}$) | Déclenchement de la sortie du dortoir ($[-0.5\text{ h}, +2\text{ h}]$ autour du lever), retour au dortoir et transitions phénologiques $\Phi$. |
| **Vitesse moyenne du vent** | `wind_speed` ($W_t$) | `float` | $\text{m}\cdot\text{s}^{-1}$ | $8 \times 8\text{ km}$ (type SAFRAN) ou plus fin | Journalière ou Horaire | Effet quadratique sur $\tau_{flight}$ et $R_{day}$ (optimum à $5\text{ m}\cdot\text{s}^{-1}$, seuils critiques à $2.5$ et $7.5\text{ m}\cdot\text{s}^{-1}$). |
| **Cumul de précipitations** | `rainfall` ($Rain_t$) | `float` | $\text{mm}$ | $8 \times 8\text{ km}$ (type SAFRAN) | Journalière ou Horaire | Réduit significativement le temps en vol $\tau_{flight}$ et la portée $R_{day}$ dans toutes les phases et pour les deux sexes. |
| **Température de l'air** | `temp_mean`, `temp_min`, `temp_max` ($T_t$) | `float` | $^\circ\text{C}$ | $8 \times 8\text{ km}$ (type SAFRAN) | Horaire & Journalière | Pilote les ascendances thermiques, les coûts de thermorégulation et la mortalité des poussins en élevage ($\beta_{Tmax} = -0.48$ sur le succès d'envol). |

### 2.2. Topographie et Aérologie Locale (Grille Haute Résolution)

| Variable Exigée | Clé API / Symbole | Type | Unité | Résolution Spatiale | Fréquence de Mise à Jour | Justification Biologique / Rôle dans les Sous-Modèles |
| :--- | :---: | :--- | :---: | :---: | :---: | :--- |
| **Altitude du terrain (MNT)** | `elevation` ($z_{ground}$) | `float` | $\text{m asl}$ | $25 \times 25\text{ m}$ | Statique | Calcul de la hauteur de vol au-dessus du sol ($AGL = z - z_{ground}$) et masquage topographique pour les attaques par surprise. |
| **Pente et Exposition** | `slope`, `aspect` | `float` | $\text{degrés}$ | $25 \times 25\text{ m}$ | Statique | Sélection des falaises de nidification et calcul de la portance orographique. |
| **Vitesse verticale de l'air** | `w_uplift` ($w$) | `float` | $\text{m}\cdot\text{s}^{-1}$ | $25 \times 25\text{ m}$ à $100 \times 100\text{ m}$ | Pas de temps $\Delta t$ ($5\text{ min}$) | Combine l'ascendance thermique (fonction de $T_t$ et de l'ensoleillement) et orographique (fonction de $W_t$ et `slope`/`aspect`) pour déterminer la fraction de vol battu $\alpha_{flap}$. |

### 2.3. Habitat, Couvert Végétal et Ressources Trophiques

| Variable Exigée                      |        Clé API / Symbole         | Type             |                 Unité                 |               Résolution Spatiale                |                       Fréquence de Mise à Jour                       | Justification Biologique / Rôle dans les Sous-Modèles                                                                                                                                                                                                         |
| :----------------------------------- | :------------------------------: | :--------------- | :-----------------------------------: | :----------------------------------------------: | :------------------------------------------------------------------: | :------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Indice de détectabilité CLC**      | `prey_detectability` ($D_{CLC}$) | `float`          |     $\{0, 0.25, 0.5, 0.75, 1.0\}$     |  $100 \times 100\text{ m}$ (CORINE Land Cover)   |                         Statique / Annuelle                          | Définit l'accessibilité des proies par classe d'habitat ($1.0 =$ ouvert/garrigue basse/prairie ; $0 =$ fermé/forêt dense/urbain). Seuil $\ge 0.50$ définit un « bon spot de chasse ».                                                                         |
| **Couvert arbustif local**           |        `shrub_cover_20m`         | `float`          |           $\%$ ($[0, 100]$)           | Rayon de $20\text{ m}$ ($25 \times 25\text{ m}$) |                             Saisonnière                              | Variable binaire d'ouverture dans le GLMM de succès d'attaque : `OPEN` si $1\text{--}69\%$, `CLOSED` si $\ge 70\%$.                                                                                                                                           |
| **Densité de perchoirs**             |       `perch_availability`       | `bool` / `float` | $\text{perchoirs}\cdot\text{ha}^{-1}$ |             $25 \times 25\text{ m}$              |                               Statique                               | Permet l'initiation d'attaques à l'affût (`ATTACK = PERCHED`), favorisant l'effet de surprise.                                                                                                                                                                |
| **Indice Kilométrique de Biomasse**  |      `kbi_biomass` ($KBI$)       | `float`          |     $\text{g}\cdot\text{km}^{-1}$     |       $1 \times 1\text{ km}$ (grille UTM)        | Saisonnière (3 périodes/an : Mars `Br`, Juin `Pfdp`, Novembre `NBr`) | Biomasse disponible agrégée (Lapin $900\text{ g}$, Corvidés $642.5\text{ g}$, Perdrix $420\text{ g}$, Pigeon $400\text{ g}$). Plus faible en `NBr` (automne/hiver), régulière à l'intérieur du domaine vital ($285\text{--}678\text{ g}\cdot\text{km}^{-1}$). |
| **Générateur de rencontre de proie** |           `prey_event`           | `dict`           |                   -                   |                 Cellule courante                 |               À chaque $\Delta t$ en `FORAGING_SEARCH`               | Retourne si une proie est détectée, son espèce (masse $m_{prey}$), la taille du groupe $G \in [1, 50]$ et sa position initiale (`SOIL` vs `AIR`) pour paramétrer l'équation de capture.                                                                       |

### 2.4. Topologie Sociale, Sites de Nidification et Anthropisation

| Variable Exigée                    |  Clé API / Symbole  | Type               |         Unité          |      Résolution Spatiale       |         Fréquence de Mise à Jour         | Justification Biologique / Rôle dans les Sous-Modèles                                                                                                           |
| :--------------------------------- | :-----------------: | :----------------- | :--------------------: | :----------------------------: | :--------------------------------------: | :-------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Localisation des nids**          |    `nest_sites`     | `list[tuple]`      | $\text{m}$ $(x, y, z)$ | Ponctuelle (falaises / arbres) | Statique ($2\text{--}3$ nids/territoire) | Point d'ancrage du *Central Place Forager* et calcul des visites dans le rayon de $25\text{ m}$.                                                                |
| **Masque des territoires voisins** | `neighbor_k95_mask` | `dict[int, float]` |        $[0, 1]$        |   $100 \times 100\text{ m}$    |           Mensuelle / Annuelle           | Indique l'appartenance d'une cellule au noyau $K_{95\%}$ d'un couple voisin pour appliquer la répulsion territoriale (chevauchement cible $4.18\% \pm 3.06\%$). |
