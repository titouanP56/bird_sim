---
tags:
  - ibm
  - validation
  - gps
  - bonelli
  - pattern-oriented-modeling
type: validation-targets
status: draft
---

# Cibles de Validation Empirique (Données GPS & Suivi Terrain)

> **Liens internes :** [[ODD_Agent_Sous_Modeles_Biophysiques]] | [[ODD_Agent_Variables_Etat_et_Parametres]] | [[jalon_1_specifications_odd]] | [[feuille_de_route_ibm]]

> Cette fiche regroupe les statistiques réelles observées sur des Aigles de Bonelli équipés de balises GPS et suivis sur le terrain. Elle ne sert pas à piloter le comportement de l'aigle dans le code, mais fournit les valeurs de référence permettant de vérifier que la simulation reproduit fidèlement la réalité (Jalon 6).

---

## 1. Métriques Journalières de Mouvement (GLMM Télémétrie GPS)

À l'échelle journalière, la propension au vol ($\tau_{flight}$), la portée ($R_{day}$) et la rectitude des trajectoires ($St_{day}$) suivent une réponse quadratique au vent ($W_t$), et linéaire à la pluie ($Rain_t$), à la température ($T_t$) et à l'expérience ($Exp$) (modèles additifs sur variables centrées-réduites $Z$, Viollat et al. 2024) :

$$Y(S, \Phi) = \mu_{Y}(S, \Phi) + \beta_{Exp} Z_{Exp} + \beta_{Rain} Z_{Rain} + \beta_{T} Z_{T} + \beta_{W1} Z_{W} + \beta_{W2} Z_{W}^2$$

| Métrique $Y$ | Phase $\Phi$ | Sexe $S$ | Moyenne $\pm$ SD | $\beta_{Exp}$ | $\beta_{Rain}$ | $\beta_{T}$ | $\beta_{W1}$ (Vent) | $\beta_{W2}$ (Vent$^2$) |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **$\tau_{flight}$** (Prop. vol) | `PRE_BREEDING` | M / F | $0.17 \pm 0.05$ / $0.15 \pm 0.08$ | NS / $-0.31$ | $-0.19$ / $-0.26$ | $(-0.02)$ / NS | $+0.80$ / $+1.11$ | $-0.58$ / $-0.87$ |
| **$\tau_{flight}$** (Prop. vol) | `INCUBATION` | M / F | $0.26 \pm 0.06$ / $0.19 \pm 0.13$ | $-0.14$ / $-0.70$ | $-0.21$ / $-0.28$ | $+0.09$ / $+0.05$ | $+0.23$ / $+0.65$ | $-0.27$ / $-0.70$ |
| **$\tau_{flight}$** (Prop. vol) | `REARING` | M / F | $0.27 \pm 0.07$ / $0.24 \pm 0.11$ | $-0.08$ / $-0.19$ | $-0.25$ / $-0.16$ | $-0.06$ / $+0.17$ | $+0.15$ / $+0.34$ | $-0.30$ / $-0.48$ |
| **$R_{day}$** (Portée, $\text{m}$) | `PRE_BREEDING` | M / F | $2032 \pm 903$ / $1817 \pm 847$ | NS / $-0.45$ | $-0.11$ / $-0.16$ | NS / NS | $+0.42$ / $+0.90$ | $-0.33$ / $-0.81$ |
| **$R_{day}$** (Portée, $\text{m}$) | `INCUBATION` | M / F | $1892 \pm 854$ / $1088 \pm 933$ | $(-0.12)$ / $-0.77$ | NS / $-0.13$ | NS / NS | $+0.29$ / NS | $-0.26$ / NS |
| **$R_{day}$** (Portée, $\text{m}$) | `REARING` | M / F | $1673 \pm 767$ / $1298 \pm 888$ | $-0.12$ / $-0.56$ | $-0.08$ / NS | NS / $+0.54$ | $+0.11$ / $(+0.20)$ | $-0.13$ / NS |
| **$St_{day}$** (Rectitude) | `PRE_BREEDING` | M / F | $0.15 \pm 0.09$ / $0.16 \pm 0.09$ | NS / $-0.26$ | $+0.08$ / $+0.10$ | $+0.05$ / $+0.07$ | $-0.62$ / $-0.41$ | $+0.46$ / NS |
| **$St_{day}$** (Rectitude) | `INCUBATION` | M / F | $0.06 \pm 0.03$ / $0.09 \pm 0.09$ | NS / $(-0.14)$ | $+0.08$ / NS | NS / NS | NS / $-0.47$ | NS / $+0.43$ |
| **$St_{day}$** (Rectitude) | `REARING` | M / F | $0.06 \pm 0.05$ / $0.06 \pm 0.04$ | NS / $-0.12$ | $+0.08$ / $+0.06$ | $(+0.02)$ / $+0.10$ | NS / NS | $(+0.07)$ / NS |

*Interprétation écologique pour le calibrage :* Les pentes estimées $\beta_{Exp}$ sont négatives : les individus expérimentés passent moins de temps en vol, ont un rayon d'action plus court et des trajectoires plus sinueuses grâce à leur mémoire spatiale des bons patchs de chasse.

---

## 2. Métriques Émergentes Globales (Espace, Chasse & Démographie)

En complément des budgets temps journaliers, les sorties agrégées de la simulation devront converger vers les ordres de grandeur suivants :

| Domaine | Métrique | Valeur Cible Empirique | Référence |
| :--- | :--- | :---: | :--- |
| **Occupation de l'espace** | Domaine vital global ($K_{95\%}$) | $54.84 \pm 20.78\text{ km}^2$ (jusqu'à $\approx 70\text{ km}^2$ en France) | Morollón et al. 2022 |
| **Occupation de l'espace** | Zone d'alimentation/repos ($K_{75\%}$) | $24.30 \pm 10.18\text{ km}^2$ | Morollón et al. 2022 |
| **Occupation de l'espace** | Zone nucléaire autour du nid ($K_{50\%}$) | $11.17 \pm 4.90\text{ km}^2$ | Morollón et al. 2022 |
| **Territorialité** | Chevauchement entre couples voisins | $4.18\% \pm 3.06\%$ | Morollón et al. 2022 |
| **Chasse** | Taux global de succès des attaques | $28.2\%$ | Martínez et al. 2014 |
| **Reproduction** | Probabilité de ponte ($P_{breed}$) | $0.85$ ($0.95$ sans nouveau recruté) | López-López et al. 2022 |
| **Reproduction** | Productivité moyenne ($N_{fledge}$) | $0.99\text{ jeune envolé / couple / an}$ | López-López et al. 2022 |