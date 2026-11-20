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

> **Liens internes :** [[ODD_Agent_Variables_Etat_et_Parametres]] | [[ODD_Agent_Cycle_Comportemental]] | [[ODD_Agent_Sous_Modeles_Biophysiques]] | [[ODD_Env_Grilles_et_Parametres_Alpilles]] | [[ODD_Env_Dynamique_et_Planification]] | [[ODD_Env_Sous_Modeles_Physiques]]

## 1. Architecture Modulaire (Protocole `EnvironmentInterface`)

Pour garantir le découplage entre la mécanique générique de l'agent (`RaptorAgent`) et le territoire simulé (ex : massif des Alpilles), l'environnement doit exposer les méthodes de requête suivantes sans dévoiler sa structure interne de grille ou de maillage, dans le respect strict de l'hypothèse **zéro humain** :

```python
from typing import Protocol, Tuple, List, Dict, Any

class EnvironmentInterface(Protocol):
    def get_weather(self, x: float, y: float, t: float) -> Dict[str, float]: ...
    def get_aerology(self, x: float, y: float, z: float, t: float) -> float: ...
    def get_cell_habitat(self, x: float, y: float) -> Dict[str, float]: ...
    def sample_prey_encounter(self, x: float, y: float, t: float) -> Dict[str, Any]: ...
    def get_territorial_context(self, x: float, y: float, territory_id: int) -> Dict[str, Any]: ...
```

---

## 2. Spécification Exhaustive des Variables Environnementales Requises

### 2.1. Forçages Météorologiques et Éphémérides (Grille Méso-Échelle / Globale)

| Variable Exigée | Clé API / Symbole | Type | Unité | Résolution Spatiale | Fréquence de Mise à Jour | Justification Biologique / Rôle dans les Sous-Modèles |
| :--- | :---: | :--- | :---: | :---: | :---: | :--- |
| **Heure solaire & Éphémérides** | `t_sunrise`, `t_sunset`, `julian_day` | `float`, `int` | $\text{h}$, $\text{jour}$ | Globale | Journalière ($24\text{ h}$) | Déclenchement de la sortie du dortoir ($[-0.5\text{ h}, +2\text{ h}]$ autour du lever), retour au dortoir et transitions phénologiques $\Phi$. |
| **Vitesse moyenne du vent** | `wind_speed` ($W_t$) | `float` | $\text{m}\cdot\text{s}^{-1}$ | $8 \times 8\text{ km}$ (type SAFRAN) ou station | Horaire ($1\text{ h}$) | Effet quadratique sur $\tau_{flight}$ et $R_{day}$ (optimum à $5\text{ m}\cdot\text{s}^{-1}$, seuils critiques à $2.5$ et $7.5\text{ m}\cdot\text{s}^{-1}$) et déclenchement de la coupure thermique Mistral à $12.87\text{ m}\cdot\text{s}^{-1}$. |
| **Cumul de précipitations** | `rainfall` ($Rain_t$) | `float` | $\text{mm}$ | $8 \times 8\text{ km}$ (type SAFRAN) ou station | Horaire ($1\text{ h}$) | Réduit significativement le temps en vol $\tau_{flight}$ et la portée $R_{day}$ dans toutes les phases et pour les deux sexes. |
| **Température de l'air** | `temp_mean`, `temp_min`, `temp_max` ($T_t$) | `float` | $^\circ\text{C}$ | $8 \times 8\text{ km}$ (type SAFRAN) ou station | Horaire ($1\text{ h}$) & Journalière ($24\text{ h}$) | Pilote les ascendances thermiques ($Q_0$, $\theta_0$, $w^*$), les coûts de thermorégulation et la mortalité des poussins en élevage ($\beta_{Tmax} = -0.48$ sur le succès d'envol). |

### 2.2. Topographie et Aérologie Locale (Grille Haute Résolution)

| Variable Exigée | Clé API / Symbole | Type | Unité | Résolution Spatiale | Fréquence de Mise à Jour | Justification Biologique / Rôle dans les Sous-Modèles |
| :--- | :---: | :--- | :---: | :---: | :---: | :--- |
| **Altitude du terrain (MNT)** | `elevation` ($z_{ground}$) | `float` | $\text{m asl}$ | $10 \times 10\text{ m}$ (rééchantillonné depuis $5\text{ m}$) | Statique | Calcul de la hauteur de vol au-dessus du sol ($AGL = z - z_{ground}$) et masquage topographique pour les attaques par surprise. |
| **Pente et Exposition** | `slope`, `aspect` | `float` | $\text{degrés}$ | $10 \times 10\text{ m}$ (dérivé à $5\text{ m}$) | Statique | Sélection des falaises de nidification et calcul de la portance orographique $w_{\text{oro}}$ (convertis de $\text{rad}$ en $\text{degrés}$ à l'exposition API). |
| **Vitesse verticale de l'air** | `w_uplift` ($w$) | `float` | $\text{m}\cdot\text{s}^{-1}$ | $10 \times 10\text{ m}$ | Pas de temps $\Delta t$ ($5\text{ min}$) | Somme linéaire $w_{\text{oro}} + w_{\text{th}}$ combinant ascendance orographique et convection thermique 3D pour déterminer la fraction de vol battu $\alpha_{flap}$. |

### 2.3. Habitat, Couvert Végétal et Ressources Trophiques

| Variable Exigée | Clé API / Symbole | Type | Unité | Résolution Spatiale | Fréquence de Mise à Jour | Justification Biologique / Rôle dans les Sous-Modèles |
| :--- | :---: | :--- | :---: | :---: | :---: | :--- |
| **Indice de détectabilité CLC** | `prey_detectability` ($D_{CLC}$) | `float` | $\{0, 0.25, 0.5, 0.75, 1.0\}$ | $10 \times 10\text{ m}$ (OSO Theia) | Statique / Annuelle | Définit l'accessibilité des proies par faciès naturel ($1.0 =$ falaises/pelouses sèches ; $0.75 =$ garrigues/prairies humides ; $0.50 =$ agrosystèmes extensifs ; $0 =$ pinède/chênaie fermée). Seuil $\ge 0.50$ définit un « bon spot de chasse ». |
| **Couvert arbustif local** | `shrub_cover_20m` | `float` | $\%$ ($[0, 100]$) | Rayon de $20\text{ m}$ (sur grille $10\text{ m}$) | Journalière / Saisonnière | Variable binaire d'ouverture dans le GLMM de succès d'attaque : `OPEN` si $1\text{--}69\%$, `CLOSED` si $\ge 70\%$. |
| **Densité de perchoirs** | `perch_availability` | `bool` / `float` | $\text{perchoirs}\cdot\text{ha}^{-1}$ | $10 \times 10\text{ m}$ | Statique / Annuelle | Disponibilité en perchoirs naturels (vires rocheuses, houppiers, lisières) permettant l'initiation d'attaques à l'affût (`ATTACK = PERCHED`). |
| **Indice Kilométrique de Biomasse** | `kbi_biomass` ($KBI$) | `float` | $\text{g}\cdot\text{km}^{-1}$ | $1 \times 1\text{ km}$ (grille UTM) | Saisonnière (3 périodes/an : Mars `Br`, Juin `Pfdp`, Novembre `NBr`) | Biomasse disponible agrégée des **populations sauvages uniquement** (Lapin $900\text{ g}$, Corvidés $642.5\text{ g}$, Perdrix $420\text{ g}$, Pigeon $400\text{ g}$, Lézard ocellé ; exclusion stricte de tout lâcher cynégétique). Référence intra-domaine : $285\text{--}678\text{ g}\cdot\text{km}^{-1}$. |
| **Générateur de rencontre de proie** | `prey_event` | `dict` | - | Cellule courante ($10 \times 10\text{ m}$) | À chaque $\Delta t$ ($5\text{ min}$) en `FORAGING_SEARCH` | Processus de Poisson inhomogène pondéré par $D_{CLC}$, $KBI$ et le rythme circadien horaire ; retourne `detected`, l'espèce (`mass` $m_{prey}$), la taille du groupe $G \in [1, 50]$ et la position initiale (`SOIL` vs `AIR`). |

### 2.4. Topologie Sociale et Sites de Nidification Naturels

| Variable Exigée | Clé API / Symbole | Type | Unité | Résolution Spatiale | Fréquence de Mise à Jour | Justification Biologique / Rôle dans les Sous-Modèles |
| :--- | :---: | :--- | :---: | :---: | :---: | :--- |
| **Localisation des nids** | `nest_sites` | `list[tuple]` | $\text{m}$ $(x, y, z)$ | Ponctuelle (falaises naturelles / arbres) | Statique ($2\text{--}3$ nids/territoire) | Point d'ancrage du *Central Place Forager* sur les parois calcaires et escarpements naturels, et calcul des visites dans le rayon de $25\text{ m}$. |
| **Masque des territoires voisins** | `neighbor_k95_mask` | `dict[int, float]` | $[0, 1]$ | $10 \times 10\text{ m}$ | Mensuelle / Annuelle | Indique l'appartenance d'une cellule au noyau $K_{95\%}$ d'un couple voisin pour appliquer la répulsion territoriale (chevauchement cible $4.18\% \pm 3.06\%$). |